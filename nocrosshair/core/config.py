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
    "aa_auto_track_multiplier": 0.6,
    "aa_auto_track_persistence_ms": 60,
    "aa_auto_track_threshold": 20,
    "aa_zone": 5000,

    "remap_rapid_fire": False,
    "remap_rf_speed": 50,
    "remap_crouch_spam": False,
    "remap_cs_speed": 60,

    "recoil_enabled": False,
    "recoil_strength": 65,
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

CONTROLLER_TYPES = ["xbox360", "xboxone", "dualshock3", "dualshock4", "switchpro"]
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
    strength: int = 65
    x_strength: int = 0
    ticks: int = 60
    delay_ms: int = 45
    return_speed: float = 0.7
    curve: str = "ease_out"
    y_gate: bool = True
    recoil_adapt: int = 0
    smart_learn: bool = False

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "RecoilConfig":
        return RecoilConfig(
            enabled=d.get("recoil_enabled", d.get("enabled", False)),
            strength=int(d.get("recoil_strength", 65)),
            x_strength=int(d.get("recoil_x_strength", 0)),
            ticks=int(d.get("recoil_ticks", 60)),
            delay_ms=int(d.get("recoil_delay", 45)),
            return_speed=float(d.get("recoil_return_speed", 0.7)),
            curve=d.get("recoil_curve", "ease_out"),
            y_gate=d.get("recoil_y_gate", True),
            recoil_adapt=int(d.get("recoil_adapt", 0)),
            smart_learn=d.get("recoil_smart_learn", False),
        )

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
    long_range_predict_lead: int = 2000
    prediction_frames: int = 3
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
    fn_ramp_up_ms: float = 150.0
    fn_camera_threshold: float = 18000.0
    fn_camera_exit: float = 14000.0
    fn_layer_strength: float = 1.0
    auto_track_enabled: bool = True
    auto_track_multiplier: float = 0.6
    auto_track_persistence_ms: float = 60.0
    auto_track_threshold: int = 20

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "AimAssistConfig":
        return AimAssistConfig(
            enabled=d.get("remap_aa_enabled", True),
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
            long_range_predict_lead=int(d.get("aa_long_range_predict_lead", 2000)),
            prediction_frames=int(d.get("aa_prediction_frames", 3)),
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
            fn_ramp_up_ms=float(d.get("aa_fn_ramp_up_ms", 150.0)),
            fn_camera_threshold=float(d.get("aa_fn_camera_threshold", 18000.0)),
            fn_camera_exit=float(d.get("aa_fn_camera_exit", 14000.0)),
            fn_layer_strength=float(d.get("aa_fn_layer_strength", 1.0)),
            auto_track_enabled=d.get("aa_auto_track_enabled", True),
            auto_track_multiplier=float(d.get("aa_auto_track_multiplier", 0.6)),
            auto_track_persistence_ms=float(d.get("aa_auto_track_persistence_ms", 60.0)),
            auto_track_threshold=int(d.get("aa_auto_track_threshold", 20)),
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

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "RapidFireConfig":
        return RapidFireConfig(
            enabled=d.get("remap_rapid_fire", False),
            speed=int(d.get("remap_rf_speed", 50)),
            hold_ms=int(d.get("remap_rf_hold_ms", 10)),
            release_ms=int(d.get("remap_rf_release_ms", 10)),
            trigger_button=d.get("remap_rf_trigger", "RT"),
            toggle_key=d.get("remap_rf_toggle_key", "KEY_F9"),
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
    ls_physics: StickPhysicsConfig = None
    rs_physics: StickPhysicsConfig = None
    lt_physics: TriggerPhysicsConfig = None
    rt_physics: TriggerPhysicsConfig = None
    aim_assist: AimAssistConfig = None
    recoil: RecoilConfig = None
    recoil_runtime: RecoilRuntimeConfig = None
    rapid_fire: RapidFireConfig = None
    crouch_spam: CrouchSpamConfig = None
    sniper_zoom: SniperZoomConfig = None
    slide_cancel: SlideCancelConfig = None
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
        if self.crouch_spam is None:
            self.crouch_spam = CrouchSpamConfig()
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
            ls_physics=AdvancedStickPhysicsConfig.from_dict(d, "ls_"),
            rs_physics=AdvancedStickPhysicsConfig.from_dict(d, "rs_"),
            lt_physics=TriggerPhysicsConfig.from_dict(d, "lt_"),
            rt_physics=TriggerPhysicsConfig.from_dict(d, "rt_"),
            aim_assist=AimAssistConfig.from_dict(d),
            recoil=RecoilConfig.from_dict(d),
            recoil_runtime=RecoilRuntimeConfig.from_dict(d),
            rapid_fire=RapidFireConfig.from_dict(d),
            crouch_spam=CrouchSpamConfig.from_dict(d),
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
            kbd_bindings=bindings,
            controller_hardware=controller_hardware,
        )

    def to_dict(self) -> Dict[str, Any]:
        def _fields(obj):
            return {f.name: getattr(obj, f.name) for f in obj.__dataclass_fields__.values()}

        d: Dict[str, Any] = {"remap_controller": self.controller_type}
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
        d["aa_prediction_frames"] = aa.prediction_frames
        d["aa_anti_shake_blend"] = aa.anti_shake_blend
        d["aa_magnetic_pull"] = aa.magnetic_pull
        d["aa_long_range_track_boost"] = aa.long_range_track_boost
        d["aa_long_range_predict_lead"] = aa.long_range_predict_lead
        d["aa_anti_flinch"] = aa.anti_flinch
        d["aa_anti_flinch_strength"] = aa.anti_flinch_strength
        d["aa_zero_delay"] = aa.zero_delay
        d["aa_zero_delay_ms"] = aa.zero_delay_ms
        d["aa_bloom_compensation"] = aa.bloom_compensation
        d["aa_fn_layer_strength"] = aa.fn_layer_strength
        d["aa_auto_track_enabled"] = aa.auto_track_enabled
        d["aa_auto_track_multiplier"] = aa.auto_track_multiplier
        d["aa_auto_track_persistence_ms"] = aa.auto_track_persistence_ms
        d["aa_auto_track_threshold"] = aa.auto_track_threshold
        d["aa_strafe_shot_enabled"] = aa.strafe_shot_enabled
        d["aa_strafe_shot_amplitude"] = aa.strafe_shot_amplitude
        d["aa_strafe_shot_frequency"] = aa.strafe_shot_frequency
        d["aa_strafe_shot_shape"] = aa.strafe_shot_shape

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
        d["recoil_smoothing"] = rr.smoothing

        rf = self.rapid_fire
        d["remap_rapid_fire"] = rf.enabled
        d["remap_rf_speed"] = rf.speed
        d["remap_rf_hold_ms"] = rf.hold_ms
        d["remap_rf_release_ms"] = rf.release_ms
        d["remap_rf_trigger"] = rf.trigger_button
        d["remap_rf_toggle_key"] = rf.toggle_key

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

        return d
