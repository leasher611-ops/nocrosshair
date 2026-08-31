#!/usr/bin/env python3

import math
import pytest
from nocrosshair.core.config import AimAssistConfig
from nocrosshair.features.aim_advanced import (
    OneEuroFilter, PredictiveTracker, AdhesionBuffer,
)
from nocrosshair.features.aim_assist import AimAssistEngine, AimAssistPipeline, AimAssistPresets


class TestOneEuroFilter:

    def test_first_sample_passthrough(self):
        f = OneEuroFilter(min_cutoff=1.0, beta=0.05, d_cutoff=1.0)
        assert f.filter(1000.0, 16.0) == 1000.0

    def test_converges_to_constant(self):
        f = OneEuroFilter(min_cutoff=1.0, beta=0.05, d_cutoff=1.0)
        out = 0.0
        for _ in range(200):
            out = f.filter(500.0, 16.0)
        assert math.isclose(out, 500.0, abs_tol=1.0)

    def test_smooths_jitter(self):
        """Uma onda quadrada (jitter máximo) tem amplitude atenuada."""
        f = OneEuroFilter(min_cutoff=1.0, beta=0.0, d_cutoff=1.0)
        outs = []
        for i in range(60):
            outs.append(f.filter(1000.0 if i % 2 == 0 else 0.0, 16.0))
        amplitude = max(outs) - min(outs)
        assert amplitude < 1000.0

    def test_high_speed_responds_faster(self):
        """Com beta > 0, movimento rápido abre o cutoff (menos lag)."""
        slow = OneEuroFilter(min_cutoff=1.0, beta=0.05, d_cutoff=1.0)
        for _ in range(20):
            slow.filter(0.0, 16.0)
        s = slow.filter(500.0, 16.0)  # salto de 500
        assert 0.0 < s < 500.0

    def test_reset(self):
        f = OneEuroFilter()
        f.filter(1000.0, 16.0)
        f.reset()
        assert f.filter(250.0, 16.0) == 250.0

    def test_deterministic(self):
        a = OneEuroFilter()
        b = OneEuroFilter()
        seq = [100.0, 250.0, 120.0, 400.0, 80.0]
        for x in seq:
            assert a.filter(x, 16.0) == b.filter(x, 16.0)


class TestPredictiveTracker:

    def _tracker(self, **kw):
        defaults = dict(vel_alpha=1.0, accel_alpha=0.0, lead_horizon_ms=40.0,
                        min_speed=1.0, max_lead=100000.0, consistency=1)
        defaults.update(kw)
        return PredictiveTracker(**defaults)

    def test_first_call_returns_zero(self):
        t = self._tracker()
        assert t.predict(1000.0, 500.0, 16.0) == (0.0, 0.0)

    def test_leads_in_direction_of_movement(self):
        t = self._tracker()
        t.predict(0.0, 0.0, 16.0)
        lead_x, lead_y = t.predict(100.0, 0.0, 16.0)
        assert lead_x > 0.0
        assert lead_y == 0.0

    def test_lead_bounded_by_max_lead(self):
        t = self._tracker(max_lead=100.0)
        t.predict(0.0, 0.0, 16.0)
        lead_x, _ = t.predict(10000.0, 0.0, 16.0)
        assert math.hypot(lead_x, 0.0) <= 100.0 + 1e-6

    def test_below_min_speed_no_lead(self):
        t = self._tracker(min_speed=1000.0)
        t.predict(0.0, 0.0, 16.0)
        lead_x, lead_y = t.predict(100.0, 0.0, 16.0)
        assert lead_x == 0.0
        assert lead_y == 0.0

    def test_consistency_gate(self):
        t = self._tracker(consistency=3)
        t.predict(0.0, 0.0, 16.0)
        assert t.predict(100.0, 0.0, 16.0) == (0.0, 0.0)
        assert t.predict(200.0, 0.0, 16.0) == (0.0, 0.0)
        lead_x, _ = t.predict(300.0, 0.0, 16.0)
        assert lead_x > 0.0

    def test_acceleration_boost(self):
        base = self._tracker(accel_alpha=0.0)
        accel = self._tracker(accel_alpha=0.3)
        for t in (base, accel):
            t.predict(0.0, 0.0, 16.0)
        for x in (100.0, 300.0, 600.0, 1000.0):
            lb, _ = base.predict(x, 0.0, 16.0)
            la, _ = accel.predict(x, 0.0, 16.0)
        assert la > lb  # aceleração adianta mais em movimento acelerado

    def test_reset(self):
        t = self._tracker()
        t.predict(0.0, 0.0, 16.0)
        t.predict(500.0, 0.0, 16.0)
        t.reset()
        assert t.predict(100.0, 0.0, 16.0) == (0.0, 0.0)

    def test_follow_dir_steers_lead(self):
        """(Fase 2) follow_dir (direção do alvo) domina a direção do lead."""
        t = self._tracker(direction_blend=1.0)
        t.predict(0.0, 0.0, 16.0)
        # velocidade em +x, mas follow_dir aponta +y → lead sai em +y
        lead_x, lead_y = t.predict(100.0, 0.0, 16.0, follow_dir=(0.0, 1.0), confidence=0.5)
        assert lead_x == 0.0
        assert lead_y > 0.0

    def test_confidence_scales_lead(self):
        """(Fase 1) mais confiança = lead mais agressivo."""
        low = self._tracker()
        high = self._tracker()
        for t in (low, high):
            t.predict(0.0, 0.0, 16.0)
        lx, _ = low.predict(100.0, 0.0, 16.0, follow_dir=(1.0, 0.0), confidence=0.0)
        hx, _ = high.predict(100.0, 0.0, 16.0, follow_dir=(1.0, 0.0), confidence=1.0)
        assert hx > lx


