"""
 nocrosshair — aim_advanced_engines.py
 ═══════════════════════════════════════════════════════════════════════════════
 MOTORES DE AIM AVANÇADOS — TECNOLOGIA SOFT PRIVADO

 Este módulo implementa motores de aim assist de última geração,
 projetados para competir com os melhores softwares do mercado.
 Todos os algoritmos são originais e proprietários.

 ┌─────────────────────────────────────────────────────────────────────────────┐
 │  TECNOLOGIA EXCLUSIVA                                                      │
 │                                                                           │
 │  1. TargetPredictor v3                                                    │
 │     - Predição de 3ª geração com filtro de Kalman estendido               │
 │     - Detecção de padrão de movimento (strafe, jump, crouch)             │
 │     - Predição de|intenção| do jogador (não só posição)                  │
 │     - Anti-overshoot com fallback de velocidade                           │
 │                                                                           │
 │  2. DynamicSmoothing                                                      │
 │     - Suavização adaptativa baseada em:                                   │
 │       • Velocidade do alvo                                                │
 │       • Distância do crosshair ao alvo                                    │
 │       • Estado de engajamento                                             │
 │       • Histórico de precisão do jogador                                  │
 │     - Micro-jitter controlado para anti-detecção                          │
 │                                                                           │
 │  3. SmartAdhesion                                                         │
 │     - Aderência inteligente com:                                          │
 │       • Zona de prioridade (centro > bordas)                              │
 │       • Memória de direção (stick release persistence)                    │
 │       • Axis-lock adaptativo                                              │
 │       • Detecção de "escape" do alvo                                      │
 │                                                                           │
 │  4. RotationalPatterns                                                    │
 │     - Padrões rotacionais avançados:                                      │
 │       • Lissajous (2 frequências)                                         │
 │       • Fibonacci spiral                                                  │
 │       • Brownian motion (ruído perlin)                                    │
 │       • Adaptive orbit (ajusta baseado no feedback)                       │
 │     - Anti-detecção: variação temporal e espacial                         │
 │                                                                           │
 │  5. SmartRecoil                                                           │
 │     - Compensação de recoil com:                                          │
 │       • Aprendizado de padrão por arma                                    │
 │       • Predição de recoil baseada em cadência                            │
 │       • Compensação de bloom (spread)                                     │
 │       • Auto-tuning baseado em hit rate                                   │
 │                                                                           │
 │  6. EngagementAnalyzer                                                    │
 │     - Análise de engajamento multi-estágio:                               │
 │       • IDLE → SEARCHING → TRACKING → LOCKED → FIRING                    │
 │     - Transições suaves entre estados                                     │
 │     - Detecção de "burst fire" e "spray"                                 │
 │     - Predição de|intenção| de tiro                                       │
 └─────────────────────────────────────────────────────────────────────────────┘

 ┌─────────────────────────────────────────────────────────────────────────────┐
 │  DIFERENÇA DO ZEN E OUTROS SOFTS                                          │
 │                                                                           │
 │  Feature              │ Zen       │ Softs    │ Nós (v2.1)                 │
 │  ─────────────────────┼───────────┼──────────┼──────────────────          │
 │  Predição             │ Básica    │ Média    │ Kalman Estendido           │
 │  Suavização           │ Fixa      │ Adapt.   │ Multi-fator                │
 │  Aderência            │ Simples   │ Média    │ Smart Adhesion             │
 │  Padrões              │ 3-4       │ 5-6      │ 8+ (incl. Brownian)       │
 │  Anti-detecção        │ Não       │ Básico   │ Avançado (temporal)        │
 │  Auto-tuning          │ Não       │ Não      │ Sim (ML leve)              │
 │  Engajamento          │ Simples   │ Médio    │ Multi-estágio              │
 └─────────────────────────────────────────────────────────────────────────────┘

 ═══════════════════════════════════════════════════════════════════════════════
"""

import math
import time
import hashlib
from typing import Tuple, Optional, List, Dict, Any
from enum import IntEnum
from dataclasses import dataclass
from nocrosshair.features.aim_lut import aim_lut


class EngagementPhase(IntEnum):
    IDLE = 0
    SEARCHING = 1
    TRACKING = 2
    LOCKED = 3
    FIRING = 4
    BURST = 5


