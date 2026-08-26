"""
Shared controller state for the overlay.

All UI widgets, keyboard shortcuts, and backends read/write through
ControllerState so there is a single source of truth for RX/RY/L2/R2.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable

Listener = Callable[["ControllerState"], None]


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(value)))


@dataclass
class ControllerState:
    """Normalized DualSense-style axes used by PS Remote Play testing.

    Axes
    ----
    rx, ry : right stick, each in [-1.0, +1.0], centre = 0.0
    l2, r2 : analog triggers, each in [0.0, 1.0], released = 0.0
    """

    rx: float = 0.0
    ry: float = 0.0
    l2: float = 0.0
    r2: float = 0.0
    simulation_mode: bool = False
    _listeners: list[Listener] = field(default_factory=list, repr=False)

    # ------------------------------------------------------------------
    # Subscriptions
    # ------------------------------------------------------------------
    def subscribe(self, listener: Listener) -> None:
        """Register a callback invoked after any state mutation."""
        if listener not in self._listeners:
            self._listeners.append(listener)

    def unsubscribe(self, listener: Listener) -> None:
        if listener in self._listeners:
            self._listeners.remove(listener)

    def _notify(self) -> None:
        for listener in list(self._listeners):
            listener(self)

    # ------------------------------------------------------------------
    # Mutators
    # ------------------------------------------------------------------
    def set_rx(self, value: float, *, notify: bool = True) -> None:
        self.rx = _clamp(value, -1.0, 1.0)
        if notify:
            self._notify()

    def set_ry(self, value: float, *, notify: bool = True) -> None:
        self.ry = _clamp(value, -1.0, 1.0)
        if notify:
            self._notify()

    def set_l2(self, value: float, *, notify: bool = True) -> None:
        self.l2 = _clamp(value, 0.0, 1.0)
        if notify:
            self._notify()

    def set_r2(self, value: float, *, notify: bool = True) -> None:
        self.r2 = _clamp(value, 0.0, 1.0)
        if notify:
            self._notify()

    def set_right_stick(self, rx: float, ry: float, *, notify: bool = True) -> None:
        self.rx = _clamp(rx, -1.0, 1.0)
        self.ry = _clamp(ry, -1.0, 1.0)
        if notify:
            self._notify()

    def reset_right_stick(self, *, notify: bool = True) -> None:
        """Snap the right stick back to centre (0, 0)."""
        self.set_right_stick(0.0, 0.0, notify=notify)

    def set_simulation_mode(self, enabled: bool, *, notify: bool = True) -> None:
        self.simulation_mode = bool(enabled)
        if notify:
            self._notify()

    def apply_partial(self, updates: dict[str, float], *, notify: bool = True) -> None:
        """Apply a dict of axis updates (keys: rx, ry, l2, r2)."""
        if "rx" in updates:
            self.rx = _clamp(updates["rx"], -1.0, 1.0)
        if "ry" in updates:
            self.ry = _clamp(updates["ry"], -1.0, 1.0)
        if "l2" in updates:
            self.l2 = _clamp(updates["l2"], 0.0, 1.0)
        if "r2" in updates:
            self.r2 = _clamp(updates["r2"], 0.0, 1.0)
        if notify:
            self._notify()

    def snapshot(self) -> dict[str, float | bool]:
        return {
            "rx": self.rx,
            "ry": self.ry,
            "l2": self.l2,
            "r2": self.r2,
            "simulation_mode": self.simulation_mode,
        }

    def format_hud(self) -> str:
        mode = "SIM ON" if self.simulation_mode else "SIM OFF"
        return (
            f"RX  {self.rx:+.2f}\n"
            f"RY  {self.ry:+.2f}\n"
            f"L2  {self.l2:.2f}\n"
            f"R2  {self.r2:.2f}\n"
            f"{mode}"
        )

    def axes_tuple(self) -> tuple[float, float, float, float]:
        return (self.rx, self.ry, self.l2, self.r2)

    def copy_axes_from(self, other: "ControllerState", *, notify: bool = True) -> None:
        self.rx, self.ry, self.l2, self.r2 = other.axes_tuple()
        if notify:
            self._notify()


def merge_held_overrides(
    base: ControllerState,
    overrides: Iterable[dict[str, float]],
) -> dict[str, float]:
    """Combine slider base values with any held keyboard overrides."""
    merged = {"rx": base.rx, "ry": base.ry, "l2": base.l2, "r2": base.r2}
    for override in overrides:
        merged.update(override)
    return merged
