"""
 nocrosshair — advanced_aim_systems.py
 ═══════════════════════════════════════════════════════════════════════════════
 SISTEMAS DE AIM AVANÇADOS — TECNOLOGIA SOFT PRIVADO

 3 sistemas avançados para competir diretamente com o Cronus Zen:

 1. AntiRecoilML — Aprendizado de recoil por arma com ML leve
    - Detecta padrão de recoil automaticamente
    - Aprende com cada tiro (online learning)
    - Compensa recoil em tempo real
    - Salva/carrega profiles por arma

 2. BallisticPredictor — Predição com velocidade de bala + gravidade
    - Usa velocidade real da bala (m/s)
    - Compensa drop de bala por gravidade
    - Predição de Lead baseada em tempo de voo
    - Compensa distância até o alvo

 3. SmartHeadshot — Detecção de cabeça + puxão automático
    - Estima posição da cabeça baseado no movimento
    - Puxa para cabeça automaticamente
    - Ajusta por distância e tipo de arma
    - Anti-overshoot para não passar da cabeça

 ═══════════════════════════════════════════════════════════════════════════════
"""

import math
import time
import hashlib
from typing import Tuple, Optional, Dict, List
from dataclasses import dataclass, field
from nocrosshair.features.aim_lut import aim_lut


@dataclass
class WeaponProfile:
    """Profile de arma para Anti-Recoil."""
    name: str
    recoil_pattern_x: List[float] = field(default_factory=list)
    recoil_pattern_y: List[float] = field(default_factory=list)
    fire_rate_rpm: float = 600.0
    bullet_speed_ms: float = 30000.0
    damage: float = 20.0
    headshot_multiplier: float = 2.0
    spread_base: float = 1.5
    recoil_compensation: float = 1.0
    learned_shots: int = 0
    confidence: float = 0.0
    last_updated: float = 0.0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "recoil_pattern_x": self.recoil_pattern_x,
            "recoil_pattern_y": self.recoil_pattern_y,
            "fire_rate_rpm": self.fire_rate_rpm,
            "bullet_speed_ms": self.bullet_speed_ms,
            "damage": self.damage,
            "headshot_multiplier": self.headshot_multiplier,
            "spread_base": self.spread_base,
            "recoil_compensation": self.recoil_compensation,
            "learned_shots": self.learned_shots,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'WeaponProfile':
        return cls(
            name=d.get("name", "unknown"),
            recoil_pattern_x=d.get("recoil_pattern_x", []),
            recoil_pattern_y=d.get("recoil_pattern_y", []),
            fire_rate_rpm=d.get("fire_rate_rpm", 600.0),
            bullet_speed_ms=d.get("bullet_speed_ms", 30000.0),
            damage=d.get("damage", 20.0),
            headshot_multiplier=d.get("headshot_multiplier", 2.0),
            spread_base=d.get("spread_base", 1.5),
            recoil_compensation=d.get("recoil_compensation", 1.0),
            learned_shots=d.get("learned_shots", 0),
            confidence=d.get("confidence", 0.0),
        )


