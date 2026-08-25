"""
Verification tests for aim_core — run before live ViGEm loop.

    python -m unittest tests.test_aim_core -v
"""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aim_core import math3d as m  # noqa: E402
from aim_core.config import AimConfig  # noqa: E402
from aim_core.engine import AimAssistEngine  # noqa: E402
from aim_core.screen_engine import ScreenAimEngine  # noqa: E402
from aim_core.stick_model import StickControllerModel  # noqa: E402
from aim_core.types import CameraState, ScreenTarget, Vec3, WorldTarget  # noqa: E402


def _cam() -> CameraState:
    return CameraState(
        position=Vec3(0.0, 1.7, 12.0),
        yaw=0.0,
        pitch=0.0,
        vfov_deg=75.0,
        screen_width=1920,
        screen_height=1080,
    )


class FixedSignTests(unittest.TestCase):
    def test_forward_matches_threejs_yxz(self) -> None:
        f = m.forward_from_angles(0.0, 0.0)
        self.assertAlmostEqual(f.x, 0.0, places=5)
        self.assertAlmostEqual(f.y, 0.0, places=5)
        self.assertAlmostEqual(f.z, -1.0, places=5)

    def test_fixed_differs_from_legacy(self) -> None:
        d = Vec3(1.0, 0.0, -1.0)
        d = m.normalize(d)
        y_fixed, p_fixed = m.angles_from_direction(d)
        y_legacy, p_legacy = m.angles_from_direction_legacy(d)
        self.assertNotAlmostEqual(y_fixed, y_legacy, places=3)


class ExpSmoothingTests(unittest.TestCase):
    def test_converges_toward_target(self) -> None:
        cur = 0.0
        target = 0.5
        for _ in range(120):
            cur = m.exp_smooth_angle(cur, target, response_speed=35.0, dt=1 / 60)
        self.assertAlmostEqual(cur, target, places=2)


class WorldEngineTests(unittest.TestCase):
    def test_selects_closest_angle(self) -> None:
        engine = AimAssistEngine(
            AimConfig(
                screen_wide_select=False,
                fov_deg=30.0,
                snap_mode=True,
                target_bone="head",
            )
        )
        cam = _cam()
        targets = [
            WorldTarget(id="far-side", position=Vec3(8.0, 0.0, -6.0)),
            WorldTarget(id="center", position=Vec3(0.0, 0.0, -6.0)),
        ]
        result = engine.update(cam, targets, dt=1 / 60)
        self.assertEqual(result.selected_target_id, "center")

    def test_no_target_zero_change_when_disabled_tracking(self) -> None:
        engine = AimAssistEngine(AimConfig())
        cam = _cam()
        result = engine.update(cam, [], dt=1 / 60)
        self.assertIsNone(result.selected_target_id)


class ScreenEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = ScreenAimEngine()
        self.engine.config.screen_width = 1920
        self.engine.config.screen_height = 1080
        self.engine.config.snap_mode = True

    def test_target_at_centre_zero_stick(self) -> None:
        cx, cy = 960, 540
        targets = [
            ScreenTarget(
                id="c",
                screen_x=cx,
                screen_y=cy,
                head_x=cx,
                head_y=cy,
                chest_x=cx,
                chest_y=cy + 50,
            )
        ]
        r = self.engine.update(targets, dt=1 / 60)
        self.assertAlmostEqual(r.stick_x, 0.0, places=2)
        self.assertAlmostEqual(r.stick_y, 0.0, places=2)

    def test_target_right_positive_stick_x(self) -> None:
        targets = [
            ScreenTarget(
                id="r",
                screen_x=1200,
                screen_y=540,
                head_x=1200,
                head_y=540,
                chest_x=1200,
                chest_y=590,
            )
        ]
        r = self.engine.update(targets, dt=1 / 60)
        self.assertGreater(r.stick_x, 0.0)

    def test_target_left_negative_stick_x(self) -> None:
        targets = [
            ScreenTarget(
                id="l",
                screen_x=720,
                screen_y=540,
                head_x=720,
                head_y=540,
                chest_x=720,
                chest_y=590,
            )
        ]
        r = self.engine.update(targets, dt=1 / 60)
        self.assertLess(r.stick_x, 0.0)

    def test_target_above_negative_pitch_stick_y(self) -> None:
        targets = [
            ScreenTarget(
                id="u",
                screen_x=960,
                screen_y=400,
                head_x=960,
                head_y=400,
                chest_x=960,
                chest_y=450,
            )
        ]
        r = self.engine.update(targets, dt=1 / 60)
        self.assertLess(r.stick_y, 0.0)

    def test_target_below_positive_stick_y(self) -> None:
        targets = [
            ScreenTarget(
                id="d",
                screen_x=960,
                screen_y=680,
                head_x=960,
                head_y=680,
                chest_x=960,
                chest_y=730,
            )
        ]
        r = self.engine.update(targets, dt=1 / 60)
        self.assertGreater(r.stick_y, 0.0)

    def test_closest_to_centre_wins(self) -> None:
        targets = [
            ScreenTarget(
                id="far",
                screen_x=1500,
                screen_y=540,
                head_x=1500,
                head_y=540,
                chest_x=1500,
                chest_y=590,
            ),
            ScreenTarget(
                id="near",
                screen_x=980,
                screen_y=550,
                head_x=980,
                head_y=550,
                chest_x=980,
                chest_y=600,
            ),
        ]
        r = self.engine.update(targets, dt=1 / 60)
        self.assertEqual(r.selected_target_id, "near")

    def test_disappearing_target_searches(self) -> None:
        r = self.engine.update([], dt=1 / 60)
        self.assertEqual(r.status, "SEARCHING — no targets")
        self.assertEqual(r.stick_x, 0.0)

    def test_moving_target_still_locks(self) -> None:
        t = ScreenTarget(
            id="move",
            screen_x=1000,
            screen_y=540,
            head_x=1000,
            head_y=540,
            chest_x=1000,
            chest_y=590,
            velocity_x=200.0,
            velocity_y=0.0,
        )
        r1 = self.engine.update([t], dt=1 / 60)
        t.head_x += 50
        t.screen_x += 50
        r2 = self.engine.update([t], dt=1 / 60)
        self.assertEqual(r1.selected_target_id, "move")
        self.assertEqual(r2.selected_target_id, "move")

    def test_prediction_changes_aim_point(self) -> None:
        self.engine.config.prediction_enabled = True
        self.engine.config.prediction_lead_seconds = 0.1
        t = ScreenTarget(
            id="p",
            screen_x=1100,
            screen_y=540,
            head_x=1100,
            head_y=540,
            chest_x=1100,
            chest_y=590,
            velocity_x=500.0,
            velocity_y=0.0,
        )
        r_off = ScreenAimEngine()
        r_off.config.snap_mode = True
        r_off.config.prediction_enabled = False
        a = self.engine.update([t], dt=1 / 60)
        b = r_off.update([t], dt=1 / 60)
        self.assertNotAlmostEqual(a.target_head_x, b.target_head_x, places=0)


class StickModelTests(unittest.TestCase):
    def test_clamps_to_one(self) -> None:
        model = StickControllerModel()
        x, y = model.compute(
            pixel_error_x=5000,
            pixel_error_y=-5000,
            yaw_error_deg=90.0,
            pitch_error_deg=-90.0,
            dt=1 / 60,
        )
        self.assertLessEqual(abs(x), 1.0)
        self.assertLessEqual(abs(y), 1.0)

    def test_zero_error_zero_stick(self) -> None:
        model = StickControllerModel()
        x, y = model.compute(
            pixel_error_x=0.0,
            pixel_error_y=0.0,
            yaw_error_deg=0.0,
            pitch_error_deg=0.0,
            dt=1 / 60,
        )
        self.assertEqual(x, 0.0)
        self.assertEqual(y, 0.0)

    def test_large_positive_yaw_positive_x(self) -> None:
        model = StickControllerModel()
        x, _ = model.from_angle_errors(0.5, 0.0, gains_yaw=1.6)
        self.assertGreater(x, 0.0)

    def test_large_negative_yaw_negative_x(self) -> None:
        model = StickControllerModel()
        x, _ = model.from_angle_errors(-0.5, 0.0, gains_yaw=1.6)
        self.assertLess(x, 0.0)


class SmoothModeTests(unittest.TestCase):
    def test_smooth_mode_converges(self) -> None:
        engine = ScreenAimEngine()
        engine.config.snap_mode = False
        engine.config.response_speed = 40.0
        targets = [
            ScreenTarget(
                id="t",
                screen_x=1200,
                screen_y=540,
                head_x=1200,
                head_y=540,
                chest_x=1200,
                chest_y=590,
            )
        ]
        sticks = []
        for _ in range(90):
            r = engine.update(targets, dt=1 / 60)
            sticks.append(r.stick_x)
        self.assertGreater(sticks[-1], sticks[0])
        self.assertAlmostEqual(sticks[-1], sticks[-2], delta=0.15)


if __name__ == "__main__":
    unittest.main()
