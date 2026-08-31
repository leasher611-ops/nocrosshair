import pytest

from nocrosshair.core.config import AppConfig, BloomReducerConfig
from nocrosshair.features.bloom_reducer import BloomReducerEngine


def _config(**kw) -> BloomReducerConfig:
    base = dict(enabled=True, burst_shots=3, hold_ms=10, tap_gap_ms=10,
                reset_ms=50)
    base.update(kw)
    return BloomReducerConfig(**base)


class TestBloomReducerEngine:

    def test_disabled_passthrough(self):
        eng = BloomReducerEngine(_config(enabled=False))
        eng.set_active(False)
        assert eng.process(123, True) == 123

    def test_not_held_passthrough(self):
        eng = BloomReducerEngine(_config())
        eng.set_active(True)
        assert eng.process(100, False) == 100
        assert eng._phase == "idle"

    def test_burst_pattern(self):
        eng = BloomReducerEngine(_config(burst_shots=3, hold_ms=10,
                                         tap_gap_ms=10, reset_ms=50))
        eng.set_active(True)
        t = 0.0
        out = []
        for _ in range(400):
            t += 0.001
            out.append(eng.process(255, True, t))
        assert out[0] == 255
        # Cada tiro = hold de ~10ms consecutivos (255) — tolera float drift
        shot_runs = _consecutive_runs([i for i, v in enumerate(out) if v == 255])
        assert len(shot_runs) >= 6
        assert all(10 <= len(r) <= 11 for r in shot_runs[:6])
        # Rajada = 3 tiros; pausa de reset (50ms de zeros) separa rajadas
        bursts = _burst_groups(shot_runs, max_gap=20)
        assert len(bursts) >= 2
        assert [len(b) for b in bursts[:2]] == [3, 3]
        # Reset: 50ms = 50 frames sem tiro entre a última bala e a próxima
        gap = bursts[1][0][0] - bursts[0][-1][-1] - 1
        assert gap == 50

    def test_release_returns_idle_and_passthrough(self):
        eng = BloomReducerEngine(_config())
        eng.set_active(True)
        eng.process(255, True, 0.0)
        assert eng._phase != "idle"
        assert eng.process(80, False, 1.0) == 80
        assert eng._phase == "idle"

    def test_update_config_disables(self):
        eng = BloomReducerEngine(_config())
        eng.set_active(True)
        eng.update_config(_config(enabled=False))
        assert not eng.is_active

    def test_get_stats(self):
        eng = BloomReducerEngine(_config())
        eng.set_active(True)
        eng.process(255, True, 0.0)
        stats = eng.get_stats()
        assert stats["active"] is True
        assert "phase" in stats and "shots" in stats


def _consecutive_runs(indices: list) -> list:
    """Agrupa índices consecutivos (passo 1) em runs."""
    runs = []
    current = [indices[0]]
    for prev, cur in zip(indices, indices[1:]):
        if cur - prev == 1:
            current.append(cur)
        else:
            runs.append(current)
            current = [cur]
    runs.append(current)
    return runs


def _burst_groups(shot_runs: list, max_gap: int) -> list:
    """Agrupa tiros em rajadas: tiros com gap <= max_gap são da mesma rajada."""
    groups = []
    current = [shot_runs[0]]
    for prev, cur in zip(shot_runs, shot_runs[1:]):
        if cur[0] - prev[-1] - 1 <= max_gap:
            current.append(cur)
        else:
            groups.append(current)
            current = [cur]
    groups.append(current)
    return groups


class TestConfigRoundTrip:

    def test_bloom_reducer_config_roundtrip(self):
        ac = AppConfig()
        ac.bloom_reducer = BloomReducerConfig(
            enabled=True, burst_shots=5, hold_ms=20, tap_gap_ms=15,
            reset_ms=300)
        d = ac.to_dict()
        restored = AppConfig.from_dict(d)
        br = restored.bloom_reducer
        assert br.enabled is True
        assert br.burst_shots == 5
        assert br.hold_ms == 20
        assert br.tap_gap_ms == 15
        assert br.reset_ms == 300

    def test_defaults(self):
        ac = AppConfig()
        assert ac.bloom_reducer.burst_shots == 3
        assert ac.bloom_reducer.reset_ms == 250
