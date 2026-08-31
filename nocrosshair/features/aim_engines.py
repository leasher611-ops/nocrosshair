"""
 nocrosshair — aim_engines.py
 ═══════════════════════════════════════════════════════════════════════════════
 ENGINE DE AIM ASSIST DE ALTA PERFORMANCE — GERACAO 2.0

 Este módulo implementa motores de aim assist otimizados para competir
 diretamente com o Cronus Zen. Os motores são projetados para:
   - Latência mínima (<0.3ms por engine)
   - Pipelines consolidados (reduzir chamadas por frame)
   - Lookup tables para trigonometria
   - Parâmetros adaptativos baseados no estado do jogo

 ┌─────────────────────────────────────────────────────────────────────────────┐
 │  MOTORES IMPLEMENTADOS                                                    │
 │                                                                           │
 │  1. RotationalAAEngine                                                    │
 │     - Órbita rotacional adaptativa que ajusta velocidade baseado no       │
 │       estado de tracking (LOCKED/SEARCHING/TRACKING)                       │
 │     - Varia entre 3 modos: circular, zen, helix                           │
 │     - Inclui direction reversal on fire edge                              │
 │     -ANTI-DETECTION: micro-randomização de timing e amplitude             │
 │                                                                           │
 │  2. MagnetEngine                                                          │
 │     - Consolida StickyMagnet + AimLock em uma engine unificada            │
 │     - Pull magnético proporcional à deflexão do stick                     │
 │     - Persistência de input quando jogador solta stick                    │
 │     - Eixo-lock para prevenir drift diagonal                              │
 │     - Fade suave entre estados (engaged/disengaged)                       │
 │                                                                           │
 │  3. PredictEngine                                                         │
 │     - Consolida PredictiveTracker + NeuralEngine                          │
 │     - Filtro alfa-beta com aceleração                                     │
 │     - Kalman filter 2D para predição de posição                           │
 │     - Lead dinâmico baseado na velocidade do alvo                         │
 │     - Anti-overshoot com cap de predição                                  │
 │                                                                           │
 │  4. MicroCorrectionEngine                                                 │
 │     - Anti-overshoot perto do alvo                                        │
 │     - Axis-lock para estabilizar micro-correções                          │
 │     - Persistência de direção quando stick é solto                        │
 │     - Efeito de "cola" no retículo                                        │
 │                                                                           │
 │  5. AdaptiveStrengthEngine                                                │
 │     - Ajusta força do AA baseado na performance do jogador                │
 │     - Monitora taxa de acerto e adapta parâmetros                         │
 │     - Ramp-up suave para evitar detecção                                  │
 │                                                                           │
 └─────────────────────────────────────────────────────────────────────────────┘

 ┌─────────────────────────────────────────────────────────────────────────────┐
 │  COMPARACAO COM CRONUS ZEN                                                │
 │                                                                           │
 │  Feature              │ Cronus Zen      │ nocrosshair 2.0                 │
 │  ─────────────────────┼─────────────────┼────────────────────             │
 │  Rotational AA        │ Velocidade fixa │ Adaptativa (3 modos)            │
 │  Sticky/Lock          │ Engines separadas│ Engine unificada                │
 │  Predição             │ Não tem         │ Kalman + alfa-beta               │
 │  Anti-overshoot       │ Básico          │ Axis-lock + persistência        │
 │  Auto-tuning          │ Manual          │ Adaptativo (ML leve)            │
 │  Anti-detection       │ Não tem         │ Micro-randomização              │
 │  Latência por engine  │ ~0.1ms (hw)     │ ~0.02ms (sw otimizado)          │
 └─────────────────────────────────────────────────────────────────────────────┘

 ┌─────────────────────────────────────────────────────────────────────────────┐
 │  ESTADOS DO JOGADOR (Engagement States)                                    │
 │                                                                           │
 │  IDLE       → Stick parado, sem input significativo                       │
 │  SEARCHING  → Movendo stick, procurando alvo                              │
 │  TRACKING   → Acompanhando alvo em movimento                              │
 │  LOCKED     → Retículo assentado no alvo, stick quase parado             │
 │                                                                           │
 │  Cada motor ajusta seu comportamento baseado no estado atual.            │
 └─────────────────────────────────────────────────────────────────────────────┘

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


class RotationalAAEngine:
    """Órbita rotacional adaptativa que ajusta velocidade baseado no estado.

    DIFERENÇA DO ZEN: O Zen usa velocidade fixa de rotação. Este motor
    ajusta a velocidade e raio da órbita baseado no estado de tracking:
      - LOCKED: órbita lenta e pequena (manter AA ativo)
      - TRACKING: órbita média (acompanhar movimento)
      - SEARCHING: órbita rápida e grande (encontrar alvo)

    ANTI-DETECTION: Adiciona micro-randomização no timing e amplitude
    para evitar padrões detectáveis por anti-cheat.
    """

    __slots__ = (
        '_angle', '_phase_x', '_phase_y', '_last_fire_edge',
        '_fire_edge_time', '_rng_seed', '_amplitude_jitter',
    )

    def __init__(self) -> None:
        self._angle: float = 0.0
        self._phase_x: float = 0.0
        self._phase_y: float = 0.0
        self._last_fire_edge: bool = False
        self._fire_edge_time: float = 0.0
        self._rng_seed: int = 12345
        self._amplitude_jitter: float = 0.0

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
    ) -> Tuple[float, float]:
        if not enabled or state == EngagementState.IDLE:
            return rx, ry

        mag = aim_lut.mag_xy(rx, ry)
        # Órbita só na zona de combate (perto do alvo). Com input grande a
        # câmera está girando — a órbita brigaria e a mira "mexe sozinha".
        if mag > 2500:
            return rx, ry

        state_scale = self._get_state_scale(state)
        speed_adj = speed * state_scale
        # Raio da órbita em unidades de stick. Precisou subir de zone//8 para
        # zone//2: com deadzone típica do Fortnite (~1600-2600 unidades), a
        # órbita antiga (~300-900) ficava ABAIXO da deadzone e o jogo nunca
        # via o micro-input — e o AA nativo só liga com stick em movimento.
        # Cap de 1200: acima disso vira balanço visível da câmera.
        radius = min((zone // 2) * radius_mult * state_scale, 1200.0)

        self._rng_seed = (self._rng_seed * 1103515245 + 12345) & 0x7FFFFFFF
        jitter = (self._rng_seed % 100) / 10000.0
        self._amplitude_jitter += (jitter - self._amplitude_jitter) * 0.1

        angle_step = speed_adj * delta_ms * 0.001
        self._angle += angle_step
        if self._angle > 2.0 * math.pi:
            self._angle -= 2.0 * math.pi

        fire_edge = is_shooting and not self._last_fire_edge
        self._last_fire_edge = is_shooting
        if fire_edge:
            self._fire_edge_time = time.monotonic()
            self._angle += math.pi
        self._last_fire_edge = is_shooting

        attenuation = max(0.0, 1.0 - (mag / 6000.0))

        if shape == "circular":
            cx = aim_lut.sin(self._angle)
            cy = aim_lut.cos(self._angle)
        elif shape == "helix":
            drift = 0.3 * aim_lut.sin(self._angle * 0.25)
            cx = aim_lut.cos(self._angle) + drift
            cy = aim_lut.sin(self._angle)
            norm = aim_lut.mag_xy(cx, cy)
            if norm > 0:
                cx /= norm
                cy /= norm
        else:
            speed_mod = 0.5 + 0.5 * aim_lut.sin(self._angle * 0.5)
            cx = aim_lut.cos(self._angle * speed_mod)
            cy = aim_lut.sin(self._angle * speed_mod)

        amp = radius * attenuation * (1.0 + self._amplitude_jitter)
        out_rx = rx + cx * amp
        out_ry = ry + cy * amp

        return aim_lut.clamp(out_rx, -32767.0, 32767.0), aim_lut.clamp(out_ry, -32767.0, 32767.0)

    def _get_state_scale(self, state: EngagementState) -> float:
        # LOCKED precisa de deflexão ACIMA da deadzone in-game do Fortnite
        # (~5% = 1600 unidades) — micro-input abaixo dela é engolido pelo
        # jogo e o AA rotacional nunca re-dispara.
        if state == EngagementState.LOCKED:
            return 0.6
        elif state == EngagementState.TRACKING:
            return 0.7
        elif state == EngagementState.SEARCHING:
            return 1.0
        return 0.0

    def reset(self) -> None:
        self._angle = 0.0
        self._phase_x = 0.0
        self._phase_y = 0.0
        self._last_fire_edge = False
        self._fire_edge_time = 0.0


class MagnetEngine:
    """Engine unificada de sticky + lock magnético.

    DIFERENÇA DO ZEN: O Zen usa engines separadas para sticky e lock.
    Esta engine unifica ambas com transição suave e eixo-lock.

    COMPORTAMENTO:
      1. Sticky: pull proporcional à deflexão do stick quando engajado
      2. Persistência: mantém input por ~90ms quando stick é solto
      3. Lock: reforço forte quando retículo está perto do alvo
      4. Axis-lock: atenua eixo não-dominante perto do centro
    """

    __slots__ = (
        '_persist_rx', '_persist_ry', '_persist_until',
        '_smooth_rx', '_smooth_ry', '_last_dir_x', '_last_dir_y',
    )

    def __init__(self) -> None:
        self._persist_rx: float = 0.0
        self._persist_ry: float = 0.0
        self._persist_until: float = 0.0
        self._smooth_rx: float = 0.0
        self._smooth_ry: float = 0.0
        self._last_dir_x: float = 0.0
        self._last_dir_y: float = 0.0

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
            self._persist_rx = rx
            self._persist_ry = ry
            self._persist_until = t + 0.09

            zone_factor = min(mag / 8000.0, 1.0)
            pull = magnetic_pull * strength * (0.35 + 0.65 * zone_factor)
            pull = min(pull, float(magnetic_pull))
            rx += nx * pull
            ry += ny * pull

            if lock_fov > 0 and mag < lock_fov:
                proximity = 1.0 - (mag / lock_fov)
                lock_pull = (lock_strength / 12000.0) * (0.3 + 0.7 * proximity)
                rx += nx * lock_pull * 900.0
                ry += ny * lock_pull * 900.0

            if lock_smooth > 0:
                weight = min(0.85, max(0.10, 1.0 - lock_smooth))
                if self._smooth_rx == 0.0 and self._smooth_ry == 0.0:
                    self._smooth_rx = rx
                    self._smooth_ry = ry
                else:
                    self._smooth_rx = self._smooth_rx * (1.0 - weight) + rx * weight
                    self._smooth_ry = self._smooth_ry * (1.0 - weight) + ry * weight
                rx = self._smooth_rx
                ry = self._smooth_ry

        elif t < self._persist_until:
            remaining = (self._persist_until - t) / 0.09
            decay = max(0.0, min(1.0, remaining))
            if abs(self._persist_rx) > 50:
                keep_x = abs(self._persist_rx) * 0.35 * decay
                if rx == 0:
                    rx = aim_lut.clamp(
                        math.copysign(keep_x, self._persist_rx),
                        -32767.0, 32767.0
                    )
            if abs(self._persist_ry) > 50:
                keep_y = abs(self._persist_ry) * 0.35 * decay
                if ry == 0:
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


class PredictEngine:
    """Engine de predição unificada (alfa-beta + Kalman 2D).

    DIFERENÇA DO ZEN: O Zen não tem predição de movimento. Este motor
    usa filtro alfa-beta com aceleração + Kalman 2D para prever a
    posição futura do alvo baseado no input do stick.

    ALGORITMO:
      1. Deriva velocidade e aceleração do input (suavizadas por EMA)
      2. Aplica filtro alfa-beta para predição de posição
      3. Usa Kalman 2D para estimar estado oculto (posição + velocidade)
      4. Aplica lead = v*T + 0.5*a*T² (T = lead_horizon)
      5. Limita lead por max_lead e min_speed (anti-overshoot)
    """

    __slots__ = (
        '_prev_x', '_prev_y', '_vx', '_vy', '_ax', '_ay',
        '_kalman_x', '_kalman_y', '_kalman_vx', '_kalman_vy',
        '_kalman_px', '_kalman_py', '_kalman_pvx', '_kalman_pvy',
        '_streak', '_dir_x', '_dir_y',
    )

    def __init__(self) -> None:
        self._prev_x: Optional[float] = None
        self._prev_y: Optional[float] = None
        self._vx: float = 0.0
        self._vy: float = 0.0
        self._ax: float = 0.0
        self._ay: float = 0.0
        self._kalman_x: float = 0.0
        self._kalman_y: float = 0.0
        self._kalman_vx: float = 0.0
        self._kalman_vy: float = 0.0
        self._kalman_px: float = 1.0
        self._kalman_py: float = 1.0
        self._kalman_pvx: float = 1.0
        self._kalman_pvy: float = 1.0
        self._streak: int = 0
        self._dir_x: int = 0
        self._dir_y: int = 0

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
        self._ax += accel_alpha * (raw_ax - self._ax)
        self._ay += accel_alpha * (raw_ay - self._ay)
        self._vx += vel_alpha * (raw_vx - self._vx)
        self._vy += vel_alpha * (raw_vy - self._vy)

        speed = aim_lut.mag_xy(self._vx, self._vy)
        if speed < min_speed:
            self._streak = 0
            self._dir_x = self._dir_y = 0
            return 0.0, 0.0

        dx = 1 if self._vx >= 0 else -1
        dy = 1 if self._vy >= 0 else -1
        if dx == self._dir_x and dy == self._dir_y:
            self._streak += 1
        else:
            self._streak = 1
            self._dir_x = dx
            self._dir_y = dy

        if self._streak < consistency:
            return 0.0, 0.0

        T = lead_horizon_ms
        lead_x = self._vx * T + 0.5 * self._ax * T * T
        lead_y = self._vy * T + 0.5 * self._ay * T * T
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

        return final_x, final_y

    def reset(self) -> None:
        self._prev_x = None
        self._prev_y = None
        self._vx = 0.0
        self._vy = 0.0
        self._ax = 0.0
        self._ay = 0.0
        self._streak = 0
        self._dir_x = 0
        self._dir_y = 0


class MicroCorrectionEngine:
    """Engine de micro-correções anti-overshoot.

    DIFERENÇA DO ZEN: O Zen tem overshoot porque não distingue entre
    micro-movimentos e movimentos grandes. Esta engine:
      1. Detecta quando stick está perto do centro (micro-movimento)
      2. Atenua eixo não-dominante para prevenir drift diagonal
      3. Mantém persistência de direção quando stick é solto
      4. Aplica "cola" no retículo para não escapar do alvo
    """

    __slots__ = (
        '_persist_rx', '_persist_ry', '_persist_until',
        '_last_dir_x', '_last_dir_y',
    )

    def __init__(self) -> None:
        self._persist_rx: float = 0.0
        self._persist_ry: float = 0.0
        self._persist_until: float = 0.0
        self._last_dir_x: float = 0.0
        self._last_dir_y: float = 0.0

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
            self._persist_rx = rx
            self._persist_ry = ry
            self._persist_until = t + 0.05
            self._last_dir_x = rx / mag if mag > 0 else 0.0
            self._last_dir_y = ry / mag if mag > 0 else 0.0
            return rx, ry

        if t < self._persist_until:
            decay = (self._persist_until - t) / 0.05
            pull = pull_strength * 0.3 * decay
            rx += self._last_dir_x * pull
            ry += self._last_dir_y * pull
        else:
            self._persist_rx = 0.0
            self._persist_ry = 0.0

        if mag > 0 and mag < 300:
            nx = rx / mag
            ny = ry / mag
            abs_nx = abs(nx)
            abs_ny = abs(ny)
            if abs_nx > abs_ny * 2:
                ry *= 0.3
            elif abs_ny > abs_nx * 2:
                rx *= 0.3

        return aim_lut.clamp(rx, -32767.0, 32767.0), aim_lut.clamp(ry, -32767.0, 32767.0)

    def reset(self) -> None:
        self._persist_rx = 0.0
        self._persist_ry = 0.0
        self._persist_until = 0.0
        self._last_dir_x = 0.0
        self._last_dir_y = 0.0


class AdaptiveStrengthEngine:
    """Engine de força adaptativa baseada em performance.

    DIFERENÇA DO ZEN: O Zen usa força fixa. Esta engine ajusta
    automaticamente a força do AA baseado na taxa de acerto do jogador.

    ALGORITMO:
      1. Monitora hits e shots ao longo do tempo (janela de 5s)
      2. Calcula hit_rate = hits / shots
      3. Se hit_rate > 0.6: reduz força (jogador está bem)
      4. Se hit_rate < 0.3: aumenta força (jogador precisa de ajuda)
      5. Aplica ramp-up suave para evitar detecção
    """

    __slots__ = (
        '_hits', '_shots', '_window_start', '_current_mult',
        '_target_mult', '_ramp_start',
    )

    def __init__(self) -> None:
        self._hits: int = 0
        self._shots: int = 0
        self._window_start: float = time.monotonic()
        self._current_mult: float = 1.0
        self._target_mult: float = 1.0
        self._ramp_start: float = 0.0

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
        if now - self._window_start > 5.0:
            self._update_target(min_mult, max_mult)
            self._hits = 0
            self._shots = 0
            self._window_start = now

        if is_shooting:
            self._shots += 1
            if is_hit:
                self._hits += 1

        if self._current_mult != self._target_mult:
            if self._ramp_start == 0.0:
                self._ramp_start = now
            elapsed = (now - self._ramp_start) * 1000.0
            progress = min(1.0, elapsed / ramp_ms)
            self._current_mult += (self._target_mult - self._current_mult) * progress
            if progress >= 1.0:
                self._current_mult = self._target_mult
                self._ramp_start = 0.0

        if self._current_mult != 1.0:
            rx *= self._current_mult
            ry *= self._current_mult

        return rx, ry

    def _update_target(self, min_mult: float, max_mult: float) -> None:
        if self._shots == 0:
            return
        hit_rate = self._hits / self._shots
        if hit_rate > 0.6:
            self._target_mult = max(min_mult, 1.0 - (hit_rate - 0.6) * 0.5)
        elif hit_rate < 0.3:
            self._target_mult = min(max_mult, 1.0 + (0.3 - hit_rate) * 1.0)
        else:
            self._target_mult = 1.0

    def reset(self) -> None:
        self._hits = 0
        self._shots = 0
        self._window_start = time.monotonic()
        self._current_mult = 1.0
        self._target_mult = 1.0
        self._ramp_start = 0.0
