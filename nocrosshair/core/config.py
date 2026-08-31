#!/usr/bin/env python3

import os
from enum import Enum
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass

from nocrosshair.features.triggers import TriggerConfig, TriggerModeType
from nocrosshair.features.gyro import GyroConfig, GyroAimMode
from nocrosshair.features.rgb import RGBConfig, RGBEffect

CONFIG_DIR = os.path.expanduser("~/.config")
CONFIG_PATH = os.path.join(CONFIG_DIR, "nocrosshair.nocro")
PROFILES_DIR = os.path.join(CONFIG_DIR, "nocrosshair_profiles")
SLOTS_PATH = os.path.join(CONFIG_DIR, "nocrosshair_slots.json")

class ControllerType(Enum):
    XBOX360 = "xbox360"
    XBOXONE = "xboxone"
    DUALSHOCK3 = "dualshock3"
    DUALSHOCK4 = "dualshock4"
    DUALSENSE = "dualsense"
    DUALSENSE_EDGE = "dualsense_edge"
    SWITCHPRO = "switchpro"

class CrosshairStyle(Enum):
    CRUZ = "cruz"
    PONTO = "ponto"
    CIRCULO = "círculo"
    CRUZ_PONTO = "cruz+ponto"
    CIRCULO_PONTO = "círculo+ponto"
    ESTILO_T = "estilo T"
    MIRA_X = "mira em x"
    LOSANGO = "losango"
    ANGULOS = "ângulos"
    SCOPE = "scope"

class RecoilCurve(Enum):
    LINEAR = "linear"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"

class ShiftModeType(Enum):
    HOLD = "hold"
    TOGGLE = "toggle"

class ActivatorType(Enum):
    SINGLE = "single"
    LONG = "long"
    DOUBLE = "double"
    TRIPLE = "triple"

class DevicePerformance(Enum):
    NORMAL = ("normal", 125)
    ALTA = ("alta", 250)
    ULTRA = ("ultra", 500)

    def __init__(self, key: str, hz: int):
        self.key = key
        self.hz = hz

DEFAULT_CONFIG: Dict[str, Any] = {
    "style": "cruz",
    "color": "#00ff88",
    "size": 20,
    "thick": 2,
    "gap": 4,
    "alpha": 1.0,
    "outline": False,
    "offset_x": 0,
    "offset_y": 0,
    "visible": True,

    "remap_kbd_path": "",
    "remap_mouse_path": "",
    "remap_mouse_sens": 10,
    "remap_active": False,
    "remap_controller": "xbox360",
    "remap_curve": 1.0,
    "remap_profile": "",
    "remap_toggle_key": "KEY_DELETE",

    "remap_aa_enabled": True,
    "remap_aa_strength": 8500,
    "aa_rotational": True,
    "aa_pulse_level": 0,
    "aa_aim_type": "flow",
    "aa_magnetic_snap": True,
    "aa_tracking": True,
    "aa_snap_strength": 0,
    "aa_snap_duration": 80,
    "aa_track_ads_pulse_ms": 240,
    "aa_tracking_strength": 1500,
    "aa_tracking_speed": 0,
    "aa_anti_flinch": True,
    "aa_anti_flinch_strength": 3000,
    "aa_zero_delay": True,
    "aa_zero_delay_ms": 40,
    "aa_bloom_compensation": True,
    "aa_fn_layer_strength": 1.0,
    "aa_auto_track_enabled": True,
    "aa_auto_track_multiplier": 0.15,
    "aa_auto_track_persistence_ms": 30,
    "aa_auto_track_threshold": 200,
    "aa_aim_spam_enabled": False,
    "aa_aim_spam_interval_ms": 180,
    "aa_aim_spam_hold_ms": 40,
    "aa_enhanced_enabled": False,
    "aa_micro_adjust_pull": 500,
    "aa_oef_enabled": False,
    "aa_oef_min_cutoff": 1.0,
    "aa_oef_beta": 0.05,
    "aa_oef_d_cutoff": 1.0,
    "aa_predictive_tracker_enabled": False,
    "aa_predictive_vel_alpha": 0.15,
    "aa_predictive_accel_alpha": 0.05,
    "aa_predictive_lead_horizon_ms": 40.0,
    "aa_predictive_min_speed": 200.0,
    "aa_predictive_max_lead": 3000,
    "aa_predictive_consistency": 3,
    "aa_predictive_direction_blend": 0.7,
    "aa_adhesion_buffer_enabled": False,
    "aa_adhesion_hold_ms": 120.0,
    "aa_adhesion_decay": 0.35,
    "aa_adhesion_axis_lock": 0.18,
    "aa_adhesion_min_mag": 100.0,
    "aa_follow_assist_enabled": False,
    "aa_follow_assist_pull": 300,
    "aa_head_assist_enabled": False,
    "aa_head_assist_strength": 0.4,
    "aa_zone": 5000,

    "remap_rapid_fire": False,
    "remap_rf_speed": 50,
    "remap_crouch_spam": False,
    "remap_cs_speed": 60,

    "recoil_enabled": False,
    "recoil_strength": 35,
    "recoil_speed": 0,
    "recoil_delay": 45,
    "recoil_curve": "ease_out",
    "recoil_y_gate": True,
    "recoil_adapt": 0,
    "recoil_smart_learn": False,
    "sens_y_mult": 0.85,

    "scope_toggle_key": "KEY_SCROLLLOCK",
    "scope_enabled": False,

    "ls_use_same_xy": True,
    "ls_deflection_min": 0.0,
    "ls_deflection_max": 1.0,
    "ls_initial_speed": 0.0,
    "ls_acceleration": 1.0,
    "ls_square_stick": False,
    "ls_squaring_factor": 1.0,
    "ls_deflection_min_x": 0.0,
    "ls_deflection_max_x": 1.0,
    "ls_initial_speed_x": 0.0,
    "ls_acceleration_x": 1.0,
    "ls_deflection_min_y": 0.0,
    "ls_deflection_max_y": 1.0,
    "ls_initial_speed_y": 0.0,
    "ls_acceleration_y": 1.0,

    "rs_use_same_xy": True,
    "rs_deflection_min": 0.0,
    "rs_deflection_max": 1.0,
    "rs_initial_speed": 0.0,
    "rs_acceleration": 1.0,
    "rs_square_stick": False,
    "rs_squaring_factor": 1.0,
    "rs_deflection_min_x": 0.0,
    "rs_deflection_max_x": 1.0,
    "rs_initial_speed_x": 0.0,
    "rs_acceleration_x": 1.0,
    "rs_deflection_min_y": 0.0,
    "rs_deflection_max_y": 1.0,
    "rs_initial_speed_y": 0.0,
    "rs_acceleration_y": 1.0,

    "lt_deadzone": 0.0,
    "lt_sensitivity": 1.0,
    "lt_hair_trigger": True,
    "rt_deadzone": 0.0,
    "rt_sensitivity": 1.0,
    "rt_hair_trigger": True,

    "device_performance": "normal",
    "map_mouse_to_stick": True,
    "mouse_passthrough": False,
    "custom_presets": {},

    "slide_cancel_enabled": False,
    "slide_cancel_jump_arc_ms": 350,
    "slide_cancel_crouch_hold_ms": 30,
    "slide_cancel_jump_hold_ms": 30,
    "slide_cancel_cooldown_ms": 200,
    "slide_cancel_crouch_btn": "0x13E",
    "slide_cancel_jump_btn": "0x130",
    "slide_cancel_toggle_key": "KEY_F11",
    "remap_dodge_shot": False,
    "remap_dodge_hold_ms": 80,
    "remap_dodge_release_ms": 120,
    "remap_slide_cancel": False,
    "remap_slide_tap_ms": 40,
    "remap_slide_gap_ms": 40,
    "remap_bunny_hop": False,
    "remap_bunny_hold_ms": 50,
    "remap_bunny_gap_ms": 120,
    "remap_mv_crouch_btn": "0x13E",
    "remap_mv_jump_btn": "0x130",

    "aa_strafe_shot_enabled": True,
    "aa_strafe_shot_amplitude": 100,
    "aa_strafe_shot_frequency": 8.0,
    "aa_strafe_shot_shape": "sine",

    "aa_cjitter_enabled": False,
    "aa_cjitter_freq": 500.0,
    "aa_cjitter_amp": 2,
    "aa_cjitter_mode": "horizontal",
    "aa_cjitter_left_enabled": False,
    "aa_cjitter_left_amp": 2,
}

CONTROLLER_TYPES = ["xbox360", "xboxone", "dualshock3", "dualshock4", "dualsense", "dualsense_edge", "switchpro"]
CROSSHAIR_STYLES = [
    "cruz", "ponto", "círculo", "cruz+ponto", "círculo+ponto",
    "estilo T", "mira em x", "losango", "ângulos", "scope"
]
RECOIL_CURVES = ["linear", "ease_in", "ease_out"]

WEAPON_CATEGORIES = ["AR", "SMG", "DMR", "Sniper", "Pistol", "Heavy", "Shotgun", "Support", "Melee", "Explosive"]

RECOIL_PRESETS = {
    "FURY AR": {
        "strength": 30,
        "x_strength": 1,
        "ticks": 50,
        "delay_ms": 35,
        "return_speed": 0.78,
        "curve": "linear",
        "color": "#ff9944",
        "category": "AR",
    },
    "SPIRE RIFLE": {
        "strength": 55,
        "x_strength": 3,
        "ticks": 35,
        "delay_ms": 60,
        "return_speed": 0.72,
        "curve": "linear",
        "color": "#ff4444",
        "category": "Heavy",
    },
    "HEAVY AR": {
        "strength": 48,
        "x_strength": -5,
        "ticks": 40,
        "delay_ms": 45,
        "return_speed": 0.75,
        "curve": "linear",
        "color": "#dd4422",
        "category": "AR",
    },
    "VEILED PRECISION SMG": {
        "strength": 20,
        "x_strength": 2,
        "ticks": 70,
        "delay_ms": 12,
        "return_speed": 0.68,
        "curve": "linear",
        "color": "#44aaff",
        "category": "SMG",
    },
    "SURGEFIRE SMG": {
        "strength": 18,
        "x_strength": 2,
        "ticks": 75,
        "delay_ms": 10,
        "return_speed": 0.65,
        "curve": "linear",
        "color": "#3388ee",
        "category": "SMG",
    },
    "SENTINEL PUMP": {
        "strength": 10,
        "x_strength": 1,
        "ticks": 5,
        "delay_ms": 0,
        "return_speed": 0.88,
        "curve": "linear",
        "color": "#cc6600",
        "category": "Shotgun",
    },
    "TWINFIRE AUTO": {
        "strength": 7,
        "x_strength": 1,
        "ticks": 10,
        "delay_ms": 0,
        "return_speed": 0.86,
        "curve": "linear",
        "color": "#ee7700",
        "category": "Shotgun",
    },
    "OUTLAW SHOTGUN": {
        "strength": 12,
        "x_strength": 2,
        "ticks": 4,
        "delay_ms": 0,
        "return_speed": 0.85,
        "curve": "linear",
        "color": "#ff8800",
        "category": "Shotgun",
    },
    "DEADEYE DMR": {
        "strength": 30,
        "x_strength": 1,
        "ticks": 12,
        "delay_ms": 35,
        "return_speed": 0.85,
        "curve": "ease_out",
        "color": "#44dd88",
        "category": "DMR",
    },
    "HYPERBURST PISTOL": {
        "strength": 12,
        "x_strength": 1,
        "ticks": 8,
        "delay_ms": 25,
        "return_speed": 0.88,
        "curve": "linear",
        "color": "#88ccff",
        "category": "Pistol",
    },
    "KILLSWITCH REVOLVERS": {
        "strength": 25,
        "x_strength": 2,
        "ticks": 8,
        "delay_ms": 30,
        "return_speed": 0.82,
        "curve": "linear",
        "color": "#ffaa00",
        "category": "Pistol",
    },
    "HUNTER SNIPER": {
        "strength": 0,
        "x_strength": 0,
        "ticks": 3,
        "delay_ms": 0,
        "return_speed": 0.95,
        "curve": "linear",
        "color": "#cc66ff",
        "category": "Sniper",
    },
    "HEAVY SNIPER": {
        "strength": 0,
        "x_strength": 0,
        "ticks": 3,
        "delay_ms": 0,
        "return_speed": 0.95,
        "curve": "linear",
        "color": "#aa44dd",
        "category": "Sniper",
    },
    "RPG": {
        "strength": 5,
        "x_strength": 0,
        "ticks": 5,
        "delay_ms": 0,
        "return_speed": 0.90,
        "curve": "linear",
        "color": "#ff6600",
        "category": "Heavy",
    },
    "BASS BOOST": {
        "strength": 0,
        "x_strength": 0,
        "ticks": 3,
        "delay_ms": 0,
        "return_speed": 0.95,
        "curve": "linear",
        "color": "#44ff88",
        "category": "Support",
    },
    "MELEE": {
        "strength": 0,
        "x_strength": 0,
        "ticks": 3,
        "delay_ms": 0,
        "return_speed": 0.95,
        "curve": "linear",
        "color": "#ff88ff",
        "category": "Melee",
    },
    "EXPLOSIVE": {
        "strength": 0,
        "x_strength": 0,
        "ticks": 3,
        "delay_ms": 0,
        "return_speed": 0.95,
        "curve": "linear",
        "color": "#ff4444",
        "category": "Explosive",
    },
    "WARFORGED AR": {
        "strength": 46,
        "x_strength": 2,
        "ticks": 35,
        "delay_ms": 35,
        "return_speed": 0.75,
        "curve": "linear",
        "color": "#ff5533",
        "category": "AR",
    },
    "EXTENDING FOCUS SHOTGUN": {
        "strength": 18,
        "x_strength": 1,
        "ticks": 3,
        "delay_ms": 0,
        "return_speed": 0.85,
        "curve": "linear",
        "color": "#ffaa44",
        "category": "Shotgun",
    },
    "AUTO SHOTGUN": {
        "strength": 12,
        "x_strength": 1,
        "ticks": 8,
        "delay_ms": 0,
        "return_speed": 0.85,
        "curve": "linear",
        "color": "#ffbb55",
        "category": "Shotgun",
    },
    "BANK SHOT PISTOL": {
        "strength": 12,
        "x_strength": 1,
        "ticks": 8,
        "delay_ms": 20,
        "return_speed": 0.85,
        "curve": "linear",
        "color": "#99ddff",
        "category": "Pistol",
    },
    "SENTRY PISTOL": {
        "strength": 14,
        "x_strength": 1,
        "ticks": 15,
        "delay_ms": 25,
        "return_speed": 0.85,
        "curve": "linear",
        "color": "#88ccff",
        "category": "Pistol",
    },
    "MAVEN AUTO SHOTGUN": {
        "strength": 14,
        "x_strength": 1,
        "ticks": 6,
        "delay_ms": 0,
        "return_speed": 0.85,
        "curve": "linear",
        "color": "#ffcc66",
        "category": "Shotgun",
    },
    "PINNACLE RIFLE": {
        "strength": 35,
        "x_strength": 2,
        "ticks": 25,
        "delay_ms": 40,
        "return_speed": 0.75,
        "curve": "linear",
        "color": "#ff7755",
        "category": "AR",
    },
    "LANCEHEAD PISTOL": {
        "strength": 18,
        "x_strength": 1,
        "ticks": 21,
        "delay_ms": 20,
        "return_speed": 0.85,
        "curve": "linear",
        "color": "#77ccff",
        "category": "Pistol",
    },
}

WEAPON_ALIASES = {
    "rifle de assalto belicoforjado": "WARFORGED AR",
    "rifle de assalto belicoforjado modular": "WARFORGED AR",
    "warforged assault rifle": "WARFORGED AR",
    "warforged ar": "WARFORGED AR",
    "modular warforged assault rifle": "WARFORGED AR",
    "espingarda de alcance estendido": "EXTENDING FOCUS SHOTGUN",
    "espingarda de foco estendido": "EXTENDING FOCUS SHOTGUN",
    "extending focus shotgun": "EXTENDING FOCUS SHOTGUN",
    "escopeta atacante": "AUTO SHOTGUN",
    "auto shotgun": "AUTO SHOTGUN",
    "pistola tiro certeiro": "BANK SHOT PISTOL",
    "pistola disparo certeiro": "BANK SHOT PISTOL",
    "bank shot pistol": "BANK SHOT PISTOL",
    "pistola sentinela": "SENTRY PISTOL",
    "pistola sentinela modular": "SENTRY PISTOL",
    "sentry pistol": "SENTRY PISTOL",
    "espingarda automatica de perito": "MAVEN AUTO SHOTGUN",
    "maven auto shotgun": "MAVEN AUTO SHOTGUN",
    "rifle pinaculo": "PINNACLE RIFLE",
    "rifle pimaculo": "PINNACLE RIFLE",
    "pinnacle rifle": "PINNACLE RIFLE",
    "pistola lancehead": "LANCEHEAD PISTOL",
    "lancehead pistol": "LANCEHEAD PISTOL",
    "pistola do john wick": "LANCEHEAD PISTOL",
    "9mm baba yaga": "LANCEHEAD PISTOL",
    "john wick pistol": "LANCEHEAD PISTOL",
}

