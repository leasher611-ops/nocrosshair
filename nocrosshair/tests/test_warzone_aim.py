#!/usr/bin/env python3
"""Testes dos Sistemas Warzone Aim — Vibração L3, Aim Buffers, Rapid Fire."""
import math
import time
import unittest.mock
from unittest import TestCase
from nocrosshair.features.warzone_aim import (
    VibrationL3Config, VibrationL3Engine,
    WarzoneAimBufferConfig, WarzoneAimBufferEngine,
    RapidFirePureConfig, RapidFirePureEngine,
    AimBufferStackConfig, AimBufferStackEngine,
)


class TestVibrationL3Engine(TestCase):
    def setUp(self):
        self.cfg = VibrationL3Config(enabled=True)
        self.engine = VibrationL3Engine(self.cfg)

    def test_disabled_passthrough(self):
        self.cfg.enabled = False
        lx, ly, vib = self.engine.apply(1000, 2000, 0, 0, True, False, 16.0)
        self.assertEqual(lx, 1000)
        self.assertEqual(ly, 2000)
        self.assertFalse(vib)

    def test_enabled_modifies_output(self):
        lx, ly, vib = self.engine.apply(1000, 2000, 0, 0, True, False, 16.0)
        self.assertNotEqual(lx, 1000)
        self.assertTrue(vib)

    def test_ads_only(self):
        self.cfg.ads_only = True
        lx, ly, vib = self.engine.apply(1000, 2000, 0, 0, False, False, 16.0)
        self.assertEqual(lx, 1000)
        self.assertFalse(vib)

    def test_fire_only(self):
        self.cfg.fire_only = True
        lx, ly, vib = self.engine.apply(1000, 2000, 0, 0, True, False, 16.0)
        self.assertEqual(lx, 1000)
        self.assertFalse(vib)

    def test_vibration_values(self):
        self.engine.apply(1000, 2000, 0, 0, True, False, 16.0)
        left, right = self.engine.get_vibration_values()
        self.assertGreater(left, 0)
        self.assertGreater(right, 0)

    def test_stop(self):
        self.engine.apply(1000, 2000, 0, 0, True, False, 16.0)
        self.engine.stop()
        left, right = self.engine.get_vibration_values()
        self.assertEqual(left, 0)
        self.assertEqual(right, 0)

    def test_bounds(self):
        for _ in range(100):
            lx, ly, _ = self.engine.apply(0, 0, 0, 0, True, False, 16.0)
            self.assertGreaterEqual(lx, -32767)
            self.assertLessEqual(lx, 32767)

    def test_active_property(self):
        self.assertFalse(self.engine.active)
        self.engine.apply(0, 0, 0, 0, True, False, 16.0)
        self.assertTrue(self.engine.active)


class TestWarzoneAimBufferEngine(TestCase):
    def setUp(self):
        self.cfg = WarzoneAimBufferConfig(enabled=True)
        self.engine = WarzoneAimBufferEngine(self.cfg)

    def test_disabled_passthrough(self):
        self.cfg.enabled = False
        rx, ry = self.engine.apply(1000, 2000, True, False, 16.0)
        self.assertEqual(rx, 1000)
        self.assertEqual(ry, 2000)

    def test_tracking_amplifies_input(self):
        rx, ry = self.engine.apply(5000, 0, True, False, 16.0)
        self.assertGreater(rx, 5000)

    def test_tracking_no_effect_small_input(self):
        rx, ry = self.engine.apply(100, 0, True, False, 16.0)
        self.assertEqual(rx, 100)

    def test_fire_boost(self):
        self.cfg.fire_boost = 2.0
        rx1, ry1 = self.engine.apply(5000, 0, True, False, 16.0)
        rx2, ry2 = self.engine.apply(5000, 0, True, True, 16.0)
        self.assertGreater(rx2, rx1)

    def test_bounds(self):
        for _ in range(100):
            rx, ry = self.engine.apply(30000, 30000, True, True, 16.0)
            self.assertGreaterEqual(rx, -32767)
            self.assertLessEqual(rx, 32767)

    def test_reset(self):
        self.engine.apply(5000, 0, True, True, 16.0)
        self.engine.reset()
        self.assertFalse(self.engine._locked)
        self.assertEqual(self.engine._lock_frames, 0)


class TestRapidFirePureEngine(TestCase):
    def setUp(self):
        self.cfg = RapidFirePureConfig(enabled=True)
        self.engine = RapidFirePureEngine(self.cfg)

    def test_disabled_passthrough(self):
        self.cfg.enabled = False
        rt, recoil, active = self.engine.process(0, True, True, 16.0)
        self.assertEqual(rt, 0)
        self.assertFalse(active)

    def test_firing_toggles_trigger(self):
        results = []
        t = 0.0
        for i in range(20):
            with unittest.mock.patch('time.monotonic', return_value=t):
                rt, recoil, active = self.engine.process(0, True, True, 16.0)
                results.append(rt)
            t += 0.016
        self.assertIn(32767, results)
        self.assertIn(0, results)

    def test_not_firing_returns_zero(self):
        rt, recoil, active = self.engine.process(0, False, True, 16.0)
        self.assertEqual(rt, 0)
        self.assertFalse(active)

    def test_ads_only(self):
        self.cfg.activate_only_ads = True
        rt, recoil, active = self.engine.process(0, True, False, 16.0)
        self.assertEqual(rt, 0)
        self.assertFalse(active)

    def test_anti_recoil(self):
        self.cfg.anti_recoil_enabled = True
        self.cfg.anti_recoil_strength = 1.5
        for _ in range(10):
            rt, recoil, active = self.engine.process(0, True, True, 16.0)
            if rt > 0:
                self.assertLess(recoil, 0)

    def test_burst_mode(self):
        self.cfg.burst_mode = True
        self.cfg.burst_count = 3
        results = []
        t = 0.0
        for i in range(50):
            with unittest.mock.patch('time.monotonic', return_value=t):
                rt, recoil, active = self.engine.process(0, True, True, 16.0)
                results.append(rt)
            t += 0.016
        self.assertIn(32767, results)
        self.assertIn(0, results)

    def test_reset(self):
        self.engine.process(0, True, True, 16.0)
        self.engine.reset()
        self.assertFalse(self.engine._active)


class TestAimBufferStackEngine(TestCase):
    def setUp(self):
        self.cfg = AimBufferStackConfig()
        self.cfg.vibration.enabled = True
        self.cfg.warzone_buffer.enabled = True
        self.cfg.rapid_fire.enabled = True
        self.engine = AimBufferStackEngine(self.cfg)

    def test_combined_apply(self):
        lx, ly, rx, ry, vib = self.engine.apply(
            1000, 2000, 5000, 0, True, True, 16.0)
        self.assertNotEqual(lx, 1000)
        self.assertNotEqual(rx, 5000)
        self.assertTrue(vib)

    def test_rapid_fire_process(self):
        rt, recoil, active = self.engine.process_rapid_fire(0, True, True, 16.0)
        self.assertTrue(active)

    def test_reset_all(self):
        self.engine.apply(1000, 2000, 5000, 0, True, True, 16.0)
        self.engine.process_rapid_fire(0, True, True, 16.0)
        self.engine.reset()
        self.assertFalse(self.engine.vibration_engine.active)

    def test_bounds(self):
        for _ in range(50):
            lx, ly, rx, ry, _ = self.engine.apply(
                0, 0, 30000, 30000, True, True, 16.0)
            self.assertGreaterEqual(lx, -32767)
            self.assertLessEqual(rx, 32767)
