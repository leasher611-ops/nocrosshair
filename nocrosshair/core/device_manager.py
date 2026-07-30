import threading
import os
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field

from evdev import InputDevice, ecodes as e

from nocrosshair.core.config import ControllerType
from nocrosshair.core.controller import VirtualController


@dataclass
class DeviceSlot:
    name: str
    ctrl_type: str = "xbox360"
    virtual_controller: Optional[VirtualController] = None
    physical_device_path: Optional[str] = None
    assigned: bool = False

    def get_info(self) -> dict:
        return {
            "name": self.name,
            "type": self.ctrl_type,
            "assigned": self.assigned,
            "physical_device": self.physical_device_path,
            "virtual_ready": self.virtual_controller is not None and self.virtual_controller.device is not None,
        }


class VirtualDeviceManager:

    def __init__(self):
        self._slots: Dict[str, DeviceSlot] = {}
        self._lock = threading.Lock()

    def create_device(self, slot_name: str, ctrl_type: str = "xbox360") -> Optional[VirtualController]:
        with self._lock:
            if slot_name in self._slots and self._slots[slot_name].virtual_controller is not None:
                return self._slots[slot_name].virtual_controller

            controller = VirtualController(ctrl_type)
            self._slots[slot_name] = DeviceSlot(
                name=slot_name,
                ctrl_type=ctrl_type,
                virtual_controller=controller,
            )
            return controller

    def remove_device(self, slot_name: str) -> bool:
        with self._lock:
            slot = self._slots.pop(slot_name, None)
            if slot and slot.virtual_controller:
                slot.virtual_controller.close()
                return True
            return False

    def get_device(self, slot_name: str) -> Optional[VirtualController]:
        with self._lock:
            slot = self._slots.get(slot_name)
            return slot.virtual_controller if slot else None

    def list_devices(self) -> List[dict]:
        with self._lock:
            return [s.get_info() for s in self._slots.values()]

    def assign_physical(self, slot_name: str, device_path: str) -> bool:
        with self._lock:
            slot = self._slots.get(slot_name)
            if not slot:
                return False
            slot.physical_device_path = device_path
            slot.assigned = True
            return True

    def release_physical(self, slot_name: str) -> bool:
        with self._lock:
            slot = self._slots.get(slot_name)
            if not slot:
                return False
            slot.physical_device_path = None
            slot.assigned = False
            return True

    def get_slot_info(self, slot_name: str) -> Optional[dict]:
        with self._lock:
            slot = self._slots.get(slot_name)
            return slot.get_info() if slot else None

    def shutdown_all(self) -> None:
        with self._lock:
            for slot in self._slots.values():
                if slot.virtual_controller:
                    slot.virtual_controller.close()
            self._slots.clear()


device_manager = VirtualDeviceManager()
