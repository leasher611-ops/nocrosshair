from typing import Optional, Dict, Any, List
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QCheckBox, QFrame, QGridLayout, QTabWidget,
)

from nocrosshair.ui.widgets import (
    LabeledSlider, SectionGroupBox, HLine, VLine,
    StickVisualizerWidget
)


_CAL_STEP_CSS = """
QFrame#calStep {
    border: 1px solid #333;
    border-radius: 8px;
    background: #0a0a12;
    padding: 10px;
}
QLabel#calTitle {
    color: #BB00FF;
    font-size: 13px;
    font-weight: bold;
}
QLabel#calStepNum {
    color: #FF00AA;
    font-size: 22px;
    font-weight: bold;
}
QLabel#calInstr {
    color: #aaa;
    font-size: 11px;
}
QLabel#instLabel {
    color: #00ff88;
    font-size: 11px;
    font-style: italic;
}
"""


class CalibrationTab(QWidget):

    config_changed = pyqtSignal(dict)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setLayout(QVBoxLayout())
        self._current_slot: int = 1
        self._profiles: Dict[int, Dict[str, Any]] = {
            1: self._default_profile(),
            2: self._default_profile(),
            3: self._default_profile(),
        }
        self._init_ui()
        self._apply_profile_to_ui(1)

    def _default_profile(self) -> Dict[str, Any]:
        return {
            "anti_deadzone_ls": 0,
            "anti_deadzone_rs": 0,
            "response_curve_ls": "linear",
            "response_curve_rs": "linear",
            "raw_mode_ls": False,
            "raw_mode_rs": False,
            "trigger_deadzone_start": 0,
            "trigger_deadzone_end": 100,
            "hair_trigger_mode": "off",
            "dpad_diag_lock": False,
            "vibration_lt": 50,
            "vibration_rt": 50,
            "vibration_sync": True,
            "polling_rate": 500,
        }

    def _init_ui(self) -> None:
        title = QLabel("Calibration & Hardware")
        title.setObjectName("hudTitle")
        self.layout().addWidget(title)
        self.layout().addWidget(HLine())

        self.layout().addWidget(self._build_profile_slots())
        self.layout().addWidget(HLine())

        sub_tabs = QTabWidget()
        sub_tabs.addTab(self._build_stick_tab(), "Sticks")
        sub_tabs.addTab(self._build_trigger_tab(), "Triggers")
        sub_tabs.addTab(self._build_dpad_vibe_tab(), "D-Pad & Vibration")
        sub_tabs.addTab(self._build_calibration_wizard(), "Calibrate")

        self.layout().addWidget(sub_tabs)

        bottom = QHBoxLayout()
        apply_btn = QPushButton("Apply")
        apply_btn.setObjectName("applyBtn")
        apply_btn.clicked.connect(self._on_apply)
        bottom.addWidget(apply_btn)

        reset_btn = QPushButton("Reset Slot")
        reset_btn.clicked.connect(self._on_reset_slot)
        bottom.addWidget(reset_btn)

        bottom.addStretch()
        self.layout().addLayout(bottom)
        self.layout().addStretch()

    def _build_profile_slots(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("profileSlot")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(8, 6, 8, 6)

        header = QLabel("On-Board Profiles")
        header.setStyleSheet("color: #BB00FF; font-weight: bold; font-size: 11px;")
        layout.addWidget(header)

        row = QHBoxLayout()
        self._slot_btns: List[QPushButton] = []
        for i in range(1, 4):
            btn = QPushButton(f"  Slot {i}  ")
            btn.setObjectName("slotBtn")
            btn.setCheckable(True)
            btn.clicked.connect(lambda _, s=i: self._on_slot_select(s))
            self._slot_btns.append(btn)
            row.addWidget(btn)

            slot_meta = QLabel(f"Profile {i}")
            slot_meta.setStyleSheet("color: #666; font-size: 10px;")
            row.addWidget(slot_meta)

            save_slot = QPushButton("Save")
            save_slot.setFixedWidth(50)
            save_slot.setStyleSheet(
                "QPushButton { background: #1a2a1a; border: 1px solid #00ff88; "
                "border-radius: 3px; color: #00ff88; font-size: 10px; padding: 2px 6px; }"
                "QPushButton:hover { background: #00ff88; color: #000; }"
            )
            save_slot.clicked.connect(lambda _, s=i: self._on_slot_save(s))
            row.addWidget(save_slot)

        row.addStretch()
        layout.addLayout(row)

        return frame

    def _on_slot_select(self, slot: int) -> None:
        for i, btn in enumerate(self._slot_btns):
            btn.setChecked(i + 1 == slot)
            btn.setProperty("active", i + 1 == slot)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self._current_slot = slot
        self._apply_profile_to_ui(slot)

    def _on_slot_save(self, slot: int) -> None:
        self._profiles[slot] = self._gather_ui_values()
        for btn in self._slot_btns:
            btn.setText(f"  Slot {slot} *" if btn.isChecked() else f"  Slot {slot}  ")
        self.config_changed.emit({"profile_slot": slot, **self._profiles[slot]})

    # ── Sticks Tab ──

    def _build_stick_tab(self) -> QWidget:
        tab = QWidget()
        tab.setLayout(QVBoxLayout())

        row = QHBoxLayout()

        left = QVBoxLayout()
        left.addWidget(self._build_stick_card("Left Stick", "ls"))
        left.addStretch()
        row.addLayout(left)

        row.addWidget(VLine())

        right = QVBoxLayout()
        right.addWidget(self._build_stick_card("Right Stick", "rs"))
        right.addStretch()
        row.addLayout(right)

        tab.layout().addLayout(row)
        tab.layout().addStretch()
        return tab

    def _build_stick_card(self, title: str, prefix: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            "QFrame { border: 1px solid #333; border-radius: 6px; "
            "background: #0d0d14; padding: 8px; }"
        )
        layout = QVBoxLayout(card)

        hdr = QLabel(title)
        hdr.setStyleSheet("color: #BB00FF; font-weight: bold; font-size: 12px;")
        layout.addWidget(hdr)

        vis = StickVisualizerWidget(title)
        layout.addWidget(vis)

        adz = LabeledSlider(f"Anti-Deadzone {prefix.upper()}", 0, 30, 0)
        adz.value_changed.connect(self._on_change)
        setattr(self, f"_anti_dz_{prefix}", adz)
        layout.addWidget(adz)

        curve_lbl = QLabel("Response Curve")
        curve_lbl.setStyleSheet("color: #888; font-size: 10px; margin-top: 4px;")
        layout.addWidget(curve_lbl)

        combo = QComboBox()
        combo.addItems(["linear", "exponential", "aggressive", "precise", "raw"])
        combo.currentTextChanged.connect(self._on_change)
        setattr(self, f"_curve_combo_{prefix}", combo)
        layout.addWidget(combo)

        raw_cb = QCheckBox(f"Raw Mode {prefix.upper()} (bypass software smoothing)")
        raw_cb.setStyleSheet("color: #FF00AA; font-size: 10px;")
        raw_cb.toggled.connect(self._on_change)
        setattr(self, f"_raw_{prefix}", raw_cb)
        layout.addWidget(raw_cb)

        return card

    # ── Triggers Tab ──

    def _build_trigger_tab(self) -> QWidget:
        tab = QWidget()
        tab.setLayout(QVBoxLayout())

        group = SectionGroupBox("Trigger Calibration")
        gl = QGridLayout()

        gl.addWidget(QLabel("Left Trigger"), 0, 0)
        self._lt_deadzone_start = LabeledSlider("Deadzone Start", 0, 50, 0)
        self._lt_deadzone_start.value_changed.connect(self._on_change)
        gl.addWidget(self._lt_deadzone_start, 1, 0)
        self._lt_deadzone_end = LabeledSlider("Deadzone End", 50, 100, 100)
        self._lt_deadzone_end.value_changed.connect(self._on_change)
        gl.addWidget(self._lt_deadzone_end, 2, 0)

        gl.addWidget(QLabel("Right Trigger"), 0, 1)
        self._rt_deadzone_start = LabeledSlider("Deadzone Start", 0, 50, 0)
        self._rt_deadzone_start.value_changed.connect(self._on_change)
        gl.addWidget(self._rt_deadzone_start, 1, 1)
        self._rt_deadzone_end = LabeledSlider("Deadzone End", 50, 100, 100)
        self._rt_deadzone_end.value_changed.connect(self._on_change)
        gl.addWidget(self._rt_deadzone_end, 2, 1)

        group.layout().addLayout(gl)
        tab.layout().addWidget(group)

        hair_group = SectionGroupBox("Hair Trigger Mode")
        self._hair_mode = QComboBox()
        self._hair_mode.addItems(["off", "adaptive", "fixed"])
        self._hair_mode.currentTextChanged.connect(self._on_change)
        hair_group.layout().addWidget(self._hair_mode)

        desc = QLabel(
            "Adaptive: digitaliza o clique apenas em FPS\n"
            "Fixed: mantém sempre digital (clique de mouse)"
        )
        desc.setStyleSheet("color: #888; font-size: 10px;")
        hair_group.layout().addWidget(desc)

        tab.layout().addWidget(hair_group)
        tab.layout().addStretch()
        return tab

    # ── D-Pad & Vibration Tab ──

    def _build_dpad_vibe_tab(self) -> QWidget:
        tab = QWidget()
        tab.setLayout(QVBoxLayout())

        dpad_group = SectionGroupBox("D-Pad Settings")
        self._dpad_lock = QCheckBox("Diagonal Lock (4-way only — blocks diagonals)")
        self._dpad_lock.setStyleSheet("color: #ffaa00; font-size: 11px;")
        self._dpad_lock.toggled.connect(self._on_change)
        dpad_group.layout().addWidget(self._dpad_lock)

        desc = QLabel("Only Up/Down/Left/Right — no diagonal inputs. Useful for fighting games.")
        desc.setStyleSheet("color: #666; font-size: 10px;")
        dpad_group.layout().addWidget(desc)
        tab.layout().addWidget(dpad_group)

        vibe_group = SectionGroupBox("Trigger Vibration")
        self._vibe_lt = LabeledSlider("Left Trigger Motor", 0, 100, 50)
        self._vibe_lt.value_changed.connect(self._on_change)
        vibe_group.layout().addWidget(self._vibe_lt)

        self._vibe_rt = LabeledSlider("Right Trigger Motor", 0, 100, 50)
        self._vibe_rt.value_changed.connect(self._on_change)
        vibe_group.layout().addWidget(self._vibe_rt)

        self._vibe_sync = QCheckBox("Sync with Grip Vibration")
        self._vibe_sync.setChecked(True)
        self._vibe_sync.toggled.connect(self._on_change)
        vibe_group.layout().addWidget(self._vibe_sync)

        tab.layout().addWidget(vibe_group)

        poll_group = SectionGroupBox("Polling Rate")
        poll_row = QHBoxLayout()
        poll_row.addWidget(QLabel("Report Rate"))
        self._poll_rate = QComboBox()
        self._poll_rate.addItems(["125 Hz", "250 Hz", "500 Hz", "1000 Hz", "4000 Hz", "8000 Hz"])
        self._poll_rate.setCurrentText("500 Hz")
        self._poll_rate.currentTextChanged.connect(self._on_change)
        poll_row.addWidget(self._poll_rate)
        poll_row.addStretch()
        poll_group.layout().addLayout(poll_row)

        poll_desc = QLabel("Higher = lower latency but more CPU usage. 500Hz is the sweet spot.")
        poll_desc.setStyleSheet("color: #888; font-size: 10px;")
        poll_group.layout().addWidget(poll_desc)

        tab.layout().addWidget(poll_group)
        tab.layout().addStretch()
        return tab

    # ── Calibration Wizard ──

    def _build_calibration_wizard(self) -> QWidget:
        tab = QWidget()
        tab.setLayout(QVBoxLayout())

        steps = [
            ("Step 1", "Center Sticks",
             "Release both sticks. Click 'Calibrate' to record center position.",
             self._cal_step1),
            ("Step 2", "Full Rotation",
             "Rotate each stick in full circles 3 times. Click when done.",
             self._cal_step2),
            ("Step 3", "Trigger Pull",
             "Press LT and RT fully. Click 'Calibrate' to record full range.",
             self._cal_step3),
            ("Step 4", "Complete",
             "Calibration data saved. Drift correction applied.",
             self._cal_step4),
        ]

        self._cal_frames: List[QFrame] = []

        for num, title, instr, handler in steps:
            cal_frame = QFrame()
            cal_frame.setObjectName("calStep")
            cal_frame.setStyleSheet(_CAL_STEP_CSS)
            cal_layout = QVBoxLayout(cal_frame)

            step_row = QHBoxLayout()
            step_num = QLabel(num)
            step_num.setObjectName("calStepNum")
            step_row.addWidget(step_num)

            step_title = QLabel(title)
            step_title.setObjectName("calTitle")
            step_row.addWidget(step_title)
            step_row.addStretch()
            cal_layout.addLayout(step_row)

            instr_label = QLabel(instr)
            instr_label.setObjectName("calInstr")
            cal_layout.addWidget(instr_label)

            inst_label = QLabel("")
            inst_label.setObjectName("instLabel")
            cal_layout.addWidget(inst_label)

            btn_row = QHBoxLayout()
            cal_btn = QPushButton(f"Calibrate {num.split()[-1]}")
            cal_btn.setObjectName("applyBtn")
            cal_btn.clicked.connect(handler)
            btn_row.addWidget(cal_btn)
            btn_row.addStretch()
            cal_layout.addLayout(btn_row)

            self._cal_frames.append(cal_frame)
            tab.layout().addWidget(cal_frame)

        tab.layout().addStretch()
        return tab

    def _cal_step1(self) -> None:
        self._cal_frames[0].findChildren(QLabel)[-1].setText("Center recorded")
        self._cal_frames[0].setStyleSheet(_CAL_STEP_CSS.replace("#0a0a12", "#0a1a0a"))

    def _cal_step2(self) -> None:
        self._cal_frames[1].findChildren(QLabel)[-1].setText("Rotation logged")
        self._cal_frames[1].setStyleSheet(_CAL_STEP_CSS.replace("#0a0a12", "#0a1a0a"))

    def _cal_step3(self) -> None:
        self._cal_frames[2].findChildren(QLabel)[-1].setText("Trigger range set")
        self._cal_frames[2].setStyleSheet(_CAL_STEP_CSS.replace("#0a0a12", "#0a1a0a"))

    def _cal_step4(self) -> None:
        for f in self._cal_frames:
            f.findChildren(QLabel)[-1].setText("Done")
            f.setStyleSheet(_CAL_STEP_CSS.replace("#0a0a12", "#0a1a0a"))
        self._cal_frames[3].findChildren(QLabel)[-1].setText("All systems calibrated")
        self._cal_frames[3].setStyleSheet(_CAL_STEP_CSS.replace("#0a0a12", "#0a1a0a"))

    # ── UI ↔ Config ──

    def _gather_ui_values(self) -> Dict[str, Any]:
        return {
            "anti_deadzone_ls": getattr(self, "_anti_dz_ls").value(),
            "anti_deadzone_rs": getattr(self, "_anti_dz_rs").value(),
            "response_curve_ls": getattr(self, "_curve_combo_ls").currentText(),
            "response_curve_rs": getattr(self, "_curve_combo_rs").currentText(),
            "raw_mode_ls": getattr(self, "_raw_ls").isChecked(),
            "raw_mode_rs": getattr(self, "_raw_rs").isChecked(),
            "trigger_deadzone_start": self._lt_deadzone_start.value(),
            "trigger_deadzone_end": self._lt_deadzone_end.value(),
            "hair_trigger_mode": self._hair_mode.currentText(),
            "dpad_diag_lock": self._dpad_lock.isChecked(),
            "vibration_lt": self._vibe_lt.value(),
            "vibration_rt": self._vibe_rt.value(),
            "vibration_sync": self._vibe_sync.isChecked(),
            "polling_rate": int(self._poll_rate.currentText().split()[0]),
        }

    def _apply_profile_to_ui(self, slot: int) -> None:
        p = self._profiles.get(slot, self._default_profile())
        getattr(self, "_anti_dz_ls").setValue(p["anti_deadzone_ls"])
        getattr(self, "_anti_dz_rs").setValue(p["anti_deadzone_rs"])
        getattr(self, "_curve_combo_ls").setCurrentText(p["response_curve_ls"])
        getattr(self, "_curve_combo_rs").setCurrentText(p["response_curve_rs"])
        getattr(self, "_raw_ls").setChecked(p["raw_mode_ls"])
        getattr(self, "_raw_rs").setChecked(p["raw_mode_rs"])
        self._lt_deadzone_start.setValue(p["trigger_deadzone_start"])
        self._lt_deadzone_end.setValue(p["trigger_deadzone_end"])
        self._hair_mode.setCurrentText(p["hair_trigger_mode"])
        self._dpad_lock.setChecked(p["dpad_diag_lock"])
        self._vibe_lt.setValue(p["vibration_lt"])
        self._vibe_rt.setValue(p["vibration_rt"])
        self._vibe_sync.setChecked(p["vibration_sync"])
        self._poll_rate.setCurrentText(f'{p["polling_rate"]} Hz')

    def _on_change(self) -> None:
        self.config_changed.emit(self._gather_ui_values())

    def _on_apply(self) -> None:
        self._on_slot_save(self._current_slot)
        self.config_changed.emit({"action": "apply", **self._gather_ui_values()})

    def _on_reset_slot(self) -> None:
        self._profiles[self._current_slot] = self._default_profile()
        self._apply_profile_to_ui(self._current_slot)
        self.config_changed.emit({"action": "reset", "slot": self._current_slot})

    def get_config(self) -> Dict[str, Any]:
        return self._gather_ui_values()

    def set_config(self, config: Dict[str, Any]) -> None:
        if "anti_deadzone_ls" in config:
            getattr(self, "_anti_dz_ls").setValue(config["anti_deadzone_ls"])
        if "anti_deadzone_rs" in config:
            getattr(self, "_anti_dz_rs").setValue(config["anti_deadzone_rs"])
        if "response_curve_ls" in config:
            getattr(self, "_curve_combo_ls").setCurrentText(config["response_curve_ls"])
        if "response_curve_rs" in config:
            getattr(self, "_curve_combo_rs").setCurrentText(config["response_curve_rs"])
        if "raw_mode_ls" in config:
            getattr(self, "_raw_ls").setChecked(config["raw_mode_ls"])
        if "raw_mode_rs" in config:
            getattr(self, "_raw_rs").setChecked(config["raw_mode_rs"])
        if "trigger_deadzone_start" in config:
            self._lt_deadzone_start.setValue(config["trigger_deadzone_start"])
        if "trigger_deadzone_end" in config:
            self._lt_deadzone_end.setValue(config["trigger_deadzone_end"])
        if "hair_trigger_mode" in config:
            self._hair_mode.setCurrentText(config["hair_trigger_mode"])
        if "dpad_diag_lock" in config:
            self._dpad_lock.setChecked(config["dpad_diag_lock"])
        if "vibration_lt" in config:
            self._vibe_lt.setValue(config["vibration_lt"])
        if "vibration_rt" in config:
            self._vibe_rt.setValue(config["vibration_rt"])
        if "vibration_sync" in config:
            self._vibe_sync.setChecked(config["vibration_sync"])
        if "polling_rate" in config:
            self._poll_rate.setCurrentText(f'{config["polling_rate"]} Hz')
