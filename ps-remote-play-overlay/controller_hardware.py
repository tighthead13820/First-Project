"""
Production Virtual DualShock 4 hardware driver for PS Remote Play / PS5 Remote Play.

Uses ViGEmBus + vgamepad (VDS4Gamepad). Stick Y is inverted on output so overlay
+RY (look down) maps to the correct camera direction in Remote Play.
"""

from __future__ import annotations

HAS_VGAMEPAD = False
try:
    import vgamepad as vg

    HAS_VGAMEPAD = True
except ImportError:
    vg = None  # type: ignore


def _clamp(value: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(value)))


class RealControllerHardware:
    """Virtual DualShock 4 — accepted by the official PS Remote Play app."""

    def __init__(self) -> None:
        self.gamepad = None
        self.enabled = False
        if HAS_VGAMEPAD and vg is not None:
            try:
                # VDS4Gamepad for native PS / PS5 Remote Play compatibility
                self.gamepad = vg.VDS4Gamepad()
                self.enabled = True
                print("[SUCCESS] Production Live Virtual DualShock 4 Driver Hooked.")
            except Exception as exc:
                print(f"[FATAL DEVICE ERROR] DualShock 4 registration failed: {exc}")
        else:
            print("[CRITICAL] 'vgamepad' missing. Run: pip install vgamepad")

    def send_stick_input(self, stick_x: float, stick_y: float) -> bool:
        """
        Push right-stick camera input.

        Uses vgamepad ``right_joystick_float`` (DS4 float stick API). Parameters
        match the requested ``right_stick_float(x_value=, y_value=)`` contract:
        overlay stick_y is negated so +RY (look down) sends the correct axis to
        Remote Play.
        """
        if not self.enabled or not self.gamepad:
            return False

        try:
            sx = _clamp(stick_x)
            sy = _clamp(stick_y)
            # vgamepad DS4 API: right_joystick_float(x_value_float, y_value_float)
            self.gamepad.right_joystick_float(
                x_value_float=sx,
                y_value_float=-sy,
            )
            self.gamepad.update()
            return True
        except Exception as exc:
            print(f"[DEVICE WRITE EXCEPTION] Failed sending stick updates: {exc}")
            return False

    def send_triggers(self, l2: float, r2: float) -> bool:
        """Push L2 / R2 analog triggers (0.0 – 1.0)."""
        if not self.enabled or not self.gamepad:
            return False
        try:
            self.gamepad.left_trigger_float(value_float=_clamp(l2, 0.0, 1.0))
            self.gamepad.right_trigger_float(value_float=_clamp(r2, 0.0, 1.0))
            self.gamepad.update()
            return True
        except Exception as exc:
            print(f"[DEVICE WRITE EXCEPTION] Failed sending trigger updates: {exc}")
            return False

    def send_full_input(
        self,
        stick_x: float,
        stick_y: float,
        l2: float = 0.0,
        r2: float = 0.0,
    ) -> bool:
        """Single update: right stick + L2/R2 (used by the live aim pipeline)."""
        if not self.enabled or not self.gamepad:
            return False
        try:
            sx = _clamp(stick_x)
            sy = _clamp(stick_y)
            self.gamepad.right_joystick_float(
                x_value_float=sx,
                y_value_float=-sy,
            )
            self.gamepad.left_trigger_float(value_float=_clamp(l2, 0.0, 1.0))
            self.gamepad.right_trigger_float(value_float=_clamp(r2, 0.0, 1.0))
            self.gamepad.update()
            return True
        except Exception as exc:
            print(f"[DEVICE WRITE EXCEPTION] Failed sending full input: {exc}")
            return False

    def rest(self) -> None:
        """Centre sticks and release triggers."""
        self.send_full_input(0.0, 0.0, 0.0, 0.0)

    def shutdown(self) -> None:
        if self.gamepad:
            try:
                self.gamepad.reset()
                self.gamepad.update()
            except Exception:
                pass
            del self.gamepad
            self.gamepad = None
            self.enabled = False
