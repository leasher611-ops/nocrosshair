from evdev import ecodes as e

from nocrosshair.controllers.descriptor import ControllerDescriptor
from nocrosshair.controllers.g7_pro_8k import G7Pro8K
from nocrosshair.controllers.cyclone_2 import Cyclone2
from nocrosshair.controllers.ds4 import DS4
from nocrosshair.controllers.dualsense_edge import DualSenseEdge
from nocrosshair.controllers.xbox360 import Xbox360
from nocrosshair.controllers.registry import registry
from nocrosshair.features.triggers import TriggerEngine, TriggerConfig, TriggerModeType
from nocrosshair.features.gyro import GyroEngine, GyroConfig, GyroAimMode
from nocrosshair.features.polling import PollingEngine, PollingPrecision
from nocrosshair.core.config import ControllerHardwareConfig, AppConfig


class TestControllerDescriptor:

    def test_create_g7_descriptor(self):
        d = G7Pro8K().descriptor
        assert d.polling_rate_hz == 8000
        assert d.joystick_type == "tmr"
        assert d.trigger_type == "hall_effect_analog"
        assert d.anti_drift is True
        assert d.has_gyro is False
        assert d.has_rgb is True

    def test_create_cyclone_descriptor(self):
        d = Cyclone2().descriptor
        assert d.polling_rate_hz == 1000
        assert d.has_gyro is True
        assert d.has_rgb is True
        assert d.has_dock is True

    def test_create_ds4_descriptor(self):
        d = DS4().descriptor
        assert d.has_gyro is True
        assert d.joystick_type == "potentiometer"
        assert d.trigger_type == "analog"

    def test_create_dualsense_edge_descriptor(self):
        d = DualSenseEdge().descriptor
        assert d.id == "dualsense_edge"
        assert d.has_gyro is True
        assert d.joystick_type == "hall_effect"
        assert d.has_trigger_stops is True
        assert d.trigger_stops_mechanical is True
        assert d.has_extra_buttons is True
        assert d.extra_button_count == 4
        assert d.vid_pid == (0x054C, 0x0DF2)

    def test_create_xbox360_descriptor(self):
        d = Xbox360().descriptor
        assert d.polling_rate_hz == 125
        assert d.has_gyro is False
        assert d.trigger_type == "digital"
        assert d.has_rgb is False

    def test_to_dict_roundtrip(self):
        d = G7Pro8K().descriptor
        serialized = d.to_dict()
        restored = ControllerDescriptor.from_dict(serialized)
        assert restored.id == d.id
        assert restored.polling_rate_hz == d.polling_rate_hz
        assert restored.joystick_type == d.joystick_type
        assert restored.trigger_type == d.trigger_type
        assert restored.has_gyro == d.has_gyro
        assert restored.has_rgb == d.has_rgb
        assert restored.vid_pid == d.vid_pid
        assert restored.dimensions_mm == d.dimensions_mm

    def test_from_dict(self):
        original = G7Pro8K().descriptor
        d = original.to_dict()
        restored = ControllerDescriptor.from_dict(d)
        assert restored.id == original.id
        assert restored.name == original.name
        assert restored.polling_rate_hz == original.polling_rate_hz
        assert restored.vid_pid == original.vid_pid
        assert restored.dimensions_mm == original.dimensions_mm


class TestG7Pro8KHardware:

    def test_create_uinput_capabilities(self):
        ctrl = G7Pro8K()
        caps = ctrl.get_capabilities()
        assert e.EV_ABS in caps
        assert e.EV_KEY in caps

    def test_vid_pid(self):
        ctrl = G7Pro8K()
        assert ctrl.descriptor.vid_pid == (0x3534, 0x1001)

    def test_get_polling_interval(self):
        ctrl = G7Pro8K()
        assert ctrl.get_polling_interval_ns() == 125_000

    def test_trigger_threshold(self):
        ctrl = G7Pro8K()
        assert ctrl.get_trigger_threshold() == 0


class TestCyclone2Hardware:

    def test_has_gyro_capability(self):
        ctrl = Cyclone2()
        caps = ctrl.get_capabilities()
        assert e.EV_ABS in caps
        assert ctrl.descriptor.gyro_axes == 6

    def test_vid_pid(self):
        ctrl = Cyclone2()
        assert ctrl.descriptor.vid_pid == (0x3534, 0x1002)

    def test_polling_interval(self):
        ctrl = Cyclone2()
        assert ctrl.get_polling_interval_ns() == 1_000_000


class TestControllerRegistry:

    def test_singleton(self):
        assert registry is not None

    def test_all_controllers_registered(self):
        available = registry.list_available()
        ids = [d.id for d in available]
        assert "g7_pro_8k" in ids
        assert "cyclone_2" in ids
        assert "ds4" in ids
        assert "dualsense_edge" in ids
        assert "xbox360" in ids

    def test_get_by_id(self):
        hw_cls = registry.get("g7_pro_8k")
        assert hw_cls == G7Pro8K

    def test_get_descriptor(self):
        desc = registry.get_descriptor("g7_pro_8k")
        assert desc.id == "g7_pro_8k"


class TestTriggerEngine:

    def test_analog_mode(self):
        config = TriggerConfig(mode=TriggerModeType.ANALOG, analog_deadzone=5)
        engine = TriggerEngine(config, G7Pro8K().descriptor)
        result = engine.process(100)
        assert result == 100

    def test_digital_mode(self):
        config = TriggerConfig(mode=TriggerModeType.DIGITAL)
        engine = TriggerEngine(config, G7Pro8K().descriptor)
        assert engine.process(100, digital_click=False) == 0
        assert engine.process(100, digital_click=True) == 255

    def test_hybrid_mode(self):
        config = TriggerConfig(
            mode=TriggerModeType.HYBRID,
            stop_position=0.85,
            analog_max=1023,
        )
        engine = TriggerEngine(config, G7Pro8K().descriptor)
        assert engine.process(100) == 100
        assert engine.process(900) == 255


