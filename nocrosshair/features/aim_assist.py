#!/usr/bin/env python3

import math
import time
from typing import Tuple, Dict, Any, Optional
from dataclasses import dataclass
from collections import deque
from nocrosshair.core.config import AimAssistConfig
from nocrosshair.features.zen_style import (
    StickyMagnetEngine, AimLockEngine, AimSpamEngine, RushEngine,
    AutoRotationEngine, HeadAssistEngine,
)
from nocrosshair.features.silent_aim_qt import (
    SilentAimQTEngine, SilentMode, silent_aim_qt,
)
from nocrosshair.features.aimlock_proto import (
    AimLockProtoConfig, AimLockProtoEngine, TargetFeed, NullTargetFeed,
)
from nocrosshair.features.kernel_aim import KernelAimConfig, KernelAimEngine
from nocrosshair.features.proxy_target import ProxyTargetConfig, ProxyTargetFeed
from nocrosshair.features.aa_mobile_proto import (
    FortniteMobileAAProto, MobileAAProtoConfig,
)
from nocrosshair.features.aim_advanced import (
    OneEuroFilter, PredictiveTracker, AdhesionBuffer,
)
from nocrosshair.features.engagement import EngagementEstimator
from nocrosshair.features.neural_aim import NeuralTrackerEngine
from nocrosshair.features.advanced_aim_systems import (
    AntiRecoilML, BallisticPredictor, SmartHeadshot,
)
from nocrosshair.features.advanced_aim import (
    MultiPolarConfig, MultiPolarEngine, PolarEngineConfig,
    GhostTrackerConfig, GhostTrackerEngine,
    BurstModeConfig, BurstModeEngine,
    BattsStickyConfig, BattsStickyEngine,
    XanaxAIConfig, XanaxAIEngine,
)
from nocrosshair.features.warzone_aim import (
    VibrationL3Config, VibrationL3Engine,
    WarzoneAimBufferConfig, WarzoneAimBufferEngine,
    RapidFirePureConfig, RapidFirePureEngine,
    AimBufferStackConfig, AimBufferStackEngine,
)


@dataclass
class PredictiveAAConfig:
    enabled: bool = False
    tracking: bool = True
    tracking_strength: int = 500
    magnetic_snap: bool = True
    predictive_enabled: bool = False
    prediction_frames: int = 3
    lead_distance: float = 0.5
    target_speed_weight: float = 0.7
    target_angle_weight: float = 0.3

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "PredictiveAAConfig":
        aa_data = d.get("aa", {})
        predictive_data = aa_data.get("predictive", {})
        return PredictiveAAConfig(
            enabled=d.get("enabled", False),
            tracking=aa_data.get("tracking", True),
            tracking_strength=aa_data.get("tracking_strength", 500),
            magnetic_snap=aa_data.get("magnetic_snap", True),
            predictive_enabled=predictive_data.get("enabled", False),
            prediction_frames=predictive_data.get("frames", 3),
            lead_distance=predictive_data.get("lead_distance", 0.5),
            target_speed_weight=predictive_data.get("speed_weight", 0.7),
            target_angle_weight=predictive_data.get("angle_weight", 0.3),
        )


class JitterEngine:
    def __init__(self):
        pass
    def set_active(self, active: bool) -> None:
        pass
    def apply_jitter(self, *args, **kwargs):
        return (0, 0)
    def reset(self) -> None:
        pass


class AutoTrackEngine:
    def __init__(self):
        self._persist_rx: float = 0.0
        self._persist_ry: float = 0.0
        self._persist_until: float = 0.0

    def apply(self, rx: int, ry: int, enabled: bool, multiplier: float,
              threshold: int, persistence_ms: float) -> Tuple[int, int]:
        if not enabled or multiplier <= 0:
            self.reset()
            return rx, ry

        now = time.monotonic()
        mag = math.sqrt(rx * rx + ry * ry)

        if mag > threshold:
            self._persist_rx = float(rx)
            self._persist_ry = float(ry)
            self._persist_until = now + persistence_ms / 1000.0

            add_x = abs(int(rx * multiplier))
            add_y = abs(int(ry * multiplier))
            rx = max(-32767, min(32767, rx + int(math.copysign(add_x, rx))))
            ry = max(-32767, min(32767, ry + int(math.copysign(add_y, ry))))
        elif mag == 0:
            # Input zerou: invalida a persistência imediatamente. Sem isso,
            # a persistência de auto_track continua produzindo output de
            #잭ré anterior — o pipeline inteiro se auto-alimenta.
            self._persist_rx = 0.0
            self._persist_ry = 0.0
            self._persist_until = 0.0
        elif now < self._persist_until:
            elapsed = now - (self._persist_until - persistence_ms / 1000.0)
            decay = max(0.0, 1.0 - elapsed / (persistence_ms / 1000.0))

            if abs(self._persist_rx) > threshold:
                add_x = abs(int(self._persist_rx * multiplier * decay))
                rx = max(-32767, min(32767, int(math.copysign(add_x, self._persist_rx))))
            if abs(self._persist_ry) > threshold:
                add_y = abs(int(self._persist_ry * multiplier * decay))
                ry = max(-32767, min(32767, int(math.copysign(add_y, self._persist_ry))))

        return rx, ry

    def reset(self) -> None:
        self._persist_rx = 0.0
        self._persist_ry = 0.0
        self._persist_until = 0.0


class StrafeShotEngine:
    def __init__(self):
        self._phase: float = 0.0

    def apply(self, lx: int, enabled: bool, amplitude: int,
              frequency: float, delta_ms: float) -> int:
        if not enabled or amplitude <= 0:
            return lx

        self._phase += 2.0 * math.pi * frequency * (delta_ms / 1000.0)
        if self._phase > 2.0 * math.pi:
            self._phase -= 2.0 * math.pi

        osc = int(amplitude * math.sin(self._phase))
        return max(-32767, min(32767, lx + osc))

    def reset(self) -> None:
        self._phase = 0.0


class LeftStickFreqEngine:
    """Oscilação do left stick pra manter o AA nativo ativo.

    Modo normal: micro-oscilação (amplitude 5-25) abaixo do deadzone do jogo.
    Modo agressivo (square): oscilação estilo Aboki/Cronus — amplitude 100,
    square wave, 500Hz — substitui o input do stick quando em repouso pra
    forçar o rotational AA do jogo com violência.

    O gate define quando parar: se o stick tá sendo usado pelo jogador
    (abs(lx) > gate ou abs(ly) > gate), a oscilação para.
    """

    def __init__(self):
        self._phase_x: float = 0.0
        self._phase_y: float = 0.0

    def apply(self, lx: int, ly: int, enabled: bool, amplitude: int,
              frequency: float, shape: str, gate: int, delta_ms: float,
              is_moving: bool = False, aggressive: bool = False) -> tuple[int, int]:
        if not enabled or amplitude <= 0:
            return lx, ly

        if is_moving or abs(lx) > gate or abs(ly) > gate:
            return lx, ly

        if aggressive:
            amp = 100
            freq = 500.0
            shape = "square"
        else:
            amp = amplitude
            freq = frequency

        self._phase_x += 2.0 * math.pi * freq * (delta_ms / 1000.0)
        self._phase_y += 2.0 * math.pi * freq * 0.7 * (delta_ms / 1000.0)
        if self._phase_x > 2.0 * math.pi:
            self._phase_x -= 2.0 * math.pi
        if self._phase_y > 2.0 * math.pi:
            self._phase_y -= 2.0 * math.pi

        if shape == "triangle":
            norm_x = self._phase_x / (2.0 * math.pi)
            norm_y = self._phase_y / (2.0 * math.pi)
            osc_x = amp * (2.0 * abs(2.0 * (norm_x - 0.5)) - 1.0)
            osc_y = amp * (2.0 * abs(2.0 * (norm_y - 0.5)) - 1.0)
        elif shape == "square":
            osc_x = amp * (1.0 if math.sin(self._phase_x) >= 0 else -1.0)
            osc_y = amp * (1.0 if math.sin(self._phase_y) >= 0 else -1.0)
        else:
            osc_x = amp * math.sin(self._phase_x)
            osc_y = amp * math.sin(self._phase_y)

        return (max(-32767, min(32767, lx + int(osc_x))),
                max(-32767, min(32767, ly + int(osc_y))))

    def reset(self) -> None:
        self._phase_x = 0.0
        self._phase_y = 0.0


class HeadSnapEngine:
    """Motor de Head Snap — micro-flick vertical pro nível da cabeça.

    Detecta "engajamento" monitorando o padrão de input do right stick:
    - Input pequeno e consistente = jogador está mirando em alguém
    - Atira em ADS = momento certo pra snap

    O snap é um pulo vertical suave que sobe o crosshair pro nível da
    cabeça, com cooldown pra não spammar. Pode ser ativado por:
    - "auto": detecta engagementautomaticamente
    - "button": pressionar R3/RS
    - "both": qualquer um dos dois

    Referências:
    - Obliteration V3: "Head Snap Power 20-100, snaps down then corrects up"
    - NEBULA: "Headshot Mod, instant snap to enemy heads"
    - YewWorks: negative hipfire recoil = upward pull for headshots
    """

    def __init__(self):
        self._snap_active: bool = False
        self._snap_start: float = 0.0
        self._snap_progress: float = 0.0
        self._last_snap_time: float = 0.0
        self._engagement_frames: int = 0
        self._prev_rx: float = 0.0
        self._prev_ry: float = 0.0
        self._button_pressed: bool = False

    def _detect_engagement(self, rx: float, ry: float, is_aiming: bool,
                           is_shooting: bool) -> bool:
        """Detecta se o jogador está mirando em alguém baseado no padrão de input.

        Heurística: stick pequeno (< 8000) + ADS + firing = provavelmente
        mirando num alvo. Se o stick tá grande, o jogador está procurando
        (sweeping) e não deve snapar.
        """
        if not is_aiming:
            self._engagement_frames = 0
            return False

        mag = math.sqrt(rx * rx + ry * ry)
        if mag < 8000:
            self._engagement_frames = min(self._engagement_frames + 1, 30)
        else:
            self._engagement_frames = max(self._engagement_frames - 2, 0)

        return self._engagement_frames >= 5 and is_shooting

    def apply(self, rx: int, ry: int, is_aiming: bool, is_shooting: bool,
              is_moving: bool, now: float, delta_ms: float,
              enabled: bool, strength: int, height: int, duration: int,
              cooldown: int, smooth: float, mode: str,
              ads_only: bool) -> Tuple[int, int]:
        if not enabled or strength <= 0:
            return rx, ry

        if ads_only and not is_aiming:
            self._snap_active = False
            self._engagement_frames = 0
            return rx, ry

        if is_moving:
            return rx, ry

        should_snap = False

        if mode in ("auto", "both"):
            if self._detect_engagement(float(rx), float(ry), is_aiming, is_shooting):
                should_snap = True

        if mode in ("button", "both") and self._button_pressed:
            should_snap = True
            self._button_pressed = False

        if should_snap and not self._snap_active:
            time_since_last = (now - self._last_snap_time) * 1000.0
            if time_since_last >= cooldown:
                self._snap_active = True
                self._snap_start = now
                self._snap_progress = 0.0

        if self._snap_active:
            elapsed_ms = (now - self._snap_start) * 1000.0
            if elapsed_ms >= duration:
                self._snap_active = False
            else:
                t = elapsed_ms / max(1.0, duration)
                self._snap_progress = t

                ease = 1.0 - (1.0 - t) ** 2 if smooth < 0.5 else t * (2.0 - t)
                snap_offset = int(height * strength / 100.0 * ease)

                if elapsed_ms > duration * 0.5:
                    decay = 1.0 - (elapsed_ms - duration * 0.5) / (duration * 0.5)
                    snap_offset = int(snap_offset * max(0.0, decay))

                ry_out = max(-32767, min(32767, ry + snap_offset))
                self._last_snap_time = now
                return rx, ry_out

        return rx, ry

    def press_button(self) -> None:
        """Ativa o snap por botão (R3/RS)."""
        self._button_pressed = True

    def reset(self) -> None:
        self._snap_active = False
        self._snap_progress = 0.0
        self._engagement_frames = 0


PULSE_RADII = {0: 0, 1: 600, 2: 1000, 3: 1500, 4: 2200, 5: 3000}
PULSE_FREQUENCIES = {0: 0, 1: 2.0, 2: 3.5, 3: 5.0, 4: 7.0, 5: 10.0}


class ZeroDelayEngine:
    def __init__(self):
        self._lt_press_time: float = 0.0
        self._rt_press_time: float = 0.0
        self._lt_was_zero: bool = True
        self._rt_was_zero: bool = True

    def process(self, lt: float, rt: float, enabled: bool,
                hold_ms: int, now: float) -> Tuple[float, float]:
        if not enabled:
            return lt, rt
        out_lt, out_rt = lt, rt
        if lt > 10 and self._lt_was_zero:
            self._lt_press_time = now
            self._lt_was_zero = False
            out_lt = 32767.0
        elif lt <= 10:
            self._lt_was_zero = True
        if self._lt_press_time > 0 and (now - self._lt_press_time) * 1000 < hold_ms:
            out_lt = 32767.0

        if rt > 10 and self._rt_was_zero:
            self._rt_press_time = now
            self._rt_was_zero = False
            out_rt = 32767.0
        elif rt <= 10:
            self._rt_was_zero = True
        if self._rt_press_time > 0 and (now - self._rt_press_time) * 1000 < hold_ms:
            out_rt = 32767.0
        return out_lt, out_rt

    def reset(self) -> None:
        self._lt_press_time = 0.0
        self._rt_press_time = 0.0
        self._lt_was_zero = True
        self._rt_was_zero = True


