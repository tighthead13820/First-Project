"""
3D aim-assist engine — port of aim-assist-sandbox/js/aimAssist.js

Branch: cursor/fix-camera-yaw-pitch-7c02
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from .config import AimConfig
from . import math3d as m
from .types import AimResult, CameraState, TargetEvaluation, TrackingState, Vec3, WorldTarget


@dataclass
class AimAssistEngine:
    config: AimConfig = field(default_factory=AimConfig)
    locked_target_id: Optional[str] = None
    last_tracking: Optional[TrackingState] = None
    last_evaluations: list[TargetEvaluation] = field(default_factory=list)

    def acquire_fov_deg(self) -> float:
        if self.config.screen_wide_select:
            return self.config.camera_vfov * 0.98
        return self.config.fov_deg

    def release_fov_deg(self) -> float:
        return self.acquire_fov_deg() * self.config.release_fov_multiplier

    def reset(self) -> None:
        self.locked_target_id = None
        self.last_tracking = None
        self.last_evaluations = []

    def update(
        self,
        camera: CameraState,
        targets: list[WorldTarget],
        dt: float,
    ) -> AimResult:
        cfg = self.config
        if not cfg.enabled:
            self.locked_target_id = None
            self.last_tracking = None
            return AimResult(
                selected_target_id=None,
                tracking=None,
                new_yaw=camera.yaw,
                new_pitch=camera.pitch,
                yaw_error_deg=0.0,
                pitch_error_deg=0.0,
                evaluations=[],
                debug_lines=["Aim assist disabled"],
                enabled=False,
            )

        yaw, pitch = camera.yaw, camera.pitch
        position = camera.position
        forward = m.forward_from_angles(yaw, pitch)

        acquire_half = math.radians(self.acquire_fov_deg()) / 2.0
        release_half = math.radians(self.release_fov_deg()) / 2.0

        evaluations: list[TargetEvaluation] = []
        best_id: Optional[str] = None
        best_angle = float("inf")
        nearest: Optional[TargetEvaluation] = None

        for target in targets:
            if not target.alive or not target.visible:
                continue

            aim = m.bone_world_position(target, cfg.target_bone)
            if cfg.prediction_enabled:
                aim = m.predict_position(
                    aim, target.velocity, position, cfg.projectile_speed
                )

            to_target = Vec3(
                aim.x - position.x,
                aim.y - position.y,
                aim.z - position.z,
            )
            dist = m.length(to_target)
            direction = m.normalize(to_target) if dist > 1e-8 else Vec3(0, 0, -1)
            angle = m.angle_between(forward, direction)
            angle_deg = math.degrees(angle)
            dot_val = m.dot(forward, direction)
            in_range = cfg.debug_ignore_range or dist <= cfg.max_range
            in_front = dot_val > 0

            sx, sy, ndc_x, ndc_y, ndc_z = m.project_world_to_screen(
                aim,
                position,
                yaw,
                pitch,
                camera.vfov_deg,
                float(camera.screen_width),
                float(camera.screen_height),
            )
            on_screen = m.is_point_in_screen_bounds(ndc_x, ndc_y, ndc_z)
            inside_fov = (
                (on_screen and in_front)
                if cfg.screen_wide_select
                else (in_front and angle <= acquire_half)
            )
            passes = in_range and inside_fov

            ev = TargetEvaluation(
                target_id=target.id,
                aim_point=aim.copy(),
                distance=dist,
                angle_rad=angle,
                angle_deg=angle_deg,
                in_range=in_range,
                in_front=in_front,
                on_screen=on_screen,
                inside_fov=inside_fov,
                passes=passes,
            )
            evaluations.append(ev)

            if nearest is None or angle < nearest.angle_rad:
                nearest = ev
            if passes and angle < best_angle:
                best_angle = angle
                best_id = target.id

        if cfg.debug_force_first_target and targets:
            best_id = targets[0].id
            best_angle = evaluations[0].angle_rad if evaluations else 0.0

        self.last_evaluations = evaluations

        # Target lock
        lock_eval: Optional[TargetEvaluation] = None
        if cfg.screen_wide_select:
            self.locked_target_id = best_id
            lock_eval = next((e for e in evaluations if e.target_id == best_id), None)
        else:
            if self.locked_target_id:
                lock_eval = next(
                    (e for e in evaluations if e.target_id == self.locked_target_id),
                    None,
                )
                still = (
                    lock_eval
                    and lock_eval.in_range
                    and lock_eval.in_front
                    and lock_eval.angle_rad <= release_half
                )
                if not still:
                    self.locked_target_id = None
                    lock_eval = None
            if not self.locked_target_id and best_id:
                self.locked_target_id = best_id
                lock_eval = next(
                    (e for e in evaluations if e.target_id == best_id), None
                )

        track_id = self.locked_target_id
        if not track_id:
            self.last_tracking = None
            return AimResult(
                selected_target_id=None,
                tracking=None,
                new_yaw=yaw,
                new_pitch=pitch,
                yaw_error_deg=0.0,
                pitch_error_deg=0.0,
                evaluations=evaluations,
                debug_lines=self._debug_no_target(nearest),
                enabled=True,
            )

        track_target = next((t for t in targets if t.id == track_id), None)
        if track_target is None:
            self.last_tracking = None
            return AimResult(
                selected_target_id=None,
                tracking=None,
                new_yaw=yaw,
                new_pitch=pitch,
                yaw_error_deg=0.0,
                pitch_error_deg=0.0,
                evaluations=evaluations,
                debug_lines=["Target lost"],
                enabled=True,
            )

        # Live aim point every frame
        live_aim = m.bone_world_position(track_target, cfg.target_bone)
        if cfg.prediction_enabled:
            live_aim = m.predict_position(
                live_aim,
                track_target.velocity,
                position,
                cfg.projectile_speed,
            )

        to_live = m.normalize(
            Vec3(
                live_aim.x - position.x,
                live_aim.y - position.y,
                live_aim.z - position.z,
            )
        )
        desired_yaw, desired_pitch = m.angles_from_direction(to_live)
        yaw_err = m.angle_delta(yaw, desired_yaw)
        pitch_err = m.angle_delta(pitch, desired_pitch)

        if cfg.snap_mode:
            new_yaw, new_pitch = desired_yaw, desired_pitch
        else:
            new_yaw = m.exp_smooth_angle(yaw, desired_yaw, cfg.response_speed, dt)
            new_pitch = m.exp_smooth_angle(
                pitch, desired_pitch, cfg.response_speed, dt
            )

        post_forward = m.forward_from_angles(new_yaw, new_pitch)
        pre_err = m.angle_between(forward, to_live)
        post_err = m.angle_between(post_forward, to_live)

        tracking = TrackingState(
            target_id=track_id,
            aim_point=live_aim,
            current_yaw=yaw,
            current_pitch=pitch,
            desired_yaw=desired_yaw,
            desired_pitch=desired_pitch,
            new_yaw=new_yaw,
            new_pitch=new_pitch,
            yaw_error_deg=math.degrees(yaw_err),
            pitch_error_deg=math.degrees(pitch_err),
            pre_error_deg=math.degrees(pre_err),
            post_error_deg=math.degrees(post_err),
            snap=cfg.snap_mode,
            locked=True,
            tracking=True,
        )
        self.last_tracking = tracking

        return AimResult(
            selected_target_id=track_id,
            tracking=tracking,
            new_yaw=new_yaw,
            new_pitch=new_pitch,
            yaw_error_deg=tracking.yaw_error_deg,
            pitch_error_deg=tracking.pitch_error_deg,
            evaluations=evaluations,
            debug_lines=self._debug_tracking(tracking, lock_eval),
            enabled=True,
        )

    def _debug_no_target(self, nearest: Optional[TargetEvaluation]) -> list[str]:
        lines = ["Tracking: NO", f"Snap: {'ON' if self.config.snap_mode else 'OFF'}"]
        if nearest:
            lines.append(
                f"Nearest: {nearest.target_id} ∠{nearest.angle_deg:.2f}° "
                f"{'IN FOV' if nearest.inside_fov else 'OUTSIDE'}"
            )
        else:
            lines.append("Nearest: none")
        return lines

    def _debug_tracking(
        self, t: TrackingState, lock_eval: Optional[TargetEvaluation]
    ) -> list[str]:
        mode = (
            f"screen-wide (FOV {self.config.camera_vfov:.0f}°)"
            if self.config.screen_wide_select
            else f"cone {self.config.fov_deg:.1f}°"
        )
        on_screen = lock_eval.on_screen if lock_eval else False
        return [
            f"Target: {t.target_id} → {self.config.target_bone}",
            f"Mode: {mode}",
            f"On screen: {'YES' if on_screen else 'NO'}",
            f"Current error: {t.pre_error_deg:.2f}°",
            f"Yaw error: {t.yaw_error_deg:.2f}°",
            f"Pitch error: {t.pitch_error_deg:.2f}°",
            f"Post-apply error: {t.post_error_deg:.3f}°",
            f"Response speed: {self.config.response_speed}",
            f"Tracking: YES",
            f"Snap: {'ON' if t.snap else 'OFF'}",
        ]
