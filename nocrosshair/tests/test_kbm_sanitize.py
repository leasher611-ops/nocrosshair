#!/usr/bin/env python3

from nocrosshair.core.config import AimAssistConfig
from nocrosshair.core.input_loop import kbm_sanitize_config


def make_cfg(**kw) -> AimAssistConfig:
    defaults = dict(
        kbm_mode=True,
        kbm_scale=0.25,
        fire_boost_mult=1.35,
        fire_boost_ms=150,
        pulse_level=2,
        snap_strength=700,
        magnetic_snap=True,
        sticky_enabled=True,
        lock_enabled=True,
        rush_enabled=True,
        head_assist_enabled=True,
        auto_rotation_enabled=True,
        adaptive_strength=True,
        enhanced_enabled=True,
        aimlock_enabled=True,
        tracking_strength=2200,
        fn_humanize=True,
        fn_rotation_cap=800,
        fn_slow_strength=0.85,
        fn_zone=5000,
    )
    defaults.update(kw)
    return AimAssistConfig(**defaults)


class TestKbmSanitize:

    def test_mode_off_returns_same(self):
        cfg = make_cfg(kbm_mode=False)
        out = kbm_sanitize_config(cfg)
        assert out is cfg

    def test_explosive_features_disabled(self):
        out = kbm_sanitize_config(make_cfg())
        assert out.fire_boost_mult == 1.0
        assert out.pulse_level == 0
        assert out.snap_strength == 0
        assert out.magnetic_snap is False
        assert out.sticky_enabled is False
        assert out.lock_enabled is False
        assert out.rush_enabled is False
        assert out.head_assist_enabled is False
        assert out.auto_rotation_enabled is False
        assert out.adaptive_strength is False
        assert out.enhanced_enabled is False
        assert out.aimlock_enabled is False
        assert out.tracking_strength == 0
        assert out.fn_humanize is False

    def test_pull_cap_scaled(self):
        out = kbm_sanitize_config(make_cfg(fn_rotation_cap=800, kbm_scale=0.25))
        assert out.fn_rotation_cap == 250

    def test_pull_cap_minimum(self):
        out = kbm_sanitize_config(make_cfg(fn_rotation_cap=300, kbm_scale=0.1))
        assert out.fn_rotation_cap == 250

    def test_input_gate_scaled(self):
        out = kbm_sanitize_config(make_cfg(fn_input_gate=800, kbm_scale=0.25))
        assert out.fn_input_gate == 200

    def test_input_gate_minimum(self):
        out = kbm_sanitize_config(make_cfg(fn_input_gate=100, kbm_scale=0.1))
        assert out.fn_input_gate == 200

    def test_rotational_gate_set(self):
        out = kbm_sanitize_config(make_cfg())
        assert out.rotational_mag_gate == 200

    def test_rotational_radius_mult_set(self):
        out = kbm_sanitize_config(make_cfg())
        assert out.rotational_radius_mult == 1.5

    def test_tweak_zone_enabled(self):
        out = kbm_sanitize_config(make_cfg())
        assert out.tweak_zone_enabled is True

    def test_silent_aim_defaults(self):
        out = kbm_sanitize_config(make_cfg())
        assert out.silent_aim_enabled is False
        assert out.silent_aim_slow_mult == 1.4
        assert out.silent_aim_pull_mult == 1.6
        assert out.silent_aim_shake_blend == 0.55

    def test_silent_hit_defaults(self):
        out = kbm_sanitize_config(make_cfg())
        assert out.silent_hit_enabled is False
        assert out.silent_hit_slow_mult == 1.2
        assert out.silent_hit_pull_mult == 2.0
        assert out.silent_hit_shake_blend == 0.50

    def test_sticky_parts_preserved(self):
        out = kbm_sanitize_config(make_cfg())
        assert out.fn_slow_strength == 0.85
        assert out.fn_zone == 5000
        assert out.fn_slow_strength > 0

    def test_original_untouched(self):
        cfg = make_cfg()
        kbm_sanitize_config(cfg)
        assert cfg.fire_boost_mult == 1.35
        assert cfg.aimlock_enabled is True
        assert cfg.pulse_level == 2
