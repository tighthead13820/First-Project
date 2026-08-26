"""
Pure-Python aim-assist core (no GUI).

Ported from vendor/aim-assist-sandbox/js on branch
``cursor/fix-camera-yaw-pitch-7c02`` — preserves corrected Three.js YXZ
yaw/pitch sign conventions. Do not reimplement from memory.
"""

from .config import AimConfig
from .engine import AimAssistEngine
from .stick_model import StickControllerModel, StickModelConfig
from .types import (
    AimResult,
    CameraState,
    ScreenTarget,
    TargetEvaluation,
    TrackingState,
    Vec3,
)

__all__ = [
    "AimAssistEngine",
    "AimConfig",
    "AimResult",
    "CameraState",
    "ScreenTarget",
    "StickControllerModel",
    "StickModelConfig",
    "TargetEvaluation",
    "TrackingState",
    "Vec3",
]
