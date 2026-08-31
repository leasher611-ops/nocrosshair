#!/usr/bin/env python3

import threading
from typing import Optional, Tuple
from evdev import uinput, ecodes as e, AbsInfo

from nocrosshair.core.config import ControllerType
from nocrosshair.controllers.registry import registry
from nocrosshair.controllers.descriptor import ControllerDescriptor

def _make_capabilities(ctrl_type: str) -> Tuple[dict, int, int]:
    # ATENÇÃO: BTN_TL2/BTN_TR2 PRECISAM estar declarados. O jogo lê os botões
    # por ÍNDICE (ordem crescente dos códigos, padrão DirectInput). Sem eles,
    # Select/Start/L3/R3 deslocam 2 posições (Shift vira Start, C vira L3...).
    btns = [
        e.BTN_A, e.BTN_B, e.BTN_X, e.BTN_Y,
        e.BTN_TL, e.BTN_TR, e.BTN_TL2, e.BTN_TR2,
        e.BTN_SELECT, e.BTN_START,
        e.BTN_THUMBL, e.BTN_THUMBR, e.BTN_MODE
    ]
    axes = [
        (e.ABS_X, AbsInfo(0, -32768, 32767, 0, 15, 0)),
        (e.ABS_Y, AbsInfo(0, -32768, 32767, 0, 15, 0)),
        (e.ABS_RX, AbsInfo(0, -32768, 32767, 0, 15, 0)),
        (e.ABS_RY, AbsInfo(0, -32768, 32767, 0, 15, 0)),
        (e.ABS_Z, AbsInfo(0, 0, 255, 0, 0, 0)),
        (e.ABS_RZ, AbsInfo(0, 0, 255, 0, 0, 0)),
        (e.ABS_HAT0X, AbsInfo(0, -1, 1, 0, 0, 0)),
        (e.ABS_HAT0Y, AbsInfo(0, -1, 1, 0, 0, 0)),
    ]

    if ctrl_type == "ds4":
        # DS4 real: stick esquerdo em ABS_X/Y, stick DIREITO em ABS_Z/RZ,
        # gatilhos L2/R2 em ABS_RX/RY (tudo 0..255).
        axes = [
            (e.ABS_X, AbsInfo(128, 0, 255, 0, 15, 0)),
            (e.ABS_Y, AbsInfo(128, 0, 255, 0, 15, 0)),
            (e.ABS_Z, AbsInfo(128, 0, 255, 0, 15, 0)),
            (e.ABS_RZ, AbsInfo(128, 0, 255, 0, 15, 0)),
            (e.ABS_RX, AbsInfo(0, 0, 255, 0, 0, 0)),
            (e.ABS_RY, AbsInfo(0, 0, 255, 0, 0, 0)),
            (e.ABS_HAT0X, AbsInfo(0, -1, 1, 0, 0, 0)),
            (e.ABS_HAT0Y, AbsInfo(0, -1, 1, 0, 0, 0)),
        ]
    elif ctrl_type in ("dualsense", "dualsense_edge"):
        # DualSense / DualSense Edge: mesmo layout físico do DS4
        # (stick direito em Z/RZ, gatilhos em RX/RY), mas com
        # range 0..255 centrado em 128.
        axes = [
            (e.ABS_X, AbsInfo(128, 0, 255, 0, 15, 0)),
            (e.ABS_Y, AbsInfo(128, 0, 255, 0, 15, 0)),
            (e.ABS_Z, AbsInfo(128, 0, 255, 0, 15, 0)),
            (e.ABS_RZ, AbsInfo(128, 0, 255, 0, 15, 0)),
            (e.ABS_RX, AbsInfo(0, 0, 255, 0, 0, 0)),
            (e.ABS_RY, AbsInfo(0, 0, 255, 0, 0, 0)),
            (e.ABS_HAT0X, AbsInfo(0, -1, 1, 0, 0, 0)),
            (e.ABS_HAT0Y, AbsInfo(0, -1, 1, 0, 0, 0)),
        ]

    capabilities = {e.EV_KEY: btns, e.EV_ABS: axes}

    if ctrl_type == "ds4":
        return capabilities, 0x054C, 0x09CC
    elif ctrl_type == "dualsense":
        return capabilities, 0x054C, 0x0CE6
    elif ctrl_type == "dualsense_edge":
        return capabilities, 0x054C, 0x0DF2
    elif ctrl_type == "xboxone":
        return capabilities, 0x045E, 0x02EA
    elif ctrl_type == "dualshock3":
        return capabilities, 0x054C, 0x0268
    elif ctrl_type == "switchpro":
        return capabilities, 0x057E, 0x2009
    else:
        return capabilities, 0x045E, 0x028E

