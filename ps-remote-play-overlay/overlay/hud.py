"""
Transparent, always-on-top HUD that shows live RX/RY/L2/R2 values.

This window is frameless and click-through for the transparent regions
where possible; the text panel itself remains visible for readouts.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

import config
from controls.state import ControllerState


class HudWindow(QWidget):
    def __init__(self, state: ControllerState) -> None:
        super().__init__()
        self._state = state

        self.setWindowTitle("PS Remote Play — Axis HUD")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(config.HUD_WIDTH, config.HUD_HEIGHT)

        self._label = QLabel(self)
        self._label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        font = QFont("Cascadia Mono", 12)
        if not font.exactMatch():
            font = QFont("Consolas", 12)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self._label.setFont(font)
        self._label.setStyleSheet(
            """
            QLabel {
                color: #E8F1FF;
                background-color: rgba(12, 18, 28, 180);
                border: 1px solid rgba(120, 170, 255, 90);
                border-radius: 8px;
                padding: 10px 12px;
            }
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._label)

        self.refresh()

    def refresh(self, effective: dict[str, float] | None = None) -> None:
        """
        Update the readout.

        If *effective* is provided (baseline + keyboard overrides), show
        those values; otherwise show the raw ControllerState.
        """
        if effective is None:
            text = self._state.format_hud()
        else:
            mode = "SIM ON" if self._state.simulation_mode else "SIM OFF"
            text = (
                f"RX  {effective['rx']:+.2f}\n"
                f"RY  {effective['ry']:+.2f}\n"
                f"L2  {effective['l2']:.2f}\n"
                f"R2  {effective['r2']:.2f}\n"
                f"{mode}"
            )
        self._label.setText(text)
