"""
Null backend — UI-only. Never emits controller output.

Use this when you only need the overlay / sliders / HUD for dry runs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import VirtualControllerBackend

if TYPE_CHECKING:
    from controls.state import ControllerState


class NullBackend(VirtualControllerBackend):
    name = "null"

    def connect(self) -> None:
        # Nothing to open.
        return None

    def disconnect(self) -> None:
        return None

    def push(self, state: "ControllerState") -> None:
        # Intentionally ignored.
        return None
