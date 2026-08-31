#!/usr/bin/env python3
"""Testes dos Sistemas Avançados de Aim — 4ª geração.

Multi-Engine Polar, Ghost Tracker, Burst Mode, Batts Sticky, XANAX AI.
"""
import math
import time
from unittest import TestCase
from nocrosshair.features.advanced_aim import (
    MultiPolarConfig, MultiPolarEngine, PolarEngineConfig,
    GhostTrackerConfig, GhostTrackerEngine,
    BurstModeConfig, BurstModeEngine,
    BattsStickyConfig, BattsStickyEngine,
    XanaxAIConfig, XanaxAIEngine,
)


class TestMultiPolarEngine(TestCase):
    def setUp(self):
        self.cfg = MultiPolarConfig(enabled=True)
        self.engine = MultiPolarEngine(self.cfg)

    def test_disabled_passthrough(self):
        self.cfg.enabled = False
        rx, ry = self.engine.apply(1000, 2000, True, True, 16.0)
        self.assertEqual(rx, 1000)
        self.assertEqual(ry, 2000)

    def test_enabled_modifies_output(self):
        rx, ry = self.engine.apply(1000, 2000, True, True, 16.0)
        self.assertNotEqual(rx, 1000)
        self.assertNotEqual(ry, 2000)

    def test_sniper_ads_only(self):
        self.cfg.sniper.ads_only = True
        self.engine._phases[3] = 0.0
        rx1, ry1 = self.engine.apply(0, 0, False, False, 16.0)
        self.engine._phases[3] = 0.0
        rx2, ry2 = self.engine.apply(0, 0, True, False, 16.0)
        self.assertNotEqual(rx1, rx2)

    def test_fire_boost_increases_radius(self):
        self.cfg.close.fire_boost_radius = 5
        self.cfg.medium.enabled = False
        self.cfg.long.enabled = False
        self.cfg.sniper.enabled = False
        self.engine._phases[0] = 0.0
        rx1, ry1 = self.engine.apply(0, 0, True, False, 16.0)
        self.engine._phases[0] = 0.0
        rx2, ry2 = self.engine.apply(0, 0, True, True, 16.0)
        dist1 = math.hypot(rx1, ry1)
        dist2 = math.hypot(rx2, ry2)
        self.assertGreater(dist2, dist1)

    def test_shapes(self):
        for shape in ["circle", "oval_tall", "oval_wide", "spiral", "zigzag"]:
            self.cfg.close.shape = shape
            self.engine._phases[0] = 0.0
            rx, ry = self.engine.apply(0, 0, True, False, 16.0)
            self.assertIsInstance(rx, int)
            self.assertIsInstance(ry, int)

    def test_bounds(self):
        for _ in range(100):
            rx, ry = self.engine.apply(0, 0, True, True, 16.0)
            self.assertGreaterEqual(rx, -32767)
            self.assertLessEqual(rx, 32767)
            self.assertGreaterEqual(ry, -32767)
            self.assertLessEqual(ry, 32767)

    def test_reset(self):
        self.engine.apply(0, 0, True, True, 16.0)
        self.engine.reset()
        self.assertEqual(self.engine._phases, [0.0, 0.0, 0.0, 0.0])

    def test_disabled_engine_no_effect(self):
        self.cfg.close.enabled = False
        self.cfg.medium.enabled = False
        self.cfg.long.enabled = False
        self.cfg.sniper.enabled = False
        rx, ry = self.engine.apply(1000, 2000, True, True, 16.0)
        self.assertEqual(rx, 1000)
        self.assertEqual(ry, 2000)

    def test_oval_tall_produces_different_x_y(self):
        self.cfg.close.shape = "oval_tall"
        self.cfg.close.fire_boost_radius = 0
        self.engine._phases[0] = math.pi / 4
        rx, ry = self.engine.apply(0, 0, True, False, 16.0)
        self.assertNotEqual(abs(rx), abs(ry))

    def test_oval_wide_produces_different_x_y(self):
        self.cfg.close.shape = "oval_wide"
        self.cfg.close.fire_boost_radius = 0
        self.engine._phases[0] = math.pi / 4
        rx, ry = self.engine.apply(0, 0, True, False, 16.0)
        self.assertNotEqual(abs(rx), abs(ry))


