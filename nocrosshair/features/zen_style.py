#!/usr/bin/env python3
"""Motores de aim assist estilo Zen (algoritmos originais).

Mecânicas de referência documentadas publicamente sobre o Cronus Zen:
- Sticky/magnetic pull: pull proporcional à deflexão do stick + persistência
  curta quando o jogador solta o stick, para a mira "grudar" no alvo.
- Aim Lock: trava forte com suavização quando atirando dentro do FOV.
- Micro-padrões rotacionais que re-disparam o AA nativo do jogo.
- Aim spam: micro-cycle rápido de ADS para refrescar o magnetismo nativo.

Nenhum código GPC do Zen é copiado — estes são algoritmos originais que
replicam o *efeito* documentado ao nível do input do right stick.
"""

import math
import time
from typing import Tuple, Optional


class StickyMagnetEngine:
    """Grudância estilo Zen: pull magnético + persistência de input.

    Princípio (documentado publicamente): sem screen capture, o "sticky"
    funciona mantendo o AA nativo do jogo re-engajado. Quando o jogador
    move o stick (input ≠ 0) e atira, aplicamos um pull na direção do
    movimento; quando ele solta o stick, mantemos o último pull por alguns
    ms (persistência) para o retículo não "escapar" do alvo.
    """

    def __init__(self) -> None:
        self._persist_rx: float = 0.0
        self._persist_ry: float = 0.0
        self._persist_until: float = 0.0
        self._last_dir_x: float = 0.0
        self._last_dir_y: float = 0.0

    def apply(self, rx: float, ry: float, *, enabled: bool,
              strength: float, magnetic_pull: int, is_shooting: bool,
              is_aiming: bool, delta_ms: float,
              now: Optional[float] = None) -> Tuple[float, float]:
        """Aplica pull magnético + persistência ao input do right stick.

        - ``strength`` (0..1): intensidade do pull magnético.
        - ``magnetic_pull`` (0..1200): força máxima do pull.
        - Só atua quando o jogador está engajado (atirando/mirando) e o
          stick está em movimento, ou dentro da janela de persistência.
        """
        if not enabled or strength <= 0 or magnetic_pull <= 0:
            self._reset_persist()
            return rx, ry

        t = now if now is not None else time.monotonic()
        mag = math.sqrt(rx * rx + ry * ry)
        engaged = (is_shooting or is_aiming) and mag > 100

        if engaged:
            # Registra a direção atual e o pull de persistência
            nx = rx / mag if mag > 0 else 0.0
            ny = ry / mag if mag > 0 else 0.0
            self._last_dir_x = nx
            self._last_dir_y = ny
            self._persist_rx = rx
            self._persist_ry = ry
            self._persist_until = t + 0.09  # 90ms de persistência

            # Pull proporcional à deflexão, limitado por magnetic_pull
            zone_factor = min(mag / 8000.0, 1.0)
            pull = magnetic_pull * strength * (0.35 + 0.65 * zone_factor)
            pull = min(pull, magnetic_pull)
            rx = rx + nx * pull
            ry = ry + ny * pull
        elif t < self._persist_until:
            # Persistência: mantém o último input decaindo rapidamente
            remaining = (self._persist_until - t) / 0.09
            decay = max(0.0, min(1.0, remaining))
            if abs(self._persist_rx) > 50:
                keep_x = abs(self._persist_rx) * 0.35 * decay
                rx = rx + math.copysign(keep_x, self._persist_rx) if rx == 0 else rx
            if abs(self._persist_ry) > 50:
                keep_y = abs(self._persist_ry) * 0.35 * decay
                ry = ry + math.copysign(keep_y, self._persist_ry) if ry == 0 else ry
        else:
            self._reset_persist()

        return max(-32767.0, min(32767.0, rx)), max(-32767.0, min(32767.0, ry))

    def _reset_persist(self) -> None:
        self._persist_rx = 0.0
        self._persist_ry = 0.0
        self._persist_until = 0.0

    def reset(self) -> None:
        self._reset_persist()
        self._last_dir_x = 0.0
        self._last_dir_y = 0.0


