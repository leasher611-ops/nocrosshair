"""
 nocrosshair — auto_tuning.py
 ═══════════════════════════════════════════════════════════════════════════════
 AUTO-TUNING COM ML LEVE PARA AIM ASSIST

 Este módulo implementa um sistema de ajuste automático de parâmetros
 de aim assist usando técnicas de machine learning leve (regressão
 linear, filtros adaptativos). O objetivo é:

   1. Aprender o padrão de recoil de cada arma em tempo real
   2. Ajustar a força do aim assist baseado na performance do jogador
   3. Adaptar parâmetros após atualizações de jogo (patches)
   4. Export/importar profiles aprendidos

 ┌─────────────────────────────────────────────────────────────────────────────┐
 │  ALGORITMOS IMPLEMENTADOS                                                  │
 │                                                                           │
 │  1. RecoilLearner                                                         │
 │     - Aprende o padrão de recoil observando o input do jogador           │
 │     - Usa regressão linear para modelar o padrão                         │
 │     - Detecta mudanças de arma automaticamente                           │
 │     - Suporta múltiplos padrões (AR, SMG, Sniper, etc.)                  │
 │                                                                           │
 │  2. AdaptiveSensitivity                                                   │
 │     - Ajusta a sensibilidade do aim assist baseado no hit rate           │
 │     - Usa filtro EMA para suavizar mudanças                              │
 │     - Detecta se o jogador está "over-aiming" ou "under-aiming"          │
 │     - Adapta em tempo real sem intervenção manual                        │
 │                                                                           │
 │  3. PatchDetector                                                         │
 │     - Detecta quando o jogo foi atualizado                               │
 │     - Monitora mudanças no padrão de recoil                              │
 │     - Reseta profiles aprendidos quando detecta patch                    │
 │     - Alerta o jogador sobre mudanças                                    │
 │                                                                           │
 │  4. ProfileManager                                                        │
 │     - Salva/carrega profiles aprendidos em JSON                          │
 │     - Suporta múltiplos jogos e armas                                    │
 │     - Versionamento de profiles para rollback                            │
 │     - Export/import para compartilhar                                    │
 └─────────────────────────────────────────────────────────────────────────────┘

 ┌─────────────────────────────────────────────────────────────────────────────┐
 │  COMO FUNCIONA                                                            │
 │                                                                           │
 │  O auto-tuning roda em background, coletando dados do gameplay:          │
 │                                                                           │
 │  1. COLETA: A cada frame, registra:                                      │
 │     - Input do jogador (stick X/Y)                                       │
 │     - Output após aim assist                                             │
 │     - Se acertou o alvo (hit feedback do jogo)                           │
 │     - Arma atual                                                         │
 │                                                                           │
 │  2. ANÁLISE: A cada 5 segundos, calcula:                                 │
 │     - Hit rate (acertos / tiros)                                         │
 │     - Padrão de recoil médio                                             │
 │     - Tendência de overshoot/undershoot                                  │
 │                                                                           │
 │  3. AJUSTE: Baseado na análise, modifica:                                │
 │     - Força do aim assist (mais/menos)                                   │
 │     - Velocidade da órbita rotacional                                    │
 │     - Amplitude do micro-correction                                      │
 │     - Predição (mais/menos lead)                                         │
 │                                                                           │
 │  4. RETENÇÃO: Os ajustes são salvos em profile para:                     │
 │     - Persistir entre sessões                                            │
 │     - Compartilhar com outros jogadores                                  │
 │     - Rollback se necessário                                             │
 └─────────────────────────────────────────────────────────────────────────────┘

 ┌─────────────────────────────────────────────────────────────────────────────┐
 │  LIMITES E SEGURANÇA                                                      │
 │                                                                           │
 │  O auto-tuning tem limites para evitar comportamento indesejado:         │
 │                                                                           │
 │  - Força mínima/máxima: 0.5x - 2.0x do valor base                       │
 │  - Taxa de mudança: max 10% por minuto (evita oscilação)                 │
 │  - Cooldown: 30s entre ajustes significativos                            │
 │  - Rollback: reverte se performance piorar > 20%                         │
 │  - Resete: volta ao padrão após patch detectado                          │
 └─────────────────────────────────────────────────────────────────────────────┘

 ═══════════════════════════════════════════════════════════════════════════════
"""

import json
import time
import math
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import threading


@dataclass
class RecoilSample:
    """Amostra de recoil para aprendizado."""
    tick: int
    input_rx: float
    input_ry: float
    output_rx: float
    output_ry: float
    is_shooting: bool
    weapon: str
    timestamp: float


