"""Aim-assist configuration."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AimConfig:
    enabled: bool = True
    fov_deg: float = 12.0
    screen_wide_select: bool = True
    camera_vfov: float = 75.0
    target_bone: str = "head"
    max_range: float = 100.0
    prediction_enabled: bool = True
    projectile_speed: float = 200.0
    snap_mode: bool = True
    response_speed: float = 35.0
    release_fov_multiplier: float = 1.0
    debug_force_first_target: bool = False
    debug_ignore_range: bool = False
