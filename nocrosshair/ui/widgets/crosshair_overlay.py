from math import sin, cos, pi
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont
from PyQt6.QtWidgets import QWidget, QApplication


class QtCrosshairOverlay(QWidget):

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self._config = dict(config)
        self._visible = config.get("visible", True)
        self._shake_x = 0.0
        self._shake_y = 0.0
        self._telemetry_text = ""

        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.ToolTip
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

        QTimer.singleShot(0, self._reposition_and_show)

    def _force_above(self):
        """Send _NET_WM_STATE ClientMessage to keep overlay above fullscreen windows."""
        try:
            from Xlib import display as Xdisplay, X, Xatom
            import struct
            dsp = Xdisplay.Display()
            root = dsp.screen().root
            win_id = int(self.winId()) & 0xFFFFFFFF
            win = dsp.create_resource_object('window', win_id)

            above_atom = dsp.intern_atom('_NET_WM_STATE_ABOVE')
            state_atom = dsp.intern_atom('_NET_WM_STATE')

            # Set property directly
            win.change_property(state_atom, Xatom.ATOM, 32, [above_atom])

            # Send ClientMessage to WM (required for already-mapped windows)
            event = struct.pack('=BBHIiiIIIII',
                33,  # ClientMessage type
                32,  # format
                0,   # sequence (ignored)
                win_id,
                state_atom,
                1,   # _NET_WM_STATE_ADD
                above_atom,
                0, 0, 0, 0
            )
            root.send_event(event, event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask)

            # Also raise in X11 stacking order
            win.configure(stack_mode=X.Above)

            dsp.flush()
            dsp.close()
        except Exception:
            pass

    def _crosshair_rects(self):
        cfg = self._config
        size = cfg.get("size", 20)
        thick = cfg.get("thick", 3)
        gap = cfg.get("gap", 4)
        s = size
        t = thick + 4
        g = gap
        ws = self._window_size()
        cx = ws // 2
        cy = ws // 2
        m = 2
        rects = []
        if g > 0:
            rects.append((cx - t // 2, cy - s - m, t, s - g + m))
            rects.append((cx - t // 2, cy + g, t, s - g + m))
            rects.append((cx - s - m, cy - t // 2, s - g + m, t))
            rects.append((cx + g, cy - t // 2, s - g + m, t))
        else:
            rects.append((cx - t // 2, cy - s - m, t, s * 2 + m * 2))
            rects.append((cx - s - m, cy - t // 2, s * 2 + m * 2, t))
        return rects

    def _apply_xshape(self):
        try:
            from Xlib import display as Xdisplay
            from Xlib.ext import shape
            dsp = Xdisplay.Display()
            win_id = int(self.winId()) & 0xFFFFFFFF
            rects = self._crosshair_rects()
            win = dsp.create_resource_object('window', win_id)
            win.shape_rectangles(
                shape.SO.Set, shape.SK.Input, 0, 0, 0, rects)
            dsp.flush()
            dsp.close()
        except Exception:
            pass

    def _window_size(self):
        s = self._config.get("size", 20)
        g = self._config.get("gap", 4)
        t = self._config.get("thick", 3)
        return int(max(s * 2 + g + t + 10, 64))

    def _center_pos(self):
        screen = QApplication.primaryScreen()
        if not screen:
            return 0, 0
        # Use geometry() instead of availableGeometry() to center over fullscreen content
        geo = screen.geometry()
        ws = self._window_size()
        ox = self._config.get("offset_x", 0)
        oy = self._config.get("offset_y", 0)
        cx = geo.center().x() + ox
        cy = geo.center().y() + oy
        return cx - ws // 2, cy - ws // 2

    def _reposition_and_show(self):
        ws = self._window_size()
        x, y = self._center_pos()
        self.setFixedSize(ws, ws)
        self.move(x, y)
        if self._visible:
            self.show()
            self.raise_()
            QTimer.singleShot(0, self._apply_xshape)
            QTimer.singleShot(50, self._force_above)

    def _tick(self):
        self._shake_x *= 0.85
        self._shake_y *= 0.85
        if abs(self._shake_x) < 0.5:
            self._shake_x = 0.0
        if abs(self._shake_y) < 0.5:
            self._shake_y = 0.0
        # Re-raise periodically to stay above fullscreen windows (~every 500ms)
        self._raise_counter = getattr(self, '_raise_counter', 0) + 1
        if self._raise_counter >= 30 and self._visible:  # 30 * 16ms ≈ 480ms
            self._raise_counter = 0
            self.raise_()
            self._force_above()
        self.update()

    def update_config(self, config: dict):
        self._config = dict(config)
        if self._visible:
            self._reposition_and_show()
        self.update()

    def set_visible(self, visible: bool):
        self._visible = visible
        if visible:
            self._reposition_and_show()
        else:
            self.hide()

    def trigger_haptic(self, strength: float = 1.0):
        from time import time
        self._shake_y = -strength * 4.0
        self._shake_x = (time() % 0.2 - 0.1) * strength * 20.0

    def set_telemetry(self, text: str):
        self._telemetry_text = text

    def update_telemetry(self, text: str):
        self._telemetry_text = text

    def update_color(self, hex_color: str):
        self._config["color"] = hex_color
        self.update()

    _STYLE_MAP = {
        "cruz": "cross",
        "ponto": "dot",
        "círculo": "circle",
        "cruz+ponto": "cross+dot",
        "círculo+ponto": "circle+dot",
        "estilo T": "t-shape",
        "mira em x": "x-cross",
        "losango": "diamond",
        "ângulos": "angles",
        "scope": "scope",
    }

    def paintEvent(self, event):
        if not self._visible:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        h = self.height()
        cx = w // 2
        cy = h // 2

        cfg = self._config
        color_hex = cfg.get("color", "#00ff88")
        color = QColor(color_hex)
        alpha = cfg.get("alpha", 1.0)
        color.setAlphaF(alpha)
        size = cfg.get("size", 20)
        thick = cfg.get("thick", 3)
        gap = cfg.get("gap", 4)
        outline = cfg.get("outline", True)

        cx += int(self._shake_x)
        cy += int(self._shake_y)

        style_raw = cfg.get("style", "cruz")
        style = self._STYLE_MAP.get(style_raw, style_raw)

        if outline:
            op = QPen(QColor(0, 0, 0, 180))
            op.setWidth(thick + 2)
            op.setCapStyle(Qt.PenCapStyle.FlatCap)
            self._draw_style(painter, cx, cy, style, size + 1, thick + 2, gap, op)

        mp = QPen(color)
        mp.setWidth(thick)
        mp.setCapStyle(Qt.PenCapStyle.FlatCap)
        self._draw_style(painter, cx, cy, style, size, thick, gap, mp)

        if self._telemetry_text:
            font = QFont("JetBrains Mono", 10)
            painter.setFont(font)
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(10, h - 10, self._telemetry_text)

        painter.end()

    def _draw_style(self, painter, cx, cy, style, size, thick, gap, pen):
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        if style == "dot":
            painter.setBrush(QBrush(pen.color()))
            r = max(thick, 3)
            painter.drawEllipse(cx - r, cy - r, r * 2, r * 2)

        elif style == "circle":
            painter.drawEllipse(cx - size, cy - size, size * 2, size * 2)

        elif style in ("cross", "cross+dot"):
            if gap > 0:
                painter.drawLine(cx, cy - size, cx, cy - gap)
                painter.drawLine(cx, cy + gap, cx, cy + size)
                painter.drawLine(cx - size, cy, cx - gap, cy)
                painter.drawLine(cx + gap, cy, cx + size, cy)
            else:
                painter.drawLine(cx, cy - size, cx, cy + size)
                painter.drawLine(cx - size, cy, cx + size, cy)
            if style == "cross+dot":
                painter.setBrush(QBrush(pen.color()))
                r = thick + 1
                painter.drawEllipse(cx - r, cy - r, r * 2, r * 2)

        elif style == "circle+dot":
            painter.drawEllipse(cx - size, cy - size, size * 2, size * 2)
            painter.setBrush(QBrush(pen.color()))
            r = thick + 1
            painter.drawEllipse(cx - r, cy - r, r * 2, r * 2)

        elif style == "t-shape":
            if gap > 0:
                painter.drawLine(cx, cy + gap, cx, cy + size)
                painter.drawLine(cx - size, cy, cx - gap, cy)
                painter.drawLine(cx + gap, cy, cx + size, cy)
            else:
                painter.drawLine(cx, cy, cx, cy + size)
                painter.drawLine(cx - size, cy, cx + size, cy)

        elif style == "x-cross":
            d = int(size / (2 ** 0.5))
            dg = int(gap / (2 ** 0.5))
            if dg > 0:
                painter.drawLine(cx - d, cy - d, cx - dg, cy - dg)
                painter.drawLine(cx + dg, cy + dg, cx + d, cy + d)
                painter.drawLine(cx - d, cy + d, cx - dg, cy + dg)
                painter.drawLine(cx + dg, cy - dg, cx + d, cy - d)
            else:
                painter.drawLine(cx - d, cy - d, cx + d, cy + d)
                painter.drawLine(cx - d, cy + d, cx + d, cy - d)

        elif style == "diamond":
            painter.drawLine(cx - size, cy, cx, cy - size)
            painter.drawLine(cx, cy - size, cx + size, cy)
            painter.drawLine(cx + size, cy, cx, cy + size)
            painter.drawLine(cx, cy + size, cx - size, cy)

        elif style == "angles":
            arm = size
            short = max(size // 2, 4)
            for dx, dy in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
                bx = cx + dx * (gap + arm)
                by = cy + dy * gap
                painter.drawLine(bx, by, bx - dx * short, by)
                painter.drawLine(bx, by, bx, by + dy * short)

        elif style == "scope":
            painter.setBrush(QBrush(pen.color()))
            painter.drawRect(cx - 2, cy - 2, 4, 4)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(cx - 12, cy - 12, 24, 24)
