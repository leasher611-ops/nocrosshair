from typing import Optional, Any
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QTabWidget, QFrame, QCheckBox, QGridLayout, QGroupBox
)

from nocrosshair.controllers.registry import registry
from nocrosshair.controllers.descriptor import ControllerDescriptor
from nocrosshair.ui.widgets.trigger_config import TriggerConfigWidget
from nocrosshair.ui.widgets.gyro_config import GyroConfigWidget
from nocrosshair.ui.widgets.rgb_picker import RGBPickerWidget


_AVAILABLE_RATES: dict[str, list[int]] = {
    "g7_pro_8k": [8000, 4000, 1000, 500],
    "cyclone_2": [1000, 500, 250],
    "ds4": [1000, 500, 250],
    "dualsense_edge": [1000, 500, 250],
    "xbox360": [1000, 500, 250],
}


class ControllerV4Tab(QWidget):

    config_changed = pyqtSignal(str, dict)
    controller_changed = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._current_id: Optional[str] = None
        self._descriptor: Optional[ControllerDescriptor] = None
        self._detected_hw_id: Optional[str] = None
        self.setLayout(QVBoxLayout())
        self._init_ui()
        QTimer.singleShot(500, self._auto_detect_startup)
        self._hotplug_timer = QTimer(self)
        self._hotplug_timer.timeout.connect(self._hotplug_scan)
        self._hotplug_timer.start(2000)

    def _init_ui(self) -> None:
        selector_row = QHBoxLayout()
        selector_row.addWidget(QLabel("Controller"))

        self.hw_combo = QComboBox()
        self._populate_selector()
        self.hw_combo.currentIndexChanged.connect(self._on_hardware_changed)
        selector_row.addWidget(self.hw_combo)

        self.detect_btn = QPushButton("Detect")
        self.detect_btn.clicked.connect(self._on_detect)
        selector_row.addWidget(self.detect_btn)

        self.detect_label = QLabel("No controller detected")
        self.detect_label.setStyleSheet("color: #888; font-size: 11px;")
        selector_row.addWidget(self.detect_label)
        selector_row.addStretch()
        self.layout().addLayout(selector_row)

        self.spec_card = QFrame()
        self.spec_card.setFrameShape(QFrame.Shape.StyledPanel)
        self.spec_card.setStyleSheet(
            "QFrame { border: 1px solid #BB00FF; border-radius: 4px; "
            "background: #0a0a0f; padding: 8px; }"
        )
        self.spec_layout = QGridLayout(self.spec_card)
        self.spec_layout.setVerticalSpacing(2)
        self.spec_layout.setHorizontalSpacing(16)
        self._build_spec_card_placeholder()
        self.layout().addWidget(self.spec_card)

        self.sub_tabs = QTabWidget()
        self.trigger_widget = TriggerConfigWidget()
        self.trigger_widget.config_changed.connect(self._on_sub_config)
        self.sub_tabs.addTab(self.trigger_widget, "Triggers")

        self.gyro_widget = GyroConfigWidget()
        self.gyro_widget.config_changed.connect(self._on_sub_config)
        self.gyro_widget.setVisible(False)
        self.sub_tabs.addTab(self.gyro_widget, "Gyro")

        self.rgb_widget = RGBPickerWidget()
        self.rgb_widget.config_changed.connect(self._on_sub_config)
        self.rgb_widget.setVisible(False)
        self.sub_tabs.addTab(self.rgb_widget, "RGB")

        self.advanced_widget = self._build_advanced_tab()
        self.sub_tabs.addTab(self.advanced_widget, "Advanced")

        self.layout().addWidget(self.sub_tabs)

        bottom_row = QHBoxLayout()
        self.apply_btn = QPushButton("Apply")
        self.apply_btn.setObjectName("applyBtn")
        self.apply_btn.clicked.connect(self._on_apply)
        bottom_row.addWidget(self.apply_btn)

        self.save_btn = QPushButton("Save Profile")
        self.save_btn.clicked.connect(self._on_save_profile)
        bottom_row.addWidget(self.save_btn)

        self.reset_btn = QPushButton("Reset to Defaults")
        self.reset_btn.clicked.connect(self._on_reset_defaults)
        bottom_row.addWidget(self.reset_btn)

        bottom_row.addStretch()
        self.layout().addLayout(bottom_row)

    def _populate_selector(self) -> None:
        self.hw_combo.clear()
        descriptors = registry.list_available()
        for desc in descriptors:
            self.hw_combo.addItem(desc.name, desc.id)
        xbox_idx = self.hw_combo.findData("xbox360")
        if xbox_idx >= 0:
            self.hw_combo.setCurrentIndex(xbox_idx)

    def _build_spec_card_placeholder(self) -> None:
        self._spec_labels: dict[str, QLabel] = {}
        fields = [
            ("Polling Rate", "--- Hz"),
            ("Joysticks", "---"),
            ("Triggers", "---"),
            ("Gyro", "---"),
            ("RGB", "---"),
            ("Battery", "---"),
            ("Weight", "---"),
            ("Extra", "---"),
        ]
        for i, (label, val) in enumerate(fields):
            lbl = QLabel(f"{label}:")
            lbl.setStyleSheet("color: #888; font-size: 11px;")
            self.spec_layout.addWidget(lbl, i // 2, (i % 2) * 2)
            val_lbl = QLabel(val)
            val_lbl.setStyleSheet("color: #00ff88; font-size: 11px;")
            self.spec_layout.addWidget(val_lbl, i // 2, (i % 2) * 2 + 1)
            self._spec_labels[label] = val_lbl

    def _build_advanced_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        cal_group = QGroupBox("Joystick Calibration")
        cal_layout = QGridLayout()
        cal_layout.addWidget(QLabel("LS Center X:"), 0, 0)
        self.ls_center_x = QLabel("0")
        self.ls_center_x.setStyleSheet("color: #00ff88;")
        cal_layout.addWidget(self.ls_center_x, 0, 1)
        cal_layout.addWidget(QLabel("LS Center Y:"), 0, 2)
        self.ls_center_y = QLabel("0")
        self.ls_center_y.setStyleSheet("color: #00ff88;")
        cal_layout.addWidget(self.ls_center_y, 0, 3)
        cal_layout.addWidget(QLabel("RS Center X:"), 1, 0)
        self.rs_center_x = QLabel("0")
        self.rs_center_x.setStyleSheet("color: #00ff88;")
        cal_layout.addWidget(self.rs_center_x, 1, 1)
        cal_layout.addWidget(QLabel("RS Center Y:"), 1, 2)
        self.rs_center_y = QLabel("0")
        self.rs_center_y.setStyleSheet("color: #00ff88;")
        cal_layout.addWidget(self.rs_center_y, 1, 3)
        self.recalibrate_btn = QPushButton("Recalibrate")
        cal_layout.addWidget(self.recalibrate_btn, 2, 0, 1, 4)
        cal_group_layout = QVBoxLayout(cal_group)
        cal_group_layout.addLayout(cal_layout)
        layout.addWidget(cal_group)

        poll_group = QGroupBox("Polling Rate")
        poll_layout = QVBoxLayout()
        rate_row = QHBoxLayout()
        rate_row.addWidget(QLabel("Rate"))
        self.poll_rate_combo = QComboBox()
        rate_row.addWidget(self.poll_rate_combo)
        poll_layout.addLayout(rate_row)
        self.auto_rate_check = QCheckBox("Auto (hardware default)")
        self.auto_rate_check.setChecked(True)
        poll_layout.addWidget(self.auto_rate_check)
        poll_group_layout = QVBoxLayout(poll_group)
        poll_group_layout.addLayout(poll_layout)
        layout.addWidget(poll_group)

        power_group = QGroupBox("Power Profile")
        power_layout = QVBoxLayout()
        power_row = QHBoxLayout()
        power_row.addWidget(QLabel("Profile"))
        self.power_combo = QComboBox()
        self.power_combo.addItems(["Performance", "Balanced", "Power Save"])
        power_row.addWidget(self.power_combo)
        power_layout.addLayout(power_row)
        self.power_rate_label = QLabel("Current: --- Hz")
        self.power_rate_label.setStyleSheet("color: #888; font-size: 11px;")
        power_layout.addWidget(self.power_rate_label)
        power_group_layout = QVBoxLayout(power_group)
        power_group_layout.addLayout(power_layout)
        layout.addWidget(power_group)

        layout.addStretch()
        return w

    def _update_spec_card(self, desc: ControllerDescriptor) -> None:
        self._spec_labels["Polling Rate"].setText(f"{desc.polling_rate_hz} Hz")
        jstype = desc.joystick_type
        if desc.anti_drift:
            jstype += " anti-drift"
        self._spec_labels["Joysticks"].setText(f"{desc.joystick_count}x {jstype}")
        trig = desc.trigger_type
        if desc.has_trigger_stops:
            trig += f" + {'Mech' if desc.trigger_stops_mechanical else 'Soft'}"
        self._spec_labels["Triggers"].setText(f"{desc.trigger_count}x {trig}")
        gyro_txt = f"{desc.gyro_axes}-axis" if desc.has_gyro else "None"
        self._spec_labels["Gyro"].setText(gyro_txt)
        rgb_txt = f"Yes ({desc.rgb_zones} zones)" if desc.has_rgb else "No"
        self._spec_labels["RGB"].setText(rgb_txt)
        bat = f"{desc.battery_capacity_mah} mAh" if desc.battery_capacity_mah > 0 else "Wired"
        self._spec_labels["Battery"].setText(bat)
        self._spec_labels["Weight"].setText(f"{desc.weight_g:.0f}g")
        extras = []
        if desc.has_extra_buttons:
            extras.append(f"{desc.extra_button_count} paddles")
        if desc.has_headphone_jack:
            extras.append("headphone")
        if desc.has_dock:
            extras.append("dock")
        self._spec_labels["Extra"].setText(", ".join(extras) if extras else "None")

    def _on_hardware_changed(self, idx: int) -> None:
        if idx < 0:
            return
        hw_id = self.hw_combo.itemData(idx)
        if hw_id is None:
            return
        self._current_id = hw_id
        try:
            desc = registry.get_descriptor(hw_id)
            self._descriptor = desc
        except KeyError:
            return

        self._update_spec_card(desc)

        gyro_idx = self.sub_tabs.indexOf(self.gyro_widget)
        if gyro_idx >= 0:
            self.sub_tabs.setTabVisible(gyro_idx, desc.has_gyro)

        rgb_idx = self.sub_tabs.indexOf(self.rgb_widget)
        if rgb_idx >= 0:
            self.sub_tabs.setTabVisible(rgb_idx, desc.has_rgb)

        self.rgb_widget.set_zone_count(desc.rgb_zones)

        rates = _AVAILABLE_RATES.get(hw_id, [1000, 500])
        self.poll_rate_combo.clear()
        self.poll_rate_combo.addItems(str(r) for r in rates)
        self.auto_rate_check.setChecked(True)

        profile = registry.load_profile(hw_id)
        if profile:
            self.load_config(profile)

        self.controller_changed.emit(hw_id)

    def current_controller_type(self) -> str:
        hw_id = self.hw_combo.currentData() or "xbox360"
        _VIRTUAL_MAP = {
            "g7_pro_8k": "xbox360",
            "cyclone_2": "xbox360",
            "ds4": "dualshock4",
            "dualsense_edge": "dualsense_edge",
            "dualsense": "dualsense",
            "xbox360": "xbox360",
        }
        return _VIRTUAL_MAP.get(hw_id, "xbox360")

    def _on_detect(self) -> None:
        import evdev
        for path in evdev.list_devices():
            hw_id = registry.detect_physical(path)
            if hw_id is not None:
                desc = registry.get_descriptor(hw_id)
                self.detect_label.setText(f"Detected: {desc.name}")
                self.detect_label.setStyleSheet("color: #00ff88; font-size: 11px;")
                self._detected_hw_id = hw_id
                return
        self.detect_label.setText("No controller detected")
        self.detect_label.setStyleSheet("color: #888; font-size: 11px;")
        self._detected_hw_id = None

    def _auto_detect_startup(self) -> None:
        self._on_detect()

    def _hotplug_scan(self) -> None:
        import evdev
        devices = evdev.list_devices()
        found = None
        for path in devices:
            hw_id = registry.detect_physical(path)
            if hw_id is not None:
                found = hw_id
                break

        if found is None and self._detected_hw_id is not None:
            self._detected_hw_id = None
            self.detect_label.setText("Disconnected")
            self.detect_label.setStyleSheet("color: #ff4444; font-size: 11px;")

        elif found is not None and self._detected_hw_id is None:
            desc = registry.get_descriptor(found)
            self.detect_label.setText(f"Detected: {desc.name}")
            self.detect_label.setStyleSheet("color: #00ff88; font-size: 11px;")
            self._detected_hw_id = found

    def _on_sub_config(self, _: Any) -> None:
        pass

    def _on_apply(self) -> None:
        cfg = self.get_config()
        self.config_changed.emit(self._current_id or "", cfg)

    def _on_save_profile(self) -> None:
        if self._current_id is None:
            return
        cfg = self.get_config()
        registry.save_profile(self._current_id, cfg)

    def _on_reset_defaults(self) -> None:
        from nocrosshair.features.triggers import TriggerConfig as _TC
        from nocrosshair.features.gyro import GyroConfig as _GC
        from nocrosshair.features.rgb import RGBConfig as _RC
        self.trigger_widget.set_config(_TC())
        self.gyro_widget.set_config(_GC())
        self.rgb_widget.set_config(_RC())
        self.auto_rate_check.setChecked(True)
        self.power_combo.setCurrentIndex(1)

    def set_controller(self, controller_id: str) -> None:
        idx = self.hw_combo.findData(controller_id)
        if idx >= 0:
            self.hw_combo.setCurrentIndex(idx)

    def get_config(self) -> dict:
        cfg: dict[str, Any] = {}
        tc = self.trigger_widget.get_config()
        cfg.update(tc.to_dict())
        gc = self.gyro_widget.get_config()
        cfg.update(gc.to_dict())
        rc = self.rgb_widget.get_config()
        cfg.update(rc.to_dict())
        cfg["polling_rate_hz"] = int(self.poll_rate_combo.currentText()) if self.poll_rate_combo.count() > 0 else 1000
        cfg["polling_auto"] = self.auto_rate_check.isChecked()
        cfg["power_profile"] = self.power_combo.currentText().lower()
        return cfg

    def load_config(self, config: dict) -> None:
        if "trigger_mode" in config:
            self.trigger_widget.load_from_dict(config)
        if "gyro_enabled" in config:
            self.gyro_widget.load_from_dict(config)
        if "effect" in config and "brightness" in config:
            self.rgb_widget.load_from_dict(config)
        if "polling_rate_hz" in config:
            rate_str = str(config["polling_rate_hz"])
            idx = self.poll_rate_combo.findText(rate_str)
            if idx >= 0:
                self.poll_rate_combo.setCurrentIndex(idx)
        if "polling_auto" in config:
            self.auto_rate_check.setChecked(bool(config["polling_auto"]))
        if "power_profile" in config:
            pwr = str(config["power_profile"]).capitalize()
            idx = self.power_combo.findText(pwr)
            if idx >= 0:
                self.power_combo.setCurrentIndex(idx)
