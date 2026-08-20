"""
Optional keyboard shortcuts that manually set axes while keys are held.

Bindings come from config.SHORTCUTS. Multiple held keys merge (later
keys overwrite earlier ones for the same axis). Releasing all shortcut
keys restores the slider baseline stored in ControllerState.
"""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import QObject, Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QApplication

import config
from controls.state import ControllerState


def _resolve_key(name: str) -> Optional[int]:
    """Map a config key name (e.g. 'Left', 'Q') to a Qt.Key value."""
    # Arrow keys and single letters are the common cases.
    special = {
        "Left": Qt.Key.Key_Left,
        "Right": Qt.Key.Key_Right,
        "Up": Qt.Key.Key_Up,
        "Down": Qt.Key.Key_Down,
        "Space": Qt.Key.Key_Space,
        "Shift": Qt.Key.Key_Shift,
        "Control": Qt.Key.Key_Control,
        "Alt": Qt.Key.Key_Alt,
        "Escape": Qt.Key.Key_Escape,
    }
    if name in special:
        return int(special[name])
    seq = QKeySequence(name)
    if seq.count() == 0:
        return None
    return int(seq[0].key())


class KeyboardController(QObject):
    """
    Installs an application-wide event filter for hold-to-set shortcuts.

    The panel sliders remain the persistent baseline. While a shortcut
    key is held, its override is layered on top and pushed to listeners
    via on_override_changed. On release, the baseline is restored.
    """

    def __init__(
        self,
        state: ControllerState,
        on_override_changed: Callable[[], None],
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._state = state
        self._on_override_changed = on_override_changed
        self._bindings: dict[int, dict[str, float]] = {}
        self._held: dict[int, dict[str, float]] = {}
        self._enabled = True
        self._load_bindings()

    def _load_bindings(self) -> None:
        self._bindings.clear()
        for name, axes in config.SHORTCUTS.items():
            key = _resolve_key(name)
            if key is None:
                print(f"[keyboard] warning: could not resolve key '{name}'")
                continue
            self._bindings[key] = dict(axes)

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = bool(enabled)
        if not self._enabled and self._held:
            self._held.clear()
            self._on_override_changed()

    def install(self, app: QApplication) -> None:
        app.installEventFilter(self)

    def active_overrides(self) -> list[dict[str, float]]:
        return list(self._held.values())

    def eventFilter(self, obj, event):  # noqa: N802 (Qt naming)
        from PySide6.QtCore import QEvent

        if not self._enabled:
            return False

        etype = event.type()
        if etype == QEvent.Type.KeyPress and not event.isAutoRepeat():
            key = int(event.key())
            if key in self._bindings and key not in self._held:
                self._held[key] = self._bindings[key]
                self._apply_held()
                return True
        elif etype == QEvent.Type.KeyRelease and not event.isAutoRepeat():
            key = int(event.key())
            if key in self._held:
                del self._held[key]
                self._apply_held()
                return True
        return False

    def _apply_held(self) -> None:
        """
        Notify the app that overrides changed.

        We do not permanently mutate slider baselines here — the app
        merges baseline + overrides each tick before pushing to backends.
        """
        self._on_override_changed()
