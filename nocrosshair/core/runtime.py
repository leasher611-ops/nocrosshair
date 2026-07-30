#!/usr/bin/env python3

import json
import os
import threading
from typing import Optional, Dict, Any, List

from nocrosshair.core.config import AppConfig, CONFIG_PATH
from nocrosshair.core.controller import VirtualController
from nocrosshair.core.input_loop import InputLoop, InputPipeline, find_controller_devices
from nocrosshair.core.plugins import plugin_manager
from nocrosshair.core.device_manager import device_manager
from nocrosshair.core.game_profiles import game_profile_manager
from nocrosshair.controllers.registry import registry


class RuntimeManager:

    _instance: Optional["RuntimeManager"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "RuntimeManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._config: Optional[AppConfig] = None
        self._device_path: Optional[str] = None
        self._controller: Optional[VirtualController] = None
        self._input_loop: Optional[InputLoop] = None
        self._running = False
        self._last_error: str = ""
        self._game_detector = game_profile_manager.detector
        self._active_slots: List[str] = []
        self._game_detector.on_game_detected(self._on_game_detected)
        self._load_plugins()

    def _load_plugins(self) -> None:
        plugins_dir = os.path.join(os.path.expanduser("~/.config"), "nocrosshair_profiles", "plugins")
        os.makedirs(plugins_dir, exist_ok=True)
        plugin_manager.add_plugin_dir(plugins_dir)
        plugin_manager.discover_plugins()
        plugin_manager.load_config()
        plugin_manager.start_file_watcher()

    def _on_game_detected(self, game_key: Optional[str]):
        """Callback automático quando um jogo é detectado via ps aux."""
        if not game_key:
            return
        profile = game_profile_manager.get_profile(game_key)
        if profile and self._running:
            print(f"[RuntimeManager] Auto-Switching to profile: {game_key}")
            # Aqui o sistema re-aplica a configuração baseada no perfil do jogo
            # O frontend ou o master config pode ser atualizado aqui.

    @property
    def game_detector(self):
        return self._game_detector

    def start(self, device_path: str, slots: Optional[List[str]] = None) -> bool:
        if self._running:
            return True

        try:
            self._device_path = device_path
            cfg = self._config or AppConfig()

            self._controller = VirtualController(cfg.controller_type)
            self._controller.change_type(cfg.controller_type)

            # v4: Apply hardware descriptor if configured
            try:
                hw_id = cfg.controller_hardware.controller_id
                if registry.get(hw_id):
                    self._controller.reconfigure_for_hardware(hw_id)
            except (KeyError, RuntimeError):
                pass

            if slots:
                self._active_slots = slots
                for slot_name in slots:
                    device_manager.create_device(
                        slot_name, cfg.controller_type
                    )

            self._input_loop = InputLoop(cfg, self._controller, device_path)
            self._input_loop.start()
            self._running = True
            self._game_detector.start()
            return True
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"[RuntimeManager] start failed: {e}\n{tb}")
            self._last_error = f"{e}"
            self._cleanup()
            return False

    def stop(self) -> None:
        if not self._running:
            return
        self._game_detector.stop()
        if self._input_loop:
            self._input_loop.stop()
        self._cleanup()

    def _cleanup(self) -> None:
        self._running = False
        device_manager.shutdown_all()
        if self._controller:
            self._controller.close()
            self._controller = None
        self._input_loop = None

    def get_device_manager_status(self) -> Dict[str, Any]:
        slots = device_manager.list_devices()
        return {
            "slot_count": len(slots),
            "slots": slots,
        }

    def _get_status(self) -> Dict[str, Any]:
        hw_info = {}
        if self._config:
            hw_id = self._config.controller_hardware.controller_id
            try:
                desc = registry.get_descriptor(hw_id)
                hw_info = {
                    "hardware_name": desc.name,
                    "polling_rate": desc.polling_rate_hz,
                    "trigger_mode": self._config.controller_hardware.trigger.mode.value,
                }
            except KeyError:
                hw_info = {"hardware_name": hw_id, "polling_rate": 0, "trigger_mode": "analog"}
        return {
            "active": self._running,
            "device": self._device_path,
            "virtual_ready": self._controller is not None and self._controller.device is not None,
            "device_manager": self.get_device_manager_status(),
            "controller_hardware": hw_info,
            "disabled": self._input_loop.is_disabled if self._input_loop else False,
        }

    def apply_config(self, cfg: AppConfig) -> None:
        old_hw_id = self._config.controller_hardware.controller_id if self._config else None
        self._config = cfg
        if self._input_loop:
            self._input_loop.update_config(cfg)
            new_hw_id = cfg.controller_hardware.controller_id
            if old_hw_id and old_hw_id != new_hw_id:
                try:
                    self._controller.reconfigure_for_hardware(new_hw_id)
                except (KeyError, RuntimeError):
                    pass

    def apply_and_save(self, cfg: AppConfig) -> bool:
        self.apply_config(cfg)
        return self._save_config(cfg)

    def _save_config(self, cfg: AppConfig) -> bool:
        try:
            data = cfg.to_dict()
            data["kbd_bindings"] = cfg.kbd_bindings
            payload = {
                "_format": "nocrosshair.nocro",
                "_version": 1,
                "config": data,
            }
            os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
            with open(CONFIG_PATH, "w") as f:
                f.write("# NOCRO v1 — nocrosshair config file\n")
                json.dump(payload, f, indent=2)
            return True
        except Exception as e:
            print(f"[RuntimeManager] save failed: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        if self._input_loop and self._running:
            if not self._input_loop.is_running:
                self._cleanup()
                return self._get_status()
        return self._get_status()

    def is_sniper_zoom_held(self) -> bool:
        if self._input_loop is None or not self._input_loop.is_running:
            return False
        cfg = self._input_loop.config
        if not cfg.sniper_zoom.enabled:
            return False
        btn = cfg.sniper_zoom.button
        return btn in self._input_loop.remap_pipeline.get_active_keys()

    def get_available_devices(self) -> List[dict]:
        return find_controller_devices()

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def config(self) -> Optional[AppConfig]:
        return self._config

    def load_config(self) -> Optional[AppConfig]:
        try:
            if not os.path.exists(CONFIG_PATH):
                return None
            with open(CONFIG_PATH, "r") as f:
                content = f.read()
            data = json.loads(content.split("\n", 1)[-1])
            inner = data.get("config", data)
            cfg = AppConfig.from_dict(inner)
            self._config = cfg
            return cfg
        except Exception as e:
            print(f"[RuntimeManager] load_config failed: {e}")
            return None

    @property
    def last_error(self) -> str:
        return self._last_error

    def shutdown(self) -> None:
        self.stop()
        RuntimeManager._instance = None
        self._initialized = False
