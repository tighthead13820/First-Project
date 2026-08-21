"""
Built-in mock target scene for exercising uploaded aim scripts.

This does **not** read game memory. It synthesizes a few moving dummies so
the overlay can demonstrate script → stick output end-to-end.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from scripts.api import AimFrame, CameraSample, TargetSample, Vec3


@dataclass
class MockScene:
    """Tiny deterministic arena used when a script is enabled."""

    camera: CameraSample = field(
        default_factory=lambda: CameraSample(
            position=Vec3(0.0, 1.7, 12.0), yaw=0.0, pitch=0.0
        )
    )
    time: float = 0.0
    # Slowly auto-pan so targets enter/leave the FOV cone during tests.
    auto_pan: bool = True

    def tick(self, dt: float) -> AimFrame:
        self.time += dt
        if self.auto_pan:
            # Gentle yaw sweep ± ~8 degrees.
            self.camera.yaw = math.sin(self.time * 0.35) * 0.14

        targets = [
            TargetSample(
                id="dummy-a",
                position=Vec3(
                    math.sin(self.time * 0.7) * 4.0,
                    0.0,
                    -6.0 + math.cos(self.time * 0.4) * 1.5,
                ),
                velocity=Vec3(
                    math.cos(self.time * 0.7) * 4.0 * 0.7,
                    0.0,
                    -math.sin(self.time * 0.4) * 1.5 * 0.4,
                ),
            ),
            TargetSample(
                id="dummy-b",
                position=Vec3(
                    3.5,
                    0.0,
                    -10.0 + math.sin(self.time * 0.55) * 2.0,
                ),
                velocity=Vec3(
                    0.0,
                    0.0,
                    math.cos(self.time * 0.55) * 2.0 * 0.55,
                ),
                head_height=1.85,
                chest_height=1.25,
            ),
            TargetSample(
                id="dummy-c",
                position=Vec3(-5.0, 0.0, -8.0),
                velocity=Vec3(0.0, 0.0, 0.0),
            ),
        ]
        return AimFrame(camera=self.camera, targets=targets, dt=dt)