SHIFT_LAYER_COLORS = ["#00ff88", "#ff4444", "#44aaff", "#ffcc00", "#cc33ff"]
SHIFT_LAYER_NAMES = ["Main", "Shift 1", "Shift 2", "Shift 3", "Shift 4"]

CURVE_HIP = [
    (0, 0),
    (5980, 10813),
    (11587, 19200),
    (18564, 27197),
    (25417, 31457),
    (32767, 32767),
]
CURVE_ADS = [
    (0, 0),
    (8192, 8195),
    (18000, 26000),
    (32767, 32767),
]

SENS_MODES = {
    "hip": {"scale_x": 24946, "scale_y": 31917, "curve": CURVE_HIP},
    "ads": {"scale_x": 32767, "scale_y": 27000, "curve": CURVE_ADS},
    "sniper": {"scale_x": 7920, "scale_y": 6740, "curve": CURVE_HIP},
}

ACTIVATOR_DEFAULT_TIMES = {
    "long": 350,
    "double": 280,
    "triple": 300,
}

class ConfigValidator:

    @staticmethod
    def validate_color(value: str) -> bool:
        if not isinstance(value, str):
            return False
        if not value.startswith("#"):
            return False
        h = value.lstrip("#")
        if len(h) != 6:
            return False
        try:
            int(h, 16)
            return True
        except ValueError:
            return False

    @staticmethod
    def validate_range(value: float, min_val: float, max_val: float) -> bool:
        try:
            v = float(value)
            return min_val <= v <= max_val
        except (TypeError, ValueError):
            return False

    @staticmethod
    def validate_controller_type(value: str) -> bool:
        return value in [ct.value for ct in ControllerType]

    @staticmethod
    def validate_crosshair_style(value: str) -> bool:
        return value in [cs.value for cs in CrosshairStyle]

    @staticmethod
    def validate_recoil_curve(value: str) -> bool:
        return value in [rc.value for rc in RecoilCurve]

    @staticmethod
    def validate_string_not_empty(value: str) -> bool:
        return isinstance(value, str) and len(value) > 0

    @staticmethod
    def validate_positive_int(value: int) -> bool:
        try:
            return int(value) > 0
        except (TypeError, ValueError):
            return False

@dataclass
class StickPhysicsConfig:
    use_same_xy: bool = True
    deflection_min: float = 0.0
    deflection_max: float = 1.0
    initial_speed: float = 0.0
    acceleration: float = 1.0
    square_stick: bool = False
    squaring_factor: float = 1.0
    deflection_min_x: float = 0.0
    deflection_max_x: float = 1.0
    initial_speed_x: float = 0.0
    acceleration_x: float = 1.0
    deflection_min_y: float = 0.0
    deflection_max_y: float = 1.0
    initial_speed_y: float = 0.0
    acceleration_y: float = 1.0
    anti_deadzone: int = 0
    raw_mode: bool = False
    response_curve: str = "linear"

    @staticmethod
    def from_dict(d: Dict[str, Any], prefix: str = "") -> "StickPhysicsConfig":
        return StickPhysicsConfig(
            use_same_xy=d.get(f"{prefix}use_same_xy", True),
            deflection_min=float(d.get(f"{prefix}deflection_min", 0.0)),
            deflection_max=float(d.get(f"{prefix}deflection_max", 1.0)),
            initial_speed=float(d.get(f"{prefix}initial_speed", 0.0)),
            acceleration=float(d.get(f"{prefix}acceleration", 1.0)),
            square_stick=d.get(f"{prefix}square_stick", False),
            squaring_factor=float(d.get(f"{prefix}squaring_factor", 1.0)),
            deflection_min_x=float(d.get(f"{prefix}deflection_min_x", 0.0)),
            deflection_max_x=float(d.get(f"{prefix}deflection_max_x", 1.0)),
            initial_speed_x=float(d.get(f"{prefix}initial_speed_x", 0.0)),
            acceleration_x=float(d.get(f"{prefix}acceleration_x", 1.0)),
            deflection_min_y=float(d.get(f"{prefix}deflection_min_y", 0.0)),
            deflection_max_y=float(d.get(f"{prefix}deflection_max_y", 1.0)),
            initial_speed_y=float(d.get(f"{prefix}initial_speed_y", 0.0)),
            acceleration_y=float(d.get(f"{prefix}acceleration_y", 1.0)),
            anti_deadzone=int(d.get(f"{prefix}anti_deadzone", 0)),
            raw_mode=d.get(f"{prefix}raw_mode", False),
            response_curve=str(d.get(f"{prefix}response_curve", "linear")),
        )

@dataclass
class AdvancedStickPhysicsConfig(StickPhysicsConfig):
    advanced_enabled: bool = False
    curve_x: List[Tuple[float, float]] = None
    curve_y: List[Tuple[float, float]] = None
    speed_based_curves: bool = False
    speed_thresholds: Dict[str, float] = None
    per_weapon_enabled: bool = False
    weapon_curves: Dict[str, Dict[str, Any]] = None

    def __post_init__(self):
        if self.curve_x is None:
            self.curve_x = [(0.0, 0.0), (0.25, 0.25), (0.5, 0.5), (0.75, 0.75), (1.0, 1.0)]
        if self.curve_y is None:
            self.curve_y = [(0.0, 0.0), (0.25, 0.25), (0.5, 0.5), (0.75, 0.75), (1.0, 1.0)]
        if self.speed_thresholds is None:
            self.speed_thresholds = {"low": 20.0, "medium": 50.0, "high": 80.0}
        if self.weapon_curves is None:
            self.weapon_curves = {}

    @staticmethod
    def from_dict(d: Dict[str, Any], prefix: str = "") -> "AdvancedStickPhysicsConfig":
        base_config = StickPhysicsConfig.from_dict(d, prefix)

        advanced_data = d.get("advanced", {})
        multi_curve = advanced_data.get("multi_curve", {})
        per_weapon = advanced_data.get("per_weapon", {})

        return AdvancedStickPhysicsConfig(
            use_same_xy=base_config.use_same_xy,
            deflection_min=base_config.deflection_min,
            deflection_max=base_config.deflection_max,
            initial_speed=base_config.initial_speed,
            acceleration=base_config.acceleration,
            square_stick=base_config.square_stick,
            squaring_factor=base_config.squaring_factor,
            deflection_min_x=base_config.deflection_min_x,
            deflection_max_x=base_config.deflection_max_x,
            initial_speed_x=base_config.initial_speed_x,
            acceleration_x=base_config.acceleration_x,
            deflection_min_y=base_config.deflection_min_y,
            deflection_max_y=base_config.deflection_max_y,
            initial_speed_y=base_config.initial_speed_y,
            acceleration_y=base_config.acceleration_y,
            anti_deadzone=base_config.anti_deadzone,
            raw_mode=base_config.raw_mode,
            response_curve=base_config.response_curve,
            advanced_enabled=advanced_data.get("advanced_enabled", False),
            curve_x=multi_curve.get("curve_points", [(0.0, 0.0), (1.0, 1.0)]),
            curve_y=multi_curve.get("curve_points", [(0.0, 0.0), (1.0, 1.0)]),
            speed_based_curves=multi_curve.get("speed_based", False),
            speed_thresholds=multi_curve.get("speed_thresholds", {"low": 20.0, "medium": 50.0, "high": 80.0}),
            per_weapon_enabled=per_weapon.get("enabled", False),
            weapon_curves=per_weapon.get("weapon_curves", {}),
        )

@dataclass
class TriggerPhysicsConfig:
    deadzone: float = 0.0
    sensitivity: float = 1.0
    hair_trigger: bool = True

    @staticmethod
    def from_dict(d: Dict[str, Any], prefix: str = "") -> "TriggerPhysicsConfig":
        return TriggerPhysicsConfig(
            deadzone=float(d.get(f"{prefix}deadzone", 0.0)),
            sensitivity=float(d.get(f"{prefix}sensitivity", 1.0)),
            hair_trigger=d.get(f"{prefix}hair_trigger", True),
        )

@dataclass
class RecoilConfig:
    enabled: bool = False
    strength: int = 35
    x_strength: int = 2
    ticks: int = 60
    delay_ms: int = 45
    return_speed: float = 0.7
    curve: str = "ease_out"
    y_gate: bool = True
    recoil_adapt: int = 0
    smart_learn: bool = False
    simple_mode: bool = False
    simple_rate: int = 4
    # ── Zen/Titan Two upgrades ──
    # Initial Kick: multiplicador separado nos primeiros ticks de spray
    # (muitas armas têm "first shot kick" forte; Titan Two aplica um
    # multiplicador próprio nos primeiros ~350ms de fogo).
    initial_kick_mult: float = 1.0
    initial_kick_ticks: int = 6
    # Headshot Assist: anti-recoil "negativo" no hipfire — em vez de
    # compensar puxando para baixo, puxa levemente para CIMA (micro-adjust
    # pós-tiro que mantém o retículo na altura da cabeça, estilo Zen).
    headshot_assist: bool = False
    headshot_assist_pull: int = 700
    # ── Zen-style toggle + intensity cycling ──
    recoil_toggle_key: str = "KEY_RIGHTCTRL"
    recoil_up_key: str = "KEY_PAGEUP"
    recoil_down_key: str = "KEY_PAGEDOWN"
    recoil_level: int = 3          # 1-10, padrão = 3 (30 GPC)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "RecoilConfig":
        return RecoilConfig(
            enabled=d.get("recoil_enabled", d.get("enabled", False)),
            strength=int(d.get("recoil_strength", 35)),
            x_strength=int(d.get("recoil_x_strength", 2)),
            ticks=int(d.get("recoil_ticks", 60)),
            delay_ms=int(d.get("recoil_delay", 45)),
            return_speed=float(d.get("recoil_return_speed", 0.7)),
            curve=d.get("recoil_curve", "ease_out"),
            y_gate=d.get("recoil_y_gate", True),
            recoil_adapt=int(d.get("recoil_adapt", 0)),
            smart_learn=d.get("recoil_smart_learn", False),
            simple_mode=d.get("recoil_simple_mode", d.get("simple_mode", False)),
            simple_rate=int(d.get("recoil_simple_rate", d.get("simple_rate", 4))),
            initial_kick_mult=float(d.get("recoil_initial_kick_mult", 1.0)),
            initial_kick_ticks=int(d.get("recoil_initial_kick_ticks", 6)),
            headshot_assist=d.get("recoil_headshot_assist", False),
            headshot_assist_pull=int(d.get("recoil_headshot_assist_pull", 700)),
            recoil_level=int(d.get("recoil_level", 3)),
        )

# Perfis de amplitude estilo Zen: GPC lookup table
# Cada nível mapeia para amplitudes crescentes (right stick)
RECOIL_AMPLITUDE_PROFILES = {
    1: 15.0,   # Leve — quase invisível, ativa AA
    2: 22.0,   # Médio-baixo
    3: 30.0,   # Padrão comunidade
    4: 38.0,   # Forte
    5: 45.0,   # Ultra — tremor claro
    6: 55.0,   # God mode
    7: 70.0,   # Insano
    8: 85.0,   # Extremo
    9: 100.0,  # Máximo-1
    10: 120.0, # Máximo absoluto
}

@dataclass
class RecoilRuntimeConfig:
    active_preset: str = "FURY AR"
    sens_y_mult: float = 0.85
    scope_toggle_key: str = "KEY_SCROLLLOCK"
    scope_enabled: bool = False
    is_scoped: bool = False
    burst_mode: bool = False
    burst_count: int = 3
    burst_delay_ms: int = 50
    horizontal_pull: int = 0
    smoothing: int = 0
    loadout_slots: List[str] = None

    DEFAULT_LOADOUT_SLOTS = [
        "Pickaxe",
        "EXTENDING FOCUS SHOTGUN",
        "SENTRY PISTOL",
        "PINNACLE RIFLE",
        "Sniper",
        "LMG",
    ]

    def __post_init__(self):
        if self.loadout_slots is None:
            self.loadout_slots = list(self.DEFAULT_LOADOUT_SLOTS)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "RecoilRuntimeConfig":
        return RecoilRuntimeConfig(
            active_preset=d.get("recoil_active_preset", "FURY AR"),
            sens_y_mult=float(d.get("sens_y_mult", 0.85)),
            scope_toggle_key=d.get("scope_toggle_key", "KEY_SCROLLLOCK"),
            scope_enabled=d.get("scope_enabled", False),
            is_scoped=d.get("recoil_is_scoped", False),
            burst_mode=d.get("recoil_burst_mode", False),
            burst_count=int(d.get("recoil_burst_count", 3)),
            burst_delay_ms=int(d.get("recoil_burst_delay", 50)),
            horizontal_pull=int(d.get("recoil_horizontal_pull", 0)),
            smoothing=int(d.get("recoil_smoothing", 0)),
            loadout_slots=list(d.get("recoil_loadout_slots", RecoilRuntimeConfig.DEFAULT_LOADOUT_SLOTS)),
        )

