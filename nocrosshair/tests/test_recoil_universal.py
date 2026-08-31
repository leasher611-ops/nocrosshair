import math

import pytest

from nocrosshair.core.config import RECOIL_PRESETS, RecoilConfig
from nocrosshair.features.recoil import (
    AntiRecoilEngine,
    AntiRecoilState,
    BezierCurve,
    RecoilAdaptEngine,
    RecoilEngine,
    RecoilPattern,
    RecoilState,
    RecoilTestbed,
    SmartLearnEngine,
)


def _make_engine(enabled=True, strength=65, x_strength=0, ticks=60,
                 curve="ease_out", y_gate=True, recoil_adapt=0,
                 smart_learn=False, weapon="FURY AR",
                 initial_kick_mult=1.0, initial_kick_ticks=6,
                 headshot_assist=False, headshot_assist_pull=700,
                 delay_ms=None, return_speed=None) -> RecoilEngine:
    cfg = RecoilConfig(
        enabled=enabled,
        strength=strength,
        x_strength=x_strength,
        ticks=ticks,
        curve=curve,
        y_gate=y_gate,
        recoil_adapt=recoil_adapt,
        smart_learn=smart_learn,
        initial_kick_mult=initial_kick_mult,
        initial_kick_ticks=initial_kick_ticks,
        headshot_assist=headshot_assist,
        headshot_assist_pull=headshot_assist_pull,
    )
    engine = RecoilEngine(cfg)
    engine.set_weapon(weapon)
    # Delay/return vêm do preset da arma por padrão; os testes genéricos
    # isolam essas features (testadas à parte) desligando o delay.
    if delay_ms is not None:
        engine._active_delay_ms = delay_ms
    else:
        engine._active_delay_ms = 0.0
    if return_speed is not None:
        engine._active_return_speed = return_speed
    return engine


def _spray(engine: RecoilEngine, ticks: int, is_aiming=True, is_moving=False,
           ry_raw=0, rx_raw=0, delta_ms=16.67, bloom=True) -> list:
    out = []
    for tick in range(ticks):
        y, x = engine.process(
            tick, is_shooting=True, is_aiming=is_aiming, is_moving=is_moving,
            ry_raw=ry_raw, rx_raw=rx_raw, delta_ms=delta_ms,
            bloom_compensation=bloom,
        )
        out.append((y, x))
    return out


class TestRecoilConfigDefaults:

    def test_from_dict_defaults(self):
        cfg = RecoilConfig.from_dict({})
        assert cfg.enabled is False
        assert cfg.strength == 35
        assert cfg.x_strength == 2
        assert cfg.ticks == 60
        assert cfg.delay_ms == 45
        assert cfg.return_speed == 0.7
        assert cfg.curve == "ease_out"
        assert cfg.y_gate is True
        assert cfg.recoil_adapt == 0
        assert cfg.smart_learn is False

    def test_from_dict_prefixed(self):
        cfg = RecoilConfig.from_dict({"recoil_strength": 42, "recoil_ticks": 30})
        assert cfg.strength == 42
        assert cfg.ticks == 30


class TestAntiRecoilDisabled:

    def test_disabled_no_pull(self):
        engine = _make_engine(enabled=False)
        y, x = engine.process(0, True, True, False, 0, 0, 16.67)
        assert y == 0
        assert x == 0

    def test_not_shooting_no_pull(self):
        engine = _make_engine()
        y, x = engine.process(0, False, True, False, 0, 0, 16.67)
        assert y == 0
        assert x == 0

    def test_state_clears_when_stop_shooting(self):
        engine = _make_engine()
        _spray(engine, 20)
        engine.process(0, False, True, False, 0, 0, 16.67)
        assert engine.state.active is False

    def test_ema_decays_when_idle(self):
        engine = _make_engine()
        _spray(engine, 20)
        engine.state.ema_y = 8000.0
        y, _ = engine.process(0, False, True, False, 0, 0, 16.67)
        assert abs(y) < 8000


