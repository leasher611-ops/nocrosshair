import pytest
from nocrosshair.features.recoil import RecoilEngine, RecoilState


class TestRecoilEngineSetPreset:

    def test_known_preset(self):
        engine = RecoilEngine()
        engine.set_preset("FURY AR")
        assert engine.active_preset == "FURY AR"

    def test_known_preset_uppercase_normalized(self):
        engine = RecoilEngine()
        engine.set_preset("spire rifle")
        assert engine.active_preset == "SPIRE RIFLE"

    def test_unknown_preset_keeps_current(self):
        engine = RecoilEngine()
        original = engine.active_preset
        engine.set_preset("UNKNOWN_WEAPON")
        assert engine.active_preset == original


class TestRecoilEngineApplyTick:

    def _preset(self, strength=65, x_strength=0, ticks=60, curve="ease_out"):
        return {"strength": strength, "x_strength": x_strength, "ticks": ticks, "curve": curve}

    def test_first_tick_has_offset(self):
        engine = RecoilEngine()
        preset = self._preset()
        y, x = engine.apply_tick(0, 60, ry_raw=0, rx_raw=0, preset=preset, recoil_y_gate=False)
        assert y > 0

    def test_last_tick_lower_than_first(self):
        engine = RecoilEngine()
        preset = self._preset()
        y_first, _ = engine.apply_tick(0, 60, ry_raw=0, rx_raw=0, preset=preset, recoil_y_gate=False)
        y_last, _ = engine.apply_tick(59, 60, ry_raw=0, rx_raw=0, preset=preset, recoil_y_gate=False)
        assert y_last <= y_first

    def test_out_of_bounds_tick_clamped(self):
        engine = RecoilEngine()
        preset = self._preset()
        y_neg, _ = engine.apply_tick(-5, 60, ry_raw=0, rx_raw=0, preset=preset, recoil_y_gate=False)
        y_overflow, _ = engine.apply_tick(999, 60, ry_raw=0, rx_raw=0, preset=preset, recoil_y_gate=False)
        y_0, _ = engine.apply_tick(0, 60, ry_raw=0, rx_raw=0, preset=preset, recoil_y_gate=False)
        y_59, _ = engine.apply_tick(59, 60, ry_raw=0, rx_raw=0, preset=preset, recoil_y_gate=False)
        assert y_neg == y_0
        assert y_overflow == y_59


class TestYGate:

    def test_y_gate_reduces_offset(self):
        engine = RecoilEngine()
        preset = {"strength": 65, "x_strength": 0, "ticks": 60, "curve": "ease_out"}
        y_no_gate, _ = engine.apply_tick(0, 60, ry_raw=0, rx_raw=0, preset=preset, recoil_y_gate=False)
        y_gated, _ = engine.apply_tick(0, 60, ry_raw=8000, rx_raw=0, preset=preset, recoil_y_gate=True)
        assert y_gated < y_no_gate

    def test_no_movement_unchanged(self):
        engine = RecoilEngine()
        preset = {"strength": 65, "x_strength": 0, "ticks": 60, "curve": "ease_out"}
        y_0, _ = engine.apply_tick(0, 60, ry_raw=0, rx_raw=0, preset=preset, recoil_y_gate=True)
        y_0_nogate, _ = engine.apply_tick(0, 60, ry_raw=0, rx_raw=0, preset=preset, recoil_y_gate=False)
        assert y_0 == y_0_nogate


class TestRecoilState:

    def test_reset_zeroes_all(self):
        state = RecoilState()
        state.tick = 10
        state.delay_remaining = 50
        state.return_offset_y = 200
        state.return_offset_x = 100
        state.last_offset_y = 150
        state.last_offset_x = 80
        state.reset(delay_ms=45)
        assert state.tick == 0
        assert state.delay_remaining == 45
        assert state.return_offset_y == 0
        assert state.return_offset_x == 0
        assert state.last_offset_y == 0
        assert state.last_offset_x == 0

    def test_advance_tick_during_delay(self):
        state = RecoilState()
        state.reset(delay_ms=50)
        result = state.advance_tick(delta_ms=10)
        assert result is False
        assert state.delay_remaining == 40

    def test_advance_tick_after_delay(self):
        state = RecoilState()
        state.reset(delay_ms=10)
        state.advance_tick(delta_ms=10)
        result = state.advance_tick(delta_ms=1)
        assert result is True

    def test_advance_tick_past_zero(self):
        state = RecoilState()
        state.reset(delay_ms=10)
        state.advance_tick(delta_ms=50)
        assert state.delay_remaining < 0
        result = state.advance_tick(delta_ms=1)
        assert result is True
