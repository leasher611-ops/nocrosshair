from typing import Optional
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QCursor
from PyQt6.QtWidgets import QWidget
from PIL import Image


class ZoomOverlay(QWidget):

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._zoom_factor: float = 4.0
        self._capture_w: int = 240
        self._capture_h: int = 180
        self._pixmap: Optional[QPixmap] = None
        self._fixed_pos: bool = False
        self._fixed_x: int = 960
        self._fixed_y: int = 540

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setStyleSheet("background: transparent;")
        self.resize(240, 180)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._capture_and_update)

    def set_zoom_params(self, factor: float, width: int, height: int,
                        fixed_pos: bool = False, fx: int = 960, fy: int = 540) -> None:
        self._zoom_factor = factor
        self._capture_w = width
        self._capture_h = height
        self._fixed_pos = fixed_pos
        self._fixed_x = fx
        self._fixed_y = fy
        self.resize(width, height)

    def set_active(self, active: bool) -> None:
        if active:
            self.show()
            self.raise_()
            self._timer.start(33)
        else:
            self._timer.stop()
            self.hide()

    def _capture_and_update(self) -> None:
        if self._fixed_pos:
            cx, cy = self._fixed_x, self._fixed_y
        else:
            cursor = self._get_cursor_pos()
            if cursor is None:
                return
            cx, cy = cursor

        half_cw = int(self._capture_w / (2.0 * self._zoom_factor))
        half_ch = int(self._capture_h / (2.0 * self._zoom_factor))
        left = int(max(0, cx - half_cw))
        top = int(max(0, cy - half_ch))
        right = int(left + half_cw * 2)
        bottom = int(top + half_ch * 2)

        try:
            import mss
            with mss.mss() as sct:
                region = {"left": left, "top": top, "width": right - left, "height": bottom - top}
                sct_img = sct.grab(region)
                img = Image.frombytes("RGB", (sct_img.width, sct_img.height), sct_img.rgb)
                img = img.resize((self._capture_w, self._capture_h), Image.NEAREST)

            img = img.convert("RGBA")
            qim = QImage(img.tobytes(), img.width, img.height, QImage.Format.Format_RGBA8888)
            self._pixmap = QPixmap.fromImage(qim)
        except Exception as e:
            print(f"[ZoomOverlay] capture failed: {e}")
            return

        if not self._fixed_pos:
            screen = self.screen()
            sw = screen.size().width() if screen else 1920
            sh = screen.size().height() if screen else 1080
            wx = int(max(0, min(cx - self._capture_w // 2, sw - self._capture_w)))
            wy = int(max(0, min(cy - self._capture_h - 30, sh - self._capture_h)))
            self.move(wx, wy)

        self.update()

    def paintEvent(self, event) -> None:
        if self._pixmap is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawPixmap(0, 0, self._pixmap)
        pen = QPen(QColor("#00ff88"))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)
        painter.drawLine(self.width() // 2 - 10, self.height() // 2,
                         self.width() // 2 + 10, self.height() // 2)
        painter.drawLine(self.width() // 2, self.height() // 2 - 10,
                         self.width() // 2, self.height() // 2 + 10)

    def _get_cursor_pos(self) -> Optional[tuple[int, int]]:
        try:
            from Xlib.display import Display
            d = Display()
            root = d.screen().root
            result = root.query_pointer()
            d.close()
            return (result.root_x, result.root_y)
        except Exception:
            pass
        try:
            p = QCursor.pos()
            return (p.x(), p.y())
        except Exception:
            return None
