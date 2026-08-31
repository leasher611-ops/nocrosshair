#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kernel Aim (BETA) — hardlock estilo kernel-mode para controle, SEM memória.

O "kernel aim" clássico lê as posições na memória do jogo e corrige a
câmera direto no alvo (hard lock): resposta alta, pouco erro, preso no
alvo enquanto atira. Sem leitura de memória, o equivalente honesto aqui
é derivar o alvo do INPUT do jogador (estilo Cronus Zen):

  - Quando atirando e corrigindo o stick, o lock assume o controle com
    força quase total (blend alto) e resposta rápida (snap alto) — a mira
    "gruda" como um kernel aim faria, sem tocar em memória.
  - Head lock no proxy (alvo sempre acima do centro) + lead preditivo
    (pseudo-velocidade do input → predição de bala).
  - Só atua em CONTROLE: no caminho KBM o sanitize desliga (kbm_mode).

Modo beta: config ``aa_kernel_aim_beta``, desligado por padrão.
"""

import math
from dataclasses import dataclass
from typing import Optional, Tuple

from nocrosshair.features.aimlock_proto import (
    AimLockProtoConfig, AimLockProtoEngine, TargetState,
)
from nocrosshair.features.proxy_target import ProxyTargetConfig, ProxyTargetFeed


@dataclass
class KernelAimConfig:
    enabled: bool = False          # BETA — desligado por padrão
    blend: float = 0.92            # quase total: o lock manda no stick
    snappiness: float = 0.55       # resposta alta (kernel-like)
    smoothing_rate: float = 12.0   # convergência rápida
    pull_max_rate_deg_s: float = 650.0   # correção rápida sem teleporte
    fov_degrees: float = 26.0      # janela de lock mais apertada
    head_pull_deg: float = 3.0     # head lock: alvo acima do centro
    min_input: float = 300.0       # engaja com micro-correção
    assumed_dist_cm: float = 3000.0
    release_ms: float = 200.0
    yaw_gain_deg: float = 2.0
    max_yaw_correction_deg: float = 45.0
    max_pitch_correction_deg: float = 28.0
    center_strength_mult: float = 2.2   # laser no centro do cone
    glue_drift_mult: float = 2.0        # agarra mais se o alvo escapar
    adhesion_cone_deg: float = 6.0      # amortece mais o input do jogador
    noise_degrees: float = 0.1          # estabilidade kernel-like
    # ── Engagement Confidence (novo) ──
    # Trackeia a consistência do input ao longo do tempo. Input consistente
    # = alta confiança = lock mais forte. Input errático = baixa confiança.
    confidence_enabled: bool = True
    confidence_rise_rate: float = 0.15    # quanto sobe por tick consistente
    confidence_fall_rate: float = 0.40    # quanto cai por tick errático
    confidence_blend_min: float = 0.50    # blend mínimo (baixa confiança)
    confidence_blend_max: float = 0.98    # blend máximo (alta confiança)
    # ── Kalman Smooth no proxy target (novo) ──
    # Suaviza a posição do alvo proxy com filtro Kalman pra reduzir jitter.
    kalman_process_noise: float = 500.0   # ruído do processo (mais alto = mais responsivo)
    kalman_measure_noise: float = 2000.0  # ruído da medição (mais alto = mais suave)


class KernelAimEngine:
    """Hardlock estilo kernel: proxy feed + aimlock com parâmetros agressivos.

    Upgrade v2:
    - Engagement Confidence: trackeia consistência do input. Input consistente
      = alta confiança = blend alto (lock forte). Input errático = baixa
      confiança = blend baixo (mais controle do jogador).
    - Kalman Smooth: suaviza a posição do alvo proxy com filtro Kalman,
      reduzindo jitter causado por input ruidoso.
    - Adaptive Blend: o blend não é mais fixo — varia entre confidence_blend_min
      e confidence_blend_max baseado na confiança atual.

    Uso por tick:
      engine.set_input(rx, ry, is_shooting, delta_ms)
      out = engine.compute(delta_ms)   # (rx, ry) ou None se não travado
    """

    def __init__(self, cfg: Optional[KernelAimConfig] = None):
        self.cfg = cfg if cfg is not None else KernelAimConfig()
        self.feed = ProxyTargetFeed(ProxyTargetConfig(
            input_min=self.cfg.min_input,
            head_pull_deg=self.cfg.head_pull_deg,
            yaw_gain_deg=self.cfg.yaw_gain_deg,
            assumed_dist_cm=self.cfg.assumed_dist_cm,
            release_ms=self.cfg.release_ms,
        ))
        self.lock = AimLockProtoEngine(AimLockProtoConfig(
            enabled=True,
            fov_degrees=self.cfg.fov_degrees,
            smoothing_rate=self.cfg.smoothing_rate,
            snappiness=self.cfg.snappiness,
            prediction_enabled=True,
            bullet_speed=30000.0,
            gravity_scale=0.12,
            humanize=True,
            noise_degrees=self.cfg.noise_degrees,
            degrees_full_stick=30.0,
            min_delta_ms=8.0,
            pull_max_rate_deg_s=self.cfg.pull_max_rate_deg_s,
            pull_ramp_up_ms=60.0,
            initial_downsight_mult=2.2,
            initial_downsight_ms=300.0,
            adhesion_cone_deg=self.cfg.adhesion_cone_deg,
            slow_strength=0.9,
            max_yaw_correction_deg=self.cfg.max_yaw_correction_deg,
            max_pitch_correction_deg=self.cfg.max_pitch_correction_deg,
            center_strength_mult=self.cfg.center_strength_mult,
            glue_drift_mult=self.cfg.glue_drift_mult,
            glue_drift_window_deg=15.0,
            lock_timeout_ms=350.0,
            target_bone="head",
            head_height_cm=30.0,
            max_tracking_distance_cm=50000.0,
        ))
        self._elapsed: float = 0.0
        self._state = None
        # ── Engagement Confidence ──
        self._confidence: float = 0.0
        self._prev_input_angle: float = 0.0
        self._input_consistent_frames: int = 0
        # ── Kalman Filter para proxy target ──
        self._kalman_x: float = 0.0
        self._kalman_y: float = 0.0
        self._kalman_z: float = 0.0
        self._kalman_vx: float = 0.0
        self._kalman_vy: float = 0.0
        self._kalman_vz: float = 0.0
        self._kalman_initialized: bool = False

    def _update_confidence(self, rx: float, ry: float, is_shooting: bool,
                           delta_ms: float) -> None:
        """Atualiza a confiança de engajamento baseado na consistência do input.

        Input consistente (ângulo similar frame a frame) = alta confiança.
        Input errático (ângulo mudando muito) = baixa confiança.
        """
        if not self.cfg.confidence_enabled:
            self._confidence = 1.0
            return

        mag = math.hypot(rx, ry)
        if not is_shooting or mag < self.cfg.min_input:
            self._confidence = max(0.0, self._confidence
                                   - self.cfg.confidence_fall_rate * delta_ms / 16.0)
            return

        angle = math.atan2(ry, rx)
        if self._prev_input_angle != 0.0:
            delta_angle = abs(angle - self._prev_input_angle)
            if delta_angle > math.pi:
                delta_angle = 2.0 * math.pi - delta_angle
            if delta_angle < 0.3:
                self._input_consistent_frames = min(
                    self._input_consistent_frames + 1, 60)
            else:
                self._input_consistent_frames = max(
                    self._input_consistent_frames - 2, 0)
        self._prev_input_angle = angle

        if self._input_consistent_frames >= 5:
            self._confidence = min(1.0, self._confidence
                                   + self.cfg.confidence_rise_rate * delta_ms / 16.0)
        else:
            self._confidence = max(0.0, self._confidence
                                   - self.cfg.confidence_fall_rate * delta_ms / 16.0)

    def _get_adaptive_blend(self) -> float:
        """Blend dinâmico baseado na confiança de engajamento."""
        if not self.cfg.confidence_enabled:
            return self.cfg.blend
        t = max(0.0, min(1.0, self._confidence))
        return self.cfg.confidence_blend_min + (
            self.cfg.confidence_blend_max - self.cfg.confidence_blend_min) * t

    def _kalman_update(self, x: float, y: float, z: float,
                       dt: float) -> Tuple[float, float, float]:
        """Filtro Kalman simplificado pra suavizar a posição do alvo."""
        if not self._kalman_initialized:
            self._kalman_x, self._kalman_y, self._kalman_z = x, y, z
            self._kalman_vx = self._kalman_vy = self._kalman_vz = 0.0
            self._kalman_initialized = True
            return x, y, z

        q = self.cfg.kalman_process_noise
        r = self.cfg.kalman_measure_noise

        pred_x = self._kalman_x + self._kalman_vx * dt
        pred_y = self._kalman_y + self._kalman_vy * dt
        pred_z = self._kalman_z + self._kalman_vz * dt

        err_x = x - pred_x
        err_y = y - pred_y
        err_z = z - pred_z

        gain = q / (q + r + 1e-6)
        self._kalman_x = pred_x + gain * err_x
        self._kalman_y = pred_y + gain * err_y
        self._kalman_z = pred_z + gain * err_z
        self._kalman_vx += gain * 0.5 * err_x / max(dt, 0.001)
        self._kalman_vy += gain * 0.5 * err_y / max(dt, 0.001)
        self._kalman_vz += gain * 0.5 * err_z / max(dt, 0.001)

        decay = 1.0 - gain * 0.3
        self._kalman_vx *= decay
        self._kalman_vy *= decay
        self._kalman_vz *= decay

        return self._kalman_x, self._kalman_y, self._kalman_z

    def set_input(self, rx: float, ry: float, is_shooting: bool,
                  delta_ms: float) -> None:
        self.feed.set_input(rx, ry, is_shooting, delta_ms)
        self._update_confidence(rx, ry, is_shooting, delta_ms)

    @property
    def engaged(self) -> bool:
        return self.lock.engaged

    @property
    def confidence(self) -> float:
        """Confiança de engajamento (0.0-1.0)."""
        return self._confidence

    @property
    def target_state(self):
        """Último estado de alvo do proxy (para a predição externa)."""
        return self._state

    def compute(self, delta_ms: float) -> Optional[Tuple[float, float]]:
        state = self.feed.get_target(delta_ms)
        if state is not None and self.cfg.confidence_enabled:
            dt = delta_ms / 1000.0
            sx, sy, sz = self._kalman_update(
                state.target[0], state.target[1], state.target[2], dt)
            state = TargetState(
                eye=state.eye,
                target=(sx, sy, sz),
                vel=state.vel,
            )
        self._state = state
        if state is None:
            self.lock.reset()
            return None
        self.lock.set_target(state.eye, state.target, state.vel)
        self._elapsed += delta_ms
        if self._elapsed < self.lock.cfg.min_delta_ms:
            if self.lock.engaged:
                return self.lock._last_out
            return None
        dt = self._elapsed
        self._elapsed = 0.0
        rx, ry = self.lock.compute(state.view_yaw, state.view_pitch, dt)
        if not self.lock.engaged:
            return None
        return rx, ry

    def reset(self) -> None:
        self.feed = ProxyTargetFeed(ProxyTargetConfig(
            input_min=self.cfg.min_input,
            head_pull_deg=self.cfg.head_pull_deg,
            yaw_gain_deg=self.cfg.yaw_gain_deg,
            assumed_dist_cm=self.cfg.assumed_dist_cm,
            release_ms=self.cfg.release_ms,
        ))
        self.lock.reset()
        self._elapsed = 0.0
        self._state = None
        self._confidence = 0.0
        self._prev_input_angle = 0.0
        self._input_consistent_frames = 0
        self._kalman_initialized = False
