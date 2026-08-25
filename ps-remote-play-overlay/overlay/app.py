"""
Application shell: wires state, panel, HUD, keyboard, backend, scripts,
and the live aim_core production pipeline.

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
from backend.base import BackendError
from controller_hardware import RealControllerHardware
from controls.keyboard import KeyboardController
from controls.state import ControllerState, merge_held_overrides
from overlay.aim_viz_hud import AimVisualizationHud
from overlay.hud import HudWindow
from overlay.panel import ControlPanel
from pipeline.live_engine import LiveAimPipeline
from sources.mock_screen_source import MockScreenTargetSource
from sources.world_mock_source import WorldMockTargetSource


class OverlayApp:
    """Owns the Qt application lifetime and the tick loop."""

    def __init__(
        self,
        backend: Optional[VirtualControllerBackend] = None,
        backend_kind: str = "simulation",
        target_source_kind: str = "mock-screen",
        controller_hardware: Optional[RealControllerHardware] = None,
    ) -> None:
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.app.setApplicationName("PS Remote Play Control Overlay")
        self.app.setQuitOnLastWindowClosed(True)

        self.state = ControllerState()
        self._controller_hw = controller_hardware
        try:
            self.backend = backend or create_backend(
                backend_kind, hardware=self._controller_hw
            )
        except BackendError as exc:
            print(f"[backend] {exc}")
            self.backend = create_backend("simulation")
        self.backend_kind = backend_kind

        source = (
            WorldMockTargetSource()
            if target_source_kind == "mock-world"
            else MockScreenTargetSource()
        )
        self.live = LiveAimPipeline(state=self.state, target_source=source)
        self.live.mode = "screen" if target_source_kind == "mock-screen" else "world"

        self.scripts = ScriptHost(self.state)

        self.panel = ControlPanel(self.state)
        self.hud = HudWindow(self.state)
        self.aim_viz = AimVisualizationHud()
        self.panel.set_backend_name(self.backend.describe())
        self.panel.set_script_status("script: (none) — Load sandbox or Upload .py")
        self.panel.set_aim_dashboard("Aim Core: OFF")

        self.keyboard = KeyboardController(
            self.state,
            on_override_changed=self._on_override_changed,
        )
        self.keyboard.install(self.app)

        self._wire_ui()

        self._effective = ControllerState()
        self._tick = QTimer()
        self._tick.setInterval(config.UI_TICK_MS)
        self._tick.timeout.connect(self._on_tick)
        self._hardware_connected = False

    def _wire_ui(self) -> None:
        self.panel.request_upload_script.connect(self._on_upload_script)
        self.panel.request_load_builtin.connect(self._on_load_builtin)
        self.panel.request_import_sandbox.connect(self._on_import_sandbox)
        self.panel.script_enabled_changed.connect(self._on_script_enabled)
        self.panel.fire_options_changed.connect(self._on_fire_options)
        self.panel.aim_core_enabled_changed.connect(self._on_aim_core_enabled)
        self.panel.aim_core_options_changed.connect(self._sync_aim_core_options)

    def _screen_geometry(self):
        screen = self.app.primaryScreen()
        if screen is None:
            return 0, 0, 1920, 1080
        geo = screen.geometry()
        return geo.x(), geo.y(), geo.width(), geo.height()

    def _sync_aim_core_options(self) -> None:
        opts = self.panel.aim_core_option_values()
        fire = self.panel.fire_option_values()
        self.live.configure_from_panel(
            snap_mode=bool(opts["snap_mode"]),
            prediction=bool(opts["prediction"]),
            response_speed=float(opts["response_speed"]),
            target_bone="head",
            auto_l2=bool(fire["auto_fire_l2"]),
            auto_r2=bool(fire["auto_fire_r2"]),
            recoil_compensate=bool(fire["recoil_compensate"]),
            recoil_vertical=float(fire["recoil_vertical"]),
            recoil_horizontal=float(fire["recoil_horizontal"]),
        )
        if not opts["show_viz"]:
            self.aim_viz.hide()
        elif self.live.enabled:
            self.aim_viz.show()

    def _ensure_controller_hardware(self) -> RealControllerHardware:
        """Lazy-init the production VDS4 driver (Aim Core LIVE hook)."""
        if self._controller_hw is None:
            self._controller_hw = RealControllerHardware()
        return self._controller_hw

    def _on_aim_core_enabled(self, enabled: bool) -> None:
        if enabled and self.panel.script_check.isChecked():
            self.panel.set_script_enabled(False)
            self.scripts.set_enabled(False)
        if enabled:
            hw = self._ensure_controller_hardware()
            if not hw.enabled:
                self.panel.aim_core_check.setChecked(False)
                QMessageBox.warning(
                    self.panel,
                    "Controller hardware unavailable",
                    "Could not register Virtual DualShock 4.\n\n"
                    "Install ViGEmBus and run: pip install vgamepad\n"
                    "Then restart with: python main.py --backend vigem --live",
                )
                return
            # Re-bind backend so push() routes through RealControllerHardware
            if self.backend_kind.startswith("vigem"):
                from backend.controller_hardware_backend import (
                    ControllerHardwareBackend,
                )

                if not isinstance(self.backend, ControllerHardwareBackend):
                    try:
                        self.backend.disconnect()
                    except Exception:
                        pass
                    self.backend = ControllerHardwareBackend(hardware=hw)
                    try:
                        self.backend.connect()
                        self._hardware_connected = True
                    except BackendError as exc:
                        self._hardware_connected = False
                        QMessageBox.warning(
                            self.panel, "Backend connect failed", str(exc)
                        )
                self.panel.set_backend_name(self.backend.describe())
            if not self.state.simulation_mode:
                self.panel.sim_check.setChecked(True)
                self.state.set_simulation_mode(True)
        self.live.set_enabled(enabled)
        self._sync_aim_core_options()
        sx, sy, sw, sh = self._screen_geometry()
        self.live.sync_screen_size(sw, sh)
        self.live.dashboard.centre_x = sw / 2
        self.live.dashboard.centre_y = sh / 2
        if enabled:
            opts = self.panel.aim_core_option_values()
            if opts["show_viz"]:
                self.aim_viz.resize_to_screen(sw, sh, sx, sy)
                self.aim_viz.show()
        else:
            self.aim_viz.hide()
        self.panel.set_aim_dashboard(self.live.format_dashboard())

    def _on_fire_options(self) -> None:
        self._sync_fire_options_to_script()
        self._sync_aim_core_options()

    def _sync_fire_options_to_script(self) -> None:
        opts = self.panel.fire_option_values()
        self.scripts.apply_fire_options(
            auto_fire_l2=bool(opts["auto_fire_l2"]),
            auto_fire_r2=bool(opts["auto_fire_r2"]),
            recoil_compensate=bool(opts["recoil_compensate"]),
            recoil_vertical=float(opts["recoil_vertical"]),
            recoil_horizontal=float(opts["recoil_horizontal"]),
        )

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
        self._sync_fire_options_to_script()
        self._refresh_script_labels(msg)

    def _on_load_builtin(self) -> None:
        try:
            msg = self.scripts.load_builtin()
        except ScriptLoadError as exc:
            QMessageBox.warning(self.panel, "Load failed", str(exc))
            return
        self._sync_fire_options_to_script()
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
        self._sync_fire_options_to_script()
        self._refresh_script_labels(msg)

    def _on_script_enabled(self, enabled: bool) -> None:
        if enabled and self.panel.aim_core_check.isChecked():
            self.panel.aim_core_check.setChecked(False)
            self.live.set_enabled(False)
        try:
            self.scripts.set_enabled(enabled)
            self._sync_fire_options_to_script()
        except ScriptLoadError as exc:
            self.panel.set_script_enabled(False)
            QMessageBox.warning(self.panel, "Script enable failed", str(exc))
            return
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
        effective = self._merged_axes()
        self.hud.refresh(effective)
        self.panel.show_effective(effective)

    def _hardware_armed(self) -> bool:
        return self.state.simulation_mode and self._hardware_connected

    def _on_tick(self) -> None:
        dt = config.UI_TICK_MS / 1000.0
        armed = self._hardware_armed()

        if self.live.enabled:
            self.live.tick(
                dt,
                hardware_connected=self._hardware_connected,
                hardware_armed=armed,
            )
            self.panel.set_aim_dashboard(self.live.format_dashboard())
            self.aim_viz.set_pipeline_state(self.live.dashboard)
            hw_line = (
                "VGAMEPAD HARDWARE BUS: CONNECTED & ARMED"
                if armed
                else "VGAMEPAD HARDWARE BUS: DISCONNECTED / NOT ARMED"
            )
            self.panel.set_hardware_status(hw_line, armed)
        elif self.scripts.enabled:
            self.scripts.tick(dt)
            self.panel.set_script_debug(self.scripts.last_debug)

        effective = self._merged_axes()
        self._effective.rx = effective["rx"]
        self._effective.ry = effective["ry"]
        self._effective.l2 = effective["l2"]
        self._effective.r2 = effective["r2"]
        self._effective.simulation_mode = self.state.simulation_mode

        self.hud.refresh(effective)
        if (
            self.keyboard.active_overrides()
            or self.scripts.enabled
            or self.live.enabled
        ):
            self.panel.show_effective(effective)

        self.backend.push(self._effective)

    def run(self) -> int:
        try:
            self.backend.connect()
            self._hardware_connected = True
        except BackendError as exc:
            self._hardware_connected = False
            QMessageBox.warning(
                self.panel,
                "Backend connect failed",
                f"{exc}\n\nFalling back to UI-only mode.",
            )

        self.panel.show()
        self.hud.show()

        sx, sy, sw, sh = self._screen_geometry()
        self.live.sync_screen_size(sw, sh)
        self.hud.move(sx + sw - self.hud.width() - 24, sy + 24)
        self.panel.move(sx + 40, sy + 40)

        self._tick.start()
        try:
            code = self.app.exec()
        finally:
            self._tick.stop()
            self.backend.disconnect()
            self._hardware_connected = False
        return int(code)


def run(
    backend_kind: str = "simulation",
    target_source_kind: str = "mock-screen",
    controller_hardware: Optional[RealControllerHardware] = None,
) -> int:
    """Public entry used by main.py and tests."""
    return OverlayApp(
        backend_kind=backend_kind,
        target_source_kind=target_source_kind,
        controller_hardware=controller_hardware,
    ).run()
