from typing import Callable, Optional, Dict, Any, List, Tuple
from PyQt6.QtCore import Qt, QTimer, QSize, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QSpinBox,
    QDoubleSpinBox, QPushButton, QComboBox, QCheckBox, QFileDialog,
    QColorDialog, QTableWidget, QTableWidgetItem, QHeaderView,
    QLineEdit, QGroupBox, QFormLayout, QFrame
)
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QIcon, QPixmap
)
from PyQt6.QtCore import Qt as QtConstants

class LabeledSlider(QWidget):

    value_changed = pyqtSignal(int)

    def __init__(self, label: str, min_val: int = 0, max_val: int = 100,
                 default: int = 50, parent=None):
        super().__init__(parent)
        self.setLayout(QHBoxLayout())

        self.label = QLabel(label)
        self.label.setMinimumWidth(100)
        self.layout().addWidget(self.label)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(min_val)
        self.slider.setMaximum(max_val)
        self.slider.setValue(default)
        self.slider.valueChanged.connect(self._on_change)
        self.layout().addWidget(self.slider)

        self.value_label = QLabel(str(default))
        self.value_label.setMinimumWidth(40)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.layout().addWidget(self.value_label)

    def _on_change(self, value: int) -> None:
        self.value_label.setText(str(value))
        self.value_changed.emit(value)

    def value(self) -> int:
        return self.slider.value()

    def setValue(self, value: int) -> None:
        self.slider.setValue(value)

class LabeledDoubleSlider(QWidget):

    value_changed = pyqtSignal(float)

    def __init__(self, label: str, min_val: float = 0.0, max_val: float = 1.0,
                 default: float = 0.5, decimals: int = 2, parent=None):
        super().__init__(parent)
        self.setLayout(QHBoxLayout())
        self.decimals = decimals

        self.label = QLabel(label)
        self.label.setMinimumWidth(100)
        self.layout().addWidget(self.label)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(1000)
        self.min_val = min_val
        self.max_val = max_val
        val_normalized = int((default - min_val) / (max_val - min_val) * 1000)
        self.slider.setValue(val_normalized)
        self.slider.valueChanged.connect(self._on_change)
        self.layout().addWidget(self.slider)

        self.value_label = QLabel(f"{default:.{decimals}f}")
        self.value_label.setMinimumWidth(50)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.layout().addWidget(self.value_label)

    def _on_change(self, slider_val: int) -> None:
        val = self.min_val + (slider_val / 1000.0) * (self.max_val - self.min_val)
        self.value_label.setText(f"{val:.{self.decimals}f}")
        self.value_changed.emit(val)

    def value(self) -> float:
        slider_val = self.slider.value()
        return self.min_val + (slider_val / 1000.0) * (self.max_val - self.min_val)

    def setValue(self, value: float) -> None:
        val_normalized = int((value - self.min_val) / (self.max_val - self.min_val) * 1000)
        self.slider.setValue(val_normalized)

class StickVisualizerWidget(QWidget):

    def __init__(self, title: str = "Analógico", parent=None):
        super().__init__(parent)
        self.title = title
        self.setMinimumSize(140, 160)
        self.setMaximumSize(200, 220)
        self.stick_x = 0
        self.stick_y = 0

    def set_position(self, x: int, y: int) -> None:
        self.stick_x = x
        self.stick_y = y
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        r = min(w, h - 20) // 2 - 8
        cx = w // 2
        cy = (h - 20) // 2 + 5

        painter.setPen(QPen(QColor("#ffffff")))
        painter.setFont(QFont("monospace", 8))
        painter.drawText(5, 12, self.title)

        painter.setBrush(QBrush(QColor("#1a1a2e")))
        painter.setPen(QPen(QColor("#444444")))
        painter.drawEllipse(cx - r, cy - r, 2 * r, 2 * r)

        painter.setPen(QPen(QColor("#333333")))
        painter.drawLine(cx - r, cy, cx + r, cy)
        painter.drawLine(cx, cy - r, cx, cy + r)

        nx = self.stick_x / 32768.0
        ny = self.stick_y / 32768.0
        dot_x = cx + int(nx * r)
        dot_y = cy - int(ny * r)

        painter.setBrush(QBrush(QColor("#00ff88")))
        painter.setPen(QPen(QColor("#00cc66")))
        painter.drawEllipse(dot_x - 5, dot_y - 5, 10, 10)

class ResponseCurveWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 200)
        self.accel = 1.0
        self.defl_min = 0.0
        self.defl_max = 1.0
        self.init_spd = 0.0

    def set_params(self, accel: float, defl_min: float, defl_max: float,
                  init_spd: float) -> None:
        self.accel = accel
        self.defl_min = defl_min
        self.defl_max = defl_max
        self.init_spd = init_spd
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        painter.fillRect(0, 0, w, h, QColor("#1a1a2e"))

        pad = 20
        gw = w - 2 * pad
        gh = h - 2 * pad

        painter.setPen(QPen(QColor("#333333")))
        for i in range(1, 4):
            x = pad + int(gw * i / 4)
            y = pad + int(gh * i / 4)
            painter.drawLine(x, pad, x, h - pad)
            painter.drawLine(pad, y, w - pad, y)

        painter.setPen(QPen(QColor("#666666")))
        painter.drawLine(pad, h - pad, w - pad, h - pad)
        painter.drawLine(pad, pad, pad, h - pad)

        painter.setPen(QPen(QColor("#00ff88"), 2))
        prev_pt = None

        for i in range(101):
            x_norm = i / 100.0

            if x_norm < self.defl_min:
                y_norm = 0.0
            elif x_norm > self.defl_max:
                y_norm = 1.0
            else:
                scale_x = (x_norm - self.defl_min) / (self.defl_max - self.defl_min)
                y_norm = self.init_spd + (1.0 - self.init_spd) * (scale_x ** self.accel)

            y_norm = max(0.0, min(1.0, y_norm))
            px = pad + int(x_norm * gw)
            py = h - pad - int(y_norm * gh)

            if prev_pt is not None:
                painter.drawLine(prev_pt[0], prev_pt[1], px, py)

            prev_pt = (px, py)

class ColorPickerButton(QPushButton):

    color_changed = pyqtSignal(str)

    def __init__(self, initial_color: str = "#00ff88", parent=None):
        super().__init__(parent)
        self.current_color = initial_color
        self.setMinimumWidth(80)
        self._update_display()
        self.clicked.connect(self._pick_color)

    def _update_display(self) -> None:
        self.setText(self.current_color)

    def _pick_color(self) -> None:
        color = QColorDialog.getColor(QColor(self.current_color), self)
        if color.isValid():
            self.current_color = color.name()
            self._update_display()
            self.color_changed.emit(self.current_color)

    def color(self) -> str:
        return self.current_color

    def setColor(self, color: str) -> None:
        self.current_color = color
        self._update_display()

class PresetSelector(QWidget):

    preset_changed = pyqtSignal(str)

    def __init__(self, label: str, presets: List[str], parent=None):
        super().__init__(parent)
        self.setLayout(QHBoxLayout())

        label_widget = QLabel(label)
        label_widget.setMinimumWidth(100)
        self.layout().addWidget(label_widget)

        self.combo = QComboBox()
        self.combo.addItems(presets)
        self.combo.addItem("Custom")
        self.combo.currentTextChanged.connect(self._on_change)
        self.layout().addWidget(self.combo)

    def _on_change(self, text: str) -> None:
        self.preset_changed.emit(text)

    def currentPreset(self) -> str:
        return self.combo.currentText()

    def setPreset(self, preset: str) -> None:
        idx = self.combo.findText(preset)
        if idx >= 0:
            self.combo.setCurrentIndex(idx)

class KeyBindingTable(QTableWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(["Button", "Target", "Type"])

        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

    def add_binding(self, button: str, target: str, binding_type: str = "Normal") -> None:
        row = self.rowCount()
        self.insertRow(row)

        item_btn = QTableWidgetItem(button)
        self.setItem(row, 0, item_btn)

        item_target = QTableWidgetItem(target)
        self.setItem(row, 1, item_target)

        item_type = QTableWidgetItem(binding_type)
        self.setItem(row, 2, item_type)

    def get_bindings(self) -> Dict[str, str]:
        bindings = {}
        for row in range(self.rowCount()):
            btn = self.item(row, 0)
            target = self.item(row, 1)
            if btn and target:
                bindings[btn.text()] = target.text()
        return bindings

class SectionGroupBox(QFrame):

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setObjectName("sectionGroupBox")
        self._section_layout = QVBoxLayout(self)
        self._section_layout.setContentsMargins(8, 20, 8, 8)
        self._section_layout.setSpacing(4)
        self._title_text = title

    def layout(self):
        return self._section_layout

class HLine(QFrame):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.HLine)
        self.setFrameShadow(QFrame.Shadow.Sunken)
        self.setStyleSheet("color: #444444")

class VLine(QFrame):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.VLine)
        self.setFrameShadow(QFrame.Shadow.Sunken)
        self.setStyleSheet("color: #444444")


from nocrosshair.ui.widgets.recoil_curve_preview import RecoilCurvePreview
