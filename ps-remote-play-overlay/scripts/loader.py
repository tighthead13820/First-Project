"""
Load / upload aim scripts into the overlay.

Supported sources
-----------------
1. Bundled sandbox port: ``scripts/builtin_sandbox_aim.py``
2. User ``.py`` files chosen via the Upload button (copied into
   ``scripts/uploaded/`` then imported)
3. Import of a vendored / external ``aim-assist-sandbox`` folder — we keep
   the JS for reference and activate the Python port that mirrors it
"""

from __future__ import annotations

import importlib
import importlib.util
import shutil
import sys
import time
from pathlib import Path
from types import ModuleType
from typing import Optional

from scripts.api import AimScript

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
UPLOADED_DIR = SCRIPTS_DIR / "uploaded"
VENDOR_SANDBOX = ROOT / "vendor" / "aim-assist-sandbox"
BUILTIN_MODULE = "scripts.builtin_sandbox_aim"


class ScriptLoadError(RuntimeError):
    """Raised when a file cannot be imported as an AimScript."""


def ensure_upload_dir() -> Path:
    UPLOADED_DIR.mkdir(parents=True, exist_ok=True)
    init = UPLOADED_DIR / "__init__.py"
    if not init.exists():
        init.write_text('"""User-uploaded aim scripts."""\n', encoding="utf-8")
    return UPLOADED_DIR


def _instantiate(module: ModuleType) -> AimScript:
    if hasattr(module, "create_script") and callable(module.create_script):
        script = module.create_script()
    elif hasattr(module, "Script") and callable(module.Script):
        script = module.Script()
    else:
        raise ScriptLoadError(
            f"Module '{module.__name__}' must define create_script() or Script."
        )
    if not hasattr(script, "update") or not hasattr(script, "reset"):
        raise ScriptLoadError(
            f"Script from '{module.__name__}' missing update()/reset()."
        )
    if not hasattr(script, "name"):
        script.name = module.__name__  # type: ignore[attr-defined]
    return script  # type: ignore[return-value]


def load_module_path(path: Path) -> AimScript:
    """Import a .py file from an arbitrary path and return its AimScript."""
    path = path.resolve()
    if not path.is_file() or path.suffix.lower() != ".py":
        raise ScriptLoadError(f"Not a Python script: {path}")

    module_name = f"aim_uploaded_{path.stem}_{int(time.time() * 1000)}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ScriptLoadError(f"Could not create import spec for {path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return _instantiate(module)


def load_builtin_sandbox() -> AimScript:
    """Load the Python port of vendor/aim-assist-sandbox/js/aimAssist.js."""
    module = importlib.import_module(BUILTIN_MODULE)
    # Reload so tweaks during a session are picked up if re-imported.
    module = importlib.reload(module)
    return _instantiate(module)


def upload_script(source: Path, dest_dir: Optional[Path] = None) -> tuple[Path, AimScript]:
    """
    Copy *source* into ``scripts/uploaded/`` and load it.

    Returns (destination_path, script_instance).
    """
    source = source.resolve()
    if not source.is_file():
        raise ScriptLoadError(f"File not found: {source}")
    if source.suffix.lower() != ".py":
        raise ScriptLoadError(
            "Only .py aim scripts can be executed inside the overlay.\n"
            "For the JS sandbox folder, use 'Load bundled sandbox script' "
            "(Python port of aimAssist.js)."
        )

    dest_root = dest_dir or ensure_upload_dir()
    dest_root.mkdir(parents=True, exist_ok=True)
    dest = dest_root / source.name
    # Avoid clobbering without a stamp if same name re-uploaded.
    if dest.exists() and dest.resolve() != source:
        stamp = time.strftime("%Y%m%d_%H%M%S")
        dest = dest_root / f"{source.stem}_{stamp}{source.suffix}"

    if dest.resolve() != source:
        shutil.copy2(source, dest)

    script = load_module_path(dest)
    return dest, script


def import_sandbox_folder(folder: Path) -> tuple[Path, AimScript]:
    """
    Copy an aim-assist-sandbox folder into vendor/ and activate the builtin port.

    Validates that ``js/aimAssist.js`` exists so users know they imported
    the right tree. The overlay runs the Python port, not the JS itself
    (PySide has no Three.js runtime).
    """
    folder = folder.resolve()
    assist = folder / "js" / "aimAssist.js"
    if not assist.is_file():
        raise ScriptLoadError(
            f"Not an aim-assist-sandbox folder (missing js/aimAssist.js): {folder}"
        )

    dest = VENDOR_SANDBOX
    if dest.resolve() != folder:
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(folder, dest)

    script = load_builtin_sandbox()
    return dest, script


def describe_vendor_sandbox() -> str:
    assist = VENDOR_SANDBOX / "js" / "aimAssist.js"
    if assist.is_file():
        return f"vendored: {assist}"
    return "vendored sandbox not present"
