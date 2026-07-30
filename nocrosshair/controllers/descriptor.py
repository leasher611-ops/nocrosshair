from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class ControllerDescriptor:
    id: str
    name: str
    manufacturer: str
    polling_rate_hz: int
    connection_types: list[str]
    joystick_type: str
    joystick_resolution_bits: int
    joystick_count: int
    anti_drift: bool
    trigger_type: str
    trigger_count: int
    has_trigger_stops: bool
    trigger_stops_mechanical: bool
    has_gyro: bool
    gyro_axes: int
    has_rumble: bool
    has_rgb: bool
    rgb_zones: int
    has_dock: bool
    has_headphone_jack: bool
    has_extra_buttons: bool
    extra_button_count: int
    battery_capacity_mah: int
    weight_g: float
    dimensions_mm: tuple[float, float, float]
    vid_pid: tuple[int, int]
    uinput_name: str
    uinput_vendor: int
    uinput_product: int
    uinput_version: int
    raw_capabilities: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["dimensions_mm"] = list(self.dimensions_mm)
        d["vid_pid"] = list(self.vid_pid)
        return d

    @staticmethod
    def from_dict(d: dict[str, Any]) -> ControllerDescriptor:
        raw = dict(d)
        raw["dimensions_mm"] = tuple(raw["dimensions_mm"])
        raw["vid_pid"] = tuple(raw["vid_pid"])
        return ControllerDescriptor(**raw)
