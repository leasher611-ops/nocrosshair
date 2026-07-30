#!/usr/bin/env python3

import os
import time
import math
import threading
from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass, field
from evdev import InputDevice, UInput, ecodes as e, categorize
from evdev.events import InputEvent

from nocrosshair.core.config import AppConfig
from nocrosshair.core.controller import VirtualController, VirtualKeyboard
from nocrosshair.features.physics import StickPhysicsEngine, TriggerPhysicsEngine
from nocrosshair.features.aim_assist import AimAssistEngine, AimAssistPipeline, ZeroDelayEngine, StrafeShotEngine
from nocrosshair.features.rapid_fire import RapidFireEngine
from nocrosshair.features.crouch_spam import CrouchSpamEngine
from nocrosshair.features.slide_cancel import SlideCancelEngine
from nocrosshair.features.recoil import AntiRecoilEngine
from nocrosshair.core.remapper import RemapPipeline, ACTION_MAP
from nocrosshair.core.shift_layers import shift_layer_manager, ShiftLayerManager
from nocrosshair.core.macro import macro_manager, MacroPlayer, MacroActionType
from nocrosshair.core.weapon_curves import weapon_curves_manager
from typing import Any
from nocrosshair.core.plugins import plugin_manager
from nocrosshair.features.polling import PollingEngine
from nocrosshair.features.triggers import TriggerEngine
from nocrosshair.features.gyro import GyroEngine
from nocrosshair.controllers.registry import registry

@dataclass
class RawInputState:
    lx: int = 0
    ly: int = 0
    rx: int = 0
    ry: int = 0
    lt: int = 0
    rt: int = 0
    hat_x: int = 0
    hat_y: int = 0
    buttons: dict = field(default_factory=dict)

    def update_axis(self, axis_code: int, value: int) -> None:
        if axis_code == e.ABS_X:
            self.lx = value
        elif axis_code == e.ABS_Y:
            self.ly = value
        elif axis_code == e.ABS_RX:
            self.rx = value
        elif axis_code == e.ABS_RY:
            self.ry = value
        elif axis_code == e.ABS_Z:
            self.lt = value
        elif axis_code == e.ABS_RZ:
            self.rt = value
        elif axis_code == e.ABS_HAT0X:
            self.hat_x = value
        elif axis_code == e.ABS_HAT0Y:
            self.hat_y = value


