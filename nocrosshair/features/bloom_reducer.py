#!/usr/bin/env python3
"""
Motor de Bloom Reducer (estilo Cronus Zen).

O bloom do Fortnite cresce com o tiro contínuo e zera após uma pausa.
Este motor transforma o gatilho segurado em rajadas curtas: N tiros,
pausa de reset, N tiros... — cada rajada recomeça com a primeira bala
(spread mínimo = bloom de "first shot").

Arquitetura:
  - Máquina de estados com 4 fases: idle -> hold -> tap -> reset
  - Temporização precisa baseada em monotonic clock (sem drift)
"""

import time
from typing import Optional

from nocrosshair.core.config import BloomReducerConfig


class BloomReducerEngine:
    """Motor de rajadas com reset de bloom.

    Quando ativo e o gatilho estiver segurado:
      hold (255) por hold_ms  -> tiro
      tap  (0)   por tap_gap_ms -> separa tiros da rajada
      reset (0)  por reset_ms -> pausa longa p/ o bloom zerar
    Cada rajada dispara ``burst_shots`` tiros antes da pausa de reset.
    Soltar o gatilho volta ao idle e passa o valor bruto.
    """

    def __init__(self, config: Optional[BloomReducerConfig] = None):
        self.config = config if config is not None else BloomReducerConfig()
        self._phase: str = "idle"   # idle | hold | tap | reset
        self._shots: int = 0
        self._phase_start: float = 0.0
        self._active: bool = False

    def set_active(self, active: bool) -> None:
        self._active = active
        if not active:
            self._phase = "idle"

    @property
    def is_active(self) -> bool:
        return self._active

    def toggle(self) -> bool:
        """Alterna o estado ativo. Retorna o novo estado."""
        self.set_active(not self._active)
        return self._active

    def process(self, rt_raw: int, is_trigger_held: bool,
                now: Optional[float] = None) -> int:
        """Processa o valor do gatilho aplicando rajadas de bloom.

        Args:
            rt_raw: Valor bruto do gatilho (0-255)
            is_trigger_held: Se o jogador está segurando o gatilho
            now: Timestamp (monotonic) para testes

        Returns:
            Valor processado do gatilho (0-255)
        """
        if not self._active or not is_trigger_held:
            if not is_trigger_held:
                self._phase = "idle"
                self._shots = 0
            return rt_raw

        t = now if now is not None else time.monotonic()
        elapsed = (t - self._phase_start) * 1000.0
        cfg = self.config

        if self._phase == "idle":
            self._phase = "hold"
            self._shots = 1
            self._phase_start = t
            return 255

        elif self._phase == "hold":
            if elapsed >= cfg.hold_ms:
                self._phase_start = t
                if self._shots >= cfg.burst_shots:
                    self._phase = "reset"
                    return 0
                self._phase = "tap"
                return 0
            return 255

        elif self._phase == "tap":
            if elapsed >= cfg.tap_gap_ms:
                self._phase = "hold"
                self._shots += 1
                self._phase_start = t
                return 255
            return 0

        elif self._phase == "reset":
            if elapsed >= cfg.reset_ms:
                self._phase = "hold"
                self._shots = 1
                self._phase_start = t
                return 255
            return 0

        return rt_raw

    def update_config(self, config: BloomReducerConfig) -> None:
        """Atualiza a configuração em tempo real."""
        self.config = config
        if not config.enabled:
            self.set_active(False)

    def get_stats(self) -> dict:
        return {
            "active": self._active,
            "phase": self._phase,
            "shots": self._shots,
        }
