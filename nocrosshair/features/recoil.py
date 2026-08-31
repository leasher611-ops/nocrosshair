import math
import time
import unicodedata
from typing import Dict, Any, Tuple, Optional, List
from dataclasses import dataclass, field
from collections import deque

from nocrosshair.core.config import RecoilConfig, RECOIL_PRESETS, WEAPON_ALIASES
from nocrosshair.features.physics import apply_recoil_curve_factor


def normalize_weapon_name(name: str) -> str:
    """Normaliza nome de arma: caixa baixa, sem acentos, espaços colapsados."""
    nfkd = unicodedata.normalize("NFKD", name)
    plain = "".join(c for c in nfkd if not unicodedata.combining(c))
    return " ".join(plain.lower().split())


@dataclass
class BezierCurve:
    p0: float
    p1: float
    p2: float
    p3: float

    def evaluate(self, t: float) -> float:
        t = max(0.0, min(1.0, t))
        mt = 1.0 - t
        return (mt**3 * self.p0 + 3 * mt**2 * t * self.p1 + 3 * mt * t**2 * self.p2 + t**3 * self.p3)

    def derivative(self, t: float) -> float:
        t = max(0.0, min(1.0, t))
        mt = 1.0 - t
        return (3 * mt**2 * (self.p1 - self.p0) + 6 * mt * t * (self.p2 - self.p1) + 3 * t**2 * (self.p3 - self.p2))


@dataclass
class RecoilPattern:
    name: str
    category: str = "AR"
    points: List[Tuple[int, int, int]] = field(default_factory=list)
    total_ticks: int = 60

    def get_offset_at_tick(self, tick: int) -> Tuple[int, int]:
        if not self.points:
            return 0, 0
        tick = max(0, min(tick, self.total_ticks - 1))
        prev_point = self.points[0]
        next_point = self.points[-1]
        for i, point in enumerate(self.points):
            if point[0] >= tick:
                next_point = point
                if i > 0:
                    prev_point = self.points[i - 1]
                break
            prev_point = point
        if prev_point[0] == next_point[0]:
            return prev_point[1], prev_point[2]
        t = (tick - prev_point[0]) / (next_point[0] - prev_point[0])
        y = int(prev_point[1] + (next_point[1] - prev_point[1]) * t)
        x = int(prev_point[2] + (next_point[2] - prev_point[2]) * t)
        return y, x


DEFAULT_PATTERNS: Dict[str, RecoilPattern] = {}

# Escala do Simple Mode: 1 "px" (MoveMouseRelative) = 90 unidades do stick,
# o mesmo escalonamento do strength do engine (1 strength = 90/tick).
SIMPLE_UNITS_PER_PX = 90