class TestAntiRecoilBasicPull:

    def test_shooting_pulls_down(self):
        engine = _make_engine(strength=30, curve="linear", weapon="FURY AR")
        out = _spray(engine, 5, is_aiming=True)
        assert all(y > 0 for y, _ in out)

    def test_preset_pattern_tracks_decay(self):
        # Preset usa o padrão gerado (decai 50% ao longo do spray),
        # independente da curva. O EMA converge para o valor do tick.
        engine = _make_engine(strength=30, curve="linear", weapon="FURY AR")
        out = _spray(engine, 30, is_aiming=True)
        expected = int(30 * 90 * (1.0 - (29 / 49) * 0.5))
        assert abs(out[-1][0] - expected) <= 40

    def test_hip_fire_stronger_than_ads(self):
        engine = _make_engine(strength=30, curve="linear", weapon="FURY AR")
        ads = _spray(engine, 10, is_aiming=True)[-1][0]
        hip = _spray(engine, 10, is_aiming=False)[-1][0]
        assert hip > ads

    def test_stronger_strength_pulls_more(self):
        # Fallback (arma sem preset) usa config.strength com a curva
        weak = _make_engine(strength=20, curve="linear", weapon="M416")
        strong = _make_engine(strength=50, curve="linear", weapon="M416")
        y_weak = _spray(weak, 15)[-1][0]
        y_strong = _spray(strong, 15)[-1][0]
        assert y_strong > y_weak

    def test_output_bounded(self):
        engine = _make_engine(strength=200, curve="linear")
        out = _spray(engine, 60)
        assert all(abs(y) <= 18000 for y, _ in out)
        assert all(abs(x) <= 18000 for y, x in out)

    def test_horizontal_strength_pulls_x(self):
        engine = _make_engine(strength=30, x_strength=20, curve="linear")
        out = _spray(engine, 30)
        assert any(x != 0 for _, x in out)


class TestCurveShapes:

    def _preset(self, curve, strength=65):
        return {"strength": strength, "x_strength": 0, "ticks": 60, "curve": curve}

    def test_apply_tick_ease_out_decays(self):
        engine = RecoilEngine()
        first = engine.apply_tick(0, 60, 0, 0, self._preset("ease_out"), recoil_y_gate=False)
        last = engine.apply_tick(59, 60, 0, 0, self._preset("ease_out"), recoil_y_gate=False)
        assert first[0] > last[0]

    def test_apply_tick_linear_stays_flat(self):
        engine = RecoilEngine()
        a = engine.apply_tick(5, 60, 0, 0, self._preset("linear"), recoil_y_gate=False)
        b = engine.apply_tick(55, 60, 0, 0, self._preset("linear"), recoil_y_gate=False)
        assert a[0] == b[0] == 65 * 90

    def test_apply_tick_ease_in_ramps_up(self):
        engine = RecoilEngine()
        first = engine.apply_tick(0, 60, 0, 0, self._preset("ease_in"), recoil_y_gate=False)
        last = engine.apply_tick(59, 60, 0, 0, self._preset("ease_in"), recoil_y_gate=False)
        assert last[0] > first[0]

    def test_apply_tick_exponential_decays_fast(self):
        engine = RecoilEngine()
        first = engine.apply_tick(0, 60, 0, 0, self._preset("exponential"), recoil_y_gate=False)
        last = engine.apply_tick(59, 60, 0, 0, self._preset("exponential"), recoil_y_gate=False)
        assert last[0] < first[0]

    def test_process_fallback_honors_linear_curve(self):
        # Fallback (arma sem preset): curva linear = pull constante
        engine = _make_engine(strength=30, curve="linear", weapon="M416")
        out = _spray(engine, 30)
        assert abs(out[-1][0] - 2700) <= 15

    def test_process_fallback_honors_ease_in_curve(self):
        engine = _make_engine(strength=30, curve="ease_in", weapon="M416")
        out = _spray(engine, 60)
        assert out[-1][0] > out[0][0]


class TestYGate:

    def test_pulling_down_reduces_pull(self):
        engine = _make_engine(strength=30, curve="linear", weapon="FURY AR")
        no_gate = _spray(engine, 15, ry_raw=0)[-1][0]
        gated = _spray(engine, 15, ry_raw=16000)[-1][0]
        assert gated < no_gate

    def test_gate_disabled_no_reduction(self):
        engine = _make_engine(strength=30, curve="linear", weapon="FURY AR",
                              y_gate=False)
        no_gate = _spray(engine, 15, ry_raw=0)[-1][0]
        with_gate_off = _spray(engine, 15, ry_raw=16000)[-1][0]
        assert abs(with_gate_off - no_gate) <= 1

    def test_extreme_pull_gated_to_floor(self):
        engine = _make_engine(strength=30, curve="linear", weapon="FURY AR")
        out = _spray(engine, 15, ry_raw=32767)
        assert out[-1][0] >= 0
        assert out[-1][0] < 500


class TestXGate:

    def test_moving_right_reduces_x_pull(self):
        engine = _make_engine(strength=30, x_strength=20, curve="linear")
        no_gate = _spray(engine, 15, rx_raw=0)
        gated = _spray(engine, 15, rx_raw=16000)
        assert abs(gated[-1][1]) < abs(no_gate[-1][1])

    def test_small_stick_movement_untouched(self):
        engine = _make_engine(strength=30, x_strength=20, curve="linear")
        small = _spray(engine, 15, rx_raw=1500)
        zero = _spray(engine, 15, rx_raw=0)
        assert small[-1][1] == zero[-1][1]


