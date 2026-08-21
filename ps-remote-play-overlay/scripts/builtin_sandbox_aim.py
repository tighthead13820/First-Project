"""
Builtin aim script — Python port of vendor/aim-assist-sandbox/js/aimAssist.js

Same pipeline as the browser sandbox:
  FOV cone filter → closest-to-crosshair target → desired yaw/pitch
  → smooth lerp → map angle error onto right-stick RX/RY.

While locked on a target (optional):
  - pull R2 fully (auto-fire for Remote Play testing)
  - add a tunable recoil-compensation stick bias

This is the default script the overlay loads when you click
“Load sandbox”. Uploaded user scripts can replace it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from aimbridge.math3d import (
    StickGains,
    angle_between,
    angles_from_direction,
    angles_to_stick,
    bone_world_position,
    clamp,
    forward_from_angles,
    lerp_angle,
    predict_position,
)
from scripts.api import AimFrame, StickCommand, Vec3


@dataclass
class SandboxAimSettings:
    enabled: bool = True
    fov_deg: float = 12.0
    smoothing: float = 0.15
    target_bone: str = "chest"  # "head" | "chest"
    max_range: float = 50.0
    prediction_enabled: bool = False
    projectile_speed: float = 200.0
    stick_gains: StickGains = field(default_factory=StickGains)

    # --- fire / recoil (overlay controller outputs) ---
    # When locked, set L2/R2 so simulation / ViGEm backends pull both triggers.
    auto_fire_l2: bool = True
    auto_fire_r2: bool = True
    # While firing, push stick opposite a simple upward-recoil model.
    recoil_compensate: bool = True
    # Vertical pull strength (stick units / second of sustained fire, capped).
    recoil_vertical: float = 0.35
    # Horizontal sway amplitude while firing (stick units).
    recoil_horizontal: float = 0.08
    # How fast the vertical compensator ramps in after lock+fire starts.
    recoil_ramp_seconds: float = 0.45


class Script:
    """Loadable aim script (discovered by scripts.loader)."""

    name = "sandbox-aimAssist"

    def __init__(self, settings: SandboxAimSettings | None = None) -> None:
        self.settings = settings or SandboxAimSettings()
        self.selected_id: str | None = None
        self.debug_info = ""
        # Smoothed look direction maintained across frames (like the JS class).
        self._yaw = 0.0
        self._pitch = 0.0
        self._initialized = False
        self._fire_time = 0.0  # seconds continuously locked + firing

    def reset(self) -> None:
        self.selected_id = None
        self.debug_info = ""
        self._initialized = False
        self._fire_time = 0.0

    def update(self, frame: AimFrame) -> StickCommand:
        cam = frame.camera
        if not self._initialized:
            self._yaw = cam.yaw
            self._pitch = cam.pitch
            self._initialized = True

        if not self.settings.enabled:
            self.selected_id = None
            self._fire_time = 0.0
            self.debug_info = "Aim assist disabled"
            return StickCommand(
                rx=0.0, ry=0.0, l2=0.0, r2=0.0, debug=self.debug_info
            )

        forward = forward_from_angles(self._yaw, self._pitch)
        fov_half = math.radians(self.settings.fov_deg) / 2.0

        best_id: str | None = None
        best_angle = float("inf")
        best_aim = Vec3()

        for target in frame.targets:
            aim = bone_world_position(
                target.position,
                self.settings.target_bone,
                target.head_height,
                target.chest_height,
            )
            if self.settings.prediction_enabled:
                aim = predict_position(
                    aim,
                    target.velocity,
                    cam.position,
                    self.settings.projectile_speed,
                )

            to_target = Vec3(
                aim.x - cam.position.x,
                aim.y - cam.position.y,
                aim.z - cam.position.z,
            )
            distance = math.sqrt(
                to_target.x**2 + to_target.y**2 + to_target.z**2
            )
            if distance > self.settings.max_range or distance < 1e-6:
                continue

            angle = angle_between(forward, to_target)
            if angle <= fov_half and angle < best_angle:
                best_angle = angle
                best_id = target.id
                best_aim = aim

        self.selected_id = best_id

        if best_id is None:
            self._fire_time = 0.0
            self.debug_info = "No target in FOV cone"
            # Release triggers and centre stick when lock is lost.
            return StickCommand(
                rx=0.0, ry=0.0, l2=0.0, r2=0.0, debug=self.debug_info
            )

        to_best = Vec3(
            best_aim.x - cam.position.x,
            best_aim.y - cam.position.y,
            best_aim.z - cam.position.z,
        )
        desired_yaw, desired_pitch = angles_from_direction(to_best)

        new_yaw = lerp_angle(self._yaw, desired_yaw, self.settings.smoothing)
        new_pitch = lerp_angle(
            self._pitch, desired_pitch, self.settings.smoothing
        )

        # Stick command = remaining error after this smooth step
        # (what you'd push on a pad to finish the rotation).
        rx, ry = angles_to_stick(
            new_yaw,
            new_pitch,
            desired_yaw,
            desired_pitch,
            self.settings.stick_gains,
        )

        self._yaw = new_yaw
        self._pitch = new_pitch

        # --- lock extras: L2/R2 + recoil compensation ---
        l2 = 1.0 if self.settings.auto_fire_l2 else None
        r2 = 1.0 if self.settings.auto_fire_r2 else None
        firing = self.settings.auto_fire_r2 or self.settings.auto_fire_l2
        if firing:
            self._fire_time += max(frame.dt, 0.0)
        else:
            self._fire_time = 0.0

        recoil_rx = 0.0
        recoil_ry = 0.0
        if self.settings.auto_fire_r2 and self.settings.recoil_compensate:
            recoil_rx, recoil_ry = self._recoil_offset(self._fire_time)
            rx = clamp(rx + recoil_rx, -1.0, 1.0)
            ry = clamp(ry + recoil_ry, -1.0, 1.0)

        dist = math.sqrt(
            (best_aim.x - cam.position.x) ** 2
            + (best_aim.y - cam.position.y) ** 2
            + (best_aim.z - cam.position.z) ** 2
        )
        l2_txt = "L2=1.0" if self.settings.auto_fire_l2 else "L2=manual"
        r2_txt = "R2=1.0" if self.settings.auto_fire_r2 else "R2=manual"
        recoil_txt = (
            f"recoil Δ=({recoil_rx:+.2f},{recoil_ry:+.2f})"
            if self.settings.recoil_compensate and self.settings.auto_fire_r2
            else "recoil off"
        )
        self.debug_info = (
            f"Target: {best_id}\n"
            f"Bone: {self.settings.target_bone}\n"
            f"Distance: {dist:.1f} m\n"
            f"Cone angle: {math.degrees(best_angle):.2f}°\n"
            f"Stick RX={rx:+.2f} RY={ry:+.2f}\n"
            f"{l2_txt}  {r2_txt}  {recoil_txt}  t={self._fire_time:.2f}s"
        )
        return StickCommand(
            rx=rx, ry=ry, l2=l2, r2=r2, debug=self.debug_info
        )

    def _recoil_offset(self, fire_time: float) -> tuple[float, float]:
        """
        Simple test pattern: games usually kick the camera *up*, so we
        compensate by pulling the stick *down* (positive RY here) and add a
        light left/right sway. Strength ramps in over recoil_ramp_seconds.
        """
        ramp = 1.0
        if self.settings.recoil_ramp_seconds > 1e-6:
            ramp = clamp(fire_time / self.settings.recoil_ramp_seconds, 0.0, 1.0)

        # Vertical: steady pull down, slightly easing after the ramp.
        ry = self.settings.recoil_vertical * ramp

        # Horizontal: slow sine sway so you can see compensation on RX too.
        rx = self.settings.recoil_horizontal * ramp * math.sin(fire_time * 9.0)
        return rx, ry


def create_script() -> Script:
    return Script()