@dataclass
class AimAssistConfig:
    enabled: bool = True
    base_aa_enabled: bool = True
    strength: int = 8500
    ads_multiplier: float = 1.05
    zone: int = 6000
    rotational: bool = True
    pulse_level: int = 1
    aim_type: str = "flow"
    magnetic_snap: bool = True
    snap_strength: int = 800
    snap_duration: int = 80
    tracking: bool = True
    tracking_strength: int = 3000
    tracking_speed: int = 0
    track_ads_pulse_ms: int = 240
    sticky_enabled: bool = False
    sticky_strength: float = 0.0
    rush_enabled: bool = False
    rush_mult: float = 3.0
    rush_always: bool = True
    rush_pulse_ms: float = 1.5
    rush_cooldown_ms: float = 80.0
    rush_deadzone: float = 0.13
    cjitter_enabled: bool = False
    cjitter_left_enabled: bool = False
    cjitter_left_amp: int = 2
    power_boost: bool = False
    power_mult: float = 1.0
    lock_strength: int = 9000
    lock_fov: int = 4500
    lock_track: int = 950
    lock_sticky: float = 0.55
    lock_smooth: float = 0.3
    lock_enabled: bool = False
    shape_mode: str = "circular"
    use_dz_radius: bool = False
    deadzone_aa_radius: int = 10
    zone_multiplier: int = 3
    aim_pattern: str = "standard"
    auto_aa_enabled: bool = False
    auto_rotation_enabled: bool = False
    auto_rotation_speed: int = 200
    bullet_drop_enabled: bool = False
    bullet_drop_factor: int = 200
    bullet_drop_offset: int = 0
    anti_sway_enabled: bool = False
    anti_sway_strength: int = 0
    pd_kp: float = 0.15
    pd_kd: float = 0.08
    adaptive_strength: bool = False
    adaptive_strength_min: float = 0.3
    adaptive_strength_max: float = 1.5
    anti_shake_blend: float = 0.40
    magnetic_pull: int = 2000
    long_range_track_boost: int = 600
    anti_flinch: bool = True
    anti_flinch_strength: int = 3000
    zero_delay: bool = True
    zero_delay_ms: int = 40
    bloom_compensation: bool = True
    strafe_shot_enabled: bool = True
    strafe_shot_amplitude: int = 100
    strafe_shot_frequency: float = 8.0
    strafe_shot_shape: str = "sine"
    fn_pull_strength: float = 1.0
    fn_slow_strength: float = 0.8
    fn_magnet_force: float = 0.5
    fn_move_pull_boost: float = 1.0
    fn_move_soft_magnet_boost: float = 1.0
    fn_move_adhesion_boost: float = 1.0
    fn_ramp_up_ms: float = 150.0
    fn_camera_threshold: float = 18000.0
    fn_camera_exit: float = 14000.0
    fn_layer_strength: float = 1.0
    fn_strength_slider: int = 100
    fn_zone: int = 6000
    fn_input_gate: int = 800
    fn_ads_multiplier: float = 1.0
    fn_rotation_cap: int = 500
    fn_camera_slow_keep: float = 0.5
    fn_aim_pull_floor: float = 0.35
    fn_camera_pull_floor: float = 0.5
    auto_track_enabled: bool = True
    auto_track_multiplier: float = 0.15
    auto_track_persistence_ms: float = 30.0
    auto_track_threshold: int = 200
    sticky_magnet_enabled: bool = True
    sticky_magnet_strength: float = 0.25
    sticky_magnet_pull: int = 300
    aim_spam_enabled: bool = True     # Ativo por padrão (re-ativa AA)
    aim_spam_interval_ms: int = 100   # 100ms ciclo rápido
    aim_spam_hold_ms: int = 40
    # ── Rotational Boost (left stick micro-oscillation) ──
    rotational_boost_enabled: bool = True
    rotational_boost_amplitude: float = 15.0   # GPC
    rotational_boost_ads_boost: float = 1.3
    # ── Aim Friction (reduz sensibilidade perto do alvo) ──
    friction_enabled: bool = True
    friction_zone: float = 8000.0     # evdev — dentro dessa zona, aplica fricção
    friction_strength: float = 0.6    # 0.6 = 60% da velocidade normal
    # ── Magnetic Pull Directional (pull na direção do movimento) ──
    magnetic_pull_dir_enabled: bool = True
    magnetic_pull_dir_strength: float = 0.15
    magnetic_pull_dir_decay_ms: float = 150.0
    enhanced_enabled: bool = False
    micro_adjust_pull: int = 500
    head_assist_enabled: bool = False
    head_assist_strength: float = 0.4
    # ── Head Lock (estilo Zen "Head Magnet") ──
    # headlock_pulse: micro-ciclo pulsado do pull vertical (sobe/segura)
    # que re-dispara o magnetismo nativo do jogo — o "headlock" de verdade.
    # headlock_drift_limit: se o jogador está puxando o stick para baixo
    # além desse limite, o pull da cabeça é reduzido para não brigar.
    # 0 = sem limite (comportamento original).
    headlock_pulse: bool = False
    headlock_pulse_ms: int = 60
    headlock_drift_limit: int = 0
    headlock_lock_window: int = 3000
    # ── Head Snap Engine (estilo Zen "Headshot Mod") ──
    # Quando o crosshair tá perto do alvo (detectado por padrão de input),
    # aplica um micro-flick vertical pra cima (head level).
    # head_snap_enabled: liga/desliga o engine.
    # head_snap_strength: intensidade do snap (1-100, padrão 40).
    # head_snap_height: altura relativa da cabeça em unidades de stick (100-2000).
    # head_snap_duration: duração do snap em ms (50-500).
    # head_snap_cooldown: tempo mínimo entre snaps em ms (100-1000).
    # head_snap_smooth: suavidade do snap (0.0=rápido, 1.0=muito suave).
    # head_snap_mode: "auto" (detecta engagement), "button" (R3/RS), "both".
    # head_snap_ads_only: só ativa quando em ADS.
    head_snap_enabled: bool = False
    head_snap_strength: int = 40
    head_snap_height: int = 800
    head_snap_duration: int = 150
    head_snap_cooldown: int = 300
    head_snap_smooth: float = 0.3
    head_snap_mode: str = "auto"
    head_snap_ads_only: bool = True
    # ── Camera Layer Boost ──
    # Multiplicador extra na camera layer (stick > threshold).
    # 1.05 = +5% de pull quando o stick tá forte.
    camera_layer_boost: float = 1.0
    # ── ADS Lock Boost ──
    # Multiplicador extra no lock (strength + sticky) quando em ADS.
    # 1.2 = +20% mais grudento ao mirar.
    ads_lock_boost: float = 1.0
    # ── Fire Boost (estilo RocketMod "Boost Strength") ──
    # Multiplicador extra no stick por alguns ms na borda do tiro, para
    # "quebrar" o aim lock do inimigo. 1.0 = desligado.
    fire_boost_mult: float = 1.0
    fire_boost_ms: int = 120
    aimlock_enabled: bool = False
    aimlock_blend: float = 0.7
    aimlock_fov_degrees: float = 30.0
    aimlock_smoothing_rate: float = 10.0
    aimlock_snappiness: float = 0.35
    aimlock_prediction_enabled: bool = True
    aimlock_bullet_speed: float = 30000.0
    aimlock_gravity_scale: float = 0.12
    aimlock_noise_degrees: float = 0.25
    aimlock_degrees_full_stick: float = 30.0
    aimlock_min_delta_ms: float = 8.0
    aimlock_pull_max_rate_deg_s: float = 420.0
    aimlock_pull_ramp_up_ms: float = 80.0
    aimlock_initial_downsight_mult: float = 1.8
    aimlock_initial_downsight_ms: float = 350.0
    aimlock_adhesion_cone_deg: float = 8.0
    aimlock_slow_strength: float = 0.85
    aimlock_max_yaw_correction_deg: float = 40.0
    aimlock_max_pitch_correction_deg: float = 25.0
    aimlock_center_strength_mult: float = 1.8
    aimlock_glue_drift_mult: float = 1.6
    aimlock_glue_drift_window_deg: float = 15.0
    aimlock_lock_timeout_ms: float = 500.0
    aimlock_target_bone: str = "head"
    aimlock_head_height_cm: float = 30.0
    aimlock_max_tracking_distance_cm: float = 50000.0
    aimlock_source: str = "cv"
    aimlock_proxy_input_min: float = 600.0
    aimlock_proxy_head_pull_deg: float = 2.5
    aimlock_proxy_yaw_gain_deg: float = 2.0
    aimlock_proxy_assumed_dist_cm: float = 3000.0
    aimlock_proxy_release_ms: float = 250.0
    aimlock_kalman_smoothing: float = 0.0
    aimlock_velocity_adaptive_boost: float = 0.0
    kbm_mode: bool = True
    kbm_scale: float = 0.50
    fn_humanize: bool = True
    # ── Rotational AA (órbita) — threshold e raio configuráveis ──
    rotational_mag_gate: int = 500
    rotational_radius_mult: float = 1.0
    # ── Tweak Zone (meta Ch7 S4) — micro-movements boosting ──
    tweak_zone_enabled: bool = True
    tweak_zone_pct: float = 0.6
    tweak_zone_offset: float = 2.0
    # ── Right stick smoothing (anti-jitter para micro-movements) ──
    rs_smoothing: float = 0.0
    # ── Silent Aim (ADS-only, zero shake) ──
    silent_aim_enabled: bool = False
    silent_aim_slow_mult: float = 1.4
    silent_aim_pull_mult: float = 1.6
    silent_aim_shake_blend: float = 0.55
    # ── Silent Aim QT (portado do v2): intensidade 0-10 + Quick Tune ──
    silent_aim_qt_enabled: bool = True
    silent_aim_intensity: int = 5
    silent_aim_qt_shake_blend: float = 0.35
    # ── Silent Hit (hip-fire, zero shake) ──
    silent_hit_enabled: bool = False
    silent_hit_slow_mult: float = 1.2
    silent_hit_pull_mult: float = 2.0
    silent_hit_shake_blend: float = 0.50
    # ── Silent Hit QT (portado do v2) ──
    silent_hit_qt_enabled: bool = True
    silent_hit_intensity: int = 8
    silent_hit_qt_shake_blend: float = 0.30
    # ── Left Stick Frequency (micro-oscillation pra AA nativo) ──
    ls_freq_enabled: bool = False
    ls_freq_amplitude: int = 10
    ls_freq_frequency: float = 15.0
    ls_freq_shape: str = "sine"
    ls_freq_gate: int = 500
    ls_freq_aggressive: bool = False

    # ── Advanced Aim (segunda geração) ──
    # One-Euro anti-shake (substitui o blend fixo quando ligado)
    oef_enabled: bool = False
    oef_min_cutoff: float = 1.0
    oef_beta: float = 0.05
    oef_d_cutoff: float = 1.0
    # PredictiveTracker (predição alfa-beta + aceleração)
    predictive_tracker_enabled: bool = False
    predictive_vel_alpha: float = 0.15
    predictive_accel_alpha: float = 0.05
    predictive_lead_horizon_ms: float = 40.0
    predictive_min_speed: float = 200.0
    predictive_max_lead: int = 3000
    predictive_consistency: int = 3
    predictive_direction_blend: float = 0.7
    # AdhesionBuffer (grude: persistência + axis-lock)
    adhesion_buffer_enabled: bool = False
    adhesion_hold_ms: float = 120.0
    adhesion_decay: float = 0.35
    adhesion_axis_lock: float = 0.18
    adhesion_min_mag: float = 100.0
    # Follow Assist (Fase C/D): puxa na direção de acompanhamento (follow_dir)
    # quando LOCKED — o retículo segue o strafe do inimigo sem esforço.
    follow_assist_enabled: bool = False
    follow_assist_pull: int = 300

    # ── Neural Aim (terceira geração) ──
    # Kalman tracker: predição bayesiana de trajetória do alvo
    neural_enabled: bool = False
    neural_kalman_noise: float = 500.0
    neural_kalman_lead_ms: float = 25.0
    neural_kalman_weight: float = 0.6
    # Micro-corrections: sub-pixel multi-frequência (Lissajous)
    neural_micro_enabled: bool = True
    neural_micro_amplitude: float = 180.0
    # Engagement confidence: detecção multi-estágio
    neural_confidence_scale: float = 1.0
    # Harmonizer: suavização cross-layer + prevenção de overcorrection
    neural_harmonizer_enabled: bool = True
    # Error feedback: loop de correção baseado em erro acumulado
    neural_error_feedback_enabled: bool = True

    # ── Pipeline Otimizado (geração 2.0) ──
    # Quando ligado, usa o AimOptimizerPipeline em vez do pipeline antigo.
    # Reduz latência de ~1.5ms para ~0.15ms por frame.
    use_optimized_pipeline: bool = False
    # ── Kernel Aim (BETA) ──
    # Hardlock estilo kernel-mode para CONTROLE, sem leitura de memória:
    # lock com blend alto + snap rápido + head lock no proxy de input.
    # BETA: desligado por padrão.
    kernel_aim_beta: bool = False
    kernel_aim_blend: float = 0.92
    kernel_aim_snappiness: float = 0.55
    kernel_aim_smoothing_rate: float = 12.0
    kernel_aim_pull_max_rate_deg_s: float = 650.0
    kernel_aim_fov_degrees: float = 26.0
    kernel_aim_head_pull_deg: float = 3.0
    kernel_aim_min_input: float = 300.0
    kernel_aim_confidence_enabled: bool = True
    kernel_aim_confidence_rise_rate: float = 0.15
    kernel_aim_confidence_fall_rate: float = 0.40
    kernel_aim_confidence_blend_min: float = 0.50
    kernel_aim_confidence_blend_max: float = 0.98
    kernel_aim_kalman_process_noise: float = 500.0
    kernel_aim_kalman_measure_noise: float = 2000.0
    # RotationalAA adaptativo
    optimized_rotational_speed: float = 0.3
    optimized_rotational_radius_mult: float = 1.0
    # PredictEngine
    optimized_predictive_enabled: bool = True
    optimized_predictive_vel_alpha: float = 0.15
    optimized_predictive_accel_alpha: float = 0.06
    optimized_predictive_lead_ms: float = 40.0
    optimized_predictive_min_speed: float = 200.0
    optimized_predictive_max_lead: float = 3000.0
    optimized_predictive_consistency: int = 3
    optimized_predictive_kalman_weight: float = 0.3
    # MicroCorrectionEngine
    optimized_micro_correction_enabled: bool = True
    optimized_micro_correction_pull: float = 0.3
    # AdaptiveStrengthEngine
    optimized_adaptive_strength_enabled: bool = False
    # Auto-Tuning
    auto_tuning_enabled: bool = False
    auto_tuning_min_mult: float = 0.7
    auto_tuning_max_mult: float = 1.3
    auto_tuning_cooldown: float = 30.0

    # ── Sistemas Avançados (3ª geração) ──
    # Anti-Recoil ML: aprende padrão de recoil por arma
    anti_recoil_ml_enabled: bool = False
    anti_recoil_ml_strength: float = 1.0
    anti_recoil_ml_learning_rate: float = 0.01
    # Ballistic Predictor: predição com velocidade de bala + gravidade
    ballistic_predictor_enabled: bool = False
    ballistic_predictor_strength: float = 1.0
    ballistic_predictor_gravity: float = 980.0
    # Smart Headshot: detecta cabeça + puxão automático
    smart_headshot_enabled: bool = False
    smart_headshot_strength: float = 1.0
    smart_headshot_max_pull: float = 500.0

    # ── Sistemas Avançados 2 (4ª geração) ──
    # Multi-Engine Polar: 4 motores de órbita simultâneos
    multi_polar_enabled: bool = False
    multi_polar_close_enabled: bool = True
    multi_polar_close_radius: int = 3
    multi_polar_close_angle: float = 8.0
    multi_polar_close_shape: str = "circle"
    multi_polar_close_fire_boost: int = 2
    multi_polar_medium_enabled: bool = True
    multi_polar_medium_radius: int = 8
    multi_polar_medium_angle: float = 12.0
    multi_polar_medium_shape: str = "oval_tall"
    multi_polar_medium_fire_boost: int = 3
    multi_polar_long_enabled: bool = True
    multi_polar_long_radius: int = 14
    multi_polar_long_angle: float = 18.0
    multi_polar_long_shape: str = "oval_wide"
    multi_polar_long_fire_boost: int = 4
    multi_polar_sniper_enabled: bool = True
    multi_polar_sniper_radius: int = 20
    multi_polar_sniper_angle: float = 22.0
    multi_polar_sniper_shape: str = "spiral"
    multi_polar_sniper_fire_boost: int = 5
    multi_polar_sniper_ads_only: bool = True
    # Ghost Tracker: desaceleração no aim bubble
    ghost_tracker_enabled: bool = False
    ghost_tracker_bubble_radius: int = 8000
    ghost_tracker_decel_strength: float = 0.3
    ghost_tracker_decel_ramp: float = 0.5
    ghost_tracker_stick_threshold: int = 4000
    # Burst Mode: boost nos primeiros tiros de rajada
    burst_mode_enabled: bool = False
    burst_mode_count: int = 3
    burst_mode_aim_boost: float = 1.5
    burst_mode_recoil_reduction: float = 0.7
    burst_mode_cooldown_ms: float = 200.0
    # Batts Sticky: diamond pattern ADS/Hipfire
    batts_sticky_enabled: bool = False
    batts_sticky_ads_size: int = 14
    batts_sticky_ads_fire_size: int = 16
    batts_sticky_hipfire_size: int = 18
    batts_sticky_ads_speed: float = 8.0
    batts_sticky_ads_fire_speed: float = 12.0
    batts_sticky_hipfire_speed: float = 6.0
    batts_sticky_drift_enabled: bool = True
    batts_sticky_drift_strength: float = 0.3
    # XANAX AI Adaptativo
    xanax_ai_enabled: bool = False
    xanax_ai_synergy_boost: float = 1.15
    xanax_ai_synergy_threshold: int = 3
    xanax_ai_close_range_boost: float = 1.2
    xanax_ai_long_range_boost: float = 0.85
    xanax_ai_close_range_threshold: int = 5000
    xanax_ai_long_range_threshold: int = 20000
    xanax_ai_humanize: bool = True
    xanax_ai_humanize_jitter: float = 0.05
    xanax_ai_adapt_rate: float = 0.02

    # ── Warzone Aim Buffers (Modo Puro) ──
    # Vibração L3: mantém aim assist ativo via vibração
    wz_vibration_enabled: bool = False
    wz_vibration_intensity: int = 50
    wz_vibration_frequency: float = 30.0
    wz_vibration_amplitude: int = 8
    wz_vibration_ads_only: bool = False
    wz_vibration_fire_only: bool = False
    # Warzone Aim Buffer: tracking + sticky + rotation agressivos
    wz_buffer_enabled: bool = False
    wz_buffer_tracking_enabled: bool = True
    wz_buffer_tracking_strength: float = 2.0
    wz_buffer_tracking_radius: int = 5000
    wz_buffer_sticky_enabled: bool = True
    wz_buffer_sticky_strength: float = 1.8
    wz_buffer_sticky_radius: int = 3000
    wz_buffer_rotation_enabled: bool = True
    wz_buffer_rotation_radius: int = 12
    wz_buffer_rotation_speed: float = 15.0
    wz_buffer_fire_boost: float = 1.4
    wz_buffer_ads_only: bool = False
    # Rapid Fire Puro
    wz_rapid_enabled: bool = False
    wz_rapid_speed: int = 80
    wz_rapid_hold_ms: int = 5
    wz_rapid_release_ms: int = 5
    wz_rapid_burst_mode: bool = False
    wz_rapid_burst_count: int = 3
    wz_rapid_burst_pause_ms: int = 100
    wz_rapid_ads_only: bool = False
    wz_rapid_anti_recoil: bool = True
    wz_rapid_anti_recoil_strength: float = 1.2

    # ── Precision Buffer (DS4 Fluid) ──
    # Tracking de precisão: suaviza micro-movimentos e mantém mira estável
    precision_tracking_enabled: bool = False
    precision_tracking_smooth: float = 0.3    # suavidade do tracking (0.0=rápido, 1.0=lento)
    precision_tracking_strength: float = 1.2   # multiplicador de tracking
    precision_tracking_deadzone: int = 200     # deadzone mínima pra ativar
    # Anti-jitter: remove jitter do stick sem perder responsividade
    precision_anti_jitter_enabled: bool = False
    precision_anti_jitter_strength: float = 0.4  # força do anti-jitter (0.0=nenhum, 1.0=máximo)
    precision_anti_jitter_adaptive: bool = True   # adapta baseado na velocidade do stick
    # Stick smoothing: suaviza transições do stick
    precision_stick_smooth_enabled: bool = False
    precision_stick_smooth_factor: float = 0.15   # fator de suavização (0.0=nenhum, 0.5=muito suave)
    precision_stick_smooth_response: float = 0.8  # velocidade de resposta (0.0=lento, 1.0=instantâneo)
    # Aim smoothing: suaviza o output do aim assist
    precision_aim_smooth_enabled: bool = False
    precision_aim_smooth_factor: float = 0.2      # fator de suavização do aim
    precision_aim_smooth_ads_boost: float = 1.3   # boost em ADS
    build_mode_enabled: bool = True      # desativa aim enquanto constrói
    build_disable_ads_only: bool = True  # só desativa em ADS

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "AimAssistConfig":
        return AimAssistConfig(
            enabled=d.get("remap_aa_enabled", False),
            base_aa_enabled=d.get("aa_base_aa_enabled", True),
            strength=int(d.get("remap_aa_strength", 8500)),
            ads_multiplier=float(d.get("aa_ads_multiplier", 1.05)),
            zone=int(d.get("aa_zone", 6000)),
            rotational=d.get("aa_rotational", True),
            pulse_level=int(d.get("aa_pulse_level", 1)),
            aim_type=d.get("aa_aim_type", "flow"),
            magnetic_snap=d.get("aa_magnetic_snap", True),
            snap_strength=int(d.get("aa_snap_strength", 800)),
            snap_duration=int(d.get("aa_snap_duration", 80)),
            tracking=d.get("aa_tracking", True),
            tracking_strength=int(d.get("aa_tracking_strength", 3000)),
            tracking_speed=int(d.get("aa_tracking_speed", 0)),
            track_ads_pulse_ms=int(d.get("aa_track_ads_pulse_ms", 240)),
            sticky_enabled=d.get("aa_sticky_enabled", False),
            sticky_strength=float(d.get("aa_sticky_strength", 0.0)),
            rush_enabled=d.get("aa_rush_enabled", False),
            rush_mult=float(d.get("aa_rush_mult", 3.0)),
            rush_always=d.get("aa_rush_always", True),
            rush_pulse_ms=float(d.get("aa_rush_pulse_ms", 1.5)),
            rush_cooldown_ms=float(d.get("aa_rush_cooldown_ms", 80.0)),
            rush_deadzone=float(d.get("aa_rush_deadzone", 0.13)),
            cjitter_enabled=d.get("aa_cjitter_enabled", False),
            cjitter_left_enabled=d.get("aa_cjitter_left_enabled", False),
            cjitter_left_amp=int(d.get("aa_cjitter_left_amp", 2)),
            power_boost=d.get("aa_power_boost", False),
            power_mult=float(d.get("aa_power_mult", 1.0)),
            lock_strength=int(d.get("aa_lock_strength", 9000)),
            lock_fov=int(d.get("aa_lock_fov", 4500)),
            lock_track=int(d.get("aa_lock_track", 950)),
            lock_sticky=float(d.get("aa_lock_sticky", 0.55)),
            lock_smooth=float(d.get("aa_lock_smooth", 0.3)),
            lock_enabled=d.get("aa_lock_enabled", False),
            shape_mode=d.get("aa_shape_mode", "circular"),
            use_dz_radius=d.get("aa_use_dz_radius", False),
            deadzone_aa_radius=int(d.get("aa_deadzone_radius", 10)),
            zone_multiplier=int(d.get("aa_zone_multiplier", 3)),
            aim_pattern=d.get("aa_aim_pattern", "standard"),
            auto_aa_enabled=d.get("aa_auto_aa_enabled", False),
            auto_rotation_enabled=d.get("aa_auto_rotation_enabled", False),
            auto_rotation_speed=int(d.get("aa_auto_rotation_speed", 200)),
            bullet_drop_enabled=d.get("aa_bullet_drop_enabled", False),
            bullet_drop_factor=int(d.get("aa_bullet_drop_factor", 200)),
            bullet_drop_offset=int(d.get("aa_bullet_drop_offset", 0)),
            anti_sway_enabled=d.get("aa_anti_sway_enabled", False),
            anti_sway_strength=int(d.get("aa_anti_sway_strength", 0)),
            pd_kp=float(d.get("aa_pd_kp", 0.15)),
            pd_kd=float(d.get("aa_pd_kd", 0.08)),
            adaptive_strength=d.get("aa_adaptive_strength", False),
            adaptive_strength_min=float(d.get("aa_adaptive_strength_min", 0.3)),
            adaptive_strength_max=float(d.get("aa_adaptive_strength_max", 1.5)),
            anti_shake_blend=float(d.get("aa_anti_shake_blend", 0.40)),
            magnetic_pull=int(d.get("aa_magnetic_pull", 2000)),
            long_range_track_boost=int(d.get("aa_long_range_track_boost", 600)),
            anti_flinch=d.get("aa_anti_flinch", True),
            anti_flinch_strength=int(d.get("aa_anti_flinch_strength", 3000)),
            zero_delay=d.get("aa_zero_delay", True),
            zero_delay_ms=int(d.get("aa_zero_delay_ms", 40)),
            bloom_compensation=d.get("aa_bloom_compensation", True),
            strafe_shot_enabled=d.get("aa_strafe_shot_enabled", True),
            strafe_shot_amplitude=int(d.get("aa_strafe_shot_amplitude", 100)),
            strafe_shot_frequency=float(d.get("aa_strafe_shot_frequency", 8.0)),
            strafe_shot_shape=d.get("aa_strafe_shot_shape", "sine"),
            fn_pull_strength=float(d.get("aa_fn_pull_strength", 1.0)),
            fn_slow_strength=float(d.get("aa_fn_slow_strength", 0.8)),
            fn_magnet_force=float(d.get("aa_fn_magnet_force", 0.5)),
            fn_move_pull_boost=float(d.get("aa_fn_move_pull_boost", 1.0)),
            fn_move_soft_magnet_boost=float(d.get("aa_fn_move_soft_magnet_boost", 1.0)),
            fn_move_adhesion_boost=float(d.get("aa_fn_move_adhesion_boost", 1.0)),
            fn_ramp_up_ms=float(d.get("aa_fn_ramp_up_ms", 150.0)),
            fn_camera_threshold=float(d.get("aa_fn_camera_threshold", 18000.0)),
            fn_camera_exit=float(d.get("aa_fn_camera_exit", 14000.0)),
            fn_layer_strength=float(d.get("aa_fn_layer_strength", 1.0)),
            fn_strength_slider=int(d.get("aa_fn_strength_slider", 100)),
            fn_zone=int(d.get("aa_fn_zone", 6000)),
            fn_input_gate=int(d.get("aa_fn_input_gate", 800)),
            fn_ads_multiplier=float(d.get("aa_fn_ads_multiplier", 1.0)),
            fn_rotation_cap=int(d.get("aa_fn_rotation_cap", 500)),
            fn_camera_slow_keep=float(d.get("aa_fn_camera_slow_keep", 0.5)),
            fn_aim_pull_floor=float(d.get("aa_fn_aim_pull_floor", 0.35)),
            fn_camera_pull_floor=float(d.get("aa_fn_camera_pull_floor", 0.5)),
            auto_track_enabled=d.get("aa_auto_track_enabled", True),
            auto_track_multiplier=float(d.get("aa_auto_track_multiplier", 0.15)),
            auto_track_persistence_ms=float(d.get("aa_auto_track_persistence_ms", 30.0)),
            auto_track_threshold=int(d.get("aa_auto_track_threshold", 200)),
            aim_spam_enabled=d.get("aa_aim_spam_enabled", False),
            aim_spam_interval_ms=int(d.get("aa_aim_spam_interval_ms", 180)),
            aim_spam_hold_ms=int(d.get("aa_aim_spam_hold_ms", 40)),
            enhanced_enabled=d.get("aa_enhanced_enabled", False),
            micro_adjust_pull=int(d.get("aa_micro_adjust_pull", 500)),
            head_assist_enabled=d.get("aa_head_assist_enabled", False),
            head_assist_strength=float(d.get("aa_head_assist_strength", 0.4)),
            headlock_pulse=d.get("aa_headlock_pulse", False),
            headlock_pulse_ms=int(d.get("aa_headlock_pulse_ms", 60)),
            headlock_drift_limit=int(d.get("aa_headlock_drift_limit", 0)),
            headlock_lock_window=int(d.get("aa_headlock_lock_window", 3000)),
            head_snap_enabled=d.get("aa_head_snap_enabled", False),
            head_snap_strength=int(d.get("aa_head_snap_strength", 40)),
            head_snap_height=int(d.get("aa_head_snap_height", 800)),
            head_snap_duration=int(d.get("aa_head_snap_duration", 150)),
            head_snap_cooldown=int(d.get("aa_head_snap_cooldown", 300)),
            head_snap_smooth=float(d.get("aa_head_snap_smooth", 0.3)),
            head_snap_mode=d.get("aa_head_snap_mode", "auto"),
            head_snap_ads_only=d.get("aa_head_snap_ads_only", True),
            camera_layer_boost=float(d.get("aa_camera_layer_boost", 1.0)),
            ads_lock_boost=float(d.get("aa_ads_lock_boost", 1.0)),
            fire_boost_mult=float(d.get("aa_fire_boost_mult", 1.0)),
            fire_boost_ms=int(d.get("aa_fire_boost_ms", 120)),
            aimlock_enabled=d.get("aa_aimlock_enabled", False),
            aimlock_blend=float(d.get("aa_aimlock_blend", 0.7)),
            aimlock_fov_degrees=float(d.get("aa_aimlock_fov_degrees", 30.0)),
            aimlock_smoothing_rate=float(d.get("aa_aimlock_smoothing_rate", 10.0)),
            aimlock_snappiness=float(d.get("aa_aimlock_snappiness", 0.35)),
            aimlock_prediction_enabled=d.get("aa_aimlock_prediction_enabled", True),
            aimlock_bullet_speed=float(d.get("aa_aimlock_bullet_speed", 30000.0)),
            aimlock_gravity_scale=float(d.get("aa_aimlock_gravity_scale", 0.12)),
            aimlock_noise_degrees=float(d.get("aa_aimlock_noise_degrees", 0.25)),
            aimlock_degrees_full_stick=float(d.get("aa_aimlock_degrees_full_stick", 30.0)),
            aimlock_min_delta_ms=float(d.get("aa_aimlock_min_delta_ms", 8.0)),
            aimlock_pull_max_rate_deg_s=float(d.get("aa_aimlock_pull_max_rate_deg_s", 420.0)),
            aimlock_pull_ramp_up_ms=float(d.get("aa_aimlock_pull_ramp_up_ms", 80.0)),
            aimlock_initial_downsight_mult=float(d.get("aa_aimlock_initial_downsight_mult", 1.8)),
            aimlock_initial_downsight_ms=float(d.get("aa_aimlock_initial_downsight_ms", 350.0)),
            aimlock_adhesion_cone_deg=float(d.get("aa_aimlock_adhesion_cone_deg", 8.0)),
            aimlock_slow_strength=float(d.get("aa_aimlock_slow_strength", 0.85)),
            aimlock_max_yaw_correction_deg=float(d.get("aa_aimlock_max_yaw_correction_deg", 40.0)),
            aimlock_max_pitch_correction_deg=float(d.get("aa_aimlock_max_pitch_correction_deg", 25.0)),
            aimlock_center_strength_mult=float(d.get("aa_aimlock_center_strength_mult", 1.8)),
            aimlock_glue_drift_mult=float(d.get("aa_aimlock_glue_drift_mult", 1.6)),
            aimlock_glue_drift_window_deg=float(d.get("aa_aimlock_glue_drift_window_deg", 15.0)),
            aimlock_lock_timeout_ms=float(d.get("aa_aimlock_lock_timeout_ms", 500.0)),
            aimlock_target_bone=d.get("aa_aimlock_target_bone", "head"),
            aimlock_head_height_cm=float(d.get("aa_aimlock_head_height_cm", 30.0)),
            aimlock_max_tracking_distance_cm=float(d.get("aa_aimlock_max_tracking_distance_cm", 50000.0)),
            aimlock_source=d.get("aa_aimlock_source", "cv"),
            aimlock_proxy_input_min=float(d.get("aa_aimlock_proxy_input_min", 600.0)),
            aimlock_proxy_head_pull_deg=float(d.get("aa_aimlock_proxy_head_pull_deg", 2.5)),
            aimlock_proxy_yaw_gain_deg=float(d.get("aa_aimlock_proxy_yaw_gain_deg", 2.0)),
            aimlock_proxy_assumed_dist_cm=float(d.get("aa_aimlock_proxy_assumed_dist_cm", 3000.0)),
            aimlock_proxy_release_ms=float(d.get("aa_aimlock_proxy_release_ms", 250.0)),
            aimlock_kalman_smoothing=float(d.get("aa_aimlock_kalman_smoothing", 0.0)),
            aimlock_velocity_adaptive_boost=float(d.get("aa_aimlock_velocity_adaptive_boost", 0.0)),
            use_optimized_pipeline=d.get("use_optimized_pipeline", False),
            kernel_aim_beta=d.get("aa_kernel_aim_beta", False),
            kernel_aim_blend=float(d.get("aa_kernel_aim_blend", 0.92)),
            kernel_aim_snappiness=float(d.get("aa_kernel_aim_snappiness", 0.55)),
            kernel_aim_smoothing_rate=float(d.get("aa_kernel_aim_smoothing_rate", 12.0)),
            kernel_aim_pull_max_rate_deg_s=float(d.get("aa_kernel_aim_pull_max_rate_deg_s", 650.0)),
            kernel_aim_fov_degrees=float(d.get("aa_kernel_aim_fov_degrees", 26.0)),
            kernel_aim_head_pull_deg=float(d.get("aa_kernel_aim_head_pull_deg", 3.0)),
            kernel_aim_min_input=float(d.get("aa_kernel_aim_min_input", 300.0)),
            kernel_aim_confidence_enabled=d.get("aa_kernel_aim_confidence_enabled", True),
            kernel_aim_confidence_rise_rate=float(d.get("aa_kernel_aim_confidence_rise_rate", 0.15)),
            kernel_aim_confidence_fall_rate=float(d.get("aa_kernel_aim_confidence_fall_rate", 0.40)),
            kernel_aim_confidence_blend_min=float(d.get("aa_kernel_aim_confidence_blend_min", 0.50)),
            kernel_aim_confidence_blend_max=float(d.get("aa_kernel_aim_confidence_blend_max", 0.98)),
            kernel_aim_kalman_process_noise=float(d.get("aa_kernel_aim_kalman_process_noise", 500.0)),
            kernel_aim_kalman_measure_noise=float(d.get("aa_kernel_aim_kalman_measure_noise", 2000.0)),
            optimized_rotational_speed=float(d.get("optimized_rotational_speed", 0.3)),
            optimized_rotational_radius_mult=float(d.get("optimized_rotational_radius_mult", 1.0)),
            optimized_predictive_enabled=d.get("optimized_predictive_enabled", True),
            optimized_predictive_vel_alpha=float(d.get("optimized_predictive_vel_alpha", 0.15)),
            optimized_predictive_accel_alpha=float(d.get("optimized_predictive_accel_alpha", 0.06)),
            optimized_predictive_lead_ms=float(d.get("optimized_predictive_lead_ms", 40.0)),
            optimized_predictive_min_speed=float(d.get("optimized_predictive_min_speed", 200.0)),
            optimized_predictive_max_lead=float(d.get("optimized_predictive_max_lead", 3000.0)),
            optimized_predictive_consistency=int(d.get("optimized_predictive_consistency", 3)),
            optimized_predictive_kalman_weight=float(d.get("optimized_predictive_kalman_weight", 0.3)),
            optimized_micro_correction_enabled=d.get("optimized_micro_correction_enabled", True),
            optimized_micro_correction_pull=float(d.get("optimized_micro_correction_pull", 0.3)),
            optimized_adaptive_strength_enabled=d.get("optimized_adaptive_strength_enabled", False),
            auto_tuning_enabled=d.get("auto_tuning_enabled", False),
            auto_tuning_min_mult=float(d.get("auto_tuning_min_mult", 0.7)),
            auto_tuning_max_mult=float(d.get("auto_tuning_max_mult", 1.3)),
            auto_tuning_cooldown=float(d.get("auto_tuning_cooldown", 30.0)),
            ls_freq_enabled=d.get("aa_ls_freq_enabled", False),
            ls_freq_amplitude=int(d.get("aa_ls_freq_amplitude", 10)),
            ls_freq_frequency=float(d.get("aa_ls_freq_frequency", 15.0)),
            ls_freq_shape=d.get("aa_ls_freq_shape", "sine"),
            ls_freq_gate=int(d.get("aa_ls_freq_gate", 500)),
            ls_freq_aggressive=d.get("aa_ls_freq_aggressive", False),
            silent_aim_enabled=d.get("aa_silent_aim_enabled", False),
            silent_aim_slow_mult=float(d.get("aa_silent_aim_slow_mult", 1.4)),
            silent_aim_pull_mult=float(d.get("aa_silent_aim_pull_mult", 1.6)),
            silent_aim_shake_blend=float(d.get("aa_silent_aim_shake_blend", 0.55)),
            silent_aim_qt_enabled=d.get("aa_silent_aim_qt_enabled", True),
            silent_aim_intensity=int(d.get("aa_silent_aim_intensity", 5)),
            silent_aim_qt_shake_blend=float(d.get("aa_silent_aim_qt_shake_blend", 0.35)),
            silent_hit_enabled=d.get("aa_silent_hit_enabled", False),
            silent_hit_slow_mult=float(d.get("aa_silent_hit_slow_mult", 1.2)),
            silent_hit_pull_mult=float(d.get("aa_silent_hit_pull_mult", 2.0)),
            silent_hit_shake_blend=float(d.get("aa_silent_hit_shake_blend", 0.50)),
            silent_hit_qt_enabled=d.get("aa_silent_hit_qt_enabled", True),
            silent_hit_intensity=int(d.get("aa_silent_hit_intensity", 8)),
            silent_hit_qt_shake_blend=float(d.get("aa_silent_hit_qt_shake_blend", 0.30)),
            kbm_mode=d.get("aa_kbm_mode", True),
            kbm_scale=float(d.get("aa_kbm_scale", 0.25)),
            fn_humanize=d.get("aa_fn_humanize", True),
            oef_enabled=d.get("aa_oef_enabled", False),
            oef_min_cutoff=float(d.get("aa_oef_min_cutoff", 1.0)),
            oef_beta=float(d.get("aa_oef_beta", 0.05)),
            oef_d_cutoff=float(d.get("aa_oef_d_cutoff", 1.0)),
            predictive_tracker_enabled=d.get("aa_predictive_tracker_enabled", False),
            predictive_vel_alpha=float(d.get("aa_predictive_vel_alpha", 0.15)),
            predictive_accel_alpha=float(d.get("aa_predictive_accel_alpha", 0.05)),
            predictive_lead_horizon_ms=float(d.get("aa_predictive_lead_horizon_ms", 40.0)),
            predictive_min_speed=float(d.get("aa_predictive_min_speed", 200.0)),
            predictive_max_lead=int(d.get("aa_predictive_max_lead", 3000)),
            predictive_consistency=int(d.get("aa_predictive_consistency", 3)),
            predictive_direction_blend=float(d.get("aa_predictive_direction_blend", 0.7)),
            adhesion_buffer_enabled=d.get("aa_adhesion_buffer_enabled", False),
            adhesion_hold_ms=float(d.get("aa_adhesion_hold_ms", 120.0)),
            adhesion_decay=float(d.get("aa_adhesion_decay", 0.35)),
            adhesion_axis_lock=float(d.get("aa_adhesion_axis_lock", 0.18)),
            adhesion_min_mag=float(d.get("aa_adhesion_min_mag", 100.0)),
            follow_assist_enabled=d.get("aa_follow_assist_enabled", False),
            follow_assist_pull=int(d.get("aa_follow_assist_pull", 300)),
            neural_enabled=d.get("aa_neural_enabled", False),
            neural_kalman_noise=float(d.get("aa_neural_kalman_noise", 500.0)),
            neural_kalman_lead_ms=float(d.get("aa_neural_kalman_lead_ms", 25.0)),
            neural_kalman_weight=float(d.get("aa_neural_kalman_weight", 0.6)),
            neural_micro_enabled=d.get("aa_neural_micro_enabled", True),
            neural_micro_amplitude=float(d.get("aa_neural_micro_amplitude", 180.0)),
            neural_confidence_scale=float(d.get("aa_neural_confidence_scale", 1.0)),
            neural_harmonizer_enabled=d.get("aa_neural_harmonizer_enabled", True),
            neural_error_feedback_enabled=d.get("aa_neural_error_feedback_enabled", True),
            multi_polar_enabled=d.get("aa_multi_polar_enabled", False),
            multi_polar_close_enabled=d.get("aa_multi_polar_close_enabled", True),
            multi_polar_close_radius=int(d.get("aa_multi_polar_close_radius", 3)),
            multi_polar_close_angle=float(d.get("aa_multi_polar_close_angle", 8.0)),
            multi_polar_close_shape=d.get("aa_multi_polar_close_shape", "circle"),
            multi_polar_close_fire_boost=int(d.get("aa_multi_polar_close_fire_boost", 2)),
            multi_polar_medium_enabled=d.get("aa_multi_polar_medium_enabled", True),
            multi_polar_medium_radius=int(d.get("aa_multi_polar_medium_radius", 8)),
            multi_polar_medium_angle=float(d.get("aa_multi_polar_medium_angle", 12.0)),
            multi_polar_medium_shape=d.get("aa_multi_polar_medium_shape", "oval_tall"),
            multi_polar_medium_fire_boost=int(d.get("aa_multi_polar_medium_fire_boost", 3)),
            multi_polar_long_enabled=d.get("aa_multi_polar_long_enabled", True),
            multi_polar_long_radius=int(d.get("aa_multi_polar_long_radius", 14)),
            multi_polar_long_angle=float(d.get("aa_multi_polar_long_angle", 18.0)),
            multi_polar_long_shape=d.get("aa_multi_polar_long_shape", "oval_wide"),
            multi_polar_long_fire_boost=int(d.get("aa_multi_polar_long_fire_boost", 4)),
            multi_polar_sniper_enabled=d.get("aa_multi_polar_sniper_enabled", True),
            multi_polar_sniper_radius=int(d.get("aa_multi_polar_sniper_radius", 20)),
            multi_polar_sniper_angle=float(d.get("aa_multi_polar_sniper_angle", 22.0)),
            multi_polar_sniper_shape=d.get("aa_multi_polar_sniper_shape", "spiral"),
            multi_polar_sniper_fire_boost=int(d.get("aa_multi_polar_sniper_fire_boost", 5)),
            multi_polar_sniper_ads_only=d.get("aa_multi_polar_sniper_ads_only", True),
            ghost_tracker_enabled=d.get("aa_ghost_tracker_enabled", False),
            ghost_tracker_bubble_radius=int(d.get("aa_ghost_tracker_bubble_radius", 8000)),
            ghost_tracker_decel_strength=float(d.get("aa_ghost_tracker_decel_strength", 0.3)),
            ghost_tracker_decel_ramp=float(d.get("aa_ghost_tracker_decel_ramp", 0.5)),
            ghost_tracker_stick_threshold=int(d.get("aa_ghost_tracker_stick_threshold", 4000)),
            burst_mode_enabled=d.get("aa_burst_mode_enabled", False),
            burst_mode_count=int(d.get("aa_burst_mode_count", 3)),
            burst_mode_aim_boost=float(d.get("aa_burst_mode_aim_boost", 1.5)),
            burst_mode_recoil_reduction=float(d.get("aa_burst_mode_recoil_reduction", 0.7)),
            burst_mode_cooldown_ms=float(d.get("aa_burst_mode_cooldown_ms", 200.0)),
            batts_sticky_enabled=d.get("aa_batts_sticky_enabled", False),
            batts_sticky_ads_size=int(d.get("aa_batts_sticky_ads_size", 14)),
            batts_sticky_ads_fire_size=int(d.get("aa_batts_sticky_ads_fire_size", 16)),
            batts_sticky_hipfire_size=int(d.get("aa_batts_sticky_hipfire_size", 18)),
            batts_sticky_ads_speed=float(d.get("aa_batts_sticky_ads_speed", 8.0)),
            batts_sticky_ads_fire_speed=float(d.get("aa_batts_sticky_ads_fire_speed", 12.0)),
            batts_sticky_hipfire_speed=float(d.get("aa_batts_sticky_hipfire_speed", 6.0)),
            batts_sticky_drift_enabled=d.get("aa_batts_sticky_drift_enabled", True),
            batts_sticky_drift_strength=float(d.get("aa_batts_sticky_drift_strength", 0.3)),
            xanax_ai_enabled=d.get("aa_xanax_ai_enabled", False),
            xanax_ai_synergy_boost=float(d.get("aa_xanax_ai_synergy_boost", 1.15)),
            xanax_ai_synergy_threshold=int(d.get("aa_xanax_ai_synergy_threshold", 3)),
            xanax_ai_close_range_boost=float(d.get("aa_xanax_ai_close_range_boost", 1.2)),
            xanax_ai_long_range_boost=float(d.get("aa_xanax_ai_long_range_boost", 0.85)),
            xanax_ai_close_range_threshold=int(d.get("aa_xanax_ai_close_range_threshold", 5000)),
            xanax_ai_long_range_threshold=int(d.get("aa_xanax_ai_long_range_threshold", 20000)),
            xanax_ai_humanize=d.get("aa_xanax_ai_humanize", True),
            xanax_ai_humanize_jitter=float(d.get("aa_xanax_ai_humanize_jitter", 0.05)),
            xanax_ai_adapt_rate=float(d.get("aa_xanax_ai_adapt_rate", 0.02)),
            wz_vibration_enabled=d.get("aa_wz_vibration_enabled", False),
            wz_vibration_intensity=int(d.get("aa_wz_vibration_intensity", 50)),
            wz_vibration_frequency=float(d.get("aa_wz_vibration_frequency", 30.0)),
            wz_vibration_amplitude=int(d.get("aa_wz_vibration_amplitude", 8)),
            wz_vibration_ads_only=d.get("aa_wz_vibration_ads_only", False),
            wz_vibration_fire_only=d.get("aa_wz_vibration_fire_only", False),
            wz_buffer_enabled=d.get("aa_wz_buffer_enabled", False),
            wz_buffer_tracking_enabled=d.get("aa_wz_buffer_tracking_enabled", True),
            wz_buffer_tracking_strength=float(d.get("aa_wz_buffer_tracking_strength", 2.0)),
            wz_buffer_tracking_radius=int(d.get("aa_wz_buffer_tracking_radius", 5000)),
            wz_buffer_sticky_enabled=d.get("aa_wz_buffer_sticky_enabled", True),
            wz_buffer_sticky_strength=float(d.get("aa_wz_buffer_sticky_strength", 1.8)),
            wz_buffer_sticky_radius=int(d.get("aa_wz_buffer_sticky_radius", 3000)),
            wz_buffer_rotation_enabled=d.get("aa_wz_buffer_rotation_enabled", True),
            wz_buffer_rotation_radius=int(d.get("aa_wz_buffer_rotation_radius", 12)),
            wz_buffer_rotation_speed=float(d.get("aa_wz_buffer_rotation_speed", 15.0)),
            wz_buffer_fire_boost=float(d.get("aa_wz_buffer_fire_boost", 1.4)),
            wz_buffer_ads_only=d.get("aa_wz_buffer_ads_only", False),
            wz_rapid_enabled=d.get("aa_wz_rapid_enabled", False),
            wz_rapid_speed=int(d.get("aa_wz_rapid_speed", 80)),
            wz_rapid_hold_ms=int(d.get("aa_wz_rapid_hold_ms", 5)),
            wz_rapid_release_ms=int(d.get("aa_wz_rapid_release_ms", 5)),
            wz_rapid_burst_mode=d.get("aa_wz_rapid_burst_mode", False),
            wz_rapid_burst_count=int(d.get("aa_wz_rapid_burst_count", 3)),
            wz_rapid_burst_pause_ms=int(d.get("aa_wz_rapid_burst_pause_ms", 100)),
            wz_rapid_ads_only=d.get("aa_wz_rapid_ads_only", False),
            wz_rapid_anti_recoil=d.get("aa_wz_rapid_anti_recoil", True),
            wz_rapid_anti_recoil_strength=float(d.get("aa_wz_rapid_anti_recoil_strength", 1.2)),
            # Precision Buffer (DS4 Fluid)
            precision_tracking_enabled=d.get("aa_precision_tracking_enabled", False),
            precision_tracking_smooth=float(d.get("aa_precision_tracking_smooth", 0.3)),
            precision_tracking_strength=float(d.get("aa_precision_tracking_strength", 1.2)),
            precision_tracking_deadzone=int(d.get("aa_precision_tracking_deadzone", 200)),
            precision_anti_jitter_enabled=d.get("aa_precision_anti_jitter_enabled", False),
            precision_anti_jitter_strength=float(d.get("aa_precision_anti_jitter_strength", 0.4)),
            precision_anti_jitter_adaptive=d.get("aa_precision_anti_jitter_adaptive", True),
            precision_stick_smooth_enabled=d.get("aa_precision_stick_smooth_enabled", False),
            precision_stick_smooth_factor=float(d.get("aa_precision_stick_smooth_factor", 0.15)),
            precision_stick_smooth_response=float(d.get("aa_precision_stick_smooth_response", 0.8)),
            precision_aim_smooth_enabled=d.get("aa_precision_aim_smooth_enabled", False),
            precision_aim_smooth_factor=float(d.get("aa_precision_aim_smooth_factor", 0.2)),
            precision_aim_smooth_ads_boost=float(d.get("aa_precision_aim_smooth_ads_boost", 1.3)),
            # Build mode detection
            build_mode_enabled=d.get("aa_build_mode_enabled", True),
            build_disable_ads_only=d.get("aa_build_disable_ads_only", True),
        )

