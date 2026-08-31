"""Head Snap + Tracking Preditivo — integrado ao Silent Aim QT.

Duas features que rodam no flush contínuo (junto com o silent_qt):

HEAD SNAP:
    No primeiro tiro em ADS, micro-puxada vertical suave em direção à
    cabeça. Detecta "engajamento" pelo padrão de input (stick pequeno +
    ADS + atirando = mirando em alguém). Usa curva ease-out para não
    parecer um snap robótico.

TRACKING PREDITIVO (lead):
    Antecipa o movimento do alvo baseado na direção do movimento do
    mouse. Filtro alfa-beta: suaviza velocidade/aceleração, só aplica
    lead quando a direção se mantém consistente (evita predizer jitter),
    adianta com lead = v·T + ½·a·T², limita por max_lead.
"""

from __future__ import annotations

import math
import time
from typing import Optional, Tuple


class HeadSnapQT:
    """Head snap adaptado para o caminho KBM + silent_qt."""

    def __init__(self):
        self._snap_active: bool = False
        self._snap_start: float = 0.0
        self._last_snap_time: float = 0.0
        self._engagement_frames: int = 0
        self._last_shot_time: float = 0.0

        # Config (setada pelo pipeline)
        self.enabled: bool = True
        self.strength: int = 80        # 0-100 (altura do snap)
        self.height: int = 900         # unidades evdev de subida
        self.duration_ms: int = 180
        self.cooldown_ms: int = 200
        self.ads_only: bool = True

    def apply(
        self,
        rx: float,
        ry: float,
        is_aiming: bool,
        is_shooting: bool,
        is_moving: bool,
        now: float,
        delta_ms: float,
        input_rx: Optional[float] = None,
        input_ry: Optional[float] = None,
    ) -> Tuple[float, float]:
        if not self.enabled or self.strength <= 0:
            return rx, ry
        if self.ads_only and not is_aiming:
            self._snap_active = False
            self._engagement_frames = 0
            return rx, ry
        if is_moving:
            return rx, ry

        # Detecta engajamento pelo INPUT ORIGINAL do jogador (não pelo
        # output oscilado do silent_qt — a oscilação confunde o detector).
        # Engaja no ADS PARADO (stick pequeno) — o snap dispara quando o
        # tiro começa. Antes exigia is_shooting, então nunca engajava
        # antes do primeiro tiro.
        mag_rx = input_rx if input_rx is not None else rx
        mag_ry = input_ry if input_ry is not None else ry
        mag = math.hypot(mag_rx, mag_ry)
        if is_aiming and mag < 8000:
            self._engagement_frames = min(self._engagement_frames + 1, 30)
        else:
            self._engagement_frames = max(self._engagement_frames - 2, 0)

        # Snap na borda do tiro (primeiro shot do engajamento)
        fire_edge = is_shooting and (now - self._last_shot_time) * 1000.0 < 40
        if is_shooting:
            self._last_shot_time = now

        should_snap = (self._engagement_frames >= 5 and fire_edge)
        if should_snap and not self._snap_active:
            if (now - self._last_snap_time) * 1000.0 >= self.cooldown_ms:
                self._snap_active = True
                self._snap_start = now

        if self._snap_active:
            elapsed_ms = (now - self._snap_start) * 1000.0
            if elapsed_ms >= self.duration_ms:
                self._snap_active = False
            else:
                t = elapsed_ms / max(1.0, self.duration_ms)
                # Ease-out: sobe rápido no início, suaviza no fim
                ease = 1.0 - (1.0 - t) ** 2
                snap_offset = self.height * (self.strength / 100.0) * ease
                # Decai na segunda metade (volta ao centro suavemente)
                if t > 0.5:
                    decay = 1.0 - (t - 0.5) / 0.5
                    snap_offset *= max(0.0, decay)
                ry_out = ry + snap_offset
                self._last_snap_time = now
                return rx, ry_out

        return rx, ry

    def reset(self) -> None:
        self._snap_active = False
        self._engagement_frames = 0


