#!/usr/bin/env python3

import os
import time
import math
import threading
from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass, field, replace
from evdev import InputDevice, UInput, ecodes as e, categorize
from evdev.events import InputEvent

from nocrosshair.core.config import AppConfig
from nocrosshair.core.controller import VirtualController, VirtualKeyboard
from nocrosshair.features.physics import StickPhysicsEngine, TriggerPhysicsEngine
from nocrosshair.features.aim_assist import AimAssistEngine, AimAssistPipeline, ZeroDelayEngine, StrafeShotEngine, LeftStickFreqEngine, HeadSnapEngine
from nocrosshair.features.aim_optimizer import AimOptimizerPipeline
from nocrosshair.features.rapid_fire import RapidFireEngine
from nocrosshair.features.bloom_reducer import BloomReducerEngine
from nocrosshair.features.crouch_spam import CrouchSpamEngine
from nocrosshair.features.crouch_aim import CrouchAimEngine
from nocrosshair.features.slide_cancel import SlideCancelEngine
from nocrosshair.features.movement_tech import (
    DodgeShotEngine, SlideCancelEngine2, BunnyHopEngine,
)
from nocrosshair.core.config import AppConfig, MovementTechConfig
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
from nocrosshair.features.aim_layers import AimLayerPipeline, LayerContext, LayerID

# Debug de runtime: NOCROSSHAIR_DEBUG=1 liga logs de eventos do mouse/teclado
# e de escrita de triggers (ABS_Z=L2, ABS_RZ=R2) para diagnosticar
# "movimento ativando L2" sem precisar adivinhar.
_DEBUG = os.environ.get("NOCROSSHAIR_DEBUG") == "1"


def _dbg(*args: Any) -> None:
    if _DEBUG:
        print("[DBG]", *args)


# Marcadores de arma de cadência alta (auto) que se beneficiam de RAPID FIRE.
# Armas de precisão (AR/Shotgun/Sniper) usam BLOOM REDUCER (tap-fire) em vez
# disso. Como rapid fire e bloom reducem o gatilho, só um roda por vez — a
# seleção é feita pela arma ativa no loadout.
_RAPID_FIRE_WEAPONS = ("SMG", "PISTOL", "AUTO", "VECTOR", "MP5", "UZI", "P90", "MACHINE PISTOL")