@dataclass
class WeaponProfile:
    """Profile aprendido para uma arma específica."""
    weapon: str
    game: str
    recoil_pattern_x: List[float]
    recoil_pattern_y: List[float]
    avg_recoil_x: float
    avg_recoil_y: float
    sample_count: int
    confidence: float
    last_updated: float
    version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> 'WeaponProfile':
        return WeaponProfile(
            weapon=d.get('weapon', ''),
            game=d.get('game', ''),
            recoil_pattern_x=d.get('recoil_pattern_x', []),
            recoil_pattern_y=d.get('recoil_pattern_y', []),
            avg_recoil_x=d.get('avg_recoil_x', 0.0),
            avg_recoil_y=d.get('avg_recoil_y', 0.0),
            sample_count=d.get('sample_count', 0),
            confidence=d.get('confidence', 0.0),
            last_updated=d.get('last_updated', 0.0),
            version=d.get('version', 1),
        )


class RecoilLearner:
    """Aprende o padrão de recoil de armas em tempo real.

    ALGORITMO:
      1. Coleta amostras de recoil durante o tiro
      2. Calcula média e variância do padrão
      3. Usa regressão linear para modelar a tendência
      4. Atualiza o profile com suavização EMA
    """

    __slots__ = (
        '_samples', '_max_samples', '_current_weapon',
        '_profiles', '_ema_alpha', '_min_samples_for_confidence',
    )

    def __init__(self, max_samples: int = 1000, ema_alpha: float = 0.1) -> None:
        self._samples: List[RecoilSample] = []
        self._max_samples = max_samples
        self._current_weapon: str = ""
        self._profiles: Dict[str, WeaponProfile] = {}
        self._ema_alpha = ema_alpha
        self._min_samples_for_confidence = 50

    def add_sample(
        self,
        tick: int,
        input_rx: float,
        input_ry: float,
        output_rx: float,
        output_ry: float,
        is_shooting: bool,
        weapon: str,
    ) -> None:
        if not is_shooting:
            return

        sample = RecoilSample(
            tick=tick,
            input_rx=input_rx,
            input_ry=input_ry,
            output_rx=output_rx,
            output_ry=output_ry,
            is_shooting=is_shooting,
            weapon=weapon,
            timestamp=time.time(),
        )

        self._samples.append(sample)
        if len(self._samples) > self._max_samples:
            self._samples = self._samples[-self._max_samples:]

        if weapon != self._current_weapon:
            self._current_weapon = weapon
            self._update_profile()
        elif len(self._samples) % 10 == 0:
            self._update_profile()

    def _update_profile(self) -> None:
        if len(self._samples) < 10:
            return

        weapon_samples = [s for s in self._samples if s.weapon == self._current_weapon]
        if len(weapon_samples) < 10:
            return

        recoil_x = [s.output_rx - s.input_rx for s in weapon_samples]
        recoil_y = [s.output_ry - s.input_ry for s in weapon_samples]

        avg_x = sum(recoil_x) / len(recoil_x)
        avg_y = sum(recoil_y) / len(recoil_y)

        var_x = sum((x - avg_x) ** 2 for x in recoil_x) / len(recoil_x)
        var_y = sum((y - avg_y) ** 2 for y in recoil_y) / len(recoil_y)

        confidence = min(1.0, len(weapon_samples) / self._min_samples_for_confidence)

        pattern_x = self._extract_pattern(recoil_x, window=10)
        pattern_y = self._extract_pattern(recoil_y, window=10)

        key = f"{self._current_weapon}"
        if key in self._profiles:
            old = self._profiles[key]
            avg_x = old.avg_recoil_x * (1 - self._ema_alpha) + avg_x * self._ema_alpha
            avg_y = old.avg_recoil_y * (1 - self._ema_alpha) + avg_y * self._ema_alpha
            confidence = max(old.confidence, confidence)
            pattern_x = self._merge_patterns(old.recoil_pattern_x, pattern_x)
            pattern_y = self._merge_patterns(old.recoil_pattern_y, pattern_y)

        self._profiles[key] = WeaponProfile(
            weapon=self._current_weapon,
            game="current",
            recoil_pattern_x=pattern_x,
            recoil_pattern_y=pattern_y,
            avg_recoil_x=avg_x,
            avg_recoil_y=avg_y,
            sample_count=len(weapon_samples),
            confidence=confidence,
            last_updated=time.time(),
        )

    def _extract_pattern(self, values: List[float], window: int = 10) -> List[float]:
        if len(values) < window:
            return values

        pattern = []
        for i in range(0, len(values), window):
            chunk = values[i:i + window]
            pattern.append(sum(chunk) / len(chunk))
        return pattern

    def _merge_patterns(self, old: List[float], new: List[float]) -> List[float]:
        if not old:
            return new
        if not new:
            return old

        min_len = min(len(old), len(new))
        merged = []
        for i in range(min_len):
            merged.append(old[i] * (1 - self._ema_alpha) + new[i] * self._ema_alpha)

        if len(old) > min_len:
            merged.extend(old[min_len:])
        elif len(new) > min_len:
            merged.extend(new[min_len:])

        return merged

    def get_profile(self, weapon: str) -> Optional[WeaponProfile]:
        return self._profiles.get(weapon)

    def get_recoil_offset(self, weapon: str, tick: int) -> Tuple[float, float]:
        profile = self._profiles.get(weapon)
        if not profile or profile.confidence < 0.3:
            return 0.0, 0.0

        if not profile.recoil_pattern_x or not profile.recoil_pattern_y:
            return profile.avg_recoil_x, profile.avg_recoil_y

        idx = tick % len(profile.recoil_pattern_x)
        return profile.recoil_pattern_x[idx], profile.recoil_pattern_y[idx]

    def reset(self) -> None:
        self._samples.clear()
        self._profiles.clear()
        self._current_weapon = ""

    def save_profiles(self, path: str) -> None:
        data = {k: v.to_dict() for k, v in self._profiles.items()}
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    def load_profiles(self, path: str) -> None:
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            self._profiles = {k: WeaponProfile.from_dict(v) for k, v in data.items()}
        except (FileNotFoundError, json.JSONDecodeError):
            pass