@dataclass
class RapidFireConfig:
    """Configuração do motor de Rapid Fire (estilo Cronus Zen).
    Alterna RT/R2 em alta frequência para maximizar cadência de tiro."""
    enabled: bool = False
    speed: int = 50          # disparos por segundo (Hz)
    hold_ms: int = 10        # tempo de pressionamento por ciclo (ms)
    release_ms: int = 10     # tempo de liberação por ciclo (ms)
    trigger_button: str = "RT"  # botão que ativa (RT, R2)
    toggle_key: str = "KEY_F9"  # tecla para ligar/desligar
    mode: str = "universal"  # universal | pistol | shotgun | custom
    hold_ratio: float = 0.75  # fração do ciclo em hold (release curto = full-auto não stuttera)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "RapidFireConfig":
        return RapidFireConfig(
            enabled=d.get("remap_rapid_fire", False),
            speed=int(d.get("remap_rf_speed", 50)),
            hold_ms=int(d.get("remap_rf_hold_ms", 10)),
            release_ms=int(d.get("remap_rf_release_ms", 10)),
            trigger_button=d.get("remap_rf_trigger", "RT"),
            toggle_key=d.get("remap_rf_toggle_key", "KEY_F9"),
            mode=d.get("remap_rf_mode", "universal"),
            hold_ratio=float(d.get("remap_rf_hold_ratio", 0.75)),
        )

