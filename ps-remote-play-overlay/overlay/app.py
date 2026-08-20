"""
Application shell: wires state, panel, HUD, keyboard, and backend.

Run via ``python main.py`` from the project root.
"""

from __future__ import annotations

import sys
from typing import Optional

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

import config
from backend import VirtualControllerBackend, create_backend
from controls.keyboard import KeyboardController
from controls.state import ControllerState, merge_held_overrides
from overlay.hud import HudWindow
from overlay.panel import ControlPanel


class OverlayApp:
    """Owns the Qt application lifetime and the tick loop."""

    def __init__(
        self,
        backend: Optional[VirtualControllerBackend] = None,
        backend_kind: str = "simulation",
    ) -> None:
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.app.setApplicationName("PS Remote Play Control Overlay")
        self.app.setQuitOnLastWindowClosed(True)

        self.state = ControllerState()
        self.backend = backend or create_backend(backend_kind)

        self.panel = ControlPanel(self.state)
        self.hud = HudWindow(self.state)
        self.panel.set_backend_name(self.backend.describe())

        self.keyboard = KeyboardController(
            self.state,
            on_override_changed=self._on_override_changed,
        )
        self.keyboard.install(self.app)

        # Working copy used when keyboard overrides are active so we can
        # push merged axes without permanently mutating slider baselines.
        self._effective = ControllerState()
        self._tick = QTimer()
        self._tick.setInterval(config.UI_TICK_MS)
        self._tick.timeout.connect(self._on_tick)

    def _merged_axes(self) -> dict[str, float]:
        return merge_held_overrides(self.state, self.keyboard.active_overrides())

    def _on_override_changed(self) -> None:
        # Immediate visual feedback when a shortcut is pressed/released.
        effective = self._merged_axes()
        self.hud.refresh(effective)
        self.panel.show_effective(effective)

    def _on_tick(self) -> None:
        effective = self._merged_axes()
        self._effective.rx = effective["rx"]
        self._effective.ry = effective["ry"]
        self._effective.l2 = effective["l2"]
        self._effective.r2 = effective["r2"]
        self._effective.simulation_mode = self.state.simulation_mode

        self.hud.refresh(effective)
        # Only rewrite the panel live label when shortcuts are held so
        # we do not fight the slider-driven subscribe path otherwise.
        if self.keyboard.active_overrides():
            self.panel.show_effective(effective)

        self.backend.push(self._effective)

    def run(self) -> int:
        self.backend.connect()
        self.panel.show()
        self.hud.show()

        # Place HUD near the top-right of the primary screen.
        screen = self.app.primaryScreen()
        if screen is not None:
            geo = screen.availableGeometry()
            self.hud.move(geo.right() - self.hud.width() - 24, geo.top() + 24)
            self.panel.move(geo.left() + 40, geo.top() + 80)

        self._tick.start()
        try:
            code = self.app.exec()
        finally:
            self._tick.stop()
            self.backend.disconnect()
        return int(code)


def run(backend_kind: str = "simulation") -> int:
    """Public entry used by main.py and tests."""
    return OverlayApp(backend_kind=backend_kind).run()
