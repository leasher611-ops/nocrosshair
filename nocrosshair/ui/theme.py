from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor, QFont

HUD_STYLESHEET = """
/* Base styling */
QWidget {
background-color: #0A0F1A;
color: #F0F4F8;
font-family: "Segoe UI", "San Francisco", "Helvetica Neue", Arial, sans-serif;
font-size: 13px;
}

QMainWindow {
background-color: #0A0F1A;
}

/* Section groups - glass effect */
QGroupBox {
background-color: rgba(18, 26, 46, 0.92);
border: 1px solid #25334F;
margin-top: 16px;
padding-top: 22px;
padding-left: 12px;
padding-right: 12px;
padding-bottom: 8px;
border-radius: 8px;
}

QGroupBox::title {
subcontrol-origin: margin;
subcontrol-position: top left;
left: 14px;
padding: 0 10px;
background-color: transparent;
color: #00E5FF;
font-size: 13px;
font-weight: 600;
letter-spacing: 1px;
}

/* Tab bar - signature element */
QTabWidget::pane {
border: 1px solid #25334F;
background: rgba(18, 26, 46, 0.95);
border-top: 2px solid #00E5FF;
border-radius: 0 0 8px 8px;
}

QTabBar {
background: rgba(18, 26, 46, 0.95);
border-bottom: 1px solid #25334F;
}

QTabBar::tab {
background-color: rgba(18, 26, 46, 0.85);
color: #A0B1C5;
border: none;
border-right: 1px solid #25334F;
padding: 10px 20px;
margin: 0;
font-size: 13px;
font-weight: 500;
}

QTabBar::tab:selected {
background-color: rgba(26, 38, 60, 0.95);
color: #00E5FF;
border-bottom: 3px solid #00E5FF;
}

QTabBar::tab:hover:!selected {
color: #C0D0E0;
background-color: rgba(26, 38, 60, 0.9);
}

QTabBar::tab:first {
border-left: none;
}

/* Buttons - clean technical style */
QPushButton {
background-color: rgba(26, 38, 60, 0.85);
color: #E0E8F0;
border: 1px solid #25334F;
padding: 8px 20px;
font-weight: 500;
font-size: 13px;
border-radius: 4px;
}

QPushButton:hover {
background-color: rgba(26, 38, 60, 0.95);
border: 1px solid #00E5FF;
color: #00E5FF;
}

QPushButton:pressed, QPushButton:active {
background-color: rgba(0, 184, 212, 0.2);
border: 1px solid #00B8D4;
color: #00B8D4;
}

QPushButton:disabled {
background-color: rgba(10, 15, 25, 0.6);
color: #6B7C93;
border: 1px solid #25334F;
}

QPushButton#startBtn {
background-color: rgba(5, 17, 45, 0.9);
color: #00E5FF;
border: 1px solid #00E5FF;
border-radius: 6px;
}

QPushButton#startBtn:hover {
background-color: rgba(0, 229, 255, 0.15);
}

QPushButton#startBtn:pressed {
color: #00B8D4;
}

QPushButton#stopBtn {
background-color: rgba(25, 17, 22, 0.9);
color: #FF6B6B;
border: 1px solid #FF6B6B;
border-radius: 6px;
}

QPushButton#stopBtn:hover {
background-color: rgba(255, 107, 107, 0.15);
}

QPushButton#applyBtn {
background-color: rgba(5, 17, 45, 0.9);
color: #00E5FF;
border: 1px solid #00E5FF;
border-radius: 6px;
}

QPushButton#applyBtn:hover {
background-color: rgba(0, 229, 255, 0.15);
}

/* Combo boxes */
QComboBox {
background-color: rgba(26, 38, 60, 0.85);
color: #E0E8F0;
border: 1px solid #25334F;
padding: 6px 12px;
min-height: 24px;
font-size: 13px;
border-radius: 4px;
}

QComboBox:hover {
border: 1px solid #00E5FF;
}

QComboBox::drop-down {
border: none;
width: 20px;
}

QComboBox::down-arrow {
width: 0;
height: 0;
border-left: 6px solid transparent;
border-right: 6px solid transparent;
border-top: 7px solid #00E5FF;
}

QComboBox QAbstractItemView {
background-color: rgba(26, 38, 60, 0.95);
color: #E0E8F0;
selection-background-color: #00E5FF;
selection-color: #0A0F1A;
border: 1px solid #25334F;
}

/* Sliders */
QSlider::groove:horizontal {
border: 1px solid #25334F;
height: 6px;
background: rgba(37, 51, 79, 0.6);
margin: 8px 0;
border-radius: 3px;
}

QSlider::handle:horizontal {
background: #00E5FF;
border: none;
width: 14px;
height: 20px;
margin: -7px 0;
border-radius: 4px;
}

QSlider::handle:horizontal:hover {
background: #00B8D4;
width: 16px;
height: 22px;
}

QSlider::sub-page:horizontal {
background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
stop:0 #00E5FF, stop:0.5 #00B8D4, stop:1 #00E5FF);
border: none;
height: 6px;
border-radius: 3px;
}

QSlider::groove:vertical {
border: 1px solid #25334F;
width: 6px;
background: rgba(37, 51, 79, 0.6);
margin: 0 8px;
border-radius: 3px;
}

QSlider::handle:vertical {
background: #00E5FF;
border: none;
width: 20px;
height: 14px;
margin: 0 -7px;
border-radius: 4px;
}

QSlider::handle:vertical:hover {
background: #00B8D4;
height: 16px;
}

QSlider::sub-page:vertical {
background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
stop:0 #00E5FF, stop:0.5 #00B8D4, stop:1 #00E5FF);
border: none;
width: 6px;
border-radius: 3px;
}

/* Checkboxes */
QCheckBox {
spacing: 10px;
color: #A0B1C5;
font-size: 13px;
}

QCheckBox::indicator {
width: 18px;
height: 18px;
border: 1px solid #25334F;
background-color: rgba(26, 38, 60, 0.85);
border-radius: 3px;
}

QCheckBox::indicator:checked {
background-color: #00E5FF;
border: 1px solid #00E5FF;
}

QCheckBox::indicator:hover {
border: 1px solid #00E5FF;
}

QCheckBox::indicator:indeterminate {
background-color: #FFAB00;
border: 1px solid #FFAB00;
}

/* Toolbar */
QToolBar {
background-color: rgba(18, 26, 46, 0.95);
border-bottom: 1px solid #25334F;
spacing: 10px;
padding: 8px 12px;
}

QToolBar QToolButton {
background-color: transparent;
color: #A0B1C5;
border: 1px solid transparent;
padding: 6px 12px;
font-weight: 500;
font-size: 13px;
border-radius: 4px;
}

QToolBar QToolButton:hover {
background-color: rgba(26, 38, 60, 0.85);
border: 1px solid #25334F;
color: #E0E8F0;
}

QToolBar QToolButton:checked {
background-color: rgba(0, 229, 255, 0.2);
border: 1px solid #00E5FF;
color: #00E5FF;
}

QToolBar QLabel {
color: #6B7C93;
font-size: 12px;
background: transparent;
padding: 0 4px;
}

/* Status bar */
QStatusBar {
background-color: rgba(18, 26, 46, 0.95);
color: #6B7C93;
border-top: 1px solid #25334F;
font-size: 12px;
font-family: "JetBrains Mono", Consolas, "Courier New", monospace;
padding: 4px 12px;
}

QStatusBar::item {
border: none;
}

QStatusBar QLabel {
color: #6B7C93;
font-size: 12px;
font-family: "JetBrains Mono", Consolas, "Courier New", monospace;
padding: 0 8px;
background: transparent;
}

/* Labels */
QLabel {
color: #F0F4F8;
background: transparent;
}

QLabel#hudTitle {
color: #00E5FF;
font-size: 16px;
font-weight: 600;
letter-spacing: 1.5px;
padding: 8px 0;
}

QLabel[class="hud"] {
color: #00E5FF;
font-size: 14px;
font-weight: 600;
letter-spacing: 1.5px;
}

QLabel[class="telemetry"] {
color: #00E5FF;
font-family: "JetBrains Mono", Consolas, "Courier New", monospace;
font-size: 12px;
}

QLabel#profileBadge {
color: #FFAB00;
font-weight: 600;
padding: 4px 12px;
font-size: 12px;
font-family: "JetBrains Mono", Consolas, "Courier New", monospace;
letter-spacing: 1px;
background-color: rgba(25, 38, 60, 0.85);
border: 1px solid #FFAB00;
border-radius: 4px;
}

QLabel#hudStatusLabel {
color: #A0B1C5;
font-weight: 500;
padding: 0 8px;
font-size: 12px;
font-family: "JetBrains Mono", Consolas, "Courier New", monospace;
letter-spacing: 1px;
}

QLabel#hudStatusLabel[active="true"] {
color: #00E5FF;
}

QLabel#hudStatusLabel[active="error"] {
color: #FF6B6B;
}

QLabel#hudStatusLabel[active="warning"] {
color: #FFAB00;
}

QLabel#fpsLabel {
color: #00E5FF;
font-family: "JetBrains Mono", Consolas, "Courier New", monospace;
font-size: 12px;
padding: 0 6px;
}

QLabel#connLabel {
color: #00E5FF;
font-family: "JetBrains Mono", Consolas, "Courier New", monospace;
font-size: 12px;
padding: 0 6px;
}

QLabel#connLabel[status="warning"] {
color: #FFAB00;
}

QLabel#connLabel[status="error"] {
color: #FF6B6B;
}

/* Menu bar */
QMenuBar {
background-color: rgba(18, 26, 46, 0.95);
color: #6B7C93;
border-bottom: 1px solid #25334F;
font-size: 12px;
}

QMenuBar::item {
padding: 8px 16px;
background: transparent;
}

QMenuBar::item:selected {
background-color: rgba(26, 38, 60, 0.85);
color: #00E5FF;
}

/* Menu */
QMenu {
background-color: rgba(26, 38, 60, 0.95);
color: #E0E8F0;
border: 1px solid #25334F;
padding: 8px;
}

QMenu::item {
padding: 8px 24px;
}

QMenu::item:selected {
background-color: #00E5FF;
color: #0A0F1A;
}

QMenu::separator {
height: 1px;
background-color: #25334F;
margin: 8px 12px;
}

/* Scrollbars */
QScrollBar:vertical {
background-color: rgba(10, 15, 25, 0.6);
width: 8px;
border: none;
margin: 0;
}

QScrollBar::handle:vertical {
background-color: #25334F;
min-height: 30px;
border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
background-color: #00E5FF;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
height: 0;
}

QScrollBar:horizontal {
background-color: rgba(10, 15, 25, 0.6);
height: 8px;
border: none;
margin: 0;
}

QScrollBar::handle:horizontal {
background-color: #25334F;
min-width: 30px;
border-radius: 4px;
}

QScrollBar::handle:horizontal:hover {
background-color: #00E5FF;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
width: 0;
}

/* Tables */
QTableWidget, QTreeWidget {
background-color: rgba(26, 38, 60, 0.85);
color: #E0E8F0;
border: 1px solid #25334F;
gridline-color: #25334F;
font-size: 13px;
selection-background-color: rgba(0, 229, 255, 0.2);
selection-color: #00E5FF;
}

QHeaderView::section {
background-color: rgba(26, 38, 60, 0.85);
color: #00E5FF;
border: none;
border-bottom: 1px solid #25334F;
padding: 8px 12px;
font-weight: 600;
}

/* Line edits */
QLineEdit {
background-color: rgba(26, 38, 60, 0.85);
color: #E0E8F0;
border: 1px solid #25334F;
padding: 6px 10px;
font-family: "JetBrains Mono", Consolas, "Courier New", monospace;
font-size: 13px;
border-radius: 4px;
}

QLineEdit:focus {
border: 1px solid #00E5FF;
}

/* Spin boxes */
QSpinBox, QDoubleSpinBox {
background-color: rgba(26, 38, 60, 0.85);
color: #E0E8F0;
border: 1px solid #25334F;
padding: 6px 10px;
min-height: 26px;
font-size: 13px;
font-family: "JetBrains Mono", Consolas, "Courier New", monospace;
border-radius: 4px;
}

QSpinBox:hover, QDoubleSpinBox:hover {
border: 1px solid #00E5FF;
}

QSpinBox::up-button, QDoubleSpinBox::up-button {
background-color: rgba(26, 38, 60, 0.85);
border: none;
border-left: 1px solid #25334F;
border-bottom: 1px solid #25334F;
width: 20px;
}

QSpinBox::down-button, QDoubleSpinBox::down-button {
background-color: rgba(26, 38, 60, 0.85);
border: none;
border-left: 1px solid #25334F;
width: 20px;
}

QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
width: 0;
height: 0;
border-left: 6px solid transparent;
border-right: 6px solid transparent;
border-bottom: 7px solid #00E5FF;
}

QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
width: 0;
height: 0;
border-left: 6px solid transparent;
border-right: 6px solid transparent;
border-top: 7px solid #FF6B6B;
}

/* Progress bar */
QProgressBar {
background-color: rgba(26, 38, 60, 0.85);
border: 1px solid #25334F;
text-align: center;
color: #E0E8F0;
font-size: 12px;
font-family: "JetBrains Mono", Consolas, "Courier New", monospace;
height: 20px;
border-radius: 4px;
}

QProgressBar::chunk {
background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
stop:0 #00E5FF, stop:0.5 #00B8D4, stop:1 #00E5FF);
border-radius: 4px;
}

/* Tooltip */
QToolTip {
background-color: rgba(26, 38, 60, 0.95);
color: #E0E8F0;
border: 1px solid #00E5FF;
font-size: 12px;
padding: 6px 10px;
font-family: "JetBrains Mono", Consolas, "Courier New", monospace;
border-radius: 4px;
}

/* Message boxes */
QMessageBox {
background-color: rgba(26, 38, 60, 0.95);
}

QMessageBox QLabel {
color: #E0E8F0;
font-size: 14px;
}

QMessageBox QPushButton {
min-width: 80px;
}

/* Scroll areas */
QScrollArea {
border: none;
background: transparent;
}

/* Crosshair preview panel - signature element */
QWidget#crosshairPreviewPanel, QFrame#crosshairPreviewFrame {
background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
stop:0 rgba(30, 40, 55, 0.85),
stop:1 rgba(20, 28, 42, 0.95));
border: 1px solid #00E5FF;
border-radius: 12px;
}

/* Recoil curve preview */
QWidget#recoilCurvePanel, QFrame#recoilCurveFrame {
background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
stop:0 rgba(30, 40, 55, 0.85),
stop:1 rgba(20, 28, 42, 0.95));
border: 1px solid #00E5FF;
border-radius: 12px;
}

/* Tab titles */
QLabel.tabTitle {
color: #A0B1C5;
font-size: 13px;
font-weight: 500;
}
"""


