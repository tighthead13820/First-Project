"""3D mock scene target source (wraps aimbridge mock scene)."""

from __future__ import annotations

from dataclasses import dataclass, field

from aim_core import math3d as m
from aim_core.types import CameraState, ScreenTarget, Vec3, WorldTarget

from .base import TargetSource


@dataclass
class WorldMockTargetSource(TargetSource):
    name: str = "mock-world-scene"
    screen_width: int = 1920
    screen_height: int = 1080
    time: float = 0.0
    camera_yaw: float = 0.0
    camera_pitch: float = 0.0
    camera_pos: Vec3 = field(default_factory=lambda: Vec3(0.0, 1.7, 12.0))
    _world: list[WorldTarget] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        self._world = [
            WorldTarget(
                id="dummy-a",
                position=Vec3(0.0, 0.0, -6.0),
                velocity=Vec3(0.0, 0.0, 0.0),
            ),
            WorldTarget(
                id="dummy-b",
                position=Vec3(3.5, 0.0, -10.0),
                velocity=Vec3(0.0, 0.0, 0.0),
            ),
        ]

    def tick(self, dt: float) -> None:
        import math

        self.time += dt
        self.camera_yaw = math.sin(self.time * 0.35) * 0.14

        self._world[0].position = Vec3(
            math.sin(self.time * 0.7) * 4.0,
            0.0,
            -6.0 + math.cos(self.time * 0.4) * 1.5,
        )
        self._world[0].velocity = Vec3(
            math.cos(self.time * 0.7) * 4.0 * 0.7,
            0.0,
            -math.sin(self.time * 0.4) * 1.5 * 0.4,
        )
        self._world[1].position = Vec3(
            3.5,
            0.0,
            -10.0 + math.sin(self.time * 0.55) * 2.0,
        )
        self._world[1].velocity = Vec3(
            0.0, 0.0, math.cos(self.time * 0.55) * 2.0 * 0.55
        )

    def get_world_targets(self) -> list[WorldTarget]:
        return [t for t in self._world if t.alive and t.visible]

    def get_screen_targets(self) -> list[ScreenTarget]:
        cam = self.get_camera_state()
        out: list[ScreenTarget] = []
        for t in self.get_world_targets():
            head = m.bone_world_position(t, "head")
            chest = m.bone_world_position(t, "chest")
            hx, hy, _, _, _ = m.project_world_to_screen(
                head,
                cam.position,
                cam.yaw,
                cam.pitch,
                cam.vfov_deg,
                float(cam.screen_width),
                float(cam.screen_height),
            )
            cx, cy, _, _, _ = m.project_world_to_screen(
                chest,
                cam.position,
                cam.yaw,
                cam.pitch,
                cam.vfov_deg,
                float(cam.screen_width),
                float(cam.screen_height),
            )
            if hx < -9000:
                continue
            out.append(
                ScreenTarget(
                    id=t.id,
                    screen_x=hx,
                    screen_y=hy,
                    head_x=hx,
                    head_y=hy,
                    chest_x=cx,
                    chest_y=cy,
                    velocity_x=0.0,
                    velocity_y=0.0,
                    alive=t.alive,
                    visible=t.visible,
                    team=t.team,
                )
            )
        return out

    def get_camera_state(self) -> CameraState:
        return CameraState(
            position=self.camera_pos.copy(),
            yaw=self.camera_yaw,
            pitch=self.camera_pitch,
            vfov_deg=75.0,
            screen_width=self.screen_width,
            screen_height=self.screen_height,
        )