class TestAdhesionBuffer:

    def _buf(self, **kw):
        defaults = dict(hold_ms=120.0, decay=0.35, axis_lock=0.0, min_mag=100.0)
        defaults.update(kw)
        return AdhesionBuffer(**defaults)

    def test_engaged_holding_passthrough(self):
        b = self._buf()
        rx, ry = b.apply(1000.0, 500.0, engaged=True, dt_ms=16.0, now=0.0)
        assert rx == 1000.0
        assert ry == 500.0

    def test_not_engaged_passthrough(self):
        b = self._buf()
        rx, ry = b.apply(1000.0, 500.0, engaged=False, dt_ms=16.0, now=0.0)
        assert rx == 1000.0
        assert ry == 500.0

    def test_release_holds_direction(self):
        b = self._buf()
        b.apply(1000.0, 0.0, engaged=True, dt_ms=16.0, now=0.0)
        rx, ry = b.apply(0.0, 0.0, engaged=True, dt_ms=16.0, now=0.0)
        assert rx > 0.0
        assert ry == 0.0

    def test_hold_decays_over_time(self):
        b = self._buf()
        b.apply(1000.0, 0.0, engaged=True, dt_ms=16.0, now=0.0)
        early, _ = b.apply(0.0, 0.0, engaged=True, dt_ms=16.0, now=0.0)
        late, _ = b.apply(0.0, 0.0, engaged=True, dt_ms=16.0, now=0.06)
        assert 0.0 < late < early

    def test_hold_expires(self):
        b = self._buf(hold_ms=120.0)
        b.apply(1000.0, 0.0, engaged=True, dt_ms=16.0, now=0.0)   # registra
        b.apply(0.0, 0.0, engaged=True, dt_ms=16.0, now=0.0)      # solta -> inicia hold
        rx, _ = b.apply(0.0, 0.0, engaged=True, dt_ms=16.0, now=0.2)  # passou hold_ms
        assert rx == 0.0

    def test_axis_lock_attenuates_minor_axis(self):
        b = self._buf(axis_lock=0.5)
        rx, ry = b.apply(1000.0, 200.0, engaged=True, dt_ms=16.0, now=0.0)
        assert rx == 1000.0
        assert math.isclose(ry, 100.0, abs_tol=1e-6)  # 200 * (1 - 0.5)

    def test_reset(self):
        b = self._buf()
        b.apply(1000.0, 0.0, engaged=True, dt_ms=16.0, now=0.0)
        b.reset()
        rx, ry = b.apply(0.0, 0.0, engaged=True, dt_ms=16.0, now=0.0)
        assert rx == 0.0
        assert ry == 0.0

    def test_no_direction_passthrough(self):
        """Sem direção prévia registrada, input pequeno NÃO pode ser zerado
        pela persistência (regressão: zerava micro-correções do jogador)."""
        b = self._buf()
        rx, ry = b.apply(50.0, 0.0, engaged=True, dt_ms=16.0, now=0.0)
        assert rx == 50.0
        assert ry == 0.0
        rx, ry = b.apply(50.0, 0.0, engaged=True, dt_ms=16.0, now=0.02)
        assert rx == 50.0