class AimLockEngine:
    """Aim Lock estilo Zen: trava forte com suavização dentro do FOV.

    Quando atirando e o input está dentro de ``fov``, aplica pull forte na
    direção do movimento do stick (mantém a mira "presa" no alvo) com
    suavização EMA para evitar overshoot. Sem screen capture, o lock é
    inferido do input: se o jogador está engajado e o retículo já está
    próximo (baixa deflexão), reforçamos o movimento naquela direção.
    """

    def __init__(self) -> None:
        self._smooth_rx: float = 0.0
        self._smooth_ry: float = 0.0

    def apply(self, rx: float, ry: float, *, enabled: bool,
              strength: int, fov: int, track: int, sticky: float,
              smooth: float, is_shooting: bool, is_aiming: bool,
              delta_ms: float) -> Tuple[float, float]:
        if not enabled or strength <= 0 or fov <= 0:
            self._smooth_rx = 0.0
            self._smooth_ry = 0.0
            return rx, ry

        mag = math.sqrt(rx * rx + ry * ry)
        if mag > fov or mag < 50:
            self._smooth_rx = 0.0
            self._smooth_ry = 0.0
            return rx, ry

        if not (is_shooting or is_aiming):
            return rx, ry

        # Proximidade dentro do FOV: mais perto = mais trava
        proximity = 1.0 - (mag / fov)
        nx = rx / mag
        ny = ry / mag

        # Pull de lock: força do lock * proximidade * sticky
        lock_pull = (strength / 12000.0) * (0.3 + 0.7 * proximity) * max(0.1, sticky)
        pull_x = nx * lock_pull * 900.0
        pull_y = ny * lock_pull * 900.0

        # Suavização EMA (anti-overshoot)
        if smooth > 0:
            weight = min(0.85, max(0.10, 1.0 - smooth))
            self._smooth_rx = self._smooth_rx * (1.0 - weight) + (rx + pull_x) * weight
            self._smooth_ry = self._smooth_ry * (1.0 - weight) + (ry + pull_y) * weight
            out_rx, out_ry = self._smooth_rx, self._smooth_ry
        else:
            out_rx, out_ry = rx + pull_x, ry + pull_y

        # Track: reforço contínuo enquanto mantém o stick na direção
        if track > 0 and mag > 100:
            track_boost = (track / 2000.0) * proximity * 300.0
            out_rx = out_rx + nx * track_boost
            out_ry = out_ry + ny * track_boost

        return max(-32767.0, min(32767.0, out_rx)), max(-32767.0, min(32767.0, out_ry))

    def reset(self) -> None:
        self._smooth_rx = 0.0
        self._smooth_ry = 0.0


class AimSpamEngine:
    """Aim spam estilo Zen: micro-cycle rápido de ADS.

    Durante tiro contínuo, alterna o ADS (LT) brevemente para refrescar o
    AA nativo do jogo (o magnetismo re-engaja a cada re-ADS). Desligado por
    padrão — em xCloud pode interferir no ADS real.
    """

    def __init__(self) -> None:
        self._phase_start: float = 0.0
        self._cycle_active: bool = False

    def process_trigger(self, lt: float, is_shooting: bool, enabled: bool,
                        interval_ms: float, hold_ms: float,
                        now: Optional[float] = None) -> float:
        if not enabled or not is_shooting or lt <= 10:
            self._cycle_active = False
            return lt

        t = now if now is not None else time.monotonic()

        if not self._cycle_active:
            self._phase_start = t
            self._cycle_active = True

        elapsed_ms = (t - self._phase_start) * 1000.0
        cycle_ms = interval_ms + hold_ms

        # Dentro da janela de "release": solta o ADS para refrescar o AA
        if elapsed_ms >= interval_ms:
            if elapsed_ms >= cycle_ms:
                self._phase_start = t
                return lt
            return 0.0

        return lt

    def reset(self) -> None:
        self._cycle_active = False
        self._phase_start = 0.0


