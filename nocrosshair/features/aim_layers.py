"""Aim Assist em Camadas — arquitetura estilo Cronus Zen.

Cada camada é independente: toggle próprio, intensidade própria, gate próprio.
O output de uma camada entra como input da próxima.

Camadas:
  1. Slowdown + Rotational (AA básico)
  2. Aim Lock + Silent Aim (só ADS — trava + oscila)
  3. Camera: Silent Hit (só hip fire — oscilação sem mirar)
  4. Track + Snap (momentum + headshot)
  5. Sticky + Magnetic (persistência ao parar)
"""

from __future__ import annotations

import math
import time
from enum import Enum
from typing import Optional, Tuple


class LayerID(Enum):
    SLOWDOWN = "slowdown"
    AIM_LOCK_SILENT = "aim_lock_silent"
    CAMERA_HIT = "camera_hit"
    TRACK = "track"
    STICKY = "sticky"
    ROTATIONAL_BOOST = "rotational_boost"
    FRICTION = "friction"
    MAGNETIC_PULL = "magnetic_pull"


class AimLayer:
    """Base abstrata para uma camada de aim assist."""

    layer_id: LayerID

    def __init__(self):
        self.enabled: bool = True
        self.intensity: float = 1.0
        self._gate_smooth: float = 1.0

    def process(self, rx: float, ry: float, ctx: "LayerContext") -> Tuple[float, float]:
        raise NotImplementedError

    def reset(self):
        self._gate_smooth = 1.0

    def _compute_gate(self, mag: float, gate_low: float, gate_high: float) -> float:
        if mag <= gate_low:
            gate = 1.0
        elif mag >= gate_high:
            gate = 0.0
        else:
            gate = 1.0 - (mag - gate_low) / (gate_high - gate_low)
        self._gate_smooth = self._gate_smooth * 0.5 + gate * 0.5
        return self._gate_smooth


class LayerContext:
    """Contexto compartilhado entre todas as camadas."""

    def __init__(self):
        self.delta_ms: float = 16.0
        self.now: float = 0.0
        self.is_aiming: bool = False
        self.is_shooting: bool = False
        self.is_moving: bool = False
        self.raw_rx: float = 0.0
        self.raw_ry: float = 0.0


# ═══════════════════════════════════════════════════════════════════════
# LAYER 1: Slowdown + Rotational
# ═══════════════════════════════════════════════════════════════════════

class SlowdownLayer(AimLayer):
    """AA básico: reduz velocidade do stick quando perto do alvo (slowdown)
    e reforça a direção do movimento (rotational).
    """

    layer_id = LayerID.SLOWDOWN

    def __init__(self):
        super().__init__()
        self.zone: int = 6000
        self.strength: int = 8000
        self.rotational_enabled: bool = True
        self.rotational_strength: float = 0.5
        self.ads_multiplier: float = 1.2
        self.humanize: bool = True

    def process(self, rx: float, ry: float, ctx: LayerContext) -> Tuple[float, float]:
        if not self.enabled or self.zone == 0:
            return rx, ry

        mag = math.sqrt(rx * rx + ry * ry)
        if mag == 0:
            return rx, ry

        zone_factor = min(mag / max(self.zone, 1), 1.0)
        effective_strength = min(self.strength, 12000)
        slowdown = max(0.40, 1.0 - (effective_strength / 10000.0) * (1.0 - zone_factor))

        if ctx.is_aiming:
            slowdown = max(0.30, slowdown - 0.1 * self.ads_multiplier)

        out_rx = rx * slowdown
        out_ry = ry * slowdown

        if self.rotational_enabled and mag > 100:
            pull = self.rotational_strength * (1.0 - zone_factor) * self._gate_smooth
            nx = rx / mag
            ny = ry / mag
            out_rx += nx * pull * 200.0
            out_ry += ny * pull * 200.0

        if self.humanize:
            import random
            r = random.Random()
            out_rx += r.uniform(-15.0, 15.0)
            out_ry += r.uniform(-15.0, 15.0)

        return (
            max(-32767.0, min(32767.0, out_rx)),
            max(-32767.0, min(32767.0, out_ry)),
        )


# ═══════════════════════════════════════════════════════════════════════
# LAYER 2: Aim Lock + Silent Aim (só ADS)
# ═══════════════════════════════════════════════════════════════════════

