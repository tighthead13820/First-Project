"""
Application shell: wires state, panel, HUD, keyboard, backend, and scripts.

Run via ``python main.py`` from the project root.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

import config
from aimbridge.host import ScriptHost, ScriptLoadError
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
        self.scripts = ScriptHost(self.state)

        self.panel = ControlPanel(self.state)
        self.hud = HudWindow(self.state)
        self.panel.set_backend_name(self.backend.describe())
        self.panel.set_script_status("script: (none) — Load sandbox or Upload .py")

        self.keyboard = KeyboardController(
            self.state,
            on_override_changed=self._on_override_changed,
        )
        self.keyboard.install(self.app)

        self._wire_script_ui()

        # Working copy used when keyboard overrides are active so we can
        # push merged axes without permanently mutating slider baselines.
        self._effective = ControllerState()
        self._tick = QTimer()
        self._tick.setInterval(config.UI_TICK_MS)
        self._tick.timeout.connect(self._on_tick)

    def _wire_script_ui(self) -> None:
        self.panel.request_upload_script.connect(self._on_upload_script)
        self.panel.request_load_builtin.connect(self._on_load_builtin)
        self.panel.request_import_sandbox.connect(self._on_import_sandbox)
        self.panel.script_enabled_changed.connect(self._on_script_enabled)

    def _on_upload_script(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self.panel,
            "Upload aim script",
            str(Path.cwd()),
            "Python scripts (*.py)",
        )
        if not path:
            return
        try:
            msg = self.scripts.upload(Path(path))
        except ScriptLoadError as exc:
            QMessageBox.warning(self.panel, "Upload failed", str(exc))
            return
        self._refresh_script_labels(msg)

    def _on_load_builtin(self) -> None:
        try:
            msg = self.scripts.load_builtin()
        except ScriptLoadError as exc:
            QMessageBox.warning(self.panel, "Load failed", str(exc))
            return
        self._refresh_script_labels(msg)

    def _on_import_sandbox(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self.panel,
            "Select aim-assist-sandbox folder",
            str(Path.cwd()),
        )
        if not folder:
            return
        try:
            msg = self.scripts.import_sandbox(Path(folder))
        except ScriptLoadError as exc:
            QMessageBox.warning(self.panel, "Import failed", str(exc))
            return
        self._refresh_script_labels(msg)

    def _on_script_enabled(self, enabled: bool) -> None:
        try:
            self.scripts.set_enabled(enabled)
        except ScriptLoadError as exc:
            self.panel.set_script_enabled(False)
            QMessageBox.warning(self.panel, "Script enable failed", str(exc))
            return
        # When script drives the stick, keyboard stick overrides stay useful
        # as a manual override layer on top.
        status = (
            f"script: {self.scripts.script_name} "
            f"[{'ON' if self.scripts.enabled else 'OFF'}]"
        )
        if self.scripts.source_path:
            status += f"\n{self.scripts.source_path}"
        self.panel.set_script_status(status)
        self.panel.set_script_debug(self.scripts.last_debug)

    def _refresh_script_labels(self, msg: str) -> None:
        status = (
            f"script: {self.scripts.script_name} "
            f"[{'ON' if self.scripts.enabled else 'OFF'}]"
        )
        if self.scripts.source_path:
            status += f"\n{self.scripts.source_path}"
        self.panel.set_script_status(status)
        self.panel.set_script_debug(msg)

    def _merged_axes(self) -> dict[str, float]:
        return merge_held_overrides(self.state, self.keyboard.active_overrides())

    def _on_override_changed(self) -> None:
        # Immediate visual feedback when a shortcut is pressed/released.
        effective = self._merged_axes()
        self.hud.refresh(effective)
        self.panel.show_effective(effective)

    def _on_tick(self) -> None:
        dt = config.UI_TICK_MS / 1000.0
        self.scripts.tick(dt)
        if self.scripts.enabled:
            self.panel.set_script_debug(self.scripts.last_debug)

        effective = self._merged_axes()
        self._effective.rx = effective["rx"]
        self._effective.ry = effective["ry"]
        self._effective.l2 = effective["l2"]
        self._effective.r2 = effective["r2"]
        self._effective.simulation_mode = self.state.simulation_mode

        self.hud.refresh(effective)
        # Rewrite panel live label when shortcuts or script are active.
        if self.keyboard.active_overrides() or self.scripts.enabled:
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
            self.panel.move(geo.left() + 40, geo.top() + 40)

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
