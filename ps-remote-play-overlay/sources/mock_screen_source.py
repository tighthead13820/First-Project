"""
Mock screen-space targets for validating the live pipeline.

Simulates enemies moving across a 1920×1080 viewport — use this to
verify selection, stick output, HUD, and ViGEm wiring without game capture.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from aim_core.types import CameraState, ScreenTarget, Vec3, WorldTarget

from .base import TargetSource


@dataclass
class MockScreenTargetSource(TargetSource):
    name: str = "mock-screen-stream"
    screen_width: int = 1920
    screen_height: int = 1080
    time: float = 0.0

    _targets: list[ScreenTarget] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        self._rebuild()

    def _rebuild(self) -> None:
        cx, cy = self.screen_width / 2, self.screen_height / 2
        self._targets = [
            ScreenTarget(
                id="enemy-a",
                screen_x=cx + 200,
                screen_y=cy - 40,
                head_x=cx + 200,
                head_y=cy - 40,
                chest_x=cx + 200,
                chest_y=cy + 10,
            ),
            ScreenTarget(
                id="enemy-b",
                screen_x=cx - 350,
                screen_y=cy + 80,
                head_x=cx - 350,
                head_y=cy + 80,
                chest_x=cx - 350,
                chest_y=cy + 130,
            ),
            ScreenTarget(
                id="enemy-c",
                screen_x=cx + 460,
                screen_y=cy + 120,
                head_x=cx + 460,
                head_y=cy + 120,
                chest_x=cx + 460,
                chest_y=cy + 170,
            ),
        ]

    def set_screen_size(self, width: int, height: int) -> None:
        self.screen_width = width
        self.screen_height = height
        self._rebuild()

    def tick(self, dt: float) -> None:
        self.time += dt
        cx, cy = self.screen_width / 2, self.screen_height / 2

        # Enemy A: orbit near centre-right
        ax = cx + 200 + math.sin(self.time * 0.9) * 120
        ay = cy - 40 + math.cos(self.time * 0.7) * 60
        self._targets[0].screen_x = ax
        self._targets[0].screen_y = ay
        self._targets[0].head_x = ax
        self._targets[0].head_y = ay
        self._targets[0].chest_x = ax
        self._targets[0].chest_y = ay + 50
        self._targets[0].velocity_x = math.cos(self.time * 0.9) * 120 * 0.9
        self._targets[0].velocity_y = -math.sin(self.time * 0.7) * 60 * 0.7

        # Enemy B: drift left
        bx = cx - 350 + math.sin(self.time * 0.5) * 80
        by = cy + 80
        self._targets[1].screen_x = bx
        self._targets[1].screen_y = by
        self._targets[1].head_x = bx
        self._targets[1].head_y = by
        self._targets[1].chest_x = bx
        self._targets[1].chest_y = by + 50
        self._targets[1].velocity_x = math.cos(self.time * 0.5) * 80 * 0.5
        self._targets[1].velocity_y = 0.0

        # Enemy C: vertical bounce right
        cx3 = cx + 460
        cy3 = cy + 120 + math.sin(self.time * 1.1) * 90
        self._targets[2].screen_x = cx3
        self._targets[2].screen_y = cy3
        self._targets[2].head_x = cx3
        self._targets[2].head_y = cy3
        self._targets[2].chest_x = cx3
        self._targets[2].chest_y = cy3 + 50
        self._targets[2].velocity_x = 0.0
        self._targets[2].velocity_y = math.cos(self.time * 1.1) * 90 * 1.1

    def get_screen_targets(self) -> list[ScreenTarget]:
        return [t for t in self._targets if t.alive and t.visible]

    def get_world_targets(self) -> list[WorldTarget]:
        return []

    def get_camera_state(self) -> CameraState:
        return CameraState(
            position=Vec3(0.0, 1.7, 0.0),
            yaw=0.0,
            pitch=0.0,
            vfov_deg=75.0,
            screen_width=self.screen_width,
            screen_height=self.screen_height,
        )