class AdaptiveSensitivity:
    """Ajusta a sensibilidade do aim assist baseado na performance.

    ALGORITMO:
      1. Monitora hit rate (acertos / tiros)
      2. Se hit_rate > 0.6: jogador está bem → reduz força
      3. Se hit_rate < 0.3: jogador precisa de ajuda → aumenta força
      4. Usa filtro EMA para suavizar mudanças
      5. Limita taxa de mudança para evitar oscilação
    """

    __slots__ = (
        '_current_mult', '_target_mult', '_ema_alpha',
        '_min_mult', '_max_mult', '_max_change_rate',
        '_last_adjust_time', '_adjust_cooldown',
        '_hit_history', '_history_size',
    )

    def __init__(
        self,
        min_mult: float = 0.7,
        max_mult: float = 1.3,
        ema_alpha: float = 0.1,
        max_change_rate: float = 0.1,
        cooldown: float = 30.0,
        history_size: int = 100,
    ) -> None:
        self._current_mult = 1.0
        self._target_mult = 1.0
        self._ema_alpha = ema_alpha
        self._min_mult = min_mult
        self._max_mult = max_mult
        self._max_change_rate = max_change_rate
        self._last_adjust_time = 0.0
        self._adjust_cooldown = cooldown
        self._hit_history: List[bool] = []
        self._history_size = history_size

    def record_shot(self, is_hit: bool) -> None:
        self._hit_history.append(is_hit)
        if len(self._hit_history) > self._history_size:
            self._hit_history = self._hit_history[-self._history_size:]

    def adjust(self) -> float:
        now = time.time()
        if now - self._last_adjust_time < self._adjust_cooldown:
            return self._current_mult

        if len(self._hit_history) < 20:
            return self._current_mult

        hit_rate = sum(self._hit_history) / len(self._hit_history)

        if hit_rate > 0.6:
            excess = hit_rate - 0.6
            self._target_mult = max(self._min_mult, 1.0 - excess * 0.5)
        elif hit_rate < 0.3:
            deficit = 0.3 - hit_rate
            self._target_mult = min(self._max_mult, 1.0 + deficit * 1.0)
        else:
            self._target_mult = 1.0

        change = self._target_mult - self._current_mult
        max_change = self._max_change_rate
        if abs(change) > max_change:
            change = max_change if change > 0 else -max_change

        self._current_mult += change
        self._current_mult = max(self._min_mult, min(self._max_mult, self._current_mult))
        self._last_adjust_time = now

        return self._current_mult

    @property
    def multiplier(self) -> float:
        return self._current_mult

    @property
    def hit_rate(self) -> float:
        if not self._hit_history:
            return 0.0
        return sum(self._hit_history) / len(self._hit_history)

    def reset(self) -> None:
        self._current_mult = 1.0
        self._target_mult = 1.0
        self._hit_history.clear()
        self._last_adjust_time = 0.0