class TestPipelineWiring:

    def _pipeline(self, **overrides):
        cfg = AimAssistConfig(
            enabled=True,
            base_aa_enabled=False,
            rotational=False,
            pulse_level=0,
            anti_flinch=False,
            adaptive_strength=False,
            fn_strength_slider=0,
            sticky_enabled=False,
            sticky_strength=0.0,
            magnetic_pull=0,
            lock_enabled=False,
            head_assist_enabled=False,
            auto_rotation_enabled=False,
            enhanced_enabled=False,
            anti_shake_blend=0.0,
            aimlock_enabled=False,
            **overrides,
        )
        return AimAssistPipeline(AimAssistEngine(cfg))

    def test_advanced_stages_off_by_default(self):
        p = self._pipeline()
        rx, ry = p.apply(1000.0, 500.0, True, True, False, 16.0, p.aa_engine.cfg, 0, 0)
        assert rx == 1000.0
        assert ry == 500.0

    def test_one_euro_shake_bounded(self):
        p = self._pipeline(oef_enabled=True)
        for _ in range(5):
            rx, ry = p.apply(1500.0, 800.0, True, True, False, 16.0, p.aa_engine.cfg, 0, 0)
            assert math.isfinite(rx) and math.isfinite(ry)
            assert -32767 <= rx <= 32767
            assert -32767 <= ry <= 32767

    def test_predictive_tracker_adds_lead(self):
        p = self._pipeline(
            predictive_tracker_enabled=True,
            predictive_vel_alpha=1.0,
            predictive_min_speed=1.0,
            predictive_consistency=1,
            predictive_max_lead=100000,
        )
        cfg = p.aa_engine.cfg
        p.apply(0.0, 0.0, True, True, False, 16.0, cfg, 0, 0)
        rx, _ = p.apply(100.0, 0.0, True, True, False, 16.0, cfg, 0, 0)
        assert rx > 100.0

    def test_adhesion_buffer_persists_on_release(self):
        p = self._pipeline(
            adhesion_buffer_enabled=True,
            adhesion_hold_ms=120.0,
            adhesion_decay=0.35,
            adhesion_axis_lock=0.0,
            adhesion_min_mag=100.0,
        )
        cfg = p.aa_engine.cfg
        p.apply(1000.0, 0.0, True, True, False, 16.0, cfg, 0, 0)
        rx, _ = p.apply(0.0, 0.0, True, True, False, 16.0, cfg, 0, 0)
        assert rx > 0.0

    def test_delta_ms_zero_not_zeroed(self):
        """1º frame com delta_ms=0 (polling altíssimo) não pode zerar o output."""
        p = self._pipeline()
        cfg = p.aa_engine.cfg
        rx, ry = p.apply(1500.0, 0.0, True, True, True, 0.0, cfg, 0, 0)
        assert not (rx == 0.0 and ry == 0.0)

    def test_follow_assist_pulls_in_follow_dir(self):
        """Fase C/D: travado, o follow assist puxa na direção do acompanhamento."""
        p = self._pipeline(
            follow_assist_enabled=True,
            follow_assist_pull=400,
        )
        cfg = p.aa_engine.cfg
        # Empurra +x por vários frames para fixar follow_dir e o estágio LOCKED
        prev = (0.0, 0.0)
        for _ in range(15):
            prev = p.apply(800.0, 0.0, True, True, False, 16.0, cfg, prev[0], prev[1])
        # Ainda travado com input pequeno: o follow assist adiciona na direção +x
        rx, _ = p.apply(800.0, 0.0, True, True, False, 16.0, cfg, prev[0], prev[1])
        assert p.engagement.follow_dir[0] > 0.5
        assert rx > 800.0

    def test_follow_assist_off_no_pull(self):
        p = self._pipeline(follow_assist_enabled=False)
        cfg = p.aa_engine.cfg
        prev = (0.0, 0.0)
        for _ in range(15):
            prev = p.apply(800.0, 0.0, True, True, False, 16.0, cfg, prev[0], prev[1])
        rx, _ = p.apply(800.0, 0.0, True, True, False, 16.0, cfg, prev[0], prev[1])
        assert rx == 800.0


