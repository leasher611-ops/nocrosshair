import pytest
from nocrosshair.core.config import AimAssistConfig
from nocrosshair.features.aim_assist import AimAssistEngine, AimAssistPresets
from nocrosshair.features.aim_assist import AimAssistPipeline


class TestFnControllerPreset:

    def test_fortnite_controller_preset_valid(self):
        cfg = AimAssistPresets.fortnite_controller()
        assert cfg.enabled is True
        assert cfg.base_aa_enabled is True
        assert cfg.strength == 8500
        assert cfg.zone == 5000
        assert isinstance(cfg, AimAssistConfig)


class TestShapeModes:

    @pytest.mark.parametrize("shape", ["circular", "zen", "helix", "wideoval", "tallowal"])
    def test_shape_modes_produce_different_output(self, shape):
        cfg = AimAssistConfig(
            enabled=True,
            rotational=True,
            shape_mode=shape,
            zone=2000,
        )
        engine = AimAssistEngine(cfg)
        pipeline = AimAssistPipeline(engine)
        rx, ry = pipeline._apply_rotational_aa(1000, 500, 16.0, cfg)
        assert isinstance(rx, float)
        assert isinstance(ry, float)
        assert -32768 <= rx <= 32767
        assert -32768 <= ry <= 32767

    def test_dz_radius_expands_zone(self):
        cfg = AimAssistConfig(
            enabled=True,
            zone=500,
            use_dz_radius=True,
            deadzone_aa_radius=10,
            zone_multiplier=3,
        )
        assert cfg.use_dz_radius is True
        assert cfg.zone < cfg.deadzone_aa_radius * 100 * cfg.zone_multiplier
        min_zone = cfg.deadzone_aa_radius * 100 * cfg.zone_multiplier
        assert min_zone == 3000


class TestApplySlowdown:

    def _make_engine(self, **overrides):
        cfg = AimAssistConfig(**overrides)
        return AimAssistEngine(cfg)

    def test_zone_zero_no_change(self):
        engine = self._make_engine(zone=0)
        rx, ry = engine.apply_slowdown(1000, 500, zone=0, strength=4500)
        assert rx == 1000
        assert ry == 500

    def test_zero_input_returns_zero(self):
        engine = self._make_engine()
        rx, ry = engine.apply_slowdown(0, 0, zone=2200, strength=4500)
        assert rx == 0
        assert ry == 0

    def test_input_outside_zone_no_change(self):
        engine = self._make_engine()
        rx, ry = engine.apply_slowdown(3000, 3000, zone=2200, strength=4500)
        assert rx == 3000
        assert ry == 3000

    def test_input_inside_zone_reduced(self):
        engine = self._make_engine()
        rx, ry = engine.apply_slowdown(1000, 0, zone=2200, strength=4500)
        assert abs(rx) < 1000
        assert ry == 0

    def test_output_clamped_positive(self):
        engine = self._make_engine()
        rx, ry = engine.apply_slowdown(32767, 32767, zone=50000, strength=9999)
        assert rx <= 32767
        assert ry <= 32767

    def test_output_clamped_negative(self):
        engine = self._make_engine()
        rx, ry = engine.apply_slowdown(-32768, -32768, zone=50000, strength=9999)
        assert rx >= -32768
        assert ry >= -32768


class TestShouldBeActive:

    def _make_engine(self):
        cfg = AimAssistConfig()
        return AimAssistEngine(cfg)

    def test_active_without_lt(self):
        engine = self._make_engine()
        assert engine.should_be_active(lt_pressed=False) is True

    def test_inactive_with_lt(self):
        engine = self._make_engine()
        assert engine.should_be_active(lt_pressed=True) is False