def _prefer_rapid_fire(weapon: str) -> bool:
    upper = weapon.upper()
    return any(k in upper for k in _RAPID_FIRE_WEAPONS)

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
        self.aa_optimizer_pipeline = AimOptimizerPipeline()
        self.zero_delay_engine = ZeroDelayEngine()
        self.strafe_shot_engine = StrafeShotEngine()
        self.left_stick_freq_engine = LeftStickFreqEngine()
        self.head_snap_engine = HeadSnapEngine()
        from nocrosshair.features.zen_style import AimSpamEngine, RushEngine
        self.aim_spam_engine = AimSpamEngine()
        self.rush_engine = RushEngine(
            config.aim_assist.rush_pulse_ms,
            config.aim_assist.rush_cooldown_ms,
            config.aim_assist.rush_deadzone,
        )

        # ── Motores Zen-like (Sprint 1) ──
        self.rapid_fire_engine = RapidFireEngine(config.rapid_fire)
        self.rapid_fire_engine.set_active(config.rapid_fire.enabled)
        self.bloom_reducer_engine = BloomReducerEngine(config.bloom_reducer)
        self.bloom_reducer_engine.set_active(config.bloom_reducer.enabled)
        self.crouch_spam_engine = CrouchSpamEngine(config.crouch_spam)
        self.crouch_aim_engine = CrouchAimEngine(config.crouch_aim)
        self.crouch_aim_engine.set_active(config.crouch_aim.enabled)
        self.slide_cancel_engine = SlideCancelEngine(config.slide_cancel)
        self.anti_recoil_engine = AntiRecoilEngine(config.recoil)

        # ── Movimentação competitiva (Dodge Shot / Slide Cancel / Bunny Hop) ──
        mt = config.movement_tech or MovementTechConfig()
        self.dodge_shot_engine = DodgeShotEngine(
            hold_ms=mt.dodge_hold_ms,
            release_ms=mt.dodge_release_ms,
            crouch_button_code=mt.crouch_button_code,
        )
        self.dodge_shot_engine.set_active(mt.dodge_shot_enabled)
        self.slide_cancel2_engine = SlideCancelEngine2(
            crouch_button_code=mt.crouch_button_code,
            jump_button_code=mt.jump_button_code,
            tap_ms=mt.slide_tap_ms,
            gap_ms=mt.slide_gap_ms,
        )
        self.slide_cancel2_engine.set_active(mt.slide_cancel_enabled)
        self.bunny_hop_engine = BunnyHopEngine(
            jump_button_code=mt.jump_button_code,
            hold_ms=mt.bunny_hold_ms,
            gap_ms=mt.bunny_gap_ms,
        )
        self.bunny_hop_engine.set_active(mt.bunny_hop_enabled)
        self._movement_output: Dict[int, int] = {}

        # ── Aim Layers (arquitetura em camadas) ──
        self.aim_layers = AimLayerPipeline()
        # Layer 1 (Slowdown) ativa por padrão, resto desligado
        self.aim_layers.slowdown.enabled = True
        self.aim_layers.aim_lock_silent.enabled = False
        self.aim_layers.camera_hit.enabled = False
        self.aim_layers.track_snap.enabled = False
        self.aim_layers.sticky.enabled = False

        # ── Right stick smoothing (anti-jitter para micro-movements) ──
        self._smooth_rs_rx: float = 0.0
        self._smooth_rs_ry: float = 0.0

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
        # Slots mapeiam para presets de RECOIL_PRESETS (configurável na UI de Recoil)
        self.weapon_slots: List[str] = list(config.recoil_runtime.loadout_slots)
        while len(self.weapon_slots) < 6:
            self.weapon_slots.append("Pickaxe")
        self.swap_triggers = {"KEY_F", "KEY_1", "KEY_2", "KEY_3", "KEY_4", "KEY_5", "BTN_Y", "BTN_MODE"}

        self.prev_rx: float = 0.0
        self.prev_ry: float = 0.0
        self.recoil_tick: int = 0
        self.recoil_active: bool = False
        self._pending_crouch: Optional[bool] = None
        self._slide_cancel_output: Dict[int, int] = {}
        self._crouch_aim_output: Dict[int, int] = {}
        self.last_time: float = time.monotonic()
        self.raw = RawInputState()

    def process(self, raw: RawInputState) -> Tuple[int, int, int, int, int, int]:
        self.raw = raw
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
        # Desligado quando Rapid Fire / Bloom Reducer assumem o gatilho:
        # eles fazem o próprio ciclo de press e o zero-delay briga com eles
        # (cada re-press re-dispara o hold de 40ms -> stutter no gatilho).
        aa_cfg = self.config.aim_assist
        trigger_owned = self.config.rapid_fire.enabled or self.config.bloom_reducer.enabled
        lt, rt = self.zero_delay_engine.process(
            lt, rt,
            enabled=aa_cfg.zero_delay and not trigger_owned,
            hold_ms=aa_cfg.zero_delay_ms,
            now=now,
        )

        is_shooting = rt > 10
        is_moving = abs(raw.lx) > 3000 or abs(raw.ly) > 3000
        is_aiming = lt > 10

        # ── Aim Spam (estilo Zen): micro-cycle de ADS para refrescar o AA nativo ──
        lt = self.aim_spam_engine.process_trigger(
            lt,
            is_shooting=is_shooting,
            enabled=aa_cfg.aim_spam_enabled,
            interval_ms=aa_cfg.aim_spam_interval_ms,
            hold_ms=aa_cfg.aim_spam_hold_ms,
            now=now,
        )
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
        if self.config.aim_assist.use_optimized_pipeline:
            rx, ry = self.aa_optimizer_pipeline.process(
                rx, ry,
                is_shooting=is_shooting,
                is_aiming=is_aiming,
                is_moving=is_moving,
                delta_ms=delta_ms,
                config=self.config.aim_assist,
            )
        else:
            # Build mode detection: desativa aim assist enquanto o jogador está construindo
            # Tecla de construir padrão do Fortnite = Q
            kbd_keys = self.remap_pipeline.get_active_keys()
            is_building = "KEY_Q" in kbd_keys and self.config.aim_assist.build_mode_enabled
            if is_building:
                # Skip aim assist entirely while building
                pass
            else:
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

        # ── Rapid Fire / Bloom Reducer: auto-seleção por arma ativa ──
        # Só um roda por vez (conflito no gatilho). Armas automáticas (SMG/
        # pistola) usam rapid fire; o resto (AR/shotgun/sniper) usa bloom
        # reducer — o tap-fire reseta o bloom do jogo na pausa.
        weapon = self.weapon_slots[self.active_weapon_index]
        if _prefer_rapid_fire(weapon) and self.config.rapid_fire.enabled:
            rt = self.rapid_fire_engine.process_from_speed(
                int(rt), is_shooting, delta_ms
            )
        elif self.config.bloom_reducer.enabled:
            rt = self.bloom_reducer_engine.process(
                int(rt), is_shooting
            )

        # ── Crouch Spam: armazena ação pendente para emissão de botão ──
        self._update_zen_features(is_shooting, delta_ms, is_moving, is_aiming)

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

        self._update_zen_features(is_shooting, delta_ms, is_moving, is_aiming)

        # Aplica a assistência de mira unificada para teclado/mouse remapeado
        aa_cfg = kbm_sanitize_config(self.config.aim_assist)
        rx, ry = self.aa_pipeline.apply(rx, ry, is_shooting, is_aiming, is_moving, delta_ms,
                                         aa_cfg, self.prev_rx, self.prev_ry)

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

    def _update_zen_features(self, is_shooting: bool, delta_ms: float,
                             is_moving: bool = False, is_aiming: bool = False) -> None:
        """Atualiza motores de Crouch Spam e outros estados temporais."""
        if self.config.crouch_spam.enabled:
            self._pending_crouch = self.crouch_spam_engine.process(is_shooting, delta_ms)
        else:
            self._pending_crouch = None
        # Crouch Aim (estilo Zen): agacha enquanto mira; garante release ao desativar
        ca_state = self.crouch_aim_engine.process(is_aiming)
        if ca_state is None:
            self._crouch_aim_output = {}
        else:
            self._crouch_aim_output = {self.crouch_aim_engine.get_button_code(): 1 if ca_state else 0}
        # Slide Cancel processa seu próprio estado
        if self.slide_cancel_engine.is_active:
            self._slide_cancel_output = self.slide_cancel_engine.process(time.monotonic())

        # ── Movimentação competitiva ──
        now = time.monotonic()
        mv = {}
        if self.dodge_shot_engine.is_active:
            mv.update(self.dodge_shot_engine.process(is_shooting, now))
        if self.bunny_hop_engine.is_active:
            mv.update(self.bunny_hop_engine.process(is_moving, now))
        if self.slide_cancel2_engine.is_active:
            mv.update(self.slide_cancel2_engine.process(now))
        self._movement_output = mv

    def update_config(self, config: AppConfig) -> None:
        self.config = config
        self.ls_engine = StickPhysicsEngine(config.ls_physics)
        self.rs_engine = StickPhysicsEngine(config.rs_physics)
        self.lt_engine = TriggerPhysicsEngine(config.lt_physics)
        self.rt_engine = TriggerPhysicsEngine(config.rt_physics)
        self.aa_pipeline.update_config(config.aim_assist)
        # Reseta o pipeline otimizado quando a config muda
        self.aa_optimizer_pipeline.reset()
        # Atualiza motores Zen-style
        self.rapid_fire_engine.update_config(config.rapid_fire)
        self.rapid_fire_engine.set_active(config.rapid_fire.enabled)
        self.bloom_reducer_engine.update_config(config.bloom_reducer)
        self.bloom_reducer_engine.set_active(config.bloom_reducer.enabled)
        self.crouch_spam_engine.update_config(config.crouch_spam)
        self.crouch_aim_engine.update_config(config.crouch_aim)
        self.crouch_aim_engine.set_active(config.crouch_aim.enabled)
        self.slide_cancel_engine.update_config(config.slide_cancel)
        self.anti_recoil_engine.update_config(config.recoil)
        self.anti_recoil_engine.update_runtime(config.recoil_runtime)
        self.anti_recoil_engine.set_weapon(config.recoil_runtime.active_preset)
        self.weapon_slots = list(config.recoil_runtime.loadout_slots)
        while len(self.weapon_slots) < 6:
            self.weapon_slots.append("Pickaxe")
        if not config.aim_assist.zero_delay:
            self.zero_delay_engine.reset()
        # Sincroniza motores de movimentação competitiva
        mt = config.movement_tech
        if mt is not None:
            self.dodge_shot_engine = DodgeShotEngine(
                hold_ms=mt.dodge_hold_ms,
                release_ms=mt.dodge_release_ms,
                crouch_button_code=mt.crouch_button_code,
            )
            self.dodge_shot_engine.set_active(mt.dodge_shot_enabled)
            self.slide_cancel2_engine = SlideCancelEngine2(
                crouch_button_code=mt.crouch_button_code,
                jump_button_code=mt.jump_button_code,
                tap_ms=mt.slide_tap_ms,
                gap_ms=mt.slide_gap_ms,
            )
            self.slide_cancel2_engine.set_active(mt.slide_cancel_enabled)
            self.bunny_hop_engine = BunnyHopEngine(
                jump_button_code=mt.jump_button_code,
                hold_ms=mt.bunny_hold_ms,
                gap_ms=mt.bunny_gap_ms,
            )
            self.bunny_hop_engine.set_active(mt.bunny_hop_enabled)

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

        # Auto Detect (estilo Zen): troca o perfil de recoil e a curva de
        # resposta para a arma do slot selecionado.
        self.anti_recoil_engine.set_weapon(current_weapon)
        if weapon_curves_manager.get_weapon_names():
            curve_weapon = current_weapon if current_weapon in weapon_curves_manager.get_weapon_names() else "Default"
            weapon_curves_manager.set_current_weapon(curve_weapon)

        if self.overlay:
            from nocrosshair.core.config import RECOIL_PRESETS
            color = RECOIL_PRESETS.get(current_weapon, {}).get("color", "#00ff88")
            self.overlay.update_color(color)


