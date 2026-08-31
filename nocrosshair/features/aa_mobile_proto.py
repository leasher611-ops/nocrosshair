#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Protótipo do Aim Assist nativo do Fortnite Mobile, recriado do zero para
controller, sem visão computacional (ver RESEARCH_FORTNITE_MOBILE_AIMLOCK.md
e RESEARCH_CONTROLLER_AIMASSIST_SCRIPTS.md).

Modelo do FM AA (replicado fielmente):
  - Slider de força 0–100% (padrão 100) que governa os dois sistemas.
  - Sistema 1 — Slowdown "sticky": com o retículo perto do alvo (zona de
    atração), a velocidade do stick é reduzida proporcionalmente à
    proximidade (mais perto = mais devagar).
  - Sistema 2 — Rotational assist: só ativa COM INPUT do jogador e dentro
    da zona; gira a câmera na direção do alvo. Para sem input.
  - Camadas camera/aim com histerese (movimento grosso vs. fino).
  - Ramp-up suave e easing "mais humano" (v31.20): sem puxadas robóticas.
  - Auto-Fire é exclusivo mobile → fora do escopo. Gyro desativa AA → fora.

Sem leitura de memória/tela, a "proximidade do alvo" é proxiada pelo input:
  - Input pequeno (zona de mira fina) = já está perto do alvo/AA nativo
    engajado → slowdown atua mais forte.
  - Direção do rotational = direção em que o jogador já está empurrando o
    stick (estilo Zen/console scripts: re-disparar o AA nativo do jogo).
