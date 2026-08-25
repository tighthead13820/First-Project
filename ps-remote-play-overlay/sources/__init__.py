"""Target input sources for the live aim pipeline."""

from .base import TargetSource
from .mock_screen_source import MockScreenTargetSource
from .world_mock_source import WorldMockTargetSource

__all__ = ["TargetSource", "MockScreenTargetSource", "WorldMockTargetSource"]
