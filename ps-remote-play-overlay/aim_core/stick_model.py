"""
Convert aim error into hardware right-stick values.

Input: pixel error and/or yaw/pitch error (degrees).
Output: stick_x, stick_y clamped to [-1.0, +1.0].
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from . import math3d as m


@dataclass
class StickModelConfig:
    """Tuning for overlay → vgamepad stick mapping."""

    # Degrees of error that saturate stick at ±1.0
    yaw_full_scale_deg: float = 12.0
    pitch_full_scale_deg: float = 8.0
    # Optional pixel-based gain (used when angles are near zero)
    pixel_gain_x: float = 0.00135
    pixel_gain_y: float = 0.00135
    deadzone: float = 0.02
    max_output: float = 1.0


@dataclass
class StickControllerModel:
    config: StickModelConfig = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.config is None:
            self.config = StickModelConfig()

    def compute(
        self,
        *,
        pixel_error_x: float,
        pixel_error_y: float,
        yaw_error_deg: float,
        pitch_error_deg: float,
        dt: float = 1.0 / 30.0,
        snap: bool = False,
        response_speed: float = 35.0,
    ) -> tuple[float, float]:
        """
        Map errors to stick output.

        Positive yaw error (target right of centre) → positive stick X.
        Positive pitch error (target below centre in angular sense) → positive stick Y.
        """
        del dt, snap, response_speed  # smoothing handled by caller

        cfg = self.config
        if abs(yaw_error_deg) > 1e-6:
            stick_x = yaw_error_deg / max(cfg.yaw_full_scale_deg, 1e-6)
        else:
            stick_x = pixel_error_x * cfg.pixel_gain_x

        if abs(pitch_error_deg) > 1e-6:
            stick_y = pitch_error_deg / max(cfg.pitch_full_scale_deg, 1e-6)
        else:
            stick_y = -pixel_error_y * cfg.pixel_gain_y

        stick_x = self._apply_deadzone(stick_x)
        stick_y = self._apply_deadzone(stick_y)

        cap = cfg.max_output
        return (
            m.clamp(stick_x, -cap, cap),
            m.clamp(stick_y, -cap, cap),
        )

    def from_angle_errors(
        self,
        yaw_error_rad: float,
        pitch_error_rad: float,
        gains_yaw: float = 1.6,
        gains_pitch: float = 1.6,
    ) -> tuple[float, float]:
        """Direct radian error → stick (3D world pipeline)."""
        dyaw = yaw_error_rad
        dpitch = pitch_error_rad
        if abs(dyaw) < 0.002:
            dyaw = 0.0
        if abs(dpitch) < 0.002:
            dpitch = 0.0
        return (
            m.clamp(dyaw * gains_yaw, -1.0, 1.0),
            m.clamp(dpitch * gains_pitch, -1.0, 1.0),
        )

    def _apply_deadzone(self, value: float) -> float:
        if abs(value) < self.config.deadzone:
            return 0.0
        return value
