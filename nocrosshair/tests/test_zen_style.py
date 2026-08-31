import pytest
from nocrosshair.features.zen_style import (
    StickyMagnetEngine, AimLockEngine, AimSpamEngine,
    RushEngine, AutoRotationEngine, HeadAssistEngine,
)


class TestStickyMagnetEngine:

    def test_disabled_returns_input_unchanged(self):
        eng = StickyMagnetEngine()
        rx, ry = eng.apply(1000, 500, enabled=False, strength=0.5,
                           magnetic_pull=400, is_shooting=True,
                           is_aiming=True, delta_ms=16.0)
        assert rx == 1000
        assert ry == 500

    def test_zero_strength_no_effect(self):
        eng = StickyMagnetEngine()
        rx, ry = eng.apply(1000, 0, enabled=True, strength=0.0,
                           magnetic_pull=400, is_shooting=True,
                           is_aiming=True, delta_ms=16.0)
        assert rx == 1000
        assert ry == 0

    def test_pull_amplifies_input_direction(self):
        eng = StickyMagnetEngine()
        rx, ry = eng.apply(1000, 0, enabled=True, strength=0.5,
                           magnetic_pull=400, is_shooting=True,
                           is_aiming=True, delta_ms=16.0)
        assert rx > 1000  # pull na direção do movimento
        assert ry == 0    # sem componente perpendicular

    def test_not_engaged_no_pull(self):
        eng = StickyMagnetEngine()
        rx, ry = eng.apply(1000, 0, enabled=True, strength=0.5,
                           magnetic_pull=400, is_shooting=False,
                           is_aiming=False, delta_ms=16.0)
        assert rx == 1000
        assert ry == 0

    def test_persistence_holds_release(self):
        import time
        eng = StickyMagnetEngine()
        now = time.monotonic()
        eng.apply(1000, 0, enabled=True, strength=0.5,
                  magnetic_pull=400, is_shooting=True,
                  is_aiming=True, delta_ms=16.0, now=now)
        # Jogador solta o stick (input 0) mas dentro da janela de persistência
        rx, ry = eng.apply(0, 0, enabled=True, strength=0.5,
                           magnetic_pull=400, is_shooting=True,
                           is_aiming=True, delta_ms=16.0, now=now + 0.03)
        assert ry == 0
        assert abs(rx) > 0  # mantém pull residual por alguns ms

    def test_output_clamped(self):
        eng = StickyMagnetEngine()
        rx, ry = eng.apply(32767, 32767, enabled=True, strength=1.0,
                           magnetic_pull=1200, is_shooting=True,
                           is_aiming=True, delta_ms=16.0)
        assert abs(rx) <= 32767
        assert abs(ry) <= 32767

    def test_reset_clears_persistence(self):
        eng = StickyMagnetEngine()
        eng.reset()
        rx, ry = eng.apply(0, 0, enabled=True, strength=0.5,
                           magnetic_pull=400, is_shooting=True,
                           is_aiming=True, delta_ms=16.0)
        assert rx == 0
        assert ry == 0


class TestAimLockEngine:

    def test_disabled_no_change(self):
        eng = AimLockEngine()
        rx, ry = eng.apply(1000, 0, enabled=False, strength=9000,
                           fov=4500, track=950, sticky=0.55,
                           smooth=0.3, is_shooting=True,
                           is_aiming=True, delta_ms=16.0)
        assert rx == 1000
        assert ry == 0

    def test_outside_fov_no_lock(self):
        eng = AimLockEngine()
        rx, ry = eng.apply(9000, 0, enabled=True, strength=9000,
                           fov=4500, track=950, sticky=0.55,
                           smooth=0.3, is_shooting=True,
                           is_aiming=True, delta_ms=16.0)
        assert rx == 9000
        assert ry == 0

    def test_inside_fov_pulls_toward_input(self):
        eng = AimLockEngine()
        rx, ry = eng.apply(1000, 0, enabled=True, strength=12000,
                           fov=4500, track=950, sticky=0.8,
                           smooth=0.0, is_shooting=True,
                           is_aiming=True, delta_ms=16.0)
        assert rx > 1000
        assert abs(ry) < 100

    def test_not_firing_no_lock(self):
        eng = AimLockEngine()
        rx, ry = eng.apply(1000, 0, enabled=True, strength=12000,
                           fov=4500, track=950, sticky=0.8,
                           smooth=0.0, is_shooting=False,
                           is_aiming=False, delta_ms=16.0)
        assert rx == 1000
        assert ry == 0

    def test_output_clamped(self):
        eng = AimLockEngine()
        rx, ry = eng.apply(30000, 0, enabled=True, strength=12000,
                           fov=4500, track=2000, sticky=1.0,
                           smooth=0.0, is_shooting=True,
                           is_aiming=True, delta_ms=16.0)
        assert abs(rx) <= 32767


