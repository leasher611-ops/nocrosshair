#!/usr/bin/env python3
"""Testes do Kernel Aim (BETA) — hardlock estilo kernel, sem memória."""

import math
from nocrosshair.features.kernel_aim import KernelAimConfig, KernelAimEngine


def make_engine(**kw) -> KernelAimEngine:
    return KernelAimEngine(KernelAimConfig(**kw))


class TestKernelAimEngagement:

    def test_no_input_no_lock(self):
        eng = make_engine()
        eng.set_input(0, 0, True, 1.0)
        assert eng.compute(1.0) is None
        assert eng.engaged is False

    def test_engages_with_input_and_fire(self):
        eng = make_engine()
        for i in range(40):
            eng.set_input(2000, 800, True, 1.0)
            out = eng.compute(1.0)
        assert eng.engaged is True
        assert out is not None

    def test_releases_when_stop_firing(self):
        eng = make_engine(release_ms=100.0)
        for i in range(40):
            eng.set_input(2000, 800, True, 1.0)
            eng.compute(1.0)
        assert eng.engaged is True
        for i in range(200):
            eng.set_input(0, 0, False, 1.0)
            eng.compute(1.0)
        assert eng.engaged is False

    def test_output_is_hard_lock(self):
        """Blend alto: a saída manda no stick (deflexão forte na direção)."""
        eng = make_engine(blend=0.92)
        for i in range(120):
            eng.set_input(2000, 800, True, 1.0)
            out = eng.compute(1.0)
        assert out is not None
        rx, ry = out
        assert math.hypot(rx, ry) > 8000.0

    def test_head_lock_pulls_up(self):
        """Head lock: pull de cabeça deixa o stick com componente pra cima
        (ry negativo = cima no Fortnite)."""
        eng = make_engine(head_pull_deg=3.0)
        for i in range(120):
            eng.set_input(3000, 0, True, 1.0)
            out = eng.compute(1.0)
        assert out is not None
        assert out[1] < 0.0

    def test_reset(self):
        eng = make_engine()
        for i in range(40):
            eng.set_input(2000, 800, True, 1.0)
            eng.compute(1.0)
        assert eng.engaged is True
        eng.reset()
        assert eng.engaged is False
        assert eng.target_state is None


class TestKernelAimPredictionFeed:

    def test_proxy_velocity_builds_up(self):
        """Input consistente = pseudo-velocidade do alvo cresce (feed do
        lead preditivo do lock)."""
        eng = make_engine()
        for i in range(120):
            eng.set_input(3500, 0, True, 1.0)
            eng.compute(1.0)
        st = eng.target_state
        assert st is not None
        assert st.vel[0] > 50.0
