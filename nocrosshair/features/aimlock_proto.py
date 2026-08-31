#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Protótipo de AimLock para controller — matemática portável do aimlock
do Fortnite Mobile / aimbot UE (ver RESEARCH_AIMBOT_MATH.md), sem leitura
de memória: os blocos de RPM/hook são substituídos por uma fonte hipotética
de alvo (olho + posição/velocidade do alvo, em centímetros).

Pipeline por tick:
  1. lead: t = dist / vel_bala; alvo_previsto = alvo + vel_alvo·t + ½·g·t²
  2. ângulos: yaw = atan2(dy, dx), pitch = atan2(dz, √(dx²+dy²)); yaw em [−180,180],
     pitch > 0 = alvo acima da view
  3. erro angular = alvo_previsto − view (wrap no yaw)
  4. gate de FOV com histerese (saída = fov × 1.2)
  5. smoothing de primeira ordem com delta-time: k = 1 − exp(−rate·dt) + snappiness
  6. humanização: ruído ±noise_degrees; taxa de atualização limitada (min_delta_ms)
  7. saída: erro angular → right stick ±32767 (rx > 0 = direita; ry < 0 = cima)

Tudo em graus (não pixels) para independer de resolução/FOV de câmera.
"""

import math
import random
from dataclasses import dataclass, field
from typing import Tuple, Optional, Sequence


@dataclass
class AimLockProtoConfig:
    enabled: bool = True
    fov_degrees: float = 30.0
    fov_hysteresis: float = 1.2
    smoothing_rate: float = 10.0
    snappiness: float = 0.5
    prediction_enabled: bool = True
    bullet_speed: float = 30000.0
    gravity_scale: float = 0.12
    world_gravity: float = 980.0
    humanize: bool = True
    noise_degrees: float = 0.25
    degrees_full_stick: float = 30.0
    min_delta_ms: float = 8.0
    seed: Optional[int] = None

    # ---- Super AimLock (inspirado no FortAimAssist2D, porém mais forte) ----
    # PullMaxRate: cap de rotação de correção (graus/s)
    pull_max_rate_deg_s: float = 420.0
    # RampUp: tempo para sair de 0 e atingir a força nominal após adquirir
    pull_ramp_up_ms: float = 80.0
    # InitialDownsight: multiplicador de força nos primeiros ms do engajamento
    initial_downsight_mult: float = 2.5
    initial_downsight_ms: float = 350.0
    # AdhesionCone + Slow: janela angular onde o input do jogador é amortecido
    adhesion_cone_deg: float = 8.0
    slow_strength: float = 0.85
    # SoftAimMagnet: clamp de correção por eixo (graus)
    max_yaw_correction_deg: float = 40.0
    max_pitch_correction_deg: float = 25.0
    # AngularStrengthMultiplier invertido: força EXTRA perto do centro
    # (o FN rampa a força na borda; aqui a aderência é no centro = laser)
    center_strength_mult: float = 1.8
    # Glue drift (DistanceAheadToRampUp do FortAimAssist2D): quando o alvo
    # escapa do cone de adesão, a força RAMPA com a distância — quanto mais
    # o inimigo anda pra fora, mais o lock agarra. Mantém o grude literal
    # com o inimigo se movimentando.
    glue_drift_mult: float = 1.6
    glue_drift_window_deg: float = 15.0

    # ---- Auto-Aim Lock / Target Bone (ver head.md) ----
    # Auto-Aim Lock: trava sozinho no alvo que entrar na janela e segura com
    # histerese; libera quando o alvo para de atualizar (timeout).
    lock_timeout_ms: float = 500.0
    # Target Bone — osso a mirar: "head" (Headshot Lock), "body" (peito)
    # ou "auto" (corpo durante a aquisição, cabeça quando travado).
    target_bone: str = "head"
    # Altura do osso cabeça acima do centro do corpo do alvo (cm).
    head_height_cm: float = 30.0
    # Aim tracking 500M: alcance máximo de rastreio (cm; 50000 = 500m).
    # Fora do alcance o lock não engaja; travado, só solta com histerese.
    max_tracking_distance_cm: float = 50000.0

    # ---- PredictiveTracker / AimSmoother (modelos Zen) ----
    # Kalman-style smoothing da velocidade do alvo (0.0 = desligado, usa a
    # velocidade bruta do feed; 0.3 = típico dos modelos de referência).
    # Estabiliza a predição contra ruído do sensor sem custo de latência.
    kalman_smoothing: float = 0.0
    # Smoothing adaptativo por velocidade do alvo (0.0 = desligado): quando o
    # alvo anda rápido, o rate de smoothing sobe (menos suavização = resposta
    # mais rápida), igual ao AimSmoother que reduz smoothing acima de ~500px/s.
    velocity_adaptive_boost: float = 0.0
    # Velocidade do alvo (cm/s) onde o boost adaptativo satura.
    velocity_adaptive_saturate: float = 5000.0


Vec3 = Sequence[float]


@dataclass
class TargetState:
    eye: Vec3
    target: Vec3
    vel: Vec3
    view_yaw: float = 0.0
    view_pitch: float = 0.0


class TargetFeed:
    """Fonte de alvo — sem visão computacional. Substitui a leitura de
    memória por qualquer sensor que forneça posição do alvo em cm."""

    def get_target(self, delta_ms: float) -> Optional[TargetState]:
        raise NotImplementedError


class NullTargetFeed(TargetFeed):
    """Sem alvo: o aimlock fica inativo (passthrough)."""

    def get_target(self, delta_ms: float) -> Optional[TargetState]:
        return None


class SimulatedTargetFeed(TargetFeed):
    """Alvo simulado orbitando a view — fonte hipotética para testes e demo.

    O alvo gira ao redor do ponto de mira com velocidade angular
    ``yaw_speed_deg_s``, a ``distance_cm``, com opção de velocidade de strafe
    extra (usada pelo prediction/lead). Fonte 100% sem visão computacional.
    """

    def __init__(self, yaw_speed_deg_s: float = 20.0, pitch_offset_deg: float = 0.0,
                 distance_cm: float = 5000.0, height_cm: float = 0.0,
                 strafe_vel: Vec3 = (0.0, 0.0, 0.0),
                 start_yaw_deg: float = 0.0):
        self.yaw_speed_deg_s = yaw_speed_deg_s
        self.pitch_offset_deg = pitch_offset_deg
        self.distance_cm = distance_cm
        self.height_cm = height_cm
        self.strafe_vel = tuple(float(v) for v in strafe_vel)
        self._yaw_deg = start_yaw_deg

    def _orbital_vel(self) -> Tuple[float, float, float]:
        omega = math.radians(self.yaw_speed_deg_s)
        cy = math.cos(math.radians(self.pitch_offset_deg))
        yaw = math.radians(self._yaw_deg)
        return (-self.distance_cm * cy * math.sin(yaw) * omega,
                self.distance_cm * cy * math.cos(yaw) * omega,
                0.0)

    def get_target(self, delta_ms: float) -> Optional[TargetState]:
        self._yaw_deg += self.yaw_speed_deg_s * (delta_ms / 1000.0)
        cy = math.cos(math.radians(self.pitch_offset_deg))
        yaw = math.radians(self._yaw_deg)
        target = (self.distance_cm * cy * math.cos(yaw),
                  self.distance_cm * cy * math.sin(yaw),
                  self.distance_cm * math.sin(math.radians(self.pitch_offset_deg)) + self.height_cm)
        vel = (self._orbital_vel()[0] + self.strafe_vel[0],
               self._orbital_vel()[1] + self.strafe_vel[1],
               self.strafe_vel[2])
        return TargetState(eye=(0.0, 0.0, 0.0), target=target, vel=vel)


class AimLockProtoEngine:

    def __init__(self, cfg: Optional[AimLockProtoConfig] = None):
        self.cfg = cfg if cfg is not None else AimLockProtoConfig()
        self._eye: Vec3 = (0.0, 0.0, 0.0)
        self._target: Vec3 = (0.0, 0.0, 0.0)
        self._vel: Vec3 = (0.0, 0.0, 0.0)
        self._locked: bool = False
        self._sm_yaw: float = 0.0
        self._sm_pitch: float = 0.0
        self._last_out: Tuple[float, float] = (0.0, 0.0)
        self._rng = random.Random(self.cfg.seed)
        self._lock_t_ms: Optional[float] = None
        self._prev_out_yaw: float = 0.0
        self._prev_out_pitch: float = 0.0
        self._since_update_ms: float = 0.0
        self._kal_v: Vec3 = (0.0, 0.0, 0.0)

    @property
    def engaged(self) -> bool:
        return self._locked

    @property
    def lock_age_ms(self) -> Optional[float]:
        """Tempo desde que o alvo foi adquirido (None = não engajado)."""
        return self._lock_t_ms

    def set_target(self, eye: Vec3, target: Vec3,
                   target_vel: Vec3 = (0.0, 0.0, 0.0)) -> None:
        self._eye = tuple(float(v) for v in eye)
        self._target = tuple(float(v) for v in target)
        self._vel = tuple(float(v) for v in target_vel)
        self._since_update_ms = 0.0
        if self.cfg.kalman_smoothing <= 0:
            return
        g = self.cfg.kalman_smoothing
        self._kal_v = tuple(v + (self._vel[i] - v) * g for i, v in enumerate(self._kal_v))

    def reset(self) -> None:
        self._locked = False
        self._sm_yaw = 0.0
        self._sm_pitch = 0.0
        self._last_out = (0.0, 0.0)
        self._rng = random.Random(self.cfg.seed)
        self._lock_t_ms = None
        self._prev_out_yaw = 0.0
        self._prev_out_pitch = 0.0
        self._since_update_ms = 0.0
        self._kal_v = (0.0, 0.0, 0.0)

    @property
    def velocity_cm_s(self) -> float:
        """Magnitude da velocidade do alvo (kalman suavizada se ativo) —
        alimenta o smoothing adaptativo."""
        v = self._kal_v if self.cfg.kalman_smoothing > 0 else self._vel
        return math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)

    @staticmethod
    def wrap180(deg: float) -> float:
        deg = math.fmod(deg + 180.0, 360.0)
        if deg < 0:
            deg += 360.0
        return deg - 180.0

    def aim_point(self) -> Vec3:
        ex, ey, ez = self._eye
        tx, ty, tz = self._target
        vx, vy, vz = self._vel
        if self.cfg.kalman_smoothing > 0:
            vx, vy, vz = self._kal_v
        dx, dy, dz = tx - ex, ty - ey, tz - ez
        dist = math.sqrt(dx * dx + dy * dy + dz * dz)
        if not self.cfg.prediction_enabled or dist <= 0 or self.cfg.bullet_speed <= 0:
            px, py, pz = tx, ty, tz
        else:
            t = dist / self.cfg.bullet_speed
            g_eff = self.cfg.world_gravity * self.cfg.gravity_scale
            px, py, pz = tx + vx * t, ty + vy * t, tz + vz * t + 0.5 * g_eff * t * t
        bone = self.cfg.target_bone
        if bone == "head" or (bone == "auto" and self._locked):
            pz += self.cfg.head_height_cm
        return (px, py, pz)

    @property
    def dist_cm(self) -> float:
        """Distância atual olho→alvo (cm) — alimenta o gate de 500M."""
        ex, ey, ez = self._eye
        tx, ty, tz = self._target
        return math.sqrt((tx - ex) ** 2 + (ty - ey) ** 2 + (tz - ez) ** 2)

    def target_angles(self) -> Tuple[float, float]:
        ax, ay, az = self.aim_point()
        ex, ey, ez = self._eye
        dx, dy, dz = ax - ex, ay - ey, az - ez
        horiz = math.sqrt(dx * dx + dy * dy)
        yaw = math.degrees(math.atan2(dy, dx))
        pitch = math.degrees(math.atan2(dz, horiz)) if horiz > 0 else 0.0
        return self.wrap180(yaw), pitch

    def slow_factor(self, view_yaw: float, view_pitch: float) -> float:
        """Aderência estilo FortAimAssist2D 'Slow': 0.0 fora do cone de
        adesão, subindo até ``slow_strength`` no centro do alvo. Aplicado
        pelo pipeline como amortecimento do INPUT do jogador (efeito sticky).
        """
        if not self._locked or self.cfg.slow_strength <= 0:
            return 0.0
        aim_yaw, aim_pitch = self.target_angles()
        err_yaw = self.wrap180(aim_yaw - view_yaw)
        err_pitch = aim_pitch - view_pitch
        d = math.sqrt(err_yaw * err_yaw + err_pitch * err_pitch)
        cone = max(self.cfg.adhesion_cone_deg, 0.0001)
        if d >= cone:
            return 0.0
        return self.cfg.slow_strength * (1.0 - d / cone)

    def _strength(self, ang_dist: float, delta_ms: float) -> float:
        """Multiplicador de força combinado: ramp-up, snap inicial (tipo
        InitialDownsight), força extra no centro (laser) e glue drift —
        quando o alvo escapa do cone, a força rampa com a distância
        (DistanceAheadToRampUp do FortAimAssist2D), mantendo o grude
        literal com o inimigo se movimentando."""
        mult = 1.0
        if self._lock_t_ms is not None:
            age = self._lock_t_ms
            if self.cfg.pull_ramp_up_ms > 0 and age < self.cfg.pull_ramp_up_ms:
                mult *= max(0.0, age / self.cfg.pull_ramp_up_ms)
            if (self.cfg.initial_downsight_mult > 1.0
                    and age < self.cfg.initial_downsight_ms):
                remaining = 1.0 - age / max(self.cfg.initial_downsight_ms, 0.0001)
                mult *= 1.0 + (self.cfg.initial_downsight_mult - 1.0) * remaining
        angular = 1.0
        cone = max(self.cfg.adhesion_cone_deg, 0.0001)
        if self.cfg.center_strength_mult > 1.0 and ang_dist < cone:
            frac = 1.0 - ang_dist / cone
            angular = max(angular, 1.0 + (self.cfg.center_strength_mult - 1.0) * frac)
        if self.cfg.glue_drift_mult > 1.0 and ang_dist >= cone:
            window = max(self.cfg.glue_drift_window_deg, 0.0001)
            frac = min(1.0, (ang_dist - cone) / window)
            angular = max(angular, 1.0 + (self.cfg.glue_drift_mult - 1.0) * frac)
        return mult * angular

    def compute(self, view_yaw: float, view_pitch: float,
                delta_ms: float) -> Tuple[float, float]:
        if not self.cfg.enabled:
            self._locked = False
            self._sm_yaw = 0.0
            self._sm_pitch = 0.0
            return (0.0, 0.0)

        if delta_ms < self.cfg.min_delta_ms:
            return self._last_out

        self._since_update_ms += delta_ms
        stale = (self.cfg.lock_timeout_ms > 0
                 and self._since_update_ms > self.cfg.lock_timeout_ms)

        aim_yaw, aim_pitch = self.target_angles()
        err_yaw = self.wrap180(aim_yaw - view_yaw)
        err_pitch = aim_pitch - view_pitch
        ang_dist = math.sqrt(err_yaw * err_yaw + err_pitch * err_pitch)

        # Gate de alcance (Aim tracking 500M): fora do alcance não engaja;
        # travado, só solta com histerese (1.15x) ou se o alvo estagnou.
        d = self.dist_cm
        max_d = self.cfg.max_tracking_distance_cm
        out_of_range = max_d > 0 and d > max_d * (1.15 if self._locked else 1.0)

        if self._locked:
            self._locked = (ang_dist <= self.cfg.fov_degrees * self.cfg.fov_hysteresis
                            and not out_of_range and not stale)
        else:
            self._locked = ang_dist <= self.cfg.fov_degrees and not out_of_range

        if not self._locked:
            self._sm_yaw = 0.0
            self._sm_pitch = 0.0
            self._last_out = (0.0, 0.0)
            self._lock_t_ms = None
            return (0.0, 0.0)

        if self._lock_t_ms is None:
            self._lock_t_ms = 0.0
        else:
            self._lock_t_ms += delta_ms

        # SoftAimMagnet: clamp de correção por eixo
        if self.cfg.max_yaw_correction_deg > 0:
            err_yaw = max(-self.cfg.max_yaw_correction_deg,
                          min(self.cfg.max_yaw_correction_deg, err_yaw))
        if self.cfg.max_pitch_correction_deg > 0:
            err_pitch = max(-self.cfg.max_pitch_correction_deg,
                            min(self.cfg.max_pitch_correction_deg, err_pitch))

        if self.cfg.humanize and self.cfg.noise_degrees > 0:
            err_yaw += self._rng.uniform(-self.cfg.noise_degrees, self.cfg.noise_degrees)
            err_pitch += self._rng.uniform(-self.cfg.noise_degrees, self.cfg.noise_degrees)

        dt = max(delta_ms / 1000.0, 0.0)
        strength = self._strength(ang_dist, delta_ms)
        adaptive = 1.0
        if self.cfg.velocity_adaptive_boost > 0:
            sat = max(self.cfg.velocity_adaptive_saturate, 0.0001)
            adaptive = 1.0 + self.cfg.velocity_adaptive_boost * min(1.0, self.velocity_cm_s / sat)
        k = 1.0 - math.exp(-self.cfg.smoothing_rate * dt * strength * adaptive)
        self._sm_yaw += (err_yaw - self._sm_yaw) * k
        self._sm_pitch += (err_pitch - self._sm_pitch) * k

        snap = max(0.0, min(1.0, self.cfg.snappiness))
        out_yaw = self._sm_yaw * (1.0 - snap) + err_yaw * snap
        out_pitch = self._sm_pitch * (1.0 - snap) + err_pitch * snap

        # PullMaxRate: cap de rotação de correção por tick
        if self.cfg.pull_max_rate_deg_s > 0:
            max_delta = self.cfg.pull_max_rate_deg_s * dt
            d_yaw = self.wrap180(out_yaw - self._prev_out_yaw)
            d_pitch = out_pitch - self._prev_out_pitch
            if abs(d_yaw) > max_delta:
                out_yaw = self._prev_out_yaw + math.copysign(max_delta, d_yaw)
            if abs(d_pitch) > max_delta:
                out_pitch = self._prev_out_pitch + math.copysign(max_delta, d_pitch)

        self._prev_out_yaw, self._prev_out_pitch = out_yaw, out_pitch

        scale = 32767.0 / max(self.cfg.degrees_full_stick, 0.0001)
        rx = max(-32767.0, min(32767.0, out_yaw * scale))
        ry = max(-32767.0, min(32767.0, -out_pitch * scale))
        self._last_out = (rx, ry)
        return rx, ry


class AimLockTestbed:

    def __init__(self, cfg: Optional[AimLockProtoConfig] = None):
        self.cfg = cfg if cfg is not None else AimLockProtoConfig()
        self.engine = AimLockProtoEngine(self.cfg)
        self.eye = (0.0, 0.0, 0.0)

    def aim_at(self, yaw_off: float, pitch_off: float, dist: float,
               vel: Vec3 = (0.0, 0.0, 0.0)) -> Vec3:
        cy = math.cos(math.radians(pitch_off))
        target = (dist * cy * math.cos(math.radians(yaw_off)),
                  dist * cy * math.sin(math.radians(yaw_off)),
                  dist * math.sin(math.radians(pitch_off)))
        self.engine.set_target(self.eye, target, vel)
        return target

    def compute(self, view_yaw: float = 0.0, view_pitch: float = 0.0,
                delta_ms: float = 16.0) -> Tuple[float, float]:
        return self.engine.compute(view_yaw, view_pitch, delta_ms)
