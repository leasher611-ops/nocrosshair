from typing import Dict, Any
from dataclasses import asdict
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QCheckBox, QHBoxLayout, QPushButton, QComboBox

from nocrosshair.core.config import AimAssistConfig
from nocrosshair.features.aim_assist import AATestbed, AimAssistEngine, AimAssistPresets
from nocrosshair.ui.widgets import (
    LabeledSlider, LabeledDoubleSlider, PresetSelector,
    StickVisualizerWidget, HLine, SectionGroupBox
)

class AimAssistTab(QWidget):

    config_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.testbed = AATestbed(AimAssistEngine(self.get_aim_assist_config()))
        self.setLayout(QVBoxLayout())
        self._init_ui()

    def _init_ui(self) -> None:
        title = QLabel("Aim Assist Configuration")
        title.setObjectName("hudTitle")
        self.layout().addWidget(title)
        self.layout().addWidget(HLine())

        enable_group = SectionGroupBox("Enable/Disable")
        enable_layout = QVBoxLayout()

        self.enable_check = QCheckBox("Enable Aim Assist (Master)")
        self.enable_check.setChecked(True)
        self.enable_check.stateChanged.connect(self._on_config_change)
        enable_layout.addWidget(self.enable_check)

        self.base_aa_check = QCheckBox("Base AA (Slowdown/Tracking/Sticky)")
        self.base_aa_check.setChecked(True)
        self.base_aa_check.stateChanged.connect(self._on_config_change)
        enable_layout.addWidget(self.base_aa_check)

        enable_group.layout().addLayout(enable_layout)
        self.layout().addWidget(enable_group)

        params_group = SectionGroupBox("Main Parameters")
        params_layout = QVBoxLayout()

        self.preset_selector = PresetSelector("Preset", ["Light", "Moderate", "Strong", "Precision", "Aimlock", "Lexicon", "Dogz Polar", "SecretAim", "xCloud Hard", "Mobile", "Mobile Lite", "M S1", "M S2", "M S3", "M S4", "Long Range", "FN Mobile xCloud", "FN Controller"])
        self.preset_selector.preset_changed.connect(self._apply_preset)
        params_layout.addWidget(self.preset_selector)

        self.strength_slider = LabeledSlider("Strength", 0, 12000, 8500)
        self.strength_slider.value_changed.connect(self._on_config_change)
        params_layout.addWidget(self.strength_slider)

        self.ads_slider = LabeledDoubleSlider("ADS Strength Multiplier", 1.0, 2.0, 1.05, decimals=2)
        self.ads_slider.value_changed.connect(self._on_config_change)
        params_layout.addWidget(self.ads_slider)

        self.zone_slider = LabeledSlider("AA Zone", 500, 8000, 4500)
        self.zone_slider.value_changed.connect(self._on_config_change)
        params_layout.addWidget(self.zone_slider)

        params_group.layout().addLayout(params_layout)
        self.layout().addWidget(params_group)

        advanced_group = SectionGroupBox("Advanced Features")
        advanced_layout = QVBoxLayout()

        self.snap_check = QCheckBox("Magnetic Snap")
        self.snap_check.setChecked(True)
        self.snap_check.stateChanged.connect(self._on_config_change)
        advanced_layout.addWidget(self.snap_check)

        self.snap_duration_slider = LabeledSlider("Snap Duration (ms)", 20, 300, 80)
        self.snap_duration_slider.value_changed.connect(self._on_config_change)
        advanced_layout.addWidget(self.snap_duration_slider)

        self.tracking_check = QCheckBox("Enable Tracking")
        self.tracking_check.setChecked(True)
        self.tracking_check.stateChanged.connect(self._on_config_change)
        advanced_layout.addWidget(self.tracking_check)

        self.tracking_strength_slider = LabeledSlider("Tracking Strength", 0, 4000, 950)
        self.tracking_strength_slider.value_changed.connect(self._on_config_change)
        advanced_layout.addWidget(self.tracking_strength_slider)

        self.sticky_check = QCheckBox("Sticky Aim")
        self.sticky_check.setChecked(True)
        self.sticky_check.stateChanged.connect(self._on_config_change)
        advanced_layout.addWidget(self.sticky_check)

        self.sticky_strength_slider = LabeledDoubleSlider("Sticky Strength", 0.05, 1.0, 0.50, decimals=2)
        self.sticky_strength_slider.value_changed.connect(self._on_config_change)
        advanced_layout.addWidget(self.sticky_strength_slider)

        adaptive_label = QLabel("Adaptive Strength AI (Acid Aim+)")
        adaptive_label.setStyleSheet("font-weight: bold; margin-top: 6px;")
        advanced_layout.addWidget(adaptive_label)

        self.adaptive_min_slider = LabeledDoubleSlider("Min Scale (distância longa)", 0.1, 1.0, 0.3, decimals=2)
        self.adaptive_min_slider.value_changed.connect(self._on_config_change)
        advanced_layout.addWidget(self.adaptive_min_slider)

        self.adaptive_max_slider = LabeledDoubleSlider("Max Scale (distância curta)", 1.0, 3.0, 1.5, decimals=2)
        self.adaptive_max_slider.value_changed.connect(self._on_config_change)
        advanced_layout.addWidget(self.adaptive_max_slider)

        advanced_group.layout().addLayout(advanced_layout)
        self.layout().addWidget(advanced_group)

        rush_group = SectionGroupBox("Rush Engine (Rotational AA)")
        rush_layout = QVBoxLayout()

        self.rush_check = QCheckBox("Enable Rush Strafe")
        self.rush_check.setChecked(True)
        self.rush_check.stateChanged.connect(self._on_config_change)
        rush_layout.addWidget(self.rush_check)

        self.rush_pulse_slider = LabeledDoubleSlider("Pulse (ms)", 0.5, 5.0, 1.5, decimals=1)
        self.rush_pulse_slider.value_changed.connect(self._on_config_change)
        rush_layout.addWidget(self.rush_pulse_slider)

        self.rush_cooldown_slider = LabeledDoubleSlider("Cooldown (ms)", 20.0, 200.0, 80.0, decimals=1)
        self.rush_cooldown_slider.value_changed.connect(self._on_config_change)
        rush_layout.addWidget(self.rush_cooldown_slider)

        self.rush_deadzone_slider = LabeledDoubleSlider("Deadzone Threshold", 0.08, 0.20, 0.13, decimals=2)
        self.rush_deadzone_slider.value_changed.connect(self._on_config_change)
        rush_layout.addWidget(self.rush_deadzone_slider)

        self.rush_mult_slider = LabeledDoubleSlider("Multiplier", 1.0, 5.0, 3.0, decimals=1)
        self.rush_mult_slider.value_changed.connect(self._on_config_change)
        rush_layout.addWidget(self.rush_mult_slider)

        self.rush_always_check = QCheckBox("Rush Always (Rotational AA even without ADS)")
        self.rush_always_check.setChecked(True)
        self.rush_always_check.stateChanged.connect(self._on_config_change)
        rush_layout.addWidget(self.rush_always_check)

        self.shape_selector = PresetSelector("Shape Mode", ["Circular", "Zen", "Helix", "WideOval", "TallOval"])
        self.shape_selector.preset_changed.connect(self._on_config_change)
        rush_layout.addWidget(self.shape_selector)

        self.dz_radius_check = QCheckBox("Use Deadzone-Based Radius (Cronus Style)")
        self.dz_radius_check.setChecked(False)
        self.dz_radius_check.stateChanged.connect(self._on_config_change)
        rush_layout.addWidget(self.dz_radius_check)

        rush_desc = QLabel("Strafe pulses activate Rotational AA without aiming.\nSmall deadzone-noise keeps it engaged on every strafe.")
        rush_desc.setStyleSheet("color: #888; font-size: 10px;")
        rush_layout.addWidget(rush_desc)

        rush_group.layout().addLayout(rush_layout)
        self.layout().addWidget(rush_group)

        pattern_group = SectionGroupBox("Aim Pattern (PD Controller)")
        pattern_layout = QVBoxLayout()

        self.aim_pattern_selector = PresetSelector("Pattern", ["Standard", "Micro Adjust", "Track Assist", "Predict", "Full"])
        self.aim_pattern_selector.preset_changed.connect(self._on_config_change)
        pattern_layout.addWidget(self.aim_pattern_selector)

        self.pd_kp_slider = LabeledDoubleSlider("PD Kp (Proportional)", 0.01, 0.50, 0.20, decimals=2)
        self.pd_kp_slider.value_changed.connect(self._on_config_change)
        pattern_layout.addWidget(self.pd_kp_slider)

        self.pd_kd_slider = LabeledDoubleSlider("PD Kd (Derivative)", 0.01, 0.30, 0.10, decimals=2)
        self.pd_kd_slider.value_changed.connect(self._on_config_change)
        pattern_layout.addWidget(self.pd_kd_slider)

        self.magnetic_pull_slider = LabeledSlider("Magnetic Pull", 0, 1200, 400)
        self.magnetic_pull_slider.value_changed.connect(self._on_config_change)
        pattern_layout.addWidget(self.magnetic_pull_slider)

        self.adaptive_strength_check = QCheckBox("Adaptive Strength (scale with distance)")
        self.adaptive_strength_check.setChecked(True)
        self.adaptive_strength_check.stateChanged.connect(self._on_config_change)
        pattern_layout.addWidget(self.adaptive_strength_check)

        pd_desc = QLabel("PD Controller replaces old jitter methods.\nKp = pull strength toward target, Kd = oscillation dampening.\nHigher Kp = faster lock, higher Kd = less shake.")
        pd_desc.setStyleSheet("color: #888; font-size: 10px;")
        pattern_layout.addWidget(pd_desc)

        self.auto_aa_check = QCheckBox("Auto Aim Assist (força AA sem stick)")
        self.auto_aa_check.setChecked(False)
        self.auto_aa_check.stateChanged.connect(self._on_config_change)
        pattern_layout.addWidget(self.auto_aa_check)

        self.auto_rotation_check = QCheckBox("Auto Rotation (gira pro alvo)")
        self.auto_rotation_check.setChecked(False)
        self.auto_rotation_check.stateChanged.connect(self._on_config_change)
        pattern_layout.addWidget(self.auto_rotation_check)

        self.auto_rotation_speed_slider = LabeledSlider("Auto Rotation Speed", 50, 600, 200)
        self.auto_rotation_speed_slider.value_changed.connect(self._on_config_change)
        pattern_layout.addWidget(self.auto_rotation_speed_slider)

        pattern_group.layout().addLayout(pattern_layout)
        self.layout().addWidget(pattern_group)

        shake_group = SectionGroupBox("Anti-Shake")
        shake_layout = QVBoxLayout()

        self.anti_shake_slider = LabeledSlider("Blend Factor (%)", 0, 100, 30)
        self.anti_shake_slider.value_changed.connect(self._on_config_change)
        shake_layout.addWidget(self.anti_shake_slider)

        self.prediction_frames_slider = LabeledSlider("Prediction Frames", 0, 10, 3)
        self.prediction_frames_slider.value_changed.connect(self._on_config_change)
        shake_layout.addWidget(self.prediction_frames_slider)

        shake_desc = QLabel("Anti-shake applies EMA smoothing to output.\n0% = no smoothing, 100% = full smoothing (laggy).\nPrediction frames = how far ahead to lead targets.")
        shake_desc.setStyleSheet("color: #888; font-size: 10px;")
        shake_layout.addWidget(shake_desc)

        shake_group.layout().addLayout(shake_layout)
        self.layout().addWidget(shake_group)

        boost_group = SectionGroupBox("Power Boost")
        boost_layout = QVBoxLayout()

        self.power_check = QCheckBox("Enable Power Boost")
        self.power_check.setChecked(True)
        self.power_check.stateChanged.connect(self._on_config_change)
        boost_layout.addWidget(self.power_check)

        self.power_mult_slider = LabeledDoubleSlider("Boost Multiplier", 1.1, 4.0, 2.0, decimals=1)
        self.power_mult_slider.value_changed.connect(self._on_config_change)
        boost_layout.addWidget(self.power_mult_slider)

        self.max_boost_btn = QPushButton("MAX BOOST (Set All to Max)")
        self.max_boost_btn.setStyleSheet("QPushButton { background: #ff4444; color: #fff; font-weight: bold; padding: 6px; }")
        self.max_boost_btn.clicked.connect(self._set_max_boost)
        boost_layout.addWidget(self.max_boost_btn)

        boost_group.layout().addLayout(boost_layout)
        self.layout().addWidget(boost_group)

        lock_group = SectionGroupBox("Aim Lock")
        lock_layout = QVBoxLayout()

        self.lock_check = QCheckBox("Enable Aim Lock")
        self.lock_check.setChecked(True)
        self.lock_check.stateChanged.connect(self._on_config_change)
        lock_layout.addWidget(self.lock_check)

        self.lock_strength_slider = LabeledSlider("Lock Strength", 1000, 12000, 9000)
        self.lock_strength_slider.value_changed.connect(self._on_config_change)
        lock_layout.addWidget(self.lock_strength_slider)

        self.lock_fov_slider = LabeledSlider("Lock FOV (Zone)", 500, 8000, 4500)
        self.lock_fov_slider.value_changed.connect(self._on_config_change)
        lock_layout.addWidget(self.lock_fov_slider)

        self.lock_track_slider = LabeledSlider("Follow Speed", 100, 2000, 950)
        self.lock_track_slider.value_changed.connect(self._on_config_change)
        lock_layout.addWidget(self.lock_track_slider)

        self.lock_sticky_slider = LabeledDoubleSlider("Sticky Force", 0.0, 1.0, 0.55, decimals=2)
        self.lock_sticky_slider.value_changed.connect(self._on_config_change)
        lock_layout.addWidget(self.lock_sticky_slider)

        self.lock_smooth_slider = LabeledDoubleSlider("Smoothness", 0.0, 1.0, 0.3, decimals=2)
        self.lock_smooth_slider.value_changed.connect(self._on_config_change)
        lock_layout.addWidget(self.lock_smooth_slider)

        lock_group.layout().addLayout(lock_layout)
        self.layout().addWidget(lock_group)

        drop_group = SectionGroupBox("Bullet Drop (Correção de Queda)")
        drop_layout = QVBoxLayout()

        self.bullet_drop_check = QCheckBox("Enable Bullet Drop Compensation")
        self.bullet_drop_check.setChecked(False)
        self.bullet_drop_check.stateChanged.connect(self._on_config_change)
        drop_layout.addWidget(self.bullet_drop_check)

        self.bullet_drop_slider = LabeledSlider("Drop Force (pixels)", 0, 1000, 200)
        self.bullet_drop_slider.value_changed.connect(self._on_config_change)
        drop_layout.addWidget(self.bullet_drop_slider)

        self.bullet_drop_offset_slider = LabeledSlider("Manual Offset", -500, 500, 0)
        self.bullet_drop_offset_slider.value_changed.connect(self._on_config_change)
        drop_layout.addWidget(self.bullet_drop_offset_slider)

        drop_group.layout().addLayout(drop_layout)
        self.layout().addWidget(drop_group)

        sway_group = SectionGroupBox("Anti-Sway (Contra Balanço Horizontal)")
        sway_layout = QVBoxLayout()

        self.anti_sway_check = QCheckBox("Enable Anti-Sway")
        self.anti_sway_check.setChecked(False)
        self.anti_sway_check.stateChanged.connect(self._on_config_change)
        sway_layout.addWidget(self.anti_sway_check)

        self.anti_sway_slider = LabeledSlider("Sway Strength", 0, 2000, 500)
        self.anti_sway_slider.value_changed.connect(self._on_config_change)
        sway_layout.addWidget(self.anti_sway_slider)

        sway_group.layout().addLayout(sway_layout)
        self.layout().addWidget(sway_group)

        long_range_group = SectionGroupBox("Long Range (Potencializar Seguimento)")
        long_range_layout = QVBoxLayout()

        self.lr_track_boost_slider = LabeledSlider("Track Boost Cap", 300, 2000, 600)
        self.lr_track_boost_slider.value_changed.connect(self._on_config_change)
        long_range_layout.addWidget(self.lr_track_boost_slider)

        self.lr_predict_lead_slider = LabeledSlider("Predict Lead Cap", 1000, 6000, 2000)
        self.lr_predict_lead_slider.value_changed.connect(self._on_config_change)
        long_range_layout.addWidget(self.lr_predict_lead_slider)

        long_range_group.layout().addLayout(long_range_layout)
        self.layout().addWidget(long_range_group)

        abuse_group = SectionGroupBox("Abuse Mode (Jitter Rotacional)")
        abuse_layout = QVBoxLayout()

        self.abuse_check = QCheckBox("Enable Abuse Jitter")
        self.abuse_check.setChecked(True)
        self.abuse_check.stateChanged.connect(self._on_config_change)
        abuse_layout.addWidget(self.abuse_check)

        pattern_row = QHBoxLayout()
        pattern_row.addWidget(QLabel("Pattern"))
        self.abuse_pattern_combo = QComboBox()
        self.abuse_pattern_combo.addItems(["oscillation", "circular", "horizontal", "zigzag"])
        self.abuse_pattern_combo.currentTextChanged.connect(self._on_config_change)
        pattern_row.addWidget(self.abuse_pattern_combo)
        abuse_layout.addLayout(pattern_row)

        self.abuse_amp_slider = LabeledSlider("Amplitude", 10, 300, 50)
        self.abuse_amp_slider.value_changed.connect(self._on_config_change)
        abuse_layout.addWidget(self.abuse_amp_slider)

        self.abuse_speed_slider = LabeledSlider("Speed", 1, 30, 10)
        self.abuse_speed_slider.value_changed.connect(self._on_config_change)
        abuse_layout.addWidget(self.abuse_speed_slider)

        abuse_group.layout().addLayout(abuse_layout)
        self.layout().addWidget(abuse_group)

        test_group = SectionGroupBox("Live Test")
        test_layout = QVBoxLayout()

        self.input_x_slider = LabeledSlider("Input X", -32768, 32767, 1200)
        self.input_y_slider = LabeledSlider("Input Y", -32768, 32767, 400)
        self.input_x_slider.value_changed.connect(self._refresh_test)
        self.input_y_slider.value_changed.connect(self._refresh_test)
        test_layout.addWidget(self.input_x_slider)
        test_layout.addWidget(self.input_y_slider)

        self.target_angle_slider = LabeledSlider("Target Angle", -180, 180, 0)
        self.target_angle_slider.value_changed.connect(self._refresh_test)
        test_layout.addWidget(self.target_angle_slider)

        self.snap_progress_slider = LabeledDoubleSlider("Snap Progress", 0.0, 1.0, 0.5, decimals=2)
        self.snap_progress_slider.value_changed.connect(self._refresh_test)
        test_layout.addWidget(self.snap_progress_slider)

        self.shooting_check = QCheckBox("Shooting")
        self.shooting_check.setChecked(True)
        self.shooting_check.stateChanged.connect(self._refresh_test)
        test_layout.addWidget(self.shooting_check)

        self.moving_check = QCheckBox("Moving")
        self.moving_check.setChecked(True)
        self.moving_check.stateChanged.connect(self._refresh_test)
        test_layout.addWidget(self.moving_check)

        self.lt_pressed_check = QCheckBox("LT Pressed")
        self.lt_pressed_check.stateChanged.connect(self._refresh_test)
        test_layout.addWidget(self.lt_pressed_check)

        visual_layout = QHBoxLayout()
        self.input_visual = StickVisualizerWidget("Input")
        self.output_visual = StickVisualizerWidget("AA Output")
        visual_layout.addWidget(self.input_visual)
        visual_layout.addWidget(self.output_visual)
        test_layout.addLayout(visual_layout)

        self.output_label = QLabel("Output: 0, 0")
        self.output_label.setStyleSheet("color: #00ff88")
        test_layout.addWidget(self.output_label)

        test_group.layout().addLayout(test_layout)
        self.layout().addWidget(test_group)

        self.layout().addStretch()
        self._refresh_test()

    def get_config(self) -> Dict[str, Any]:
        return {
            "enabled": self.enable_check.isChecked(),
            "base_aa_enabled": self.base_aa_check.isChecked(),
            "preset": self.preset_selector.currentPreset(),
            "strength": self.strength_slider.value(),
            "zone": self.zone_slider.value(),
            "magnetic_snap": self.snap_check.isChecked(),
            "snap_duration": self.snap_duration_slider.value(),
            "tracking": self.tracking_check.isChecked(),
            "tracking_strength": self.tracking_strength_slider.value(),
            "sticky": self.sticky_check.isChecked(),
            "sticky_strength": self.sticky_strength_slider.value(),
            "rush": self.rush_check.isChecked(),
            "rush_pulse_ms": self.rush_pulse_slider.value(),
            "rush_cooldown_ms": self.rush_cooldown_slider.value(),
            "rush_deadzone": self.rush_deadzone_slider.value(),
            "rush_mult": self.rush_mult_slider.value(),
            "rush_always": self.rush_always_check.isChecked(),
            "power_boost": self.power_check.isChecked(),
            "power_mult": self.power_mult_slider.value(),
            "lock_enabled": self.lock_check.isChecked(),
            "lock_strength": self.lock_strength_slider.value(),
            "lock_fov": self.lock_fov_slider.value(),
            "lock_track": self.lock_track_slider.value(),
            "lock_sticky": self.lock_sticky_slider.value(),
            "lock_smooth": self.lock_smooth_slider.value(),
            "shape_mode": self.shape_selector.currentPreset(),
            "use_dz_radius": self.dz_radius_check.isChecked(),
            "aim_pattern": self.aim_pattern_selector.currentPreset(),
            "pd_kp": self.pd_kp_slider.value(),
            "pd_kd": self.pd_kd_slider.value(),
            "magnetic_pull": self.magnetic_pull_slider.value(),
            "adaptive_strength": self.adaptive_strength_check.isChecked(),
            "adaptive_strength_min": self.adaptive_min_slider.value(),
            "adaptive_strength_max": self.adaptive_max_slider.value(),
            "anti_shake_blend": self.anti_shake_slider.value() / 100.0,
            "prediction_frames": self.prediction_frames_slider.value(),
            "auto_aa_enabled": self.auto_aa_check.isChecked(),
            "auto_rotation_enabled": self.auto_rotation_check.isChecked(),
            "auto_rotation_speed": self.auto_rotation_speed_slider.value(),
            "bullet_drop_enabled": self.bullet_drop_check.isChecked(),
            "bullet_drop_factor": self.bullet_drop_slider.value(),
            "bullet_drop_offset": self.bullet_drop_offset_slider.value(),
            "anti_sway_enabled": self.anti_sway_check.isChecked(),
            "anti_sway_strength": self.anti_sway_slider.value(),
            "long_range_track_boost": self.lr_track_boost_slider.value(),
            "long_range_predict_lead": self.lr_predict_lead_slider.value(),
            "abuse_enabled": self.abuse_check.isChecked(),
            "abuse_mode": self.abuse_pattern_combo.currentText(),
            "abuse_amp": self.abuse_amp_slider.value(),
            "abuse_speed": self.abuse_speed_slider.value(),
        }

    def get_aim_assist_config(self) -> AimAssistConfig:
        config = self.get_config() if hasattr(self, "enable_check") else {}
        return AimAssistConfig(
            enabled=config.get("enabled", True),
            base_aa_enabled=config.get("base_aa_enabled", True),
            strength=int(config.get("strength", 8500)),
            ads_multiplier=float(config.get("ads_multiplier", 1.05)),
            zone=int(config.get("zone", 5000)),
            rotational=config.get("rotational", True),
            pulse_level=int(config.get("pulse_level", 0)),
            aim_type=config.get("aim_type", "flow"),
            magnetic_snap=config.get("magnetic_snap", True),
            snap_strength=int(config.get("snap_strength", 800)),
            snap_duration=int(config.get("snap_duration", 80)),
            tracking=config.get("tracking", True),
            tracking_strength=int(config.get("tracking_strength", 1500)),
            tracking_speed=int(config.get("tracking_speed", 0)),
            track_ads_pulse_ms=int(config.get("track_ads_pulse_ms", 240)),
            shape_mode=str(config.get("shape_mode", "Circular")).lower(),
            aim_pattern=str(config.get("aim_pattern", "Standard")).lower().replace(" ", "_"),
            pd_kp=float(config.get("pd_kp", 0.15)),
            pd_kd=float(config.get("pd_kd", 0.08)),
            magnetic_pull=int(config.get("magnetic_pull", 400)),
            anti_shake_blend=float(config.get("anti_shake_blend", 0.30)),
            prediction_frames=int(config.get("prediction_frames", 3)),
            anti_flinch=config.get("anti_flinch", True),
            anti_flinch_strength=int(config.get("anti_flinch_strength", 3000)),
            zero_delay=config.get("zero_delay", True),
            zero_delay_ms=int(config.get("zero_delay_ms", 40)),
            bloom_compensation=config.get("bloom_compensation", True),
            cjitter_enabled=config.get("cjitter_enabled", False),
            cjitter_left_enabled=config.get("cjitter_left_enabled", False),
            cjitter_left_amp=int(config.get("cjitter_left_amp", 2)),
        )

    def set_config(self, config: Dict[str, Any]) -> None:
        c = config
        for nkey, okey, widget, wtype in [
            ("remap_aa_enabled", "enabled", "enable_check", "check"),
            ("aa_base_aa_enabled", "base_aa_enabled", "base_aa_check", "check"),
            ("remap_aa_strength", "strength", "strength_slider", "int"),
            ("aa_ads_multiplier", "ads_multiplier", "ads_slider", "float"),
            ("aa_zone", "zone", "zone_slider", "int"),
            ("aa_magnetic_snap", "magnetic_snap", "snap_check", "check"),
            ("aa_snap_duration", "snap_duration", "snap_duration_slider", "int"),
            ("aa_tracking", "tracking", "tracking_check", "check"),
            ("aa_tracking_strength", "tracking_strength", "tracking_strength_slider", "int"),
            ("aa_sticky_enabled", "sticky", "sticky_check", "check"),
            ("aa_sticky_strength", "sticky_strength", "sticky_strength_slider", "float"),
            ("aa_rush_enabled", "rush", "rush_check", "check"),
            ("aa_rush_pulse_ms", "rush_pulse_ms", "rush_pulse_slider", "float"),
            ("aa_rush_cooldown_ms", "rush_cooldown_ms", "rush_cooldown_slider", "float"),
            ("aa_rush_deadzone", "rush_deadzone", "rush_deadzone_slider", "float"),
            ("aa_rush_mult", "rush_mult", "rush_mult_slider", "float"),
            ("aa_rush_always", "rush_always", "rush_always_check", "check"),
            ("aa_lock_enabled", "lock_enabled", "lock_check", "check"),
            ("aa_lock_strength", "lock_strength", "lock_strength_slider", "int"),
            ("aa_lock_fov", "lock_fov", "lock_fov_slider", "int"),
            ("aa_lock_track", "lock_track", "lock_track_slider", "int"),
            ("aa_lock_sticky", "lock_sticky", "lock_sticky_slider", "float"),
            ("aa_lock_smooth", "lock_smooth", "lock_smooth_slider", "float"),
            ("aa_shape_mode", "shape_mode", "shape_selector", "preset"),
            ("aa_use_dz_radius", "use_dz_radius", "dz_radius_check", "check"),
            ("aa_pd_kp", "pd_kp", "pd_kp_slider", "float"),
            ("aa_pd_kd", "pd_kd", "pd_kd_slider", "float"),
            ("aa_magnetic_pull", "magnetic_pull", "magnetic_pull_slider", "int"),
            ("aa_adaptive_strength", "adaptive_strength", "adaptive_strength_check", "check"),
            ("aa_adaptive_strength_min", "adaptive_strength_min", "adaptive_min_slider", "float"),
            ("aa_adaptive_strength_max", "adaptive_strength_max", "adaptive_max_slider", "float"),
            ("aa_prediction_frames", "prediction_frames", "prediction_frames_slider", "int"),
            ("aa_auto_aa_enabled", "auto_aa_enabled", "auto_aa_check", "check"),
            ("aa_auto_rotation_enabled", "auto_rotation_enabled", "auto_rotation_check", "check"),
            ("aa_auto_rotation_speed", "auto_rotation_speed", "auto_rotation_speed_slider", "int"),
            ("aa_bullet_drop_enabled", "bullet_drop_enabled", "bullet_drop_check", "check"),
            ("aa_bullet_drop_factor", "bullet_drop_factor", "bullet_drop_slider", "int"),
            ("aa_bullet_drop_offset", "bullet_drop_offset", "bullet_drop_offset_slider", "int"),
            ("aa_anti_sway_enabled", "anti_sway_enabled", "anti_sway_check", "check"),
            ("aa_anti_sway_strength", "anti_sway_strength", "anti_sway_slider", "int"),
            ("aa_long_range_track_boost", "long_range_track_boost", "lr_track_boost_slider", "int"),
            ("aa_long_range_predict_lead", "long_range_predict_lead", "lr_predict_lead_slider", "int"),
            ("aa_abuse_enabled", "abuse_enabled", "abuse_check", "check"),
            ("aa_abuse_amp", "abuse_amp", "abuse_amp_slider", "int"),
            ("aa_abuse_speed", "abuse_speed", "abuse_speed_slider", "int"),
        ]:
            val = None
            if nkey in c:
                val = c[nkey]
            elif okey in c:
                val = c[okey]
            if val is not None and hasattr(self, widget):
                w = getattr(self, widget)
                if wtype == "check":
                    w.setChecked(bool(val))
                elif wtype == "int":
                    w.setValue(int(val))
                elif wtype == "float":
                    w.setValue(float(val))
                elif wtype == "preset" and hasattr(w, "setPreset"):
                    w.setPreset(str(val).title())
        if "aa_power_boost" in c:
            self.power_check.setChecked(c["aa_power_boost"])
        if "power_boost" in c:
            self.power_check.setChecked(c["power_boost"])
        if "aa_power_mult" in c:
            self.power_mult_slider.setValue(float(c["aa_power_mult"]))
        if "power_mult" in c:
            self.power_mult_slider.setValue(float(c["power_mult"]))
        if "aa_shape_mode" in c:
            self.shape_selector.setPreset(str(c["aa_shape_mode"]).title())
        if "shape_mode" in c:
            self.shape_selector.setPreset(str(c["shape_mode"]).title())
        if "aa_use_dz_radius" in c:
            self.dz_radius_check.setChecked(c["aa_use_dz_radius"])
        if "use_dz_radius" in c:
            self.dz_radius_check.setChecked(c["use_dz_radius"])
        if "aa_aim_pattern" in c:
            self.aim_pattern_selector.setPreset(str(c["aa_aim_pattern"]).replace("_", " ").title())
        if "aim_pattern" in c:
            self.aim_pattern_selector.setPreset(str(c["aim_pattern"]).replace("_", " ").title())
        if "anti_shake_blend" in c:
            self.anti_shake_slider.setValue(int(float(c["anti_shake_blend"]) * 100))
        if "aa_auto_aa_enabled" in c:
            self.auto_aa_check.setChecked(c["aa_auto_aa_enabled"])
        if "auto_aa_enabled" in c:
            self.auto_aa_check.setChecked(c["auto_aa_enabled"])
        if "aa_auto_rotation_enabled" in c:
            self.auto_rotation_check.setChecked(c["aa_auto_rotation_enabled"])
        if "auto_rotation_enabled" in c:
            self.auto_rotation_check.setChecked(c["auto_rotation_enabled"])
        if "aa_auto_rotation_speed" in c:
            self.auto_rotation_speed_slider.setValue(int(c["aa_auto_rotation_speed"]))
        if "auto_rotation_speed" in c:
            self.auto_rotation_speed_slider.setValue(int(c["auto_rotation_speed"]))
        if "aa_abuse_mode" in c:
            idx = self.abuse_pattern_combo.findText(c["aa_abuse_mode"])
            if idx >= 0:
                self.abuse_pattern_combo.setCurrentIndex(idx)
        if "abuse_mode" in c:
            idx = self.abuse_pattern_combo.findText(c["abuse_mode"])
            if idx >= 0:
                self.abuse_pattern_combo.setCurrentIndex(idx)

    def _set_max_boost(self) -> None:
        self.strength_slider.setValue(10000)
        self.zone_slider.setValue(5000)
        self.tracking_strength_slider.setValue(1000)
        self.sticky_strength_slider.setValue(0.95)
        self.lock_strength_slider.setValue(10000)
        self.lock_fov_slider.setValue(5000)
        self.lock_track_slider.setValue(1000)
        self.lock_sticky_slider.setValue(0.95)
        self.power_check.setChecked(True)
        self.power_mult_slider.setValue(3.0)
        self.snap_check.setChecked(True)
        self.aim_pattern_selector.setPreset("Predict")
        self.pd_kp_slider.setValue(0.35)
        self.pd_kd_slider.setValue(0.15)
        self.magnetic_pull_slider.setValue(800)
        self.anti_shake_slider.setValue(20)
        self.adaptive_strength_check.setChecked(True)
        self.rush_always_check.setChecked(True)
        self._on_config_change()

    def _on_config_change(self, *args) -> None:
        self._refresh_test()
        self.config_changed.emit(self.get_config())

    def _refresh_test(self, *args) -> None:
        if not hasattr(self, "input_x_slider"):
            return

        cfg = self.get_aim_assist_config()
        self.testbed.apply_config(cfg)
        self.testbed.set_target(self.target_angle_slider.value())

        input_x = self.input_x_slider.value()
        input_y = self.input_y_slider.value()
        output_x, output_y = self.testbed.simulate_input(
            input_x,
            input_y,
            is_shooting=self.shooting_check.isChecked(),
            is_moving=self.moving_check.isChecked(),
            lt_pressed=self.lt_pressed_check.isChecked(),
            snap_progress=self.snap_progress_slider.value(),
        )

        self.input_visual.set_position(input_x, input_y)
        self.output_visual.set_position(output_x, output_y)
        layer = self.testbed.aa_engine.get_aa_layer(input_x, input_y)
        self.output_label.setText(f"Output: {output_x}, {output_y} | Layer: {layer}")

    def _apply_preset(self, preset: str) -> None:
        preset_map = {
            "FN Controller": AimAssistPresets.fortnite_controller,
        }
        if preset not in preset_map:
            return

        self._set_from_typed_config(preset_map[preset]())

    def _set_from_typed_config(self, cfg: AimAssistConfig) -> None:
        data = asdict(cfg)
        self.set_config({
            "enabled": data["enabled"],
            "strength": data["strength"],
            "zone": data["zone"],
            "magnetic_snap": data["magnetic_snap"],
            "snap_duration": data["snap_duration"],
            "tracking": data["tracking"],
            "tracking_strength": data["tracking_strength"],
            "sticky": data["sticky_enabled"],
            "rush": data["rush_enabled"],
            "rush_mult": data["rush_mult"],
            "rush_always": data["rush_always"],
            "sticky_strength": data["sticky_strength"],
            "snap_strength": data["snap_strength"],
            "power_boost": data["power_boost"],
            "power_mult": data["power_mult"],
            "lock_enabled": data["lock_enabled"],
            "lock_strength": data["lock_strength"],
            "lock_fov": data["lock_fov"],
            "lock_track": data["lock_track"],
            "lock_sticky": data["lock_sticky"],
            "lock_smooth": data["lock_smooth"],
            "base_aa_enabled": data["base_aa_enabled"],
            "shape_mode": data["shape_mode"].title(),
            "use_dz_radius": data["use_dz_radius"],
            "aim_pattern": data["aim_pattern"].replace("_", " ").title(),
            "pd_kp": data["pd_kp"],
            "pd_kd": data["pd_kd"],
            "magnetic_pull": data["magnetic_pull"],
            "adaptive_strength": data["adaptive_strength"],
            "adaptive_strength_min": data["adaptive_strength_min"],
            "adaptive_strength_max": data["adaptive_strength_max"],
            "anti_shake_blend": data["anti_shake_blend"],
            "prediction_frames": data["prediction_frames"],
            "auto_aa_enabled": data["auto_aa_enabled"],
            "auto_rotation_enabled": data["auto_rotation_enabled"],
            "auto_rotation_speed": data["auto_rotation_speed"],
            "bullet_drop_enabled": data["bullet_drop_enabled"],
            "bullet_drop_factor": data["bullet_drop_factor"],
            "bullet_drop_offset": data["bullet_drop_offset"],
            "anti_sway_enabled": data["anti_sway_enabled"],
            "anti_sway_strength": data["anti_sway_strength"],
            "long_range_track_boost": data["long_range_track_boost"],
            "long_range_predict_lead": data["long_range_predict_lead"],
        })
