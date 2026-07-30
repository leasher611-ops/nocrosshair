#!/usr/bin/env python3

from typing import Dict, Any, Optional


class OverlayManager:

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self._config = config or {}
        self._visible = self._config.get("visible", True)
        self._overlay = None
        self._init_overlay()

    def _init_overlay(self) -> None:
        try:
            from nocrosshair.ui.widgets.crosshair_overlay import QtCrosshairOverlay
            self._overlay = QtCrosshairOverlay(self._config)
            self._visible = self._config.get("visible", True)
        except Exception as e:
            print(f"[OverlayManager] Failed to initialize overlay: {e}")

    def show(self) -> None:
        self._visible = True
        if self._overlay:
            self._overlay.set_visible(True)

    def hide(self) -> None:
        self._visible = False
        if self._overlay:
            self._overlay.set_visible(False)

    def toggle(self) -> None:
        if self._visible:
            self.hide()
        else:
            self.show()

    def update_config(self, config: Dict[str, Any]) -> None:
        self._config = dict(config)
        if self._overlay:
            self._overlay.update_config(self._config)

    def close(self) -> None:
        if self._overlay:
            self._overlay.set_visible(False)
            self._overlay = None

    @property
    def is_visible(self) -> bool:
        return self._visible

    @property
    def config(self) -> Dict[str, Any]:
        return dict(self._config)
