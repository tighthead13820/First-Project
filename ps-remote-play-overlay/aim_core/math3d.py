"""
3D vector/angle utilities — port of aim-assist-sandbox/js/math.js

Source of truth: origin/cursor/fix-camera-yaw-pitch-7c02
Preserves corrected Three.js YXZ camera sign conventions.
"""

from __future__ import annotations

import math

from .types import Vec3


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def forward_from_angles(yaw: float, pitch: float) -> Vec3:
    """
    Build unit forward vector matching Three.js PerspectiveCamera YXZ.

    forward.x = -cos(pitch) * sin(yaw)
    forward.y =  sin(pitch)
    forward.z = -cos(pitch) * cos(yaw)
    """
    cos_pitch = math.cos(pitch)
    return normalize(
        Vec3(
            -cos_pitch * math.sin(yaw),
            math.sin(pitch),
            -cos_pitch * math.cos(yaw),
        )
    )


def angles_from_direction(direction: Vec3) -> tuple[float, float]:
    """
    Extract yaw/pitch from unit direction (Three.js YXZ):

    pitch = asin(dy)
    yaw   = -atan2(dx, -dz)
    """
    dx, dy, dz = direction.x, direction.y, direction.z
    pitch = math.asin(clamp(dy, -1.0, 1.0))
    yaw = -math.atan2(dx, -dz)
    return yaw, pitch


def angles_from_direction_legacy(direction: Vec3) -> tuple[float, float]:
    """Pre-fix broken signs — diagnostic comparison only."""
    dx, dy, dz = direction.x, direction.y, direction.z
    pitch = math.asin(clamp(-dy, -1.0, 1.0))
    yaw = math.atan2(dx, -dz)
    return yaw, pitch


def angle_between(a: Vec3, b: Vec3) -> float:
    return math.acos(clamp(dot(normalize(a), normalize(b)), -1.0, 1.0))


def angle_delta(from_angle: float, to_angle: float) -> float:
    delta = to_angle - from_angle
    while delta > math.pi:
        delta -= 2.0 * math.pi
    while delta < -math.pi:
        delta += 2.0 * math.pi
    return delta


def exp_smooth_angle(
    current: float, target: float, response_speed: float, dt: float
) -> float:
    """
    Frame-rate-independent exponential smoothing.

    alpha = 1 - exp(-responseSpeed * dt)
    """
    alpha = 1.0 - math.exp(-max(response_speed, 0.0) * max(dt, 0.0))
    return current + angle_delta(current, target) * alpha


def lerp_angle(current: float, target: float, smoothing: float) -> float:
    """Legacy frame-rate-dependent lerp (tests/reference only)."""
    return current + angle_delta(current, target) * clamp(smoothing, 0.0, 1.0)


def bone_world_position(target, bone: str) -> Vec3:
    """
    Aim point on target mesh — matches fixed JS getBoneWorldPosition.

    Bone heights are from feet; mesh center offset avoids double-counting.
    """
    base = target.position
    height = target.head_height if bone == "head" else target.chest_height
    center_offset = getattr(target, "mesh_center_offset", 0.9)
    return Vec3(base.x, base.y + (height - center_offset), base.z)


def predict_position(
    current: Vec3,
    velocity: Vec3,
    camera_pos: Vec3,
    projectile_speed: float,
) -> Vec3:
    distance = distance_between(current, camera_pos)
    travel = distance / max(projectile_speed, 0.001)
    return Vec3(
        current.x + velocity.x * travel,
        current.y + velocity.y * travel,
        current.z + velocity.z * travel,
    )


def fov_radius_pixels(aim_fov_deg: float, camera_vfov_deg: float, screen_height: float) -> float:
    aim_half = math.radians(aim_fov_deg) / 2.0
    vfov_half = math.radians(camera_vfov_deg) / 2.0
    focal = screen_height / 2.0 / math.tan(vfov_half)
    return math.tan(aim_half) * focal


def is_point_in_screen_bounds(
    ndc_x: float, ndc_y: float, ndc_z: float, margin: float = 0.02
) -> bool:
    lo = -1.0 + margin
    hi = 1.0 - margin
    return (
        -1.0 < ndc_z < 1.0
        and lo <= ndc_x <= hi
        and lo <= ndc_y <= hi
    )


def project_world_to_screen(
    world: Vec3,
    camera_pos: Vec3,
    yaw: float,
    pitch: float,
    vfov_deg: float,
    screen_width: float,
    screen_height: float,
) -> tuple[float, float, float, float, float]:
    """
    Simplified world→screen projection for mock targets.

    Returns (screen_x, screen_y, ndc_x, ndc_y, ndc_z).
    """
    # Camera-relative direction
    dx = world.x - camera_pos.x
    dy = world.y - camera_pos.y
    dz = world.z - camera_pos.z

    # Rotate into camera space (inverse YXZ)
    cos_y, sin_y = math.cos(yaw), math.sin(yaw)
    cos_p, sin_p = math.cos(pitch), math.sin(pitch)

    # Yaw around Y
    rx = dx * cos_y + dz * sin_y
    rz = -dx * sin_y + dz * cos_y
    ry = dy

    # Pitch around X
    cam_y = ry * cos_p - rz * sin_p
    cam_z = ry * sin_p + rz * cos_p
    cam_x = rx

    if cam_z >= -1e-6:
        return (-9999.0, -9999.0, 0.0, 0.0, 1.0)

    aspect = screen_width / max(screen_height, 1.0)
    vfov_half = math.radians(vfov_deg) / 2.0
    tan_v = math.tan(vfov_half)

    ndc_x = (cam_x / -cam_z) / (tan_v * aspect)
    ndc_y = (cam_y / -cam_z) / tan_v
    ndc_z = cam_z

    sx = (ndc_x * 0.5 + 0.5) * screen_width
    sy = (-ndc_y * 0.5 + 0.5) * screen_height
    return (sx, sy, ndc_x, ndc_y, ndc_z)


def dot(a: Vec3, b: Vec3) -> float:
    return a.x * b.x + a.y * b.y + a.z * b.z


def length(v: Vec3) -> float:
    return math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z)


def distance_between(a: Vec3, b: Vec3) -> float:
    return length(Vec3(a.x - b.x, a.y - b.y, a.z - b.z))


def normalize(v: Vec3) -> Vec3:
    ln = length(v)
    if ln <= 1e-9:
        return Vec3(0.0, 0.0, -1.0)
    return Vec3(v.x / ln, v.y / ln, v.z / ln)
