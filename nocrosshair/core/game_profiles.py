#!/usr/bin/env python3

import os
import json
import subprocess
import threading
import time
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict

from nocrosshair.core.config import (
    AimAssistConfig, StickPhysicsConfig, RecoilConfig, PROFILES_DIR
)
from nocrosshair.features.aim_assist import PredictiveAAConfig


GAME_MAP: Dict[str, str] = {
    "pubg": "TslGame",
    "cs2": "cs2",
    "fortnite": "FortniteClient-Win64-Shipping",
    "valorant": "VALORANT-Win64-Shipping",
    "r5apex": "r5apex",
    "cod": "cod",
    "overwatch": "Overwatch",
}


@dataclass
class GameProfile:
    game_name: str
    process_name: str
    aa_config: Optional[AimAssistConfig] = None
    physics_config: Optional[StickPhysicsConfig] = None
    recoil_config: Optional[RecoilConfig] = None
    predictive_config: Optional[PredictiveAAConfig] = None
    auto_activate: bool = True

    def __post_init__(self):
        if self.aa_config is None:
            self.aa_config = AimAssistConfig()
        if self.physics_config is None:
            self.physics_config = StickPhysicsConfig()
        if self.recoil_config is None:
            self.recoil_config = RecoilConfig()
        if self.predictive_config is None:
            self.predictive_config = PredictiveAAConfig()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "game_name": self.game_name,
            "process_name": self.process_name,
            "aa_config": asdict(self.aa_config) if self.aa_config else None,
            "physics_config": asdict(self.physics_config) if self.physics_config else None,
            "recoil_config": asdict(self.recoil_config) if self.recoil_config else None,
            "predictive_config": asdict(self.predictive_config) if self.predictive_config else None,
            "auto_activate": self.auto_activate,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "GameProfile":
        aa_config = None
        if d.get("aa_config"):
            aa_config = AimAssistConfig(**d["aa_config"])

        physics_config = None
        if d.get("physics_config"):
            physics_config = StickPhysicsConfig(**d["physics_config"])

        recoil_config = None
        if d.get("recoil_config"):
            recoil_config = RecoilConfig(**d["recoil_config"])

        predictive_config = None
        if d.get("predictive_config"):
            predictive_config = PredictiveAAConfig(**d["predictive_config"])

        return GameProfile(
            game_name=d.get("game_name", "Unknown"),
            process_name=d.get("process_name", ""),
            aa_config=aa_config,
            physics_config=physics_config,
            recoil_config=recoil_config,
            predictive_config=predictive_config,
            auto_activate=d.get("auto_activate", True),
        )


