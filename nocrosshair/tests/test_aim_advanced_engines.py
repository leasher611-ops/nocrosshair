"""
 nocrosshair — test_aim_advanced_engines.py
 ═══════════════════════════════════════════════════════════════════════════════
 TESTES PARA MOTORES DE AIM AVANÇADOS

 ═══════════════════════════════════════════════════════════════════════════════
"""

import pytest
import time
from nocrosshair.features.aim_advanced_engines import (
    TargetPredictorV3,
    MotionPatternDetector,
    DynamicSmoothing,
    SmartAdhesion,
    RotationalPatternsV2,
    SmartRecoilV2,
    CadencePredictor,
    EngagementAnalyzerV2,
    EngagementPhase,
)


class TestTargetPredictorV3:
    """Testes para preditor de alvos de 3ª geração."""

    def test_initial_state(self):
        predictor = TargetPredictorV3()
        assert len(predictor._history) == 0

    def test_update_adds_to_history(self):
        predictor = TargetPredictorV3()
        predictor.update(100.0, 200.0, 16.67)
        assert len(predictor._history) == 1

    def test_predict_returns_tuple(self):
        predictor = TargetPredictorV3()
        predictor.update(100.0, 200.0, 16.67)
        lead_x, lead_y, confidence = predictor.predict(100.0, 200.0, 16.67)
        assert isinstance(lead_x, float)
        assert isinstance(lead_y, float)
        assert isinstance(confidence, float)

    def test_confidence_increases_with_consistent_input(self):
        predictor = TargetPredictorV3()
        for i in range(20):
            predictor.update(100.0 + i * 10, 200.0, 16.67)
            predictor.predict(100.0 + i * 10, 200.0, 16.67)
        _, _, confidence = predictor.predict(300.0, 200.0, 16.67)
        assert confidence > 0.3

    def test_lead_ahead_of_moving_target(self):
        """Alvo andando pra direita → lead pra direita (x positivo)."""
        predictor = TargetPredictorV3()
        for i in range(30):
            x = 100.0 + i * 10
            predictor.update(x, 200.0, 16.67)
            predictor.predict(x, 200.0, 16.67)
        lead_x, lead_y, confidence = predictor.predict(400.0, 200.0, 16.67)
        assert confidence > 0.5
        assert lead_x > 0.0

    def test_no_lead_on_static_target(self):
        """Alvo parado → sem lead (confidence 0)."""
        predictor = TargetPredictorV3()
        for i in range(30):
            predictor.update(100.0, 200.0, 16.67)
            predictor.predict(100.0, 200.0, 16.67)
        lead_x, lead_y, confidence = predictor.predict(100.0, 200.0, 16.67)
        assert confidence == 0.0
        assert lead_x == 0.0 and lead_y == 0.0

    def test_lead_resets_on_direction_reversal(self):
        """Mudança de direção → streak reseta → sem lead na hora."""
        predictor = TargetPredictorV3()
        for i in range(20):
            x = 100.0 + i * 10
            predictor.update(x, 200.0, 16.67)
            predictor.predict(x, 200.0, 16.67)
        lead_x, _, confidence = predictor.predict(180.0, 200.0, 16.67)
        assert lead_x == 0.0 or confidence <= 0.3

    def test_reset(self):
        predictor = TargetPredictorV3()
        predictor.update(100.0, 200.0, 16.67)
        predictor.reset()
        assert len(predictor._history) == 0


class TestMotionPatternDetector:
    """Testes para detector de padrões de movimento."""

    def test_initial_state(self):
        detector = MotionPatternDetector()
        assert detector._pattern == "linear"

    def test_linear_detection(self):
        detector = MotionPatternDetector()
        for i in range(10):
            detector.update(i * 10.0, 100.0, 16.67)
        assert detector._pattern == "linear"

    def test_strafe_detection(self):
        detector = MotionPatternDetector()
        for i in range(10):
            detector.update(100.0 + (i % 2) * 200, 100.0, 16.67)
        assert detector._pattern in ("strafe", "erratic")

    def test_reset(self):
        detector = MotionPatternDetector()
        detector.update(100.0, 200.0, 16.67)
        detector.reset()
        assert len(detector._history) == 0


