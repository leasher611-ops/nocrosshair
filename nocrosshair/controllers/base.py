from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from nocrosshair.controllers.descriptor import ControllerDescriptor


class ControllerHardware(ABC):

    descriptor: ControllerDescriptor

    def __init__(self, descriptor: ControllerDescriptor) -> None:
        self.descriptor = descriptor

    @abstractmethod
    def create_uinput_device(self) -> tuple[int, int, int, int]:
        raise NotImplementedError

    @abstractmethod
    def get_capabilities(self) -> dict[int, list[Any]]:
        raise NotImplementedError

    def get_polling_interval_ns(self) -> int:
        return int(1_000_000_000 / self.descriptor.polling_rate_hz)

    def get_joystick_deadzone(self) -> int:
        max_val = (1 << self.descriptor.joystick_resolution_bits) - 1
        return int(max_val * 0.05)

    def get_trigger_threshold(self) -> int:
        return 0
