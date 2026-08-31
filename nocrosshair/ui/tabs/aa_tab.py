from typing import Dict, Any
import time
from dataclasses import asdict
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QCheckBox, QHBoxLayout, QPushButton, QComboBox, QGridLayout

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
        self._preset_extras: Dict[str, Any] = {}
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

        self.preset_selector = PresetSelector("Preset", ["Light", "Moderate", "Strong", "Precision", "Aimlock", "Lexicon", "Dogz Polar", "SecretAim", "xCloud Hard", "Mobile", "Mobile Lite", "M S1", "M S2", "M S3", "M S4", "Long Range", "FN Mobile xCloud", "FN Controller", "FN Aimbot", "FN Luna"])
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

        self.enhanced_check = QCheckBox("Enable Enhanced Pattern")
        self.enhanced_check.setChecked(False)
        self.enhanced_check.stateChanged.connect(self._on_config_change)
        pattern_layout.addWidget(self.enhanced_check)

        self.head_assist_check = QCheckBox("Head Assist (aim na cabeça)")
        self.head_assist_check.setChecked(False)
        self.head_assist_check.stateChanged.connect(self._on_config_change)
        pattern_layout.addWidget(self.head_assist_check)

        self.head_assist_slider = LabeledDoubleSlider("Head Assist Strength", 0.0, 1.0, 0.4, decimals=2)
        self.head_assist_slider.value_changed.connect(self._on_config_change)
        pattern_layout.addWidget(self.head_assist_slider)

        self.headlock_pulse_check = QCheckBox("Head Lock Pulse (micro-ciclo sobe/segura, estilo Zen)")
        self.headlock_pulse_check.setChecked(False)
        self.headlock_pulse_check.stateChanged.connect(self._on_config_change)
        pattern_layout.addWidget(self.headlock_pulse_check)

        self.headlock_pulse_slider = LabeledSlider("Head Lock Pulse Cycle (ms)", 10, 200, 60)
        self.headlock_pulse_slider.value_changed.connect(self._on_config_change)
        pattern_layout.addWidget(self.headlock_pulse_slider)

        self.headlock_drift_slider = LabeledSlider("Head Lock Drift Limit (0 = off)", 0, 8000, 0)
        self.headlock_drift_slider.value_changed.connect(self._on_config_change)
        pattern_layout.addWidget(self.headlock_drift_slider)

        self.headlock_window_slider = LabeledSlider("Head Lock Window (raio de engajamento)", 500, 8000, 3000)
        self.headlock_window_slider.value_changed.connect(self._on_config_change)
        pattern_layout.addWidget(self.headlock_window_slider)

        self.fire_boost_check = QCheckBox("Fire Boost (multiplica stick na borda do tiro)")
        self.fire_boost_check.setChecked(False)
        self.fire_boost_check.stateChanged.connect(self._on_config_change)
        pattern_layout.addWidget(self.fire_boost_check)

        self.fire_boost_slider = LabeledDoubleSlider("Fire Boost Mult", 1.0, 1.5, 1.15, decimals=2)
        self.fire_boost_slider.value_changed.connect(self._on_config_change)
        pattern_layout.addWidget(self.fire_boost_slider)

        self.fire_boost_ms_slider = LabeledSlider("Fire Boost Duration (ms)", 20, 300, 120)
        self.fire_boost_ms_slider.value_changed.connect(self._on_config_change)
        pattern_layout.addWidget(self.fire_boost_ms_slider)

        self.aim_pattern_selector = PresetSelector("Pattern", ["Standard", "Micro Adjust", "Track Assist", "Predict", "Full"])
        self.aim_pattern_selector.preset_changed.connect(self._on_config_change)
        pattern_layout.addWidget(self.aim_pattern_selector)

        self.pd_kp_slider = LabeledDoubleSlider("PD Kp (Proportional)", 0.01, 0.50, 0.20, decimals=2)
        self.pd_kp_slider.value_changed.connect(self._on_config_change)
        pattern_layout.addWidget(self.pd_kp_slider)

        self.pd_kd_slider = LabeledDoubleSlider("PD Kd (Derivative)", 0.01, 0.30, 0.10, decimals=2)
        self.pd_kd_slider.value_changed.connect(self._on_config_change)
        pattern_layout.addWidget(self.pd_kd_slider)

        self.magnetic_pull_slider = LabeledSlider("Magnetic Pull", 0, 2000, 500)
        self.magnetic_pull_slider.value_changed.connect(self._on_config_change)
        pattern_layout.addWidget(self.magnetic_pull_slider)

        self.micro_adjust_slider = LabeledSlider("Micro Adjust", 0, 2000, 500)
        self.micro_adjust_slider.value_changed.connect(self._on_config_change)
        pattern_layout.addWidget(self.micro_adjust_slider)

        self.adaptive_strength_check = QCheckBox("Adaptive Strength (scale with distance)")
        self.adaptive_strength_check.setChecked(True)
        self.adaptive_strength_check.stateChanged.connect(self._on_config_change)
        pattern_layout.addWidget(self.adaptive_strength_check)

        pd_desc = QLabel("Enhanced Pattern ativa Snap, PD Controller, Micro Adjust,\nTrack Assist e Predict — os motores que antes ficavam desligados.\nStandard = comportamento antigo.")
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

        track_group = SectionGroupBox("Auto Tracking")
        track_layout = QVBoxLayout()

        self.pulse_level_slider = LabeledSlider("Pulse Level (órbita polar 0-5)", 0, 5, 1)
        self.pulse_level_slider.value_changed.connect(self._on_config_change)
        track_layout.addWidget(self.pulse_level_slider)

        self.tracking_speed_slider = LabeledSlider("Tracking Speed (multiplica 1+4%/unid)", 0, 50, 0)
        self.tracking_speed_slider.value_changed.connect(self._on_config_change)
        track_layout.addWidget(self.tracking_speed_slider)

        self.auto_track_check = QCheckBox("Auto Track (reforça tracking em alvos móveis)")
        self.auto_track_check.setChecked(True)
        self.auto_track_check.stateChanged.connect(self._on_config_change)
        track_layout.addWidget(self.auto_track_check)

        self.auto_track_mult_slider = LabeledDoubleSlider("Auto Track Multiplier", 0.0, 1.5, 0.6, decimals=2)
        self.auto_track_mult_slider.value_changed.connect(self._on_config_change)
        track_layout.addWidget(self.auto_track_mult_slider)

        self.auto_track_persist_slider = LabeledSlider("Auto Track Persistence (ms)", 10, 200, 60)
        self.auto_track_persist_slider.value_changed.connect(self._on_config_change)
        track_layout.addWidget(self.auto_track_persist_slider)

        track_desc = QLabel("Pulse Level = órbita polar do right stick (lock-on).\nAuto Track = amplifica o input na direção do alvo móvel\ne mantém a direção por 'Persistence' ms quando solta o stick.")
        track_desc.setStyleSheet("color: #888; font-size: 10px;")
        track_layout.addWidget(track_desc)

        track_group.layout().addLayout(track_layout)
        self.layout().addWidget(track_group)

        cv_group = SectionGroupBox("AimLock (proxy, sem visão)")
        cv_layout = QVBoxLayout()

        self.aimlock_enabled_check = QCheckBox("Enable AimLock (trava no alvo)")
        self.aimlock_enabled_check.setChecked(False)
        self.aimlock_enabled_check.stateChanged.connect(self._on_config_change)
        cv_layout.addWidget(self.aimlock_enabled_check)

        self.aimlock_blend_slider = LabeledDoubleSlider("AimLock Blend (peso do lock)", 0.0, 1.0, 0.7, decimals=2)
        self.aimlock_blend_slider.value_changed.connect(self._on_config_change)
        cv_layout.addWidget(self.aimlock_blend_slider)

        self.aimlock_fov_slider = LabeledSlider("AimLock FOV (graus)", 10, 90, 30)
        self.aimlock_fov_slider.value_changed.connect(self._on_config_change)
        cv_layout.addWidget(self.aimlock_fov_slider)

        cv_group.layout().addLayout(cv_layout)
        self.layout().addWidget(cv_group)

        super_group = SectionGroupBox("AimLock Super (padrão nativo do Fortnite, porém mais forte)")
        super_layout = QVBoxLayout()

        self.aimlock_pull_max_rate_slider = LabeledSlider("PullMaxRate (graus/s — cap de rotação)", 30, 1000, 420)
        self.aimlock_pull_max_rate_slider.value_changed.connect(self._on_config_change)
        super_layout.addWidget(self.aimlock_pull_max_rate_slider)

        self.aimlock_ramp_up_slider = LabeledSlider("RampUp (ms p/ atingir força total)", 0, 500, 80)
        self.aimlock_ramp_up_slider.value_changed.connect(self._on_config_change)
        super_layout.addWidget(self.aimlock_ramp_up_slider)

        self.aimlock_initial_mult_slider = LabeledDoubleSlider("InitialDownsight mult (snap ao engajar)", 1.0, 5.0, 2.5, decimals=1)
        self.aimlock_initial_mult_slider.value_changed.connect(self._on_config_change)
        super_layout.addWidget(self.aimlock_initial_mult_slider)

        self.aimlock_initial_ms_slider = LabeledSlider("InitialDownsight tempo (ms)", 0, 1000, 350)
        self.aimlock_initial_ms_slider.value_changed.connect(self._on_config_change)
        super_layout.addWidget(self.aimlock_initial_ms_slider)

        self.aimlock_adhesion_cone_slider = LabeledDoubleSlider("AdhesionCone (graus — janela do sticky)", 1.0, 30.0, 8.0, decimals=1)
        self.aimlock_adhesion_cone_slider.value_changed.connect(self._on_config_change)
        super_layout.addWidget(self.aimlock_adhesion_cone_slider)

        self.aimlock_slow_strength_slider = LabeledDoubleSlider("Slow strength (amortece seu input perto do alvo)", 0.0, 1.0, 0.85, decimals=2)
        self.aimlock_slow_strength_slider.value_changed.connect(self._on_config_change)
        super_layout.addWidget(self.aimlock_slow_strength_slider)

        self.aimlock_max_yaw_slider = LabeledDoubleSlider("MaxYawCorrection (graus)", 5.0, 90.0, 40.0, decimals=1)
        self.aimlock_max_yaw_slider.value_changed.connect(self._on_config_change)
        super_layout.addWidget(self.aimlock_max_yaw_slider)

        self.aimlock_max_pitch_slider = LabeledDoubleSlider("MaxPitchCorrection (graus)", 5.0, 90.0, 25.0, decimals=1)
        self.aimlock_max_pitch_slider.value_changed.connect(self._on_config_change)
        super_layout.addWidget(self.aimlock_max_pitch_slider)

        self.aimlock_center_mult_slider = LabeledDoubleSlider("Center strength mult (força extra no centro — laser)", 1.0, 3.0, 1.8, decimals=1)
        self.aimlock_center_mult_slider.value_changed.connect(self._on_config_change)
        super_layout.addWidget(self.aimlock_center_mult_slider)

        self.aimlock_glue_mult_slider = LabeledDoubleSlider("Glue drift mult (agarra MAIS quando o inimigo foge)", 1.0, 3.0, 1.6, decimals=1)
        self.aimlock_glue_mult_slider.value_changed.connect(self._on_config_change)
        super_layout.addWidget(self.aimlock_glue_mult_slider)

        self.aimlock_glue_window_slider = LabeledSlider("Glue drift janela (graus p/ atingir mult máx)", 5, 40, 15)
        self.aimlock_glue_window_slider.value_changed.connect(self._on_config_change)
        super_layout.addWidget(self.aimlock_glue_window_slider)

        super_desc = QLabel("O Fortnite nativo rampa a força na BORDA do cone. Aqui é o inverso:\nforça extra no CENTRO (sticky/laser) + snap de 2.5x nos primeiros 350ms\n+ cap de rotação. Mais forte que o padrão nativo, por construção.")
        super_desc.setStyleSheet("color: #888; font-size: 10px;")
        super_layout.addWidget(super_desc)

        super_group.layout().addLayout(super_layout)
        self.layout().addWidget(super_group)

        shake_group = SectionGroupBox("Anti-Shake")
        shake_layout = QVBoxLayout()

        self.anti_shake_slider = LabeledSlider("Blend Factor (%)", 0, 100, 30)
        self.anti_shake_slider.value_changed.connect(self._on_config_change)
        shake_layout.addWidget(self.anti_shake_slider)

        shake_desc = QLabel("Anti-shake applies EMA smoothing to output.\n0% = no smoothing, 100% = full smoothing (laggy).")
        shake_desc.setStyleSheet("color: #888; font-size: 10px;")
        shake_layout.addWidget(shake_desc)

        shake_group.layout().addLayout(shake_layout)
        self.layout().addWidget(shake_group)

        tweak_group = SectionGroupBox("Tweak Zone (Ch7 S4 Meta)")
        tweak_layout = QVBoxLayout()

        self.tweak_zone_check = QCheckBox("Enable Tweak Zone (micro-movements boost)")
        self.tweak_zone_check.setChecked(True)
        self.tweak_zone_check.stateChanged.connect(self._on_config_change)
        tweak_layout.addWidget(self.tweak_zone_check)

        self.tweak_zone_pct_slider = LabeledDoubleSlider("Zone % (stick range)", 0.2, 1.0, 0.6, decimals=2)
        self.tweak_zone_pct_slider.value_changed.connect(self._on_config_change)
        tweak_layout.addWidget(self.tweak_zone_pct_slider)

        self.tweak_zone_offset_slider = LabeledDoubleSlider("Offset (magnetism boost)", 1.0, 4.0, 2.0, decimals=1)
        self.tweak_zone_offset_slider.value_changed.connect(self._on_config_change)
        tweak_layout.addWidget(self.tweak_zone_offset_slider)

        tweak_desc = QLabel("Micro-movements below Zone % activate Tweak Zone.\nMagnetism is boosted by Offset, slowdown is reduced.")
        tweak_desc.setStyleSheet("color: #888; font-size: 10px;")
        tweak_layout.addWidget(tweak_desc)

        tweak_group.layout().addLayout(tweak_layout)
        self.layout().addWidget(tweak_group)

        rs_group = SectionGroupBox("Right Stick Smoothing")
        rs_layout = QVBoxLayout()

        self.rs_smoothing_slider = LabeledDoubleSlider("Smoothing", 0.0, 0.9, 0.0, decimals=2)
        self.rs_smoothing_slider.value_changed.connect(self._on_config_change)
        rs_layout.addWidget(self.rs_smoothing_slider)

        self.rotational_mag_gate_slider = LabeledSlider("Orbit Gate (min input)", 50, 800, 200)
        self.rotational_mag_gate_slider.value_changed.connect(self._on_config_change)
        rs_layout.addWidget(self.rotational_mag_gate_slider)

        self.rotational_radius_mult_slider = LabeledDoubleSlider("Orbit Radius Mult", 0.5, 3.0, 1.5, decimals=1)
        self.rotational_radius_mult_slider.value_changed.connect(self._on_config_change)
        rs_layout.addWidget(self.rotational_radius_mult_slider)

        rs_desc = QLabel("Smoothing reduces jitter on micro-movements.\nOrbit Gate: min input for rotational AA.\nOrbit Radius Mult: orbit size multiplier.")
        rs_desc.setStyleSheet("color: #888; font-size: 10px;")
        rs_layout.addWidget(rs_desc)

        rs_group.layout().addLayout(rs_layout)
        self.layout().addWidget(rs_group)

        gen2_group = SectionGroupBox("Advanced Aim (2ª geração)")
        gen2_layout = QVBoxLayout()

        self.oef_check = QCheckBox("One-Euro Anti-Shake (filtro adaptativo)")
        self.oef_check.setChecked(False)
        self.oef_check.stateChanged.connect(self._on_config_change)
        gen2_layout.addWidget(self.oef_check)

        self.oef_min_cutoff_slider = LabeledDoubleSlider("Min Cutoff (Hz)", 0.1, 10.0, 1.0, decimals=1)
        self.oef_min_cutoff_slider.value_changed.connect(self._on_config_change)
        gen2_layout.addWidget(self.oef_min_cutoff_slider)

        self.oef_beta_slider = LabeledDoubleSlider("Beta (velocidade→cutoff)", 0.0, 0.5, 0.05, decimals=2)
        self.oef_beta_slider.value_changed.connect(self._on_config_change)
        gen2_layout.addWidget(self.oef_beta_slider)

        self.oef_d_cutoff_slider = LabeledDoubleSlider("D-Cutoff (Hz derivada)", 0.1, 10.0, 1.0, decimals=1)
        self.oef_d_cutoff_slider.value_changed.connect(self._on_config_change)
        gen2_layout.addWidget(self.oef_d_cutoff_slider)

        gen2_layout.addWidget(HLine())
        pred_label = QLabel("Predictive Tracker (predição alfa-beta + aceleração)")
        pred_label.setStyleSheet("font-weight: bold; color: #0f8;")
        gen2_layout.addWidget(pred_label)

        self.predictive_check = QCheckBox("Enable Predictive Tracker (lead em alvos móveis)")
        self.predictive_check.setChecked(False)
        self.predictive_check.stateChanged.connect(self._on_config_change)
        gen2_layout.addWidget(self.predictive_check)

        self.predictive_vel_alpha_slider = LabeledDoubleSlider("Vel Alpha (EMA velocidade)", 0.01, 0.50, 0.15, decimals=2)
        self.predictive_vel_alpha_slider.value_changed.connect(self._on_config_change)
        gen2_layout.addWidget(self.predictive_vel_alpha_slider)

        self.predictive_accel_alpha_slider = LabeledDoubleSlider("Accel Alpha (EMA aceleração)", 0.0, 0.50, 0.05, decimals=2)
        self.predictive_accel_alpha_slider.value_changed.connect(self._on_config_change)
        gen2_layout.addWidget(self.predictive_accel_alpha_slider)

        self.predictive_horizon_slider = LabeledDoubleSlider("Lead Horizon (ms)", 10.0, 120.0, 40.0, decimals=1)
        self.predictive_horizon_slider.value_changed.connect(self._on_config_change)
        gen2_layout.addWidget(self.predictive_horizon_slider)

        self.predictive_min_speed_slider = LabeledSlider("Min Speed (unid/ms)", 50, 1000, 200)
        self.predictive_min_speed_slider.value_changed.connect(self._on_config_change)
        gen2_layout.addWidget(self.predictive_min_speed_slider)

        self.predictive_max_lead_slider = LabeledSlider("Max Lead", 500, 8000, 3000)
        self.predictive_max_lead_slider.value_changed.connect(self._on_config_change)
        gen2_layout.addWidget(self.predictive_max_lead_slider)

        self.predictive_consistency_slider = LabeledSlider("Consistency (frames p/ direção)", 1, 10, 3)
        self.predictive_consistency_slider.value_changed.connect(self._on_config_change)
        gen2_layout.addWidget(self.predictive_consistency_slider)

        self.predictive_direction_blend_slider = LabeledDoubleSlider("Direction Blend (follow_dir vs velocidade)", 0.0, 1.0, 0.7, decimals=2)
        self.predictive_direction_blend_slider.value_changed.connect(self._on_config_change)
        gen2_layout.addWidget(self.predictive_direction_blend_slider)

        gen2_layout.addWidget(HLine())
        adhesion_label = QLabel("Adhesion Buffer (mais grude)")
        adhesion_label.setStyleSheet("font-weight: bold; color: #0f8;")
        gen2_layout.addWidget(adhesion_label)

        self.adhesion_check = QCheckBox("Enable Adhesion Buffer (persistência + axis-lock)")
        self.adhesion_check.setChecked(False)
        self.adhesion_check.stateChanged.connect(self._on_config_change)
        gen2_layout.addWidget(self.adhesion_check)

        self.adhesion_hold_slider = LabeledSlider("Hold (ms)", 20, 300, 120)
        self.adhesion_hold_slider.value_changed.connect(self._on_config_change)
        gen2_layout.addWidget(self.adhesion_hold_slider)

        self.adhesion_decay_slider = LabeledDoubleSlider("Decay", 0.05, 1.0, 0.35, decimals=2)
        self.adhesion_decay_slider.value_changed.connect(self._on_config_change)
        gen2_layout.addWidget(self.adhesion_decay_slider)

        self.adhesion_axis_slider = LabeledDoubleSlider("Axis Lock", 0.0, 0.8, 0.18, decimals=2)
        self.adhesion_axis_slider.value_changed.connect(self._on_config_change)
        gen2_layout.addWidget(self.adhesion_axis_slider)

        self.adhesion_min_mag_slider = LabeledSlider("Min Mag (limiar de liberação)", 20, 1000, 100)
        self.adhesion_min_mag_slider.value_changed.connect(self._on_config_change)
        gen2_layout.addWidget(self.adhesion_min_mag_slider)

        self.follow_assist_check = QCheckBox("Follow Assist (puxa na direção do alvo quando travado)")
        self.follow_assist_check.setChecked(False)
        self.follow_assist_check.stateChanged.connect(self._on_config_change)
        gen2_layout.addWidget(self.follow_assist_check)

        self.follow_assist_pull_slider = LabeledSlider("Follow Assist Pull", 50, 1500, 300)
        self.follow_assist_pull_slider.value_changed.connect(self._on_config_change)
        gen2_layout.addWidget(self.follow_assist_pull_slider)

        gen2_desc = QLabel("One-Euro: suaviza jitter e responde rápido (anti-shake adaptativo).\nPredictive Tracker: adianta a mira com lead = v·T + ½·a·T².\nAdhesion Buffer: segura a direção ao soltar o stick + axis-lock no centro.\nFollow Assist: segue o strafe do inimigo sem esforço (direção do AA).")
        gen2_desc.setStyleSheet("color: #888; font-size: 10px;")
        gen2_layout.addWidget(gen2_desc)

        gen2_group.layout().addLayout(gen2_layout)
        self.layout().addWidget(gen2_group)

        opt_group = SectionGroupBox("Optimized Pipeline (2ª geração)")
        opt_layout = QVBoxLayout()

        self.opt_pipeline_check = QCheckBox("Use Optimized Pipeline (reduz latência de ~1.5ms para ~0.15ms)")
        self.opt_pipeline_check.setChecked(False)
        self.opt_pipeline_check.stateChanged.connect(self._on_config_change)
        opt_layout.addWidget(self.opt_pipeline_check)

        opt_label = QLabel("Rotational AA Adaptativo")
        opt_label.setStyleSheet("font-weight: bold; color: #0f8;")
        opt_layout.addWidget(opt_label)

        self.opt_rot_speed_slider = LabeledDoubleSlider("Rotation Speed", 0.05, 1.0, 0.3, decimals=2)
        self.opt_rot_speed_slider.value_changed.connect(self._on_config_change)
        opt_layout.addWidget(self.opt_rot_speed_slider)

        self.opt_rot_radius_slider = LabeledDoubleSlider("Radius Multiplier", 0.1, 3.0, 1.0, decimals=1)
        self.opt_rot_radius_slider.value_changed.connect(self._on_config_change)
        opt_layout.addWidget(self.opt_rot_radius_slider)

        opt_label2 = QLabel("Predict Engine (Kalman + alfa-beta)")
        opt_label2.setStyleSheet("font-weight: bold; color: #0f8;")
        opt_layout.addWidget(opt_label2)

        self.opt_predict_check = QCheckBox("Enable Predict Engine")
        self.opt_predict_check.setChecked(True)
        self.opt_predict_check.stateChanged.connect(self._on_config_change)
        opt_layout.addWidget(self.opt_predict_check)

        self.opt_predict_lead_slider = LabeledDoubleSlider("Lead Horizon (ms)", 10.0, 120.0, 40.0, decimals=1)
        self.opt_predict_lead_slider.value_changed.connect(self._on_config_change)
        opt_layout.addWidget(self.opt_predict_lead_slider)

        self.opt_predict_kalman_slider = LabeledDoubleSlider("Kalman Weight", 0.0, 1.0, 0.3, decimals=2)
        self.opt_predict_kalman_slider.value_changed.connect(self._on_config_change)
        opt_layout.addWidget(self.opt_predict_kalman_slider)

        opt_label3 = QLabel("Micro Correction")
        opt_label3.setStyleSheet("font-weight: bold; color: #0f8;")
        opt_layout.addWidget(opt_label3)

        self.opt_micro_check = QCheckBox("Enable Micro Correction (anti-overshoot)")
        self.opt_micro_check.setChecked(True)
        self.opt_micro_check.stateChanged.connect(self._on_config_change)
        opt_layout.addWidget(self.opt_micro_check)

        self.opt_micro_pull_slider = LabeledDoubleSlider("Micro Pull Strength", 0.0, 1.0, 0.3, decimals=2)
        self.opt_micro_pull_slider.value_changed.connect(self._on_config_change)
        opt_layout.addWidget(self.opt_micro_pull_slider)

        opt_desc = QLabel("Pipeline otimizado com lookup tables (10x mais rápido).\nRotational adaptativo ajusta velocidade baseado no estado de tracking.\nPredict Engine usa Kalman + alfa-beta para predição de alvos.\nMicro Correction previne overshoot perto do alvo.")
        opt_desc.setStyleSheet("color: #888; font-size: 10px;")
        opt_layout.addWidget(opt_desc)

        opt_group.layout().addLayout(opt_layout)
        self.layout().addWidget(opt_group)

        auto_group = SectionGroupBox("Auto-Tuning (ML Leve)")
        auto_layout = QVBoxLayout()

        self.auto_tuning_check = QCheckBox("Enable Auto-Tuning (ajusta parâmetros automaticamente)")
        self.auto_tuning_check.setChecked(False)
        self.auto_tuning_check.stateChanged.connect(self._on_config_change)
        auto_layout.addWidget(self.auto_tuning_check)

        auto_label = QLabel("Adaptive Sensitivity")
        auto_label.setStyleSheet("font-weight: bold; color: #0f8;")
        auto_layout.addWidget(auto_label)

        self.auto_min_mult_slider = LabeledDoubleSlider("Min Multiplier", 0.3, 1.0, 0.7, decimals=2)
        self.auto_min_mult_slider.value_changed.connect(self._on_config_change)
        auto_layout.addWidget(self.auto_min_mult_slider)

        self.auto_max_mult_slider = LabeledDoubleSlider("Max Multiplier", 1.0, 2.0, 1.3, decimals=2)
        self.auto_max_mult_slider.value_changed.connect(self._on_config_change)
        auto_layout.addWidget(self.auto_max_mult_slider)

        self.auto_cooldown_slider = LabeledSlider("Cooldown (s)", 5, 120, 30)
        self.auto_cooldown_slider.value_changed.connect(self._on_config_change)
        auto_layout.addWidget(self.auto_cooldown_slider)

        auto_desc = QLabel("Auto-tuning ajusta a força do aim assist baseado no hit rate.\nSe você está acertando muito → reduz força (jogador está bem).\nSe você está errando → aumenta força (jogador precisa de ajuda).\nDetecta patches e reseta profiles automaticamente.")
        auto_desc.setStyleSheet("color: #888; font-size: 10px;")
        auto_layout.addWidget(auto_desc)

        auto_group.layout().addLayout(auto_layout)
        self.layout().addWidget(auto_group)

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

        spam_group = SectionGroupBox("Aim Spam (Zen Style)")
        spam_layout = QVBoxLayout()

        self.aim_spam_check = QCheckBox("Enable Aim Spam (ADS refresh)")
        self.aim_spam_check.setChecked(False)
        self.aim_spam_check.stateChanged.connect(self._on_config_change)
        spam_layout.addWidget(self.aim_spam_check)

        self.aim_spam_interval_slider = LabeledSlider("Interval (ms)", 80, 400, 180)
        self.aim_spam_interval_slider.value_changed.connect(self._on_config_change)
        spam_layout.addWidget(self.aim_spam_interval_slider)

        self.aim_spam_hold_slider = LabeledSlider("Hold (ms)", 10, 100, 40)
        self.aim_spam_hold_slider.value_changed.connect(self._on_config_change)
        spam_layout.addWidget(self.aim_spam_hold_slider)

        spam_desc = QLabel("Micro-cycle de ADS durante o tiro para refrescar o AA nativo.\nPode interferir no ADS em xCloud — use com cuidado.")
        spam_desc.setStyleSheet("color: #6B7C93; font-size: 10px;")
        spam_layout.addWidget(spam_desc)

        spam_group.layout().addLayout(spam_layout)
        self.layout().addWidget(spam_group)

        rf_group = SectionGroupBox("Rapid Fire (Zen Style)")
        rf_layout = QVBoxLayout()

        self.rapid_fire_check = QCheckBox("Enable Rapid Fire")
        self.rapid_fire_check.setChecked(False)
        self.rapid_fire_check.stateChanged.connect(self._on_config_change)
        rf_layout.addWidget(self.rapid_fire_check)

        self.rapid_fire_mode_combo = QComboBox()
        self.rapid_fire_mode_combo.addItems(["Universal (todas as armas)", "Pistola (semi-auto)", "Shotgun", "Custom"])
        self.rapid_fire_mode_combo.currentTextChanged.connect(self._on_config_change)
        rf_layout.addWidget(self.rapid_fire_mode_combo)

        self.rapid_fire_speed_slider = LabeledSlider("Speed (shots/s)", 10, 120, 50)
        self.rapid_fire_speed_slider.value_changed.connect(self._on_config_change)
        rf_layout.addWidget(self.rapid_fire_speed_slider)

        self.rapid_fire_ratio_slider = LabeledDoubleSlider("Hold Ratio", 0.30, 0.95, 0.75, decimals=2)
        self.rapid_fire_ratio_slider.value_changed.connect(self._on_config_change)
        rf_layout.addWidget(self.rapid_fire_ratio_slider)

        rf_desc = QLabel("Turbo no botão de atirar (R2). Release curto = full-auto (AR/SMG)\nnão stuttera; semi-auto (pistola) dispara no teto.\nUniversal é o modo equilibrado pra todas as armas.")
        rf_desc.setStyleSheet("color: #6B7C93; font-size: 10px;")
        rf_layout.addWidget(rf_desc)

        rf_group.layout().addLayout(rf_layout)
        self.layout().addWidget(rf_group)

        br_group = SectionGroupBox("Bloom Reducer (Zen Style)")
        br_layout = QVBoxLayout()

        self.bloom_reducer_check = QCheckBox("Enable Bloom Reducer (rajada + pausa)")
        self.bloom_reducer_check.setChecked(False)
        self.bloom_reducer_check.stateChanged.connect(self._on_config_change)
        br_layout.addWidget(self.bloom_reducer_check)

        self.br_shots_slider = LabeledSlider("Tiros por rajada", 2, 10, 3)
        self.br_shots_slider.value_changed.connect(self._on_config_change)
        br_layout.addWidget(self.br_shots_slider)

        self.br_hold_slider = LabeledSlider("Duração do tiro (ms)", 10, 60, 25)
        self.br_hold_slider.value_changed.connect(self._on_config_change)
        br_layout.addWidget(self.br_hold_slider)

        self.br_tap_slider = LabeledSlider("Separação entre tiros (ms)", 10, 60, 20)
        self.br_tap_slider.value_changed.connect(self._on_config_change)
        br_layout.addWidget(self.br_tap_slider)

        self.br_reset_slider = LabeledSlider("Pausa de reset de bloom (ms)", 100, 600, 250)
        self.br_reset_slider.value_changed.connect(self._on_config_change)
        br_layout.addWidget(self.br_reset_slider)

        br_desc = QLabel("Segurar R2 vira rajadas curtas com pausa — o bloom do\nFortnite zera na pausa e cada rajada recomeça com a 1ª bala\n(spread mínimo). Ideal pra AR em média/longa distância.\nNÃO usar junto com Rapid Fire (conflito no gatilho).")
        br_desc.setStyleSheet("color: #6B7C93; font-size: 10px;")
        br_layout.addWidget(br_desc)

        br_group.layout().addLayout(br_layout)
        self.layout().addWidget(br_group)

        silent_group = SectionGroupBox("Silent Aim / Silent Hit (Zero Shake)")
        silent_layout = QVBoxLayout()

        self.silent_aim_check = QCheckBox("Silent Aim (ADS-only: slowdown + pull forte, zero shake)")
        self.silent_aim_check.setChecked(False)
        self.silent_aim_check.stateChanged.connect(self._on_config_change)
        silent_layout.addWidget(self.silent_aim_check)

        self.silent_aim_slow_slider = LabeledDoubleSlider("Silent Aim Slow Mult", 1.0, 2.5, 1.4, decimals=1)
        self.silent_aim_slow_slider.value_changed.connect(self._on_config_change)
        silent_layout.addWidget(self.silent_aim_slow_slider)

        self.silent_aim_pull_slider = LabeledDoubleSlider("Silent Aim Pull Mult", 1.0, 3.0, 1.6, decimals=1)
        self.silent_aim_pull_slider.value_changed.connect(self._on_config_change)
        silent_layout.addWidget(self.silent_aim_pull_slider)

        self.silent_aim_shake_slider = LabeledDoubleSlider("Silent Aim Anti-Shake", 0.0, 0.8, 0.55, decimals=2)
        self.silent_aim_shake_slider.value_changed.connect(self._on_config_change)
        silent_layout.addWidget(self.silent_aim_shake_slider)

        silent_layout.addWidget(HLine())

        self.silent_hit_check = QCheckBox("Silent Hit (Hip-fire: pull forte no curta distância, zero shake)")
        self.silent_hit_check.setChecked(False)
        self.silent_hit_check.stateChanged.connect(self._on_config_change)
        silent_layout.addWidget(self.silent_hit_check)

        self.silent_hit_slow_slider = LabeledDoubleSlider("Silent Hit Slow Mult", 1.0, 2.0, 1.2, decimals=1)
        self.silent_hit_slow_slider.value_changed.connect(self._on_config_change)
        silent_layout.addWidget(self.silent_hit_slow_slider)

        self.silent_hit_pull_slider = LabeledDoubleSlider("Silent Hit Pull Mult", 1.0, 4.0, 2.0, decimals=1)
        self.silent_hit_pull_slider.value_changed.connect(self._on_config_change)
        silent_layout.addWidget(self.silent_hit_pull_slider)

        self.silent_hit_shake_slider = LabeledDoubleSlider("Silent Hit Anti-Shake", 0.0, 0.8, 0.50, decimals=2)
        self.silent_hit_shake_slider.value_changed.connect(self._on_config_change)
        silent_layout.addWidget(self.silent_hit_shake_slider)

        silent_desc = QLabel("Silent Aim: ativa só no ADS — mantém a mira grudada\ncom slowdown+pull fortes e ZERO shake na tela.\nSilent Hit: ativa no hip-fire — tracking automático\nde curta distância (shotgun/SMG), zero oscilação.\nAmbos pulam a órbita rotacional (senoide).")
        silent_desc.setStyleSheet("color: #888; font-size: 10px;")
        silent_layout.addWidget(silent_desc)

        silent_group.layout().addLayout(silent_layout)
        self.layout().addWidget(silent_group)

        ls_freq_group = SectionGroupBox("Left Stick Frequency (AA Trigger)")
        ls_freq_layout = QVBoxLayout()

        self.ls_freq_check = QCheckBox("Enable Left Stick Freq (micro-oscillation, sem mover personagem)")
        self.ls_freq_check.setChecked(False)
        self.ls_freq_check.stateChanged.connect(self._on_config_change)
        ls_freq_layout.addWidget(self.ls_freq_check)

        self.ls_freq_amplitude_slider = LabeledSlider("Amplitude (1-30)", 1, 30, 10)
        self.ls_freq_amplitude_slider.value_changed.connect(self._on_config_change)
        ls_freq_layout.addWidget(self.ls_freq_amplitude_slider)

        self.ls_freq_frequency_slider = LabeledDoubleSlider("Frequency (Hz)", 1.0, 50.0, 15.0, decimals=1)
        self.ls_freq_frequency_slider.value_changed.connect(self._on_config_change)
        ls_freq_layout.addWidget(self.ls_freq_frequency_slider)

        self.ls_freq_shape_selector = PresetSelector("Shape", ["Sine", "Triangle", "Square"])
        self.ls_freq_shape_selector.preset_changed.connect(self._on_config_change)
        ls_freq_layout.addWidget(self.ls_freq_shape_selector)

        self.ls_freq_gate_slider = LabeledSlider("Gate (stick threshold)", 100, 2000, 500)
        self.ls_freq_gate_slider.value_changed.connect(self._on_config_change)
        ls_freq_layout.addWidget(self.ls_freq_gate_slider)

        self.ls_freq_aggressive_check = QCheckBox("Aggressive Mode (square wave, amp 100, 500Hz — estilo Aboki/Cronus)")
        self.ls_freq_aggressive_check.setChecked(False)
        self.ls_freq_aggressive_check.stateChanged.connect(self._on_config_change)
        ls_freq_layout.addWidget(self.ls_freq_aggressive_check)

        ls_freq_desc = QLabel("Micro-oscilação no left stick que mantém o AA nativo\nativo SEM mover o personagem. Amplitude < deadzone do jogo.\nGate: se o stick estiver acima deste valor, não oscila.\nFreq 15Hz + Amplitude 10 é um bom ponto de partida.")
        ls_freq_desc.setStyleSheet("color: #888; font-size: 10px;")
        ls_freq_layout.addWidget(ls_freq_desc)

        ls_freq_group.layout().addLayout(ls_freq_layout)
        self.layout().addWidget(ls_freq_group)

        hs_group = SectionGroupBox("Head Snap Engine (Headshot Mod)")
        hs_layout = QVBoxLayout()

        self.hs_enabled_check = QCheckBox("Enable Head Snap (micro-flick vertical pra cabeça)")
        self.hs_enabled_check.setChecked(False)
        self.hs_enabled_check.stateChanged.connect(self._on_config_change)
        hs_layout.addWidget(self.hs_enabled_check)

        self.hs_strength_slider = LabeledSlider("Strength (1-100)", 1, 100, 40)
        self.hs_strength_slider.value_changed.connect(self._on_config_change)
        hs_layout.addWidget(self.hs_strength_slider)

        self.hs_height_slider = LabeledSlider("Height (100-2000)", 100, 2000, 800)
        self.hs_height_slider.value_changed.connect(self._on_config_change)
        hs_layout.addWidget(self.hs_height_slider)

        self.hs_duration_slider = LabeledSlider("Duration (ms)", 50, 500, 150)
        self.hs_duration_slider.value_changed.connect(self._on_config_change)
        hs_layout.addWidget(self.hs_duration_slider)

        self.hs_cooldown_slider = LabeledSlider("Cooldown (ms)", 100, 1000, 300)
        self.hs_cooldown_slider.value_changed.connect(self._on_config_change)
        hs_layout.addWidget(self.hs_cooldown_slider)

        self.hs_smooth_slider = LabeledDoubleSlider("Smooth (0.0-1.0)", 0.0, 1.0, 0.3, decimals=2)
        self.hs_smooth_slider.value_changed.connect(self._on_config_change)
        hs_layout.addWidget(self.hs_smooth_slider)

        self.hs_mode_selector = PresetSelector("Mode", ["Auto", "Button", "Both"])
        self.hs_mode_selector.preset_changed.connect(self._on_config_change)
        hs_layout.addWidget(self.hs_mode_selector)

        self.hs_ads_only_check = QCheckBox("ADS Only (só ativa em ADS)")
        self.hs_ads_only_check.setChecked(True)
        self.hs_ads_only_check.stateChanged.connect(self._on_config_change)
        hs_layout.addWidget(self.hs_ads_only_check)

        hs_desc = QLabel("Micro-flick vertical que sobe o crosshair pro nível da\ncabeça. Auto: detecta engagement por padrão de input.\nButton: ativa com R3/RS. Both: os dois.\nStrength: intensidade. Height: altura do snap.")
        hs_desc.setStyleSheet("color: #888; font-size: 10px;")
        hs_layout.addWidget(hs_desc)

        hs_group.layout().addLayout(hs_layout)
        self.layout().addWidget(hs_group)

        # ── Multi-Engine Polar (4 motores simultâneos) ──
        mp_group = SectionGroupBox("Multi-Engine Polar (4 órbitas simultâneas)")
        mp_layout = QVBoxLayout()

        self.mp_enabled_check = QCheckBox("Enable Multi-Polar (4 motores: close/medium/long/sniper)")
        self.mp_enabled_check.setChecked(False)
        self.mp_enabled_check.stateChanged.connect(self._on_config_change)
        mp_layout.addWidget(self.mp_enabled_check)

        mp_inner = QGridLayout()
        # Close
        mp_inner.addWidget(QLabel("Close (Shotgun/SMG):"), 0, 0)
        self.mp_close_radius = LabeledSlider("Radius", 1, 10, 3)
        self.mp_close_radius.value_changed.connect(self._on_config_change)
        mp_inner.addWidget(self.mp_close_radius, 0, 1)
        self.mp_close_angle = LabeledDoubleSlider("Angle", 1.0, 30.0, 8.0, decimals=1)
        self.mp_close_angle.value_changed.connect(self._on_config_change)
        mp_inner.addWidget(self.mp_close_angle, 0, 2)
        # Medium
        mp_inner.addWidget(QLabel("Medium (SMG/AR):"), 1, 0)
        self.mp_medium_radius = LabeledSlider("Radius", 3, 20, 8)
        self.mp_medium_radius.value_changed.connect(self._on_config_change)
        mp_inner.addWidget(self.mp_medium_radius, 1, 1)
        self.mp_medium_angle = LabeledDoubleSlider("Angle", 1.0, 30.0, 12.0, decimals=1)
        self.mp_medium_angle.value_changed.connect(self._on_config_change)
        mp_inner.addWidget(self.mp_medium_angle, 1, 2)
        # Long
        mp_inner.addWidget(QLabel("Long (AR):"), 2, 0)
        self.mp_long_radius = LabeledSlider("Radius", 5, 30, 14)
        self.mp_long_radius.value_changed.connect(self._on_config_change)
        mp_inner.addWidget(self.mp_long_radius, 2, 1)
        self.mp_long_angle = LabeledDoubleSlider("Angle", 1.0, 40.0, 18.0, decimals=1)
        self.mp_long_angle.value_changed.connect(self._on_config_change)
        mp_inner.addWidget(self.mp_long_angle, 2, 2)
        # Sniper
        mp_inner.addWidget(QLabel("Sniper:"), 3, 0)
        self.mp_sniper_radius = LabeledSlider("Radius", 10, 40, 20)
        self.mp_sniper_radius.value_changed.connect(self._on_config_change)
        mp_inner.addWidget(self.mp_sniper_radius, 3, 1)
        self.mp_sniper_angle = LabeledDoubleSlider("Angle", 5.0, 50.0, 22.0, decimals=1)
        self.mp_sniper_angle.value_changed.connect(self._on_config_change)
        mp_inner.addWidget(self.mp_sniper_angle, 3, 2)
        self.mp_sniper_ads_only = QCheckBox("Sniper ADS Only")
        self.mp_sniper_ads_only.setChecked(True)
        self.mp_sniper_ads_only.stateChanged.connect(self._on_config_change)
        mp_inner.addWidget(self.mp_sniper_ads_only, 3, 3)
        mp_layout.addLayout(mp_inner)

        mp_desc = QLabel("4 órbitas simultâneas com raios e formatos diferentes.\nClose=amp baixa/freq alta. Sniper=amp alto/freq baixa.\nTodos rodam ao mesmo tempo criando órbita rica e multi-camada.")
        mp_desc.setStyleSheet("color: #888; font-size: 10px;")
        mp_layout.addWidget(mp_desc)

        mp_group.layout().addLayout(mp_layout)
        self.layout().addWidget(mp_group)

        # ── Ghost Tracker ──
        gt_group = SectionGroupBox("Ghost Tracker (desaceleração no aim bubble)")
        gt_layout = QVBoxLayout()

        self.gt_enabled_check = QCheckBox("Enable Ghost Tracker (freia quando no bubble)")
        self.gt_enabled_check.setChecked(False)
        self.gt_enabled_check.stateChanged.connect(self._on_config_change)
        gt_layout.addWidget(self.gt_enabled_check)

        gt_inner = QGridLayout()
        gt_inner.addWidget(QLabel("Bubble Radius:"), 0, 0)
        self.gt_bubble = LabeledSlider("Radius (stick units)", 2000, 15000, 8000)
        self.gt_bubble.value_changed.connect(self._on_config_change)
        gt_inner.addWidget(self.gt_bubble, 0, 1)
        gt_inner.addWidget(QLabel("Decel Strength:"), 1, 0)
        self.gt_decel = LabeledDoubleSlider("Strength", 0.0, 1.0, 0.3, decimals=2)
        self.gt_decel.value_changed.connect(self._on_config_change)
        gt_inner.addWidget(self.gt_decel, 1, 1)
        gt_inner.addWidget(QLabel("Decel Ramp:"), 2, 0)
        self.gt_ramp = LabeledDoubleSlider("Ramp", 0.0, 1.0, 0.5, decimals=2)
        self.gt_ramp.value_changed.connect(self._on_config_change)
        gt_inner.addWidget(self.gt_ramp, 2, 1)
        gt_inner.addWidget(QLabel("Stick Threshold:"), 3, 0)
        self.gt_threshold = LabeledSlider("Threshold", 1000, 10000, 4000)
        self.gt_threshold.value_changed.connect(self._on_config_change)
        gt_inner.addWidget(self.gt_threshold, 3, 1)
        gt_layout.addLayout(gt_inner)

        gt_desc = QLabel("Desacelera o stick quando crosshair está perto do alvo.\nAnti-overshoot: empurra forte demais → freia suavemente.\nMantém o grude no aim bubble.")
        gt_desc.setStyleSheet("color: #888; font-size: 10px;")
        gt_layout.addWidget(gt_desc)

        gt_group.layout().addLayout(gt_layout)
        self.layout().addWidget(gt_group)

        # ── Burst Mode ──
        bm_group = SectionGroupBox("Burst Mode (boost primeiros tiros)")
        bm_layout = QVBoxLayout()

        self.bm_enabled_check = QCheckBox("Enable Burst Mode (boost nos primeiros 3 tiros)")
        self.bm_enabled_check.setChecked(False)
        self.bm_enabled_check.stateChanged.connect(self._on_config_change)
        bm_layout.addWidget(self.bm_enabled_check)

        bm_inner = QGridLayout()
        bm_inner.addWidget(QLabel("Burst Count:"), 0, 0)
        self.bm_count = LabeledSlider("Tiros (2-6)", 2, 6, 3)
        self.bm_count.value_changed.connect(self._on_config_change)
        bm_inner.addWidget(self.bm_count, 0, 1)
        bm_inner.addWidget(QLabel("Aim Boost:"), 1, 0)
        self.bm_aim_boost = LabeledDoubleSlider("Boost", 1.0, 3.0, 1.5, decimals=1)
        self.bm_aim_boost.value_changed.connect(self._on_config_change)
        bm_inner.addWidget(self.bm_aim_boost, 1, 1)
        bm_inner.addWidget(QLabel("Recoil Reduction:"), 2, 0)
        self.bm_recoil_red = LabeledDoubleSlider("Reduction", 0.1, 1.0, 0.7, decimals=2)
        self.bm_recoil_red.value_changed.connect(self._on_config_change)
        bm_inner.addWidget(self.bm_recoil_red, 2, 1)
        bm_inner.addWidget(QLabel("Cooldown (ms):"), 3, 0)
        self.bm_cooldown = LabeledSlider("Cooldown", 50, 500, 200)
        self.bm_cooldown.value_changed.connect(self._on_config_change)
        bm_inner.addWidget(self.bm_cooldown, 3, 1)
        bm_layout.addLayout(bm_inner)

        bm_desc = QLabel("Boost de aim assist nos primeiros N tiros de cada rajada.\nCompensa first-shot kick e recoil inicial.\nCooldown: tempo entre rajadas pra resetar counter.")
        bm_desc.setStyleSheet("color: #888; font-size: 10px;")
        bm_layout.addWidget(bm_desc)

        bm_group.layout().addLayout(bm_layout)
        self.layout().addWidget(bm_group)

        # ── Batts Sticky (Diamond) ──
        bs_group = SectionGroupBox("Batts Sticky (Diamond Pattern)")
        bs_layout = QVBoxLayout()

        self.bs_enabled_check = QCheckBox("Enable Batts Sticky (diamond pattern)")
        self.bs_enabled_check.setChecked(False)
        self.bs_enabled_check.stateChanged.connect(self._on_config_change)
        bs_layout.addWidget(self.bs_enabled_check)

        bs_inner = QGridLayout()
        bs_inner.addWidget(QLabel("ADS Size:"), 0, 0)
        self.bs_ads_size = LabeledSlider("Size", 5, 30, 14)
        self.bs_ads_size.value_changed.connect(self._on_config_change)
        bs_inner.addWidget(self.bs_ads_size, 0, 1)
        bs_inner.addWidget(QLabel("ADS+Fire Size:"), 1, 0)
        self.bs_ads_fire_size = LabeledSlider("Size", 5, 30, 16)
        self.bs_ads_fire_size.value_changed.connect(self._on_config_change)
        bs_inner.addWidget(self.bs_ads_fire_size, 1, 1)
        bs_inner.addWidget(QLabel("Hipfire Size:"), 2, 0)
        self.bs_hipfire_size = LabeledSlider("Size", 5, 30, 18)
        self.bs_hipfire_size.value_changed.connect(self._on_config_change)
        bs_inner.addWidget(self.bs_hipfire_size, 2, 1)
        bs_inner.addWidget(QLabel("ADS Speed:"), 0, 2)
        self.bs_ads_speed = LabeledDoubleSlider("Speed", 1.0, 20.0, 8.0, decimals=1)
        self.bs_ads_speed.value_changed.connect(self._on_config_change)
        bs_inner.addWidget(self.bs_ads_speed, 0, 3)
        bs_inner.addWidget(QLabel("ADS+Fire Speed:"), 1, 2)
        self.bs_ads_fire_speed = LabeledDoubleSlider("Speed", 1.0, 20.0, 12.0, decimals=1)
        self.bs_ads_fire_speed.value_changed.connect(self._on_config_change)
        bs_inner.addWidget(self.bs_ads_fire_speed, 1, 3)
        bs_inner.addWidget(QLabel("Hipfire Speed:"), 2, 2)
        self.bs_hipfire_speed = LabeledDoubleSlider("Speed", 1.0, 20.0, 6.0, decimals=1)
        self.bs_hipfire_speed.value_changed.connect(self._on_config_change)
        bs_inner.addWidget(self.bs_hipfire_speed, 2, 3)
        self.bs_drift_check = QCheckBox("Drift (empurra na direção do input)")
        self.bs_drift_check.setChecked(True)
        self.bs_drift_check.stateChanged.connect(self._on_config_change)
        bs_inner.addWidget(self.bs_drift_check, 3, 0, 1, 2)
        bs_inner.addWidget(QLabel("Drift Strength:"), 3, 2)
        self.bs_drift_strength = LabeledDoubleSlider("Strength", 0.0, 1.0, 0.3, decimals=2)
        self.bs_drift_strength.value_changed.connect(self._on_config_change)
        bs_inner.addWidget(self.bs_drift_strength, 3, 3)
        bs_layout.addLayout(bs_inner)

        bs_desc = QLabel("Diamond pattern de 4 pontos cardeais.\nVelocidade e tamanho mudam por contexto:\nADS=grude, ADS+Fire=mais forte, Hipfire=largo.\nDrift empurra suavemente na direção do input.")
        bs_desc.setStyleSheet("color: #888; font-size: 10px;")
        bs_layout.addWidget(bs_desc)

        bs_group.layout().addLayout(bs_layout)
        self.layout().addWidget(bs_group)

        # ── XANAX AI Adaptativo ──
        xa_group = SectionGroupBox("XANAX AI Adaptativo")
        xa_layout = QVBoxLayout()

        self.xa_enabled_check = QCheckBox("Enable XANAX AI (adapta baseado nos mods ativos)")
        self.xa_enabled_check.setChecked(False)
        self.xa_enabled_check.stateChanged.connect(self._on_config_change)
        xa_layout.addWidget(self.xa_enabled_check)

        xa_inner = QGridLayout()
        xa_inner.addWidget(QLabel("Synergy Boost:"), 0, 0)
        self.xa_synergy_boost = LabeledDoubleSlider("Boost", 1.0, 2.0, 1.15, decimals=2)
        self.xa_synergy_boost.value_changed.connect(self._on_config_change)
        xa_inner.addWidget(self.xa_synergy_boost, 0, 1)
        xa_inner.addWidget(QLabel("Synergy Threshold:"), 1, 0)
        self.xa_synergy_threshold = LabeledSlider("Mods (2-6)", 2, 6, 3)
        self.xa_synergy_threshold.value_changed.connect(self._on_config_change)
        xa_inner.addWidget(self.xa_synergy_threshold, 1, 1)
        xa_inner.addWidget(QLabel("Close Range Boost:"), 2, 0)
        self.xa_close_boost = LabeledDoubleSlider("Boost", 1.0, 2.0, 1.2, decimals=2)
        self.xa_close_boost.value_changed.connect(self._on_config_change)
        xa_inner.addWidget(self.xa_close_boost, 2, 1)
        xa_inner.addWidget(QLabel("Long Range Boost:"), 3, 0)
        self.xa_long_boost = LabeledDoubleSlider("Boost", 0.5, 1.5, 0.85, decimals=2)
        self.xa_long_boost.value_changed.connect(self._on_config_change)
        xa_inner.addWidget(self.xa_long_boost, 3, 1)
        xa_inner.addWidget(QLabel("Humanize Jitter:"), 4, 0)
        self.xa_jitter = LabeledDoubleSlider("Jitter", 0.0, 0.15, 0.05, decimals=2)
        self.xa_jitter.value_changed.connect(self._on_config_change)
        xa_inner.addWidget(self.xa_jitter, 4, 1)
        self.xa_humanize_check = QCheckBox("Humanize (anti-deteção)")
        self.xa_humanize_check.setChecked(True)
        self.xa_humanize_check.stateChanged.connect(self._on_config_change)
        xa_inner.addWidget(self.xa_humanize_check, 5, 0, 1, 2)
        xa_layout.addLayout(xa_inner)

        xa_desc = QLabel("Sistema adaptativo que melhora outros mods.\nSynergy: boost quando 3+ mods ativos.\nRange: ajusta por alcance estimado.\nHumanize: varia parâmetros pra não criar padrão detectável.")
        xa_desc.setStyleSheet("color: #888; font-size: 10px;")
        xa_layout.addWidget(xa_desc)

        xa_group.layout().addLayout(xa_layout)
        self.layout().addWidget(xa_group)

        # ── Warzone Aim Buffers (Modo Puro) ──
        wz_group = SectionGroupBox("Warzone Aim Buffers (Modo Puro)")
        wz_layout = QVBoxLayout()

        # Vibração L3
        wz_vib_check = QCheckBox("Vibração L3 (mantém AA ativo via vibração)")
        wz_vib_check.setChecked(False)
        wz_vib_check.stateChanged.connect(self._on_config_change)
        self.wz_vibration_enabled_check = wz_vib_check
        wz_layout.addWidget(wz_vib_check)

        wz_vib_inner = QGridLayout()
        wz_vib_inner.addWidget(QLabel("Intensity:"), 0, 0)
        self.wz_vib_intensity = LabeledSlider("Intensity (0-100)", 0, 100, 50)
        self.wz_vib_intensity.value_changed.connect(self._on_config_change)
        wz_vib_inner.addWidget(self.wz_vib_intensity, 0, 1)
        wz_vib_inner.addWidget(QLabel("Frequency:"), 1, 0)
        self.wz_vib_freq = LabeledDoubleSlider("Hz", 5.0, 60.0, 30.0, decimals=1)
        self.wz_vib_freq.value_changed.connect(self._on_config_change)
        wz_vib_inner.addWidget(self.wz_vib_freq, 1, 1)
        wz_vib_inner.addWidget(QLabel("Amplitude:"), 2, 0)
        self.wz_vib_amp = LabeledSlider("Stick units", 1, 20, 8)
        self.wz_vib_amp.value_changed.connect(self._on_config_change)
        wz_vib_inner.addWidget(self.wz_vib_amp, 2, 1)
        self.wz_vib_ads_check = QCheckBox("ADS Only")
        self.wz_vib_ads_check.setChecked(False)
        self.wz_vib_ads_check.stateChanged.connect(self._on_config_change)
        wz_vib_inner.addWidget(self.wz_vib_ads_check, 3, 0)
        self.wz_vib_fire_check = QCheckBox("Fire Only")
        self.wz_vib_fire_check.setChecked(False)
        self.wz_vib_fire_check.stateChanged.connect(self._on_config_change)
        wz_vib_inner.addWidget(self.wz_vib_fire_check, 3, 1)
        wz_layout.addLayout(wz_vib_inner)

        # Warzone Aim Buffer
        wz_buf_check = QCheckBox("Warzone Aim Buffer (tracking + sticky + rotation)")
        wz_buf_check.setChecked(False)
        wz_buf_check.stateChanged.connect(self._on_config_change)
        self.wz_buffer_enabled_check = wz_buf_check
        wz_layout.addWidget(wz_buf_check)

        wz_buf_inner = QGridLayout()
        wz_buf_inner.addWidget(QLabel("Tracking Strength:"), 0, 0)
        self.wz_buf_track_str = LabeledDoubleSlider("Strength", 0.5, 4.0, 2.0, decimals=1)
        self.wz_buf_track_str.value_changed.connect(self._on_config_change)
        wz_buf_inner.addWidget(self.wz_buf_track_str, 0, 1)
        wz_buf_inner.addWidget(QLabel("Sticky Strength:"), 1, 0)
        self.wz_buf_sticky_str = LabeledDoubleSlider("Strength", 0.5, 4.0, 1.8, decimals=1)
        self.wz_buf_sticky_str.value_changed.connect(self._on_config_change)
        wz_buf_inner.addWidget(self.wz_buf_sticky_str, 1, 1)
        wz_buf_inner.addWidget(QLabel("Rotation Radius:"), 2, 0)
        self.wz_buf_rot_radius = LabeledSlider("Radius", 3, 30, 12)
        self.wz_buf_rot_radius.value_changed.connect(self._on_config_change)
        wz_buf_inner.addWidget(self.wz_buf_rot_radius, 2, 1)
        wz_buf_inner.addWidget(QLabel("Rotation Speed:"), 3, 0)
        self.wz_buf_rot_speed = LabeledDoubleSlider("Speed", 5.0, 40.0, 15.0, decimals=1)
        self.wz_buf_rot_speed.value_changed.connect(self._on_config_change)
        wz_buf_inner.addWidget(self.wz_buf_rot_speed, 3, 1)
        wz_buf_inner.addWidget(QLabel("Fire Boost:"), 4, 0)
        self.wz_buf_fire_boost = LabeledDoubleSlider("Boost", 1.0, 3.0, 1.4, decimals=1)
        self.wz_buf_fire_boost.value_changed.connect(self._on_config_change)
        wz_buf_inner.addWidget(self.wz_buf_fire_boost, 4, 1)
        wz_layout.addLayout(wz_buf_inner)

        # Rapid Fire Puro
        wz_rf_check = QCheckBox("Rapid Fire Puro (cadência máxima)")
        wz_rf_check.setChecked(False)
        wz_rf_check.stateChanged.connect(self._on_config_change)
        self.wz_rapid_enabled_check = wz_rf_check
        wz_layout.addWidget(wz_rf_check)

        wz_rf_inner = QGridLayout()
        wz_rf_inner.addWidget(QLabel("Speed (Hz):"), 0, 0)
        self.wz_rf_speed = LabeledSlider("Hz", 20, 120, 80)
        self.wz_rf_speed.value_changed.connect(self._on_config_change)
        wz_rf_inner.addWidget(self.wz_rf_speed, 0, 1)
        self.wz_rf_burst_check = QCheckBox("Burst Mode (3 tiros + pausa)")
        self.wz_rf_burst_check.setChecked(False)
        self.wz_rf_burst_check.stateChanged.connect(self._on_config_change)
        wz_rf_inner.addWidget(self.wz_rf_burst_check, 1, 0, 1, 2)
        wz_rf_inner.addWidget(QLabel("Burst Count:"), 2, 0)
        self.wz_rf_burst_count = LabeledSlider("Tiros", 2, 6, 3)
        self.wz_rf_burst_count.value_changed.connect(self._on_config_change)
        wz_rf_inner.addWidget(self.wz_rf_burst_count, 2, 1)
        wz_rf_inner.addWidget(QLabel("Burst Pause:"), 3, 0)
        self.wz_rf_burst_pause = LabeledSlider("ms", 50, 300, 100)
        self.wz_rf_burst_pause.value_changed.connect(self._on_config_change)
        wz_rf_inner.addWidget(self.wz_rf_burst_pause, 3, 1)
        self.wz_rf_ads_check = QCheckBox("ADS Only")
        self.wz_rf_ads_check.setChecked(False)
        self.wz_rf_ads_check.stateChanged.connect(self._on_config_change)
        wz_rf_inner.addWidget(self.wz_rf_ads_check, 4, 0)
        self.wz_rf_ar_check = QCheckBox("Anti-Recoil integrado")
        self.wz_rf_ar_check.setChecked(True)
        self.wz_rf_ar_check.stateChanged.connect(self._on_config_change)
        wz_rf_inner.addWidget(self.wz_rf_ar_check, 4, 1)
        wz_layout.addLayout(wz_rf_inner)

        wz_desc = QLabel("Modo puro Warzone — sem humanização.\nVibração L3: micro-movimento no L3 via vibração = AA sempre ativo.\nAim Buffer: tracking + sticky + rotation agressivos.\nRapid Fire: cadência máxima com anti-recoil integrado.")
        wz_desc.setStyleSheet("color: #888; font-size: 10px;")
        wz_layout.addWidget(wz_desc)

        wz_group.layout().addLayout(wz_layout)
        self.layout().addWidget(wz_group)

        # ── Precision Buffer (DS4 Fluid) ──
        pb_group = SectionGroupBox("Precision Buffer (DS4 Fluid)")
        pb_layout = QVBoxLayout()

        # Tracking smoothing
        pb_track_check = QCheckBox("Tracking Smoothing (suaviza rastreamento)")
        pb_track_check.setChecked(False)
        pb_track_check.stateChanged.connect(self._on_config_change)
        self.pb_tracking_enabled_check = pb_track_check
        pb_layout.addWidget(pb_track_check)

        pb_track_inner = QGridLayout()
        pb_track_inner.addWidget(QLabel("Smooth:"), 0, 0)
        self.pb_tracking_smooth = LabeledDoubleSlider("Smooth", 0.0, 1.0, 0.3, decimals=2)
        self.pb_tracking_smooth.value_changed.connect(self._on_config_change)
        pb_track_inner.addWidget(self.pb_tracking_smooth, 0, 1)
        pb_track_inner.addWidget(QLabel("Strength:"), 1, 0)
        self.pb_tracking_strength = LabeledDoubleSlider("Strength", 0.5, 3.0, 1.2, decimals=1)
        self.pb_tracking_strength.value_changed.connect(self._on_config_change)
        pb_track_inner.addWidget(self.pb_tracking_strength, 1, 1)
        pb_track_inner.addWidget(QLabel("Deadzone:"), 2, 0)
        self.pb_tracking_deadzone = LabeledSlider("Min units", 50, 500, 200)
        self.pb_tracking_deadzone.value_changed.connect(self._on_config_change)
        pb_track_inner.addWidget(self.pb_tracking_deadzone, 2, 1)
        pb_layout.addLayout(pb_track_inner)

        # Anti-jitter
        pb_jitter_check = QCheckBox("Anti-Jitter (remove micro-oscilações)")
        pb_jitter_check.setChecked(False)
        pb_jitter_check.stateChanged.connect(self._on_config_change)
        self.pb_jitter_enabled_check = pb_jitter_check
        pb_layout.addWidget(pb_jitter_check)

        pb_jitter_inner = QGridLayout()
        pb_jitter_inner.addWidget(QLabel("Strength:"), 0, 0)
        self.pb_jitter_strength = LabeledDoubleSlider("Strength", 0.0, 1.0, 0.4, decimals=2)
        self.pb_jitter_strength.value_changed.connect(self._on_config_change)
        pb_jitter_inner.addWidget(self.pb_jitter_strength, 0, 1)
        self.pb_jitter_adaptive_check = QCheckBox("Adaptive (ajusta por velocidade)")
        self.pb_jitter_adaptive_check.setChecked(True)
        self.pb_jitter_adaptive_check.stateChanged.connect(self._on_config_change)
        pb_jitter_inner.addWidget(self.pb_jitter_adaptive_check, 1, 0, 1, 2)
        pb_layout.addLayout(pb_jitter_inner)

        # Stick smoothing
        pb_stick_check = QCheckBox("Stick Smoothing (suaviza input do stick)")
        pb_stick_check.setChecked(False)
        pb_stick_check.stateChanged.connect(self._on_config_change)
        self.pb_stick_smooth_enabled_check = pb_stick_check
        pb_layout.addWidget(pb_stick_check)

        pb_stick_inner = QGridLayout()
        pb_stick_inner.addWidget(QLabel("Factor:"), 0, 0)
        self.pb_stick_factor = LabeledDoubleSlider("Factor", 0.0, 0.5, 0.15, decimals=2)
        self.pb_stick_factor.value_changed.connect(self._on_config_change)
        pb_stick_inner.addWidget(self.pb_stick_factor, 0, 1)
        pb_stick_inner.addWidget(QLabel("Response:"), 1, 0)
        self.pb_stick_response = LabeledDoubleSlider("Response", 0.1, 1.0, 0.8, decimals=2)
        self.pb_stick_response.value_changed.connect(self._on_config_change)
        pb_stick_inner.addWidget(self.pb_stick_response, 1, 1)
        pb_layout.addLayout(pb_stick_inner)

        # Aim smoothing
        pb_aim_check = QCheckBox("Aim Smoothing (suaviza output do aim)")
        pb_aim_check.setChecked(False)
        pb_aim_check.stateChanged.connect(self._on_config_change)
        self.pb_aim_smooth_enabled_check = pb_aim_check
        pb_layout.addWidget(pb_aim_check)

        pb_aim_inner = QGridLayout()
        pb_aim_inner.addWidget(QLabel("Factor:"), 0, 0)
        self.pb_aim_factor = LabeledDoubleSlider("Factor", 0.0, 0.5, 0.2, decimals=2)
        self.pb_aim_factor.value_changed.connect(self._on_config_change)
        pb_aim_inner.addWidget(self.pb_aim_factor, 0, 1)
        pb_aim_inner.addWidget(QLabel("ADS Boost:"), 1, 0)
        self.pb_aim_ads_boost = LabeledDoubleSlider("Boost", 1.0, 2.0, 1.3, decimals=1)
        self.pb_aim_ads_boost.value_changed.connect(self._on_config_change)
        pb_aim_inner.addWidget(self.pb_aim_ads_boost, 1, 1)
        pb_layout.addLayout(pb_aim_inner)

        pb_desc = QLabel("DS4 Fluid: suaviza micro-movimentos sem perder responsividade.\nAnti-jitter remove oscilações, tracking smoothing mantém mira estável.")
        pb_desc.setStyleSheet("color: #888; font-size: 10px;")
        pb_layout.addWidget(pb_desc)

        pb_group.layout().addLayout(pb_layout)
        self.layout().addWidget(pb_group)

        mv_group = SectionGroupBox("Movement (Zen Style)")
        mv_layout = QVBoxLayout()

        self.dodge_shot_check = QCheckBox("Dodge Shot (crouch no tiro)")
        self.dodge_shot_check.setChecked(False)
        self.dodge_shot_check.stateChanged.connect(self._on_config_change)
        mv_layout.addWidget(self.dodge_shot_check)

        self.slide_cancel2_check = QCheckBox("Slide Cancel (momentum tech)")
        self.slide_cancel2_check.setChecked(False)
        self.slide_cancel2_check.stateChanged.connect(self._on_config_change)
        mv_layout.addWidget(self.slide_cancel2_check)

        self.bunny_hop_check = QCheckBox("Bunny Hop (jump spam)")
        self.bunny_hop_check.setChecked(False)
        self.bunny_hop_check.stateChanged.connect(self._on_config_change)
        mv_layout.addWidget(self.bunny_hop_check)

        self.crouch_aim_check = QCheckBox("Crouch Aim (agacha ao mirar ADS)")
        self.crouch_aim_check.setChecked(False)
        self.crouch_aim_check.stateChanged.connect(self._on_config_change)
        mv_layout.addWidget(self.crouch_aim_check)

        mv_desc = QLabel("Dodge Shot: agacha no tiro de perto — inimigo perde AA.\nSlide Cancel: tap crouch 2x + jump ao pular correndo (momentum).\nBunny Hop: re-press de jump enquanto corre.\nCrouch Aim: segura agachar enquanto mira — hitbox menor no ADS.")
        mv_desc.setStyleSheet("color: #6B7C93; font-size: 10px;")
        mv_layout.addWidget(mv_desc)

        mv_group.layout().addLayout(mv_layout)
        self.layout().addWidget(mv_group)

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

        self.output_label = QLabel("Output: 0, 0 | Layer: neutral")
        self.output_label.setStyleSheet("color: #00E5FF; font-weight: 500;")
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
            "enhanced_enabled": self.enhanced_check.isChecked(),
            "micro_adjust_pull": self.micro_adjust_slider.value(),
            "head_assist_enabled": self.head_assist_check.isChecked(),
            "head_assist_strength": self.head_assist_slider.value(),
            "headlock_pulse": self.headlock_pulse_check.isChecked(),
            "headlock_pulse_ms": self.headlock_pulse_slider.value(),
            "headlock_drift_limit": self.headlock_drift_slider.value(),
            "headlock_lock_window": self.headlock_window_slider.value(),
            "fire_boost_mult": self.fire_boost_slider.value() if self.fire_boost_check.isChecked() else 1.0,
            "fire_boost_ms": self.fire_boost_ms_slider.value(),
            "pd_kp": self.pd_kp_slider.value(),
            "pd_kd": self.pd_kd_slider.value(),
            "magnetic_pull": self.magnetic_pull_slider.value(),
            "adaptive_strength": self.adaptive_strength_check.isChecked(),
            "adaptive_strength_min": self.adaptive_min_slider.value(),
            "adaptive_strength_max": self.adaptive_max_slider.value(),
            "anti_shake_blend": self.anti_shake_slider.value() / 100.0,
            "auto_aa_enabled": self.auto_aa_check.isChecked(),
            "auto_rotation_enabled": self.auto_rotation_check.isChecked(),
            "auto_rotation_speed": self.auto_rotation_speed_slider.value(),
            "bullet_drop_enabled": self.bullet_drop_check.isChecked(),
            "bullet_drop_factor": self.bullet_drop_slider.value(),
            "bullet_drop_offset": self.bullet_drop_offset_slider.value(),
            "anti_sway_enabled": self.anti_sway_check.isChecked(),
            "anti_sway_strength": self.anti_sway_slider.value(),
            "long_range_track_boost": self.lr_track_boost_slider.value(),
            "abuse_enabled": self.abuse_check.isChecked(),
            "abuse_mode": self.abuse_pattern_combo.currentText(),
            "abuse_amp": self.abuse_amp_slider.value(),
            "abuse_speed": self.abuse_speed_slider.value(),
            "aim_spam_enabled": self.aim_spam_check.isChecked(),
            "aim_spam_interval_ms": self.aim_spam_interval_slider.value(),
            "aim_spam_hold_ms": self.aim_spam_hold_slider.value(),
            "pulse_level": self.pulse_level_slider.value(),
            "tracking_speed": self.tracking_speed_slider.value(),
            "auto_track_enabled": self.auto_track_check.isChecked(),
            "auto_track_multiplier": self.auto_track_mult_slider.value(),
            "auto_track_persistence_ms": self.auto_track_persist_slider.value(),
            "aimlock_enabled": self.aimlock_enabled_check.isChecked(),
            "aimlock_blend": self.aimlock_blend_slider.value(),
            "aimlock_fov_degrees": self.aimlock_fov_slider.value(),
            "aimlock_pull_max_rate_deg_s": self.aimlock_pull_max_rate_slider.value(),
            "aimlock_pull_ramp_up_ms": self.aimlock_ramp_up_slider.value(),
            "aimlock_initial_downsight_mult": self.aimlock_initial_mult_slider.value(),
            "aimlock_initial_downsight_ms": self.aimlock_initial_ms_slider.value(),
            "aimlock_adhesion_cone_deg": self.aimlock_adhesion_cone_slider.value(),
            "aimlock_slow_strength": self.aimlock_slow_strength_slider.value(),
            "aimlock_max_yaw_correction_deg": self.aimlock_max_yaw_slider.value(),
            "aimlock_max_pitch_correction_deg": self.aimlock_max_pitch_slider.value(),
            "aimlock_center_strength_mult": self.aimlock_center_mult_slider.value(),
            "aimlock_glue_drift_mult": self.aimlock_glue_mult_slider.value(),
            "aimlock_glue_drift_window_deg": self.aimlock_glue_window_slider.value(),
            "aimlock_source": "proxy",
            "oef_enabled": self.oef_check.isChecked(),
            "oef_min_cutoff": self.oef_min_cutoff_slider.value(),
            "oef_beta": self.oef_beta_slider.value(),
            "oef_d_cutoff": self.oef_d_cutoff_slider.value(),
            "predictive_tracker_enabled": self.predictive_check.isChecked(),
            "predictive_vel_alpha": self.predictive_vel_alpha_slider.value(),
            "predictive_accel_alpha": self.predictive_accel_alpha_slider.value(),
            "predictive_lead_horizon_ms": self.predictive_horizon_slider.value(),
            "predictive_min_speed": self.predictive_min_speed_slider.value(),
            "predictive_max_lead": self.predictive_max_lead_slider.value(),
            "predictive_consistency": self.predictive_consistency_slider.value(),
            "predictive_direction_blend": self.predictive_direction_blend_slider.value(),
            "adhesion_buffer_enabled": self.adhesion_check.isChecked(),
            "adhesion_hold_ms": self.adhesion_hold_slider.value(),
            "adhesion_decay": self.adhesion_decay_slider.value(),
            "adhesion_axis_lock": self.adhesion_axis_slider.value(),
            "adhesion_min_mag": self.adhesion_min_mag_slider.value(),
            "follow_assist_enabled": self.follow_assist_check.isChecked(),
            "follow_assist_pull": self.follow_assist_pull_slider.value(),
            "use_optimized_pipeline": self.opt_pipeline_check.isChecked(),
            "optimized_rotational_speed": self.opt_rot_speed_slider.value(),
            "optimized_rotational_radius_mult": self.opt_rot_radius_slider.value(),
            "optimized_predictive_enabled": self.opt_predict_check.isChecked(),
            "optimized_predictive_lead_ms": self.opt_predict_lead_slider.value(),
            "optimized_predictive_kalman_weight": self.opt_predict_kalman_slider.value(),
            "optimized_micro_correction_enabled": self.opt_micro_check.isChecked(),
            "optimized_micro_correction_pull": self.opt_micro_pull_slider.value(),
            "auto_tuning_enabled": self.auto_tuning_check.isChecked(),
            "auto_tuning_min_mult": self.auto_min_mult_slider.value(),
            "auto_tuning_max_mult": self.auto_max_mult_slider.value(),
            "auto_tuning_cooldown": float(self.auto_cooldown_slider.value()),
        }
        # Campos sem widget setados pelo preset (strafe_shot, fn_*)
        if getattr(self, "_preset_extras", None):
            config.update(self._preset_extras)
        return config

    def get_rapid_fire_config(self) -> "RapidFireConfig":
        from nocrosshair.core.config import RapidFireConfig
        mode_map = {
            "Universal (todas as armas)": "universal",
            "Pistola (semi-auto)": "pistol",
            "Shotgun": "shotgun",
            "Custom": "custom",
        }
        return RapidFireConfig(
            enabled=self.rapid_fire_check.isChecked(),
            speed=self.rapid_fire_speed_slider.value(),
            mode=mode_map.get(self.rapid_fire_mode_combo.currentText(), "universal"),
            hold_ratio=self.rapid_fire_ratio_slider.value(),
        )

    def set_rapid_fire_config(self, rf: "RapidFireConfig") -> None:
        if rf is None:
            return
        self.rapid_fire_check.setChecked(rf.enabled)
        self.rapid_fire_speed_slider.setValue(rf.speed)
        mode_map = {
            "universal": "Universal (todas as armas)",
            "pistol": "Pistola (semi-auto)",
            "shotgun": "Shotgun",
            "custom": "Custom",
        }
        self.rapid_fire_mode_combo.setCurrentText(mode_map.get(rf.mode, "Universal (todas as armas)"))
        self.rapid_fire_ratio_slider.setValue(rf.hold_ratio)

    def get_movement_tech_config(self) -> "MovementTechConfig":
        from nocrosshair.core.config import MovementTechConfig
        return MovementTechConfig(
            dodge_shot_enabled=self.dodge_shot_check.isChecked(),
            slide_cancel_enabled=self.slide_cancel2_check.isChecked(),
            bunny_hop_enabled=self.bunny_hop_check.isChecked(),
        )

    def set_movement_tech_config(self, mt: "MovementTechConfig") -> None:
        if mt is None:
            return
        self.dodge_shot_check.setChecked(mt.dodge_shot_enabled)
        self.slide_cancel2_check.setChecked(mt.slide_cancel_enabled)
        self.bunny_hop_check.setChecked(mt.bunny_hop_enabled)

    def get_crouch_aim_config(self) -> "CrouchAimConfig":
        from nocrosshair.core.config import CrouchAimConfig
        return CrouchAimConfig(
            enabled=self.crouch_aim_check.isChecked(),
        )

    def set_crouch_aim_config(self, ca: "CrouchAimConfig") -> None:
        if ca is None:
            return
        self.crouch_aim_check.setChecked(ca.enabled)

    def get_bloom_reducer_config(self) -> "BloomReducerConfig":
        from nocrosshair.core.config import BloomReducerConfig
        return BloomReducerConfig(
            enabled=self.bloom_reducer_check.isChecked(),
            burst_shots=self.br_shots_slider.value(),
            hold_ms=self.br_hold_slider.value(),
            tap_gap_ms=self.br_tap_slider.value(),
            reset_ms=self.br_reset_slider.value(),
        )

    def set_bloom_reducer_config(self, br: "BloomReducerConfig") -> None:
        if br is None:
            return
        self.bloom_reducer_check.setChecked(br.enabled)
        self.br_shots_slider.setValue(br.burst_shots)
        self.br_hold_slider.setValue(br.hold_ms)
        self.br_tap_slider.setValue(br.tap_gap_ms)
        self.br_reset_slider.setValue(br.reset_ms)

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
            auto_track_enabled=config.get("auto_track_enabled", True),
            auto_track_multiplier=float(config.get("auto_track_multiplier", 0.6)),
            auto_track_persistence_ms=float(config.get("auto_track_persistence_ms", 60.0)),
            auto_track_threshold=int(config.get("auto_track_threshold", 20)),
            shape_mode=str(config.get("shape_mode", "Circular")).lower(),
            aim_pattern=str(config.get("aim_pattern", "Standard")).lower().replace(" ", "_"),
            enhanced_enabled=config.get("enhanced_enabled", False),
            micro_adjust_pull=int(config.get("micro_adjust_pull", 500)),
            head_assist_enabled=config.get("head_assist_enabled", False),
            head_assist_strength=float(config.get("head_assist_strength", 0.4)),
            headlock_pulse=config.get("headlock_pulse", False),
            headlock_pulse_ms=int(config.get("headlock_pulse_ms", 60)),
            headlock_drift_limit=int(config.get("headlock_drift_limit", 0)),
            headlock_lock_window=int(config.get("headlock_lock_window", 3000)),
            fire_boost_mult=float(config.get("fire_boost_mult", 1.0)),
            fire_boost_ms=int(config.get("fire_boost_ms", 120)),
            pd_kp=float(config.get("pd_kp", 0.15)),
            pd_kd=float(config.get("pd_kd", 0.08)),
            magnetic_pull=int(config.get("magnetic_pull", 400)),
            anti_shake_blend=float(config.get("anti_shake_blend", 0.30)),
            anti_flinch=config.get("anti_flinch", True),
            anti_flinch_strength=int(config.get("anti_flinch_strength", 3000)),
            zero_delay=config.get("zero_delay", True),
            zero_delay_ms=int(config.get("zero_delay_ms", 40)),
            bloom_compensation=config.get("bloom_compensation", True),
            cjitter_enabled=config.get("cjitter_enabled", False),
            cjitter_left_enabled=config.get("cjitter_left_enabled", False),
            cjitter_left_amp=int(config.get("cjitter_left_amp", 2)),
            aimlock_source=str(config.get("aimlock_source", "proxy")),
            oef_enabled=config.get("oef_enabled", False),
            oef_min_cutoff=float(config.get("oef_min_cutoff", 1.0)),
            oef_beta=float(config.get("oef_beta", 0.05)),
            oef_d_cutoff=float(config.get("oef_d_cutoff", 1.0)),
            predictive_tracker_enabled=config.get("predictive_tracker_enabled", False),
            predictive_vel_alpha=float(config.get("predictive_vel_alpha", 0.15)),
            predictive_accel_alpha=float(config.get("predictive_accel_alpha", 0.05)),
            predictive_lead_horizon_ms=float(config.get("predictive_lead_horizon_ms", 40.0)),
            predictive_min_speed=float(config.get("predictive_min_speed", 200.0)),
            predictive_max_lead=int(config.get("predictive_max_lead", 3000)),
            predictive_consistency=int(config.get("predictive_consistency", 3)),
            predictive_direction_blend=float(config.get("predictive_direction_blend", 0.7)),
            adhesion_buffer_enabled=config.get("adhesion_buffer_enabled", False),
            adhesion_hold_ms=float(config.get("adhesion_hold_ms", 120.0)),
            adhesion_decay=float(config.get("adhesion_decay", 0.35)),
            adhesion_axis_lock=float(config.get("adhesion_axis_lock", 0.18)),
            adhesion_min_mag=float(config.get("adhesion_min_mag", 100.0)),
            follow_assist_enabled=config.get("follow_assist_enabled", False),
            follow_assist_pull=int(config.get("follow_assist_pull", 300)),
            tweak_zone_enabled=config.get("tweak_zone_enabled", True),
            tweak_zone_pct=float(config.get("tweak_zone_pct", 0.6)),
            tweak_zone_offset=float(config.get("tweak_zone_offset", 2.0)),
            rs_smoothing=float(config.get("rs_smoothing", 0.0)),
            rotational_mag_gate=int(config.get("rotational_mag_gate", 200)),
            rotational_radius_mult=float(config.get("rotational_radius_mult", 1.5)),
            silent_aim_enabled=config.get("silent_aim_enabled", False),
            silent_aim_slow_mult=float(config.get("silent_aim_slow_mult", 1.4)),
            silent_aim_pull_mult=float(config.get("silent_aim_pull_mult", 1.6)),
            silent_aim_shake_blend=float(config.get("silent_aim_shake_blend", 0.55)),
            silent_hit_enabled=config.get("silent_hit_enabled", False),
            silent_hit_slow_mult=float(config.get("silent_hit_slow_mult", 1.2)),
            silent_hit_pull_mult=float(config.get("silent_hit_pull_mult", 2.0)),
            silent_hit_shake_blend=float(config.get("silent_hit_shake_blend", 0.50)),
            ls_freq_enabled=config.get("ls_freq_enabled", False),
            ls_freq_amplitude=int(config.get("ls_freq_amplitude", 10)),
            ls_freq_frequency=float(config.get("ls_freq_frequency", 15.0)),
            ls_freq_shape=str(config.get("ls_freq_shape", "Sine")).lower(),
            ls_freq_gate=int(config.get("ls_freq_gate", 500)),
            ls_freq_aggressive=config.get("ls_freq_aggressive", False),
            head_snap_enabled=config.get("head_snap_enabled", False),
            head_snap_strength=int(config.get("head_snap_strength", 40)),
            head_snap_height=int(config.get("head_snap_height", 800)),
            head_snap_duration=int(config.get("head_snap_duration", 150)),
            head_snap_cooldown=int(config.get("head_snap_cooldown", 300)),
            head_snap_smooth=float(config.get("head_snap_smooth", 0.3)),
            head_snap_mode=str(config.get("head_snap_mode", "Auto")).lower(),
            head_snap_ads_only=config.get("head_snap_ads_only", True),
            camera_layer_boost=float(config.get("camera_layer_boost", 1.0)),
            ads_lock_boost=float(config.get("ads_lock_boost", 1.0)),
            # 4ª geração
            multi_polar_enabled=config.get("multi_polar_enabled", False),
            multi_polar_close_radius=int(config.get("multi_polar_close_radius", 3)),
            multi_polar_close_angle=float(config.get("multi_polar_close_angle", 8.0)),
            multi_polar_close_fire_boost=int(config.get("multi_polar_close_fire_boost", 2)),
            multi_polar_medium_radius=int(config.get("multi_polar_medium_radius", 8)),
            multi_polar_medium_angle=float(config.get("multi_polar_medium_angle", 12.0)),
            multi_polar_medium_fire_boost=int(config.get("multi_polar_medium_fire_boost", 3)),
            multi_polar_long_radius=int(config.get("multi_polar_long_radius", 14)),
            multi_polar_long_angle=float(config.get("multi_polar_long_angle", 18.0)),
            multi_polar_long_fire_boost=int(config.get("multi_polar_long_fire_boost", 4)),
            multi_polar_sniper_enabled=config.get("multi_polar_sniper_enabled", True),
            multi_polar_sniper_radius=int(config.get("multi_polar_sniper_radius", 20)),
            multi_polar_sniper_angle=float(config.get("multi_polar_sniper_angle", 22.0)),
            multi_polar_sniper_fire_boost=int(config.get("multi_polar_sniper_fire_boost", 5)),
            multi_polar_sniper_ads_only=config.get("multi_polar_sniper_ads_only", True),
            ghost_tracker_enabled=config.get("ghost_tracker_enabled", False),
            ghost_tracker_bubble_radius=int(config.get("ghost_tracker_bubble_radius", 8000)),
            ghost_tracker_decel_strength=float(config.get("ghost_tracker_decel_strength", 0.3)),
            ghost_tracker_decel_ramp=float(config.get("ghost_tracker_decel_ramp", 0.5)),
            ghost_tracker_stick_threshold=int(config.get("ghost_tracker_stick_threshold", 4000)),
            burst_mode_enabled=config.get("burst_mode_enabled", False),
            burst_mode_count=int(config.get("burst_mode_count", 3)),
            burst_mode_aim_boost=float(config.get("burst_mode_aim_boost", 1.5)),
            burst_mode_recoil_reduction=float(config.get("burst_mode_recoil_reduction", 0.7)),
            burst_mode_cooldown_ms=float(config.get("burst_mode_cooldown_ms", 200.0)),
            batts_sticky_enabled=config.get("batts_sticky_enabled", False),
            batts_sticky_ads_size=int(config.get("batts_sticky_ads_size", 14)),
            batts_sticky_ads_fire_size=int(config.get("batts_sticky_ads_fire_size", 16)),
            batts_sticky_hipfire_size=int(config.get("batts_sticky_hipfire_size", 18)),
            batts_sticky_ads_speed=float(config.get("batts_sticky_ads_speed", 8.0)),
            batts_sticky_ads_fire_speed=float(config.get("batts_sticky_ads_fire_speed", 12.0)),
            batts_sticky_hipfire_speed=float(config.get("batts_sticky_hipfire_speed", 6.0)),
            batts_sticky_drift_enabled=config.get("batts_sticky_drift_enabled", True),
            batts_sticky_drift_strength=float(config.get("batts_sticky_drift_strength", 0.3)),
            xanax_ai_enabled=config.get("xanax_ai_enabled", False),
            xanax_ai_synergy_boost=float(config.get("xanax_ai_synergy_boost", 1.15)),
            xanax_ai_synergy_threshold=int(config.get("xanax_ai_synergy_threshold", 3)),
            xanax_ai_close_range_boost=float(config.get("xanax_ai_close_range_boost", 1.2)),
            xanax_ai_long_range_boost=float(config.get("xanax_ai_long_range_boost", 0.85)),
            xanax_ai_humanize=config.get("xanax_ai_humanize", True),
            xanax_ai_humanize_jitter=float(config.get("xanax_ai_humanize_jitter", 0.05)),
            # Warzone Aim Buffers
            wz_vibration_enabled=config.get("wz_vibration_enabled", False),
            wz_vibration_intensity=int(config.get("wz_vibration_intensity", 50)),
            wz_vibration_frequency=float(config.get("wz_vibration_frequency", 30.0)),
            wz_vibration_amplitude=int(config.get("wz_vibration_amplitude", 8)),
            wz_vibration_ads_only=config.get("wz_vibration_ads_only", False),
            wz_vibration_fire_only=config.get("wz_vibration_fire_only", False),
            wz_buffer_enabled=config.get("wz_buffer_enabled", False),
            wz_buffer_tracking_enabled=config.get("wz_buffer_tracking_enabled", True),
            wz_buffer_tracking_strength=float(config.get("wz_buffer_tracking_strength", 2.0)),
            wz_buffer_tracking_radius=int(config.get("wz_buffer_tracking_radius", 5000)),
            wz_buffer_sticky_enabled=config.get("wz_buffer_sticky_enabled", True),
            wz_buffer_sticky_strength=float(config.get("wz_buffer_sticky_strength", 1.8)),
            wz_buffer_sticky_radius=int(config.get("wz_buffer_sticky_radius", 3000)),
            wz_buffer_rotation_enabled=config.get("wz_buffer_rotation_enabled", True),
            wz_buffer_rotation_radius=int(config.get("wz_buffer_rotation_radius", 12)),
            wz_buffer_rotation_speed=float(config.get("wz_buffer_rotation_speed", 15.0)),
            wz_buffer_fire_boost=float(config.get("wz_buffer_fire_boost", 1.4)),
            wz_buffer_ads_only=config.get("wz_buffer_ads_only", False),
            wz_rapid_enabled=config.get("wz_rapid_enabled", False),
            wz_rapid_speed=int(config.get("wz_rapid_speed", 80)),
            wz_rapid_hold_ms=int(config.get("wz_rapid_hold_ms", 5)),
            wz_rapid_release_ms=int(config.get("wz_rapid_release_ms", 5)),
            wz_rapid_burst_mode=config.get("wz_rapid_burst_mode", False),
            wz_rapid_burst_count=int(config.get("wz_rapid_burst_count", 3)),
            wz_rapid_burst_pause_ms=int(config.get("wz_rapid_burst_pause_ms", 100)),
            wz_rapid_ads_only=config.get("wz_rapid_ads_only", False),
            wz_rapid_anti_recoil=config.get("wz_rapid_anti_recoil", True),
            wz_rapid_anti_recoil_strength=float(config.get("wz_rapid_anti_recoil_strength", 1.2)),
            # Precision Buffer (DS4 Fluid)
            precision_tracking_enabled=config.get("precision_tracking_enabled", False),
            precision_tracking_smooth=float(config.get("precision_tracking_smooth", 0.3)),
            precision_tracking_strength=float(config.get("precision_tracking_strength", 1.2)),
            precision_tracking_deadzone=int(config.get("precision_tracking_deadzone", 200)),
            precision_anti_jitter_enabled=config.get("precision_anti_jitter_enabled", False),
            precision_anti_jitter_strength=float(config.get("precision_anti_jitter_strength", 0.4)),
            precision_anti_jitter_adaptive=config.get("precision_anti_jitter_adaptive", True),
            precision_stick_smooth_enabled=config.get("precision_stick_smooth_enabled", False),
            precision_stick_smooth_factor=float(config.get("precision_stick_smooth_factor", 0.15)),
            precision_stick_smooth_response=float(config.get("precision_stick_smooth_response", 0.8)),
            precision_aim_smooth_enabled=config.get("precision_aim_smooth_enabled", False),
            precision_aim_smooth_factor=float(config.get("precision_aim_smooth_factor", 0.2)),
            precision_aim_smooth_ads_boost=float(config.get("precision_aim_smooth_ads_boost", 1.3)),
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
            ("aa_auto_aa_enabled", "auto_aa_enabled", "auto_aa_check", "check"),
            ("aa_auto_rotation_enabled", "auto_rotation_enabled", "auto_rotation_check", "check"),
            ("aa_auto_rotation_speed", "auto_rotation_speed", "auto_rotation_speed_slider", "int"),
            ("aa_pulse_level", "pulse_level", "pulse_level_slider", "int"),
            ("aa_tracking_speed", "tracking_speed", "tracking_speed_slider", "int"),
            ("aa_auto_track_enabled", "auto_track_enabled", "auto_track_check", "check"),
            ("aa_auto_track_multiplier", "auto_track_multiplier", "auto_track_mult_slider", "float"),
            ("aa_auto_track_persistence_ms", "auto_track_persistence_ms", "auto_track_persist_slider", "int"),
            ("aa_aimlock_enabled", "aimlock_enabled", "aimlock_enabled_check", "check"),
            ("aa_aimlock_blend", "aimlock_blend", "aimlock_blend_slider", "float"),
            ("aa_aimlock_fov_degrees", "aimlock_fov_degrees", "aimlock_fov_slider", "int"),
            ("aa_aimlock_pull_max_rate_deg_s", "aimlock_pull_max_rate_deg_s", "aimlock_pull_max_rate_slider", "int"),
            ("aa_aimlock_pull_ramp_up_ms", "aimlock_pull_ramp_up_ms", "aimlock_ramp_up_slider", "int"),
            ("aa_aimlock_initial_downsight_mult", "aimlock_initial_downsight_mult", "aimlock_initial_mult_slider", "float"),
            ("aa_aimlock_initial_downsight_ms", "aimlock_initial_downsight_ms", "aimlock_initial_ms_slider", "int"),
            ("aa_aimlock_adhesion_cone_deg", "aimlock_adhesion_cone_deg", "aimlock_adhesion_cone_slider", "float"),
            ("aa_aimlock_slow_strength", "aimlock_slow_strength", "aimlock_slow_strength_slider", "float"),
            ("aa_aimlock_max_yaw_correction_deg", "aimlock_max_yaw_correction_deg", "aimlock_max_yaw_slider", "float"),
            ("aa_aimlock_max_pitch_correction_deg", "aimlock_max_pitch_correction_deg", "aimlock_max_pitch_slider", "float"),
            ("aa_aimlock_center_strength_mult", "aimlock_center_strength_mult", "aimlock_center_mult_slider", "float"),
            ("aa_aimlock_glue_drift_mult", "aimlock_glue_drift_mult", "aimlock_glue_mult_slider", "float"),
            ("aa_aimlock_glue_drift_window_deg", "aimlock_glue_drift_window_deg", "aimlock_glue_window_slider", "int"),
            ("aa_bullet_drop_enabled", "bullet_drop_enabled", "bullet_drop_check", "check"),
            ("aa_bullet_drop_factor", "bullet_drop_factor", "bullet_drop_slider", "int"),
            ("aa_bullet_drop_offset", "bullet_drop_offset", "bullet_drop_offset_slider", "int"),
            ("aa_anti_sway_enabled", "anti_sway_enabled", "anti_sway_check", "check"),
            ("aa_anti_sway_strength", "anti_sway_strength", "anti_sway_slider", "int"),
            ("aa_long_range_track_boost", "long_range_track_boost", "lr_track_boost_slider", "int"),
            ("aa_abuse_enabled", "abuse_enabled", "abuse_check", "check"),
            ("aa_abuse_amp", "abuse_amp", "abuse_amp_slider", "int"),
            ("aa_abuse_speed", "abuse_speed", "abuse_speed_slider", "int"),
            ("aa_headlock_pulse", "headlock_pulse", "headlock_pulse_check", "check"),
            ("aa_headlock_pulse_ms", "headlock_pulse_ms", "headlock_pulse_slider", "int"),
            ("aa_headlock_drift_limit", "headlock_drift_limit", "headlock_drift_slider", "int"),
            ("aa_headlock_lock_window", "headlock_lock_window", "headlock_window_slider", "int"),
            ("aa_fire_boost_mult", "fire_boost_mult", "fire_boost_slider", "float"),
            ("aa_fire_boost_ms", "fire_boost_ms", "fire_boost_ms_slider", "int"),
            ("aa_oef_enabled", "oef_enabled", "oef_check", "check"),
            ("aa_oef_min_cutoff", "oef_min_cutoff", "oef_min_cutoff_slider", "float"),
            ("aa_oef_beta", "oef_beta", "oef_beta_slider", "float"),
            ("aa_oef_d_cutoff", "oef_d_cutoff", "oef_d_cutoff_slider", "float"),
            ("aa_predictive_tracker_enabled", "predictive_tracker_enabled", "predictive_check", "check"),
            ("aa_predictive_vel_alpha", "predictive_vel_alpha", "predictive_vel_alpha_slider", "float"),
            ("aa_predictive_accel_alpha", "predictive_accel_alpha", "predictive_accel_alpha_slider", "float"),
            ("aa_predictive_lead_horizon_ms", "predictive_lead_horizon_ms", "predictive_horizon_slider", "float"),
            ("aa_predictive_min_speed", "predictive_min_speed", "predictive_min_speed_slider", "int"),
            ("aa_predictive_max_lead", "predictive_max_lead", "predictive_max_lead_slider", "int"),
            ("aa_predictive_consistency", "predictive_consistency", "predictive_consistency_slider", "int"),
            ("aa_predictive_direction_blend", "predictive_direction_blend", "predictive_direction_blend_slider", "float"),
            ("aa_adhesion_buffer_enabled", "adhesion_buffer_enabled", "adhesion_check", "check"),
            ("aa_adhesion_hold_ms", "adhesion_hold_ms", "adhesion_hold_slider", "int"),
            ("aa_adhesion_decay", "adhesion_decay", "adhesion_decay_slider", "float"),
            ("aa_adhesion_axis_lock", "adhesion_axis_lock", "adhesion_axis_slider", "float"),
            ("aa_adhesion_min_mag", "adhesion_min_mag", "adhesion_min_mag_slider", "int"),
            ("aa_follow_assist_enabled", "follow_assist_enabled", "follow_assist_check", "check"),
            ("aa_follow_assist_pull", "follow_assist_pull", "follow_assist_pull_slider", "int"),
            ("aa_tweak_zone_enabled", "tweak_zone_enabled", "tweak_zone_check", "check"),
            ("aa_tweak_zone_pct", "tweak_zone_pct", "tweak_zone_pct_slider", "float"),
            ("aa_tweak_zone_offset", "tweak_zone_offset", "tweak_zone_offset_slider", "float"),
            ("aa_rs_smoothing", "rs_smoothing", "rs_smoothing_slider", "float"),
            ("aa_rotational_mag_gate", "rotational_mag_gate", "rotational_mag_gate_slider", "int"),
            ("aa_rotational_radius_mult", "rotational_radius_mult", "rotational_radius_mult_slider", "float"),
            ("aa_silent_aim_enabled", "silent_aim_enabled", "silent_aim_check", "check"),
            ("aa_silent_aim_slow_mult", "silent_aim_slow_mult", "silent_aim_slow_slider", "float"),
            ("aa_silent_aim_pull_mult", "silent_aim_pull_mult", "silent_aim_pull_slider", "float"),
            ("aa_silent_aim_shake_blend", "silent_aim_shake_blend", "silent_aim_shake_slider", "float"),
            ("aa_silent_hit_enabled", "silent_hit_enabled", "silent_hit_check", "check"),
            ("aa_silent_hit_slow_mult", "silent_hit_slow_mult", "silent_hit_slow_slider", "float"),
            ("aa_silent_hit_pull_mult", "silent_hit_pull_mult", "silent_hit_pull_slider", "float"),
            ("aa_silent_hit_shake_blend", "silent_hit_shake_blend", "silent_hit_shake_slider", "float"),
            ("aa_ls_freq_enabled", "ls_freq_enabled", "ls_freq_check", "check"),
            ("aa_ls_freq_amplitude", "ls_freq_amplitude", "ls_freq_amplitude_slider", "int"),
            ("aa_ls_freq_frequency", "ls_freq_frequency", "ls_freq_frequency_slider", "float"),
            ("aa_ls_freq_shape", "ls_freq_shape", "ls_freq_shape_selector", "preset"),
            ("aa_ls_freq_gate", "ls_freq_gate", "ls_freq_gate_slider", "int"),
            ("aa_ls_freq_aggressive", "ls_freq_aggressive", "ls_freq_aggressive_check", "check"),
            ("aa_head_snap_enabled", "head_snap_enabled", "hs_enabled_check", "check"),
            ("aa_head_snap_strength", "head_snap_strength", "hs_strength_slider", "int"),
            ("aa_head_snap_height", "head_snap_height", "hs_height_slider", "int"),
            ("aa_head_snap_duration", "head_snap_duration", "hs_duration_slider", "int"),
            ("aa_head_snap_cooldown", "head_snap_cooldown", "hs_cooldown_slider", "int"),
            ("aa_head_snap_smooth", "head_snap_smooth", "hs_smooth_slider", "float"),
            ("aa_head_snap_mode", "head_snap_mode", "hs_mode_selector", "preset"),
            ("aa_head_snap_ads_only", "head_snap_ads_only", "hs_ads_only_check", "check"),
            # 4ª geração
            ("aa_multi_polar_enabled", "multi_polar_enabled", "mp_enabled_check", "check"),
            ("aa_multi_polar_close_radius", "multi_polar_close_radius", "mp_close_radius", "int"),
            ("aa_multi_polar_close_angle", "multi_polar_close_angle", "mp_close_angle", "float"),
            ("aa_multi_polar_medium_radius", "multi_polar_medium_radius", "mp_medium_radius", "int"),
            ("aa_multi_polar_medium_angle", "multi_polar_medium_angle", "mp_medium_angle", "float"),
            ("aa_multi_polar_long_radius", "multi_polar_long_radius", "mp_long_radius", "int"),
            ("aa_multi_polar_long_angle", "multi_polar_long_angle", "mp_long_angle", "float"),
            ("aa_multi_polar_sniper_enabled", "multi_polar_sniper_enabled", "mp_sniper_ads_only", "check"),
            ("aa_multi_polar_sniper_radius", "multi_polar_sniper_radius", "mp_sniper_radius", "int"),
            ("aa_multi_polar_sniper_angle", "multi_polar_sniper_angle", "mp_sniper_angle", "float"),
            ("aa_ghost_tracker_enabled", "ghost_tracker_enabled", "gt_enabled_check", "check"),
            ("aa_ghost_tracker_bubble_radius", "ghost_tracker_bubble_radius", "gt_bubble", "int"),
            ("aa_ghost_tracker_decel_strength", "ghost_tracker_decel_strength", "gt_decel", "float"),
            ("aa_ghost_tracker_decel_ramp", "ghost_tracker_decel_ramp", "gt_ramp", "float"),
            ("aa_ghost_tracker_stick_threshold", "ghost_tracker_stick_threshold", "gt_threshold", "int"),
            ("aa_burst_mode_enabled", "burst_mode_enabled", "bm_enabled_check", "check"),
            ("aa_burst_mode_count", "burst_mode_count", "bm_count", "int"),
            ("aa_burst_mode_aim_boost", "burst_mode_aim_boost", "bm_aim_boost", "float"),
            ("aa_burst_mode_recoil_reduction", "burst_mode_recoil_reduction", "bm_recoil_red", "float"),
            ("aa_burst_mode_cooldown_ms", "burst_mode_cooldown_ms", "bm_cooldown", "int"),
            ("aa_batts_sticky_enabled", "batts_sticky_enabled", "bs_enabled_check", "check"),
            ("aa_batts_sticky_ads_size", "batts_sticky_ads_size", "bs_ads_size", "int"),
            ("aa_batts_sticky_ads_fire_size", "batts_sticky_ads_fire_size", "bs_ads_fire_size", "int"),
            ("aa_batts_sticky_hipfire_size", "batts_sticky_hipfire_size", "bs_hipfire_size", "int"),
            ("aa_batts_sticky_ads_speed", "batts_sticky_ads_speed", "bs_ads_speed", "float"),
            ("aa_batts_sticky_ads_fire_speed", "batts_sticky_ads_fire_speed", "bs_ads_fire_speed", "float"),
            ("aa_batts_sticky_hipfire_speed", "batts_sticky_hipfire_speed", "bs_hipfire_speed", "float"),
            ("aa_batts_sticky_drift_enabled", "batts_sticky_drift_enabled", "bs_drift_check", "check"),
            ("aa_batts_sticky_drift_strength", "batts_sticky_drift_strength", "bs_drift_strength", "float"),
            ("aa_xanax_ai_enabled", "xanax_ai_enabled", "xa_enabled_check", "check"),
            ("aa_xanax_ai_synergy_boost", "xanax_ai_synergy_boost", "xa_synergy_boost", "float"),
            ("aa_xanax_ai_synergy_threshold", "xanax_ai_synergy_threshold", "xa_synergy_threshold", "int"),
            ("aa_xanax_ai_close_range_boost", "xanax_ai_close_range_boost", "xa_close_boost", "float"),
            ("aa_xanax_ai_long_range_boost", "xanax_ai_long_range_boost", "xa_long_boost", "float"),
            ("aa_xanax_ai_humanize", "xanax_ai_humanize", "xa_humanize_check", "check"),
            ("aa_xanax_ai_humanize_jitter", "xanax_ai_humanize_jitter", "xa_jitter", "float"),
            # Warzone Aim Buffers
            ("aa_wz_vibration_enabled", "wz_vibration_enabled", "wz_vibration_enabled_check", "check"),
            ("aa_wz_vibration_intensity", "wz_vibration_intensity", "wz_vib_intensity", "int"),
            ("aa_wz_vibration_frequency", "wz_vibration_frequency", "wz_vib_freq", "float"),
            ("aa_wz_vibration_amplitude", "wz_vibration_amplitude", "wz_vib_amp", "int"),
            ("aa_wz_vibration_ads_only", "wz_vibration_ads_only", "wz_vib_ads_check", "check"),
            ("aa_wz_vibration_fire_only", "wz_vibration_fire_only", "wz_vib_fire_check", "check"),
            ("aa_wz_buffer_enabled", "wz_buffer_enabled", "wz_buffer_enabled_check", "check"),
            ("aa_wz_buffer_tracking_strength", "wz_buffer_tracking_strength", "wz_buf_track_str", "float"),
            ("aa_wz_buffer_sticky_strength", "wz_buffer_sticky_strength", "wz_buf_sticky_str", "float"),
            ("aa_wz_buffer_rotation_radius", "wz_buffer_rotation_radius", "wz_buf_rot_radius", "int"),
            ("aa_wz_buffer_rotation_speed", "wz_buffer_rotation_speed", "wz_buf_rot_speed", "float"),
            ("aa_wz_buffer_fire_boost", "wz_buffer_fire_boost", "wz_buf_fire_boost", "float"),
            ("aa_wz_rapid_enabled", "wz_rapid_enabled", "wz_rapid_enabled_check", "check"),
            ("aa_wz_rapid_speed", "wz_rapid_speed", "wz_rf_speed", "int"),
            ("aa_wz_rapid_burst_mode", "wz_rapid_burst_mode", "wz_rf_burst_check", "check"),
            ("aa_wz_rapid_burst_count", "wz_rapid_burst_count", "wz_rf_burst_count", "int"),
            ("aa_wz_rapid_burst_pause_ms", "wz_rapid_burst_pause_ms", "wz_rf_burst_pause", "int"),
            ("aa_wz_rapid_ads_only", "wz_rapid_ads_only", "wz_rf_ads_check", "check"),
            ("aa_wz_rapid_anti_recoil", "wz_rapid_anti_recoil", "wz_rf_ar_check", "check"),
            # Precision Buffer (DS4 Fluid)
            ("aa_precision_tracking_enabled", "precision_tracking_enabled", "pb_tracking_enabled_check", "check"),
            ("aa_precision_tracking_smooth", "precision_tracking_smooth", "pb_tracking_smooth", "float"),
            ("aa_precision_tracking_strength", "precision_tracking_strength", "pb_tracking_strength", "float"),
            ("aa_precision_tracking_deadzone", "precision_tracking_deadzone", "pb_tracking_deadzone", "int"),
            ("aa_precision_anti_jitter_enabled", "precision_anti_jitter_enabled", "pb_jitter_enabled_check", "check"),
            ("aa_precision_anti_jitter_strength", "precision_anti_jitter_strength", "pb_jitter_strength", "float"),
            ("aa_precision_anti_jitter_adaptive", "precision_anti_jitter_adaptive", "pb_jitter_adaptive_check", "check"),
            ("aa_precision_stick_smooth_enabled", "precision_stick_smooth_enabled", "pb_stick_smooth_enabled_check", "check"),
            ("aa_precision_stick_smooth_factor", "precision_stick_smooth_factor", "pb_stick_factor", "float"),
            ("aa_precision_stick_smooth_response", "precision_stick_smooth_response", "pb_stick_response", "float"),
            ("aa_precision_aim_smooth_enabled", "precision_aim_smooth_enabled", "pb_aim_smooth_enabled_check", "check"),
            ("aa_precision_aim_smooth_factor", "precision_aim_smooth_factor", "pb_aim_factor", "float"),
            ("aa_precision_aim_smooth_ads_boost", "precision_aim_smooth_ads_boost", "pb_aim_ads_boost", "float"),
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
                elif wtype == "text":
                    if hasattr(w, "setText"):
                        w.setText(str(val))
                    elif hasattr(w, "findText"):
                        idx = w.findText(str(val))
                        if idx < 0:
                            idx = w.findText(str(val).title())
                        if idx >= 0:
                            w.setCurrentIndex(idx)
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
        if "fire_boost_mult" in c or "aa_fire_boost_mult" in c:
            mult = float(c.get("fire_boost_mult", c.get("aa_fire_boost_mult", 1.0)))
            self.fire_boost_check.setChecked(mult > 1.0)
        if "aa_abuse_mode" in c:
            idx = self.abuse_pattern_combo.findText(c["aa_abuse_mode"])
            if idx >= 0:
                self.abuse_pattern_combo.setCurrentIndex(idx)
        if "abuse_mode" in c:
            idx = self.abuse_pattern_combo.findText(c["abuse_mode"])
            if idx >= 0:
                self.abuse_pattern_combo.setCurrentIndex(idx)
        if "aim_spam_enabled" in c:
            self.aim_spam_check.setChecked(c["aim_spam_enabled"])
        if "aa_aim_spam_enabled" in c:
            self.aim_spam_check.setChecked(c["aa_aim_spam_enabled"])
        if "aim_spam_interval_ms" in c:
            self.aim_spam_interval_slider.setValue(int(c["aim_spam_interval_ms"]))
        if "aim_spam_hold_ms" in c:
            self.aim_spam_hold_slider.setValue(int(c["aim_spam_hold_ms"]))
        if "aa_enhanced_enabled" in c:
            self.enhanced_check.setChecked(c["aa_enhanced_enabled"])
        if "enhanced_enabled" in c:
            self.enhanced_check.setChecked(c["enhanced_enabled"])
        if "aa_micro_adjust_pull" in c:
            self.micro_adjust_slider.setValue(int(c["aa_micro_adjust_pull"]))
        if "micro_adjust_pull" in c:
            self.micro_adjust_slider.setValue(int(c["micro_adjust_pull"]))
        if "aa_head_assist_enabled" in c:
            self.head_assist_check.setChecked(c["aa_head_assist_enabled"])
        if "head_assist_enabled" in c:
            self.head_assist_check.setChecked(c["head_assist_enabled"])
        if "aa_head_assist_strength" in c:
            self.head_assist_slider.setValue(float(c["aa_head_assist_strength"]))
        if "head_assist_strength" in c:
            self.head_assist_slider.setValue(float(c["head_assist_strength"]))

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
            "FN Aimbot": AimAssistPresets.fortnite_aimbot,
            "FN Luna": AimAssistPresets.luna_style,
        }
        if preset not in preset_map:
            return
        # Guarda campos sem widget (strafe_shot, fn_*, silent_*, tweak_*, ls_freq_*)
        # que o preset seta mas não têm slider na UI — para o get_config
        # devolvê-los.
        self._preset_extras = {
            "strafe_shot_amplitude": preset_map[preset]().strafe_shot_amplitude,
            "strafe_shot_frequency": preset_map[preset]().strafe_shot_frequency,
            "fn_magnet_force": preset_map[preset]().fn_magnet_force,
            "fn_layer_strength": preset_map[preset]().fn_layer_strength,
            "fn_slow_strength": preset_map[preset]().fn_slow_strength,
            "track_ads_pulse_ms": preset_map[preset]().track_ads_pulse_ms,
            "silent_aim_slow_mult": preset_map[preset]().silent_aim_slow_mult,
            "silent_aim_pull_mult": preset_map[preset]().silent_aim_pull_mult,
            "silent_aim_shake_blend": preset_map[preset]().silent_aim_shake_blend,
            "silent_hit_slow_mult": preset_map[preset]().silent_hit_slow_mult,
            "silent_hit_pull_mult": preset_map[preset]().silent_hit_pull_mult,
            "silent_hit_shake_blend": preset_map[preset]().silent_hit_shake_blend,
            "tweak_zone_pct": preset_map[preset]().tweak_zone_pct,
            "tweak_zone_offset": preset_map[preset]().tweak_zone_offset,
            "rs_smoothing": preset_map[preset]().rs_smoothing,
            "rotational_mag_gate": preset_map[preset]().rotational_mag_gate,
            "rotational_radius_mult": preset_map[preset]().rotational_radius_mult,
            "ls_freq_amplitude": preset_map[preset]().ls_freq_amplitude,
            "ls_freq_frequency": preset_map[preset]().ls_freq_frequency,
            "ls_freq_shape": preset_map[preset]().ls_freq_shape,
            "ls_freq_gate": preset_map[preset]().ls_freq_gate,
            "ls_freq_aggressive": preset_map[preset]().ls_freq_aggressive,
            "head_snap_strength": preset_map[preset]().head_snap_strength,
            "head_snap_height": preset_map[preset]().head_snap_height,
            "head_snap_duration": preset_map[preset]().head_snap_duration,
            "head_snap_cooldown": preset_map[preset]().head_snap_cooldown,
            "head_snap_smooth": preset_map[preset]().head_snap_smooth,
            "head_snap_mode": preset_map[preset]().head_snap_mode,
            "camera_layer_boost": preset_map[preset]().camera_layer_boost,
            "ads_lock_boost": preset_map[preset]().ads_lock_boost,
            "aimlock_proxy_input_min": preset_map[preset]().aimlock_proxy_input_min,
            "aimlock_proxy_head_pull_deg": preset_map[preset]().aimlock_proxy_head_pull_deg,
            "aimlock_proxy_yaw_gain_deg": preset_map[preset]().aimlock_proxy_yaw_gain_deg,
            "aimlock_proxy_assumed_dist_cm": preset_map[preset]().aimlock_proxy_assumed_dist_cm,
            "aimlock_proxy_release_ms": preset_map[preset]().aimlock_proxy_release_ms,
            "kernel_aim_beta": preset_map[preset]().kernel_aim_beta,
            "kernel_aim_blend": preset_map[preset]().kernel_aim_blend,
            "kernel_aim_snappiness": preset_map[preset]().kernel_aim_snappiness,
            "kernel_aim_smoothing_rate": preset_map[preset]().kernel_aim_smoothing_rate,
            "kernel_aim_pull_max_rate_deg_s": preset_map[preset]().kernel_aim_pull_max_rate_deg_s,
            "kernel_aim_fov_degrees": preset_map[preset]().kernel_aim_fov_degrees,
            "kernel_aim_head_pull_deg": preset_map[preset]().kernel_aim_head_pull_deg,
            "kernel_aim_min_input": preset_map[preset]().kernel_aim_min_input,
            # 4ª geração
            "multi_polar_close_radius": preset_map[preset]().multi_polar_close_radius,
            "multi_polar_close_angle": preset_map[preset]().multi_polar_close_angle,
            "multi_polar_close_fire_boost": preset_map[preset]().multi_polar_close_fire_boost,
            "multi_polar_medium_radius": preset_map[preset]().multi_polar_medium_radius,
            "multi_polar_medium_angle": preset_map[preset]().multi_polar_medium_angle,
            "multi_polar_medium_fire_boost": preset_map[preset]().multi_polar_medium_fire_boost,
            "multi_polar_long_radius": preset_map[preset]().multi_polar_long_radius,
            "multi_polar_long_angle": preset_map[preset]().multi_polar_long_angle,
            "multi_polar_long_fire_boost": preset_map[preset]().multi_polar_long_fire_boost,
            "multi_polar_sniper_enabled": preset_map[preset]().multi_polar_sniper_enabled,
            "multi_polar_sniper_radius": preset_map[preset]().multi_polar_sniper_radius,
            "multi_polar_sniper_angle": preset_map[preset]().multi_polar_sniper_angle,
            "multi_polar_sniper_fire_boost": preset_map[preset]().multi_polar_sniper_fire_boost,
            "multi_polar_sniper_ads_only": preset_map[preset]().multi_polar_sniper_ads_only,
            "ghost_tracker_bubble_radius": preset_map[preset]().ghost_tracker_bubble_radius,
            "ghost_tracker_decel_strength": preset_map[preset]().ghost_tracker_decel_strength,
            "ghost_tracker_decel_ramp": preset_map[preset]().ghost_tracker_decel_ramp,
            "ghost_tracker_stick_threshold": preset_map[preset]().ghost_tracker_stick_threshold,
            "burst_mode_count": preset_map[preset]().burst_mode_count,
            "burst_mode_aim_boost": preset_map[preset]().burst_mode_aim_boost,
            "burst_mode_recoil_reduction": preset_map[preset]().burst_mode_recoil_reduction,
            "burst_mode_cooldown_ms": preset_map[preset]().burst_mode_cooldown_ms,
            "batts_sticky_ads_size": preset_map[preset]().batts_sticky_ads_size,
            "batts_sticky_ads_fire_size": preset_map[preset]().batts_sticky_ads_fire_size,
            "batts_sticky_hipfire_size": preset_map[preset]().batts_sticky_hipfire_size,
            "batts_sticky_ads_speed": preset_map[preset]().batts_sticky_ads_speed,
            "batts_sticky_ads_fire_speed": preset_map[preset]().batts_sticky_ads_fire_speed,
            "batts_sticky_hipfire_speed": preset_map[preset]().batts_sticky_hipfire_speed,
            "batts_sticky_drift_enabled": preset_map[preset]().batts_sticky_drift_enabled,
            "batts_sticky_drift_strength": preset_map[preset]().batts_sticky_drift_strength,
            "xanax_ai_synergy_boost": preset_map[preset]().xanax_ai_synergy_boost,
            "xanax_ai_synergy_threshold": preset_map[preset]().xanax_ai_synergy_threshold,
            "xanax_ai_close_range_boost": preset_map[preset]().xanax_ai_close_range_boost,
            "xanax_ai_long_range_boost": preset_map[preset]().xanax_ai_long_range_boost,
            "xanax_ai_humanize": preset_map[preset]().xanax_ai_humanize,
            "xanax_ai_humanize_jitter": preset_map[preset]().xanax_ai_humanize_jitter,
        }
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
            "enhanced_enabled": data["enhanced_enabled"],
            "micro_adjust_pull": data["micro_adjust_pull"],
            "head_assist_enabled": data["head_assist_enabled"],
            "head_assist_strength": data["head_assist_strength"],
            "headlock_pulse": data["headlock_pulse"],
            "headlock_pulse_ms": data["headlock_pulse_ms"],
            "headlock_drift_limit": data["headlock_drift_limit"],
            "headlock_lock_window": data["headlock_lock_window"],
            "fire_boost_mult": data["fire_boost_mult"],
            "fire_boost_ms": data["fire_boost_ms"],
            "pd_kp": data["pd_kp"],
            "pd_kd": data["pd_kd"],
            "magnetic_pull": data["magnetic_pull"],
            "adaptive_strength": data["adaptive_strength"],
            "adaptive_strength_min": data["adaptive_strength_min"],
            "adaptive_strength_max": data["adaptive_strength_max"],
            "anti_shake_blend": data["anti_shake_blend"],
            "auto_aa_enabled": data["auto_aa_enabled"],
            "auto_rotation_enabled": data["auto_rotation_enabled"],
            "auto_rotation_speed": data["auto_rotation_speed"],
            "pulse_level": data["pulse_level"],
            "tracking_speed": data["tracking_speed"],
            "auto_track_enabled": data["auto_track_enabled"],
            "auto_track_multiplier": data["auto_track_multiplier"],
            "auto_track_persistence_ms": data["auto_track_persistence_ms"],
            "aimlock_enabled": data["aimlock_enabled"],
            "aimlock_blend": data["aimlock_blend"],
            "aimlock_fov_degrees": data["aimlock_fov_degrees"],
            "aimlock_pull_max_rate_deg_s": data["aimlock_pull_max_rate_deg_s"],
            "aimlock_pull_ramp_up_ms": data["aimlock_pull_ramp_up_ms"],
            "aimlock_initial_downsight_mult": data["aimlock_initial_downsight_mult"],
            "aimlock_initial_downsight_ms": data["aimlock_initial_downsight_ms"],
            "aimlock_adhesion_cone_deg": data["aimlock_adhesion_cone_deg"],
            "aimlock_slow_strength": data["aimlock_slow_strength"],
            "aimlock_max_yaw_correction_deg": data["aimlock_max_yaw_correction_deg"],
            "aimlock_max_pitch_correction_deg": data["aimlock_max_pitch_correction_deg"],
            "aimlock_center_strength_mult": data["aimlock_center_strength_mult"],
            "aimlock_glue_drift_mult": data["aimlock_glue_drift_mult"],
            "aimlock_glue_drift_window_deg": data["aimlock_glue_drift_window_deg"],
            "bullet_drop_enabled": data["bullet_drop_enabled"],
            "bullet_drop_factor": data["bullet_drop_factor"],
            "bullet_drop_offset": data["bullet_drop_offset"],
            "anti_sway_enabled": data["anti_sway_enabled"],
            "anti_sway_strength": data["anti_sway_strength"],
            "long_range_track_boost": data["long_range_track_boost"],
            "oef_enabled": data["oef_enabled"],
            "oef_min_cutoff": data["oef_min_cutoff"],
            "oef_beta": data["oef_beta"],
            "oef_d_cutoff": data["oef_d_cutoff"],
            "predictive_tracker_enabled": data["predictive_tracker_enabled"],
            "predictive_vel_alpha": data["predictive_vel_alpha"],
            "predictive_accel_alpha": data["predictive_accel_alpha"],
            "predictive_lead_horizon_ms": data["predictive_lead_horizon_ms"],
            "predictive_min_speed": data["predictive_min_speed"],
            "predictive_max_lead": data["predictive_max_lead"],
            "predictive_consistency": data["predictive_consistency"],
            "predictive_direction_blend": data["predictive_direction_blend"],
            "adhesion_buffer_enabled": data["adhesion_buffer_enabled"],
            "adhesion_hold_ms": data["adhesion_hold_ms"],
            "adhesion_decay": data["adhesion_decay"],
            "adhesion_axis_lock": data["adhesion_axis_lock"],
            "adhesion_min_mag": data["adhesion_min_mag"],
            "follow_assist_enabled": data["follow_assist_enabled"],
            "follow_assist_pull": data["follow_assist_pull"],
            "tweak_zone_enabled": data["tweak_zone_enabled"],
            "tweak_zone_pct": data["tweak_zone_pct"],
            "tweak_zone_offset": data["tweak_zone_offset"],
            "rs_smoothing": data["rs_smoothing"],
            "rotational_mag_gate": data["rotational_mag_gate"],
            "rotational_radius_mult": data["rotational_radius_mult"],
            "silent_aim_enabled": data["silent_aim_enabled"],
            "silent_aim_slow_mult": data["silent_aim_slow_mult"],
            "silent_aim_pull_mult": data["silent_aim_pull_mult"],
            "silent_aim_shake_blend": data["silent_aim_shake_blend"],
            "silent_hit_enabled": data["silent_hit_enabled"],
            "silent_hit_slow_mult": data["silent_hit_slow_mult"],
            "silent_hit_pull_mult": data["silent_hit_pull_mult"],
            "silent_hit_shake_blend": data["silent_hit_shake_blend"],
            "ls_freq_enabled": data["ls_freq_enabled"],
            "ls_freq_amplitude": data["ls_freq_amplitude"],
            "ls_freq_frequency": data["ls_freq_frequency"],
            "ls_freq_shape": data["ls_freq_shape"],
            "ls_freq_gate": data["ls_freq_gate"],
            "ls_freq_aggressive": data["ls_freq_aggressive"],
            "head_snap_enabled": data["head_snap_enabled"],
            "head_snap_strength": data["head_snap_strength"],
            "head_snap_height": data["head_snap_height"],
            "head_snap_duration": data["head_snap_duration"],
            "head_snap_cooldown": data["head_snap_cooldown"],
            "head_snap_smooth": data["head_snap_smooth"],
            "head_snap_mode": data["head_snap_mode"],
            "head_snap_ads_only": data["head_snap_ads_only"],
            "camera_layer_boost": data["camera_layer_boost"],
            "ads_lock_boost": data["ads_lock_boost"],
            # 4ª geração
            "multi_polar_enabled": data["multi_polar_enabled"],
            "multi_polar_close_radius": data["multi_polar_close_radius"],
            "multi_polar_close_angle": data["multi_polar_close_angle"],
            "multi_polar_close_fire_boost": data["multi_polar_close_fire_boost"],
            "multi_polar_medium_radius": data["multi_polar_medium_radius"],
            "multi_polar_medium_angle": data["multi_polar_medium_angle"],
            "multi_polar_medium_fire_boost": data["multi_polar_medium_fire_boost"],
            "multi_polar_long_radius": data["multi_polar_long_radius"],
            "multi_polar_long_angle": data["multi_polar_long_angle"],
            "multi_polar_long_fire_boost": data["multi_polar_long_fire_boost"],
            "multi_polar_sniper_enabled": data["multi_polar_sniper_enabled"],
            "multi_polar_sniper_radius": data["multi_polar_sniper_radius"],
            "multi_polar_sniper_angle": data["multi_polar_sniper_angle"],
            "multi_polar_sniper_fire_boost": data["multi_polar_sniper_fire_boost"],
            "multi_polar_sniper_ads_only": data["multi_polar_sniper_ads_only"],
            "ghost_tracker_enabled": data["ghost_tracker_enabled"],
            "ghost_tracker_bubble_radius": data["ghost_tracker_bubble_radius"],
            "ghost_tracker_decel_strength": data["ghost_tracker_decel_strength"],
            "ghost_tracker_decel_ramp": data["ghost_tracker_decel_ramp"],
            "ghost_tracker_stick_threshold": data["ghost_tracker_stick_threshold"],
            "burst_mode_enabled": data["burst_mode_enabled"],
            "burst_mode_count": data["burst_mode_count"],
            "burst_mode_aim_boost": data["burst_mode_aim_boost"],
            "burst_mode_recoil_reduction": data["burst_mode_recoil_reduction"],
            "burst_mode_cooldown_ms": data["burst_mode_cooldown_ms"],
            "batts_sticky_enabled": data["batts_sticky_enabled"],
            "batts_sticky_ads_size": data["batts_sticky_ads_size"],
            "batts_sticky_ads_fire_size": data["batts_sticky_ads_fire_size"],
            "batts_sticky_hipfire_size": data["batts_sticky_hipfire_size"],
            "batts_sticky_ads_speed": data["batts_sticky_ads_speed"],
            "batts_sticky_ads_fire_speed": data["batts_sticky_ads_fire_speed"],
            "batts_sticky_hipfire_speed": data["batts_sticky_hipfire_speed"],
            "batts_sticky_drift_enabled": data["batts_sticky_drift_enabled"],
            "batts_sticky_drift_strength": data["batts_sticky_drift_strength"],
            "xanax_ai_enabled": data["xanax_ai_enabled"],
            "xanax_ai_synergy_boost": data["xanax_ai_synergy_boost"],
            "xanax_ai_synergy_threshold": data["xanax_ai_synergy_threshold"],
            "xanax_ai_close_range_boost": data["xanax_ai_close_range_boost"],
            "xanax_ai_long_range_boost": data["xanax_ai_long_range_boost"],
            "xanax_ai_humanize": data["xanax_ai_humanize"],
            "xanax_ai_humanize_jitter": data["xanax_ai_humanize_jitter"],
            # Warzone Aim Buffers
            "wz_vibration_enabled": data["wz_vibration_enabled"],
            "wz_vibration_intensity": data["wz_vibration_intensity"],
            "wz_vibration_frequency": data["wz_vibration_frequency"],
            "wz_vibration_amplitude": data["wz_vibration_amplitude"],
            "wz_vibration_ads_only": data["wz_vibration_ads_only"],
            "wz_vibration_fire_only": data["wz_vibration_fire_only"],
            "wz_buffer_enabled": data["wz_buffer_enabled"],
            "wz_buffer_tracking_enabled": data["wz_buffer_tracking_enabled"],
            "wz_buffer_tracking_strength": data["wz_buffer_tracking_strength"],
            "wz_buffer_tracking_radius": data["wz_buffer_tracking_radius"],
            "wz_buffer_sticky_enabled": data["wz_buffer_sticky_enabled"],
            "wz_buffer_sticky_strength": data["wz_buffer_sticky_strength"],
            "wz_buffer_sticky_radius": data["wz_buffer_sticky_radius"],
            "wz_buffer_rotation_enabled": data["wz_buffer_rotation_enabled"],
            "wz_buffer_rotation_radius": data["wz_buffer_rotation_radius"],
            "wz_buffer_rotation_speed": data["wz_buffer_rotation_speed"],
            "wz_buffer_fire_boost": data["wz_buffer_fire_boost"],
            "wz_buffer_ads_only": data["wz_buffer_ads_only"],
            "wz_rapid_enabled": data["wz_rapid_enabled"],
            "wz_rapid_speed": data["wz_rapid_speed"],
            "wz_rapid_hold_ms": data["wz_rapid_hold_ms"],
            "wz_rapid_release_ms": data["wz_rapid_release_ms"],
            "wz_rapid_burst_mode": data["wz_rapid_burst_mode"],
            "wz_rapid_burst_count": data["wz_rapid_burst_count"],
            "wz_rapid_burst_pause_ms": data["wz_rapid_burst_pause_ms"],
            "wz_rapid_ads_only": data["wz_rapid_ads_only"],
            "wz_rapid_anti_recoil": data["wz_rapid_anti_recoil"],
            "wz_rapid_anti_recoil_strength": data["wz_rapid_anti_recoil_strength"],
            # Precision Buffer (DS4 Fluid)
            "precision_tracking_enabled": data["precision_tracking_enabled"],
            "precision_tracking_smooth": data["precision_tracking_smooth"],
            "precision_tracking_strength": data["precision_tracking_strength"],
            "precision_tracking_deadzone": data["precision_tracking_deadzone"],
            "precision_anti_jitter_enabled": data["precision_anti_jitter_enabled"],
            "precision_anti_jitter_strength": data["precision_anti_jitter_strength"],
            "precision_anti_jitter_adaptive": data["precision_anti_jitter_adaptive"],
            "precision_stick_smooth_enabled": data["precision_stick_smooth_enabled"],
            "precision_stick_smooth_factor": data["precision_stick_smooth_factor"],
            "precision_stick_smooth_response": data["precision_stick_smooth_response"],
            "precision_aim_smooth_enabled": data["precision_aim_smooth_enabled"],
            "precision_aim_smooth_factor": data["precision_aim_smooth_factor"],
            "precision_aim_smooth_ads_boost": data["precision_aim_smooth_ads_boost"],
        })
