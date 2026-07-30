from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QSplitter, QTableWidget,
    QTableWidgetItem, QHeaderView, QLineEdit, QMessageBox, QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal

from nocrosshair.core.macro import macro_manager, Macro, MacroActionType


class MacrosTab(QWidget):

    macro_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._recording_macro_name: Optional[str] = None
        self.setLayout(QVBoxLayout())
        self._init_ui()
        self._load_macros()

    def _init_ui(self) -> None:
        title = QLabel("Macros")
        title.setObjectName("hudTitle")
        self.layout().addWidget(title)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("color: #444;")
        self.layout().addWidget(separator)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.macro_list = QListWidget()
        self.macro_list.currentItemChanged.connect(self._on_macro_selected)
        left_layout.addWidget(self.macro_list)

        buttons_layout = QHBoxLayout()
        self.btn_new = QPushButton("+ Novo")
        self.btn_new.clicked.connect(self._on_new_macro)
        self.btn_record = QPushButton("Gravar")
        self.btn_record.clicked.connect(self._on_toggle_record)
        self.btn_delete = QPushButton("Deletar")
        self.btn_delete.clicked.connect(self._on_delete_macro)
        buttons_layout.addWidget(self.btn_new)
        buttons_layout.addWidget(self.btn_record)
        buttons_layout.addWidget(self.btn_delete)
        left_layout.addLayout(buttons_layout)

        trigger_layout = QHBoxLayout()
        trigger_label = QLabel("Trigger Key:")
        trigger_label.setMinimumWidth(80)
        self.trigger_input = QLineEdit()
        self.trigger_input.setPlaceholderText("Ex: F5, Ctrl+F1")
        self.trigger_input.editingFinished.connect(self._on_trigger_changed)
        trigger_layout.addWidget(trigger_label)
        trigger_layout.addWidget(self.trigger_input)
        left_layout.addLayout(trigger_layout)

        left_layout.addStretch()

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.action_table = QTableWidget()
        self.action_table.setColumnCount(3)
        self.action_table.setHorizontalHeaderLabels(["Tipo", "Alvo", "Delay (ms)"])
        self.action_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.action_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.action_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.action_table.verticalHeader().setVisible(False)
        right_layout.addWidget(self.action_table)

        self.status_label = QLabel("Nenhum macro selecionado")
        self.status_label.setStyleSheet("color: #888; padding: 4px;")
        right_layout.addWidget(self.status_label)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([300, 500])

        self.layout().addWidget(splitter)

    def _load_macros(self) -> None:
        macro_manager.load_from_file()
        self._refresh_list()

    def _refresh_list(self) -> None:
        self.macro_list.clear()
        for name in macro_manager.get_macro_names():
            self.macro_list.addItem(QListWidgetItem(name))

    def _on_new_macro(self) -> None:
        count = self.macro_list.count() + 1
        name = f"Macro {count}"
        macro = Macro(name=name, trigger="", actions=[], timing=[])
        macro_manager.add_macro(macro)
        macro_manager.save_to_file()
        self._refresh_list()
        for i in range(self.macro_list.count()):
            if self.macro_list.item(i).text() == name:
                self.macro_list.setCurrentRow(i)
                break
        self.macro_changed.emit()

    def _on_toggle_record(self) -> None:
        if macro_manager.is_recording():
            macro = macro_manager.stop_recording()
            self.btn_record.setText("Gravar")
            self.btn_new.setEnabled(True)
            self.btn_delete.setEnabled(True)
            if macro:
                self.status_label.setText(
                    f"Gravado: {len(macro.actions)} ações"
                )
                self._refresh_list()
                macro_manager.save_to_file()
                self.macro_changed.emit()
            else:
                self.status_label.setText("Nenhuma ação gravada")
        else:
            item = self.macro_list.currentItem()
            if item:
                name = item.text()
            else:
                count = self.macro_list.count() + 1
                name = f"Macro {count}"
                macro = Macro(name=name, trigger="", actions=[], timing=[])
                macro_manager.add_macro(macro)
                self._refresh_list()
                for i in range(self.macro_list.count()):
                    if self.macro_list.item(i).text() == name:
                        self.macro_list.setCurrentRow(i)
                        break

            macro_manager.start_recording(name)
            self.btn_record.setText("Parar")
            self.btn_new.setEnabled(False)
            self.btn_delete.setEnabled(False)
            self.status_label.setText("Gravando...")

    def _on_delete_macro(self) -> None:
        item = self.macro_list.currentItem()
        if not item:
            return
        name = item.text()
        reply = QMessageBox.question(
            self,
            "Deletar Macro",
            f"Deletar macro '{name}'?",
        )
        if reply == QMessageBox.StandardButton.Yes:
            macro_manager.remove_macro(name)
            macro_manager.save_to_file()
            self._refresh_list()
            self._populate_action_table(None)
            self.status_label.setText("Macro deletada")
            self.macro_changed.emit()

    def _on_macro_selected(self, current: QListWidgetItem, _previous: QListWidgetItem) -> None:
        if current is None:
            self._populate_action_table(None)
            return
        name = current.text()
        macro = macro_manager.get_macro(name)
        if macro:
            self.trigger_input.setText(macro.trigger)
            self._populate_action_table(macro)
            status = f"{len(macro.actions)} ações"
            if macro_manager.is_recording():
                status = "Gravando..."
            self.status_label.setText(status)

    def _on_trigger_changed(self) -> None:
        item = self.macro_list.currentItem()
        if not item:
            return
        name = item.text()
        macro = macro_manager.get_macro(name)
        if macro:
            macro.trigger = self.trigger_input.text()
            macro_manager.save_to_file()

    def _populate_action_table(self, macro: Optional[Macro]) -> None:
        self.action_table.setRowCount(0)
        if macro is None:
            return

        self.action_table.setRowCount(len(macro.actions))
        for row, action in enumerate(macro.actions):
            tipo_item = QTableWidgetItem(action.action_type.value)
            self.action_table.setItem(row, 0, tipo_item)

            target_item = QTableWidgetItem(action.target)
            self.action_table.setItem(row, 1, target_item)

            delay = macro.timing[row] if row < len(macro.timing) else 0
            delay_item = QTableWidgetItem(str(delay))
            self.action_table.setItem(row, 2, delay_item)

    def get_selected_macro_name(self) -> Optional[str]:
        item = self.macro_list.currentItem()
        return item.text() if item else None

    def get_config(self):
        return {
            "macros": macro_manager.get_macro_names(),
            "recording": macro_manager.is_recording(),
        }

    def refresh_macros(self) -> None:
        self._refresh_list()

