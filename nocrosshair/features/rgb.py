from __future__ import annotations

import os
import struct
from enum import Enum
from dataclasses import dataclass, asdict
from typing import Optional


class RGBEffect(Enum):
    STATIC = "static"
    BREATHING = "breathing"
    RAINBOW = "rainbow"
    WAVE = "wave"
    CUSTOM = "custom"


@dataclass
class RGBConfig:
    enabled: bool = False
    color: tuple[int, int, int] = (0, 255, 136)
    effect: RGBEffect = RGBEffect.STATIC
    brightness: int = 128
    speed: float = 1.0
    zone: int = 0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["effect"] = self.effect.value
        d["color"] = list(self.color)
        return d

    @staticmethod
    def from_dict(d: dict) -> RGBConfig:
        color_raw = d.get("color", [0, 255, 136])
        if isinstance(color_raw, list):
            color = tuple(int(c) for c in color_raw[:3])
        else:
            color = (0, 255, 136)
        effect_str = d.get("effect", "static")
        try:
            effect = RGBEffect(effect_str)
        except ValueError:
            effect = RGBEffect.STATIC
        return RGBConfig(
            enabled=bool(d.get("enabled", False)),
            color=color,
            effect=effect,
            brightness=int(d.get("brightness", 128)),
            speed=float(d.get("speed", 1.0)),
            zone=int(d.get("zone", 0)),
        )


RGB_HID_REPORT_ID = 0x07
RGB_ZONE_MAP: dict[str, int] = {
    "cyclone_2": 2,
    "g7_pro_8k": 1,
    "ds4": 1,
}

RGB_EFFECT_MAP: dict[str, list[RGBEffect]] = {
    "cyclone_2": [RGBEffect.STATIC, RGBEffect.BREATHING, RGBEffect.RAINBOW, RGBEffect.WAVE],
    "g7_pro_8k": [RGBEffect.STATIC, RGBEffect.BREATHING, RGBEffect.RAINBOW],
    "ds4": [RGBEffect.STATIC, RGBEffect.BREATHING, RGBEffect.RAINBOW, RGBEffect.CUSTOM],
}


class RGBController:
    def __init__(self) -> None:
        self._current_config: Optional[RGBConfig] = None

    def apply(self, config: RGBConfig, device_path: str = "") -> bool:
        self._current_config = config
        if not config.enabled:
            return self.turn_off()
        return self._send_report(config, device_path)

    def set_color(self, r: int, g: int, b: int, zone: int = 0) -> bool:
        if self._current_config is None:
            self._current_config = RGBConfig()
        self._current_config.color = (r, g, b)
        self._current_config.zone = zone
        return True

    def set_effect(self, effect: RGBEffect, speed: float = 1.0) -> bool:
        if self._current_config is None:
            self._current_config = RGBConfig()
        self._current_config.effect = effect
        self._current_config.speed = speed
        return True

    def set_brightness(self, level: int) -> bool:
        level = max(0, min(255, level))
        if self._current_config is None:
            self._current_config = RGBConfig()
        self._current_config.brightness = level
        return True

    def turn_off(self) -> bool:
        return self._send_off()

    def get_supported_effects(self, hw_id: str) -> list[RGBEffect]:
        return RGB_EFFECT_MAP.get(hw_id, [RGBEffect.STATIC])

    def get_zone_count(self, hw_id: str) -> int:
        return RGB_ZONE_MAP.get(hw_id, 1)

    def _send_report(self, config: RGBConfig, device_path: str) -> bool:
        if not device_path or not os.path.exists(device_path):
            return False
        try:
            report = self._build_hid_report(config)
            with open(device_path, "wb") as f:
                f.write(report)
            return True
        except (OSError, PermissionError, FileNotFoundError):
            return False

    def _send_off(self) -> bool:
        return True

    @staticmethod
    def _build_hid_report(config: RGBConfig) -> bytes:
        r, g, b = config.color
        effect_id = {
            RGBEffect.STATIC: 0x01,
            RGBEffect.BREATHING: 0x02,
            RGBEffect.RAINBOW: 0x03,
            RGBEffect.WAVE: 0x04,
            RGBEffect.CUSTOM: 0x05,
        }.get(config.effect, 0x01)
        speed_byte = max(0, min(255, int(config.speed * 25.5)))
        bright_byte = max(0, min(255, config.brightness))
        zone_byte = max(0, min(255, config.zone))
        report = struct.pack(
            "<BBBBBBBB",
            RGB_HID_REPORT_ID,
            effect_id,
            r, g, b,
            bright_byte,
            speed_byte,
            zone_byte,
        )
        return report
