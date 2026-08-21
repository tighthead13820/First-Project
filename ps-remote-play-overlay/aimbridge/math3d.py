"""
3D helpers — Python port of vendor/aim-assist-sandbox/js/math.js

Coordinate system matches the Three.js sandbox:
  +X right, +Y up, -Z forward when yaw = pitch = 0.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from scripts.api import Vec3


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def forward_from_angles(yaw: float, pitch: float) -> Vec3:
    cos_pitch = math.cos(pitch)
    return _normalize(
        Vec3(
            cos_pitch * math.sin(yaw),
            -math.sin(pitch),
            -cos_pitch * math.cos(yaw),
        )
    )


def angles_from_direction(direction: Vec3) -> tuple[float, float]:
    pitch = math.asin(clamp(-direction.y, -1.0, 1.0))
    yaw = math.atan2(direction.x, -direction.z)
    return yaw, pitch


def angle_between(a: Vec3, b: Vec3) -> float:
    return math.acos(clamp(_dot(_normalize(a), _normalize(b)), -1.0, 1.0))


def angle_delta(from_angle: float, to_angle: float) -> float:
    delta = to_angle - from_angle
    while delta > math.pi:
        delta -= 2.0 * math.pi
    while delta < -math.pi:
        delta += 2.0 * math.pi
    return delta


def lerp_angle(current: float, target: float, smoothing: float) -> float:
    return current + angle_delta(current, target) * smoothing


def bone_world_position(
    base: Vec3, bone: str, head_height: float, chest_height: float
) -> Vec3:
    height = head_height if bone == "head" else chest_height
    return Vec3(base.x, base.y + height, base.z)


def predict_position(
    current: Vec3, velocity: Vec3, camera: Vec3, projectile_speed: float
) -> Vec3:
    distance = _distance(current, camera)
    travel = distance / max(projectile_speed, 0.001)
    return Vec3(
        current.x + velocity.x * travel,
        current.y + velocity.y * travel,
        current.z + velocity.z * travel,
    )


def _dot(a: Vec3, b: Vec3) -> float:
    return a.x * b.x + a.y * b.y + a.z * b.z


def _length(v: Vec3) -> float:
    return math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z)


def _distance(a: Vec3, b: Vec3) -> float:
    return _length(Vec3(a.x - b.x, a.y - b.y, a.z - b.z))


def _normalize(v: Vec3) -> Vec3:
    length = _length(v)
    if length <= 1e-9:
        return Vec3(0.0, 0.0, -1.0)
    return Vec3(v.x / length, v.y / length, v.z / length)


@dataclass
class StickGains:
    """Map yaw/pitch error (radians) onto stick deflection."""

    yaw_gain: float = 1.6
    pitch_gain: float = 1.6
    deadzone: float = 0.002  # rad


def angles_to_stick(
    current_yaw: float,
    current_pitch: float,
    desired_yaw: float,
    desired_pitch: float,
    gains: StickGains | None = None,
) -> tuple[float, float]:
    """
    Convert shortest-path angle error into right-stick RX/RY.

    Positive yaw delta (look right) → positive RX.
    Positive pitch delta (look down in sandbox convention) → positive RY.
    """
    g = gains or StickGains()
    dyaw = angle_delta(current_yaw, desired_yaw)
    dpitch = angle_delta(current_pitch, desired_pitch)

    if abs(dyaw) < g.deadzone:
        dyaw = 0.0
    if abs(dpitch) < g.deadzone:
        dpitch = 0.0

    rx = clamp(dyaw * g.yaw_gain, -1.0, 1.0)
    ry = clamp(dpitch * g.pitch_gain, -1.0, 1.0)
    return rx, ry