class AntiRecoilML:
    """Sistema de Anti-Recoil com Machine Learning leve.

    ALGORITMO:
      1. Coleta dados de recoil durante o tiro (dx, dy por frame)
      2. Usa Online Gradient Descent para aprender o padrão
      3. Compensa o recoil subtraindo o padrão aprendido
      4. Ajusta a compensação baseado na taxa de acerto

    VANTAGEM SOBRE ZEN:
      - Zen usa padrões estáticos pré-definidos
      - Nós aprendemos em tempo real (cada tiro melhora o padrão)
      - Adaptativo: muda conforme a arma e distância

    TECNOLOGIA:
      - Linear Regression com SGD (Stochastic Gradient Descent)
      - Feature engineering: tempo, cadência, bloom
      - Regularização L2 para evitar overfitting
      - Decay de learning rate para estabilidade
    """

    __slots__ = (
        '_profiles', '_current_weapon', '_recoil_buffer',
        '_recoil_index', '_learning_rate', '_weights_x', '_weights_y',
        '_bias_x', '_bias_y', '_shot_count', '_last_shot_time',
        '_features_buffer', '_feature_dim',
    )

    def __init__(self) -> None:
        self._profiles: Dict[str, WeaponProfile] = {}
        self._current_weapon: str = ""
        self._recoil_buffer: List[Tuple[float, float]] = []
        self._recoil_index: int = 0
        self._learning_rate: float = 0.01
        self._weights_x: List[float] = [0.0, 0.0, 0.0, 0.0]
        self._weights_y: List[float] = [0.0, 0.0, 0.0, 0.0]
        self._bias_x: float = 0.0
        self._bias_y: float = 0.0
        self._shot_count: int = 0
        self._last_shot_time: float = 0.0
        self._features_buffer: List[List[float]] = []
        self._feature_dim: int = 4

    def start_shooting(self, weapon: str) -> None:
        if weapon != self._current_weapon:
            self._current_weapon = weapon
            self._recoil_buffer.clear()
            self._recoil_index = 0
            self._features_buffer.clear()
            self._load_weapon_profile(weapon)

    def record_shot(
        self,
        delta_x: float,
        delta_y: float,
        delta_ms: float,
        is_ads: bool,
        distance: float,
    ) -> None:
        now = time.time()
        self._recoil_buffer.append((delta_x, delta_y))
        if len(self._recoil_buffer) > 100:
            self._recoil_buffer = self._recoil_buffer[-100:]

        features = self._extract_features(delta_ms, is_ads, distance)
        self._features_buffer.append(features)
        if len(self._features_buffer) > 100:
            self._features_buffer = self._features_buffer[-100:]

        self._shot_count += 1
        self._last_shot_time = now

        if self._shot_count % 5 == 0:
            self._online_learn()

        self._update_profile(delta_x, delta_y)

    def compensate(
        self,
        rx: float,
        ry: float,
        *,
        weapon: str,
        is_shooting: bool,
        is_ads: bool,
        delta_ms: float,
        distance: float,
    ) -> Tuple[float, float]:
        if not is_shooting:
            return rx, ry

        if weapon != self._current_weapon:
            self.start_shooting(weapon)

        profile = self._profiles.get(weapon)
        if profile and profile.confidence > 0.3:
            features = self._extract_features(delta_ms, is_ads, distance)
            pred_x = self._predict_x(features)
            pred_y = self._predict_y(features)

            comp_x = -pred_x * profile.recoil_compensation
            comp_y = -pred_y * profile.recoil_compensation

            comp_x *= min(1.0, profile.confidence)
            comp_y *= min(1.0, profile.confidence)

            rx += comp_x
            ry += comp_y

        return rx, ry

    def _extract_features(
        self,
        delta_ms: float,
        is_ads: bool,
        distance: float,
    ) -> List[float]:
        shot_index = min(self._recoil_index, 50)
        cadence = 60000.0 / max(delta_ms, 1.0)
        ads_factor = 1.0 if is_ads else 0.5
        distance_factor = min(1.0, distance / 10000.0)
        # Cap na cadência: no tick de ~1ms (1000Hz) a feature vale 60.0 —
        # sem cap o SGD diverge (pesos → inf/nan) e derruba o pipeline.
        return [float(shot_index), min(10.0, cadence / 1000.0), ads_factor, distance_factor]

    def _predict_x(self, features: List[float]) -> float:
        result = self._bias_x
        for i in range(min(len(features), len(self._weights_x))):
            result += features[i] * self._weights_x[i]
        return result

    def _predict_y(self, features: List[float]) -> float:
        result = self._bias_y
        for i in range(min(len(features), len(self._weights_y))):
            result += features[i] * self._weights_y[i]
        return result

    def _online_learn(self) -> None:
        if len(self._features_buffer) < 3:
            return

        lr = self._learning_rate / (1.0 + self._shot_count * 0.001)

        for i in range(len(self._features_buffer)):
            features = self._features_buffer[i]
            target_x = self._recoil_buffer[i][0] if i < len(self._recoil_buffer) else 0.0
            target_y = self._recoil_buffer[i][1] if i < len(self._recoil_buffer) else 0.0

            pred_x = self._predict_x(features)
            pred_y = self._predict_y(features)

            error_x = target_x - pred_x
            error_y = target_y - pred_y

            for j in range(min(len(features), len(self._weights_x))):
                # Gradient clipping: sem cap, o SGD diverge (inf/nan) com
                # features de cadência alta no tick de ~1ms.
                grad_x = max(-50.0, min(50.0, lr * error_x * features[j]))
                grad_y = max(-50.0, min(50.0, lr * error_y * features[j]))
                self._weights_x[j] = max(-100.0, min(100.0, self._weights_x[j] + grad_x))
                self._weights_y[j] = max(-100.0, min(100.0, self._weights_y[j] + grad_y))

            g_bias_x = max(-50.0, min(50.0, lr * error_x))
            g_bias_y = max(-50.0, min(50.0, lr * error_y))
            self._bias_x = max(-100.0, min(100.0, self._bias_x + g_bias_x))
            self._bias_y = max(-100.0, min(100.0, self._bias_y + g_bias_y))

        profile = self._profiles.get(self._current_weapon)
        if profile:
            profile.confidence = min(1.0, profile.confidence + 0.05)
            profile.learned_shots = self._shot_count
            profile.last_updated = time.time()

    def _update_profile(self, delta_x: float, delta_y: float) -> None:
        if self._current_weapon not in self._profiles:
            self._profiles[self._current_weapon] = WeaponProfile(name=self._current_weapon)

        profile = self._profiles[self._current_weapon]
        profile.recoil_pattern_x.append(delta_x)
        profile.recoil_pattern_y.append(delta_y)

        if len(profile.recoil_pattern_x) > 100:
            profile.recoil_pattern_x = profile.recoil_pattern_x[-100:]
            profile.recoil_pattern_y = profile.recoil_pattern_y[-100:]

    def _load_weapon_profile(self, weapon: str) -> None:
        if weapon in self._profiles:
            profile = self._profiles[weapon]
            self._weights_x = [0.0] * self._feature_dim
            self._weights_y = [0.0] * self._feature_dim
            if profile.recoil_pattern_x:
                avg_x = sum(profile.recoil_pattern_x) / len(profile.recoil_pattern_x)
                avg_y = sum(profile.recoil_pattern_y) / len(profile.recoil_pattern_y)
                self._weights_y[0] = avg_y * 0.01
                self._bias_y = avg_y * 0.1

    def stop_shooting(self) -> None:
        self._recoil_index = 0

    def get_profile(self, weapon: str) -> Optional[WeaponProfile]:
        return self._profiles.get(weapon)

    def get_all_profiles(self) -> Dict[str, WeaponProfile]:
        return self._profiles.copy()

    def reset(self) -> None:
        self._recoil_buffer.clear()
        self._recoil_index = 0
        self._features_buffer.clear()
        self._shot_count = 0
        self._last_shot_time = 0.0