class TestAimSpamEngine:

    def test_disabled_no_change(self):
        eng = AimSpamEngine()
        lt = eng.process_trigger(200.0, is_shooting=True, enabled=False,
                                 interval_ms=180, hold_ms=40)
        assert lt == 200.0

    def test_not_shooting_no_change(self):
        eng = AimSpamEngine()
        lt = eng.process_trigger(200.0, is_shooting=False, enabled=True,
                                 interval_ms=180, hold_ms=40)
        assert lt == 200.0

    def test_cycle_releases_ads_during_spray(self):
        import time
        eng = AimSpamEngine()
        now = time.monotonic()
        # Dentro da janela de release (intervalo decorrido)
        lt = eng.process_trigger(200.0, is_shooting=True, enabled=True,
                                 interval_ms=180, hold_ms=40, now=now)
        lt = eng.process_trigger(200.0, is_shooting=True, enabled=True,
                                 interval_ms=180, hold_ms=40, now=now + 0.20)
        assert lt == 0.0  # ADS solto para refrescar o AA
        # Após o ciclo completo, volta ao ADS normal
        lt = eng.process_trigger(200.0, is_shooting=True, enabled=True,
                                 interval_ms=180, hold_ms=40, now=now + 0.25)
        assert lt == 200.0

    def test_reset(self):
        eng = AimSpamEngine()
        eng.reset()
        lt = eng.process_trigger(0.0, is_shooting=True, enabled=True,
                                 interval_ms=180, hold_ms=40)
        assert lt == 0.0


class TestRushEngine:

    def test_disabled_returns_zero(self):
        eng = RushEngine()
        assert eng.get_strafe(0.0) == 0

    def test_active_pulses_strafe(self):
        eng = RushEngine(pulse_ms=10.0, cooldown_ms=90.0, deadzone=0.13)
        eng.set_active(True)
        # Dentro da janela de pulso: strafe não-zero na direção atual
        strafe = eng.get_strafe(0.0)
        assert strafe != 0
        # Após o ciclo completo, o pulso repete
        strafe_2 = eng.get_strafe(0.2)
        assert strafe_2 != 0

    def test_active_off_during_cooldown(self):
        eng = RushEngine(pulse_ms=10.0, cooldown_ms=90.0, deadzone=0.13)
        eng.set_active(True)
        # Em t=50ms está no cooldown (entre pulse 10ms e ciclo 100ms)
        strafe = eng.get_strafe(0.05)
        assert strafe == 0

    def test_deactivate_stops(self):
        eng = RushEngine(pulse_ms=10.0, cooldown_ms=90.0, deadzone=0.13)
        eng.set_active(True)
        eng.set_active(False)
        assert eng.get_strafe(0.0) == 0

    def test_update_config(self):
        eng = RushEngine()
        eng.update_config(5.0, 50.0, 0.2)
        eng.set_active(True)
        assert eng.get_strafe(0.0) != 0

    def test_reset(self):
        eng = RushEngine()
        eng.set_active(True)
        eng.reset()
        assert eng.get_strafe(0.0) == 0


