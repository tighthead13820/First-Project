"""
Virtual-controller backend interface.

Implement VirtualControllerBackend to plug in a real device later
(e.g. ViGEmBus + vgamepad, or another HID injector). The overlay only
depends on this abstract API — never on a specific driver.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from controls.state import ControllerState


class VirtualControllerBackend(ABC):
    """Sends normalized axes somewhere (or nowhere, for UI-only testing)."""

    name: str = "base"

    @abstractmethod
    def connect(self) -> None:
        """Acquire resources (open virtual pad, start driver session, …)."""

    @abstractmethod
    def disconnect(self) -> None:
        """Release resources and centre/clear outputs if needed."""

    @abstractmethod
    def push(self, state: "ControllerState") -> None:
        """Push the latest axes. Called on every UI tick while running."""

    def describe(self) -> str:
        return self.name


class BackendError(RuntimeError):
    """Raised when a backend cannot connect or push state."""