class TestGyroEngine:

    def test_disabled_returns_zero(self):
        config = GyroConfig(enabled=False)
        engine = GyroEngine(config)
        x, y = engine.process((0, 0, 0), (0, 0, 0))
        assert x == 0
        assert y == 0

    def test_calibrate(self):
        config = GyroConfig(enabled=True)
        engine = GyroEngine(config)
        offsets = engine.calibrate(samples=5)
        assert len(offsets) == 3
        assert isinstance(offsets[0], float)
        assert isinstance(offsets[1], float)
        assert isinstance(offsets[2], float)


class TestPollingEngine:

    def test_8000hz_ultra(self):
        pe = PollingEngine(8000)
        assert pe.precision == PollingPrecision.ULTRA

    def test_1000hz_high(self):
        pe = PollingEngine(1000)
        assert pe.precision == PollingPrecision.HIGH

    def test_250hz_medium(self):
        pe = PollingEngine(250)
        assert pe.precision == PollingPrecision.MEDIUM

    def test_125hz_low(self):
        pe = PollingEngine(125)
        assert pe.precision == PollingPrecision.LOW

    def test_interval_ns(self):
        pe_8k = PollingEngine(8000)
        assert pe_8k.interval_ns == 125000
        pe_1k = PollingEngine(1000)
        assert pe_1k.interval_ns == 1000000


class TestDualSenseEdgeHardware:

    def test_vid_pid(self):
        ctrl = DualSenseEdge()
        assert ctrl.descriptor.vid_pid == (0x054C, 0x0DF2)

    def test_has_gyro(self):
        ctrl = DualSenseEdge()
        assert ctrl.has_motion_controls is True

    def test_get_capabilities_includes_extra_buttons(self):
        ctrl = DualSenseEdge()
        caps = ctrl.get_capabilities()
        key_caps = caps.get(e.EV_KEY, [])
        assert e.BTN_TRIGGER_HAPPY1 in key_caps
        assert e.BTN_TRIGGER_HAPPY2 in key_caps
        assert e.BTN_TRIGGER_HAPPY3 in key_caps
        assert e.BTN_TRIGGER_HAPPY4 in key_caps

    def test_capabilities_use_8bit_sticks(self):
        ctrl = DualSenseEdge()
        caps = ctrl.get_capabilities()
        abs_caps = {code: info for code, info in caps.get(e.EV_ABS, [])}
        assert abs_caps[e.ABS_X].min == 0
        assert abs_caps[e.ABS_X].max == 255
        assert abs_caps[e.ABS_X].flat == 15
        assert abs_caps[e.ABS_RX].min == 0
        assert abs_caps[e.ABS_RX].max == 255


class TestConfigIntegration:

    def test_controller_hardware_config_defaults(self):
        cfg = ControllerHardwareConfig()
        assert cfg.controller_id == "xbox360"

    def test_config_serialization(self):
        cfg = ControllerHardwareConfig(
            controller_id="g7_pro_8k",
            polling_rate_hz=8000,
        )
        d = cfg.to_dict()
        restored = ControllerHardwareConfig.from_dict(d)
        assert restored.controller_id == "g7_pro_8k"
        assert restored.polling_rate_hz == 8000

    def test_app_config_has_hardware(self):
        ac = AppConfig()
        assert ac.controller_hardware is not None


class TestControllerTypeNormalization:

    def test_dualshock4_normalizes_to_ds4(self):
        from nocrosshair.core.controller import _normalize_type
        assert _normalize_type("dualshock4") == "ds4"

    def test_dualsense_edge_normalizes_to_ds4(self):
        from nocrosshair.core.controller import _normalize_type
        assert _normalize_type("dualsense_edge") == "ds4"

    def test_xbox360_stays_xbox360(self):
        from nocrosshair.core.controller import _normalize_type
        assert _normalize_type("xbox360") == "xbox360"


class TestDS4Translation:

    def test_ds4_button_map(self):
        from nocrosshair.core.input_loop import DS4_BUTTON_MAP, _is_ds4_controller
        assert DS4_BUTTON_MAP[0x130] == e.BTN_A
        assert DS4_BUTTON_MAP[0x131] == e.BTN_B
        assert DS4_BUTTON_MAP[0x132] == e.BTN_X
        assert DS4_BUTTON_MAP[0x133] == e.BTN_Y
        assert DS4_BUTTON_MAP[0x134] == e.BTN_TL
        assert DS4_BUTTON_MAP[0x135] == e.BTN_TR

    def test_is_ds4_controller_detection(self):
        from nocrosshair.core.input_loop import _is_ds4_controller
        class MockDevInfo:
            vendor = 0x054C
        class MockDev:
            info = MockDevInfo()
            name = "Sony Interactive Entertainment Wireless Controller"
            def capabilities(self):
                return {e.EV_KEY: [e.BTN_A, e.BTN_C]}
        
        assert _is_ds4_controller(MockDev()) is True
        
        class MockXboxDevInfo:
            vendor = 0x045E
        class MockXboxDev:
            info = MockXboxDevInfo()
            name = "Microsoft Xbox 360 pad"
            def capabilities(self):
                return {e.EV_KEY: [e.BTN_A, e.BTN_B]}

        assert _is_ds4_controller(MockXboxDev()) is False
