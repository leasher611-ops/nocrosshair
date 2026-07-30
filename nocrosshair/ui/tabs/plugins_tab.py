import os
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QPushButton, QTextEdit, QSplitter, QFrame, QMessageBox,
    QFileDialog, QAbstractItemView
)
from PyQt6.QtGui import QColor

from nocrosshair.core.plugins import plugin_manager


class PluginsTab(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._plugin_manager = plugin_manager
        self._log_cache = ""
        self._discovered = False
        self._init_ui()
        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self._refresh_log)
        self._refresh_timer.start(5000)

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        header = QLabel("Plugins")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #00ff88; padding: 4px 0;")
        layout.addWidget(header)

        splitter = QSplitter(Qt.Orientation.Vertical)

        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.plugin_list = QListWidget()
        self.plugin_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.plugin_list.currentItemChanged.connect(self._on_plugin_selected)
        left_layout.addWidget(self.plugin_list)

        btn_row = QHBoxLayout()
        self.btn_install = QPushButton("Install...")
        self.btn_install.clicked.connect(self._on_install)
        btn_row.addWidget(self.btn_install)

        self.btn_open_folder = QPushButton("Open folder")
        self.btn_open_folder.clicked.connect(self._on_open_folder)
        btn_row.addWidget(self.btn_open_folder)

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self._refresh_list)
        btn_row.addWidget(self.btn_refresh)

        left_layout.addLayout(btn_row)

        top_layout.addWidget(left_panel, stretch=3)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.detail_label = QLabel("Select a plugin")
        self.detail_label.setStyleSheet("color: #aaa; padding: 4px;")
        self.detail_label.setWordWrap(True)
        right_layout.addWidget(self.detail_label)

        btn_row2 = QHBoxLayout()
        self.btn_enable = QPushButton("Enable")
        self.btn_enable.clicked.connect(self._on_enable)
        btn_row2.addWidget(self.btn_enable)

        self.btn_disable = QPushButton("Disable")
        self.btn_disable.clicked.connect(self._on_disable)
        btn_row2.addWidget(self.btn_disable)

        self.btn_load = QPushButton("Load")
        self.btn_load.clicked.connect(self._on_load)
        btn_row2.addWidget(self.btn_load)

        self.btn_unload = QPushButton("Unload")
        self.btn_unload.clicked.connect(self._on_unload)
        btn_row2.addWidget(self.btn_unload)

        right_layout.addLayout(btn_row2)

        top_layout.addWidget(right_panel, stretch=2)

        splitter.addWidget(top_widget)

        log_frame = QFrame()
        log_layout = QVBoxLayout(log_frame)
        log_layout.setContentsMargins(0, 4, 0, 0)

        log_header = QHBoxLayout()
        log_label = QLabel("Log")
        log_label.setStyleSheet("color: #888; font-weight: bold;")
        log_header.addWidget(log_label)
        log_header.addStretch()

        btn_clear_log = QPushButton("Clear")
        btn_clear_log.setFixedWidth(60)
        btn_clear_log.clicked.connect(self._on_clear_log)
        log_header.addWidget(btn_clear_log)

        log_layout.addLayout(log_header)

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMaximumHeight(150)
        self.log_area.setStyleSheet("QTextEdit { background: #0d0d0f; color: #00ff88; font-family: monospace; font-size: 11px; }")
        log_layout.addWidget(self.log_area)

        splitter.addWidget(log_frame)
        splitter.setSizes([400, 150])

        layout.addWidget(splitter)

        self._refresh_list()

    def _refresh_list(self) -> None:
        if not self._discovered:
            self._plugin_manager.discover_plugins()
            self._discovered = True
        self.plugin_list.blockSignals(True)
        self.plugin_list.clear()
        for info in self._plugin_manager.get_available_plugins():
            status = " [loaded]" if info.name in self._plugin_manager.get_loaded_plugins() else ""
            enabled = "" if info.enabled else " [disabled]"
            self.plugin_list.addItem(f"{info.name} v{info.version}{enabled}{status}")
        self.plugin_list.blockSignals(False)

    def _get_selected_name(self) -> str:
        item = self.plugin_list.currentItem()
        if item:
            return item.text().split(" v")[0]
        return ""

    def _on_plugin_selected(self, current, previous) -> None:
        name = self._get_selected_name()
        if not name:
            self.detail_label.setText("Select a plugin")
            return

        info = self._plugin_manager._plugin_info.get(name)
        if info:
            loaded = name in self._plugin_manager.get_loaded_plugins()
            self.detail_label.setText(
                f"<b>{info.name}</b> v{info.version}<br>"
                f"Author: {info.author}<br>"
                f"Description: {info.description}<br>"
                f"Status: {'Loaded' if loaded else 'Not loaded'}<br>"
                f"Enabled: {'Yes' if info.enabled else 'No'}"
            )
        else:
            self.detail_label.setText(name)

    def _on_install(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Plugin Folder")
        if folder:
            self._plugin_manager.add_plugin_dir(folder)
            self._discovered = False
            self._refresh_list()

    def _on_open_folder(self) -> None:
        import subprocess
        folder = self._plugin_manager.open_plugin_folder()
        try:
            subprocess.Popen(["xdg-open", folder])
        except Exception:
            pass

    def _on_enable(self) -> None:
        name = self._get_selected_name()
        if name:
            self._plugin_manager.enable_plugin(name)
            self._refresh_list()

    def _on_disable(self) -> None:
        name = self._get_selected_name()
        if name:
            self._plugin_manager.disable_plugin(name)
            self._refresh_list()

    def _on_load(self) -> None:
        name = self._get_selected_name()
        if name:
            if self._plugin_manager.load_plugin(name):
                self._refresh_list()

    def _on_unload(self) -> None:
        name = self._get_selected_name()
        if name:
            if self._plugin_manager.unload_plugin(name):
                self._refresh_list()

    def _refresh_log(self) -> None:
        log_entries = self._plugin_manager.get_log()
        if not log_entries:
            return
        new_text = "\n".join(log_entries[-50:])
        if new_text != self._log_cache:
            self._log_cache = new_text
            self.log_area.blockSignals(True)
            self.log_area.setPlainText(new_text)
            sb = self.log_area.verticalScrollBar()
            sb.setValue(sb.maximum())
            self.log_area.blockSignals(False)

    def _on_clear_log(self) -> None:
        self._plugin_manager.clear_log()
        self._log_cache = ""
        self.log_area.clear()
