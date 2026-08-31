#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Motores avançados de aim assist (segunda geração).

Três engines novos, ortogonais aos motores estilo Zen existentes, que levam
o aim assist a um nível diferente de suavidade e aderência:

1. :class:`OneEuroFilter` — filtro adaptativo (Casiez et al., "1€ filter")
   que remove jitter em baixa velocidade (mais suavização) e responde rápido
   em alta velocidade (menos latência). Substitui o anti-shake de blend fixo.

2. :class:`PredictiveTracker` — predição de movimento do right stick com
   filtro alfa-beta + termo de aceleração. A velocidade/derivada são
   suavizadas por EMA, o lead só é aplicado quando a direção se mantém
   consistente por N frames (sem predizer ruído) e é limitado por um cap
   anti-overshoot. Produz o "lead" que adianta a mira no alvo em movimento.

3. :class:`AdhesionBuffer` — "grude": (a) persistência de direção quando o
   jogador solta o stick (o retículo não escapa do alvo por alguns ms) e
   (b) axis-lock — perto do centro, o eixo não-dominante é atenuado para o
   retículo não "derrapar" em diagonal para fora do alvo.

Todos nascem desligados (config default), preservando o comportamento atual.
"""

import math
import time
from typing import Tuple, Optional


class OneEuroFilter:
    """Filtro 1€ adaptativo (jitter removal com resposta rápida).

    Referência: Casiez, Roussel & Vogel (CHI 2012). O cutoff sobe conforme a
    velocidade do sinal (``beta * |dx/dt|``), então o filtro fica mais
    "aberto" em movimento rápido e mais "fechado" quando o input é lento —
    exatamente o trade-off anti-shake que um blend fixo não consegue.
    """

    def __init__(self, min_cutoff: float = 1.0, beta: float = 0.05,
                 d_cutoff: float = 1.0) -> None:
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self._prev: Optional[float] = None
        self._prev_dx: float = 0.0
        self._value: float = 0.0
        self._initialized: bool = False

    def set_params(self, min_cutoff: float, beta: float, d_cutoff: float) -> None:
        self.min_cutoff = max(min_cutoff, 1e-6)
        self.beta = max(beta, 0.0)
        self.d_cutoff = max(d_cutoff, 1e-6)

    @staticmethod
    def _alpha(cutoff: float, dt: float) -> float:
        tau = 1.0 / (2.0 * math.pi * max(cutoff, 1e-6))
        return 1.0 / (1.0 + tau / max(dt, 1e-6))

    def filter(self, x: float, dt: float) -> float:
        dt = max(dt, 1e-6)
        if not self._initialized:
            self._value = x
            self._prev = x
            self._initialized = True
            return x
        dx = (x - self._prev) / dt
        a_d = self._alpha(self.d_cutoff, dt)
        self._prev_dx = self._prev_dx + a_d * (dx - self._prev_dx)
        cutoff = self.min_cutoff + self.beta * abs(self._prev_dx)
        a = self._alpha(cutoff, dt)
        self._value = self._value + a * (x - self._value)
        self._prev = x
        return self._value

    def reset(self) -> None:
        self._prev = None
        self._prev_dx = 0.0
        self._value = 0.0
        self._initialized = False


class PredictiveTracker:
    """Predição de movimento do right stick (proxi do alvo) com filtro
    alfa-beta + aceleração.

    Sem visão computacional, a única fonte de "velocidade do alvo" é a
    velocidade com que o jogador está empurrando o stick. Em vez de derivar
    a velocidade bruta por tick (ruidosa), o tracker:

    - suaviza velocidade e aceleração com EMA (``vel_alpha``/``accel_alpha``),
    - só aplica lead quando a direção se mantém consistente por
      ``consistency`` frames (não prediz oscilação de jitter),
    - adianta o input com ``lead = v·T + ½·a·T²`` (T = lead_horizon_ms),
    - limita o lead por ``max_lead`` (anti-overshoot) e por ``min_speed``.
    """

    def __init__(self, vel_alpha: float = 0.15, accel_alpha: float = 0.06,
                 lead_horizon_ms: float = 40.0, min_speed: float = 200.0,
                 max_lead: float = 3000.0, consistency: int = 3,
                 direction_blend: float = 0.7) -> None:
        self.vel_alpha = vel_alpha
        self.accel_alpha = accel_alpha
        self.lead_horizon_ms = lead_horizon_ms
        self.min_speed = min_speed
        self.max_lead = max_lead
        self.consistency = max(1, int(consistency))
        self.direction_blend = direction_blend
        self._prev_x: Optional[float] = None
        self._prev_y: Optional[float] = None
        self._vx: float = 0.0
        self._vy: float = 0.0
        self._ax: float = 0.0
        self._ay: float = 0.0
        self._dir_x: int = 0
        self._dir_y: int = 0
        self._streak: int = 0

    def predict(self, rx: float, ry: float, dt_ms: float,
                follow_dir: Tuple[float, float] = (0.0, 0.0),
                confidence: float = 0.0) -> Tuple[float, float]:
        dt = max(float(dt_ms), 1.0)
        rx_f, ry_f = float(rx), float(ry)
        if self._prev_x is None:
            self._prev_x, self._prev_y = rx_f, ry_f
            return 0.0, 0.0

        # Input parado (jogador soltou o stick): NADA de lead. Antes o
        # follow_dir + a EMA de velocidade continuavam adiantando a mira na
        # última direção por centenas de ms — a câmera "continuava andando
        # pro lado que o jogador mexia" depois de soltar.
        if math.hypot(rx_f, ry_f) < 100.0:
            self._prev_x, self._prev_y = rx_f, ry_f
            self._streak = 0
            self._dir_x = self._dir_y = 0
            return 0.0, 0.0

        raw_vx = (rx_f - self._prev_x) / dt
        raw_vy = (ry_f - self._prev_y) / dt
        self._prev_x, self._prev_y = rx_f, ry_f

        raw_ax = (raw_vx - self._vx) / dt
        raw_ay = (raw_vy - self._vy) / dt
        self._ax += self.accel_alpha * (raw_ax - self._ax)
        self._ay += self.accel_alpha * (raw_ay - self._ay)
        self._vx += self.vel_alpha * (raw_vx - self._vx)
        self._vy += self.vel_alpha * (raw_vy - self._vy)

        speed = math.hypot(self._vx, self._vy)
        if speed < self.min_speed:
            self._streak = 0
            self._dir_x = self._dir_y = 0
            return 0.0, 0.0

        dx = 1 if self._vx >= 0 else -1
        dy = 1 if self._vy >= 0 else -1
        if dx == self._dir_x and dy == self._dir_y:
            self._streak += 1
        else:
            self._streak = 1
        self._dir_x, self._dir_y = dx, dy
        if self._streak < self.consistency:
            return 0.0, 0.0

        # Direção do lead: mistura a direção do alvo (follow_dir, vinda do
        # engagement estimator) com a direção da velocidade do stick. O
        # follow_dir (EMA estável) domina quando o jogador está travado no alvo.
        vdx = self._vx / speed
        vdy = self._vy / speed
        fx, fy = float(follow_dir[0]), float(follow_dir[1])
        fmag = math.hypot(fx, fy)
        if fmag > 0.1:
            b = self.direction_blend
            dir_x = (fx / fmag) * b + vdx * (1.0 - b)
            dir_y = (fy / fmag) * b + vdy * (1.0 - b)
            dnorm = math.hypot(dir_x, dir_y)
            if dnorm > 0.0:
                dir_x /= dnorm
                dir_y /= dnorm
        else:
            dir_x, dir_y = vdx, vdy

        # Magnitude: lead = v·T + ½·a·T², mais agressivo quando confiante.
        t = self.lead_horizon_ms
        accel = math.hypot(self._ax, self._ay)
        lead_mag = speed * t + 0.5 * accel * t * t
        lead_mag = min(lead_mag, self.max_lead)
        lead_mag *= 0.6 + 0.6 * confidence
        return dir_x * lead_mag, dir_y * lead_mag

    def reset(self) -> None:
        self._prev_x = self._prev_y = None
        self._vx = self._vy = 0.0
        self._ax = self._ay = 0.0
        self._dir_x = self._dir_y = 0
        self._streak = 0


class AdhesionBuffer:
    """Grude extra: persistência de direção + axis-lock perto do centro.

    - **Persistência**: quando o jogador solta o stick (``mag < min_mag``)
      enquanto engajado (mirando/atirando), o engine mantém a última direção
      por ``hold_ms`` decaindo (``decay``) — o retículo não "escapa" do alvo
      no micro-instante entre correções.
    - **Axis-lock**: com o input pequeno (retículo perto do alvo), atenua o
      eixo não-dominante por ``axis_lock`` para o retículo não derrapar em
      diagonal para fora do alvo (adere ao eixo de acompanhamento).
    """

    def __init__(self, hold_ms: float = 120.0, decay: float = 0.35,
                 axis_lock: float = 0.18, min_mag: float = 100.0) -> None:
        self.hold_ms = hold_ms
        self.decay = decay
        self.axis_lock = axis_lock
        self.min_mag = min_mag
        self._last_x: float = 0.0
        self._last_y: float = 0.0
        self._has_dir: bool = False
        self._holding: bool = False
        self._hold_start: float = 0.0

    def _axis_lock(self, rx: float, ry: float) -> Tuple[float, float]:
        if self.axis_lock <= 0:
            return rx, ry
        if abs(rx) >= abs(ry):
            return rx, ry * (1.0 - self.axis_lock)
        return rx * (1.0 - self.axis_lock), ry

    def apply(self, rx: float, ry: float, engaged: bool, dt_ms: float,
              now: Optional[float] = None) -> Tuple[float, float]:
        t = now if now is not None else time.monotonic()
        mag = math.hypot(rx, ry)
        if not engaged:
            self.reset()
            return rx, ry
        if mag >= self.min_mag:
            self._last_x, self._last_y = float(rx), float(ry)
            self._has_dir = True
            self._holding = False
            return self._axis_lock(rx, ry)
        # stick solto (mag < min_mag) mas engajado → persiste a última direção
        if not self._holding:
            self._holding = True
            self._hold_start = t
        elapsed_ms = (t - self._hold_start) * 1000.0
        if elapsed_ms >= self.hold_ms:
            self._last_x = self._last_y = 0.0
            self._has_dir = False
            self._holding = False
            return rx, ry
        if not self._has_dir:
            # nunca houve direção registrada — não há o que persistir (passthrough)
            return rx, ry
        remaining = 1.0 - elapsed_ms / max(self.hold_ms, 1.0)
        keep = self.decay * remaining
        # Cap no grude de persistência: segura no máximo ~600 unidades
        # (micro-glue pra não escapar do alvo), nunca 20% de um input
        # grande — senão a câmera "continua andando" depois de soltar.
        keep_mag = math.hypot(self._last_x, self._last_y)
        cap = 600.0
        scale = min(1.0, cap / keep_mag) if keep_mag > 0 else 0.0
        return self._last_x * keep * scale, self._last_y * keep * scale

    def reset(self) -> None:
        self._last_x = self._last_y = 0.0
        self._has_dir = False
        self._holding = False
        self._hold_start = 0.0
