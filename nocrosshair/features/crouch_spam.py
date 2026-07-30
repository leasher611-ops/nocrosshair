#!/usr/bin/env python3
"""
Motor de Crouch Spam (estilo Cronus Zen).
Alterna o botão de agachar em alta frequência para dificultar
headshots adversários enquanto o jogador atira.

Arquitetura:
  - Máquina de estados com 2 fases: CROUCH (pressionado) e STAND (liberado)
  - Suporte a "only_while_shooting": só ativa durante tiro ativo
  - Temporização baseada em monotonic clock
  - Emissão de eventos de botão via VirtualController
"""

import time
from dataclasses import dataclass
from typing import Optional

from nocrosshair.core.config import CrouchSpamConfig


# Mapeamento de nomes de botão para códigos de evento evdev
BUTTON_MAP = {
    "B": 0x131,       # BTN_B (Xbox)
    "A": 0x130,       # BTN_A
    "X": 0x133,       # BTN_X
    "Y": 0x134,       # BTN_Y
    "Circle": 0x131,  # BTN_B (PS equivalente)
    "Cross": 0x130,   # BTN_A (PS equivalente)
    "RS": 0x13E,      # BTN_THUMBR (Right Stick Press)
    "LS": 0x13D,      # BTN_THUMBL (Left Stick Press)
}


@dataclass
class CrouchSpamState:
    """Estado interno do motor de Crouch Spam."""
    phase: str = "idle"           # "idle", "crouch", "stand"
    last_transition: float = 0.0  # timestamp da última transição
    cycle_count: int = 0          # ciclos completados
    is_crouched: bool = False     # estado atual de agachamento


class CrouchSpamEngine:
    """Motor de Crouch Spam com timing preciso.

    Quando ativo, emite rapidamente press/release do botão de agachar
    para criar o efeito de "crouch spam" usado em jogos FPS competitivos.

    Uso:
        engine = CrouchSpamEngine(config)
        # No loop de input:
        should_press = engine.process(is_shooting, delta_ms)
        if should_press is not None:
            controller.emit_button(button_code, should_press)
    """

    def __init__(self, config: CrouchSpamConfig):
        self.config = config
        self.state = CrouchSpamState()
        self._active = False

    def set_active(self, active: bool) -> None:
        """Liga/desliga o motor de crouch spam."""
        if active and not self._active:
            self.state = CrouchSpamState(
                phase="crouch",
                last_transition=time.monotonic(),
                cycle_count=0,
                is_crouched=False,
            )
        elif not active:
            self.state.phase = "idle"
            self.state.is_crouched = False
        self._active = active

    @property
    def is_active(self) -> bool:
        return self._active

    def toggle(self) -> bool:
        """Alterna o estado ativo. Retorna o novo estado."""
        self.set_active(not self._active)
        return self._active

    def get_button_code(self) -> int:
        """Retorna o código do botão de agachar baseado na config."""
        return BUTTON_MAP.get(self.config.crouch_button, 0x131)

    def process(self, is_shooting: bool, delta_ms: float) -> Optional[bool]:
        """Processa o estado de crouch spam.

        Args:
            is_shooting: Se o jogador está atirando
            delta_ms: Tempo desde o último frame em ms

        Returns:
            True = pressionar botão, False = liberar botão, None = sem ação
        """
        if not self._active:
            return None

        # Se configurado para "só durante tiro" e não está atirando, para
        if self.config.only_while_shooting and not is_shooting:
            if self.state.is_crouched:
                self.state.is_crouched = False
                self.state.phase = "idle"
                return False  # Libera o botão
            return None

        now = time.monotonic()
        elapsed_ms = (now - self.state.last_transition) * 1000.0

        if self.state.phase == "idle":
            self.state.phase = "crouch"
            self.state.last_transition = now
            self.state.is_crouched = True
            return True  # Pressiona agachar

        elif self.state.phase == "crouch":
            if elapsed_ms >= self.config.hold_ms:
                self.state.phase = "stand"
                self.state.last_transition = now
                self.state.is_crouched = False
                return False  # Libera agachar (levanta)
            return None  # Mantém estado atual

        elif self.state.phase == "stand":
            if elapsed_ms >= self.config.release_ms:
                self.state.phase = "crouch"
                self.state.last_transition = now
                self.state.cycle_count += 1
                self.state.is_crouched = True
                return True  # Pressiona agachar de novo
            return None  # Mantém estado atual

        return None

    def get_stats(self) -> dict:
        """Retorna estatísticas do motor para a UI."""
        effective_hz = 0
        if self._active and self.config.hold_ms + self.config.release_ms > 0:
            effective_hz = 1000.0 / (self.config.hold_ms + self.config.release_ms)
        return {
            "active": self._active,
            "phase": self.state.phase,
            "cycles": self.state.cycle_count,
            "effective_hz": round(effective_hz, 1),
            "is_crouched": self.state.is_crouched,
            "button": self.config.crouch_button,
        }

    def update_config(self, config: CrouchSpamConfig) -> None:
        """Atualiza a configuração em tempo real."""
        self.config = config
        if not config.enabled:
            self.set_active(False)
