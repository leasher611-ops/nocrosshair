from math import sin, cos
from PyQt6.QtCore import Qt, QTimer, QRect
from PyQt6.QtGui import QPainter, QColor, QFont, QFontDatabase, QPen, QBrush, QFontMetrics
from PyQt6.QtWidgets import QWidget, QApplication


class SplashScreen(QWidget):

    def __init__(self, on_finished=None):
        super().__init__()
        self._on_finished = on_finished
        self._progress = 0.0
        self._pulse = 0.0
        self._scan_y = 0.0
        self._glitch_offset = 0.0
        self._glitch_frame = 0
        self._phase = 0
        self._modules = [
            "CORE INIT",
            "INPUT PIPELINE",
            "PHYSICS ENGINE",
            "AIM ASSIST",
            "RECOIL CTRL",
            "OVERLAY",
            "HUD",
        ]
        self._current_module = 0
        self._typewriter = ""
        self._typewriter_target = "NOCROSSHAIR"
        self._typewriter_pos = 0
        self._fade_out = 1.0

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.SplashScreen
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")
        self.setFixedSize(520, 340)

        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(
                geo.center().x() - self.width() // 2,
                geo.center().y() - self.height() // 2,
            )

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)
        self.show()

    def _tick(self):
        self._pulse += 0.07
        self._scan_y = (self._scan_y + 1.5) % self.height()
        self._glitch_frame += 1

        if self._phase == 0:
            self._typewriter_pos = min(self._typewriter_pos + 0.15, len(self._typewriter_target))
            self._typewriter = self._typewriter_target[:int(self._typewriter_pos)]
            if self._typewriter_pos >= len(self._typewriter_target):
                self._phase = 1
                self._glitch_frame = 0

        elif self._phase == 1:
            self._progress = min(self._progress + 0.008, 1.0)
            if self._glitch_frame % 8 == 0:
                self._glitch_offset = 3 if sin(self._glitch_frame * 0.5) > 0.7 else 0
            if self._progress >= 0.3 and self._current_module < 1:
                self._current_module = 1
            if self._progress >= 0.5 and self._current_module < 2:
                self._current_module = 2
            if self._progress >= 0.7 and self._current_module < 3:
                self._current_module = 3
            if self._progress >= 0.85 and self._current_module < 4:
                self._current_module = 4
            if self._progress >= 0.95 and self._current_module < 5:
                self._current_module = 5
            if self._progress >= 0.99 and self._current_module < 6:
                self._current_module = 6
            if self._progress >= 1.0:
                self._phase = 2
                self._timer.setInterval(16)

        elif self._phase == 2:
            self._fade_out = max(0.0, self._fade_out - 0.025)
            if self._fade_out <= 0.0:
                self._timer.stop()
                self.close()
                if self._on_finished:
                    self._on_finished()
                return

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        w = self.width()
        h = self.height()
        f = self._fade_out

        painter.setBrush(QBrush(QColor(4, 6, 8, int(220 * f))))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(0, 0, w, h)

        self._draw_border(painter, w, h, f)
        self._draw_title(painter, w, f)
        self._draw_version(painter, w, f)
        self._draw_progress_bar(painter, w, f)
        self._draw_status(painter, w, f)
        self._draw_scanline(painter, w, f)
        self._draw_corners(painter, w, h, f)

        painter.end()

    def _draw_border(self, painter, w, h, f):
        pen = QPen(QColor(0, 255, 136, int(60 * f)))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(2, 2, w - 4, h - 4)

    def _draw_corners(self, painter, w, h, f):
        c = QColor(0, 255, 136, int(180 * f))
        s = 16
        pw = QPen(c, 2)
        painter.setPen(pw)
        painter.drawLine(10, 10 + s, 10, 10)
        painter.drawLine(10, 10, 10 + s, 10)
        painter.drawLine(w - 10 - s, 10, w - 10, 10)
        painter.drawLine(w - 10, 10, w - 10, 10 + s)
        painter.drawLine(10, h - 10 - s, 10, h - 10)
        painter.drawLine(10, h - 10, 10 + s, h - 10)
        painter.drawLine(w - 10 - s, h - 10, w - 10, h - 10)
        painter.drawLine(w - 10, h - 10 - s, w - 10, h - 10)

    def _draw_title(self, painter, w, f):
        font = QFont("Rajdhani", 48)
        font.setBold(True)
        painter.setFont(font)

        pulse = sin(self._pulse) * 0.15 + 0.85
        alpha = int(255 * pulse * f)
        painter.setPen(QPen(QColor(0, 255, 136, alpha)))

        if self._glitch_offset > 0 and self._phase < 2:
            r = QColor(0, 255, 136, int(60 * f))
            painter.setPen(QPen(r))
            painter.drawText(82, 145, self._typewriter)
            b = QColor(0, 200, 255, int(40 * f))
            painter.setPen(QPen(b))
            painter.drawText(78, 145, self._typewriter)

        painter.setPen(QPen(QColor(0, 255, 136, alpha)))
        painter.drawText(80, 145, self._typewriter)

        if self._phase < 2:
            cursor = "▌" if int(self._pulse * 4) % 2 == 0 else " "
            painter.setPen(QPen(QColor(0, 255, 136, alpha)))
            fm = QFontMetrics(font)
            cw = fm.horizontalAdvance(self._typewriter)
            painter.drawText(80 + cw, 145, cursor)

    def _draw_version(self, painter, w, f):
        font = QFont("JetBrains Mono", 9)
        painter.setFont(font)

        pulse = sin(self._pulse * 0.5) * 0.3 + 0.7
        painter.setPen(QPen(QColor(100, 100, 100, int(200 * pulse * f))))
        painter.drawText(82, 168, "BUILD 2.0.0-ALPHA // x86_64")

    def _draw_progress_bar(self, painter, w, f):
        bar_x = 60
        bar_y = 200
        bar_w = w - 120
        bar_h = 4

        painter.setPen(QPen(QColor(20, 40, 30, int(120 * f)), 1))
        painter.setBrush(QBrush(QColor(10, 15, 12, int(200 * f))))
        painter.drawRect(bar_x, bar_y, bar_w, bar_h)

        fill_w = int(bar_w * self._progress)
        if fill_w > 0:
            grad = QColor(0, 255, 136, int(200 * f))
            painter.setBrush(QBrush(grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(bar_x, bar_y, fill_w, bar_h)

            glow = QColor(0, 255, 136, int(30 * f))
            painter.setBrush(QBrush(glow))
            painter.drawRect(bar_x, bar_y, fill_w, bar_h + 4)

        pct = int(self._progress * 100)
        painter.setPen(QPen(QColor(0, 255, 136, int(200 * f))))
        font = QFont("JetBrains Mono", 9)
        painter.setFont(font)
        painter.drawText(bar_x + bar_w + 12, bar_y + 10, f"{pct}%")

    def _draw_status(self, painter, w, f):
        font = QFont("Rajdhani", 11)
        font.setBold(True)
        painter.setFont(font)

        status_y = 235

        if self._phase == 0:
            msg = "INITIALIZING DISPLAY..."
        elif self._phase == 1:
            idx = min(self._current_module, len(self._modules) - 1)
            msg = f"LOADING {self._modules[idx]}"
        else:
            msg = "LAUNCHING..."

        blink = int(self._pulse * 3) % 2 == 0
        suffix = "..." if blink else ""
        painter.setPen(QPen(QColor(140, 140, 140, int(200 * f))))
        painter.drawText(60, status_y, msg + suffix)

        font2 = QFont("JetBrains Mono", 8)
        painter.setFont(font2)
        painter.setPen(QPen(QColor(60, 80, 70, int(150 * f))))

        if self._phase == 1:
            total = len(self._modules)
            done = min(self._current_module, total)
            painter.drawText(60, status_y + 22,
                             f"[{done}/{total}] MODULES READY")

        painter.setPen(QPen(QColor(30, 50, 40, int(100 * f))))
        painter.drawText(60, status_y + 22, "│" * self._current_module)

    def _draw_scanline(self, painter, w, f):
        sy = int(self._scan_y)
        if sy > 0 and sy < self.height() - 4 and self._phase < 2:
            alpha = int(25 * f)
            painter.fillRect(10, sy, w - 20, 2, QColor(0, 255, 136, alpha))