class InputPipeline:

    def __init__(self, config: AppConfig, overlay: Optional[Any] = None):
        self.config = config
        self.overlay = overlay
        self.ls_engine = StickPhysicsEngine(config.ls_physics)
        self.rs_engine = StickPhysicsEngine(config.rs_physics)
        self.lt_engine = TriggerPhysicsEngine(config.lt_physics)
        self.rt_engine = TriggerPhysicsEngine(config.rt_physics)
        self.aa_pipeline = AimAssistPipeline(
            AimAssistEngine(config.aim_assist)
        )
        self.zero_delay_engine = ZeroDelayEngine()
        self.strafe_shot_engine = StrafeShotEngine()

        # ── Motores Zen-like (Sprint 1) ──
        self.rapid_fire_engine = RapidFireEngine(config.rapid_fire)
        self.crouch_spam_engine = CrouchSpamEngine(config.crouch_spam)
        self.slide_cancel_engine = SlideCancelEngine(config.slide_cancel)
        self.anti_recoil_engine = AntiRecoilEngine(config.recoil)

        # ── Motores v4 (Hardware-aware) ──
        hw_id = config.controller_hardware.controller_id
        try:
            hw_class = registry.get(hw_id)
            self.descriptor = hw_class().descriptor
        except KeyError:
            self.descriptor = None
        self.trigger_engine = TriggerEngine(config.controller_hardware.trigger, self.descriptor) if self.descriptor else None
        self.gyro_engine = GyroEngine(config.controller_hardware.gyro) if (self.descriptor and self.descriptor.has_gyro) else None
        self.polling_engine = PollingEngine(
            config.controller_hardware.polling_rate_hz or (self.descriptor.polling_rate_hz if self.descriptor else 250)
        ) if self.descriptor else None
        
        # Sistema de Macros e Estado Injetado
        self.macro_player = MacroPlayer()
        self.macro_buttons: Dict[int, int] = {}
        self._macro_wait_until: float = 0.0
        
        # Analytics de Performance
        self.avg_latency: float = 0.0
        self._latency_samples: List[float] = []

        # ── Estado de Combate Dinâmico ──
        self.active_weapon_index: int = 0  # 0: Picareta, 1-5: Armas
        self.weapon_slots: List[str] = ["Pickaxe", "M416", "UMP45", "", "", ""]
        self.swap_triggers = {"KEY_F", "KEY_1", "KEY_2", "KEY_3", "KEY_4", "KEY_5", "BTN_Y", "BTN_MODE"}

        self.prev_rx: float = 0.0
        self.prev_ry: float = 0.0
        self.recoil_tick: int = 0
        self.recoil_active: bool = False
        self._pending_crouch: Optional[bool] = None
        self._slide_cancel_output: Dict[int, int] = {}
        self.last_time: float = time.monotonic()

    def process(self, raw: RawInputState) -> Tuple[int, int, int, int, int, int]:
        now = time.monotonic()
        delta_ms = (now - self.last_time) * 1000.0
        self.last_time = now

        # Before physics: apply trigger engine
        lt_raw = raw.lt
        rt_raw = raw.rt
        if self.trigger_engine:
            if raw.lt >= 0:
                lt_raw = self.trigger_engine.process(raw.lt)
            if raw.rt >= 0:
                rt_raw = self.trigger_engine.process(raw.rt)

        # Hook: Antes de qualquer processamento
        plugin_manager.call_hook("on_raw_input", raw)

        lx, ly = self.ls_engine.apply(raw.lx, raw.ly)
        rx, ry = self.rs_engine.apply(raw.rx, raw.ry)
        
        # Hook: Após física básica (pipeline)
        lx, ly, rx, ry = plugin_manager.call_hook_pipeline("on_post_physics", (lx, ly, rx, ry))

        lt = self.lt_engine.apply(lt_raw)
        rt = self.rt_engine.apply(rt_raw)

        # ── Zero Delay (AUREN+/Cronus): full trigger hold on press edge ──
        aa_cfg = self.config.aim_assist
        lt, rt = self.zero_delay_engine.process(
            lt, rt,
            enabled=aa_cfg.zero_delay,
            hold_ms=aa_cfg.zero_delay_ms,
            now=now,
        )

        is_shooting = rt > 10
        is_moving = abs(raw.lx) > 3000 or abs(raw.ly) > 3000
        is_aiming = lt > 10

        # ── Integração Reativa de Camadas (The "Foda" Part) ──
        # Se a camada "ADS" ou "Shift 1" estiver ativa, forçamos comportamentos específicos
        active_layers = shift_layer_manager.get_active_layers()
        
        # Sincroniza a arma baseada no slot de troca rápida
        current_weapon = self.weapon_slots[self.active_weapon_index]
        self.anti_recoil_engine.set_weapon(current_weapon)

        if "Shift 1" in active_layers or is_aiming:
            if "Sniper" in current_weapon:
                self.anti_recoil_engine.EMA_FACTOR = 0.15 # Muito mais suave para Snipers
            is_aiming = True 

        # ── Zen Anti-Recoil (Pattern-based with EMA Smoothing) ──
        if self.config.recoil.enabled:
            ry_off, rx_off = self.anti_recoil_engine.process(
                tick=self.recoil_tick,
                is_shooting=is_shooting,
                is_aiming=is_aiming,
                is_moving=is_moving,
                ry_raw=int(ry),
                rx_raw=int(rx),
                delta_ms=delta_ms,
                bloom_compensation=aa_cfg.bloom_compensation,
            )
            # Feedback Visual de Recuo
            if is_shooting and self.overlay:
                self.overlay.trigger_haptic(self.config.recoil.strength / 100.0)

            ry += ry_off
            rx += rx_off
            if is_shooting:
                self.recoil_tick += 1
            else:
                self.recoil_tick = 0

        # ── Processamento de Macros e Curvas Dynamicas ──
        self._process_macros(now)
        weapon_cfg = weapon_curves_manager.get_weapon_curve(current_weapon)
        
        # Aplica a curva Bezier/Power evoluída
        rx = weapon_curves_manager.apply_curve_to_input(rx / 32767.0, weapon_cfg["curve_x"]) * 32767.0
        ry = weapon_curves_manager.apply_curve_to_input(ry / 32767.0, weapon_cfg["curve_y"]) * 32767.0

        # Aplica a assistência de mira unificada para controle físico
        rx, ry = self.aa_pipeline.apply(rx, ry, is_shooting, is_aiming, is_moving, delta_ms,
                                         self.config.aim_assist, self.prev_rx, self.prev_ry)

        # Hook: Após assistência de mira (pipeline — plugins podem modificar rx, ry)
        rx, ry = plugin_manager.call_hook_pipeline("on_post_aa", (rx, ry))

        # After AA, before return: apply gyro to stick if enabled
        if self.gyro_engine and self.gyro_engine.config.enabled:
            gyro_rx, gyro_ry = self.gyro_engine.process((0, 0, 0), (0, 0, 0))
            rx = max(-32768, min(32767, rx + gyro_rx))
            ry = max(-32768, min(32767, ry + gyro_ry))

        # Telemetria: Calcula latência de processamento
        self._track_performance(time.monotonic() - now)

        # ── Rapid Fire: alterna RT em alta frequência ──
        if self.config.rapid_fire.enabled:
            rt = self.rapid_fire_engine.process_from_speed(
                int(rt), is_shooting, delta_ms
            )

        # ── Crouch Spam: armazena ação pendente para emissão de botão ──
        self._update_zen_features(is_shooting, delta_ms)

        self.prev_rx = rx
        self.prev_ry = ry

        lx = self.strafe_shot_engine.apply(
            int(lx),
            enabled=aa_cfg.strafe_shot_enabled,
            amplitude=aa_cfg.strafe_shot_amplitude,
            frequency=aa_cfg.strafe_shot_frequency,
            delta_ms=delta_ms,
        )

        return (
            max(-32767, min(32767, lx)),
            max(-32767, min(32767, int(ly))),
            max(-32767, min(32767, int(rx))),
            max(-32767, min(32767, int(ry))),
            max(0, min(255, int(lt))),
            max(0, min(255, int(rt)))
        )

    def apply_to_stick(self, rx: float, ry: float, is_shooting: bool,
                        is_aiming: bool, is_moving: bool, delta_ms: float
                        ) -> Tuple[float, float]:
        # ── Zen Anti-Recoil (Advanced) no caminho do Mouse ──
        if self.config.recoil.enabled:
            ry_off, rx_off = self.anti_recoil_engine.process(
                tick=self.recoil_tick,
                is_shooting=is_shooting,
                is_aiming=is_aiming,
                is_moving=is_moving,
                ry_raw=int(ry),
                rx_raw=int(rx),
                delta_ms=delta_ms,
                bloom_compensation=self.config.aim_assist.bloom_compensation,
            )
            ry += ry_off
            rx += rx_off
            if is_shooting:
                self.recoil_tick += 1
            else:
                self.recoil_tick = 0

        self._update_zen_features(is_shooting, delta_ms)

        # Aplica a assistência de mira unificada para teclado/mouse remapeado
        rx, ry = self.aa_pipeline.apply(rx, ry, is_shooting, is_aiming, is_moving, delta_ms,
                                         self.config.aim_assist, self.prev_rx, self.prev_ry)

        # Hook: plugins podem modificar rx, ry após AA (KBM path)
        rx, ry = plugin_manager.call_hook_pipeline("on_post_aa", (rx, ry))

        self.prev_rx = rx
        self.prev_ry = ry

        return max(-32767.0, min(32767.0, rx)), max(-32767.0, min(32767.0, ry))

    def _track_performance(self, latency_sec: float) -> None:
        """Rastreia e exibe latência no overlay."""
        ms = latency_sec * 1000.0
        self._latency_samples.append(ms)
        if len(self._latency_samples) > 100:
            self.avg_latency = sum(self._latency_samples) / 100
            self._latency_samples = []
            if self.overlay and self.config.visible:
                weapon = self.weapon_slots[self.active_weapon_index]
                telemetry = f"{weapon} | {self.avg_latency:.2f}ms"
                self.overlay.update_telemetry(telemetry)

    def _update_zen_features(self, is_shooting: bool, delta_ms: float) -> None:
        """Atualiza motores de Crouch Spam e outros estados temporais."""
        if self.config.crouch_spam.enabled:
            self._pending_crouch = self.crouch_spam_engine.process(is_shooting, delta_ms)
        else:
            self._pending_crouch = None
        # Slide Cancel processa seu próprio estado
        if self.slide_cancel_engine.is_active:
            self._slide_cancel_output = self.slide_cancel_engine.process(time.monotonic())

    def update_config(self, config: AppConfig) -> None:
        self.config = config
        self.ls_engine = StickPhysicsEngine(config.ls_physics)
        self.rs_engine = StickPhysicsEngine(config.rs_physics)
        self.lt_engine = TriggerPhysicsEngine(config.lt_physics)
        self.rt_engine = TriggerPhysicsEngine(config.rt_physics)
        self.aa_pipeline.update_config(config.aim_assist)
        # Atualiza motores Zen-style
        self.rapid_fire_engine.update_config(config.rapid_fire)
        self.crouch_spam_engine.update_config(config.crouch_spam)
        self.slide_cancel_engine.update_config(config.slide_cancel)
        self.anti_recoil_engine.update_config(config.recoil)
        self.anti_recoil_engine.set_weapon(config.recoil_runtime.active_preset)
        if not config.aim_assist.zero_delay:
            self.zero_delay_engine.reset()

    def set_macro(self, macro_name: str):
        m = macro_manager.get_macro(macro_name)
        if m: self.macro_player.play(m)

    def _process_macros(self, now: float) -> None:
        """Processa a execução de macros e injeção de estados virtuais."""
        if not self.macro_player.is_playing() or now < self._macro_wait_until:
            return

        while True:
            action = self.macro_player.get_next_action()
            if not action:
                return

            if action.action_type == MacroActionType.DELAY:
                self._macro_wait_until = now + (action.duration / 1000.0)
                return
            elif action.action_type == MacroActionType.PRESS:
                code = ACTION_MAP.get(action.target)
                if code is not None:
                    if action.target.startswith("BTN_"):
                        self.macro_buttons[code] = 1
            elif action.action_type == MacroActionType.RELEASE:
                code = ACTION_MAP.get(action.target)
                if code is not None:
                    if action.target.startswith("BTN_"):
                        self.macro_buttons[code] = 0

            self.macro_player.advance()

    def handle_weapon_swap(self, trigger: str) -> None:
        
        _SLOT_MAP = {
            "KEY_F": 0,
            "KEY_1": 1,
            "KEY_2": 2,
            "KEY_3": 3,
            "KEY_4": 4,
            "KEY_5": 5,
        }
        if trigger in _SLOT_MAP:
            self.active_weapon_index = _SLOT_MAP[trigger]
        elif trigger == "SCROLL_UP":
            self.active_weapon_index = (self.active_weapon_index - 1) % 6
        elif trigger == "SCROLL_DOWN":
            self.active_weapon_index = (self.active_weapon_index + 1) % 6
        elif trigger in ("BTN_Y", "BTN_MODE"):
            self.active_weapon_index = (self.active_weapon_index + 1) % 6

        
        self._game_weapon_index = self.active_weapon_index

        current_weapon = self.weapon_slots[self.active_weapon_index]
        
        if self.overlay:
            from nocrosshair.core.config import RECOIL_PRESETS
            color = RECOIL_PRESETS.get(current_weapon, {}).get("color", "#00ff88")
            self.overlay.update_color(color)


