"""
3D helpers — re-exports from aim_core.math3d (fixed YXZ signs).

Legacy import path kept for scripts/ and aimbridge/ modules.
Source of truth: aim_core/math3d.py (branch fix-camera-yaw-pitch-7c02).
"""

from __future__ import annotations

from aim_core import math3d as _m
from aim_core.stick_model import StickControllerModel, StickModelConfig as StickGains

# Re-export all math helpers
clamp = _m.clamp
forward_from_angles = _m.forward_from_angles
angles_from_direction = _m.angles_from_direction
angle_between = _m.angle_between
angle_delta = _m.angle_delta
exp_smooth_angle = _m.exp_smooth_angle
lerp_angle = _m.lerp_angle
bone_world_position = _m.bone_world_position
predict_position = _m.predict_position
normalize = _m.normalize
project_world_to_screen = _m.project_world_to_screen


def angles_to_stick(
    current_yaw: float,
    current_pitch: float,
    desired_yaw: float,
    desired_pitch: float,
    gains: StickGains | None = None,
) -> tuple[float, float]:
    model = StickControllerModel(gains or StickGains())
    return model.from_angle_errors(
        _m.angle_delta(current_yaw, desired_yaw),
        _m.angle_delta(current_pitch, desired_pitch),
        gains_yaw=model.config.yaw_full_scale_deg / 12.0 * 1.6,
        gains_pitch=model.config.pitch_full_scale_deg / 8.0 * 1.6,
    )


__all__ = [
    "StickGains",
    "StickControllerModel",
    "clamp",
    "forward_from_angles",
    "angles_from_direction",
    "angle_between",
    "angle_delta",
    "exp_smooth_angle",
    "lerp_angle",
    "bone_world_position",
    "predict_position",
    "angles_to_stick",
    "normalize",
    "project_world_to_screen",
]
