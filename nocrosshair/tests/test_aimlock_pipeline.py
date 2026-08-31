#!/usr/bin/env python3

import math
import pytest
from nocrosshair.core.config import AimAssistConfig
from nocrosshair.features.aim_assist import AimAssistEngine, AimAssistPipeline
from nocrosshair.features.aimlock_proto import (
    SimulatedTargetFeed, NullTargetFeed, TargetFeed,
)


def make_pipeline(feed: TargetFeed = None, **overrides):
    aimlock_enabled = overrides.pop("aimlock_enabled", True)
    cfg = AimAssistConfig(
        enabled=True,
        base_aa_enabled=False,
        rotational=False,
        anti_flinch=False,
        adaptive_strength=False,
        anti_shake_blend=0.0,
        enhanced_enabled=False,
        sticky_enabled=False,
        lock_enabled=False,
        head_assist_enabled=False,
        auto_rotation_enabled=False,
        fn_slow_strength=0.0,
        fn_pull_strength=0.0,
        fn_magnet_force=0.0,
        aimlock_enabled=aimlock_enabled,
        aimlock_snappiness=1.0,
        aimlock_smoothing_rate=100.0,
        aimlock_noise_degrees=0.0,
        aimlock_pull_max_rate_deg_s=0.0,
        aimlock_pull_ramp_up_ms=0.0,
        aimlock_initial_downsight_mult=1.0,
        aimlock_initial_downsight_ms=0.0,
        aimlock_adhesion_cone_deg=0.0,
        aimlock_slow_strength=0.0,
        aimlock_center_strength_mult=1.0,
        **overrides,
    )
    return AimAssistPipeline(AimAssistEngine(cfg), target_feed=feed)


class TestFeedPassthrough:

    def test_null_feed(self):
        feed = NullTargetFeed()
        assert feed.get_target(16.0) is None

    def test_no_feed_unchanged(self):
        pipeline = make_pipeline()
        rx, ry = pipeline.apply(2000, 1000, True, True, False, 16.0,
                                pipeline.aa_engine.cfg, 0, 0)
        assert rx == 2000
        assert ry == 1000

    def test_disabled_unchanged(self):
        pipeline = make_pipeline(aimlock_enabled=False,
                                 feed=SimulatedTargetFeed(start_yaw_deg=10.0,
                                                          yaw_speed_deg_s=0.0))
        rx, ry = pipeline.apply(2000, 1000, True, True, False, 16.0,
                                pipeline.aa_engine.cfg, 0, 0)
        assert rx == 2000
        assert ry == 1000

    def test_feed_out_of_fov_unchanged(self):
        pipeline = make_pipeline(aimlock_fov_degrees=30.0,
                                 feed=SimulatedTargetFeed(start_yaw_deg=60.0,
                                                          yaw_speed_deg_s=0.0))
        rx, ry = pipeline.apply(1500, 500, True, True, False, 16.0,
                                pipeline.aa_engine.cfg, 0, 0)
        assert rx == 1500
        assert ry == 500


class TestFeedEngagement:

    def test_engaged_pulls_toward_target(self):
        pipeline = make_pipeline(aimlock_blend=0.7,
                                 feed=SimulatedTargetFeed(start_yaw_deg=10.0,
                                                          yaw_speed_deg_s=0.0))
        rx, ry = pipeline.apply(0, 0, True, True, False, 16.0,
                                pipeline.aa_engine.cfg, 0, 0)
        expected = 0.7 * 32767.0 * (10.0 / 30.0)
        assert math.isclose(rx, expected, rel_tol=0.02)
        assert rx > 0

    def test_blend_zero_keeps_user_input(self):
        pipeline = make_pipeline(aimlock_blend=0.0,
                                 feed=SimulatedTargetFeed(start_yaw_deg=10.0,
                                                          yaw_speed_deg_s=0.0))
        rx, ry = pipeline.apply(2000, 1000, True, True, False, 16.0,
                                pipeline.aa_engine.cfg, 0, 0)
        assert rx == 2000
        assert ry == 1000

    def test_blend_full_overrides_user(self):
        pipeline = make_pipeline(aimlock_blend=1.0,
                                 feed=SimulatedTargetFeed(start_yaw_deg=10.0,
                                                          yaw_speed_deg_s=0.0))
        rx, ry = pipeline.apply(2000, 1000, True, True, False, 16.0,
                                pipeline.aa_engine.cfg, 0, 0)
        expected = 32767.0 * (10.0 / 30.0)
        assert math.isclose(rx, expected, rel_tol=0.02)

    def test_mix_user_and_aimlock(self):
        pipeline = make_pipeline(aimlock_blend=0.5,
                                 feed=SimulatedTargetFeed(start_yaw_deg=10.0,
                                                          yaw_speed_deg_s=0.0))
        rx, ry = pipeline.apply(2000, 1000, True, True, False, 16.0,
                                pipeline.aa_engine.cfg, 0, 0)
        expected = 0.5 * 2000 + 0.5 * 32767.0 * (10.0 / 30.0)
        assert math.isclose(rx, expected, rel_tol=0.02)

    def test_pitch_above_aims_up(self):
        pipeline = make_pipeline(feed=SimulatedTargetFeed(start_yaw_deg=0.0,
                                                          pitch_offset_deg=10.0,
                                                          yaw_speed_deg_s=0.0))
        rx, ry = pipeline.apply(0, 0, True, True, False, 16.0,
                                pipeline.aa_engine.cfg, 0, 0)
        assert ry < 0

    def test_bounded_every_frame(self):
        pipeline = make_pipeline(
            feed=SimulatedTargetFeed(yaw_speed_deg_s=720.0))
        cfg = pipeline.aa_engine.cfg
        for _ in range(60):
            rx, ry = pipeline.apply(0, 0, True, True, False, 16.0, cfg, 0, 0)
            assert math.isfinite(rx) and math.isfinite(ry)
            assert abs(rx) <= 32767.0 + 1e-9
            assert abs(ry) <= 32767.0 + 1e-9


