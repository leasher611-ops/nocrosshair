import os
import json
import tempfile
import math
import pytest

from nocrosshair.core.shift_layers import ShiftLayer, ShiftLayerManager
from nocrosshair.core.plugins import PluginHooks, PluginInfo, PluginManager, NocrosshairPlugin
from nocrosshair.core.weapon_curves import WeaponCurvesManager
from nocrosshair.core.remapper import InputRemapper, RemapPipeline, DEFAULT_KBD_BINDINGS, ACTION_MAP


class TestShiftLayer:
    def test_creation(self):
        layer = ShiftLayer(name="Test", trigger="BTN_LB", mappings={"KEY_W": "ABS_Y"}, nested_layers=[])
        assert layer.name == "Test"
        assert layer.trigger == "BTN_LB"
        assert layer.mappings == {"KEY_W": "ABS_Y"}
        assert layer.color == "#00ff88"

    def test_defaults(self):
        layer = ShiftLayer(name="Test", trigger="", mappings={}, nested_layers=[])
        assert layer.enabled is True
        assert layer.nested_layers == []

    def test_to_dict(self):
        layer = ShiftLayer(name="Test", trigger="BTN_LB", mappings={"KEY_W": "ABS_Y"}, nested_layers=[], color="#ff0000")
        d = layer.to_dict()
        assert d["name"] == "Test"
        assert d["color"] == "#ff0000"

    def test_from_dict(self):
        d = {"name": "Test", "trigger": "BTN_LB", "mappings": {"KEY_W": "ABS_Y"}, "color": "#ff0000"}
        layer = ShiftLayer.from_dict(d)
        assert layer.name == "Test"
        assert layer.trigger == "BTN_LB"
        assert layer.color == "#ff0000"


class TestShiftLayerManager:
    def test_default_layers(self):
        mgr = ShiftLayerManager()
        names = mgr.get_layer_names()
        assert "Main" in names
        assert "Shift 1" in names
        assert "Shift 2" in names

    def test_add_remove_layer(self):
        mgr = ShiftLayerManager()
        layer = ShiftLayer(name="Custom", trigger="BTN_X", mappings={}, nested_layers=[])
        mgr.add_layer(layer)
        assert mgr.get_layer("Custom") is not None
        assert mgr.remove_layer("Custom") is True
        assert mgr.get_layer("Custom") is None

    def test_remove_main_protected(self):
        mgr = ShiftLayerManager()
        assert mgr.remove_layer("Main") is False

    def test_activate_deactivate(self):
        mgr = ShiftLayerManager()
        assert mgr.activate_layer("Shift 1") is True
        assert "Shift 1" in mgr.get_active_layers()
        assert mgr.deactivate_layer("Shift 1") is True
        assert "Shift 1" not in mgr.get_active_layers()

    def test_activate_nonexistent(self):
        mgr = ShiftLayerManager()
        assert mgr.activate_layer("Nope") is False

    def test_trigger_bindings(self):
        mgr = ShiftLayerManager()
        assert mgr.handle_button_press("BTN_LB") == "Shift 1"
        assert "Shift 1" in mgr.get_active_layers()
        assert mgr.handle_button_release("BTN_LB") == "Shift 1"
        assert "Shift 1" not in mgr.get_active_layers()

    def test_trigger_unmapped_button(self):
        mgr = ShiftLayerManager()
        assert mgr.handle_button_press("KEY_SPACE") is None
        assert mgr.handle_button_release("KEY_SPACE") is None

    def test_mappings(self):
        mgr = ShiftLayerManager()
        mgr.set_mapping("Shift 1", "KEY_W", "ABS_RY")
        mgr.activate_layer("Shift 1")
        assert mgr.get_mapping("KEY_W") == "ABS_RY"

    def test_mapping_fallback_to_main(self):
        mgr = ShiftLayerManager()
        mgr.set_mapping("Main", "KEY_SPACE", "BTN_A")
        assert mgr.get_mapping("KEY_SPACE") == "BTN_A"

    def test_clear_mapping(self):
        mgr = ShiftLayerManager()
        mgr.set_mapping("Shift 1", "KEY_W", "ABS_RY")
        mgr.clear_mapping("Shift 1", "KEY_W")
        assert mgr.get_mapping("KEY_W") is None

    def test_get_all_mappings(self):
        mgr = ShiftLayerManager()
        mgr.set_mapping("Shift 1", "KEY_W", "ABS_RY")
        all_maps = mgr.get_all_mappings()
        assert "Shift 1" in all_maps
        assert all_maps["Shift 1"]["KEY_W"] == "ABS_RY"

    def test_enable_disable_layer(self):
        mgr = ShiftLayerManager()
        mgr.activate_layer("Shift 1")
        mgr.enable_layer("Shift 1", False)
        assert mgr.is_layer_enabled("Shift 1") is False
        assert "Shift 1" not in mgr.get_active_layers()

    def test_save_load(self):
        mgr = ShiftLayerManager()
        mgr.set_mapping("Shift 1", "KEY_W", "ABS_RY")
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            path = f.name
        try:
            assert mgr.save_to_file(path) is True
            mgr2 = ShiftLayerManager()
            assert mgr2.load_from_file(path) is True
            mgr2.activate_layer("Shift 1")
            assert mgr2.get_mapping("KEY_W") == "ABS_RY"
        finally:
            os.unlink(path)


