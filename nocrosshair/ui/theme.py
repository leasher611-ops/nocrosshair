from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor, QFont

HUD_STYLESHEET = """
QWidget {
background-color: #050508;
color: #d0d0e0;
font-family: "JetBrains Mono", "Consolas", "Courier New", monospace;
font-size: 13px;
}

QMainWindow {
background-color: #050508;
}

QGroupBox {
background-color: rgba(10, 10, 15, 180);
border: 1px solid #BB00FF;
margin-top: 14px;
padding-top: 18px;
padding-left: 8px;
padding-right: 8px;
padding-bottom: 6px;
font-weight: bold;
}

QGroupBox::title {
subcontrol-origin: margin;
subcontrol-position: top left;
left: 10px;
padding: 0 8px;
background-color: #050508;
color: #BB00FF;
font-size: 11px;
text-transform: uppercase;
letter-spacing: 2px;
}

QTabWidget::pane {
border: 1px solid #101018;
background: transparent;
border-top: 2px solid #FF00AA;
}

QTabBar {
background: transparent;
border-bottom: 1px solid #101018;
}

QTabBar::tab {
background-color: rgba(10, 10, 15, 200);
color: #444466;
border: none;
border-right: 1px solid #101018;
padding: 8px 18px;
margin: 0;
font-size: 12px;
font-weight: bold;
text-transform: uppercase;
letter-spacing: 1px;
}

QTabBar::tab:selected {
background-color: rgba(16, 16, 24, 220);
color: #BB00FF;
border-bottom: 2px solid #BB00FF;
}

QTabBar::tab:hover:!selected {
color: #8888aa;
background-color: rgba(16, 16, 24, 200);
}

QTabBar::tab:first {
border-left: none;
}

QPushButton {
background-color: #0a0a0f;
color: #d0d0e0;
border: 1px solid #101018;
padding: 6px 16px;
font-weight: bold;
font-size: 12px;
text-transform: uppercase;
letter-spacing: 1px;
}

QPushButton:hover {
background-color: #101018;
border: 1px solid #BB00FF;
color: #BB00FF;
}

QPushButton:pressed {
background-color: rgba(0, 255, 136, 0.1);
border: 1px solid #FF00AA;
color: #FF00AA;
}

QPushButton:disabled {
background-color: #050508;
color: #444466;
border: 1px solid #101018;
}

QPushButton#startBtn {
background-color: #050508;
color: #BB00FF;
border: 1px solid #BB00FF;
}

QPushButton#startBtn:hover {
background-color: rgba(0, 255, 136, 0.1);
}

QPushButton#stopBtn {
background-color: #050508;
color: #ff3355;
border: 1px solid #ff3355;
}

QPushButton#stopBtn:hover {
background-color: rgba(255, 51, 85, 0.1);
}

QPushButton#applyBtn {
background-color: #050508;
color: #FF00AA;
border: 1px solid #FF00AA;
}

QPushButton#applyBtn:hover {
background-color: rgba(0, 204, 204, 0.1);
}

QComboBox {
background-color: #0a0a0f;
color: #d0d0e0;
border: 1px solid #101018;
padding: 4px 10px;
min-height: 22px;
font-size: 12px;
}

QComboBox:hover {
border: 1px solid #BB00FF;
}

QComboBox::drop-down {
border: none;
width: 22px;
}

QComboBox::down-arrow {
width: 0;
height: 0;
border-left: 5px solid transparent;
border-right: 5px solid transparent;
border-top: 6px solid #BB00FF;
}

QComboBox QAbstractItemView {
background-color: #0a0a0f;
color: #d0d0e0;
selection-background-color: #BB00FF;
selection-color: #050508;
border: 1px solid #BB00FF;
outline: none;
}

QSlider::groove:horizontal {
border: 1px solid #101018;
height: 4px;
background: #0a0a0f;
margin: 4px 0;
}

QSlider::handle:horizontal {
background: #BB00FF;
border: none;
width: 12px;
height: 16px;
margin: -6px 0;
}

QSlider::handle:horizontal:hover {
background: #FF00AA;
width: 14px;
}

QSlider::sub-page:horizontal {
background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
stop:0 #BB00FF, stop:0.5 #FF00AA, stop:1 #BB00FF);
border: none;
height: 4px;
}

QSlider::groove:vertical {
border: 1px solid #101018;
width: 4px;
background: #0a0a0f;
margin: 0 4px;
}

QSlider::handle:vertical {
background: #BB00FF;
border: none;
width: 16px;
height: 12px;
margin: 0 -6px;
}

QSlider::handle:vertical:hover {
background: #FF00AA;
height: 14px;
}

QSlider::sub-page:vertical {
background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
stop:0 #BB00FF, stop:0.5 #FF00AA, stop:1 #BB00FF);
border: none;
width: 4px;
}

QCheckBox {
spacing: 8px;
color: #d0d0e0;
font-size: 12px;
}

QCheckBox::indicator {
width: 16px;
height: 16px;
border: 1px solid #101018;
background-color: #0a0a0f;
}

QCheckBox::indicator:checked {
background-color: #BB00FF;
border: 1px solid #BB00FF;
}

QCheckBox::indicator:hover {
border: 1px solid #BB00FF;
}

QCheckBox::indicator:indeterminate {
background-color: #ffaa00;
border: 1px solid #ffaa00;
}

QToolBar {
background-color: #0a0a0f;
border-bottom: 1px solid #BB00FF;
spacing: 6px;
padding: 4px 8px;
}

QToolBar QToolButton {
background-color: transparent;
color: #8888aa;
border: 1px solid transparent;
padding: 4px 10px;
font-weight: bold;
font-size: 11px;
text-transform: uppercase;
letter-spacing: 1px;
}

QToolBar QToolButton:hover {
background-color: #101018;
border: 1px solid #101018;
color: #d0d0e0;
}

QToolBar QToolButton:checked {
background-color: rgba(0, 255, 136, 0.1);
border: 1px solid #BB00FF;
color: #BB00FF;
}

QToolBar QLabel {
color: #8888aa;
font-size: 10px;
text-transform: uppercase;
letter-spacing: 1px;
background: transparent;
padding: 0 2px;
}

QStatusBar {
background-color: #0a0a0f;
color: #8888aa;
border-top: 1px solid #101018;
font-size: 11px;
font-family: "JetBrains Mono", "Consolas", "Courier New", monospace;
padding: 2px 8px;
}

QStatusBar::item {
border: none;
}

QStatusBar QLabel {
color: #8888aa;
font-size: 11px;
font-family: "JetBrains Mono", "Consolas", "Courier New", monospace;
padding: 0 8px;
background: transparent;
}

QLabel {
color: #d0d0e0;
background: transparent;
}

QLabel#hudTitle {
color: #BB00FF;
font-size: 14px;
font-weight: bold;
font-family: "JetBrains Mono", "Consolas", "Courier New", monospace;
letter-spacing: 3px;
text-transform: uppercase;
padding: 4px 0;
}

QLabel[class="hud"] {
color: #BB00FF;
font-size: 14px;
font-weight: bold;
font-family: "JetBrains Mono", "Consolas", "Courier New", monospace;
letter-spacing: 2px;
}

QLabel[class="telemetry"] {
color: #BB00FF;
font-family: "JetBrains Mono", "Consolas", "Courier New", monospace;
font-size: 11px;
}

QLabel#profileBadge {
color: #ffaa00;
font-weight: bold;
padding: 2px 10px;
font-size: 11px;
font-family: "JetBrains Mono", "Consolas", "Courier New", monospace;
letter-spacing: 2px;
background-color: #0a0a0f;
border: 1px solid #BB00FF;
text-transform: uppercase;
}

QLabel#hudStatusLabel {
color: #8888aa;
font-weight: bold;
padding: 0 8px;
font-size: 12px;
font-family: "JetBrains Mono", "Consolas", "Courier New", monospace;
letter-spacing: 1px;
text-transform: uppercase;
}

QLabel#hudStatusLabel[active="true"] {
color: #BB00FF;
}

QLabel#hudStatusLabel[active="error"] {
color: #ff3355;
}

QLabel#hudStatusLabel[active="warning"] {
color: #ffaa00;
}

QLabel#fpsLabel {
color: #BB00FF;
font-family: "JetBrains Mono", "Consolas", "Courier New", monospace;
font-size: 11px;
padding: 0 6px;
}

QLabel#connLabel {
color: #BB00FF;
font-family: "JetBrains Mono", "Consolas", "Courier New", monospace;
font-size: 11px;
padding: 0 6px;
}

QLabel#connLabel[status="warning"] {
color: #ffaa00;
}

QLabel#connLabel[status="error"] {
color: #ff3355;
}

QMenuBar {
background-color: #0a0a0f;
color: #8888aa;
border-bottom: 1px solid #101018;
font-size: 12px;
text-transform: uppercase;
letter-spacing: 1px;
}

QMenuBar::item {
padding: 6px 14px;
background: transparent;
}

QMenuBar::item:selected {
background-color: #101018;
color: #BB00FF;
}

QMenu {
background-color: #0a0a0f;
color: #d0d0e0;
border: 1px solid #101018;
padding: 4px;
}

QMenu::item {
padding: 6px 24px;
}

QMenu::item:selected {
background-color: #BB00FF;
color: #050508;
}

QMenu::separator {
height: 1px;
background-color: #101018;
margin: 4px 8px;
}

QScrollBar:vertical {
background-color: #050508;
width: 6px;
border: none;
margin: 0;
}

QScrollBar::handle:vertical {
background-color: #101018;
min-height: 30px;
}

QScrollBar::handle:vertical:hover {
background-color: #BB00FF;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
height: 0;
}

QScrollBar:horizontal {
background-color: #050508;
height: 6px;
border: none;
margin: 0;
}

QScrollBar::handle:horizontal {
background-color: #101018;
min-width: 30px;
}

QScrollBar::handle:horizontal:hover {
background-color: #BB00FF;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
width: 0;
}

QTableWidget, QTreeWidget {
background-color: #0a0a0f;
color: #d0d0e0;
border: 1px solid #101018;
gridline-color: #101018;
font-size: 12px;
selection-background-color: rgba(0, 255, 136, 0.15);
selection-color: #BB00FF;
}

QHeaderView::section {
background-color: #0a0a0f;
color: #BB00FF;
border: none;
border-bottom: 1px solid #101018;
padding: 6px 10px;
font-weight: bold;
font-size: 11px;
text-transform: uppercase;
letter-spacing: 1px;
}

QLineEdit {
background-color: #0a0a0f;
color: #d0d0e0;
border: 1px solid #101018;
padding: 4px 8px;
font-family: "JetBrains Mono", "Consolas", "Courier New", monospace;
font-size: 12px;
}

QLineEdit:focus {
border: 1px solid #BB00FF;
}

QSpinBox, QDoubleSpinBox {
background-color: #0a0a0f;
color: #d0d0e0;
border: 1px solid #101018;
padding: 3px 6px;
min-height: 22px;
font-size: 12px;
font-family: "JetBrains Mono", "Consolas", "Courier New", monospace;
}

QSpinBox:hover, QDoubleSpinBox:hover {
border: 1px solid #BB00FF;
}

QSpinBox::up-button, QDoubleSpinBox::up-button {
background-color: #0a0a0f;
border: none;
border-left: 1px solid #101018;
border-bottom: 1px solid #101018;
width: 18px;
}

QSpinBox::down-button, QDoubleSpinBox::down-button {
background-color: #0a0a0f;
border: none;
border-left: 1px solid #101018;
width: 18px;
}

QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
width: 0;
height: 0;
border-left: 4px solid transparent;
border-right: 4px solid transparent;
border-bottom: 5px solid #BB00FF;
}

QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
width: 0;
height: 0;
border-left: 4px solid transparent;
border-right: 4px solid transparent;
border-top: 5px solid #ff3355;
}

QProgressBar {
background-color: #0a0a0f;
border: 1px solid #101018;
text-align: center;
color: #d0d0e0;
font-size: 11px;
font-family: "JetBrains Mono", "Consolas", "Courier New", monospace;
height: 18px;
}

QProgressBar::chunk {
background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
stop:0 #BB00FF, stop:0.5 #FF00AA, stop:1 #BB00FF);
}

QToolTip {
background-color: #0a0a0f;
color: #d0d0e0;
border: 1px solid #BB00FF;
font-size: 11px;
padding: 4px 8px;
font-family: "JetBrains Mono", "Consolas", "Courier New", monospace;
}

QMessageBox {
background-color: #0a0a0f;
}

QMessageBox QLabel {
color: #d0d0e0;
font-size: 13px;
}

QMessageBox QPushButton {
min-width: 80px;
}

QScrollArea {
border: none;
background: transparent;
}
"""


