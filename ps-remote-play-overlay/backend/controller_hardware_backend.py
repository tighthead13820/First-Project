"""
VirtualControllerBackend adapter around RealControllerHardware (VDS4Gamepad).
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from controller_hardware import RealControllerHardware

from .base import BackendError, VirtualControllerBackend

if TYPE_CHECKING:
    from controls.state import ControllerState


class ControllerHardwareBackend(VirtualControllerBackend):
    """Production DS4 backend — delegates to controller_hardware.py."""

    name = "vigem-ds4"

    def __init__(self, hardware: RealControllerHardware | None = None) -> None:
        self._hw = hardware or RealControllerHardware()
        self._connected = False
        self._last_sim = False

    @property
    def hardware(self) -> RealControllerHardware:
        return self._hw

    def connect(self) -> None:
        if sys.platform != "win32":
            raise BackendError(
                "Controller hardware backend requires Windows + ViGEmBus."
            )
        if not self._hw.enabled:
            raise BackendError(
                "DualShock 4 driver not available. Install ViGEmBus and vgamepad:\n"
                "  pip install vgamepad\n"
                "  https://github.com/nefarius/ViGEmBus/releases"
            )
        self._connected = True
        self._hw.rest()
        print(f"[vigem] connected ({self.name}) via RealControllerHardware")

    def disconnect(self) -> None:
        if self._connected:
            self._hw.shutdown()
        self._connected = False
        print(f"[vigem] disconnected ({self.name})")

    def push(self, state: "ControllerState") -> None:
        if not self._connected or not self._hw.enabled:
            return

        if not state.simulation_mode:
            if self._last_sim:
                self._hw.rest()
            self._last_sim = False
            return

        self._last_sim = True
        self._hw.send_full_input(state.rx, state.ry, state.l2, state.r2)
