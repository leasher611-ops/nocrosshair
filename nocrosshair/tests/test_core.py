import pytest
from nocrosshair.core.config import (
    ConfigValidator, StickPhysicsConfig, TriggerPhysicsConfig,
    AimAssistConfig
)
from nocrosshair.core.profile_manager import Profile, ProfileManager
from nocrosshair.features.physics import (
    StickPhysicsEngine, TriggerPhysicsEngine,
    apply_curve_multipoint, apply_recoil_curve_factor
)

class TestConfigValidator:

    def test_validate_color_valid(self):
        assert ConfigValidator.validate_color("#00ff88") is True
        assert ConfigValidator.validate_color("#ffffff") is True
        assert ConfigValidator.validate_color("#000000") is True

    def test_validate_color_invalid(self):
        assert ConfigValidator.validate_color("00ff88") is False
        assert ConfigValidator.validate_color("#zzzzzz") is False
        assert ConfigValidator.validate_color("#12345") is False
        assert ConfigValidator.validate_color("") is False

    def test_validate_range(self):
        assert ConfigValidator.validate_range(0.5, 0.0, 1.0) is True
        assert ConfigValidator.validate_range(0.0, 0.0, 1.0) is True
        assert ConfigValidator.validate_range(1.0, 0.0, 1.0) is True
        assert ConfigValidator.validate_range(1.5, 0.0, 1.0) is False
        assert ConfigValidator.validate_range(-0.5, 0.0, 1.0) is False

    def test_validate_controller_type(self):
        assert ConfigValidator.validate_controller_type("xbox360") is True
        assert ConfigValidator.validate_controller_type("dualshock4") is True
        assert ConfigValidator.validate_controller_type("invalid") is False

class TestStickPhysics:

    def test_zero_input(self):
        cfg = StickPhysicsConfig()
        engine = StickPhysicsEngine(cfg)
        x, y = engine.apply(0, 0)
        assert x == 0 and y == 0

    def test_full_deflection(self):
        cfg = StickPhysicsConfig()
        engine = StickPhysicsEngine(cfg)
        x, y = engine.apply(32767, 0)
        assert x != 0
        assert abs(x) <= 32767

    def test_deadzone_cutoff(self):
        cfg = StickPhysicsConfig(deflection_min=0.5)
        engine = StickPhysicsEngine(cfg)
        x, y = engine.apply(5000, 0)
        assert x == 0 and y == 0

    def test_acceleration(self):
        cfg1 = StickPhysicsConfig(acceleration=1.0)
        cfg2 = StickPhysicsConfig(acceleration=2.0)
        engine1 = StickPhysicsEngine(cfg1)
        engine2 = StickPhysicsEngine(cfg2)

        x1, _ = engine1.apply(16384, 0)
        x2, _ = engine2.apply(16384, 0)

        assert abs(x2) < abs(x1)

    def test_initial_speed(self):
        cfg1 = StickPhysicsConfig(initial_speed=0.0)
        cfg2 = StickPhysicsConfig(initial_speed=0.5)
        engine1 = StickPhysicsEngine(cfg1)
        engine2 = StickPhysicsEngine(cfg2)

        x1, _ = engine1.apply(5000, 0)
        x2, _ = engine2.apply(5000, 0)

        assert abs(x2) > abs(x1)

class TestTriggerPhysics:

    def test_hair_trigger_off(self):
        cfg = TriggerPhysicsConfig(hair_trigger=False, deadzone=0.1)
        engine = TriggerPhysicsEngine(cfg)

        assert engine.apply(10) == 0

        val = engine.apply(128)
        assert 0 < val <= 255

    def test_hair_trigger_on(self):
        cfg = TriggerPhysicsConfig(hair_trigger=True)
        engine = TriggerPhysicsEngine(cfg)

        assert engine.apply(0) == 0
        assert engine.apply(1) == 255
        assert engine.apply(128) == 255

    def test_sensitivity_curve(self):
        cfg1 = TriggerPhysicsConfig(hair_trigger=False, sensitivity=1.0)
        cfg2 = TriggerPhysicsConfig(hair_trigger=False, sensitivity=2.0)
        engine1 = TriggerPhysicsEngine(cfg1)
        engine2 = TriggerPhysicsEngine(cfg2)

        val1 = engine1.apply(128)
        val2 = engine2.apply(128)

        assert val2 < val1

