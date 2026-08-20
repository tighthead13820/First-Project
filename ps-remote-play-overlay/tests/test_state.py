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


if __name__ == "__main__":
    unittest.main()
