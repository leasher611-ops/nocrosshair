#!/usr/bin/env python3

import math
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath, QFont


class RecoilCurvePreview(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(220, 180)
        self.setMaximumSize(300, 240)
        self._curve_type = "ease_out"
        self._strength = 65
        self._ticks = 60

    def update_curve(self, curve_type: str, strength: int, ticks: int) -> None:
        self._curve_type = curve_type
        self._strength = strength
        self._ticks = ticks
        self.update()

    def _eval_curve(self, t: float) -> float:
        if self._curve_type == "linear":
            return t
        if self._curve_type == "ease_in":
            return t * t
        return 1.0 - (1.0 - t) * (1.0 - t)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        painter.fillRect(0, 0, w, h, QColor("#1a1a2e"))

        pad_l, pad_r, pad_t, pad_b = 30, 15, 20, 25
        gw = w - pad_l - pad_r
        gh = h - pad_t - pad_b

        painter.setPen(QPen(QColor("#333333"), 1, Qt.PenStyle.SolidLine))
        for i in range(1, 5):
            x = pad_l + int(gw * i / 5)
            painter.drawLine(x, pad_t, x, h - pad_b)
        for i in range(1, 4):
            y = pad_t + int(gh * i / 4)
            painter.drawLine(pad_l, y, w - pad_r, y)

        painter.setPen(QPen(QColor("#555555"), 1))
        painter.drawLine(pad_l, pad_t, pad_l, h - pad_b)
        painter.drawLine(pad_l, h - pad_b, w - pad_r, h - pad_b)

        painter.setPen(QPen(QColor("#666666")))
        painter.setFont(QFont("monospace", 7))
        painter.drawText(2, pad_t + 8, f"{self._strength}")
        painter.drawText(pad_l + gw // 2 - 5, h - 6, f"{self._ticks}t")

        if self._strength == 0:
            painter.end()
            return

        max_y = self._strength * 90
        path = QPainterPath()
        first = True
        for i in range(61):
            t = i / 60.0
            y_norm = self._eval_curve(t)
            px = pad_l + int(t * gw)
            py = h - pad_b - int(y_norm * gh)
            if first:
                path.moveTo(QPointF(px, py))
                first = False
            else:
                path.lineTo(QPointF(px, py))

        curve_color = QColor("#00ff88")
        painter.setPen(QPen(curve_color, 2, Qt.PenStyle.SolidLine))
        painter.drawPath(path)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(0, 255, 136, 30)))
        fill_path = QPainterPath(path)
        fill_path.lineTo(QPointF(pad_l + gw, h - pad_b))
        fill_path.lineTo(QPointF(pad_l, h - pad_b))
        fill_path.closeSubpath()
        painter.drawPath(fill_path)

        painter.setPen(QPen(curve_color, 1, Qt.PenStyle.NoPen))
        painter.setBrush(QBrush(curve_color))
        for i in range(0, 61, 12):
            t = i / 60.0
            y_norm = self._eval_curve(t)
            px = pad_l + int(t * gw)
            py = h - pad_b - int(y_norm * gh)
            painter.drawEllipse(QPointF(px, py), 3, 3)

        painter.end()
