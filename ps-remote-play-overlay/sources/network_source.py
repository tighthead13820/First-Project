"""
External network TargetSource — UDP JSON telemetry → screen targets.

External apps (simulators, private game servers, debug tools) can push
target coordinates as JSON datagrams. This module does **not** capture
game video; it only receives explicit coordinate payloads you send.

Default bind: 127.0.0.1:5555

Example packet (UDP):
  {
    "targets": [
      {"id": "bot_1", "head_x": 1100, "head_y": 480},
      {"id": "bot_2", "x": 800, "y": 520, "chest_x": 800, "chest_y": 560}
    ],
    "screen_width": 1920,
    "screen_height": 1080
  }

Or a bare list:
  [{"id": "a", "head_x": 960, "head_y": 540}]
"""

from __future__ import annotations

import json
import socket
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from aim_core.types import CameraState, ScreenTarget, Vec3, WorldTarget

from .base import TargetSource

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5555
DEFAULT_CHEST_OFFSET_Y = 25.0
STALE_SECONDS = 0.5  # clear targets if no packet arrives


def parse_network_payload(
    data: bytes | str,
    *,
    default_chest_offset_y: float = DEFAULT_CHEST_OFFSET_Y,
) -> tuple[list[ScreenTarget], Optional[int], Optional[int]]:
    """
    Parse a JSON UDP payload into ScreenTarget list.

    Returns (targets, screen_width_or_None, screen_height_or_None).
    """
    if isinstance(data, bytes):
        text = data.decode("utf-8", errors="replace").strip()
    else:
        text = data.strip()
    if not text:
        return [], None, None

    payload: Any = json.loads(text)
    screen_w: Optional[int] = None
    screen_h: Optional[int] = None
    raw_list: list[Any]

    if isinstance(payload, dict):
        if "screen_width" in payload:
            screen_w = int(payload["screen_width"])
        if "screen_height" in payload:
            screen_h = int(payload["screen_height"])
        raw_list = payload.get("targets", payload.get("data", []))
        if not isinstance(raw_list, list):
            raw_list = []
    elif isinstance(payload, list):
        raw_list = payload
    else:
        return [], None, None

    targets: list[ScreenTarget] = []
    for idx, item in enumerate(raw_list):
        if not isinstance(item, dict):
            continue
        tid = str(item.get("id", f"net_{idx}"))
        # Accept head_x/head_y or x/y aliases
        if "head_x" in item and "head_y" in item:
            hx = float(item["head_x"])
            hy = float(item["head_y"])
        elif "x" in item and "y" in item:
            hx = float(item["x"])
            hy = float(item["y"])
        else:
            continue

        if "chest_x" in item and "chest_y" in item:
            cx = float(item["chest_x"])
            cy = float(item["chest_y"])
        else:
            cx = hx
            cy = hy + default_chest_offset_y

        alive = bool(item.get("alive", True))
        visible = bool(item.get("visible", True))
        team_raw = item.get("team", 1)
        try:
            team = int(team_raw)
        except (TypeError, ValueError):
            team = 1 if str(team_raw).lower() in {"enemy", "1", "hostile"} else 0

        targets.append(
            ScreenTarget(
                id=tid,
                screen_x=hx,
                screen_y=hy,
                head_x=hx,
                head_y=hy,
                chest_x=cx,
                chest_y=cy,
                velocity_x=float(item.get("velocity_x", 0.0)),
                velocity_y=float(item.get("velocity_y", 0.0)),
                alive=alive,
                visible=visible,
                team=team,
            )
        )
    return targets, screen_w, screen_h


@dataclass
class ExternalNetworkTargetSource(TargetSource):
    """UDP JSON telemetry → TargetSource for the live aim pipeline."""

    name: str = "external-network-udp"
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    screen_width: int = 1920
    screen_height: int = 1080
    stale_seconds: float = STALE_SECONDS
    auto_start: bool = True

    _sock: Optional[socket.socket] = field(default=None, init=False, repr=False)
    _thread: Optional[threading.Thread] = field(default=None, init=False, repr=False)
    _stop: threading.Event = field(default_factory=threading.Event, init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)
    _targets: list[ScreenTarget] = field(default_factory=list, init=False, repr=False)
    _last_packet_time: float = field(default=0.0, init=False, repr=False)
    _packets_received: int = field(default=0, init=False, repr=False)
    _parse_errors: int = field(default=0, init=False, repr=False)
    _started: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.auto_start:
            self.start()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def start(self) -> None:
        if self._started:
            return
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.host, self.port))
        sock.settimeout(0.25)  # non-blocking-ish: wake to check stop flag
        self._sock = sock
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._reader_loop,
            name="ExternalNetworkTargetSource",
            daemon=True,
        )
        self._thread.start()
        self._started = True
        print(f"[network-source] listening UDP {self.host}:{self.port}")

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
        self._started = False
        print("[network-source] stopped")

    def set_screen_size(self, width: int, height: int) -> None:
        with self._lock:
            self.screen_width = int(width)
            self.screen_height = int(height)

    # ------------------------------------------------------------------
    # Background reader
    # ------------------------------------------------------------------
    def _reader_loop(self) -> None:
        assert self._sock is not None
        while not self._stop.is_set():
            try:
                data, _addr = self._sock.recvfrom(65535)
            except socket.timeout:
                continue
            except OSError:
                if self._stop.is_set():
                    break
                continue
            try:
                targets, sw, sh = parse_network_payload(data)
            except (json.JSONDecodeError, TypeError, ValueError) as exc:
                self._parse_errors += 1
                if self._parse_errors <= 3:
                    print(f"[network-source] parse error: {exc}")
                continue

            with self._lock:
                if sw is not None:
                    self.screen_width = sw
                if sh is not None:
                    self.screen_height = sh
                self._targets = targets
                self._last_packet_time = time.monotonic()
                self._packets_received += 1

    # ------------------------------------------------------------------
    # TargetSource API
    # ------------------------------------------------------------------
    def get_targets(self) -> list[ScreenTarget]:
        """Thread-safe snapshot (alias used by callers / docs)."""
        return self.get_screen_targets()

    def get_screen_targets(self) -> list[ScreenTarget]:
        with self._lock:
            if (
                self.stale_seconds > 0
                and self._last_packet_time > 0
                and (time.monotonic() - self._last_packet_time) > self.stale_seconds
            ):
                return []
            return list(self._targets)

    def get_world_targets(self) -> list[WorldTarget]:
        return []

    def get_camera_state(self) -> CameraState:
        with self._lock:
            w, h = self.screen_width, self.screen_height
        return CameraState(
            position=Vec3(0.0, 1.7, 0.0),
            yaw=0.0,
            pitch=0.0,
            vfov_deg=75.0,
            screen_width=w,
            screen_height=h,
        )

    def tick(self, dt: float) -> None:
        # Background thread owns I/O; tick only enforces staleness lazily
        # via get_screen_targets().
        del dt

    def describe(self) -> str:
        with self._lock:
            n = len(self._targets)
            pkts = self._packets_received
        return f"{self.name} ({self.host}:{self.port}, targets={n}, pkts={pkts})"

    def stats(self) -> dict[str, int | float | bool]:
        with self._lock:
            return {
                "packets_received": self._packets_received,
                "parse_errors": self._parse_errors,
                "target_count": len(self._targets),
                "started": self._started,
                "last_packet_age_s": (
                    time.monotonic() - self._last_packet_time
                    if self._last_packet_time
                    else -1.0
                ),
            }