class TestDynamicSmoothing:
    """Testes para suavização adaptativa."""

    def test_initial_state(self):
        smoothing = DynamicSmoothing()
        assert smoothing._smooth_x == 0.0
        assert smoothing._smooth_y == 0.0

    def test_apply_returns_tuple(self):
        smoothing = DynamicSmoothing()
        result = smoothing.apply(1000.0, 1000.0)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_smoothing_reduces_movement(self):
        smoothing = DynamicSmoothing(base_smoothing=0.5)
        smooth_x, smooth_y = smoothing.apply(1000.0, 1000.0)
        assert abs(smooth_x) < 1000.0
        assert abs(smooth_y) < 1000.0

    def test_firing_reduces_smoothing(self):
        smoothing_no_fire = DynamicSmoothing(base_smoothing=0.5)
        smoothing_fire = DynamicSmoothing(base_smoothing=0.5)
        _, _ = smoothing_no_fire.apply(1000.0, 1000.0, is_firing=False, distance_to_target=2000.0)
        _, _ = smoothing_fire.apply(1000.0, 1000.0, is_firing=True, distance_to_target=2000.0)
        smooth_x_no, _ = smoothing_no_fire.apply(1000.0, 1000.0, is_firing=False, distance_to_target=2000.0)
        smooth_x_fire, _ = smoothing_fire.apply(1000.0, 1000.0, is_firing=True, distance_to_target=2000.0)
        assert smooth_x_fire < smooth_x_no

    def test_record_accuracy(self):
        smoothing = DynamicSmoothing()
        smoothing.record_accuracy(True)
        smoothing.record_accuracy(False)
        assert len(smoothing._accuracy_history) == 2

    def test_reset(self):
        smoothing = DynamicSmoothing()
        smoothing.apply(1000.0, 1000.0)
        smoothing.reset()
        assert smoothing._smooth_x == 0.0


class TestSmartAdhesion:
    """Testes para aderência inteligente."""

    def test_initial_state(self):
        adhesion = SmartAdhesion()
        assert adhesion._persist_x == 0.0

    def test_engaged_pull(self):
        adhesion = SmartAdhesion()
        rx, ry = adhesion.apply(
            1000.0, 1000.0,
            enabled=True,
            strength=0.5,
            is_shooting=True,
            is_aiming=True,
            delta_ms=16.67,
        )
        assert rx > 1000.0 or ry > 1000.0

    def test_persistence(self):
        adhesion = SmartAdhesion()
        adhesion.apply(
            1000.0, 1000.0,
            enabled=True,
            strength=0.5,
            is_shooting=True,
            is_aiming=True,
            delta_ms=16.67,
        )
        rx, ry = adhesion.apply(
            0.0, 0.0,
            enabled=True,
            strength=0.5,
            is_shooting=False,
            is_aiming=False,
            delta_ms=16.67,
        )
        assert rx != 0.0 or ry != 0.0

    def test_disabled_passthrough(self):
        adhesion = SmartAdhesion()
        rx, ry = adhesion.apply(
            1000.0, 1000.0,
            enabled=False,
            strength=0.5,
            is_shooting=True,
            is_aiming=True,
            delta_ms=16.67,
        )
        assert rx == 1000.0
        assert ry == 1000.0

    def test_reset(self):
        adhesion = SmartAdhesion()
        adhesion.apply(
            1000.0, 1000.0,
            enabled=True,
            strength=0.5,
            is_shooting=True,
            is_aiming=True,
            delta_ms=16.67,
        )
        adhesion.reset()
        assert adhesion._persist_x == 0.0