@dataclass
class BloomReducerConfig:
    """Configuração do Bloom Reducer (estilo Cronus Zen).

    Segurar RT dispara rajadas curtas (burst_shots) com pausa de reset_ms —
    o bloom do Fortnite zera nessa pausa e cada rajada recomeça com a
    primeira bala (spread mínimo). Tiros separados por tap_gap_ms."""
    enabled: bool = False
    burst_shots: int = 3      # tiros por rajada (2-10)
    hold_ms: int = 25         # duração de cada tiro (ms)
    tap_gap_ms: int = 20      # separação entre tiros da rajada (ms)
    reset_ms: int = 250       # pausa entre rajadas — bloom zera (ms)
    trigger_button: str = "RT"  # gatilho que ativa (RT, R2)
    toggle_key: str = "KEY_F12"  # tecla para ligar/desligar

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "BloomReducerConfig":
        return BloomReducerConfig(
            enabled=d.get("remap_bloom_reducer", False),
            burst_shots=int(d.get("remap_br_shots", 3)),
            hold_ms=int(d.get("remap_br_hold_ms", 25)),
            tap_gap_ms=int(d.get("remap_br_tap_ms", 20)),
            reset_ms=int(d.get("remap_br_reset_ms", 250)),
            trigger_button=d.get("remap_br_trigger", "RT"),
            toggle_key=d.get("remap_br_toggle_key", "KEY_F12"),
        )

