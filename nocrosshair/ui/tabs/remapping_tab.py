from typing import Dict, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider,
    QCheckBox, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal

from nocrosshair.ui.widgets import KeyBindingTable, HLine, SectionGroupBox

class RemappingTab(QWidget):

    config_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayout(QVBoxLayout())
        self._init_ui()

    def _init_ui(self) -> None:
        title = QLabel("Input Remapping")
        title.setObjectName("hudTitle")
        self.layout().addWidget(title)
        self.layout().addWidget(HLine())

        sens_group = SectionGroupBox("Mouse Sensitivity")
        sens_layout = QVBoxLayout()

        self._add_sens_slider(sens_layout, "Geral:", "mouse_sens", 80, 5, 200)
        self._add_sens_slider(sens_layout, "Horizontal (X):", "sens_x", 80, 5, 200)
        self._add_sens_slider(sens_layout, "Vertical (Y):", "sens_y", 80, 5, 200)
        self._add_sens_slider(sens_layout, "Curva:", "mouse_curve", 65, 10, 100, 2)
        self._add_sens_slider(sens_layout, "Deflexao ini.:", "mouse_min_output", 8, 0, 30, 2)
        self._add_sens_slider(sens_layout, "Suavizacao:", "mouse_smooth", 0, 0, 95, 2)

        sens_group.layout().addLayout(sens_layout)
        self.layout().addWidget(sens_group)

        bindings_group = SectionGroupBox("Key Bindings")
        bindings_layout = QVBoxLayout()

        self.bindings_table = KeyBindingTable()
        self.bindings_table.add_binding("KEY_SPACE", "BTN_A", "Normal")
        self.bindings_table.add_binding("KEY_LEFTSHIFT", "BTN_THUMBL", "Normal")
        self.bindings_table.add_binding("KEY_C", "BTN_THUMBR", "Normal")
        self.bindings_table.add_binding("KEY_E", "BTN_X", "Normal")
        bindings_layout.addWidget(self.bindings_table)

        buttons_layout = QHBoxLayout()
        add_btn = QPushButton("Add Binding")
        remove_btn = QPushButton("Remove Binding")
        buttons_layout.addWidget(add_btn)
        buttons_layout.addWidget(remove_btn)
        buttons_layout.addStretch()
        bindings_layout.addLayout(buttons_layout)

        bindings_group.layout().addLayout(bindings_layout)
        self.layout().addWidget(bindings_group)

        zoom_group = SectionGroupBox("Sniper Zoom (reWASD-style)")
        zoom_layout = QVBoxLayout()

        self.zoom_enabled = QCheckBox("Enable Sniper Zoom")
        self.zoom_enabled.stateChanged.connect(self._on_change)
        zoom_layout.addWidget(self.zoom_enabled)

        zoom_row = QHBoxLayout()
        zoom_row.addWidget(QLabel("Activation Button"))
        self.zoom_button = QComboBox()
        self.zoom_button.addItems(["BTN_SIDE", "BTN_EXTRA", "BTN_MIDDLE", "BTN_RIGHT", "BTN_LEFT"])
        self.zoom_button.currentIndexChanged.connect(self._on_change)
        zoom_row.addWidget(self.zoom_button)
        zoom_row.addStretch()
        zoom_layout.addLayout(zoom_row)

        self._add_sens_slider(zoom_layout, "Zoom Factor:", "zoom_factor", 4, 2, 10)
        self._add_sens_slider(zoom_layout, "Window Width:", "zoom_width", 240, 100, 500)
        self._add_sens_slider(zoom_layout, "Window Height:", "zoom_height", 180, 80, 400)

        self.zoom_fixed = QCheckBox("Fixed position (don't follow cursor)")
        self.zoom_fixed.stateChanged.connect(self._on_change)
        self.zoom_capture_btn = QPushButton("Capture Position")

        pos_row = QHBoxLayout()
        self.zoom_capture_btn = QPushButton("Capture Position")
        self.zoom_capture_btn.clicked.connect(self._capture_position)
        self.zoom_pos_label = QLabel("960, 540")
        self.zoom_pos_label.setStyleSheet("color: #0f0; font-size: 11px;")
        pos_row.addWidget(self.zoom_capture_btn)
        pos_row.addWidget(self.zoom_pos_label)
        pos_row.addStretch()
        zoom_layout.addLayout(pos_row)

        zoom_note = QLabel("Shows a magnified view of the crosshair area while the button is held")
        zoom_note.setStyleSheet("color: #888; font-size: 10px; font-style: italic;")
        zoom_layout.addWidget(zoom_note)

        zoom_group.layout().addLayout(zoom_layout)
        self.layout().addWidget(zoom_group)

        self.layout().addStretch()

    def _add_sens_slider(self, layout, label_text: str, attr: str,
                          default: int, min_val: int, max_val: int, fmt_decimals: int = 0):
        row = QHBoxLayout()
        lbl = QLabel(label_text)
        lbl.setMinimumWidth(110)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(default)
        slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        slider.setTickInterval(10)
        val_label = QLabel(str(default))
        val_label.setMinimumWidth(35)
        if fmt_decimals > 0:
            slider.valueChanged.connect(
                lambda v, l=val_label, d=fmt_decimals: l.setText(f"{v / (10**d):.{d}f}")
            )
        else:
            slider.valueChanged.connect(lambda v, l=val_label: l.setText(str(v)))
        slider.valueChanged.connect(self._on_change)
        row.addWidget(lbl)
        row.addWidget(slider)
        row.addWidget(val_label)
        layout.addLayout(row)
        setattr(self, f"{attr}_slider", slider)
        setattr(self, f"{attr}_value", val_label)

    def _on_change(self) -> None:
        self.config_changed.emit(self.get_config())

    def _capture_position(self) -> None:
        try:
            from Xlib.display import Display
            d = Display()
            r = d.screen().root
            p = r.query_pointer()
            d.close()
            x, y = p.root_x, p.root_y
        except Exception:
            x, y = 960, 540
        self._captured_x = x
        self._captured_y = y
        self.zoom_pos_label.setText(f"{x}, {y}")

    def get_config(self) -> Dict[str, Any]:
        return {
            "bindings": self.bindings_table.get_bindings(),
            "mouse_sens": self.mouse_sens_slider.value(),
            "sens_x": self.sens_x_slider.value(),
            "sens_y": self.sens_y_slider.value(),
            "mouse_curve": self.mouse_curve_slider.value() / 100.0,
            "mouse_min_output": self.mouse_min_output_slider.value() / 100.0,
            "square_stick": True,
            "mouse_smooth": self.mouse_smooth_slider.value() / 100.0,
            "sniper_zoom_enabled": self.zoom_enabled.isChecked(),
            "sniper_zoom_button": self.zoom_button.currentText(),
            "sniper_zoom_factor": self.zoom_factor_slider.value(),
            "sniper_zoom_window_width": self.zoom_width_slider.value(),
            "sniper_zoom_window_height": self.zoom_height_slider.value(),
            "sniper_zoom_fixed_pos": self.zoom_fixed.isChecked(),
            "sniper_zoom_fixed_x": getattr(self, "_captured_x", 960),
            "sniper_zoom_fixed_y": getattr(self, "_captured_y", 540),
        }

    def set_config(self, config: Dict[str, Any]) -> None:
        c = config
        if "kbd_bindings" in c:
            self.bindings_table.setRowCount(0)
            for button, target in c["kbd_bindings"].items():
                self.bindings_table.add_binding(button, target, "Normal")
        elif "bindings" in c:
            self.bindings_table.setRowCount(0)
            for button, target in c["bindings"].items():
                self.bindings_table.add_binding(button, target, "Normal")
        for key, slider in [
            ("remap_mouse_sens", "mouse_sens"), ("mouse_sens", "mouse_sens"),
            ("remap_sens_x", "sens_x"), ("sens_x", "sens_x"),
            ("remap_sens_y", "sens_y"), ("sens_y", "sens_y"),
            ("remap_curve", "mouse_curve"), ("mouse_curve", "mouse_curve"),
            ("remap_min_output", "mouse_min_output"), ("mouse_min_output", "mouse_min_output"),
            ("remap_smooth", "mouse_smooth"), ("mouse_smooth", "mouse_smooth"),
        ]:
            if key in c and hasattr(self, f"{slider}_slider"):
                val = c[key]
                if slider == "mouse_curve":
                    val = int(float(val) * 100)
                elif slider in ("mouse_min_output", "mouse_smooth"):
                    val = int(float(val) * 100)
                getattr(self, f"{slider}_slider").setValue(int(val))
        for key in ("sniper_zoom_fixed_pos", "sniper_zoom_fixed_x", "sniper_zoom_fixed_y"):
            if key in c:
                if key == "sniper_zoom_fixed_pos":
                    self.zoom_fixed.setChecked(bool(c[key]))
                elif key == "sniper_zoom_fixed_x":
                    self._captured_x = int(c[key])
                elif key == "sniper_zoom_fixed_y":
                    self._captured_y = int(c[key])
        if hasattr(self, "_captured_x") and hasattr(self, "_captured_y"):
            self.zoom_pos_label.setText(f"{self._captured_x}, {self._captured_y}")
