"""
Lightweight unit tests for ControllerState (no GUI required).

Run:
    python -m unittest tests.test_state -v
"""

from __future__ import annotations

import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from controls.state import ControllerState, merge_held_overrides  # noqa: E402
from backend import create_backend  # noqa: E402
from backend.simulation_backend import SimulationBackend  # noqa: E402


class ControllerStateTests(unittest.TestCase):
    def test_clamp_stick_and_triggers(self) -> None:
        s = ControllerState()
        s.set_rx(2.5)
        s.set_ry(-3.0)
        s.set_l2(1.5)
        s.set_r2(-0.2)
        self.assertEqual(s.rx, 1.0)
        self.assertEqual(s.ry, -1.0)
        self.assertEqual(s.l2, 1.0)
        self.assertEqual(s.r2, 0.0)

    def test_reset_right_stick(self) -> None:
        s = ControllerState(rx=0.8, ry=-0.4)
        s.reset_right_stick()
        self.assertEqual((s.rx, s.ry), (0.0, 0.0))

    def test_listeners_fire(self) -> None:
        s = ControllerState()
        seen: list[float] = []
        s.subscribe(lambda st: seen.append(st.rx))
        s.set_rx(0.5)
        self.assertEqual(seen, [0.5])

    def test_merge_overrides(self) -> None:
        base = ControllerState(rx=0.1, ry=0.2, l2=0.3, r2=0.4)
        merged = merge_held_overrides(base, [{"rx": -1.0}, {"l2": 1.0}])
        self.assertEqual(merged["rx"], -1.0)
        self.assertEqual(merged["ry"], 0.2)
        self.assertEqual(merged["l2"], 1.0)
        self.assertEqual(merged["r2"], 0.4)


class BackendTests(unittest.TestCase):
    def test_factory(self) -> None:
        self.assertEqual(create_backend("simulation").name, "simulation")
        self.assertEqual(create_backend("null").name, "null")
        self.assertEqual(create_backend("vigem").name, "vigem-ds4")
        self.assertEqual(create_backend("vigem-x360").name, "vigem-x360")

    def test_simulation_only_pushes_when_enabled(self) -> None:
        backend = SimulationBackend()
        backend.connect()
        state = ControllerState(rx=0.5, simulation_mode=False)
        backend.push(state)
        self.assertIsNone(backend.last_frame)

        state.simulation_mode = True
        backend.push(state)
        self.assertIsNotNone(backend.last_frame)
        assert backend.last_frame is not None
        self.assertEqual(backend.last_frame.rx, 0.5)
        backend.disconnect()

    def test_vigem_push_with_fake_pad(self) -> None:
        from backend.vigem_backend import ViGEmBackend

        class FakePad:
            def __init__(self) -> None:
                self.calls: list[tuple] = []

            def right_joystick_float(self, x_value_float, y_value_float):
                self.calls.append(("stick", x_value_float, y_value_float))

            def left_trigger_float(self, value_float):
                self.calls.append(("l2", value_float))

            def right_trigger_float(self, value_float):
                self.calls.append(("r2", value_float))

            def update(self):
                self.calls.append(("update",))

            def reset(self):
                self.calls.append(("reset",))

        backend = ViGEmBackend(pad_type="ds4")
        backend._connected = True
        pad = FakePad()
        backend._pad = pad
        state = ControllerState(
            rx=0.5, ry=0.25, l2=0.8, r2=1.0, simulation_mode=True
        )
        backend.push(state)
        self.assertIn(("stick", 0.5, -0.25), pad.calls)  # Y flipped
        self.assertIn(("l2", 0.8), pad.calls)
        self.assertIn(("r2", 1.0), pad.calls)
        self.assertIn(("update",), pad.calls)

        # When simulation mode turns off, pad is rested once.
        state.simulation_mode = False
        pad.calls.clear()
        backend.push(state)
        stick_calls = [c for c in pad.calls if c[0] == "stick"]
        self.assertTrue(stick_calls)
        self.assertAlmostEqual(stick_calls[0][1], 0.0)
        self.assertAlmostEqual(stick_calls[0][2], 0.0)
        self.assertIn(("update",), pad.calls)


if __name__ == "__main__":
    unittest.main()