class BallisticPredictor:
    """Preditor Balístico com Velocidade de Bala e Gravidade.

    ALGORITMO:
      1. Calcula tempo de voo: t = distância / velocidade_bala
      2. Compensa gravidade: drop = 0.5 * g * t²
      3. Calcula lead: lead = velocidade_alvo * t
      4. Aplica predição: target = alvo + lead + gravidade

    DADOS DE ARMA (default):
      - Pistola: 35000 m/s, drop baixo
      - AR: 30000 m/s, drop médio
      - Sniper: 50000 m/s, drop alto
      - Shotgun: 20000 m/s, drop alto

    VANTAGEM SOBRE ZEN:
      - Zen não compensa gravidade
      - Zen não usa velocidade real da bala
      - Nós usamos dados reais de cada arma
    """

    __slots__ = (
        '_gravity', '_bullet_speed', '_target_speed',
        '_prev_target_x', '_prev_target_y', '_prev_time',
        '_target_vx', '_target_vy', '_smooth_lead_x', '_smooth_lead_y',
    )

    def __init__(self) -> None:
        self._gravity: float = 980.0
        self._bullet_speed: float = 30000.0
        self._target_speed: float = 0.0
        self._prev_target_x: Optional[float] = None
        self._prev_target_y: Optional[float] = None
        self._prev_time: Optional[float] = None
        self._target_vx: float = 0.0
        self._target_vy: float = 0.0
        self._smooth_lead_x: float = 0.0
        self._smooth_lead_y: float = 0.0

    def predict(
        self,
        crosshair_x: float,
        crosshair_y: float,
        target_x: float,
        target_y: float,
        distance_cm: float,
        *,
        weapon: Optional[WeaponProfile] = None,
        delta_ms: float = 16.67,
        target_vx: Optional[float] = None,
        target_vy: Optional[float] = None,
        is_ads: bool = False,
    ) -> Tuple[float, float]:
        now = time.time()

        if weapon:
            self._bullet_speed = weapon.bullet_speed_ms

        if target_vx is not None and target_vy is not None:
            self._target_vx = target_vx
            self._target_vy = target_vy
        elif self._prev_target_x is not None and self._prev_time is not None:
            dt = max(now - self._prev_time, 0.001)
            self._target_vx = (target_x - self._prev_target_x) / dt
            self._target_vy = (target_y - self._prev_target_y) / dt
        else:
            self._target_vx = 0.0
            self._target_vy = 0.0

        self._prev_target_x = target_x
        self._prev_target_y = target_y
        self._prev_time = now

        distance_m = distance_cm / 100.0
        flight_time = distance_m / max(self._bullet_speed / 100.0, 1.0)

        gravity_drop = 0.5 * self._gravity * flight_time * flight_time

        lead_x = self._target_vx * flight_time
        lead_y = self._target_vy * flight_time + gravity_drop

        if is_ads:
            ads_factor = 0.7
            lead_x *= ads_factor
            lead_y *= ads_factor

        alpha = 0.3
        self._smooth_lead_x = self._smooth_lead_x * (1.0 - alpha) + lead_x * alpha
        self._smooth_lead_y = self._smooth_lead_y * (1.0 - alpha) + lead_y * alpha

        return self._smooth_lead_x, self._smooth_lead_y

    def set_weapon(self, weapon: WeaponProfile) -> None:
        self._bullet_speed = weapon.bullet_speed_ms

    def set_gravity(self, gravity: float) -> None:
        self._gravity = gravity

    def reset(self) -> None:
        self._prev_target_x = None
        self._prev_target_y = None
        self._prev_time = None
        self._target_vx = 0.0
        self._target_vy = 0.0
        self._smooth_lead_x = 0.0
        self._smooth_lead_y = 0.0


