#!/usr/bin/env python3
"""
Motor de Rapid Fire (estilo Cronus Zen).
Alterna o gatilho de tiro em alta frequência para maximizar a cadência
de armas semi-automáticas, transformando-as em automáticas.

Arquitetura:
  - Máquina de estados com 2 fases: HOLD e RELEASE
  - Temporização precisa baseada em monotonic clock (sem drift)
  - Lock-free: thread-safe via estado atômico simples
"""

import time
from dataclasses import dataclass
from typing import Tuple

from nocrosshair.core.config import RapidFireConfig


@dataclass
class RapidFireState:
    """Estado interno do motor de Rapid Fire."""
    phase: str = "idle"        # "idle", "hold", "release"
    last_transition: float = 0.0  # timestamp da última transição
    cycle_count: int = 0       # ciclos completados


class RapidFireEngine:
    """Motor de Rapid Fire com timing preciso.

    Quando ativo, intercepta o estado do gatilho RT/R2 e alterna
    entre pressionado/liberado na frequência configurada.

    Uso:
        engine = RapidFireEngine(config)
        # No loop de input:
        rt_value = engine.process(rt_raw, is_rt_pressed, delta_ms)
    """

    def __init__(self, config: RapidFireConfig):
        self.config = config
        self.state = RapidFireState()
        self._active = False

    def set_active(self, active: bool) -> None:
        """Liga/desliga o motor de rapid fire."""
        if active and not self._active:
            self.state = RapidFireState(
                phase="hold",
                last_transition=time.monotonic(),
                cycle_count=0,
            )
        elif not active:
            self.state.phase = "idle"
        self._active = active

    @property
    def is_active(self) -> bool:
        return self._active

    def toggle(self) -> bool:
        """Alterna o estado ativo. Retorna o novo estado."""
        self.set_active(not self._active)
        return self._active

    def process(self, rt_raw: int, is_trigger_held: bool, delta_ms: float) -> int:
        """Processa o valor do gatilho aplicando rapid fire.

        Args:
            rt_raw: Valor bruto do gatilho (0-255)
            is_trigger_held: Se o jogador está segurando o gatilho
            delta_ms: Tempo desde o último frame em ms

        Returns:
            Valor processado do gatilho (0-255)
        """
        if not self._active or not is_trigger_held:
            if not is_trigger_held:
                self.state.phase = "idle"
            return rt_raw

        now = time.monotonic()
        elapsed_ms = (now - self.state.last_transition) * 1000.0

        if self.state.phase == "idle":
            # Inicia novo ciclo
            self.state.phase = "hold"
            self.state.last_transition = now
            return 255  # Pressionado total

        elif self.state.phase == "hold":
            if elapsed_ms >= self.config.hold_ms:
                self.state.phase = "release"
                self.state.last_transition = now
                return 0  # Liberado
            return 255  # Mantém pressionado

        elif self.state.phase == "release":
            if elapsed_ms >= self.config.release_ms:
                self.state.phase = "hold"
                self.state.last_transition = now
                self.state.cycle_count += 1
                return 255  # Volta a pressionar
            return 0  # Mantém liberado

        return rt_raw

    def process_from_speed(self, rt_raw: int, is_trigger_held: bool, delta_ms: float) -> int:
        """Versão alternativa que calcula hold/release a partir de speed (Hz).

        Se speed = 50 Hz -> 1 ciclo = 20ms -> hold=10ms, release=10ms

        Modos (universal/pistol/shotgun/custom) ajustam speed e hold_ratio:
        - universal: release curto (~25% do ciclo) para não stutterar full-auto
          enquanto semi-autos disparam no teto.
        - pistol: mais Hz (semi-auto rápida).
        - shotgun: mais lento, hold dominante.
        """
        mode = getattr(self.config, "mode", "universal")
        if mode == "pistol":
            self.config.speed = max(self.config.speed, 70)
            ratio = 0.60
        elif mode == "shotgun":
            self.config.speed = min(self.config.speed, 30)
            ratio = 0.75
        elif mode == "custom":
            ratio = max(0.30, min(0.95, self.config.hold_ratio))
        else:  # universal
            ratio = max(0.30, min(0.95, self.config.hold_ratio))

        if self.config.speed > 0:
            cycle_ms = 1000.0 / self.config.speed
            self.config.hold_ms = max(1, int(cycle_ms * ratio))
            self.config.release_ms = max(1, int(cycle_ms * (1.0 - ratio)))
        return self.process(rt_raw, is_trigger_held, delta_ms)

    def get_stats(self) -> dict:
        """Retorna estatísticas do motor para a UI."""
        effective_hz = 0
        if self._active and self.config.hold_ms + self.config.release_ms > 0:
            effective_hz = 1000.0 / (self.config.hold_ms + self.config.release_ms)
        return {
            "active": self._active,
            "phase": self.state.phase,
            "cycles": self.state.cycle_count,
            "effective_hz": round(effective_hz, 1),
        }

    def update_config(self, config: RapidFireConfig) -> None:
        """Atualiza a configuração em tempo real."""
        self.config = config
        if not config.enabled:
            self.set_active(False)
