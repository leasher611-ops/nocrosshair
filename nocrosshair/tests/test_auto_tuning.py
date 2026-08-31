"""
 nocrosshair — test_auto_tuning.py
 ═══════════════════════════════════════════════════════════════════════════════
 TESTES PARA O SISTEMA DE AUTO-TUNING

 Testa os módulos:
   - auto_tuning.py (RecoilLearner, AdaptiveSensitivity, PatchDetector)

 ═══════════════════════════════════════════════════════════════════════════════
"""

import pytest
import time
from nocrosshair.features.auto_tuning import (
    RecoilLearner,
    AdaptiveSensitivity,
    PatchDetector,
    AutoTuner,
    RecoilSample,
    WeaponProfile,
)


class TestRecoilLearner:
    """Testes para aprendizado de recoil."""

    def test_initial_state(self):
        learner = RecoilLearner()
        assert len(learner._samples) == 0
        assert len(learner._profiles) == 0

    def test_add_sample(self):
        learner = RecoilLearner()
        learner.add_sample(
            tick=0,
            input_rx=1000.0,
            input_ry=1000.0,
            output_rx=1100.0,
            output_ry=1100.0,
            is_shooting=True,
            weapon="AR",
        )
        assert len(learner._samples) == 1

    def test_non_shooting_ignored(self):
        learner = RecoilLearner()
        learner.add_sample(
            tick=0,
            input_rx=1000.0,
            input_ry=1000.0,
            output_rx=1100.0,
            output_ry=1100.0,
            is_shooting=False,
            weapon="AR",
        )
        assert len(learner._samples) == 0

    def test_max_samples_limit(self):
        learner = RecoilLearner(max_samples=100)
        for i in range(150):
            learner.add_sample(
                tick=i,
                input_rx=1000.0,
                input_ry=1000.0,
                output_rx=1100.0,
                output_ry=1100.0,
                is_shooting=True,
                weapon="AR",
            )
        assert len(learner._samples) == 100

    def test_weapon_change_updates_profile(self):
        learner = RecoilLearner()
        for i in range(20):
            learner.add_sample(
                tick=i,
                input_rx=1000.0,
                input_ry=1000.0,
                output_rx=1100.0,
                output_ry=1100.0,
                is_shooting=True,
                weapon="AR",
            )
        learner._current_weapon = "SMG"
        learner._update_profile()
        assert "AR" in learner._profiles

    def test_get_profile(self):
        learner = RecoilLearner()
        for i in range(20):
            learner.add_sample(
                tick=i,
                input_rx=1000.0,
                input_ry=1000.0,
                output_rx=1100.0,
                output_ry=1100.0,
                is_shooting=True,
                weapon="AR",
            )
        profile = learner.get_profile("AR")
        assert profile is not None
        assert profile.weapon == "AR"

    def test_get_recoil_offset(self):
        learner = RecoilLearner()
        for i in range(60):
            learner.add_sample(
                tick=i,
                input_rx=1000.0,
                input_ry=1000.0,
                output_rx=1100.0,
                output_ry=1100.0,
                is_shooting=True,
                weapon="AR",
            )
        offset_x, offset_y = learner.get_recoil_offset("AR", 0)
        assert offset_x != 0.0 or offset_y != 0.0

    def test_reset(self):
        learner = RecoilLearner()
        learner.add_sample(
            tick=0,
            input_rx=1000.0,
            input_ry=1000.0,
            output_rx=1100.0,
            output_ry=1100.0,
            is_shooting=True,
            weapon="AR",
        )
        learner.reset()
        assert len(learner._samples) == 0
        assert len(learner._profiles) == 0

    def test_save_load_profiles(self, tmp_path):
        learner = RecoilLearner()
        for i in range(20):
            learner.add_sample(
                tick=i,
                input_rx=1000.0,
                input_ry=1000.0,
                output_rx=1100.0,
                output_ry=1100.0,
                is_shooting=True,
                weapon="AR",
            )
        path = str(tmp_path / "profiles.json")
        learner.save_profiles(path)

        learner2 = RecoilLearner()
        learner2.load_profiles(path)
        assert "AR" in learner2._profiles


