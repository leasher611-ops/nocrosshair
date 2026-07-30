from typing import Optional
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QComboBox, QCheckBox,
    QHBoxLayout, QLabel, QSlider
)

from nocrosshair.features.triggers import TriggerConfig, TriggerModeType


class TriggerConfigWidget(QWidget):

    config_changed = pyqtSignal(object)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._config = TriggerConfig()
        self.setLayout(QVBoxLayout())
        self._init_ui()
        self._sync_from_config()

    def _init_ui(self) -> None:
        group = QGroupBox("Trigger Configuration")
        layout = QVBoxLayout()

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Mode"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Analog", TriggerModeType.ANALOG)
        self.mode_combo.addItem("Digital", TriggerModeType.DIGITAL)
        self.mode_combo.addItem("Hybrid", TriggerModeType.HYBRID)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode_row.addWidget(self.mode_combo)
        layout.addLayout(mode_row)

        stop_row = QHBoxLayout()
        stop_row.addWidget(QLabel("Trigger Stop Position"))
        self.stop_slider = QSlider(Qt.Orientation.Horizontal)
        self.stop_slider.setMinimum(0)
        self.stop_slider.setMaximum(100)
        self.stop_slider.setValue(85)
        self.stop_slider.valueChanged.connect(self._on_change)
        stop_row.addWidget(self.stop_slider)
        self.stop_label = QLabel("0.85")
        self.stop_label.setMinimumWidth(40)
        self.stop_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        stop_row.addWidget(self.stop_label)
        layout.addLayout(stop_row)

        self.rapid_check = QCheckBox("Rapid Trigger")
        self.rapid_check.stateChanged.connect(self._on_change)
        layout.addWidget(self.rapid_check)

        rapid_sens_row = QHBoxLayout()
        rapid_sens_row.addWidget(QLabel("Rapid Sensitivity"))
        self.rapid_sens_slider = QSlider(Qt.Orientation.Horizontal)
        self.rapid_sens_slider.setMinimum(1)
        self.rapid_sens_slider.setMaximum(100)
        self.rapid_sens_slider.setValue(50)
        self.rapid_sens_slider.valueChanged.connect(self._on_change)
        rapid_sens_row.addWidget(self.rapid_sens_slider)
        self.rapid_sens_label = QLabel("50")
        self.rapid_sens_label.setMinimumWidth(40)
        self.rapid_sens_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        rapid_sens_row.addWidget(self.rapid_sens_label)
        layout.addLayout(rapid_sens_row)

        deadzone_row = QHBoxLayout()
        deadzone_row.addWidget(QLabel("Analog Deadzone"))
        self.deadzone_slider = QSlider(Qt.Orientation.Horizontal)
        self.deadzone_slider.setMinimum(0)
        self.deadzone_slider.setMaximum(255)
        self.deadzone_slider.setValue(5)
        self.deadzone_slider.valueChanged.connect(self._on_change)
        deadzone_row.addWidget(self.deadzone_slider)
        self.deadzone_label = QLabel("5")
        self.deadzone_label.setMinimumWidth(40)
        self.deadzone_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        deadzone_row.addWidget(self.deadzone_label)
        layout.addLayout(deadzone_row)

        analog_max_row = QHBoxLayout()
        analog_max_row.addWidget(QLabel("Analog Max"))
        self.analog_max_slider = QSlider(Qt.Orientation.Horizontal)
        self.analog_max_slider.setMinimum(255)
        self.analog_max_slider.setMaximum(1023)
        self.analog_max_slider.setValue(1023)
        self.analog_max_slider.valueChanged.connect(self._on_change)
        analog_max_row.addWidget(self.analog_max_slider)
        self.analog_max_label = QLabel("1023")
        self.analog_max_label.setMinimumWidth(40)
        self.analog_max_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        analog_max_row.addWidget(self.analog_max_label)
        layout.addLayout(analog_max_row)

        group_layout = QVBoxLayout(group)
        group_layout.addLayout(layout)
        self.layout().addWidget(group)

    def _on_mode_changed(self, idx: int) -> None:
        mode = self.mode_combo.currentData()
        is_hybrid = mode == TriggerModeType.HYBRID
        self.stop_slider.setVisible(is_hybrid)
        self.stop_label.setVisible(is_hybrid)
        self._on_change()

    def _on_change(self) -> None:
        self._update_labels()
        self._flush_to_config()
        self.config_changed.emit(self._config)

    def _update_labels(self) -> None:
        stop_val = self.stop_slider.value() / 100.0
        self.stop_label.setText(f"{stop_val:.2f}")
        self.rapid_sens_label.setText(str(self.rapid_sens_slider.value()))
        self.deadzone_label.setText(str(self.deadzone_slider.value()))
        self.analog_max_label.setText(str(self.analog_max_slider.value()))

    def _flush_to_config(self) -> None:
        self._config.mode = self.mode_combo.currentData()
        self._config.stop_position = self.stop_slider.value() / 100.0
        self._config.rapid_trigger_enabled = self.rapid_check.isChecked()
        self._config.rapid_trigger_sensitivity = self.rapid_sens_slider.value()
        self._config.analog_deadzone = self.deadzone_slider.value()
        self._config.analog_max = self.analog_max_slider.value()

    def _sync_from_config(self) -> None:
        mode_idx = self.mode_combo.findData(self._config.mode)
        if mode_idx >= 0:
            self.mode_combo.setCurrentIndex(mode_idx)
        self.stop_slider.setValue(int(self._config.stop_position * 100))
        self.rapid_check.setChecked(self._config.rapid_trigger_enabled)
        self.rapid_sens_slider.setValue(self._config.rapid_trigger_sensitivity)
        self.deadzone_slider.setValue(self._config.analog_deadzone)
        self.analog_max_slider.setValue(self._config.analog_max)
        self._update_labels()
        self._on_mode_changed(self.mode_combo.currentIndex())

    def get_config(self) -> TriggerConfig:
        return self._config

    def set_config(self, config: TriggerConfig) -> None:
        self._config = config
        self._sync_from_config()

    def load_from_dict(self, d: dict) -> None:
        self._config = TriggerConfig.from_dict(d)
        self._sync_from_config()
