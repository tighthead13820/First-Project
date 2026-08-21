"""
Builtin aim script — Python port of vendor/aim-assist-sandbox/js/aimAssist.js

Same pipeline as the browser sandbox:
  FOV cone filter → closest-to-crosshair target → desired yaw/pitch
  → smooth lerp → map angle error onto right-stick RX/RY.

This is the default script the overlay loads when you click
“Load bundled sandbox script”. Uploaded user scripts can replace it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from aimbridge.math3d import (
    StickGains,
    angle_between,
    angles_from_direction,
    angles_to_stick,
    bone_world_position,
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
    stick_gains: StickGains = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.stick_gains is None:
            self.stick_gains = StickGains()


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

    def reset(self) -> None:
        self.selected_id = None
        self.debug_info = ""
        self._initialized = False

    def update(self, frame: AimFrame) -> StickCommand:
        cam = frame.camera
        if not self._initialized:
            self._yaw = cam.yaw
            self._pitch = cam.pitch
            self._initialized = True

        if not self.settings.enabled:
            self.selected_id = None
            self.debug_info = "Aim assist disabled"
            return StickCommand(debug=self.debug_info)

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
            self.debug_info = "No target in FOV cone"
            # Decay stick toward centre when nothing is locked.
            return StickCommand(rx=0.0, ry=0.0, debug=self.debug_info)

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

        dist = math.sqrt(
            (best_aim.x - cam.position.x) ** 2
            + (best_aim.y - cam.position.y) ** 2
            + (best_aim.z - cam.position.z) ** 2
        )
        self.debug_info = (
            f"Target: {best_id}\n"
            f"Bone: {self.settings.target_bone}\n"
            f"Distance: {dist:.1f} m\n"
            f"Cone angle: {math.degrees(best_angle):.2f}°\n"
            f"Stick RX={rx:+.2f} RY={ry:+.2f}"
        )
        return StickCommand(rx=rx, ry=ry, debug=self.debug_info)


def create_script() -> Script:
    return Script()
