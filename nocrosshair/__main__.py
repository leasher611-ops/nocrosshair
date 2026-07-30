import os
import sys
import signal

if os.environ.get("XDG_SESSION_TYPE") == "wayland":
    os.environ.setdefault("QT_QPA_PLATFORM", "wayland;xcb")

from PyQt6.QtCore import QMessageLogContext, QtMsgType, qInstallMessageHandler
from PyQt6.QtWidgets import QApplication
from nocrosshair.ui.main_window import MainWindow
from nocrosshair.ui.widgets.splash_screen import SplashScreen
from nocrosshair.ui.theme import apply_theme

_main_window = None


def _qt_message_handler(mode: QtMsgType, context: QMessageLogContext, message: str):
    if "setLayout" in message and "already has a layout" in message:
        return
    if "propagateSizeHints" in message:
        return
    print(f"[Qt{mode.value}] {message}", file=sys.stderr, flush=True)


def _emergency_ungrab(sig=None, frame=None):
    try:
        import evdev
        for path in evdev.list_devices():
            try:
                d = evdev.InputDevice(path)
                d.ungrab()
                d.close()
            except Exception:
                pass
    except Exception:
        pass
    sys.exit(0)


def _launch_main_window(app: QApplication):
    global _main_window
    _main_window = MainWindow()
    _main_window.show()
    app.setQuitOnLastWindowClosed(True)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    apply_theme(app)
    qInstallMessageHandler(_qt_message_handler)

    app.setQuitOnLastWindowClosed(False)
    splash = SplashScreen(on_finished=lambda: _launch_main_window(app))
    splash.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, _emergency_ungrab)
    signal.signal(signal.SIGINT, _emergency_ungrab)
    main()
