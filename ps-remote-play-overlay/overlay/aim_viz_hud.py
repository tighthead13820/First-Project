"""
Full-screen translucent aim HUD — crosshair, targets, FOV, trail.

Drawn over the desktop; position/size syncs to primary screen when shown.
"""

from __future__ import annotations

from typing import Deque, Optional

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from pipeline.live_engine import LivePipelineState


class AimVisualizationHud(QWidget):
    """Transparent overlay for live aim debug visualization."""

    def __init__(self) -> None:
        super().__init__()
        self._state: Optional[LivePipelineState] = None
        self._fov_radius_px: float = 120.0

        self.setWindowTitle("Aim Visualization HUD")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def set_pipeline_state(
        self, state: LivePipelineState, fov_radius_px: float = 120.0
    ) -> None:
        self._state = state
        self._fov_radius_px = fov_radius_px
        self.update()

    def resize_to_screen(self, width: int, height: int, x: int = 0, y: int = 0) -> None:
        self.setGeometry(x, y, width, height)

    def paintEvent(self, event) -> None:  # noqa: N802
        if self._state is None:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        s = self._state
        cx, cy = s.centre_x, s.centre_y

        # FOV perimeter
        pen_fov = QPen(QColor(100, 160, 255, 90))
        pen_fov.setWidth(2)
        p.setPen(pen_fov)
        p.setBrush(QColor(100, 160, 255, 25))
        r = self._fov_radius_px
        p.drawEllipse(QPointF(cx, cy), r, r)

        # Crosshair at screen centre
        pen_cross = QPen(QColor(255, 255, 255, 200))
        pen_cross.setWidth(2)
        p.setPen(pen_cross)
        size = 14
        p.drawLine(int(cx - size), int(cy), int(cx + size), int(cy))
        p.drawLine(int(cx), int(cy - size), int(cx), int(cy + size))
        p.drawEllipse(QPointF(cx, cy), 3, 3)

        # Trail
        trail: Deque[tuple[float, float]] = s.trail
        if len(trail) > 1:
            pen_trail = QPen(QColor(255, 200, 80, 120))
            pen_trail.setWidth(2)
            p.setPen(pen_trail)
            pts = list(trail)
            for i in range(1, len(pts)):
                x0, y0 = pts[i - 1]
                x1, y1 = pts[i]
                alpha = int(40 + (i / len(pts)) * 180)
                pen_trail.setColor(QColor(255, 200, 80, alpha))
                p.setPen(pen_trail)
                p.drawLine(int(x0), int(y0), int(x1), int(y1))

        # Selected target
        if s.selected_target_id and s.target_x > -9000:
            tx, ty = s.target_x, s.target_y
            # Line crosshair → target
            pen_line = QPen(QColor(80, 255, 120, 180))
            pen_line.setWidth(2)
            p.setPen(pen_line)
            p.drawLine(int(cx), int(cy), int(tx), int(ty))

            # Head marker
            p.setPen(QPen(QColor(80, 255, 120, 255), 3))
            p.setBrush(QColor(80, 255, 120, 60))
            p.drawEllipse(QPointF(tx, ty), 10, 10)

            # Target ID label
            font = QFont("Consolas", 10)
            p.setFont(font)
            p.setPen(QColor(200, 255, 220, 230))
            p.drawText(int(tx + 14), int(ty - 8), str(s.selected_target_id))

            # Live errors near target
            err_text = (
                f"Δpx {s.pixel_error_x:+.0f},{s.pixel_error_y:+.0f}  "
                f"∠ {s.yaw_error_deg:+.1f}°,{s.pitch_error_deg:+.1f}°"
            )
            p.drawText(int(tx + 14), int(ty + 10), err_text)

        p.end()