TAP_ONLY_KEYS = {"KEY_Q", "KEY_F"}

# Duração mínima do press de um tap (Q/F) para que o jogo/xCloud detecte.
# Press+release no mesmo tick = pulso de ~0ms, que o jogo nunca vê.
TAP_HOLD_MS = 50


# Tradução de um DS4/DualSense real (físico) para o dispositivo virtual.
# O kernel (hid-playstation) reporta os botões do DS4 na convenção posicional:
# Cross=BTN_SOUTH 0x130, Circle=BTN_EAST 0x131, Triangle=BTN_NORTH 0x133,
# Square=BTN_WEST 0x134, L1=BTN_TL 0x136, R1=BTN_TR 0x137, L2=BTN_TL2 0x138,
# R2=BTN_TR2 0x139, Create=BTN_SELECT 0x13a, Options=BTN_START 0x13b,
# PS=BTN_MODE 0x13c, L3=BTN_THUMBL 0x13d, R3=BTN_THUMBR 0x13e.
# O virtual é Xbox 360: o jogo lê BTN_X(307)=Quadrado e BTN_Y(308)=Triângulo.
# Então Triangle físico (0x133=307) deve virar BTN_Y (308) e Square físico
# (0x134=308) deve virar BTN_X (307) — caso contrário Quadrado/Triângulo
# invertem no jogo. L2/R2 analógicos chegam como ABS_Z/ABS_RZ (EV_ABS), não
# passam por esta tabela. O clique do touchpad (BTN_LEFT 0x110) vem num device
# evdev separado ("Touchpad"), também fora desta tabela.
DS4_BUTTON_MAP = {
    0x130: e.BTN_A,       # Cross (baixo) -> A do Xbox
    0x131: e.BTN_B,       # Circle (direita) -> B do Xbox
    0x133: e.BTN_Y,       # Triangle (cima) -> Y do Xbox (Triângulo)
    0x134: e.BTN_X,       # Square (esquerda) -> X do Xbox (Quadrado)
    0x136: e.BTN_TL,      # L1
    0x137: e.BTN_TR,      # R1
    0x138: e.BTN_TL2,     # L2 (digital)
    0x139: e.BTN_TR2,     # R2 (digital)
    0x13a: e.BTN_SELECT,  # Create / Share
    0x13b: e.BTN_START,   # Options
    0x13c: e.BTN_MODE,    # PS Home
    0x13d: e.BTN_THUMBL,  # L3
    0x13e: e.BTN_THUMBR,  # R3
}


def _detect_sony_kind(dev: Optional[InputDevice]) -> Optional[str]:
    """Identifica o controle Sony físico: 'ds4' ou 'dualsense' (ou None).

    Precisa distinguir porque os dois têm layout de eixos DIFERENTE:
    - DS4 (hid-sony): stick direito em ABS_Z/ABS_RZ, gatilhos L2/R2 em
      ABS_RX/ABS_RY.
    - DualSense (hid-playstation): stick direito em ABS_RX/ABS_RY, gatilhos
      em ABS_Z/ABS_RZ (igual Xbox).
    """
    if not dev:
        return None
    try:
        vid = getattr(dev.info, 'vendor', 0)
        pid = getattr(dev.info, 'product', 0)
    except Exception:
        vid = pid = 0
    name = (dev.name or "").lower()
    sony_name = any(k in name for k in ("sony", "dualshock", "dualsense", "playstation", "wireless controller"))
    is_sony = vid == 0x054C or sony_name
    if not is_sony:
        return None
    # DualSense (0x0CE6) / DualSense Edge (0x0DF2) — ou nome "dualsense".
    if pid in (0x0CE6, 0x0DF2) or "dualsense" in name:
        return "dualsense"
    return "ds4"


def _detect_8bitdo_kind(dev: Optional[InputDevice]) -> Optional[str]:
    """Detecta controles 8BitDo (VID 0x2DC8) e retorna o tipo de saída.

    O 8BitDo Ultimate 2C via dongle 2.4GHz se apresenta como XInput.
    Para melhor compatibilidade com xCloud/Fortnite, pode ser mapeado
    como DS5 (DualSense) na saída virtual.
    """
    if not dev:
        return None
    try:
        vid = getattr(dev.info, 'vendor', 0)
        pid = getattr(dev.info, 'product', 0)
    except Exception:
        vid = pid = 0
    name = (dev.name or "").lower()
    # 8BitDo vendor ID: 0x2DC8
    is_8bitdo = vid == 0x2DC8 or "8bitdo" in name
    if not is_8bitdo:
        return None
    return "8bitdo"


# Layouts de eixos dos controles Sony FÍSICOS → código canônico do pipeline
# (estilo Xbox): ABS_X/Y = stick esquerdo, ABS_RX/RY = stick direito,
# ABS_Z/RZ = gatilhos L2/R2. kind: "ds4" | "dualsense".
_SONY_AXIS_MAPS: Dict[str, Dict[int, Tuple[str, str]]] = {
    "ds4": {
        e.ABS_X: ("stick", "lx"),
        e.ABS_Y: ("stick", "ly"),
        e.ABS_Z: ("stick", "rx"),
        e.ABS_RZ: ("stick", "ry"),
        e.ABS_RX: ("trigger", "lt"),
        e.ABS_RY: ("trigger", "rt"),
    },
    "dualsense": {
        e.ABS_X: ("stick", "lx"),
        e.ABS_Y: ("stick", "ly"),
        e.ABS_RX: ("stick", "rx"),
        e.ABS_RY: ("stick", "ry"),
        e.ABS_Z: ("trigger", "lt"),
        e.ABS_RZ: ("trigger", "rt"),
    },
}

_CANONICAL_AXIS: Dict[str, int] = {
    "lx": e.ABS_X, "ly": e.ABS_Y,
    "rx": e.ABS_RX, "ry": e.ABS_RY,
    "lt": e.ABS_Z, "rt": e.ABS_RZ,
}


def map_sony_axis(kind: str, code: int, value: int) -> Optional[Tuple[int, int]]:
    """Converte um evento de eixo de um controle Sony físico para o código
    canônico (estilo Xbox) + valor normalizado.

    - Stick (0..255, centro 128) → -32768..32767.
    - Gatilho (0..255) → mantido (0..255).
    Retorna (canonical_code, value), ou None se o eixo não é mapeado (dpad).
    """
    entry = _SONY_AXIS_MAPS.get(kind, {}).get(code)
    if entry is None:
        return None
    axis_kind, target = entry
    if axis_kind == "stick":
        value = int((value - 128) * 32767 / 127.5)
        value = max(-32768, min(32767, value))
    else:
        value = max(0, min(255, value))
    return _CANONICAL_AXIS[target], value