def _controller_name(ctrl_type: str) -> str:
    names = {
        "ds4": "Sony Computer Entertainment Wireless Controller",
        "dualsense": "Sony DualSense Wireless Controller",
        "dualsense_edge": "Sony DualSense Edge Wireless Controller",
        "xboxone": "Microsoft Xbox One S Controller",
        "dualshock3": "Sony PLAYSTATION(R)3 Controller",
        "switchpro": "Nintendo Switch Pro Controller",
        "xbox360": "Microsoft X-Box 360 pad",
    }
    return names.get(ctrl_type, "Microsoft X-Box 360 pad")

_TYPE_ALIASES = {
    "dualshock4": "ds4",
    "dualshock5": "dualsense",
    "ds5": "dualsense",
    "dualsense5": "dualsense",
    "dualsense_edge": "dualsense_edge",
    "ds5edge": "dualsense_edge",
    "ds5_edge": "dualsense_edge",
}


def _normalize_type(ctrl_type: str) -> str:
    return _TYPE_ALIASES.get(ctrl_type, ctrl_type)


# Código canônico (pipeline, estilo Xbox) → eixo FÍSICO do DS4 real.
# O pipeline usa ABS_X/Y = stick esquerdo, ABS_RX/RY = stick direito,
# ABS_Z/RZ = gatilhos. No DS4 físico, o stick direito é ABS_Z/RZ e os
# gatilhos são ABS_RX/RY — então a saída virtual DS4 precisa trocar.
_DS4_OUTPUT_AXIS_MAP = {
    e.ABS_X: e.ABS_X,
    e.ABS_Y: e.ABS_Y,
    e.ABS_RX: e.ABS_Z,
    e.ABS_RY: e.ABS_RZ,
    e.ABS_Z: e.ABS_RX,
    e.ABS_RZ: e.ABS_RY,
}

# Cluster de stick (L3/R3/PS): o kernel enumera os botões do relatório na
# ORDEM NUMÉRICA dos códigos evdev (0x13A, 0x13B, 0x13C, 0x13D, 0x13E), mas o
# jogo lê o DS4 na ordem física (Share, Options, L3, R3, PS). Sem o swap o
# MODE(0x13C) cai no slot do L3, o THUMBL(0x13D) no slot do R3 e o THUMBR
# (0x13E) no do PS — Shift (correr) virava R3 e C (agachar) virava PS.
# A rotação abaixo reencaminha cada código para o slot correto do jogo.
# Só vale para pads lidos por índice (DS4/DS3/Switch Pro); no Xbox o wine
# mapeia por CÓDIGO evdev e a identidade é a correta.
_STICK_CLUSTER_ROTATION = {
    e.BTN_THUMBL: e.BTN_MODE,    # L3 → código que cai no slot L3 do jogo
    e.BTN_THUMBR: e.BTN_THUMBL,  # R3 → código que cai no slot R3 do jogo
    e.BTN_MODE: e.BTN_THUMBR,    # PS → código que cai no slot PS do jogo
}

# Face buttons no DS4 virtual: o pipeline é convenção XBOX (A=Cruz, B=Círculo,
# X=Quadrado, Y=Triângulo) e o kernel enumera A,B,X,Y nos índices 0-3. O jogo
# identifica o pad pelo VID/PID Sony e lê o relatório HID do DS4, cuja ordem
# de face é Quadrado, Cruz, Círculo, Triângulo. Sem a rotação, Q (Círculo,
# Xbox B, índice 1) cai no slot da Cruz e E/R (Quadrado, Xbox X, índice 2)
# caem no slot do Círculo. Y/Triângulo já está no slot 3 — identidade.
_DS4_FACE_ROTATION = {
    e.BTN_X: e.BTN_A,  # Quadrado → slot HID 0
    e.BTN_A: e.BTN_B,  # Cruz     → slot HID 1
    e.BTN_B: e.BTN_X,  # Círculo  → slot HID 2
}


