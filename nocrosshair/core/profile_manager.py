#!/usr/bin/env python3

import json
import os
import threading
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime

from nocrosshair.core.config import (
    CONFIG_DIR, PROFILES_DIR, SLOTS_PATH, DEFAULT_CONFIG,
    ConfigValidator
)

@dataclass
class Profile:
    name: str
    description: str = ""
    controller_type: str = "xbox360"
    key_map: Dict[str, Any] = None
    mouse_map: Dict[str, Any] = None
    shift_layers: Dict[str, Any] = None
    macros: Dict[str, Any] = None
    crosshair: Dict[str, Any] = None
    remapping: Dict[str, Any] = None
    aiming: Dict[str, Any] = None
    recoil: Dict[str, Any] = None
    physics: Dict[str, Any] = None
    created_at: str = ""
    modified_at: str = ""

    def __post_init__(self):
        if self.key_map is None:
            self.key_map = {}
        if self.mouse_map is None:
            self.mouse_map = {}
        if self.shift_layers is None:
            self.shift_layers = {}
        if self.macros is None:
            self.macros = {}
        if self.crosshair is None:
            self.crosshair = {}
        if self.remapping is None:
            self.remapping = {}
        if self.aiming is None:
            self.aiming = {}
        if self.recoil is None:
            self.recoil = {}
        if self.physics is None:
            self.physics = {}
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.modified_at:
            self.modified_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Profile":
        return Profile(
            name=d.get("name", "Untitled"),
            description=d.get("description", ""),
            controller_type=d.get("controller_type", "xbox360"),
            key_map=d.get("key_map", {}),
            mouse_map=d.get("mouse_map", {}),
            shift_layers=d.get("shift_layers", {}),
            macros=d.get("macros", {}),
            crosshair=d.get("crosshair", {}),
            remapping=d.get("remapping", {}),
            aiming=d.get("aiming", {}),
            recoil=d.get("recoil", {}),
            physics=d.get("physics", {}),
            created_at=d.get("created_at", datetime.now().isoformat()),
            modified_at=d.get("modified_at", datetime.now().isoformat()),
        )

class ProfileManager:

    def __init__(self):
        self._lock = threading.Lock()
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        os.makedirs(PROFILES_DIR, exist_ok=True)

    def _profile_path(self, name: str) -> str:
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
        return os.path.join(PROFILES_DIR, f"{safe_name}.json")

    def profile_exists(self, name: str) -> bool:
        return os.path.exists(self._profile_path(name))

    def save_profile(self, profile: Profile) -> bool:
        try:
            profile.modified_at = datetime.now().isoformat()
            path = self._profile_path(profile.name)

            with self._lock:
                with open(path, "w") as f:
                    json.dump(profile.to_dict(), f, indent=2)

            return True
        except Exception as e:
            print(f"[ProfileManager] Error saving profile: {e}")
            return False

    def load_profile(self, name: str) -> Optional[Profile]:
        try:
            path = self._profile_path(name)

            if not os.path.exists(path):
                return None

            with self._lock:
                with open(path, "r") as f:
                    data = json.load(f)

            return Profile.from_dict(data)
        except Exception as e:
            print(f"[ProfileManager] Error loading profile: {e}")
            return None

    def delete_profile(self, name: str) -> bool:
        try:
            path = self._profile_path(name)

            if os.path.exists(path):
                with self._lock:
                    os.remove(path)

            return True
        except Exception as e:
            print(f"[ProfileManager] Error deleting profile: {e}")
            return False

    def list_profiles(self) -> List[str]:
        try:
            if not os.path.exists(PROFILES_DIR):
                return []

            with self._lock:
                files = os.listdir(PROFILES_DIR)

            profiles = []
            for f in files:
                if f.endswith(".json"):
                    path = os.path.join(PROFILES_DIR, f)
                    try:
                        with open(path, "r") as profile_file:
                            data = json.load(profile_file)
                        profiles.append(data.get("name", f[:-5]))
                    except Exception:
                        profiles.append(f[:-5])

            return sorted(profiles)
        except Exception:
            return []

    def export_profile(self, name: str, export_path: str) -> bool:
        try:
            profile = self.load_profile(name)
            if not profile:
                return False

            with self._lock:
                with open(export_path, "w") as f:
                    json.dump(profile.to_dict(), f, indent=2)

            return True
        except Exception as e:
            print(f"[ProfileManager] Error exporting profile: {e}")
            return False

    def import_profile(self, import_path: str, new_name: str) -> bool:
        try:
            with self._lock:
                with open(import_path, "r") as f:
                    data = json.load(f)

            profile = Profile.from_dict(data)
            profile.name = new_name
            profile.created_at = datetime.now().isoformat()
            errors = self.validate_profile(profile)
            if errors:
                print(f"[ProfileManager] Invalid imported profile: {'; '.join(errors)}")
                return False

            return self.save_profile(profile)
        except Exception as e:
            print(f"[ProfileManager] Error importing profile: {e}")
            return False

    def validate_profile(self, profile: Profile) -> List[str]:
        errors = []

        if not profile.name or len(profile.name) == 0:
            errors.append("Profile name cannot be empty")

        if not ConfigValidator.validate_controller_type(profile.controller_type):
            errors.append(f"Invalid controller type: {profile.controller_type}")

        return errors

    def merge_with_default(self, profile_dict: Dict[str, Any]) -> Dict[str, Any]:
        merged = dict(DEFAULT_CONFIG)

        for key in ["style", "color", "size", "thick", "gap", "alpha", "outline",
                    "offset_x", "offset_y", "visible", "remap_controller", "remap_active"]:
            if key in profile_dict:
                merged[key] = profile_dict[key]

        return merged

class SlotManager:

    def __init__(self):
        self.current_slot = 1
        self.slots: Dict[int, Optional[str]] = {1: None, 2: None, 3: None, 4: None}
        self._lock = threading.Lock()
        self.load()

    def load(self) -> None:
        try:
            if os.path.exists(SLOTS_PATH):
                with self._lock:
                    with open(SLOTS_PATH, "r") as f:
                        data = json.load(f)
                        self.current_slot = data.get("current_slot", 1)
                        for k, v in data.get("slots", {}).items():
                            self.slots[int(k)] = v
        except Exception:
            pass

    def save(self) -> None:
        try:
            with self._lock:
                with open(SLOTS_PATH, "w") as f:
                    json.dump(
                        {"current_slot": self.current_slot, "slots": self.slots},
                        f,
                        indent=2
                    )
        except Exception:
            pass

    def assign(self, slot: int, profile_name: Optional[str]) -> bool:
        if not (1 <= slot <= 4):
            return False

        with self._lock:
            self.slots[slot] = profile_name

        self.save()
        return True

    def get_slot(self, slot: int) -> Optional[str]:
        if not (1 <= slot <= 4):
            return None

        with self._lock:
            return self.slots.get(slot)

    def cycle_slot(self) -> int:
        with self._lock:
            self.current_slot = self.current_slot + 1
            if self.current_slot > 4:
                self.current_slot = 1

        self.save()
        return self.current_slot

    def get_current_profile(self) -> Optional[str]:
        with self._lock:
            return self.slots.get(self.current_slot)
