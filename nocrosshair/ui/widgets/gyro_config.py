from typing import Optional
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QComboBox, QCheckBox,
    QHBoxLayout, QLabel, QSlider, QPushButton, QProgressBar
)

from nocrosshair.features.gyro import GyroConfig, GyroAimMode, GyroCalibrator


class GyroConfigWidget(QWidget):

    config_changed = pyqtSignal(object)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._config = GyroConfig()
        self._calibrating = False
        self.setLayout(QVBoxLayout())
        self._init_ui()
        self._sync_from_config()

    def _init_ui(self) -> None:
        group = QGroupBox("Gyroscope / Motion Aim")
        layout = QVBoxLayout()

        self.enable_check = QCheckBox("Enable Gyro")
        self.enable_check.stateChanged.connect(self._on_change)
        layout.addWidget(self.enable_check)

        aim_row = QHBoxLayout()
        aim_row.addWidget(QLabel("Aim Mode"))
        self.aim_combo = QComboBox()
        self.aim_combo.addItem("Disabled", GyroAimMode.DISABLED)
        self.aim_combo.addItem("Mouse", GyroAimMode.MOUSE)
        self.aim_combo.addItem("Stick", GyroAimMode.STICK)
        self.aim_combo.addItem("Hybrid", GyroAimMode.HYBRID)
        self.aim_combo.currentIndexChanged.connect(self._on_change)
        aim_row.addWidget(self.aim_combo)
        layout.addLayout(aim_row)

        sens_row = QHBoxLayout()
        sens_row.addWidget(QLabel("Sensitivity"))
        self.sens_slider = QSlider(Qt.Orientation.Horizontal)
        self.sens_slider.setMinimum(1)
        self.sens_slider.setMaximum(100)
        self.sens_slider.setValue(10)
        self.sens_slider.valueChanged.connect(self._on_change)
        sens_row.addWidget(self.sens_slider)
        self.sens_label = QLabel("1.0")
        self.sens_label.setMinimumWidth(40)
        self.sens_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        sens_row.addWidget(self.sens_label)
        layout.addLayout(sens_row)

        smooth_row = QHBoxLayout()
        smooth_row.addWidget(QLabel("Smoothing"))
        self.smooth_slider = QSlider(Qt.Orientation.Horizontal)
        self.smooth_slider.setMinimum(0)
        self.smooth_slider.setMaximum(100)
        self.smooth_slider.setValue(50)
        self.smooth_slider.valueChanged.connect(self._on_change)
        smooth_row.addWidget(self.smooth_slider)
        self.smooth_label = QLabel("50")
        self.smooth_label.setMinimumWidth(40)
        self.smooth_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        smooth_row.addWidget(self.smooth_label)
        layout.addLayout(smooth_row)

        deadzone_row = QHBoxLayout()
        deadzone_row.addWidget(QLabel("Deadzone"))
        self.deadzone_slider = QSlider(Qt.Orientation.Horizontal)
        self.deadzone_slider.setMinimum(0)
        self.deadzone_slider.setMaximum(50)
        self.deadzone_slider.setValue(2)
        self.deadzone_slider.valueChanged.connect(self._on_change)
        deadzone_row.addWidget(self.deadzone_slider)
        self.deadzone_label = QLabel("2")
        self.deadzone_label.setMinimumWidth(40)
        self.deadzone_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        deadzone_row.addWidget(self.deadzone_label)
        layout.addLayout(deadzone_row)

        space_row = QHBoxLayout()
        space_row.addWidget(QLabel("Coordinate Space"))
        self.space_combo = QComboBox()
        self.space_combo.addItem("Local", "local")
        self.space_combo.addItem("World", "world")
        self.space_combo.currentIndexChanged.connect(self._on_change)
        space_row.addWidget(self.space_combo)
        layout.addLayout(space_row)

        self.invert_y_check = QCheckBox("Invert Y")
        self.invert_y_check.stateChanged.connect(self._on_change)
        layout.addWidget(self.invert_y_check)

        self.invert_x_check = QCheckBox("Invert X")
        self.invert_x_check.stateChanged.connect(self._on_change)
        layout.addWidget(self.invert_x_check)

        self.rot_comp_check = QCheckBox("Rotation Compensation")
        self.rot_comp_check.setChecked(True)
        self.rot_comp_check.stateChanged.connect(self._on_change)
        layout.addWidget(self.rot_comp_check)

        cal_row = QHBoxLayout()
        self.calibrate_btn = QPushButton("Calibrate Gyro")
        self.calibrate_btn.clicked.connect(self._on_calibrate)
        cal_row.addWidget(self.calibrate_btn)
        self.cal_progress = QProgressBar()
        self.cal_progress.setRange(0, 100)
        self.cal_progress.setValue(0)
        self.cal_progress.setVisible(False)
        cal_row.addWidget(self.cal_progress)
        layout.addLayout(cal_row)

        group_layout = QVBoxLayout(group)
        group_layout.addLayout(layout)
        self.layout().addWidget(group)

    def _on_calibrate(self) -> None:
        if self._calibrating:
            return
        self._calibrating = True
        self.calibrate_btn.setEnabled(False)
        self.cal_progress.setVisible(True)
        self.cal_progress.setValue(0)
        self._cal_timer = QTimer(self)
        self._cal_step = 0
        self._cal_timer.timeout.connect(self._cal_tick)
        self._cal_timer.start(20)

    def _cal_tick(self) -> None:
        self._cal_step += 1
        self.cal_progress.setValue(min(self._cal_step, 100))
        if self._cal_step >= 100:
            self._cal_timer.stop()
            self._calibrating = False
            self.calibrate_btn.setEnabled(True)
            self.cal_progress.setVisible(False)
            self.config_changed.emit(self._config)

    def _on_change(self) -> None:
        self._update_labels()
        self._flush_to_config()
        self.config_changed.emit(self._config)

    def _update_labels(self) -> None:
        sens_val = self.sens_slider.value() / 10.0
        self.sens_label.setText(f"{sens_val:.1f}")
        self.smooth_label.setText(str(self.smooth_slider.value()))
        self.deadzone_label.setText(str(self.deadzone_slider.value()))

    def _flush_to_config(self) -> None:
        self._config.enabled = self.enable_check.isChecked()
        self._config.aim_mode = self.aim_combo.currentData()
        self._config.sensitivity = self.sens_slider.value() / 10.0
        self._config.smoothing = self.smooth_slider.value() / 100.0
        self._config.deadzone = self.deadzone_slider.value() / 32767.0
        self._config.space = self.space_combo.currentData()
        self._config.invert_y = self.invert_y_check.isChecked()
        self._config.invert_x = self.invert_x_check.isChecked()
        self._config.rotation_compensation = self.rot_comp_check.isChecked()

    def _sync_from_config(self) -> None:
        self.enable_check.setChecked(self._config.enabled)
        mode_idx = self.aim_combo.findData(self._config.aim_mode)
        if mode_idx >= 0:
            self.aim_combo.setCurrentIndex(mode_idx)
        self.sens_slider.setValue(int(self._config.sensitivity * 10))
        self.smooth_slider.setValue(int(self._config.smoothing * 100))
        dz = int(self._config.deadzone * 32767)
        self.deadzone_slider.setValue(min(dz, 50))
        space_idx = self.space_combo.findData(self._config.space)
        if space_idx >= 0:
            self.space_combo.setCurrentIndex(space_idx)
        self.invert_y_check.setChecked(self._config.invert_y)
        self.invert_x_check.setChecked(self._config.invert_x)
        self.rot_comp_check.setChecked(self._config.rotation_compensation)
        self._update_labels()

    def get_config(self) -> GyroConfig:
        return self._config

    def set_config(self, config: GyroConfig) -> None:
        self._config = config
        self._sync_from_config()

    def load_from_dict(self, d: dict) -> None:
        self._config = GyroConfig.from_dict(d)
        self._sync_from_config()
