"""
 nocrosshair — test_advanced_aim_systems.py
 ═══════════════════════════════════════════════════════════════════════════════
 TESTES PARA SISTEMAS DE AIM AVANÇADOS

 ═══════════════════════════════════════════════════════════════════════════════
"""

import pytest
import time
from nocrosshair.features.advanced_aim_systems import (
    AntiRecoilML,
    BallisticPredictor,
    SmartHeadshot,
    AdvancedAimPipeline,
    WeaponProfile,
)


class TestWeaponProfile:
    """Testes para WeaponProfile."""

    def test_initial_state(self):
        profile = WeaponProfile(name="AR")
        assert profile.name == "AR"
        assert profile.fire_rate_rpm == 600.0
        assert profile.bullet_speed_ms == 30000.0

    def test_to_dict(self):
        profile = WeaponProfile(name="AR", recoil_pattern_x=[1.0, 2.0])
        d = profile.to_dict()
        assert d["name"] == "AR"
        assert d["recoil_pattern_x"] == [1.0, 2.0]

    def test_from_dict(self):
        d = {"name": "SMG", "fire_rate_rpm": 900.0}
        profile = WeaponProfile.from_dict(d)
        assert profile.name == "SMG"
        assert profile.fire_rate_rpm == 900.0


class TestAntiRecoilML:
    """Testes para AntiRecoilML."""

    def test_initial_state(self):
        ml = AntiRecoilML()
        assert ml._current_weapon == ""
        assert ml._shot_count == 0

    def test_start_shooting(self):
        ml = AntiRecoilML()
        ml.start_shooting("AR")
        assert ml._current_weapon == "AR"

    def test_record_shot(self):
        ml = AntiRecoilML()
        ml.start_shooting("AR")
        ml.record_shot(10.0, 20.0, 16.67, True, 5000.0)
        assert ml._shot_count == 1
        assert len(ml._recoil_buffer) == 1

    def test_compensate_returns_tuple(self):
        ml = AntiRecoilML()
        rx, ry = ml.compensate(
            1000.0, 1000.0,
            weapon="AR",
            is_shooting=True,
            is_ads=True,
            delta_ms=16.67,
            distance=5000.0,
        )
        assert isinstance(rx, float)
        assert isinstance(ry, float)

    def test_compensate_not_shooting(self):
        ml = AntiRecoilML()
        rx, ry = ml.compensate(
            1000.0, 1000.0,
            weapon="AR",
            is_shooting=False,
            is_ads=True,
            delta_ms=16.67,
            distance=5000.0,
        )
        assert rx == 1000.0
        assert ry == 1000.0

    def test_online_learn(self):
        ml = AntiRecoilML()
        ml.start_shooting("AR")
        for i in range(10):
            ml.record_shot(float(i), float(i * 2), 16.67, True, 5000.0)
        assert ml._shot_count == 10
        profile = ml.get_profile("AR")
        assert profile is not None
        assert profile.learned_shots > 0

    def test_get_profile(self):
        ml = AntiRecoilML()
        ml.start_shooting("AR")
        ml.record_shot(10.0, 20.0, 16.67, True, 5000.0)
        profile = ml.get_profile("AR")
        assert profile is not None
        assert profile.name == "AR"

    def test_reset(self):
        ml = AntiRecoilML()
        ml.start_shooting("AR")
        ml.record_shot(10.0, 20.0, 16.67, True, 5000.0)
        ml.reset()
        assert ml._shot_count == 0
        assert len(ml._recoil_buffer) == 0