def apply_theme(app: QApplication) -> None:
    app.setStyleSheet(HUD_STYLESHEET)

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(0x05, 0x05, 0x08))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(0xd0, 0xd0, 0xe0))
    palette.setColor(QPalette.ColorRole.Base, QColor(0x0a, 0x0a, 0x0f))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(0x10, 0x10, 0x18))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(0x0a, 0x0a, 0x0f))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(0xd0, 0xd0, 0xe0))
    palette.setColor(QPalette.ColorRole.Text, QColor(0xd0, 0xd0, 0xe0))
    palette.setColor(QPalette.ColorRole.Button, QColor(0x0a, 0x0a, 0x0f))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(0xd0, 0xd0, 0xe0))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(0xBB, 0x00, 0xFF))
    palette.setColor(QPalette.ColorRole.Link, QColor(0xBB, 0x00, 0xFF))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(0xBB, 0x00, 0xFF))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(0x05, 0x05, 0x08))
    palette.setColor(QPalette.ColorRole.Dark, QColor(0x0a, 0x0a, 0x0f))
    palette.setColor(QPalette.ColorRole.Mid, QColor(0x10, 0x10, 0x18))
    palette.setColor(QPalette.ColorRole.Light, QColor(0x10, 0x10, 0x18))

    app.setPalette(palette)

    font = QFont("JetBrains Mono", 12)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(font)