class TestPluginHooks:
    def test_register_and_call(self):
        hooks = PluginHooks()
        results = []

        def my_cb(x):
            results.append(x)

        hooks.register("on_raw_input", my_cb)
        hooks.call("on_raw_input", 42)
        assert results == [42]

    def test_unregister(self):
        hooks = PluginHooks()

        def my_cb():
            pass

        hooks.register("on_raw_input", my_cb)
        assert hooks.get_registered()["on_raw_input"] == 1
        hooks.unregister("on_raw_input", my_cb)
        assert hooks.get_registered()["on_raw_input"] == 0

    def test_call_unknown_hook(self):
        hooks = PluginHooks()
        assert hooks.call("nonexistent") == []

    def test_callback_error_does_not_propagate(self):
        hooks = PluginHooks()

        def broken():
            raise ValueError("oops")

        hooks.register("on_button", broken)
        assert hooks.call("on_button") == []

    def test_clear(self):
        hooks = PluginHooks()

        def my_cb():
            pass

        hooks.register("on_raw_input", my_cb)
        hooks.clear()
        assert hooks.get_registered()["on_raw_input"] == 0

    def test_get_registered(self):
        hooks = PluginHooks()

        def cb():
            pass

        hooks.register("on_pre_write", cb)
        reg = hooks.get_registered()
        assert reg["on_pre_write"] == 1


class TestPluginInfo:
    def test_to_dict(self):
        info = PluginInfo(name="Test", version="1.0", author="Me",
                          description="Test plugin", enabled=True, path="/tmp")
        d = info.to_dict()
        assert d["name"] == "Test"
        assert d["version"] == "1.0"

    def test_from_dict(self):
        d = {"name": "Test", "version": "1.0", "author": "Me",
             "description": "Test", "enabled": True, "path": "/tmp"}
        info = PluginInfo.from_dict(d)
        assert info.name == "Test"
        assert info.path == "/tmp"

    def test_from_dict_missing_fields(self):
        info = PluginInfo.from_dict({})
        assert info.name == ""
        assert info.version == ""
        assert info.enabled is True


class TestPluginManager:
    def test_initial_state(self):
        pm = PluginManager()
        assert pm.get_loaded_plugins() == []
        assert pm.get_available_plugins() == []

    def test_add_plugin_dir(self):
        pm = PluginManager()
        pm.add_plugin_dir("/tmp/plugins")
        assert "/tmp/plugins" in pm._plugin_dirs

    def test_register_hook_and_call(self):
        pm = PluginManager()
        results = []

        def my_cb(val):
            results.append(val)

        pm.register_hook("on_button", my_cb)
        pm.call_hook("on_button", 99)
        assert results == [99]

    def test_enable_disable_plugin(self):
        pm = PluginManager()
        pm._plugin_info["test"] = PluginInfo(name="test", version="", author="",
                                              description="", enabled=False, path="")
        assert pm._plugin_info["test"].enabled is False
        pm.enable_plugin("test")
        assert pm._plugin_info["test"].enabled is True
        pm.disable_plugin("test")
        assert pm._plugin_info["test"].enabled is False

    def test_load_unload_nonexistent(self):
        pm = PluginManager()
        assert pm.load_plugin("nope") is False
        assert pm.unload_plugin("nope") is False

    def test_open_plugin_folder_default(self):
        pm = PluginManager()
        folder = pm.open_plugin_folder()
        assert folder.endswith("plugins")

    def test_save_load_config(self):
        pm = PluginManager()
        pm._plugin_info["test"] = PluginInfo(name="test", version="1.0", author="me",
                                              description="", enabled=True, path="")
        assert pm.save_config() is True
        pm2 = PluginManager()
        assert pm2.load_config() is True
        assert "test" in pm2._plugin_info


