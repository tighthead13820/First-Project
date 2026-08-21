"""
Small movable control panel for right-stick and trigger testing.

Sliders write into ControllerState. The panel itself is a normal
always-on-top Tool window so you can drag it around the desktop while
PS Remote Play (or any other window) stays focused underneath / beside it.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

# Signals used by OverlayApp to open file dialogs / toggle the script host.

import config
from controls.state import ControllerState


def _slider_to_axis(slider_value: int, lo: float, hi: float) -> float:
    """Map an integer slider (0..1000) onto [lo, hi]."""
    t = slider_value / 1000.0
    return lo + t * (hi - lo)


def _axis_to_slider(axis_value: float, lo: float, hi: float) -> int:
    if hi == lo:
        return 0
    t = (axis_value - lo) / (hi - lo)
    return int(round(max(0.0, min(1.0, t)) * 1000))


class AxisSliderRow(QWidget):
    """Label + slider + numeric readout for one axis."""

    value_changed = Signal(float)

    def __init__(
        self,
        title: str,
        lo: float,
        hi: float,
        initial: float = 0.0,
        decimals: int = 2,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._lo = lo
        self._hi = hi
        self._updating = False

        self._label = QLabel(title)
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, 1000)
        self._slider.setSingleStep(1)
        self._slider.setPageStep(50)

        self._spin = QDoubleSpinBox()
        self._spin.setRange(lo, hi)
        self._spin.setDecimals(decimals)
        self._spin.setSingleStep(0.01)
        self._spin.setFixedWidth(72)

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self._label, 1)
        row.addWidget(self._slider, 4)
        row.addWidget(self._spin, 0)

        self._slider.valueChanged.connect(self._on_slider)
        self._spin.valueChanged.connect(self._on_spin)
        self.set_value(initial)

    def _on_slider(self, slider_value: int) -> None:
        if self._updating:
            return
        value = _slider_to_axis(slider_value, self._lo, self._hi)
        self._updating = True
        self._spin.setValue(value)
        self._updating = False
        self.value_changed.emit(value)

    def _on_spin(self, value: float) -> None:
        if self._updating:
            return
        self._updating = True
        self._slider.setValue(_axis_to_slider(value, self._lo, self._hi))
        self._updating = False
        self.value_changed.emit(float(value))

    def set_value(self, value: float) -> None:
        self._updating = True
        self._spin.setValue(value)
        self._slider.setValue(_axis_to_slider(value, self._lo, self._hi))
        self._updating = False

    def value(self) -> float:
        return float(self._spin.value())


class ControlPanel(QWidget):
    """Movable always-on-top panel hosting stick / trigger controls."""

    # Emitted when the user wants to load / toggle an aim script.
    request_upload_script = Signal()
    request_load_builtin = Signal()
    request_import_sandbox = Signal()
    script_enabled_changed = Signal(bool)

    def __init__(self, state: ControllerState) -> None:
        super().__init__()
        self._state = state
        self._syncing = False

        self.setWindowTitle("PS Remote Play — Control Panel")
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool
        )
        self.resize(config.PANEL_WIDTH, config.PANEL_HEIGHT)

        self._build_ui()
        self._wire_state()
        self._apply_style()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(10)

        title = QLabel("Remote Play Control Tester")
        title.setObjectName("title")
        root.addWidget(title)

        hint = QLabel(
            "Drag this panel anywhere. HUD stays on top.\n"
            "Arrows = stick · Q/E = L2/R2 · C = centre"
        )
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        root.addWidget(hint)

        stick_box = QGroupBox("Right stick")
        stick_layout = QVBoxLayout(stick_box)
        self.rx_row = AxisSliderRow("X", *config.RX_RANGE, initial=0.0)
        self.ry_row = AxisSliderRow("Y", *config.RY_RANGE, initial=0.0)
        stick_layout.addWidget(self.rx_row)
        stick_layout.addWidget(self.ry_row)

        reset_btn = QPushButton("Reset to centre")
        reset_btn.clicked.connect(self._reset_stick)
        stick_layout.addWidget(reset_btn)
        root.addWidget(stick_box)

        trigger_box = QGroupBox("Triggers")
        trigger_layout = QVBoxLayout(trigger_box)
        self.l2_row = AxisSliderRow("L2", *config.TRIGGER_RANGE, initial=0.0)
        self.r2_row = AxisSliderRow("R2", *config.TRIGGER_RANGE, initial=0.0)
        trigger_layout.addWidget(self.l2_row)
        trigger_layout.addWidget(self.r2_row)
        root.addWidget(trigger_box)

        sim_box = QGroupBox("Output")
        sim_layout = QFormLayout(sim_box)
        self.sim_check = QCheckBox("Simulation mode (send controller output)")
        self.sim_check.setChecked(self._state.simulation_mode)
        self.backend_label = QLabel("backend: —")
        self.backend_label.setObjectName("hint")
        sim_layout.addRow(self.sim_check)
        sim_layout.addRow(self.backend_label)
        root.addWidget(sim_box)

        script_box = QGroupBox("Aim script")
        script_layout = QVBoxLayout(script_box)
        self.script_check = QCheckBox("Drive stick from loaded script")
        script_layout.addWidget(self.script_check)

        btn_row = QHBoxLayout()
        self.upload_btn = QPushButton("Upload .py…")
        self.builtin_btn = QPushButton("Load sandbox")
        self.import_btn = QPushButton("Import folder…")
        self.upload_btn.setToolTip("Copy a Python aim script into scripts/uploaded/ and load it")
        self.builtin_btn.setToolTip(
            "Load the bundled Python port of vendor/aim-assist-sandbox/js/aimAssist.js"
        )
        self.import_btn.setToolTip(
            "Point at an aim-assist-sandbox folder (must contain js/aimAssist.js)"
        )
        btn_row.addWidget(self.upload_btn)
        btn_row.addWidget(self.builtin_btn)
        btn_row.addWidget(self.import_btn)
        script_layout.addLayout(btn_row)

        self.script_status = QLabel("script: (none)")
        self.script_status.setObjectName("hint")
        self.script_status.setWordWrap(True)
        script_layout.addWidget(self.script_status)

        self.script_debug = QLabel("")
        self.script_debug.setObjectName("live")
        self.script_debug.setWordWrap(True)
        self.script_debug.setMinimumHeight(72)
        self.script_debug.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        script_layout.addWidget(self.script_debug)
        root.addWidget(script_box)

        self.live_label = QLabel()
        self.live_label.setObjectName("live")
        self.live_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        root.addWidget(self.live_label)

        root.addStretch(1)

    def _wire_state(self) -> None:
        self.rx_row.value_changed.connect(self._on_rx)
        self.ry_row.value_changed.connect(self._on_ry)
        self.l2_row.value_changed.connect(self._on_l2)
        self.r2_row.value_changed.connect(self._on_r2)
        self.sim_check.toggled.connect(self._on_sim_toggled)
        self.script_check.toggled.connect(self._on_script_toggled)
        self.upload_btn.clicked.connect(self.request_upload_script.emit)
        self.builtin_btn.clicked.connect(self.request_load_builtin.emit)
        self.import_btn.clicked.connect(self.request_import_sandbox.emit)
        self._state.subscribe(self._on_state_changed)
        self._refresh_live(self._state)

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QWidget {
                background-color: #121820;
                color: #E6EEF8;
                font-family: "Segoe UI", "Cascadia Text", sans-serif;
                font-size: 12px;
            }
            QLabel#title {
                font-size: 15px;
                font-weight: 600;
                color: #F2F7FF;
            }
            QLabel#hint { color: #8FA3BB; font-size: 11px; }
            QLabel#live {
                font-family: "Cascadia Mono", "Consolas", monospace;
                font-size: 12px;
                padding: 8px;
                background: #0C121C;
                border: 1px solid #2A3A50;
                border-radius: 6px;
            }
            QGroupBox {
                border: 1px solid #2A3A50;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
                color: #A8C4E8;
            }
            QPushButton {
                background: #1E2A3A;
                border: 1px solid #3A516E;
                border-radius: 4px;
                padding: 6px 10px;
            }
            QPushButton:hover { background: #273649; }
            QPushButton:pressed { background: #1A2430; }
            QSlider::groove:horizontal {
                height: 6px;
                background: #1A2430;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                width: 14px;
                margin: -5px 0;
                background: #6EA8FF;
                border-radius: 7px;
            }
            QCheckBox { spacing: 8px; }
            """
        )

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------
    def _on_rx(self, value: float) -> None:
        if self._syncing:
            return
        self._state.set_rx(value)

    def _on_ry(self, value: float) -> None:
        if self._syncing:
            return
        self._state.set_ry(value)

    def _on_l2(self, value: float) -> None:
        if self._syncing:
            return
        self._state.set_l2(value)

    def _on_r2(self, value: float) -> None:
        if self._syncing:
            return
        self._state.set_r2(value)

    def _on_sim_toggled(self, checked: bool) -> None:
        if self._syncing:
            return
        self._state.set_simulation_mode(checked)

    def _on_script_toggled(self, checked: bool) -> None:
        if self._syncing:
            return
        self.script_enabled_changed.emit(checked)

    def _reset_stick(self) -> None:
        self._state.reset_right_stick()

    def set_script_status(self, text: str) -> None:
        self.script_status.setText(text)

    def set_script_debug(self, text: str) -> None:
        self.script_debug.setText(text or "")

    def set_script_enabled(self, enabled: bool) -> None:
        self._syncing = True
        self.script_check.setChecked(enabled)
        self._syncing = False

    def _on_state_changed(self, state: ControllerState) -> None:
        self._syncing = True
        self.rx_row.set_value(state.rx)
        self.ry_row.set_value(state.ry)
        self.l2_row.set_value(state.l2)
        self.r2_row.set_value(state.r2)
        self.sim_check.setChecked(state.simulation_mode)
        self._syncing = False
        self._refresh_live(state)

    def _refresh_live(self, state: ControllerState) -> None:
        self.live_label.setText(state.format_hud())

    def set_backend_name(self, name: str) -> None:
        self.backend_label.setText(f"backend: {name}")

    def show_effective(self, effective: dict[str, float]) -> None:
        """Update the live readout with merged (slider + shortcut) values."""
        mode = "SIM ON" if self._state.simulation_mode else "SIM OFF"
        self.live_label.setText(
            f"RX  {effective['rx']:+.2f}\n"
            f"RY  {effective['ry']:+.2f}\n"
            f"L2  {effective['l2']:.2f}\n"
            f"R2  {effective['r2']:.2f}\n"
            f"{mode}"
        )