class AimLockSilentLayer(AimLayer):
    """Aim Lock + Silent Aim — combo ADS.

    Aim Lock: reforça a direção do stick quando perto do alvo (trava).
    Silent Aim: oscilação quadrada X que ativa o AA nativo do jogo.

    Só roda quando is_aiming=True (ADS/mirando).
    """

    layer_id = LayerID.AIM_LOCK_SILENT

    def __init__(self):
        super().__init__()
        # Aim Lock
        self.lock_enabled: bool = True
        self.lock_fov: int = 10000
        self.lock_strength: float = 0.5     # 0.0-1.0
        self.lock_smooth: float = 0.3

        # Silent Aim (oscilação)
        self.silent_enabled: bool = True
        self.gpc_amp: float = 8.0           # GPC (5-20)
        self.gate_low: float = 1500.0
        self.gate_high: float = 6000.0
        self.pattern: str = "square"        # square | circle
        self.circle_y_scale: float = 0.3

        # Estado interno
        self._drift_dir: int = 1
        self._drift_tick: float = 0.0
        self._orbit_angle: float = 0.0
        self._smooth_rx: float = 0.0
        self._smooth_ry: float = 0.0

    def process(self, rx: float, ry: float, ctx: LayerContext) -> Tuple[float, float]:
        if not ctx.is_aiming:
            return rx, ry

        out_rx, out_ry = rx, ry

        # ── Aim Lock ──
        if self.lock_enabled and self.lock_strength > 0:
            out_rx, out_ry = self._apply_lock(out_rx, out_ry, ctx)

        # ── Silent Aim (oscilação) ──
        if self.silent_enabled and self.gpc_amp > 0:
            out_rx, out_ry = self._apply_silent(out_rx, out_ry, ctx)

        return out_rx, out_ry

    def _apply_lock(self, rx: float, ry: float, ctx: LayerContext) -> Tuple[float, float]:
        mag = math.sqrt(rx * rx + ry * ry)
        if mag > self.lock_fov or mag < 50:
            self._smooth_rx = 0.0
            self._smooth_ry = 0.0
            return rx, ry

        proximity = 1.0 - (mag / self.lock_fov)
        nx = rx / mag
        ny = ry / mag

        lock_pull = self.lock_strength * (0.3 + 0.7 * proximity)
        pull_x = nx * lock_pull * 900.0
        pull_y = ny * lock_pull * 900.0

        if self.lock_smooth > 0:
            weight = min(0.85, max(0.10, 1.0 - self.lock_smooth))
            self._smooth_rx = self._smooth_rx * (1.0 - weight) + (rx + pull_x) * weight
            self._smooth_ry = self._smooth_ry * (1.0 - weight) + (ry + pull_y) * weight
            out_rx, out_ry = self._smooth_rx, self._smooth_ry
        else:
            out_rx, out_ry = rx + pull_x, ry + pull_y

        return (
            max(-32767.0, min(32767.0, out_rx)),
            max(-32767.0, min(32767.0, out_ry)),
        )

    def _apply_silent(self, rx: float, ry: float, ctx: LayerContext) -> Tuple[float, float]:
        mag = math.hypot(rx, ry)
        gate = self._compute_gate(mag, self.gate_low, self.gate_high)

        if gate < 0.02:
            return rx, ry

        amplitude = 327.67 * self.gpc_amp * gate

        if self.pattern == "square":
            self._drift_tick += ctx.delta_ms
            if self._drift_tick >= 20.0:
                self._drift_tick = 0.0
                self._drift_dir = -self._drift_dir
            off_x = self._drift_dir * amplitude
            return rx + off_x, ry
        else:
            speed = 2.0 + self.intensity * 1.0
            self._orbit_angle = (self._orbit_angle
                                 + speed * (ctx.delta_ms / 1000.0)) % (2 * math.pi)
            out_rx = rx + math.cos(self._orbit_angle) * amplitude
            out_ry = ry + math.sin(self._orbit_angle) * amplitude * self.circle_y_scale
            return out_rx, out_ry

    def reset(self):
        super().reset()
        self._drift_dir = 1
        self._drift_tick = 0.0
        self._orbit_angle = 0.0
        self._smooth_rx = 0.0
        self._smooth_ry = 0.0


