"""
Motor de Crouch Aim (estilo Cronus Zen).
Enquanto o jogador está mirando (ADS), segura o botão de agachar —
reduz o hitbox e "aperta" o crosshair. Solta quando desmira.

Arquitetura:
  - Segue o estado de ADS (BTN_RIGHT / gatilho L2)
  - Emite apenas o botão de agachar (default R3 / BTN_THUMBR)
  - Garante release no desativar (não deixa o botão preso)
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class CrouchAimState:
    aiming: bool = False
    last_state: Optional[bool] = None


class CrouchAimEngine:

    def __init__(self, config):
        self.config = config
        self.state = CrouchAimState()
        self._active = False

    def set_active(self, active: bool) -> None:
        if active and not self._active:
            self.state = CrouchAimState()
        self._active = active

    @property
    def is_active(self) -> bool:
        return self._active

    def toggle(self) -> bool:
        self.set_active(not self._active)
        return self._active

    def get_button_code(self) -> int:
        return int(self.config.button_code)

    def process(self, is_aiming: bool) -> Optional[bool]:
        """Retorna True (agachar), False (levantar) ou None (sem mudança)."""
        if not self._active:
            if self.state.last_state:
                self.state.last_state = False
                self.state.aiming = False
                return False
            return None

        if is_aiming == self.state.last_state:
            return None

        self.state.last_state = is_aiming
        self.state.aiming = is_aiming
        return is_aiming

    def get_stats(self) -> dict:
        return {
            "active": self._active,
            "aiming": self.state.aiming,
            "button": hex(self.config.button_code),
        }

    def update_config(self, config) -> None:
        self.config = config
        if not config.enabled:
            self.set_active(False)