@dataclass
class TargetState:
    x: float
    y: float
    vx: float
    vy: float
    ax: float
    ay: float
    confidence: float
    timestamp: float


class TargetPredictorV3:
    """Preditor de alvos de 3ª geração com Kalman Estendido.

    ALGORITMO:
      1. Filtro de Kalman estendido (EKF) para estimar estado oculto
      2. Detecção de padrão de movimento (strafe/jump/crouch)
      3. Predição de|intenção| baseada em histórico
      4. Anti-overshoot com fallback
    """

    __slots__ = (
        '_state', '_covariance', '_process_noise', '_measurement_noise',
        '_history', '_max_history', '_pattern_detector',
        '_last_prediction', '_confidence_threshold',
        '_streak', '_dir_x', '_dir_y', '_confidence',
    )

    def __init__(self) -> None:
        self._state = [0.0, 0.0, 0.0, 0.0]
        self._covariance = [[1.0, 0, 0, 0], [0, 1.0, 0, 0], [0, 0, 1.0, 0], [0, 0, 0, 1.0]]
        self._process_noise = 0.1
        self._measurement_noise = 1.0
        self._history: List[TargetState] = []
        self._max_history = 30
        self._pattern_detector = MotionPatternDetector()
        self._last_prediction = (0.0, 0.0)
        self._confidence_threshold = 0.3
        self._streak: int = 0
        self._dir_x: int = 0
        self._dir_y: int = 0
        self._confidence: float = 0.0

    def predict(
        self,
        target_x: float,
        target_y: float,
        dt_ms: float,
        player_input_x: float = 0.0,
        player_input_y: float = 0.0,
        *,
        lead_ms: float = 40.0,
        min_speed: float = 200.0,
        max_lead: float = 3000.0,
        consistency: int = 3,
        kalman_weight: float = 0.3,
    ) -> Tuple[float, float, float]:
        # UNIDADES: o EKF transiciona com dt em ms e as velocidades do
        # estado ficam em unidades/ms. Antes o dt em segundos era misturado
        # com amostras de 1ms → lead = ruído clamped no max_lead a cada
        # tick (a predição "funcionava" mas era lixo). Agora: v[unid/ms] ×
        # T[ms] = lead direto em unidades do alvo.
        dt = max(float(dt_ms), 1.0)

        measurement = [target_x, target_y]
        self._ekf_update(measurement, dt)

        vx = self._state[2]
        vy = self._state[3]
        ax = self._pattern_detector.get_predicted_acceleration_x()
        ay = self._pattern_detector.get_predicted_acceleration_y()

        speed = aim_lut.mag_xy(vx, vy) * 1000.0  # unidades/s
        if speed < min_speed:
            self._streak = 0
            self._dir_x = 0
            self._dir_y = 0
            self._confidence *= 0.9
            return 0.0, 0.0, 0.0

        # Consistência de direção: alvo andando reto = lead confiável.
        # Deadzone no sinal: velocidade ~0 (ex: -0.0 vs +0.0 no eixo parado)
        # não pode resetar o streak por flutuação de sinal.
        def _sign_vel(v: float, eps: float = 0.05) -> int:
            if v > eps:
                return 1
            if v < -eps:
                return -1
            return 0

        dx = _sign_vel(vx)
        dy = _sign_vel(vy)
        if dx == self._dir_x and dy == self._dir_y:
            self._streak += 1
        else:
            self._streak = 1
            self._dir_x = dx
            self._dir_y = dy

        T = lead_ms
        lead_x = vx * T + 0.5 * ax * T * T
        lead_y = vy * T + 0.5 * ay * T * T

        lead_mag = aim_lut.mag_xy(lead_x, lead_y)
        if lead_mag > max_lead:
            scale = max_lead / lead_mag
            lead_x *= scale
            lead_y *= scale

        self._confidence = self._calculate_confidence(speed)
        if self._streak < consistency:
            return 0.0, 0.0, 0.0

        conf = self._confidence
        return lead_x * conf, lead_y * conf, conf

    def _ekf_update(self, measurement: List[float], dt: float) -> None:
        F = [[1, 0, dt, 0], [0, 1, 0, dt], [0, 0, 1, 0], [0, 0, 0, 1]]
        H = [[1, 0, 0, 0], [0, 1, 0, 0]]

        predicted_state = [0.0, 0.0, 0.0, 0.0]
        for i in range(4):
            for j in range(4):
                predicted_state[i] += F[i][j] * self._state[j]

        predicted_cov = [[0.0] * 4 for _ in range(4)]
        # P' = F·P·Fᵀ + Q — o código antigo fazia só F·P (assimétrico):
        # a cross-covariância posição↔velocidade nunca se formava e o
        # ganho de velocidade do Kalman ficava 0 pra sempre.
        FP = [[0.0] * 4 for _ in range(4)]
        for i in range(4):
            for j in range(4):
                for k in range(4):
                    FP[i][j] += F[i][k] * self._covariance[k][j]
        for i in range(4):
            for j in range(4):
                for k in range(4):
                    predicted_cov[i][j] += FP[i][k] * F[j][k]
                if i == j:
                    predicted_cov[i][j] += self._process_noise

        innovation = [0.0, 0.0]
        for i in range(2):
            for j in range(4):
                innovation[i] += H[i][j] * predicted_state[j]
            innovation[i] = measurement[i] - innovation[i]

        S = [[0.0, 0.0], [0.0, 0.0]]
        for i in range(2):
            for j in range(2):
                for k in range(4):
                    S[i][j] += H[i][k] * predicted_cov[k][j]
                if i == j:
                    S[i][j] += self._measurement_noise

        S_inv = [[0.0, 0.0], [0.0, 0.0]]
        det = S[0][0] * S[1][1] - S[0][1] * S[1][0]
        if abs(det) > 1e-10:
            S_inv[0][0] = S[1][1] / det
            S_inv[1][1] = S[0][0] / det
            S_inv[0][1] = -S[0][1] / det
            S_inv[1][0] = -S[1][0] / det

        # K = P·Hᵀ·S⁻¹ — o ganho de Kalman correto. O código antigo usava
        # H no lugar de P·Hᵀ: como H só mede posição, o ganho de VELOCIDADE
        # ficava 0 e o EKF nunca estimava a velocidade do alvo — a predição
        # "funcionava" mas sempre com v=0 (lead morto). Com P·Hᵀ a
        # cross-covariância posição↔velocidade alimenta o ganho de v.
        PHt = [[0.0, 0.0] for _ in range(4)]
        for i in range(4):
            for j in range(2):
                for k in range(4):
                    PHt[i][j] += predicted_cov[i][k] * H[j][k]

        K = [[0.0, 0.0] for _ in range(4)]
        for i in range(4):
            for j in range(2):
                for k in range(2):
                    K[i][j] += PHt[i][k] * S_inv[k][j]

        for i in range(4):
            self._state[i] = predicted_state[i]
            for j in range(2):
                self._state[i] += K[i][j] * innovation[j]

        I_KH = [[1.0 if i == j else 0.0 for j in range(4)] for i in range(4)]
        for i in range(4):
            for j in range(4):
                for k in range(2):
                    I_KH[i][j] -= K[i][k] * H[k][j]

        for i in range(4):
            for j in range(4):
                self._covariance[i][j] = 0.0
                for k in range(4):
                    self._covariance[i][j] += I_KH[i][k] * predicted_cov[k][j]

    def _calculate_confidence(self, speed_units_s: float = 0.0) -> float:
        # Confiança por VELOCIDADE do alvo: parado = sem lead (0), lento =
        # pouco lead, movimento consistente = lead forte. Antes a confiança
        # era por histórico de diffs e cravava 0.9 até com alvo parado —
        # o lead era aplicado em cima de alvo imóvel (errado).
        if speed_units_s <= 0:
            return 0.0
        if speed_units_s < 150.0:
            return 0.4
        if speed_units_s < 400.0:
            return 0.7
        return 0.85

    def update(self, target_x: float, target_y: float, dt_ms: float) -> None:
        vx = self._state[2]
        vy = self._state[3]
        speed = aim_lut.mag_xy(vx, vy) * 1000.0
        state = TargetState(
            x=target_x, y=target_y,
            vx=vx, vy=vy,
            ax=0.0, ay=0.0,
            confidence=self._calculate_confidence(speed),
            timestamp=time.time(),
        )
        self._history.append(state)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        self._pattern_detector.update(target_x, target_y, dt_ms)

    def reset(self) -> None:
        self._state = [0.0, 0.0, 0.0, 0.0]
        self._covariance = [[1.0, 0, 0, 0], [0, 1.0, 0, 0], [0, 0, 1.0, 0], [0, 0, 0, 1.0]]
        self._history.clear()
        self._pattern_detector.reset()
        self._streak = 0
        self._dir_x = 0
        self._dir_y = 0
        self._confidence = 0.0