class TestWeaponCurvesManager:
    def test_default_weapons(self):
        mgr = WeaponCurvesManager()
        names = mgr.get_weapon_names()
        assert "Default" in names
        assert "AR" in names
        assert "SMG" in names

    def test_get_weapon_curve_default(self):
        mgr = WeaponCurvesManager()
        curve = mgr.get_weapon_curve("Nope")
        assert curve["curve_x"][0] == (0.0, 0.0)

    def test_set_get_current_weapon(self):
        mgr = WeaponCurvesManager()
        assert mgr.get_current_weapon() == "Default"
        mgr.set_current_weapon("AR")
        assert mgr.get_current_weapon() == "AR"
        mgr.set_current_weapon("Nope")
        assert mgr.get_current_weapon() == "AR"

    def test_set_weapon_curve(self):
        mgr = WeaponCurvesManager()
        mgr.set_weapon_curve("Custom", {"curve_x": [(0, 0), (1, 1)]})
        curve = mgr.get_weapon_curve("Custom")
        assert curve["curve_x"] == [(0, 0), (1, 1)]

    def test_apply_curve_to_input_linear(self):
        mgr = WeaponCurvesManager()
        curve = mgr.get_weapon_curve("Default")
        result = mgr.apply_curve_to_input(0.5, curve["curve_x"])
        assert abs(result - 0.5) < 0.001

    def test_apply_curve_to_input_ar(self):
        mgr = WeaponCurvesManager()
        curve = mgr.get_weapon_curve("AR")
        result = mgr.apply_curve_to_input(0.5, curve["curve_x"])
        assert abs(result - 0.53333) < 0.001

    def test_apply_curve_to_input_negative(self):
        mgr = WeaponCurvesManager()
        curve = mgr.get_weapon_curve("Default")
        result = mgr.apply_curve_to_input(-0.5, curve["curve_x"])
        assert result < 0
        assert abs(result) < 0.501

    def test_apply_curve_to_input_power(self):
        mgr = WeaponCurvesManager()
        curve = mgr.get_weapon_curve("Default")
        result = mgr.apply_curve_to_input(0.5, curve["curve_x"], power=2.0)
        assert abs(result - 0.25) < 0.001

    def test_apply_curve_empty_points(self):
        mgr = WeaponCurvesManager()
        result = mgr.apply_curve_to_input(0.5, [], power=2.0)
        assert abs(result - 0.25) < 0.001

    def test_apply_curve_out_of_range_above(self):
        mgr = WeaponCurvesManager()
        result = mgr.apply_curve_to_input(2.0, [(0, 0), (1, 1)])
        assert abs(result - 1.0) < 0.001

    def test_apply_curve_out_of_range_below(self):
        mgr = WeaponCurvesManager()
        result = mgr.apply_curve_to_input(-0.1, [(0.5, 0.5), (1, 1)])
        assert abs(result - (-0.1)) < 0.001

    def test_add_remove_weapon(self):
        mgr = WeaponCurvesManager()
        mgr.add_weapon("Custom")
        assert "Custom" in mgr.get_weapon_names()
        assert mgr.remove_weapon("Custom") is True
        assert "Custom" not in mgr.get_weapon_names()

    def test_remove_default_protected(self):
        mgr = WeaponCurvesManager()
        assert mgr.remove_weapon("Default") is False

    def test_get_all_curves(self):
        mgr = WeaponCurvesManager()
        all_c = mgr.get_all_curves()
        assert "Default" in all_c
        assert isinstance(all_c["Default"]["curve_x"], list)

    def test_save_load(self):
        mgr = WeaponCurvesManager()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            path = f.name
        try:
            assert mgr.save_to_file(path) is True
            mgr2 = WeaponCurvesManager()
            assert mgr2.load_from_file(path) is True
            assert "AR" in mgr2.get_weapon_names()
        finally:
            os.unlink(path)


