import json
import os
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, asdict

from nocrosshair.core.config import PROFILES_DIR

@dataclass
class ShiftLayer:
    name: str
    trigger: str
    mappings: Dict[str, str]
    nested_layers: List[str]
    color: str = "#00ff88"
    enabled: bool = True

    def __post_init__(self):
        if self.mappings is None:
            self.mappings = {}
        if self.nested_layers is None:
            self.nested_layers = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "trigger": self.trigger,
            "mappings": self.mappings,
            "nested_layers": self.nested_layers,
            "color": self.color,
            "enabled": self.enabled,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "ShiftLayer":
        return ShiftLayer(
            name=d.get("name", "Unnamed"),
            trigger=d.get("trigger", ""),
            mappings=d.get("mappings", {}),
            nested_layers=d.get("nested_layers", []),
            color=d.get("color", "#00ff88"),
            enabled=d.get("enabled", True),
        )

class ShiftLayerManager:

    def __init__(self):
        self._layers: Dict[str, ShiftLayer] = {}
        self._active_layers: Set[str] = set()
        self._trigger_map: Dict[str, str] = {}
        self._create_default_layers()
        self._rebuild_trigger_map()

    def _create_default_layers(self) -> None:
        self._layers["Main"] = ShiftLayer(
            name="Main",
            trigger="",
            mappings={},
            nested_layers=[],
            color="#00ff88"
        )

        self._layers["Shift 1"] = ShiftLayer(
            name="Shift 1",
            trigger="BTN_LB",
            mappings={},
            nested_layers=[],
            color="#ffcc00"
        )

        self._layers["Shift 2"] = ShiftLayer(
            name="Shift 2",
            trigger="BTN_RB",
            mappings={},
            nested_layers=[],
            color="#ff6666"
        )

    def _rebuild_trigger_map(self) -> None:
        self._trigger_map = {
            layer.trigger: name
            for name, layer in self._layers.items()
            if layer.trigger
        }

    def get_layer_names(self) -> List[str]:
        return list(self._layers.keys())

    def get_layer(self, name: str) -> Optional[ShiftLayer]:
        return self._layers.get(name)

    def add_layer(self, layer: ShiftLayer) -> None:
        self._layers[layer.name] = layer
        self._rebuild_trigger_map()

    def remove_layer(self, name: str) -> bool:
        if name != "Main" and name in self._layers:
            del self._layers[name]
            self._rebuild_trigger_map()
            return True
        return False

    def activate_layer(self, name: str) -> bool:
        if name in self._layers and self._layers[name].enabled:
            self._active_layers.add(name)
            return True
        return False

    def deactivate_layer(self, name: str) -> bool:
        if name in self._active_layers:
            self._active_layers.discard(name)
            return True
        return False

    def get_active_layers(self) -> List[str]:
        return list(self._active_layers)

    def handle_button_press(self, button: str) -> Optional[str]:
        if button in self._trigger_map:
            layer_name = self._trigger_map[button]
            self.activate_layer(layer_name)
            return layer_name
        return None

    def handle_button_release(self, button: str) -> Optional[str]:
        if button in self._trigger_map:
            layer_name = self._trigger_map[button]
            self.deactivate_layer(layer_name)
            return layer_name
        return None

    def get_mapping(self, button: str) -> Optional[str]:
        for layer_name in reversed(list(self._active_layers)):
            layer = self._layers.get(layer_name)
            if layer and button in layer.mappings:
                return layer.mappings[button]

        main_layer = self._layers.get("Main")
        if main_layer and button in main_layer.mappings:
            return main_layer.mappings[button]

        return None

    def set_mapping(self, layer_name: str, button: str, mapping: str) -> None:
        if layer_name in self._layers:
            self._layers[layer_name].mappings[button] = mapping

    def clear_mapping(self, layer_name: str, button: str) -> None:
        if layer_name in self._layers and button in self._layers[layer_name].mappings:
            del self._layers[layer_name].mappings[button]

    def get_all_mappings(self) -> Dict[str, Dict[str, str]]:
        return {name: layer.mappings.copy() for name, layer in self._layers.items()}

    def save_to_file(self, filepath: Optional[str] = None) -> bool:
        if filepath is None:
            filepath = os.path.join(PROFILES_DIR, "shift_layers.json")

        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            data = {name: layer.to_dict() for name, layer in self._layers.items()}
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            print(f"[ShiftLayerManager] Error saving: {e}")
            return False

    def load_from_file(self, filepath: Optional[str] = None) -> bool:
        if filepath is None:
            filepath = os.path.join(PROFILES_DIR, "shift_layers.json")

        try:
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    data = json.load(f)
                self._layers = {
                    name: ShiftLayer.from_dict(layer_data)
                    for name, layer_data in data.items()
                }
                self._rebuild_trigger_map()
                return True
            return False
        except Exception as e:
            print(f"[ShiftLayerManager] Error loading: {e}")
            return False

    def enable_layer(self, name: str, enabled: bool) -> None:
        if name in self._layers:
            self._layers[name].enabled = enabled
            if not enabled:
                self.deactivate_layer(name)

    def is_layer_enabled(self, name: str) -> bool:
        return self._layers.get(name, ShiftLayer("", "", {}, [])).enabled

shift_layer_manager = ShiftLayerManager()
