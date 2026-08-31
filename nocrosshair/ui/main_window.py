from typing import Optional, Dict, Any
import sys
import json
import os
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QAction, QShortcut, QKeySequence, QIcon, QFont, QColor, QPalette, QPainter
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStatusBar, QMenuBar, QMenu, QFileDialog, QMessageBox, QLabel,
    QInputDialog, QComboBox, QPushButton, QToolBar
)
from nocrosshair.ui.widgets.animated_tabs import AnimatedTabWidget
from nocrosshair.ui.tabs.crosshair_tab import CrosshairTab
from nocrosshair.ui.tabs.physics_tab import PhysicsTab
from nocrosshair.ui.tabs.remapping_tab import RemappingTab
from nocrosshair.ui.tabs.aa_tab import AimAssistTab
from nocrosshair.ui.tabs.recoil_tab import RecoilTab
from nocrosshair.ui.tabs.profiles_tab import ProfilesTab
from nocrosshair.ui.tabs.macros_tab import MacrosTab
from nocrosshair.ui.tabs.plugins_tab import PluginsTab
from nocrosshair.ui.tabs.controller_v4_tab import ControllerV4Tab
from nocrosshair.ui.tabs.calibration_tab import CalibrationTab
from nocrosshair.ui.widgets.status_hud import StatusHUD
from nocrosshair.ui.effects.glitch_bg import GlitchPainter
from nocrosshair.core.profile_manager import Profile, ProfileManager, SlotManager
from nocrosshair.core.runtime import RuntimeManager
from nocrosshair.core.overlay import OverlayManager
from nocrosshair.core.config import ControllerHardwareConfig

class _GlitchWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._painter = GlitchPainter(self)
        self._repaint_timer = QTimer(self)
        self._repaint_timer.timeout.connect(self.update)
        self._repaint_timer.start(33)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event):
        painter = QPainter(self)
        self._painter.paint(painter, float(self.width()), float(self.height()))
        painter.end()

