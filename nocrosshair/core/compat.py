#!/usr/bin/env python3

import json
import os
from typing import Dict, Any, Optional

from nocrosshair.core.config import CONFIG_PATH, DEFAULT_CONFIG
from nocrosshair.core.profile_manager import Profile

class CompatibilityAdapter:

    @staticmethod
    def load_legacy_config() -> Optional[Dict[str, Any]]:
        if not os.path.exists(CONFIG_PATH):
            return None

        try:
            with open(CONFIG_PATH, "r") as f:
                return json.load(f)
        except Exception:
            return None

    @staticmethod
    def migrate_to_profile(legacy_cfg: Dict[str, Any]) -> Profile:
        profile = Profile(name="Migrated Config")

        crosshair_keys = [
            "style", "color", "size", "thick", "gap", "alpha",
            "outline", "offset_x", "offset_y", "visible"
        ]
        crosshair_cfg = {k: legacy_cfg.get(k) for k in crosshair_keys if k in legacy_cfg}

        physics_keys = [k for k in legacy_cfg.keys() if k.startswith("ls_") or k.startswith("rs_")]
        physics_cfg = {k: legacy_cfg.get(k) for k in physics_keys}

        aa_keys = [k for k in legacy_cfg.keys() if k.startswith("aa_") or k.startswith("remap_aa_")]
        aa_cfg = {k: legacy_cfg.get(k) for k in aa_keys}

        recoil_keys = [k for k in legacy_cfg.keys() if k.startswith("recoil_")]
        recoil_cfg = {k: legacy_cfg.get(k) for k in recoil_keys}

        profile.physics = {**crosshair_cfg, **physics_cfg}
        profile.aiming = aa_cfg
        profile.recoil = recoil_cfg

        return profile

    @staticmethod
    def needs_migration(legacy_cfg: Dict[str, Any]) -> bool:
        has_old_keys = any(k in legacy_cfg for k in ["remap_aa_enabled", "recoil_enabled"])
        has_new_keys = "profiles" in legacy_cfg or "shift_layers" in legacy_cfg
        return has_old_keys and not has_new_keys
