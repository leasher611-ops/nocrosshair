from math import sin, cos, pi
from PyQt6.QtCore import Qt, QTimer, QElapsedTimer
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QFontDatabase
from PyQt6.QtWidgets import QWidget


class StatusHUD(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active = False
        self._device_name = "--"
        self._aa_enabled = False
        self._recoil_enabled = False
        self._fps = 0
        self._uptime_secs = 0
        self._pulse = 0.0
        self._scanline_y = -10.0
        self._scan_direction = 1

        self._runtime = None

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setStyleSheet("background: transparent;")
        self.setFixedSize(260, 160)

        screen = self.screen()
        if screen:
            geo = screen.availableGeometry()
            self.move(geo.width() - 280, 20)

        self._elapsed = QElapsedTimer()
        self._elapsed.start()

        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._animate)
        self._anim_timer.start(33)

        self._data_timer = QTimer(self)
        self._data_timer.timeout.connect(self._refresh_data)
        self._data_timer.start(250)

    def set_runtime(self, runtime) -> None:
        self._runtime = runtime

    def set_config(self, config) -> None:
        if config is not None:
            self._aa_enabled = (
                getattr(config.aim_assist, "enabled", False)
                if hasattr(config, "aim_assist")
                else False
            )
            self._recoil_enabled = (
                getattr(config.recoil, "enabled", False)
                if hasattr(config, "recoil")
                else False
            )

    def _animate(self) -> None:
        self._pulse += 0.08
        if self._scanline_y > self.height() + 10:
            self._scanline_y = -10.0
        self._scanline_y += 0.6

        self.update()

    def _refresh_data(self) -> None:
        self._uptime_secs = self._elapsed.elapsed() / 1000.0

        if self._runtime is not None:
            status = self._runtime.get_status()
            self._active = status.get("active", False)
            device = status.get("device", "")
            self._device_name = device.rsplit("/", 1)[-1] if device else "--"
            self._fps = status.get("fps", 0)
            cfg = self._runtime.config
            if cfg is not None:
                self._aa_enabled = (
                    getattr(cfg.aim_assist, "enabled", False)
                    if hasattr(cfg, "aim_assist")
                    else False
                )
                self._recoil_enabled = (
                    getattr(cfg.recoil, "enabled", False)
                    if hasattr(cfg, "recoil")
                    else False
                )

    def _draw_corner_bracket(self, painter, x, y, w, h, color):
        bracket = QPen(color)
        bracket.setWidth(2)
        painter.setPen(bracket)

        size = 8
        painter.drawLine(x, y + size, x, y)
        painter.drawLine(x, y, x + size, y)

        painter.drawLine(x + w - size, y, x + w, y)
        painter.drawLine(x + w, y, x + w, y + size)

        painter.drawLine(x, y + h - size, x, y + h)
        painter.drawLine(x, y + h, x + size, y + h)

        painter.drawLine(x + w - size, y + h, x + w, y + h)
        painter.drawLine(x + w, y + h - size, x + w, y + h)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        bg = QColor(4, 6, 8, 200)
        painter.setBrush(QBrush(bg))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, w, h, 4, 4)

        self._draw_corner_bracket(painter, 3, 3, w - 6, h - 6, QColor(0, 255, 136, 80))

        border_pen = QPen(QColor(20, 40, 30, 180))
        border_pen.setWidth(1)
        painter.setPen(border_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(1, 1, w - 2, h - 2, 4, 4)

        title_font = QFont("Rajdhani", 8)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(QColor(0, 255, 136, 100))
        painter.drawText(10, 14, "NOCROSSHAIR v2")

        self._draw_scanline(painter, w)

        self._draw_status_section(painter)

        self._draw_fps_bar(painter, w)

        self._draw_device_section(painter)

        self._draw_uptime(painter, w)

        painter.end()

    def _draw_scanline(self, painter, w):
        alpha = max(0, int(30 - abs(self._scanline_y - 30)))
        if alpha > 2:
            scan = QColor(0, 255, 136, alpha)
            scan.setAlpha(alpha)
            line_y = int(self._scanline_y) % (self.height() - 10) + 5
            painter.fillRect(4, line_y, w - 8, 2, scan)

    def _draw_status_section(self, painter):
        font = QFont("Rajdhani", 14)
        font.setBold(True)
        painter.setFont(font)

        pulse = sin(self._pulse) * 0.3 + 0.7

        if self._active:
            dot_color = QColor(0, 255, 136, int(255 * pulse))
            painter.setPen(QPen(dot_color))
            painter.drawText(12, 40, "●")
            painter.setPen(QPen(QColor(0, 255, 136, int(200 * pulse))))
            painter.drawText(30, 40, "ACTIVE")

            glow = QColor(0, 255, 136, int(20 * pulse))
            painter.setBrush(QBrush(glow))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(8, 24, 80, 20, 4, 4)
        else:
            painter.setPen(QPen(QColor(80, 80, 80)))
            painter.drawText(12, 40, "●")
            painter.setPen(QPen(QColor(100, 100, 100)))
            painter.drawText(30, 40, "IDLE")

    def _draw_fps_bar(self, painter, w):
        font = QFont("JetBrains Mono", 9)
        font.setBold(True)
        painter.setFont(font)

        fps_text = f"FPS: {self._fps}"
        painter.setPen(QPen(QColor(160, 160, 160)))
        painter.drawText(12, 62, fps_text)

        bar_x = 70
        bar_y = 54
        bar_w = w - bar_x - 14
        bar_h = 8

        painter.setPen(QPen(QColor(20, 40, 30, 120), 1))
        painter.setBrush(QBrush(QColor(10, 15, 12)))
        painter.drawRoundedRect(bar_x, bar_y, bar_w, bar_h, 2, 2)

        fill = max(0, min(bar_w, int(bar_w * (self._fps / 120.0))))
        if fill > 0:
            if self._fps >= 55:
                c = QColor(0, 255, 136)
            elif self._fps >= 30:
                c = QColor(255, 204, 0)
            else:
                c = QColor(255, 60, 60)
            painter.setBrush(QBrush(c))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(bar_x, bar_y, fill, bar_h, 2, 2)

    def _draw_device_section(self, painter):
        font = QFont("Rajdhani", 11)
        font.setBold(True)
        painter.setFont(font)

        painter.setPen(QPen(QColor(160, 160, 160)))
        painter.drawText(12, 82, "DEV")

        painter.setPen(QPen(QColor(200, 200, 200)))
        dev = self._device_name if len(self._device_name) < 20 else self._device_name[:18] + ".."
        painter.drawText(50, 82, dev)

        font2 = QFont("Rajdhani", 10)
        painter.setFont(font2)

        y = 100
        aa_c = QColor(0, 255, 136, 200 if self._aa_enabled else 80)
        painter.setPen(QPen(aa_c))
        painter.drawText(12, y, "AA")
        painter.drawText(36, y, "ON" if self._aa_enabled else "OFF")

        painter.setPen(QPen(QColor(30, 60, 40, 120)))
        painter.drawText(70, y, "|")

        r_c = QColor(0, 255, 136, 200 if self._recoil_enabled else 80)
        painter.setPen(QPen(r_c))
        painter.drawText(82, y, "REC")
        painter.drawText(118, y, "ON" if self._recoil_enabled else "OFF")

        self._draw_signal_bars(painter)

    def _draw_signal_bars(self, painter):
        x = self.width() - 50
        y = 90
        num_bars = 5
        active_bars = 4 if self._active else 1

        for i in range(num_bars):
            bh = 4 + i * 2
            by = y - bh
            if i < active_bars:
                c = QColor(0, 255, 136, 180)
            else:
                c = QColor(30, 30, 30, 100)
            painter.fillRect(x + i * 8, by, 4, bh, c)

    def _draw_uptime(self, painter, w):
        font = QFont("JetBrains Mono", 8)
        painter.setFont(font)

        hours = int(self._uptime_secs // 3600)
        mins = int((self._uptime_secs % 3600) // 60)
        secs = int(self._uptime_secs % 60)
        time_str = f"UP {hours:02d}:{mins:02d}:{secs:02d}"

        painter.setPen(QPen(QColor(100, 100, 100)))
        painter.drawText(w - 90, 14, time_str)