class TestBloomCompensation:

    def test_moving_pulls_more_than_standing(self):
        engine = _make_engine(strength=30, curve="linear", weapon="FURY AR")
        standing = _spray(engine, 15, is_moving=False)[-1][0]
        moving = _spray(engine, 15, is_moving=True)[-1][0]
        assert moving > standing

    def test_ads_scales_bloom_down(self):
        engine = _make_engine(strength=30, curve="linear", weapon="FURY AR")
        hip_moving = _spray(engine, 15, is_aiming=False, is_moving=True)[-1][0]
        ads_moving = _spray(engine, 15, is_aiming=True, is_moving=True)[-1][0]
        assert ads_moving < hip_moving

    def test_bloom_disabled_no_delta(self):
        engine = _make_engine(strength=30, curve="linear", weapon="FURY AR")
        standing = _spray(engine, 15, is_moving=False)[-1][0]
        moving = _spray(engine, 15, is_moving=True)[-1][0]
        assert moving > standing
        standing_no_bloom = _spray(engine, 15, is_moving=False, bloom=False)[-1][0]
        moving_no_bloom = _spray(engine, 15, is_moving=True, bloom=False)[-1][0]
        assert standing_no_bloom == moving_no_bloom


class TestRecoilAdaptRamp:

    def test_level_0_no_ramp(self):
        engine = _make_engine(strength=30, curve="linear", weapon="FURY AR",
                              recoil_adapt=0)
        out = _spray(engine, 20)
        assert out[-1][0] <= out[5][0] + 5

    def test_high_level_ramps_multiplier(self):
        engine = _make_engine(strength=30, curve="linear", weapon="FURY AR",
                              recoil_adapt=3)
        out = _spray(engine, 20)
        assert out[-1][0] > out[1][0]

    def test_ramp_resets_after_ceasefire(self):
        adapt = RecoilAdaptEngine()
        m1 = adapt.get_multiplier(3, True)
        m2 = adapt.get_multiplier(3, True)
        m3 = adapt.get_multiplier(3, True)
        m4 = adapt.get_multiplier(3, True)
        m5 = adapt.get_multiplier(3, True)
        assert m5 > m1
        adapt.reset()
        assert adapt.get_multiplier(3, True) == m1

    def test_level_bounds(self):
        adapt = RecoilAdaptEngine()
        assert adapt.get_multiplier(0, True) == 1.0
        assert adapt.get_multiplier(9, True) <= 1.50
        assert adapt.get_multiplier(3, False) == 1.0


class TestSmartLearn:

    def test_category_detection(self):
        sl = SmartLearnEngine()
        assert sl.get_category("M416") == "AR"
        assert sl.get_category("VECTOR") == "SMG"
        assert sl.get_category("M249") == "LMG"
        assert sl.get_category("AWM") == "SNIPER"
        assert sl.get_category("DEAGLE") == "PISTOL"
        assert sl.get_category("UNKNOWN GUN") == "AR"

    def test_no_samples_identity(self):
        sl = SmartLearnEngine()
        assert sl.compute_multipliers("M416") == (1.0, 1.0)

    def test_multipliers_clamped(self):
        sl = SmartLearnEngine()
        for _ in range(12):
            sl.observe("M416", 30000, 30000, is_shooting=True)
        v, h = sl.compute_multipliers("M416")
        assert 0.70 <= v <= 1.30
        assert 0.70 <= h <= 1.30

    def test_observe_ignores_not_shooting(self):
        sl = SmartLearnEngine()
        for _ in range(12):
            sl.observe("M416", 30000, 30000, is_shooting=False)
        assert sl.compute_multipliers("M416") == (1.0, 1.0)

    def test_engine_applies_smart_learn(self):
        engine = _make_engine(strength=30, curve="linear", weapon="FURY AR",
                              smart_learn=True)
        out = _spray(engine, 60, ry_raw=15000, rx_raw=15000)
        assert all(abs(y) <= 18000 for y, _ in out)


class TestWeaponAutoDetect:

    def test_exact_preset_name(self):
        engine = _make_engine(weapon="SPIRE RIFLE")
        assert engine._pattern is not None

    def test_category_fallback(self):
        engine = _make_engine(weapon="AR")
        assert engine._pattern is not None
        assert engine._weapon == "FURY AR"

    def test_smg_category_fallback(self):
        engine = _make_engine(weapon="SMG")
        assert engine._weapon == "VEILED PRECISION SMG"

    def test_unknown_weapon_falls_back_to_config(self):
        engine = _make_engine(strength=40, curve="linear", weapon="M416")
        assert engine._pattern is None
        out = _spray(engine, 15)
        assert all(y > 0 for y, _ in out)
        assert abs(out[-1][0] - 3600) <= 15