def kbm_sanitize_config(cfg: AimAssistConfig) -> AimAssistConfig:
    """Config reduzido para o caminho teclado/mouse.

    O pipeline inteiro é pensado em espaço de stick (0-32767, correções com
    magnitudes de centenas/milhares de unidades). Aplicado cru em cima de
    deltas de mouse, as correções viram "pulos de pixel" (fire boost x1.35,
    snap 700, pulse, headlock, aimlock proxy, ruído humano...).

    Para KBM ficam apenas as mecânicas que não pulam:
      - slowdown de zona (fração do input = grude sem jump)
      - magnetismo FN suave, com cap reduzido por ``kbm_scale``
      - recoil/anti-shake (rodam antes/fora do pipeline)
    """
    if not cfg.kbm_mode:
        return cfg
    return replace(
        cfg,
        # Órbita rotacional: técnica de CONTROLE pra re-disparar o AA nativo
        # do jogo. No mouse não existe AA nativo — a órbita vira balanço
        # lateral sozinho (a mira "mexe pros lados" sem o usuário mover o
        # mouse). Desligada no caminho KBM.
        rotational=False,
        # Neural/micro-correções: em espaço de stick são micro-pulls; em
        # deltas de mouse viram pulos de pixel aleatórios.
        neural_enabled=False,
        neural_micro_enabled=False,
        # Adhesion buffer segura a última direção por hold_ms — no mouse
        # isso é "mira anda sozinha" depois que o usuário parou.
        adhesion_buffer_enabled=False,
        fire_boost_mult=1.0,
        fire_boost_ms=0.0,
        pulse_level=0,
        snap_strength=0,
        snap_duration=0,
        magnetic_snap=False,
        sticky_enabled=False,
        lock_enabled=False,
        rush_enabled=False,
        head_assist_enabled=False,
        auto_rotation_enabled=False,
        adaptive_strength=False,
        enhanced_enabled=False,
        aimlock_enabled=False,
        tracking_strength=0,
        fn_humanize=False,
        fn_rotation_cap=max(250, int(cfg.fn_rotation_cap * cfg.kbm_scale)),
        fn_input_gate=max(200, int(cfg.fn_input_gate * cfg.kbm_scale)),
        rotational_mag_gate=200,
        rotational_radius_mult=1.5,
        tweak_zone_enabled=True,
    )