class TestInputRemapper:
    def test_default_bindings(self):
        remapper = InputRemapper({})
        assert len(remapper.bindings) > 0

    def test_process_key_mapped(self):
        remapper = InputRemapper({"KEY_SPACE": "BTN_A"})
        action, value = remapper.process_key("KEY_SPACE", 1)
        assert action == "BTN_A"
        assert value == 1

    def test_process_key_unmapped(self):
        remapper = InputRemapper({})
        action, value = remapper.process_key("KEY_NONE", 1)
        assert action is None

    def test_process_key_min(self):
        remapper = InputRemapper({"KEY_A": "ABS_X_MIN"})
        action, value = remapper.process_key("KEY_A", 1)
        assert action == "ABS_X"
        assert value == -32767

    def test_process_key_max(self):
        remapper = InputRemapper({"KEY_D": "ABS_X_MAX"})
        action, value = remapper.process_key("KEY_D", 1)
        assert action == "ABS_X"
        assert value == 32767

    def test_process_key_min_release(self):
        remapper = InputRemapper({"KEY_A": "ABS_X_MIN"})
        action, value = remapper.process_key("KEY_A", 0)
        assert action == "ABS_X"
        assert value == 0

    def test_resolve_action(self):
        assert InputRemapper({}).resolve_action("BTN_A") == ACTION_MAP["BTN_A"]

    def test_resolve_action_unknown(self):
        assert InputRemapper({}).resolve_action("NOPE") is None

    def test_process_mouse_move_basic(self):
        remapper = InputRemapper({}, mouse_sens=80.0)
        rx, ry = remapper.process_mouse_move(10, 5, 8.0)
        assert abs(rx) > 0
        assert abs(ry) > 0

    def test_process_mouse_move_zero(self):
        remapper = InputRemapper({})
        rx, ry = remapper.process_mouse_move(0, 0, 1.0)
        assert rx == 0.0
        assert ry == 0.0

    def test_process_mouse_move_bounds(self):
        remapper = InputRemapper({}, mouse_sens=80.0)
        rx, ry = remapper.process_mouse_move(500, 500, 8.0)
        assert -32768 <= rx <= 32767
        assert -32768 <= ry <= 32767

    def test_square_stick(self):
        remapper = InputRemapper({}, mouse_sens=80.0, square_stick=True)
        rx, ry = remapper.process_mouse_move(100, 100, 8.0)
        assert -32768 <= rx <= 32767
        assert -32768 <= ry <= 32767


class TestRemapPipeline:
    def test_update_key_press(self):
        pipeline = RemapPipeline({"KEY_SPACE": "BTN_A"})
        pipeline.update_key("KEY_SPACE", 1)
        assert "KEY_SPACE" in pipeline.get_active_keys()

    def test_update_key_release(self):
        pipeline = RemapPipeline({"KEY_SPACE": "BTN_A"})
        pipeline.update_key("KEY_SPACE", 1)
        pipeline.update_key("KEY_SPACE", 0)
        assert "KEY_SPACE" not in pipeline.get_active_keys()

    def test_get_stick_values_wasd(self):
        pipeline = RemapPipeline({})
        pipeline.update_key("KEY_W", 1)
        pipeline.update_key("KEY_D", 1)
        lx, ly = pipeline.get_stick_values()
        assert lx > 0
        assert ly < 0

    def test_get_stick_values_diagonal_normalization(self):
        pipeline = RemapPipeline({})
        pipeline.update_key("KEY_W", 1)
        pipeline.update_key("KEY_D", 1)
        lx, ly = pipeline.get_stick_values()
        mag = math.sqrt(lx*lx + ly*ly)
        assert abs(mag - 32767) < 100, f"mag={mag}"

    def test_get_trigger_values(self):
        pipeline = RemapPipeline({"BTN_LEFT": "ABS_RZ"})
        pipeline.update_key("BTN_LEFT", 1)
        lt, rt = pipeline.get_trigger_values()
        assert rt == 255

    def test_get_hat_values(self):
        pipeline = RemapPipeline({"KEY_Z": "ABS_HAT0Y_MIN"})
        pipeline.update_key("KEY_Z", 1)
        hx, hy = pipeline.get_hat_values()
        assert hy < 0

    def test_reset(self):
        pipeline = RemapPipeline({"KEY_SPACE": "BTN_A"})
        pipeline.update_key("KEY_SPACE", 1)
        pipeline.reset()
        assert pipeline.get_active_keys() == set()