def _map_button_for_output(ctrl_type: str, button_code: int) -> int:
    if ctrl_type in ("ds4", "dualsense", "dualsense_edge"):
        button_code = _DS4_FACE_ROTATION.get(button_code, button_code)
        return _STICK_CLUSTER_ROTATION.get(button_code, button_code)
    if ctrl_type in ("dualshock3", "switchpro"):
        return _STICK_CLUSTER_ROTATION.get(button_code, button_code)
    return button_code


class VirtualController:

    def __init__(self, ctrl_type: str = "xbox360"):
        ctrl_type = _normalize_type(ctrl_type)
        self.ctrl_type = ctrl_type
        self.device: Optional[uinput.UInput] = None
        self._lock = threading.Lock()

        try:
            cap, vid, pid = _make_capabilities(ctrl_type)
            name = _controller_name(ctrl_type)

            self.device = uinput.UInput(
                events=cap,
                name=name,
                vendor=vid,
                product=pid,
                version=0x0100,
                bustype=0x0003,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to create virtual controller: {e}")

    @classmethod
    def create_from_descriptor(cls, descriptor: ControllerDescriptor) -> "VirtualController":
        cap, _, _ = _make_capabilities(descriptor.id)
        ctrl = cls.__new__(cls)
        ctrl.ctrl_type = descriptor.id
        ctrl.device = None
        ctrl._lock = threading.Lock()
        try:
            ctrl.device = uinput.UInput(
                events=cap,
                name=descriptor.uinput_name,
                vendor=descriptor.uinput_vendor,
                product=descriptor.uinput_product,
                version=descriptor.uinput_version,
                bustype=0x0003,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to create virtual controller from descriptor: {e}")
        return ctrl

    def reconfigure_for_hardware(self, hw_id: str) -> bool:
        try:
            desc = registry.get_descriptor(hw_id)
        except KeyError:
            return False
        if self.device:
            try:
                self.reset()
                self.device.close()
            except Exception:
                pass
            finally:
                self.device = None
        try:
            cap, _, _ = _make_capabilities(hw_id)
            self.device = uinput.UInput(
                events=cap,
                name=desc.uinput_name,
                vendor=desc.uinput_vendor,
                product=desc.uinput_product,
                version=desc.uinput_version,
                bustype=0x0003,
            )
            self.ctrl_type = hw_id
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to reconfigure for hardware: {e}")

    def write_button(self, button_code: int, value: int) -> None:
        if self.device is None:
            return
        button_code = _map_button_for_output(self.ctrl_type, button_code)
        try:
            with self._lock:
                self.device.write(e.EV_KEY, button_code, value)
                self.device.syn()
        except Exception:
            pass

    def write_axis(self, axis_code: int, value: int) -> None:
        if self.device is None:
            return

        if self.ctrl_type in ("ds4", "dualsense", "dualsense_edge"):
            # Stick (código canônico) → 0..255 centrado em 128, escrito no
            # eixo físico do DS4/DS5 (stick direito vira ABS_Z/RZ).
            if axis_code in (e.ABS_X, e.ABS_Y, e.ABS_RX, e.ABS_RY):
                value = int((value + 32768) * 255 / 65535)
                value = max(0, min(255, value))
            # Gatilho → 0..255, escrito em ABS_RX/RY do DS4/DS5.
            else:
                value = max(0, min(255, value))
            axis_code = _DS4_OUTPUT_AXIS_MAP.get(axis_code, axis_code)

        try:
            with self._lock:
                self.device.write(e.EV_ABS, axis_code, value)
                self.device.syn()
        except Exception:
            pass

    def write_trigger(self, axis_code: int, value: int) -> None:
        value_clamped = max(0, min(255, value))
        self.write_axis(axis_code, value_clamped)

    def write_hat(self, x: int, y: int) -> None:
        if self.device is None:
            return
        try:
            with self._lock:
                self.device.write(e.EV_ABS, e.ABS_HAT0X, x)
                self.device.write(e.EV_ABS, e.ABS_HAT0Y, y)
                self.device.syn()
        except Exception:
            pass

    def reset(self) -> None:
        if self.device is None:
            return
        try:
            with self._lock:
                buttons = [e.BTN_A, e.BTN_B, e.BTN_X, e.BTN_Y,
                           e.BTN_TL, e.BTN_TR, e.BTN_TL2, e.BTN_TR2,
                           e.BTN_SELECT, e.BTN_START,
                           e.BTN_THUMBL, e.BTN_THUMBR, e.BTN_MODE]
                for btn in buttons:
                    self.device.write(e.EV_KEY, btn, 0)

                if self.ctrl_type in ("ds4", "dualsense", "dualsense_edge"):
                    axes = [
                        (e.ABS_X, 128), (e.ABS_Y, 128),
                        (e.ABS_Z, 128), (e.ABS_RZ, 128),
                        (e.ABS_RX, 0), (e.ABS_RY, 0),
                        (e.ABS_HAT0X, 0), (e.ABS_HAT0Y, 0),
                    ]
                else:
                    axes = [
                        (e.ABS_X, 0), (e.ABS_Y, 0),
                        (e.ABS_RX, 0), (e.ABS_RY, 0),
                        (e.ABS_Z, 0), (e.ABS_RZ, 0),
                        (e.ABS_HAT0X, 0), (e.ABS_HAT0Y, 0),
                    ]
                for axis, val in axes:
                    self.device.write(e.EV_ABS, axis, val)

                self.device.syn()
        except Exception:
            pass

    def change_type(self, ctrl_type: str) -> bool:
        ctrl_type = _normalize_type(ctrl_type)
        if self.device:
            try:
                self.reset()
                self.device.close()
            except Exception:
                pass
            finally:
                self.device = None
        try:
            cap, vid, pid = _make_capabilities(ctrl_type)
            name = _controller_name(ctrl_type)
            self.device = uinput.UInput(
                events=cap,
                name=name,
                vendor=vid,
                product=pid,
                version=0x0100,
                bustype=0x0003,
            )
            self.ctrl_type = ctrl_type
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to change controller type: {e}")

    def close(self) -> None:
        if self.device:
            try:
                self.reset()
                self.device.close()
            except Exception:
                pass
            finally:
                self.device = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        self.close()

class VirtualKeyboard:

    def __init__(self):
        self.device: Optional[uinput.UInput] = None
        self._lock = threading.Lock()

        try:
            self.device = uinput.UInput(
                events={e.EV_KEY: [v for k, v in vars(e).items() if k.startswith("KEY_") and isinstance(v, int) and 0 < v < 768]},
                name="Nocrosshair Virtual Keyboard",
            )
        except Exception as exc:
            raise RuntimeError(f"Failed to create virtual keyboard: {exc}") from exc

    def write_key(self, key_code: int, value: int) -> None:
        if self.device is None:
            return
        try:
            with self._lock:
                self.device.write(e.EV_KEY, key_code, value)
                self.device.syn()
        except Exception:
            pass

    def close(self) -> None:
        if self.device:
            try:
                self.device.close()
            except Exception:
                pass
            finally:
                self.device = None

    def __del__(self):
        self.close()

class VirtualMouse:

    def __init__(self):
        self.device: Optional[uinput.UInput] = None
        self._lock = threading.Lock()

        try:
            self.device = uinput.UInput(
                events={
                    e.EV_REL: [e.REL_X, e.REL_Y, e.REL_WHEEL, e.REL_HWHEEL],
                    e.EV_KEY: [e.BTN_LEFT, e.BTN_RIGHT, e.BTN_MIDDLE],
                },
                name="Nocrosshair Virtual Mouse",
            )
        except Exception as e:
            raise RuntimeError(f"Failed to create virtual mouse: {e}")

    def write_motion(self, dx: int, dy: int) -> None:
        if self.device is None:
            return
        try:
            with self._lock:
                if dx != 0:
                    self.device.write(e.EV_REL, e.REL_X, dx)
                if dy != 0:
                    self.device.write(e.EV_REL, e.REL_Y, dy)
                self.device.syn()
        except Exception:
            pass

    def write_button(self, button_code: int, value: int) -> None:
        if self.device is None:
            return
        try:
            with self._lock:
                self.device.write(e.EV_KEY, button_code, value)
                self.device.syn()
        except Exception:
            pass

    def close(self) -> None:
        if self.device:
            try:
                self.device.close()
            except Exception:
                pass
            finally:
                self.device = None

    def __del__(self):
        self.close()