class TestAutoRotationEngine:

    def test_disabled_returns_input(self):
        eng = AutoRotationEngine()
        rx, ry = eng.apply(0, 0, enabled=False, speed=200,
                           is_shooting=True, is_aiming=True, delta_ms=16.0)
        assert rx == 0
        assert ry == 0

    def test_active_input_passthrough(self):
        eng = AutoRotationEngine()
        # Stick em movimento: sem rotação automática
        rx, ry = eng.apply(5000, 0, enabled=True, speed=200,
                           is_shooting=True, is_aiming=True, delta_ms=16.0)
        assert rx == 5000
        assert ry == 0

    def test_released_stick_rotates_toward_bearing(self):
        eng = AutoRotationEngine()
        # Primeiro o jogador segura uma direção (define o bearing)
        eng.apply(5000, 0, enabled=True, speed=200,
                  is_shooting=True, is_aiming=True, delta_ms=16.0)
        # Depois solta o stick: deve injetar drift positivo em X
        rx, ry = eng.apply(0, 0, enabled=True, speed=200,
                           is_shooting=True, is_aiming=True, delta_ms=16.0)
        assert rx > 0
        assert abs(ry) < 1000

    def test_no_bearing_no_rotation(self):
        eng = AutoRotationEngine()
        # Nunca segurou direção: sem rotação
        rx, ry = eng.apply(0, 0, enabled=True, speed=200,
                           is_shooting=True, is_aiming=True, delta_ms=16.0)
        assert rx == 0
        assert ry == 0

    def test_output_clamped(self):
        eng = AutoRotationEngine()
        eng.apply(32767, 32767, enabled=True, speed=600,
                  is_shooting=True, is_aiming=True, delta_ms=16.0)
        rx, ry = eng.apply(0, 0, enabled=True, speed=600,
                           is_shooting=True, is_aiming=True, delta_ms=16.0)
        assert abs(rx) <= 32767
        assert abs(ry) <= 32767

    def test_reset(self):
        eng = AutoRotationEngine()
        eng.apply(5000, 0, enabled=True, speed=200,
                  is_shooting=True, is_aiming=True, delta_ms=16.0)
        eng.reset()
        rx, ry = eng.apply(0, 0, enabled=True, speed=200,
                           is_shooting=True, is_aiming=True, delta_ms=16.0)
        assert rx == 0
        assert ry == 0


class TestHeadAssistEngine:

    def test_disabled_returns_input(self):
        eng = HeadAssistEngine()
        rx, ry = eng.apply(1000, 0, enabled=False, strength=0.5,
                           is_shooting=True, is_aiming=True, delta_ms=16.0)
        assert rx == 1000
        assert ry == 0

    def test_zero_strength_no_effect(self):
        eng = HeadAssistEngine()
        rx, ry = eng.apply(1000, 0, enabled=True, strength=0.0,
                           is_shooting=True, is_aiming=True, delta_ms=16.0)
        assert rx == 1000
        assert ry == 0

    def test_pulls_up_when_engaged(self):
        """Grudado (input pequeno) + mirando → pull para cima (Y negativo)."""
        eng = HeadAssistEngine()
        rx, ry = eng.apply(500, 0, enabled=True, strength=0.5,
                           is_shooting=True, is_aiming=True, delta_ms=16.0)
        assert rx == 500
        assert ry < 0  # cima = Y negativo

    def test_no_pull_with_large_input(self):
        """Input grande (mira viajando) → sem pull, evita atrapalhar."""
        eng = HeadAssistEngine()
        rx, ry = eng.apply(10000, 5000, enabled=True, strength=0.5,
                           is_shooting=True, is_aiming=True, delta_ms=16.0)
        assert ry == 5000

    def test_not_engaged_no_pull(self):
        eng = HeadAssistEngine()
        rx, ry = eng.apply(500, 0, enabled=True, strength=0.5,
                           is_shooting=False, is_aiming=False, delta_ms=16.0)
        assert rx == 500
        assert ry == 0

    def test_ramps_with_time(self):
        """O pull aumenta conforme o tempo grudado (mais confiança)."""
        eng = HeadAssistEngine()
        _, ry1 = eng.apply(500, 0, enabled=True, strength=0.5,
                           is_shooting=True, is_aiming=True, delta_ms=16.0)
        _, ry2 = eng.apply(500, 0, enabled=True, strength=0.5,
                           is_shooting=True, is_aiming=True, delta_ms=16.0)
        assert ry2 < ry1  # mais negativo = mais para cima

    def test_output_clamped(self):
        eng = HeadAssistEngine()
        rx, ry = eng.apply(0, 0, enabled=True, strength=1.0,
                           is_shooting=True, is_aiming=True, delta_ms=16.0)
        assert rx == 0
        assert -32767 <= ry <= 32767

    def test_reset(self):
        eng = HeadAssistEngine()
        eng.apply(500, 0, enabled=True, strength=0.5,
                  is_shooting=True, is_aiming=True, delta_ms=16.0)
        eng.reset()
        rx, ry = eng.apply(500, 0, enabled=True, strength=0.5,
                           is_shooting=True, is_aiming=True, delta_ms=16.0)
        assert ry < 0