@dataclass
class CrouchSpamConfig:
    """Configuração do motor de Crouch Spam (estilo Cronus Zen).
    Alterna botão de agachar em alta frequência para dificultar headshots."""
    enabled: bool = False
    speed: int = 60          # acionamentos por segundo (Hz)
    hold_ms: int = 8         # tempo de pressionamento por ciclo (ms)
    release_ms: int = 8      # tempo de liberação por ciclo (ms)
    crouch_button: str = "B"  # botão de agachar (B, Circle)
    only_while_shooting: bool = True  # só ativa durante tiro
    toggle_key: str = "KEY_F10"  # tecla para ligar/desligar

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "CrouchSpamConfig":
        return CrouchSpamConfig(
            enabled=d.get("remap_crouch_spam", False),
            speed=int(d.get("remap_cs_speed", 60)),
            hold_ms=int(d.get("remap_cs_hold_ms", 8)),
            release_ms=int(d.get("remap_cs_release_ms", 8)),
            crouch_button=d.get("remap_cs_button", "B"),
            only_while_shooting=d.get("remap_cs_only_shooting", True),
            toggle_key=d.get("remap_cs_toggle_key", "KEY_F10"),
        )

@dataclass
class SlideCancelConfig:
    """Configuração do Slide Cancel macro.
    Ao pressionar Espaço (pulo), após o tempo de arco, executa
    C (agachar) + Espaço (pular) para cancelar a animação de aterrissagem.
    """
    enabled: bool = False
    jump_arc_ms: int = 350    # tempo até executar o combo após o pulo
    crouch_hold_ms: int = 30  # quanto tempo segura o agachar
    jump_hold_ms: int = 30    # quanto tempo segura o segundo pulo
    cooldown_ms: int = 200    # pausa entre combos
    crouch_button_code: int = 0x13E  # BTN_THUMBR (RS) - agachar
    jump_button_code: int = 0x130    # BTN_A - pular
    toggle_key: str = "KEY_F11"

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "SlideCancelConfig":
        return SlideCancelConfig(
            enabled=d.get("slide_cancel_enabled", False),
            jump_arc_ms=int(d.get("slide_cancel_jump_arc_ms", 350)),
            crouch_hold_ms=int(d.get("slide_cancel_crouch_hold_ms", 30)),
            jump_hold_ms=int(d.get("slide_cancel_jump_hold_ms", 30)),
            cooldown_ms=int(d.get("slide_cancel_cooldown_ms", 200)),
            crouch_button_code=int(d.get("slide_cancel_crouch_btn", "0x13E"), 16) if isinstance(d.get("slide_cancel_crouch_btn"), str) else int(d.get("slide_cancel_crouch_btn", 0x13E)),
            jump_button_code=int(d.get("slide_cancel_jump_btn", "0x130"), 16) if isinstance(d.get("slide_cancel_jump_btn"), str) else int(d.get("slide_cancel_jump_btn", 0x130)),
            toggle_key=d.get("slide_cancel_toggle_key", "KEY_F11"),
        )

@dataclass
class MovementTechConfig:
    """Configuração dos motores de movimentação competitiva.

    - dodge_shot: crouch on/off durante o tiro de perto — inimigo perde AA.
    - slide_cancel: tap crouch 2x + jump ao pular correndo (momentum tech).
    - bunny_hop: re-press de jump em cadência enquanto corre.
    Timings seguem ReWASD minimum (30-50ms entre teclas).
    """
    dodge_shot_enabled: bool = False
    dodge_hold_ms: int = 40
    dodge_release_ms: int = 60
    slide_cancel_enabled: bool = False
    slide_tap_ms: int = 40
    slide_gap_ms: int = 40
    bunny_hop_enabled: bool = False
    bunny_hold_ms: int = 50
    bunny_gap_ms: int = 120
    crouch_button_code: int = 0x13E  # BTN_THUMBR (RS) - agachar
    jump_button_code: int = 0x130    # BTN_A - pular

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "MovementTechConfig":
        return MovementTechConfig(
            dodge_shot_enabled=d.get("remap_dodge_shot", False),
            dodge_hold_ms=int(d.get("remap_dodge_hold_ms", 40)),
            dodge_release_ms=int(d.get("remap_dodge_release_ms", 60)),
            slide_cancel_enabled=d.get("remap_slide_cancel", False),
            slide_tap_ms=int(d.get("remap_slide_tap_ms", 40)),
            slide_gap_ms=int(d.get("remap_slide_gap_ms", 40)),
            bunny_hop_enabled=d.get("remap_bunny_hop", False),
            bunny_hold_ms=int(d.get("remap_bunny_hold_ms", 50)),
            bunny_gap_ms=int(d.get("remap_bunny_gap_ms", 120)),
            crouch_button_code=int(d.get("remap_mv_crouch_btn", "0x13E"), 16) if isinstance(d.get("remap_mv_crouch_btn"), str) else int(d.get("remap_mv_crouch_btn", 0x13E)),
            jump_button_code=int(d.get("remap_mv_jump_btn", "0x130"), 16) if isinstance(d.get("remap_mv_jump_btn"), str) else int(d.get("remap_mv_jump_btn", 0x130)),
        )


@dataclass
class CrouchAimConfig:
    """Crouch Aim (estilo Zen): agacha enquanto está mirando (ADS)."""
    enabled: bool = False
    button_code: int = 0x13E  # BTN_THUMBR (RS) - agachar

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "CrouchAimConfig":
        return CrouchAimConfig(
            enabled=d.get("remap_crouch_aim", False),
            button_code=int(d.get("remap_ca_button", "0x13E"), 16) if isinstance(d.get("remap_ca_button"), str) else int(d.get("remap_ca_button", 0x13E)),
        )


@dataclass
class ControllerHardwareConfig:
    controller_id: str = "xbox360"
    polling_rate_hz: int = 0
    power_profile: str = "performance"
    trigger: TriggerConfig = None
    gyro: GyroConfig = None
    rgb: RGBConfig = None
    joystick_response_curve: str = "linear"
    anti_deadzone_ls: int = 0
    anti_deadzone_rs: int = 0
    response_curve_ls: str = "linear"
    response_curve_rs: str = "linear"
    raw_mode_ls: bool = False
    raw_mode_rs: bool = False
    trigger_deadzone_start: int = 0
    trigger_deadzone_end: int = 100
    hair_trigger_mode: str = "off"
    dpad_diag_lock: bool = False
    vibration_lt: int = 50
    vibration_rt: int = 50
    vibration_sync: bool = True

    def __post_init__(self):
        if self.trigger is None:
            self.trigger = TriggerConfig()
        if self.gyro is None:
            self.gyro = GyroConfig()
        if self.rgb is None:
            self.rgb = RGBConfig()

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "controller_id": self.controller_id,
            "polling_rate_hz": self.polling_rate_hz,
            "power_profile": self.power_profile,
            "joystick_response_curve": self.joystick_response_curve,
            "anti_deadzone_ls": self.anti_deadzone_ls,
            "anti_deadzone_rs": self.anti_deadzone_rs,
            "response_curve_ls": self.response_curve_ls,
            "response_curve_rs": self.response_curve_rs,
            "raw_mode_ls": self.raw_mode_ls,
            "raw_mode_rs": self.raw_mode_rs,
            "trigger_deadzone_start": self.trigger_deadzone_start,
            "trigger_deadzone_end": self.trigger_deadzone_end,
            "hair_trigger_mode": self.hair_trigger_mode,
            "dpad_diag_lock": self.dpad_diag_lock,
            "vibration_lt": self.vibration_lt,
            "vibration_rt": self.vibration_rt,
            "vibration_sync": self.vibration_sync,
        }
        d.update(self.trigger.to_dict())
        d.update(self.gyro.to_dict())
        d.update(self.rgb.to_dict())
        return d

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "ControllerHardwareConfig":
        return ControllerHardwareConfig(
            controller_id=d.get("controller_id", "xbox360"),
            polling_rate_hz=int(d.get("polling_rate_hz", 0)),
            power_profile=d.get("power_profile", "performance"),
            trigger=TriggerConfig.from_dict(d),
            gyro=GyroConfig.from_dict(d),
            rgb=RGBConfig.from_dict(d),
            joystick_response_curve=d.get("joystick_response_curve", "linear"),
            anti_deadzone_ls=int(d.get("anti_deadzone_ls", 0)),
            anti_deadzone_rs=int(d.get("anti_deadzone_rs", 0)),
            response_curve_ls=d.get("response_curve_ls", "linear"),
            response_curve_rs=d.get("response_curve_rs", "linear"),
            raw_mode_ls=bool(d.get("raw_mode_ls", False)),
            raw_mode_rs=bool(d.get("raw_mode_rs", False)),
            trigger_deadzone_start=int(d.get("trigger_deadzone_start", 0)),
            trigger_deadzone_end=int(d.get("trigger_deadzone_end", 100)),
            hair_trigger_mode=d.get("hair_trigger_mode", "off"),
            dpad_diag_lock=bool(d.get("dpad_diag_lock", False)),
            vibration_lt=int(d.get("vibration_lt", 50)),
            vibration_rt=int(d.get("vibration_rt", 50)),
            vibration_sync=bool(d.get("vibration_sync", True)),
        )

@dataclass
class SniperZoomConfig:
    enabled: bool = False
    button: str = "BTN_SIDE"
    zoom_factor: float = 4.0
    window_width: int = 240
    window_height: int = 180
    fixed_position: bool = False
    fixed_x: int = 960
    fixed_y: int = 540

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "SniperZoomConfig":
        return SniperZoomConfig(
            enabled=d.get("sniper_zoom_enabled", False),
            button=str(d.get("sniper_zoom_button", "BTN_SIDE")),
            zoom_factor=float(d.get("sniper_zoom_factor", 4.0)),
            window_width=int(d.get("sniper_zoom_window_width", 240)),
            window_height=int(d.get("sniper_zoom_window_height", 180)),
            fixed_position=d.get("sniper_zoom_fixed_pos", False),
            fixed_x=int(d.get("sniper_zoom_fixed_x", 960)),
            fixed_y=int(d.get("sniper_zoom_fixed_y", 540)),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sniper_zoom_enabled": self.enabled,
            "sniper_zoom_button": self.button,
            "sniper_zoom_factor": self.zoom_factor,
            "sniper_zoom_window_width": self.window_width,
            "sniper_zoom_window_height": self.window_height,
            "sniper_zoom_fixed_pos": self.fixed_position,
            "sniper_zoom_fixed_x": self.fixed_x,
            "sniper_zoom_fixed_y": self.fixed_y,
        }


