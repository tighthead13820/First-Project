"""Tests for controller_hardware.py (Virtual DualShock 4)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from controller_hardware import RealControllerHardware  # noqa: E402


class FakeDS4:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def right_joystick_float(self, x_value_float=0.0, y_value_float=0.0):
        self.calls.append(("stick", x_value_float, y_value_float))

    def left_trigger_float(self, value_float=0.0):
        self.calls.append(("l2", value_float))

    def right_trigger_float(self, value_float=0.0):
        self.calls.append(("r2", value_float))

    def update(self):
        self.calls.append(("update",))

    def reset(self):
        self.calls.append(("reset",))


class ControllerHardwareTests(unittest.TestCase):
    @patch("controller_hardware.HAS_VGAMEPAD", True)
    @patch("controller_hardware.vg")
    def test_uses_vds4_gamepad(self, mock_vg) -> None:
        mock_vg.VDS4Gamepad.return_value = FakeDS4()
        hw = RealControllerHardware()
        self.assertTrue(hw.enabled)
        mock_vg.VDS4Gamepad.assert_called_once()

    @patch("controller_hardware.HAS_VGAMEPAD", True)
    @patch("controller_hardware.vg")
    def test_send_stick_inverts_y(self, mock_vg) -> None:
        pad = FakeDS4()
        mock_vg.VDS4Gamepad.return_value = pad
        hw = RealControllerHardware()
        ok = hw.send_stick_input(0.62, -0.05)
        self.assertTrue(ok)
        self.assertIn(("stick", 0.62, 0.05), pad.calls)  # -(-0.05) = +0.05
        self.assertIn(("update",), pad.calls)

    @patch("controller_hardware.HAS_VGAMEPAD", True)
    @patch("controller_hardware.vg")
    def test_send_full_input_triggers(self, mock_vg) -> None:
        pad = FakeDS4()
        mock_vg.VDS4Gamepad.return_value = pad
        hw = RealControllerHardware()
        hw.send_full_input(0.5, 0.25, l2=0.8, r2=1.0)
        self.assertIn(("l2", 0.8), pad.calls)
        self.assertIn(("r2", 1.0), pad.calls)


if __name__ == "__main__":
    unittest.main()