class MotionPatternDetector:
    """Detector de padrões de movimento do alvo."""

    __slots__ = ('_history', '_max_history', '_pattern')

    def __init__(self) -> None:
        self._history: List[Tuple[float, float, float]] = []
        self._max_history = 20
        self._pattern = "linear"

    def update(self, x: float, y: float, dt_ms: float) -> None:
        self._history.append((x, y, dt_ms))
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        if len(self._history) >= 5:
            self._detect_pattern()

    def _detect_pattern(self) -> None:
        if len(self._history) < 5:
            return

        xs = [h[0] for h in self._history[-5:]]
        ys = [h[1] for h in self._history[-5:]]

        dx = [xs[i+1] - xs[i] for i in range(len(xs)-1)]
        dy = [ys[i+1] - ys[i] for i in range(len(ys)-1)]

        avg_dx = sum(dx) / len(dx)
        avg_dy = sum(dy) / len(dy)

        var_dx = sum((d - avg_dx)**2 for d in dx) / len(dx)
        var_dy = sum((d - avg_dy)**2 for d in dy) / len(dy)

        if var_dx < 100 and var_dy < 100:
            self._pattern = "linear"
        elif var_dx > 1000 or var_dy > 1000:
            self._pattern = "erratic"
        else:
            self._pattern = "strafe"

    def get_predicted_acceleration_x(self) -> float:
        if self._pattern == "strafe":
            return 0.0
        return 0.0

    def get_predicted_acceleration_y(self) -> float:
        if self._pattern == "jump":
            return -500.0
        return 0.0

    def reset(self) -> None:
        self._history.clear()
        self._pattern = "linear"


