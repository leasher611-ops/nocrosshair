"""Silent Aim & Silent Hit com Quick Tune — portado do nocrosshair v2.

Lógica original: /home/n0c/Documentos/nocrosshair-v2/nocrosshair/core/silent_aim.py

Silent Aim  (mira silenciosa): ADS + não atirando
Silent Hit  (hit fire assist): atirando + sem ADS (box fights)
Quick Tune: sobe a intensidade até tremer, depois desce 1.

Intensidade (0-10):
    0  = desligado
    2  = leve (Silent Hit recomendado)
    5  = médio (Silent Aim recomendado)
    7+ = grudento, mas pode tremer
"""

from __future__ import annotations

import math
import time
from enum import Enum
from typing import Optional, Tuple


class SilentMode(Enum):
    NONE = "none"
    AIM = "aim"
    HIT = "hit"


class QuickTuneState(Enum):
    IDLE = "idle"
    TUNING = "tuning"
    DONE = "done"


def intensity_to_pull(intensity: int) -> float:
    """Intensidade (0-10) -> multiplicador de pull."""
    if intensity <= 0:
        return 0.0
    return 0.9 + (intensity * 0.15)


def intensity_to_slow(intensity: int) -> float:
    """Intensidade (0-10) -> multiplicador de slowdown (1.0 = normal)."""
    if intensity <= 0:
        return 1.0
    return max(0.5, 1.0 - (intensity * 0.06))


class QuickTuner:
    """Quick Tune estilo Cronus Zen/reWASD.

    O tremor NÃO é detectado por sensor — é o jogador que vê a tela.
    Método (como o vídeo):
      1. start() → intensidade vai subindo 1 a cada ~700ms
      2. O JOGADOR aperta CONFIRM quando a tela começa a tremer
      3. Desce 1 → valor perfeito (grudento sem jitter)

    Também suporta auto-stop se o shake interno for detectado, mas o
    método confiável é o visual (o jogo treme na tela, não no output).
    """

    def __init__(self, mode: SilentMode, get_intensity, set_intensity,
                 pause_ms: float = 700.0, step: int = 1):
        self.mode = mode
        self._get = get_intensity
        self._set = set_intensity
        self._pause_ms = pause_ms
        self._step = step
        self.state = QuickTuneState.IDLE
        self._last_step_time: float = 0.0

    @property
    def current_intensity(self) -> int:
        return self._get()

    def start(self) -> None:
        self.state = QuickTuneState.TUNING
        # Não reseta pra 1 — continua do valor atual (defaults: AIM=5, HIT=8)
        self._last_step_time = time.monotonic()
        print(f"[SilentAimQT] Quick Tune iniciado ({self.mode.value}) "
              f"a partir de intensity={self.current_intensity} — "
              f"aperte CONFIRMAR (F5) quando a tela tremer")

    def tick(self, shake_detected: bool, now: float) -> Optional[int]:
        if self.state != QuickTuneState.TUNING:
            return None

        # Auto-detect opcional (bônus): se o output tremer MUITO (nunca no
        # modo normal), para sozinho. O método real é o visual do jogador.
        if shake_detected:
            best = max(0, self.current_intensity - 1)
            self._set(best)
            self.state = QuickTuneState.DONE
            print(f"[SilentAimQT] {self.mode.value}: tremor detectado! Valor final={best}")
            return best

        if (now - self._last_step_time) * 1000.0 < self._pause_ms:
            return None

        next_val = self.current_intensity + self._step
        if next_val > 10:
            self.state = QuickTuneState.DONE
            print(f"[SilentAimQT] {self.mode.value}: max={self.current_intensity}")
            return self.current_intensity

        self._set(next_val)
        self._last_step_time = now
        return next_val

    def confirm_shake(self) -> int:
        """Jogador viu tremor na tela → desce 1 e trava (Cronus Zen method)."""
        if self.state != QuickTuneState.TUNING:
            return self._get()
        best = max(0, self.current_intensity - 1)
        self._set(best)
        self.state = QuickTuneState.DONE
        print(f"[SilentAimQT] {self.mode.value}: CONFIRMADO tremor! Valor final={best}")
        return best

    def cancel(self) -> int:
        """Cancela sem mudar nada (volta pro valor anterior)."""
        self.state = QuickTuneState.IDLE
        return self._get()

    def stop(self) -> None:
        self.state = QuickTuneState.IDLE

    def is_tuning(self) -> bool:
        return self.state == QuickTuneState.TUNING