@dataclass
class AppConfig:
    controller_type: str = "xbox360"
    # Quando 8BitDo detectado, mapear saída virtual como DS5 (DualSense)
    eightbitdo_as_dualsense: bool = True
    ls_physics: StickPhysicsConfig = None
    rs_physics: StickPhysicsConfig = None
    lt_physics: TriggerPhysicsConfig = None
    rt_physics: TriggerPhysicsConfig = None
    aim_assist: AimAssistConfig = None
    recoil: RecoilConfig = None
    recoil_runtime: RecoilRuntimeConfig = None
    rapid_fire: RapidFireConfig = None
    bloom_reducer: BloomReducerConfig = None
    crouch_spam: CrouchSpamConfig = None
    crouch_aim: CrouchAimConfig = None
    sniper_zoom: SniperZoomConfig = None
    slide_cancel: SlideCancelConfig = None
    movement_tech: MovementTechConfig = None
    remap_kbd_path: str = ""
    remap_mouse_path: str = ""
    remap_active: bool = False
    mouse_sens: float = 80.0
    sens_x: float = 80.0
    sens_y: float = 80.0
    mouse_curve: float = 0.65
    mouse_smooth: float = 0.0
    mouse_min_output: float = 0.0
    square_stick: bool = True
    kbd_bindings: dict = None
    controller_hardware: ControllerHardwareConfig = None

    def __post_init__(self):
        if self.ls_physics is None:
            self.ls_physics = StickPhysicsConfig()
        if self.rs_physics is None:
            self.rs_physics = StickPhysicsConfig()
        if self.lt_physics is None:
            self.lt_physics = TriggerPhysicsConfig()
        if self.rt_physics is None:
            self.rt_physics = TriggerPhysicsConfig()
        if self.aim_assist is None:
            self.aim_assist = AimAssistConfig()
        if self.recoil is None:
            self.recoil = RecoilConfig()
        if self.recoil_runtime is None:
            self.recoil_runtime = RecoilRuntimeConfig()
        if self.rapid_fire is None:
            self.rapid_fire = RapidFireConfig()
        if self.bloom_reducer is None:
            self.bloom_reducer = BloomReducerConfig()
        if self.crouch_spam is None:
            self.crouch_spam = CrouchSpamConfig()
        if self.crouch_aim is None:
            self.crouch_aim = CrouchAimConfig()
        if self.sniper_zoom is None:
            self.sniper_zoom = SniperZoomConfig()
        if self.slide_cancel is None:
            self.slide_cancel = SlideCancelConfig()
        if self.controller_hardware is None:
            self.controller_hardware = ControllerHardwareConfig()
        if self.kbd_bindings is None:
            from nocrosshair.core.remapper import DEFAULT_KBD_BINDINGS
            self.kbd_bindings = dict(DEFAULT_KBD_BINDINGS)
        else:
            from nocrosshair.core.remapper import DEFAULT_KBD_BINDINGS
            for k, v in DEFAULT_KBD_BINDINGS.items():
                if k not in self.kbd_bindings:
                    self.kbd_bindings[k] = v

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "AppConfig":
        kbd_path = d.get("remap_kbd_path", "")
        mouse_path = d.get("remap_mouse_path", "")
        bindings = d.get("kbd_bindings", None)
        controller_hardware = ControllerHardwareConfig()
        hw_data = d.get("controller_hardware", None)
        if hw_data is not None:
            controller_hardware = ControllerHardwareConfig.from_dict(hw_data)
        return AppConfig(
            controller_type=d.get("remap_controller", "xbox360"),
            eightbitdo_as_dualsense=d.get("eightbitdo_as_dualsense", True),
            ls_physics=AdvancedStickPhysicsConfig.from_dict(d, "ls_"),
            rs_physics=AdvancedStickPhysicsConfig.from_dict(d, "rs_"),
            lt_physics=TriggerPhysicsConfig.from_dict(d, "lt_"),
            rt_physics=TriggerPhysicsConfig.from_dict(d, "rt_"),
            aim_assist=AimAssistConfig.from_dict(d),
            recoil=RecoilConfig.from_dict(d),
            recoil_runtime=RecoilRuntimeConfig.from_dict(d),
            rapid_fire=RapidFireConfig.from_dict(d),
            bloom_reducer=BloomReducerConfig.from_dict(d),
            crouch_spam=CrouchSpamConfig.from_dict(d),
            crouch_aim=CrouchAimConfig.from_dict(d),
            remap_kbd_path=kbd_path,
            remap_mouse_path=mouse_path,
            remap_active=d.get("remap_active", bool(kbd_path or mouse_path)),
            mouse_sens=float(d.get("remap_mouse_sens", 80.0)),
            sens_x=float(d.get("remap_sens_x", 80.0)),
            sens_y=float(d.get("remap_sens_y", 80.0)),
            mouse_curve=float(d.get("remap_curve", 0.65)),
            mouse_smooth=float(d.get("remap_smooth", 0.0)),
            mouse_min_output=float(d.get("remap_min_output", 0.0)),
            square_stick=bool(d.get("remap_square_stick", True)),
            sniper_zoom=SniperZoomConfig.from_dict(d),
            slide_cancel=SlideCancelConfig.from_dict(d),
            movement_tech=MovementTechConfig.from_dict(d),
            kbd_bindings=bindings,
            controller_hardware=controller_hardware,
        )

    def to_dict(self) -> Dict[str, Any]:
        def _fields(obj):
            return {f.name: getattr(obj, f.name) for f in obj.__dataclass_fields__.values()}

        d: Dict[str, Any] = {"remap_controller": self.controller_type}
        d["eightbitdo_as_dualsense"] = self.eightbitdo_as_dualsense
        for prefix, cfg in [
            ("ls_", self.ls_physics),
            ("rs_", self.rs_physics),
            ("lt_", self.lt_physics),
            ("rt_", self.rt_physics),
        ]:
            for k, v in _fields(cfg).items():
                d[f"{prefix}{k}"] = v

        aa = self.aim_assist
        d["remap_aa_enabled"] = aa.enabled
        d["aa_base_aa_enabled"] = aa.base_aa_enabled
        d["remap_aa_strength"] = aa.strength
        d["aa_ads_multiplier"] = aa.ads_multiplier
        d["aa_zone"] = aa.zone
        d["aa_rotational"] = aa.rotational
        d["aa_pulse_level"] = aa.pulse_level
        d["aa_aim_type"] = aa.aim_type
        d["aa_magnetic_snap"] = aa.magnetic_snap
        d["aa_snap_strength"] = aa.snap_strength
        d["aa_snap_duration"] = aa.snap_duration
        d["aa_tracking"] = aa.tracking
        d["aa_tracking_strength"] = aa.tracking_strength
        d["aa_tracking_speed"] = aa.tracking_speed
        d["aa_track_ads_pulse_ms"] = aa.track_ads_pulse_ms
        d["aa_sticky_enabled"] = aa.sticky_enabled
        d["aa_sticky_strength"] = aa.sticky_strength
        d["aa_rush_enabled"] = aa.rush_enabled
        d["aa_rush_mult"] = aa.rush_mult
        d["aa_rush_always"] = aa.rush_always
        d["aa_rush_pulse_ms"] = aa.rush_pulse_ms
        d["aa_rush_cooldown_ms"] = aa.rush_cooldown_ms
        d["aa_rush_deadzone"] = aa.rush_deadzone
        d["aa_cjitter_enabled"] = aa.cjitter_enabled
        d["aa_cjitter_left_enabled"] = aa.cjitter_left_enabled
        d["aa_cjitter_left_amp"] = aa.cjitter_left_amp
        d["aa_power_boost"] = aa.power_boost
        d["aa_power_mult"] = aa.power_mult
        d["aa_lock_enabled"] = aa.lock_enabled
        d["aa_lock_strength"] = aa.lock_strength
        d["aa_lock_fov"] = aa.lock_fov
        d["aa_lock_track"] = aa.lock_track
        d["aa_lock_sticky"] = aa.lock_sticky
        d["aa_lock_smooth"] = aa.lock_smooth
        d["aa_shape_mode"] = aa.shape_mode
        d["aa_use_dz_radius"] = aa.use_dz_radius
        d["aa_deadzone_radius"] = aa.deadzone_aa_radius
        d["aa_zone_multiplier"] = aa.zone_multiplier
        d["aa_aim_pattern"] = aa.aim_pattern
        d["aa_auto_aa_enabled"] = aa.auto_aa_enabled
        d["aa_auto_rotation_enabled"] = aa.auto_rotation_enabled
        d["aa_auto_rotation_speed"] = aa.auto_rotation_speed
        d["aa_bullet_drop_enabled"] = aa.bullet_drop_enabled
        d["aa_bullet_drop_factor"] = aa.bullet_drop_factor
        d["aa_bullet_drop_offset"] = aa.bullet_drop_offset
        d["aa_anti_sway_enabled"] = aa.anti_sway_enabled
        d["aa_anti_sway_strength"] = aa.anti_sway_strength
        d["aa_pd_kp"] = aa.pd_kp
        d["aa_pd_kd"] = aa.pd_kd
        d["aa_adaptive_strength"] = aa.adaptive_strength
        d["aa_adaptive_strength_min"] = aa.adaptive_strength_min
        d["aa_adaptive_strength_max"] = aa.adaptive_strength_max
        d["aa_anti_shake_blend"] = aa.anti_shake_blend
        d["aa_magnetic_pull"] = aa.magnetic_pull
        d["aa_long_range_track_boost"] = aa.long_range_track_boost
        d["aa_anti_flinch"] = aa.anti_flinch
        d["aa_anti_flinch_strength"] = aa.anti_flinch_strength
        d["aa_zero_delay"] = aa.zero_delay
        d["aa_zero_delay_ms"] = aa.zero_delay_ms
        d["aa_bloom_compensation"] = aa.bloom_compensation
        d["aa_fn_layer_strength"] = aa.fn_layer_strength
        d["aa_fn_strength_slider"] = aa.fn_strength_slider
        d["aa_fn_zone"] = aa.fn_zone
        d["aa_fn_input_gate"] = aa.fn_input_gate
        d["aa_fn_ads_multiplier"] = aa.fn_ads_multiplier
        d["aa_fn_rotation_cap"] = aa.fn_rotation_cap
        d["aa_fn_camera_slow_keep"] = aa.fn_camera_slow_keep
        d["aa_fn_aim_pull_floor"] = aa.fn_aim_pull_floor
        d["aa_fn_camera_pull_floor"] = aa.fn_camera_pull_floor
        d["aa_auto_track_enabled"] = aa.auto_track_enabled
        d["aa_auto_track_multiplier"] = aa.auto_track_multiplier
        d["aa_auto_track_persistence_ms"] = aa.auto_track_persistence_ms
        d["aa_auto_track_threshold"] = aa.auto_track_threshold
        d["aa_sticky_magnet_enabled"] = aa.sticky_magnet_enabled
        d["aa_sticky_magnet_strength"] = aa.sticky_magnet_strength
        d["aa_sticky_magnet_pull"] = aa.sticky_magnet_pull
        d["aa_aim_spam_enabled"] = aa.aim_spam_enabled
        d["aa_aim_spam_interval_ms"] = aa.aim_spam_interval_ms
        d["aa_aim_spam_hold_ms"] = aa.aim_spam_hold_ms
        d["aa_enhanced_enabled"] = aa.enhanced_enabled
        d["aa_micro_adjust_pull"] = aa.micro_adjust_pull
        d["aa_head_assist_enabled"] = aa.head_assist_enabled
        d["aa_head_assist_strength"] = aa.head_assist_strength
        d["aa_aimlock_enabled"] = aa.aimlock_enabled
        d["aa_aimlock_blend"] = aa.aimlock_blend
        d["aa_aimlock_fov_degrees"] = aa.aimlock_fov_degrees
        d["aa_aimlock_smoothing_rate"] = aa.aimlock_smoothing_rate
        d["aa_aimlock_snappiness"] = aa.aimlock_snappiness
        d["aa_aimlock_prediction_enabled"] = aa.aimlock_prediction_enabled
        d["aa_aimlock_bullet_speed"] = aa.aimlock_bullet_speed
        d["aa_aimlock_gravity_scale"] = aa.aimlock_gravity_scale
        d["aa_aimlock_noise_degrees"] = aa.aimlock_noise_degrees
        d["aa_aimlock_degrees_full_stick"] = aa.aimlock_degrees_full_stick
        d["aa_aimlock_min_delta_ms"] = aa.aimlock_min_delta_ms
        d["aa_aimlock_pull_max_rate_deg_s"] = aa.aimlock_pull_max_rate_deg_s
        d["aa_aimlock_pull_ramp_up_ms"] = aa.aimlock_pull_ramp_up_ms
        d["aa_aimlock_initial_downsight_mult"] = aa.aimlock_initial_downsight_mult
        d["aa_aimlock_initial_downsight_ms"] = aa.aimlock_initial_downsight_ms
        d["aa_aimlock_adhesion_cone_deg"] = aa.aimlock_adhesion_cone_deg
        d["aa_aimlock_slow_strength"] = aa.aimlock_slow_strength
        d["aa_aimlock_max_yaw_correction_deg"] = aa.aimlock_max_yaw_correction_deg
        d["aa_aimlock_max_pitch_correction_deg"] = aa.aimlock_max_pitch_correction_deg
        d["aa_aimlock_center_strength_mult"] = aa.aimlock_center_strength_mult
        d["aa_aimlock_glue_drift_mult"] = aa.aimlock_glue_drift_mult
        d["aa_aimlock_glue_drift_window_deg"] = aa.aimlock_glue_drift_window_deg
        d["aa_aimlock_lock_timeout_ms"] = aa.aimlock_lock_timeout_ms
        d["aa_aimlock_target_bone"] = aa.aimlock_target_bone
        d["aa_aimlock_head_height_cm"] = aa.aimlock_head_height_cm
        d["aa_aimlock_max_tracking_distance_cm"] = aa.aimlock_max_tracking_distance_cm
        d["aa_aimlock_source"] = aa.aimlock_source
        d["aa_aimlock_proxy_input_min"] = aa.aimlock_proxy_input_min
        d["aa_aimlock_proxy_head_pull_deg"] = aa.aimlock_proxy_head_pull_deg
        d["aa_aimlock_proxy_yaw_gain_deg"] = aa.aimlock_proxy_yaw_gain_deg
        d["aa_aimlock_proxy_assumed_dist_cm"] = aa.aimlock_proxy_assumed_dist_cm
        d["aa_aimlock_proxy_release_ms"] = aa.aimlock_proxy_release_ms
        d["aa_aimlock_kalman_smoothing"] = aa.aimlock_kalman_smoothing
        d["aa_aimlock_velocity_adaptive_boost"] = aa.aimlock_velocity_adaptive_boost
        d["aa_fn_pull_strength"] = aa.fn_pull_strength
        d["aa_fn_slow_strength"] = aa.fn_slow_strength
        d["aa_fn_magnet_force"] = aa.fn_magnet_force
        d["aa_fn_move_pull_boost"] = aa.fn_move_pull_boost
        d["aa_fn_move_soft_magnet_boost"] = aa.fn_move_soft_magnet_boost
        d["aa_fn_move_adhesion_boost"] = aa.fn_move_adhesion_boost
        d["aa_fn_ramp_up_ms"] = aa.fn_ramp_up_ms
        d["aa_fn_camera_threshold"] = aa.fn_camera_threshold
        d["aa_fn_camera_exit"] = aa.fn_camera_exit
        d["aa_headlock_pulse"] = aa.headlock_pulse
        d["aa_headlock_pulse_ms"] = aa.headlock_pulse_ms
        d["aa_headlock_drift_limit"] = aa.headlock_drift_limit
        d["aa_headlock_lock_window"] = aa.headlock_lock_window
        d["aa_head_snap_enabled"] = aa.head_snap_enabled
        d["aa_head_snap_strength"] = aa.head_snap_strength
        d["aa_head_snap_height"] = aa.head_snap_height
        d["aa_head_snap_duration"] = aa.head_snap_duration
        d["aa_head_snap_cooldown"] = aa.head_snap_cooldown
        d["aa_head_snap_smooth"] = aa.head_snap_smooth
        d["aa_head_snap_mode"] = aa.head_snap_mode
        d["aa_head_snap_ads_only"] = aa.head_snap_ads_only
        d["aa_camera_layer_boost"] = aa.camera_layer_boost
        d["aa_ads_lock_boost"] = aa.ads_lock_boost
        d["aa_fire_boost_mult"] = aa.fire_boost_mult
        d["aa_fire_boost_ms"] = aa.fire_boost_ms
        d["aa_rotational_mag_gate"] = aa.rotational_mag_gate
        d["aa_rotational_radius_mult"] = aa.rotational_radius_mult
        d["aa_tweak_zone_enabled"] = aa.tweak_zone_enabled
        d["aa_tweak_zone_pct"] = aa.tweak_zone_pct
        d["aa_tweak_zone_offset"] = aa.tweak_zone_offset
        d["aa_rs_smoothing"] = aa.rs_smoothing
        d["aa_silent_aim_enabled"] = aa.silent_aim_enabled
        d["aa_silent_aim_slow_mult"] = aa.silent_aim_slow_mult
        d["aa_silent_aim_pull_mult"] = aa.silent_aim_pull_mult
        d["aa_silent_aim_shake_blend"] = aa.silent_aim_shake_blend
        d["aa_silent_aim_qt_enabled"] = aa.silent_aim_qt_enabled
        d["aa_silent_aim_intensity"] = aa.silent_aim_intensity
        d["aa_silent_aim_qt_shake_blend"] = aa.silent_aim_qt_shake_blend
        d["aa_silent_hit_enabled"] = aa.silent_hit_enabled
        d["aa_silent_hit_slow_mult"] = aa.silent_hit_slow_mult
        d["aa_silent_hit_pull_mult"] = aa.silent_hit_pull_mult
        d["aa_silent_hit_shake_blend"] = aa.silent_hit_shake_blend
        d["aa_silent_hit_qt_enabled"] = aa.silent_hit_qt_enabled
        d["aa_silent_hit_intensity"] = aa.silent_hit_intensity
        d["aa_silent_hit_qt_shake_blend"] = aa.silent_hit_qt_shake_blend
        d["aa_ls_freq_enabled"] = aa.ls_freq_enabled
        d["aa_ls_freq_amplitude"] = aa.ls_freq_amplitude
        d["aa_ls_freq_frequency"] = aa.ls_freq_frequency
        d["aa_ls_freq_shape"] = aa.ls_freq_shape
        d["aa_ls_freq_gate"] = aa.ls_freq_gate
        d["aa_ls_freq_aggressive"] = aa.ls_freq_aggressive
        d["aa_multi_polar_enabled"] = aa.multi_polar_enabled
        d["aa_multi_polar_close_enabled"] = aa.multi_polar_close_enabled
        d["aa_multi_polar_close_radius"] = aa.multi_polar_close_radius
        d["aa_multi_polar_close_angle"] = aa.multi_polar_close_angle
        d["aa_multi_polar_close_shape"] = aa.multi_polar_close_shape
        d["aa_multi_polar_close_fire_boost"] = aa.multi_polar_close_fire_boost
        d["aa_multi_polar_medium_enabled"] = aa.multi_polar_medium_enabled
        d["aa_multi_polar_medium_radius"] = aa.multi_polar_medium_radius
        d["aa_multi_polar_medium_angle"] = aa.multi_polar_medium_angle
        d["aa_multi_polar_medium_shape"] = aa.multi_polar_medium_shape
        d["aa_multi_polar_medium_fire_boost"] = aa.multi_polar_medium_fire_boost
        d["aa_multi_polar_long_enabled"] = aa.multi_polar_long_enabled
        d["aa_multi_polar_long_radius"] = aa.multi_polar_long_radius
        d["aa_multi_polar_long_angle"] = aa.multi_polar_long_angle
        d["aa_multi_polar_long_shape"] = aa.multi_polar_long_shape
        d["aa_multi_polar_long_fire_boost"] = aa.multi_polar_long_fire_boost
        d["aa_multi_polar_sniper_enabled"] = aa.multi_polar_sniper_enabled
        d["aa_multi_polar_sniper_radius"] = aa.multi_polar_sniper_radius
        d["aa_multi_polar_sniper_angle"] = aa.multi_polar_sniper_angle
        d["aa_multi_polar_sniper_shape"] = aa.multi_polar_sniper_shape
        d["aa_multi_polar_sniper_fire_boost"] = aa.multi_polar_sniper_fire_boost
        d["aa_multi_polar_sniper_ads_only"] = aa.multi_polar_sniper_ads_only
        d["aa_ghost_tracker_enabled"] = aa.ghost_tracker_enabled
        d["aa_ghost_tracker_bubble_radius"] = aa.ghost_tracker_bubble_radius
        d["aa_ghost_tracker_decel_strength"] = aa.ghost_tracker_decel_strength
        d["aa_ghost_tracker_decel_ramp"] = aa.ghost_tracker_decel_ramp
        d["aa_ghost_tracker_stick_threshold"] = aa.ghost_tracker_stick_threshold
        d["aa_burst_mode_enabled"] = aa.burst_mode_enabled
        d["aa_burst_mode_count"] = aa.burst_mode_count
        d["aa_burst_mode_aim_boost"] = aa.burst_mode_aim_boost
        d["aa_burst_mode_recoil_reduction"] = aa.burst_mode_recoil_reduction
        d["aa_burst_mode_cooldown_ms"] = aa.burst_mode_cooldown_ms
        d["aa_batts_sticky_enabled"] = aa.batts_sticky_enabled
        d["aa_batts_sticky_ads_size"] = aa.batts_sticky_ads_size
        d["aa_batts_sticky_ads_fire_size"] = aa.batts_sticky_ads_fire_size
        d["aa_batts_sticky_hipfire_size"] = aa.batts_sticky_hipfire_size
        d["aa_batts_sticky_ads_speed"] = aa.batts_sticky_ads_speed
        d["aa_batts_sticky_ads_fire_speed"] = aa.batts_sticky_ads_fire_speed
        d["aa_batts_sticky_hipfire_speed"] = aa.batts_sticky_hipfire_speed
        d["aa_batts_sticky_drift_enabled"] = aa.batts_sticky_drift_enabled
        d["aa_batts_sticky_drift_strength"] = aa.batts_sticky_drift_strength
        d["aa_xanax_ai_enabled"] = aa.xanax_ai_enabled
        d["aa_xanax_ai_synergy_boost"] = aa.xanax_ai_synergy_boost
        d["aa_xanax_ai_synergy_threshold"] = aa.xanax_ai_synergy_threshold
        d["aa_xanax_ai_close_range_boost"] = aa.xanax_ai_close_range_boost
        d["aa_xanax_ai_long_range_boost"] = aa.xanax_ai_long_range_boost
        d["aa_xanax_ai_close_range_threshold"] = aa.xanax_ai_close_range_threshold
        d["aa_xanax_ai_long_range_threshold"] = aa.xanax_ai_long_range_threshold
        d["aa_xanax_ai_humanize"] = aa.xanax_ai_humanize
        d["aa_xanax_ai_humanize_jitter"] = aa.xanax_ai_humanize_jitter
        d["aa_xanax_ai_adapt_rate"] = aa.xanax_ai_adapt_rate
        d["aa_wz_vibration_enabled"] = aa.wz_vibration_enabled
        d["aa_wz_vibration_intensity"] = aa.wz_vibration_intensity
        d["aa_wz_vibration_frequency"] = aa.wz_vibration_frequency
        d["aa_wz_vibration_amplitude"] = aa.wz_vibration_amplitude
        d["aa_wz_vibration_ads_only"] = aa.wz_vibration_ads_only
        d["aa_wz_vibration_fire_only"] = aa.wz_vibration_fire_only
        d["aa_wz_buffer_enabled"] = aa.wz_buffer_enabled
        d["aa_wz_buffer_tracking_enabled"] = aa.wz_buffer_tracking_enabled
        d["aa_wz_buffer_tracking_strength"] = aa.wz_buffer_tracking_strength
        d["aa_wz_buffer_tracking_radius"] = aa.wz_buffer_tracking_radius
        d["aa_wz_buffer_sticky_enabled"] = aa.wz_buffer_sticky_enabled
        d["aa_wz_buffer_sticky_strength"] = aa.wz_buffer_sticky_strength
        d["aa_wz_buffer_sticky_radius"] = aa.wz_buffer_sticky_radius
        d["aa_wz_buffer_rotation_enabled"] = aa.wz_buffer_rotation_enabled
        d["aa_wz_buffer_rotation_radius"] = aa.wz_buffer_rotation_radius
        d["aa_wz_buffer_rotation_speed"] = aa.wz_buffer_rotation_speed
        d["aa_wz_buffer_fire_boost"] = aa.wz_buffer_fire_boost
        d["aa_wz_buffer_ads_only"] = aa.wz_buffer_ads_only
        d["aa_wz_rapid_enabled"] = aa.wz_rapid_enabled
        d["aa_wz_rapid_speed"] = aa.wz_rapid_speed
        d["aa_wz_rapid_hold_ms"] = aa.wz_rapid_hold_ms
        d["aa_wz_rapid_release_ms"] = aa.wz_rapid_release_ms
        d["aa_wz_rapid_burst_mode"] = aa.wz_rapid_burst_mode
        d["aa_wz_rapid_burst_count"] = aa.wz_rapid_burst_count
        d["aa_wz_rapid_burst_pause_ms"] = aa.wz_rapid_burst_pause_ms
        d["aa_wz_rapid_ads_only"] = aa.wz_rapid_ads_only
        d["aa_wz_rapid_anti_recoil"] = aa.wz_rapid_anti_recoil
        d["aa_wz_rapid_anti_recoil_strength"] = aa.wz_rapid_anti_recoil_strength
        # Precision Buffer (DS4 Fluid)
        d["aa_precision_tracking_enabled"] = aa.precision_tracking_enabled
        d["aa_precision_tracking_smooth"] = aa.precision_tracking_smooth
        d["aa_precision_tracking_strength"] = aa.precision_tracking_strength
        d["aa_precision_tracking_deadzone"] = aa.precision_tracking_deadzone
        d["aa_precision_anti_jitter_enabled"] = aa.precision_anti_jitter_enabled
        d["aa_precision_anti_jitter_strength"] = aa.precision_anti_jitter_strength
        d["aa_precision_anti_jitter_adaptive"] = aa.precision_anti_jitter_adaptive
        d["aa_precision_stick_smooth_enabled"] = aa.precision_stick_smooth_enabled
        d["aa_precision_stick_smooth_factor"] = aa.precision_stick_smooth_factor
        d["aa_precision_stick_smooth_response"] = aa.precision_stick_smooth_response
        d["aa_precision_aim_smooth_enabled"] = aa.precision_aim_smooth_enabled
        d["aa_precision_aim_smooth_factor"] = aa.precision_aim_smooth_factor
        d["aa_precision_aim_smooth_ads_boost"] = aa.precision_aim_smooth_ads_boost
        d["use_optimized_pipeline"] = aa.use_optimized_pipeline
        d["aa_kernel_aim_beta"] = aa.kernel_aim_beta
        d["aa_kernel_aim_blend"] = aa.kernel_aim_blend
        d["aa_kernel_aim_snappiness"] = aa.kernel_aim_snappiness
        d["aa_kernel_aim_smoothing_rate"] = aa.kernel_aim_smoothing_rate
        d["aa_kernel_aim_pull_max_rate_deg_s"] = aa.kernel_aim_pull_max_rate_deg_s
        d["aa_kernel_aim_fov_degrees"] = aa.kernel_aim_fov_degrees
        d["aa_kernel_aim_head_pull_deg"] = aa.kernel_aim_head_pull_deg
        d["aa_kernel_aim_min_input"] = aa.kernel_aim_min_input
        d["optimized_rotational_speed"] = aa.optimized_rotational_speed
        d["optimized_rotational_radius_mult"] = aa.optimized_rotational_radius_mult
        d["optimized_predictive_enabled"] = aa.optimized_predictive_enabled
        d["optimized_predictive_vel_alpha"] = aa.optimized_predictive_vel_alpha
        d["optimized_predictive_accel_alpha"] = aa.optimized_predictive_accel_alpha
        d["optimized_predictive_lead_ms"] = aa.optimized_predictive_lead_ms
        d["optimized_predictive_min_speed"] = aa.optimized_predictive_min_speed
        d["optimized_predictive_max_lead"] = aa.optimized_predictive_max_lead
        d["optimized_predictive_consistency"] = aa.optimized_predictive_consistency
        d["optimized_predictive_kalman_weight"] = aa.optimized_predictive_kalman_weight
        d["optimized_micro_correction_enabled"] = aa.optimized_micro_correction_enabled
        d["optimized_micro_correction_pull"] = aa.optimized_micro_correction_pull
        d["optimized_adaptive_strength_enabled"] = aa.optimized_adaptive_strength_enabled
        d["auto_tuning_enabled"] = aa.auto_tuning_enabled
        d["auto_tuning_min_mult"] = aa.auto_tuning_min_mult
        d["auto_tuning_max_mult"] = aa.auto_tuning_max_mult
        d["auto_tuning_cooldown"] = aa.auto_tuning_cooldown
        d["aa_anti_recoil_ml_enabled"] = aa.anti_recoil_ml_enabled
        d["aa_anti_recoil_ml_strength"] = aa.anti_recoil_ml_strength
        d["aa_anti_recoil_ml_learning_rate"] = aa.anti_recoil_ml_learning_rate
        d["aa_ballistic_predictor_enabled"] = aa.ballistic_predictor_enabled
        d["aa_ballistic_predictor_strength"] = aa.ballistic_predictor_strength
        d["aa_ballistic_predictor_gravity"] = aa.ballistic_predictor_gravity
        d["aa_smart_headshot_enabled"] = aa.smart_headshot_enabled
        d["aa_smart_headshot_strength"] = aa.smart_headshot_strength
        d["aa_smart_headshot_max_pull"] = aa.smart_headshot_max_pull
        d["aa_kbm_mode"] = aa.kbm_mode
        d["aa_kbm_scale"] = aa.kbm_scale
        d["aa_fn_humanize"] = aa.fn_humanize
        d["aa_oef_enabled"] = aa.oef_enabled
        d["aa_oef_min_cutoff"] = aa.oef_min_cutoff
        d["aa_oef_beta"] = aa.oef_beta
        d["aa_oef_d_cutoff"] = aa.oef_d_cutoff
        d["aa_predictive_tracker_enabled"] = aa.predictive_tracker_enabled
        d["aa_predictive_vel_alpha"] = aa.predictive_vel_alpha
        d["aa_predictive_accel_alpha"] = aa.predictive_accel_alpha
        d["aa_predictive_lead_horizon_ms"] = aa.predictive_lead_horizon_ms
        d["aa_predictive_min_speed"] = aa.predictive_min_speed
        d["aa_predictive_max_lead"] = aa.predictive_max_lead
        d["aa_predictive_consistency"] = aa.predictive_consistency
        d["aa_predictive_direction_blend"] = aa.predictive_direction_blend
        d["aa_adhesion_buffer_enabled"] = aa.adhesion_buffer_enabled
        d["aa_adhesion_hold_ms"] = aa.adhesion_hold_ms
        d["aa_adhesion_decay"] = aa.adhesion_decay
        d["aa_adhesion_axis_lock"] = aa.adhesion_axis_lock
        d["aa_adhesion_min_mag"] = aa.adhesion_min_mag
        d["aa_follow_assist_enabled"] = aa.follow_assist_enabled
        d["aa_follow_assist_pull"] = aa.follow_assist_pull
        d["aa_strafe_shot_enabled"] = aa.strafe_shot_enabled
        d["aa_strafe_shot_amplitude"] = aa.strafe_shot_amplitude
        d["aa_strafe_shot_frequency"] = aa.strafe_shot_frequency
        d["aa_strafe_shot_shape"] = aa.strafe_shot_shape
        d["aa_neural_enabled"] = aa.neural_enabled
        d["aa_neural_kalman_noise"] = aa.neural_kalman_noise
        d["aa_neural_kalman_lead_ms"] = aa.neural_kalman_lead_ms
        d["aa_neural_kalman_weight"] = aa.neural_kalman_weight
        d["aa_neural_micro_enabled"] = aa.neural_micro_enabled
        d["aa_neural_micro_amplitude"] = aa.neural_micro_amplitude
        d["aa_neural_confidence_scale"] = aa.neural_confidence_scale
        d["aa_neural_harmonizer_enabled"] = aa.neural_harmonizer_enabled
        d["aa_neural_error_feedback_enabled"] = aa.neural_error_feedback_enabled

        rc = self.recoil
        d["recoil_enabled"] = rc.enabled
        d["recoil_strength"] = rc.strength
        d["recoil_x_strength"] = rc.x_strength
        d["recoil_ticks"] = rc.ticks
        d["recoil_delay"] = rc.delay_ms
        d["recoil_return_speed"] = rc.return_speed
        d["recoil_curve"] = rc.curve
        d["recoil_y_gate"] = rc.y_gate
        d["recoil_adapt"] = rc.recoil_adapt
        d["recoil_smart_learn"] = rc.smart_learn
        d["recoil_simple_mode"] = rc.simple_mode
        d["recoil_simple_rate"] = rc.simple_rate

        rr = self.recoil_runtime
        d["recoil_active_preset"] = rr.active_preset
        d["sens_y_mult"] = rr.sens_y_mult
        d["scope_toggle_key"] = rr.scope_toggle_key
        d["scope_enabled"] = rr.scope_enabled
        d["recoil_is_scoped"] = rr.is_scoped
        d["recoil_burst_mode"] = rr.burst_mode
        d["recoil_burst_count"] = rr.burst_count
        d["recoil_burst_delay"] = rr.burst_delay_ms
        d["recoil_horizontal_pull"] = rr.horizontal_pull
        d["recoil_loadout_slots"] = list(rr.loadout_slots)
        d["recoil_smoothing"] = rr.smoothing

        rf = self.rapid_fire
        d["remap_rapid_fire"] = rf.enabled
        d["remap_rf_speed"] = rf.speed
        d["remap_rf_hold_ms"] = rf.hold_ms
        d["remap_rf_release_ms"] = rf.release_ms
        d["remap_rf_trigger"] = rf.trigger_button
        d["remap_rf_toggle_key"] = rf.toggle_key
        d["remap_rf_mode"] = rf.mode
        d["remap_rf_hold_ratio"] = rf.hold_ratio

        br = self.bloom_reducer
        d["remap_bloom_reducer"] = br.enabled
        d["remap_br_shots"] = br.burst_shots
        d["remap_br_hold_ms"] = br.hold_ms
        d["remap_br_tap_ms"] = br.tap_gap_ms
        d["remap_br_reset_ms"] = br.reset_ms
        d["remap_br_trigger"] = br.trigger_button
        d["remap_br_toggle_key"] = br.toggle_key

        cs = self.crouch_spam
        d["remap_crouch_spam"] = cs.enabled
        d["remap_cs_speed"] = cs.speed
        d["remap_cs_hold_ms"] = cs.hold_ms
        d["remap_cs_release_ms"] = cs.release_ms
        d["remap_cs_button"] = cs.crouch_button
        d["remap_cs_only_shooting"] = cs.only_while_shooting
        d["remap_cs_toggle_key"] = cs.toggle_key

        d["remap_kbd_path"] = self.remap_kbd_path
        d["remap_mouse_path"] = self.remap_mouse_path
        d["remap_active"] = self.remap_active
        d["remap_mouse_sens"] = self.mouse_sens
        d["remap_sens_x"] = self.sens_x
        d["remap_sens_y"] = self.sens_y
        d["remap_curve"] = self.mouse_curve
        d["remap_smooth"] = self.mouse_smooth
        d["remap_min_output"] = self.mouse_min_output
        d["remap_square_stick"] = self.square_stick
        d["kbd_bindings"] = self.kbd_bindings
        d["controller_hardware"] = self.controller_hardware.to_dict()

        sz = self.sniper_zoom
        d["sniper_zoom_enabled"] = sz.enabled
        d["sniper_zoom_button"] = sz.button
        d["sniper_zoom_factor"] = sz.zoom_factor
        d["sniper_zoom_window_width"] = sz.window_width
        d["sniper_zoom_window_height"] = sz.window_height
        d["sniper_zoom_fixed_pos"] = sz.fixed_position
        d["sniper_zoom_fixed_x"] = sz.fixed_x
        d["sniper_zoom_fixed_y"] = sz.fixed_y

        sc = self.slide_cancel
        d["slide_cancel_enabled"] = sc.enabled
        d["slide_cancel_jump_arc_ms"] = sc.jump_arc_ms
        d["slide_cancel_crouch_hold_ms"] = sc.crouch_hold_ms
        d["slide_cancel_jump_hold_ms"] = sc.jump_hold_ms
        d["slide_cancel_cooldown_ms"] = sc.cooldown_ms
        d["slide_cancel_crouch_btn"] = hex(sc.crouch_button_code)
        d["slide_cancel_jump_btn"] = hex(sc.jump_button_code)
        d["slide_cancel_toggle_key"] = sc.toggle_key

        mt = self.movement_tech
        if mt is None:
            mt = MovementTechConfig()
        d["remap_dodge_shot"] = mt.dodge_shot_enabled
        d["remap_dodge_hold_ms"] = mt.dodge_hold_ms
        d["remap_dodge_release_ms"] = mt.dodge_release_ms
        d["remap_slide_cancel"] = mt.slide_cancel_enabled
        d["remap_slide_tap_ms"] = mt.slide_tap_ms
        d["remap_slide_gap_ms"] = mt.slide_gap_ms
        d["remap_bunny_hop"] = mt.bunny_hop_enabled
        d["remap_bunny_hold_ms"] = mt.bunny_hold_ms
        d["remap_bunny_gap_ms"] = mt.bunny_gap_ms
        d["remap_mv_crouch_btn"] = hex(mt.crouch_button_code)
        d["remap_mv_jump_btn"] = hex(mt.jump_button_code)

        ca = self.crouch_aim
        if ca is None:
            ca = CrouchAimConfig()
        d["remap_crouch_aim"] = ca.enabled
        d["remap_ca_button"] = hex(ca.button_code)

        return d
