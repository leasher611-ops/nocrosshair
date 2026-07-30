from typing import Dict, Any, List, Tuple, Optional
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QCheckBox, QPushButton, QGroupBox, QGridLayout, QSpinBox
)
from PyQt6.QtGui import QFont

from nocrosshair.ui.widgets import LabeledSlider, SectionGroupBox, HLine
from nocrosshair.ui.widgets.bezier_curve_editor import BezierCurveEditorWithControls
from nocrosshair.core.weapon_curves import weapon_curves_manager

class AdvancedPhysicsEditor(QWidget):

    config_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("Advanced Physics Configuration")
        title.setFont(QFont("monospace", 10, QFont.Weight.Bold))
        title.setStyleSheet("color: #00ff88")
        layout.addWidget(title)

        layout.addWidget(HLine())

        self.advanced_check = QCheckBox("Enable Advanced Mode")
        self.advanced_check.stateChanged.connect(self._on_config_change)
        layout.addWidget(self.advanced_check)

        self.advanced_widget = QWidget()
        self.advanced_layout = QVBoxLayout(self.advanced_widget)
        self.advanced_layout.setContentsMargins(0, 0, 0, 0)

        self._init_multi_curve_section()
        self._init_per_weapon_section()
        self._init_advanced_testing_section()

        layout.addWidget(self.advanced_widget)
        layout.addStretch()

        self._update_advanced_visibility()

    def _init_multi_curve_section(self) -> None:
        multi_curve_group = SectionGroupBox("Multi-Curve Configuration")

        self.axis_combo = QComboBox()
        self.axis_combo.addItems(["X-Axis (Horizontal)", "Y-Axis (Vertical)", "Both Axes"])
        self.axis_combo.currentTextChanged.connect(self._on_config_change)
        multi_curve_group.layout().addWidget(QLabel("Configure curve for:"))
        multi_curve_group.layout().addWidget(self.axis_combo)

        self.curve_editor = BezierCurveEditorWithControls()
        self.curve_editor.curve_changed.connect(self._on_config_change)
        multi_curve_group.layout().addWidget(self.curve_editor)

        self.speed_based_check = QCheckBox("Speed-based curves (different curves for different speeds)")
        self.speed_based_check.stateChanged.connect(self._on_config_change)
        multi_curve_group.layout().addWidget(self.speed_based_check)

        speed_group = QGroupBox("Speed Thresholds")
        speed_layout = QGridLayout()

        speed_layout.addWidget(QLabel("Low Speed:"), 0, 0)
        self.low_speed_slider = LabeledSlider("Low", 0, 50, 20)
        self.low_speed_slider.value_changed.connect(self._on_config_change)
        speed_layout.addWidget(self.low_speed_slider, 0, 1)

        speed_layout.addWidget(QLabel("Medium Speed:"), 1, 0)
        self.med_speed_slider = LabeledSlider("Med", 20, 80, 50)
        self.med_speed_slider.value_changed.connect(self._on_config_change)
        speed_layout.addWidget(self.med_speed_slider, 1, 1)

        speed_layout.addWidget(QLabel("High Speed:"), 2, 0)
        self.high_speed_slider = LabeledSlider("High", 50, 100, 80)
        self.high_speed_slider.value_changed.connect(self._on_config_change)
        speed_layout.addWidget(self.high_speed_slider, 2, 1)

        speed_group.setLayout(speed_layout)
        multi_curve_group.layout().addWidget(speed_group)

        self.advanced_layout.addWidget(multi_curve_group)

    def _init_per_weapon_section(self) -> None:
        weapon_group = SectionGroupBox("Per-Weapon Profiles")

        weapon_group.layout().addWidget(QLabel("Select weapon profile to edit:"))
        self.weapon_selector = QComboBox()
        self.weapon_selector.addItems([
            "Default", "AR", "SMG", "Shotgun", "Sniper", "Pistol", "LMG"
        ])
        self.weapon_selector.currentTextChanged.connect(self._on_weapon_changed)
        weapon_group.layout().addWidget(self.weapon_selector)

        self.weapon_enabled_check = QCheckBox("Enable per-weapon curves")
        self.weapon_enabled_check.stateChanged.connect(self._on_config_change)
        weapon_group.layout().addWidget(self.weapon_enabled_check)

        weapon_info_layout = QHBoxLayout()

        weapon_info_layout.addWidget(QLabel("Current weapon:"))
        self.weapon_label = QLabel("Default")
        self.weapon_label.setStyleSheet("color: #ffcc00")
        weapon_info_layout.addWidget(self.weapon_label)

        weapon_info_layout.addStretch()

        load_btn = QPushButton("Load from Preset")
        load_btn.clicked.connect(self._load_weapon_preset)
        weapon_info_layout.addWidget(load_btn)

        save_btn = QPushButton("Save as Preset")
        save_btn.clicked.connect(self._save_weapon_preset)
        weapon_info_layout.addWidget(save_btn)

        weapon_group.layout().addLayout(weapon_info_layout)

        self.advanced_layout.addWidget(weapon_group)

    def _init_advanced_testing_section(self) -> None:
        test_group = SectionGroupBox("Advanced Testing")

        test_group.layout().addWidget(QLabel("Test different curves with input simulation:"))

        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Input Value:"))
        self.test_input_slider = LabeledSlider("Input", 0, 100, 50)
        input_layout.addWidget(self.test_input_slider)
        test_group.layout().addLayout(input_layout)

        result_layout = QHBoxLayout()
        result_layout.addWidget(QLabel("Output (X-Axis):"))
        self.output_x_label = QLabel("50.0")
        self.output_x_label.setStyleSheet("color: #00ff88")
        result_layout.addWidget(self.output_x_label)

        result_layout.addWidget(QLabel("Output (Y-Axis):"))
        self.output_y_label = QLabel("50.0")
        self.output_y_label.setStyleSheet("color: #00ff88")
        result_layout.addWidget(self.output_y_label)
        test_group.layout().addLayout(result_layout)

        self.advanced_layout.addWidget(test_group)

    def _update_advanced_visibility(self) -> None:
        is_advanced = self.advanced_check.isChecked()
        self.advanced_widget.setVisible(is_advanced)

    def _on_config_change(self, *args) -> None:
        self._update_advanced_visibility()
        self.config_changed.emit(self.get_config())

    def _on_weapon_changed(self, weapon: str) -> None:
        self.weapon_label.setText(weapon)
        self._on_config_change()

    def _load_weapon_preset(self) -> None:
        weapon = self.weapon_selector.currentText()
        curve_data = weapon_curves_manager.get_weapon_curve(weapon)

        if "curve_x" in curve_data:
            self.curve_editor.set_curve(curve_data["curve_x"])

        self._on_config_change()

    def _save_weapon_preset(self) -> None:
        weapon = self.weapon_selector.currentText()
        curve_data = {
            "curve_x": self.curve_editor.get_curve(),
            "curve_y": self.curve_editor.get_curve(),
            "acceleration": 1.0,
            "deadzone": 0.0,
        }
        weapon_curves_manager.set_weapon_curve(weapon, curve_data)
        weapon_curves_manager.save_to_file()
        self._on_config_change()

    def get_config(self) -> Dict[str, Any]:
        return {
            "advanced_enabled": self.advanced_check.isChecked(),
            "multi_curve": {
                "axis": self.axis_combo.currentText(),
                "curve_points": self.curve_editor.get_curve(),
                "speed_based": self.speed_based_check.isChecked(),
                "speed_thresholds": {
                    "low": self.low_speed_slider.value(),
                    "medium": self.med_speed_slider.value(),
                    "high": self.high_speed_slider.value()
                }
            },
            "per_weapon": {
                "enabled": self.weapon_enabled_check.isChecked(),
                "current_weapon": self.weapon_selector.currentText(),
            }
        }

    def set_config(self, config: Dict[str, Any]) -> None:
        if "advanced_enabled" in config:
            self.advanced_check.setChecked(config["advanced_enabled"])

        if "multi_curve" in config:
            mc = config["multi_curve"]
            if "axis" in mc:
                self.axis_combo.setCurrentText(mc["axis"])
            if "curve_points" in mc:
                self.curve_editor.set_curve(mc["curve_points"])
            if "speed_based" in mc:
                self.speed_based_check.setChecked(mc["speed_based"])
            if "speed_thresholds" in mc:
                st = mc["speed_thresholds"]
                if "low" in st:
                    self.low_speed_slider.setValue(st["low"])
                if "medium" in st:
                    self.med_speed_slider.setValue(st["medium"])
                if "high" in st:
                    self.high_speed_slider.setValue(st["high"])

        if "per_weapon" in config:
            pw = config["per_weapon"]
            if "enabled" in pw:
                self.weapon_enabled_check.setChecked(pw["enabled"])
            if "current_weapon" in pw:
                self.weapon_selector.setCurrentText(pw["current_weapon"])