# ═══════════════════════════════════════════════════════════════════════
# LAYER 3: Camera — Silent Hit (só hip fire)
# ═══════════════════════════════════════════════════════════════════════

class CameraHitLayer(AimLayer):
    """Silent Hit — oscilação no right stick quando atirando SEM ADS (hip fire).

    A técnica é a mesma do Silent Aim (oscilação quadrada/circular), mas o
    gate é mais permissivo: o jogador segue o alvo SEM ADS com input grande —
    a oscilação deve continuar ajudando.

    Só roda quando is_shooting=True e is_aiming=False.
    """

    layer_id = LayerID.CAMERA_HIT

    def __init__(self):
        super().__init__()
        self.gpc_amp: float = 6.0
        self.gate_low: float = 6000.0      # gate mais permissivo que Silent Aim
        self.gate_high: float = 25000.0
        self.pattern: str = "square"
        self.circle_y_scale: float = 0.3

        # Estado interno
        self._drift_dir: int = 1
        self._drift_tick: float = 0.0
        self._orbit_angle: float = 0.0

    def process(self, rx: float, ry: float, ctx: LayerContext) -> Tuple[float, float]:
        if not ctx.is_shooting or ctx.is_aiming:
            return rx, ry

        mag = math.hypot(rx, ry)
        gate = self._compute_gate(mag, self.gate_low, self.gate_high)

        if gate < 0.02:
            return rx, ry

        amplitude = 327.67 * self.gpc_amp * gate

        if self.pattern == "square":
            self._drift_tick += ctx.delta_ms
            if self._drift_tick >= 20.0:
                self._drift_tick = 0.0
                self._drift_dir = -self._drift_dir
            off_x = self._drift_dir * amplitude
            return rx + off_x, ry
        else:
            speed = 2.0 + self.intensity * 1.0
            self._orbit_angle = (self._orbit_angle
                                 + speed * (ctx.delta_ms / 1000.0)) % (2 * math.pi)
            out_rx = rx + math.cos(self._orbit_angle) * amplitude
            out_ry = ry + math.sin(self._orbit_angle) * amplitude * self.circle_y_scale
            return out_rx, out_ry

    def reset(self):
        super().reset()
        self._drift_dir = 1
        self._drift_tick = 0.0
        self._orbit_angle = 0.0


# ═══════════════════════════════════════════════════════════════════════
# LAYER 4: Track + Snap (momentum + headshot)
# ═══════════════════════════════════════════════════════════════════════

