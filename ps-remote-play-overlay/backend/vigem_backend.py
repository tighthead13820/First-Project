"""
ViGEm virtual-controller backend (Windows).

Uses the ``vgamepad`` package, which talks to the ViGEmBus kernel driver
and exposes a virtual DualShock 4 (default) or Xbox 360 pad.

Install (Windows):
  1. ViGEmBus: https://github.com/nefarius/ViGEmBus/releases
  2. pip install vgamepad

Run:
  python main.py --backend vigem
  # or DualShock 4 explicitly:
  python main.py --backend vigem-ds4
  # Xbox 360 pad:
  python main.py --backend vigem-x360

Simulation mode on ControllerState still gates output: when the checkbox
is off, the pad is centred and no fresh report is forced beyond a rest
frame. When on, RX/RY/L2/R2 are pushed every tick.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any, Optional

from .base import BackendError, VirtualControllerBackend

if TYPE_CHECKING:
    from controls.state import ControllerState


def _import_vgamepad():
    try:
        import vgamepad as vg  # type: ignore
    except ImportError as exc:
        raise BackendError(
            "vgamepad is not installed. On Windows run: pip install vgamepad\n"
            "Also install ViGEmBus from "
            "https://github.com/nefarius/ViGEmBus/releases"
        ) from exc
    return vg


class ViGEmBackend(VirtualControllerBackend):
    """Push normalized axes to a ViGEm virtual gamepad."""

    name = "vigem"

    def __init__(self, pad_type: str = "ds4") -> None:
        """
        pad_type:
          - "ds4" / "dualshock" — virtual DualShock 4 (best for PS Remote Play)
          - "x360" / "xbox" — virtual Xbox 360 controller
        """
        self.pad_type = (pad_type or "ds4").strip().lower()
        self._vg: Any = None
        self._pad: Any = None
        self._connected = False
        self._last_sim = False

        if self.pad_type in {"ds4", "dualshock", "dualshock4", "vds4"}:
            self.name = "vigem-ds4"
            self._kind = "ds4"
        elif self.pad_type in {"x360", "xbox", "vx360"}:
            self.name = "vigem-x360"
            self._kind = "x360"
        else:
            raise BackendError(
                f"Unknown ViGEm pad type '{pad_type}'. Use ds4 or x360."
            )

    def connect(self) -> None:
        if sys.platform != "win32":
            raise BackendError(
                "ViGEm backend only runs on Windows (ViGEmBus required)."
            )
        self._vg = _import_vgamepad()
        try:
            if self._kind == "ds4":
                self._pad = self._vg.VDS4Gamepad()
            else:
                self._pad = self._vg.VX360Gamepad()
        except Exception as exc:  # noqa: BLE001 — driver missing etc.
            raise BackendError(
                "Failed to create virtual gamepad. Is ViGEmBus installed?\n"
                f"Details: {exc}"
            ) from exc
        self._connected = True
        self._rest()
        print(f"[vigem] connected ({self.name})")

    def disconnect(self) -> None:
        if self._pad is not None:
            try:
                self._rest()
                # Prefer reset if available; ignore failures on teardown.
                if hasattr(self._pad, "reset"):
                    self._pad.reset()
                    self._pad.update()
            except Exception:  # noqa: BLE001
                pass
        self._pad = None
        self._vg = None
        self._connected = False
        print(f"[vigem] disconnected ({self.name})")

    def push(self, state: "ControllerState") -> None:
        if not self._connected or self._pad is None:
            return

        # Gate on simulation mode (= "send real controller output").
        if not state.simulation_mode:
            if self._last_sim:
                self._rest()
            self._last_sim = False
            return

        self._last_sim = True
        self._apply_axes(state.rx, state.ry, state.l2, state.r2)

    def _apply_axes(self, rx: float, ry: float, l2: float, r2: float) -> None:
        assert self._pad is not None
        # vgamepad stick Y: +1 is up. Our overlay uses +RY = down (gamepad
        # common). Flip Y when sending so look-down still moves the camera down.
        stick_y = -float(ry)
        self._pad.right_joystick_float(
            x_value_float=float(rx), y_value_float=stick_y
        )
        self._pad.left_trigger_float(value_float=float(l2))
        self._pad.right_trigger_float(value_float=float(r2))
        self._pad.update()

    def _rest(self) -> None:
        if self._pad is None:
            return
        self._apply_axes(0.0, 0.0, 0.0, 0.0)
