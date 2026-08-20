"""
Backend package.

Default factory returns SimulationBackend. Replace create_backend() or
pass a custom instance into the app when you add a real virtual pad.
"""

from __future__ import annotations

from .base import BackendError, VirtualControllerBackend
from .null_backend import NullBackend
from .simulation_backend import SimulationBackend

__all__ = [
    "BackendError",
    "VirtualControllerBackend",
    "NullBackend",
    "SimulationBackend",
    "create_backend",
]


def create_backend(kind: str = "simulation") -> VirtualControllerBackend:
    """
    Build a backend by name.

    kind:
      - "simulation" (default): logs frames when simulation mode is on
      - "null": never emits output
      - anything else: raises BackendError (hook point for future drivers)
    """
    key = (kind or "simulation").strip().lower()
    if key in {"simulation", "sim"}:
        return SimulationBackend()
    if key in {"null", "none", "ui"}:
        return NullBackend()
    raise BackendError(
        f"Unknown backend '{kind}'. "
        "Implement VirtualControllerBackend and register it in create_backend()."
    )