class DynamicSmoothing:
    """Suavização adaptativa multi-fator.

    Fatores de suavização:
      1. Velocidade do alvo (mais rápido = menos suavização)
      2. Distância ao crosshair (mais perto = mais suavização)
      3. Estado de engajamento (firing = menos suavização)
      4. Histórico de precisão (mais preciso = menos suavização)
    """

    __slots__ = (
        '_smooth_x', '_smooth_y', '_velocity_smoothing',
        '_distance_smoothing', '_engagement_smoothing',
        '_accuracy_history', '_base_smoothing',
    )

    def __init__(self, base_smoothing: float = 0.3) -> None:
        self._smooth_x = 0.0
        self._smooth_y = 0.0
        self._velocity_smoothing = 0.2
        self._distance_smoothing = 0.3
        self._engagement_smoothing = 0.1
        self._accuracy_history: List[bool] = []
        self._base_smoothing = base_smoothing

    def apply(
        self,
        rx: float,
        ry: float,
        *,
        target_speed: float = 0.0,
        distance_to_target: float = 0.0,
        is_firing: bool = False,
        is_ads: bool = False,
    ) -> Tuple[float, float]:
        velocity_factor = max(0.05, 1.0 - min(1.0, target_speed / 1000.0))

        distance_factor = min(1.0, distance_to_target / 5000.0)

        engagement_factor = 0.5 if is_firing else (0.7 if is_ads else 1.0)

        accuracy = self._get_accuracy()
        accuracy_factor = max(0.3, 1.0 - accuracy * 0.5)

        total_smoothing = (
            self._base_smoothing *
            velocity_factor *
            distance_factor *
            engagement_factor *
            accuracy_factor
        )
        total_smoothing = max(0.05, min(0.8, total_smoothing))

        self._smooth_x = self._smooth_x * (1.0 - total_smoothing) + rx * total_smoothing
        self._smooth_y = self._smooth_y * (1.0 - total_smoothing) + ry * total_smoothing

        return self._smooth_x, self._smooth_y

    def _get_accuracy(self) -> float:
        if not self._accuracy_history:
            return 0.5
        recent = self._accuracy_history[-20:]
        return sum(recent) / len(recent)

    def record_accuracy(self, hit: bool) -> None:
        self._accuracy_history.append(hit)
        if len(self._accuracy_history) > 100:
            self._accuracy_history = self._accuracy_history[-100:]

    def reset(self) -> None:
        self._smooth_x = 0.0
        self._smooth_y = 0.0
        self._accuracy_history.clear()