class TestRotationalPatternsV2:
    """Testes para padrões rotacionais de 2ª geração."""

    def test_initial_state(self):
        patterns = RotationalPatternsV2()
        assert patterns._angle == 0.0

    def test_lissajous(self):
        patterns = RotationalPatternsV2()
        rx, ry = patterns.apply(
            1000.0, 1000.0,
            enabled=True,
            amplitude=100.0,
            speed=0.3,
            delta_ms=16.67,
            pattern="lissajous",
        )
        assert rx != 1000.0 or ry != 1000.0

    def test_fibonacci(self):
        patterns = RotationalPatternsV2()
        rx, ry = patterns.apply(
            1000.0, 1000.0,
            enabled=True,
            amplitude=100.0,
            speed=0.3,
            delta_ms=16.67,
            pattern="fibonacci",
        )
        assert rx != 1000.0 or ry != 1000.0

    def test_brownian(self):
        patterns = RotationalPatternsV2()
        rx, ry = patterns.apply(
            1000.0, 1000.0,
            enabled=True,
            amplitude=100.0,
            speed=0.3,
            delta_ms=16.67,
            pattern="brownian",
        )
        assert rx != 1000.0 or ry != 1000.0

    def test_disabled_passthrough(self):
        patterns = RotationalPatternsV2()
        rx, ry = patterns.apply(
            1000.0, 1000.0,
            enabled=False,
            amplitude=100.0,
            speed=0.3,
            delta_ms=16.67,
        )
        assert rx == 1000.0
        assert ry == 1000.0

    def test_adapt_amplitude(self):
        patterns = RotationalPatternsV2()
        patterns.adapt_amplitude(0.8)
        assert patterns._amplitude_adapt < 1.0
        patterns._amplitude_adapt = 1.0
        patterns.adapt_amplitude(0.2)
        assert patterns._amplitude_adapt > 1.0

    def test_reset(self):
        patterns = RotationalPatternsV2()
        patterns.apply(
            1000.0, 1000.0,
            enabled=True,
            amplitude=100.0,
            speed=0.3,
            delta_ms=16.67,
        )
        patterns.reset()
        assert patterns._angle == 0.0


class TestSmartRecoilV2:
    """Testes para compensação de recoil inteligente."""

    def test_initial_state(self):
        recoil = SmartRecoilV2()
        assert len(recoil._patterns) == 0

    def test_compensate_returns_tuple(self):
        recoil = SmartRecoilV2()
        rx, ry = recoil.compensate(
            1000.0, 1000.0,
            weapon="AR",
            is_shooting=True,
            is_hit=True,
            delta_ms=16.67,
        )
        assert isinstance(rx, float)
        assert isinstance(ry, float)

    def test_learn_pattern(self):
        recoil = SmartRecoilV2()
        pattern = [(10.0, 20.0), (15.0, 25.0), (20.0, 30.0)]
        recoil.learn_pattern("AR", pattern)
        assert "AR" in recoil._patterns

    def test_reset(self):
        recoil = SmartRecoilV2()
        recoil.compensate(
            1000.0, 1000.0,
            weapon="AR",
            is_shooting=True,
            is_hit=True,
            delta_ms=16.67,
        )
        recoil.reset()
        assert recoil._tick == 0


class TestCadencePredictor:
    """Testes para preditor de cadência."""

    def test_initial_state(self):
        predictor = CadencePredictor()
        assert predictor._avg_cadence == 100.0

    def test_update(self):
        predictor = CadencePredictor()
        predictor.update(50.0)
        predictor.update(60.0)
        assert predictor._avg_cadence == 55.0

    def test_get_multiplier(self):
        predictor = CadencePredictor()
        predictor._avg_cadence = 30.0
        assert predictor.get_multiplier(50.0) == 0.8
        predictor._avg_cadence = 75.0
        assert predictor.get_multiplier(100.0) == 1.0
        predictor._avg_cadence = 150.0
        assert predictor.get_multiplier(150.0) == 1.2

    def test_reset(self):
        predictor = CadencePredictor()
        predictor.update(50.0)
        predictor.reset()
        assert predictor._avg_cadence == 100.0


class TestEngagementAnalyzerV2:
    """Testes para analisador de engajamento de 2ª geração."""

    def test_initial_state(self):
        analyzer = EngagementAnalyzerV2()
        assert analyzer.phase == EngagementPhase.IDLE

    def test_idle_detection(self):
        analyzer = EngagementAnalyzerV2()
        phase = analyzer.analyze(0.0, 0.0, False, False, 16.67)
        assert phase == EngagementPhase.IDLE

    def test_tracking_detection(self):
        analyzer = EngagementAnalyzerV2()
        phase = analyzer.analyze(1000.0, 1000.0, False, False, 16.67)
        assert phase == EngagementPhase.TRACKING

    def test_firing_detection(self):
        analyzer = EngagementAnalyzerV2()
        phase = analyzer.analyze(500.0, 500.0, True, False, 16.67)
        assert phase == EngagementPhase.FIRING

    def test_burst_detection(self):
        analyzer = EngagementAnalyzerV2()
        for _ in range(5):
            phase = analyzer.analyze(500.0, 500.0, True, False, 16.67)
        assert phase == EngagementPhase.BURST

    def test_reset(self):
        analyzer = EngagementAnalyzerV2()
        analyzer.analyze(1000.0, 1000.0, True, False, 16.67)
        analyzer.reset()
        assert analyzer.phase == EngagementPhase.IDLE
