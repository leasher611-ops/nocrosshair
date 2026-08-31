#!/usr/bin/env python3

import math
from typing import Tuple, List, Optional
from nocrosshair.core.config import StickPhysicsConfig, TriggerPhysicsConfig
from nocrosshair.core.performance import PhysicsLookupTable, LRUCache

_recoil_lut = PhysicsLookupTable()
_recoil_lut.generate_curve_table("ease_out", lambda x: 1.0 - x * x)
_recoil_lut.generate_curve_table("ease_in", lambda x: x * x)
_recoil_lut.generate_curve_table("ease_in_out", lambda x: 2 * x * x if x < 0.5 else 1 - 2 * (1 - x) * (1 - x))
_recoil_lut.generate_curve_table("exponential", lambda x: math.exp(-4.0 * x))
_recoil_lut.generate_curve_table("linear", lambda x: 1.0)

class StickPhysicsEngine:

    def __init__(self, cfg: StickPhysicsConfig):
        self.cfg = cfg
        self._cache = LRUCache(256)

    def invalidate_cache(self) -> None:
        self._cache.clear()

    def apply(self, x: int, y: int) -> Tuple[int, int]:
        cache_key = f"{x}:{y}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        if x == 0 and y == 0:
            return 0, 0

        mag_sq = x * x + y * y
        mag = math.sqrt(mag_sq)
        angle = math.atan2(y, x)
        norm_mag = min(mag / 32768.0, 1.0)

        use_same = self.cfg.use_same_xy
        if use_same:
            defl_min = self.cfg.deflection_min
            defl_max = self.cfg.deflection_max
            init_spd = self.cfg.initial_speed
            accel = self.cfg.acceleration
        else:
            px = abs(math.cos(angle))
            py = abs(math.sin(angle))
            defl_min = (self.cfg.deflection_min_x * px +
                       self.cfg.deflection_min_y * py)
            defl_max = (self.cfg.deflection_max_x * px +
                       self.cfg.deflection_max_y * py)
            init_spd = (self.cfg.initial_speed_x * px +
                       self.cfg.initial_speed_y * py)
            accel = (self.cfg.acceleration_x * px +
                    self.cfg.acceleration_y * py)

        if norm_mag < defl_min:
            return 0, 0

        if self.cfg.anti_deadzone > 0:
            adz = self.cfg.anti_deadzone / 100.0
            if norm_mag < adz:
                norm_mag = adz

        if defl_max > defl_min:
            scaled_mag = (norm_mag - defl_min) / (defl_max - defl_min)
            scaled_mag = max(0.0, min(1.0, scaled_mag))
        else:
            scaled_mag = 1.0

        curved_mag = self._apply_response_curve(scaled_mag, init_spd, accel)
        curved_mag = max(0.0, min(1.0, curved_mag))

        if self.cfg.square_stick and not self.cfg.raw_mode:
            curved_mag = self._apply_squaring(curved_mag, angle)

        out_mag = curved_mag * 32768.0
        rx = int(out_mag * math.cos(angle))
        ry = int(out_mag * math.sin(angle))

        rx = max(-32768, min(32767, rx))
        ry = max(-32768, min(32767, ry))

        result = (rx, ry)
        self._cache.put(cache_key, result)
        return result

    def _apply_squaring(self, mag: float, angle: float) -> float:
        factor = self.cfg.squaring_factor
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)

        max_r_square = 1.0
        if abs(cos_a) > 0.0001 or abs(sin_a) > 0.0001:
            candidates = []
            if abs(cos_a) > 0.0001:
                candidates.append(1.0 / abs(cos_a))
            if abs(sin_a) > 0.0001:
                candidates.append(1.0 / abs(sin_a))
            max_r_square = min(candidates) if candidates else 1.0

        stretch = 1.0 + (max_r_square - 1.0) * factor
        mag *= stretch
        mag = min(mag, max_r_square)

        return mag

    def _apply_response_curve(self, scaled_mag: float, init_spd: float, accel: float) -> float:
        curve = self.cfg.response_curve
        if curve == "raw":
            return scaled_mag
        elif curve == "exponential":
            return scaled_mag ** (2.0 * accel)
        elif curve == "aggressive":
            return init_spd + (1.0 - init_spd) * (scaled_mag ** max(0.1, accel * 0.7))
        elif curve == "precise":
            return scaled_mag ** (0.5 * accel) if scaled_mag < 0.5 else 0.5 + 0.5 * ((scaled_mag - 0.5) / 0.5) ** accel
        elif curve == "dynamic":
            # Curva dinâmica: suave no centro, rápida nas bordas
            # Similar ao "Dynamic" do Fortnite/CoD
            if scaled_mag < 0.3:
                return scaled_mag ** (1.8 * accel)
            elif scaled_mag < 0.7:
                return 0.3 ** (1.8 * accel) + (scaled_mag - 0.3) * (0.7 - 0.3 ** (1.8 * accel)) / 0.4
            else:
                return 0.3 ** (1.8 * accel) + 0.4 + (scaled_mag - 0.7) ** (0.5 / accel) * 0.3
        elif curve == "smooth":
            # Curva suave: resposta proporcional com easing nas bordas
            # Mais fluido que linear, menos agressivo que dynamic
            return scaled_mag ** (1.0 / max(0.5, accel))
        elif curve == "fluid":
            # Curva fluida:combinação de smooth + anti-stick
            # Suave no centro, responsivo no meio, estabilizado nas bordas
            if scaled_mag < 0.15:
                return scaled_mag * 0.6  # Centro muito suave
            elif scaled_mag < 0.5:
                return 0.09 + (scaled_mag - 0.15) * 1.8  # Transição responsiva
            elif scaled_mag < 0.85:
                return 0.09 + 0.63 + (scaled_mag - 0.5) * 1.0  # Meio linear
            else:
                return 0.09 + 0.63 + 0.35 + (scaled_mag - 0.85) * 0.33  # Bordas estabilizadas
        else:
            return init_spd + (1.0 - init_spd) * (scaled_mag ** accel)

