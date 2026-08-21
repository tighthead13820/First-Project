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
            # Return stick + triggers to rest when disabling script drive.
            self.state.set_right_stick(0.0, 0.0)
            self.state.set_l2(0.0)
            self.state.set_r2(0.0)

    def apply_fire_options(
        self,
        *,
        auto_fire_l2: bool | None = None,
        auto_fire_r2: bool | None = None,
        recoil_compensate: bool | None = None,
        recoil_vertical: float | None = None,
        recoil_horizontal: float | None = None,
    ) -> None:
        """Push panel toggles into the loaded script when it exposes settings."""
        script = self.script
        settings = getattr(script, "settings", None) if script is not None else None
        if settings is None:
            return
        if auto_fire_l2 is not None and hasattr(settings, "auto_fire_l2"):
            settings.auto_fire_l2 = bool(auto_fire_l2)
        if auto_fire_r2 is not None and hasattr(settings, "auto_fire_r2"):
            settings.auto_fire_r2 = bool(auto_fire_r2)
        if recoil_compensate is not None and hasattr(settings, "recoil_compensate"):
            settings.recoil_compensate = bool(recoil_compensate)
        if recoil_vertical is not None and hasattr(settings, "recoil_vertical"):
            settings.recoil_vertical = float(recoil_vertical)
        if recoil_horizontal is not None and hasattr(settings, "recoil_horizontal"):
            settings.recoil_horizontal = float(recoil_horizontal)
        if script is not None:
            # Restart fire timer so ramp feels consistent after option changes.
            if hasattr(script, "_fire_time"):
                script._fire_time = 0.0  # noqa: SLF001 — intentional reset

    def fire_options(self) -> dict[str, bool | float]:
        settings = getattr(self.script, "settings", None) if self.script else None
        if settings is None:
            return {
                "auto_fire_l2": True,
                "auto_fire_r2": True,
                "recoil_compensate": True,
                "recoil_vertical": 0.35,
                "recoil_horizontal": 0.08,
            }
        return {
            "auto_fire_l2": bool(getattr(settings, "auto_fire_l2", True)),
            "auto_fire_r2": bool(getattr(settings, "auto_fire_r2", True)),
            "recoil_compensate": bool(getattr(settings, "recoil_compensate", True)),
            "recoil_vertical": float(getattr(settings, "recoil_vertical", 0.35)),
            "recoil_horizontal": float(getattr(settings, "recoil_horizontal", 0.08)),
        }

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
