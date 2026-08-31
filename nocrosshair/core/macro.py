#!/usr/bin/env python3

import time
import json
import os
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum

from nocrosshair.core.config import PROFILES_DIR

class MacroActionType(Enum):
    PRESS = "press"
    RELEASE = "release"
    DELAY = "delay"

@dataclass
class MacroAction:
    action_type: MacroActionType
    target: str
    duration: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_type": self.action_type.value,
            "target": self.target,
            "duration": self.duration,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "MacroAction":
        return MacroAction(
            action_type=MacroActionType(d.get("action_type", "press")),
            target=d.get("target", ""),
            duration=d.get("duration", 0),
        )

@dataclass
class Macro:
    name: str
    trigger: str
    actions: List[MacroAction]
    timing: List[int]
    repeat: bool = False
    repeat_count: int = 1
    speed: float = 1.0

    def __post_init__(self):
        if self.actions is None:
            self.actions = []
        if self.timing is None:
            self.timing = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "trigger": self.trigger,
            "actions": [action.to_dict() for action in self.actions],
            "timing": self.timing,
            "repeat": self.repeat,
            "repeat_count": self.repeat_count,
            "speed": self.speed,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Macro":
        actions = [MacroAction.from_dict(action_data) for action_data in d.get("actions", [])]
        return Macro(
            name=d.get("name", "Unnamed"),
            trigger=d.get("trigger", ""),
            actions=actions,
            timing=d.get("timing", []),
            repeat=d.get("repeat", False),
            repeat_count=d.get("repeat_count", 1),
            speed=float(d.get("speed", 1.0)),
        )

class MacroRecorder:

    def __init__(self):
        self._recording = False
        self._actions: List[MacroAction] = []
        self._timing: List[int] = []
        self._last_timestamp: float = 0
        self._current_macro_name: str = ""

    def start_recording(self, name: str = "New Macro") -> None:
        self._recording = True
        self._actions = []
        self._timing = []
        self._last_timestamp = time.time()
        self._current_macro_name = name

    def stop_recording(self) -> Optional[Macro]:
        if not self._recording:
            return None

        self._recording = False

        if not self._actions:
            return None

        return Macro(
            name=self._current_macro_name,
            trigger="",
            actions=self._actions.copy(),
            timing=self._timing.copy(),
        )

    def record_action(self, action_type: MacroActionType, target: str) -> None:
        if not self._recording:
            return

        current_time = time.time()
        delay_ms = int((current_time - self._last_timestamp) * 1000)

        if delay_ms > 10:
            self._timing.append(delay_ms)

        self._actions.append(MacroAction(
            action_type=action_type,
            target=target,
            duration=0,
        ))

        self._last_timestamp = current_time

    def is_recording(self) -> bool:
        return self._recording

    def get_recorded_actions(self) -> List[MacroAction]:
        return self._actions.copy()

class MacroPlayer:

    def __init__(self):
        self._playing = False
        self._current_macro: Optional[Macro] = None
        self._current_index: int = 0
        self._repeat_count: int = 0

    def play(self, macro: Macro) -> None:
        self._current_macro = macro
        self._current_index = 0
        self._repeat_count = 0
        self._playing = True

    def stop(self) -> None:
        self._playing = False
        self._current_macro = None

    def get_next_action(self) -> Optional[MacroAction]:
        if not self._playing or not self._current_macro:
            return None

        if self._current_index >= len(self._current_macro.actions):
            if self._current_macro.repeat and self._repeat_count < self._current_macro.repeat_count:
                self._repeat_count += 1
                self._current_index = 0
            else:
                self._playing = False
                return None

        action = self._current_macro.actions[self._current_index]
        return action

    def advance(self) -> None:
        self._current_index += 1

    def get_delay(self) -> int:
        if not self._current_macro:
            return 0

        if self._current_index < len(self._current_macro.timing):
            speed = max(0.1, self._current_macro.speed)
            delay = int(self._current_macro.timing[self._current_index] / speed)
            return max(1, delay)

        return 0

    def is_playing(self) -> bool:
        return self._playing

class MacroManager:

    def __init__(self):
        self._macros: Dict[str, Macro] = {}
        self._recorder = MacroRecorder()
        self._player = MacroPlayer()
        self._trigger_capture_macro: Optional[str] = None
        self._trigger_capture_listeners: List[Callable[[str, str], None]] = []

    def get_macro_names(self) -> List[str]:
        return list(self._macros.keys())

    def get_macro(self, name: str) -> Optional[Macro]:
        return self._macros.get(name)

    def get_macro_by_trigger(self, trigger: str) -> Optional[Macro]:
        for macro in self._macros.values():
            if macro.trigger == trigger:
                return macro
        return None

    def add_macro(self, macro: Macro) -> None:
        self._macros[macro.name] = macro

    def remove_macro(self, name: str) -> bool:
        if name in self._macros:
            del self._macros[name]
            return True
        return False

    def start_recording(self, name: str = "New Macro") -> None:
        self._recorder.start_recording(name)

    def stop_recording(self) -> Optional[Macro]:
        macro = self._recorder.stop_recording()
        if macro:
            self._macros[macro.name] = macro
        return macro

    def start_trigger_capture(self, macro_name: str) -> bool:
        if macro_name not in self._macros:
            return False
        self._trigger_capture_macro = macro_name
        return True

    def stop_trigger_capture(self) -> None:
        self._trigger_capture_macro = None

    def get_trigger_capture_macro(self) -> Optional[str]:
        return self._trigger_capture_macro

    def is_trigger_capturing(self) -> bool:
        return self._trigger_capture_macro is not None

    def set_capture_trigger(self, trigger: str) -> bool:
        if not self._trigger_capture_macro:
            return False
        macro = self._macros.get(self._trigger_capture_macro)
        if not macro:
            return False
        macro.trigger = trigger
        self._trigger_capture_macro = None
        self.save_to_file()
        for callback in self._trigger_capture_listeners:
            callback(macro.name, trigger)
        return True

    def register_trigger_capture_listener(self, callback: Callable[[str, str], None]) -> None:
        self._trigger_capture_listeners.append(callback)

    def play_macro(self, macro: Macro) -> None:
        self._player.play(macro)

    def play_macro_by_trigger(self, trigger: str) -> bool:
        macro = self.get_macro_by_trigger(trigger)
        if not macro:
            return False
        self.play_macro(macro)
        return True

    def stop_playback(self) -> None:
        self._player.stop()

    def record_action(self, action_type: MacroActionType, target: str) -> None:
        if self._recorder.is_recording():
            self._recorder.record_action(action_type, target)

    def is_recording(self) -> bool:
        return self._recorder.is_recording()

    def is_playing(self) -> bool:
        return self._player.is_playing()

    def save_to_file(self, filepath: Optional[str] = None) -> bool:
        if filepath is None:
            filepath = os.path.join(PROFILES_DIR, "macros.json")

        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            data = {name: macro.to_dict() for name, macro in self._macros.items()}
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            print(f"[MacroManager] Error saving: {e}")
            return False

    def load_from_file(self, filepath: Optional[str] = None) -> bool:
        if filepath is None:
            filepath = os.path.join(PROFILES_DIR, "macros.json")

        try:
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    data = json.load(f)
                self._macros = {
                    name: Macro.from_dict(macro_data)
                    for name, macro_data in data.items()
                }
                return True
            return False
        except Exception as e:
            print(f"[MacroManager] Error loading: {e}")
            return False

macro_manager = MacroManager()