class PulseLevelEngine:
    def __init__(self):
        self._angle: float = 0.0

    def apply(self, rx: float, ry: float, level: int, delta_ms: float,
              y_scale: float = 1.0) -> Tuple[float, float]:
        if level == 0:
            return rx, ry
        mag = math.sqrt(rx * rx + ry * ry)
        if mag < 500:
            return rx, ry
        radius = PULSE_RADII.get(level, 0)
        freq = PULSE_FREQUENCIES.get(level, 0)
        self._angle += 2.0 * math.pi * freq * (delta_ms / 1000.0)
        if self._angle > 2.0 * math.pi:
            self._angle -= 2.0 * math.pi
        attenuation = max(0.0, 1.0 - (mag / 6000.0))
        pulse = attenuation * radius
        rx += math.cos(self._angle) * pulse
        ry += math.sin(self._angle) * pulse * y_scale
        return rx, ry

    def reset(self) -> None:
        self._angle = 0.0


class AntiFlinchEngine:
    def __init__(self):
        self._ry_history = deque(maxlen=5)
        self._flinch_active: bool = False
        self._correction_remaining: int = 0
        self._correction: int = 0

    def process(self, rx: int, ry: int, strength: int,
                is_shooting: bool, is_aiming: bool) -> Tuple[int, int]:
        # Flinch real só acontece ATIRANDO. Enquanto apenas mira, um salto
        # >4000 vem dos nossos próprios motores (snap/magnetic/PD) e a
        # correção vira kick vertical falso que tremula o retículo.
        if not is_shooting:
            self._flinch_active = False
            self._correction_remaining = 0
            self._correction = 0
            self._ry_history.clear()
            return rx, ry
        self._ry_history.append(ry)
        if len(self._ry_history) < 5:
            return rx, ry
        avg = sum(self._ry_history) / len(self._ry_history)
        recent = self._ry_history[-1]
        diff = abs(recent - avg)
        if diff > 4000 and not self._flinch_active:
            self._flinch_active = True
            self._correction_remaining = 3
            self._correction = int(math.copysign(strength, -diff))
        if self._flinch_active and self._correction_remaining > 0:
            ry += self._correction
            self._correction_remaining -= 1
            if self._correction_remaining <= 0:
                self._flinch_active = False
                self._correction = 0
        return rx, ry

    def reset(self) -> None:
        self._ry_history.clear()
        self._flinch_active = False
        self._correction_remaining = 0
        self._correction = 0


class ZeroDelayEngine:
    """Cronus/AUREN+ Zero Delay: force trigger to 100% for hold_ms on press edge.

    On the rising edge of LT or RT (crossing threshold), immediately clamp the
    trigger to full deflection for ``hold_ms`` milliseconds so the game sees a
    hard press with no analog ramp-up delay.
    """

    PRESS_THRESHOLD = 10

    def __init__(self):
        self._prev_lt: int = 0
        self._prev_rt: int = 0
        self._lt_hold_until: float = 0.0
        self._rt_hold_until: float = 0.0

    def process(self, lt: int, rt: int, enabled: bool, hold_ms: float,
                now: Optional[float] = None) -> Tuple[int, int]:
        if not enabled:
            self._prev_lt = lt
            self._prev_rt = rt
            return lt, rt

        t = now if now is not None else time.monotonic()
        hold_s = max(0.0, hold_ms) / 1000.0

        if lt > self.PRESS_THRESHOLD and self._prev_lt <= self.PRESS_THRESHOLD:
            self._lt_hold_until = t + hold_s
        if rt > self.PRESS_THRESHOLD and self._prev_rt <= self.PRESS_THRESHOLD:
            self._rt_hold_until = t + hold_s

        out_lt = 255 if (lt > 0 and t < self._lt_hold_until) else lt
        out_rt = 255 if (rt > 0 and t < self._rt_hold_until) else rt

        self._prev_lt = lt
        self._prev_rt = rt
        return out_lt, out_rt

    def reset(self) -> None:
        self._prev_lt = 0
        self._prev_rt = 0
        self._lt_hold_until = 0.0
        self._rt_hold_until = 0.0


class PrecisionBufferEngine:
    """DS4 Fluid Precision Buffer: suaviza micro-movimentos, remove jitter,
    mantém mira estável sem perder responsividade.

    Combina 4 subsistemas:
    - Tracking smoothing: suaviza o rastreamento contínuo
    - Anti-jitter: remove oscilações micro do stick
    - Stick smoothing: suaviza transições do input
    - Aim smoothing: suaviza o output final do aim assist
    """

    def __init__(self):
        self._prev_rx: float = 0.0
        self._prev_ry: float = 0.0
        self._prev_output_rx: float = 0.0
        self._prev_output_ry: float = 0.0
        self._stick_vel_x: float = 0.0
        self._stick_vel_y: float = 0.0

    def process(self, rx: int, ry: int, irx: int, iry: int,
                is_moving: bool, is_aiming: bool, delta_ms: float,
                config: 'AimAssistConfig') -> Tuple[int, int]:
        """Aplica precision buffer ao output do pipeline.

        Args:
            rx, ry: input raw do stick direito
            irx, iry: output processado pelo pipeline (antes do clamp final)
            is_moving: se o jogador está se movendo
            is_aiming: se está em ADS
            delta_ms: tempo desde último frame
            config: configuração do aim assist
        Returns:
            (irx, iry) processados com precision buffer
        """
        dt = delta_ms / 1000.0 if delta_ms > 0 else 0.016

        # ── Stick smoothing: suaviza input antes do processamento ──
        if config.precision_stick_smooth_enabled and is_moving:
            factor = config.precision_stick_smooth_factor
            response = config.precision_stick_smooth_response
            target_x = float(rx)
            target_y = float(ry)
            # Suavização exponencial com resposta ajustável
            alpha = 1.0 - (1.0 - factor) ** (response * dt * 60)
            smooth_rx = self._prev_rx + alpha * (target_x - self._prev_rx)
            smooth_ry = self._prev_ry + alpha * (target_y - self._prev_ry)
            self._prev_rx = smooth_rx
            self._prev_ry = smooth_ry
        else:
            self._prev_rx = float(rx)
            self._prev_ry = float(ry)

        # ── Anti-jitter: remove micro-oscilações ──
        if config.precision_anti_jitter_enabled:
            vel_x = (float(rx) - self._prev_rx) / dt if dt > 0 else 0.0
            vel_y = (float(ry) - self._prev_ry) / dt if dt > 0 else 0.0
            self._stick_vel_x = vel_x
            self._stick_vel_y = vel_y
            speed = math.hypot(vel_x, vel_y)

            strength = config.precision_anti_jitter_strength
            if config.precision_anti_jitter_adaptive:
                # Adapta: mais anti-jitter em velocidade baixa, menos em alta
                if speed < 100:
                    strength = min(1.0, strength * 1.5)
                elif speed > 500:
                    strength = max(0.0, strength * 0.3)

            # Aplica damping baseado na força
            if speed > 0:
                damp = 1.0 - strength * min(1.0, dt * 10)
                irx = int(irx * damp + self._prev_output_rx * (1 - damp))
                iry = int(iry * damp + self._prev_output_ry * (1 - damp))

        # ── Tracking smoothing: suaviza rastreamento contínuo ──
        if config.precision_tracking_enabled:
            mag = math.hypot(irx, iry)
            if mag > config.precision_tracking_deadzone:
                smooth = config.precision_tracking_smooth
                strength = config.precision_tracking_strength
                alpha = 1.0 - (1.0 - smooth) ** (dt * 60)
                # Suaviza o tracking mantendo a direção
                target_rx = float(irx) * strength
                target_ry = float(iry) * strength
                irx = int(self._prev_output_rx + alpha * (target_rx - self._prev_output_rx))
                iry = int(self._prev_output_ry + alpha * (target_ry - self._prev_output_ry))

        # ── Aim smoothing: suaviza output final ──
        if config.precision_aim_smooth_enabled:
            factor = config.precision_aim_smooth_factor
            if is_aiming:
                factor *= config.precision_aim_smooth_ads_boost
            alpha = 1.0 - (1.0 - factor) ** (dt * 60)
            smooth_irx = self._prev_output_rx + alpha * (float(irx) - self._prev_output_rx)
            smooth_iry = self._prev_output_ry + alpha * (float(iry) - self._prev_output_ry)
            irx = int(smooth_irx)
            iry = int(smooth_iry)

        self._prev_output_rx = float(irx)
        self._prev_output_ry = float(iry)

        return irx, iry

    def reset(self) -> None:
        self._prev_rx = 0.0
        self._prev_ry = 0.0
        self._prev_output_rx = 0.0
        self._prev_output_ry = 0.0
        self._stick_vel_x = 0.0
        self._stick_vel_y = 0.0


class AimAssistEngine:

    def __init__(self, cfg: AimAssistConfig):
        self.cfg = cfg
        self._auto_rot_angle: float = 0.0
        self._adaptive_engage: float = 0.0
    def apply_slowdown(self, rx: int, ry: int, zone: int, strength: int) -> Tuple[int, int]:
        if zone == 0:
            return rx, ry
        mag_sq = rx * rx + ry * ry
        zone_sq = zone * zone
        if mag_sq == 0:
            return rx, ry
        mag = math.sqrt(mag_sq)
        zone_factor = min(mag / zone, 1.0)
        effective_strength = min(strength, 8000)
        slowdown = max(0.40, 1.0 - (effective_strength / 10000.0) * (1.0 - zone_factor))
        rx_out = int(rx * slowdown)
        ry_out = int(ry * slowdown)
        return max(-32768, min(32767, rx_out)), max(-32768, min(32767, ry_out))

    def apply_tracking(self, rx: int, ry: int, tracking_strength: int, tracking_speed: int = 0) -> Tuple[int, int]:
        speed_factor = 1.0 + tracking_speed * 0.04
        factor = min(tracking_strength / 5000.0 * speed_factor, 0.20)
        if rx != 0:
            rx_adj = int(rx + math.copysign(abs(rx) * factor, rx))
            rx = max(-32768, min(32767, rx_adj))
        if ry != 0:
            ry_adj = int(ry + math.copysign(abs(ry) * factor, ry))
            ry = max(-32768, min(32767, ry_adj))
        return rx, ry

    def apply_snap(self, rx: int, ry: int, snap_progress: float, snap_strength: int = 0) -> Tuple[int, int]:
        snap_curve = 0.20 + 0.80 * (snap_progress ** 1.5)
        if snap_strength > 0:
            extra = snap_strength / 500.0
            snap_f = max(0.40, snap_curve - extra * 0.10)
        else:
            snap_f = snap_curve
        rx_out = int(rx * snap_f)
        ry_out = int(ry * snap_f)
        return rx_out, ry_out

    def apply_pd_controller(self, rx: int, ry: int, kp: float, kd: float,
                            prev_error_x: float = 0.0, prev_error_y: float = 0.0) -> Tuple[int, int, float, float]:
        mag = math.sqrt(rx * rx + ry * ry)
        if mag < 10:
            return rx, ry, prev_error_x, prev_error_y
        error_x = -rx / 32767.0
        error_y = -ry / 32767.0
        derivative_x = (error_x - prev_error_x) * kd
        derivative_y = (error_y - prev_error_y) * kd
        correction_x = error_x * kp + derivative_x
        correction_y = error_y * kp + derivative_y
        correction_mag = math.sqrt(correction_x**2 + correction_y**2)
        if correction_mag > 1.0:
            correction_x /= correction_mag
            correction_y /= correction_mag
        rx_out = int(rx + correction_x * mag * 0.5)
        ry_out = int(ry + correction_y * mag * 0.5)
        return (max(-32768, min(32767, rx_out)),
                max(-32768, min(32767, ry_out)),
                error_x, error_y)

    def apply_anti_shake(self, rx: int, ry: int, prev_rx: int, prev_ry: int,
                         blend: float = 0.40) -> Tuple[int, int]:
        if blend <= 0:
            return rx, ry
        if rx == 0 and ry == 0:
            return 0, 0
        rx_out = int(rx * (1.0 - blend) + prev_rx * blend)
        ry_out = int(ry * (1.0 - blend) + prev_ry * blend)
        return rx_out, ry_out

    def apply_track_assist(self, rx: int, ry: int, config: AimAssistConfig,
                           prev_rx: int, prev_ry: int) -> Tuple[int, int]:
        mag = math.sqrt(rx**2 + ry**2)
        if mag < 200 or mag > 15000:
            return rx, ry
        boost = config.tracking_strength / 5000.0
        dx = rx - prev_rx
        dy = ry - prev_ry
        dx_mag = abs(dx)
        dy_mag = abs(dy)
        if dx_mag > 50:
            rx += int(math.copysign(min(dx_mag * 0.15 * boost, config.long_range_track_boost), dx))
        if dy_mag > 50:
            ry += int(math.copysign(min(dy_mag * 0.15 * boost, config.long_range_track_boost), dy))
        return max(-32768, min(32767, rx)), max(-32768, min(32767, ry))

    def should_be_active(self, lt_pressed: bool) -> bool:
        return not lt_pressed

    def get_aa_layer(self, rx: int, ry: int,
                     prev_rx: int = 0, prev_ry: int = 0,
                     camera_threshold: int = 18000) -> str:
        mag_sq = rx * rx + ry * ry
        threshold_sq = camera_threshold * camera_threshold
        delta_sq = (rx - prev_rx) ** 2 + (ry - prev_ry) ** 2
        delta_threshold_sq = (camera_threshold * 0.4) ** 2
        if mag_sq >= threshold_sq or delta_sq >= delta_threshold_sq:
            return "camera"
        return "aim"

    def apply_micro_adjust(self, rx: int, ry: int, pull: int,
                           prev_rx: int, prev_ry: int) -> Tuple[int, int]:
        mag = math.sqrt(rx * rx + ry * ry)
        if mag < 50 or mag > 8000:
            return rx, ry
        pull_factor = pull / 1000.0
        rx_out = int(rx * (1.0 - pull_factor * 0.3))
        ry_out = int(ry * (1.0 - pull_factor * 0.3))
        rx_out = int(rx_out * 0.6 + prev_rx * 0.4)
        ry_out = int(ry_out * 0.6 + prev_ry * 0.4)
        return rx_out, ry_out