"""

import math
import random
from dataclasses import dataclass
from typing import Tuple, Optional


@dataclass
class MobileAAProtoConfig:
    strength_slider: int = 100
    zone: int = 6000
    slow_curve: float = 0.8
    rotational_enabled: bool = True
    rotational_strength: float = 1.0
    input_gate: int = 800
    rotation_cap: int = 500
    ads_multiplier: float = 1.0
    ramp_up_ms: float = 150.0
    ramp_down_ms: float = 100.0
    camera_threshold: int = 18000
    camera_exit: int = 14000
    move_boost: float = 1.0
    # Quanto do slowdown é MANTIDO na layer de câmera (0.5 = metade, 1.0 = igual
    # ao aim layer). Mais grudante = mais alto, sem cortar totalmente o giro.
    camera_slow_keep: float = 0.5
    # Piso do pull rotacional fora da zona: aim layer e camera layer.
    # 1.0 = força total mesmo a full stick; 0.0 = morre fora da zona.
    aim_pull_floor: float = 0.35
    camera_pull_floor: float = 0.5
    humanize: bool = True
    easing_tau_ms: float = 24.0
    tweak_mode: bool = False
    # Boost extra na camera layer (stick > threshold). 1.05 = +5%.
    camera_layer_boost: float = 1.0
    seed: Optional[int] = None


class FortniteMobileAAProto:

    def __init__(self, cfg: Optional[MobileAAProtoConfig] = None):
        self.cfg = cfg if cfg is not None else MobileAAProtoConfig()
        self._in_camera: bool = False
        self._rot_blend: float = 0.0
        self._ease_rx: float = 0.0
        self._ease_ry: float = 0.0
        self._rng = random.Random(self.cfg.seed)

    @property
    def in_camera_layer(self) -> bool:
        return self._in_camera

    @property
    def rotation_engaged(self) -> bool:
        return self._rot_blend > 0.0

    def reset(self) -> None:
        self._in_camera = False
        self._rot_blend = 0.0
        self._ease_rx = 0.0
        self._ease_ry = 0.0
        self._rng = random.Random(self.cfg.seed)

    def _strength(self) -> float:
        slider = max(0, min(100, self.cfg.strength_slider))
        return slider / 100.0

    def _detect_layer(self, mag: float) -> str:
        if self._in_camera:
            if mag < self.cfg.camera_exit:
                self._in_camera = False
                return "aim"
            return "camera"
        if mag > self.cfg.camera_threshold:
            self._in_camera = True
            return "camera"
        return "aim"

    def process(self, rx: float, ry: float, is_shooting: bool,
                is_aiming: bool, is_moving: bool, delta_ms: float) -> Tuple[float, float]:
        strength = self._strength()
        if strength <= 0 or not (is_aiming or is_shooting):
            self._rot_blend = max(0.0, self._rot_blend - delta_ms / max(1.0, self.cfg.ramp_down_ms))
            return self._clamp((rx, ry))

        if rx == 0.0 and ry == 0.0:
            self._rot_blend = 0.0
            self._ease_rx = 0.0
            self._ease_ry = 0.0
            return (0.0, 0.0)

        mag = math.sqrt(rx * rx + ry * ry)
        layer = self._detect_layer(mag)
        zone_factor = min(mag / max(self.cfg.zone, 1), 0.85 if self.cfg.tweak_mode else 1.0)

        slow = 1.0 - self.cfg.slow_curve * strength * (1.0 - zone_factor)
        if self.cfg.tweak_mode:
            slow = max(slow, 0.55)
        if layer == "camera":
            slow = 1.0 - (1.0 - slow) * self.cfg.camera_slow_keep
        out_rx = rx * slow
        out_ry = ry * slow

        pull = 0.0
        effective_gate = max(100, self.cfg.input_gate // 3) if self.cfg.tweak_mode else self.cfg.input_gate
        if self.cfg.rotational_enabled and mag >= effective_gate:
            engaged = True
            self._rot_blend = min(1.0, self._rot_blend + delta_ms / max(1.0, self.cfg.ramp_up_ms))
            boost = 1.0 + max(0.0, self.cfg.move_boost - 1.0) * (1.0 if is_moving else 0.0)
            near = max(0.0, 1.0 - mag / max(self.cfg.zone, 1.0))
            floor = self.cfg.camera_pull_floor if layer == "camera" else self.cfg.aim_pull_floor
            taper = max(0.0, 1.0 - mag / max(self.cfg.camera_threshold * 2.0, 1.0))
            pull = (self.cfg.rotation_cap * strength * (floor + (1.0 - floor) * near)
                    * self._rot_blend * self.cfg.ads_multiplier * boost
                    * self.cfg.rotational_strength) * taper
            if layer == "camera":
                pull *= self.cfg.camera_layer_boost
            if mag > 0:
                out_rx += (rx / mag) * pull
                out_ry += (ry / mag) * pull
        else:
            engaged = False
            self._rot_blend = max(0.0, self._rot_blend - delta_ms / max(1.0, self.cfg.ramp_down_ms))

        if pull > 0 and self.cfg.humanize:
            noise = 30.0 * self._rng.uniform(-1.0, 1.0)
            out_rx += noise
            out_ry += noise

        if slow == 1.0 and pull <= 0:
            return self._clamp((rx, ry))

        return self._clamp(self._ease(out_rx, out_ry, delta_ms))

    def _ease(self, rx: float, ry: float, delta_ms: float) -> Tuple[float, float]:
        k = 1.0 - math.exp(-delta_ms / max(self.cfg.easing_tau_ms, 1.0))
        self._ease_rx += (rx - self._ease_rx) * k
        self._ease_ry += (ry - self._ease_ry) * k
        return self._ease_rx, self._ease_ry

    @staticmethod
    def _clamp(vals: Tuple[float, float]) -> Tuple[float, float]:
        return (max(-32767.0, min(32767.0, vals[0])),
                max(-32767.0, min(32767.0, vals[1])))


class MobileAATestbed:

    def __init__(self, cfg: Optional[MobileAAProtoConfig] = None):
        self.cfg = cfg if cfg is not None else MobileAAProtoConfig()
        self.engine = FortniteMobileAAProto(self.cfg)

    def simulate(self, rx: float, ry: float, is_shooting: bool = True,
                 is_aiming: bool = True, is_moving: bool = True,
                 delta_ms: float = 16.0) -> Tuple[float, float]:
        return self.engine.process(rx, ry, is_shooting, is_aiming, is_moving, delta_ms)