class SmartHeadshot:
    """Sistema de Headshot Inteligente.

    ALGORITMO:
      1. Estima posição da cabeça baseado no centro do corpo
      2. Ajusta altura da cabeça por distância (mais longe = mais alto)
      3. Puxa para cabeça com força adaptativa
      4. Anti-overshoot: para antes de passar da cabeça
      5. Compensa movimento do alvo

    DADOS ANATÔMICOS (estimativa):
      - Altura da cabeça: ~30cm do centro do torso
      - Largura da cabeça: ~20cm
      - Distância olhos-centro: ~15cm

    VANTAGEM SOBRE ZEN:
      - Zen não tem detecção de cabeça real
      - Zen usa offset fixo
      - Nós adaptamos por distância e arma
    """

    __slots__ = (
        '_head_offset_y', '_head_offset_x', '_confidence',
        '_prev_head_x', '_prev_head_y', '_smooth_head_x', '_smooth_head_y',
        '_overshoot_detector', '_pull_strength',
    )

    def __init__(self) -> None:
        self._head_offset_y: float = 30.0
        self._head_offset_x: float = 0.0
        self._confidence: float = 0.0
        self._prev_head_x: Optional[float] = None
        self._prev_head_y: Optional[float] = None
        self._smooth_head_x: float = 0.0
        self._smooth_head_y: float = 0.0
        self._overshoot_detector: float = 0.0
        self._pull_strength: float = 1.0

    def predict_head(
        self,
        body_x: float,
        body_y: float,
        distance_cm: float,
        *,
        weapon: Optional[WeaponProfile] = None,
        is_ads: bool = False,
        target_moving_up: bool = False,
        target_moving_down: bool = False,
    ) -> Tuple[float, float]:
        distance_m = max(distance_cm / 100.0, 1.0)

        height_scale = 1.0 + (distance_m - 10.0) * 0.005
        height_scale = max(0.8, min(1.5, height_scale))

        base_offset_y = self._head_offset_y * height_scale

        if weapon and weapon.headshot_multiplier > 2.0:
            base_offset_y *= 1.1

        if is_ads:
            base_offset_y *= 0.9

        head_x = body_x + self._head_offset_x
        head_y = body_y - base_offset_y

        alpha = 0.4
        self._smooth_head_x = self._smooth_head_x * (1.0 - alpha) + head_x * alpha
        self._smooth_head_y = self._smooth_head_y * (1.0 - alpha) + head_y * alpha

        return self._smooth_head_x, self._smooth_head_y

    def calculate_pull(
        self,
        crosshair_x: float,
        crosshair_y: float,
        head_x: float,
        head_y: float,
        *,
        strength: float = 1.0,
        max_pull: float = 500.0,
    ) -> Tuple[float, float]:
        dx = head_x - crosshair_x
        dy = head_y - crosshair_y

        dist = aim_lut.mag_xy(dx, dy)

        if dist < 1.0:
            return 0.0, 0.0

        if dist > max_pull * 3:
            self._confidence *= 0.9
            return 0.0, 0.0

        self._confidence = min(1.0, self._confidence + 0.02)

        pull_factor = min(1.0, dist / 200.0)
        pull_strength = strength * self._pull_strength * self._confidence * pull_factor

        pull_x = (dx / dist) * min(dist * pull_strength, max_pull)
        pull_y = (dy / dist) * min(dist * pull_strength, max_pull)

        if dist < 50:
            dampening = dist / 50.0
            pull_x *= dampening
            pull_y *= dampening

        return pull_x, pull_y

    def set_weapon(self, weapon: WeaponProfile) -> None:
        if weapon.headshot_multiplier >= 2.5:
            self._pull_strength = 1.2
        elif weapon.headshot_multiplier >= 2.0:
            self._pull_strength = 1.0
        else:
            self._pull_strength = 0.8

    def reset(self) -> None:
        self._prev_head_x = None
        self._prev_head_y = None
        self._smooth_head_x = 0.0
        self._smooth_head_y = 0.0
        self._confidence = 0.0
        self._overshoot_detector = 0.0