class TestAdaptiveSensitivity:
    """Testes para sensibilidade adaptativa."""

    def test_initial_state(self):
        adaptive = AdaptiveSensitivity()
        assert adaptive.multiplier == 1.0
        assert adaptive.hit_rate == 0.0

    def test_record_shot(self):
        adaptive = AdaptiveSensitivity()
        adaptive.record_shot(True)
        adaptive.record_shot(False)
        assert adaptive.hit_rate == 0.5

    def test_high_hit_rate_reduces_multiplier(self):
        adaptive = AdaptiveSensitivity()
        for _ in range(100):
            adaptive.record_shot(True)
        for _ in range(5):
            adaptive.adjust()
        assert adaptive.multiplier < 1.0

    def test_low_hit_rate_increases_multiplier(self):
        adaptive = AdaptiveSensitivity()
        for _ in range(100):
            adaptive.record_shot(False)
        for _ in range(5):
            adaptive.adjust()
        assert adaptive.multiplier > 1.0

    def test_bounds_respected(self):
        adaptive = AdaptiveSensitivity(min_mult=0.8, max_mult=1.2)
        for _ in range(100):
            adaptive.record_shot(False)
        for _ in range(100):
            adaptive.adjust()
        assert adaptive.multiplier <= 1.2

    def test_reset(self):
        adaptive = AdaptiveSensitivity()
        adaptive.record_shot(True)
        adaptive.adjust()
        adaptive.reset()
        assert adaptive.multiplier == 1.0
        assert adaptive.hit_rate == 0.0


class TestPatchDetector:
    """Testes para detector de patches."""

    def test_initial_state(self):
        detector = PatchDetector()
        assert detector.patch_detected is False

    def test_stable_recoil_no_patch(self):
        detector = PatchDetector()
        for _ in range(100):
            detected = detector.update(100.0, 100.0)
        assert detected is False

    def test_sudden_change_detects_patch(self):
        detector = PatchDetector(threshold=0.3, min_samples=5, window=1.0)
        for _ in range(10):
            time.sleep(0.001)
            detector.update(100.0, 100.0)
        detected = False
        for _ in range(20):
            time.sleep(0.001)
            if detector.update(200.0, 200.0):
                detected = True
                break
        assert detected is True
        assert detector.patch_detected is True

    def test_acknowledge_patch(self):
        detector = PatchDetector()
        detector._patch_detected = True
        detector.acknowledge_patch()
        assert detector.patch_detected is False

    def test_reset(self):
        detector = PatchDetector()
        detector.update(100.0, 100.0)
        detector.reset()
        assert detector._baseline_recoil is None
        assert detector.patch_detected is False


class TestAutoTuner:
    """Testes para o sistema unificado de auto-tuning."""

    def test_initial_state(self):
        tuner = AutoTuner()
        assert tuner.enabled is False

    def test_enable_disable(self):
        tuner = AutoTuner()
        tuner.enable()
        assert tuner.enabled is True
        tuner.disable()
        assert tuner.enabled is False

    def test_process_frame_disabled(self):
        tuner = AutoTuner()
        rx, ry = tuner.process_frame(
            1000.0, 1000.0, 1100.0, 1100.0,
            True, True, "AR", 0,
        )
        assert rx == 1100.0
        assert ry == 1100.0

    def test_process_frame_enabled(self):
        tuner = AutoTuner()
        tuner.enable()
        rx, ry = tuner.process_frame(
            1000.0, 1000.0, 1100.0, 1100.0,
            True, True, "AR", 0,
        )
        assert -32767 <= rx <= 32767
        assert -32767 <= ry <= 32767

    def test_get_stats(self):
        tuner = AutoTuner()
        stats = tuner.get_stats()
        assert "enabled" in stats
        assert "hit_rate" in stats
        assert "multiplier" in stats

    def test_reset(self):
        tuner = AutoTuner()
        tuner.enable()
        tuner.process_frame(
            1000.0, 1000.0, 1100.0, 1100.0,
            True, True, "AR", 0,
        )
        tuner.reset()
        stats = tuner.get_stats()
        assert stats["profiles_count"] == 0


class TestWeaponProfile:
    """Testes para profile de arma."""

    def test_to_dict(self):
        profile = WeaponProfile(
            weapon="AR",
            game="Fortnite",
            recoil_pattern_x=[1.0, 2.0, 3.0],
            recoil_pattern_y=[1.0, 2.0, 3.0],
            avg_recoil_x=2.0,
            avg_recoil_y=2.0,
            sample_count=100,
            confidence=0.8,
            last_updated=time.time(),
        )
        d = profile.to_dict()
        assert d["weapon"] == "AR"
        assert d["sample_count"] == 100

    def test_from_dict(self):
        d = {
            "weapon": "SMG",
            "game": "Valorant",
            "recoil_pattern_x": [1.0, 2.0],
            "recoil_pattern_y": [1.0, 2.0],
            "avg_recoil_x": 1.5,
            "avg_recoil_y": 1.5,
            "sample_count": 50,
            "confidence": 0.5,
            "last_updated": time.time(),
        }
        profile = WeaponProfile.from_dict(d)
        assert profile.weapon == "SMG"
        assert profile.sample_count == 50