def _is_mouse_device(dev: Optional[InputDevice], mouse_fd: Optional[int] = None) -> bool:
    if not dev:
        return False
    if mouse_fd is not None and dev.fd == mouse_fd:
        return True
    try:
        caps = dev.capabilities()
        if e.EV_REL in caps:
            rel_caps = caps[e.EV_REL]
            if e.REL_X in rel_caps and e.REL_Y in rel_caps:
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

        # ── Silent QT output smoothing (anti pixel-jump) ──
        self._qt_out_rx: float = 0.0
        self._qt_out_ry: float = 0.0

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
        # Último instante com input real (controle, teclado ou mouse) — usado
        # pelo idle cleanup e auto-stop. O tick de AA (~1ms) sustenta o output
        # mesmo sem evento físico, então não conta como "input".
        self._last_input_time: float = time.monotonic()
        # True quando um controle físico foi encontrado (caminho de stick).
        # No modo KBM o tick de AA é desligado (o mouse é event-driven).
        self._controller_mode: bool = False

        # Taps (Q/F) agendados: action -> timestamp de release
        self._pending_tap_releases: Dict[str, float] = {}

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
            self._controller_mode = path is not None
            self._last_input_time = time.monotonic()

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

        if action in ("ABS_Z", "ABS_RZ"):
            _dbg(f"write trigger {action} = {value} (L2={action=='ABS_Z'})")

        active_layers = self.shift_manager.get_active_layers()
        if active_layers:
            mapped_action = self.shift_manager.get_mapping(action)
            if mapped_action:
                code = ACTION_MAP.get(mapped_action, code)

        # Nota: rapid fire / bloom reducer NÃO são aplicados aqui (evento de
        # press). O ciclo precisa rodar a cada loop — quem aplica é
        # _run_flush_remap, senão o hold do botão não cicla o gatilho.

        if action.startswith("BTN_"):
            self.controller.write_button(code, value)
        elif action in ("ABS_HAT0X", "ABS_HAT0Y"):
            self.controller.write_axis(code, value)
        elif action in ("ABS_Z", "ABS_RZ"):
            self.controller.write_trigger(code, value)
        else:
            self.controller.write_axis(code, value)

    def _write_keyboard_passthrough(self, event, action: Optional[str]) -> None:
        if not hasattr(self, "virtual_keyboard") or self.virtual_keyboard is None:
            return
        if event.type != e.EV_KEY:
            return

        # Chave remapeada é consumida (não passa pro teclado virtual) SÓ
        # quando o botão mapeado conflita com a tecla. Ex: F → BTN_Y
        # (picareta/troca) fazia o jogo trocar duas vezes (tecla F + BTN_Y).
        # As demais teclas remapeadas passam JUNTO pro teclado virtual: o jogo
        # é KBM e sem isso 1-5 (slots), M (mapa), B (emoji), Tab (inventário)
        # e Space/Shift/C/R/E/Q param de funcionar como teclas.
        if action == "BTN_Y":
            return

        # Only passthrough genuine keyboard keycodes, not mouse button or controller button codes.
        if 0 < event.code < e.BTN_MISC:
            self.virtual_keyboard.write_key(event.code, event.value)

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

                handled = False
                for fd in r:
                    dev = fd_map[fd]
                    handled = True
                    if not self._process_device_events(fd, dev):
                        break

                # Sem evento físico neste ciclo: roda o tick de AA. O Cronus
                # Zen empurra o stick continuamente (~1000Hz) mesmo com o
                # jogador parado — é esse micro-input que re-dispara o AA
                # rotacional nativo do Fortnite. O loop dirigido por evento
                # nunca escrevia com o stick em repouso, e o "grude" morria.
                if not handled:
                    self._run_aa_tick(now)

                self._run_flush_remap(now)

                self._flush_tap_releases(now)

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
        idle_elapsed = time.monotonic() - self._last_input_time
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

                if dev_is_mouse and event.type in (e.EV_REL, e.EV_KEY, e.EV_SYN):
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
            self._last_input_time = now_syn
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

                # Right stick smoothing (anti-jitter para micro-movements)
                rs_smooth = self.config.aim_assist.rs_smoothing
                if rs_smooth > 0:
                    w = min(0.85, max(0.10, 1.0 - (rs_smooth * 0.9)))
                    self._smooth_rs_rx = self._smooth_rs_rx * (1.0 - w) + rx * w
                    self._smooth_rs_ry = self._smooth_rs_ry * (1.0 - w) + ry * w
                    if abs(self._smooth_rs_rx) < 20:
                        self._smooth_rs_rx = 0.0
                    if abs(self._smooth_rs_ry) < 20:
                        self._smooth_rs_ry = 0.0
                    self._last_rx = self._smooth_rs_rx
                    self._last_ry = self._smooth_rs_ry

                # ── Head Snap Engine (KBM path) ──
                if self.config.aim_assist.head_snap_enabled:
                    kb_keys = self.remap_pipeline.get_active_keys()
                    is_aiming = "BTN_RIGHT" in kb_keys
                    is_shooting = "BTN_LEFT" in kb_keys
                    is_moving = self.remap_pipeline.is_moving()
                    head_rx, head_ry = self.pipeline.head_snap_engine.apply(
                        int(round(self._last_rx)), int(round(self._last_ry)),
                        is_aiming=is_aiming,
                        is_shooting=is_shooting,
                        is_moving=is_moving,
                        now=now,
                        delta_ms=(now - self.pipeline.last_time) * 1000.0,
                        enabled=self.config.aim_assist.head_snap_enabled,
                        strength=self.config.aim_assist.head_snap_strength,
                        height=self.config.aim_assist.head_snap_height,
                        duration=self.config.aim_assist.head_snap_duration,
                        cooldown=self.config.aim_assist.head_snap_cooldown,
                        smooth=self.config.aim_assist.head_snap_smooth,
                        mode=self.config.aim_assist.head_snap_mode,
                        ads_only=self.config.aim_assist.head_snap_ads_only,
                    )
                    self._last_rx = float(head_rx)
                    self._last_ry = float(head_ry)

                self.controller.write_axis(e.ABS_RX, int(round(self._last_rx)))
                self.controller.write_axis(e.ABS_RY, int(round(self._last_ry)))
            else:
                self._last_rx = 0.0
                self._last_ry = 0.0
                self._aa_rx = 0.0
                self._aa_ry = 0.0
                self.controller.write_axis(e.ABS_RX, 0)
                self.controller.write_axis(e.ABS_RY, 0)

            if self.pipeline._pending_crouch is not None:
                btn_code = self.pipeline.crouch_spam_engine.get_button_code()
                self.controller.write_button(btn_code, 1 if self.pipeline._pending_crouch else 0)

            for btn_code, state in self.pipeline._slide_cancel_output.items():
                self.controller.write_button(btn_code, state)

        elif event.type == e.EV_KEY:
            _dbg(f"mouse EV_KEY code={event.code} ({e.keys.get(event.code, '?')}) value={event.value}")
            self._handle_remap_key_event(event, "BTN_")

    def _handle_kbd_event(self, event) -> None:
        self._last_mouse_time = time.monotonic()
        self._last_input_time = time.monotonic()
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

        if macro_manager.is_trigger_capturing() and norm_value:
            if macro_manager.set_capture_trigger(code_str):
                self.status_message = f"Trigger capturado: {code_str}"
            return

        self.remap_pipeline.update_key(code_str, norm_value)
        plugin_manager.call_hook("on_button", code_str, bool(norm_value))

        if norm_value and code_str in self.pipeline.swap_triggers:
            self.pipeline.handle_weapon_swap(code_str)

        if norm_value:
            self.shift_manager.handle_button_press(code_str)
            if code_str == "KEY_SPACE":
                self.pipeline.slide_cancel_engine.notify_space_pressed()
                self.pipeline.slide_cancel2_engine.notify_jump()
            if code_str == self.config.slide_cancel.toggle_key:
                self.pipeline.slide_cancel_engine.toggle()
            if code_str == self.config.rapid_fire.toggle_key:
                self.config.rapid_fire.enabled = not self.config.rapid_fire.enabled
                self.pipeline.rapid_fire_engine.set_active(self.config.rapid_fire.enabled)
                self.status_message = f"Rapid Fire {'ON' if self.config.rapid_fire.enabled else 'OFF'}"
                print(f"[RapidFire] {'ON' if self.config.rapid_fire.enabled else 'OFF'}")
            if code_str == self.config.bloom_reducer.toggle_key:
                self.config.bloom_reducer.enabled = not self.config.bloom_reducer.enabled
                self.pipeline.bloom_reducer_engine.set_active(self.config.bloom_reducer.enabled)
                self.status_message = f"Bloom Reducer {'ON' if self.config.bloom_reducer.enabled else 'OFF'}"
                print(f"[BloomReducer] {'ON' if self.config.bloom_reducer.enabled else 'OFF'}")
            if code_str == self.config.crouch_spam.toggle_key:
                self.config.crouch_spam.enabled = not self.config.crouch_spam.enabled
                self.pipeline.crouch_spam_engine.set_active(self.config.crouch_spam.enabled)
                self.status_message = f"Crouch Spam {'ON' if self.config.crouch_spam.enabled else 'OFF'}"
                print(f"[CrouchSpam] {'ON' if self.config.crouch_spam.enabled else 'OFF'}")
            print(f"[KEY] {code_str} (code={event.code})")
            if code_str in ("KEY_CAPSLOCK", "KEY_SCROLLLOCK", "KEY_PAUSE"):
                aa = self.config.aim_assist
                aa.cjitter_enabled = not aa.cjitter_enabled
                aa.cjitter_left_enabled = aa.cjitter_enabled
                print(f"[Jitter] {'ON' if aa.cjitter_enabled else 'OFF'}")
            if code_str == "KEY_F7":
                # Quick Tune Silent Aim (portado do v2)
                self.pipeline.aa_pipeline.silent_qt.quick_tune_aim.start()
                self.status_message = "Quick Tune AIM: subindo... F5 = parou no tremor"
                print("[SilentAimQT] F7 -> Quick Tune AIM (F5 para confirmar tremor)")
            if code_str == "KEY_F8":
                # Quick Tune Silent Hit (portado do v2)
                self.pipeline.aa_pipeline.silent_qt.quick_tune_hit.start()
                self.status_message = "Quick Tune HIT: subindo... F5 = parou no tremor"
                print("[SilentAimQT] F8 -> Quick Tune HIT (F5 para confirmar tremor)")
            if code_str == "KEY_F5":
                # Confirma tremor durante Quick Tune (Cronus Zen method)
                qt = self.pipeline.aa_pipeline.silent_qt
                tuned = False
                if qt.quick_tune_aim.is_tuning():
                    val = qt.quick_tune_aim.confirm_shake()
                    self.status_message = f"Silent Aim QT: valor final {val}"
                    print(f"[SilentAimQT] AIM confirmado: {val}")
                    tuned = True
                if qt.quick_tune_hit.is_tuning():
                    val = qt.quick_tune_hit.confirm_shake()
                    self.status_message = f"Silent Hit QT: valor final {val}"
                    print(f"[SilentAimQT] HIT confirmado: {val}")
                    tuned = True
                if not tuned:
                    self.status_message = "Quick Tune não ativo (F7=F8 para iniciar)"
                    print("[SilentAimQT] F5 sem Quick Tune ativo")
            if code_str == "KEY_F6":
                # Toggle Silent Aim QT on/off
                aa = self.config.aim_assist
                aa.silent_aim_enabled = not aa.silent_aim_enabled
                aa.silent_hit_enabled = not aa.silent_hit_enabled
                self.pipeline.update_config(self.config)
                self.status_message = f"Silent Aim/Hit {'ON' if aa.silent_aim_enabled else 'OFF'}"
                print(f"[SilentAimQT] {'ON' if aa.silent_aim_enabled else 'OFF'}")
            if code_str == "KEY_INSERT":
                # Aumenta intensidade MANUALMENTE (modo que estiver ativo)
                qt = self.pipeline.aa_pipeline.silent_qt
                aa = self.config.aim_assist
                if qt.get_mode().value == "aim":
                    aa.silent_aim_intensity = min(10, aa.silent_aim_intensity + 1)
                    qt.aim_intensity = aa.silent_aim_intensity
                    self.status_message = f"Silent Aim intensity: {aa.silent_aim_intensity}"
                else:
                    aa.silent_hit_intensity = min(10, aa.silent_hit_intensity + 1)
                    qt.hit_intensity = aa.silent_hit_intensity
                    self.status_message = f"Silent Hit intensity: {aa.silent_hit_intensity}"
                print(f"[SilentAimQT] Intensidade +1 -> {self.status_message}")
            if code_str == "KEY_HOME":
                # Diminui intensidade MANUALMENTE
                qt = self.pipeline.aa_pipeline.silent_qt
                aa = self.config.aim_assist
                if qt.get_mode().value == "aim":
                    aa.silent_aim_intensity = max(1, aa.silent_aim_intensity - 1)
                    qt.aim_intensity = aa.silent_aim_intensity
                    self.status_message = f"Silent Aim intensity: {aa.silent_aim_intensity}"
                else:
                    aa.silent_hit_intensity = max(1, aa.silent_hit_intensity - 1)
                    qt.hit_intensity = aa.silent_hit_intensity
                    self.status_message = f"Silent Hit intensity: {aa.silent_hit_intensity}"
                print(f"[SilentAimQT] Intensidade -1 -> {self.status_message}")
        else:
            self.shift_manager.handle_button_release(code_str)

        if macro_manager.is_recording():
            action, _ = self.remap_pipeline.remapper.process_key(code_str, 1)
            if action and (action.startswith("BTN_") or action in ("ABS_Z", "ABS_RZ")):
                macro_manager.record_action(
                    MacroActionType.PRESS if norm_value else MacroActionType.RELEASE,
                    action
                )

        if code_str in TAP_ONLY_KEYS:
            if norm_value:
                action, _ = self.remap_pipeline.remapper.process_key(code_str, 1)
                self._write_keyboard_passthrough(event, action)
                if action:
                    self._write_mapped(action, 1)
                    self._pending_tap_releases[action] = time.monotonic() + TAP_HOLD_MS / 1000.0
            else:
                # Release físico: se ainda não foi agendado/flushado, solta imediatamente.
                action, _ = self.remap_pipeline.remapper.process_key(code_str, 1)
                self._pending_tap_releases.pop(action, None)
                self._write_keyboard_passthrough(event, action)
                if action:
                    self._write_mapped(action, 0)
        else:
            action, out_val = self.remap_pipeline.remapper.process_key(code_str, norm_value)
            self._write_keyboard_passthrough(event, action)
            if action:
                self._write_mapped(action, out_val)

        if norm_value and not macro_manager.is_recording():
            if macro_manager.play_macro_by_trigger(code_str):
                return

        for btn_code, state in self.pipeline.macro_buttons.items():
            self.controller.write_button(btn_code, state)

        # Crouch Aim reage imediatamente ao press/release de ADS (não espera
        # o próximo movimento do mouse pra atualizar o estado).
        if code_str in ("BTN_RIGHT", "BTN_LEFT", "BTN_TL", "BTN_TR"):
            kbd_keys = self.remap_pipeline.get_active_keys()
            self.pipeline._update_zen_features(
                is_shooting="BTN_LEFT" in kbd_keys,
                delta_ms=0.0,
                is_moving=bool({"KEY_W", "KEY_S", "KEY_A", "KEY_D"} & kbd_keys),
                is_aiming=("BTN_RIGHT" in kbd_keys or "BTN_TL" in kbd_keys or "BTN_TR" in kbd_keys),
            )

    def _handle_controller_event(self, event, dev: Optional[InputDevice] = None) -> None:
        sony_kind = _detect_sony_kind(dev)
        eightbitdo_kind = _detect_8bitdo_kind(dev)
        now = time.monotonic()

        if event.type == e.EV_ABS:
            val = event.value
            code = event.code
            if sony_kind:
                mapped = map_sony_axis(sony_kind, code, val)
                if mapped is not None:
                    code, val = mapped

            self.raw.update_axis(code, val)
            self._apply_controller_state(now)

        elif event.type == e.EV_KEY:
            code = event.code
            if sony_kind and code in DS4_BUTTON_MAP:
                code = DS4_BUTTON_MAP[code]

            self.raw.buttons[code] = event.value
            self._last_input_time = now
            if event.value:
                code_str = e.keys.get(code, f"KEY_{code}")
                if not isinstance(code_str, str):
                    code_str = code_str[0] if isinstance(code_str, (list, tuple)) else str(code_str)
                print(f"[CTRL KEY] {code_str} (code={code})")
                if macro_manager.is_trigger_capturing():
                    if macro_manager.set_capture_trigger(code_str):
                        self.status_message = f"Trigger capturado: {code_str}"
                    return
                if macro_manager.is_recording():
                    macro_manager.record_action(MacroActionType.PRESS, code_str)
                if code_str in ("KEY_CAPSLOCK", "KEY_SCROLLLOCK", "KEY_PAUSE"):
                    aa = self.config.aim_assist
                    aa.cjitter_enabled = not aa.cjitter_enabled
                    aa.cjitter_left_enabled = aa.cjitter_enabled
                    print(f"[Jitter] {'ON' if aa.cjitter_enabled else 'OFF'}")
                if code == e.BTN_Y:  # Triângulo: troca de arma
                    self.pipeline.handle_weapon_swap("BTN_Y")
            self.controller.write_button(code, event.value)

    def _run_aa_tick(self, now: float) -> None:
        """Tick fixo (~1ms) do caminho controle.

        Sem evento físico, roda os motores de AA sobre o último estado do
        stick e escreve o output continuamente no controle virtual — o
        micro-input constante que re-dispara o AA nativo do Fortnite
        (estilo Cronus Zen). Sem isso, stick parado = output morto.
        """
        if self._disabled or not self._controller_mode:
            return
        if not self.config.aim_assist.enabled:
            return
        self._apply_controller_state(now)

    def _apply_controller_state(self, now: float) -> None:
        """Processa o estado atual do stick (evento físico ou tick de AA).

        Roda o pipeline completo (física + AA + Zen) e escreve os eixos no
        controle virtual. No caminho controle os motores Zen do left stick
        (Rush strafe e micro-oscilação) rodam aqui — antes só existiam no
        caminho KBM (_run_flush_remap), então o AA nativo perdia o strafe
        que o mantém vivo.
        """
        lx, ly, rx, ry, lt, rt = self.pipeline.process(self.raw)

        # ── Head Snap Engine ──
        is_aiming = lt > 20
        is_shooting = rt > 20
        is_moving = abs(lx) > 3000 or abs(ly) > 3000
        rx, ry = self.pipeline.head_snap_engine.apply(
            rx, ry,
            is_aiming=is_aiming,
            is_shooting=is_shooting,
            is_moving=is_moving,
            now=now,
            delta_ms=(now - self.pipeline.last_time) * 1000.0,
            enabled=self.config.aim_assist.head_snap_enabled,
            strength=self.config.aim_assist.head_snap_strength,
            height=self.config.aim_assist.head_snap_height,
            duration=self.config.aim_assist.head_snap_duration,
            cooldown=self.config.aim_assist.head_snap_cooldown,
            smooth=self.config.aim_assist.head_snap_smooth,
            mode=self.config.aim_assist.head_snap_mode,
            ads_only=self.config.aim_assist.head_snap_ads_only,
        )

        if self.config.remap_active:
            klx, kly = self.remap_pipeline.get_stick_values()
            if klx or kly:
                lx, ly = klx, kly

        # ── Rush strafe (estilo Zen) no caminho controle ──
        # O strafe lateral do left stick é o que mantém o rotational AA do
        # Fortnite engajado (AA só atua com o stick em movimento).
        if self.config.aim_assist.rush_enabled:
            rush_active = is_aiming or self.config.aim_assist.rush_always
            self.pipeline.rush_engine.set_active(rush_active)
            if rush_active:
                strafe = self.pipeline.rush_engine.get_strafe(now)
                lx = lx + strafe if lx or strafe else strafe

        # ── Micro-oscilação do left stick (estilo Zen) ──
        delta_ms = (now - self.pipeline.last_time) * 1000.0
        lx, ly = self.pipeline.left_stick_freq_engine.apply(
            int(lx), int(ly),
            enabled=self.config.aim_assist.ls_freq_enabled,
            amplitude=self.config.aim_assist.ls_freq_amplitude,
            frequency=self.config.aim_assist.ls_freq_frequency,
            shape=self.config.aim_assist.ls_freq_shape,
            gate=self.config.aim_assist.ls_freq_gate,
            delta_ms=delta_ms,
            is_moving=abs(lx) > 3000 or abs(ly) > 3000,
            aggressive=self.config.aim_assist.ls_freq_aggressive,
        )

        self.controller.write_axis(e.ABS_X, int(lx))
        self.controller.write_axis(e.ABS_Y, int(ly))
        self.controller.write_axis(e.ABS_RX, int(rx))
        self.controller.write_axis(e.ABS_RY, int(ry))
        self.controller.write_trigger(e.ABS_Z, int(lt))
        self.controller.write_trigger(e.ABS_RZ, int(rt))

        self._last_rx = float(rx)
        self._last_ry = float(ry)
        self._last_input_time = now

        if self.pipeline._pending_crouch is not None:
            btn_code = self.pipeline.crouch_spam_engine.get_button_code()
            self.controller.write_button(btn_code, 1 if self.pipeline._pending_crouch else 0)

        for btn_code, state in self.pipeline._slide_cancel_output.items():
            self.controller.write_button(btn_code, state)

        for btn_code, state in self.pipeline._crouch_aim_output.items():
            self.controller.write_button(btn_code, state)

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

        if self.config.aim_assist.enabled:
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

            lx, ly = self.pipeline.left_stick_freq_engine.apply(
                lx, ly,
                enabled=self.config.aim_assist.ls_freq_enabled,
                amplitude=self.config.aim_assist.ls_freq_amplitude,
                frequency=self.config.aim_assist.ls_freq_frequency,
                shape=self.config.aim_assist.ls_freq_shape,
                gate=self.config.aim_assist.ls_freq_gate,
                delta_ms=delta_ms,
                is_moving=abs(lx) > 3000 or abs(ly) > 3000,
                aggressive=self.config.aim_assist.ls_freq_aggressive,
            )

            # ── Oscilação do LEFT stick (grude nos dois analógicos) ──
            # O rotational AA do Fortnite ativa com o left stick em movimento
            # contínuo. Aplica micro-oscilação com gate adaptativo: gruda
            # quando parado, fica fluido quando o jogador move (WASD).
            if self.config.aim_assist.ls_freq_enabled:
                qt_left = self.pipeline.aa_pipeline.silent_qt
                lx_f, ly_f = qt_left.process_left_stick(
                    float(lx), float(ly),
                    delta_ms=delta_ms,
                )
                lx, ly = int(lx_f), int(ly_f)

        lx = max(-32767, min(32767, lx))
        ly = max(-32767, min(32767, ly))
        self.controller.write_axis(e.ABS_X, lx)
        self.controller.write_axis(e.ABS_Y, ly)

        # ── Silent Aim / Silent Hit QT — oscilação CONTÍNUA no right stick ──
        # O Cronus Zen escreve o stick a ~50Hz MESMO com o jogador parado.
        # O right stick só era atualizado no movimento do mouse — com o
        # jogador parado em ADS, a oscilação do silent_qt morria. Aqui o
        # flush roda a cada loop (~1ms) e mantém a oscilação viva.
        if self.config.aim_assist.enabled:
            qt = self.pipeline.aa_pipeline.silent_qt
            aa_cfg = kbm_sanitize_config(self.config.aim_assist)
            # Sincroniza config com o pipeline (mudanças por tecla/UI)
            qt.enabled = (
                (aa_cfg.silent_aim_qt_enabled and aa_cfg.silent_aim_enabled)
                or (aa_cfg.silent_hit_qt_enabled and aa_cfg.silent_hit_enabled)
            )
            qt.aim_intensity = aa_cfg.silent_aim_intensity
            qt.hit_intensity = aa_cfg.silent_hit_intensity
            qt.aim_shake_blend = aa_cfg.silent_aim_qt_shake_blend
            qt.hit_shake_blend = aa_cfg.silent_hit_qt_shake_blend
            qt.aim_enabled = aa_cfg.silent_aim_enabled
            qt.hit_enabled = aa_cfg.silent_hit_enabled

            # AutoTrack config
            qt.auto_track_enabled = aa_cfg.auto_track_enabled
            qt.auto_track_multiplier = aa_cfg.auto_track_multiplier
            qt.auto_track_threshold = aa_cfg.auto_track_threshold
            qt.auto_track_persistence_ms = aa_cfg.auto_track_persistence_ms

            # StickyMagnet config
            qt.sticky_magnet_enabled = aa_cfg.sticky_magnet_enabled
            qt.sticky_magnet_strength = aa_cfg.sticky_magnet_strength
            qt.sticky_magnet_pull = aa_cfg.sticky_magnet_pull

            # Estado do jogador
            kbd_keys = self.remap_pipeline.get_active_keys()
            is_shooting = ("BTN_LEFT" in kbd_keys)
            is_aiming = ("BTN_RIGHT" in kbd_keys or "BTN_TL" in kbd_keys or "BTN_TR" in kbd_keys)

            # Último right stick (do mouse ou 0)
            last_rx = self._last_rx if abs(self._last_rx) > 0 else 0.0
            last_ry = self._last_ry if abs(self._last_ry) > 0 else 0.0

            delta_ms = (now - self.pipeline.last_time) * 1000.0
            if delta_ms <= 0 or delta_ms > 100:
                delta_ms = 16.0

            out_x, out_y = qt.process_combo(
                float(last_rx), float(last_ry),
                is_firing=is_shooting,
                is_ads=is_aiming,
                delta_ms=delta_ms,
                now=now,
            )

            # Só escreve se o silent_qt está ativo em algum modo
            from nocrosshair.features.silent_aim_qt import SilentMode
            if qt.get_mode() != SilentMode.NONE:
                # ── Smoothing do right stick (anti pixel-jump) ──
                # O mouse é delta com min_output que "pula" o stick. Um EMA
                # no output suaviza os micro-saltos verticais/horizontais
                # sem atrasar o tracking (alpha alto = responsivo).
                alpha = 0.55
                self._qt_out_rx = self._qt_out_rx * (1.0 - alpha) + out_x * alpha
                self._qt_out_ry = self._qt_out_ry * (1.0 - alpha) + out_y * alpha
                out_x = self._qt_out_rx
                out_y = self._qt_out_ry
                self.controller.write_axis(e.ABS_RX, int(round(out_x)))
                self.controller.write_axis(e.ABS_RY, int(round(out_y)))

        # ── Aim Layers (arquitetura em camadas) ──
        # Rodo as layers SEMPRE que o aim assist está ligado.
        # Substitui o bloco acima quando todas as layers estiverem prontas.
        if self.config.aim_assist.enabled and self.pipeline.aim_layers is not None:
            kbd_keys = self.remap_pipeline.get_active_keys()
            is_shooting = ("BTN_LEFT" in kbd_keys)
            is_aiming = ("BTN_RIGHT" in kbd_keys or "BTN_TL" in kbd_keys or "BTN_TR" in kbd_keys)
            is_moving = any(k in kbd_keys for k in ("KEY_W", "KEY_A", "KEY_S", "KEY_D"))

            ctx = LayerContext()
            ctx.delta_ms = delta_ms
            ctx.now = now
            ctx.is_aiming = is_aiming
            ctx.is_shooting = is_shooting
            ctx.is_moving = is_moving
            ctx.raw_rx = float(last_rx)
            ctx.raw_ry = float(last_ry)

            al = self.pipeline.aim_layers
            # Sincroniza config do slowdown layer
            al.slowdown.zone = self.config.aim_assist.zone
            al.slowdown.strength = self.config.aim_assist.strength
            al.slowdown.rotational_enabled = self.config.aim_assist.rotational
            al.slowdown.ads_multiplier = self.config.aim_assist.ads_multiplier

            # Sincroniza aim_lock_silent layer (Layer 2 — ADS)
            al.aim_lock_silent.enabled = self.config.aim_assist.silent_aim_enabled
            al.aim_lock_silent.gpc_amp = 5.0 + self.config.aim_assist.silent_aim_intensity * 3.0
            al.aim_lock_silent.lock_enabled = self.config.aim_assist.lock_enabled
            al.aim_lock_silent.lock_fov = self.config.aim_assist.lock_fov
            al.aim_lock_silent.lock_strength = self.config.aim_assist.lock_strength / 18000.0
            al.aim_lock_silent.lock_smooth = self.config.aim_assist.lock_smooth

            # Sincroniza camera_hit layer (Layer 3 — hip fire)
            al.camera_hit.enabled = self.config.aim_assist.silent_hit_enabled
            al.camera_hit.gpc_amp = 5.0 + self.config.aim_assist.silent_hit_intensity * 3.0

            # Sincroniza track layer
            al.track_snap.track_enabled = self.config.aim_assist.auto_track_enabled
            al.track_snap.track_multiplier = self.config.aim_assist.auto_track_multiplier
            al.track_snap.track_threshold = self.config.aim_assist.auto_track_threshold
            al.track_snap.track_persistence_ms = self.config.aim_assist.auto_track_persistence_ms

            # Sincroniza sticky layer
            al.sticky.enabled = self.config.aim_assist.sticky_magnet_enabled
            al.sticky.strength = self.config.aim_assist.sticky_magnet_strength
            al.sticky.magnetic_pull = self.config.aim_assist.sticky_magnet_pull

            layer_rx, layer_ry = al.process(ctx.raw_rx, ctx.raw_ry, ctx)

            # Escreve o output das layers
            self.controller.write_axis(e.ABS_RX, int(round(layer_rx)))
            self.controller.write_axis(e.ABS_RY, int(round(layer_ry)))

        lt, rt = self.remap_pipeline.get_trigger_values()

        # ── Rapid Fire / Bloom Reducer no caminho KBM ──
        # O hold do botão do mouse precisa do ciclo a cada loop (o evento de
        # press sozinho não cicla). Auto-seleção pela arma ativa. Só age com
        # o gatilho KBM pressionado (raw_rt>0) — no modo controle físico o
        # pipeline.process já aplica o engine e escreve os triggers.
        # O release do mouse grava 0 via evento (não trava o R2).
        raw_rt = rt
        fire_active = raw_rt > 10 and (
            self.config.bloom_reducer.enabled or self.config.rapid_fire.enabled
        )
        if fire_active:
            weapon = self.pipeline.weapon_slots[self.pipeline.active_weapon_index]
            if _prefer_rapid_fire(weapon) and self.config.rapid_fire.enabled:
                now_f = time.monotonic()
                delta_ms = (now_f - self.pipeline.last_time) * 1000.0
                rt = self.pipeline.rapid_fire_engine.process_from_speed(
                    int(rt), True, delta_ms
                )
            elif self.config.bloom_reducer.enabled:
                rt = self.pipeline.bloom_reducer_engine.process(int(rt), True)

        if lt:
            _dbg(f"flush ABS_Z(L2) = {lt} (output_state ABS_Z={self.remap_pipeline._output_state.get('ABS_Z')})")
            self.controller.write_trigger(e.ABS_Z, lt)
        if rt or fire_active:
            _dbg(f"flush ABS_RZ(R2) = {rt} (output_state ABS_RZ={self.remap_pipeline._output_state.get('ABS_RZ')})")
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

        for btn_code, state in self.pipeline._crouch_aim_output.items():
            self.controller.write_button(btn_code, state)

        for btn_code, state in self.pipeline._movement_output.items():
            self.controller.write_button(btn_code, state)

    def _flush_tap_releases(self, now: float) -> None:
        """Libera taps (Q/F) agendados após o hold mínimo, para o jogo detectar o press."""
        if not self._pending_tap_releases:
            return
        due = [action for action, release_at in self._pending_tap_releases.items() if now >= release_at]
        for action in due:
            self._pending_tap_releases.pop(action, None)
            self._write_mapped(action, 0)

    def _run_idle_cleanup(self, now: float) -> None:
        if self._disabled:
            time.sleep(0.0005)
            return
        idle_ms = (now - self._last_input_time) * 1000.0
        if idle_ms > 50 and (self._last_rx != 0.0 or self._last_ry != 0.0):
            # Com AA ligado os motores sustentam o output (persistência,
            # lock, drift) — forçar 0 aqui matava o "grude" do Zen no
            # momento em que o jogador solta o stick.
            if not self.config.aim_assist.enabled:
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
