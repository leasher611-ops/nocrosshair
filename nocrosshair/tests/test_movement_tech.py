import pytest
from nocrosshair.features.movement_tech import (
    DodgeShotEngine, SlideCancelEngine2, BunnyHopEngine,
)


class TestDodgeShotEngine:

    def test_disabled_no_output(self):
        eng = DodgeShotEngine()
        assert eng.process(True, 0.0) == {}

    def test_not_shooting_no_output(self):
        eng = DodgeShotEngine()
        eng.set_active(True)
        assert eng.process(False, 0.0) == {}

    def test_alternates_crouch(self):
        import time
        eng = DodgeShotEngine(hold_ms=80, release_ms=120, crouch_button_code=318)
        eng.set_active(True)
        t0 = time.monotonic()
        transitions = []
        last = None
        while (time.monotonic() - t0) * 1000 < 450:
            out = eng.process(True, time.monotonic())
            v = out.get(318)
            if v is not None and v != last:
                transitions.append(v)
                last = v
        # Alterna 1/0 várias vezes
        assert transitions.count(1) >= 2
        assert transitions.count(0) >= 1
        # Alternância estrita
        assert transitions == [1, 0, 1, 0, 1][:len(transitions)]

    def test_deactivate_stops(self):
        eng = DodgeShotEngine()
        eng.set_active(True)
        eng.set_active(False)
        assert eng.process(True, 0.0) == {}

    def test_reset(self):
        eng = DodgeShotEngine()
        eng.set_active(True)
        eng.reset()
        assert eng._crouching is False

    def test_faster_default_timings(self):
        """Dodge shot mais rápido (macro-like) com mínimo legítimo >= 30ms."""
        from nocrosshair.core.config import MovementTechConfig
        mt = MovementTechConfig()
        assert mt.dodge_hold_ms == 40
        assert mt.dodge_release_ms == 60
        assert mt.dodge_hold_ms >= 30
        assert mt.dodge_release_ms >= 30

    def test_jitter_bounded(self):
        """Jitter anti-detecção: fica dentro do range (0-12ms) e nunca
        empurra o ciclo abaixo do mínimo legítimo de ~30ms."""
        eng = DodgeShotEngine(hold_ms=40, release_ms=60, crouch_button_code=318)
        eng.set_active(True)
        t = 0.0
        crouches = 0
        for _ in range(400):
            out = eng.process(True, t)
            if out.get(318) == 1:
                crouches += 1
            assert 0.0 <= eng._jitter_ms < 12.0
            t += 0.004
        # Com hold 40ms + jitter<12, o agachamento dispara várias vezes
        assert crouches >= 2


class TestSlideCancelEngine2:

    def test_disabled_no_output(self):
        eng = SlideCancelEngine2()
        eng.notify_jump()
        assert eng.process(0.0) == {}

    def test_sequence_crouch_tap_tap_jump(self):
        import time
        eng = SlideCancelEngine2(crouch_button_code=318, jump_button_code=304,
                                 tap_ms=40, gap_ms=40)
        eng.set_active(True)
        eng.notify_jump()
        t0 = time.monotonic()
        seq = []
        last = None
        while (time.monotonic() - t0) * 1000 < 300:
            out = eng.process(time.monotonic())
            v = out.get(318, out.get(304))
            if v is not None and v != last:
                seq.append(v)
                last = v
        # crouch on/off + crouch on/off + jump on/off
        assert seq == [1, 0, 1, 0, 1, 0]
        # Estado final idle
        assert eng._state == eng.IDLE

    def test_no_jump_no_sequence(self):
        eng = SlideCancelEngine2()
        eng.set_active(True)
        assert eng.process(0.0) == {}

    def test_toggle(self):
        eng = SlideCancelEngine2()
        assert eng.toggle() is True
        assert eng.toggle() is False

    def test_reset(self):
        eng = SlideCancelEngine2()
        eng.set_active(True)
        eng.notify_jump()
        eng.reset()
        assert eng._state == eng.IDLE


class TestBunnyHopEngine:

    def test_disabled_no_output(self):
        eng = BunnyHopEngine()
        assert eng.process(True, 0.0) == {}

    def test_not_moving_no_output(self):
        eng = BunnyHopEngine()
        eng.set_active(True)
        assert eng.process(False, 0.0) == {}

    def test_hops_while_moving(self):
        import time
        eng = BunnyHopEngine(jump_button_code=304, hold_ms=50, gap_ms=120)
        eng.set_active(True)
        t0 = time.monotonic()
        presses = 0
        last = None
        while (time.monotonic() - t0) * 1000 < 600:
            out = eng.process(True, time.monotonic())
            v = out.get(304)
            if v == 1 and last != 1:
                presses += 1
            last = v
        assert presses >= 3

    def test_deactivate_stops(self):
        eng = BunnyHopEngine()
        eng.set_active(True)
        eng.set_active(False)
        assert eng.process(True, 0.0) == {}

    def test_reset(self):
        eng = BunnyHopEngine()
        eng.set_active(True)
        eng.reset()
        assert eng._jumping is False