TAP_ONLY_KEYS = {"KEY_Q", "KEY_F"}


DS4_BUTTON_MAP = {
    0x130: e.BTN_A,       # 304 Cross -> BTN_A (A)
    0x131: e.BTN_B,       # 305 Circle -> BTN_B (B)
    0x132: e.BTN_X,       # 306 Square -> BTN_X (X)
    0x133: e.BTN_Y,       # 307 Triangle -> BTN_Y (Y)
    0x134: e.BTN_TL,      # 308 L1 -> BTN_TL (LB)
    0x135: e.BTN_TR,      # 309 R1 -> BTN_TR (RB)
    0x136: e.BTN_TL2,     # 310 L2 (digital) -> BTN_TL2
    0x137: e.BTN_TR2,     # 311 R2 (digital) -> BTN_TR2
    0x138: e.BTN_SELECT,  # 312 Share -> BTN_SELECT (Select/Back)
    0x139: e.BTN_START,   # 313 Options -> BTN_START (Start/Menu)
    0x13a: e.BTN_MODE,    # 314 PS Button -> BTN_MODE (Guide)
    0x13b: e.BTN_SELECT,  # 315 Touchpad Click -> BTN_SELECT
    0x13d: e.BTN_THUMBL,  # 317 L3 -> BTN_THUMBL
    0x13e: e.BTN_THUMBR,  # 318 R3 -> BTN_THUMBR
}


