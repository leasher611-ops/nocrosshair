from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, Qt
from PyQt6.QtWidgets import QTabWidget, QGraphicsOpacityEffect


class AnimatedTabWidget(QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setUsesScrollButtons(True)
        self.tabBar().setExpanding(False)
        self.setElideMode(Qt.TextElideMode.ElideRight)
        self._current_animation = None
        self._previous_effect = None
        self._previous_widget = None
        self.currentChanged.connect(self._on_animated_tab_changed)

    def _on_animated_tab_changed(self, index: int):
        if self._current_animation:
            self._current_animation.stop()
            self._current_animation = None

        self._remove_effect()

        widget = self.widget(index)
        if not widget:
            return

        effect = QGraphicsOpacityEffect(widget)
        effect.setOpacity(0.0)
        widget.setGraphicsEffect(effect)

        self._previous_effect = effect
        self._previous_widget = widget

        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(180)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        anim.finished.connect(self._remove_effect)
        anim.start()

        self._current_animation = anim

    def _remove_effect(self):
        try:
            if self._previous_widget and self._previous_effect:
                current = self._previous_widget.graphicsEffect()
                if current is self._previous_effect:
                    self._previous_widget.setGraphicsEffect(None)
        except RuntimeError:
            pass
        self._previous_effect = None
        self._previous_widget = None
        self._current_animation = None
