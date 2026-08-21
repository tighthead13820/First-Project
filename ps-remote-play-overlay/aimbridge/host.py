"""
Hosts a loaded AimScript, feeds it mock (or external) frames, and applies
stick output onto ControllerState when script mode is enabled.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from aimbridge.mock_scene import MockScene
from controls.state import ControllerState
from scripts.api import AimScript, StickCommand
from scripts.loader import (
    ScriptLoadError,
    import_sandbox_folder,
    load_builtin_sandbox,
    upload_script,
)


class ScriptHost:
    """Owns the active script instance + enable flag."""

    def __init__(self, state: ControllerState) -> None:
        self.state = state
        self.script: Optional[AimScript] = None
        self.source_path: Optional[Path] = None
        self.enabled = False
        self.last_debug = ""
        self.last_command = StickCommand()
        self.scene = MockScene()

    @property
    def script_name(self) -> str:
        if self.script is None:
            return "(none)"
        return getattr(self.script, "name", "unnamed")

    def load_builtin(self) -> str:
        self.script = load_builtin_sandbox()
        self.script.reset()
        self.source_path = (
            Path(__file__).resolve().parents[1]
            / "scripts"
            / "builtin_sandbox_aim.py"
        )
        self.last_debug = f"Loaded builtin: {self.script_name}"
        return self.last_debug

    def upload(self, path: Path) -> str:
        dest, script = upload_script(path)
        script.reset()
        self.script = script
        self.source_path = dest
        self.last_debug = f"Uploaded: {dest.name} ({self.script_name})"
        return self.last_debug

    def import_sandbox(self, folder: Path) -> str:
        dest, script = import_sandbox_folder(folder)
        script.reset()
        self.script = script
        self.source_path = dest / "js" / "aimAssist.js"
        self.last_debug = (
            f"Imported sandbox → {dest} (running Python port of aimAssist.js)"
        )
        return self.last_debug

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)
        if self.enabled and self.script is None:
            # Auto-load bundled port so Enable "just works".
            self.load_builtin()
        if self.script is not None:
            self.script.reset()
        if not self.enabled:
            # Return stick to centre when disabling script drive.
            self.state.set_right_stick(0.0, 0.0)

    def tick(self, dt: float) -> None:
        if not self.enabled or self.script is None:
            return

        frame = self.scene.tick(dt)
        # Keep the script's internal yaw/pitch aligned with the mock camera
        # so cone tests match the simulated look direction.
        try:
            cmd = self.script.update(frame)
        except Exception as exc:  # noqa: BLE001 — surface to HUD, keep overlay alive
            self.last_debug = f"Script error: {exc}"
            return

        self.last_command = cmd
        self.last_debug = cmd.debug or self.last_debug
        # Drive stick from script; leave triggers unless script sets them.
        self.state.set_right_stick(cmd.rx, cmd.ry, notify=True)
        if cmd.l2 is not None:
            self.state.set_l2(cmd.l2, notify=True)
        if cmd.r2 is not None:
            self.state.set_r2(cmd.r2, notify=True)


# Re-export for callers that catch load failures.
__all__ = ["ScriptHost", "ScriptLoadError"]
