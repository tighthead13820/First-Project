#!/usr/bin/env python3
"""
PS Remote Play control-testing overlay with integrated aim_core pipeline.

Usage (Windows / PS5 Remote Play):
    python -m venv .venv
    .venv\\Scripts\\activate
    pip install -r requirements.txt
    python -m unittest discover -s tests -v
    python main.py --backend vigem --live

Backend selection:
    python main.py --backend simulation
    python main.py --backend vigem          # Virtual DualShock 4 (PS Remote Play)
    python main.py --backend vigem-x360

Live aim core:
    python main.py --live                   # mock screen targets (default)
    python main.py --live --source mock-world
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Windows overlay with aim_core live pipeline."
    )
    parser.add_argument(
        "--backend",
        default="simulation",
        choices=["simulation", "null", "vigem", "vigem-ds4", "vigem-x360"],
        help="Virtual-controller backend (default: simulation). Use vigem for PS Remote Play.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Enable aim core pipeline on startup and init Virtual DualShock 4 driver.",
    )
    parser.add_argument(
        "--source",
        default="mock-screen",
        choices=["mock-screen", "mock-world"],
        help="TargetSource for live pipeline (default: mock-screen).",
    )
    return parser.parse_args(argv)


def init_live_controller_hardware():
    """
    Explicit hook: register Virtual DualShock 4 before the Qt loop.

    Called when --live and/or --backend vigem* so Aim Core (LIVE) can push
    stick input through RealControllerHardware immediately.
    """
    from controller_hardware import HAS_VGAMEPAD, RealControllerHardware

    if not HAS_VGAMEPAD:
        print(
            "[main] vgamepad not installed — hardware loop disabled.\n"
            "       pip install vgamepad  (+ ViGEmBus on Windows)"
        )
        return None
    hw = RealControllerHardware()
    if hw.enabled:
        print("[main] RealControllerHardware ready (VDS4Gamepad).")
    return hw


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    live_hw: Optional[object] = None
    if args.live or args.backend.startswith("vigem"):
        live_hw = init_live_controller_hardware()

    # Run verification tests before live hardware loop when using ViGEm.
    if args.backend.startswith("vigem"):
        import unittest

        print("[preflight] Running aim_core verification tests…")
        loader = unittest.TestLoader()
        suite = loader.discover("tests", pattern="test_*.py")
        result = unittest.TextTestRunner(verbosity=1).run(suite)
        if not result.wasSuccessful():
            print("[preflight] Tests failed — aborting hardware loop.")
            return 1
        print("[preflight] All tests passed.")

    from overlay.app import OverlayApp

    app = OverlayApp(
        backend_kind=args.backend,
        target_source_kind=args.source,
        controller_hardware=live_hw,
    )
    if args.live:
        app.panel.aim_core_check.setChecked(True)
        app.live.set_enabled(True)
        app._sync_aim_core_options()
        app._on_aim_core_enabled(True)
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())
