import json
import os
from typing import Dict, Any, List
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QCheckBox, QHBoxLayout,
    QComboBox, QPushButton, QFileDialog
)

from nocrosshair.core.config import RECOIL_PRESETS, WEAPON_CATEGORIES
from nocrosshair.features.recoil import RecoilEngine, RecoilTestbed
from nocrosshair.ui.widgets import (
    LabeledSlider, LabeledDoubleSlider, PresetSelector, ResponseCurveWidget, StickVisualizerWidget,
    HLine, SectionGroupBox, RecoilCurvePreview
)

class RecoilTab(QWidget):

    config_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.testbed = RecoilTestbed(RecoilEngine())
        self.setLayout(QVBoxLayout())
        self._init_ui()

    def _init_ui(self) -> None:
        title = QLabel("Recoil Control")
        title.setObjectName("hudTitle")
        self.layout().addWidget(title)
        self.layout().addWidget(HLine())

        self.enable_check = QCheckBox("Enable Recoil Control")
        self.enable_check.setChecked(True)
        self.enable_check.stateChanged.connect(self._on_config_change)
        self.layout().addWidget(self.enable_check)

        weapon_group = SectionGroupBox("Weapon Presets")
        weapon_layout = QVBoxLayout()

        cat_row = QHBoxLayout()
        cat_label = QLabel("Category")
        cat_label.setMinimumWidth(100)
        cat_row.addWidget(cat_label)
        self.category_combo = QComboBox()
        self.category_combo.addItems(WEAPON_CATEGORIES)
        self.category_combo.currentTextChanged.connect(self._on_category_changed)
        cat_row.addWidget(self.category_combo)
        weapon_layout.addLayout(cat_row)

        self.weapon_selector = PresetSelector("Weapon", self._weapons_for_category("AR"))
        self.weapon_selector.preset_changed.connect(self._apply_weapon_preset)
        weapon_layout.addWidget(self.weapon_selector)

        slots_label = QLabel("Loadout Slots (auto-switch with F / 1-5 / Y / scroll)")
        slots_label.setObjectName("hudSubLabel")
        weapon_layout.addWidget(slots_label)

        all_weapons = sorted(
            RECOIL_PRESETS.keys(),
            key=lambda w: (RECOIL_PRESETS[w].get("category", ""), w),
        )
        self.loadout_combos = []
        for i in range(1, 6):
            row = QHBoxLayout()
            lbl = QLabel(f"Slot {i}")
            lbl.setMinimumWidth(100)
            row.addWidget(lbl)
            combo = QComboBox()
            combo.addItems(all_weapons)
            combo.currentTextChanged.connect(self._on_config_change)
            row.addWidget(combo)
            weapon_layout.addLayout(row)
            self.loadout_combos.append(combo)

        btn_row = QHBoxLayout()
        self.save_preset_btn = QPushButton("Save Recoil Preset")
        self.save_preset_btn.clicked.connect(self._save_recoil_preset)
        btn_row.addWidget(self.save_preset_btn)
        self.load_preset_btn = QPushButton("Load Recoil Preset")
        self.load_preset_btn.clicked.connect(self._load_recoil_preset)
        btn_row.addWidget(self.load_preset_btn)
        weapon_layout.addLayout(btn_row)

        weapon_group.layout().addLayout(weapon_layout)
        self.layout().addWidget(weapon_group)

        self.curve_preview = RecoilCurvePreview()
        self.layout().addWidget(self.curve_preview)

        params_group = SectionGroupBox("Recoil Parameters")
        params_layout = QVBoxLayout()

        self.simple_mode_check = QCheckBox("Simple Mode (puxada constante, estilo script G-Hub)")
        self.simple_mode_check.setChecked(False)
        self.simple_mode_check.stateChanged.connect(self._on_config_change)
        params_layout.addWidget(self.simple_mode_check)

        self.simple_rate_slider = LabeledSlider("Pull Rate (px / 7ms)", 0, 20, 4)
        self.simple_rate_slider.value_changed.connect(self._on_config_change)
        params_layout.addWidget(self.simple_rate_slider)

        self.strength_slider = LabeledSlider("Strength", 0, 100, 65)
        self.strength_slider.value_changed.connect(self._on_config_change)
        params_layout.addWidget(self.strength_slider)

        self.x_strength_slider = LabeledSlider("X-Axis Strength", 0, 50, 0)
        self.x_strength_slider.value_changed.connect(self._on_config_change)
        params_layout.addWidget(self.x_strength_slider)

        self.ticks_slider = LabeledSlider("Recoil Ticks", 10, 120, 60)
        self.ticks_slider.value_changed.connect(self._on_config_change)
        params_layout.addWidget(self.ticks_slider)

        self.delay_slider = LabeledSlider("Delay (ms)", 0, 200, 45)
        self.delay_slider.value_changed.connect(self._on_config_change)
        params_layout.addWidget(self.delay_slider)

        self.return_speed_selector = PresetSelector("Return Speed", ["Slow (0.5)", "Normal (0.7)", "Fast (0.9)"])
        self.return_speed_selector.preset_changed.connect(self._on_config_change)
        params_layout.addWidget(self.return_speed_selector)

        self.curve_selector = PresetSelector("Curve Type", ["Linear", "Ease-In", "Ease-Out"])
        self.curve_selector.preset_changed.connect(self._on_config_change)
        params_layout.addWidget(self.curve_selector)

        self.initial_kick_slider = LabeledDoubleSlider("Initial Kick (1.0 = off, 2.0 = dobro no 1º tiro)", 1.0, 2.0, 1.0, decimals=2)
        self.initial_kick_slider.value_changed.connect(self._on_config_change)
        params_layout.addWidget(self.initial_kick_slider)

        self.initial_kick_ticks_slider = LabeledSlider("Initial Kick Ticks", 1, 30, 6)
        self.initial_kick_ticks_slider.value_changed.connect(self._on_config_change)
        params_layout.addWidget(self.initial_kick_ticks_slider)

        params_group.layout().addLayout(params_layout)
        self.layout().addWidget(params_group)

        adv_group = SectionGroupBox("Advanced Options")
        adv_layout = QVBoxLayout()

        self.y_gate_check = QCheckBox("Y-Axis Gate (reduce if aiming up)")
        self.y_gate_check.setChecked(True)
        self.y_gate_check.stateChanged.connect(self._on_config_change)
        adv_layout.addWidget(self.y_gate_check)

        self.headshot_assist_check = QCheckBox("Headshot Assist (puxa pra cima no hipfire, estilo Zen)")
        self.headshot_assist_check.setChecked(False)
        self.headshot_assist_check.stateChanged.connect(self._on_config_change)
        adv_layout.addWidget(self.headshot_assist_check)

        self.headshot_assist_slider = LabeledSlider("Headshot Assist Pull", 0, 3000, 700)
        self.headshot_assist_slider.value_changed.connect(self._on_config_change)
        adv_layout.addWidget(self.headshot_assist_slider)

        self.curve_widget = ResponseCurveWidget()
        adv_layout.addWidget(self.curve_widget)

        adv_group.layout().addLayout(adv_layout)
        self.layout().addWidget(adv_group)

        test_group = SectionGroupBox("Shooting Simulator")
        test_layout = QVBoxLayout()

        self.tick_slider = LabeledSlider("Tick", 0, 120, 0)
        self.tick_slider.value_changed.connect(self._refresh_test)
        test_layout.addWidget(self.tick_slider)

        self.raw_rx_slider = LabeledSlider("Aim X", -32768, 32767, 0)
        self.raw_rx_slider.value_changed.connect(self._refresh_test)
        test_layout.addWidget(self.raw_rx_slider)

        self.raw_ry_slider = LabeledSlider("Aim Y", -32768, 32767, 0)
        self.raw_ry_slider.value_changed.connect(self._refresh_test)
        test_layout.addWidget(self.raw_ry_slider)

        visual_layout = QHBoxLayout()
        self.aim_visual = StickVisualizerWidget("Aim")
        self.recoil_visual = StickVisualizerWidget("Recoil Offset")
        visual_layout.addWidget(self.aim_visual)
        visual_layout.addWidget(self.recoil_visual)
        test_layout.addLayout(visual_layout)

        self.output_label = QLabel("Offset: 0, 0")
        self.output_label.setStyleSheet("color: #00ff88")
        test_layout.addWidget(self.output_label)

        self.pattern_label = QLabel("Pattern: --")
        self.pattern_label.setStyleSheet("color: #ffcc00")
        test_layout.addWidget(self.pattern_label)

        test_group.layout().addLayout(test_layout)
        self.layout().addWidget(test_group)

        self.layout().addStretch()
        self._refresh_test()

    def get_config(self) -> Dict[str, Any]:
        return {
            "enabled": self.enable_check.isChecked(),
            "weapon": self.weapon_selector.currentPreset(),
            "strength": self.strength_slider.value(),
            "x_strength": self.x_strength_slider.value(),
            "ticks": self.ticks_slider.value(),
            "delay": self.delay_slider.value(),
            "return_speed": self.return_speed_selector.currentPreset(),
            "curve": self.curve_selector.currentPreset(),
            "y_gate": self.y_gate_check.isChecked(),
            "loadout_slots": ["Pickaxe"] + [c.currentText() for c in self.loadout_combos],
            "simple_mode": self.simple_mode_check.isChecked(),
            "simple_rate": self.simple_rate_slider.value(),
            "initial_kick_mult": self.initial_kick_slider.value(),
            "initial_kick_ticks": self.initial_kick_ticks_slider.value(),
            "headshot_assist": self.headshot_assist_check.isChecked(),
            "headshot_assist_pull": self.headshot_assist_slider.value(),
        }

    def set_config(self, config: Dict[str, Any]) -> None:
        c = config
        if "recoil_enabled" in c:
            self.enable_check.setChecked(c["recoil_enabled"])
        if "enabled" in c:
            self.enable_check.setChecked(c["enabled"])
        if "weapon" in c:
            weapon_name = c["weapon"].upper()
            preset = RECOIL_PRESETS.get(weapon_name)
            if preset:
                cat = preset.get("category", "")
                idx = self.category_combo.findText(cat)
                if idx >= 0:
                    self.category_combo.blockSignals(True)
                    self.category_combo.setCurrentIndex(idx)
                    self.category_combo.blockSignals(False)
                    self._on_category_changed(cat)
            self.weapon_selector.setPreset(c["weapon"])
        slots = c.get("loadout_slots") or c.get("recoil_loadout_slots")
        if isinstance(slots, (list, tuple)) and len(slots) >= 6:
            for i, combo in enumerate(self.loadout_combos):
                idx = combo.findText(slots[i + 1])
                if idx >= 0:
                    combo.blockSignals(True)
                    combo.setCurrentIndex(idx)
                    combo.blockSignals(False)
        for json_key, slider_attr in [
            ("recoil_strength", "strength_slider"), ("strength", "strength_slider"),
            ("recoil_x_strength", "x_strength_slider"), ("x_strength", "x_strength_slider"),
            ("recoil_ticks", "ticks_slider"), ("ticks", "ticks_slider"),
            ("recoil_delay", "delay_slider"), ("delay_ms", "delay_slider"),
            ("delay", "delay_slider"),
        ]:
            if json_key in c and hasattr(self, slider_attr):
                getattr(self, slider_attr).setValue(int(c[json_key]))
        for json_key, check_attr in [
            ("recoil_enabled", "enable_check"),
            ("recoil_y_gate", "y_gate_check"), ("y_gate", "y_gate_check"),
            ("recoil_simple_mode", "simple_mode_check"), ("simple_mode", "simple_mode_check"),
            ("recoil_headshot_assist", "headshot_assist_check"), ("headshot_assist", "headshot_assist_check"),
        ]:
            if json_key in c and hasattr(self, check_attr):
                getattr(self, check_attr).setChecked(bool(c[json_key]))
        for json_key, slider_attr in [
            ("recoil_simple_rate", "simple_rate_slider"), ("simple_rate", "simple_rate_slider"),
            ("recoil_initial_kick_ticks", "initial_kick_ticks_slider"), ("initial_kick_ticks", "initial_kick_ticks_slider"),
            ("recoil_headshot_assist_pull", "headshot_assist_slider"), ("headshot_assist_pull", "headshot_assist_slider"),
        ]:
            if json_key in c and hasattr(self, slider_attr):
                getattr(self, slider_attr).setValue(int(c[json_key]))
        for json_key, slider_attr in [
            ("recoil_initial_kick_mult", "initial_kick_slider"), ("initial_kick_mult", "initial_kick_slider"),
        ]:
            if json_key in c and hasattr(self, slider_attr):
                getattr(self, slider_attr).setValue(float(c[json_key]))
        for json_key, sel_attr, label_func in [
            ("recoil_return_speed", "return_speed_selector", "_return_speed_label"),
            ("return_speed", "return_speed_selector", "_return_speed_label"),
            ("recoil_curve", "curve_selector", "_curve_label"),
            ("curve", "curve_selector", "_curve_label"),
        ]:
            if json_key in c and hasattr(self, sel_attr):
                val = float(c[json_key]) if label_func == "_return_speed_label" else c[json_key]
                label = getattr(self, label_func)(val)
                getattr(self, sel_attr).setPreset(label)
        self._on_config_change()

    def get_recoil_preset(self) -> Dict[str, Any]:
        return {
            "strength": self.strength_slider.value(),
            "x_strength": self.x_strength_slider.value(),
            "ticks": self.ticks_slider.value(),
            "delay_ms": self.delay_slider.value(),
            "return_speed": self._return_speed_value(),
            "curve": self._curve_value(),
        }

    def _on_config_change(self, *args) -> None:
        self._refresh_test()
        self.config_changed.emit(self.get_config())

    def _refresh_test(self, *args) -> None:
        if not hasattr(self, "tick_slider"):
            return

        config = self.get_config()
        self.testbed.apply_config(config)

        max_tick = max(0, self.ticks_slider.value() - 1)
        if self.tick_slider.slider.maximum() != max_tick:
            self.tick_slider.slider.setMaximum(max_tick)
        if self.tick_slider.value() > max_tick:
            self.tick_slider.setValue(max_tick)

        tick = self.tick_slider.value()
        raw_rx = self.raw_rx_slider.value()
        raw_ry = self.raw_ry_slider.value()
        if not self.enable_check.isChecked():
            offset_y, offset_x = 0, 0
        else:
            offset_y, offset_x = self.testbed.simulate_tick(tick, raw_ry, raw_rx, config)

        self.aim_visual.set_position(raw_rx, raw_ry)
        self.recoil_visual.set_position(offset_x, offset_y)
        self.curve_widget.set_params(
            self._curve_accel_for_preview(),
            0.0,
            1.0,
            min(self.strength_slider.value() / 100.0, 1.0),
        )
        self.output_label.setText(f"Offset: Y {offset_y}, X {offset_x}")

        self.curve_preview.update_curve(self._curve_value(), self.strength_slider.value(), self.ticks_slider.value())

        pattern = self.testbed.get_pattern(config, samples=5)
        short_pattern = " | ".join(f"{y}/{x}" for y, x in pattern[:5])
        self.pattern_label.setText(f"Pattern: {short_pattern}")

    def _weapons_for_category(self, category: str) -> List[str]:
        return [
            name for name, preset in RECOIL_PRESETS.items()
            if preset.get("category", "") == category
        ]

    def _on_category_changed(self, category: str) -> None:
        weapons = self._weapons_for_category(category)
        self.weapon_selector.combo.blockSignals(True)
        self.weapon_selector.combo.clear()
        self.weapon_selector.combo.addItems(weapons)
        self.weapon_selector.combo.addItem("Custom")
        self.weapon_selector.combo.blockSignals(False)
        if weapons:
            self._apply_weapon_preset(weapons[0])

    def _apply_weapon_preset(self, weapon: str) -> None:
        preset = RECOIL_PRESETS.get(weapon.upper())
        if not preset:
            return

        self.set_config({
            "weapon": weapon,
            "strength": preset.get("strength", 65),
            "x_strength": preset.get("x_strength", 0),
            "ticks": preset.get("ticks", 60),
            "delay": preset.get("delay_ms", 45),
            "return_speed": self._return_speed_label(preset.get("return_speed", 0.7)),
            "curve": self._curve_label(preset.get("curve", "ease_out")),
        })

        self.curve_preview.update_curve(
            preset.get("curve", "ease_out"),
            preset.get("strength", 65),
            preset.get("ticks", 60),
        )

    def _return_speed_value(self) -> float:
        text = self.return_speed_selector.currentPreset()
        if "(" in text and ")" in text:
            return float(text.split("(", 1)[1].split(")", 1)[0])
        return 0.7

    def _return_speed_label(self, value: float) -> str:
        if value <= 0.55:
            return "Slow (0.5)"
        if value >= 0.85:
            return "Fast (0.9)"
        return "Normal (0.7)"

    def _curve_value(self) -> str:
        return self.curve_selector.currentPreset().lower().replace("-", "_")

    def _curve_label(self, value: str) -> str:
        labels = {
            "linear": "Linear",
            "ease_in": "Ease-In",
            "ease_out": "Ease-Out",
        }
        return labels.get(value, "Ease-Out")

    def _curve_accel_for_preview(self) -> float:
        curve = self._curve_value()
        if curve == "ease_in":
            return 2.0
        if curve == "linear":
            return 1.0
        return 0.6

    def _save_recoil_preset(self) -> None:
        name = self.weapon_selector.currentPreset()
        cfg = self.get_config()
        payload = {
            "_format": "nocrosshair.nocro",
            "_version": 1,
            "_type": "recoil_preset",
            "config": {
                "recoil_enabled": True,
                "recoil_strength": cfg.get("strength", 65),
                "recoil_x_strength": cfg.get("x_strength", 0),
                "recoil_ticks": cfg.get("ticks", 60),
                "recoil_delay": cfg.get("delay_ms", 45),
                "recoil_return_speed": cfg.get("return_speed", 0.7),
                "recoil_curve": cfg.get("curve", "ease_out"),
                "recoil_y_gate": cfg.get("y_gate", True),
            },
        }
        path, _ = QFileDialog.getSaveFileName(
            self, f"Save {name} Recoil", os.path.expanduser("~"),
            "Nocro (*.nocro);;All (*)"
        )
        if path:
            with open(path, "w") as f:
                f.write("# NOCRO v1 — recoil preset\n")
                json.dump(payload, f, indent=2)

    def _load_recoil_preset(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Recoil Preset", os.path.expanduser("~"),
            "Nocro (*.nocro);;All (*)"
        )
        if not path:
            return
        try:
            with open(path, "r") as f:
                content = f.read()
            data = json.loads(content.split("\n", 1)[-1])
            inner = data.get("config", data)
            self.set_config(inner)
            self._on_config_change()
        except Exception as e:
            print(f"Load recoil failed: {e}")