class TestSimulatedFeed:

    def test_advances_and_returns_state(self):
        feed = SimulatedTargetFeed(yaw_speed_deg_s=180.0, distance_cm=5000.0)
        state = feed.get_target(16.0)
        assert state is not None
        assert state.eye == (0.0, 0.0, 0.0)
        dist = math.sqrt(sum(c * c for c in state.target))
        assert math.isclose(dist, 5000.0, rel_tol=1e-6)
        for v in state.target + state.vel:
            assert math.isfinite(v)

    def test_stationary_when_speed_zero(self):
        feed = SimulatedTargetFeed(yaw_speed_deg_s=0.0, start_yaw_deg=10.0)
        s1 = feed.get_target(16.0)
        s2 = feed.get_target(16.0)
        assert all(math.isclose(a, b, abs_tol=1e-9) for a, b in zip(s1.target, s2.target))
        assert all(math.isclose(a, 0.0, abs_tol=1e-9) for a in s1.vel)

    def test_orbit_changes_sign(self):
        pipeline = make_pipeline(
            feed=SimulatedTargetFeed(yaw_speed_deg_s=720.0))
        cfg = pipeline.aa_engine.cfg
        signs = []
        for _ in range(60):
            rx, _ = pipeline.apply(0, 0, True, True, False, 16.0, cfg, 0, 0)
            if abs(rx) > 100:
                signs.append(1 if rx > 0 else -1)
        assert 1 in signs and -1 in signs

    def test_deterministic_with_zero_noise(self):
        a = make_pipeline(feed=SimulatedTargetFeed(yaw_speed_deg_s=90.0))
        b = make_pipeline(feed=SimulatedTargetFeed(yaw_speed_deg_s=90.0))
        ca, cb = a.aa_engine.cfg, b.aa_engine.cfg
        for _ in range(5):
            ra = a.apply(0, 0, True, True, False, 16.0, ca, 0, 0)
            rb = b.apply(0, 0, True, True, False, 16.0, cb, 0, 0)
            assert all(math.isclose(x, y, abs_tol=1e-9) for x, y in zip(ra, rb))


class TestProxySource:

    def test_proxy_engages_with_input_and_pulls_up(self):
        pipeline = make_pipeline(aimlock_source="proxy",
                                 aimlock_blend=1.0,
                                 aimlock_proxy_head_pull_deg=2.5)
        rx, ry = pipeline.apply(3000, 0, True, True, False, 16.0,
                                pipeline.aa_engine.cfg, 0, 0)
        assert ry < 0

    def test_proxy_idle_is_passthrough(self):
        pipeline = make_pipeline(aimlock_source="proxy")
        rx, ry = pipeline.apply(2000, 1000, False, True, False, 16.0,
                                pipeline.aa_engine.cfg, 0, 0)
        assert rx == 2000
        assert ry == 1000

    def test_cv_source_default_unchanged(self):
        pipeline = make_pipeline()
        rx, ry = pipeline.apply(2000, 1000, True, True, False, 16.0,
                                pipeline.aa_engine.cfg, 0, 0)
        assert rx == 2000
        assert ry == 1000