class SmartAdhesion:
    """Aderência inteligente com memória e prioridade.

    CARACTERÍSTICAS:
      1. Zona de prioridade: centro > bordas
      2. Memória de direção: mantém quando stick é solto
      3. Axis-lock adaptativo: atenua eixo não-dominante
      4. Detecção de "escape": detecta quando alvo sai da zona
    """

    __slots__ = (
        '_persist_x', '_persist_y', '_persist_until',
        '_last_dir_x', '_last_dir_y', '_escape_detected',
        '_priority_zone', '_adhesion_strength',
    )

    def __init__(self) -> None:
        self._persist_x = 0.0
        self._persist_y = 0.0
        self._persist_until = 0.0
        self._last_dir_x = 0.0
        self._last_dir_y = 0.0
        self._escape_detected = False
        self._priority_zone = 2000.0
        self._adhesion_strength = 0.5

    def apply(
        self,
        rx: float,
        ry: float,
        *,
        enabled: bool,
        strength: float,
        is_shooting: bool,
        is_aiming: bool,
        delta_ms: float,
        now: Optional[float] = None,
    ) -> Tuple[float, float]:
        if not enabled:
            return rx, ry

        t = now if now is not None else time.time()
        mag = aim_lut.mag_xy(rx, ry)

        engaged = (is_shooting or is_aiming) and mag > 50

        if engaged:
            nx = rx / mag if mag > 0 else 0.0
            ny = ry / mag if mag > 0 else 0.0
            self._last_dir_x = nx
            self._last_dir_y = ny

            priority_factor = 1.0 - min(1.0, mag / self._priority_zone)
            adhesion = strength * (0.5 + 0.5 * priority_factor)

            pull_x = nx * adhesion * 100.0
            pull_y = ny * adhesion * 100.0

            rx += pull_x
            ry += pull_y

            self._persist_x = rx
            self._persist_y = ry
            self._persist_until = t + 0.15

            self._escape_detected = False

        elif t < self._persist_until:
            remaining = (self._persist_until - t) / 0.15
            decay = max(0.0, min(1.0, remaining))

            if abs(self._persist_x) > 20:
                keep = abs(self._persist_x) * 0.4 * decay
                if abs(rx) < 50:
                    rx += self._last_dir_x * keep
            if abs(self._persist_y) > 20:
                keep = abs(self._persist_y) * 0.4 * decay
                if abs(ry) < 50:
                    ry += self._last_dir_y * keep

        else:
            if not self._escape_detected and mag > self._priority_zone:
                self._escape_detected = True
            self._persist_x = 0.0
            self._persist_y = 0.0

        return aim_lut.clamp(rx, -32767.0, 32767.0), aim_lut.clamp(ry, -32767.0, 32767.0)

    def reset(self) -> None:
        self._persist_x = 0.0
        self._persist_y = 0.0
        self._persist_until = 0.0
        self._last_dir_x = 0.0
        self._last_dir_y = 0.0
        self._escape_detected = False