class TestHeadLockEngine:

    def _locked_engine(self, **kwargs):
        eng = HeadAssistEngine()
        # Rampa completa de engajamento para isolar o comportamento do lock
        for _ in range(10):
            eng.apply(500, 0, enabled=True, strength=0.5,
                      is_shooting=True, is_aiming=True, delta_ms=16.0)
        return eng

    def test_lock_window_smaller_disables_pull(self):
        """Window menor que a mag do input → sem pull (não está "na cabeça")."""
        eng = HeadAssistEngine()
        rx, ry = eng.apply(2500, 0, enabled=True, strength=0.5,
                           is_shooting=True, is_aiming=True, delta_ms=16.0,
                           lock_window=1000)
        assert ry == 0

    def test_lock_window_larger_enables_pull(self):
        eng = HeadAssistEngine()
        _, ry = eng.apply(2500, 0, enabled=True, strength=0.5,
                          is_shooting=True, is_aiming=True, delta_ms=16.0,
                          lock_window=5000)
        assert ry < 0

    def test_pulse_oscillates_pull(self):
        """Pulse: pull forte na maior parte do ciclo, queda curta no fim."""
        eng = self._locked_engine()
        rx1, ry1 = eng.apply(500, 0, enabled=True, strength=0.5,
                             is_shooting=True, is_aiming=True, delta_ms=1.0,
                             headlock_pulse=True, headlock_pulse_ms=100)
        # ciclo = 100ms; 1ms está no "sobe" (fase < 80% do ciclo)
        assert ry1 < 0
        # avança até a fase 79ms (ainda no "sobe" — 80% do ciclo)
        for _ in range(78):
            rx1, ry1 = eng.apply(500, 0, enabled=True, strength=0.5,
                                 is_shooting=True, is_aiming=True, delta_ms=1.0,
                                 headlock_pulse=True, headlock_pulse_ms=100)
        rx2, ry2 = eng.apply(500, 0, enabled=True, strength=0.5,
                             is_shooting=True, is_aiming=True, delta_ms=1.0,
                             headlock_pulse=True, headlock_pulse_ms=100)
        # fase 80ms = fim do ciclo → queda curta (0.6x) → menos negativo
        assert ry2 > ry1

    def test_pulse_off_keeps_continuous_pull(self):
        """Pulse off = mesmo comportamento da rampa contínua original."""
        eng = HeadAssistEngine()
        _, ry1 = eng.apply(500, 0, enabled=True, strength=0.5,
                           is_shooting=True, is_aiming=True, delta_ms=16.0)
        _, ry2 = eng.apply(500, 0, enabled=True, strength=0.5,
                           is_shooting=True, is_aiming=True, delta_ms=16.0,
                           headlock_pulse=False)
        assert ry2 < ry1  # contínuo: rampa cresce sem pulse

    def test_drift_limit_reduces_pull_when_fighting_down(self):
        """Jogador puxando forte para baixo além do limite → pull atenuado."""
        eng = self._locked_engine()
        _, ry_no_fight = eng.apply(500, 4000, enabled=True, strength=0.5,
                                   is_shooting=True, is_aiming=True, delta_ms=16.0,
                                   drift_limit=2000)
        eng = self._locked_engine()
        _, ry_fight = eng.apply(500, 4000, enabled=True, strength=0.5,
                                is_shooting=True, is_aiming=True, delta_ms=16.0,
                                drift_limit=0)
        assert ry_no_fight > ry_fight  # menos puxado para cima (pull menor)

    def test_drift_limit_zero_preserves_original(self):
        eng = self._locked_engine()
        _, ry_a = eng.apply(500, 3000, enabled=True, strength=0.5,
                            is_shooting=True, is_aiming=True, delta_ms=16.0)
        eng = self._locked_engine()
        _, ry_b = eng.apply(500, 3000, enabled=True, strength=0.5,
                            is_shooting=True, is_aiming=True, delta_ms=16.0,
                            drift_limit=0)
        assert ry_a == ry_b