def _is_ds4_controller(dev: Optional[InputDevice]) -> bool:
    if not dev:
        return False
    try:
        vid = getattr(dev.info, 'vendor', 0)
        pid = getattr(dev.info, 'product', 0)
        if vid == 0x054C:
            return True
        name_lower = dev.name.lower()
        if any(k in name_lower for k in ("sony", "dualshock", "dualsense", "playstation", "wireless controller")):
            return True
        caps = dev.capabilities()
        if e.BTN_C in caps.get(e.EV_KEY, []):
            return True
    except Exception:
        pass
    return False


def _is_mouse_device(dev: Optional[InputDevice], mouse_fd: Optional[int] = None) -> bool:
    if not dev:
        return False
    if mouse_fd is not None and dev.fd == mouse_fd:
        return True
    try:
        caps = dev.capabilities()
        if e.EV_REL in caps:
            rel_caps = caps[e.EV_REL]
            if e.REL_X in rel_caps or e.REL_Y in rel_caps:
                return True
        key_caps = caps.get(e.EV_KEY, [])
        if e.BTN_LEFT in key_caps or e.BTN_RIGHT in key_caps:
            return True
    except Exception:
        pass
    return False


def _is_kbd_device(dev: Optional[InputDevice], kbd_fd: Optional[int] = None) -> bool:
    if not dev:
        return False
    if kbd_fd is not None and dev.fd == kbd_fd:
        return True
    try:
        caps = dev.capabilities()
        if e.EV_KEY in caps and e.EV_ABS not in caps and e.EV_REL not in caps:
            return True
    except Exception:
        pass
    return False


