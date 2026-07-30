from typing import List, Tuple, Optional
from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QRectF
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QFont, QPainterPath, QMouseEvent

class BezierCurveEditor(QWidget):

    curve_changed = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(300, 200)
        self.setMaximumSize(400, 300)

        self._points = [
            (0.0, 0.0),
            (0.25, 0.25),
            (0.5, 0.5),
            (0.75, 0.75),
            (1.0, 1.0)
        ]
        self._selected_index = -1
        self._dragging = False
        self._grid_size = 10

        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def set_curve(self, points: List[Tuple[float, float]]) -> None:
        if len(points) >= 2:
            self._points = list(points)
            self._selected_index = -1
            self.update()

    def get_curve(self) -> List[Tuple[float, float]]:
        return list(self._points)

    def add_point(self, x: float, y: float) -> None:
        new_point = (max(0.0, min(1.0, x)), max(0.0, min(1.0, y)))

        insert_pos = 0
        for i, (px, _) in enumerate(self._points):
            if px < new_point[0]:
                insert_pos = i + 1

        self._points.insert(insert_pos, new_point)
        self.update()
        self.curve_changed.emit(self._points)

    def remove_selected_point(self) -> None:
        if 0 < self._selected_index < len(self._points) - 1:
            del self._points[self._selected_index]
            self._selected_index = -1
            self.update()
            self.curve_changed.emit(self._points)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()

        painter.fillRect(0, 0, width, height, QColor(30, 30, 30))

        painter.setPen(QPen(QColor(60, 60, 60), 1))
        for i in range(0, width, self._grid_size):
            painter.drawLine(i, 0, i, height)
        for i in range(0, height, self._grid_size):
            painter.drawLine(0, i, width, i)

        painter.setPen(QPen(QColor(100, 100, 100), 1))
        painter.drawLine(0, height - 1, width, height - 1)
        painter.drawLine(0, 0, 0, height - 1)

        if len(self._points) >= 2:
            path = QPainterPath()
            start_x = self._points[0][0] * width
            start_y = (1.0 - self._points[0][1]) * height
            path.moveTo(start_x, start_y)

            for i in range(1, len(self._points)):
                x = self._points[i][0] * width
                y = (1.0 - self._points[i][1]) * height
                path.lineTo(x, y)

            painter.setPen(QPen(QColor(0, 255, 136), 2))
            painter.drawPath(path)

        for i, (x, y) in enumerate(self._points):
            screen_x = x * width
            screen_y = (1.0 - y) * height

            if i == self._selected_index:
                painter.setBrush(QBrush(QColor(255, 100, 100)))
                painter.setPen(QPen(QColor(255, 150, 150), 2))
                size = 12
            else:
                painter.setBrush(QBrush(QColor(0, 255, 136)))
                painter.setPen(QPen(QColor(0, 200, 100), 1))
                size = 8

            painter.drawEllipse(QPointF(screen_x, screen_y), size / 2, size / 2)

        painter.end()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            x = event.position().x() / self.width()
            y = 1.0 - event.position().y() / self.height()

            self._selected_index = -1
            for i, (px, py) in enumerate(self._points):
                dist = ((x - px) ** 2 + (y - py) ** 2) ** 0.5
                if dist < 0.05:
                    self._selected_index = i
                    self._dragging = True
                    break

            if self._selected_index == -1 and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                self.add_point(x, y)

            self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._dragging and 0 <= self._selected_index < len(self._points):
            x = event.position().x() / self.width()
            y = 1.0 - event.position().y() / self.height()

            x = max(0.0, min(1.0, x))
            y = max(0.0, min(1.0, y))

            if self._selected_index == 0:
                x = 0.0
            elif self._selected_index == len(self._points) - 1:
                x = 1.0

            self._points[self._selected_index] = (x, y)
            self.update()
            self.curve_changed.emit(self._points)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Delete:
            self.remove_selected_point()
        elif event.key() == Qt.Key.Key_R:
            self._points = [
                (0.0, 0.0),
                (0.25, 0.25),
                (0.5, 0.5),
                (0.75, 0.75),
                (1.0, 1.0)
            ]
            self._selected_index = -1
            self.update()
            self.curve_changed.emit(self._points)

class BezierCurveEditorWithControls(QWidget):

    curve_changed = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        title = QLabel("Advanced Curve Editor")
        title.setFont(QFont("monospace", 10, QFont.Weight.Bold))
        title.setStyleSheet("color: #00ff88")
        layout.addWidget(title)

        self.editor = BezierCurveEditor()
        self.editor.curve_changed.connect(self.curve_changed.emit)
        layout.addWidget(self.editor)

        controls = QHBoxLayout()

        reset_btn = QPushButton("Reset")
        reset_btn.clicked.connect(self._reset_curve)
        controls.addWidget(reset_btn)

        linear_btn = QPushButton("Linear")
        linear_btn.clicked.connect(self._set_linear)
        controls.addWidget(linear_btn)

        ease_in_btn = QPushButton("Ease-In")
        ease_in_btn.clicked.connect(self._set_ease_in)
        controls.addWidget(ease_in_btn)

        ease_out_btn = QPushButton("Ease-Out")
        ease_out_btn.clicked.connect(self._set_ease_out)
        controls.addWidget(ease_out_btn)

        controls.addStretch()

        help_label = QLabel("Ctrl+Click: Add point | Del: Remove point | R: Reset")
        help_label.setStyleSheet("color: #888888")
        controls.addWidget(help_label)

        layout.addLayout(controls)

    def set_curve(self, points: List[Tuple[float, float]]) -> None:
        self.editor.set_curve(points)

    def get_curve(self) -> List[Tuple[float, float]]:
        return self.editor.get_curve()

    def _reset_curve(self) -> None:
        self.editor.set_curve([
            (0.0, 0.0),
            (0.25, 0.25),
            (0.5, 0.5),
            (0.75, 0.75),
            (1.0, 1.0)
        ])

    def _set_linear(self) -> None:
        self.editor.set_curve([
            (0.0, 0.0),
            (1.0, 1.0)
        ])

    def _set_ease_in(self) -> None:
        self.editor.set_curve([
            (0.0, 0.0),
            (0.42, 0.0),
            (1.0, 1.0)
        ])

    def _set_ease_out(self) -> None:
        self.editor.set_curve([
            (0.0, 0.0),
            (0.58, 1.0),
            (1.0, 1.0)
        ])
