from __future__ import annotations

from evdev import ecodes as e, AbsInfo

from nocrosshair.controllers.base import ControllerHardware
from nocrosshair.controllers.descriptor import ControllerDescriptor


_CYCLONE_2_DESCRIPTOR = ControllerDescriptor(
    id="cyclone_2",
    name="Cyclone 2",
    manufacturer="GAMESIR",
    polling_rate_hz=1000,
    connection_types=["wired", "wireless"],
    joystick_type="tmr",
    joystick_resolution_bits=12,
    joystick_count=2,
    anti_drift=True,
    trigger_type="hall_effect_hybrid",
    trigger_count=2,
    has_trigger_stops=True,
    trigger_stops_mechanical=True,
    has_gyro=True,
    gyro_axes=6,
    has_rumble=True,
    has_rgb=True,
    rgb_zones=2,
    has_dock=True,
    has_headphone_jack=False,
    has_extra_buttons=True,
    extra_button_count=3,
    battery_capacity_mah=860,
    weight_g=195.0,
    dimensions_mm=(140.0, 95.0, 55.0),
    vid_pid=(0x3534, 0x1002),
    uinput_name="Cyclone 2",
    uinput_vendor=0x3534,
    uinput_product=0x1002,
    uinput_version=0x0100,
    raw_capabilities=[
        "EV_KEY", "EV_ABS",
        "ABS_X", "ABS_Y", "ABS_RX", "ABS_RY", "ABS_Z", "ABS_RZ",
        "ABS_HAT0X", "ABS_HAT0Y",
        "ABS_RX", "ABS_RY", "ABS_RZ",
        "BTN_A", "BTN_B", "BTN_X", "BTN_Y",
        "BTN_TL", "BTN_TR", "BTN_SELECT", "BTN_START",
        "BTN_THUMBL", "BTN_THUMBR", "BTN_MODE",
        "BTN_TR2", "BTN_TL2",
    ],
)


class Cyclone2(ControllerHardware):

    def __init__(self) -> None:
        super().__init__(_CYCLONE_2_DESCRIPTOR)

    def create_uinput_device(self) -> tuple[int, int, int, int]:
        return (
            self.descriptor.uinput_vendor,
            self.descriptor.uinput_product,
            self.descriptor.uinput_version,
            0x0003,
        )

    def get_capabilities(self) -> dict[int, list]:
        flat = 0
        max_analog = 1023
        return {
            e.EV_KEY: [
                e.BTN_A, e.BTN_B, e.BTN_X, e.BTN_Y,
                e.BTN_TL, e.BTN_TR,
                e.BTN_SELECT, e.BTN_START,
                e.BTN_THUMBL, e.BTN_THUMBR,
                e.BTN_MODE,
                e.BTN_TR2, e.BTN_TL2,
            ],
            e.EV_ABS: [
                (e.ABS_X, AbsInfo(flat, -32768, 32767, 0, 15, 0)),
                (e.ABS_Y, AbsInfo(flat, -32768, 32767, 0, 15, 0)),
                (e.ABS_RX, AbsInfo(flat, -32768, 32767, 0, 15, 0)),
                (e.ABS_RY, AbsInfo(flat, -32768, 32767, 0, 15, 0)),
                (e.ABS_Z, AbsInfo(flat, 0, max_analog, 0, 0, 0)),
                (e.ABS_RZ, AbsInfo(flat, 0, max_analog, 0, 0, 0)),
                (e.ABS_HAT0X, AbsInfo(flat, -1, 1, 0, 0, 0)),
                (e.ABS_HAT0Y, AbsInfo(flat, -1, 1, 0, 0, 0)),
            ],
        }

    @property
    def has_motion_aim(self) -> bool:
        return True

    @property
    def has_dock_detection(self) -> bool:
        return True

    @property
    def has_rgb_control(self) -> bool:
        return True

    @property
    def polling_rate_class(self) -> str:
        return "1k"

    def get_trigger_threshold(self) -> int:
        return 0
