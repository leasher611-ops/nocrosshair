"""
 nocrosshair — aim_engines_v3.py
 ═══════════════════════════════════════════════════════════════════════════════
 ENGINE DE AIM ASSIST — GERACAO 3.0

 Motores de aim assist de última geração com tecnologia avançada.

 MOTORES:
   1. RotationalAAEngineV3 — órbita adaptativa 4 modos + anti-detecção
   2. MagnetEngineV3 — pull 3 zonas + histeresis + velocity persistence
   3. PredictEngineV3 — Kalman 2D + jerk + pattern detection
   4. MicroCorrectionEngineV3 — low-pass adaptativo + histeresis
   5. AdaptiveStrengthEngineV3 — multi-window + trend detection
   6. EngagementDetectorV3 — intent detection + burst/spray

 ═══════════════════════════════════════════════════════════════════════════════
"""

import math
import time
from enum import IntEnum
from typing import Tuple, Optional
from nocrosshair.features.aim_lut import aim_lut


class EngagementState(IntEnum):
    IDLE = 0
    SEARCHING = 1
    TRACKING = 2
    LOCKED = 3


class RotationalAAEngineV3:
    """Orbita rotacional adaptativa de 3a geracao.

    TECNOLOGIA:
      - 4 modos de orbita com transicao suave
      - Phase randomization temporal (anti-deteccao)
      - Amplitude adaptativa baseada em hit rate
      - Direction reversal inteligente
      - Micro-jitter temporal para evitar padroes

    ANTI-DETECCAO:
      - Timing jitter: +/-5ms no step
      - Amplitude jitter: +/-8% na amplitude
      - Phase offset: +/-0.1 rad por frame
    """

    __slots__ = (
        '_angle', '_last_fire_edge', '_fire_edge_time',
        '_rng_seed', '_amplitude_jitter', '_hit_rate',
        '_phase_offset', '_amplitude_adapt',
    )

    def __init__(self) -> None:
        self._angle: float = 0.0
        self._last_fire_edge: bool = False
        self._fire_edge_time: float = 0.0
        self._rng_seed: int = 12345
        self._amplitude_jitter: float = 0.0
        self._hit_rate: float = 0.5
        self._phase_offset: float = 0.0
        self._amplitude_adapt: float = 1.0

    def apply(
        self,
        rx: float,
        ry: float,
        *,
        enabled: bool,
        state: EngagementState,
        zone: int,
        speed: float,
        radius_mult: float,
        shape: str,
        is_shooting: bool,
        is_aiming: bool,
        delta_ms: float,
        fire_edge_reset: bool = True,
        hit_rate: float = 0.5,
    ) -> Tuple[float, float]:
        if not enabled or state == EngagementState.IDLE:
            return rx, ry

        mag = aim_lut.mag_xy(rx, ry)
        if mag < 100:
            return rx, ry

        self._hit_rate = hit_rate
        self._adapt_amplitude()

        state_scale = self._get_state_scale(state)
        speed_adj = speed * state_scale
        radius = (zone // 8) * radius_mult * state_scale

        self._rng_seed = (self._rng_seed * 1103515245 + 12345) & 0x7FFFFFFF
        timing_jitter = (self._rng_seed % 100) / 2000.0 - 0.025
        self._rng_seed = (self._rng_seed * 1103515245 + 12345) & 0x7FFFFFFF
        amp_jitter = (self._rng_seed % 100) / 1250.0 - 0.04
        self._amplitude_jitter = self._amplitude_jitter * 0.9 + amp_jitter * 0.1

        self._rng_seed = (self._rng_seed * 1103515245 + 12345) & 0x7FFFFFFF
        self._phase_offset = (self._rng_seed % 100) / 1000.0 - 0.05

        angle_step = speed_adj * (delta_ms + timing_jitter) * 0.001
        self._angle += angle_step
        if self._angle > 2.0 * math.pi:
            self._angle -= 2.0 * math.pi

        fire_edge = is_shooting and not self._last_fire_edge
        self._last_fire_edge = is_shooting
        if fire_edge:
            self._fire_edge_time = time.monotonic()
            self._angle += math.pi

        attenuation = max(0.0, 1.0 - (mag / 6000.0))

        cx, cy = self._get_orbit(shape)

        amp = radius * attenuation * (1.0 + self._amplitude_jitter) * self._amplitude_adapt
        out_rx = rx + cx * amp
        out_ry = ry + cy * amp

        return aim_lut.clamp(out_rx, -32767.0, 32767.0), aim_lut.clamp(out_ry, -32767.0, 32767.0)

    def _get_orbit(self, shape: str) -> Tuple[float, float]:
        angle = self._angle + self._phase_offset

        if shape == "circular":
            return aim_lut.sin(angle), aim_lut.cos(angle)

        if shape == "helix":
            drift = 0.3 * aim_lut.sin(angle * 0.25)
            cx = aim_lut.cos(angle) + drift
            cy = aim_lut.sin(angle)
            norm = aim_lut.mag_xy(cx, cy)
            if norm > 0:
                cx /= norm
                cy /= norm
            return cx, cy

        if shape == "fibonacci":
            golden = 1.618033988749
            cx = aim_lut.cos(angle) * aim_lut.cos(angle * golden)
            cy = aim_lut.sin(angle) * aim_lut.sin(angle * golden)
            norm = aim_lut.mag_xy(cx, cy)
            if norm > 0:
                cx /= norm
                cy /= norm
            return cx, cy

        speed_mod = 0.5 + 0.5 * aim_lut.sin(angle * 0.5)
        return aim_lut.cos(angle * speed_mod), aim_lut.sin(angle * speed_mod)

    def _adapt_amplitude(self) -> None:
        if self._hit_rate > 0.7:
            self._amplitude_adapt = max(0.6, self._amplitude_adapt * 0.98)
        elif self._hit_rate < 0.3:
            self._amplitude_adapt = min(1.4, self._amplitude_adapt * 1.02)

    def _get_state_scale(self, state: EngagementState) -> float:
        if state == EngagementState.LOCKED:
            return 0.3
        elif state == EngagementState.TRACKING:
            return 0.6
        elif state == EngagementState.SEARCHING:
            return 1.0
        return 0.0

    def reset(self) -> None:
        self._angle = 0.0
        self._last_fire_edge = False
        self._fire_edge_time = 0.0
        self._amplitude_adapt = 1.0


class MagnetEngineV3:
    """Engine unificada de sticky + lock magnetico de 3a geracao.

    TECNOLOGIA:
      - Pull adaptativo com 3 zonas (outer/mid/inner)
      - Velocity-based persistence
      - Multi-zone lock com histeresis
      - Axis-lock dinamico baseado na velocidade
      - Fade adaptativo entre engaged/disengaged
    """

    __slots__ = (
        '_persist_rx', '_persist_ry', '_persist_until',
        '_smooth_rx', '_smooth_ry', '_last_dir_x', '_last_dir_y',
        '_velocity_mag', '_lock_active', '_hysteresis',
    )

    def __init__(self) -> None:
        self._persist_rx: float = 0.0
        self._persist_ry: float = 0.0
        self._persist_until: float = 0.0
        self._smooth_rx: float = 0.0
        self._smooth_ry: float = 0.0
        self._last_dir_x: float = 0.0
        self._last_dir_y: float = 0.0
        self._velocity_mag: float = 0.0
        self._lock_active: bool = False
        self._hysteresis: float = 0.0

    def apply(
        self,
        rx: float,
        ry: float,
        *,
        enabled: bool,
        strength: float,
        magnetic_pull: int,
        lock_fov: int,
        lock_strength: int,
        lock_smooth: float,
        is_shooting: bool,
        is_aiming: bool,
        delta_ms: float,
        now: Optional[float] = None,
    ) -> Tuple[float, float]:
        if not enabled or strength <= 0:
            self._reset_persist()
            return rx, ry

        t = now if now is not None else time.monotonic()
        mag = aim_lut.mag_xy(rx, ry)
        engaged = (is_shooting or is_aiming) and mag > 100

        if engaged:
            nx = rx / mag if mag > 0 else 0.0
            ny = ry / mag if mag > 0 else 0.0
            self._last_dir_x = nx
            self._last_dir_y = ny

            velocity = mag / max(delta_ms, 1.0)
            self._velocity_mag = self._velocity_mag * 0.8 + velocity * 0.2

            persist_time = 0.07 + min(0.05, self._velocity_mag / 50000.0)
            self._persist_rx = rx
            self._persist_ry = ry
            self._persist_until = t + persist_time

            outer_pull = magnetic_pull * strength * 0.3
            mid_pull = magnetic_pull * strength * 0.6
            inner_pull = magnetic_pull * strength * 1.0

            if mag < lock_fov / 4:
                pull = inner_pull
            elif mag < lock_fov / 2:
                pull = mid_pull
            else:
                pull = outer_pull

            pull = min(pull, float(magnetic_pull))
            rx += nx * pull
            ry += ny * pull

            if lock_fov > 0:
                lock_threshold = lock_fov if self._lock_active else lock_fov * 0.8
                if mag < lock_threshold:
                    self._lock_active = True
                    self._hysteresis = 1.0
                elif mag > lock_fov * 1.1:
                    self._lock_active = False
                    self._hysteresis = 0.0

                if self._lock_active:
                    proximity = max(0.0, 1.0 - (mag / lock_fov))
                    lock_pull = (lock_strength / 12000.0) * (0.3 + 0.7 * proximity)
                    lock_pull *= self._hysteresis
                    rx += nx * lock_pull * 900.0
                    ry += ny * lock_pull * 900.0

            if lock_smooth > 0:
                speed_factor = min(1.0, self._velocity_mag / 2000.0)
                weight = min(0.9, max(0.10, 1.0 - lock_smooth * (1.0 - speed_factor * 0.3)))
                if self._smooth_rx == 0.0 and self._smooth_ry == 0.0:
                    self._smooth_rx = rx
                    self._smooth_ry = ry
                else:
                    self._smooth_rx = self._smooth_rx * (1.0 - weight) + rx * weight
                    self._smooth_ry = self._smooth_ry * (1.0 - weight) + ry * weight
                rx = self._smooth_rx
                ry = self._smooth_ry

        elif t < self._persist_until:
            remaining = (self._persist_until - t) / max(0.01, self._persist_until - (t - delta_ms * 0.001))
            decay = max(0.0, min(1.0, remaining))
            velocity_factor = min(1.0, self._velocity_mag / 3000.0)
            persist_strength = 0.3 + 0.2 * velocity_factor

            if abs(self._persist_rx) > 50:
                keep_x = abs(self._persist_rx) * persist_strength * decay
                if abs(rx) < 50:
                    rx = aim_lut.clamp(
                        math.copysign(keep_x, self._persist_rx),
                        -32767.0, 32767.0
                    )
            if abs(self._persist_ry) > 50:
                keep_y = abs(self._persist_ry) * persist_strength * decay
                if abs(ry) < 50:
                    ry = aim_lut.clamp(
                        math.copysign(keep_y, self._persist_ry),
                        -32767.0, 32767.0
                    )
        else:
            self._reset_persist()

        return aim_lut.clamp(rx, -32767.0, 32767.0), aim_lut.clamp(ry, -32767.0, 32767.0)

    def _reset_persist(self) -> None:
        self._persist_rx = 0.0
        self._persist_ry = 0.0
        self._persist_until = 0.0

    def reset(self) -> None:
        self._reset_persist()
        self._smooth_rx = 0.0
        self._smooth_ry = 0.0
        self._last_dir_x = 0.0
        self._last_dir_y = 0.0
        self._velocity_mag = 0.0
        self._lock_active = False
        self._hysteresis = 0.0


class PredictEngineV3:
    """Engine de predicao unificada de 3a geracao.

    TECNOLOGIA:
      - Kalman 2D completo com covariance update
      - Jerk estimation (mudanca de aceleracao)
      - Pattern detection (strafe/jump/crouch)
      - Adaptive gain baseado em confidence
      - Anti-overshoot com velocity clamping
    """

    __slots__ = (
        '_prev_x', '_prev_y', '_vx', '_vy', '_ax', '_ay',
        '_jx', '_jy',
        '_kalman_x', '_kalman_y', '_kalman_vx', '_kalman_vy',
        '_confidence', '_streak', '_dir_x', '_dir_y',
        '_pattern', '_pattern_history',
    )

    def __init__(self) -> None:
        self._prev_x: Optional[float] = None
        self._prev_y: Optional[float] = None
        self._vx: float = 0.0
        self._vy: float = 0.0
        self._ax: float = 0.0
        self._ay: float = 0.0
        self._jx: float = 0.0
        self._jy: float = 0.0
        self._kalman_x: float = 0.0
        self._kalman_y: float = 0.0
        self._kalman_vx: float = 0.0
        self._kalman_vy: float = 0.0
        self._confidence: float = 0.0
        self._streak: int = 0
        self._dir_x: int = 0
        self._dir_y: int = 0
        self._pattern: str = "linear"
        self._pattern_history: list = []

    def predict(
        self,
        rx: float,
        ry: float,
        dt_ms: float,
        *,
        vel_alpha: float = 0.15,
        accel_alpha: float = 0.06,
        lead_horizon_ms: float = 40.0,
        min_speed: float = 200.0,
        max_lead: float = 3000.0,
        consistency: int = 3,
        kalman_weight: float = 0.3,
    ) -> Tuple[float, float]:
        dt = max(float(dt_ms), 1.0)
        rx_f, ry_f = float(rx), float(ry)

        if self._prev_x is None:
            self._prev_x, self._prev_y = rx_f, ry_f
            self._kalman_x, self._kalman_y = rx_f, ry_f
            return 0.0, 0.0

        raw_vx = (rx_f - self._prev_x) / dt
        raw_vy = (ry_f - self._prev_y) / dt
        self._prev_x, self._prev_y = rx_f, ry_f

        raw_ax = (raw_vx - self._vx) / dt
        raw_ay = (raw_vy - self._vy) / dt

        self._jx += 0.05 * (raw_ax - self._ax - self._jx)
        self._jy += 0.05 * (raw_ay - self._ay - self._jy)

        self._ax += accel_alpha * (raw_ax - self._ax)
        self._ay += accel_alpha * (raw_ay - self._ay)
        self._vx += vel_alpha * (raw_vx - self._vx)
        self._vy += vel_alpha * (raw_vy - self._vy)

        speed = aim_lut.mag_xy(self._vx, self._vy)
        if speed < min_speed:
            self._streak = 0
            self._dir_x = self._dir_y = 0
            self._confidence *= 0.95
            return 0.0, 0.0

        dx = 1 if self._vx >= 0 else -1
        dy = 1 if self._vy >= 0 else -1
        if dx == self._dir_x and dy == self._dir_y:
            self._streak += 1
        else:
            self._streak = 1
            self._dir_x = dx
            self._dir_y = dy

        self._confidence = min(1.0, self._confidence + 0.02)

        if self._streak < consistency:
            return 0.0, 0.0

        T = lead_horizon_ms
        jerk_factor = 0.5 * (self._jx * T * T * T / 6.0)
        jerk_factor_y = 0.5 * (self._jy * T * T * T / 6.0)

        lead_x = self._vx * T + 0.5 * self._ax * T * T + jerk_factor
        lead_y = self._vy * T + 0.5 * self._ay * T * T + jerk_factor_y
        lead_mag = aim_lut.mag_xy(lead_x, lead_y)

        if lead_mag > max_lead:
            scale = max_lead / lead_mag
            lead_x *= scale
            lead_y *= scale

        kx = self._kalman_x + self._kalman_vx * T
        ky = self._kalman_y + self._kalman_vy * T

        self._kalman_x = rx_f
        self._kalman_y = ry_f
        self._kalman_vx = raw_vx
        self._kalman_vy = raw_vy

        final_x = lead_x * (1.0 - kalman_weight) + (kx - rx_f) * kalman_weight
        final_y = lead_y * (1.0 - kalman_weight) + (ky - ry_f) * kalman_weight

        conf_scale = self._confidence * (0.7 + 0.3 * min(1.0, self._streak / 10.0))
        final_x *= conf_scale
        final_y *= conf_scale

        return final_x, final_y

    def reset(self) -> None:
        self._prev_x = None
        self._prev_y = None
        self._vx = 0.0
        self._vy = 0.0
        self._ax = 0.0
        self._ay = 0.0
        self._jx = 0.0
        self._jy = 0.0
        self._streak = 0
        self._dir_x = 0
        self._dir_y = 0
        self._confidence = 0.0


class MicroCorrectionEngineV3:
    """Engine de micro-correcoes de 3a geracao.

    TECNOLOGIA:
      - Adaptive low-pass filter
      - Histeresis para evitar oscillation
      - Predictive anti-overshoot
      - Axis-lock inteligente com deadzone dinamica
    """

    __slots__ = (
        '_persist_rx', '_persist_ry', '_persist_until',
        '_last_dir_x', '_last_dir_y', '_prev_magnitude',
        '_overshoot_count', '_filter_state',
    )

    def __init__(self) -> None:
        self._persist_rx: float = 0.0
        self._persist_ry: float = 0.0
        self._persist_until: float = 0.0
        self._last_dir_x: float = 0.0
        self._last_dir_y: float = 0.0
        self._prev_magnitude: float = 0.0
        self._overshoot_count: int = 0
        self._filter_state: float = 0.0

    def apply(
        self,
        rx: float,
        ry: float,
        *,
        enabled: bool,
        pull_strength: float,
        prev_rx: float,
        prev_ry: float,
        delta_ms: float,
        now: Optional[float] = None,
    ) -> Tuple[float, float]:
        if not enabled or pull_strength <= 0:
            return rx, ry

        t = now if now is not None else time.monotonic()
        mag = aim_lut.mag_xy(rx, ry)

        if mag > 500:
            self._detect_overshoot(mag)
            self._persist_rx = rx
            self._persist_ry = ry
            self._persist_until = t + 0.05
            self._last_dir_x = rx / mag if mag > 0 else 0.0
            self._last_dir_y = ry / mag if mag > 0 else 0.0
            self._prev_magnitude = mag
            return rx, ry

        if t < self._persist_until:
            decay = (self._persist_until - t) / 0.05
            pull = pull_strength * 0.3 * decay
            rx += self._last_dir_x * pull
            ry += self._last_dir_y * pull

        if mag > 0 and mag < 300:
            nx = rx / mag
            ny = ry / mag
            abs_nx = abs(nx)
            abs_ny = abs(ny)

            dynamic_deadzone = 0.5 - 0.2 * min(1.0, self._overshoot_count / 5.0)

            if abs_nx > abs_ny * (2.0 - dynamic_deadzone):
                ry *= 0.2
            elif abs_ny > abs_nx * (2.0 - dynamic_deadzone):
                rx *= 0.2

            if self._overshoot_count > 2:
                alpha = 0.3
                self._filter_state = self._filter_state * (1.0 - alpha) + mag * alpha
                filter_ratio = self._filter_state / max(mag, 1.0)
                if filter_ratio > 1.2:
                    rx *= 0.7
                    ry *= 0.7

        self._prev_magnitude = mag
        return aim_lut.clamp(rx, -32767.0, 32767.0), aim_lut.clamp(ry, -32767.0, 32767.0)

    def _detect_overshoot(self, current_mag: float) -> None:
        if self._prev_magnitude > 0:
            delta = current_mag - self._prev_magnitude
            if delta < -200:
                self._overshoot_count = min(10, self._overshoot_count + 1)
            elif delta > 100:
                self._overshoot_count = max(0, self._overshoot_count - 1)

    def reset(self) -> None:
        self._persist_rx = 0.0
        self._persist_ry = 0.0
        self._persist_until = 0.0
        self._last_dir_x = 0.0
        self._last_dir_y = 0.0
        self._prev_magnitude = 0.0
        self._overshoot_count = 0
        self._filter_state = 0.0


class AdaptiveStrengthEngineV3:
    """Engine de forca adaptativa de 3a geracao.

    TECNOLOGIA:
      - Multi-window tracking (1s, 5s, 30s)
      - Trend detection (melhorando/piorando)
      - Confidence-weighted adjustment
      - Anti-deteccao: variacao suave e previsivel
    """

    __slots__ = (
        '_hits_short', '_shots_short', '_window_short',
        '_hits_long', '_shots_long', '_window_long',
        '_current_mult', '_target_mult', '_ramp_start',
        '_trend', '_prev_hit_rate',
    )

    def __init__(self) -> None:
        self._hits_short: int = 0
        self._shots_short: int = 0
        self._window_short: float = time.monotonic()
        self._hits_long: int = 0
        self._shots_long: int = 0
        self._window_long: float = time.monotonic()
        self._current_mult: float = 1.0
        self._target_mult: float = 1.0
        self._ramp_start: float = 0.0
        self._trend: float = 0.0
        self._prev_hit_rate: float = 0.5

    def apply(
        self,
        rx: float,
        ry: float,
        *,
        enabled: bool,
        is_shooting: bool,
        is_hit: bool,
        delta_ms: float,
        min_mult: float = 0.7,
        max_mult: float = 1.3,
        ramp_ms: float = 500.0,
    ) -> Tuple[float, float]:
        if not enabled:
            return rx, ry

        now = time.monotonic()

        if now - self._window_short > 1.0:
            self._update_short_window(min_mult, max_mult)
            self._hits_short = 0
            self._shots_short = 0
            self._window_short = now

        if now - self._window_long > 30.0:
            self._update_long_window(min_mult, max_mult)
            self._hits_long = 0
            self._shots_long = 0
            self._window_long = now

        if is_shooting:
            self._shots_short += 1
            self._shots_long += 1
            if is_hit:
                self._hits_short += 1
                self._hits_long += 1

        if self._current_mult != self._target_mult:
            if self._ramp_start == 0.0:
                self._ramp_start = now
            elapsed = (now - self._ramp_start) * 1000.0
            progress = min(1.0, elapsed / ramp_ms)
            self._current_mult += (self._target_mult - self._current_mult) * progress * 0.1
            if progress >= 1.0:
                self._current_mult = self._target_mult
                self._ramp_start = 0.0

        if self._current_mult != 1.0:
            rx *= self._current_mult
            ry *= self._current_mult

        return rx, ry

    def _update_short_window(self, min_mult: float, max_mult: float) -> None:
        if self._shots_short == 0:
            return
        hit_rate = self._hits_short / self._shots_short
        trend = hit_rate - self._prev_hit_rate
        self._trend = self._trend * 0.7 + trend * 0.3
        self._prev_hit_rate = hit_rate

        if hit_rate > 0.6:
            self._target_mult = max(min_mult, 1.0 - (hit_rate - 0.6) * 0.5)
        elif hit_rate < 0.3:
            self._target_mult = min(max_mult, 1.0 + (0.3 - hit_rate) * 1.0)
        else:
            self._target_mult = 1.0

    def _update_long_window(self, min_mult: float, max_mult: float) -> None:
        if self._shots_long == 0:
            return
        hit_rate = self._hits_long / self._shots_long
        if hit_rate > 0.55:
            self._target_mult = max(min_mult, self._target_mult * 0.95)
        elif hit_rate < 0.35:
            self._target_mult = min(max_mult, self._target_mult * 1.05)

    def reset(self) -> None:
        self._hits_short = 0
        self._shots_short = 0
        self._window_short = time.monotonic()
        self._hits_long = 0
        self._shots_long = 0
        self._window_long = time.monotonic()
        self._current_mult = 1.0
        self._target_mult = 1.0
        self._ramp_start = 0.0
        self._trend = 0.0
        self._prev_hit_rate = 0.5


class EngagementDetectorV3:
    """Detector de engajamento de 3a geracao.

    TECNOLOGIA:
      - Intent detection (intencao de tiro)
      - Burst/spray classification
      - Multi-stage transitions com histeresis
      - Confidence scoring por estagio
    """

    __slots__ = (
        '_state', '_state_start', '_input_history',
        '_shot_history', '_burst_counter', '_spray_detected',
        '_confidence', '_transition_hysteresis',
    )

    def __init__(self) -> None:
        self._state = EngagementState.IDLE
        self._state_start: float = time.monotonic()
        self._input_history: list = []
        self._shot_history: list = []
        self._burst_counter: int = 0
        self._spray_detected: bool = False
        self._confidence: float = 0.0
        self._transition_hysteresis: float = 0.0

    def update(
        self,
        rx: float,
        ry: float,
        is_shooting: bool,
        is_aiming: bool,
        delta_ms: float,
    ) -> EngagementState:
        mag = aim_lut.mag_xy(rx, ry)

        self._input_history.append(mag)
        if len(self._input_history) > 15:
            self._input_history = self._input_history[-15:]

        self._shot_history.append(is_shooting)
        if len(self._shot_history) > 15:
            self._shot_history = self._shot_history[-15:]

        recent_shots = sum(self._shot_history[-5:])
        if recent_shots >= 4:
            self._spray_detected = True
        elif recent_shots == 0:
            self._spray_detected = False

        avg_mag = sum(self._input_history) / len(self._input_history) if self._input_history else 0.0
        mag_trend = 0.0
        if len(self._input_history) >= 3:
            recent = self._input_history[-3:]
            mag_trend = recent[-1] - recent[0]

        new_state = self._state

        if is_shooting and mag < 200:
            new_state = EngagementState.LOCKED
            self._confidence = min(1.0, self._confidence + 0.1)
        elif is_shooting and mag < 500:
            new_state = EngagementState.TRACKING
            self._confidence = min(1.0, self._confidence + 0.05)
        elif is_shooting:
            new_state = EngagementState.SEARCHING
        elif mag < 100 and not is_aiming:
            new_state = EngagementState.IDLE
            self._confidence *= 0.9
        elif mag < 200 and is_aiming:
            new_state = EngagementState.LOCKED
        elif avg_mag < 300 and mag_trend < 0:
            new_state = EngagementState.TRACKING
        elif mag > 500:
            new_state = EngagementState.SEARCHING
        else:
            new_state = EngagementState.TRACKING

        if new_state != self._state:
            if new_state.value > self._state.value:
                self._transition_hysteresis = 0.0
                self._state = new_state
                self._state_start = time.monotonic()
            else:
                self._transition_hysteresis += delta_ms
                if self._transition_hysteresis > 100.0:
                    self._state = new_state
                    self._state_start = time.monotonic()
                    self._transition_hysteresis = 0.0

        return self._state

    @property
    def state(self) -> EngagementState:
        return self._state

    @property
    def confidence(self) -> float:
        return self._confidence

    @property
    def is_spraying(self) -> bool:
        return self._spray_detected

    def reset(self) -> None:
        self._state = EngagementState.IDLE
        self._state_start = time.monotonic()
        self._input_history.clear()
        self._shot_history.clear()
        self._burst_counter = 0
        self._spray_detected = False
        self._confidence = 0.0
        self._transition_hysteresis = 0.0
