#!/usr/bin/env python3

import os
import json
import importlib.util
import threading
import time
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from abc import ABC, abstractmethod

from nocrosshair.core.config import PROFILES_DIR


class PluginHooks:
    """Central hook registry for the plugin system."""

    HOOK_NAMES = [
        "on_raw_input",
        "on_post_physics",
        "on_post_aa",
        "on_pre_write",
        "on_button",
    ]

    def __init__(self):
        self._hooks: Dict[str, List[Callable]] = {h: [] for h in self.HOOK_NAMES}

    def register(self, hook_name: str, callback: Callable) -> None:
        if hook_name not in self._hooks:
            self._hooks[hook_name] = []
        self._hooks[hook_name].append(callback)

    def unregister(self, hook_name: str, callback: Callable) -> None:
        if hook_name in self._hooks:
            self._hooks[hook_name] = [c for c in self._hooks[hook_name] if c is not callback]

    def call(self, hook_name: str, *args, **kwargs) -> List[Any]:
        results = []
        for callback in self._hooks.get(hook_name, []):
            try:
                result = callback(*args, **kwargs)
                results.append(result)
            except Exception as e:
                print(f"[PluginHooks] Error in {hook_name}: {e}")
        return results

    def pipeline(self, hook_name: str, initial, *args, **kwargs):
        current = initial
        for callback in self._hooks.get(hook_name, []):
            try:
                current = callback(current, *args, **kwargs)
            except Exception as e:
                print(f"[PluginHooks] Error in {hook_name}: {e}")
        return current

    def clear(self) -> None:
        for hook_name in self._hooks:
            self._hooks[hook_name] = []

    def get_registered(self) -> Dict[str, int]:
        return {h: len(cbs) for h, cbs in self._hooks.items()}


class NocrosshairPlugin(ABC):
    """Base class all plugins must extend."""

    def __init__(self):
        self.name = "Base Plugin"
        self.version = "1.0.0"
        self.author = "Unknown"
        self.enabled = True

    @abstractmethod
    def on_load(self, hooks: PluginHooks) -> None:
        pass

    @abstractmethod
    def on_unload(self) -> None:
        pass

    def on_config_change(self, cfg: Dict[str, Any]) -> None:
        pass

    def get_physics_engine(self):
        return None

    def get_aa_engine(self):
        return None

    def on_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        return input_data


@dataclass
class PluginInfo:
    name: str
    version: str
    author: str
    description: str
    enabled: bool
    path: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "enabled": self.enabled,
            "path": self.path,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "PluginInfo":
        return PluginInfo(
            name=d.get("name", ""),
            version=d.get("version", ""),
            author=d.get("author", ""),
            description=d.get("description", ""),
            enabled=d.get("enabled", True),
            path=d.get("path", ""),
        )


class PluginFileWatcher:
    """Watches plugin directories for file changes and triggers hot-reload.

    Tries watchdog first; falls back to polling if unavailable.
    """

    def __init__(self, plugin_manager: "PluginManager", poll_interval: float = 2.0):
        self._pm = plugin_manager
        self._poll_interval = poll_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._mtimes: Dict[str, float] = {}
        self._observer = None
        self._use_watchdog = False

        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
            self._Observer = Observer
            self._FileSystemEventHandler = FileSystemEventHandler
            self._use_watchdog = True
        except ImportError:
            pass

    def start(self) -> None:
        if self._running:
            return
        self._running = True

        if self._use_watchdog:
            self._start_watchdog()
        else:
            self._start_polling()

    def stop(self) -> None:
        self._running = False
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=3)
            self._observer = None
        if self._thread:
            self._thread.join(timeout=3)
            self._thread = None

    def _start_watchdog(self) -> None:
        pm = self._pm

        class _Handler(self._FileSystemEventHandler):
            def on_modified(self, event):
                if event.is_directory:
                    return
                if event.src_path.endswith(".py"):
                    pm._handle_file_change(event.src_path)

            def on_created(self, event):
                if event.is_directory:
                    return
                if event.src_path.endswith(".py"):
                    pm._handle_file_change(event.src_path)

        self._observer = self._Observer()
        handler = _Handler()
        for plugin_dir in self._pm._plugin_dirs:
            if os.path.isdir(plugin_dir):
                self._observer.schedule(handler, plugin_dir, recursive=True)
        self._observer.start()

    def _start_polling(self) -> None:
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def _poll_loop(self) -> None:
        while self._running:
            for plugin_dir in self._pm._plugin_dirs:
                if not os.path.isdir(plugin_dir):
                    continue
                for root, _dirs, files in os.walk(plugin_dir):
                    for fname in files:
                        if not fname.endswith(".py"):
                            continue
                        fpath = os.path.join(root, fname)
                        try:
                            mtime = os.path.getmtime(fpath)
                        except OSError:
                            continue
                        old = self._mtimes.get(fpath)
                        if old is not None and mtime != old:
                            self._pm._handle_file_change(fpath)
                        self._mtimes[fpath] = mtime
            time.sleep(self._poll_interval)