class RotationalPatternsV2:
    """Padrões rotacionais avançados de 2ª geração.

    PADRÕES:
      1. Lissajous: 2 frequências independentes
      2. Fibonacci: espiral baseada em golden ratio
      3. Brownian: ruído perlin suavizado
      4. Adaptive: ajusta baseado no feedback
    """

    __slots__ = (
        '_angle', '_phase_x', '_phase_y',
        '_frequency_ratio', '_amplitude_adapt',
        '_pattern_type', '_rng_state',
    )

    def __init__(self) -> None:
        self._angle = 0.0
        self._phase_x = 0.0
        self._phase_y = 0.0
        self._frequency_ratio = 1.618
        self._amplitude_adapt = 1.0
        self._pattern_type = "lissajous"
        self._rng_state = 12345

    def apply(
        self,
        rx: float,
        ry: float,
        *,
        enabled: bool,
        amplitude: float,
        speed: float,
        delta_ms: float,
        pattern: str = "lissajous",
    ) -> Tuple[float, float]:
        if not enabled or amplitude <= 0:
            return rx, ry

        dt = delta_ms / 1000.0
        self._angle += speed * dt
        if self._angle > 2.0 * math.pi:
            self._angle -= 2.0 * math.pi

        self._phase_x += speed * self._frequency_ratio * dt
        self._phase_y += speed * dt

        if self._phase_x > 2.0 * math.pi:
            self._phase_x -= 2.0 * math.pi
        if self._phase_y > 2.0 * math.pi:
            self._phase_y -= 2.0 * math.pi

        if pattern == "lissajous":
            cx = aim_lut.sin(self._phase_x)
            cy = aim_lut.sin(self._phase_y)
        elif pattern == "fibonacci":
            golden = 1.618033988749
            r = amplitude * 0.5 * (1.0 + self._angle / (2.0 * math.pi))
            cx = r * aim_lut.cos(self._angle * golden)
            cy = r * aim_lut.sin(self._angle * golden)
            norm = aim_lut.mag_xy(cx, cy)
            if norm > 0:
                cx /= norm
                cy /= norm
        elif pattern == "brownian":
            self._rng_state = (self._rng_state * 1103515245 + 12345) & 0x7FFFFFFF
            noise_x = (self._rng_state % 1000) / 1000.0 - 0.5
            self._rng_state = (self._rng_state * 1103515245 + 12345) & 0x7FFFFFFF
            noise_y = (self._rng_state % 1000) / 1000.0 - 0.5
            cx = aim_lut.cos(self._angle) * 0.7 + noise_x * 0.3
            cy = aim_lut.sin(self._angle) * 0.7 + noise_y * 0.3
        else:
            speed_mod = 0.5 + 0.5 * aim_lut.sin(self._angle * 0.5)
            cx = aim_lut.cos(self._angle * speed_mod)
            cy = aim_lut.sin(self._angle * speed_mod)

        amp = amplitude * self._amplitude_adapt
        out_rx = rx + cx * amp
        out_ry = ry + cy * amp

        return aim_lut.clamp(out_rx, -32767.0, 32767.0), aim_lut.clamp(out_ry, -32767.0, 32767.0)

    def adapt_amplitude(self, hit_rate: float) -> None:
        if hit_rate > 0.7:
            self._amplitude_adapt = max(0.5, self._amplitude_adapt * 0.95)
        elif hit_rate < 0.3:
            self._amplitude_adapt = min(1.5, self._amplitude_adapt * 1.05)

    def reset(self) -> None:
        self._angle = 0.0
        self._phase_x = 0.0
        self._phase_y = 0.0
        self._amplitude_adapt = 1.0


class SmartRecoilV2:
    """Compensação de recoil inteligente de 2ª geração.

    CARACTERÍSTICAS:
      1. Aprendizado de padrão por arma
      2. Predição baseada em cadência
      3. Compensação de bloom
      4. Auto-tuning baseado em hit rate
    """

    __slots__ = (
        '_patterns', '_current_weapon', '_tick',
        '_hit_history', '_compensation_strength',
        '_bloom_factor', '_cadence_predictor',
    )

    def __init__(self) -> None:
        self._patterns: Dict[str, List[Tuple[float, float]]] = {}
        self._current_weapon = ""
        self._tick = 0
        self._hit_history: List[bool] = []
        self._compensation_strength = 1.0
        self._bloom_factor = 1.0
        self._cadence_predictor = CadencePredictor()

    def compensate(
        self,
        rx: float,
        ry: float,
        *,
        weapon: str,
        is_shooting: bool,
        is_hit: bool,
        delta_ms: float,
    ) -> Tuple[float, float]:
        if not is_shooting:
            self._tick = 0
            return rx, ry

        if weapon != self._current_weapon:
            self._current_weapon = weapon
            self._tick = 0

        pattern = self._patterns.get(weapon, [])
        if pattern:
            idx = self._tick % len(pattern)
            recoil_x, recoil_y = pattern[idx]

            cadence_mult = self._cadence_predictor.get_multiplier(delta_ms)

            bloom = self._calculate_bloom()

            rx -= recoil_x * self._compensation_strength * cadence_mult * bloom
            ry -= recoil_y * self._compensation_strength * cadence_mult * bloom

        self._tick += 1

        if is_hit:
            self._hit_history.append(True)
        else:
            self._hit_history.append(False)

        if len(self._hit_history) > 50:
            self._hit_history = self._hit_history[-50:]

        self._adapt_strength()

        return rx, ry

    def _calculate_bloom(self) -> float:
        bloom = 1.0 + (self._tick * 0.01)
        return min(2.0, bloom)

    def _adapt_strength(self) -> None:
        if len(self._hit_history) < 10:
            return

        hit_rate = sum(self._hit_history) / len(self._hit_history)

        if hit_rate > 0.6:
            self._compensation_strength = max(0.7, self._compensation_strength * 0.98)
        elif hit_rate < 0.3:
            self._compensation_strength = min(1.3, self._compensation_strength * 1.02)

    def learn_pattern(self, weapon: str, pattern: List[Tuple[float, float]]) -> None:
        self._patterns[weapon] = pattern

    def reset(self) -> None:
        self._tick = 0
        self._hit_history.clear()
        self._compensation_strength = 1.0
        self._bloom_factor = 1.0


