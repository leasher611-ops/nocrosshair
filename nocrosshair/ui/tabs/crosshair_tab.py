from typing import Callable, Optional, Dict, Any
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QSpinBox,
    QCheckBox, QGridLayout
)

from nocrosshair.core.config import CrosshairStyle
from nocrosshair.ui.widgets import (
    LabeledSlider, LabeledDoubleSlider, ColorPickerButton,
    PresetSelector, HLine, SectionGroupBox
)
from nocrosshair.ui.widgets.crosshair_preview import CrosshairPreview

class CrosshairTab(QWidget):

    config_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayout(QVBoxLayout())
        self._init_ui()

    def _init_ui(self) -> None:
        title = QLabel("Crosshair Configuration")
        title.setObjectName("hudTitle")
        self.layout().addWidget(title)

        self.layout().addWidget(HLine())

        style_group = SectionGroupBox("Visual Style")
        style_layout = QGridLayout()

        style_label = QLabel("Style:")
        self.style_combo = QComboBox()
        self.style_combo.addItems([cs.value for cs in CrosshairStyle])
        self.style_combo.currentTextChanged.connect(self._on_change)
        style_layout.addWidget(style_label, 0, 0)
        style_layout.addWidget(self.style_combo, 0, 1)

        color_label = QLabel("Color:")
        self.color_picker = ColorPickerButton("#00ff88")
        self.color_picker.color_changed.connect(self._on_change)
        style_layout.addWidget(color_label, 1, 0)
        style_layout.addWidget(self.color_picker, 1, 1)

        self.outline_check = QCheckBox("Outline")
        self.outline_check.stateChanged.connect(self._on_change)
        style_layout.addWidget(self.outline_check, 2, 0, 1, 2)

        style_group.layout().addLayout(style_layout)
        self.layout().addWidget(style_group)

        size_group = SectionGroupBox("Dimensions")
        size_layout = QVBoxLayout()

        self.size_slider = LabeledSlider("Size", 5, 100, 20)
        self.size_slider.value_changed.connect(self._on_change)
        size_layout.addWidget(self.size_slider)

        self.thick_slider = LabeledSlider("Thickness", 1, 10, 2)
        self.thick_slider.value_changed.connect(self._on_change)
        size_layout.addWidget(self.thick_slider)

        self.gap_slider = LabeledSlider("Gap", 0, 20, 4)
        self.gap_slider.value_changed.connect(self._on_change)
        size_layout.addWidget(self.gap_slider)

        size_group.layout().addLayout(size_layout)
        self.layout().addWidget(size_group)

        pos_group = SectionGroupBox("Position & Opacity")
        pos_layout = QVBoxLayout()

        offset_x_layout = QHBoxLayout()
        offset_x_label = QLabel("Offset X:")
        offset_x_label.setMinimumWidth(100)
        self.offset_x_spin = SpinBoxSigned(-100, 100, 0)
        self.offset_x_spin.valueChanged.connect(self._on_change)
        offset_x_layout.addWidget(offset_x_label)
        offset_x_layout.addWidget(self.offset_x_spin)
        offset_x_layout.addStretch()
        pos_layout.addLayout(offset_x_layout)

        offset_y_layout = QHBoxLayout()
        offset_y_label = QLabel("Offset Y:")
        offset_y_label.setMinimumWidth(100)
        self.offset_y_spin = SpinBoxSigned(-100, 100, 0)
        self.offset_y_spin.valueChanged.connect(self._on_change)
        offset_y_layout.addWidget(offset_y_label)
        offset_y_layout.addWidget(self.offset_y_spin)
        offset_y_layout.addStretch()
        pos_layout.addLayout(offset_y_layout)

        self.alpha_slider = LabeledDoubleSlider("Opacity", 0.0, 1.0, 1.0, decimals=2)
        self.alpha_slider.value_changed.connect(self._on_change)
        pos_layout.addWidget(self.alpha_slider)

        self.visible_check = QCheckBox("Visible")
        self.visible_check.setChecked(True)
        self.visible_check.stateChanged.connect(self._on_change)
        pos_layout.addWidget(self.visible_check)

        pos_group.layout().addLayout(pos_layout)
        self.layout().addWidget(pos_group)

        preview_group = SectionGroupBox("Preview")
        preview_layout = QVBoxLayout()

        self.crosshair_preview = CrosshairPreview()
        preview_layout.addWidget(self.crosshair_preview)

        preview_group.layout().addLayout(preview_layout)
        self.layout().addWidget(preview_group)

        self.layout().addStretch()

        self._sync_preview()

    def _on_change(self) -> None:
        config = self.get_config()
        self.crosshair_preview.update_config(config)
        self.config_changed.emit(config)

    def _sync_preview(self) -> None:
        self.crosshair_preview.update_config(self.get_config())

    def get_config(self) -> Dict[str, Any]:
        return {
            "style": self.style_combo.currentText(),
            "color": self.color_picker.color(),
            "size": self.size_slider.value(),
            "thick": self.thick_slider.value(),
            "gap": self.gap_slider.value(),
            "offset_x": self.offset_x_spin.value(),
            "offset_y": self.offset_y_spin.value(),
            "alpha": self.alpha_slider.value(),
            "outline": self.outline_check.isChecked(),
            "visible": self.visible_check.isChecked(),
        }

    def set_config(self, config: Dict[str, Any]) -> None:
        if "style" in config:
            self.style_combo.setCurrentText(config["style"])
        if "color" in config:
            self.color_picker.setColor(config["color"])
        if "size" in config:
            self.size_slider.setValue(config["size"])
        if "thick" in config:
            self.thick_slider.setValue(config["thick"])
        if "gap" in config:
            self.gap_slider.setValue(config["gap"])
        if "offset_x" in config:
            self.offset_x_spin.setValue(config["offset_x"])
        if "offset_y" in config:
            self.offset_y_spin.setValue(config["offset_y"])
        if "alpha" in config:
            self.alpha_slider.setValue(config["alpha"])
        if "outline" in config:
            self.outline_check.setChecked(config["outline"])
        if "visible" in config:
            self.visible_check.setChecked(config["visible"])

class SpinBoxSigned(QSpinBox):

    def __init__(self, min_val: int, max_val: int, default: int, parent=None):
        super().__init__(parent)
        self.setMinimum(min_val)
        self.setMaximum(max_val)
        self.setValue(default)
        self.setMinimumWidth(80)