def apply_theme(app: QApplication) -> None:
    app.setStyleSheet(HUD_STYLESHEET)

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(0x0A, 0x0F, 0x1A))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(0xF0, 0xF4, 0xF8))
    palette.setColor(QPalette.ColorRole.Base, QColor(0x12, 0x1A, 0x2E))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(0x19, 0x26, 0x3C))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(0x12, 0x1A, 0x2E))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(0xF0, 0xF4, 0xF8))
    palette.setColor(QPalette.ColorRole.Text, QColor(0xF0, 0xF4, 0xF8))
    palette.setColor(QPalette.ColorRole.Button, QColor(0x12, 0x1A, 0x2E))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(0xF0, 0xF4, 0xF8))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(0x00, 0xE5, 0xFF))
    palette.setColor(QPalette.ColorRole.Link, QColor(0x00, 0xE5, 0xFF))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(0x00, 0xE5, 0xFF))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(0x0A, 0x0F, 0x1A))
    palette.setColor(QPalette.ColorRole.Dark, QColor(0x0A, 0x0F, 0x1A))
    palette.setColor(QPalette.ColorRole.Mid, QColor(0x12, 0x1A, 0x2E))
    palette.setColor(QPalette.ColorRole.Light, QColor(0x19, 0x26, 0x3C))

    app.setPalette(palette)

    font = QFont("Segoe UI", 13)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(font)