class PluginManager:

    def __init__(self):
        self._plugins: Dict[str, NocrosshairPlugin] = {}
        self._plugin_info: Dict[str, PluginInfo] = {}
        self._plugin_dirs: List[str] = []
        self._hooks = PluginHooks()
        self._file_watcher: Optional[PluginFileWatcher] = None
        self._log: List[str] = []

    @property
    def hooks(self) -> PluginHooks:
        return self._hooks

    def add_plugin_dir(self, directory: str) -> None:
        if directory not in self._plugin_dirs:
            self._plugin_dirs.append(directory)

    def start_file_watcher(self) -> None:
        if self._file_watcher is None:
            self._file_watcher = PluginFileWatcher(self)
        self._file_watcher.start()

    def stop_file_watcher(self) -> None:
        if self._file_watcher:
            self._file_watcher.stop()

    def _handle_file_change(self, filepath: str) -> None:
        dir_name = os.path.basename(os.path.dirname(filepath))
        plugin_name = None
        for name, info in self._plugin_info.items():
            if info.path and os.path.normpath(info.path) == os.path.normpath(os.path.dirname(filepath)):
                plugin_name = name
                break

        if plugin_name:
            self._log_event(f"Hot-reload: {plugin_name} ({filepath})")
            self.unload_plugin(plugin_name)
            self.load_plugin(plugin_name)

    def _log_event(self, msg: str) -> None:
        ts = time.strftime("%H:%M:%S")
        entry = f"[{ts}] {msg}"
        self._log.append(entry)
        if len(self._log) > 200:
            self._log = self._log[-200:]
        print(f"[PluginManager] {msg}")

    def get_log(self) -> List[str]:
        return list(self._log)

    def clear_log(self) -> None:
        self._log.clear()

    def discover_plugins(self) -> List[PluginInfo]:
        discovered = []

        for plugin_dir in self._plugin_dirs:
            if not os.path.exists(plugin_dir):
                continue

            for item in os.listdir(plugin_dir):
                item_path = os.path.join(plugin_dir, item)
                if os.path.isdir(item_path):
                    plugin_file = os.path.join(item_path, "plugin.py")
                    if os.path.exists(plugin_file):
                        info = self._load_plugin_info(item_path)
                        if info:
                            discovered.append(info)
                            self._plugin_info[info.name] = info

        return discovered

    def _load_plugin_info(self, plugin_path: str) -> Optional[PluginInfo]:
        try:
            info_file = os.path.join(plugin_path, "plugin.json")
            if os.path.exists(info_file):
                with open(info_file, 'r') as f:
                    data = json.load(f)
                data["path"] = data.get("path", "") or plugin_path
                return PluginInfo.from_dict(data)
        except Exception:
            pass

        return None

    def load_plugin(self, name: str) -> bool:
        if name in self._plugins:
            return True

        info = self._plugin_info.get(name)
        if not info or not info.path:
            return False

        try:
            plugin_file = os.path.join(info.path, "plugin.py")
            spec = importlib.util.spec_from_file_location(name, plugin_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if hasattr(module, 'Plugin'):
                plugin_class = module.Plugin
                plugin = plugin_class()
                plugin.name = name
                plugin.version = info.version
                plugin.author = info.author

                self._plugins[name] = plugin
                plugin.on_load(self._hooks)
                self._log_event(f"Loaded: {name} v{info.version}")
                return True
        except Exception as e:
            self._log_event(f"Error loading {name}: {e}")

        return False

    def unload_plugin(self, name: str) -> bool:
        if name not in self._plugins:
            return False
        plugin = self._plugins[name]
        try:
            plugin.on_unload()
        except Exception as e:
            self._log_event(f"Error unloading {name}: {e}")
        for hook_name in PluginHooks.HOOK_NAMES:
            self._hooks._hooks[hook_name] = [
                cb for cb in self._hooks._hooks[hook_name]
                if not (hasattr(cb, '__self__') and cb.__self__ is plugin)
                and not (hasattr(cb, '__wrapped__') and cb.__wrapped__ is plugin)
            ]
        del self._plugins[name]
        self._log_event(f"Unloaded: {name}")
        return True

    def get_plugin(self, name: str) -> Optional[NocrosshairPlugin]:
        return self._plugins.get(name)

    def get_loaded_plugins(self) -> List[str]:
        return list(self._plugins.keys())

    def get_available_plugins(self) -> List[PluginInfo]:
        return list(self._plugin_info.values())

    def enable_plugin(self, name: str) -> None:
        if name in self._plugin_info:
            self._plugin_info[name].enabled = True

    def disable_plugin(self, name: str) -> None:
        if name in self._plugin_info:
            self._plugin_info[name].enabled = False

    def register_hook(self, hook_name: str, callback: Callable) -> None:
        self._hooks.register(hook_name, callback)

    def call_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        return self._hooks.call(hook_name, *args, **kwargs)

    def call_hook_pipeline(self, hook_name: str, initial, *args, **kwargs):
        return self._hooks.pipeline(hook_name, initial, *args, **kwargs)

    def save_config(self) -> bool:
        try:
            config_path = os.path.join(PROFILES_DIR, "plugins.json")
            os.makedirs(os.path.dirname(config_path), exist_ok=True)

            config = {
                "plugins": {name: info.to_dict() for name, info in self._plugin_info.items()},
                "loaded": list(self._plugins.keys()),
            }

            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            self._log_event(f"Error saving config: {e}")
            return False

    def load_config(self) -> bool:
        try:
            config_path = os.path.join(PROFILES_DIR, "plugins.json")
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)

                for name, info_data in config.get("plugins", {}).items():
                    existing = self._plugin_info.get(name)
                    if existing and existing.path and not info_data.get("path"):
                        info_data["path"] = existing.path
                    self._plugin_info[name] = PluginInfo.from_dict(info_data)

                for name in config.get("loaded", []):
                    self.load_plugin(name)

                return True
            return False
        except Exception as e:
            self._log_event(f"Error loading config: {e}")
            return False

    def open_plugin_folder(self) -> str:
        if self._plugin_dirs:
            folder = self._plugin_dirs[0]
            os.makedirs(folder, exist_ok=True)
            return folder
        default = os.path.join(PROFILES_DIR, "plugins")
        os.makedirs(default, exist_ok=True)
        return default


plugin_manager = PluginManager()