class TestGhostTrackerEngine(TestCase):
    def setUp(self):
        self.cfg = GhostTrackerConfig(enabled=True)
        self.engine = GhostTrackerEngine(self.cfg)

    def test_disabled_passthrough(self):
        self.cfg.enabled = False
        rx, ry = self.engine.apply(5000, 5000, True, False)
        self.assertEqual(rx, 5000)
        self.assertEqual(ry, 5000)

    def test_in_bubble_decelerates(self):
        rx, ry = self.engine.apply(6000, 0, True, False)
        self.assertLess(rx, 6000)

    def test_outside_bubble_no_decel(self):
        rx, ry = self.engine.apply(20000, 0, True, False)
        self.assertEqual(rx, 20000)

    def test_bubble_property(self):
        self.engine.apply(6000, 0, True, False)
        self.assertTrue(self.engine.in_bubble)
        self.engine.apply(20000, 0, True, False)
        self.assertFalse(self.engine.in_bubble)

    def test_stick_threshold(self):
        self.cfg.stick_threshold = 10000
        rx, ry = self.engine.apply(5000, 0, True, False)
        self.assertEqual(rx, 5000)

    def test_bounds(self):
        rx, ry = self.engine.apply(32767, 32767, True, False)
        self.assertGreaterEqual(rx, -32767)
        self.assertLessEqual(rx, 32767)

    def test_decel_ramp_affects_output(self):
        self.cfg.decel_ramp = 0.0
        rx1, _ = self.engine.apply(6000, 0, True, False)
        self.cfg.decel_ramp = 1.0
        rx2, _ = self.engine.apply(6000, 0, True, False)
        self.assertLess(rx2, rx1)


class TestBurstModeEngine(TestCase):
    def setUp(self):
        self.cfg = BurstModeConfig(enabled=True, burst_count=3, aim_boost=2.0)
        self.engine = BurstModeEngine(self.cfg)

    def test_disabled_passthrough(self):
        self.cfg.enabled = False
        rx, ry, mult = self.engine.apply(1000, 2000, True, 100.0, 16.0)
        self.assertEqual(rx, 1000)
        self.assertEqual(ry, 2000)
        self.assertEqual(mult, 1.0)

    def test_burst_boosts_first_shots(self):
        rx, ry, mult = self.engine.apply(1000, 2000, True, 100.0, 16.0)
        self.assertEqual(rx, 2000)
        self.assertEqual(ry, 4000)
        self.assertEqual(mult, 0.7)

    def test_burst_ends_after_count(self):
        for i in range(4):
            rx, ry, mult = self.engine.apply(1000, 2000, True, 100.0 + i * 16, 16.0)
        self.assertEqual(rx, 1000)
        self.assertEqual(mult, 1.0)

    def test_reset_on_not_shooting(self):
        self.engine.apply(1000, 2000, True, 100.0, 16.0)
        self.engine.apply(1000, 2000, False, 120.0, 16.0)
        rx, ry, mult = self.engine.apply(1000, 2000, True, 500.0, 16.0)
        self.assertEqual(rx, 2000)

    def test_cooldown_prevents_immediate_reburst(self):
        for i in range(4):
            self.engine.apply(1000, 2000, True, 0.1 + i * 0.016, 16.0)
        rx, ry, mult = self.engine.apply(1000, 2000, True, 0.2, 16.0)
        self.assertEqual(mult, 1.0)

    def test_cooldown_allows_reburst_after_time(self):
        for i in range(4):
            self.engine.apply(1000, 2000, True, 0.1 + i * 0.016, 16.0)
        rx, ry, mult = self.engine.apply(1000, 2000, True, 0.5, 16.0)
        self.assertEqual(rx, 2000)

    def test_bounds(self):
        rx, ry, _ = self.engine.apply(32767, 32767, True, 100.0, 16.0)
        self.assertGreaterEqual(rx, -32767)
        self.assertLessEqual(rx, 32767)

    def test_reset_method(self):
        self.engine.apply(1000, 2000, True, 100.0, 16.0)
        self.engine.reset()
        self.assertFalse(self.engine._burst_active)
        self.assertEqual(self.engine._burst_frames, 0)