class RushEngine:
    """Rush strafe (estilo Zen): alterna o left stick em onda quadrada.

    Enquanto ativo (mirando e a AA rotacional ligada, ou rush_always),
    injeta um strafe lateral alternando ``+amp`` / ``-amp`` no left stick,
    com ciclo ``pulse_ms`` ligado e ``cooldown_ms`` desligado. O deadzone
    do right stick é usado como limiar: se o jogador está mexendo muito a
    mira, o strafe é atenuado para não atrapalhar.
    """

    def __init__(self, pulse_ms: float = 1.5, cooldown_ms: float = 80.0,
                 deadzone: float = 0.13) -> None:
        self._active: bool = False
        self._phase: float = 0.0
        self._direction: int = 1
        self._pulse_ms: float = pulse_ms
        self._cooldown_ms: float = cooldown_ms
        self._deadzone: float = deadzone

    def set_active(self, active: bool) -> None:
        if active and not self._active:
            self._phase = 0.0
            self._direction = 1
        self._active = active

    def get_strafe(self, now: float) -> int:
        if not self._active:
            return 0
        cycle_ms = self._pulse_ms + self._cooldown_ms
        pos = (now * 1000.0) % cycle_ms
        # Fase de "pulso": empurra o stick para o lado. Fora dela, volta ao neutro.
        if pos < self._pulse_ms:
            return self._direction * 2400
        # Na transição para o cooldown, inverte a direção para o próximo pulso.
        if pos - self._pulse_ms < 2.0:
            self._direction = -self._direction
        return 0

    def update_config(self, pulse_ms: float, cooldown_ms: float, deadzone: float) -> None:
        self._pulse_ms = pulse_ms
        self._cooldown_ms = cooldown_ms
        self._deadzone = deadzone

    def reset(self) -> None:
        self._active = False
        self._phase = 0.0
        self._direction = 1


class AutoRotationEngine:
    """Auto Rotation (surpresa estilo Zen): gira o right stick sem input.

    Sem screen capture, o único proxy honesto de "alvo" é a última direção
    que o jogador segurou no right stick. Quando o jogador solta o stick
    (mag < 60) enquanto atirando/mirando, injeta um drift sinusoidal suave
    nessa direção (escalado por ``speed``). O AA nativo do jogo re-engaja
    com esse micro-movimento — a câmera continua "perseguindo" sozinha.
    """

    def __init__(self) -> None:
        self._bearing_x: float = 0.0
        self._bearing_y: float = 0.0
        self._has_bearing: bool = False
        self._phase: float = 0.0
        self._engaged: bool = False

    def apply(self, rx: float, ry: float, *, enabled: bool,
              speed: int, is_shooting: bool, is_aiming: bool,
              delta_ms: float) -> Tuple[float, float]:
        mag = math.sqrt(rx * rx + ry * ry)
        engaged = (is_shooting or is_aiming) and enabled

        if mag >= 60:
            # Jogador está segurando o stick: atualiza a direção de referência
            # e desliga a rotação automática.
            self._bearing_x = rx / mag
            self._bearing_y = ry / mag
            self._has_bearing = True
            self._engaged = False
            self._phase = 0.0
            return rx, ry

        if not engaged or not self._has_bearing:
            self._engaged = False
            self._phase = 0.0
            return rx, ry

        # Stick solto + mirando/atirando: gira suavemente na última direção.
        if not self._engaged:
            self._engaged = True
            self._phase = 0.0

        self._phase += delta_ms / 1000.0
        # Envelope sinusoidal: começa fraco, acelera, e oscila para re-disparar
        # o magnetismo nativo sem parecer um aimbot rígido.
        envelope = 0.35 + 0.65 * math.sin(self._phase * 1.2)
        amp = max(20.0, min(300.0, speed * 0.5)) * envelope
        out_rx = rx + self._bearing_x * amp
        out_ry = ry + self._bearing_y * amp
        return max(-32767.0, min(32767.0, out_rx)), max(-32767.0, min(32767.0, out_ry))

    def reset(self) -> None:
        self._bearing_x = 0.0
        self._bearing_y = 0.0
        self._has_bearing = False
        self._phase = 0.0
        self._engaged = False