class TestRecoilPattern:

    def _pattern(self):
        return RecoilPattern(
            name="TEST",
            category="AR",
            points=[(0, 100, 0), (30, 300, 50), (60, 600, 100)],
            total_ticks=60,
        )

    def test_interpolation_midpoint(self):
        pat = self._pattern()
        y, x = pat.get_offset_at_tick(15)
        assert y == 200
        assert x == 25

    def test_exact_point(self):
        pat = self._pattern()
        y, _ = pat.get_offset_at_tick(0)
        assert y == 100
        y, _ = pat.get_offset_at_tick(59)
        assert y == 590
        # tick >= total_ticks clampa para total_ticks-1
        y_clamped, _ = pat.get_offset_at_tick(60)
        assert y_clamped == 590

    def test_tick_clamped(self):
        pat = self._pattern()
        assert pat.get_offset_at_tick(-5) == pat.get_offset_at_tick(0)
        assert pat.get_offset_at_tick(999) == pat.get_offset_at_tick(60)

    def test_empty_pattern_zero(self):
        pat = RecoilPattern(name="EMPTY")
        assert pat.get_offset_at_tick(10) == (0, 0)


class TestBezierCurve:

    def test_evaluate_bounds(self):
        curve = BezierCurve(0, 30, 60, 90)
        for t in (0.0, 0.25, 0.5, 0.75, 1.0):
            v = curve.evaluate(t)
            assert 0 <= v <= 90

    def test_evaluate_endpoints(self):
        curve = BezierCurve(0, 30, 60, 90)
        assert curve.evaluate(0.0) == 0
        assert curve.evaluate(1.0) == 90

    def test_evaluate_clamps_t(self):
        curve = BezierCurve(0, 30, 60, 90)
        assert curve.evaluate(-1.0) == 0
        assert curve.evaluate(2.0) == 90

    def test_derivative_positive_for_increasing(self):
        curve = BezierCurve(0, 30, 60, 90)
        assert curve.derivative(0.5) > 0


class TestRecoilStateReturn:

    def test_return_decays_to_zero(self):
        state = RecoilState()
        state.return_offset_y = 5000
        state.return_offset_x = 3000
        for _ in range(30):
            state.apply_return(0.7)
        assert state.return_offset_y == 0
        assert state.return_offset_x == 0

    def test_capture_and_return(self):
        state = RecoilState()
        state.capture_offset(800, 400)
        assert state.last_offset_y == 800
        assert state.last_offset_x == 400

    def test_reset_zeroes_return(self):
        state = RecoilState()
        state.return_offset_y = 900
        state.reset(delay_ms=20)
        assert state.return_offset_y == 0
        assert state.delay_remaining == 20


class TestRecoilTestbed:

    def test_full_spray_bounded_and_positive(self):
        testbed = RecoilTestbed(RecoilEngine())
        config = {"weapon": "AR", "strength": 65, "ticks": 60}
        points = testbed.get_pattern(config, samples=60)
        assert len(points) == 60
        assert all(y >= 0 and abs(y) <= 18000 for y, _ in points)
        assert any(y > 0 for y, _ in points)

    def test_shotgun_no_recoil(self):
        testbed = RecoilTestbed(RecoilEngine())
        points = testbed.get_pattern({"weapon": "Shotgun", "strength": 0}, samples=5)
        assert all(y == 0 for y, _ in points)

    def test_heavier_weapon_more_total_pull(self):
        light = RecoilTestbed(RecoilEngine())
        heavy = RecoilTestbed(RecoilEngine())
        pts_l = light.get_pattern({"weapon": "AR", "strength": 40}, samples=20)
        pts_h = heavy.get_pattern({"weapon": "AR", "strength": 80}, samples=20)
        assert sum(y for y, _ in pts_h) > sum(y for y, _ in pts_l)


