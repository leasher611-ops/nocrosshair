#!/usr/bin/env python3

import math
from typing import Dict, Any, Tuple, Optional, List, Set
from evdev import ecodes as e

DEFAULT_KBD_BINDINGS: Dict[str, str] = {
    "KEY_W": "ABS_Y_MIN",
    "KEY_S": "ABS_Y_MAX",
    "KEY_A": "ABS_X_MIN",
    "KEY_D": "ABS_X_MAX",
    # Botões de face: o pipeline usa a convenção XBOX (letra) — BTN_X =
    # recarregar (Quadrado), BTN_Y = picareta (Triângulo). O jogo lê o pad
    # por índice na ordem padrão, então esses códigos batem direto.
    "KEY_SPACE": "BTN_A",          # Pular -> A do Xbox (Cruz)
    # Shift é o botão de correr: L3/left stick press.
    # C continua sendo agachar: R3/right stick press.
    "KEY_LEFTSHIFT": "BTN_THUMBL", # Correr -> Click analógico esquerdo (L3)
    "KEY_C": "BTN_THUMBR",         # Agachar -> Click analógico direito (R3)
    "KEY_R": "BTN_X",              # Recarregar -> X do Xbox (Quadrado)
    "KEY_E": "BTN_X",              # Coletar -> X do Xbox (Quadrado)
    "KEY_Q": "BTN_B",              # Granada de impulso -> B do Xbox (Círculo)
    "KEY_F": "BTN_Y",              # Picareta / última arma -> Y do Xbox (Triângulo)
    "BTN_RIGHT": "ABS_Z",          # Mirar (Botão direito do mouse) -> L2
    "BTN_LEFT": "ABS_RZ",          # Atirar (Botão esquerdo do mouse) -> R2
    "KEY_TAB": "ABS_HAT0Y_MIN",    # Abrir inventário -> D-Pad para cima
    "KEY_M": "BTN_SELECT",         # Abrir mapa -> Select / Share
    "KEY_B": "ABS_HAT0Y_MAX",      # Agradecer motorista/Emoji -> D-Pad para baixo
    # KEY_1..5 NÃO são remapeados de propósito: o jogo roda em KBM e as teclas
    # 1-5 selecionam o slot direto. Se fossem mapeados pra RB (ciclar), o jogo
    # receberia a tecla E o RB e o slot ia pra frente demais.
}

ACTION_MAP: Dict[str, int] = {
    "ABS_X": e.ABS_X, "ABS_Y": e.ABS_Y,
    "ABS_RX": e.ABS_RX, "ABS_RY": e.ABS_RY,
    "ABS_Z": e.ABS_Z, "ABS_RZ": e.ABS_RZ,
    "ABS_HAT0X": e.ABS_HAT0X, "ABS_HAT0Y": e.ABS_HAT0Y,
    "BTN_A": e.BTN_A, "BTN_B": e.BTN_B,
    "BTN_X": e.BTN_X, "BTN_Y": e.BTN_Y,
    "BTN_TL": e.BTN_TL, "BTN_TR": e.BTN_TR,
    "BTN_SELECT": e.BTN_SELECT, "BTN_START": e.BTN_START,
    "BTN_THUMBL": e.BTN_THUMBL, "BTN_THUMBR": e.BTN_THUMBR,
    "BTN_MODE": e.BTN_MODE,
    "BTN_LEFT": e.BTN_LEFT, "BTN_RIGHT": e.BTN_RIGHT,
    "BTN_MIDDLE": e.BTN_MIDDLE,
}


