"""
Simulation backend — exercises the “send output” path without a driver.

When simulation mode is enabled on ControllerState, each push() records
the axes that *would* be sent to a virtual pad. Swap this class for a
real ViGEm/vgamepad implementation later without changing the UI.

Example future backend sketch (not shipped):

    import vgamepad as vg

    class ViGEmBackend(VirtualControllerBackend):
        name = "vigem"
        def connect(self):
            self.pad = vg.VX360Gamepad()  # or VDS4Gamepad
        def push(self, state):
            if not state.simulation_mode:
                return
            self.pad.right_joystick_float(x_value_float=state.rx,
                                          y_value_float=-state.ry)
            self.pad.left_trigger_float(value_float=state.l2)
            self.pad.right_trigger_float(value_float=state.r2)
            self.pad.update()
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING, Deque, Optional

from .base import VirtualControllerBackend

if TYPE_CHECKING:
    from controls.state import ControllerState


@dataclass(frozen=True)
class SimulatedFrame:
    """One frame of axes that would have been sent to a virtual pad."""

    timestamp: float
    rx: float
    ry: float
    l2: float
    r2: float


class SimulationBackend(VirtualControllerBackend):
    """
    Logs outbound frames while simulation_mode is True.

    - Does not talk to any kernel driver.
    - Keeps a short ring buffer so you can inspect recent output.
    - Prints a throttled line to stdout for quick debugging.
    """

    name = "simulation"
    history_size: int = 120  # ~4 seconds at 30 Hz
    print_every_n: int = 15  # print roughly twice per second at 30 Hz

    def __init__(self) -> None:
        self._connected = False
        self._history: Deque[SimulatedFrame] = deque(maxlen=self.history_size)
        self._push_count = 0
        self._last_printed: Optional[SimulatedFrame] = None

    def connect(self) -> None:
        self._connected = True
        print("[simulation] backend connected (no hardware)")

    def disconnect(self) -> None:
        self._connected = False
        self._history.clear()
        print("[simulation] backend disconnected")

    def push(self, state: "ControllerState") -> None:
        if not self._connected:
            return
        # Simulation mode gate: when off, we do not emit frames.
        if not state.simulation_mode:
            return

        frame = SimulatedFrame(
            timestamp=time.time(),
            rx=state.rx,
            ry=state.ry,
            l2=state.l2,
            r2=state.r2,
        )
        self._history.append(frame)
        self._push_count += 1

        if self._push_count % self.print_every_n == 0:
            print(
                f"[simulation] RX={frame.rx:+.2f} RY={frame.ry:+.2f} "
                f"L2={frame.l2:.2f} R2={frame.r2:.2f}"
            )
            self._last_printed = frame

    @property
    def history(self) -> list[SimulatedFrame]:
        return list(self._history)

    @property
    def last_frame(self) -> Optional[SimulatedFrame]:
        return self._history[-1] if self._history else None