# ── AutoTrack (momentum) ────────────────────────────────────────────
# Quando o stick move, adiciona boost % na mesma direção.
# Quando para, mantém momentum por N ms com decay.
class _AutoTrack:
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

    def reset(self):
        self._persist_rx = 0.0
        self._persist_ry = 0.0
        self._persist_until = 0.0


# ── StickyMagnet (persistência magnética) ───────────────────────────
# Quando atirando/mirando e stick movendo: pull na direção do movimento.
# Quando para: mantém último pull por ~90ms com decay.
class _StickyMagnet:
    def __init__(self):
        self._persist_rx: float = 0.0
        self._persist_ry: float = 0.0
        self._persist_until: float = 0.0

    def apply(self, rx: float, ry: float, *, enabled: bool,
              strength: float, magnetic_pull: int, is_shooting: bool,
              is_aiming: bool, delta_ms: float,
              now: Optional[float] = None) -> Tuple[float, float]:
        if not enabled or strength <= 0 or magnetic_pull <= 0:
            self.reset()
            return rx, ry

        t = now if now is not None else time.monotonic()
        mag = math.sqrt(rx * rx + ry * ry)
        engaged = (is_shooting or is_aiming) and mag > 100

        if engaged:
            nx = rx / mag if mag > 0 else 0.0
            ny = ry / mag if mag > 0 else 0.0
            self._persist_rx = rx
            self._persist_ry = ry
            self._persist_until = t + 0.09

            zone_factor = min(mag / 8000.0, 1.0)
            pull = magnetic_pull * strength * (0.35 + 0.65 * zone_factor)
            pull = min(pull, magnetic_pull)
            rx = rx + nx * pull
            ry = ry + ny * pull
        elif t < self._persist_until:
            remaining = (self._persist_until - t) / 0.09
            decay = max(0.0, min(1.0, remaining))
            if abs(self._persist_rx) > 50:
                keep_x = abs(self._persist_rx) * 0.35 * decay
                rx = rx + math.copysign(keep_x, self._persist_rx) if rx == 0 else rx
            if abs(self._persist_ry) > 50:
                keep_y = abs(self._persist_ry) * 0.35 * decay
                ry = ry + math.copysign(keep_y, self._persist_ry) if ry == 0 else ry
        else:
            self.reset()

        return max(-32767.0, min(32767.0, rx)), max(-32767.0, min(32767.0, ry))

    def reset(self):
        self._persist_rx = 0.0
        self._persist_ry = 0.0
        self._persist_until = 0.0