class TriggerPhysicsEngine:

    def __init__(self, cfg: TriggerPhysicsConfig):
        self.cfg = cfg

    def apply(self, value_in: int) -> int:
        nv = value_in / 255.0

        if self.cfg.hair_trigger:
            return 255 if nv > 0.0 else 0

        dz = self.cfg.deadzone
        if nv < dz:
            return 0

        sens = self.cfg.sensitivity
        scaled = (nv - dz) / (1.0 - dz) if dz < 1.0 else 1.0
        scaled = max(0.0, min(1.0, scaled))

        out_val = int((scaled ** sens) * 255.0)
        return max(0, min(255, out_val))

class PhysicsTestbed:

    def __init__(self, physics_engine: StickPhysicsEngine):
        self.physics_engine = physics_engine

    def simulate_input(self, x: int, y: int) -> Tuple[int, int]:
        return self.physics_engine.apply(x, y)

    def apply_config(self, config: StickPhysicsConfig) -> None:
        self.physics_engine = StickPhysicsEngine(config)

    def get_curve_points(self, samples: int = 25) -> List[Tuple[float, float]]:
        points = []
        total = max(samples - 1, 1)
        for i in range(samples):
            input_norm = i / total
            raw = int(input_norm * 32767)
            out_x, out_y = self.simulate_input(raw, 0)
            output_norm = min(math.sqrt(out_x * out_x + out_y * out_y) / 32768.0, 1.0)
            points.append((input_norm, output_norm))
        return points

def apply_curve_multipoint(raw: int, points: List[Tuple[int, int]],
                          scale_factor: float = 1.0) -> int:
    if raw == 0:
        return 0

    sign = 1 if raw > 0 else -1
    abs_val = abs(raw)

    if abs_val < points[0][0]:
        t = abs_val / points[0][0]
        return int(sign * t * points[0][1] * scale_factor)

    if abs_val >= points[-1][0]:
        return int(sign * points[-1][1] * scale_factor)

    for i in range(len(points) - 1):
        x0, y0 = points[i]
        x1, y1 = points[i + 1]
        if x0 <= abs_val < x1:
            t = (abs_val - x0) / (x1 - x0)
            y = y0 + t * (y1 - y0)
            return int(sign * y * scale_factor)

    return int(sign * points[-1][1] * scale_factor)

def apply_recoil_curve_factor(tick: int, total_ticks: int, curve_type: str) -> float:
    t = tick / max(total_ticks - 1, 1)
    return _recoil_lut.get_curve_value(curve_type, t)

class StickPhysicsPresets:

    @staticmethod
    def fps() -> StickPhysicsConfig:
        return StickPhysicsConfig(
            deflection_min=0.0,
            deflection_max=1.0,
            initial_speed=0.0,
            acceleration=1.0,
        )

    @staticmethod
    def platformer() -> StickPhysicsConfig:
        return StickPhysicsConfig(
            deflection_min=0.15,
            deflection_max=1.0,
            initial_speed=0.2,
            acceleration=1.5,
        )

    @staticmethod
    def racing() -> StickPhysicsConfig:
        return StickPhysicsConfig(
            use_same_xy=False,
            deflection_min_x=0.1,
            deflection_max_x=0.95,
            acceleration_x=1.2,
            deflection_min_y=0.05,
            deflection_max_y=1.0,
            acceleration_y=0.8,
        )

    @staticmethod
    def simulation() -> StickPhysicsConfig:
        return StickPhysicsConfig(
            deflection_min=0.0,
            deflection_max=1.0,
            initial_speed=0.0,
            acceleration=2.0,
        )

class TriggerPhysicsPresets:

    @staticmethod
    def normal() -> TriggerPhysicsConfig:
        return TriggerPhysicsConfig(
            deadzone=0.05,
            sensitivity=1.0,
            hair_trigger=False,
        )

    @staticmethod
    def hair() -> TriggerPhysicsConfig:
        return TriggerPhysicsConfig(
            deadzone=0.0,
            sensitivity=1.0,
            hair_trigger=True,
        )

    @staticmethod
    def sensitive() -> TriggerPhysicsConfig:
        return TriggerPhysicsConfig(
            deadzone=0.02,
            sensitivity=1.2,
            hair_trigger=False,
        )