class TrackSnapLayer(AimLayer):
    """Tracking pulse + head snap vertical.

    - Tracking: micro-boost na direção do movimento (momentum)
    - Head Snap: pulo vertical suave quando engajado
    """

    layer_id = LayerID.TRACK

    def __init__(self):
        super().__init__()
        self.track_enabled: bool = True
        self.track_multiplier: float = 0.15
        self.track_threshold: int = 200
        self.track_persistence_ms: float = 30.0

        self.snap_enabled: bool = True
        self.snap_strength: float = 0.3
        self.snap_height: int = 500
        self.snap_duration_ms: float = 150.0
        self.snap_cooldown_ms: float = 200.0

        self._persist_rx: float = 0.0
        self._persist_ry: float = 0.0
        self._persist_until: float = 0.0
        self._snap_active: bool = False
        self._snap_start: float = 0.0
        self._last_snap_time: float = 0.0

    def process(self, rx: float, ry: float, ctx: LayerContext) -> Tuple[float, float]:
        out_rx, out_ry = rx, ry

        if self.track_enabled and self.track_multiplier > 0:
            out_rx, out_ry = self._apply_track(out_rx, out_ry, ctx)

        if self.snap_enabled and self.snap_strength > 0:
            out_rx, out_ry = self._apply_snap(out_rx, out_ry, ctx)

        return out_rx, out_ry

    def _apply_track(self, rx: float, ry: float, ctx: LayerContext) -> Tuple[float, float]:
        now = ctx.now
        mag = math.sqrt(rx * rx + ry * ry)

        if mag > self.track_threshold:
            self._persist_rx = float(rx)
            self._persist_ry = float(ry)
            self._persist_until = now + self.track_persistence_ms / 1000.0
            add_x = abs(rx * self.track_multiplier)
            add_y = abs(ry * self.track_multiplier)
            rx += math.copysign(add_x, rx)
            ry += math.copysign(add_y, ry)
        elif mag == 0:
            self._persist_rx = 0.0
            self._persist_ry = 0.0
            self._persist_until = 0.0
        elif now < self._persist_until:
            remaining = (self._persist_until - now) / (self.track_persistence_ms / 1000.0)
            decay = max(0.0, min(1.0, remaining))
            if abs(self._persist_rx) > self.track_threshold:
                add_x = abs(self._persist_rx * self.track_multiplier * decay)
                rx += math.copysign(add_x, self._persist_rx)
            if abs(self._persist_ry) > self.track_threshold:
                add_y = abs(self._persist_ry * self.track_multiplier * decay)
                ry += math.copysign(add_y, self._persist_ry)

        return (
            max(-32767.0, min(32767.0, rx)),
            max(-32767.0, min(32767.0, ry)),
        )

    def _apply_snap(self, rx: float, ry: float, ctx: LayerContext) -> Tuple[float, float]:
        if not ctx.is_aiming:
            self._snap_active = False
            return rx, ry

        mag = math.sqrt(rx * rx + ry * ry)
        if mag > 3000:
            return rx, ry

        now = ctx.now

        if not self._snap_active:
            time_since_last = (now - self._last_snap_time) * 1000.0
            if time_since_last >= self.snap_cooldown_ms:
                self._snap_active = True
                self._snap_start = now

        if self._snap_active:
            elapsed_ms = (now - self._snap_start) * 1000.0
            if elapsed_ms >= self.snap_duration_ms:
                self._snap_active = False
            else:
                t = elapsed_ms / self.snap_duration_ms
                ease = 1.0 - (1.0 - t) ** 2
                snap_offset = self.snap_height * self.snap_strength * ease

                if elapsed_ms > self.snap_duration_ms * 0.5:
                    decay = 1.0 - (elapsed_ms - self.snap_duration_ms * 0.5) / (
                        self.snap_duration_ms * 0.5)
                    snap_offset *= max(0.0, decay)

                ry -= snap_offset
                self._last_snap_time = now

        return (
            max(-32767.0, min(32767.0, rx)),
            max(-32767.0, min(32767.0, ry)),
        )

    def reset(self):
        super().reset()
        self._persist_rx = 0.0
        self._persist_ry = 0.0
        self._persist_until = 0.0
        self._snap_active = False


# ═══════════════════════════════════════════════════════════════════════
# LAYER 5: Sticky + Magnetic (persistência ao parar)
# ═══════════════════════════════════════════════════════════════════════

class StickyLayer(AimLayer):
    """Magnetic pull + persistência quando para.

    Quando stick movendo + engajado: pull magnético na direção.
    Quando para: mantém último pull por N ms com decay.
    """

    layer_id = LayerID.STICKY

    def __init__(self):
        super().__init__()
        self.strength: float = 0.25
        self.magnetic_pull: int = 300
        self.min_input: int = 100
        self.persist_ms: float = 200.0     # 200ms = padrão Zen (era 90ms — curto)

        self._persist_rx: float = 0.0
        self._persist_ry: float = 0.0
        self._persist_until: float = 0.0

    def process(self, rx: float, ry: float, ctx: LayerContext) -> Tuple[float, float]:
        if not self.enabled or self.strength <= 0 or self.magnetic_pull <= 0:
            self._reset_persist()
            return rx, ry

        now = ctx.now
        mag = math.sqrt(rx * rx + ry * ry)
        engaged = (ctx.is_shooting or ctx.is_aiming) and mag > self.min_input

        if engaged:
            nx = rx / mag if mag > 0 else 0.0
            ny = ry / mag if mag > 0 else 0.0
            self._persist_rx = rx
            self._persist_ry = ry
            self._persist_until = now + self.persist_ms / 1000.0

            zone_factor = min(mag / 8000.0, 1.0)
            pull = self.magnetic_pull * self.strength * (0.35 + 0.65 * zone_factor)
            pull = min(pull, self.magnetic_pull)
            rx += nx * pull
            ry += ny * pull

        elif now < self._persist_until:
            remaining = (self._persist_until - now) / (self.persist_ms / 1000.0)
            decay = max(0.0, min(1.0, remaining))
            if abs(self._persist_rx) > 50:
                keep_x = abs(self._persist_rx) * 0.35 * decay
                rx += math.copysign(keep_x, self._persist_rx) if rx == 0 else 0
            if abs(self._persist_ry) > 50:
                keep_y = abs(self._persist_ry) * 0.35 * decay
                ry += math.copysign(keep_y, self._persist_ry) if ry == 0 else 0
        else:
            self._reset_persist()

        return (
            max(-32767.0, min(32767.0, rx)),
            max(-32767.0, min(32767.0, ry)),
        )

    def _reset_persist(self):
        self._persist_rx = 0.0
        self._persist_ry = 0.0
        self._persist_until = 0.0

    def reset(self):
        super().reset()
        self._reset_persist()


