#!/usr/bin/env python3

import math
from nocrosshair.features.proxy_target import ProxyTargetConfig, ProxyTargetFeed


def base_cfg(**kw) -> ProxyTargetConfig:
    kw.setdefault("release_ms", 250.0)
    kw.setdefault("hold_decay", 8.0)
    return ProxyTargetConfig(**kw)


class TestEngagement:

    def test_idle_no_target(self):
        feed = ProxyTargetFeed(base_cfg())
        feed.set_input(0, 0, False, 16.0)
        assert feed.get_target(16.0) is None

    def test_shooting_without_input_does_not_engage(self):
        feed = ProxyTargetFeed(base_cfg())
        feed.set_input(0, 0, True, 16.0)
        assert feed.get_target(16.0) is None

    def test_shooting_with_input_engages(self):
        feed = ProxyTargetFeed(base_cfg())
        feed.set_input(3000, 0, True, 16.0)
        assert feed.get_target(16.0) is not None
        assert feed.engaged is True

    def test_releases_after_stop_shooting(self):
        feed = ProxyTargetFeed(base_cfg(release_ms=200.0))
        feed.set_input(3000, 0, True, 16.0)
        assert feed.get_target(16.0) is not None
        feed.set_input(0, 0, False, 250.0)
        assert feed.get_target(16.0) is None

    def test_holds_while_still_shooting(self):
        """Atirando com input: o lock segura (bridge curto)."""
        feed = ProxyTargetFeed(base_cfg(release_ms=200.0))
        feed.set_input(3000, 0, True, 16.0)
        for _ in range(2):
            feed.set_input(0, 0, True, 16.0)
        assert feed.get_target(16.0) is not None

    def test_releases_when_stick_zero_while_shooting(self):
        """Atirando com o stick ZERADO por mais que zero_release_ms: o lock
        solta — a câmera não pode continuar andando sozinha pro lado do
        último input."""
        feed = ProxyTargetFeed(base_cfg(release_ms=200.0, zero_release_ms=80.0))
        feed.set_input(3000, 0, True, 16.0)
        assert feed.get_target(16.0) is not None
        for _ in range(10):
            feed.set_input(0, 0, True, 16.0)
        assert feed.get_target(16.0) is None


class TestHeadPull:

    def test_target_above_center(self):
        feed = ProxyTargetFeed(base_cfg(head_pull_deg=2.5))
        feed.set_input(3000, 0, True, 16.0)
        state = feed.get_target(16.0)
        assert state is not None
        _, _, z = state.target
        assert z > 0.0

    def test_distance_respected(self):
        feed = ProxyTargetFeed(base_cfg(assumed_dist_cm=3000.0, head_pull_deg=0.0))
        feed.set_input(3000, 0, True, 16.0)
        state = feed.get_target(16.0)
        dist = math.sqrt(sum(c * c for c in state.target))
        assert math.isclose(dist, 3000.0, rel_tol=1e-6)


class TestDirection:

    def test_follows_input_yaw(self):
        feed = ProxyTargetFeed(base_cfg(head_pull_deg=0.0))
        feed.set_input(0, -3000, True, 16.0)
        state = feed.get_target(16.0)
        tx, ty, _ = state.target
        assert ty < 0.0

    def test_direction_decays_when_input_stops(self):
        feed = ProxyTargetFeed(base_cfg(head_pull_deg=0.0, hold_decay=8.0))
        feed.set_input(-3000, -1000, True, 16.0)
        s1 = feed.get_target(16.0)
        a1 = math.degrees(math.atan2(s1.target[1], s1.target[0]))
        for _ in range(3):
            feed.set_input(0, 0, True, 16.0)
        s2 = feed.get_target(16.0)
        a2 = math.degrees(math.atan2(s2.target[1], s2.target[0]))
        assert abs(a2) < abs(a1)

    def test_decay_zero_holds_direction_briefly(self):
        """hold_decay=0 segura a direção DENTRO da janela de zero_release_ms
        (bridge curto); depois do zero_release o lock solta."""
        feed = ProxyTargetFeed(base_cfg(head_pull_deg=0.0, hold_decay=0.0))
        feed.set_input(-3000, 0, True, 16.0)
        s1 = feed.get_target(16.0)
        for _ in range(3):
            feed.set_input(0, 0, True, 16.0)
        s2 = feed.get_target(16.0)
        assert math.isclose(s2.target[0], s1.target[0], abs_tol=1e-9)
        for _ in range(10):
            feed.set_input(0, 0, True, 16.0)
        assert feed.get_target(16.0) is None