class TestConfigRoundtrip:

    def test_new_fields_roundtrip(self):
        cfg = AimAssistConfig.from_dict({
            "aa_oef_enabled": True,
            "aa_oef_min_cutoff": 1.5,
            "aa_oef_beta": 0.03,
            "aa_oef_d_cutoff": 2.0,
            "aa_predictive_tracker_enabled": True,
            "aa_predictive_vel_alpha": 0.2,
            "aa_predictive_accel_alpha": 0.08,
            "aa_predictive_lead_horizon_ms": 45.0,
            "aa_predictive_min_speed": 300.0,
            "aa_predictive_max_lead": 4000,
            "aa_predictive_consistency": 4,
            "aa_adhesion_buffer_enabled": True,
            "aa_adhesion_hold_ms": 90.0,
            "aa_adhesion_decay": 0.4,
            "aa_adhesion_axis_lock": 0.25,
            "aa_adhesion_min_mag": 150.0,
        })
        assert cfg.oef_enabled is True
        assert cfg.oef_min_cutoff == 1.5
        assert cfg.oef_beta == 0.03
        assert cfg.oef_d_cutoff == 2.0
        assert cfg.predictive_tracker_enabled is True
        assert cfg.predictive_vel_alpha == 0.2
        assert cfg.predictive_accel_alpha == 0.08
        assert cfg.predictive_lead_horizon_ms == 45.0
        assert cfg.predictive_min_speed == 300.0
        assert cfg.predictive_max_lead == 4000
        assert cfg.predictive_consistency == 4
        assert cfg.adhesion_buffer_enabled is True
        assert cfg.adhesion_hold_ms == 90.0
        assert cfg.adhesion_decay == 0.4
        assert cfg.adhesion_axis_lock == 0.25
        assert cfg.adhesion_min_mag == 150.0

    def test_app_config_roundtrip(self):
        from nocrosshair.core.config import AppConfig
        cfg = AimAssistPresets.fortnite_aimbot()
        app = AppConfig(aim_assist=cfg)
        d = app.to_dict()
        back = AppConfig.from_dict(d)
        assert back.aim_assist.oef_enabled is False
        assert back.aim_assist.predictive_tracker_enabled is True
        assert back.aim_assist.adhesion_buffer_enabled is True
        assert back.aim_assist.predictive_max_lead == 5500

    def test_defaults_off(self):
        cfg = AimAssistConfig()
        assert cfg.oef_enabled is False
        assert cfg.predictive_tracker_enabled is False
        assert cfg.adhesion_buffer_enabled is False


class TestAimbotPresetAdvanced:

    def test_aimbot_enables_advanced_aim(self):
        cfg = AimAssistPresets.fortnite_aimbot()
        assert cfg.oef_enabled is False
        assert cfg.predictive_tracker_enabled is True
        assert cfg.adhesion_buffer_enabled is True
        assert cfg.predictive_lead_horizon_ms == 60.0
        assert cfg.predictive_max_lead == 5500
        assert cfg.adhesion_hold_ms == 200.0

class TestAntiRecoilMLStability:

    def test_sgd_does_not_diverge_at_1ms(self):
        """Regressão: no tick de ~1ms o SGD explodia pra inf/nan e
        derrubava o pipeline inteiro (int(nan))."""
        from nocrosshair.features.advanced_aim_systems import AntiRecoilML
        ml = AntiRecoilML()
        for i in range(100):
            ml.start_shooting("weapon")
            ml.record_shot(2000.0, 800.0, 1.0, True, 5000.0)
            comp_x, comp_y = ml.compensate(0.0, 0.0, weapon="weapon",
                                           is_shooting=True, is_ads=True,
                                           delta_ms=1.0, distance=5000.0)
            import math
            assert not math.isnan(comp_x)
            assert not math.isnan(comp_y)
        for w in ml._weights_x + ml._weights_y:
            assert abs(w) <= 100.0
