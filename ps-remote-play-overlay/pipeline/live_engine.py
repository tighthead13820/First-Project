"""
Live production aim pipeline.

TargetSource → aim_core → StickControllerModel → ControllerState → ViGEm

Does NOT include PS Remote Play screen capture. Use MockScreenTargetSource
for end-to-end validation, or implement TargetSource for your own adapter.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Optional

from aim_core.config import AimConfig
from aim_core.engine import AimAssistEngine
from aim_core.screen_engine import ScreenAimConfig, ScreenAimEngine
from aim_core.stick_model import StickControllerModel
from aim_core.types import ScreenAimResult
from controls.state import ControllerState
from sources.base import TargetSource
from sources.mock_screen_source import MockScreenTargetSource


@dataclass
class LivePipelineState:
    """Dashboard / HUD snapshot."""

    aim_core_active: bool = False
    target_source_name: str = ""
    selected_target_id: Optional[str] = None
    tracking_status: str = "SEARCHING"
    target_bone: str = "head"
    snap_mode: bool = False
    prediction: bool = True
    smoothing: str = "exp"
    response_speed: float = 35.0
    centre_x: float = 960.0
    centre_y: float = 540.0
    target_x: float = 0.0
    target_y: float = 0.0
    pixel_error_x: float = 0.0
    pixel_error_y: float = 0.0
    total_pixel_error: float = 0.0
    yaw_error_deg: float = 0.0
    pitch_error_deg: float = 0.0
    stick_x: float = 0.0
    stick_y: float = 0.0
    hardware_armed: bool = False
    hardware_connected: bool = False
    debug_lines: list[str] = field(default_factory=list)
    trail: Deque[tuple[float, float]] = field(default_factory=lambda: deque(maxlen=30))


@dataclass
class LiveAimPipeline:
    """
    Orchestrates the live loop: capture → aim → stick → state.

    Modes:
      - screen: ScreenAimEngine + screen targets (default for overlay)
      - world:  AimAssistEngine + 3D world targets
    """

    state: ControllerState
    target_source: TargetSource = field(default_factory=MockScreenTargetSource)
    mode: str = "screen"
    enabled: bool = False
    auto_l2: bool = True
    auto_r2: bool = True
    recoil_compensate: bool = True
    recoil_vertical: float = 0.35
    recoil_horizontal: float = 0.08

    screen_engine: ScreenAimEngine = field(default_factory=ScreenAimEngine)
    world_engine: AimAssistEngine = field(default_factory=AimAssistEngine)
    stick_model: StickControllerModel = field(default_factory=StickControllerModel)

    dashboard: LivePipelineState = field(default_factory=LivePipelineState)
    last_result: Optional[ScreenAimResult] = None
    _fire_time: float = 0.0
    _world_yaw: float = 0.0
    _world_pitch: float = 0.0

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)
        if not self.enabled:
            self._fire_time = 0.0
            self.state.set_right_stick(0.0, 0.0)
            self.state.set_l2(0.0)
            self.state.set_r2(0.0)
            self.dashboard.tracking_status = "SEARCHING"
        else:
            self.screen_engine.reset()
            self.world_engine.reset()

    def configure_from_panel(
        self,
        *,
        snap_mode: bool,
        prediction: bool,
        response_speed: float,
        target_bone: str,
        auto_l2: bool,
        auto_r2: bool,
        recoil_compensate: bool,
        recoil_vertical: float,
        recoil_horizontal: float,
    ) -> None:
        self.auto_l2 = auto_l2
        self.auto_r2 = auto_r2
        self.recoil_compensate = recoil_compensate
        self.recoil_vertical = recoil_vertical
        self.recoil_horizontal = recoil_horizontal

        self.screen_engine.config.snap_mode = snap_mode
        self.screen_engine.config.prediction_enabled = prediction
        self.screen_engine.config.response_speed = response_speed
        self.screen_engine.config.target_bone = target_bone

        self.world_engine.config.snap_mode = snap_mode
        self.world_engine.config.prediction_enabled = prediction
        self.world_engine.config.response_speed = response_speed
        self.world_engine.config.target_bone = target_bone

    def sync_screen_size(self, width: int, height: int) -> None:
        self.screen_engine.config.screen_width = float(width)
        self.screen_engine.config.screen_height = float(height)
        if hasattr(self.target_source, "set_screen_size"):
            self.target_source.set_screen_size(width, height)  # type: ignore[attr-defined]
        cam = self.target_source.get_camera_state()
        cam.screen_width = width
        cam.screen_height = height

    def tick(self, dt: float, *, hardware_connected: bool, hardware_armed: bool) -> None:
        self.dashboard.hardware_connected = hardware_connected
        self.dashboard.hardware_armed = hardware_armed
        self.dashboard.aim_core_active = self.enabled
        self.dashboard.target_source_name = self.target_source.describe()

        if not self.enabled:
            self.dashboard.debug_lines = ["Aim core: OFF"]
            return

        self.target_source.tick(dt)

        if self.mode == "world":
            self._tick_world(dt)
        else:
            self._tick_screen(dt)

        self._update_dashboard(hardware_connected, hardware_armed)

    def _tick_screen(self, dt: float) -> None:
        targets = self.target_source.get_screen_targets()
        result = self.screen_engine.update(targets, dt)
        self.last_result = result

        locked = result.selected_target_id is not None
        if locked:
            self._fire_time += dt
        else:
            self._fire_time = 0.0

        rx, ry = result.stick_x, result.stick_y
        if locked and self.recoil_compensate and self.auto_r2:
            import math

            ramp = min(1.0, self._fire_time / 0.45)
            ry += self.recoil_vertical * ramp
            rx += self.recoil_horizontal * ramp * math.sin(self._fire_time * 9.0)
            rx = max(-1.0, min(1.0, rx))
            ry = max(-1.0, min(1.0, ry))

        self.state.set_right_stick(rx, ry, notify=True)
        if locked:
            if self.auto_l2:
                self.state.set_l2(1.0, notify=True)
            if self.auto_r2:
                self.state.set_r2(1.0, notify=True)
        else:
            self.state.set_l2(0.0, notify=True)
            self.state.set_r2(0.0, notify=True)

        if locked:
            self.dashboard.trail.append((result.target_head_x, result.target_head_y))

    def _tick_world(self, dt: float) -> None:
        cam = self.target_source.get_camera_state()
        cam.yaw = self._world_yaw
        cam.pitch = self._world_pitch
        targets = self.target_source.get_world_targets()
        result = self.world_engine.update(cam, targets, dt)

        if result.tracking:
            self._world_yaw = result.new_yaw
            self._world_pitch = result.new_pitch
            t = result.tracking
            rx, ry = self.stick_model.from_angle_errors(
                t.desired_yaw - t.current_yaw,
                t.desired_pitch - t.current_pitch,
            )
            locked = True
            self._fire_time += dt
        else:
            rx, ry = 0.0, 0.0
            locked = False
            self._fire_time = 0.0

        if locked and self.recoil_compensate and self.auto_r2:
            import math

            ramp = min(1.0, self._fire_time / 0.45)
            ry += self.recoil_vertical * ramp
            rx += self.recoil_horizontal * ramp * math.sin(self._fire_time * 9.0)

        self.state.set_right_stick(max(-1, min(1, rx)), max(-1, min(1, ry)), notify=True)
        if locked:
            if self.auto_l2:
                self.state.set_l2(1.0, notify=True)
            if self.auto_r2:
                self.state.set_r2(1.0, notify=True)
        else:
            self.state.set_l2(0.0, notify=True)
            self.state.set_r2(0.0, notify=True)

        # Build screen result for HUD from projected targets
        screen_targets = self.target_source.get_screen_targets()
        if screen_targets and result.selected_target_id:
            st = next(
                (s for s in screen_targets if s.id == result.selected_target_id),
                screen_targets[0],
            )
            cx = self.screen_engine.centre_x
            cy = self.screen_engine.centre_y
            self.last_result = ScreenAimResult(
                selected_target_id=result.selected_target_id,
                target_head_x=st.head_x,
                target_head_y=st.head_y,
                centre_x=cx,
                centre_y=cy,
                pixel_error_x=st.head_x - cx,
                pixel_error_y=st.head_y - cy,
                total_pixel_error=0.0,
                yaw_error_deg=result.yaw_error_deg,
                pitch_error_deg=result.pitch_error_deg,
                stick_x=rx,
                stick_y=ry,
                status="LOCKED" if locked else "SEARCHING",
                debug_lines=result.debug_lines,
            )
        else:
            self.last_result = None

    def _update_dashboard(self, connected: bool, armed: bool) -> None:
        d = self.dashboard
        cfg = self.screen_engine.config
        d.snap_mode = cfg.snap_mode
        d.prediction = cfg.prediction_enabled
        d.response_speed = cfg.response_speed
        d.target_bone = cfg.target_bone
        d.smoothing = "snap" if cfg.snap_mode else "exp"

        r = self.last_result
        if r:
            d.selected_target_id = r.selected_target_id
            d.tracking_status = r.status
            d.centre_x = r.centre_x
            d.centre_y = r.centre_y
            d.target_x = r.target_head_x
            d.target_y = r.target_head_y
            d.pixel_error_x = r.pixel_error_x
            d.pixel_error_y = r.pixel_error_y
            d.total_pixel_error = r.total_pixel_error
            d.yaw_error_deg = r.yaw_error_deg
            d.pitch_error_deg = r.pitch_error_deg
            d.stick_x = r.stick_x
            d.stick_y = r.stick_y
            d.debug_lines = r.debug_lines
        else:
            d.selected_target_id = None
            d.tracking_status = "SEARCHING"
            d.stick_x = 0.0
            d.stick_y = 0.0
            d.debug_lines = ["No target"]

        d.hardware_connected = connected
        d.hardware_armed = armed

    def format_dashboard(self) -> str:
        d = self.dashboard
        armed = (
            "CONNECTED & ARMED"
            if d.hardware_connected and d.hardware_armed
            else "DISCONNECTED / NOT ARMED"
        )
        return (
            f"Aim Core: {'ACTIVE' if d.aim_core_active else 'OFF'}\n"
            f"Target Source: {d.target_source_name}\n"
            f"Selected Target: {d.selected_target_id or '—'}\n"
            f"Tracking Status: {d.tracking_status}\n"
            f"Target Bone: {d.target_bone}\n"
            f"Snap Mode: {'ON' if d.snap_mode else 'OFF'}\n"
            f"Prediction: {'ON' if d.prediction else 'OFF'}\n"
            f"Smoothing: {d.smoothing} ({d.response_speed:.0f})\n"
            f"\n"
            f"Screen Centre: {d.centre_x:.0f}, {d.centre_y:.0f}\n"
            f"Target X/Y: {d.target_x:.0f}, {d.target_y:.0f}\n"
            f"Pixel Error X/Y: {d.pixel_error_x:+.0f}, {d.pixel_error_y:+.0f}\n"
            f"Total Pixel Error: {d.total_pixel_error:.0f}\n"
            f"\n"
            f"Yaw Error: {d.yaw_error_deg:+.2f}°\n"
            f"Pitch Error: {d.pitch_error_deg:+.2f}°\n"
            f"\n"
            f"Hardware Stick X: {d.stick_x:+.2f}\n"
            f"Hardware Stick Y: {d.stick_y:+.2f}\n"
            f"\n"
            f"VGAMEPAD HARDWARE BUS: {armed}"
        )
