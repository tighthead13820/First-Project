"""
Aim-script plugin contract used by the overlay loader.

Any uploaded/imported ``.py`` file should expose either:

* a module-level ``create_script() -> AimScript`` factory, or
* a class named ``Script`` that implements ``AimScript``.

Scripts receive normalized camera/target frames and return stick commands.
They must not touch Windows APIs or game memory — adapters feed them data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol, runtime_checkable


@dataclass
class Vec3:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


@dataclass
class TargetSample:
    """One detectable target in world space (sandbox / adapter fed)."""

    id: str
    position: Vec3  # base / feet
    velocity: Vec3 = field(default_factory=Vec3)
    head_height: float = 1.7
    chest_height: float = 1.2


@dataclass
class CameraSample:
    position: Vec3
    yaw: float = 0.0  # radians
    pitch: float = 0.0  # radians


@dataclass
class AimFrame:
    """One tick of inputs for an aim script."""

    camera: CameraSample
    targets: list[TargetSample]
    dt: float = 1.0 / 30.0


@dataclass
class StickCommand:
    """Normalized stick / trigger output from a script."""

    rx: float = 0.0
    ry: float = 0.0
    l2: Optional[float] = None  # None = leave slider baseline alone
    r2: Optional[float] = None
    debug: str = ""


@runtime_checkable
class AimScript(Protocol):
    """Minimal interface every loadable script must satisfy."""

    name: str

    def reset(self) -> None:
        """Clear locks / smoothing state."""

    def update(self, frame: AimFrame) -> StickCommand:
        """Produce stick output for this frame."""
