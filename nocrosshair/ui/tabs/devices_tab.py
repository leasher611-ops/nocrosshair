from typing import Dict, Any, List, Optional
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QGroupBox, QGridLayout, QTextEdit, QSplitter, QFrame, QMessageBox,
    QCheckBox
)
from PyQt6.QtGui import QFont

from nocrosshair.ui.widgets import HLine, SectionGroupBox
from nocrosshair.core.device_manager import device_manager


CONTROLLER_TYPES = [
    ("xbox360", "Xbox 360", 0x045E, 0x028E),
    ("xboxone", "Xbox One", 0x045E, 0x02EA),
    ("dualshock4", "DualShock 4", 0x054C, 0x09CC),
    ("dualshock3", "DualShock 3", 0x054C, 0x0268),
    ("dualsense_edge", "DualSense Edge", 0x054C, 0x0DF2),
    ("switchpro", "Switch Pro", 0x057E, 0x2009),
]


class SlotCard(QFrame):
    slot_changed = pyqtSignal(str, str, object)

    def __init__(self, slot_name: str, ctrl_type: str = "xbox360", slot_id: int = 0, parent=None):
        super().__init__(parent)
        self.slot_name = slot_name
        self.slot_id = slot_id
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setStyleSheet("""
            SlotCard {
                background-color: #1a1a1a;
                border: 1px solid #333;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        self._init_ui(ctrl_type)

    def _init_ui(self, ctrl_type: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        header = QHBoxLayout()
        self.name_label = QLabel(self.slot_name)
        self.name_label.setFont(QFont("monospace", 10, QFont.Weight.Bold))
        self.name_label.setStyleSheet("color: #00ff88;")
        header.addWidget(self.name_label)

        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("color: #ff3333; font-size: 16px;")
        header.addWidget(self.status_dot)
        header.addStretch()
        layout.addLayout(header)

        type_row = QHBoxLayout()
        type_row.addWidget(QLabel("Type:"))
        self.type_combo = QComboBox()
        for tid, tname, _, _ in CONTROLLER_TYPES:
            self.type_combo.addItem(tname, tid)
        idx = self.type_combo.findData(ctrl_type)
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        type_row.addWidget(self.type_combo)
        type_row.addStretch()
        layout.addLayout(type_row)

        info_row = QHBoxLayout()
        self.info_label = QLabel("Device: None")
        self.info_label.setStyleSheet("color: #888; font-size: 9px;")
        info_row.addWidget(self.info_label)
        info_row.addStretch()
        layout.addLayout(info_row)

        btn_row = QHBoxLayout()
        self.create_btn = QPushButton("Create")
        self.create_btn.setStyleSheet("""
            QPushButton {
                background-color: #00ff88; color: #000; border: none;
                padding: 4px 12px; border-radius: 4px; font-weight: bold;
            }
            QPushButton:hover { background-color: #00cc6a; }
        """)
        self.create_btn.clicked.connect(self._on_create)
        btn_row.addWidget(self.create_btn)

        self.remove_btn = QPushButton("Remove")
        self.remove_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff4444; color: #fff; border: none;
                padding: 4px 12px; border-radius: 4px; font-weight: bold;
            }
            QPushButton:hover { background-color: #cc0000; }
        """)
        self.remove_btn.clicked.connect(self._on_remove)
        btn_row.addWidget(self.remove_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _on_type_changed(self, idx):
        ctrl_type = self.type_combo.currentData()
        self.slot_changed.emit(self.slot_name, "type", ctrl_type)

    def _on_create(self):
        ctrl_type = self.type_combo.currentData()
        self.slot_changed.emit(self.slot_name, "create", ctrl_type)

    def _on_remove(self):
        self.slot_changed.emit(self.slot_name, "remove", None)

    def update_status(self, active: bool):
        color = "#00ff88" if active else "#ff3333"
        self.status_dot.setStyleSheet(f"color: {color}; font-size: 16px;")

    def update_device_info(self, info: str):
        self.info_label.setText(info)


class DevicesTab(QWidget):
    config_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._slots: Dict[str, SlotCard] = {}
        self._slot_counter = 0
        self.setLayout(QVBoxLayout())
        self._init_ui()

    def _init_ui(self):
        title = QLabel("Device Manager")
        title.setObjectName("hudTitle")
        self.layout().addWidget(title)
        self.layout().addWidget(HLine())

        toolbar = QHBoxLayout()
        self.add_slot_btn = QPushButton("+ Add Slot")
        self.add_slot_btn.setStyleSheet("""
            QPushButton {
                background-color: #333; color: #00ff88;
                border: 1px solid #00ff88; padding: 6px 16px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #00ff88; color: #000; }
        """)
        self.add_slot_btn.clicked.connect(self._add_slot)
        toolbar.addWidget(self.add_slot_btn)

        self.create_all_btn = QPushButton("Create All")
        self.create_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #00ff88; color: #000; border: none;
                padding: 6px 16px; border-radius: 4px; font-weight: bold;
            }
            QPushButton:hover { background-color: #00cc6a; }
        """)
        self.create_all_btn.clicked.connect(self._create_all)
        toolbar.addWidget(self.create_all_btn)

        self.destroy_all_btn = QPushButton("Destroy All")
        self.destroy_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff4444; color: #fff; border: none;
                padding: 6px 16px; border-radius: 4px; font-weight: bold;
            }
            QPushButton:hover { background-color: #cc0000; }
        """)
        self.destroy_all_btn.clicked.connect(self._destroy_all)
        toolbar.addWidget(self.destroy_all_btn)

        toolbar.addStretch()

        self.slot_count_label = QLabel("0/4 slots used")
        self.slot_count_label.setStyleSheet("color: #888;")
        toolbar.addWidget(self.slot_count_label)

        self.layout().addLayout(toolbar)

        self.slots_container = QVBoxLayout()
        self.layout().addLayout(self.slots_container)
        self.layout().addStretch()

        self._add_slot()

    def _add_slot(self):
        if len(self._slots) >= 4:
            QMessageBox.warning(self, "Limit", "Maximum 4 device slots.")
            return

        self._slot_counter += 1
        name = f"Slot {self._slot_counter}"
        card = SlotCard(name, "xbox360", self._slot_counter)
        card.slot_changed.connect(self._on_slot_action)
        self._slots[name] = card
        self.slots_container.addWidget(card)
        self._update_counts()

    def _remove_slot(self, name: str):
        card = self._slots.pop(name, None)
        if card:
            device_manager.remove_device(name)
            self.slots_container.removeWidget(card)
            card.deleteLater()
            self._update_counts()

    def _on_slot_action(self, slot_name: str, action: str, data):
        if action == "remove":
            self._remove_slot(slot_name)
        elif action == "create":
            ctrl = device_manager.create_device(slot_name, data)
            card = self._slots.get(slot_name)
            if card:
                card.update_status(ctrl is not None)
                card.update_device_info(f"Virtual: {data}")
        elif action == "type":
            ctrl = device_manager.get_device(slot_name)
            if ctrl:
                try:
                    ctrl.change_type(data)
                except Exception as e:
                    QMessageBox.warning(self, "Error", str(e))

    def _create_all(self):
        for name, card in self._slots.items():
            ctrl_type = card.type_combo.currentData()
            ctrl = device_manager.create_device(name, ctrl_type)
            card.update_status(ctrl is not None)
            card.update_device_info(f"Virtual: {ctrl_type}")

    def _destroy_all(self):
        for name in list(self._slots.keys()):
            device_manager.remove_device(name)
            card = self._slots.get(name)
            if card:
                card.update_status(False)
                card.update_device_info("Device: None")

    def _update_counts(self):
        count = len(self._slots)
        self.slot_count_label.setText(f"{count}/4 slots used")

    def get_config(self) -> Dict[str, Any]:
        slots = {}
        for name, card in self._slots.items():
            slots[name] = {
                "type": card.type_combo.currentData(),
                "created": device_manager.get_device(name) is not None,
            }
        return {"device_slots": slots}

    def set_config(self, config: Dict[str, Any]):
        slots = config.get("device_slots", {})
        for name, slot_cfg in slots.items():
            card = self._slots.get(name)
            if card:
                idx = card.type_combo.findData(slot_cfg.get("type", "xbox360"))
                if idx >= 0:
                    card.type_combo.setCurrentIndex(idx)
