#!/usr/bin/env python3

import math
import time
from typing import Tuple, Dict, Any, Optional
from dataclasses import dataclass
from collections import deque
from nocrosshair.core.config import AimAssistConfig


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


class RushEngine:
    def __init__(self, pulse_ms: float = 1.5, cooldown_ms: float = 80.0,
                 deadzone: float = 0.13):
        self._active = False
    def set_active(self, active: bool) -> None:
        self._active = active
    def get_strafe(self, now: float) -> int:
        return 0
    def update_config(self, pulse_ms: float, cooldown_ms: float, deadzone: float) -> None:
        pass
    def reset(self) -> None:
        self._active = False


class AutoTrackEngine:
    def __init__(self):
        self._persist_rx: float = 0.0
        self._persist_ry: float = 0.0
        self._persist_until: float = 0.0

    def apply(self, rx: int, ry: int, enabled: bool, multiplier: float,
              threshold: int, persistence_ms: float) -> Tuple[int, int]:
        if not enabled or multiplier <= 0:
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

    def apply(self, rx: float, ry: float, level: int, delta_ms: float) -> Tuple[float, float]:
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
        attenuation = max(0.05, 1.0 - (mag / 10000.0))
        pulse = attenuation * radius
        rx += math.cos(self._angle) * pulse
        ry += math.sin(self._angle) * pulse
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
        if not is_shooting and not is_aiming:
            self._flinch_active = False
            self._correction_remaining = 0
            self._correction = 0
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


class AimAssistEngine:

    def __init__(self, cfg: AimAssistConfig):
        self.cfg = cfg
        self._auto_rot_angle: float = 0.0
        self._adaptive_engage: float = 0.0
        self._predict_prev_rx: int = 0
        self._predict_prev_ry: int = 0

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
        slowdown = max(0.20, 1.0 - (effective_strength / 10000.0) * (1.0 - zone_factor))
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
            snap_f = max(0.05, snap_curve - extra * 0.15)
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

    def apply_predict(self, rx: int, ry: int, config: AimAssistConfig,
                      prev_rx: int, prev_ry: int, delta_ms: float) -> Tuple[int, int]:
        mag = math.sqrt(rx**2 + ry**2)
        if mag < 300:
            return rx, ry
        vel_x = (rx - self._predict_prev_rx) / max(delta_ms, 1)
        vel_y = (ry - self._predict_prev_ry) / max(delta_ms, 1)
        self._predict_prev_rx, self._predict_prev_ry = rx, ry
        frames = config.prediction_frames
        lead_x = int(vel_x * frames * 0.5)
        lead_y = int(vel_y * frames * 0.5)
        lead_mag = math.sqrt(lead_x**2 + lead_y**2)
        max_lead = config.long_range_predict_lead
        if lead_mag > max_lead:
            scale = max_lead / lead_mag
            lead_x = int(lead_x * scale)
            lead_y = int(lead_y * scale)
        rx += lead_x
        ry += lead_y
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
                 soft_magnet_force: float = 0.5, ramp_up_ms: float = 150.0):
        self.pull_strength = pull_strength
        self.slow_strength = slow_strength
        self.soft_magnet_force = soft_magnet_force
        self.ramp_up_ms = ramp_up_ms
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
            self._cam_blend = min(1.0, self._cam_blend + delta_ms / max(1.0, self.ramp_up_ms))
            self._aim_blend = max(0.0, self._aim_blend - delta_ms / 80.0)
            if mag > 500:
                target_pull_x = rx * (self.pull_strength * 0.18)
                target_pull_y = ry * (self.pull_strength * 0.18)
                interp_speed = 10.0 * (delta_ms / 1000.0)
                self._cam_pull_x += (target_pull_x - self._cam_pull_x) * min(1.0, interp_speed)
                self._cam_pull_y += (target_pull_y - self._cam_pull_y) * min(1.0, interp_speed)
            rx_out = rx + self._cam_pull_x * self._cam_blend * 0.25
            ry_out = ry + self._cam_pull_y * self._cam_blend * 0.25
            dominant_x = abs(rx) > abs(ry)
            adhesion = 0.08 * self.pull_strength * self._cam_blend
            if dominant_x:
                ry_out = ry_out * (1.0 - adhesion)
            else:
                rx_out = rx_out * (1.0 - adhesion)
            return (max(-32768.0, min(32767.0, rx_out)),
                    max(-32768.0, min(32767.0, ry_out)))
        else:
            self._aim_blend = min(1.0, self._aim_blend + delta_ms / max(1.0, self.ramp_up_ms * 0.7))
            self._cam_blend = max(0.0, self._cam_blend - delta_ms / 60.0)
            slow_factor = 1.0 - (self.slow_strength * 0.42 * self._aim_blend)
            rx_out = rx * slow_factor
            ry_out = ry * slow_factor
            if mag > 50:
                target_pull_x = rx * (self.pull_strength * 0.12)
                target_pull_y = ry * (self.pull_strength * 0.12)
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
                rx_out += magnet_yaw * (self.soft_magnet_force * 1.05) * self._aim_blend
                ry_out += magnet_pitch * (self.soft_magnet_force * 1.05) * self._aim_blend
            return (max(-32768.0, min(32767.0, rx_out)),
                    max(-32768.0, min(32767.0, ry_out)))


