import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtWidgets import QApplication, QWidget
import sys

_app = None

@pytest.fixture(scope="session", autouse=True)
def qapp():
    global _app
    if _app is None:
        _app = QApplication([])
    return _app

def test_labeled_slider_creation():
    from nocrosshair.ui.widgets import LabeledSlider

    slider = LabeledSlider("Test", 0, 100, 50)
    assert slider.value() == 50
    assert slider.slider.minimum() == 0
    assert slider.slider.maximum() == 100

def test_labeled_slider_change():
    from nocrosshair.ui.widgets import LabeledSlider

    slider = LabeledSlider("Test", 0, 100, 50)
    slider.setValue(75)
    assert slider.value() == 75

def test_labeled_double_slider_creation():
    from nocrosshair.ui.widgets import LabeledDoubleSlider

    slider = LabeledDoubleSlider("Test", 0.0, 1.0, 0.5)
    assert abs(slider.value() - 0.5) < 0.01

def test_labeled_double_slider_change():
    from nocrosshair.ui.widgets import LabeledDoubleSlider

    slider = LabeledDoubleSlider("Test", 0.0, 1.0, 0.5)
    slider.setValue(0.75)
    assert abs(slider.value() - 0.75) < 0.01

def test_stick_visualizer():
    from nocrosshair.ui.widgets import StickVisualizerWidget

    visualizer = StickVisualizerWidget("Test Stick")
    visualizer.set_position(16384, 16384)
    assert visualizer.stick_x == 16384
    assert visualizer.stick_y == 16384

def test_response_curve_widget():
    from nocrosshair.ui.widgets import ResponseCurveWidget

    widget = ResponseCurveWidget()
    widget.set_params(1.5, 0.1, 0.9, 0.2)
    assert widget.accel == 1.5
    assert widget.defl_min == 0.1
    assert widget.defl_max == 0.9
    assert widget.init_spd == 0.2

def test_color_picker_button():
    from nocrosshair.ui.widgets import ColorPickerButton

    button = ColorPickerButton("#00ff88")
    assert button.color() == "#00ff88"

    button.setColor("#ffffff")
    assert button.color() == "#ffffff"

def test_preset_selector():
    from nocrosshair.ui.widgets import PresetSelector

    selector = PresetSelector("Test", ["Option1", "Option2", "Option3"])
    assert selector.currentPreset() in ["Option1", "Option2", "Option3", "Custom"]

def test_key_binding_table():
    from nocrosshair.ui.widgets import KeyBindingTable

    table = KeyBindingTable()
    table.add_binding("BTN_A", "KEY_SPACE", "Normal")
    assert table.rowCount() == 1

def test_crosshair_tab():
    from nocrosshair.ui.tabs.crosshair_tab import CrosshairTab

    tab = CrosshairTab()
    config = tab.get_config()
    assert "style" in config
    assert "color" in config
    assert "size" in config

def test_physics_tab():
    from nocrosshair.ui.tabs.physics_tab import PhysicsTab

    tab = PhysicsTab()
    assert tab is not None

def test_remapping_tab():
    from nocrosshair.ui.tabs.remapping_tab import RemappingTab

    tab = RemappingTab()
    config = tab.get_config()
    assert "bindings" in config or "mouse_sens" in config

def test_aa_tab():
    from nocrosshair.ui.tabs.aa_tab import AimAssistTab

    tab = AimAssistTab()
    assert tab is not None

def test_recoil_tab():
    from nocrosshair.ui.tabs.recoil_tab import RecoilTab

    tab = RecoilTab()
    assert tab is not None

def test_profiles_tab():
    from nocrosshair.ui.tabs.profiles_tab import ProfilesTab

    tab = ProfilesTab()
    assert tab is not None

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