class TestUniversalPresetSweep:

    @pytest.mark.parametrize("preset_name", list(RECOIL_PRESETS.keys()))
    def test_every_preset_is_sane(self, preset_name):
        preset = RECOIL_PRESETS[preset_name]
        engine = _make_engine(
            strength=preset["strength"],
            x_strength=preset["x_strength"],
            ticks=preset["ticks"],
            curve=preset["curve"],
            weapon=preset_name,
        )
        ticks = preset["ticks"]
        out = _spray(engine, ticks, is_aiming=True)
        assert len(out) == ticks
        total_y = 0.0
        for y, x in out:
            assert math.isfinite(y) and math.isfinite(x)
            assert -18000 <= y <= 18000
            assert -18000 <= x <= 18000
            assert y >= 0, f"{preset_name} empurrou para cima no tick"
            total_y += y
        if preset["strength"] > 0:
            assert total_y > 0, f"{preset_name} não compensa nada"
        else:
            assert total_y == 0, f"{preset_name} sem strength mas puxou"

    def test_ads_and_hip_never_overshoot_clamp(self):
        for preset_name, preset in RECOIL_PRESETS.items():
            engine = _make_engine(
                strength=preset["strength"],
                x_strength=preset["x_strength"],
                ticks=preset["ticks"],
                curve=preset["curve"],
                weapon=preset_name,
            )
            out = _spray(engine, preset["ticks"], is_aiming=False)
            assert all(abs(y) <= 18000 and abs(x) <= 18000 for y, x in out)

    def test_full_auto_ar_total_compensation_reasonable(self):
        engine = _make_engine(strength=30, curve="linear", weapon="FURY AR")
        out = _spray(engine, 50)
        total = sum(y for y, _ in out)
        assert 50_000 < total < 500_000, f"Compensação total irreal: {total}"

    def test_reset_clears_state(self):
        engine = _make_engine()
        _spray(engine, 30)
        engine.reset()
        assert engine.state == AntiRecoilState()
        assert engine.state.tick == 0


class TestUniversalFallbackConfig:

    UNKNOWN_WEAPON = "UNMATCHED AR-77"

    def _fallback_engine(self):
        engine = RecoilEngine(RecoilConfig.from_dict({"recoil_enabled": True}))
        engine.set_weapon(self.UNKNOWN_WEAPON)
        engine._active_delay_ms = 0.0
        assert engine._pattern is None
        return engine

    def _pattern_engine(self, preset_name: str):
        engine = RecoilEngine(RecoilConfig.from_dict({"recoil_enabled": True}))
        engine.set_weapon(preset_name)
        assert engine._pattern is not None
        return engine

    def test_fallback_uses_universal_defaults(self):
        engine = self._fallback_engine()
        cfg = engine.config
        assert cfg.strength == 35
        assert cfg.curve == "ease_out"
        out = _spray(engine, 10)
        assert all(y > 0 for y, _ in out)

    def test_fallback_bounded_everywhere(self):
        for preset_name in RECOIL_PRESETS:
            engine = self._fallback_engine()
            ticks = RECOIL_PRESETS[preset_name]["ticks"]
            for is_aiming in (True, False):
                out = _spray(engine, ticks, is_aiming=is_aiming)
                for y, x in out:
                    assert math.isfinite(y) and math.isfinite(x)
                    assert -18000 <= y <= 18000, (preset_name, is_aiming, y)
                    assert -18000 <= x <= 18000, (preset_name, is_aiming, x)

    def test_fallback_covers_recoil_weapons(self):
        for preset_name, preset in RECOIL_PRESETS.items():
            if preset["strength"] == 0:
                continue
            ticks = preset["ticks"]
            fallback_out = _spray(self._fallback_engine(), ticks)
            pattern_out = _spray(self._pattern_engine(preset_name), ticks)
            fallback_total = sum(y for y, _ in fallback_out)
            pattern_total = sum(y for y, _ in pattern_out)
            ratio = fallback_total / max(pattern_total, 1)
            assert ratio >= 0.70, (
                f"{preset_name}: fallback universal ({fallback_total:.0f}) "
                f"cobre só {ratio:.2f} do preset ({pattern_total:.0f})"
            )

    def test_fallback_overshoot_bounded_on_zero_recoil_weapons(self):
        for preset_name, preset in RECOIL_PRESETS.items():
            if preset["strength"] != 0:
                continue
            ticks = preset["ticks"]
            out = _spray(self._fallback_engine(), ticks)
            total = sum(y for y, _ in out)
            assert 0 < total <= 8000, (
                f"{preset_name}: fallback universal puxou {total:.0f} "
                f"numa arma sem recoil"
            )

    def test_default_sweep_presets_still_exact(self):
        for preset_name in RECOIL_PRESETS:
            engine = self._pattern_engine(preset_name)
            out = _spray(engine, RECOIL_PRESETS[preset_name]["ticks"])
            assert all(math.isfinite(y) and math.isfinite(x) for y, x in out)


USER_WEAPON_NAMES_PT = [
    "Rifle de assalto BelicoForjado Modular",
    "Espingarda De alcance estendido",
    "Escopeta atacante",
    "Pistola tiro certeiro",
    "Pistola sentinela Modular",
    "Espingarda automática de perito",
    "Rifle Pimâculo",
    "Pistola do John Wick",
]