class InputRemapper:

    def __init__(self, bindings: Dict[str, str], mouse_sens: float = 80.0,
                 curve: float = 0.65, sens_x: float = 80.0, sens_y: float = 80.0,
                 smooth: float = 0.0, min_output: float = 0.0, square_stick: bool = True):
        self.bindings = dict(bindings) if bindings else {}
        if not self.bindings:
            self.bindings = dict(DEFAULT_KBD_BINDINGS)
        self.mouse_sens = mouse_sens
        self.sens_x = sens_x if sens_x > 0 else mouse_sens
        self.sens_y = sens_y if sens_y > 0 else mouse_sens
        self.curve = curve
        self.smooth = smooth
        self.min_output = min_output
        self.square_stick = square_stick
        self._dt_ema = 1.0
        self.smooth_rx = 0.0
        self.smooth_ry = 0.0

    def process_key(self, key_code_str: str, value: int) -> Tuple[Optional[str], int]:
        action = self.bindings.get(key_code_str)
        if not action:
            return None, 0

        if action.endswith("_MIN"):
            return action.replace("_MIN", ""), -32767 if value else 0
        if action.endswith("_MAX"):
            return action.replace("_MAX", ""), 32767 if value else 0

        if action.endswith("_ON"):
            return action.replace("_ON", ""), 1 if value else 0

        return action, value

    def process_mouse_move(self, dx: int, dy: int, dt_ms: float = 1.0) -> Tuple[float, float]:
        if abs(dx) + abs(dy) < 1:
            self.smooth_rx *= 0.2
            self.smooth_ry *= 0.2
            if abs(self.smooth_rx) < 1.0:
                self.smooth_rx = 0.0
            if abs(self.smooth_ry) < 1.0:
                self.smooth_ry = 0.0
            return 0.0, 0.0

        # Filtra o tempo entre eventos (dt_ms) para evitar picos de sensibilidade
        if dt_ms < 50.0:
            self._dt_ema = self._dt_ema * 0.85 + dt_ms * 0.15
        else:
            self._dt_ema = 2.0

        dt_clamped = max(0.5, min(self._dt_ema, 8.0))
        velocity_scale = min(1.0 / dt_clamped, 2.5)

        out_x = dx * self.sens_x * 40 * velocity_scale
        out_y = dy * self.sens_y * 40 * velocity_scale

        norm_x = out_x / 32767.0
        norm_y = out_y / 32767.0

        mag = math.sqrt(norm_x * norm_x + norm_y * norm_y)
        if mag < 0.0001:
            self.smooth_rx *= 0.2
            self.smooth_ry *= 0.2
            return 0.0, 0.0

        if mag < self.min_output:
            scale = self.min_output / mag
            norm_x *= scale
            norm_y *= scale
            mag = self.min_output

        curved_mag = mag ** self.curve
        if mag > 0:
            norm_x = (norm_x / mag) * curved_mag
            norm_y = (norm_y / mag) * curved_mag

        if self.square_stick and abs(norm_x) > 0.0001 and abs(norm_y) > 0.0001:
            nx = max(-1.0, min(1.0, norm_x))
            ny = max(-1.0, min(1.0, norm_y))
            u = nx * math.sqrt(1.0 - (ny * ny) * 0.5)
            v = ny * math.sqrt(1.0 - (nx * nx) * 0.5)
            norm_x, norm_y = u, v

        target_rx = norm_x * 32767.0
        target_ry = norm_y * 32767.0

        if abs(target_rx) < 20:
            target_rx = 0.0
        if abs(target_ry) < 20:
            target_ry = 0.0

        # Filtro passa-baixa suave para suavizar micro-tremores na mira do mouse
        weight = min(0.85, max(0.10, 1.0 - (self.smooth * 0.9)))
        self.smooth_rx = self.smooth_rx * (1.0 - weight) + target_rx * weight
        self.smooth_ry = self.smooth_ry * (1.0 - weight) + target_ry * weight

        if abs(self.smooth_rx) < 20:
            self.smooth_rx = 0.0
        if abs(self.smooth_ry) < 20:
            self.smooth_ry = 0.0

        return max(-32767.0, min(32767.0, self.smooth_rx)), \
               max(-32767.0, min(32767.0, self.smooth_ry))

    def resolve_action(self, action: str) -> Optional[int]:
        return ACTION_MAP.get(action)


class RemapPipeline:

    def __init__(self, bindings: Dict[str, str], mouse_sens: float = 80.0,
                 curve: float = 0.65, sens_x: float = 80.0, sens_y: float = 80.0,
                 smooth: float = 0.0, min_output: float = 0.0, square_stick: bool = True):
        self.remapper = InputRemapper(bindings, mouse_sens=mouse_sens, curve=curve,
                                       sens_x=sens_x, sens_y=sens_y, smooth=smooth,
                                       min_output=min_output, square_stick=square_stick)
        self.active_keys: Set[str] = set()
        self._output_state: Dict[str, int] = {}

    def update_key(self, code_str: str, value: int):
        if value:
            self.active_keys.add(code_str)
        else:
            self.active_keys.discard(code_str)

        # Resolve binding directly from raw bindings dict to get the full action string
        raw_action = self.remapper.bindings.get(code_str)
        if raw_action is None:
            return

        # Compute the output value for this key/state
        action, out_val = self.remapper.process_key(code_str, value)
        if action is None:
            return

        # For axis actions, recalculate full axis value from all currently active keys
        # to handle multi-key conflicts correctly (e.g. W+S = 0)
        if action in ("ABS_X", "ABS_Y", "ABS_HAT0X", "ABS_HAT0Y"):
            # Recalculate net value for this axis across all active keys
            net = 0
            for k in self.active_keys:
                a, v = self.remapper.process_key(k, 1)
                if a == action:
                    net += v
            net = max(-32767, min(32767, net))
            self._output_state[action] = net
        else:
            self._output_state[action] = out_val

    def get_stick_values(self) -> Tuple[int, int]:
        lx = self._output_state.get("ABS_X", 0)
        ly = self._output_state.get("ABS_Y", 0)

        # Diagonal normalization
        if lx != 0 and ly != 0:
            lx = int(lx * 0.707)
            ly = int(ly * 0.707)
        return lx, ly

    def get_trigger_values(self) -> Tuple[int, int]:
        lt = self._output_state.get("ABS_Z", 0)
        rt = self._output_state.get("ABS_RZ", 0)
        return 255 if lt else 0, 255 if rt else 0

    def get_hat_values(self) -> Tuple[int, int]:
        hx = self._output_state.get("ABS_HAT0X", 0)
        hy = self._output_state.get("ABS_HAT0Y", 0)
        return hx, hy

    def get_active_keys(self) -> Set[str]:
        return set(self.active_keys)

    def reset(self):
        self.active_keys.clear()
        self._output_state.clear()

