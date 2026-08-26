"""
Tests for aim-script loading and the sandbox aim port.

Run from project root:
    python -m unittest tests.test_state tests.test_scripts -v
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aimbridge.host import ScriptHost  # noqa: E402
from aimbridge.math3d import angles_to_stick, forward_from_angles  # noqa: E402
from controls.state import ControllerState  # noqa: E402
from scripts.api import AimFrame, CameraSample, TargetSample, Vec3  # noqa: E402
from scripts.loader import (  # noqa: E402
    ScriptLoadError,
    load_builtin_sandbox,
    upload_script,
)


class MathPortTests(unittest.TestCase):
    def test_forward_looks_down_negative_z(self) -> None:
        f = forward_from_angles(0.0, 0.0)
        self.assertAlmostEqual(f.x, 0.0, places=5)
        self.assertAlmostEqual(f.y, 0.0, places=5)
        self.assertAlmostEqual(f.z, -1.0, places=5)

    def test_stick_maps_yaw_error(self) -> None:
        rx, ry = angles_to_stick(0.0, 0.0, 0.5, 0.0)
        self.assertGreater(rx, 0.0)
        self.assertEqual(ry, 0.0)


class BuiltinScriptTests(unittest.TestCase):
    def test_locks_target_ahead(self) -> None:
        script = load_builtin_sandbox()
        frame = AimFrame(
            camera=CameraSample(position=Vec3(0.0, 1.7, 12.0), yaw=0.0, pitch=0.0),
            targets=[
                TargetSample(id="front", position=Vec3(0.0, 0.0, -6.0)),
            ],
            dt=1 / 30,
        )
        cmd = script.update(frame)
        self.assertEqual(script.selected_id, "front")
        self.assertIn("Target: front", cmd.debug)
        self.assertEqual(cmd.l2, 1.0)
        self.assertEqual(cmd.r2, 1.0)
        self.assertNotEqual((cmd.rx, cmd.ry), (0.0, 0.0))

    def test_no_target_centres_stick(self) -> None:
        script = load_builtin_sandbox()
        frame = AimFrame(
            camera=CameraSample(position=Vec3(0.0, 1.7, 12.0)),
            targets=[],
            dt=1 / 30,
        )
        cmd = script.update(frame)
        self.assertEqual((cmd.rx, cmd.ry), (0.0, 0.0))
        self.assertEqual(cmd.l2, 0.0)
        self.assertEqual(cmd.r2, 0.0)

    def test_can_disable_auto_fire_and_recoil(self) -> None:
        script = load_builtin_sandbox()
        script.settings.auto_fire_l2 = False
        script.settings.auto_fire_r2 = False
        script.settings.recoil_compensate = False
        frame = AimFrame(
            camera=CameraSample(position=Vec3(0.0, 1.7, 12.0), yaw=0.0, pitch=0.0),
            targets=[TargetSample(id="front", position=Vec3(0.0, 0.0, -6.0))],
            dt=1 / 30,
        )
        cmd = script.update(frame)
        self.assertIsNone(cmd.l2)
        self.assertIsNone(cmd.r2)
        self.assertIn("L2=manual", cmd.debug)
        self.assertIn("R2=manual", cmd.debug)


class LoaderTests(unittest.TestCase):
    def test_upload_example_circle(self) -> None:
        src = ROOT / "scripts" / "example_circle.py"
        with tempfile.TemporaryDirectory() as tmp:
            dest, script = upload_script(src, dest_dir=Path(tmp))
            self.assertTrue(dest.is_file())
            self.assertEqual(script.name, "example-circle")
            cmd = script.update(
                AimFrame(
                    camera=CameraSample(position=Vec3()),
                    targets=[],
                    dt=0.1,
                )
            )
            self.assertNotEqual((cmd.rx, cmd.ry), (0.0, 0.0))

    def test_reject_non_python(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "aimAssist.js"
            bad.write_text("// nope", encoding="utf-8")
            with self.assertRaises(ScriptLoadError):
                upload_script(bad, dest_dir=Path(tmp))


class HostTests(unittest.TestCase):
    def test_enable_drives_state(self) -> None:
        state = ControllerState()
        host = ScriptHost(state)
        host.load_builtin()
        host.set_enabled(True)
        host.tick(1 / 30)
        # After a tick with targets in the mock scene, debug should update.
        self.assertTrue(host.last_debug)
        host.set_enabled(False)
        self.assertEqual((state.rx, state.ry), (0.0, 0.0))


if __name__ == "__main__":
    unittest.main()