class HeadAssistEngine:
    """Head Assist / Head Lock: tende a mira para a cabeça sem screen capture.

    O AA nativo do jogo já está "grudado" no alvo quando o jogador está
    engajado (mirando/atirando) e o input do right stick é pequeno — isso
    significa que o retículo está perto do corpo do inimigo. Nesse estado,
    injetamos um pull vertical para cima (eixo Y negativo), que desloca a
    mira em direção à cabeça. É o equivalente aproximado do "aimPoint: top"
    dos aimbots, mas sem visão computacional — o engajamento do AA nativo
    é o proxy de "estou no alvo".

    Upgrade estilo Zen ("Head Magnet"): o pull pode operar em modo PULSO —
    micro-ciclo sobe/segura que re-dispara o magnetismo nativo do jogo a
    cada pulso (mesma ideia do L2 spam, mas no stick) — e com ``drift_limit``
    o pull é reduzido quando o jogador puxa o stick para baixo (para não
    brigar com o counter-strafe do inimigo nem com o anti-recoil manual).
    """

    def __init__(self) -> None:
        self._engage: float = 0.0
        self._last_ry: float = 0.0
        self._pulse_phase: float = 0.0

    def apply(self, rx: float, ry: float, *, enabled: bool,
              strength: float, is_shooting: bool, is_aiming: bool,
              delta_ms: float, lock_window: int = 3000,
              headlock_pulse: bool = False,
              headlock_pulse_ms: int = 60,
              drift_limit: int = 0,
              min_input: int = 150) -> Tuple[float, float]:
        """Aplica pull vertical para cima quando o AA nativo está engajado.

        - ``strength`` (0..1): 0 = centro do corpo, 1 = forte desvio p/ cabeça.
        - ``lock_window``: raio de engajamento (mag do input até onde o lock
          atua; default 3000 preserva o comportamento original).
        - ``headlock_pulse``: pull pulsado (sobe/segura) para re-disparar o
          magnetismo nativo a cada pulso. False = pull contínuo (original).
        - ``drift_limit``: se o jogador empurra o stick para baixo além
          desse valor, o pull é atenuado. 0 = sem limite (original).
        - ``min_input``: gate mínimo de input. Abaixo disso o head assist
          não engaja — evita que a câmera continue andando pra cima (pull)
          quando o jogador solta o stick completamente.
        - Só atua com input pequeno (retículo perto do alvo) + engajado.
        """
        if not enabled or strength <= 0:
            self._engage = 0.0
            self._last_ry = ry
            return rx, ry

        mag = math.sqrt(rx * rx + ry * ry)
        engaged = (is_shooting or is_aiming) and mag < lock_window and mag >= min_input

        if engaged:
            # Rampa de engajamento: sobe rápido ao grudar
            self._engage = min(1.0, self._engage + delta_ms / 40.0)
        else:
            self._engage = max(0.0, self._engage - delta_ms / 100.0)

        # Pull para cima: negativo em Y (cima), escalado pelo engajamento
        # e pela força. Aumenta com o tempo grudado (mais confiança = mais
        # desvio para a cabeça).
        pull = strength * self._engage * 1200.0

        # ── Head Lock pulse (estilo Zen "Head Magnet") ──
        # Ciclo em pull forte com queda curta (não solta de vez): o retículo
        # "bate" na tração nativa e VOLTA a segurar — mais pegada que o
        # antigo 50/50 (que parecia não travar).
        if headlock_pulse and headlock_pulse_ms > 0:
            cycle = max(1.0, float(headlock_pulse_ms))
            self._pulse_phase = (self._pulse_phase + max(0.0, delta_ms)) % cycle
            pulse_env = 1.0 if self._pulse_phase < cycle * 0.8 else 0.6
            pull *= pulse_env

        # ── Drift limit ──
        # Jogador puxando para baixo além do limite (fight de stick):
        # atenua o pull para não anular o que ele está fazendo.
        if drift_limit > 0 and ry > drift_limit:
            fight = max(0.0, 1.0 - (ry - drift_limit) / 8000.0)
            pull *= fight

        out_ry = ry - pull

        self._last_ry = out_ry
        return rx, max(-32767.0, min(32767.0, out_ry))

    def reset(self) -> None:
        self._engage = 0.0
        self._last_ry = 0.0
        self._pulse_phase = 0.0