class TestBattsStickyEngine(TestCase):
    def setUp(self):
        self.cfg = BattsStickyConfig(enabled=True)
        self.engine = BattsStickyEngine(self.cfg)

    def test_disabled_passthrough(self):
        self.cfg.enabled = False
        rx, ry = self.engine.apply(1000, 2000, True, True)
        self.assertEqual(rx, 1000)
        self.assertEqual(ry, 2000)

    def test_enabled_modifies_output(self):
        rx, ry = self.engine.apply(1000, 2000, True, True)
        self.assertNotEqual(rx, 1000)

    def test_ads_vs_hipfire_sizes(self):
        self.engine._phase = 0.0
        rx1, ry1 = self.engine.apply(0, 0, True, False)
        self.engine._phase = 0.0
        rx2, ry2 = self.engine.apply(0, 0, False, False)
        dist1 = math.hypot(rx1, ry1)
        dist2 = math.hypot(rx2, ry2)
        self.assertLess(dist1, dist2)

    def test_ads_fire_vs_ads_sizes(self):
        self.engine._phase = 0.0
        rx1, ry1 = self.engine.apply(0, 0, True, False)
        self.engine._phase = 0.0
        rx2, ry2 = self.engine.apply(0, 0, True, True)
        dist1 = math.hypot(rx1, ry1)
        dist2 = math.hypot(rx2, ry2)
        self.assertLess(dist1, dist2)

    def test_drift_follows_input(self):
        self.cfg.drift_enabled = True
        self.cfg.drift_strength = 0.5
        self.engine._phase = 0.0
        rx, ry = self.engine.apply(10000, 0, True, True)
        self.assertGreater(rx, 0)

    def test_bounds(self):
        for _ in range(100):
            rx, ry = self.engine.apply(0, 0, True, True)
            self.assertGreaterEqual(rx, -32767)
            self.assertLessEqual(rx, 32767)

    def test_reset(self):
        self.engine.apply(0, 0, True, True)
        self.engine.reset()
        self.assertEqual(self.engine._phase, 0.0)

    def test_different_speeds_by_context(self):
        self.engine._phase = 0.0
        for _ in range(10):
            self.engine.apply(0, 0, True, True)
        phase_ads_fire = self.engine._phase

        self.engine._phase = 0.0
        for _ in range(10):
            self.engine.apply(0, 0, True, False)
        phase_ads = self.engine._phase

        self.engine._phase = 0.0
        for _ in range(10):
            self.engine.apply(0, 0, False, False)
        phase_hip = self.engine._phase

        self.assertGreaterEqual(phase_ads_fire, phase_ads)
        self.assertGreaterEqual(phase_ads, phase_hip)


class TestXanaxAIEngine(TestCase):
    def setUp(self):
        self.cfg = XanaxAIConfig(enabled=True)
        self.engine = XanaxAIEngine(self.cfg)

    def test_disabled_returns_one(self):
        self.cfg.enabled = False
        mult = self.engine.compute_multiplier(0, 0, False, 16.0)
        self.assertEqual(mult, 1.0)

    def test_synergy_boost(self):
        self.engine.update_mods(3)
        mult = self.engine.compute_multiplier(0, 0, False, 16.0)
        self.assertGreater(mult, 1.0)

    def test_no_synergy_below_threshold(self):
        self.engine.update_mods(2)
        mult = self.engine.compute_multiplier(0, 0, False, 16.0)
        self.assertAlmostEqual(mult, 1.0, delta=0.05)

    def test_close_range_boost(self):
        self.engine.update_mods(0)
        mult = self.engine.compute_multiplier(3000, 0, False, 16.0)
        self.assertGreater(mult, 1.0)

    def test_long_range_reduction(self):
        self.engine.update_mods(0)
        mult = self.engine.compute_multiplier(25000, 0, False, 16.0)
        self.assertLess(mult, 1.0)

    def test_humanize_jitter(self):
        self.cfg.humanize_enabled = True
        self.cfg.humanize_jitter = 0.1
        mults = []
        for i in range(100):
            mults.append(self.engine.compute_multiplier(0, 0, False, 16.0))
        self.assertGreater(max(mults) - min(mults), 0.01)

    def test_smooth_transition(self):
        self.engine.update_mods(5)
        m1 = self.engine.compute_multiplier(0, 0, False, 16.0)
        m2 = self.engine.compute_multiplier(0, 0, False, 16.0)
        self.assertAlmostEqual(m1, m2, delta=0.1)

    def test_multiplier_bounded(self):
        for _ in range(1000):
            mult = self.engine.compute_multiplier(0, 0, False, 16.0)
            self.assertGreaterEqual(mult, 0.5)
            self.assertLessEqual(mult, 2.0)

    def test_reset(self):
        self.engine.update_mods(5)
        self.engine.compute_multiplier(0, 0, False, 16.0)
        self.engine.reset()
        self.assertEqual(self.engine._active_mods, 0)
        self.assertEqual(self.engine._current_multiplier, 1.0)

    def test_mods_count(self):
        self.engine.update_mods(5)
        self.assertEqual(self.engine._active_mods, 5)

    def test_property_multiplier(self):
        self.engine.compute_multiplier(0, 0, False, 16.0)
        self.assertIsInstance(self.engine.multiplier, float)
