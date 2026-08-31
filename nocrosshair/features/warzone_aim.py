#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sistemas de Aim inspirados no Warzone — Vibração L3, Aim Buffers puros,
Rapid Fire agressivo. Modo puro, sem humanização.

Inspirado nos scripts premium do Warzone (Exodus V3, Panda Aim V8,
Rocket Aim, Zen King) mas adaptado para Fortnite.
"""

import math
import time
from dataclasses import dataclass
from typing import Optional, Tuple, List


# ═══════════════════════════════════════════════════════════════════════
# 1. VIBRAÇÃO L3 — mantém aim assist ativo via vibração do controller
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class VibrationL3Config:
    """Vibração do controller cria micro-movimentos no L3, mantendo
    o aim assist nativo do Fortnite sempre ativo. O AA do Fortnite
    só liga quando o stick está em movimento — a vibração gera esse
    movimento automaticamente sem o jogador precisar mexer o stick."""
    enabled: bool = False
    intensity: int = 50         # intensidade da vibração (0-100)
    frequency: float = 30.0     # frequência da oscilação (Hz)
    amplitude: int = 8          # amplitude do micro-movimento no L3
    gate: int = 200             # magnitude mínima do stick pra ativar
    ads_only: bool = False      # só ativa em ADS
    fire_only: bool = False     # só ativa ao atirar


class VibrationL3Engine:
    """Gera micro-movimentos no L3 via vibração pra manter AA ativo.

    O segredo dos scripts Warzone: o AA do Fortnite só reage quando
    o stick tá em movimento. A vibração cria esse movimento artificial
    sem o jogador precisar fazer nada. Resultado: aim assist sempre
    grudento, mesmo com stick parado.
    """

    def __init__(self, cfg: Optional[VibrationL3Config] = None):
        self.cfg = cfg if cfg is not None else VibrationL3Config()
        self._phase: float = 0.0
        self._vibration_active: bool = False
        self._last_vibration_time: float = 0.0

    def apply(self, lx: int, ly: int, rx: int, ry: int,
              is_aiming: bool, is_shooting: bool,
              delta_ms: float) -> Tuple[int, int, bool]:
        """Retorna (lx, ly, vibration_on)."""
        if not self.cfg.enabled:
            return lx, ly, False

        # Checa condições de ativação
        if self.cfg.ads_only and not is_aiming:
            return lx, ly, False
        if self.cfg.fire_only and not is_shooting:
            return lx, ly, False

        # Calcula vibração
        self._phase += 2.0 * math.pi * self.cfg.frequency * (delta_ms / 1000.0)
        if self._phase > 2.0 * math.pi:
            self._phase -= 2.0 * math.pi

        # Micro-movimento sinusoidal no L3
        micro_x = int(self.cfg.amplitude * math.sin(self._phase))
        micro_y = int(self.cfg.amplitude * math.cos(self._phase * 0.7))

        # Soma com input existente (relative deflection)
        lx = max(-32767, min(32767, lx + micro_x))
        ly = max(-32767, min(32767, ly + micro_y))

        self._vibration_active = True
        self._last_vibration_time = time.monotonic()

        return lx, ly, True

    def get_vibration_values(self) -> Tuple[int, int]:
        """Retorna (left_motor, right_motor) pra enviar ao controller."""
        if not self._vibration_active:
            return 0, 0
        left = int(self.cfg.intensity * 2.55)  # 0-255
        right = int(self.cfg.intensity * 2.55 * 0.8)  # um pouco mais fraco
        return left, right

    def stop(self) -> None:
        self._vibration_active = False
        self._phase = 0.0

    @property
    def active(self) -> bool:
        return self._vibration_active


# ═══════════════════════════════════════════════════════════════════════
# 2. WARZONE AIM BUFFER — tracking agressivo + sticky puro
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class WarzoneAimBufferConfig:
    """Buffer de aim estilo Warzone — mantém o stick "grudento" no alvo
    com tracking agressivo. Modo puro: sem suavização, sem jitter,
    sem humanização. O stick pica no alvo e fica lá."""
    enabled: bool = False
    # Tracking: segue o alvo com força bruta
    tracking_enabled: bool = True
    tracking_strength: float = 2.0   # multiplicador de tracking
    tracking_radius: int = 5000      # raio de detecção (unidades stick)
    # Sticky: gruda quando perto do alvo
    sticky_enabled: bool = True
    sticky_strength: float = 1.8     # multiplicador de stickiness
    sticky_radius: int = 3000        # raio de grude
    # Rotation: órbita agressiva quando locked
    rotation_enabled: bool = True
    rotation_radius: int = 12        # raio da órbita
    rotation_speed: float = 15.0     # velocidade (graus/tick)
    # Boost: multiplicador no tiro
    fire_boost: float = 1.4          # +40% quando atirando
    # Activation
    ads_only: bool = False           # só em ADS


class WarzoneAimBufferEngine:
    """Aim buffer puro estilo Warzone — tracking + sticky + rotation.

    Diferente do aim assist suave do Fortnite, este é agressivo:
    - Tracking: puxa o stick na direção do "alvo" (proxy input)
    - Sticky: quando perto, gruda com força multiplicada
    - Rotation: órbita quando locked (mantém AA nativo re-disparando)
    - Fire Boost: multiplica tudo quando atirando

    Sem jitter, sem humanização, sem suavização — modo puro.
    """

    def __init__(self, cfg: Optional[WarzoneAimBufferConfig] = None):
        self.cfg = cfg if cfg is not None else WarzoneAimBufferConfig()
        self._rotation_phase: float = 0.0
        self._locked: bool = False
        self._lock_frames: int = 0

    def apply(self, rx: int, ry: int, is_aiming: bool,
              is_shooting: bool, delta_ms: float) -> Tuple[int, int]:
        if not self.cfg.enabled:
            return rx, ry

        mag = math.hypot(rx, ry)

        # Detecta se está "locked" (stick parado ou movimento pequeno)
        if mag < self.cfg.sticky_radius:
            self._lock_frames += 1
            if self._lock_frames > 5:
                self._locked = True
        else:
            self._lock_frames = 0
            self._locked = False

        # Tracking: puxa na direção do input quando há movimento
        if self.cfg.tracking_enabled and mag > 500:
            track_mult = self.cfg.tracking_strength
            if is_shooting:
                track_mult *= self.cfg.fire_boost
            rx = max(-32767, min(32767, int(rx * track_mult)))
            ry = max(-32767, min(32767, int(ry * track_mult)))

        # Sticky: gruda quando perto do alvo
        if self.cfg.sticky_enabled and self._locked:
            sticky_mult = self.cfg.sticky_strength
            if is_shooting:
                sticky_mult *= self.cfg.fire_boost
            # Mantém a direção mas amplifica
            if mag > 0:
                dx = rx / max(mag, 1.0)
                dy = ry / max(mag, 1.0)
                new_mag = min(mag * sticky_mult, 32767.0)
                rx = int(dx * new_mag)
                ry = int(dy * new_mag)

        # Rotation: órbita quando locked (mantém AA re-disparando)
        if self.cfg.rotation_enabled and self._locked and is_shooting:
            self._rotation_phase += math.radians(self.cfg.rotation_speed) * (delta_ms / 16.0)
            if self._rotation_phase > 2.0 * math.pi:
                self._rotation_phase -= 2.0 * math.pi
            rot_x = int(self.cfg.rotation_radius * math.cos(self._rotation_phase))
            rot_y = int(self.cfg.rotation_radius * math.sin(self._rotation_phase))
            rx = max(-32767, min(32767, rx + rot_x))
            ry = max(-32767, min(32767, ry + rot_y))

        return max(-32767, min(32767, rx)), max(-32767, min(32767, ry))

    def reset(self) -> None:
        self._rotation_phase = 0.0
        self._locked = False
        self._lock_frames = 0


# ═══════════════════════════════════════════════════════════════════════
# 3. RAPID FIRE PURO — sem limites, modo agressivo
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class RapidFirePureConfig:
    """Rapid Fire puro — alterna o gatilho em alta frequência sem
    nenhuma limitação. Modo Warzone: cadência máxima, zero pause."""
    enabled: bool = False
    speed: int = 80              # disparos por segundo (Hz) — modo puro
    hold_ms: int = 5             # tempo pressionado por ciclo
    release_ms: int = 5          # tempo liberado por ciclo
    burst_mode: bool = False     # modo rajada (3 tiros + pausa)
    burst_count: int = 3         # tiros por rajada
    burst_pause_ms: int = 100    # pausa entre rajadas
    trigger_button: str = "RT"   # gatilho (RT, R2)
    activate_only_ads: bool = False  # só ativa em ADS
    # Anti-recoil integrado
    anti_recoil_enabled: bool = True
    anti_recoil_strength: float = 1.2  # multiplicador de recoil reduction


class RapidFirePureEngine:
    """Rapid Fire puro estilo Warzone — cadência máxima sem limites.

    Modo normal: alterna RT/R2 em alta frequência.
    Modo burst: 3 tiros + pausa (compensa bloom do Fortnite).
    Anti-recoil integrado: puxa stick pra baixo durante o tiro.
    """

    def __init__(self, cfg: Optional[RapidFirePureConfig] = None):
        self.cfg = cfg if cfg is not None else RapidFirePureConfig()
        self._active: bool = False
        self._cycle_start: float = 0.0
        self._burst_count: int = 0
        self._burst_pausing: bool = False
        self._burst_pause_start: float = 0.0

    def process(self, rt: int, is_shooting: bool, is_aiming: bool,
                delta_ms: float) -> Tuple[int, int, bool]:
        """Retorna (rt_out, recoil_ry, active)."""
        if not self.cfg.enabled:
            return rt, 0, False

        if self.cfg.activate_only_ads and not is_aiming:
            return rt, 0, False

        now = time.monotonic()

        # Burst mode
        if self.cfg.burst_mode:
            return self._process_burst(rt, is_shooting, now, delta_ms)

        # Rapid fire normal
        if is_shooting:
            if not self._active:
                self._active = True
                self._cycle_start = now

            cycle_time = (self.cfg.hold_ms + self.cfg.release_ms) / 1000.0
            elapsed = now - self._cycle_start
            position_in_cycle = elapsed % cycle_time

            if position_in_cycle < self.cfg.hold_ms / 1000.0:
                # Fase de hold — gatilho pressionado
                recoil = int(-100 * self.cfg.anti_recoil_strength) if self.cfg.anti_recoil_enabled else 0
                return 32767, recoil, True
            else:
                # Fase de release — gatilho solto
                return 0, 0, True
        else:
            self._active = False
            return 0, 0, False

    def _process_burst(self, rt: int, is_shooting: bool,
                       now: float, delta_ms: float) -> Tuple[int, int, bool]:
        if not is_shooting:
            self._burst_count = 0
            self._burst_pausing = False
            self._active = False
            return 0, 0, False

        if not self._active:
            self._active = True
            self._burst_count = 0
            self._burst_pausing = False
            self._cycle_start = now

        # Pausa entre rajadas
        if self._burst_pausing:
            if (now - self._burst_pause_start) * 1000.0 < self.cfg.burst_pause_ms:
                return 0, 0, True
            self._burst_pausing = False
            self._burst_count = 0
            self._cycle_start = now

        # Tiros da rajada
        cycle_time = (self.cfg.hold_ms + self.cfg.release_ms) / 1000.0
        elapsed = now - self._cycle_start
        position_in_cycle = elapsed % cycle_time

        if position_in_cycle < self.cfg.hold_ms / 1000.0:
            recoil = int(-100 * self.cfg.anti_recoil_strength) if self.cfg.anti_recoil_enabled else 0
            return 32767, recoil, True
        else:
            # Verifica se completou um tiro
            shot_index = int(elapsed / cycle_time)
            if shot_index > self._burst_count:
                self._burst_count = shot_index
                if self._burst_count >= self.cfg.burst_count:
                    self._burst_pausing = True
                    self._burst_pause_start = now
            return 0, 0, True

    def reset(self) -> None:
        self._active = False
        self._burst_count = 0
        self._burst_pausing = False


# ═══════════════════════════════════════════════════════════════════════
# 4. AIM BUFFER STACK — combina todos os buffers
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class AimBufferStackConfig:
    """Stack de aim buffers — combina vibração L3, Warzone aim buffer,
    e rapid fire num sistema unificado. Modo puro: tudo no máximo,
    sem limitações, sem humanização."""
    vibration: VibrationL3Config = None
    warzone_buffer: WarzoneAimBufferConfig = None
    rapid_fire: RapidFirePureConfig = None

    def __post_init__(self):
        if self.vibration is None:
            self.vibration = VibrationL3Config()
        if self.warzone_buffer is None:
            self.warzone_buffer = WarzoneAimBufferConfig()
        if self.rapid_fire is None:
            self.rapid_fire = RapidFirePureConfig()


class AimBufferStackEngine:
    """Stack unificado de aim buffers — vibração + tracking + rapid fire.

    Combina todos os sistemas num pipeline único:
    1. Vibração L3 mantém AA ativo
    2. Warzone aim buffer adiciona tracking/sticky/rotation
    3. Rapid fire processa o gatilho
    """

    def __init__(self, cfg: Optional[AimBufferStackConfig] = None):
        self.cfg = cfg if cfg is not None else AimBufferStackConfig()
        self.vibration_engine = VibrationL3Engine(self.cfg.vibration)
        self.warzone_engine = WarzoneAimBufferEngine(self.cfg.warzone_buffer)
        self.rapid_engine = RapidFirePureEngine(self.cfg.rapid_fire)

    def apply(self, lx: int, ly: int, rx: int, ry: int,
              is_aiming: bool, is_shooting: bool,
              delta_ms: float) -> Tuple[int, int, int, int, bool]:
        """Retorna (lx, ly, rx, ry, vibration_on)."""
        # 1. Vibração L3
        lx, ly, vib_on = self.vibration_engine.apply(
            lx, ly, rx, ry, is_aiming, is_shooting, delta_ms)

        # 2. Warzone aim buffer
        rx, ry = self.warzone_engine.apply(
            rx, ry, is_aiming, is_shooting, delta_ms)

        return lx, ly, rx, ry, vib_on

    def process_rapid_fire(self, rt: int, is_shooting: bool,
                           is_aiming: bool, delta_ms: float) -> Tuple[int, int, bool]:
        """Retorna (rt_out, recoil_ry, active)."""
        return self.rapid_engine.process(rt, is_shooting, is_aiming, delta_ms)

    def reset(self) -> None:
        self.vibration_engine.stop()
        self.warzone_engine.reset()
        self.rapid_engine.reset()
