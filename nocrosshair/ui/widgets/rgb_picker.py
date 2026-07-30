from typing import Optional
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QComboBox, QCheckBox,
    QHBoxLayout, QLabel, QSlider, QPushButton, QColorDialog
)
from PyQt6.QtGui import QColor, QPixmap, QPainter, QIcon

from nocrosshair.features.rgb import RGBConfig, RGBEffect


class _ColorSwatchButton(QPushButton):

    def __init__(self, color: tuple[int, int, int] = (0, 255, 136), parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._r, self._g, self._b = color
        self.setFixedSize(36, 24)
        self.clicked.connect(self._pick)
        self._render_swatch()

    def _render_swatch(self) -> None:
        pm = QPixmap(32, 20)
        pm.fill(QColor(self._r, self._g, self._b))
        self.setIcon(QIcon(pm))

    def _pick(self) -> None:
        current = QColor(self._r, self._g, self._b)
        color = QColorDialog.getColor(current, self)
        if color.isValid():
            self._r = color.red()
            self._g = color.green()
            self._b = color.blue()
            self._render_swatch()

    def get_color(self) -> tuple[int, int, int]:
        return (self._r, self._g, self._b)

    def set_color(self, r: int, g: int, b: int) -> None:
        self._r = r
        self._g = g
        self._b = b
        self._render_swatch()


class RGBPickerWidget(QWidget):

    config_changed = pyqtSignal(object)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._config = RGBConfig()
        self._zone_count = 1
        self.setLayout(QVBoxLayout())
        self._init_ui()
        self._sync_from_config()

    def _init_ui(self) -> None:
        group = QGroupBox("RGB Lighting")
        layout = QVBoxLayout()

        self.enable_check = QCheckBox("Enable RGB")
        self.enable_check.stateChanged.connect(self._on_change)
        layout.addWidget(self.enable_check)

        color_row = QHBoxLayout()
        color_row.addWidget(QLabel("Color"))
        self.color_swatch = _ColorSwatchButton((0, 255, 136))
        color_row.addWidget(self.color_swatch)
        color_row.addStretch()
        layout.addLayout(color_row)

        effect_row = QHBoxLayout()
        effect_row.addWidget(QLabel("Effect"))
        self.effect_combo = QComboBox()
        self.effect_combo.addItem("Static", RGBEffect.STATIC)
        self.effect_combo.addItem("Breathing", RGBEffect.BREATHING)
        self.effect_combo.addItem("Rainbow", RGBEffect.RAINBOW)
        self.effect_combo.addItem("Wave", RGBEffect.WAVE)
        self.effect_combo.addItem("Custom", RGBEffect.CUSTOM)
        self.effect_combo.currentIndexChanged.connect(self._on_change)
        effect_row.addWidget(self.effect_combo)
        layout.addLayout(effect_row)

        bright_row = QHBoxLayout()
        bright_row.addWidget(QLabel("Brightness"))
        self.bright_slider = QSlider(Qt.Orientation.Horizontal)
        self.bright_slider.setMinimum(0)
        self.bright_slider.setMaximum(255)
        self.bright_slider.setValue(128)
        self.bright_slider.valueChanged.connect(self._on_change)
        bright_row.addWidget(self.bright_slider)
        self.bright_label = QLabel("128")
        self.bright_label.setMinimumWidth(40)
        self.bright_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        bright_row.addWidget(self.bright_label)
        layout.addLayout(bright_row)

        speed_row = QHBoxLayout()
        speed_row.addWidget(QLabel("Speed"))
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setMinimum(1)
        self.speed_slider.setMaximum(100)
        self.speed_slider.setValue(10)
        self.speed_slider.valueChanged.connect(self._on_change)
        speed_row.addWidget(self.speed_slider)
        self.speed_label = QLabel("1.0")
        self.speed_label.setMinimumWidth(40)
        self.speed_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        speed_row.addWidget(self.speed_label)
        layout.addLayout(speed_row)

        zone_row = QHBoxLayout()
        zone_row.addWidget(QLabel("Zone"))
        self.zone_combo = QComboBox()
        zone_row.addWidget(self.zone_combo)
        layout.addLayout(zone_row)

        self.apply_btn = QPushButton("Apply RGB")
        self.apply_btn.clicked.connect(self._on_apply)
        layout.addWidget(self.apply_btn)

        group_layout = QVBoxLayout(group)
        group_layout.addLayout(layout)
        self.layout().addWidget(group)

    def set_zone_count(self, count: int) -> None:
        self._zone_count = count
        self.zone_combo.clear()
        self.zone_combo.addItem("All", 0)
        for i in range(1, count + 1):
            self.zone_combo.addItem(f"Zone {i}", i)

    def _on_apply(self) -> None:
        self._flush_to_config()
        self.config_changed.emit(self._config)

    def _on_change(self) -> None:
        self._update_labels()

    def _update_labels(self) -> None:
        self.bright_label.setText(str(self.bright_slider.value()))
        speed_val = self.speed_slider.value() / 10.0
        self.speed_label.setText(f"{speed_val:.1f}")

    def _flush_to_config(self) -> None:
        self._config.enabled = self.enable_check.isChecked()
        self._config.color = self.color_swatch.get_color()
        self._config.effect = self.effect_combo.currentData()
        self._config.brightness = self.bright_slider.value()
        self._config.speed = self.speed_slider.value() / 10.0
        self._config.zone = self.zone_combo.currentData()

    def _sync_from_config(self) -> None:
        self.enable_check.setChecked(self._config.enabled)
        self.color_swatch.set_color(*self._config.color)
        effect_idx = self.effect_combo.findData(self._config.effect)
        if effect_idx >= 0:
            self.effect_combo.setCurrentIndex(effect_idx)
        self.bright_slider.setValue(self._config.brightness)
        self.speed_slider.setValue(int(self._config.speed * 10))
        zone_idx = self.zone_combo.findData(self._config.zone)
        if zone_idx >= 0:
            self.zone_combo.setCurrentIndex(zone_idx)
        self._update_labels()

    def get_config(self) -> RGBConfig:
        return self._config

    def set_config(self, config: RGBConfig) -> None:
        self._config = config
        self._sync_from_config()

    def load_from_dict(self, d: dict) -> None:
        self._config = RGBConfig.from_dict(d)
        self._sync_from_config()