class PredictiveTrackQT:
    """Tracking preditivo (lead) adaptado para KBM + silent_qt.

    Usa a velocidade do mouse (rx/ry delta) como proxy da velocidade do
    alvo. Só aplica lead com direção consistente por N frames.
    """

    def __init__(self):
        self._prev_x: Optional[float] = None
        self._prev_y: Optional[float] = None
        self._vx: float = 0.0
        self._vy: float = 0.0
        self._ax: float = 0.0
        self._ay: float = 0.0
        self._dir_x: int = 0
        self._dir_y: int = 0
        self._streak: int = 0

        # Config (setada pelo pipeline)
        self.enabled: bool = True
        self.vel_alpha: float = 0.15
        self.accel_alpha: float = 0.06
        self.lead_horizon_ms: float = 40.0
        self.min_speed: float = 200.0
        self.max_lead: float = 3000.0
        self.consistency: int = 3
        self.direction_blend: float = 0.7
        # Modo KBM: o input é DELTA (movimento do mouse), não posição.
        # O lead escala por frames (não por ms) — lead = v * horizon_frames.
        self.kbm_mode: bool = True
        self.lead_frames: float = 6.0

    def predict(self, rx: float, ry: float, dt_ms: float) -> Tuple[float, float]:
        if not self.enabled:
            return 0.0, 0.0

        dt = max(float(dt_ms), 1.0)
        rx_f, ry_f = float(rx), float(ry)
        if self._prev_x is None:
            self._prev_x, self._prev_y = rx_f, ry_f
            return 0.0, 0.0

        # Input parado: nada de lead
        if math.hypot(rx_f, ry_f) < 100.0:
            self._prev_x, self._prev_y = rx_f, ry_f
            self._streak = 0
            self._dir_x = self._dir_y = 0
            return 0.0, 0.0

        raw_vx = (rx_f - self._prev_x) / dt
        raw_vy = (ry_f - self._prev_y) / dt
        self._prev_x, self._prev_y = rx_f, ry_f

        raw_ax = (raw_vx - self._vx) / dt
        raw_ay = (raw_vy - self._vy) / dt
        self._ax += self.accel_alpha * (raw_ax - self._ax)
        self._ay += self.accel_alpha * (raw_ay - self._ay)
        self._vx += self.vel_alpha * (raw_vx - self._vx)
        self._vy += self.vel_alpha * (raw_vy - self._vy)

        speed = math.hypot(self._vx, self._vy)
        if speed < self.min_speed:
            self._streak = 0
            self._dir_x = self._dir_y = 0
            return 0.0, 0.0

        dx = 1 if self._vx >= 0 else -1
        dy = 1 if self._vy >= 0 else -1
        if dx == self._dir_x and dy == self._dir_y:
            self._streak += 1
        else:
            self._streak = 1
        self._dir_x, self._dir_y = dx, dy
        if self._streak < self.consistency:
            return 0.0, 0.0

        T = self.lead_horizon_ms / 1000.0
        if self.kbm_mode:
            # KBM: _vx já é o delta médio por ms. O lead é quanto o alvo
            # vai andar nos próximos N frames na direção atual:
            # lead = v_delta_per_ms * (frame_interval * lead_frames)
            # frame_interval ~16ms, lead_frames 6 → ~96ms de antecipação.
            lead_x = self._vx * (16.0 * self.lead_frames)
            lead_y = self._vy * (16.0 * self.lead_frames)
        else:
            lead_x = self._vx * T + 0.5 * self._ax * T * T
            lead_y = self._vy * T + 0.5 * self._ay * T * T

        # Limita o lead (anti-overshoot)
        lead_mag = math.hypot(lead_x, lead_y)
        if lead_mag > self.max_lead:
            scale = self.max_lead / lead_mag
            lead_x *= scale
            lead_y *= scale

        # Blend com a direção dominante (mais estável)
        if abs(self._vx) > abs(self._vy):
            lead_y *= self.direction_blend
        else:
            lead_x *= self.direction_blend

        return lead_x, lead_y

    def reset(self) -> None:
        self._prev_x = None
        self._prev_y = None
        self._vx = self._vy = 0.0
        self._ax = self._ay = 0.0
        self._dir_x = self._dir_y = 0
        self._streak = 0