class AimAssistPipeline:

    def __init__(self, aa_engine: AimAssistEngine, _jitter=None):
        self.aa_engine = aa_engine
        self.fortnite_engine = FortniteMobileAimAssist()
        self.pulse_engine = PulseLevelEngine()
        self.auto_track_engine = AutoTrackEngine()
        self.anti_flinch = AntiFlinchEngine()
        self.raa_angle: float = 0.0
        self._prev_error_x: float = 0.0
        self._prev_error_y: float = 0.0
        self._smooth_prev_rx: int = 0
        self._smooth_prev_ry: int = 0
        self._last_aim_time: float = 0.0
        self._adaptive_engage: float = 0.0
        self._track_pulse_active: bool = False
        self._track_pulse_start: float = 0.0

    def apply(self, rx: float, ry: float, is_shooting: bool,
              is_aiming: bool, is_moving: bool, delta_ms: float,
              config: AimAssistConfig, prev_rx: float, prev_ry: float) -> tuple[float, float]:
        if not config.enabled:
            return rx, ry

        irx, iry = int(rx), int(ry)

        layer = config.fn_layer_strength
        self.fortnite_engine.pull_strength = config.fn_pull_strength * layer
        self.fortnite_engine.slow_strength = config.fn_slow_strength * layer
        self.fortnite_engine.soft_magnet_force = config.fn_magnet_force * layer
        self.fortnite_engine.ramp_up_ms = config.fn_ramp_up_ms
        self.fortnite_engine.CAMERA_THRESHOLD = config.fn_camera_threshold
        self.fortnite_engine.CAMERA_EXIT_THRESHOLD = config.fn_camera_exit
        irx_f, iry_f = self.fortnite_engine.process(irx, iry, is_shooting, is_aiming, is_moving, delta_ms)
        irx, iry = int(irx_f), int(iry_f)

        irx, iry = self._apply_base_aa(irx, iry, config, prev_rx, prev_ry, is_aiming, delta_ms)

        if config.anti_flinch:
            irx, iry = self.anti_flinch.process(irx, iry, config.anti_flinch_strength,
                                                is_shooting, is_aiming)

        if config.adaptive_strength:
            irx, iry = self._apply_adaptive_strength(irx, iry, config, is_shooting)

        if config.rotational:
            if config.aim_type == "still":
                mag = math.sqrt(irx**2 + iry**2)
                if mag < 1000:
                    irx, iry = self._apply_rotational_aa(irx, iry, delta_ms, config)
            else:
                irx, iry = self._apply_rotational_aa(irx, iry, delta_ms, config)

        irx, iry = self.aa_engine.apply_anti_shake(
            irx, iry, self._smooth_prev_rx, self._smooth_prev_ry, config.anti_shake_blend)

        self._smooth_prev_rx, self._smooth_prev_ry = irx, iry
        return float(irx), float(iry)

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

    def _apply_rotational_aa(self, rx: float, ry: float, delta_ms: float,
                             config: AimAssistConfig) -> tuple[float, float]:
        mag = math.sqrt(rx**2 + ry**2)
        if mag < 500:
            return rx, ry

        radius = config.zone // 4
        if config.power_boost:
            radius = int(radius * config.power_mult)

        angle_step = 0.30 * (1.0 / max(0.01, 1.0 - mag / 20000.0))
        self.raa_angle += angle_step
        if self.raa_angle > 2 * math.pi:
            self.raa_angle -= 2 * math.pi

        attenuation = max(0.05, 1.0 - (mag / 10000.0))

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

        rx += cx * radius * attenuation
        ry += cy * radius * attenuation

        rx, ry = self.pulse_engine.apply(rx, ry, config.pulse_level, delta_ms)
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
            strength=8500,
            ads_multiplier=1.05,
            zone=5000,
            rotational=True,
            pulse_level=0,
            aim_type="flow",
            magnetic_snap=True,
            snap_strength=300,
            snap_duration=80,
            tracking=True,
            tracking_strength=1500,
            tracking_speed=0,
            track_ads_pulse_ms=240,
            sticky_enabled=False,
            rush_enabled=False,
            power_boost=False,
            power_mult=1.0,
            lock_enabled=False,
            shape_mode="circular",
            aim_pattern="standard",
            anti_shake_blend=0.30,
            magnetic_pull=1500,
            anti_flinch=True,
            anti_flinch_strength=3000,
            zero_delay=True,
            zero_delay_ms=40,
            bloom_compensation=True,
            strafe_shot_enabled=True,
            strafe_shot_amplitude=100,
            strafe_shot_frequency=8.0,
            strafe_shot_shape="sine",
            fn_layer_strength=1.0,
            auto_track_enabled=True,
            auto_track_multiplier=0.6,
            auto_track_persistence_ms=60.0,
            auto_track_threshold=20,
            fn_pull_strength=1.0,
            fn_slow_strength=0.8,
            fn_magnet_force=0.5,
            fn_ramp_up_ms=150.0,
            fn_camera_threshold=18000.0,
            fn_camera_exit=14000.0,
        )


AntiRecoilEngine = AimAssistEngine
AntiRecoilPattern = AimAssistPipeline
