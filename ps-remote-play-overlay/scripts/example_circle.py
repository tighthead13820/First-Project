"""
Example user aim script you can Upload via the control panel.

Copies the same contract as scripts/builtin_sandbox_aim.py but always
pushes a gentle circular stick motion — useful to verify upload → drive
without depending on the mock target scene.
"""

from __future__ import annotations

import math

from scripts.api import AimFrame, StickCommand


class Script:
    name = "example-circle"

    def __init__(self) -> None:
        self._t = 0.0

    def reset(self) -> None:
        self._t = 0.0

    def update(self, frame: AimFrame) -> StickCommand:
        self._t += frame.dt
        rx = math.sin(self._t) * 0.35
        ry = math.cos(self._t) * 0.35
        return StickCommand(
            rx=rx,
            ry=ry,
            debug=f"example-circle RX={rx:+.2f} RY={ry:+.2f}",
        )


def create_script() -> Script:
    return Script()
