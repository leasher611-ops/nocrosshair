from __future__ import annotations

import json
import os
from typing import Any, Optional

from evdev import InputDevice, ecodes as e

from nocrosshair.controllers.base import ControllerHardware
from nocrosshair.controllers.descriptor import ControllerDescriptor
from nocrosshair.controllers.g7_pro_8k import G7Pro8K
from nocrosshair.controllers.cyclone_2 import Cyclone2
from nocrosshair.controllers.ds4 import DS4
from nocrosshair.controllers.dualsense_edge import DualSenseEdge
from nocrosshair.controllers.xbox360 import Xbox360


class ControllerRegistry:

    def __init__(self) -> None:
        self._hardware: dict[str, type[ControllerHardware]] = {}
        self._profiles_path: str = os.path.expanduser(
            "~/.config/nocrosshair/controller_profiles"
        )

    def register(self, hw_class: type[ControllerHardware]) -> None:
        desc = hw_class().descriptor
        self._hardware[desc.id] = hw_class

    def get(self, hw_id: str) -> type[ControllerHardware]:
        if hw_id not in self._hardware:
            raise KeyError(f"Unknown controller hardware: {hw_id}")
        return self._hardware[hw_id]

    def list_available(self) -> list[ControllerDescriptor]:
        return [cls().descriptor for cls in self._hardware.values()]

    def get_descriptor(self, hw_id: str) -> ControllerDescriptor:
        return self.get(hw_id)().descriptor

    def detect_physical(self, device_path: str) -> Optional[str]:
        try:
            dev = InputDevice(device_path)
        except (FileNotFoundError, PermissionError, OSError):
            return None

        vid = dev.info.vendor
        pid = dev.info.product

        for hw_id, hw_class in self._hardware.items():
            desc = hw_class().descriptor
            if desc.vid_pid == (vid, pid):
                return hw_id

        return None

    def load_profile(self, hw_id: str) -> Optional[dict[str, Any]]:
        path = os.path.join(self._profiles_path, f"{hw_id}.json")
        if not os.path.isfile(path):
            return None
        try:
            with open(path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError, PermissionError):
            return None

    def save_profile(self, hw_id: str, config: dict[str, Any]) -> bool:
        os.makedirs(self._profiles_path, exist_ok=True)
        path = os.path.join(self._profiles_path, f"{hw_id}.json")
        try:
            with open(path, "w") as f:
                json.dump(config, f, indent=2)
            return True
        except (OSError, PermissionError, TypeError):
            return False


registry = ControllerRegistry()
registry.register(G7Pro8K)
registry.register(Cyclone2)
registry.register(DS4)
registry.register(DualSenseEdge)
registry.register(Xbox360)