class GameDetector:
    """Polls running processes and auto-applies game profiles."""

    def __init__(self, game_profile_manager: "GameProfileManager"):
        self._gpm = game_profile_manager
        self._poll_interval = 5.0
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_detected: Optional[str] = None
        self._callbacks: List[Callable[[Optional[str]], None]] = []
        self._game_map = dict(GAME_MAP)

    def set_game_map(self, game_map: Dict[str, str]) -> None:
        self._game_map = dict(game_map)

    def get_game_map(self) -> Dict[str, str]:
        return dict(self._game_map)

    def on_game_detected(self, callback: Callable[[Optional[str]], None]) -> None:
        self._callbacks.append(callback)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
            self._thread = None

    def _poll_loop(self) -> None:
        while self._running:
            detected = self._detect_game()
            if detected != self._last_detected:
                self._last_detected = detected
                self._apply_profile(detected)
                for cb in self._callbacks:
                    try:
                        cb(detected)
                    except Exception:
                        pass
            time.sleep(self._poll_interval)

    def _detect_game(self) -> Optional[str]:
        try:
            result = subprocess.run(
                ["ps", "aux"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            output = result.stdout.lower()
            for game_key, process_name in self._game_map.items():
                if process_name.lower() in output:
                    return game_key
        except Exception:
            pass
        return None

    def _apply_profile(self, game_key: Optional[str]) -> None:
        if game_key is None:
            return

        for profile_name, profile in self._gpm._profiles.items():
            if profile.process_name.lower() == self._game_map.get(game_key, "").lower():
                if profile.auto_activate:
                    self._gpm.set_active_profile(profile_name)
                    print(f"[GameDetector] Auto-activated profile: {profile_name}")
                    return

    def get_last_detected(self) -> Optional[str]:
        return self._last_detected

    def set_poll_interval(self, seconds: float) -> None:
        self._poll_interval = max(1.0, seconds)


class GameProfileManager:

    def __init__(self):
        self._profiles: Dict[str, GameProfile] = {}
        self._active_profile: Optional[str] = None
        self._detection_enabled = True
        self._detector = GameDetector(self)
        self._load_default_profiles()

    @property
    def detector(self) -> GameDetector:
        return self._detector

    def _load_default_profiles(self) -> None:
        default_games = [
            ("Fortnite", "FortniteClient-Win64-Shipping"),
            ("Call of Duty", "cod.exe"),
            ("Apex Legends", "r5apex.exe"),
            ("Valorant", "VALORANT-Win64-Shipping"),
            ("Overwatch", "Overwatch.exe"),
            ("CS2", "cs2.exe"),
        ]

        for game_name, process_name in default_games:
            self._profiles[game_name] = GameProfile(
                game_name=game_name,
                process_name=process_name,
            )

    def get_profile_names(self) -> List[str]:
        return list(self._profiles.keys())

    def get_profile(self, game_name: str) -> Optional[GameProfile]:
        return self._profiles.get(game_name)

    def add_profile(self, profile: GameProfile) -> None:
        self._profiles[profile.game_name] = profile

    def remove_profile(self, game_name: str) -> bool:
        if game_name in self._profiles:
            del self._profiles[game_name]
            return True
        return False

    def get_active_profile(self) -> Optional[GameProfile]:
        if self._active_profile:
            return self._profiles.get(self._active_profile)
        return None

    def set_active_profile(self, game_name: str) -> bool:
        if game_name in self._profiles:
            self._active_profile = game_name
            return True
        return False

    def detect_running_games(self) -> List[str]:
        running_games = []

        try:
            result = subprocess.run(
                ["ps", "aux"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            for line in result.stdout.split('\n'):
                for game_name, profile in self._profiles.items():
                    if profile.process_name.lower() in line.lower():
                        running_games.append(game_name)
        except Exception:
            pass

        return running_games

    def auto_detect_and_activate(self) -> Optional[str]:
        if not self._detection_enabled:
            return None

        running_games = self.detect_running_games()

        for game_name in running_games:
            profile = self._profiles.get(game_name)
            if profile and profile.auto_activate:
                self._active_profile = game_name
                return game_name

        return None

    def start_detection(self) -> None:
        self._detector.start()

    def stop_detection(self) -> None:
        self._detector.stop()

    def save_to_file(self, filepath: Optional[str] = None) -> bool:
        if filepath is None:
            filepath = os.path.join(PROFILES_DIR, "game_profiles.json")

        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            data = {name: profile.to_dict() for name, profile in self._profiles.items()}
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            print(f"[GameProfileManager] Error saving: {e}")
            return False

    def load_from_file(self, filepath: Optional[str] = None) -> bool:
        if filepath is None:
            filepath = os.path.join(PROFILES_DIR, "game_profiles.json")

        try:
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    data = json.load(f)
                self._profiles = {
                    name: GameProfile.from_dict(profile_data)
                    for name, profile_data in data.items()
                }
                return True
            return False
        except Exception as e:
            print(f"[GameProfileManager] Error loading: {e}")
            return False

    def enable_detection(self, enabled: bool) -> None:
        self._detection_enabled = enabled

    def is_detection_enabled(self) -> bool:
        return self._detection_enabled


game_profile_manager = GameProfileManager()
