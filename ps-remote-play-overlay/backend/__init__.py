"""
Backend package.

Default factory returns SimulationBackend. Pass ``vigem`` / ``vigem-ds4``
/ ``vigem-x360`` on Windows once ViGEmBus + vgamepad are installed.
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
    "ViGEmBackend",
    "create_backend",
]


def create_backend(kind: str = "simulation") -> VirtualControllerBackend:
    """
    Build a backend by name.

    kind:
      - "simulation" (default): logs frames when simulation mode is on
      - "null": never emits output
      - "vigem" / "vigem-ds4": virtual DualShock 4 via ViGEmBus
      - "vigem-x360": virtual Xbox 360 via ViGEmBus
    """
    key = (kind or "simulation").strip().lower()
    if key in {"simulation", "sim"}:
        return SimulationBackend()
    if key in {"null", "none", "ui"}:
        return NullBackend()
    if key in {"vigem", "vigem-ds4", "ds4", "dualshock"}:
        from .vigem_backend import ViGEmBackend

        return ViGEmBackend(pad_type="ds4")
    if key in {"vigem-x360", "x360", "xbox"}:
        from .vigem_backend import ViGEmBackend

        return ViGEmBackend(pad_type="x360")
    raise BackendError(
        f"Unknown backend '{kind}'. "
        "Use simulation, null, vigem, vigem-ds4, or vigem-x360."
    )


def __getattr__(name: str):
    # Lazy export so importing backend does not require vgamepad on Linux.
    if name == "ViGEmBackend":
        from .vigem_backend import ViGEmBackend

        return ViGEmBackend
    raise AttributeError(name)