# ═══════════════════════════════════════════════════════════════════════
# Layer 6: Rotational Boost (left stick micro-oscillation)
# ═══════════════════════════════════════════════════════════════════════

class RotationalBoostLayer(AimLayer):
    """Micro-oscilação no left stick para manter rotational AA ativo.

    O Fortnite só ativa rotational AA com left stick em movimento.
    Esta layer injeta micro-strafe que o jogo interpreta como movimento
    do jogador, mantendo o rotational ativo mesmo quando parado.
    """

    layer_id = LayerID.ROTATIONAL_BOOST

    def __init__(self):
        super().__init__()
        self._ls_phase = 0        # 0=X, 1=Y
        self._ls_timer = 0.0
        self._ls_toggle_ms = 25.0  # alterna eixo a cada 25ms
        self._ls_dir = 1.0
        # Config
        self.base_amplitude = 15.0   # GPC padrão
        self.ads_boost = 1.3         # multiplicador em ADS

    def process(self, rx: float, ry: float, ctx: "LayerContext") -> Tuple[float, float]:
        # Esta layer NÃO modifica rx/ry — opera no left stick
        return rx, ry

    def apply_left_stick(self, lx: float, ly: float, ctx: "LayerContext") -> Tuple[float, float]:
        """Aplica micro-oscilação no left stick."""
        if not self.enabled:
            return lx, ly

        # Amplitude em evdev
        amp_gpc = self.base_amplitude
        if ctx.is_aiming:
            amp_gpc *= self.ads_boost
        amp = 327.67 * amp_gpc

        # Gate: só ativa quando jogador parado ou movendo leve
        mag = math.hypot(lx, ly)
        if mag > 20000:  # correndo forte — não interfere
            return lx, ly

        if mag < 3000:
            factor = 1.0
        else:
            factor = max(0.3, 1.0 - (mag / 25000.0))
        amp *= factor

        # Timer
        self._ls_timer += ctx.delta_ms
        if self._ls_timer >= self._ls_toggle_ms:
            self._ls_timer = 0.0
            self._ls_phase = 1 - self._ls_phase
            self._ls_dir = -self._ls_dir

        # Aplica
        if self._ls_phase == 0:
            lx_out = lx + self._ls_dir * amp
            ly_out = ly
        else:
            lx_out = lx
            ly_out = ly + self._ls_dir * amp * 0.6

        return lx_out, ly_out

    def reset(self):
        super().reset()
        self._ls_phase = 0
        self._ls_timer = 0.0
        self._ls_dir = 1.0


# ═══════════════════════════════════════════════════════════════════════
# Layer 7: Aim Friction (reduz sensibilidade perto do alvo)
# ═══════════════════════════════════════════════════════════════════════

class FrictionLayer(AimLayer):
    """Reduz sensibilidade quando stick está em micro-ajuste.

    Quando o stick está perto do centro (< 8000 evdev), reduz a velocidade
    para dar mais controle. Simula a "fricção" que o AA nativo aplica quando
    o retículo está perto do alvo.
    """

    layer_id = LayerID.FRICTION

    def __init__(self):
        super().__init__()
        self.friction_zone = 8000.0     # evdev — dentro dessa zona, aplica fricção
        self.friction_strength = 0.6    # 0.6 = 60% da velocidade normal

    def process(self, rx: float, ry: float, ctx: "LayerContext") -> Tuple[float, float]:
        if not self.enabled:
            return rx, ry

        mag = math.hypot(rx, ry)

        if mag < self.friction_zone:
            # Dentro da zona — reduz velocidade
            factor = 1.0 - (1.0 - self.friction_strength) * (1.0 - mag / self.friction_zone)
            factor = max(0.3, factor)
            return rx * factor, ry * factor

        return rx, ry

    def reset(self):
        super().reset()


