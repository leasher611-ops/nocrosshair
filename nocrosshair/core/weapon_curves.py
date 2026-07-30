#!/usr/bin/env python3

import json
import os
import math
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import asdict

from nocrosshair.core.config import PROFILES_DIR

class WeaponCurvesManager:

    def __init__(self):
        self._weapon_curves: Dict[str, Dict[str, Any]] = {}
        self._current_weapon: str = "Default"
        self._load_presets()

    def _load_presets(self) -> None:
        self._weapon_curves = {
            "Default": {
                "curve_x": [(0.0, 0.0), (0.25, 0.25), (0.5, 0.5), (0.75, 0.75), (1.0, 1.0)],
                "curve_y": [(0.0, 0.0), (0.25, 0.25), (0.5, 0.5), (0.75, 0.75), (1.0, 1.0)],
                "acceleration": 1.0,
                "deadzone": 0.0,
            },
            "AR": {
                "curve_x": [(0.0, 0.0), (0.3, 0.2), (0.6, 0.7), (1.0, 1.0)],
                "curve_y": [(0.0, 0.0), (0.2, 0.15), (0.5, 0.6), (1.0, 1.0)],
                "acceleration": 1.2,
                "deadzone": 0.05,
            },
            "SMG": {
                "curve_x": [(0.0, 0.0), (0.4, 0.3), (0.7, 0.8), (1.0, 1.0)],
                "curve_y": [(0.0, 0.0), (0.3, 0.25), (0.6, 0.75), (1.0, 1.0)],
                "acceleration": 1.4,
                "deadzone": 0.03,
            },
            "Shotgun": {
                "curve_x": [(0.0, 0.0), (0.5, 0.4), (0.8, 0.9), (1.0, 1.0)],
                "curve_y": [(0.0, 0.0), (0.4, 0.35), (0.7, 0.85), (1.0, 1.0)],
                "acceleration": 1.1,
                "deadzone": 0.08,
            },
            "Sniper": {
                "curve_x": [(0.0, 0.0), (0.2, 0.1), (0.4, 0.3), (0.6, 0.6), (0.8, 0.9), (1.0, 1.0)],
                "curve_y": [(0.0, 0.0), (0.15, 0.08), (0.35, 0.25), (0.55, 0.55), (0.75, 0.88), (1.0, 1.0)],
                "acceleration": 0.9,
                "deadzone": 0.1,
            },
            "Pistol": {
                "curve_x": [(0.0, 0.0), (0.35, 0.25), (0.65, 0.75), (1.0, 1.0)],
                "curve_y": [(0.0, 0.0), (0.25, 0.2), (0.55, 0.7), (1.0, 1.0)],
                "acceleration": 1.3,
                "deadzone": 0.04,
            },
            "LMG": {
                "curve_x": [(0.0, 0.0), (0.25, 0.18), (0.55, 0.65), (0.85, 0.95), (1.0, 1.0)],
                "curve_y": [(0.0, 0.0), (0.2, 0.15), (0.5, 0.6), (0.8, 0.92), (1.0, 1.0)],
                "acceleration": 1.15,
                "deadzone": 0.06,
            },
        }

    def get_weapon_names(self) -> List[str]:
        return list(self._weapon_curves.keys())

    def get_weapon_curve(self, weapon: str) -> Dict[str, Any]:
        return self._weapon_curves.get(weapon, self._weapon_curves["Default"])

    def set_weapon_curve(self, weapon: str, curve_data: Dict[str, Any]) -> None:
        self._weapon_curves[weapon] = curve_data

    def get_current_weapon(self) -> str:
        return self._current_weapon

    def set_current_weapon(self, weapon: str) -> None:
        if weapon in self._weapon_curves:
            self._current_weapon = weapon

    def apply_curve_to_input(self, input_value: float, curve_points: List[Tuple[float, float]], power: float = 1.0) -> float:
        if not curve_points or len(curve_points) < 2:
            return input_value ** power

        abs_input = abs(input_value)
        sign = 1.0 if input_value >= 0 else -1.0
        
        # Aplicação de curva por pontos (Linear Interpolation com Deadzone)
        output = 0.0
        found = False
        for i in range(len(curve_points) - 1):
            x0, y0 = curve_points[i]
            x1, y1 = curve_points[i + 1]

            if x0 <= abs_input <= x1:
                if x1 - x0 == 0:
                    output = y0
                else:
                    t = (abs_input - x0) / (x1 - x0)
                    output = y0 + t * (y1 - y0)
                found = True
                break
        
        if not found:
            output = curve_points[-1][1] if abs_input >= curve_points[-1][0] else abs_input

        # Aplicação de Curva de Potência Adicional (Estilo reWASD)
        if power != 1.0:
            output = output ** power
            
        return output * sign

    def save_to_file(self, filepath: Optional[str] = None) -> bool:
        if filepath is None:
            filepath = os.path.join(PROFILES_DIR, "weapon_curves.json")

        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w') as f:
                json.dump(self._weapon_curves, f, indent=2)
            return True
        except Exception as e:
            print(f"[WeaponCurvesManager] Error saving: {e}")
            return False

    def load_from_file(self, filepath: Optional[str] = None) -> bool:
        if filepath is None:
            filepath = os.path.join(PROFILES_DIR, "weapon_curves.json")

        try:
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    self._weapon_curves = json.load(f)
                return True
            return False
        except Exception as e:
            print(f"[WeaponCurvesManager] Error loading: {e}")
            return False

    def get_all_curves(self) -> Dict[str, Dict[str, Any]]:
        return dict(self._weapon_curves)

    def add_weapon(self, name: str, base_weapon: str = "Default") -> None:
        if name not in self._weapon_curves:
            base_curve = self.get_weapon_curve(base_weapon)
            self._weapon_curves[name] = dict(base_curve)

    def remove_weapon(self, name: str) -> bool:
        if name != "Default" and name in self._weapon_curves:
            del self._weapon_curves[name]
            return True
        return False

weapon_curves_manager = WeaponCurvesManager()