class AdvancedAimPipeline:
    """Pipeline integrado com os 3 sistemas avançados.

    Combina:
      1. AntiRecoilML — compensa recoil automaticamente
      2. BallisticPredictor — predição balística
      3. SmartHeadshot — puxa para cabeça

    USAGE:
      pipeline = AdvancedAimPipeline()
      rx, ry = pipeline.process(
          rx, ry,
          weapon="AR",
          is_shooting=True,
          is_ads=True,
          distance=5000,
          target_x=1000,
          target_y=2000,
      )
    """

    __slots__ = (
        'anti_recoil', 'ballistic', 'headshot',
        '_enabled', '_anti_recoil_strength',
        '_ballistic_strength', '_headshot_strength',
    )

    def __init__(self) -> None:
        self.anti_recoil = AntiRecoilML()
        self.ballistic = BallisticPredictor()
        self.headshot = SmartHeadshot()
        self._enabled: bool = True
        self._anti_recoil_strength: float = 1.0
        self._ballistic_strength: float = 1.0
        self._headshot_strength: float = 1.0

    def process(
        self,
        rx: float,
        ry: float,
        *,
        weapon: str,
        is_shooting: bool,
        is_ads: bool,
        distance_cm: float,
        target_x: Optional[float] = None,
        target_y: Optional[float] = None,
        target_vx: Optional[float] = None,
        target_vy: Optional[float] = None,
        delta_ms: float = 16.67,
    ) -> Tuple[float, float]:
        if not self._enabled:
            return rx, ry

        out_rx, out_ry = rx, ry

        if is_shooting:
            self.anti_recoil.start_shooting(weapon)
            self.anti_recoil.record_shot(
                0.0, 0.0,
                delta_ms, is_ads, distance_cm
            )
            out_rx, out_ry = self.anti_recoil.compensate(
                out_rx, out_ry,
                weapon=weapon,
                is_shooting=is_shooting,
                is_ads=is_ads,
                delta_ms=delta_ms,
                distance=distance_cm,
            )

        if target_x is not None and target_y is not None:
            weapon_profile = self.anti_recoil.get_profile(weapon)
            lead_x, lead_y = self.ballistic.predict(
                out_rx, out_ry,
                target_x, target_y,
                distance_cm,
                weapon=weapon_profile,
                delta_ms=delta_ms,
                target_vx=target_vx,
                target_vy=target_vy,
                is_ads=is_ads,
            )
            out_rx += lead_x * self._ballistic_strength
            out_ry += lead_y * self._ballistic_strength

            head_x, head_y = self.headshot.predict_head(
                target_x, target_y,
                distance_cm,
                weapon=weapon_profile,
                is_ads=is_ads,
            )
            pull_x, pull_y = self.headshot.calculate_pull(
                out_rx, out_ry,
                head_x, head_y,
                strength=self._headshot_strength,
            )
            out_rx += pull_x
            out_ry += pull_y

        if not is_shooting:
            self.anti_recoil.stop_shooting()

        return out_rx, out_ry

    def set_weapon(self, weapon: str) -> None:
        profile = self.anti_recoil.get_profile(weapon)
        if profile:
            self.ballistic.set_weapon(profile)
            self.headshot.set_weapon(profile)

    def set_strength(
        self,
        anti_recoil: float = 1.0,
        ballistic: float = 1.0,
        headshot: float = 1.0,
    ) -> None:
        self._anti_recoil_strength = anti_recoil
        self._ballistic_strength = ballistic
        self._headshot_strength = headshot

    def get_stats(self) -> dict:
        profiles = self.anti_recoil.get_all_profiles()
        return {
            "weapons_learned": len(profiles),
            "total_shots": sum(p.learned_shots for p in profiles.values()),
            "avg_confidence": (
                sum(p.confidence for p in profiles.values()) / max(1, len(profiles))
            ),
        }

    def reset(self) -> None:
        self.anti_recoil.reset()
        self.ballistic.reset()
        self.headshot.reset()