def _generate_default_patterns():
    for name, preset in RECOIL_PRESETS.items():
        strength = preset.get("strength", 0)
        x_strength = preset.get("x_strength", 0)
        ticks = preset.get("ticks", 60)
        category = preset.get("category", "AR")
        points = []
        for i in range(0, ticks, max(1, ticks // 10)):
            progress = i / max(ticks - 1, 1)
            y = int(strength * 90 * (1.0 - progress * 0.5))
            x = int(x_strength * 90 * math.sin(progress * math.pi))
            points.append((i, y, x))
        points.append((ticks - 1, int(strength * 45), 0))
        DEFAULT_PATTERNS[name] = RecoilPattern(
            name=name,
            category=category,
            points=points,
            total_ticks=ticks,
        )

_generate_default_patterns()


@dataclass
class AntiRecoilState:
    active: bool = False
    tick: int = 0
    last_y_offset: float = 0.0
    last_x_offset: float = 0.0
    ema_y: float = 0.0
    ema_x: float = 0.0
    burst_count: int = 0
    spray_start: float = 0.0


class RecoilState:

    def __init__(self):
        self.tick = 0
        self.delay_remaining = 0
        self.return_offset_y = 0
        self.return_offset_x = 0
        self.last_offset_y = 0
        self.last_offset_x = 0

    def reset(self, delay_ms: float) -> None:
        self.tick = 0
        self.delay_remaining = delay_ms
        self.return_offset_y = 0
        self.return_offset_x = 0
        self.last_offset_y = 0
        self.last_offset_x = 0

    def advance_tick(self, delta_ms: float) -> bool:
        if self.delay_remaining > 0:
            self.delay_remaining -= delta_ms
            return False
        return True

    def capture_offset(self, y_offset: int, x_offset: int) -> None:
        self.last_offset_y = y_offset
        self.last_offset_x = x_offset

    def apply_return(self, return_speed: float) -> Tuple[int, int]:
        if self.return_offset_y != 0:
            self.return_offset_y = int(self.return_offset_y * return_speed)
            if abs(self.return_offset_y) < 150:
                self.return_offset_y = 0
        if self.return_offset_x != 0:
            self.return_offset_x = int(self.return_offset_x * return_speed)
            if abs(self.return_offset_x) < 150:
                self.return_offset_x = 0
        return self.return_offset_y, self.return_offset_x


class RecoilAdaptEngine:
    MAX_MULTIPLIERS = {0: 1.0, 1: 1.15, 2: 1.30, 3: 1.50}
    RAMP_SHOTS = {0: 1, 1: 8, 2: 6, 3: 4}

    def __init__(self):
        self._consecutive_shots = 0

    def reset(self) -> None:
        self._consecutive_shots = 0

    def get_multiplier(self, level: int, is_shooting: bool) -> float:
        if level == 0 or not is_shooting:
            return 1.0
        self._consecutive_shots += 1
        max_mult = self.MAX_MULTIPLIERS.get(level, 1.0)
        ramp_shots = self.RAMP_SHOTS.get(level, 1)
        progress = min(1.0, self._consecutive_shots / ramp_shots)
        return 1.0 + (max_mult - 1.0) * progress


class SmartLearnEngine:
    WEAPON_CATEGORIES = {
        "AR": ["M416", "SCAR", "AK", "AUG", "G36", "FAMAS", "AR"],
        "SMG": ["MP5", "UMP", "P90", "VECTOR", "SMG"],
        "LMG": ["LMG", "M249", "RPD"],
        "SNIPER": ["KAR", "AWM", "SNIPER"],
        "PISTOL": ["DEAGLE", "PISTOL", "HANDGUN"],
    }

    def __init__(self):
        self._v_mult: Dict[str, float] = {}
        self._h_mult: Dict[str, float] = {}
        self._samples: Dict[str, List[Tuple[int, int]]] = {}

    def get_category(self, weapon: str) -> str:
        upper = weapon.upper()
        for cat, weapons in self.WEAPON_CATEGORIES.items():
            for w in weapons:
                if w in upper:
                    return cat
        return "AR"

    def observe(self, weapon: str, ry_raw: int, rx_raw: int,
                is_shooting: bool) -> None:
        if not is_shooting:
            return
        cat = self.get_category(weapon)
        if cat not in self._samples:
            self._samples[cat] = []
        self._samples[cat].append((ry_raw, rx_raw))
        if len(self._samples[cat]) > 60:
            self._samples[cat].pop(0)

    def compute_multipliers(self, weapon: str) -> Tuple[float, float]:
        cat = self.get_category(weapon)
        samples = self._samples.get(cat, [])
        if len(samples) < 10:
            return 1.0, 1.0
        recent = samples[-20:]
        n = len(recent)
        avg_ry = sum(s[0] for s in recent) / n
        avg_rx = sum(s[1] for s in recent) / n
        v_adj = 1.0 + (avg_ry / 30000.0) * 0.15
        h_adj = 1.0 + (avg_rx / 30000.0) * 0.15
        v_mult = max(0.70, min(1.30, v_adj))
        h_mult = max(0.70, min(1.30, h_adj))
        if cat in self._v_mult:
            v_mult = self._v_mult[cat] * 0.95 + v_mult * 0.05
        if cat in self._h_mult:
            h_mult = self._h_mult[cat] * 0.95 + h_mult * 0.05
        self._v_mult[cat] = v_mult
        self._h_mult[cat] = h_mult
        return v_mult, h_mult

    def get_stats(self) -> dict:
        return {
            "v_mult": dict(self._v_mult),
            "h_mult": dict(self._h_mult),
            "samples": {k: len(v) for k, v in self._samples.items()},
        }


class RecoilEngine:
    EMA_FACTOR = 0.35
    MAX_MULT_BOOST = 2.5

    def __init__(self, config=None):
        self.active_preset: str = "M416"
        self.custom_presets: Dict[str, Dict[str, Any]] = {}
        self.config = config or RecoilConfig()
        self.runtime = None
        self.state = AntiRecoilState()
        self._weapon: str = "M416"
        self._pattern: Optional[RecoilPattern] = DEFAULT_PATTERNS.get("M416")
        self._custom_patterns: Dict[str, RecoilPattern] = {}
        self._active_delay_ms: float = float(self.config.delay_ms)
        self._active_return_speed: float = float(self.config.return_speed)
        self._sm_active_pattern = None
        self._sm_current_tick = 0
        self._sm_total_ticks = 60
        self._sm_delay_remaining = 0.0
        self._sm_curves: Dict[str, BezierCurve] = {}
        self._sm_smoothing_buffer = deque(maxlen=5)
        self._adapt: RecoilAdaptEngine = RecoilAdaptEngine()
        self._smart_learn: SmartLearnEngine = SmartLearnEngine()

    # ── Old RecoilEngine API ──

    def set_preset(self, preset_name: str) -> None:
        normalized = preset_name.upper()
        if normalized in RECOIL_PRESETS:
            self.active_preset = normalized

    def set_custom_presets(self, presets: Dict[str, Dict[str, Any]]) -> None:
        self.custom_presets = presets

    def get_preset(self, preset_name: str) -> Dict[str, Any]:
        default = next(iter(RECOIL_PRESETS.values()))
        base = RECOIL_PRESETS.get(preset_name.upper(), default)
        if preset_name.upper() in self.custom_presets:
            return {**base, **self.custom_presets[preset_name.upper()]}
        return base

    def apply_tick(self, tick: int, total_ticks: int,
                   ry_raw: int, rx_raw: int,
                   preset: Dict[str, Any],
                   recoil_y_gate: bool = True) -> Tuple[int, int]:
        tick = max(0, min(tick, total_ticks - 1))
        strength = preset.get("strength", 0)
        x_strength = preset.get("x_strength", 0)
        curve = preset.get("curve", "ease_out")

        y_offset = 0
        x_offset = 0

        if strength != 0:
            factor = apply_recoil_curve_factor(tick, total_ticks, curve)
            base = int(strength * 90 * factor)
            y_offset = min(base, 18000)

            if recoil_y_gate and abs(ry_raw) > 0:
                gate = max(0.15, 1.0 - abs(ry_raw) / 16000.0)
                y_offset = int(y_offset * gate)

        if x_strength != 0:
            factor = apply_recoil_curve_factor(tick, total_ticks, curve)
            base = int(x_strength * 90 * factor)
            x_offset = max(-18000, min(18000, base))

            if abs(rx_raw) > 2000:
                x_gate = max(0.0, 1.0 - abs(rx_raw) / 16000.0)
                x_offset = int(x_offset * x_gate)

        return y_offset, x_offset

    # ── AntiRecoilEngine API ──

    def set_weapon(self, weapon_name: str) -> None:
        self._weapon = weapon_name
        normalized = normalize_weapon_name(weapon_name)
        canonical = WEAPON_ALIASES.get(normalized, "")
        pattern = (
            self._custom_patterns.get(weapon_name) or
            DEFAULT_PATTERNS.get(weapon_name) or
            DEFAULT_PATTERNS.get(normalized.upper()) or
            DEFAULT_PATTERNS.get(canonical)
        )
        if pattern is not None and canonical:
            self._weapon = canonical
        if pattern is None:
            for preset_name, preset in RECOIL_PRESETS.items():
                if normalize_weapon_name(preset_name) == normalized:
                    pattern = DEFAULT_PATTERNS.get(preset_name)
                    self._weapon = preset_name
                    break
        if pattern is None:
            # Auto Detect por categoria: se o nome não é um preset exato,
            # resolve para o primeiro preset da mesma categoria (AR, SMG...).
            category = weapon_name.upper()
            for name, preset in RECOIL_PRESETS.items():
                if preset.get("category", "").upper() == category:
                    pattern = DEFAULT_PATTERNS.get(name)
                    self._weapon = name
                    break
        self._pattern = pattern
        # Perfil por arma: delay e return vêm do preset da arma quando existem
        preset = RECOIL_PRESETS.get(self._weapon, {})
        self._active_delay_ms = float(preset.get("delay_ms", self.config.delay_ms))
        self._active_return_speed = float(preset.get("return_speed", self.config.return_speed))

    def update_runtime(self, runtime) -> None:
        self.runtime = runtime

    def add_custom_pattern(self, pattern: RecoilPattern) -> None:
        self._custom_patterns[pattern.name] = pattern

    # Bloom ramps over this many seconds of continuous spray while moving
    BLOOM_RAMP_S = 0.40
    BLOOM_Y_BASE = 0.20   # +20% Y when moving (start of spray)
    BLOOM_X_BASE = 0.15   # +15% X when moving
    BLOOM_Y_EXTRA = 0.10  # additional +10% Y at full ramp
    BLOOM_X_EXTRA = 0.08  # additional +8% X at full ramp
    BLOOM_ADS_SCALE = 0.70  # ADS reduces bloom compensation (tighter cone)

    def process(self, tick: int, is_shooting: bool, is_aiming: bool,
                is_moving: bool, ry_raw: int, rx_raw: int,
                delta_ms: float, bloom_compensation: bool = True) -> Tuple[int, int]:
        if not self.config.enabled:
            return 0, 0

        # ── Simple Mode (estilo script LUA do Logitech G-Hub) ──
        # Pull plano e constante: MoveMouseRelative(0, rate) a cada 7ms
        # enquanto atira. Sem curva, sem pattern, sem EMA — do primeiro tiro.
        if self.config.simple_mode:
            self._adapt.reset()
            if not is_shooting:
                self.state.ema_y = 0
                self.state.ema_x = 0
                self.state.active = False
                return 0, 0
            if not self.state.active:
                self.state.active = True
                self.state.tick = 0
            self.state.tick = tick
            pull = self.config.simple_rate * SIMPLE_UNITS_PER_PX * (delta_ms / 7.0)
            y_out = max(-18000, min(18000, int(pull)))
            if self.config.headshot_assist and not is_aiming:
                y_out = max(-18000, y_out - self.config.headshot_assist_pull)
            return y_out, 0

        if not is_shooting:
            # ── Return (estilo Zen) ──
            # Ao soltar o gatilho o retículo "volta" progressivamente:
            # o EMA decai com a return_speed do preset da arma em vez do
            # 0.7 fixo — assim o engajamento seguinte começa de onde o
            # retículo naturalmente assentou, sem salto.
            self._adapt.reset()
            rs = self._active_return_speed
            self.state.ema_y *= rs
            self.state.ema_x *= rs
            if abs(self.state.ema_y) < 50:
                self.state.ema_y = 0
            if abs(self.state.ema_x) < 50:
                self.state.ema_x = 0
            self.state.active = False
            self.state.burst_count = 0
            return int(self.state.ema_y), int(self.state.ema_x)

        if not self.state.active:
            self.state.active = True
            self.state.tick = 0
            self.state.spray_start = time.monotonic()
            self.state.burst_count = 0

        # ── Delay do primeiro tiro (perfil da arma) ──
        # Armas com first-shot kick alto esperam o tiro "assentar" antes de
        # começar a puxar. O preset da arma define (ex.: SPIRE RIFLE 60ms).
        # Híbrido tick + wall-clock: no jogo vale o tempo real; nos testes o
        # tick (determinístico) desbloqueia mesmo sem relógio avançar.
        if self._active_delay_ms > 0:
            spray_elapsed_ms = (time.monotonic() - self.state.spray_start) * 1000.0
            delay_ticks = max(1, int(self._active_delay_ms / 16.67))
            if tick < delay_ticks and spray_elapsed_ms < self._active_delay_ms:
                return int(self.state.ema_y), int(self.state.ema_x)

        # ── Burst Mode (rajada com reset) ──
        # Aplica pull apenas em janelas de rajada e pausa entre elas: simula
        # o tap-fire (o recoil do jogo reseta na pausa e a 1ª bala de cada
        # rajada sai com spread mínimo). Ideal pra AR em média distância.
        runtime = self.runtime
        burst_mode = bool(runtime.burst_mode) if runtime else False
        if burst_mode:
            burst_count = int(runtime.burst_count) if runtime else 3
            off_ticks = max(1, int((runtime.burst_delay_ms if runtime else 50) / 16.67))
            phase = self.state.burst_count % max(1, burst_count + off_ticks)
            self.state.burst_count += 1
            if phase >= burst_count:
                # Pausa da rajada: pull ZERO — o recoil do jogo reseta na pausa
                self.state.ema_y = 0
                self.state.ema_x = 0
                return 0, 0

        if self._pattern:
            raw_y, raw_x = self._pattern.get_offset_at_tick(tick)
        else:
            progress = tick / max(self.config.ticks, 1)
            factor = apply_recoil_curve_factor(tick, self.config.ticks, self.config.curve)
            raw_y = int(self.config.strength * 90 * factor)
            raw_x = int(self.config.x_strength * 90 * math.sin(progress * math.pi))

        # ── Teto de boost (predictabilidade) ──
        # Todos os multiplicadores abaixo (kick, bloom, hipfire, adapt,
        # smart_learn) juntos não podem passar de MAX_MULT_BOOST sobre o
        # valor base do padrão — senão o pull vira imprevisível de tunar.
        base_y, base_x = raw_y, raw_x

        # ── Initial Kick (estilo Titan Two) ──
        # Muitas armas têm "first shot kick" forte: nos primeiros ticks de
        # spray aplicamos um multiplicador extra que decai linearmente até
        # 1.0. Default 1.0 = sem efeito (comportamento original).
        if self.config.initial_kick_mult != 1.0:
            kick_progress = min(1.0, tick / max(self.config.initial_kick_ticks, 1))
            kick_mult = self.config.initial_kick_mult - (self.config.initial_kick_mult - 1.0) * kick_progress
            raw_y = int(raw_y * kick_mult)
            raw_x = int(raw_x * kick_mult)

        # ── Bloom compensation (AUREN+ style) ──
        # Extra pull while strafing; ramps during sustained spray; weaker under ADS.
        if bloom_compensation and is_moving:
            spray_elapsed = max(0.0, time.monotonic() - self.state.spray_start)
            ramp = min(1.0, spray_elapsed / self.BLOOM_RAMP_S)
            y_mult = 1.0 + self.BLOOM_Y_BASE + self.BLOOM_Y_EXTRA * ramp
            x_mult = 1.0 + self.BLOOM_X_BASE + self.BLOOM_X_EXTRA * ramp
            if is_aiming:
                y_mult = 1.0 + (y_mult - 1.0) * self.BLOOM_ADS_SCALE
                x_mult = 1.0 + (x_mult - 1.0) * self.BLOOM_ADS_SCALE
            raw_y = int(raw_y * y_mult)
            raw_x = int(raw_x * x_mult)

        if not is_aiming:
            raw_y = int(raw_y * 1.4)
            raw_x = int(raw_x * 1.3)

        if self.config.y_gate and abs(ry_raw) > 0:
            gate = max(0.15, 1.0 - abs(ry_raw) / 16000.0)
            raw_y = int(raw_y * gate)

        if abs(rx_raw) > 2000:
            x_gate = max(0.15, 1.0 - abs(rx_raw) / 16000.0)
            raw_x = int(raw_x * x_gate)

        adapt_mult = self._adapt.get_multiplier(self.config.recoil_adapt, is_shooting)
        if adapt_mult != 1.0:
            raw_y = int(raw_y * adapt_mult)
            raw_x = int(raw_x * adapt_mult)

        if self.config.smart_learn:
            self._smart_learn.observe(self._weapon, ry_raw, rx_raw, is_shooting)
            sl_v, sl_h = self._smart_learn.compute_multipliers(self._weapon)
            if sl_v != 1.0 or sl_h != 1.0:
                raw_y = int(raw_y * sl_v)
                raw_x = int(raw_x * sl_h)

        def _cap(raw: int, base: int) -> int:
            if base == 0:
                return raw
            limit = abs(int(base * self.MAX_MULT_BOOST))
            return max(-limit, min(limit, raw))

        raw_y = _cap(raw_y, base_y)
        raw_x = _cap(raw_x, base_x)

        # ── Smoothing (suavização configurável) ──
        # 0 = fator padrão (0.35); acima disso suaviza progressivamente até
        # 0.80 (pull mais lento e "redondo"). O caminho do Sniper ainda pode
        # forçar EMA_FACTOR = 0.15 no class attr.
        ema_factor = self.EMA_FACTOR
        if runtime and runtime.smoothing > 0:
            ema_factor = min(0.80, self.EMA_FACTOR + (runtime.smoothing / 100.0) * 0.45)

        self.state.ema_y = self.state.ema_y * ema_factor + raw_y * (1.0 - ema_factor)
        self.state.ema_x = self.state.ema_x * ema_factor + raw_x * (1.0 - ema_factor)

        y_out = max(-18000, min(18000, int(self.state.ema_y)))
        x_out = max(-18000, min(18000, int(self.state.ema_x)))

        # ── Horizontal Pull (viés lateral constante, ex.: compensar drift) ──
        if runtime and runtime.horizontal_pull:
            x_out = max(-18000, min(18000, x_out + int(runtime.horizontal_pull)))

        # ── Headshot Assist (estilo Zen) ──
        # Anti-recoil "negativo" no hipfire: em vez de puxar para baixo
        # (compensar o climb), injeta um micro-adjust para CIMA a cada tiro
        # para o retículo assentar na altura da cabeça. No ADS quem cuida
        # disso é o Head Lock do aim assist.
        if self.config.headshot_assist and not is_aiming:
            y_out = max(-18000, y_out - self.config.headshot_assist_pull)

        return y_out, x_out

    def reset(self) -> None:
        self.state = AntiRecoilState()

    def get_stats(self) -> dict:
        return {
            "active": self.state.active,
            "weapon": self._weapon,
            "tick": self.state.tick,
            "ema_y": round(self.state.ema_y, 1),
            "ema_x": round(self.state.ema_x, 1),
            "pattern_loaded": self._pattern is not None,
            "custom_patterns": list(self._custom_patterns.keys()),
            "recoil_adapt_level": self.config.recoil_adapt,
            "smart_learn_enabled": self.config.smart_learn,
            "smart_learn": self._smart_learn.get_stats() if self.config.smart_learn else None,
        }

    def update_config(self, config: RecoilConfig) -> None:
        self.config = config

    # ── RecoilSmoothingEngine API ──

    def set_pattern(self, pattern: Dict[str, Any]) -> None:
        self._sm_active_pattern = pattern
        self._sm_total_ticks = int(pattern.get("ticks", 60))
        self._sm_delay_remaining = float(pattern.get("delay_ms", 0))
        strength = float(pattern.get("strength", 65))
        curve_type = pattern.get("curve", "ease_out").lower()
        if curve_type == "linear":
            self._sm_curves["vertical"] = BezierCurve(0, strength/3, 2*strength/3, strength)
        elif curve_type == "ease_in":
            self._sm_curves["vertical"] = BezierCurve(0, strength/6, strength/3, strength)
        elif curve_type == "ease_out":
            self._sm_curves["vertical"] = BezierCurve(0, 2*strength/3, 5*strength/6, strength)
        else:
            self._sm_curves["vertical"] = BezierCurve(0, strength/4, 3*strength/4, strength)
        x_strength = float(pattern.get("x_strength", 0))
        self._sm_curves["horizontal"] = BezierCurve(0, x_strength/4, x_strength/2, x_strength)

    def apply_smoothed_tick(self, tick: int, ry_raw: int, rx_raw: int) -> Tuple[int, int]:
        if not self._sm_active_pattern:
            return 0, 0
        t = tick / max(self._sm_total_ticks - 1, 1)
        t = max(0.0, min(1.0, t))
        y_offset = int(self._sm_curves["vertical"].evaluate(t))
        x_offset = int(self._sm_curves["horizontal"].evaluate(t))
        if self._sm_delay_remaining > 0:
            self._sm_delay_remaining -= 16.67
            if tick == 0:
                return 0, 0
        return y_offset, x_offset


class RecoilTestbed:

    def __init__(self, recoil_engine: RecoilEngine):
        self.recoil_engine = recoil_engine

    def apply_config(self, config: Dict[str, Any]) -> None:
        weapon = config.get("weapon", "AR").upper()
        if weapon not in RECOIL_PRESETS:
            # Resolve categoria ("AR", "SMG", "Shotgun"...) para o preset real
            for name, preset in RECOIL_PRESETS.items():
                if preset.get("category", "").upper() == weapon:
                    weapon = name
                    break
        self.recoil_engine.set_preset(weapon)
        self.recoil_engine.set_custom_presets({
            weapon: self._preset_from_config(config)
        })

    def simulate_tick(self, tick: int, ry_raw: int = 0, rx_raw: int = 0,
                      config: Dict[str, Any] = None) -> Tuple[int, int]:
        if config:
            self.apply_config(config)
        preset = self.recoil_engine.get_preset(self.recoil_engine.active_preset)
        total_ticks = int(preset.get("ticks", 60))
        y_gate = True if config is None else config.get("y_gate", True)
        return self.recoil_engine.apply_tick(
            max(0, min(tick, total_ticks - 1)),
            total_ticks,
            ry_raw,
            rx_raw,
            preset,
            y_gate,
        )

    def get_pattern(self, config: Dict[str, Any], samples: int = 20) -> Tuple[Tuple[int, int], ...]:
        self.apply_config(config)
        preset = self.recoil_engine.get_preset(self.recoil_engine.active_preset)
        total_ticks = int(preset.get("ticks", 60))
        sample_count = max(1, min(samples, total_ticks))
        points = []
        for i in range(sample_count):
            tick = int(i * max(total_ticks - 1, 1) / max(sample_count - 1, 1))
            points.append(self.simulate_tick(tick, config=config))
        return tuple(points)

    def _preset_from_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "strength": int(config.get("strength", 65)),
            "x_strength": int(config.get("x_strength", 0)),
            "ticks": int(config.get("ticks", 60)),
            "delay_ms": int(config.get("delay", 45)),
            "return_speed": _parse_return_speed(config.get("return_speed", "Normal (0.7)")),
            "curve": _parse_curve(config.get("curve", "Ease-Out")),
        }


class RecoilPresets:

    @staticmethod
    def ar_balanced() -> Dict[str, Any]:
        return {
            "strength": 65, "x_strength": 0, "ticks": 60,
            "delay_ms": 45, "return_speed": 0.70, "curve": "ease_out", "color": "#00ff88"
        }

    @staticmethod
    def ar_heavy() -> Dict[str, Any]:
        return {
            "strength": 85, "x_strength": 10, "ticks": 50,
            "delay_ms": 30, "return_speed": 0.65, "curve": "linear", "color": "#ff4444"
        }

    @staticmethod
    def smg_fast() -> Dict[str, Any]:
        return {
            "strength": 45, "x_strength": 0, "ticks": 45,
            "delay_ms": 18, "return_speed": 0.78, "curve": "linear", "color": "#ffcc00"
        }

    @staticmethod
    def shotgun() -> Dict[str, Any]:
        return {
            "strength": 0, "x_strength": 0, "ticks": 10,
            "delay_ms": 0, "return_speed": 0.90, "curve": "linear", "color": "#00ccff"
        }

    @staticmethod
    def sniper() -> Dict[str, Any]:
        return {
            "strength": 0, "x_strength": 0, "ticks": 10,
            "delay_ms": 0, "return_speed": 0.90, "curve": "linear", "color": "#cc66ff"
        }


class RecoilPresetBuilder:
    @staticmethod
    def create_ar_preset(weapon_name: str, base_strength: int = 65) -> Dict[str, Any]:
        return {"name": f"AR - {weapon_name}", "strength": base_strength, "x_strength": base_strength // 6, "ticks": 60, "delay_ms": 45, "return_speed": 0.70, "curve": "ease_out", "fire_rate": 750}
    @staticmethod
    def create_smg_preset(weapon_name: str, base_strength: int = 45) -> Dict[str, Any]:
        return {"name": f"SMG - {weapon_name}", "strength": base_strength, "x_strength": base_strength // 8, "ticks": 45, "delay_ms": 18, "return_speed": 0.78, "curve": "linear", "fire_rate": 1200}
    @staticmethod
    def create_sniper_preset(weapon_name: str) -> Dict[str, Any]:
        return {"name": f"Sniper - {weapon_name}", "strength": 0, "x_strength": 0, "ticks": 10, "delay_ms": 0, "return_speed": 0.90, "curve": "linear", "fire_rate": 60}
    @staticmethod
    def create_shotgun_preset(weapon_name: str) -> Dict[str, Any]:
        return {"name": f"Shotgun - {weapon_name}", "strength": 0, "x_strength": 0, "ticks": 10, "delay_ms": 0, "return_speed": 0.90, "curve": "linear", "fire_rate": 100}


def _parse_return_speed(value: Any) -> float:
    text = str(value)
    if "(" in text and ")" in text:
        try:
            return float(text.split("(", 1)[1].split(")", 1)[0])
        except ValueError:
            pass
    try:
        return float(text)
    except (TypeError, ValueError):
        return 0.7


def _parse_curve(value: Any) -> str:
    normalized = str(value).strip().lower().replace("-", "_")
    aliases = {
        "linear": "linear",
        "ease_in": "ease_in",
        "ease_out": "ease_out",
    }
    return aliases.get(normalized, "ease_out")


AntiRecoilEngine = RecoilEngine
AntiRecoilPattern = RecoilPattern
class RecoilSmoothingEngine(RecoilEngine):
    def apply_tick(self, tick: int, ry_raw: int, rx_raw: int) -> Tuple[int, int]:
        return self.apply_smoothed_tick(tick, ry_raw, rx_raw)
RecoilPresetBuilderAlias = RecoilPresets
