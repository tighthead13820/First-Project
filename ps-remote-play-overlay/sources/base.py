"""
TargetSource interface — normalized target + camera feed for aim_core.

Implementations supply coordinates from a mock scene, manual debug input,
or (externally) a validated stream adapter. This overlay does NOT ship
automated PS Remote Play screen/object detection.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from aim_core.types import CameraState, ScreenTarget, WorldTarget


class TargetSource(ABC):
    """Live target capture abstraction."""

    name: str = "base"

    @abstractmethod
    def get_screen_targets(self) -> list[ScreenTarget]:
        """Return targets in screen pixel space (top-left origin)."""

    @abstractmethod
    def get_world_targets(self) -> list[WorldTarget]:
        """Return 3D targets for world-space aim_core (optional)."""

    @abstractmethod
    def get_camera_state(self) -> CameraState:
        """Current camera / view state."""

    @abstractmethod
    def tick(self, dt: float) -> None:
        """Advance internal simulation / buffer."""

    def get_screen_size(self) -> tuple[int, int]:
        cam = self.get_camera_state()
        return cam.screen_width, cam.screen_height

    def describe(self) -> str:
        return self.name