class MainWindow(QMainWindow):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nocrosshair - ReWASD Alternative for Linux")
        self.setGeometry(100, 100, 1200, 800)

        self.profile_manager = ProfileManager()
        self.slot_manager = SlotManager()
        self.current_profile = None
        self.overlay_manager = None
        self.runtime = RuntimeManager()
        self._config_dirty = False

        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self._auto_save)
        self.auto_save_timer.start(5000)

        self._debounce_save_timer = QTimer()
        self._debounce_save_timer.setSingleShot(True)
        self._debounce_save_timer.timeout.connect(self._debounced_save)

        self._init_ui()
        self._init_toolbar()
        self._init_menu()
        self._init_status()
        self._init_overlay()
        self._init_sniper_zoom()
        self._init_runtime_poll()
        self._init_hud()
        self._refresh_profile_list()
        self._refresh_all_devices()
        self._load_saved_config()
        self.show()

    def _init_sniper_zoom(self) -> None:
        from nocrosshair.ui.widgets.zoom_overlay import ZoomOverlay
        self._zoom_overlay = ZoomOverlay()
        self._zoom_poll = QTimer()
        self._zoom_poll.timeout.connect(self._poll_sniper_zoom)
        self._zoom_poll.start(50)

    def _poll_sniper_zoom(self) -> None:
        held = self.runtime.is_sniper_zoom_held()
        if held and not self._zoom_overlay.isVisible():
            cfg = self.runtime.config.sniper_zoom
            self._zoom_overlay.set_zoom_params(
                cfg.zoom_factor, cfg.window_width, cfg.window_height,
                fixed_pos=cfg.fixed_position, fx=cfg.fixed_x, fy=cfg.fixed_y,
            )
            if cfg.fixed_position:
                self._zoom_overlay.move(cfg.fixed_x - cfg.window_width // 2,
                                        cfg.fixed_y - cfg.window_height - 30)
            self._zoom_overlay.set_active(True)
        elif not held and self._zoom_overlay.isVisible():
            self._zoom_overlay.set_active(False)

    def _init_ui(self) -> None:
        central = _GlitchWidget()
        self.setCentralWidget(central)
        self._glitch = central._painter

        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tabs = AnimatedTabWidget()

        self.crosshair_tab = CrosshairTab()
        self.physics_tab = PhysicsTab()
        self.remapping_tab = RemappingTab()
        self.aa_tab = AimAssistTab()
        self.recoil_tab = RecoilTab()
        self.profiles_tab = ProfilesTab()
        self.profiles_tab.load_requested.connect(self._load_profile)
        self.profiles_tab.save_requested.connect(self._save_profile_as)
        self.profiles_tab.delete_requested.connect(self._delete_profile)
        self.profiles_tab.export_requested.connect(self._export_profile_named)
        self.profiles_tab.import_requested.connect(self._import_profile)
        self.profiles_tab.slot_assign_requested.connect(self._assign_profile_slot)
        self.macros_tab = MacrosTab()
        self.plugins_tab = PluginsTab()
        self.controller_v4_tab = ControllerV4Tab()
        self.controller_v4_tab.config_changed.connect(self._on_controller_v4_changed)
        self.controller_v4_tab.controller_changed.connect(self._update_ctrl_type_label)

        self.calibration_tab = CalibrationTab()
        self.calibration_tab.config_changed.connect(self._on_calibration_changed)

        from PyQt6.QtWidgets import QScrollArea
        tab_list = [
            ("Crosshair", self.crosshair_tab),
            ("Physics", self.physics_tab),
            ("Remapping", self.remapping_tab),
            ("Aim Assist", self.aa_tab),
            ("Recoil", self.recoil_tab),
            ("Controller", self.controller_v4_tab),
            ("Calibration", self.calibration_tab),
            ("Profiles", self.profiles_tab),
            ("Macros", self.macros_tab),
            ("Plugins", self.plugins_tab),
        ]
        for name, tab in tab_list:
            tab.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(tab)
            scroll.setStyleSheet("QScrollArea { background: transparent; border: none; } "
                                 "QScrollArea > QWidget { background: transparent; }")
            self.tabs.addTab(scroll, name)

        self.tabs.currentChanged.connect(self._on_tab_changed)
        for i in range(self.tabs.count()):
            if self.tabs.tabText(i).rstrip(" *") == "Controller":
                self.tabs.setCurrentIndex(i)
                break

        for tab in [self.crosshair_tab, self.physics_tab, self.remapping_tab,
                    self.aa_tab, self.recoil_tab]:
            if hasattr(tab, "config_changed"):
                tab.config_changed.connect(lambda: self._mark_dirty())

        self.macros_tab.macro_changed.connect(lambda: self._mark_dirty())

        layout.addWidget(self.tabs)
        central.setLayout(layout)

    def _init_toolbar(self) -> None:
        toolbar = QToolBar("Runtime")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(toolbar)

        toolbar.addWidget(QLabel("  Ctrl: "))
        self.device_combo = QComboBox()
        self.device_combo.setMinimumWidth(160)
        self.device_combo.currentIndexChanged.connect(self._on_device_changed)
        self.device_combo.setToolTip("Physical controller (passthrough). Leave as None for KBM mode.")
        toolbar.addWidget(self.device_combo)

        toolbar.addWidget(QLabel(" Tipo: "))
        self.ctrl_type_label = QLabel("xbox360")
        self.ctrl_type_label.setStyleSheet("color: #00E5FF; font-weight: 600;")
        self.ctrl_type_label.setMinimumWidth(80)
        toolbar.addWidget(self.ctrl_type_label)

        toolbar.addWidget(QLabel("  Kbd: "))
        self.kbd_combo = QComboBox()
        self.kbd_combo.setMinimumWidth(160)
        self.kbd_combo.setToolTip("Keyboard device to remap to controller buttons.")
        self.kbd_combo.currentIndexChanged.connect(lambda: self._mark_dirty())
        toolbar.addWidget(self.kbd_combo)

        toolbar.addWidget(QLabel("  Mouse: "))
        self.mouse_combo = QComboBox()
        self.mouse_combo.setMinimumWidth(160)
        self.mouse_combo.setToolTip("Mouse device for aim assist and right-stick emulation.")
        self.mouse_combo.currentIndexChanged.connect(lambda: self._mark_dirty())
        toolbar.addWidget(self.mouse_combo)

        self.btn_refresh = QPushButton("⟳")
        self.btn_refresh.setFixedWidth(30)
        self.btn_refresh.setToolTip("Refresh devices")
        self.btn_refresh.clicked.connect(self._refresh_all_devices)
        toolbar.addWidget(self.btn_refresh)

        toolbar.addSeparator()

        self.btn_start = QPushButton("▶ Iniciar")
        self.btn_start.setObjectName("startBtn")
        self.btn_start.clicked.connect(self._on_start)
        toolbar.addWidget(self.btn_start)

        self.btn_stop = QPushButton("■ Parar")
        self.btn_stop.setObjectName("stopBtn")
        self.btn_stop.clicked.connect(self._on_stop)
        self.btn_stop.setEnabled(False)
        toolbar.addWidget(self.btn_stop)

        toolbar.addSeparator()

        toolbar.addWidget(QLabel(" Profile: "))
        self.profile_combo = QComboBox()
        self.profile_combo.setObjectName("profileCombo")
        self.profile_combo.setMinimumWidth(140)
        self.profile_combo.setToolTip("Switch active profile")
        self.profile_combo.currentTextChanged.connect(self._on_profile_combo_changed)
        toolbar.addWidget(self.profile_combo)

        self.profile_badge = QLabel("  [ NO PROFILE ]")
        self.profile_badge.setObjectName("profileBadge")
        self.profile_badge.setStyleSheet("background-color: rgba(25, 38, 60, 0.85);")
        toolbar.addWidget(self.profile_badge)

        toolbar.addSeparator()

        self.status_indicator = QLabel("○ IDLE")
        self.status_indicator.setObjectName("hudStatusLabel")
        self.status_indicator.setProperty("active", "false")
        toolbar.addWidget(self.status_indicator)

        self.btn_apply = QPushButton("Aplicar")
        self.btn_apply.setObjectName("applyBtn")
        self.btn_apply.clicked.connect(self._on_apply_config)
        toolbar.addWidget(self.btn_apply)

        toolbar.addSeparator()

        self.btn_export = QPushButton("Export")
        self.btn_export.clicked.connect(self._on_export_config)
        toolbar.addWidget(self.btn_export)

        self.btn_import = QPushButton("Import")
        self.btn_import.clicked.connect(self._on_import_config)
        toolbar.addWidget(self.btn_import)

        toolbar.addSeparator()

    def _init_runtime_poll(self) -> None:
        self._status_poll_timer = QTimer()
        self._status_poll_timer.timeout.connect(self._poll_runtime_status)
        self._status_poll_timer.start(1000)

    def _init_hud(self) -> None:
        self.hud = StatusHUD()
        self.hud.set_runtime(self.runtime)

        hud_shortcut = QShortcut(QKeySequence("Ctrl+Shift+H"), self)
        hud_shortcut.activated.connect(self._toggle_hud)

    def _toggle_hud(self) -> None:
        if self.hud.isVisible():
            self.hud.hide()
        else:
            self._sync_hud_config()
            self.hud.show()

    def _sync_hud_config(self) -> None:
        if self.runtime.config is not None:
            self.hud.set_config(self.runtime.config)
        else:
            self.hud.set_config(self._build_config_from_ui())

    def _mark_dirty(self) -> None:
        if not self._config_dirty:
            self._config_dirty = True
            self._update_tab_titles()
        self._debounce_save_timer.start(1000)

    def _on_controller_v4_changed(self, controller_id: str, config: dict) -> None:
        cfg = self._build_config_from_ui()
        if cfg:
            cfg.controller_hardware.controller_id = controller_id
            self.runtime.apply_config(cfg)
            self._mark_dirty()

    def _on_calibration_changed(self, config: dict) -> None:
        cfg = self._build_config_from_ui()
        if cfg:
            self.runtime.apply_config(cfg)
            self._mark_dirty()

    def _update_ctrl_type_label(self, hw_id: str) -> None:
        type_map = {
            "g7_pro_8k": "xbox360",
            "cyclone_2": "xbox360",
            "ds4": "dualshock4",
            "dualsense_edge": "dualsense_edge",
            "dualsense": "dualsense",
            "xbox360": "xbox360",
        }
        self.ctrl_type_label.setText(type_map.get(hw_id, "xbox360"))

    def _debounced_save(self) -> None:
        if not self._config_dirty:
            return
        cfg = self._build_config_from_ui()
        if self.runtime.apply_and_save(cfg):
            self._config_dirty = False
            self._update_tab_titles()

    def _mark_clean(self) -> None:
        if self._config_dirty:
            self._config_dirty = False
            self._update_tab_titles()

    def _update_tab_titles(self) -> None:
        suffix = " *" if self._config_dirty else ""
        tab_names = ["Crosshair", "Physics", "Remapping", "Aim Assist", "Recoil", "Controller", "Profiles", "Macros", "Plugins"]
        tab_widgets = [
            self.crosshair_tab, self.physics_tab, self.remapping_tab,
            self.aa_tab, self.recoil_tab, self.controller_v4_tab, self.profiles_tab, self.macros_tab,
            self.plugins_tab,
        ]
        for i, (name, widget) in enumerate(zip(tab_names, tab_widgets)):
            current = self.tabs.tabText(i).rstrip(" *")
            if current == name:
                self.tabs.setTabText(i, name + suffix)

    def _refresh_all_devices(self) -> None:
        try:
            import evdev
            from evdev import ecodes as e
        except ImportError:
            return

        skip_words = [
            "hd-audio", "consumer control", "system control",
            "video bus", "power button", "sleep button",
            "lid switch", "pc speaker", "virtual", "uinput"
        ]

        ctrl_list = []
        kbd_list = []
        mouse_list = []

        for path in evdev.list_devices():
            try:
                dev = evdev.InputDevice(path)
                name = dev.name.lower()
                if any(w in name for w in skip_words):
                    dev.close()
                    continue
                caps = dev.capabilities()
                label = f"{dev.name} ({path})"

                if e.EV_KEY in caps:
                    key_list = caps[e.EV_KEY]
                    has_mouse_btn = e.BTN_LEFT in key_list
                    has_alpha = any(k in key_list for k in [e.KEY_A, e.KEY_Z, e.KEY_Q])
                    name_lower = dev.name.lower()
                    is_gaming_mouse = "gaming mouse" in name_lower
                    if has_alpha and not has_mouse_btn and not is_gaming_mouse:
                        kbd_list.append((len(key_list), label, path))
                    if has_mouse_btn:
                        mouse_list.append((label, path))

                if e.EV_ABS in caps:
                    abs_codes = [c for c, _ in caps[e.EV_ABS]]
                    if e.ABS_X in abs_codes and e.ABS_RX in abs_codes:
                        ctrl_list.append((label, path))

                dev.close()
            except Exception:
                pass

        kbd_list.sort(key=lambda x: x[0], reverse=True)
        for combo, items, name in [
            (self.device_combo, ctrl_list, "Controller"),
            (self.kbd_combo, [(lbl, pth) for _, lbl, pth in kbd_list], "Keyboard"),
            (self.mouse_combo, mouse_list, "Mouse"),
        ]:
            combo.blockSignals(True)
            current = combo.currentData()
            combo.clear()
            combo.addItem(f"None ({name})", "")
            for lbl, pth in items:
                combo.addItem(lbl, pth)
            selected = False
            if current:
                for i in range(combo.count()):
                    if combo.itemData(i) == current:
                        combo.setCurrentIndex(i)
                        selected = True
                        break
            if not selected and items:
                combo.setCurrentIndex(1)
            combo.blockSignals(False)

    def _on_device_changed(self, index: int) -> None:
        pass

    def _load_saved_config(self) -> None:
        cfg = self.runtime.load_config()
        if cfg is None:
            return
        if cfg.remap_kbd_path:
            for i in range(self.kbd_combo.count()):
                if self.kbd_combo.itemData(i) == cfg.remap_kbd_path:
                    self.kbd_combo.setCurrentIndex(i)
                    break
        if cfg.remap_mouse_path:
            for i in range(self.mouse_combo.count()):
                if self.mouse_combo.itemData(i) == cfg.remap_mouse_path:
                    self.mouse_combo.setCurrentIndex(i)
                    break
        if cfg.controller_type and hasattr(self, 'controller_v4_tab'):
            hw_map = {"xbox360": "xbox360", "dualshock4": "ds4", "dualsense_edge": "dualsense_edge", "dualsense": "dualsense", "xboxone": "xbox360"}
            hw_id = hw_map.get(cfg.controller_type, "xbox360")
            idx = self.controller_v4_tab.hw_combo.findData(hw_id)
            if idx >= 0:
                self.controller_v4_tab.hw_combo.setCurrentIndex(idx)

        flat = cfg.to_dict()
        self._restore_ui_from_flat(flat)
        self.statusBar().showMessage("Config loaded from ~/.config/nocrosshair.nocro")

    def _restore_ui_from_flat(self, flat: dict) -> None:
        if hasattr(self, 'remapping_tab') and hasattr(self.remapping_tab, 'set_config'):
            self.remapping_tab.set_config(flat)
        if hasattr(self, 'aa_tab') and hasattr(self.aa_tab, 'set_config'):
            self.aa_tab.set_config(flat)
        if hasattr(self, 'aa_tab') and hasattr(self.aa_tab, 'set_rapid_fire_config'):
            from nocrosshair.core.config import RapidFireConfig
            self.aa_tab.set_rapid_fire_config(RapidFireConfig.from_dict(flat))
        if hasattr(self, 'aa_tab') and hasattr(self.aa_tab, 'set_bloom_reducer_config'):
            from nocrosshair.core.config import BloomReducerConfig
            self.aa_tab.set_bloom_reducer_config(BloomReducerConfig.from_dict(flat))
        if hasattr(self, 'aa_tab') and hasattr(self.aa_tab, 'set_movement_tech_config'):
            from nocrosshair.core.config import MovementTechConfig
            self.aa_tab.set_movement_tech_config(MovementTechConfig.from_dict(flat))
        if hasattr(self, 'aa_tab') and hasattr(self.aa_tab, 'set_crouch_aim_config'):
            from nocrosshair.core.config import CrouchAimConfig
            self.aa_tab.set_crouch_aim_config(CrouchAimConfig.from_dict(flat))
        if hasattr(self, 'recoil_tab') and hasattr(self.recoil_tab, 'set_config'):
            self.recoil_tab.set_config(flat)
        if hasattr(self, 'physics_tab') and hasattr(self.physics_tab, 'set_config'):
            self.physics_tab.set_config(flat)
        if hasattr(self, 'calibration_tab') and hasattr(self.calibration_tab, 'set_config'):
            hw = flat.get("controller_hardware", {})
            if hw:
                cal_config = dict(hw)
                if "polling_rate_hz" in cal_config:
                    cal_config["polling_rate"] = cal_config.pop("polling_rate_hz")
                self.calibration_tab.set_config(cal_config)

    def _on_start(self) -> None:
        device_path = self.device_combo.currentData()
        cfg = self._build_config_from_ui()
        self.runtime.apply_config(cfg)

        if not cfg.remap_active and not device_path:
            self.status_indicator.setText("⛔ NO DEVICE")
            self.status_indicator.setProperty("active", "error")
            self.status_indicator.style().unpolish(self.status_indicator)
            self.status_indicator.style().polish(self.status_indicator)
            self.statusBar().showMessage("Select a controller or enable remap (KBM)")
            return

        started = self.runtime.start(device_path or "")
        if started:
            self.status_indicator.setText("● ACTIVE")
            self.status_indicator.setProperty("active", "true")
            self.status_indicator.style().unpolish(self.status_indicator)
            self.status_indicator.style().polish(self.status_indicator)
            self.btn_start.setEnabled(False)
            self.btn_stop.setEnabled(True)
        else:
            self.status_indicator.setText("● FAILURE")
            self.status_indicator.setProperty("active", "error")
            self.status_indicator.style().unpolish(self.status_indicator)
            self.status_indicator.style().polish(self.status_indicator)
            err = self.runtime.last_error or "unknown error"
            self.statusBar().showMessage(f"Failed: {err}")
            QMessageBox.critical(self, "Start Failed", f"Falha ao iniciar:\n\n{err}")

    def _on_stop(self) -> None:
        self.runtime.stop()
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.status_indicator.setText("○ IDLE")
        self.status_indicator.setProperty("active", "false")
        self.status_indicator.style().unpolish(self.status_indicator)
        self.status_indicator.style().polish(self.status_indicator)
        self.statusBar().showMessage("Runtime stopped")

    def _on_export_config(self) -> None:
        cfg = self._build_config_from_ui()
        data = cfg.to_dict()
        data["kbd_bindings"] = cfg.kbd_bindings
        payload = {"_format": "nocrosshair.nocro", "_version": 1, "config": data}
        path, _ = QFileDialog.getSaveFileName(self, "Export Config",
                                               os.path.expanduser("~"), "Nocro (*.nocro);;JSON (*.json)")
        if path:
            try:
                with open(path, "w") as f:
                    f.write("# NOCRO v1 — nocrosshair config file\n")
                    json.dump(payload, f, indent=2)
                self.statusBar().showMessage(f"Exported to {path}")
            except Exception as e:
                self.statusBar().showMessage(f"Export failed: {e}")

    def _on_import_config(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import Config",
                                               os.path.expanduser("~"), "Nocro (*.nocro);;JSON (*.json);;All (*)")
        if not path:
            return
        try:
            with open(path, "r") as f:
                content = f.read()
            data = json.loads(content.split("\n", 1)[-1])
            inner = data.get("config", data)
            cfg = AppConfig.from_dict(inner)
            self.runtime.apply_and_save(cfg)
            self._load_saved_config()
            self.statusBar().showMessage(f"Imported from {path}")
        except Exception as e:
            self.statusBar().showMessage(f"Import failed: {e}")
        self.runtime.stop()
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.status_indicator.setText("○ IDLE")
        self.status_indicator.setProperty("active", "false")
        self.status_indicator.style().unpolish(self.status_indicator)
        self.status_indicator.style().polish(self.status_indicator)
        self.statusBar().showMessage("Runtime stopped")

    def _on_apply_config(self) -> None:
        cfg = self._build_config_from_ui()
        if self.runtime.apply_and_save(cfg):
            self._mark_clean()
            self._sync_hud_config()
            self.statusBar().showMessage("Config applied and saved")
        else:
            self.statusBar().showMessage("Failed to apply config")

    def _build_config_from_ui(self):
        from nocrosshair.core.config import (
            AppConfig, AdvancedStickPhysicsConfig, TriggerPhysicsConfig,
            AimAssistConfig, RecoilConfig, SniperZoomConfig,
            RecoilRuntimeConfig,
        )
        physics = self.physics_tab.get_config()
        cal = self.calibration_tab.get_config()
        physics["ls_response_curve"] = cal.get("response_curve_ls", "linear")
        physics["rs_response_curve"] = cal.get("response_curve_rs", "linear")
        physics["ls_anti_deadzone"] = cal.get("anti_deadzone_ls", 0)
        physics["rs_anti_deadzone"] = cal.get("anti_deadzone_rs", 0)
        physics["ls_raw_mode"] = cal.get("raw_mode_ls", False)
        physics["rs_raw_mode"] = cal.get("raw_mode_rs", False)
        aa = self.aa_tab.get_aim_assist_config()
        recoil_cfg = self.recoil_tab.get_config()
        remap = self.remapping_tab.get_config()
        rapid_fire_cfg = self.aa_tab.get_rapid_fire_config()
        bloom_reducer_cfg = self.aa_tab.get_bloom_reducer_config()
        movement_tech_cfg = self.aa_tab.get_movement_tech_config()
        crouch_aim_cfg = self.aa_tab.get_crouch_aim_config()

        kbd_path = self.kbd_combo.currentData() or ""
        mouse_path = self.mouse_combo.currentData() or ""
        has_remap = bool(kbd_path or mouse_path)
        ctrl_type = self.controller_v4_tab.current_controller_type()
        mouse_sens = remap.get("mouse_sens", 80.0)
        sens_x = remap.get("sens_x", 80.0)
        sens_y = remap.get("sens_y", 80.0)
        mouse_curve = remap.get("mouse_curve", 0.65)
        mouse_smooth = remap.get("mouse_smooth", 0.0)
        mouse_min_output = remap.get("mouse_min_output", 0.08)
        square_stick = remap.get("square_stick", True)

        cfg = AppConfig(
            controller_type=ctrl_type,
            ls_physics=AdvancedStickPhysicsConfig.from_dict(physics, "ls_"),
            rs_physics=AdvancedStickPhysicsConfig.from_dict(physics, "rs_"),
            lt_physics=TriggerPhysicsConfig.from_dict(physics, "lt_"),
            rt_physics=TriggerPhysicsConfig.from_dict(physics, "rt_"),
            aim_assist=aa,
            rapid_fire=rapid_fire_cfg,
            bloom_reducer=bloom_reducer_cfg,
            movement_tech=movement_tech_cfg,
            crouch_aim=crouch_aim_cfg,
            recoil=RecoilConfig.from_dict(recoil_cfg),
            remap_kbd_path=kbd_path,
            remap_mouse_path=mouse_path,
            remap_active=has_remap,
            mouse_sens=float(mouse_sens),
            sens_x=float(sens_x),
            sens_y=float(sens_y),
            mouse_curve=float(mouse_curve),
            mouse_smooth=float(mouse_smooth),
            mouse_min_output=float(mouse_min_output),
            square_stick=bool(square_stick),
            kbd_bindings=remap.get("bindings"),
            controller_hardware=ControllerHardwareConfig(
                controller_id=ctrl_type,
                anti_deadzone_ls=cal["anti_deadzone_ls"],
                anti_deadzone_rs=cal["anti_deadzone_rs"],
                response_curve_ls=cal["response_curve_ls"],
                response_curve_rs=cal["response_curve_rs"],
                raw_mode_ls=cal["raw_mode_ls"],
                raw_mode_rs=cal["raw_mode_rs"],
                trigger_deadzone_start=cal["trigger_deadzone_start"],
                trigger_deadzone_end=cal["trigger_deadzone_end"],
                hair_trigger_mode=cal["hair_trigger_mode"],
                dpad_diag_lock=cal["dpad_diag_lock"],
                vibration_lt=cal["vibration_lt"],
                vibration_rt=cal["vibration_rt"],
                vibration_sync=cal["vibration_sync"],
                polling_rate_hz=cal["polling_rate"],
            ),
            sniper_zoom=SniperZoomConfig(
                enabled=remap.get("sniper_zoom_enabled", False),
                button=remap.get("sniper_zoom_button", "BTN_SIDE"),
                zoom_factor=float(remap.get("sniper_zoom_factor", 4)),
                window_width=int(remap.get("sniper_zoom_window_width", 240)),
                window_height=int(remap.get("sniper_zoom_window_height", 180)),
                fixed_position=remap.get("sniper_zoom_fixed_pos", False),
                fixed_x=int(remap.get("sniper_zoom_fixed_x", 960)),
                fixed_y=int(remap.get("sniper_zoom_fixed_y", 540)),
            ),
        )
        cfg.recoil_runtime.loadout_slots = list(recoil_cfg.get(
            "loadout_slots", RecoilRuntimeConfig.DEFAULT_LOADOUT_SLOTS,
        ))
        return cfg

    def _poll_runtime_status(self) -> None:
        status = self.runtime.get_status()
        if status["active"]:
            if status.get("disabled"):
                self.status_indicator.setText("● OFF (DEL)")
                self.status_indicator.setProperty("active", "disabled")
            else:
                self.status_indicator.setText("● ACTIVE")
                self.status_indicator.setProperty("active", "true")
            self.status_indicator.style().unpolish(self.status_indicator)
            self.status_indicator.style().polish(self.status_indicator)
            self.btn_start.setEnabled(False)
            self.btn_stop.setEnabled(True)
        else:
            self.status_indicator.setText("○ IDLE")
            self.status_indicator.setProperty("active", "false")
            self.status_indicator.style().unpolish(self.status_indicator)
            self.status_indicator.style().polish(self.status_indicator)
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)
        if self.hud.isVisible():
            self._sync_hud_config()

    def closeEvent(self, event) -> None:
        self.auto_save_timer.stop()
        self._debounce_save_timer.stop()
        self.runtime.stop()
        if self.hud:
            self.hud.close()
        event.accept()

    def _init_menu(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")

        new_action = QAction("New Profile", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self._new_profile)
        file_menu.addAction(new_action)

        open_action = QAction("Open Profile", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_profile)
        file_menu.addAction(open_action)

        save_action = QAction("Save Profile", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._save_profile)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        export_action = QAction("Export", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self._export_profile)
        file_menu.addAction(export_action)

        import_action = QAction("Import", self)
        import_action.setShortcut("Ctrl+I")
        import_action.triggered.connect(self._import_profile)
        file_menu.addAction(import_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Alt+F4")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        edit_menu = menubar.addMenu("Edit")
        reset_action = QAction("Reset to Defaults", self)
        reset_action.setShortcut("Ctrl+R")
        reset_action.triggered.connect(self._reset_profile)
        edit_menu.addAction(reset_action)

        view_menu = menubar.addMenu("View")
        toggle_action = QAction("Toggle Overlay (F8)", self)
        toggle_action.setShortcut("F8")
        toggle_action.triggered.connect(self._toggle_overlay)
        view_menu.addAction(toggle_action)

        hud_action = QAction("Toggle HUD (Ctrl+Shift+H)", self)
        hud_action.setShortcut("Ctrl+Shift+H")
        hud_action.triggered.connect(self._toggle_hud)
        view_menu.addAction(hud_action)



        help_menu = menubar.addMenu("Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _init_status(self) -> None:
        self.statusBar().showMessage("SYSTEM NOMINAL")

        self.fps_label = QLabel("FPS: --")
        self.fps_label.setObjectName("fpsLabel")
        self.statusBar().addPermanentWidget(self.fps_label)

        self.conn_label = QLabel("CONNECTED")
        self.conn_label.setObjectName("connLabel")
        self.statusBar().addPermanentWidget(self.conn_label)

    def _init_overlay(self) -> None:
        try:
            config = self.crosshair_tab.get_config()
            self.overlay_manager = OverlayManager(config)
            self.crosshair_tab.config_changed.connect(self._on_crosshair_config_changed)
            self.statusBar().showMessage("Overlay initialized")
        except Exception as e:
            print(f"[MainWindow] Failed to initialize overlay: {e}")
            self.statusBar().showMessage("Overlay initialization failed")

    def _on_tab_changed(self, index: int) -> None:
        self.statusBar().showMessage(f"Tab: {self.tabs.tabText(index)}")

    def _auto_save(self) -> None:
        if self.current_profile:
            try:
                profile = self._create_profile_from_ui(self.current_profile.name)
                if self.profile_manager.save_profile(profile):
                    self.current_profile = profile
                    self._refresh_profile_list()
                    self.statusBar().showMessage("Auto-saved")
                else:
                    self.statusBar().showMessage("Auto-save failed")
            except Exception as e:
                self.statusBar().showMessage(f"Auto-save failed: {e}")

    def _gather_all_configs(self) -> Dict[str, Any]:
        configs = {
            "crosshair": self.crosshair_tab.get_config(),
            "physics": self.physics_tab.get_config(),
            "remapping": self.remapping_tab.get_config(),
            "aa": self.aa_tab.get_config(),
            "recoil": self.recoil_tab.get_config(),
        }
        return configs

    def _create_profile_from_ui(self, name: str) -> Profile:
        configs = self._gather_all_configs()
        return Profile(
            name=name,
            crosshair=configs["crosshair"],
            remapping=configs["remapping"],
            key_map={"bindings": configs["remapping"].get("bindings", [])},
            mouse_map={"device": configs["remapping"].get("mouse", "")},
            physics=configs["physics"],
            aiming=configs["aa"],
            recoil=configs["recoil"],
        )

    def _apply_profile_to_ui(self, profile: Profile) -> None:
        self.current_profile = profile
        self.crosshair_tab.set_config(profile.crosshair)
        self.remapping_tab.set_config(profile.remapping)
        self.physics_tab.set_config(profile.physics)
        self.aa_tab.set_config(profile.aiming)
        self.recoil_tab.set_config(profile.recoil)
        self.profiles_tab.set_active_profile(profile.name)
        self._refresh_profile_list()

    def _sync_profile_combo(self, active_name: str = "") -> None:
        self.profile_combo.blockSignals(True)
        current = self.profile_combo.currentText()
        self.profile_combo.clear()
        for p in self.profile_manager.list_profiles():
            self.profile_combo.addItem(p, p)
        idx = self.profile_combo.findText(active_name or current)
        if idx >= 0:
            self.profile_combo.setCurrentIndex(idx)
            self.profile_badge.setText(f"  [ {active_name or current} ]")
        self.profile_combo.blockSignals(False)

    def _refresh_profile_list(self) -> None:
        profiles = self.profile_manager.list_profiles()
        self.profiles_tab.refresh_profiles(profiles, self.slot_manager.slots)
        self._sync_profile_combo()

    def _on_profile_combo_changed(self, name: str) -> None:
        if not name or not name.strip():
            return
        if self.current_profile and self.current_profile.name == name:
            return
        self._load_profile(name)

    def _new_profile(self) -> None:
        name, ok = QInputDialog.getText(self, "New Profile", "Profile name:")
        if not ok:
            return

        name = name.strip()
        if not name:
            self.statusBar().showMessage("Profile name cannot be empty")
            return

        profile = self._create_profile_from_ui(name)
        self.current_profile = profile
        self.profiles_tab.set_active_profile(name)
        self._sync_profile_combo(name)
        self.statusBar().showMessage(f"New profile ready: {name}")

    def _open_profile(self) -> None:
        name = self.profiles_tab.selected_profile_name()
        if not name:
            profiles = self.profile_manager.list_profiles()
            name = profiles[0] if profiles else ""
        if name:
            self._load_profile(name)
        else:
            self.statusBar().showMessage("No profiles available")

    def _load_profile(self, name: str) -> None:
        profile = self.profile_manager.load_profile(name)
        if profile is None:
            self.statusBar().showMessage(f"Profile not found: {name}")
            return

        self._apply_profile_to_ui(profile)
        self._mark_clean()
        self._sync_hud_config()
        self._sync_profile_combo(profile.name)
        self.statusBar().showMessage(f"Loaded profile: {profile.name}")

    def _save_profile(self) -> None:
        name = self.current_profile.name if self.current_profile else self.profiles_tab.current_profile_name()
        if not name:
            self.statusBar().showMessage("Profile name cannot be empty")
            return
        self._save_profile_as(name)

    def _save_profile_as(self, name: str) -> None:
        name = name.strip()
        if not name:
            self.statusBar().showMessage("Profile name cannot be empty")
            return

        is_current = self.current_profile is not None and self.current_profile.name == name
        if self.profile_manager.profile_exists(name) and not is_current:
            reply = QMessageBox.question(
                self,
                "Overwrite Profile",
                f"Profile '{name}' already exists. Overwrite it?",
            )
            if reply != QMessageBox.StandardButton.Yes:
                self.statusBar().showMessage("Save cancelled")
                return

        profile = self._create_profile_from_ui(name)
        errors = self.profile_manager.validate_profile(profile)
        if errors:
            self.statusBar().showMessage("; ".join(errors))
            return

        if self.profile_manager.save_profile(profile):
            self.current_profile = profile
            self.profiles_tab.set_active_profile(name)
            self._refresh_profile_list()
            self._mark_clean()
            self.statusBar().showMessage(f"Profile saved: {name}")
        else:
            self.statusBar().showMessage(f"Failed to save profile: {name}")

    def _delete_profile(self, name: str) -> None:
        reply = QMessageBox.question(self, "Delete Profile", f"Delete profile '{name}'?")
        if reply != QMessageBox.StandardButton.Yes:
            return

        if self.profile_manager.delete_profile(name):
            for slot, profile_name in list(self.slot_manager.slots.items()):
                if profile_name == name:
                    self.slot_manager.assign(slot, None)
            if self.current_profile and self.current_profile.name == name:
                self.current_profile = None
                self.profiles_tab.set_active_profile("Default")
            self._refresh_profile_list()
            self.statusBar().showMessage(f"Profile deleted: {name}")
        else:
            self.statusBar().showMessage(f"Failed to delete profile: {name}")

    def _export_profile(self) -> None:
        name = self.current_profile.name if self.current_profile else self.profiles_tab.selected_profile_name()
        if not name:
            self.statusBar().showMessage("Select a profile to export")
            return
        self._export_profile_named(name)

    def _export_profile_named(self, name: str) -> None:
        filename, _ = QFileDialog.getSaveFileName(self, "Export Profile", "", "JSON Files (*.json)")
        if filename:
            if self.profile_manager.export_profile(name, filename):
                self.statusBar().showMessage(f"Profile exported to {filename}")
            else:
                self.statusBar().showMessage(f"Failed to export profile: {name}")

    def _import_profile(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "Import Profile", "", "JSON Files (*.json)")
        if filename:
            suggested = filename.rsplit("/", 1)[-1].rsplit(".", 1)[0]
            name, ok = QInputDialog.getText(self, "Import Profile", "Profile name:", text=suggested)
            if not ok:
                return

            name = name.strip()
            if not name:
                self.statusBar().showMessage("Profile name cannot be empty")
                return

            if self.profile_manager.profile_exists(name):
                reply = QMessageBox.question(
                    self,
                    "Overwrite Profile",
                    f"Profile '{name}' already exists. Overwrite it?",
                )
                if reply != QMessageBox.StandardButton.Yes:
                    self.statusBar().showMessage("Import cancelled")
                    return

            if self.profile_manager.import_profile(filename, name):
                self._refresh_profile_list()
                self.statusBar().showMessage(f"Profile imported: {name}")
            else:
                self.statusBar().showMessage(f"Failed to import profile: {filename}")

    def _assign_profile_slot(self, slot: int, name: str) -> None:
        profile_name = name or None
        if profile_name and not self.profile_manager.profile_exists(profile_name):
            self.statusBar().showMessage(f"Profile not found: {profile_name}")
            return

        if self.slot_manager.assign(slot, profile_name):
            self._refresh_profile_list()
            if profile_name:
                self.statusBar().showMessage(f"Assigned {profile_name} to slot {slot}")
            else:
                self.statusBar().showMessage(f"Cleared slot {slot}")
        else:
            self.statusBar().showMessage(f"Invalid slot: {slot}")

    def _reset_profile(self) -> None:
        reply = QMessageBox.question(self, "Reset", "Reset to default settings?")
        if reply == QMessageBox.StandardButton.Yes:
            self.statusBar().showMessage("Profile reset to defaults")

    def _toggle_overlay(self) -> None:
        if self.overlay_manager:
            self.overlay_manager.toggle()
            state = "visible" if self.overlay_manager.is_visible else "hidden"
            self.statusBar().showMessage(f"Overlay {state}")
        else:
            self.statusBar().showMessage("Overlay not initialized")

    def _on_crosshair_config_changed(self, config: dict) -> None:
        if self.overlay_manager:
            self.overlay_manager.update_config(config)

    def _show_about(self) -> None:
        QMessageBox.information(self, "About Nocrosshair",
            "Nocrosshair v2.0\nReWASD alternative for Linux\n\n"
            "Physics Engine • Aim Assist • Recoil Control\n"
            "Python 3.8+ • PyQt6 • X11 Support")

def main():
    from PyQt6.QtWidgets import QApplication
    from nocrosshair.ui.theme import apply_theme

    app = QApplication(sys.argv)
    apply_theme(app)

    window = MainWindow()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
