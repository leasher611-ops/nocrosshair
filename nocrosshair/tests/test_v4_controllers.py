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

    def test_dualsense_edge_uses_dualsense_layout(self):
        from nocrosshair.core.controller import _normalize_type
        # DualSense NÃO é DS4: layout de eixos é o do Xbox (stick dir em RX/RY)
        assert _normalize_type("dualsense_edge") == "dualsense_edge"

    def test_xbox360_stays_xbox360(self):
        from nocrosshair.core.controller import _normalize_type
        assert _normalize_type("xbox360") == "xbox360"


class TestDS4Translation:

    def test_ds4_button_map(self):
        from nocrosshair.core.input_loop import DS4_BUTTON_MAP
        # hid-playstation reporta códigos posicionais; o virtual é Xbox 360,
        # onde o jogo lê BTN_X(307)=Quadrado e BTN_Y(308)=Triângulo.
        assert DS4_BUTTON_MAP[0x130] == e.BTN_A     # Cross (baixo) -> A do Xbox
        assert DS4_BUTTON_MAP[0x131] == e.BTN_B     # Circle (direita) -> B do Xbox
        assert DS4_BUTTON_MAP[0x133] == e.BTN_Y     # Triangle (cima) -> Y do Xbox
        assert DS4_BUTTON_MAP[0x134] == e.BTN_X     # Square (esquerda) -> X do Xbox
        assert DS4_BUTTON_MAP[0x136] == e.BTN_TL    # L1
        assert DS4_BUTTON_MAP[0x137] == e.BTN_TR    # R1
        assert DS4_BUTTON_MAP[0x138] == e.BTN_TL2   # L2 digital
        assert DS4_BUTTON_MAP[0x139] == e.BTN_TR2   # R2 digital
        assert DS4_BUTTON_MAP[0x13a] == e.BTN_SELECT  # Create/Share
        assert DS4_BUTTON_MAP[0x13b] == e.BTN_START   # Options
        assert DS4_BUTTON_MAP[0x13c] == e.BTN_MODE    # PS Home
        assert DS4_BUTTON_MAP[0x13d] == e.BTN_THUMBL  # L3
        assert DS4_BUTTON_MAP[0x13e] == e.BTN_THUMBR  # R3
        # Códigos inexistentes/duplicados não devem estar na tabela.
        assert 0x132 not in DS4_BUTTON_MAP  # BTN_C (unused)
        assert 0x135 not in DS4_BUTTON_MAP  # BTN_Z (unused)

    def test_sony_stick_cluster_swap(self):
        """O kernel enumera os botões do relatório na ordem NUMÉRICA dos
        códigos evdev (0x13A..0x13E), mas o jogo lê o DS4 na ordem física
        (Share, Options, L3, R3, PS). Sem a rotação, o MODE(0x13C) cai no
        slot do L3, o THUMBL(0x13D) no do R3 e o THUMBR(0x13E) no do PS —
        Shift (correr) virava R3. A rotação reencaminha cada código para o
        slot correto do jogo."""
        from nocrosshair.core.controller import _map_button_for_output
        assert _map_button_for_output("ds4", e.BTN_THUMBL) == e.BTN_MODE
        assert _map_button_for_output("ds4", e.BTN_THUMBR) == e.BTN_THUMBL
        assert _map_button_for_output("ds4", e.BTN_MODE) == e.BTN_THUMBR
        # Face: HID DS4 = Quadrado, Cruz, Círculo, Triângulo (índices 0-3).
        # Evdev enumera A,B,X,Y — a rotação manda cada letra Xbox pro slot HID.
        assert _map_button_for_output("ds4", e.BTN_X) == e.BTN_A  # Quadrado → slot 0
        assert _map_button_for_output("ds4", e.BTN_A) == e.BTN_B  # Cruz     → slot 1
        assert _map_button_for_output("ds4", e.BTN_B) == e.BTN_X  # Círculo  → slot 2
        assert _map_button_for_output("ds4", e.BTN_Y) == e.BTN_Y  # Triângulo já é slot 3
        # No Xbox o wine mapeia por CÓDIGO evdev: identidade correta.
        assert _map_button_for_output("xbox360", e.BTN_THUMBL) == e.BTN_THUMBL
        assert _map_button_for_output("xbox360", e.BTN_THUMBR) == e.BTN_THUMBR
        assert _map_button_for_output("xbox360", e.BTN_X) == e.BTN_X
        assert _map_button_for_output("xbox360", e.BTN_B) == e.BTN_B

    def test_ds4_kbd_face_buttons_land_on_hid_slots(self):
        """Q deve ser Círculo e E/R Quadrado no DS4 virtual — não Cruz/Círculo."""
        from nocrosshair.core.controller import _map_button_for_output
        from nocrosshair.core.remapper import ACTION_MAP, DEFAULT_KBD_BINDINGS

        def ds4_out(key: str) -> int:
            action = DEFAULT_KBD_BINDINGS[key]
            return _map_button_for_output("ds4", ACTION_MAP[action])

        assert ds4_out("KEY_E") == e.BTN_A      # Quadrado (slot HID 0)
        assert ds4_out("KEY_R") == e.BTN_A      # Quadrado
        assert ds4_out("KEY_Q") == e.BTN_X      # Círculo  (slot HID 2)
        assert ds4_out("KEY_SPACE") == e.BTN_B  # Cruz     (slot HID 1)
        assert ds4_out("KEY_F") == e.BTN_Y      # Triângulo (slot HID 3)

    def test_virtual_caps_include_trigger_buttons(self):
        """TL2/TR2 precisam estar declarados — sem eles o índice dos botões
        seguintes (Select/Start/L3/R3) desloca e o jogo lê tudo errado."""
        from nocrosshair.core.controller import _make_capabilities
        caps, vid, pid = _make_capabilities("ds4")
        key_caps = caps.get(e.EV_KEY, [])
        assert e.BTN_TL2 in key_caps
        assert e.BTN_TR2 in key_caps
        caps_xbox, _, _ = _make_capabilities("xbox360")
        key_caps_xbox = caps_xbox.get(e.EV_KEY, [])
        assert e.BTN_TL2 in key_caps_xbox
        assert e.BTN_TR2 in key_caps_xbox

    def test_sony_controller_detection(self):
        from nocrosshair.core.input_loop import _detect_sony_kind
        class MockDevInfo:
            vendor = 0x054C
            product = 0x09CC
        class MockDev:
            info = MockDevInfo()
            name = "Sony Interactive Entertainment Wireless Controller"

        assert _detect_sony_kind(MockDev()) == "ds4"

        class MockDualSenseInfo:
            vendor = 0x054C
            product = 0x0CE6
        class MockDualSense:
            info = MockDualSenseInfo()
            name = "DualSense Wireless Controller"

        assert _detect_sony_kind(MockDualSense()) == "dualsense"

        class MockXboxDevInfo:
            vendor = 0x045E
        class MockXboxDev:
            info = MockXboxDevInfo()
            name = "Microsoft Xbox 360 pad"

        assert _detect_sony_kind(MockXboxDev()) is None

    def test_sony_axis_map(self):
        """DS4 e DualSense têm layouts de eixo DIFERENTES — o mapa corrige."""
        from nocrosshair.core.input_loop import map_sony_axis
        # DS4: stick direito em ABS_Z/ABS_RZ, gatilhos em ABS_RX/ABS_RY
        assert map_sony_axis("ds4", e.ABS_X, 128) == (e.ABS_X, 0)          # centro
        assert map_sony_axis("ds4", e.ABS_X, 255)[1] > 30000               # full direito
        assert map_sony_axis("ds4", e.ABS_X, 0)[1] <= -30000               # full esquerdo
        assert map_sony_axis("ds4", e.ABS_Z, 255)[0] == e.ABS_RX           # stick dir X → canonical RX
        assert map_sony_axis("ds4", e.ABS_RZ, 255)[0] == e.ABS_RY          # stick dir Y → canonical RY
        assert map_sony_axis("ds4", e.ABS_RX, 200) == (e.ABS_Z, 200)       # L2 → canonical LT
        assert map_sony_axis("ds4", e.ABS_RY, 180) == (e.ABS_RZ, 180)      # R2 → canonical RT
        # DualSense: stick direito em ABS_RX/ABS_RY, gatilhos em ABS_Z/ABS_RZ
        assert map_sony_axis("dualsense", e.ABS_RX, 255)[0] == e.ABS_RX
        assert map_sony_axis("dualsense", e.ABS_Z, 180) == (e.ABS_Z, 180)  # L2 → canonical LT
        # Eixo não mapeado (dpad) → None
        assert map_sony_axis("ds4", e.ABS_HAT0X, 1) is None
