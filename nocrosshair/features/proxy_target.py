#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Alvo proxy para AimLock — SEM visão computacional (estilo Cronus Zen).

Como não existe sensor de alvo, o ProxyTargetFeed deriva o alvo do INPUT
do jogador:

  1. Engaja quando o jogador está atirando e mexendo o stick (mira ativa).
  2. Assume que o inimigo está na direção do stick (onde o jogador está
     corrigindo) e em distância nominal (assumed_dist_cm).
  3. Aplica o headshot lock: o alvo fica fixo ACIMA do centro (head_pull_deg)
     — o engine de aimlock então puxa a mira pra cima enquanto você atira
     (efeito "headlock" do head.md, sem tela).
  4. Quando o jogador para de corrigir, a direção segurada decai suavemente
     pra frente — o pull de cabeça continua segurando o grude no alvo.

Quando não engajado, retorna None → pipeline faz passthrough.
"""

import math
from dataclasses import dataclass
from typing import Optional, Tuple

from nocrosshair.features.aimlock_proto import TargetFeed, TargetState


@dataclass
class ProxyTargetConfig:
    # Mag mínima do stick para considerar "mira ativa" (engaja no primeiro tick)
    input_min: float = 600.0
    # Ângulo fixo ACIMA do centro que o lock mantém (headshot pull, graus)
    head_pull_deg: float = 2.5
    # Erro de yaw a full stick na direção do input (graus)
    yaw_gain_deg: float = 2.0
    # Distância assumida do alvo (cm) — 3000 = 30m
    assumed_dist_cm: float = 3000.0
    # Solta o lock N ms depois de parar de atirar
    release_ms: float = 250.0
    # Solta o lock N ms depois de ZERAR o stick (ainda atirando). Sem isso o
    # lock congela a última direção e a câmera continua andando pro lado que
    # o jogador mexia — até soltar o gatilho.
    zero_release_ms: float = 80.0
    # Decaimento 1/s da direção segurada quando o stick para (0 = segura fixo)
    hold_decay: float = 8.0


class ProxyTargetFeed(TargetFeed):
    """Fonte de alvo por input — sem CV, sem memória, sem tela.

    Upgrade de alcance/movimento:
    - Pseudo-distância derivada do input: micro-correção = alvo perto
      (cone de cabeça maior, ângulo de pitch maior), varredura grande =
      alvo longe (pitch menor, mais lead). Sem sensor, o tamanho do
      input é o único proxy honesto de "onde estou no engajamento".
    - Pseudo-velocidade do alvo: EMA da direção × magnitude do input —
      quando o jogador está acompanhando um inimigo que se move, o stick
      fica empurrado numa direção consistente; isso vira velocidade de
      alvo pro prediction/lead do aimlock (bala demora mais pra chegar
      longe = mais lead).
    """

    def __init__(self, cfg: Optional[ProxyTargetConfig] = None):
        self.cfg = cfg if cfg is not None else ProxyTargetConfig()
        self._dir: Tuple[float, float] = (1.0, 0.0)
        self._engaged: bool = False
        self._since_shoot_ms: float = 0.0
        self._since_input_ms: float = 0.0
        self._mag_ema: float = 0.0
        self._vel: Tuple[float, float, float] = (0.0, 0.0, 0.0)
        self._vel_gain: float = 0.09  # unidades de stick → cm/s

    def set_input(self, rx: float, ry: float, is_shooting: bool,
                  delta_ms: float) -> None:
        if is_shooting:
            self._since_shoot_ms = 0.0
            mag = math.hypot(rx, ry)
            if mag >= self.cfg.input_min:
                self._since_input_ms = 0.0
                # EMA da magnitude → pseudo-distância (perto/longe). No
                # primeiro engajamento parte do nominal (assumed_dist_cm);
                # com input zerado, congela no último valor (o alvo não
                # "encolhe" porque o jogador parou de corrigir).
                k = 1.0 - math.exp(-3.0 * max(0.0, delta_ms) / 1000.0)
                if not self._engaged:
                    self._mag_ema = mag
                else:
                    self._mag_ema += (mag - self._mag_ema) * k
                self._dir = (rx / mag, ry / mag)
                self._engaged = True
                # Pseudo-velocidade do alvo: input consistente numa direção
                # = inimigo se movendo pra lá (tracking). EMA suave.
                k = 1.0 - math.exp(-6.0 * max(0.0, delta_ms) / 1000.0)
                target_vel = (self._dir[0] * mag * self._vel_gain,
                              self._dir[1] * mag * self._vel_gain,
                              0.0)
                self._vel = tuple(v + (t - v) * k for v, t in zip(self._vel, target_vel))
            else:
                # Atirando com o stick zerado: o lock NÃO pode congelar a
                # última direção pra sempre. Solta em zero_release_ms —
                # a câmera para de andar pro lado que o jogador mexia.
                self._since_input_ms += delta_ms
                if self._since_input_ms > self.cfg.zero_release_ms:
                    self._engaged = False
                self._vel = tuple(v * 0.9 for v in self._vel)
        else:
            self._since_shoot_ms += delta_ms
            self._vel = tuple(v * 0.9 for v in self._vel)
            if self._since_shoot_ms > self.cfg.release_ms:
                self._engaged = False
        if self.cfg.hold_decay > 0:
            k = 1.0 - math.exp(-self.cfg.hold_decay * max(0.0, delta_ms) / 1000.0)
            dx, dy = self._dir
            dx += (1.0 - dx) * k
            dy += (0.0 - dy) * k
            self._dir = (dx, dy)

    def _effective_distance(self) -> float:
        """Pseudo-distância do engajamento a partir do input sustentado.

        A distância nominal (assumed_dist_cm) é o ponto de referência
        (input ≈ 3000). Micro-correção sustenta perto (alvo colado),
        varredura sustenta longe — o pull de cabeça e o lead de bala
        acompanham.
        """
        base = max(1.0, self.cfg.assumed_dist_cm)
        m = self._mag_ema
        if m < 3000.0:
            return base * max(0.4, 0.4 + 0.6 * m / 3000.0)
        return base * min(2.5, 1.0 + 0.8 * (m - 3000.0) / 8000.0)

    def get_target(self, delta_ms: float) -> Optional[TargetState]:
        if not self._engaged:
            return None
        dx, dy = self._dir
        yaw = math.atan2(dy, dx)
        dist = self._effective_distance()
        # Ângulo de cabeça escala com a proximidade: perto = mais graus de
        # elevação (a cabeça ocupa mais da tela), longe = quase centro.
        pitch = math.radians(self.cfg.head_pull_deg * min(2.0, 3000.0 / dist))
        horiz = dist * math.cos(pitch)
        target = (horiz * math.cos(yaw),
                  horiz * math.sin(yaw),
                  dist * math.sin(pitch))
        return TargetState(eye=(0.0, 0.0, 0.0), target=target, vel=self._vel)

    @property
    def engaged(self) -> bool:
        return self._engaged
