import random
import math
from PyQt6.QtCore import QObject, QTimer, QRectF
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QRadialGradient
from typing import Optional

class GlitchSlice:
    def __init__(self) -> None:
        self.active: bool = False
        self.y: float = 0.0
        self.height: float = 0.0
        self.width: float = 0.0
        self.offset_x: float = 0.0
        self.color: QColor = QColor(0, 0, 0)
        self.opacity: float = 0.0
        self.timer: QTimer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._deactivate)

    def _deactivate(self) -> None:
        self.active = False

class MatrixChar:
    def __init__(self) -> None:
        self.x: float = 0.0
        self.y: float = 0.0
        self.speed: float = 0.0
        self.char: str = " "
        self.opacity: float = 0.0

class GlitchPainter(QObject):
    GLITCH_COLORS = [
        QColor(0xBB, 0x00, 0xFF),
        QColor(0xFF, 0x00, 0xAA),
        QColor(0x88, 0x00, 0xFF),
    ]

    ASCII_CHARS = "ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜｦﾝ0123456789ABCDEF"

    def __init__(self, parent: Optional[QObject] = None,
                 accent_color: str = "#BB00FF",
                 glitch_colors: Optional[list[str]] = None) -> None:
        super().__init__(parent)
        self._bg_color: QColor = QColor(0x05, 0x05, 0x08)
        self._scanline_color: QColor = QColor(255, 255, 255, 10)
        self._glitch_slices: list[GlitchSlice] = [GlitchSlice() for _ in range(3)]
        self._matrix_chars: list[MatrixChar] = []
        self._glitch_timer: QTimer = QTimer(self)
        self._glitch_timer.timeout.connect(self._schedule_next_glitch)
        self._accent_color: QColor = QColor(accent_color)
        self._glitch_color_list: list[QColor] = [
            QColor(c) for c in (glitch_colors or ["#BB00FF", "#FF00AA", "#8800FF"])
        ]
        self._init_matrix_chars()
        self._schedule_next_glitch()

    def _init_matrix_chars(self) -> None:
        for _ in range(60):
            mc = MatrixChar()
            mc.x = random.uniform(0, 1)
            mc.y = random.uniform(0, 1)
            mc.speed = random.uniform(0.002, 0.008)
            mc.char = random.choice(self.ASCII_CHARS)
            mc.opacity = random.uniform(0.04, 0.12)
            self._matrix_chars.append(mc)

    def _schedule_next_glitch(self) -> None:
        delay: int = random.randint(2000, 5000)
        self._glitch_timer.singleShot(delay, self._trigger_glitch)

    def _trigger_glitch(self) -> None:
        self.start_glitch()
        self._schedule_next_glitch()

    def start_glitch(self) -> None:
        count: int = random.randint(1, 3)
        for i in range(count):
            if i < len(self._glitch_slices):
                s = self._glitch_slices[i]
                s.y = random.uniform(0, 1)
                s.height = random.uniform(0.02, 0.08)
                s.width = random.uniform(0.15, 0.7)
                s.offset_x = random.uniform(-30, 30)
                s.color = random.choice(self._glitch_color_list)
                s.opacity = random.uniform(0.15, 0.3)
                s.active = True
                s.timer.start(random.randint(100, 200))

    def set_colors(self, accent_color: str,
                   glitch_colors: Optional[list[str]] = None) -> None:
        self._accent_color = QColor(accent_color)
        if glitch_colors:
            self._glitch_color_list = [QColor(c) for c in glitch_colors]

    def paint(self, painter: QPainter, width: float, height: float) -> None:
        if width < 1 or height < 1:
            return

        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.fillRect(QRectF(0, 0, width, height), self._bg_color)

        pen = QPen(self._scanline_color)
        pen.setWidth(2)
        painter.setPen(pen)
        y: float = 0.0
        while y < height:
            painter.drawLine(0, int(y), int(width), int(y))
            y += 4.0

        for s in self._glitch_slices:
            if not s.active:
                continue
            color = QColor(s.color)
            color.setAlphaF(s.opacity)
            painter.fillRect(
                int(s.offset_x) if s.offset_x >= 0 else 0,
                int(s.y * height),
                int(width * s.width),
                int(s.height * height),
                color,
            )
            accent = QColor(s.color)
            accent.setAlphaF(min(s.opacity + 0.1, 0.5))
            painter.fillRect(
                int(s.offset_x) if s.offset_x >= 0 else 0,
                int(s.y * height),
                int(width * s.width),
                2,
                accent,
            )

        gradient = QRadialGradient(width / 2.0, height / 2.0, math.hypot(width, height) * 0.55)
        gradient.setColorAt(0.0, QColor(0, 0, 0, 0))
        gradient.setColorAt(0.6, QColor(0, 0, 0, 20))
        gradient.setColorAt(1.0, QColor(0, 0, 0, 120))
        painter.fillRect(QRectF(0, 0, width, height), gradient)

        font = QFont("Courier New", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        painter.setFont(font)
        for mc in self._matrix_chars:
            mc.y += mc.speed
            if mc.y > 1.0:
                mc.y = -0.05
                mc.x = random.uniform(0, 1)
                mc.char = random.choice(self.ASCII_CHARS)
                mc.opacity = random.uniform(0.04, 0.12)
            color = QColor(self._accent_color)
            color.setAlphaF(mc.opacity)
            painter.setPen(QPen(color))
            painter.drawText(int(mc.x * width), int(mc.y * height), mc.char)
