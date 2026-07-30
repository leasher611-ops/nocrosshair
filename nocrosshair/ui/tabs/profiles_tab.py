from typing import Dict, Any
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QLineEdit
)

from nocrosshair.ui.widgets import HLine, SectionGroupBox

class ProfilesTab(QWidget):

    load_requested = pyqtSignal(str)
    save_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)
    export_requested = pyqtSignal(str)
    import_requested = pyqtSignal()
    slot_assign_requested = pyqtSignal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.slot_fields = {}
        self.setLayout(QVBoxLayout())
        self._init_ui()

    def _init_ui(self) -> None:
        title = QLabel("Profiles Management")
        title.setObjectName("hudTitle")
        self.layout().addWidget(title)
        self.layout().addWidget(HLine())

        current_group = SectionGroupBox("Current Profile")
        current_layout = QVBoxLayout()

        current_label = QLabel("Active Profile:")
        self.current_profile_label = QLabel("Default")
        self.current_profile_label.setStyleSheet("color: #00ff88")

        current_layout.addWidget(current_label)
        current_layout.addWidget(self.current_profile_label)

        name_layout = QHBoxLayout()
        name_label = QLabel("Profile Name:")
        name_label.setMinimumWidth(100)
        self.profile_name_edit = QLineEdit("Default")
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.profile_name_edit)
        current_layout.addLayout(name_layout)

        current_group.layout().addLayout(current_layout)
        self.layout().addWidget(current_group)

        list_group = SectionGroupBox("Available Profiles")
        list_layout = QVBoxLayout()

        self.profiles_list = QListWidget()
        self.profiles_list.currentTextChanged.connect(self._on_profile_selected)
        list_layout.addWidget(self.profiles_list)

        buttons_layout = QHBoxLayout()
        self.load_button = QPushButton("Load")
        self.save_button = QPushButton("Save")
        self.delete_button = QPushButton("Delete")
        self.load_button.clicked.connect(self._emit_load)
        self.save_button.clicked.connect(self._emit_save)
        self.delete_button.clicked.connect(self._emit_delete)
        buttons_layout.addWidget(self.load_button)
        buttons_layout.addWidget(self.save_button)
        buttons_layout.addWidget(self.delete_button)

        list_layout.addLayout(buttons_layout)

        list_group.layout().addLayout(list_layout)
        self.layout().addWidget(list_group)

        slots_group = SectionGroupBox("Quick Access Slots")
        slots_layout = QVBoxLayout()

        slots_label = QLabel("Assign profiles to slots for quick switching")
        slots_label.setStyleSheet("color: #888888")
        slots_layout.addWidget(slots_label)

        for i in range(1, 5):
            slot_layout = QHBoxLayout()
            slot_label = QLabel(f"Slot {i}:")
            slot_label.setMinimumWidth(60)
            slot_combo = QLineEdit()
            slot_combo.setReadOnly(True)
            slot_combo.setText("(Empty)")
            self.slot_fields[i] = slot_combo
            slot_layout.addWidget(slot_label)
            slot_layout.addWidget(slot_combo)
            slot_btn = QPushButton("Assign")
            slot_btn.clicked.connect(lambda checked=False, slot=i: self._emit_slot_assign(slot))
            slot_layout.addWidget(slot_btn)
            clear_btn = QPushButton("Clear")
            clear_btn.clicked.connect(lambda checked=False, slot=i: self._emit_slot_clear(slot))
            slot_layout.addWidget(clear_btn)
            slots_layout.addLayout(slot_layout)

        slots_group.layout().addLayout(slots_layout)
        self.layout().addWidget(slots_group)

        io_group = SectionGroupBox("Import / Export")
        io_layout = QHBoxLayout()

        self.import_button = QPushButton("Import Profile")
        self.export_button = QPushButton("Export Profile")
        cloud_btn = QPushButton("Cloud Sync (Coming Soon)")
        cloud_btn.setEnabled(False)

        self.import_button.clicked.connect(self.import_requested.emit)
        self.export_button.clicked.connect(self._emit_export)

        io_layout.addWidget(self.import_button)
        io_layout.addWidget(self.export_button)
        io_layout.addWidget(cloud_btn)
        io_layout.addStretch()

        io_group.layout().addLayout(io_layout)
        self.layout().addWidget(io_group)

        self.layout().addStretch()

    def get_config(self) -> Dict[str, Any]:
        return {
            "active_profile": self.current_profile_label.text(),
            "profile_name": self.profile_name_edit.text().strip(),
            "slots": {slot: field.text() for slot, field in self.slot_fields.items()},
        }

    def set_config(self, config: Dict[str, Any]) -> None:
        if "active_profile" in config:
            self.set_active_profile(config["active_profile"])
        if "profile_name" in config:
            self.profile_name_edit.setText(config["profile_name"])

    def selected_profile_name(self) -> str:
        item = self.profiles_list.currentItem()
        if item is not None:
            return item.text()
        return self.profile_name_edit.text().strip()

    def current_profile_name(self) -> str:
        return self.profile_name_edit.text().strip()

    def set_active_profile(self, name: str) -> None:
        display_name = name or "Default"
        self.current_profile_label.setText(display_name)
        self.profile_name_edit.setText(display_name)

    def refresh_profiles(self, profiles, slots=None) -> None:
        current = self.selected_profile_name()
        self.profiles_list.clear()
        for profile in profiles:
            self.profiles_list.addItem(QListWidgetItem(profile))

        matches = self.profiles_list.findItems(current, Qt.MatchFlag.MatchExactly)
        if matches:
            self.profiles_list.setCurrentItem(matches[0])
        elif self.profiles_list.count() > 0:
            self.profiles_list.setCurrentRow(0)

        if slots:
            for slot, field in self.slot_fields.items():
                field.setText(slots.get(slot) or "(Empty)")

    def _on_profile_selected(self, name: str) -> None:
        if name:
            self.profile_name_edit.setText(name)

    def _emit_load(self) -> None:
        name = self.selected_profile_name()
        if name:
            self.load_requested.emit(name)

    def _emit_save(self) -> None:
        name = self.current_profile_name()
        if name:
            self.save_requested.emit(name)

    def _emit_delete(self) -> None:
        name = self.selected_profile_name()
        if name:
            self.delete_requested.emit(name)

    def _emit_export(self) -> None:
        name = self.selected_profile_name()
        if name:
            self.export_requested.emit(name)

    def _emit_slot_assign(self, slot: int) -> None:
        name = self.selected_profile_name()
        if name:
            self.slot_assign_requested.emit(slot, name)

    def _emit_slot_clear(self, slot: int) -> None:
        self.slot_assign_requested.emit(slot, "")
