from math import sin, cos, pi, radians
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont
from PyQt6.QtWidgets import QWidget


class CrosshairPreview(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 200)
        self._config = self._default_config()

    def _default_config(self):
        return {
            "crosshair_type": "Cross",
            "color": "#00ff88",
            "size": 20,
            "thick": 3,
            "gap": 4,
            "outline": True,
            "alpha": 1.0,
        }

    def update_config(self, config: dict):
        self._config = config
        self.update()

    _STYLE_MAP = {
        "cruz": "Cross",
        "ponto": "Dot",
        "círculo": "Circle",
        "cruz+ponto": "Cross",
        "círculo+ponto": "Crosshair",
        "estilo T": "Cross",
        "mira em x": "Cross",
        "losango": "Cross",
        "ângulos": "Cross",
        "scope": "Crosshair",
    }

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        cx = w // 2
        cy = h // 2

        painter.fillRect(0, 0, w, h, QColor(12, 26, 46))

        pen = QPen(QColor(37, 51, 79))
        pen.setWidth(1)
        painter.setPen(pen)

        for i in range(0, w, 20):
            painter.drawLine(i, 0, i, h)
        for i in range(0, h, 20):
            painter.drawLine(0, i, w, i)

        pen2 = QPen(QColor(18, 38, 60))
        pen2.setWidth(1)
        painter.setPen(pen2)
        painter.drawLine(cx, 0, cx, h)
        painter.drawLine(0, cy, w, cy)

        cfg = self._config
        raw_style = cfg.get("style", "cruz")
        cross_type = self._STYLE_MAP.get(raw_style, "Cross")
        color_hex = cfg.get("color", "#00ff88")
        color = QColor(color_hex)
        size = cfg.get("size", 20)
        thick = cfg.get("thick", 3)
        gap = cfg.get("gap", 4)
        outline = cfg.get("outline", True)
        alpha = cfg.get("alpha", 1.0)
        color.setAlphaF(alpha)

        if outline:
            self._draw_cross(painter, cx, cy, cross_type, size + 1, thick + 2, gap, QColor(0, 0, 0, 180))

        self._draw_cross(painter, cx, cy, cross_type, size, thick, gap, color)

        circle_pen = QPen(QColor(20, 40, 60, 80))
        circle_pen.setWidth(1)
        painter.setPen(circle_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(cx - size - gap, cy - size - gap, 2 * (size + gap), 2 * (size + gap))

        font = QFont("Consolas", 7)
        painter.setFont(font)
        painter.setPen(QColor(96, 115, 100))
        painter.drawText(6, h - 6, f"W:{w} H:{h}")

    def _draw_cross(self, painter, cx, cy, cross_type, size, thick, gap, color):
        pen = QPen(color)
        pen.setWidth(thick)
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        hs = size // 2
        hg = gap

        if cross_type == "Cross":
            painter.drawLine(cx - hs - hg, cy, cx - hg, cy)
            painter.drawLine(cx + hg, cy, cx + hs + hg, cy)
            painter.drawLine(cx, cy - hs - hg, cx, cy - hg)
            painter.drawLine(cx, cy + hg, cx, cy + hs + hg)

        elif cross_type == "Circle":
            r = hs + hg
            painter.drawEllipse(cx - r, cy - r, 2 * r, 2 * r)
            painter.drawPoint(cx, cy)

        elif cross_type == "Dot":
            painter.setBrush(QBrush(color))
            painter.drawEllipse(cx - hs, cy - hs, 2 * hs, 2 * hs)

        elif cross_type == "Crosshair":
            r = hs + hg
            painter.drawEllipse(cx - r, cy - r, 2 * r, 2 * r)
            painter.drawLine(cx - hs - hg, cy, cx - hg, cy)
            painter.drawLine(cx + hg, cy, cx + hs + hg, cy)
            painter.drawLine(cx, cy - hs - hg, cx, cy - hg)
            painter.drawLine(cx, cy + hg, cx, cy + hs + hg)

        elif cross_type == "Triangle":
            r = hs + hg
            pts = [
                (cx, cy - r),
                (cx - int(r * 0.866), cy + r // 2),
                (cx + int(r * 0.866), cy + r // 2),
            ]
            painter.drawLine(pts[0][0], pts[0][1], pts[1][0], pts[1][1])
            painter.drawLine(pts[1][0], pts[1][1], pts[2][0], pts[2][1])
            painter.drawLine(pts[2][0], pts[2][1], pts[0][0], pts[0][1])