class TestBallisticPredictor:
    """Testes para BallisticPredictor."""

    def test_initial_state(self):
        bp = BallisticPredictor()
        assert bp._gravity == 980.0
        assert bp._bullet_speed == 30000.0

    def test_predict_returns_tuple(self):
        bp = BallisticPredictor()
        lead_x, lead_y = bp.predict(
            1000.0, 1000.0,
            1500.0, 1200.0,
            5000.0,
        )
        assert isinstance(lead_x, float)
        assert isinstance(lead_y, float)

    def test_gravity_drop(self):
        bp = BallisticPredictor()
        lead_x1, lead_y1 = bp.predict(
            1000.0, 1000.0,
            1500.0, 1200.0,
            5000.0,
        )
        bp.reset()
        lead_x2, lead_y2 = bp.predict(
            1000.0, 1000.0,
            1500.0, 1200.0,
            10000.0,
        )
        assert abs(lead_y2) > abs(lead_y1)

    def test_bullet_speed_effect(self):
        bp1 = BallisticPredictor()
        bp1._bullet_speed = 20000.0
        lead_x1, lead_y1 = bp1.predict(
            1000.0, 1000.0,
            1500.0, 1200.0,
            5000.0,
        )
        bp2 = BallisticPredictor()
        bp2._bullet_speed = 50000.0
        lead_x2, lead_y2 = bp2.predict(
            1000.0, 1000.0,
            1500.0, 1200.0,
            5000.0,
        )
        assert abs(lead_y1) > abs(lead_y2)

    def test_smoothing(self):
        bp = BallisticPredictor()
        lead_x1, lead_y1 = bp.predict(
            1000.0, 1000.0,
            1500.0, 1200.0,
            5000.0,
        )
        lead_x2, lead_y2 = bp.predict(
            1000.0, 1000.0,
            1500.0, 1200.0,
            5000.0,
        )
        assert lead_x2 != lead_x1 or lead_y2 != lead_y1

    def test_set_weapon(self):
        bp = BallisticPredictor()
        weapon = WeaponProfile(name="Sniper", bullet_speed_ms=50000.0)
        bp.set_weapon(weapon)
        assert bp._bullet_speed == 50000.0

    def test_reset(self):
        bp = BallisticPredictor()
        bp.predict(1000.0, 1000.0, 1500.0, 1200.0, 5000.0)
        bp.reset()
        assert bp._prev_target_x is None
        assert bp._smooth_lead_x == 0.0


class TestSmartHeadshot:
    """Testes para SmartHeadshot."""

    def test_initial_state(self):
        hs = SmartHeadshot()
        assert hs._head_offset_y == 30.0
        assert hs._confidence == 0.0

    def test_predict_head_returns_tuple(self):
        hs = SmartHeadshot()
        head_x, head_y = hs.predict_head(1000.0, 1000.0, 5000.0)
        assert isinstance(head_x, float)
        assert isinstance(head_y, float)

    def test_head_above_body(self):
        hs = SmartHeadshot()
        body_x, body_y = 1000.0, 1000.0
        head_x, head_y = hs.predict_head(body_x, body_y, 5000.0)
        assert head_y < body_y

    def test_distance_effect(self):
        hs = SmartHeadshot()
        head_x1, head_y1 = hs.predict_head(1000.0, 1000.0, 1000.0)
        hs.reset()
        head_x2, head_y2 = hs.predict_head(1000.0, 1000.0, 10000.0)
        assert head_y2 < head_y1

    def test_calculate_pull(self):
        hs = SmartHeadshot()
        pull_x, pull_y = hs.calculate_pull(
            1000.0, 1000.0,
            1000.0, 900.0,
            strength=1.0,
        )
        assert isinstance(pull_x, float)
        assert isinstance(pull_y, float)

    def test_pull_towards_head(self):
        hs = SmartHeadshot()
        pull_x, pull_y = hs.calculate_pull(
            1000.0, 1000.0,
            1000.0, 900.0,
            strength=1.0,
        )
        assert pull_y < 0

    def test_confidence_building(self):
        hs = SmartHeadshot()
        for _ in range(10):
            hs.calculate_pull(
                1000.0, 1000.0,
                1000.0, 900.0,
                strength=1.0,
            )
        assert hs._confidence > 0.0

    def test_overshoot_prevention(self):
        hs = SmartHeadshot()
        pull_x, pull_y = hs.calculate_pull(
            1000.0, 1000.0,
            1000.0, 900.0,
            strength=1.0,
            max_pull=50.0,
        )
        assert abs(pull_y) <= 50.0

    def test_set_weapon(self):
        hs = SmartHeadshot()
        weapon = WeaponProfile(name="AR", headshot_multiplier=2.5)
        hs.set_weapon(weapon)
        assert hs._pull_strength == 1.2

    def test_reset(self):
        hs = SmartHeadshot()
        hs.predict_head(1000.0, 1000.0, 5000.0)
        hs.reset()
        assert hs._confidence == 0.0
        assert hs._smooth_head_x == 0.0


