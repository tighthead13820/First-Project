#!/usr/bin/env python3
"""
PS Remote Play control-testing overlay with integrated aim_core pipeline.

Primary live path (Aim Core LIVE):
    ExternalNetworkTargetSource (UDP JSON)
        → ScreenAimEngine (closest-to-centre)
        → StickControllerModel (fixed-sign sandbox maths)
        → RealControllerHardware (VDS4Gamepad)

Usage (Windows):
    python main.py --backend vigem --live
    python tools/send_network_targets.py

Optional sources:
    python main.py --live --source mock-screen
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

# Explicit primary live provider (Aim Core LIVE).
from sources.network_source import ExternalNetworkTargetSource  # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Windows overlay with aim_core live pipeline. "
            "Aim Core LIVE defaults to ExternalNetworkTargetSource (UDP)."
        )
    )
    parser.add_argument(
        "--backend",
        default="simulation",
        choices=["simulation", "null", "vigem", "vigem-ds4", "vigem-x360"],
        help="Virtual-controller backend (default: simulation). Use vigem for DS4 output.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help=(
            "Enable Aim Core LIVE on startup, bind ExternalNetworkTargetSource, "
            "and init RealControllerHardware (Virtual DualShock 4)."
        ),
    )
    parser.add_argument(
        "--source",
        default=None,
        choices=["mock-screen", "mock-world", "network"],
        help=(
            "TargetSource. Default: 'network' when --live, else 'mock-screen'. "
            "network = UDP JSON on --network-port (default 5555)."
        ),
    )
    parser.add_argument(
        "--network-host",
        default="127.0.0.1",
        help="UDP bind host for ExternalNetworkTargetSource (default 127.0.0.1).",
    )
    parser.add_argument(
        "--network-port",
        type=int,
        default=5555,
        help="UDP bind port for ExternalNetworkTargetSource (default 5555).",
    )
    return parser.parse_args(argv)


def resolve_source_kind(args: argparse.Namespace) -> str:
    """Aim Core LIVE prefers ExternalNetworkTargetSource unless overridden."""
    if args.source:
        return args.source
    if args.live:
        return "network"
    return "mock-screen"


def init_live_controller_hardware():
    """
    Explicit hook: register Virtual DualShock 4 before the Qt loop.

    Stick outputs from StickControllerModel are pushed through this bus when
    Simulation mode is armed and Aim Core LIVE is on.
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


def activate_aim_core_live(app) -> None:
    """
    Flip Aim Core LIVE on and ensure the pipeline reads from the configured
    TargetSource (ExternalNetworkTargetSource when --source network / --live).
    """
    src = app.live.target_source
    if isinstance(src, ExternalNetworkTargetSource):
        if not src._started:  # noqa: SLF001 — ensure listener is up
            src.start()
        print(
            f"[main] Aim Core LIVE → ExternalNetworkTargetSource "
            f"udp://{src.host}:{src.port}"
        )
        print(
            "[main] Flow: UDP targets → closest-to-centre → "
            "StickControllerModel → RealControllerHardware"
        )
    else:
        print(
            f"[main] Aim Core LIVE → {src.describe()} "
            f"(use --source network for UDP telemetry)"
        )

    app.panel.aim_core_check.setChecked(True)
    app.live.set_enabled(True)
    app._sync_aim_core_options()
    app._on_aim_core_enabled(True)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    source_kind = resolve_source_kind(args)

    live_hw: Optional[object] = None
    if args.live or args.backend.startswith("vigem") or source_kind == "network":
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

    if source_kind == "network":
        print(
            f"[main] Primary TargetSource = ExternalNetworkTargetSource "
            f"({args.network_host}:{args.network_port})"
        )

    app = OverlayApp(
        backend_kind=args.backend,
        target_source_kind=source_kind,
        controller_hardware=live_hw,
        network_host=args.network_host,
        network_port=args.network_port,
    )

    # Prefer network when Aim Core LIVE is toggled from the panel as well.
    app.prefer_network_on_live = source_kind == "network" or args.live
    app.network_host = args.network_host
    app.network_port = args.network_port

    if args.live:
        activate_aim_core_live(app)

    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())
