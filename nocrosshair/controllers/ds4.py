from __future__ import annotations

from evdev import ecodes as e, AbsInfo

from nocrosshair.controllers.base import ControllerHardware
from nocrosshair.controllers.descriptor import ControllerDescriptor


_DS4_DESCRIPTOR = ControllerDescriptor(
    id="ds4",
    name="Sony Computer Entertainment Wireless Controller",
    manufacturer="Sony Interactive Entertainment",
    polling_rate_hz=250,
    connection_types=["bluetooth", "usb"],
    joystick_type="potentiometer",
    joystick_resolution_bits=12,
    joystick_count=2,
    anti_drift=False,
    trigger_type="analog",
    trigger_count=2,
    has_trigger_stops=False,
    trigger_stops_mechanical=False,
    has_gyro=True,
    gyro_axes=6,
    has_rumble=True,
    has_rgb=True,
    rgb_zones=1,
    has_dock=False,
    has_headphone_jack=True,
    has_extra_buttons=False,
    extra_button_count=0,
    battery_capacity_mah=1000,
    weight_g=210.0,
    dimensions_mm=(162.0, 98.0, 52.0),
    vid_pid=(0x054C, 0x09CC),
    uinput_name="Sony Computer Entertainment Wireless Controller",
    uinput_vendor=0x054C,
    uinput_product=0x09CC,
    uinput_version=0x0100,
    raw_capabilities=[
        "EV_KEY", "EV_ABS",
        "ABS_X", "ABS_Y", "ABS_RX", "ABS_RY", "ABS_Z", "ABS_RZ",
        "ABS_HAT0X", "ABS_HAT0Y",
        "BTN_A", "BTN_B", "BTN_X", "BTN_Y",
        "BTN_TL", "BTN_TR", "BTN_SELECT", "BTN_START",
        "BTN_THUMBL", "BTN_THUMBR", "BTN_MODE",
        "BTN_TL2", "BTN_TR2",
    ],
)


class DS4(ControllerHardware):

    def __init__(self) -> None:
        super().__init__(_DS4_DESCRIPTOR)

    def create_uinput_device(self) -> tuple[int, int, int, int]:
        return (
            self.descriptor.uinput_vendor,
            self.descriptor.uinput_product,
            self.descriptor.uinput_version,
            0x0003,
        )

    def get_capabilities(self) -> dict[int, list]:
        flat = 0
        return {
            e.EV_KEY: [
                e.BTN_A, e.BTN_B, e.BTN_X, e.BTN_Y,
                e.BTN_TL, e.BTN_TR,
                e.BTN_TL2, e.BTN_TR2,
                e.BTN_SELECT, e.BTN_START,
                e.BTN_THUMBL, e.BTN_THUMBR,
                e.BTN_MODE,
            ],
            e.EV_ABS: [
                (e.ABS_X, AbsInfo(128, 0, 255, 0, 15, 0)),
                (e.ABS_Y, AbsInfo(128, 0, 255, 0, 15, 0)),
                (e.ABS_RX, AbsInfo(128, 0, 255, 0, 15, 0)),
                (e.ABS_RY, AbsInfo(128, 0, 255, 0, 15, 0)),
                (e.ABS_Z, AbsInfo(flat, 0, 255, 0, 0, 0)),
                (e.ABS_RZ, AbsInfo(flat, 0, 255, 0, 0, 0)),
                (e.ABS_HAT0X, AbsInfo(flat, -1, 1, 0, 0, 0)),
                (e.ABS_HAT0Y, AbsInfo(flat, -1, 1, 0, 0, 0)),
            ],
        }

    @property
    def has_motion_controls(self) -> bool:
        return True

    @property
    def polling_rate_usb(self) -> int:
        return 1000

    @property
    def polling_rate_class(self) -> str:
        return "250hz"

    def get_polling_interval_ns(self) -> int:
        return 4_000_000

    def get_trigger_threshold(self) -> int:
        return 30