EXPECTED_USER_PRESETS = [
    "WARFORGED AR",
    "EXTENDING FOCUS SHOTGUN",
    "AUTO SHOTGUN",
    "BANK SHOT PISTOL",
    "SENTRY PISTOL",
    "MAVEN AUTO SHOTGUN",
    "PINNACLE RIFLE",
    "LANCEHEAD PISTOL",
]


class TestUserWeapons:

    def test_pt_names_resolve_to_presets(self):
        for pt_name, expected in zip(USER_WEAPON_NAMES_PT, EXPECTED_USER_PRESETS):
            engine = RecoilEngine(RecoilConfig(enabled=True))
            engine.set_weapon(pt_name)
            assert engine._pattern is not None, f"{pt_name} não resolveu"
            assert engine._weapon == expected, f"{pt_name} -> {engine._weapon}"

    def test_english_names_resolve_to_presets(self):
        for expected in EXPECTED_USER_PRESETS:
            engine = RecoilEngine(RecoilConfig(enabled=True))
            engine.set_weapon(expected)
            assert engine._pattern is not None, f"{expected} não resolveu"

    def test_quase_estatico_full_spray(self):
        for preset_name in EXPECTED_USER_PRESETS:
            preset = RECOIL_PRESETS[preset_name]
            engine = _make_engine(
                strength=preset["strength"],
                x_strength=preset["x_strength"],
                ticks=preset["ticks"],
                curve=preset["curve"],
                weapon=preset_name,
            )
            out = _spray(engine, preset["ticks"], is_aiming=True)
            for tick, (y, x) in enumerate(out):
                assert math.isfinite(y) and math.isfinite(x), preset_name
                assert 0 <= y <= 18000, (preset_name, tick, y)
                assert abs(x) <= 18000, (preset_name, tick, x)
            total = sum(y for y, _ in out)
            assert total > 0, f"{preset_name} não compensa nada"

    def test_quase_estatico_hip_never_saturates(self):
        for preset_name in EXPECTED_USER_PRESETS:
            preset = RECOIL_PRESETS[preset_name]
            engine = _make_engine(
                strength=preset["strength"],
                x_strength=preset["x_strength"],
                ticks=preset["ticks"],
                curve=preset["curve"],
                weapon=preset_name,
            )
            out = _spray(engine, preset["ticks"], is_aiming=False)
            assert all(abs(y) <= 18000 and abs(x) <= 18000 for y, x in out), preset_name

    def test_universal_fallback_covers_user_weapons(self):
        for preset_name in EXPECTED_USER_PRESETS:
            preset = RECOIL_PRESETS[preset_name]
            ticks = preset["ticks"]
            fallback_out = _spray(self._fallback_engine(), ticks)
            pattern_out = _spray(_make_engine(weapon=preset_name), ticks)
            fb = sum(y for y, _ in fallback_out)
            pat = sum(y for y, _ in pattern_out)
            assert fb >= 0.70 * pat, f"{preset_name}: fallback cobre {fb/pat:.2f}"

    def _fallback_engine(self):
        engine = RecoilEngine(RecoilConfig(enabled=True))
        engine.set_weapon("UNMATCHED AR-77")
        engine._active_delay_ms = 0.0
        assert engine._pattern is None
        return engine


class TestSimpleMode:
    """Simple Mode: pull plano e constante estilo script LUA do G-Hub."""

    def test_simple_mode_flat_pull_while_firing(self):
        cfg = RecoilConfig(enabled=True, simple_mode=True, simple_rate=4)
        engine = AntiRecoilEngine(cfg)
        out = []
        for tick in range(10):
            y, x = engine.process(tick, is_shooting=True, is_aiming=True,
                                  is_moving=False, ry_raw=0, rx_raw=0,
                                  delta_ms=7.0)
            out.append((y, x))
        assert all(y > 0 and x == 0 for y, x in out), out
        assert out[0][0] == pytest.approx(4 * 90, abs=2)

    def test_simple_mode_time_scaled(self):
        cfg = RecoilConfig(enabled=True, simple_mode=True, simple_rate=4)
        engine = AntiRecoilEngine(cfg)
        _, y1, *_ = engine.process(0, True, True, False, 0, 0, delta_ms=3.5)
        engine2 = AntiRecoilEngine(cfg)
        _, y2, *_ = engine2.process(0, True, True, False, 0, 0, delta_ms=14.0)
        assert abs(y2 - 2 * y1) <= 4

    def test_simple_mode_zero_when_not_firing(self):
        cfg = RecoilConfig(enabled=True, simple_mode=True, simple_rate=4)
        engine = AntiRecoilEngine(cfg)
        engine.process(0, True, True, False, 0, 0, delta_ms=7.0)
        y, x = engine.process(5, False, True, False, 0, 0, delta_ms=7.0)
        assert (y, x) == (0, 0)

    def test_simple_mode_capped(self):
        cfg = RecoilConfig(enabled=True, simple_mode=True, simple_rate=20)
        engine = AntiRecoilEngine(cfg)
        y, _ = engine.process(0, True, True, False, 0, 0, delta_ms=1000.0)
        assert abs(y) <= 18000

    def test_simple_mode_disabled_by_default(self):
        cfg = RecoilConfig.from_dict({})
        assert cfg.simple_mode is False
        assert cfg.simple_rate == 4

    def test_from_dict_roundtrip(self):
        cfg = RecoilConfig.from_dict({"recoil_simple_mode": True, "recoil_simple_rate": 9})
        assert cfg.simple_mode is True
        assert cfg.simple_rate == 9
        d = {}
        d["recoil_simple_mode"] = cfg.simple_mode
        d["recoil_simple_rate"] = cfg.simple_rate
        cfg2 = RecoilConfig.from_dict(d)
        assert cfg2.simple_mode is True
        assert cfg2.simple_rate == 9


