#!/usr/bin/env python3
"""Motores de movimentação competitiva (estilo Zen, algoritmos originais).

Pesquisa pública (Reddit r/FortniteCompetitive, r/cronus_zen, Saw's mods):
- Dodge Shot: crouch + auto-stand durante tiro de perto — "very OP upclose,
  makes enemy lose aa". Crouch spam também reduz bloom do AR.
- Slide Cancel real (Fortnite): é momentum tech — tap crouch 2x enquanto
  sprintando (inicia e cancela o slide) e então jump, preservando o
  sprint-jump. Não é o macro jump->arc->crouch (isso é bunny-hop).
- Timings exatos não são públicos (GPC paywalled); ReWASD recomenda
  30-50ms entre teclas para o jogo reconhecer. Ajuste empírico.
- Anti-detecção: delays >= 30-50ms, nunca periodicidade perfeita.
"""

import time
from typing import Dict, Optional


class DodgeShotEngine:
    """Dodge Shot: alterna crouch (R3) durante o tiro de perto.

    Crouch on/off rápido enquanto atira faz o inimigo perder o AA e reduz
    a hitbox, sem sacrificar a cadência (não toca no gatilho). Gated por
    is_shooting. Com pequena variação no timing para não parecer periódico.
    """

    def __init__(self, hold_ms: int = 40, release_ms: int = 60,
                 crouch_button_code: int = 318):
        self._hold_ms = hold_ms
        self._release_ms = release_ms
        self._crouch_button_code = crouch_button_code
        self._phase_start: float = 0.0
        self._crouching: bool = False
        self._active: bool = False
        # Jitter por ciclo (0-N ms) — anti-detecção: nunca periódico perfeito,
        # mas nunca abaixo do mínimo de ~30ms (ReWASD).
        self._jitter_ms: float = 0.0

    def set_active(self, active: bool) -> None:
        if not active:
            self._crouching = False
        self._active = active

    def toggle(self) -> bool:
        self.set_active(not self._active)
        return self._active

    @property
    def is_active(self) -> bool:
        return self._active

    def process(self, is_shooting: bool, now: float) -> Dict[int, int]:
        if not self._active or not is_shooting:
            self._crouching = False
            return {}

        elapsed_ms = (now - self._phase_start) * 1000.0

        if self._crouching:
            if elapsed_ms >= self._hold_ms + self._jitter_ms:
                self._crouching = False
                self._phase_start = now
                self._jitter_ms = float(time.monotonic() % 10)  # 0-10ms de variação
                return {self._crouch_button_code: 0}
            return {self._crouch_button_code: 1}
        else:
            if elapsed_ms >= self._release_ms + self._jitter_ms:
                self._crouching = True
                self._phase_start = now
                self._jitter_ms = float(time.monotonic() % 12)  # 0-12ms de variação
                return {self._crouch_button_code: 1}
            return {}

        return {}

    def reset(self) -> None:
        self._crouching = False
        self._phase_start = 0.0
        self._jitter_ms = 0.0


class SlideCancelEngine2:
    """Slide Cancel (momentum tech): tap crouch 2x + jump.

    Ao detectar que o jogador pulou enquanto corre (notify_jump), dispara a
    sequência: crouch on -> crouch off -> crouch on -> crouch off -> jump,
    com delays >= 30ms entre teclas (ReWASD minimum). Preserva o momentum
    do sprint e evita o "new jump" do Fortnite.
    """

    # Estados da máquina
    IDLE = "idle"
    CROUCH1 = "crouch1"
    RELEASE1 = "release1"
    CROUCH2 = "crouch2"
    RELEASE2 = "release2"
    JUMP = "jump"

    def __init__(self, crouch_button_code: int = 318,
                 jump_button_code: int = 304,
                 tap_ms: int = 40, gap_ms: int = 40):
        self._crouch_button_code = crouch_button_code
        self._jump_button_code = jump_button_code
        self._tap_ms = tap_ms      # tempo segurando crouch
        self._gap_ms = gap_ms      # tempo entre taps
        self._state = self.IDLE
        self._state_start: float = 0.0
        self._active: bool = False

    def set_active(self, active: bool) -> None:
        if not active:
            self._state = self.IDLE
        self._active = active

    def toggle(self) -> bool:
        self.set_active(not self._active)
        return self._active

    @property
    def is_active(self) -> bool:
        return self._active

    def notify_jump(self) -> None:
        if self._active and self._state == self.IDLE:
            self._state = self.CROUCH1
            self._state_start = time.monotonic()

    def process(self, now: float) -> Dict[int, int]:
        if not self._active or self._state == self.IDLE:
            return {}

        elapsed = (now - self._state_start) * 1000.0

        if self._state == self.CROUCH1:
            if elapsed >= self._tap_ms:
                self._state = self.RELEASE1
                self._state_start = now
                return {self._crouch_button_code: 0}
            return {self._crouch_button_code: 1}

        elif self._state == self.RELEASE1:
            if elapsed >= self._gap_ms:
                self._state = self.CROUCH2
                self._state_start = now
                return {self._crouch_button_code: 1}
            return {}

        elif self._state == self.CROUCH2:
            if elapsed >= self._tap_ms:
                self._state = self.RELEASE2
                self._state_start = now
                return {self._crouch_button_code: 0}
            return {self._crouch_button_code: 1}

        elif self._state == self.RELEASE2:
            if elapsed >= self._gap_ms:
                self._state = self.JUMP
                self._state_start = now
                return {self._jump_button_code: 1}
            return {}

        elif self._state == self.JUMP:
            if elapsed >= self._tap_ms:
                self._state = self.IDLE
                self._state_start = now
                return {self._jump_button_code: 0}
            return {self._jump_button_code: 1}

        return {}

    def reset(self) -> None:
        self._state = self.IDLE
        self._state_start = 0.0


class BunnyHopEngine:
    """Bunny Hop: re-press de jump em cadência enquanto corre.

    Pular repetidamente mantém o momentum e dificulta acerto. Simples:
    quando ativo e o jogador está em movimento, dispara jumps com variação
    de timing (evita periodicidade perfeita = anti-detecção).
    """

    def __init__(self, jump_button_code: int = 304,
                 hold_ms: int = 50, gap_ms: int = 120):
        self._jump_button_code = jump_button_code
        self._hold_ms = hold_ms
        self._gap_ms = gap_ms
        self._phase_start: float = 0.0
        self._jumping: bool = False
        self._active: bool = False
        self._jitter = 0.0

    def set_active(self, active: bool) -> None:
        if not active:
            self._jumping = False
        self._active = active

    def toggle(self) -> bool:
        self.set_active(not self._active)
        return self._active

    @property
    def is_active(self) -> bool:
        return self._active

    def process(self, is_moving: bool, now: float) -> Dict[int, int]:
        if not self._active or not is_moving:
            self._jumping = False
            return {}

        elapsed_ms = (now - self._phase_start) * 1000.0
        if not self._jumping and elapsed_ms >= self._gap_ms + self._jitter:
            self._jumping = True
            self._phase_start = now
            self._jitter = (time.monotonic() % 25)  # variação 0-25ms
            return {self._jump_button_code: 1}
        elif self._jumping and elapsed_ms >= self._hold_ms:
            self._jumping = False
            self._phase_start = now
            return {self._jump_button_code: 0}
        elif self._jumping:
            return {self._jump_button_code: 1}
        return {}

    def reset(self) -> None:
        self._jumping = False
        self._phase_start = 0.0
        self._jitter = 0.0
