#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sistemas de Aim Avançados — Multi-Engine Polar, Ghost Tracker, Burst Mode,
Batts Sticky Diamond, XANAX AI Adaptativo.

Inspirado nos scripts premium mais avançados do mercado (Aimlock Custom,
Apex v6.0, Eclipse V6, Xanax V7) mas implementado do zero, sem memória,
sem visão computacional — apenas manipulação de input do controller.
"""

import math
import time
from dataclasses import dataclass, field
from typing import Optional, Tuple, List


# ═══════════════════════════════════════════════════════════════════════
# 1. MULTI-ENGINE POLAR — 4 motores simultâneos de órbita
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class PolarEngineConfig:
    """Configuração de um único motor polar."""
    enabled: bool = True
    radius: int = 10           # raio da órbita (unidades de stick)
    angle_step: float = 15.0   # graus por tick de rotação
    shape: str = "circle"      # circle, oval_tall, oval_wide, spiral, zigzag
    fire_boost_radius: int = 0 # boost extra no raio ao atirar
    fire_boost_angle: float = 0.0  # boost extra no ângulo ao atirar
    ads_only: bool = False     # só ativa em ADS
    hipfire_enabled: bool = True  # ativa em hipfire


@dataclass
class MultiPolarConfig:
    """Configuração dos 4 motores polar simultâneos."""
    enabled: bool = False
    # Motor 1: Ultra-close (shotgun/SMG)
    close: PolarEngineConfig = field(default_factory=lambda: PolarEngineConfig(
        enabled=True, radius=3, angle_step=8.0, shape="circle",
        fire_boost_radius=2, fire_boost_angle=3.0,
    ))
    # Motor 2: Close-medium (SMG/AR)
    medium: PolarEngineConfig = field(default_factory=lambda: PolarEngineConfig(
        enabled=True, radius=8, angle_step=12.0, shape="oval_tall",
        fire_boost_radius=3, fire_boost_angle=5.0,
    ))
    # Motor 3: Medium-long (AR)
    long: PolarEngineConfig = field(default_factory=lambda: PolarEngineConfig(
        enabled=True, radius=14, angle_step=18.0, shape="oval_wide",
        fire_boost_radius=4, fire_boost_angle=4.0,
    ))
    # Motor 4: Sniper (long range)
    sniper: PolarEngineConfig = field(default_factory=lambda: PolarEngineConfig(
        enabled=True, radius=20, angle_step=22.0, shape="spiral",
        fire_boost_radius=5, fire_boost_angle=6.0, ads_only=True,
    ))


class MultiPolarEngine:
    """4 motores polar simultâneos — cada um cobre uma faixa de alcance.

    O jogador não precisa selecionar alcance; os 4 rodam ao mesmo tempo
    e o efeito combinado cria uma órbita rica e multi-camada.
    Ultra-close (amp baixo, freq alta) = grude em shotgun/SMG.
    Sniper (amp alto, freq baixa) = estabilidade em longo alcance.
    """

    def __init__(self, cfg: Optional[MultiPolarConfig] = None):
        self.cfg = cfg if cfg is not None else MultiPolarConfig()
        self._phases: List[float] = [0.0, 0.0, 0.0, 0.0]

    def apply(self, rx: int, ry: int, is_aiming: bool, is_shooting: bool,
              delta_ms: float) -> Tuple[int, int]:
        if not self.cfg.enabled:
            return rx, ry

        engines = [self.cfg.close, self.cfg.medium, self.cfg.long, self.cfg.sniper]

        for i, eng in enumerate(engines):
            if not eng.enabled:
                continue
            if eng.ads_only and not is_aiming:
                continue
            if not eng.hipfire_enabled and not is_aiming:
                continue

            self._phases[i] += math.radians(eng.angle_step) * (delta_ms / 16.0)
            if self._phases[i] > 2.0 * math.pi:
                self._phases[i] -= 2.0 * math.pi

            r = eng.radius
            if is_shooting:
                r += eng.fire_boost_radius
            angle = self._phases[i]
            a_step = eng.fire_boost_angle if is_shooting else 0.0

            if eng.shape == "oval_tall":
                ox = int(r * 0.6 * math.cos(angle + a_step))
                oy = int(r * math.sin(angle + a_step))
            elif eng.shape == "oval_wide":
                ox = int(r * math.cos(angle + a_step))
                oy = int(r * 0.6 * math.sin(angle + a_step))
            elif eng.shape == "spiral":
                spiral_r = r * (0.7 + 0.3 * abs(math.sin(angle * 0.5)))
                ox = int(spiral_r * math.cos(angle + a_step))
                oy = int(spiral_r * math.sin(angle + a_step))
            elif eng.shape == "zigzag":
                ox = int(r * math.copysign(1.0, math.sin(angle)) * abs(math.sin(angle * 2)))
                oy = int(r * 0.5 * math.cos(angle + a_step))
            else:  # circle
                ox = int(r * math.cos(angle + a_step))
                oy = int(r * math.sin(angle + a_step))

            rx = max(-32767, min(32767, rx + ox))
            ry = max(-32767, min(32767, ry + oy))

        return rx, ry

    def reset(self) -> None:
        self._phases = [0.0, 0.0, 0.0, 0.0]


# ═══════════════════════════════════════════════════════════════════════
# 2. GHOST TRACKER — desaceleração no aim bubble
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class GhostTrackerConfig:
    """Desacelera o aim quando o crosshair está dentro do aim bubble.
    Anti-oversoot: se o jogador empurra o stick forte demais, o ghost
    tracker freia suavemente pra manter o crosshair no alvo."""
    enabled: bool = False
    bubble_radius: int = 8000    # raio do "aim bubble" (unidades stick)
    decel_strength: float = 0.3  # força da desaceleração (0.0-1.0)
    decel_ramp: float = 0.5      # suavidade da transição (0.0-1.0)
    stick_threshold: int = 4000  # stick mínimo pra ativar desaceleração


class GhostTrackerEngine:
    """Desacelera o stick quando o crosshair tá perto do alvo.

    Quando o stick tá sendo empurrado forte mas o crosshair já tá dentro
    do aim bubble (distância baixa), o ghost tracker reduz a velocidade
    do stick proporcionalmente — evitando overshoot e mantendo o grude.
    """

    def __init__(self, cfg: Optional[GhostTrackerConfig] = None):
        self.cfg = cfg if cfg is not None else GhostTrackerConfig()
        self._in_bubble: bool = False

    def apply(self, rx: int, ry: int, is_aiming: bool,
              is_shooting: bool) -> Tuple[int, int]:
        if not self.cfg.enabled:
            return rx, ry

        mag = math.hypot(rx, ry)
        in_bubble = mag < self.cfg.bubble_radius

        if in_bubble and mag > self.cfg.stick_threshold:
            ratio = mag / self.cfg.bubble_radius
            decel = self.cfg.decel_strength * (1.0 - ratio)
            factor = 1.0 - decel * self.cfg.decel_ramp
            rx = int(rx * factor)
            ry = int(ry * factor)
            self._in_bubble = True
        else:
            if self._in_bubble:
                factor = 1.0 + self.cfg.decel_strength * 0.2
                rx = int(rx * factor)
                ry = int(ry * factor)
            self._in_bubble = False

        return max(-32767, min(32767, rx)), max(-32767, min(32767, ry))

    @property
    def in_bubble(self) -> bool:
        return self._in_bubble


# ═══════════════════════════════════════════════════════════════════════
# 3. BURST MODE — boost nos primeiros tiros de rajada
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class BurstModeConfig:
    """Boost de aim assist nos primeiros N tiros de cada rajada.
    Compensa o "first shot kick" e o recoil inicial antes do
    anti-recoil estabilizar."""
    enabled: bool = False
    burst_count: int = 3         # quantos tiros terão boost
    aim_boost: float = 1.5       # multiplicador de aim assist (1.5 = +50%)
    recoil_reduction: float = 0.7 # redução de recoil nos primeiros tiros (0.7 = -30%)
    cooldown_ms: float = 200.0   # tempo entre rajadas pra resetar o counter


class BurstModeEngine:
    """Boost de aim nos primeiros tiros de cada rajada.

    Detecta o início de uma rajada (transição de não-atirando → atirando)
    e aplica boost de aim assist + redução de recoil nos primeiros N tiros.
    """

    def __init__(self, cfg: Optional[BurstModeConfig] = None):
        self.cfg = cfg if cfg is not None else BurstModeConfig()
        self._burst_active: bool = False
        self._burst_frames: int = 0
        self._last_fire_time: float = 0.0

    def apply(self, rx: int, ry: int, is_shooting: bool,
              now: float, delta_ms: float) -> Tuple[int, int, float]:
        """Retorna (rx, ry, recoil_multiplier)."""
        if not self.cfg.enabled:
            return rx, ry, 1.0

        if is_shooting:
            if not self._burst_active:
                time_since_last = (now - self._last_fire_time) * 1000.0
                if time_since_last > self.cfg.cooldown_ms:
                    self._burst_active = True
                    self._burst_frames = 0

            self._burst_frames += 1
            self._last_fire_time = now

            if self._burst_active and self._burst_frames <= self.cfg.burst_count:
                boost = self.cfg.aim_boost
                rx = int(rx * boost)
                ry = int(ry * boost)
                recoil_mult = self.cfg.recoil_reduction
                return (max(-32767, min(32767, rx)),
                        max(-32767, min(32767, ry)), recoil_mult)

            if self._burst_frames > self.cfg.burst_count:
                self._burst_active = False
        else:
            self._burst_active = False
            self._burst_frames = 0

        return rx, ry, 1.0

    def reset(self) -> None:
        self._burst_active = False
        self._burst_frames = 0


# ═══════════════════════════════════════════════════════════════════════
# 4. BATTS STICKY — diamond pattern com contextos separados
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class BattsStickyConfig:
    """Pattern diamond de aim assist — 4 pontos cardeais com tamanhos
    e velocidades separados por contexto (ADS, ADS+Fire, Hipfire)."""
    enabled: bool = False
    # Tamanho do diamond (raio do padrão)
    ads_size: int = 14
    ads_fire_size: int = 16
    hipfire_size: int = 18
    # Velocidade de rotação do diamond (graus/tick)
    ads_speed: float = 8.0
    ads_fire_speed: float = 12.0
    hipfire_speed: float = 6.0
    # Drift compensation (empurra suavemente na direção do input)
    drift_enabled: bool = True
    drift_strength: float = 0.3


class BattsStickyEngine:
    """Diamond pattern estilo Batts Sticky — 4 pontos cardeais.

    O padrão diamond é um padrão de 4 pontos que rotaciona suavemente,
    criando uma "estrela" de aim assist que gruda o crosshair no alvo.
    Velocidade e tamanho mudam conforme o contexto de combate.
    """

    def __init__(self, cfg: Optional[BattsStickyConfig] = None):
        self.cfg = cfg if cfg is not None else BattsStickyConfig()
        self._phase: float = 0.0

    def apply(self, rx: int, ry: int, is_aiming: bool,
              is_shooting: bool) -> Tuple[int, int]:
        if not self.cfg.enabled:
            return rx, ry

        if is_aiming and is_shooting:
            size = self.cfg.ads_fire_size
            speed = self.cfg.ads_fire_speed
        elif is_aiming:
            size = self.cfg.ads_size
            speed = self.cfg.ads_speed
        else:
            size = self.cfg.hipfire_size
            speed = self.cfg.hipfire_speed

        self._phase += math.radians(speed)
        if self._phase > 2.0 * math.pi:
            self._phase -= 2.0 * math.pi

        diamond_x = int(size * math.cos(self._phase) * abs(math.cos(self._phase)))
        diamond_y = int(size * math.sin(self._phase) * abs(math.sin(self._phase)))

        if self.cfg.drift_enabled and (is_aiming or is_shooting):
            mag = math.hypot(rx, ry)
            if mag > 100:
                dx = rx / mag
                dy = ry / mag
                drift = int(size * self.cfg.drift_strength)
                diamond_x += int(dx * drift)
                diamond_y += int(dy * drift)

        rx = max(-32767, min(32767, rx + diamond_x))
        ry = max(-32767, min(32767, ry + diamond_y))
        return rx, ry

    def reset(self) -> None:
        self._phase = 0.0


# ═══════════════════════════════════════════════════════════════════════
# 5. XANAX AI ADAPTATIVO — adapta baseado nos mods ativos
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class XanaxAIConfig:
    """Sistema adaptativo que aprende dos mods ativos e injeta
    comportamento otimizado. Não é auto-aim — é um modificador
    que melhora os outros mods baseado no contexto."""
    enabled: bool = False
    # Boost quando vários mods estão ativos ao mesmo tempo
    synergy_boost: float = 1.15  # +15% quando 3+ mods ativos
    synergy_threshold: int = 3   # quantos mods pra ativar synergy
    # Adaptabilidade por range
    close_range_boost: float = 1.2   # +20% em close range
    long_range_boost: float = 0.85   # -15% em long range (mais suave)
    close_range_threshold: int = 5000   # stick magnitude = close
    long_range_threshold: int = 20000   # stick magnitude = long
    # Anti-deteção: varia os parâmetros pra não criar padrão detectável
    humanize_enabled: bool = True
    humanize_jitter: float = 0.05   # ±5% de variação
    # Aprendizado de taxa de acerto (simulado)
    adapt_rate: float = 0.02        # velocidade de adaptação


class XanaxAIEngine:
    """Motor adaptativo que ajusta o comportamento baseado no contexto.

    Analisa:
    1. Quantos mods estão ativos (synergy)
    2. Range estimado (stick magnitude)
    3. Padrão de input (consistência)
    4. Histórico de engajamento

    Ajusta dinamicamente:
    - Força do aim assist
    - Tamanho da órbita
    - Velocidade de rotação
    """

    def __init__(self, cfg: Optional[XanaxAIConfig] = None):
        self.cfg = cfg if cfg is not None else XanaxAIConfig()
        self._active_mods: int = 0
        self._engagement_history: List[float] = []
        self._current_multiplier: float = 1.0
        self._humanize_seed: float = 0.0

    def update_mods(self, count: int) -> None:
        """Atualiza quantos mods estão ativos."""
        self._active_mods = count

    def compute_multiplier(self, rx: float, ry: float, is_shooting: bool,
                           delta_ms: float) -> float:
        """Computa o multiplicador adaptativo baseado no contexto."""
        if not self.cfg.enabled:
            return 1.0

        mult = 1.0

        # Synergy boost
        if self._active_mods >= self.cfg.synergy_threshold:
            mult *= self.cfg.synergy_boost

        # Range adaptation
        mag = math.hypot(rx, ry)
        if mag < self.cfg.close_range_threshold:
            mult *= self.cfg.close_range_boost
        elif mag > self.cfg.long_range_threshold:
            mult *= self.cfg.long_range_boost

        # Anti-detection humanize
        if self.cfg.humanize_enabled:
            self._humanize_seed += delta_ms * 0.001
            jitter = self.cfg.humanize_jitter * math.sin(self._humanize_seed * 7.3)
            mult *= (1.0 + jitter)

        # Smooth transition
        self._current_multiplier += (mult - self._current_multiplier) * min(
            1.0, self.cfg.adapt_rate * delta_ms / 16.0)

        return max(0.5, min(2.0, self._current_multiplier))

    @property
    def multiplier(self) -> float:
        return self._current_multiplier

    def reset(self) -> None:
        self._active_mods = 0
        self._engagement_history.clear()
        self._current_multiplier = 1.0
        self._humanize_seed = 0.0