class TestAdvancedAimPipeline:
    """Testes para AdvancedAimPipeline."""

    def test_initial_state(self):
        pipeline = AdvancedAimPipeline()
        assert pipeline._enabled is True

    def test_process_returns_tuple(self):
        pipeline = AdvancedAimPipeline()
        rx, ry = pipeline.process(
            1000.0, 1000.0,
            weapon="AR",
            is_shooting=True,
            is_ads=True,
            distance_cm=5000.0,
            target_x=1500.0,
            target_y=1200.0,
        )
        assert isinstance(rx, float)
        assert isinstance(ry, float)

    def test_disabled_passthrough(self):
        pipeline = AdvancedAimPipeline()
        pipeline._enabled = False
        rx, ry = pipeline.process(
            1000.0, 1000.0,
            weapon="AR",
            is_shooting=True,
            is_ads=True,
            distance_cm=5000.0,
        )
        assert rx == 1000.0
        assert ry == 1000.0

    def test_anti_recoil_applied(self):
        pipeline = AdvancedAimPipeline()
        for _ in range(10):
            pipeline.process(
                1000.0, 1000.0,
                weapon="AR",
                is_shooting=True,
                is_ads=True,
                distance_cm=5000.0,
                delta_ms=16.67,
            )
        profile = pipeline.anti_recoil.get_profile("AR")
        assert profile is not None
        assert profile.learned_shots > 0

    def test_ballistic_applied(self):
        pipeline = AdvancedAimPipeline()
        rx1, ry1 = pipeline.process(
            1000.0, 1000.0,
            weapon="AR",
            is_shooting=False,
            is_ads=True,
            distance_cm=5000.0,
            target_x=1500.0,
            target_y=1200.0,
        )
        assert rx1 != 1000.0 or ry1 != 1000.0

    def test_headshot_applied(self):
        pipeline = AdvancedAimPipeline()
        rx, ry = pipeline.process(
            1000.0, 1000.0,
            weapon="AR",
            is_shooting=False,
            is_ads=True,
            distance_cm=5000.0,
            target_x=1000.0,
            target_y=1000.0,
        )
        assert ry < 1000.0

    def test_get_stats(self):
        pipeline = AdvancedAimPipeline()
        pipeline.process(
            1000.0, 1000.0,
            weapon="AR",
            is_shooting=True,
            is_ads=True,
            distance_cm=5000.0,
            delta_ms=16.67,
        )
        stats = pipeline.get_stats()
        assert "weapons_learned" in stats
        assert "total_shots" in stats
        assert "avg_confidence" in stats

    def test_set_strength(self):
        pipeline = AdvancedAimPipeline()
        pipeline.set_strength(anti_recoil=0.5, ballistic=0.8, headshot=1.2)
        assert pipeline._anti_recoil_strength == 0.5
        assert pipeline._ballistic_strength == 0.8
        assert pipeline._headshot_strength == 1.2

    def test_reset(self):
        pipeline = AdvancedAimPipeline()
        pipeline.process(
            1000.0, 1000.0,
            weapon="AR",
            is_shooting=True,
            is_ads=True,
            distance_cm=5000.0,
        )
        pipeline.reset()
        stats = pipeline.get_stats()
        assert stats["total_shots"] == 0
