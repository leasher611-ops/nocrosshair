from typing import Dict, Any
from dataclasses import asdict
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QTabWidget
)
from PyQt6.QtGui import QFont

from nocrosshair.core.config import StickPhysicsConfig, TriggerPhysicsConfig
from nocrosshair.features.physics import (
    PhysicsTestbed,
    StickPhysicsEngine,
    StickPhysicsPresets,
    TriggerPhysicsPresets,
)
from nocrosshair.ui.widgets import (
    LabeledSlider, LabeledDoubleSlider, ResponseCurveWidget, PresetSelector,
    StickVisualizerWidget, HLine, SectionGroupBox
)
from nocrosshair.ui.widgets.advanced_physics_editor import AdvancedPhysicsEditor

class PhysicsTab(QWidget):

    config_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.stick_controls = {}
        self.trigger_controls = {}
        self.testbeds = {}
        self.setLayout(QVBoxLayout())
        self._init_ui()

    def _init_ui(self) -> None:
        title = QLabel("Physics Configuration")
        title.setObjectName("hudTitle")
        self.layout().addWidget(title)
        self.layout().addWidget(HLine())

        physics_tabs = QTabWidget()

        ls_widget = self._create_stick_tab("Left Stick", "ls_")
        physics_tabs.addTab(ls_widget, "Left Stick")

        rs_widget = self._create_stick_tab("Right Stick", "rs_")
        physics_tabs.addTab(rs_widget, "Right Stick")

        self.advanced_editor = AdvancedPhysicsEditor()
        self.advanced_editor.config_changed.connect(self._on_advanced_config_change)
        physics_tabs.addTab(self.advanced_editor, "Advanced")

        self.layout().addWidget(physics_tabs)

        trigger_group = SectionGroupBox("Trigger Physics")

        lt_section = self._create_trigger_section("LT", "lt_")
        trigger_group.layout().addWidget(lt_section)

        rt_section = self._create_trigger_section("RT", "rt_")
        trigger_group.layout().addWidget(rt_section)

        self.layout().addWidget(trigger_group)

        self.layout().addStretch()

    def _create_stick_tab(self, name: str, prefix: str) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout()

        preset_selector = PresetSelector("Preset", ["FPS", "Platformer", "Racing", "Simulation"])
        preset_selector.preset_changed.connect(lambda preset, p=prefix: self._apply_stick_preset(p, preset))
        layout.addWidget(preset_selector)

        same_xy_check = QCheckBox("Use Same X/Y Settings")
        same_xy_check.setChecked(True)
        same_xy_check.stateChanged.connect(self._on_physics_change)
        layout.addWidget(same_xy_check)

        layout.addWidget(HLine())

        defl_min = LabeledDoubleSlider("Deflection Min", 0.0, 0.5, 0.0, decimals=2)
        defl_min.value_changed.connect(self._on_physics_change)
        layout.addWidget(defl_min)

        defl_max = LabeledDoubleSlider("Deflection Max", 0.5, 1.0, 1.0, decimals=2)
        defl_max.value_changed.connect(self._on_physics_change)
        layout.addWidget(defl_max)

        init_spd = LabeledDoubleSlider("Initial Speed", 0.0, 1.0, 0.0, decimals=2)
        init_spd.value_changed.connect(self._on_physics_change)
        layout.addWidget(init_spd)

        accel = LabeledDoubleSlider("Acceleration", 0.5, 3.0, 1.0, decimals=2)
        accel.value_changed.connect(self._on_physics_change)
        layout.addWidget(accel)

        square_check = QCheckBox("Square Stick (Barrel Effect)")
        square_check.stateChanged.connect(self._on_physics_change)
        layout.addWidget(square_check)

        square_factor = LabeledDoubleSlider("Squaring Factor", 0.0, 1.0, 1.0, decimals=2)
        square_factor.value_changed.connect(self._on_physics_change)
        layout.addWidget(square_factor)

        anti_dz = LabeledSlider("Anti-Deadzone", 0, 50, 0)
        anti_dz.value_changed.connect(self._on_physics_change)
        layout.addWidget(anti_dz)

        raw_check = QCheckBox("Raw Mode (No Squaring)")
        raw_check.stateChanged.connect(self._on_physics_change)
        layout.addWidget(raw_check)

        curve_widget = ResponseCurveWidget()
        layout.addWidget(curve_widget)

        test_group = SectionGroupBox("Live Test")
        test_layout = QVBoxLayout()

        input_x = LabeledSlider("Input X", -32768, 32767, 16384)
        input_y = LabeledSlider("Input Y", -32768, 32767, 0)
        input_x.value_changed.connect(lambda value, p=prefix: self._refresh_stick_test(p))
        input_y.value_changed.connect(lambda value, p=prefix: self._refresh_stick_test(p))
        test_layout.addWidget(input_x)
        test_layout.addWidget(input_y)

        visual_layout = QHBoxLayout()
        input_visual = StickVisualizerWidget("Input")
        output_visual = StickVisualizerWidget("Output")
        visual_layout.addWidget(input_visual)
        visual_layout.addWidget(output_visual)
        test_layout.addLayout(visual_layout)

        output_label = QLabel("Output: 0, 0")
        output_label.setStyleSheet("color: #00E5FF; font-weight: 500;")
        test_layout.addWidget(output_label)

        test_group.layout().addLayout(test_layout)
        layout.addWidget(test_group)

        self.stick_controls[prefix] = {
            "preset": preset_selector,
            "use_same_xy": same_xy_check,
            "deflection_min": defl_min,
            "deflection_max": defl_max,
            "initial_speed": init_spd,
            "acceleration": accel,
            "square_stick": square_check,
            "squaring_factor": square_factor,
            "anti_deadzone": anti_dz,
            "raw_mode": raw_check,
            "curve": curve_widget,
            "input_x": input_x,
            "input_y": input_y,
            "input_visual": input_visual,
            "output_visual": output_visual,
            "output_label": output_label,
        }
        self.testbeds[prefix] = PhysicsTestbed(StickPhysicsEngine(self.get_stick_config(prefix)))
        self._refresh_stick_test(prefix)

        layout.addStretch()

        widget.setLayout(layout)
        return widget

    def _create_trigger_section(self, name: str, prefix: str) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout()

        label = QLabel(f"{name} Trigger")
        label.setFont(QFont("monospace", 10, QFont.Weight.Bold))
        layout.addWidget(label)

        preset = PresetSelector("Preset", ["Normal", "Hair", "Sensitive"])
        preset.preset_changed.connect(lambda preset_name, p=prefix: self._apply_trigger_preset(p, preset_name))
        layout.addWidget(preset)

        deadzone = LabeledDoubleSlider("Deadzone", 0.0, 0.3, 0.05, decimals=2)
        deadzone.value_changed.connect(self._on_physics_change)
        layout.addWidget(deadzone)

        sensitivity = LabeledDoubleSlider("Sensitivity", 0.5, 2.0, 1.0, decimals=2)
        sensitivity.value_changed.connect(self._on_physics_change)
        layout.addWidget(sensitivity)

        hair_check = QCheckBox("Hair Trigger (Binary)")
        hair_check.stateChanged.connect(self._on_physics_change)
        layout.addWidget(hair_check)

        self.trigger_controls[prefix] = {
            "preset": preset,
            "deadzone": deadzone,
            "sensitivity": sensitivity,
            "hair_trigger": hair_check,
        }

        widget.setLayout(layout)
        return widget

    def get_stick_config(self, prefix: str = "ls_") -> StickPhysicsConfig:
        return StickPhysicsConfig.from_dict(self.get_config(), prefix)

    def get_trigger_config(self, prefix: str = "lt_") -> TriggerPhysicsConfig:
        return TriggerPhysicsConfig.from_dict(self.get_config(), prefix)

    def get_config(self) -> Dict[str, Any]:
        config = {}
        for prefix, controls in self.stick_controls.items():
            config[f"{prefix}preset"] = controls["preset"].currentPreset()
            config[f"{prefix}use_same_xy"] = controls["use_same_xy"].isChecked()
            config[f"{prefix}deflection_min"] = controls["deflection_min"].value()
            config[f"{prefix}deflection_max"] = controls["deflection_max"].value()
            config[f"{prefix}initial_speed"] = controls["initial_speed"].value()
            config[f"{prefix}acceleration"] = controls["acceleration"].value()
            config[f"{prefix}square_stick"] = controls["square_stick"].isChecked()
            config[f"{prefix}squaring_factor"] = controls["squaring_factor"].value()
            config[f"{prefix}anti_deadzone"] = controls["anti_deadzone"].value()
            config[f"{prefix}raw_mode"] = controls["raw_mode"].isChecked()

        for prefix, controls in self.trigger_controls.items():
            config[f"{prefix}preset"] = controls["preset"].currentPreset()
            config[f"{prefix}deadzone"] = controls["deadzone"].value()
            config[f"{prefix}sensitivity"] = controls["sensitivity"].value()
            config[f"{prefix}hair_trigger"] = controls["hair_trigger"].isChecked()

        if hasattr(self, 'advanced_editor'):
            config["advanced"] = self.advanced_editor.get_config()

        return config

    def set_config(self, config: Dict[str, Any]) -> None:
        for prefix, controls in self.stick_controls.items():
            if f"{prefix}preset" in config:
                controls["preset"].setPreset(config[f"{prefix}preset"])
            if f"{prefix}use_same_xy" in config:
                controls["use_same_xy"].setChecked(config[f"{prefix}use_same_xy"])
            if f"{prefix}deflection_min" in config:
                controls["deflection_min"].setValue(config[f"{prefix}deflection_min"])
            if f"{prefix}deflection_max" in config:
                controls["deflection_max"].setValue(config[f"{prefix}deflection_max"])
            if f"{prefix}initial_speed" in config:
                controls["initial_speed"].setValue(config[f"{prefix}initial_speed"])
            if f"{prefix}acceleration" in config:
                controls["acceleration"].setValue(config[f"{prefix}acceleration"])
            if f"{prefix}square_stick" in config:
                controls["square_stick"].setChecked(config[f"{prefix}square_stick"])
            if f"{prefix}squaring_factor" in config:
                controls["squaring_factor"].setValue(config[f"{prefix}squaring_factor"])
            if f"{prefix}anti_deadzone" in config:
                controls["anti_deadzone"].setValue(config[f"{prefix}anti_deadzone"])
            if f"{prefix}raw_mode" in config:
                controls["raw_mode"].setChecked(config[f"{prefix}raw_mode"])

            self._refresh_stick_test(prefix)

        for prefix, controls in self.trigger_controls.items():
            if f"{prefix}preset" in config:
                controls["preset"].setPreset(config[f"{prefix}preset"])
            if f"{prefix}deadzone" in config:
                controls["deadzone"].setValue(config[f"{prefix}deadzone"])
            if f"{prefix}sensitivity" in config:
                controls["sensitivity"].setValue(config[f"{prefix}sensitivity"])
            if f"{prefix}hair_trigger" in config:
                controls["hair_trigger"].setChecked(config[f"{prefix}hair_trigger"])

        if "advanced" in config and hasattr(self, 'advanced_editor'):
            self.advanced_editor.set_config(config["advanced"])

        self._on_physics_change()

    def _on_physics_change(self, *args) -> None:
        for prefix in self.stick_controls:
            self._refresh_stick_test(prefix)
        self.config_changed.emit(self.get_config())

    def _on_advanced_config_change(self, *args) -> None:
        self.config_changed.emit(self.get_config())

    def _refresh_stick_test(self, prefix: str) -> None:
        controls = self.stick_controls.get(prefix)
        if not controls:
            return

        cfg = self.get_stick_config(prefix)
        testbed = self.testbeds.get(prefix)
        if testbed is None:
            testbed = PhysicsTestbed(StickPhysicsEngine(cfg))
            self.testbeds[prefix] = testbed
        else:
            testbed.apply_config(cfg)

        controls["curve"].set_params(
            cfg.acceleration,
            cfg.deflection_min,
            cfg.deflection_max,
            cfg.initial_speed,
        )

        input_x = controls["input_x"].value()
        input_y = controls["input_y"].value()
        output_x, output_y = testbed.simulate_input(input_x, input_y)

        controls["input_visual"].set_position(input_x, input_y)
        controls["output_visual"].set_position(output_x, output_y)
        controls["output_label"].setText(f"Output: {output_x}, {output_y}")

    def _apply_stick_preset(self, prefix: str, preset: str) -> None:
        preset_map = {
            "FPS": StickPhysicsPresets.fps,
            "Platformer": StickPhysicsPresets.platformer,
            "Racing": StickPhysicsPresets.racing,
            "Simulation": StickPhysicsPresets.simulation,
        }
        if preset not in preset_map:
            return

        self._set_stick_config(prefix, preset_map[preset]())

    def _set_stick_config(self, prefix: str, cfg: StickPhysicsConfig) -> None:
        config = {}
        for key, value in asdict(cfg).items():
            config[f"{prefix}{key}"] = value
        self.set_config(config)

    def _apply_trigger_preset(self, prefix: str, preset: str) -> None:
        preset_map = {
            "Normal": TriggerPhysicsPresets.normal,
            "Hair": TriggerPhysicsPresets.hair,
            "Sensitive": TriggerPhysicsPresets.sensitive,
        }
        if preset not in preset_map:
            return

        cfg = preset_map[preset]()
        self.set_config({
            f"{prefix}deadzone": cfg.deadzone,
            f"{prefix}sensitivity": cfg.sensitivity,
            f"{prefix}hair_trigger": cfg.hair_trigger,
        })