class InputLoop:

    def __init__(self, config: AppConfig, controller: VirtualController,
                 device_path: Optional[str] = None, overlay: Optional[Any] = None):
        self.config = config
        self.controller = controller
        self.device_path = device_path
        self.virtual_keyboard = VirtualKeyboard()
        self.pipeline = InputPipeline(config, overlay)
        self.raw = RawInputState()
        self._devices: List[InputDevice] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        self.shift_manager = shift_layer_manager
        self.remap_pipeline = RemapPipeline(config.kbd_bindings or {}, config.mouse_sens,
                                             sens_x=config.sens_x, sens_y=config.sens_y,
                                             curve=config.mouse_curve, smooth=config.mouse_smooth,
                                             min_output=config.mouse_min_output,
                                             square_stick=config.square_stick)
        self._mouse_fd: Optional[int] = None
        self._kbd_fd: Optional[int] = None
        self._mouse_passthrough: bool = False

        try:
            self.hw_descriptor = registry.get_descriptor(config.controller_hardware.controller_id)
        except KeyError:
            self.hw_descriptor = None

        # mutable loop state (set in _run)
        self._mouse_dx: int = 0
        self._mouse_dy: int = 0
        self._last_rx: float = 0.0
        self._last_ry: float = 0.0
        self._last_mouse_time: float = 0.0
        self._has_received_event: bool = False
        self._aa_rx: float = 0.0
        self._aa_ry: float = 0.0
        self._jitter_phase: float = 0.0
        self._disabled: bool = False

    def _find_device(self) -> Optional[str]:
        if self.device_path and os.path.exists(self.device_path):
            return self.device_path

        if self.config.remap_kbd_path or self.config.remap_mouse_path:
            return None

        import evdev
        for path in evdev.list_devices():
            if not os.path.exists(path):
                continue
            try:
                dev = InputDevice(path)
                caps = dev.capabilities()
                if e.EV_ABS in caps and e.EV_KEY in caps:
                    has_stick = (
                        e.ABS_X in caps.get(e.EV_ABS, {}) and
                        e.ABS_RX in caps.get(e.EV_ABS, {})
                    )
                    has_btn = e.BTN_A in caps.get(e.EV_KEY, [])
                    if has_stick and has_btn:
                        dev.close()
                        return path
                dev.close()
            except (PermissionError, OSError):
                continue

        return None

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True

        self._last_mouse_time = time.monotonic()
        self._has_received_event = False

        try:
            path = self.device_path or self._find_device()

            if path:
                dev = InputDevice(path)
                dev.grab()
                self._devices.append(dev)

            print("[InputLoop] Testing devices for 1s before grab...")
            time.sleep(0.5)

            grabbed_any = False
            if path:
                grabbed_any = True

            if self.config.remap_kbd_path and self.config.remap_kbd_path != path:
                try:
                    kbd = InputDevice(self.config.remap_kbd_path)
                    kbd.grab()
                    self._devices.append(kbd)
                    self._kbd_fd = kbd.fd
                    grabbed_any = True
                    print(f"[InputLoop] KBD grabbed: {kbd.name} ({self.config.remap_kbd_path})")
                except Exception as ex:
                    print(f"[InputLoop] KBD open failed: {ex}")

            if self.config.remap_mouse_path and self.config.remap_mouse_path != path:
                try:
                    mouse = InputDevice(self.config.remap_mouse_path)
                    mouse.grab()
                    self._devices.append(mouse)
                    self._mouse_fd = mouse.fd
                    grabbed_any = True
                    print(f"[InputLoop] Mouse grabbed: {mouse.name} ({self.config.remap_mouse_path})")
                except Exception as ex:
                    print(f"[InputLoop] Mouse grab failed: {ex}")

            # Auto-detect keyboard if not explicitly configured
            if self._kbd_fd is None:
                self._auto_open_keyboard(path)

            # Auto-detect mouse if not explicitly configured
            if self._mouse_fd is None:
                self._auto_open_mouse(path)

        except Exception as e:
            self._running = False
            for d in self._devices:
                try:
                    d.ungrab()
                    d.close()
                except Exception:
                    pass
            self._devices = []
            raise RuntimeError(f"Failed to grab devices: {e}")

        if not self._devices:
            self._running = False
            raise RuntimeError("No devices to read from")

        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _auto_open_keyboard(self, exclude_path: Optional[str] = None) -> None:
        """Auto-detect and open the first keyboard device for listening (no grab)."""
        import evdev
        existing_fds = {d.fd for d in self._devices}
        for dev_path in evdev.list_devices():
            if dev_path == exclude_path:
                continue
            try:
                dev = InputDevice(dev_path)
                if dev.fd in existing_fds:
                    dev.close()
                    continue
                caps = dev.capabilities()
                has_keys = e.EV_KEY in caps
                has_abs = e.EV_ABS in caps
                has_rel = e.EV_REL in caps
                if has_keys and not has_abs and not has_rel:
                    key_caps = caps.get(e.EV_KEY, [])
                    if e.KEY_A in key_caps and e.KEY_1 in key_caps:
                        dev.grab()
                        self._devices.append(dev)
                        self._kbd_fd = dev.fd
                        print(f"[InputLoop] KBD auto-detected and grabbed: {dev.name} ({dev_path})")
                        return
                dev.close()
            except (PermissionError, OSError):
                continue

    def _auto_open_mouse(self, exclude_path: Optional[str] = None) -> None:
        """Auto-detect and open the first mouse device for listening (no grab)."""
        import evdev
        existing_fds = {d.fd for d in self._devices}
        for dev_path in evdev.list_devices():
            if dev_path == exclude_path:
                continue
            try:
                dev = InputDevice(dev_path)
                if dev.fd in existing_fds:
                    dev.close()
                    continue
                caps = dev.capabilities()
                if e.EV_REL in caps:
                    rel_caps = caps[e.EV_REL]
                    if e.REL_X in rel_caps and e.REL_Y in rel_caps:
                        self._devices.append(dev)
                        self._mouse_fd = dev.fd
                        print(f"[InputLoop] Mouse auto-detected (no grab): {dev.name} ({dev_path})")
                        return
                dev.close()
            except (PermissionError, OSError):
                continue

    def stop(self) -> None:
        with self._lock:
            self._running = False

        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

        for dev in self._devices:
            try:
                dev.ungrab()
                dev.close()
            except Exception:
                pass
        self._devices = []
        self.controller.reset()
        if hasattr(self, 'virtual_keyboard') and self.virtual_keyboard:
            self.virtual_keyboard.close()

    def _write_mapped(self, action: str, value: int) -> None:
        code = ACTION_MAP.get(action)
        if code is None:
            return

        active_layers = self.shift_manager.get_active_layers()
        if active_layers:
            mapped_action = self.shift_manager.get_mapping(action)
            if mapped_action:
                code = ACTION_MAP.get(mapped_action, code)

        if action == "ABS_RZ" and self.config.rapid_fire.enabled:
            now = time.monotonic()
            delta_ms = (now - self.pipeline.last_time) * 1000.0
            value = self.pipeline.rapid_fire_engine.process_from_speed(
                255 if value else 0, value > 0, delta_ms
            )

        if action.startswith("BTN_"):
            self.controller.write_button(code, value)
        elif action in ("ABS_HAT0X", "ABS_HAT0Y"):
            self.controller.write_axis(code, value)
        elif action in ("ABS_Z", "ABS_RZ"):
            self.controller.write_trigger(code, value)
        else:
            self.controller.write_axis(code, value)

    def _run(self) -> None:
        if not self._devices:
            return

        import select

        fd_map = {d.fd: d for d in self._devices}
        self._mouse_dx = 0
        self._mouse_dy = 0
        self._last_rx = 0.0
        self._last_ry = 0.0
        self._last_mouse_time = time.monotonic()

        try:
            while self._running:
                if self._check_auto_stop():
                    break
                now = time.monotonic()

                r, w, x = select.select(fd_map.keys(), [], [], 0.001)

                for fd in r:
                    dev = fd_map[fd]
                    if not self._process_device_events(fd, dev):
                        break

                self._run_flush_remap(now)

                if not r:
                    self._run_idle_cleanup(now)
        except Exception as exc:
            print(f"[InputLoop] Fatal error in event loop: {exc}")
            import traceback
            traceback.print_exc()
        finally:
            self._run_cleanup_exit()

    def _check_auto_stop(self) -> bool:
        if not self._has_received_event:
            return False
        idle_elapsed = time.monotonic() - self._last_mouse_time
        if idle_elapsed > 60.0 and not self.config.remap_active:
            print("[InputLoop] No events for 60s — auto-stopping")
            return True
        if idle_elapsed > 120.0:
            print("[InputLoop] No events for 120s — auto-stopping")
            return True
        return False

    def _process_device_events(self, fd: int, dev: InputDevice) -> bool:
        dev_is_mouse = _is_mouse_device(dev, self._mouse_fd)
        dev_is_kbd = _is_kbd_device(dev, self._kbd_fd)

        try:
            for event in dev.read():
                if self._handle_global_event(event):
                    if event.type == e.EV_KEY and event.code == e.KEY_ESC:
                        return False
                    continue

                if self._disabled:
                    continue

                if event.type == e.EV_REL or dev_is_mouse:
                    self._handle_mouse_event(event)
                elif dev_is_kbd and event.type == e.EV_KEY:
                    self._handle_kbd_event(event)
                else:
                    self._handle_controller_event(event, dev)
        except (OSError, BlockingIOError):
            pass
        return True

    def _notify(self, message: str) -> None:
        """Show a desktop notification visible in fullscreen games."""
        print(f"[InputLoop] {message}")
        try:
            import subprocess
            subprocess.run(
                ["notify-send", "-u", "normal", "-t", "1500", "Nocrosshair", message],
                capture_output=True, timeout=2,
            )
        except Exception:
            pass

    def _handle_global_event(self, event) -> bool:
        if event.type == e.EV_KEY and event.code == e.KEY_ESC and event.value == 1:
            print("[InputLoop] ESC — stopping...")
            self._running = False
            return True

        if event.type == e.EV_KEY and event.code == e.KEY_DELETE and event.value == 1:
            self._disabled = not self._disabled
            if self._disabled:
                self._mouse_passthrough = True
                self.remap_pipeline.update_key("BTN_LEFT", 0)
                self.remap_pipeline.update_key("BTN_RIGHT", 0)
                # Clear all active keys to stop walking
                for k in list(self.remap_pipeline.active_keys):
                    self.remap_pipeline.update_key(k, 0)
                self.controller.write_trigger(e.ABS_Z, 0)
                self.controller.write_trigger(e.ABS_RZ, 0)
                self.controller.write_axis(e.ABS_X, 0)
                self.controller.write_axis(e.ABS_Y, 0)
                for d in self._devices:
                    try:
                        d.ungrab()
                    except Exception:
                        pass
                self._mouse_dx = 0
                self._mouse_dy = 0
                self._notify("Nocrosshair OFF")
            else:
                self._mouse_passthrough = False
                for d in self._devices:
                    try:
                        # Grab all devices to support Mute Native Input passthrough
                        d.grab()
                    except Exception:
                        pass
                self._notify("Nocrosshair ON")
            return True

        return False

    def _handle_mouse_event(self, event) -> None:
        if self._mouse_passthrough:
            return

        if event.type == e.EV_REL:
            if event.code == e.REL_X:
                self._mouse_dx += event.value
            elif event.code == e.REL_Y:
                self._mouse_dy += event.value
            elif event.code in (e.REL_WHEEL, getattr(e, 'REL_WHEEL_HI_RES', 11)):
                if abs(event.value) >= 8 or event.code == e.REL_WHEEL:
                    btn = e.BTN_TR if event.value > 0 else e.BTN_TL
                    self.controller.write_button(btn, 1)
                    self.controller.write_button(btn, 0)

        elif event.type == e.EV_SYN and (self._mouse_dx or self._mouse_dy):
            now_syn = time.monotonic()
            dt_ms = (now_syn - self._last_mouse_time) * 1000.0
            self._last_mouse_time = now_syn
            self._has_received_event = True

            rx, ry = self.remap_pipeline.remapper.process_mouse_move(
                self._mouse_dx, self._mouse_dy, dt_ms
            )
            self._mouse_dx = 0
            self._mouse_dy = 0

            if self.config.aim_assist.enabled or self.config.recoil.enabled:
                kbd_keys = self.remap_pipeline.get_active_keys()
                is_shooting = ("BTN_LEFT" in kbd_keys)
                is_aiming = ("BTN_RIGHT" in kbd_keys or "BTN_TL" in kbd_keys or "BTN_TR" in kbd_keys)
                is_moving = bool({"KEY_W", "KEY_S", "KEY_A", "KEY_D"} & kbd_keys)
                self.pipeline.last_time = now_syn
                rx, ry = self.pipeline.apply_to_stick(rx, ry, is_shooting, is_aiming, is_moving, dt_ms)

            self._last_rx = rx
            self._last_ry = ry
            self._aa_rx = rx
            self._aa_ry = ry
            self.controller.write_axis(e.ABS_RX, int(round(self._last_rx)))
            self.controller.write_axis(e.ABS_RY, int(round(self._last_ry)))

            if self.pipeline._pending_crouch is not None:
                btn_code = self.pipeline.crouch_spam_engine.get_button_code()
                self.controller.write_button(btn_code, 1 if self.pipeline._pending_crouch else 0)

            for btn_code, state in self.pipeline._slide_cancel_output.items():
                self.controller.write_button(btn_code, state)

        elif event.type == e.EV_KEY:
            self._handle_remap_key_event(event, "BTN_")

    def _handle_kbd_event(self, event) -> None:
        self._last_mouse_time = time.monotonic()
        self._has_received_event = True
        self._handle_remap_key_event(event, "KEY_")

    def _handle_remap_key_event(self, event, default_prefix: str) -> None:
        code_str = e.keys.get(event.code, f"{default_prefix}{event.code}")
        if not isinstance(code_str, str):
            code_str = code_str[0] if isinstance(code_str, (list, tuple)) else code_str

        # Ignora key-repeat (value=2) completamente.
        # Só processa press real (1) e release (0).
        # Repeat causava cliques duplos em F (picareta), Q (bola/granada), etc.
        if event.value == 2:
            return

        norm_value = event.value

        self.remap_pipeline.update_key(code_str, norm_value)
        plugin_manager.call_hook("on_button", code_str, bool(norm_value))

        if norm_value and code_str in self.pipeline.swap_triggers:
            self.pipeline.handle_weapon_swap(code_str)

        if norm_value:
            self.shift_manager.handle_button_press(code_str)
            if code_str == "KEY_SPACE":
                self.pipeline.slide_cancel_engine.notify_space_pressed()
            if code_str == self.config.slide_cancel.toggle_key:
                self.pipeline.slide_cancel_engine.toggle()
            print(f"[KEY] {code_str} (code={event.code})")
            if code_str in ("KEY_CAPSLOCK", "KEY_SCROLLLOCK", "KEY_PAUSE"):
                aa = self.config.aim_assist
                aa.cjitter_enabled = not aa.cjitter_enabled
                aa.cjitter_left_enabled = aa.cjitter_enabled
                print(f"[Jitter] {'ON' if aa.cjitter_enabled else 'OFF'}")
        else:
            self.shift_manager.handle_button_release(code_str)

        if code_str in TAP_ONLY_KEYS:
            if norm_value:
                action, _ = self.remap_pipeline.remapper.process_key(code_str, 1)
                if action:
                    self._write_mapped(action, 1)
                    self._write_mapped(action, 0)
        else:
            action, out_val = self.remap_pipeline.remapper.process_key(code_str, norm_value)
            if action:
                self._write_mapped(action, out_val)

        for btn_code, state in self.pipeline.macro_buttons.items():
            self.controller.write_button(btn_code, state)

    def _handle_controller_event(self, event, dev: Optional[InputDevice] = None) -> None:
        is_ds4 = _is_ds4_controller(dev)

        if event.type == e.EV_ABS:
            val = event.value
            code = event.code
            if is_ds4 and code in (e.ABS_Z, e.ABS_RZ):
                pass
            elif is_ds4 and code in (e.ABS_X, e.ABS_Y, e.ABS_RX, e.ABS_RY):
                val = int((val - 128) * 32767 / 127.5)
                val = max(-32768, min(32767, val))

            self.raw.update_axis(code, val)
            lx, ly, rx, ry, lt, rt = self.pipeline.process(self.raw)

            if self.config.remap_active:
                klx, kly = self.remap_pipeline.get_stick_values()
                if klx or kly:
                    lx, ly = klx, kly

            self.controller.write_axis(e.ABS_X, lx)
            self.controller.write_axis(e.ABS_Y, ly)
            self.controller.write_axis(e.ABS_RX, rx)
            self.controller.write_axis(e.ABS_RY, ry)
            self.controller.write_trigger(e.ABS_Z, lt)
            self.controller.write_trigger(e.ABS_RZ, rt)

            if self.pipeline._pending_crouch is not None:
                btn_code = self.pipeline.crouch_spam_engine.get_button_code()
                self.controller.write_button(btn_code, 1 if self.pipeline._pending_crouch else 0)

            for btn_code, state in self.pipeline._slide_cancel_output.items():
                self.controller.write_button(btn_code, state)

        elif event.type == e.EV_KEY:
            code = event.code
            if is_ds4 and code in DS4_BUTTON_MAP:
                code = DS4_BUTTON_MAP[code]

            self.raw.buttons[code] = event.value
            if event.value:
                code_str = e.keys.get(code, f"KEY_{code}")
                if not isinstance(code_str, str):
                    code_str = code_str[0] if isinstance(code_str, (list, tuple)) else str(code_str)
                print(f"[CTRL KEY] {code_str} (code={code})")
                if code_str in ("KEY_CAPSLOCK", "KEY_SCROLLLOCK", "KEY_PAUSE"):
                    aa = self.config.aim_assist
                    aa.cjitter_enabled = not aa.cjitter_enabled
                    aa.cjitter_left_enabled = aa.cjitter_enabled
                    print(f"[Jitter] {'ON' if aa.cjitter_enabled else 'OFF'}")
                if code == e.BTN_Y:
                    self.pipeline.handle_weapon_swap("BTN_Y")
            self.controller.write_button(code, event.value)

    def _run_flush_remap(self, now: float) -> None:
        if not self.config.remap_active:
            return
        if self._disabled:
            return

        self._jitter_phase += 0.4
        if self._jitter_phase > 2 * math.pi:
            self._jitter_phase -= 2 * math.pi

        lx, ly = self.remap_pipeline.get_stick_values()
        lx, ly = self.pipeline.ls_engine.apply(lx, ly)

        cj = self.config.aim_assist

        if cj.cjitter_left_enabled:
            jx = int(cj.cjitter_left_amp * math.sin(self._jitter_phase))
            lx = max(-32767, min(32767, lx + jx))

        if self.config.aim_assist.rush_enabled:
            kbd_keys = self.remap_pipeline.get_active_keys()
            is_aiming = "BTN_RIGHT" in kbd_keys
            rush_active = is_aiming or self.config.aim_assist.rush_always
            self.pipeline.rush_engine.set_active(rush_active)
            if rush_active:
                strafe = self.pipeline.rush_engine.get_strafe(now)
                lx = lx + strafe if lx or strafe else strafe

        delta_ms = (now - self.pipeline.last_time) * 1000.0
        lx = self.pipeline.strafe_shot_engine.apply(
            lx,
            enabled=self.config.aim_assist.strafe_shot_enabled,
            amplitude=self.config.aim_assist.strafe_shot_amplitude,
            frequency=self.config.aim_assist.strafe_shot_frequency,
            delta_ms=delta_ms,
        )

        lx = max(-32767, min(32767, lx))
        self.controller.write_axis(e.ABS_X, lx)
        self.controller.write_axis(e.ABS_Y, ly)

        lt, rt = self.remap_pipeline.get_trigger_values()
        if lt:
            self.controller.write_trigger(e.ABS_Z, lt)
        if rt:
            self.controller.write_trigger(e.ABS_RZ, rt)

        hx, hy = self.remap_pipeline.get_hat_values()
        if hx or hy:
            self.controller.write_axis(e.ABS_HAT0X, hx)
            self.controller.write_axis(e.ABS_HAT0Y, hy)

        if self.pipeline._pending_crouch is not None:
            btn_code = self.pipeline.crouch_spam_engine.get_button_code()
            self.controller.write_button(btn_code, 1 if self.pipeline._pending_crouch else 0)

        for btn_code, state in self.pipeline._slide_cancel_output.items():
            self.controller.write_button(btn_code, state)

    def _run_idle_cleanup(self, now: float) -> None:
        if self._disabled:
            time.sleep(0.0005)
            return
        idle_ms = (now - self._last_mouse_time) * 1000.0
        if idle_ms > 50 and (self._last_rx != 0.0 or self._last_ry != 0.0):
            self._last_rx = 0.0
            self._last_ry = 0.0
            self._aa_rx = 0.0
            self._aa_ry = 0.0
            if not self.config.aim_assist.cjitter_enabled:
                self.controller.write_axis(e.ABS_RX, 0)
                self.controller.write_axis(e.ABS_RY, 0)
        time.sleep(0.0005)

    def _run_cleanup_exit(self) -> None:
        self.controller.reset()
        self.remap_pipeline.reset()
        self.controller.write_axis(e.ABS_X, 0)
        self.controller.write_axis(e.ABS_Y, 0)
        for dev in self._devices:
            try:
                dev.ungrab()
                dev.close()
            except Exception:
                pass
        self._devices = []
        print("[InputLoop] Loop exited — devices released")

    def update_config(self, config: AppConfig) -> None:
        with self._lock:
            self.config = config
            self.pipeline.update_config(config)
            self.remap_pipeline = RemapPipeline(config.kbd_bindings or {}, config.mouse_sens,
                                                 sens_x=config.sens_x, sens_y=config.sens_y,
                                                 curve=config.mouse_curve, smooth=config.mouse_smooth,
                                                 min_output=config.mouse_min_output,
                                                 square_stick=config.square_stick)

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_disabled(self) -> bool:
        return self._disabled


def find_controller_devices() -> List[dict]:
    devices = []
    input_dir = "/dev/input"

    if not os.path.isdir(input_dir):
        return devices

    for entry in sorted(os.listdir(input_dir)):
        if not entry.startswith("event"):
            continue

        path = os.path.join(input_dir, entry)
        try:
            dev = InputDevice(path)
            caps = dev.capabilities()
            info = {
                "path": path,
                "name": dev.name,
                "phys": dev.phys,
                "has_sticks": False,
                "has_triggers": False,
                "has_buttons": False,
            }

            abs_caps = caps.get(e.EV_ABS, {})
            key_caps = caps.get(e.EV_KEY, [])

            info["has_sticks"] = e.ABS_X in abs_caps and e.ABS_RX in abs_caps
            info["has_triggers"] = e.ABS_Z in abs_caps and e.ABS_RZ in abs_caps
            info["has_buttons"] = e.BTN_A in key_caps

            if info["has_sticks"] or info["has_buttons"]:
                devices.append(info)

            dev.close()
        except (PermissionError, OSError):
            continue

    return devices