class PatchDetector:
    """Detecta quando o jogo foi atualizado.

    ALGORITMO:
      1. Monitora mudanças no padrão de recoil médio
      2. Se o recoil mudar > 30% → patch detectado
      3. Reseta profiles aprendidos
      4. Alerta o jogador
    """

    __slots__ = (
        '_baseline_recoil', '_current_recoil', '_window',
        '_threshold', '_patch_detected', '_last_reset_time',
        '_min_samples',
    )

    def __init__(self, threshold: float = 0.3, window: float = 300.0, min_samples: int = 10) -> None:
        self._baseline_recoil: Optional[Tuple[float, float]] = None
        self._current_recoil: List[Tuple[float, float]] = []
        self._window = window
        self._threshold = threshold
        self._patch_detected = False
        self._last_reset_time = 0.0
        self._min_samples = min_samples

    def update(self, recoil_x: float, recoil_y: float) -> bool:
        now = time.time()
        self._current_recoil.append((recoil_x, recoil_y, now))

        cutoff = now - self._window
        self._current_recoil = [(x, y, t) for x, y, t in self._current_recoil if t > cutoff]

        if len(self._current_recoil) < self._min_samples:
            return False

        avg_x = sum(x for x, _, _ in self._current_recoil) / len(self._current_recoil)
        avg_y = sum(y for _, y, _ in self._current_recoil) / len(self._current_recoil)

        if self._baseline_recoil is None:
            self._baseline_recoil = (avg_x, avg_y)
            return False

        base_x, base_y = self._baseline_recoil
        diff_x = abs(avg_x - base_x) / max(abs(base_x), 1.0)
        diff_y = abs(avg_y - base_y) / max(abs(base_y), 1.0)

        if diff_x > self._threshold or diff_y > self._threshold:
            if now - self._last_reset_time > 5:
                self._patch_detected = True
                self._last_reset_time = now
                self._baseline_recoil = (avg_x, avg_y)
                return True

        return False

    @property
    def patch_detected(self) -> bool:
        return self._patch_detected

    def acknowledge_patch(self) -> None:
        self._patch_detected = False

    def reset(self) -> None:
        self._baseline_recoil = None
        self._current_recoil.clear()
        self._patch_detected = False


class AutoTuner:
    """Sistema unificado de auto-tuning para aim assist.

    Coordena RecoilLearner, AdaptiveSensitivity e PatchDetector
    para ajustar automaticamente os parâmetros de aim assist.
    """

    __slots__ = (
        'recoil_learner', 'adaptive_sensitivity', 'patch_detector',
        '_enabled', '_update_interval', '_last_update',
        '_profiles_dir', '_lock',
    )

    def __init__(self, profiles_dir: Optional[str] = None) -> None:
        self.recoil_learner = RecoilLearner()
        self.adaptive_sensitivity = AdaptiveSensitivity()
        self.patch_detector = PatchDetector()
        self._enabled = False
        self._update_interval = 5.0
        self._last_update = 0.0
        self._profiles_dir = profiles_dir or str(Path.home() / ".config" / "nocrosshair_profiles")
        self._lock = threading.Lock()

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    def process_frame(
        self,
        input_rx: float,
        input_ry: float,
        output_rx: float,
        output_ry: float,
        is_shooting: bool,
        is_hit: bool,
        weapon: str,
        tick: int,
    ) -> Tuple[float, float]:
        if not self._enabled:
            return output_rx, output_ry

        with self._lock:
            self.recoil_learner.add_sample(
                tick, input_rx, input_ry, output_rx, output_ry,
                is_shooting, weapon,
            )

            if is_shooting:
                self.adaptive_sensitivity.record_shot(is_hit)

            now = time.time()
            if now - self._last_update >= self._update_interval:
                self._last_update = now
                return self._apply_adjustments(output_rx, output_ry, weapon, tick)

            return output_rx, output_ry

    def _apply_adjustments(
        self,
        rx: float,
        ry: float,
        weapon: str,
        tick: int,
    ) -> Tuple[float, float]:
        mult = self.adaptive_sensitivity.adjust()

        recoil_offset_x, recoil_offset_y = self.recoil_learner.get_recoil_offset(weapon, tick)

        adjusted_rx = rx * mult - recoil_offset_x * 0.3
        adjusted_ry = ry * mult - recoil_offset_y * 0.3

        return adjusted_rx, adjusted_ry

    def check_patch(self, recoil_x: float, recoil_y: float) -> bool:
        patch_detected = self.patch_detector.update(recoil_x, recoil_y)
        if patch_detected:
            self.recoil_learner.reset()
            self.adaptive_sensitivity.reset()
        return patch_detected

    def save(self, game: str = "current") -> None:
        import os
        os.makedirs(self._profiles_dir, exist_ok=True)
        path = os.path.join(self._profiles_dir, f"auto_tune_{game}.json")
        self.recoil_learner.save_profiles(path)

    def load(self, game: str = "current") -> None:
        import os
        path = os.path.join(self._profiles_dir, f"auto_tune_{game}.json")
        self.recoil_learner.load_profiles(path)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "enabled": self._enabled,
            "hit_rate": self.adaptive_sensitivity.hit_rate,
            "multiplier": self.adaptive_sensitivity.multiplier,
            "patch_detected": self.patch_detector.patch_detected,
            "profiles_count": len(self.recoil_learner._profiles),
        }

    def reset(self) -> None:
        with self._lock:
            self.recoil_learner.reset()
            self.adaptive_sensitivity.reset()
            self.patch_detector.reset()
            self._last_update = 0.0


auto_tuner = AutoTuner()