class TestInitialKick:

    def test_default_off(self):
        cfg = RecoilConfig.from_dict({})
        assert cfg.initial_kick_mult == 1.0
        assert cfg.initial_kick_ticks == 6
        assert cfg.headshot_assist is False
        assert cfg.headshot_assist_pull == 700

    def test_kick_boosts_first_tick(self):
        normal = _make_engine(strength=65)
        kicked = _make_engine(strength=65, initial_kick_mult=1.5, initial_kick_ticks=6)
        y_n, _ = normal.process(0, True, True, False, 0, 0, 16.67)
        y_k, _ = kicked.process(0, True, True, False, 0, 0, 16.67)
        assert y_k > y_n

    def test_kick_decays_over_ticks(self):
        eng = lambda: _make_engine(strength=65, initial_kick_mult=1.5, initial_kick_ticks=6)
        y0, _ = eng().process(0, True, True, False, 0, 0, 16.67)
        y2, _ = eng().process(2, True, True, False, 0, 0, 16.67)
        y6, _ = eng().process(6, True, True, False, 0, 0, 16.67)
        assert y0 > y2 > y6

    def test_kick_ends_at_window(self):
        kicked = _make_engine(strength=65, initial_kick_mult=1.5, initial_kick_ticks=6)
        normal = _make_engine(strength=65)
        y_k, _ = kicked.process(6, True, True, False, 0, 0, 16.67)
        y_n, _ = normal.process(6, True, True, False, 0, 0, 16.67)
        assert y_k == y_n  # fora da janela = multiplicador 1.0

    def test_kick_applies_to_x_axis(self):
        # FURY AR tem x_strength no pattern; tick 3 = dentro da janela de
        # kick (6 ticks) e com seno>0 no eixo X
        normal = _make_engine(strength=0, x_strength=10, weapon="FURY AR")
        kicked = _make_engine(strength=0, x_strength=10, weapon="FURY AR",
                              initial_kick_mult=1.5, initial_kick_ticks=6)
        _, x_n = normal.process(3, True, True, False, 0, 0, 16.67)
        _, x_k = kicked.process(3, True, True, False, 0, 0, 16.67)
        assert x_k > x_n


class TestHeadshotAssist:

    def test_off_by_default_unchanged(self):
        off = _make_engine(strength=65)
        on = _make_engine(strength=65, headshot_assist=True, headshot_assist_pull=700)
        y_off, _ = off.process(0, True, True, False, 0, 0, 16.67)          # ADS
        y_on, _ = on.process(0, True, True, False, 0, 0, 16.67)
        assert y_off == y_on  # ADS: sem efeito

    def test_hipfire_pulls_up(self):
        off = _make_engine(strength=65)
        on = _make_engine(strength=65, headshot_assist=True, headshot_assist_pull=700)
        y_off, _ = off.process(0, True, False, False, 0, 0, 16.67)         # hipfire
        y_on, _ = on.process(0, True, False, False, 0, 0, 16.67)
        assert y_on < y_off  # puxa para cima no hipfire

    def test_pull_strength_scales(self):
        soft = _make_engine(strength=65, headshot_assist=True, headshot_assist_pull=300)
        hard = _make_engine(strength=65, headshot_assist=True, headshot_assist_pull=2000)
        y_soft, _ = soft.process(0, True, False, False, 0, 0, 16.67)
        y_hard, _ = hard.process(0, True, False, False, 0, 0, 16.67)
        assert y_hard < y_soft

    def test_simple_mode_headshot_assist(self):
        cfg = RecoilConfig(enabled=True, simple_mode=True, simple_rate=4,
                           headshot_assist=True, headshot_assist_pull=700)
        engine = AntiRecoilEngine(cfg)
        y, _ = engine.process(0, True, False, False, 0, 0, delta_ms=7.0)
        assert y < 4 * 90  # reduzido pelo pull para cima

    def test_clamped_lower_bound(self):
        cfg = RecoilConfig(enabled=True, simple_mode=True, simple_rate=4,
                           headshot_assist=True, headshot_assist_pull=50000)
        engine = AntiRecoilEngine(cfg)
        y, _ = engine.process(0, True, False, False, 0, 0, delta_ms=7.0)
        assert y >= -18000