class FortniteMobileAimAssist:
    CAMERA_THRESHOLD: float = 18000.0
    CAMERA_EXIT_THRESHOLD: float = 14000.0

    def __init__(self, pull_strength: float = 1.0, slow_strength: float = 0.8,
                 soft_magnet_force: float = 0.5, ramp_up_ms: float = 150.0,
                 move_pull_boost: float = 1.0, move_soft_magnet_boost: float = 1.0,
                 move_adhesion_boost: float = 1.0):
        self.pull_strength = pull_strength
        self.slow_strength = slow_strength
        self.soft_magnet_force = soft_magnet_force
        self.ramp_up_ms = ramp_up_ms
        self.move_pull_boost = move_pull_boost
        self.move_soft_magnet_boost = move_soft_magnet_boost
        self.move_adhesion_boost = move_adhesion_boost
        self._cam_blend: float = 0.0
        self._cam_pull_x: float = 0.0
        self._cam_pull_y: float = 0.0
        self._aim_blend: float = 0.0
        self._aim_pull_x: float = 0.0
        self._aim_pull_y: float = 0.0
        self._in_camera_layer: bool = False

    def _detect_layer(self, mag: float) -> str:
        if self._in_camera_layer:
            if mag < self.CAMERA_EXIT_THRESHOLD:
                self._in_camera_layer = False
                return "aim"
            return "camera"
        else:
            if mag > self.CAMERA_THRESHOLD:
                self._in_camera_layer = True
                return "camera"
            return "aim"

    def process(self, rx: float, ry: float, is_shooting: bool, is_aiming: bool,
                is_moving: bool, delta_ms: float) -> Tuple[float, float]:
        if not (is_aiming or is_shooting):
            blend_out = delta_ms / 100.0
            self._cam_blend = max(0.0, self._cam_blend - blend_out)
            self._aim_blend = max(0.0, self._aim_blend - blend_out)
            self._cam_pull_x *= 0.6
            self._cam_pull_y *= 0.6
            self._aim_pull_x *= 0.6
            self._aim_pull_y *= 0.6
            return rx, ry

        mag = math.sqrt(rx * rx + ry * ry)
        layer = self._detect_layer(mag)

        if layer == "camera":
            ramp_boost = 0.9 if is_moving and is_shooting else 1.0
            self._cam_blend = min(1.0, self._cam_blend + delta_ms / max(1.0, self.ramp_up_ms * ramp_boost))
            self._aim_blend = max(0.0, self._aim_blend - delta_ms / 80.0)
            if mag > 500:
                move_cam_pull = self.move_pull_boost if is_moving and is_shooting else 1.0
                target_pull_x = rx * (self.pull_strength * 0.18 * move_cam_pull)
                target_pull_y = ry * (self.pull_strength * 0.18 * move_cam_pull)
                interp_speed = 10.0 * (delta_ms / 1000.0)
                self._cam_pull_x += (target_pull_x - self._cam_pull_x) * min(1.0, interp_speed)
                self._cam_pull_y += (target_pull_y - self._cam_pull_y) * min(1.0, interp_speed)
            rx_out = rx + self._cam_pull_x * self._cam_blend * 0.25
            ry_out = ry + self._cam_pull_y * self._cam_blend * 0.25
            dominant_x = abs(rx) > abs(ry)
            adhesion = 0.08 * self.pull_strength * self._cam_blend * (self.move_adhesion_boost if is_moving and is_shooting else 1.0)
            if dominant_x:
                ry_out = ry_out * (1.0 - adhesion)
            else:
                rx_out = rx_out * (1.0 - adhesion)
            return (max(-32768.0, min(32767.0, rx_out)),
                    max(-32768.0, min(32767.0, ry_out)))
        else:
            aim_ramp = 0.55 if is_moving and is_shooting else 0.7
            self._aim_blend = min(1.0, self._aim_blend + delta_ms / max(1.0, self.ramp_up_ms * aim_ramp))
            self._cam_blend = max(0.0, self._cam_blend - delta_ms / 60.0)
            slow_factor = 1.0 - (self.slow_strength * 0.42 * self._aim_blend)
            rx_out = rx * slow_factor
            ry_out = ry * slow_factor
            if mag > 50:
                move_pull_factor = self.move_pull_boost if is_moving and is_shooting else 1.0
                target_pull_x = rx * (self.pull_strength * 0.12 * move_pull_factor)
                target_pull_y = ry * (self.pull_strength * 0.12 * move_pull_factor)
                interp_speed = 15.0 * (delta_ms / 1000.0)
                self._aim_pull_x += (target_pull_x - self._aim_pull_x) * min(1.0, interp_speed)
                self._aim_pull_y += (target_pull_y - self._aim_pull_y) * min(1.0, interp_speed)
                rx_out += self._aim_pull_x * self._aim_blend * 0.55
                ry_out += self._aim_pull_y * self._aim_blend * 0.55
            if is_shooting:
                magnet_yaw = math.copysign(
                    min(abs(rx_out) * 0.13, 210.0), rx_out) if rx_out != 0 else 0.0
                magnet_pitch = math.copysign(
                    min(abs(ry_out) * 0.085, 126.0), ry_out) if ry_out != 0 else 0.0
                soft_factor = self.move_soft_magnet_boost if is_moving and is_shooting else 1.0
                rx_out += magnet_yaw * (self.soft_magnet_force * 1.05 * soft_factor) * self._aim_blend
                ry_out += magnet_pitch * (self.soft_magnet_force * 1.05 * soft_factor) * self._aim_blend
            return (max(-32768.0, min(32767.0, rx_out)),
                    max(-32768.0, min(32767.0, ry_out)))


def is_fire_edge(pipeline: "AimAssistPipeline", delta_ms: float) -> bool:
    """Detecta a borda de subida do tiro (RT recém pressionado).

    Usado pelo rotational AA para inverter a direção do giro no primeiro
    frame do tiro (estilo Zen "direction reversal on fire").
    """
    now = time.monotonic()
    edge = False
    if hasattr(pipeline, "_last_shooting_time"):
        if pipeline._last_shooting_time > 0 and now - pipeline._last_shooting_time < 40:
            edge = True
    return edge


