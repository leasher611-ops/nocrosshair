import time
from typing import Dict, Optional

from nocrosshair.core.config import SlideCancelConfig

STATE_IDLE = "idle"
STATE_JUMP_WAIT = "jump_wait"
STATE_CROUCH = "crouch"
STATE_JUMP_AGAIN = "jump_again"
STATE_COOLDOWN = "cooldown"


class SlideCancelEngine:

    def __init__(self, config: SlideCancelConfig):
        self.config = config
        self._active = False
        self._state = STATE_IDLE
        self._state_start: float = 0.0
        self._pending_output: Dict[int, int] = {}
        self._last_space_press: float = 0.0

    def set_active(self, active: bool) -> None:
        if not active:
            self._reset()
        self._active = active

    def toggle(self) -> bool:
        self.set_active(not self._active)
        return self._active

    @property
    def is_active(self) -> bool:
        return self._active

    def _reset(self) -> None:
        self._state = STATE_IDLE
        self._state_start = 0.0
        self._pending_output = {}

    def notify_space_pressed(self) -> None:
        self._last_space_press = time.monotonic()

    def process(self, now: float) -> Dict[int, int]:
        if not self._active:
            return {}

        if self._state == STATE_IDLE:
            elapsed_since_space = (now - self._last_space_press) * 1000.0
            if self._last_space_press > 0 and elapsed_since_space < 50:
                self._state = STATE_JUMP_WAIT
                self._state_start = now
            return {}

        elif self._state == STATE_JUMP_WAIT:
            elapsed = (now - self._state_start) * 1000.0
            if elapsed >= self.config.jump_arc_ms:
                self._pending_output = {
                    self.config.crouch_button_code: 1,
                    self.config.jump_button_code: 0,
                }
                self._state = STATE_CROUCH
                self._state_start = now
            return dict(self._pending_output)

        elif self._state == STATE_CROUCH:
            elapsed = (now - self._state_start) * 1000.0
            if elapsed >= self.config.crouch_hold_ms:
                self._pending_output = {
                    self.config.crouch_button_code: 0,
                    self.config.jump_button_code: 1,
                }
                self._state = STATE_JUMP_AGAIN
                self._state_start = now
            return dict(self._pending_output)

        elif self._state == STATE_JUMP_AGAIN:
            elapsed = (now - self._state_start) * 1000.0
            if elapsed >= self.config.jump_hold_ms:
                self._pending_output = {
                    self.config.crouch_button_code: 0,
                    self.config.jump_button_code: 0,
                }
                self._state = STATE_COOLDOWN
                self._state_start = now
            return dict(self._pending_output)

        elif self._state == STATE_COOLDOWN:
            elapsed = (now - self._state_start) * 1000.0
            if elapsed >= self.config.cooldown_ms:
                self._reset()
            return {}

        return {}

    def get_pending_output(self) -> Dict[int, int]:
        return dict(self._pending_output)

    def update_config(self, config: SlideCancelConfig) -> None:
        self.config = config
        if not self.config.enabled:
            self.set_active(False)