class TestCurveHelpers:

    def test_apply_curve_multipoint(self):
        points = [(0, 0), (100, 50), (200, 200)]

        assert apply_curve_multipoint(50, points) == 25

        assert apply_curve_multipoint(100, points) == 50

        assert apply_curve_multipoint(200, points) == 200

    def test_apply_curve_negative(self):
        points = [(0, 0), (100, 100)]
        result = apply_curve_multipoint(-50, points)
        assert result < 0

    def test_recoil_curve_factor(self):
        start = apply_recoil_curve_factor(0, 10, "ease_out")
        mid = apply_recoil_curve_factor(5, 10, "ease_out")
        end = apply_recoil_curve_factor(9, 10, "ease_out")

        assert start > mid > end
        assert 0 <= start <= 1
        assert 0 <= end <= 1

class TestProfile:

    def test_profile_creation(self):
        profile = Profile(name="Test")
        assert profile.name == "Test"
        assert isinstance(profile.key_map, dict)
        assert profile.created_at != ""

    def test_profile_to_dict(self):
        profile = Profile(name="Test", description="Test profile")
        d = profile.to_dict()
        assert d["name"] == "Test"
        assert d["description"] == "Test profile"

    def test_profile_from_dict(self):
        d = {"name": "Test", "description": "Test profile", "controller_type": "dualshock4"}
        profile = Profile.from_dict(d)
        assert profile.name == "Test"
        assert profile.controller_type == "dualshock4"

class TestConfigDataclasses:

    def test_stick_physics_config_from_dict(self):
        cfg_dict = {
            "ls_deflection_min": 0.1,
            "ls_acceleration": 1.5,
        }
        cfg = StickPhysicsConfig.from_dict(cfg_dict, "ls_")
        assert cfg.deflection_min == 0.1
        assert cfg.acceleration == 1.5

    def test_trigger_physics_config_from_dict(self):
        cfg_dict = {
            "rt_deadzone": 0.05,
            "rt_hair_trigger": True,
        }
        cfg = TriggerPhysicsConfig.from_dict(cfg_dict, "rt_")
        assert cfg.deadzone == 0.05
        assert cfg.hair_trigger is True

    def test_aim_assist_config_from_dict(self):
        cfg_dict = {
            "remap_aa_enabled": True,
            "remap_aa_strength": 5000,
            "aa_zone": 2500,
        }
        cfg = AimAssistConfig.from_dict(cfg_dict)
        assert cfg.enabled is True
        assert cfg.strength == 5000
        assert cfg.zone == 2500

class TestWeaponBinds:

    def test_default_kbd_bindings_has_weapon_keys(self):
        from nocrosshair.core.remapper import DEFAULT_KBD_BINDINGS
        assert "KEY_1" in DEFAULT_KBD_BINDINGS
        assert "KEY_2" in DEFAULT_KBD_BINDINGS
        assert "KEY_3" in DEFAULT_KBD_BINDINGS
        assert "KEY_4" in DEFAULT_KBD_BINDINGS
        assert "KEY_5" in DEFAULT_KBD_BINDINGS
        assert "KEY_F" in DEFAULT_KBD_BINDINGS
        assert "KEY_Q" in DEFAULT_KBD_BINDINGS
        assert DEFAULT_KBD_BINDINGS["KEY_F"] == "BTN_Y"
        assert DEFAULT_KBD_BINDINGS["KEY_Q"] == "BTN_B"

    def test_process_key_normal(self):
        from nocrosshair.core.remapper import InputRemapper, DEFAULT_KBD_BINDINGS
        remapper = InputRemapper(DEFAULT_KBD_BINDINGS)
        action_e, val_e = remapper.process_key("KEY_E", 1)
        assert action_e == "BTN_X"
        assert val_e == 1

        action_q, val_q = remapper.process_key("KEY_Q", 1)
        assert action_q == "BTN_B"
        assert val_q == 1

        action_1, val_1 = remapper.process_key("KEY_1", 1)
        assert action_1 == "BTN_TR"
        assert val_1 == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