class AimAssistPipeline:

    def __init__(self, aa_engine: AimAssistEngine, _jitter=None,
                 target_feed: Optional[TargetFeed] = None):
        self.aa_engine = aa_engine
        self.fortnite_engine = FortniteMobileAAProto()
        self.pulse_engine = PulseLevelEngine()
        self.auto_track_engine = AutoTrackEngine()
        self.anti_flinch = AntiFlinchEngine()
        self.sticky_engine = StickyMagnetEngine()
        self.lock_engine = AimLockEngine()
        self.auto_rotation_engine = AutoRotationEngine()
        self.head_assist_engine = HeadAssistEngine()
        self.aimlock_engine = AimLockProtoEngine()
        self.kernel_aim = KernelAimEngine()
        self.target_feed: TargetFeed = target_feed if target_feed is not None else NullTargetFeed()
        self.proxy_feed = ProxyTargetFeed()
        self.oef_x = OneEuroFilter()
        self.oef_y = OneEuroFilter()
        self.predictive_tracker = PredictiveTracker()
        self.adhesion_buffer = AdhesionBuffer()
        self.engagement = EngagementEstimator()
        self.neural_engine = NeuralTrackerEngine()
        self.anti_recoil_ml = AntiRecoilML()
        self.ballistic_predictor = BallisticPredictor()
        self.smart_headshot = SmartHeadshot()
        # 4ª geração: Multi-Polar, Ghost Tracker, Burst Mode, Batts Sticky, XANAX AI
        self.multi_polar = MultiPolarEngine()
        self.ghost_tracker = GhostTrackerEngine()
        self.burst_mode = BurstModeEngine()
        self.batts_sticky = BattsStickyEngine()
        self.xanax_ai = XanaxAIEngine()
        # Warzone Aim Buffers (Modo Puro)
        self.wz_vibration = VibrationL3Engine()
        self.wz_buffer = WarzoneAimBufferEngine()
        self.wz_rapid = RapidFirePureEngine()
        # Precision Buffer (DS4 Fluid)
        self.precision_buffer = PrecisionBufferEngine()
        # Silent Aim QT (portado do v2: intensidade 0-10 + Quick Tune)
        self.silent_qt = SilentAimQTEngine()
        self.raa_angle: float = 0.0
        self._prev_error_x: float = 0.0
        self._prev_error_y: float = 0.0
        self._smooth_prev_rx: int = 0
        self._smooth_prev_ry: int = 0
        self._last_aim_time: float = 0.0
        self._adaptive_engage: float = 0.0
        self._track_pulse_active: bool = False
        self._track_pulse_start: float = 0.0
        self._last_shooting: bool = False
        self._last_shooting_time: float = 0.0
        self._snap_active: bool = False
        self._snap_start: float = 0.0
        self._fire_boost_until: float = 0.0
        self._prev_raw_rx: float = 0.0
        self._prev_raw_ry: float = 0.0
        self._aimlock_elapsed: float = 0.0

    def apply(self, rx: float, ry: float, is_shooting: bool,
              is_aiming: bool, is_moving: bool, delta_ms: float,
              config: AimAssistConfig, prev_rx: float, prev_ry: float) -> tuple[float, float]:
        if not config.enabled:
            return rx, ry

        # Quando não está atirando nem mirando, o pipeline NÃO deveria
        # modificar o output. Sem isso, o estado interno (anti-shake,
        # ballistic, neural, _smooth_prev_rx/ry, _prev_raw_rx/ry) gera
        # pull indesejado a cada tick do _run_aa_tick (~1000Hz), causando
        # camera drift mesmo com stick em repouso.
        if not is_shooting and not is_aiming:
            return rx, ry

        # Robustez a taxa de polling alta / 1º frame: delta_ms ~0 faz o easing
        # do engine FN (k = 1 - exp(-dt/tau)) travar a saída em ~0 por um tick.
        delta_ms = max(delta_ms, 1.0)

        # Rastreia a borda de tiro para a reversão de direção do rotational AA
        if is_shooting and not self._last_shooting:
            self._last_shooting_time = time.monotonic()
            if config.fire_boost_mult > 1.0:
                self._fire_boost_until = time.monotonic() + config.fire_boost_ms / 1000.0
        self._last_shooting = is_shooting

        irx, iry = int(rx), int(ry)

        # ── Fase A: modelo unificado de engajamento ──
        # Estimado do input cru (não do processado) para não contaminar com
        # os nossos próprios pulls. Comanda a órbita rotacional e a
        # persistência de direção (fases B/C).
        self.engagement.update(rx, ry, is_shooting, is_aiming, delta_ms)

        # ── Tweak Zone (Ch7 S4 meta) ──
        # Quando o stick está em micro-movimento (abaixo de zone * tweak_zone_pct),
        # o crosshair flutua perto do alvo e o aim assist fica mais grudento.
        mag_raw = math.sqrt(rx**2 + ry**2)
        in_tweak_zone = (config.tweak_zone_enabled
                         and mag_raw < config.fn_zone * config.tweak_zone_pct
                         and (is_aiming or is_shooting))

        layer = config.fn_layer_strength
        rot_str = config.fn_magnet_force * layer
        slow_curve = max(0.0, min(1.0, config.fn_slow_strength * layer))

        # ── Silent Aim / Silent Hit: boost FN engine, skip orbit ──
        silent_aim_active = (config.silent_aim_enabled and is_aiming
                             and not is_shooting)
        silent_hit_active = (config.silent_hit_enabled and is_shooting
                             and not is_aiming)
        if silent_aim_active:
            rot_str *= config.silent_aim_pull_mult
            slow_curve = min(1.0, slow_curve * config.silent_aim_slow_mult)
        elif silent_hit_active:
            rot_str *= config.silent_hit_pull_mult
            slow_curve = min(1.0, slow_curve * config.silent_hit_slow_mult)

        if in_tweak_zone:
            rot_str *= config.tweak_zone_offset
            slow_curve *= 0.7

        self.fortnite_engine.cfg = MobileAAProtoConfig(
            strength_slider=config.fn_strength_slider,
            zone=config.fn_zone,
            slow_curve=slow_curve,
            rotational_strength=rot_str,
            ramp_up_ms=config.fn_ramp_up_ms,
            camera_threshold=int(config.fn_camera_threshold),
            camera_exit=int(config.fn_camera_exit),
            move_boost=config.fn_move_pull_boost,
            input_gate=config.fn_input_gate,
            ads_multiplier=config.fn_ads_multiplier,
            rotation_cap=config.fn_rotation_cap,
            camera_slow_keep=config.fn_camera_slow_keep,
            aim_pull_floor=config.fn_aim_pull_floor,
            camera_pull_floor=config.fn_camera_pull_floor,
            humanize=config.fn_humanize,
            tweak_mode=in_tweak_zone,
            camera_layer_boost=config.camera_layer_boost,
            seed=None,
        )
        irx_f, iry_f = self.fortnite_engine.process(irx, iry, is_shooting, is_aiming, is_moving, delta_ms)
        irx, iry = int(irx_f), int(iry_f)

        irx, iry = self._apply_base_aa(irx, iry, config, prev_rx, prev_ry, is_aiming, delta_ms)

        # ── Silent Aim / Silent Hit QT (portado do v2) ──
        # A OSCILAÇÃO roda no _run_flush_remap do input_loop (contínua,
        # ~50Hz, mesmo com o jogador parado). Aqui apenas sincronizamos a
        # config e rodamos o Quick Tune tick (que precisa do estado).
        silent_qt = self.silent_qt
        silent_qt.enabled = (
            (config.silent_aim_qt_enabled and config.silent_aim_enabled)
            or (config.silent_hit_qt_enabled and config.silent_hit_enabled)
        )
        silent_qt.aim_intensity = config.silent_aim_intensity
        silent_qt.hit_intensity = config.silent_hit_intensity
        silent_qt.aim_shake_blend = config.silent_aim_qt_shake_blend
        silent_qt.hit_shake_blend = config.silent_hit_qt_shake_blend
        silent_qt.aim_enabled = config.silent_aim_enabled
        silent_qt.hit_enabled = config.silent_hit_enabled
        # Quick Tune tick (o modo é detectado pelo flush no próximo loop)
        if silent_qt.enabled:
            for mode in (SilentMode.AIM, SilentMode.HIT):
                silent_qt.quick_tune_tick(mode, time.monotonic())

        # ── Auto Rotation (surpresa estilo Zen): gira sozinho na última
        # direção de mira quando o stick é solto, re-disparando o AA nativo.
        irx, iry = self._apply_auto_rotation(irx, iry, config, is_shooting, is_aiming, delta_ms)

        # ── Enhanced Pattern: ativa os motores que já existiam mas estavam
        # mortos (snap, PD controller, micro adjust, track assist, predict).
        irx, iry = self._apply_enhanced_pattern(
            irx, iry, config, prev_rx, prev_ry, delta_ms)

        # ── Sticky / Magnetic Pull (estilo Zen) ──
        irx, iry = self.sticky_engine.apply(
            irx, iry,
            enabled=config.sticky_enabled or config.magnetic_pull > 0,
            strength=config.sticky_strength,
            magnetic_pull=config.magnetic_pull,
            is_shooting=is_shooting,
            is_aiming=is_aiming,
            delta_ms=delta_ms,
        )

        # ── Aim Lock (estilo Zen) ──
        lock_str = config.lock_strength
        lock_stk = config.lock_sticky
        if is_aiming and config.ads_lock_boost > 1.0:
            lock_str = int(lock_str * config.ads_lock_boost)
            lock_stk = min(1.0, lock_stk * config.ads_lock_boost)
        irx, iry = self.lock_engine.apply(
            irx, iry,
            enabled=config.lock_enabled,
            strength=lock_str,
            fov=config.lock_fov,
            track=config.lock_track,
            sticky=lock_stk,
            smooth=config.lock_smooth,
            is_shooting=is_shooting,
            is_aiming=is_aiming,
            delta_ms=delta_ms,
        )

        # ── Head Assist (aimPoint top): tende a mira para a cabeça quando o
        # AA nativo já está grudado — sem screen capture, o engajamento é o
        # proxy de "estou no alvo". Com headlock_pulse, vira o "Head Lock"
        # estilo Zen (micro-ciclo sobe/segura que re-dispara o magnetismo).
        irx, iry = self.head_assist_engine.apply(
            irx, iry,
            enabled=config.head_assist_enabled,
            strength=config.head_assist_strength,
            is_shooting=is_shooting,
            is_aiming=is_aiming,
            delta_ms=delta_ms,
            lock_window=config.headlock_lock_window,
            headlock_pulse=config.headlock_pulse,
            headlock_pulse_ms=config.headlock_pulse_ms,
            drift_limit=config.headlock_drift_limit,
        )

        if config.anti_flinch:
            irx, iry = self.anti_flinch.process(irx, iry, config.anti_flinch_strength,
                                                is_shooting, is_aiming)

        if config.adaptive_strength:
            irx, iry = self._apply_adaptive_strength(irx, iry, config, is_shooting)

        # ── Fase B: órbita rotacional ADAPTATIVA ──
        # Só orbita quando LOCKED (retículo assentado no alvo, stick quase
        # parado) — é aí que o AA nativo desliga e precisa do micro-movimento
        # pra re-engajar. Em SEARCHING/TRACKING o jogador já está movendo o
        # stick (AA acordado), então a órbita só atrapalharia ("briga").
        # Silent Aim/Hit pulam a órbita: o pull do FN engine já é suficiente,
        # e a senoide causaria shake indesejado.
        if (config.rotational and self.engagement.locked
                and is_shooting
                and not silent_aim_active and not silent_hit_active):
            scale = 0.4 + 0.6 * self.engagement.confidence
            irx, iry = self._apply_rotational_aa(
                irx, iry, delta_ms, config, is_aiming, radius_scale=scale)

        # ── Fire Boost (estilo RocketMod "Boost Strength") ──
        # Na borda do tiro, multiplica o stick por alguns ms para "quebrar"
        # o aim lock do inimigo. 1.0 = desligado.
        if config.fire_boost_mult > 1.0 and is_shooting:
            if time.monotonic() < self._fire_boost_until:
                irx = max(-32767.0, min(32767.0, irx * config.fire_boost_mult))
                iry = max(-32767.0, min(32767.0, iry * config.fire_boost_mult))

        # ── Anti-shake: quando o Silent Aim QT está ativo, o próprio engine
        # já aplica o Zero Tremor (shake_blend 0.35/0.30). O anti-shake do v1
        # aqui aplicaria um blend de 0.8 por cima e MATARIA a órbita —
        # por isso o silent_qt não fazia efeito.
        qt_active = silent_qt.enabled and silent_qt.get_mode() != SilentMode.NONE
        if qt_active:
            irx, iry = self.aa_engine.apply_anti_shake(
                irx, iry, self._smooth_prev_rx, self._smooth_prev_ry, 0.0)
        else:
            irx, iry = self.aa_engine.apply_anti_shake(
                irx, iry, self._smooth_prev_rx, self._smooth_prev_ry,
                config.silent_aim_shake_blend if silent_aim_active
                else (config.silent_hit_shake_blend if silent_hit_active
                      else config.anti_shake_blend))

        # ── Anti-shake One-Euro (segunda geração): filtro adaptativo ──
        if config.oef_enabled:
            irx, iry = self._apply_one_euro_shake(irx, iry, config, delta_ms)

        # ── AdhesionBuffer: mais grude (persistência + axis-lock) ──
        if config.adhesion_buffer_enabled:
            irx, iry = self._apply_adhesion_buffer(
                irx, iry, config, is_shooting, is_aiming, delta_ms)

        # ── PredictiveTracker: predição alfa-beta + aceleração ──
        if config.predictive_tracker_enabled:
            irx, iry = self._apply_predictive_tracker(irx, iry, config, delta_ms)

        # ── Follow Assist (Fase C/D): puxa na direção do alvo quando LOCKED ──
        if config.follow_assist_enabled:
            irx, iry = self._apply_follow_assist(irx, iry, config)

        irx, iry = self._apply_aimlock(irx, iry, config, delta_ms, is_shooting,
                                       raw_rx=rx, raw_ry=ry)

        # ── Neural Tracker (terceira geração): Kalman + micro-corrections + harmonizer ──
        if config.neural_enabled:
            self.neural_engine.enabled = True
            self.neural_engine.kalman_measurement_noise = config.neural_kalman_noise
            self.neural_engine.kalman_lead_ms = config.neural_kalman_lead_ms
            self.neural_engine.kalman_weight = config.neural_kalman_weight
            self.neural_engine.micro_enabled = config.neural_micro_enabled
            self.neural_engine.micro_amplitude = config.neural_micro_amplitude
            self.neural_engine.confidence_scale = config.neural_confidence_scale
            self.neural_engine.harmonizer_enabled = config.neural_harmonizer_enabled
            self.neural_engine.error_feedback_enabled = config.neural_error_feedback_enabled
            irx, iry = self.neural_engine.apply(
                irx, iry, float(int(rx)), float(int(ry)),
                is_shooting, is_aiming, delta_ms,
            )
        else:
            self.neural_engine.enabled = False

        # ── Sistemas Avançados (3ª geração) ──
        # Anti-Recoil ML: aprende padrão de recoil por arma em tempo real
        if config.anti_recoil_ml_enabled:
            self.anti_recoil_ml._learning_rate = config.anti_recoil_ml_learning_rate
            if is_shooting:
                self.anti_recoil_ml.start_shooting("weapon")
                self.anti_recoil_ml.record_shot(
                    rx, ry, delta_ms, is_aiming, 5000.0
                )
                comp_x, comp_y = self.anti_recoil_ml.compensate(
                    0.0, 0.0,
                    weapon="weapon",
                    is_shooting=is_shooting,
                    is_ads=is_aiming,
                    delta_ms=delta_ms,
                    distance=5000.0,
                )
                irx += int(comp_x * config.anti_recoil_ml_strength)
                iry += int(comp_y * config.anti_recoil_ml_strength)
                irx = max(-32767, min(32767, irx))
                iry = max(-32767, min(32767, iry))

        # Ballistic Predictor: compensação de velocidade de bala + gravidade
        # Sem dados reais de alvo, funciona como preditor de inércia (follow
        # a direção do input com decaimento).
        if config.ballistic_predictor_enabled:
            self.ballistic_predictor.set_gravity(config.ballistic_predictor_gravity)
            vx = (rx - self._prev_raw_rx) / max(delta_ms, 1.0) * 1000.0
            vy = (ry - self._prev_raw_ry) / max(delta_ms, 1.0) * 1000.0
            lead_x, lead_y = self.ballistic_predictor.predict(
                irx, iry,
                irx, iry,
                5000.0,
                target_vx=vx * 0.3,
                target_vy=vy * 0.3,
                is_ads=is_aiming,
            )
            irx += int(lead_x * config.ballistic_predictor_strength)
            iry += int(lead_y * config.ballistic_predictor_strength)
            irx = max(-32767, min(32767, irx))
            iry = max(-32767, min(32767, iry))

        # Smart Headshot: puxa mira para cabeça automaticamente
        if config.smart_headshot_enabled:
            head_x, head_y = self.smart_headshot.predict_head(
                irx, iry, 5000.0
            )
            pull_x, pull_y = self.smart_headshot.calculate_pull(
                irx, iry,
                head_x, head_y,
                strength=config.smart_headshot_strength,
                max_pull=config.smart_headshot_max_pull,
            )
            irx += int(pull_x)
            iry += int(pull_y)
            irx = max(-32767, min(32767, irx))
            iry = max(-32767, min(32767, iry))

        # ── Sistemas Avançados 2 (4ª geração) ──
        # Só aplicam quando o jogador está movendo o stick (mag > gate).
        # Evita câmera andando sozinha.
        stick_active = math.hypot(irx, iry) > config.rotational_mag_gate

        # XANAX AI: computa multiplicador adaptativo baseado em mods ativos
        xanax_mult = 1.0
        if config.xanax_ai_enabled:
            active_mods = sum([
                config.multi_polar_enabled,
                config.ghost_tracker_enabled,
                config.burst_mode_enabled,
                config.batts_sticky_enabled,
                config.sticky_enabled,
                config.lock_enabled,
                config.neural_enabled,
                config.kernel_aim_beta,
            ])
            self.xanax_ai.update_mods(active_mods)
            xanax_mult = self.xanax_ai.compute_multiplier(
                float(irx), float(iry), is_shooting, delta_ms)

        # Burst Mode: boost nos primeiros tiros (só quando atirando)
        if config.burst_mode_enabled and is_shooting:
            burst_cfg = BurstModeConfig(
                enabled=True,
                burst_count=config.burst_mode_count,
                aim_boost=config.burst_mode_aim_boost,
                recoil_reduction=config.burst_mode_recoil_reduction,
                cooldown_ms=config.burst_mode_cooldown_ms,
            )
            self.burst_mode.cfg = burst_cfg
            irx, iry, recoil_mult = self.burst_mode.apply(
                irx, iry, is_shooting, time.monotonic(), delta_ms)
        else:
            recoil_mult = 1.0

        # Batts Sticky: diamond pattern (só quando stick ativo)
        if config.batts_sticky_enabled and stick_active:
            batts_cfg = BattsStickyConfig(
                enabled=True,
                ads_size=config.batts_sticky_ads_size,
                ads_fire_size=config.batts_sticky_ads_fire_size,
                hipfire_size=config.batts_sticky_hipfire_size,
                ads_speed=config.batts_sticky_ads_speed,
                ads_fire_speed=config.batts_sticky_ads_fire_speed,
                hipfire_speed=config.batts_sticky_hipfire_speed,
                drift_enabled=config.batts_sticky_drift_enabled,
                drift_strength=config.batts_sticky_drift_strength,
            )
            self.batts_sticky.cfg = batts_cfg
            irx, iry = self.batts_sticky.apply(irx, iry, is_aiming, is_shooting)

        # Ghost Tracker: desaceleração no aim bubble (só quando stick ativo)
        if config.ghost_tracker_enabled and stick_active:
            ghost_cfg = GhostTrackerConfig(
                enabled=True,
                bubble_radius=config.ghost_tracker_bubble_radius,
                decel_strength=config.ghost_tracker_decel_strength,
                decel_ramp=config.ghost_tracker_decel_ramp,
                stick_threshold=config.ghost_tracker_stick_threshold,
            )
            self.ghost_tracker.cfg = ghost_cfg
            irx, iry = self.ghost_tracker.apply(irx, iry, is_aiming, is_shooting)

        # Multi-Engine Polar: 4 órbitas simultâneas (só quando stick ativo)
        if config.multi_polar_enabled and stick_active:
            mp_cfg = MultiPolarConfig(
                enabled=True,
                close=PolarEngineConfig(
                    enabled=config.multi_polar_close_enabled,
                    radius=config.multi_polar_close_radius,
                    angle_step=config.multi_polar_close_angle,
                    shape=config.multi_polar_close_shape,
                    fire_boost_radius=config.multi_polar_close_fire_boost,
                ),
                medium=PolarEngineConfig(
                    enabled=config.multi_polar_medium_enabled,
                    radius=config.multi_polar_medium_radius,
                    angle_step=config.multi_polar_medium_angle,
                    shape=config.multi_polar_medium_shape,
                    fire_boost_radius=config.multi_polar_medium_fire_boost,
                ),
                long=PolarEngineConfig(
                    enabled=config.multi_polar_long_enabled,
                    radius=config.multi_polar_long_radius,
                    angle_step=config.multi_polar_long_angle,
                    shape=config.multi_polar_long_shape,
                    fire_boost_radius=config.multi_polar_long_fire_boost,
                ),
                sniper=PolarEngineConfig(
                    enabled=config.multi_polar_sniper_enabled,
                    radius=config.multi_polar_sniper_radius,
                    angle_step=config.multi_polar_sniper_angle,
                    shape=config.multi_polar_sniper_shape,
                    fire_boost_radius=config.multi_polar_sniper_fire_boost,
                    ads_only=config.multi_polar_sniper_ads_only,
                ),
            )
            self.multi_polar.cfg = mp_cfg
            irx, iry = self.multi_polar.apply(
                irx, iry, is_aiming, is_shooting, delta_ms)

        # Aplica multiplicador XANAX AI (só quando stick ativo)
        if config.xanax_ai_enabled and xanax_mult != 1.0 and stick_active:
            irx = int(irx * xanax_mult)
            ry_out = int(iry * xanax_mult)
            irx = max(-32767, min(32767, irx))
            ry_out = max(-32767, min(32767, ry_out))
            iry = ry_out

        # ── Warzone Aim Buffers (Modo Puro) ──
        # Vibração L3: mantém aim assist ativo
        if config.wz_vibration_enabled:
            wz_vib_cfg = VibrationL3Config(
                enabled=True,
                intensity=config.wz_vibration_intensity,
                frequency=config.wz_vibration_frequency,
                amplitude=config.wz_vibration_amplitude,
                ads_only=config.wz_vibration_ads_only,
                fire_only=config.wz_vibration_fire_only,
            )
            self.wz_vibration.cfg = wz_vib_cfg
            # Aplica micro-movimento no L3 (lx/ly do input original)
            # Nota: lx/ly não estão disponíveis aqui, então aplicamos
            # o efeito no rx/ry como proxy
            if stick_active or is_shooting:
                irx, iry, _ = self.wz_vibration.apply(
                    irx, iry, irx, iry, is_aiming, is_shooting, delta_ms)

        # Warzone Aim Buffer: tracking + sticky + rotation agressivos
        if config.wz_buffer_enabled:
            wz_buf_cfg = WarzoneAimBufferConfig(
                enabled=True,
                tracking_enabled=config.wz_buffer_tracking_enabled,
                tracking_strength=config.wz_buffer_tracking_strength,
                tracking_radius=config.wz_buffer_tracking_radius,
                sticky_enabled=config.wz_buffer_sticky_enabled,
                sticky_strength=config.wz_buffer_sticky_strength,
                sticky_radius=config.wz_buffer_sticky_radius,
                rotation_enabled=config.wz_buffer_rotation_enabled,
                rotation_radius=config.wz_buffer_rotation_radius,
                rotation_speed=config.wz_buffer_rotation_speed,
                fire_boost=config.wz_buffer_fire_boost,
                ads_only=config.wz_buffer_ads_only,
            )
            self.wz_buffer.cfg = wz_buf_cfg
            irx, iry = self.wz_buffer.apply(
                irx, iry, is_aiming, is_shooting, delta_ms)

        # ── Precision Buffer (DS4 Fluid) ──
        # Suaviza micro-movimentos, remove jitter, mantém mira estável
        irx, iry = self.precision_buffer.process(
            rx, ry, irx, iry, is_moving, is_aiming, delta_ms, config)

        self._smooth_prev_rx, self._smooth_prev_ry = irx, iry
        self._prev_raw_rx, self._prev_raw_ry = rx, ry
        # Clamp final: garante que output nunca excede limites do stick
        # Clamp individual + magnitude (hypotenuse pode exceder mesmo com componentes dentro)
        irx = max(-32767, min(32767, irx))
        iry = max(-32767, min(32767, iry))
        mag = math.hypot(irx, iry)
        if mag > 32767.0:
            scale = 32767.0 / mag
            irx = int(irx * scale)
            iry = int(iry * scale)
        return float(irx), float(iry)

    @staticmethod
    def _aimlock_proto_config(config: AimAssistConfig) -> AimLockProtoConfig:
        return AimLockProtoConfig(
            enabled=True,
            fov_degrees=config.aimlock_fov_degrees,
            smoothing_rate=config.aimlock_smoothing_rate,
            snappiness=config.aimlock_snappiness,
            prediction_enabled=config.aimlock_prediction_enabled,
            bullet_speed=config.aimlock_bullet_speed,
            gravity_scale=config.aimlock_gravity_scale,
            noise_degrees=config.aimlock_noise_degrees,
            degrees_full_stick=config.aimlock_degrees_full_stick,
            min_delta_ms=config.aimlock_min_delta_ms,
            pull_max_rate_deg_s=config.aimlock_pull_max_rate_deg_s,
            pull_ramp_up_ms=config.aimlock_pull_ramp_up_ms,
            initial_downsight_mult=config.aimlock_initial_downsight_mult,
            initial_downsight_ms=config.aimlock_initial_downsight_ms,
            adhesion_cone_deg=config.aimlock_adhesion_cone_deg,
            slow_strength=config.aimlock_slow_strength,
            max_yaw_correction_deg=config.aimlock_max_yaw_correction_deg,
            max_pitch_correction_deg=config.aimlock_max_pitch_correction_deg,
            center_strength_mult=config.aimlock_center_strength_mult,
            glue_drift_mult=config.aimlock_glue_drift_mult,
            glue_drift_window_deg=config.aimlock_glue_drift_window_deg,
            lock_timeout_ms=config.aimlock_lock_timeout_ms,
            target_bone=config.aimlock_target_bone,
            head_height_cm=config.aimlock_head_height_cm,
            max_tracking_distance_cm=config.aimlock_max_tracking_distance_cm,
            kalman_smoothing=config.aimlock_kalman_smoothing,
            velocity_adaptive_boost=config.aimlock_velocity_adaptive_boost,
        )

    def _apply_aimlock(self, rx: float, ry: float, config: AimAssistConfig,
                       delta_ms: float, is_shooting: bool = False,
                       raw_rx: Optional[float] = None,
                       raw_ry: Optional[float] = None) -> Tuple[float, float]:
        """AimLock protótipo (sem visão computacional): usa a fonte de alvo
        do target_feed (Null = sem alvo → passthrough). Quando engajado,
        mistura o stick do engine com o input do jogador por ``aimlock_blend``.

        Slow (aderência): quando o alvo está dentro do cone de adesão, o
        INPUT do jogador é amortecido antes da mistura — o retículo "cola"
        no alvo (efeito sticky do FortAimAssist2D, mais forte no centro).
        """
        if raw_rx is None:
            raw_rx = rx
        if raw_ry is None:
            raw_ry = ry
        if not config.aimlock_enabled:
            return rx, ry

        # ── Kernel Aim (BETA): hardlock estilo kernel, sem memória ──
        # Substitui o aimlock proxy comum quando o beta está ligado.
        # IMPORTANTE: o proxy é alimentado com o input CRU do jogador
        # (raw_rx/raw_ry) — nunca com o output processado. Antes recebia o
        # output amplificado (sticky+lock+head), o lock travava na direção
        # do PRÓPRIO output e a câmera continuava andando sozinha pro lado
        # do input (feedback positivo infinito).
        if getattr(config, "kernel_aim_beta", False) and config.aimlock_source == "proxy":
            self.kernel_aim.set_input(raw_rx, raw_ry, is_shooting, delta_ms)
            k_out = self.kernel_aim.compute(delta_ms)
            if k_out is None:
                return rx, ry
            k_blend = self.kernel_aim._get_adaptive_blend()
            k_rx, k_ry = k_out
            return (max(-32767.0, min(32767.0, rx * (1.0 - k_blend) + k_rx * k_blend)),
                    max(-32767.0, min(32767.0, ry * (1.0 - k_blend) + k_ry * k_blend)))

        if config.aimlock_source == "proxy":
            self.proxy_feed.cfg = ProxyTargetConfig(
                input_min=config.aimlock_proxy_input_min,
                head_pull_deg=config.aimlock_proxy_head_pull_deg,
                yaw_gain_deg=config.aimlock_proxy_yaw_gain_deg,
                assumed_dist_cm=config.aimlock_proxy_assumed_dist_cm,
                release_ms=config.aimlock_proxy_release_ms,
            )
            self.proxy_feed.set_input(raw_rx, raw_ry, is_shooting, delta_ms)
            state = self.proxy_feed.get_target(delta_ms)
        else:
            state = self.target_feed.get_target(delta_ms)
        if state is None:
            return rx, ry
        self.aimlock_engine.cfg = self._aimlock_proto_config(config)
        self.aimlock_engine.set_target(state.eye, state.target, state.vel)
        # min_delta_ms (8ms) do engine: no tick de ~1ms o compute nunca
        # calcularia o lock. Acumula o delta até passar do mínimo; entre um
        # compute e outro, SEGURA o último output (sem oscilação hard/soft).
        self._aimlock_elapsed += delta_ms
        if self._aimlock_elapsed < self.aimlock_engine.cfg.min_delta_ms:
            if self.aimlock_engine.engaged:
                al_rx, al_ry = self.aimlock_engine._last_out
                slow = self.aimlock_engine.slow_factor(
                    state.view_yaw, state.view_pitch)
                blend = max(0.0, min(1.0, config.aimlock_blend))
                rx_in = rx * (1.0 - slow)
                ry_in = ry * (1.0 - slow)
                return (max(-32767.0, min(32767.0, rx_in * (1.0 - blend) + al_rx * blend)),
                        max(-32767.0, min(32767.0, ry_in * (1.0 - blend) + al_ry * blend)))
            return rx, ry
        dt = self._aimlock_elapsed
        self._aimlock_elapsed = 0.0
        al_rx, al_ry = self.aimlock_engine.compute(
            state.view_yaw, state.view_pitch, dt)
        if not self.aimlock_engine.engaged:
            return rx, ry
        slow = self.aimlock_engine.slow_factor(state.view_yaw, state.view_pitch)
        blend = max(0.0, min(1.0, config.aimlock_blend))
        rx_in = rx * (1.0 - slow)
        ry_in = ry * (1.0 - slow)
        rx_out = rx_in * (1.0 - blend) + al_rx * blend
        ry_out = ry_in * (1.0 - blend) + al_ry * blend
        return max(-32767.0, min(32767.0, rx_out)), max(-32767.0, min(32767.0, ry_out))

    def _apply_base_aa(self, rx: float, ry: float, config: AimAssistConfig,
                       prev_rx: float, prev_ry: float, is_aiming: bool = False,
                       delta_ms: float = 16.0) -> tuple[float, float]:
        if not config.base_aa_enabled:
            return rx, ry

        zone = config.zone
        strength = config.strength
        track = config.tracking_strength

        if is_aiming and hasattr(config, "ads_multiplier"):
            strength = int(strength * config.ads_multiplier)
            track = int(track * config.ads_multiplier)

        if config.power_boost:
            boost = config.power_mult
            zone = int(zone * boost)
            strength = int(strength * boost)
            track = int(track * boost)

        if config.use_dz_radius:
            min_zone = config.deadzone_aa_radius * 100 * config.zone_multiplier
            zone = max(zone, min_zone)

        zone = min(zone, 8000)
        strength = min(strength, 12000)
        track = min(track, 2000)

        irx, iry = int(rx), int(ry)
        irx, iry = self.aa_engine.apply_slowdown(irx, iry, zone, strength)
        if config.tracking:
            if config.auto_track_enabled:
                mult = config.auto_track_multiplier * (track / 5000.0)
                irx, iry = self.auto_track_engine.apply(
                    irx, iry,
                    enabled=True,
                    multiplier=mult,
                    threshold=config.auto_track_threshold,
                    persistence_ms=config.auto_track_persistence_ms,
                )
            elif is_aiming:
                irx, iry = self._apply_track_pulse(irx, iry, track, config.track_ads_pulse_ms, delta_ms)
            else:
                irx, iry = self.aa_engine.apply_tracking(irx, iry, track, config.tracking_speed)
        return float(irx), float(iry)

    def _apply_track_pulse(self, rx: int, ry: int, strength: int,
                           pulse_ms: int, delta_ms: float) -> Tuple[int, int]:
        now = time.monotonic() * 1000
        if not self._track_pulse_active:
            self._track_pulse_active = True
            self._track_pulse_start = now
        elapsed = now - self._track_pulse_start
        if elapsed > pulse_ms:
            self._track_pulse_active = False
            return rx, ry
        progress = min(1.0, elapsed / pulse_ms)
        pulse_factor = 1.0 + (1.0 - progress) * 0.5
        factor = min(strength / 5000.0 * pulse_factor, 0.20)
        if rx != 0:
            rx_adj = int(rx + math.copysign(abs(rx) * factor, rx))
            rx = max(-32768, min(32767, rx_adj))
        if ry != 0:
            ry_adj = int(ry + math.copysign(abs(ry) * factor, ry))
            ry = max(-32768, min(32767, ry_adj))
        return rx, ry

    def _apply_auto_rotation(self, rx: float, ry: float, config: AimAssistConfig,
                             is_shooting: bool, is_aiming: bool,
                             delta_ms: float) -> Tuple[float, float]:
        """Auto Rotation: gira o right stick sozinho quando o jogador solta.

        Sem screen capture, a única direção honesta é a última que o jogador
        segurou. Quando o stick é solto mirando/atirando, o drift sinusoidal
        mantém o AA nativo do jogo re-engajado.
        """
        if not config.auto_rotation_enabled:
            return rx, ry
        return self.auto_rotation_engine.apply(
            rx, ry,
            enabled=config.auto_rotation_enabled,
            speed=config.auto_rotation_speed,
            is_shooting=is_shooting,
            is_aiming=is_aiming,
            delta_ms=delta_ms,
        )

    def _apply_enhanced_pattern(self, rx: float, ry: float, config: AimAssistConfig,
                                prev_rx: float, prev_ry: float,
                                delta_ms: float) -> Tuple[float, float]:
        """Enhanced Pattern: ativa motores que existiam mas estavam mortos.

        Gate principal: ``config.enhanced_enabled``. O seletor ``aim_pattern``
        escolhe o combo: standard (passthrough), micro_adjust, track_assist
        ou full. ``standard`` preserva o comportamento atual. A predição
        (lead) foi consolidada no PredictiveTracker unificado (fora daqui).
        """
        if not config.enhanced_enabled or config.aim_pattern == "standard":
            return rx, ry

        pattern = config.aim_pattern.lower().replace(" ", "_")
        do_micro = pattern in ("micro_adjust", "full") and config.micro_adjust_pull > 0
        do_track = pattern in ("track_assist", "full")

        # 1. Snap magnético: puxa o retículo para o centro do alvo no início
        # do engajamento (dentro de snap_duration). Só atua com input PEQUENO
        # (retículo já perto do alvo) — se atuasse durante a busca da câmera,
        # cortaria o movimento e a câmera ficaria dura.
        if config.magnetic_snap and config.snap_strength > 0:
            mag = math.sqrt(rx * rx + ry * ry)
            now = time.monotonic()
            if mag < 2500 and not self._snap_active:
                self._snap_active = True
                self._snap_start = now
            elif mag >= 2500:
                self._snap_active = False
            if self._snap_active:
                progress = min(1.0, (now - self._snap_start) / max(1, config.snap_duration))
                rx, ry = self.aa_engine.apply_snap(rx, ry, progress, config.snap_strength)

        # 2. PD controller: correção proporcional-derivativa contra overshoot.
        if config.pd_kp > 0:
            rx, ry, self._prev_error_x, self._prev_error_y = self.aa_engine.apply_pd_controller(
                rx, ry, config.pd_kp, config.pd_kd,
                self._prev_error_x, self._prev_error_y,
            )

        # 3. Micro adjust: estabiliza micro-correções perto do alvo.
        if do_micro:
            rx, ry = self.aa_engine.apply_micro_adjust(
                rx, ry, config.micro_adjust_pull, prev_rx, prev_ry)

        # 4. Track assist: boost de acompanhamento em longa distância.
        if do_track:
            rx, ry = self.aa_engine.apply_track_assist(rx, ry, config, prev_rx, prev_ry)

        return rx, ry

    def _apply_rotational_aa(self, rx: float, ry: float, delta_ms: float,
                             config: AimAssistConfig,
                             is_aiming: bool = False,
                             radius_scale: float = 1.0) -> tuple[float, float]:
        mag = math.sqrt(rx**2 + ry**2)
        if mag < config.rotational_mag_gate:
            return rx, ry
        # Órbita só na zona de combate: com input grande a câmera está
        # girando (o jogador está mirando) — a órbita brigaria e a mira
        # "mexe sozinha". Ela só serve pra re-disparar o AA nativo com o
        # retículo PERTO do alvo.
        if mag > 2500:
            return rx, ry

        in_rx, in_ry = rx, ry

        radius = int(config.zone // 8 * radius_scale * config.rotational_radius_mult)
        if config.power_boost:
            radius = int(radius * config.power_mult)
        # Cap de 1200 unidades: acima disso o balanço lateral fica visível.
        radius = min(radius, 1200)

        # Raio mínimo casado com o deadzone do jogo: o micro-movimento precisa
        # ultrapassar o deadzone para re-disparar o AA nativo (estilo Zen).
        if config.use_dz_radius and config.deadzone_aa_radius > 0:
            dz_min = config.deadzone_aa_radius * 40
            radius = max(radius, dz_min)

        angle_step = 0.30 * (1.0 / max(0.01, 1.0 - mag / 20000.0))
        self.raa_angle += angle_step
        if self.raa_angle > 2 * math.pi:
            self.raa_angle -= 2 * math.pi

        # A órbita serve para re-disparar o AA nativo quando o jogador está
        # PERTO do alvo. Quando ele está girando a câmera de verdade (mag
        # alto), a órbita some — senão ela LUTA com o input e inverte a
        # direção do jogador (o "não segue" do preset).
        attenuation = max(0.0, 1.0 - (mag / 6000.0))

        # Reversão de direção na borda de tiro: quando o jogador começa a
        # atirar, inverte o sentido do giro para re-disparar o magnetismo
        # nativo na direção oposta (estilo Zen "direction reversal on fire").
        fire_edge = config.rotational and is_fire_edge(self, delta_ms)

        shape = config.shape_mode
        if shape == "circular":
            cx = math.cos(self.raa_angle)
            cy = math.sin(self.raa_angle)
        elif shape == "zen":
            speed_mod = 0.5 + 0.5 * math.sin(self.raa_angle * 0.5)
            cx = math.cos(self.raa_angle * speed_mod)
            cy = math.sin(self.raa_angle * speed_mod)
        elif shape == "helix":
            drift = 0.3 * math.sin(self.raa_angle * 0.25)
            cx = math.cos(self.raa_angle) + drift
            cy = math.sin(self.raa_angle)
            norm = math.sqrt(cx**2 + cy**2)
            cx /= norm
            cy /= norm
        elif shape == "wideoval":
            cx = math.cos(self.raa_angle) * 2.0
            cy = math.sin(self.raa_angle)
            norm = math.sqrt(cx**2 + cy**2)
            cx /= norm
            cy /= norm
        elif shape == "tallowal":
            cx = math.cos(self.raa_angle)
            cy = math.sin(self.raa_angle) * 2.0
            norm = math.sqrt(cx**2 + cy**2)
            cx /= norm
            cy /= norm
        else:
            cx = math.cos(self.raa_angle)
            cy = math.sin(self.raa_angle)

        if fire_edge:
            cx, cy = -cx, -cy

        # Ao mirar (ADS), achata o componente vertical: o propósito da órbita
        # é re-disparar o AA nativo — isso se faz com a oscilação horizontal;
        # a senoide vertical é o "travando pra cima e pra baixo".
        if is_aiming:
            cy *= 0.25

        rx += cx * radius * attenuation
        ry += cy * radius * attenuation

        rx, ry = self.pulse_engine.apply(
            rx, ry, config.pulse_level, delta_ms,
            y_scale=0.25 if is_aiming else 1.0)

        # Guard anti-briga: a órbita/pulso nunca pode INVERTER a direção que o
        # jogador está segurando no eixo — se isso acontecer, para no neutro.
        # Sem essa trava o retículo "luta" contra a mão e não segue o alvo.
        if in_rx != 0 and rx * in_rx < 0:
            rx = 0.0
        if in_ry != 0 and ry * in_ry < 0:
            ry = 0.0
        return rx, ry

    def _apply_adaptive_strength(self, rx: float, ry: float, config: AimAssistConfig,
                                 is_shooting: bool) -> tuple[float, float]:
        mag = math.sqrt(rx**2 + ry**2)
        if mag < 100:
            return rx, ry
        boost = 1.0 + max(0, 1.0 - mag / 12000.0) * 0.4
        if is_shooting:
            self._adaptive_engage = min(1.0, self._adaptive_engage + 0.1)
        else:
            self._adaptive_engage = max(0.5, self._adaptive_engage - 0.02)
        engagement = 0.8 + 0.2 * self._adaptive_engage
        scale = boost * engagement
        return int(rx * scale), int(ry * scale)

    def _apply_one_euro_shake(self, rx: float, ry: float, config: AimAssistConfig,
                              delta_ms: float) -> Tuple[float, float]:
        """Anti-shake adaptativo (filtro 1€): suaviza jitter em baixa
        velocidade e responde rápido em alta velocidade. Substitui o blend
        fixo quando ``oef_enabled`` — os parâmetros vêm do config a cada
        tick para refletir mudanças ao vivo da UI."""
        self.oef_x.set_params(config.oef_min_cutoff, config.oef_beta, config.oef_d_cutoff)
        self.oef_y.set_params(config.oef_min_cutoff, config.oef_beta, config.oef_d_cutoff)
        out_x = self.oef_x.filter(float(rx), delta_ms)
        out_y = self.oef_y.filter(float(ry), delta_ms)
        return (max(-32767.0, min(32767.0, out_x)),
                max(-32767.0, min(32767.0, out_y)))

    def _apply_predictive_tracker(self, rx: float, ry: float, config: AimAssistConfig,
                                  delta_ms: float) -> Tuple[float, float]:
        """Predição unificada: adianta a mira na direção do alvo (follow_dir)
        com a magnitude da velocidade de acompanhamento + aceleração."""
        self.predictive_tracker.vel_alpha = config.predictive_vel_alpha
        self.predictive_tracker.accel_alpha = config.predictive_accel_alpha
        self.predictive_tracker.lead_horizon_ms = config.predictive_lead_horizon_ms
        self.predictive_tracker.min_speed = config.predictive_min_speed
        self.predictive_tracker.max_lead = config.predictive_max_lead
        self.predictive_tracker.consistency = config.predictive_consistency
        self.predictive_tracker.direction_blend = config.predictive_direction_blend
        lead_x, lead_y = self.predictive_tracker.predict(
            rx, ry, delta_ms,
            follow_dir=self.engagement.follow_dir,
            confidence=self.engagement.confidence,
        )
        return (max(-32767.0, min(32767.0, rx + lead_x)),
                max(-32767.0, min(32767.0, ry + lead_y)))

    def _apply_adhesion_buffer(self, rx: float, ry: float, config: AimAssistConfig,
                               is_shooting: bool, is_aiming: bool,
                               delta_ms: float) -> Tuple[float, float]:
        """Grude extra: persistência de direção ao soltar o stick + axis-lock
        perto do centro (evita derrapagem diagonal para fora do alvo)."""
        self.adhesion_buffer.hold_ms = config.adhesion_hold_ms
        self.adhesion_buffer.decay = config.adhesion_decay
        self.adhesion_buffer.axis_lock = config.adhesion_axis_lock
        self.adhesion_buffer.min_mag = config.adhesion_min_mag
        engaged = is_shooting or is_aiming
        out_x, out_y = self.adhesion_buffer.apply(rx, ry, engaged, delta_ms)
        return (max(-32767.0, min(32767.0, out_x)),
                max(-32767.0, min(32767.0, out_y)))

    def _apply_follow_assist(self, rx: float, ry: float,
                             config: AimAssistConfig) -> Tuple[float, float]:
        """Fase C/D: quando LOCKED (retículo assentado no alvo), puxa na
        direção de acompanhamento (follow_dir do engagement estimator) para o
        retículo seguir o strafe do inimigo sem esforço do jogador. A direção
        é a EMA da direção recente — já acompanha o strafe (glue drift)."""
        if not self.engagement.locked:
            return rx, ry
        conf = self.engagement.confidence
        if conf <= 0.5:
            return rx, ry
        fx, fy = self.engagement.follow_dir
        if fx == 0.0 and fy == 0.0:
            return rx, ry
        pull = config.follow_assist_pull * conf
        return (max(-32767.0, min(32767.0, rx + fx * pull)),
                max(-32767.0, min(32767.0, ry + fy * pull)))

    def update_config(self, config: AimAssistConfig) -> None:
        self.aa_engine = AimAssistEngine(config)


class AATestbed:

    def __init__(self, aa_engine: AimAssistEngine):
        self.aa_engine = aa_engine
        self.last_rx = 0
        self.last_ry = 0
        self.target_angle = 0.0

    def set_target(self, angle: float) -> None:
        self.target_angle = angle

    def apply_config(self, config: AimAssistConfig) -> None:
        self.aa_engine = AimAssistEngine(config)

    def simulate_input(self, x: int, y: int,
                       is_shooting: bool = True,
                       is_moving: bool = True,
                       lt_pressed: bool = False,
                       snap_progress: float = 0.5) -> Tuple[int, int]:
        cfg = self.aa_engine.cfg
        if not cfg.enabled or not self.aa_engine.should_be_active(lt_pressed):
            return x, y

        rx, ry = x, y
        rx, ry = self.aa_engine.apply_slowdown(rx, ry, cfg.zone, cfg.strength)
        if cfg.tracking:
            rx, ry = self.aa_engine.apply_tracking(rx, ry, cfg.tracking_strength, cfg.tracking_speed)
        if cfg.magnetic_snap:
            rx, ry = self.aa_engine.apply_snap(rx, ry, snap_progress, cfg.snap_strength)

        if x != 0 or y != 0:
            self.last_rx = x
            self.last_ry = y
        return rx, ry


class AimAssistPresets:

    @staticmethod
    def fortnite_controller() -> AimAssistConfig:
        return AimAssistConfig(
            enabled=True,
            base_aa_enabled=True,
            strength=8925,
            ads_multiplier=1.05,
            zone=5000,
            rotational=True,
            pulse_level=0,
            aim_type="flow",
            magnetic_snap=True,
            snap_strength=450,
            snap_duration=80,
            tracking=True,
            tracking_strength=1575,
            tracking_speed=0,
            track_ads_pulse_ms=240,
            sticky_enabled=True,
            sticky_strength=0.75,
            rush_enabled=False,
            power_boost=False,
            power_mult=1.0,
            lock_enabled=True,
            lock_strength=11000,
            lock_fov=5000,
            lock_track=1200,
            lock_sticky=0.65,
            lock_smooth=0.45,
            shape_mode="circular",
            aim_pattern="full",
            enhanced_enabled=True,
            micro_adjust_pull=600,
            anti_shake_blend=0.20,
            magnetic_pull=2200,
            anti_flinch=True,
            anti_flinch_strength=3000,
            zero_delay=True,
            zero_delay_ms=40,
            bloom_compensation=True,
            strafe_shot_enabled=True,
            strafe_shot_amplitude=100,
            strafe_shot_frequency=8.0,
            strafe_shot_shape="sine",
            fn_layer_strength=1.05,
            auto_track_enabled=True,
            auto_track_multiplier=0.15,
            auto_track_persistence_ms=30.0,
            auto_track_threshold=200,
            fn_pull_strength=1.0,
            fn_slow_strength=0.75,
            fn_magnet_force=0.65,
            fn_move_pull_boost=1.05,
            fn_move_soft_magnet_boost=1.10,
            fn_move_adhesion_boost=1.10,
            fn_ramp_up_ms=150.0,
            fn_camera_threshold=18000.0,
            fn_camera_exit=14000.0,
            pd_kp=0.25,
            pd_kd=0.12,
            long_range_track_boost=900,
            headlock_pulse=True,
            headlock_pulse_ms=60,
            headlock_drift_limit=2500,
            headlock_lock_window=3200,
            fire_boost_mult=1.12,
            fire_boost_ms=100,
        )

    @staticmethod
    def fortnite_aimbot() -> AimAssistConfig:
        """Combo Aimbot: preset FN Controller com TODOS os aims no MÁXIMO.

        TODOS OS SETTINGS AVANÇADOS:
        - Master Aim Assist: máximo
        - Sticky/Magnet/Lock: máximo
        - Head Assist + Headlock: máximo
        - Follow Assist: máximo
        - Adhesion Buffer: máximo
        - Predictive Tracker: máximo
        - Neural Aim: máximo
        - Silent Aim/Hit: máximo
        - Camera Layer: máximo
        - ADS Lock: máximo
        - Kernel Aim (BETA): hardlock estilo kernel, sem memória
        - AimLock proxy: trava ativa (input_min 300 = engaja de perto)
        - LS freq + Rush strafe: micro-movimento do analógico esquerdo
        - Multi-Engine Polar: 4 órbitas simultâneas
        - Ghost Tracker: desaceleração no aim bubble
        - Burst Mode: boost nos primeiros 3 tiros
        - Batts Sticky: diamond pattern ADS/Hipfire
        - XANAX AI: adapta por mods + range
        - Vibração L3: mantém AA ativo via vibração
        - Warzone Aim Buffer: tracking + sticky + rotation agressivos
        - Rapid Fire: cadência máxima com anti-recoil integrado
        """
        cfg = AimAssistPresets.fortnite_controller()
        cfg.enabled = True
        cfg.base_aa_enabled = True
        cfg.strength = 12000         # Forte — o AA do jogo é fraco, precisamos compensar
        cfg.zone = 8000
        cfg.ads_multiplier = 1.4
        cfg.rotational = True
        cfg.pulse_level = 2
        cfg.aim_type = "flow"
        cfg.magnetic_snap = True
        cfg.snap_strength = 1200
        cfg.snap_duration = 150
        cfg.tracking = True
        cfg.tracking_strength = 5000  # Tracking forte — precisa compensar AA nerfado
        cfg.tracking_speed = 0
        cfg.track_ads_pulse_ms = 150
        cfg.sticky_enabled = True
        cfg.sticky_strength = 1.8     # Grudar forte
        cfg.magnetic_pull = 6000
        cfg.lock_enabled = True
        cfg.lock_strength = 18000     # Lock forte — gruda no alvo
        cfg.lock_fov = 10000
        cfg.lock_track = 2500
        cfg.lock_sticky = 1.0
        cfg.lock_smooth = 0.2
        cfg.auto_rotation_enabled = False
        cfg.power_boost = True
        cfg.power_mult = 1.5
        cfg.rush_enabled = False
        cfg.adaptive_strength = True
        cfg.adaptive_strength_min = 0.4
        cfg.adaptive_strength_max = 2.0
        cfg.strafe_shot_amplitude = 0
        cfg.strafe_shot_frequency = 0.0
        cfg.fn_magnet_force = 1.6        # Forte — precisa compensar AA nerfado
        cfg.fn_pull_strength = 1.8       # Puxão forte
        cfg.fn_layer_strength = 1.5      # Camada forte
        cfg.fn_strength_slider = 100
        cfg.fn_zone = 8000               # Zona maior — pega mais alvos
        cfg.fn_slow_strength = 0.95      # Slow forte — quase para no alvo
        cfg.fn_ramp_up_ms = 15.0         # Rápido — ativa rápido
        cfg.fn_move_pull_boost = 2.5     # Boost forte ao mover
        cfg.fn_move_soft_magnet_boost = 2.0
        cfg.fn_move_adhesion_boost = 2.0
        cfg.fn_input_gate = 180
        cfg.fn_ads_multiplier = 1.4
        cfg.fn_rotation_cap = 700        # Rotação moderada-alta
        cfg.fn_camera_slow_keep = 0.95   # era 0.9 — slow mais forte
        cfg.fn_aim_pull_floor = 0.65
        cfg.fn_camera_pull_floor = 0.88
        cfg.fn_camera_threshold = 17000.0
        cfg.fn_camera_exit = 13000.0
        cfg.camera_layer_boost = 1.3
        cfg.ads_lock_boost = 1.6
        cfg.fire_boost_mult = 1.6       # Boost forte ao atirar
        cfg.fire_boost_ms = 200
        cfg.head_assist_enabled = True
        cfg.head_assist_strength = 1.0   # Gruda na cabeça
        cfg.headlock_pulse = True
        cfg.headlock_pulse_ms = 25
        cfg.headlock_drift_limit = 7000  # Limite alto
        cfg.headlock_lock_window = 5500
        cfg.head_snap_enabled = True
        cfg.head_snap_strength = 80      # Snap moderado — puxa pra cabeça
        cfg.head_snap_height = 900
        cfg.head_snap_duration = 200
        cfg.head_snap_cooldown = 180
        cfg.head_snap_smooth = 0.2
        cfg.head_snap_mode = "auto"
        cfg.head_snap_ads_only = False
        cfg.anti_flinch = True
        cfg.anti_flinch_strength = 5000
        cfg.bloom_compensation = True
        cfg.anti_shake_blend = 0.0
        cfg.aimlock_enabled = True
        cfg.aimlock_blend = 0.9         # Forte — trava e segura
        cfg.aimlock_source = "proxy"
        cfg.aimlock_target_bone = "head"
        cfg.aimlock_head_height_cm = 30.0
        cfg.aimlock_max_tracking_distance_cm = 50000.0
        cfg.aimlock_kalman_smoothing = 0.25
        cfg.aimlock_velocity_adaptive_boost = 0.9
        cfg.aimlock_proxy_input_min = 300.0
        cfg.aimlock_proxy_head_pull_deg = 2.5  # Puxa cabeça moderado
        cfg.aimlock_proxy_yaw_gain_deg = 2.0
        cfg.aimlock_proxy_assumed_dist_cm = 3000.0
        cfg.aimlock_proxy_release_ms = 250.0
        cfg.kbm_mode = True
        cfg.kbm_scale = 0.2
        cfg.fn_humanize = True
        cfg.oef_enabled = False
        cfg.predictive_tracker_enabled = True
        cfg.predictive_vel_alpha = 0.22
        cfg.predictive_accel_alpha = 0.1
        cfg.predictive_lead_horizon_ms = 60.0
        cfg.predictive_min_speed = 120.0
        cfg.predictive_max_lead = 5500
        cfg.predictive_consistency = 2
        cfg.predictive_direction_blend = 0.8
        cfg.adhesion_buffer_enabled = True
        cfg.adhesion_hold_ms = 200.0     # Gruda mais tempo
        cfg.adhesion_decay = 0.18        # Decai devagar
        cfg.adhesion_axis_lock = 0.3     # Trava moderado
        cfg.adhesion_min_mag = 55.0
        cfg.follow_assist_enabled = True
        cfg.follow_assist_pull = 700     # Puxa forte
        cfg.neural_enabled = True
        cfg.neural_kalman_noise = 300.0
        cfg.neural_kalman_lead_ms = 40.0
        cfg.neural_kalman_weight = 0.8
        cfg.neural_micro_enabled = False
        cfg.neural_micro_amplitude = 0.0
        cfg.neural_confidence_scale = 1.4
        cfg.neural_harmonizer_enabled = True
        cfg.neural_error_feedback_enabled = True
        cfg.silent_aim_enabled = True
        cfg.silent_aim_slow_mult = 2.5
        cfg.silent_aim_pull_mult = 4.0
        cfg.silent_aim_shake_blend = 0.8
        # ── Silent Aim QT (portado do v2: intensidade 0-10 + Quick Tune) ──
        cfg.silent_aim_qt_enabled = True
        cfg.silent_aim_intensity = 5          # Quick Tune recomenda 5
        cfg.silent_aim_qt_shake_blend = 0.35
        cfg.silent_hit_enabled = True
        cfg.silent_hit_slow_mult = 2.2
        cfg.silent_hit_pull_mult = 4.5
        cfg.silent_hit_shake_blend = 0.75
        # ── Silent Hit QT (portado do v2) ──
        cfg.silent_hit_qt_enabled = True
        cfg.silent_hit_intensity = 8          # default configurado
        cfg.silent_hit_qt_shake_blend = 0.30
        cfg.tweak_zone_enabled = True
        cfg.tweak_zone_pct = 0.4
        cfg.tweak_zone_offset = 2.5
        cfg.rs_smoothing = 0.03
        # Gate da órbita: 500 (não 60) — com 60, qualquer encostada no stick
        # disparava a órbita e a MIRA MEXIA SOZINHA. O raio é capped em 1200
        # no engine (balanço visível). É o único fix aqui: as outras funções
        # de força ficam no MÁXIMO, como eram.
        cfg.rotational_mag_gate = 500
        cfg.rotational_radius_mult = 2.0
        cfg.ls_freq_enabled = False
        cfg.micro_adjust_enabled = True
        cfg.micro_adjust_pull = 500
        cfg.auto_track_enabled = True
        cfg.auto_track_multiplier = 0.15   # sutil (era 0.8 — rouba controle)
        cfg.auto_track_persistence_ms = 30.0  # curto (era 100ms)
        cfg.auto_track_threshold = 200     # threshold maior (era 10)
        cfg.aim_spam_enabled = False
        cfg.pd_kp = 0.3
        cfg.pd_kd = 0.15
        cfg.long_range_track_boost = 1200

        # ── Combo novo (2026): Kernel Aim BETA + LS freq + Rush ──
        # Kernel Aim: hardlock estilo kernel-mode, sem memória, só controle.
        cfg.kernel_aim_beta = True
        cfg.kernel_aim_blend = 0.9         # Forte — trava
        cfg.kernel_aim_snappiness = 0.55   # Snap moderado
        cfg.kernel_aim_smoothing_rate = 12.0
        cfg.kernel_aim_pull_max_rate_deg_s = 600.0
        cfg.kernel_aim_fov_degrees = 25.0
        cfg.kernel_aim_head_pull_deg = 3.0  # Puxa cabeça
        cfg.kernel_aim_min_input = 300.0
        # LS freq (zero analógico esquerdo): square 30Hz acima da deadzone
        # + Rush strafe — mantém o AA nativo re-disparando o tempo todo.
        cfg.ls_freq_enabled = True
        cfg.ls_freq_amplitude = 2400
        cfg.ls_freq_frequency = 30.0
        cfg.ls_freq_shape = "square"
        cfg.ls_freq_gate = 500
        cfg.ls_freq_aggressive = False
        cfg.rush_enabled = True
        cfg.rush_always = True
        cfg.rush_pulse_ms = 1.5
        cfg.rush_cooldown_ms = 80.0
        cfg.rush_deadzone = 0.13

        # ── Sistemas Avançados (3ª geração): MÁXIMO ──
        cfg.anti_recoil_ml_enabled = True
        cfg.anti_recoil_ml_strength = 1.2
        cfg.anti_recoil_ml_learning_rate = 0.015
        cfg.ballistic_predictor_enabled = True
        cfg.ballistic_predictor_strength = 1.5
        cfg.ballistic_predictor_gravity = 980.0
        cfg.smart_headshot_enabled = True
        cfg.smart_headshot_strength = 1.5
        cfg.smart_headshot_max_pull = 600.0

        # ── Sistemas Avançados 2 (4ª geração): COMBO OTIMIZADO ──
        # Multi-Polar: 4 órbitas simultâneas com raios calibrados
        # Close (shotgun/SMG): raio pequeno, freq alta = grude instantâneo
        # Medium (SMG/AR): raio médio, oval_tall = cobre torso/cabeça
        # Long (AR): raio grande, oval_wide = cobre horizontal
        # Sniper: raio máximo, spiral = estabilidade em longo alcance
        # ── Multi-Polar AGRESSIVO — estilo Eclipse V6 / Aimology ──
        # 4 órbitas simultâneas com timings diferentes = grude ABSOLUTO
        # Cada órbita cobre uma faixa de alcance e velocidade
        cfg.multi_polar_enabled = True
        # Close (shotgun/SMG): raio 8, speed 20, circle = grude instantâneo
        cfg.multi_polar_close_enabled = True
        cfg.multi_polar_close_radius = 8
        cfg.multi_polar_close_angle = 20.0
        cfg.multi_polar_close_shape = "circle"
        cfg.multi_polar_close_fire_boost = 4
        # Medium (SMG/AR): raio 12, speed 22, oval_tall = cobre torso/cabeça
        cfg.multi_polar_medium_enabled = True
        cfg.multi_polar_medium_radius = 12
        cfg.multi_polar_medium_angle = 22.0
        cfg.multi_polar_medium_shape = "oval_tall"
        cfg.multi_polar_medium_fire_boost = 5
        # Long (AR): raio 16, speed 24, oval_wide = cobre horizontal
        cfg.multi_polar_long_enabled = True
        cfg.multi_polar_long_radius = 16
        cfg.multi_polar_long_angle = 24.0
        cfg.multi_polar_long_shape = "oval_wide"
        cfg.multi_polar_long_fire_boost = 6
        # Sniper: raio 20, speed 18, spiral = estabilidade longo alcance
        cfg.multi_polar_sniper_enabled = True
        cfg.multi_polar_sniper_radius = 20
        cfg.multi_polar_sniper_angle = 18.0
        cfg.multi_polar_sniper_shape = "spiral"
        cfg.multi_polar_sniper_fire_boost = 7
        cfg.multi_polar_sniper_ads_only = True
        cfg.multi_polar_sniper_ads_only = True
        # Ghost Tracker: desacelera agressiva no bubble
        # bubble 6000 = detecta alvo perto, decel 0.5 = freia forte
        cfg.ghost_tracker_enabled = True
        cfg.ghost_tracker_bubble_radius = 6000
        cfg.ghost_tracker_decel_strength = 0.5
        cfg.ghost_tracker_decel_ramp = 0.65
        cfg.ghost_tracker_stick_threshold = 3000
        # Burst Mode: boost agressivo nos primeiros tiros
        # 3 tiros com +60% aim e -35% recoil = derruba rápido
        # Burst Mode: boost agressivo nos primeiros tiros
        # 3 tiros com +80% aim e -35% recoil = derruba rápido
        cfg.burst_mode_enabled = True
        cfg.burst_mode_count = 3
        cfg.burst_mode_aim_boost = 1.8   # +80% aim
        cfg.burst_mode_recoil_reduction = 0.65  # -35% recoil
        cfg.burst_mode_cooldown_ms = 150.0
        # Batts Sticky: diamond pattern que gruda
        # Batts Sticky: diamond pattern que gruda forte
        cfg.batts_sticky_enabled = True
        cfg.batts_sticky_ads_size = 14      # Grude em ADS
        cfg.batts_sticky_ads_fire_size = 18 # Grude forte ao atirar
        cfg.batts_sticky_hipfire_size = 22  # Largo em hipfire
        cfg.batts_sticky_ads_speed = 10.0
        cfg.batts_sticky_ads_fire_speed = 15.0
        cfg.batts_sticky_hipfire_speed = 7.0
        cfg.batts_sticky_drift_enabled = True
        cfg.batts_sticky_drift_strength = 0.4
        # XANAX AI: synergy quando 3+ mods ativos, adapta por range
        cfg.xanax_ai_enabled = True
        cfg.xanax_ai_synergy_boost = 1.25   # Synergy forte quando 3+ mods
        cfg.xanax_ai_synergy_threshold = 3
        cfg.xanax_ai_close_range_boost = 1.3  # Close range forte
        cfg.xanax_ai_long_range_boost = 0.85
        cfg.xanax_ai_close_range_threshold = 5000
        cfg.xanax_ai_long_range_threshold = 20000
        cfg.xanax_ai_humanize = True
        cfg.xanax_ai_humanize_jitter = 0.07
        cfg.xanax_ai_adapt_rate = 0.025

        # ── Warzone Aim Buffers (Modo Puro) ──
        # Vibração L3: mantém AA ativo sempre (micro-movimento no stick)
        cfg.wz_vibration_enabled = True
        cfg.wz_vibration_intensity = 60
        cfg.wz_vibration_frequency = 35.0
        cfg.wz_vibration_amplitude = 10
        cfg.wz_vibration_ads_only = False
        cfg.wz_vibration_fire_only = False
        # Warzone Aim Buffer: tracking + sticky + rotation agressivos
        # NOTA: Valores conservadores pois o pipeline já amplifica muito.
        # Tracking/sticky multiplicam o output JÁ processado pelo FN engine.
        cfg.wz_buffer_enabled = True
        cfg.wz_buffer_tracking_enabled = True
        cfg.wz_buffer_tracking_strength = 1.2    # +20% tracking
        cfg.wz_buffer_tracking_radius = 5500
        cfg.wz_buffer_sticky_enabled = True
        cfg.wz_buffer_sticky_strength = 1.15     # +15% sticky
        cfg.wz_buffer_sticky_radius = 3800
        cfg.wz_buffer_rotation_enabled = True
        cfg.wz_buffer_rotation_radius = 10       # Rotação moderada
        cfg.wz_buffer_rotation_speed = 18.0
        cfg.wz_buffer_fire_boost = 1.25          # +25% ao atirar
        cfg.wz_buffer_ads_only = False
        # Rapid Fire Puro: cadência máxima com anti-recoil
        cfg.wz_rapid_enabled = False  # Off por padrão (configurável)
        cfg.wz_rapid_speed = 85
        cfg.wz_rapid_hold_ms = 5
        cfg.wz_rapid_release_ms = 5
        cfg.wz_rapid_burst_mode = False
        cfg.wz_rapid_burst_count = 3
        cfg.wz_rapid_burst_pause_ms = 100
        cfg.wz_rapid_ads_only = False
        cfg.wz_rapid_anti_recoil = True
        cfg.wz_rapid_anti_recoil_strength = 1.3

        # ── Precision Buffer (DS4 Fluid) ──
        # SÓ anti-jitter (remove oscilações sem matar força)
        # SEM stick/aim smoothing — queremos a força INSTANTÂNEA
        cfg.precision_tracking_enabled = False  # OFF: não suaviza tracking
        cfg.precision_anti_jitter_enabled = True
        cfg.precision_anti_jitter_strength = 0.15  # era 0.2 — mais leve
        cfg.precision_anti_jitter_adaptive = True
        cfg.precision_stick_smooth_enabled = False  # OFF: input cru
        cfg.precision_aim_smooth_enabled = False     # OFF: output cru = força máxima

        return cfg

    @staticmethod
    def luna_style() -> AimAssistConfig:
        """FN Luna TEST — preset limpo pra testar as 5 camadas.

        Pipeline antigo DESLIGADO. Só as layers novas rodam.
        Para testar cada layer, ligue/desligue via config.
        """
        cfg = AimAssistPresets.fortnite_controller()

        # ── Pipeline antigo: TUDO DESLIGADO ──
        cfg.base_aa_enabled = False
        cfg.strength = 0
        cfg.zone = 0
        cfg.rotational = False
        cfg.tracking = False
        cfg.tracking_strength = 0
        cfg.sticky_enabled = False
        cfg.lock_enabled = False
        cfg.magnetic_snap = False
        cfg.magnetic_pull = 0
        cfg.micro_adjust_enabled = False
        cfg.enhanced_enabled = False
        cfg.head_assist_enabled = False
        cfg.headlock_pulse = False
        cfg.head_snap_enabled = False
        cfg.aimlock_enabled = False
        cfg.auto_rotation_enabled = False
        cfg.auto_track_enabled = False
        cfg.auto_track_multiplier = 0.0
        cfg.auto_track_persistence_ms = 0.0
        cfg.auto_track_threshold = 99999
        cfg.silent_aim_enabled = False
        cfg.silent_hit_enabled = False
        cfg.strafe_shot_enabled = False
        cfg.rush_enabled = False
        cfg.ls_freq_enabled = False
        cfg.multi_polar_enabled = False
        cfg.ghost_tracker_enabled = False
        cfg.burst_mode_enabled = False
        cfg.batts_sticky_enabled = False
        cfg.xanax_ai_enabled = False
        cfg.precision_tracking_enabled = False
        cfg.anti_flinch = False
        cfg.anti_shake_blend = 0.0
        cfg.bloom_compensation = False
        cfg.adaptive_strength = False
        cfg.oef_enabled = False
        cfg.predictive_tracker_enabled = False
        cfg.adhesion_buffer_enabled = False
        cfg.follow_assist_enabled = False
        cfg.neural_enabled = False
        cfg.pd_enabled = False
        cfg.tweak_zone_enabled = False

        # ── FN Mobile AA: DESLIGADO (camadas fazem tudo) ──
        cfg.fn_strength_slider = 0
        cfg.fn_zone = 0
        cfg.fn_slow_strength = 0.0
        cfg.fn_ramp_up_ms = 999
        cfg.fn_pull_strength = 0.0
        cfg.fn_magnet_force = 0.0
        cfg.fn_layer_strength = 0.0
        cfg.fn_rotation_cap = 0
        cfg.fn_ads_multiplier = 1.0
        cfg.fn_camera_slow_keep = 1.0
        cfg.fn_aim_pull_floor = 0.0
        cfg.fn_camera_pull_floor = 0.0
        cfg.fn_input_gate = 99999
        cfg.fn_move_pull_boost = 1.0
        cfg.fn_camera_threshold = 99999.0
        cfg.fn_camera_exit = 99999.0
        cfg.camera_layer_boost = 1.0
        cfg.fn_humanize = False
        cfg.fn_move_adhesion_boost = 1.0
        cfg.fn_move_soft_magnet_boost = 1.0

        # ── Camadas novas: CONFIGURAÇÃO DE TESTE ──
        # Layer 1 (Slowdown) — ativa por padrão no input_loop
        # Layer 2 (AimLock + Silent Aim) — ligar quando testar ADS
        # Layer 3 (CameraHit — Silent Hit) — ligar quando testar hip fire
        # Layer 4 (Track/Snap) — ligar quando testar momentum
        # Layer 5 (Sticky) — ligar quando testar persistência
        #
        # Valores de teste (conservadores — ir subindo aos poucos):
        cfg.silent_aim_enabled = True    # ativa Layer 2
        cfg.silent_aim_intensity = 7     # até tremer (era 4 — fraco demais)
        cfg.silent_hit_enabled = True    # ativa Layer 3
        cfg.silent_hit_intensity = 7     # até tremer (era 4 — fraco demais)
        cfg.lock_enabled = True          # ativa aim lock na Layer 2
        cfg.lock_strength = 12000        # moderado
        cfg.lock_fov = 8000
        cfg.lock_smooth = 0.3
        cfg.auto_track_enabled = True    # ativa Layer 4
        cfg.auto_track_multiplier = 0.15
        cfg.auto_track_threshold = 200
        cfg.auto_track_persistence_ms = 30.0
        cfg.sticky_magnet_enabled = True # ativa Layer 5
        cfg.sticky_magnet_strength = 0.25
        cfg.sticky_magnet_pull = 300

        # ── KBM ──
        cfg.kbm_mode = True
        cfg.kbm_scale = 0.50

        # ── Anti-recoil (base) ──
        cfg.enabled = True

        return cfg


AntiRecoilEngine = AimAssistEngine
AntiRecoilPattern = AimAssistPipeline
