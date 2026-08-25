"""Shared types for the aim-assist core (renderer-independent)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Vec3:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def copy(self) -> "Vec3":
        return Vec3(self.x, self.y, self.z)


@dataclass
class CameraState:
    """First-person camera in world space (Three.js YXZ convention)."""

    position: Vec3
    yaw: float = 0.0
    pitch: float = 0.0
    vfov_deg: float = 75.0
    screen_width: int = 1920
    screen_height: int = 1080


@dataclass
class WorldTarget:
    """3D sandbox-style target (feet position + velocity)."""

    id: str
    position: Vec3
    velocity: Vec3 = field(default_factory=Vec3)
    head_height: float = 1.7
    chest_height: float = 1.2
    mesh_center_offset: float = 0.9
    alive: bool = True
    visible: bool = True
    team: int = 1


@dataclass
class ScreenTarget:
    """
    Normalized 2D target for overlay / stream adapters.

    Screen origin: top-left. Head/chest are pixel coordinates.
    """

    id: str
    screen_x: float
    screen_y: float
    head_x: float
    head_y: float
    chest_x: float
    chest_y: float
    velocity_x: float = 0.0
    velocity_y: float = 0.0
    alive: bool = True
    visible: bool = True
    team: int = 1

    @property
    def head(self) -> tuple[float, float]:
        return (self.head_x, self.head_y)

    @property
    def chest(self) -> tuple[float, float]:
        return (self.chest_x, self.chest_y)


@dataclass
class TargetEvaluation:
    target_id: str
    aim_point: Vec3
    distance: float
    angle_rad: float
    angle_deg: float
    in_range: bool
    in_front: bool
    on_screen: bool
    inside_fov: bool
    passes: bool


@dataclass
class TrackingState:
    target_id: str
    aim_point: Vec3
    current_yaw: float
    current_pitch: float
    desired_yaw: float
    desired_pitch: float
    new_yaw: float
    new_pitch: float
    yaw_error_deg: float
    pitch_error_deg: float
    pre_error_deg: float
    post_error_deg: float
    snap: bool
    locked: bool
    tracking: bool


@dataclass
class AimResult:
    """One aim-core tick output."""

    selected_target_id: Optional[str]
    tracking: Optional[TrackingState]
    new_yaw: float
    new_pitch: float
    yaw_error_deg: float
    pitch_error_deg: float
    evaluations: list[TargetEvaluation]
    debug_lines: list[str]
    enabled: bool


@dataclass
class ScreenAimResult:
    """Screen-space aim tick (pixel errors → stick)."""

    selected_target_id: Optional[str]
    target_head_x: float
    target_head_y: float
    centre_x: float
    centre_y: float
    pixel_error_x: float
    pixel_error_y: float
    total_pixel_error: float
    yaw_error_deg: float
    pitch_error_deg: float
    stick_x: float
    stick_y: float
    status: str  # LOCKED / SEARCHING
    debug_lines: list[str]