class TestPerWeaponDelay:
    """Delay do primeiro tiro vindo do preset da arma (Zen per-weapon)."""

    def test_delay_blocks_first_ticks(self):
        engine = _make_engine(strength=30, curve="linear", weapon="FURY AR", delay_ms=35)
        y0, _ = engine.process(0, True, True, False, 0, 0, 16.67)
        y1, _ = engine.process(1, True, True, False, 0, 0, 16.67)
        y2, _ = engine.process(2, True, True, False, 0, 0, 16.67)
        assert (y0, y1) == (0, 0)
        assert y2 > 0

    def test_zero_delay_pulls_immediately(self):
        engine = _make_engine(strength=30, curve="linear", weapon="FURY AR", delay_ms=0)
        y0, _ = engine.process(0, True, True, False, 0, 0, 16.67)
        assert y0 > 0

    def test_set_weapon_loads_preset_delay(self):
        engine = RecoilEngine(RecoilConfig(enabled=True))
        engine.set_weapon("SPIRE RIFLE")
        assert engine._active_delay_ms == 60


class TestBurstMode:
    """Burst Mode: pull em rajadas com pausa (reset de recoil no jogo)."""

    def _burst_engine(self):
        from nocrosshair.core.config import RecoilRuntimeConfig
        engine = _make_engine(strength=30, curve="linear", weapon="FURY AR", delay_ms=0)
        engine.update_runtime(RecoilRuntimeConfig(
            burst_mode=True, burst_count=3, burst_delay_ms=50,
        ))
        return engine

    def test_burst_alternates_pull_and_idle(self):
        engine = self._burst_engine()
        out = [engine.process(t, True, True, False, 0, 0, 16.67)[0] for t in range(10)]
        assert out[0] > 0 and out[1] > 0 and out[2] > 0   # janela de rajada
        assert out[3] == 0 and out[4] == 0                 # pausa (50ms / 16.67 = 3 ticks)

    def test_burst_off_continuous(self):
        engine = _make_engine(strength=30, curve="linear", weapon="FURY AR", delay_ms=0)
        out = [engine.process(t, True, True, False, 0, 0, 16.67)[0] for t in range(6)]
        assert all(y > 0 for y in out)


class TestReturnAndSmoothing:
    """Return speed e Smoothing — configs que antes eram mortas."""

    def test_return_speed_decays_ema(self):
        slow = _make_engine(strength=30, weapon="FURY AR", delay_ms=0, return_speed=0.90)
        fast = _make_engine(strength=30, weapon="FURY AR", delay_ms=0, return_speed=0.50)
        slow.state.ema_y = 8000.0
        fast.state.ema_y = 8000.0
        y_slow, _ = slow.process(0, False, True, False, 0, 0, 16.67)
        y_fast, _ = fast.process(0, False, True, False, 0, 0, 16.67)
        assert y_fast < y_slow < 8000.0

    def test_smoothing_slows_convergence(self):
        from nocrosshair.core.config import RecoilRuntimeConfig
        crisp = _make_engine(strength=30, curve="linear", weapon="FURY AR", delay_ms=0)
        smooth = _make_engine(strength=30, curve="linear", weapon="FURY AR", delay_ms=0)
        smooth.update_runtime(RecoilRuntimeConfig(smoothing=100))
        y_crisp, _ = crisp.process(0, True, True, False, 0, 0, 16.67)
        y_smooth, _ = smooth.process(0, True, True, False, 0, 0, 16.67)
        assert y_smooth < y_crisp

    def test_horizontal_pull_adds_bias(self):
        from nocrosshair.core.config import RecoilRuntimeConfig
        engine = _make_engine(strength=30, x_strength=0, curve="linear", weapon="FURY AR", delay_ms=0)
        engine.update_runtime(RecoilRuntimeConfig(horizontal_pull=500))
        _, x = engine.process(0, True, True, False, 0, 0, 16.67)
        assert x == 500