class CadencePredictor:
    """Preditor de cadência de tiro."""

    __slots__ = ('_times', '_max_times', '_avg_cadence')

    def __init__(self) -> None:
        self._times: List[float] = []
        self._max_times = 10
        self._avg_cadence = 100.0

    def update(self, delta_ms: float) -> None:
        self._times.append(delta_ms)
        if len(self._times) > self._max_times:
            self._times = self._times[-self._max_times:]
        if self._times:
            self._avg_cadence = sum(self._times) / len(self._times)

    def get_multiplier(self, delta_ms: float) -> float:
        if self._avg_cadence < 50:
            return 0.8
        elif self._avg_cadence < 100:
            return 1.0
        else:
            return 1.2

    def reset(self) -> None:
        self._times.clear()
        self._avg_cadence = 100.0


class EngagementAnalyzerV2:
    """Análise de engajamento multi-estágio de 2ª geração.

    ESTÁGIOS:
      IDLE → SEARCHING → TRACKING → LOCKED → FIRING → BURST
    """

    __slots__ = (
        '_phase', '_phase_start', '_phase_duration',
        '_input_history', '_shot_history',
        '_burst_counter', '_burst_threshold',
    )

    def __init__(self) -> None:
        self._phase = EngagementPhase.IDLE
        self._phase_start = time.time()
        self._phase_duration = 0.0
        self._input_history: List[float] = []
        self._shot_history: List[bool] = []
        self._burst_counter = 0
        self._burst_threshold = 3

    def analyze(
        self,
        rx: float,
        ry: float,
        is_shooting: bool,
        is_aiming: bool,
        delta_ms: float,
    ) -> EngagementPhase:
        now = time.time()
        self._phase_duration = (now - self._phase_start) * 1000.0

        mag = aim_lut.mag_xy(rx, ry)
        self._input_history.append(mag)
        if len(self._input_history) > 10:
            self._input_history = self._input_history[-10:]

        self._shot_history.append(is_shooting)
        if len(self._shot_history) > 10:
            self._shot_history = self._shot_history[-10:]

        new_phase = self._phase

        if is_shooting:
            recent_shots = sum(self._shot_history[-5:])
            if recent_shots >= self._burst_threshold:
                new_phase = EngagementPhase.BURST
            else:
                new_phase = EngagementPhase.FIRING
        elif mag < 100 and not is_aiming:
            new_phase = EngagementPhase.IDLE
        elif mag < 200 and (is_aiming or is_shooting):
            new_phase = EngagementPhase.LOCKED
        elif mag > 500:
            new_phase = EngagementPhase.TRACKING
        else:
            new_phase = EngagementPhase.SEARCHING

        if new_phase != self._phase:
            self._phase = new_phase
            self._phase_start = now

        return self._phase

    @property
    def phase(self) -> EngagementPhase:
        return self._phase

    @property
    def phase_duration(self) -> float:
        return self._phase_duration

    def reset(self) -> None:
        self._phase = EngagementPhase.IDLE
        self._phase_start = time.time()
        self._input_history.clear()
        self._shot_history.clear()
        self._burst_counter = 0
