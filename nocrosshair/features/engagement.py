#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Modelo unificado de engajamento (Fase A).

Sem visão computacional, o "engajamento" é inferido do input: quando o
jogador está mirando/atirando com o stick quase parado, ele está PERTO do
alvo — o aim assist nativo do jogo já está grudado. Esse estimador produz
um único sinal (confidence + estágio + direção de acompanhamento) que
comanda TODOS os engines do pipeline, em vez de cada um ter sua própria
heurística (que era a causa da briga entre slowdown vs boost).

Sinais de entrada:
  - magnitude do input (pequeno = perto do alvo)
  - consistência de direção (mesma direção por N frames = seguindo o alvo)
  - is_shooting / is_aiming (engajado no combate)
  - tempo de permanência ("dwell") no estágio locked/tracking

Saídas:
  - stage: IDLE / SEARCHING / TRACKING / LOCKED
  - confidence: 0..1 (quão confiante de que está no alvo)
  - follow_dir: (x, y) direção de acompanhamento (EMA da direção recente)
"""

import math
from collections import deque
from typing import Tuple


class EngagementEstimator:

    IDLE = 0
    SEARCHING = 1
    TRACKING = 2
    LOCKED = 3

    def __init__(self, lock_mag: float = 2500.0, search_mag: float = 8000.0,
                 direction_alpha: float = 0.15, dwell_ramp_ms: float = 250.0) -> None:
        self.lock_mag = lock_mag
        self.search_mag = search_mag
        self.direction_alpha = direction_alpha
        self.dwell_ramp_ms = dwell_ramp_ms
        self.stage: int = self.IDLE
        self.confidence: float = 0.0
        self.follow_dir: Tuple[float, float] = (0.0, 0.0)
        self._dir_history: deque = deque(maxlen=12)
        self._dwell_ms: float = 0.0

    @property
    def locked(self) -> bool:
        return self.stage == self.LOCKED

    def update(self, rx: float, ry: float, is_shooting: bool,
               is_aiming: bool, delta_ms: float) -> float:
        mag = math.hypot(rx, ry)
        engaged = is_shooting or is_aiming

        # ── Estágio ──
        if mag < 60 and not engaged:
            new_stage = self.IDLE
        elif mag > self.search_mag:
            new_stage = self.SEARCHING
        elif engaged and mag < self.lock_mag:
            # LOCKED só com input real — sem isso, o jogador solta o stick
            # e o stage fica preso em LOCKED (mag=0 < lock_mag + shooting),
            # fazendo o follow_assist puxar na última direção pra sempre.
            new_stage = self.LOCKED if (is_shooting and mag > 60) else self.TRACKING
        elif engaged:
            new_stage = self.TRACKING
        else:
            new_stage = self.SEARCHING
        self.stage = new_stage

        # ── Direção de acompanhamento (EMA da direção recente) ──
        if mag > 150:
            nx, ny = rx / mag, ry / mag
            fx, fy = self.follow_dir
            self.follow_dir = (
                fx + self.direction_alpha * (nx - fx),
                fy + self.direction_alpha * (ny - fy),
            )
            self._dir_history.append((nx, ny))
        elif mag < 60:
            self._dir_history.clear()

        # ── Dwell (tempo grudado) ──
        if self.stage >= self.TRACKING:
            self._dwell_ms += delta_ms
        else:
            self._dwell_ms = max(0.0, self._dwell_ms - delta_ms * 2.0)

        # ── Confidence ──
        if self.stage == self.IDLE:
            self.confidence = 0.0
            return self.confidence
        stage_base = {
            self.SEARCHING: 0.05,
            self.TRACKING: 0.4,
            self.LOCKED: 0.7,
        }[self.stage]
        coherence = self._coherence()
        dwell_bonus = min(0.2, self._dwell_ms / max(self.dwell_ramp_ms, 1.0))
        shooting_bonus = 0.1 if is_shooting else 0.0
        self.confidence = max(0.0, min(1.0,
            stage_base + 0.15 * coherence + dwell_bonus + shooting_bonus))
        return self.confidence

    def _coherence(self) -> float:
        """Coerência da direção recente (1 = perfeitamente consistente)."""
        if len(self._dir_history) < 3:
            return 0.5
        n = len(self._dir_history)
        sx = sum(x for x, _ in self._dir_history)
        sy = sum(y for _, y in self._dir_history)
        return math.hypot(sx / n, sy / n)

    def reset(self) -> None:
        self.stage = self.IDLE
        self.confidence = 0.0
        self.follow_dir = (0.0, 0.0)
        self._dir_history.clear()
        self._dwell_ms = 0.0