class SilentAimQTEngine:
    """Silent Aim / Silent Hit engine (portado do v2).

    Técnica REAL dos scripts Cronus Zen (análise em docs/RESEARCH_AIM.md):
    - Sahr03 v1/v2 + Full_Accessability: OSCILAÇÃO QUADRADA alternada
      no right stick — set_val(RS, +amp) → wait → set_val(RS, -amp),
      amplitude ±5-10% do stick, delay 16-20ms (50-60Hz).
    - MikeCrowne GPC: padrões Circle/Triangle/Spiral/Helix somados ao
      input do jogador (set_val(RX, get_val(RX) + offset)).

    O nosso engine combina:
    - Oscilação quadrada alternada (técnica base dos silent aims)
    - Padrão circular suave (GPC avançado)
    - Zero Tremor (anti-shake)
    """

    def __init__(self):
        self._mode: SilentMode = SilentMode.NONE
        self._orbit_angle: float = 0.0
        self._prev_rx: float = 0.0
        self._prev_ry: float = 0.0
        self._shake_score: float = 0.0
        self._last_apply: float = 0.0
        self._drift_dir: int = 1        # direção da oscilação quadrada
        self._drift_tick: int = 0       # tick da oscilação quadrada
        self._pattern: str = "square"   # square | circle | helix
        self._gate_smooth: float = 1.0  # gate adaptativo suavizado (0-1)
        self._gate_l_smooth: float = 1.0  # gate do left stick (0-1)

        # Config (referências setadas pelo pipeline)
        self.enabled: bool = True
        self.aim_intensity: int = 5   # Silent Aim default (Quick Tune recomenda)
        self.hit_intensity: int = 8   # Silent Hit default
        self.aim_shake_blend: float = 0.35
        self.hit_shake_blend: float = 0.30
        self.aim_enabled: bool = True
        self.hit_enabled: bool = True
        self.anti_recoil_vert: int = 0
        self.anti_recoil_horiz: int = 0

        self.quick_tune_aim = QuickTuner(
            SilentMode.AIM,
            lambda: self.aim_intensity,
            lambda v: setattr(self, "aim_intensity", v),
        )
        self.quick_tune_hit = QuickTuner(
            SilentMode.HIT,
            lambda: self.hit_intensity,
            lambda v: setattr(self, "hit_intensity", v),
        )

        # ── AutoTrack + StickyMagnet (integrados) ──
        self.auto_track = _AutoTrack()
        self.auto_track_enabled: bool = True
        self.auto_track_multiplier: float = 0.15  # 15% boost sutil (era 60% — rouba controle)
        self.auto_track_threshold: int = 200      # threshold maior (era 20 — ativa até com tremer)
        self.auto_track_persistence_ms: float = 30.0  # momentum curto (era 60ms)

        self.sticky_magnet = _StickyMagnet()
        self.sticky_magnet_enabled: bool = True
        self.sticky_magnet_strength: float = 0.25  # pull sutil (era 0.6 — empurrava mira)
        self.sticky_magnet_pull: int = 300         # força menor (era 800)

    def get_mode(self) -> SilentMode:
        return self._mode

    def process(
        self,
        rx: float,
        ry: float,
        is_firing: bool,
        is_ads: bool,
        delta_ms: float,
    ) -> Tuple[float, float]:
        if not self.enabled:
            return rx, ry

        # Detecta modo
        if self.aim_enabled and is_ads and not is_firing:
            self._mode = SilentMode.AIM
        elif self.hit_enabled and is_firing and not is_ads:
            self._mode = SilentMode.HIT
        else:
            self._mode = SilentMode.NONE

        if self._mode == SilentMode.NONE:
            return rx, ry

        if self._mode == SilentMode.AIM:
            intensity = self.aim_intensity
            shake_blend = self.aim_shake_blend
        else:
            intensity = self.hit_intensity
            shake_blend = self.hit_shake_blend

        pull_mult = intensity_to_pull(intensity)
        slow_mult = intensity_to_slow(intensity)

        # ── Escala REAL do Cronus Zen (pesquisa docs/RESEARCH_AIM.md) ──
        # Scripts reais analisados:
        #   Sahr03 v1:        amplitude ±10 GPC (=±3277 evdev), delay 20ms
        #   Sahr03 v2:        amplitude ±8  GPC (=±2621 evdev), delay 16ms
        #   Full_Accessability: ±5 GPC (=±1638 evdev), delay 16ms
        #   MikeCrowne GPC:   intensity 10-100% somado ao input
        # GPC usa escala 0-100 (0-100% do stick). Nosso nível 1-10:
        #   nível 1  → 5 GPC  = 5%  = 1638 evdev
        #   nível 5  → 10 GPC = 10% = 3277 evdev
        #   nível 10 → 20 GPC = 20% = 6553 evdev
        gpc_amp = 10.0 + intensity * 3.0   # 13 (nível 1) a 40 (nível 10) — community standard 30 GPC
        amplitude = 327.67 * gpc_amp      # evdev
        # Velocidade angular do círculo (GPC speed 1-10x)
        speed = 2.0 + intensity * 1.0

        # Delay da oscilação (ms) — script real usa 16-20ms (50-60Hz)
        drift_delay_ms = 20.0

        # ── GATE adaptativo (Cronus Zen) ──
        # A oscilação NUNCA deve brigar com o input do jogador. Quanto mais
        # o jogador move o stick/mouse, menor a oscilação:
        #   mag <  gate_low  → oscilação 100% (parado/micro-ajuste)
        #   mag ~ gate_high → oscilação 0%  (movendo forte, passa limpo)
        # Isso evita o "mouse travado/pulando pixel" em intensidade alta.
        # O Silent Hit (hip fire) usa gate mais permissivo: o jogador segue
        # o alvo SEM ADS com input grande — a oscilação deve continuar
        # ajudando em vez de cortar.
        mag_in = math.hypot(rx, ry)
        if self._mode == SilentMode.HIT:
            gate_low = 6000.0
            gate_high = 25000.0
        else:
            # Silent Aim: gate MAIOR — mouse "respira" com 2000-4000 evdev
            # gate_low precisa absorver os micro-tremores humanos
            gate_low = 5000.0    # abaixo: oscilação cheia (absorve tremores)
            gate_high = 12000.0  # acima: sem oscilação (movendo forte)
        if mag_in <= gate_low:
            gate = 1.0
        elif mag_in >= gate_high:
            gate = 0.0
        else:
            # Interpolação linear 1.0 → 0.0 entre os gates
            gate = 1.0 - (mag_in - gate_low) / (gate_high - gate_low)
        # Suaviza a transição do gate (evita "corte" seco) — rápido o
        # suficiente para o mouse não ficar travado ao mover.
        self._gate_smooth = self._gate_smooth * 0.5 + gate * 0.5

        # ── Gate também no SLOWDOWN/PULL ──
        # O slow_mult reduz o input do jogador (o "peso"). Isso SÓ deve
        # acontecer quando o jogador está parado/micro-ajustando (gate alto).
        # Quando ele move o mouse (gate baixo), o input passa 100% limpo:
        #   slow_eff = 1.0 quando gate = 0 (input puro, fluido)
        #   slow_eff = slow_mult quando gate = 1 (gruda)
        # Interpola entre o slowdown total e nenhum slowdown pelo gate.
        slow_eff = 1.0 - (1.0 - slow_mult) * self._gate_smooth
        pull_eff = pull_mult * self._gate_smooth

        rx_slow = rx * slow_eff
        ry_slow = ry * slow_eff

        # ── Oscilação (2 modos: square = técnica real base, circle = GPC) ──
        if pull_eff > 0 and self._gate_smooth > 0.02:
            if self._pattern == "square":
                # Técnica REAL dos silent aims (Sahr03/Full_Accessability):
                # oscilação QUADRADA alternada. A cada drift_delay_ms,
                # alterna a direção. APENAS eixo X (horizontal) —
                # oscilação no Y puxa a câmera pro chão/céu.
                self._drift_tick += delta_ms
                if self._drift_tick >= drift_delay_ms:
                    self._drift_tick = 0.0
                    self._drift_dir = -self._drift_dir
                # Amplitude escalada pelo gate (0-1)
                amp_gated = amplitude * self._gate_smooth
                off_x = self._drift_dir * amp_gated
                off_y = 0.0
                rx_out = rx_slow + off_x
                ry_out = ry_slow + off_y
            else:
                # Padrão circular suave (MikeCrowne GPC — somado ao input)
                # Amplitude Y reduzida para 30% da X — evita puxar câmera
                self._orbit_angle = (self._orbit_angle
                                     + speed * (delta_ms / 1000.0)) % (2 * math.pi)
                amp_gated = amplitude * self._gate_smooth
                rx_out = rx_slow + math.cos(self._orbit_angle) * amp_gated
                ry_out = ry_slow + math.sin(self._orbit_angle) * amp_gated * 0.3
        else:
            # Sem oscilação: o input do jogador passa LIMPO (mouse fluido)
            rx_out = rx_slow * (1.0 + pull_eff * 0.06)
            ry_out = ry_slow * (1.0 + pull_eff * 0.06)

        # Zero Tremor (anti-shake)
        if shake_blend > 0:
            alpha = min(1.0, shake_blend + (delta_ms / 100.0))
            out_x = self._prev_rx * (1.0 - alpha) + rx_out * alpha
            out_y = self._prev_ry * (1.0 - alpha) + ry_out * alpha
        else:
            out_x, out_y = rx_out, ry_out

        self._prev_rx = out_x
        self._prev_ry = out_y

        # Anti-recoil no Silent Hit
        if self._mode == SilentMode.HIT:
            out_x -= self.anti_recoil_horiz * 50
            out_y -= self.anti_recoil_vert * 100

        # Shake score para Quick Tune
        jitter = math.hypot(rx_out - self._prev_rx, ry_out - self._prev_ry)
        self._shake_score = self._shake_score * 0.9 + min(jitter, 2000.0) * 0.1

        return out_x, out_y

    def is_shaking(self) -> bool:
        return self._shake_score > 120.0

    # ── Combo completo: silent_qt + auto_track + sticky_magnet ──
    # Chamado pelo flush contínuo. rx/ry = input do jogador (mouse),
    # is_firing/is_ads = estado dos botões.
    def process_combo(
        self,
        rx: float,
        ry: float,
        is_firing: bool,
        is_ads: bool,
        delta_ms: float,
        now: float,
    ) -> Tuple[float, float]:
        # 1. Silent Aim/Hit (oscilação — gruda quando parado)
        out_x, out_y = self.process(
            rx, ry,
            is_firing=is_firing,
            is_ads=is_ads,
            delta_ms=delta_ms,
        )

        # 2. AutoTrack (momentum — acelera na direção do movimento)
        # Quando o mouse move, adiciona um boost percentual na mesma direção.
        # Quando para, mantém momentum por ~80ms com decay.
        if self.auto_track_enabled and self.auto_track_multiplier > 0:
            out_x, out_y = self.auto_track.apply(
                int(out_x), int(out_y),
                enabled=True,
                multiplier=self.auto_track_multiplier,
                threshold=self.auto_track_threshold,
                persistence_ms=self.auto_track_persistence_ms,
            )

        # 3. StickyMagnet (persistência — mantém pull ao parar)
        # Quando atirando/mirando e stick movendo: pull magnético na direção.
        # Quando para: mantém último pull por ~90ms com decay.
        if self.sticky_magnet_enabled and self.sticky_magnet_strength > 0:
            out_x, out_y = self.sticky_magnet.apply(
                float(out_x), float(out_y),
                enabled=True,
                strength=self.sticky_magnet_strength,
                magnetic_pull=self.sticky_magnet_pull,
                is_shooting=is_firing,
                is_aiming=is_ads,
                delta_ms=delta_ms,
                now=now,
            )

        return out_x, out_y

    # ── Left stick (movimento) — oscilação para rotational AA ──
    # O rotational AA do Fortnite ativa com o left stick em movimento.
    # Usa amplitude baixa (5-10% do stick) com gate adaptativo: gruda
    # quando parado, fica fluido quando o jogador move (WASD).
    def process_left_stick(
        self,
        lx: float,
        ly: float,
        delta_ms: float,
    ) -> Tuple[float, float]:
        if not self.enabled:
            return lx, ly

        # Gate adaptativo: para a oscilação quando o jogador move forte
        mag_in = math.hypot(lx, ly)
        gate_low = 3000.0
        gate_high = 12000.0
        if mag_in <= gate_low:
            gate = 1.0
        elif mag_in >= gate_high:
            gate = 0.0
        else:
            gate = 1.0 - (mag_in - gate_low) / (gate_high - gate_low)
        self._gate_l_smooth = self._gate_l_smooth * 0.5 + gate * 0.5

        if self._gate_l_smooth < 0.02:
            return lx, ly

        # Amplitude do left stick: precisa de 15-20 GPC pra ativar rotational AA.
        # 4-10 GPC (antigo) era ABAIXO da deadzone do jogo (5% = ~1638 evdev).
        intensity = self.hit_intensity
        gpc_amp = 12.0 + intensity * 2.5   # 14 (nível 1) a 37 (nível 10) — rotational AA
        amp = 327.67 * gpc_amp * self._gate_l_smooth

        # Oscilação quadrada alternada X↔Y (como os silent aims)
        self._drift_tick += delta_ms
        if self._drift_tick >= 20.0:
            self._drift_tick = 0.0
            self._drift_dir = -self._drift_dir
        axis = 0 if (self._drift_tick < 10.0) else 1
        if axis == 0:
            lx_out = lx + self._drift_dir * amp
            ly_out = ly
        else:
            lx_out = lx
            ly_out = ly + self._drift_dir * amp

        return lx_out, ly_out

    def quick_tune_tick(self, mode: SilentMode, now: float) -> Optional[int]:
        tuner = self.quick_tune_aim if mode == SilentMode.AIM else self.quick_tune_hit
        if not tuner.is_tuning():
            return None
        return tuner.tick(self.is_shaking(), now)

    def reset(self) -> None:
        self._orbit_angle = 0.0
        self._prev_rx = 0.0
        self._prev_ry = 0.0
        self._shake_score = 0.0
        self._gate_l_smooth = 1.0


# Instância global
silent_aim_qt = SilentAimQTEngine()
