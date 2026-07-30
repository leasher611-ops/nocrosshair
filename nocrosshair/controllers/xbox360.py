from __future__ import annotations

from evdev import ecodes as e, AbsInfo

from nocrosshair.controllers.base import ControllerHardware
from nocrosshair.controllers.descriptor import ControllerDescriptor


_XBOX360_DESCRIPTOR = ControllerDescriptor(
    id="xbox360",
    name="Microsoft X-Box 360 pad",
    manufacturer="Microsoft",
    polling_rate_hz=125,
    connection_types=["wired", "wireless"],
    joystick_type="potentiometer",
    joystick_resolution_bits=12,
    joystick_count=2,
    anti_drift=False,
    trigger_type="digital",
    trigger_count=2,
    has_trigger_stops=False,
    trigger_stops_mechanical=False,
    has_gyro=False,
    gyro_axes=0,
    has_rumble=True,
    has_rgb=False,
    rgb_zones=0,
    has_dock=False,
    has_headphone_jack=False,
    has_extra_buttons=False,
    extra_button_count=0,
    battery_capacity_mah=0,
    weight_g=260.0,
    dimensions_mm=(156.0, 104.0, 60.0),
    vid_pid=(0x045E, 0x028E),
    uinput_name="Microsoft X-Box 360 pad",
    uinput_vendor=0x045E,
    uinput_product=0x028E,
    uinput_version=0x0100,
    raw_capabilities=[
        "EV_KEY", "EV_ABS", "EV_FF",
        "ABS_X", "ABS_Y", "ABS_RX", "ABS_RY", "ABS_Z", "ABS_RZ",
        "ABS_HAT0X", "ABS_HAT0Y",
        "BTN_A", "BTN_B", "BTN_X", "BTN_Y",
        "BTN_TL", "BTN_TR", "BTN_SELECT", "BTN_START",
        "BTN_THUMBL", "BTN_THUMBR", "BTN_MODE",
    ],
)


class Xbox360(ControllerHardware):

    def __init__(self) -> None:
        super().__init__(_XBOX360_DESCRIPTOR)

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
                e.BTN_SELECT, e.BTN_START,
                e.BTN_THUMBL, e.BTN_THUMBR,
                e.BTN_MODE,
            ],
            e.EV_ABS: [
                (e.ABS_X, AbsInfo(flat, -32768, 32767, 0, 15, 0)),
                (e.ABS_Y, AbsInfo(flat, -32768, 32767, 0, 15, 0)),
                (e.ABS_RX, AbsInfo(flat, -32768, 32767, 0, 15, 0)),
                (e.ABS_RY, AbsInfo(flat, -32768, 32767, 0, 15, 0)),
                (e.ABS_Z, AbsInfo(flat, 0, 255, 0, 0, 0)),
                (e.ABS_RZ, AbsInfo(flat, 0, 255, 0, 0, 0)),
                (e.ABS_HAT0X, AbsInfo(flat, -1, 1, 0, 0, 0)),
                (e.ABS_HAT0Y, AbsInfo(flat, -1, 1, 0, 0, 0)),
            ],
        }

    @property
    def has_digital_triggers(self) -> bool:
        return True

    @property
    def polling_rate_class(self) -> str:
        return "125hz"

    def get_polling_interval_ns(self) -> int:
        return 8_000_000

    def get_trigger_threshold(self) -> int:
        return 127
