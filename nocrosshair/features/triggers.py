from __future__ import annotations

from enum import Enum
from typing import Optional

from nocrosshair.controllers.descriptor import ControllerDescriptor


class TriggerModeType(Enum):
    ANALOG = "analog"
    DIGITAL = "digital"
    HYBRID = "hybrid"


class TriggerConfig:
    def __init__(
        self,
        mode: TriggerModeType = TriggerModeType.ANALOG,
        stop_position: float = 0.85,
        rapid_trigger_enabled: bool = False,
        rapid_trigger_sensitivity: int = 50,
        analog_deadzone: int = 5,
        analog_max: int = 1023,
    ) -> None:
        self.mode = mode
        self.stop_position = stop_position
        self.rapid_trigger_enabled = rapid_trigger_enabled
        self.rapid_trigger_sensitivity = rapid_trigger_sensitivity
        self.analog_deadzone = analog_deadzone
        self.analog_max = analog_max

    @staticmethod
    def from_dict(d: dict, prefix: str = "trigger_") -> TriggerConfig:
        mode_str = d.get(f"{prefix}mode", "analog")
        try:
            mode = TriggerModeType(mode_str)
        except ValueError:
            mode = TriggerModeType.ANALOG
        return TriggerConfig(
            mode=mode,
            stop_position=float(d.get(f"{prefix}stop_position", 0.85)),
            rapid_trigger_enabled=bool(d.get(f"{prefix}rapid_trigger", False)),
            rapid_trigger_sensitivity=int(d.get(f"{prefix}rapid_sensitivity", 50)),
            analog_deadzone=int(d.get(f"{prefix}deadzone", 5)),
            analog_max=int(d.get(f"{prefix}analog_max", 1023)),
        )

    def to_dict(self) -> dict:
        return {
            "trigger_mode": self.mode.value,
            "trigger_stop_position": self.stop_position,
            "trigger_rapid_trigger": self.rapid_trigger_enabled,
            "trigger_rapid_sensitivity": self.rapid_trigger_sensitivity,
            "trigger_deadzone": self.analog_deadzone,
            "trigger_analog_max": self.analog_max,
        }


class TriggerEngine:
    def __init__(self, config: TriggerConfig, hardware_desc: ControllerDescriptor) -> None:
        self.config = config
        self.hardware = hardware_desc
        self._prev_raw: int = 0
        self._rapid_fired: bool = False

    def process(self, raw_value: int, digital_click: bool = False) -> int:
        mode = self.config.mode

        if mode == TriggerModeType.DIGITAL:
            return 255 if digital_click else 0

        if mode == TriggerModeType.HYBRID:
            if digital_click:
                return 255
            stop = int(self.config.stop_position * self.config.analog_max)
            clamped = max(0, min(raw_value, self.config.analog_max))
            if clamped >= stop:
                return 255
            return self._apply_deadzone(clamped)

        clamped = max(0, min(raw_value, self.config.analog_max))
        return self._apply_deadzone(clamped)

    def detect_rapid_trigger(self, current: int, previous: int) -> bool:
        if not self.config.rapid_trigger_enabled:
            return False
        diff = abs(current - previous)
        threshold = int(self.config.rapid_trigger_sensitivity / 100.0 * self.config.analog_max)
        if diff >= threshold and current < previous:
            self._rapid_fired = True
            return True
        self._rapid_fired = False
        return False

    def reset(self) -> None:
        self._prev_raw = 0
        self._rapid_fired = False

    def _apply_deadzone(self, value: int) -> int:
        if value < self.config.analog_deadzone:
            return 0
        if value > self.config.analog_max:
            return self.config.analog_max
        return value

    @property
    def rapid_fired(self) -> bool:
        return self._rapid_fired

    @property
    def current_mode(self) -> TriggerModeType:
        return self.config.mode
