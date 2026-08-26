"""
Screen-space aim engine for normalized 2D target inputs.

Used by the live overlay pipeline when TargetSource supplies screen_x/y.
Pixel error → angular error → StickControllerModel.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from .stick_model import StickControllerModel, StickModelConfig
from .types import ScreenAimResult, ScreenTarget


@dataclass
class ScreenAimConfig:
    enabled: bool = True
    target_bone: str = "head"
    screen_width: float = 1920.0
    screen_height: float = 1080.0
    camera_hfov_deg: float = 90.0  # approximate horizontal FOV for PS stream
    max_pixel_error: float = 960.0
    prediction_enabled: bool = True
    prediction_lead_seconds: float = 0.05
    snap_mode: bool = False
    response_speed: float = 35.0


@dataclass
class ScreenAimEngine:
    config: ScreenAimConfig = field(default_factory=ScreenAimConfig)
    stick_model: StickControllerModel = field(default_factory=StickControllerModel)
    locked_id: Optional[str] = None
    _smooth_stick_x: float = 0.0
    _smooth_stick_y: float = 0.0

    @property
    def centre_x(self) -> float:
        return self.config.screen_width / 2.0

    @property
    def centre_y(self) -> float:
        return self.config.screen_height / 2.0

    def reset(self) -> None:
        self.locked_id = None
        self._smooth_stick_x = 0.0
        self._smooth_stick_y = 0.0

    def update(self, targets: list[ScreenTarget], dt: float) -> ScreenAimResult:
        cfg = self.config
        cx, cy = self.centre_x, self.centre_y

        if not cfg.enabled:
            return self._empty("Aim core disabled")

        visible = [t for t in targets if t.alive and t.visible]
        if not visible:
            self.locked_id = None
            return self._empty("SEARCHING — no targets")

        # Closest-to-centre selection (screen-wide)
        best: Optional[ScreenTarget] = None
        best_dist = float("inf")
        for t in visible:
            hx, hy = t.head if cfg.target_bone == "head" else t.chest
            dx, dy = hx - cx, hy - cy
            dist = math.hypot(dx, dy)
            if dist < best_dist:
                best_dist = dist
                best = t

        if best is None:
            return self._empty("SEARCHING")

        self.locked_id = best.id
        hx, hy = best.head if cfg.target_bone == "head" else best.chest

        if cfg.prediction_enabled:
            hx += best.velocity_x * cfg.prediction_lead_seconds
            hy += best.velocity_y * cfg.prediction_lead_seconds

        px_err = hx - cx
        py_err = hy - cy
        total_px = math.hypot(px_err, py_err)

        # Pixel → angular error via horizontal FOV
        hfov_half = math.radians(cfg.camera_hfov_deg) / 2.0
        focal_x = (cfg.screen_width / 2.0) / math.tan(hfov_half)
        aspect = cfg.screen_width / max(cfg.screen_height, 1.0)
        vfov_half = math.atan(math.tan(hfov_half) / aspect)
        focal_y = (cfg.screen_height / 2.0) / math.tan(vfov_half)

        yaw_err_deg = math.degrees(math.atan(px_err / focal_x))
        pitch_err_deg = math.degrees(math.atan(py_err / focal_y))

        raw_x, raw_y = self.stick_model.compute(
            pixel_error_x=px_err,
            pixel_error_y=py_err,
            yaw_error_deg=yaw_err_deg,
            pitch_error_deg=pitch_err_deg,
            dt=dt,
            snap=cfg.snap_mode,
            response_speed=cfg.response_speed,
        )

        if cfg.snap_mode:
            stick_x, stick_y = raw_x, raw_y
        else:
            alpha = 1.0 - math.exp(-max(cfg.response_speed, 0.0) * max(dt, 0.0))
            self._smooth_stick_x += (raw_x - self._smooth_stick_x) * alpha
            self._smooth_stick_y += (raw_y - self._smooth_stick_y) * alpha
            stick_x, stick_y = self._smooth_stick_x, self._smooth_stick_y

        return ScreenAimResult(
            selected_target_id=best.id,
            target_head_x=hx,
            target_head_y=hy,
            centre_x=cx,
            centre_y=cy,
            pixel_error_x=px_err,
            pixel_error_y=py_err,
            total_pixel_error=total_px,
            yaw_error_deg=yaw_err_deg,
            pitch_error_deg=pitch_err_deg,
            stick_x=stick_x,
            stick_y=stick_y,
            status="LOCKED",
            debug_lines=[
                f"Target: {best.id}",
                f"Head: {hx:.0f}, {hy:.0f}",
                f"Centre: {cx:.0f}, {cy:.0f}",
                f"Pixel error: {px_err:+.0f}, {py_err:+.0f}",
                f"Yaw error: {yaw_err_deg:+.2f}°",
                f"Pitch error: {pitch_err_deg:+.2f}°",
                f"Stick: {stick_x:+.2f}, {stick_y:+.2f}",
            ],
        )

    def _empty(self, status: str) -> ScreenAimResult:
        return ScreenAimResult(
            selected_target_id=None,
            target_head_x=0.0,
            target_head_y=0.0,
            centre_x=self.centre_x,
            centre_y=self.centre_y,
            pixel_error_x=0.0,
            pixel_error_y=0.0,
            total_pixel_error=0.0,
            yaw_error_deg=0.0,
            pitch_error_deg=0.0,
            stick_x=0.0,
            stick_y=0.0,
            status=status,
            debug_lines=[status],
        )