# ═══════════════════════════════════════════════════════════════════════
# Layer 8: Magnetic Pull Directional (pull na direção do movimento)
# ═══════════════════════════════════════════════════════════════════════

class MagneticPullLayer(AimLayer):
    """Pull magnético na direção do último movimento do stick.

    Quando o jogador move a mira para a direita, injeta um pull extra
    naquela direção por um curto período. Diferente do StickyLayer que
    é radial, este é direcional.
    """

    layer_id = LayerID.MAGNETIC_PULL

    def __init__(self):
        super().__init__()
        self.pull_strength = 0.15    # 15% do movimento
        self.decay_ms = 150.0        # pull dura 150ms
        self.last_dir_x = 0.0
        self.last_dir_y = 0.0
        self.decay_timer = 0.0
        self.min_input = 100.0       # threshold mínimo

    def process(self, rx: float, ry: float, ctx: "LayerContext") -> Tuple[float, float]:
        if not self.enabled:
            return rx, ry

        # Detecta direção do movimento
        if abs(rx) > self.min_input or abs(ry) > self.min_input:
            self.last_dir_x = math.copysign(1.0, rx) if rx != 0 else 0
            self.last_dir_y = math.copysign(1.0, ry) if ry != 0 else 0
            self.decay_timer = self.decay_ms

        # Aplica pull enquanto houver decay
        if self.decay_timer > 0:
            self.decay_timer -= ctx.delta_ms
            factor = max(0.0, self.decay_timer / self.decay_ms)
            pull_x = self.last_dir_x * 500.0 * self.pull_strength * factor
            pull_y = self.last_dir_y * 500.0 * self.pull_strength * factor
            return rx + pull_x, ry + pull_y

        return rx, ry

    def reset(self):
        super().reset()
        self.last_dir_x = 0.0
        self.last_dir_y = 0.0
        self.decay_timer = 0.0


# ═══════════════════════════════════════════════════════════════════════
# Pipeline de Camadas
# ═══════════════════════════════════════════════════════════════════════

class AimLayerPipeline:
    """Pipeline que roda as 8 camadas em sequência.

    1: Friction        → reduz sensibilidade perto do alvo
    2: Slowdown        → reduz velocidade perto do alvo
    3: AimLock+Silent  → trava + oscila (só ADS)
    4: CameraHit       → oscilação hip fire (só atirando sem mirar)
    5: Track/Snap      → momentum + headshot
    6: MagneticPull    → pull direcional na direção do movimento
    7: Sticky          → persistência ao parar
    8: RotationalBoost → micro-oscilação no left stick
    """

    def __init__(self):
        self.friction = FrictionLayer()
        self.slowdown = SlowdownLayer()
        self.aim_lock_silent = AimLockSilentLayer()
        self.camera_hit = CameraHitLayer()
        self.track_snap = TrackSnapLayer()
        self.magnetic_pull = MagneticPullLayer()
        self.sticky = StickyLayer()
        self.rotational_boost = RotationalBoostLayer()

        self._layers: list[AimLayer] = [
            self.friction,
            self.slowdown,
            self.aim_lock_silent,
            self.camera_hit,
            self.track_snap,
            self.magnetic_pull,
            self.sticky,
            self.rotational_boost,
        ]

    def process(self, rx: float, ry: float, ctx: LayerContext) -> Tuple[float, float]:
        out_rx, out_ry = rx, ry

        for layer in self._layers:
            if layer.enabled:
                out_rx, out_ry = layer.process(out_rx, out_ry, ctx)

        return out_rx, out_ry

    def reset(self):
        for layer in self._layers:
            layer.reset()

    def get_layer(self, layer_id: LayerID) -> Optional[AimLayer]:
        for layer in self._layers:
            if layer.layer_id == layer_id:
                return layer
        return None
