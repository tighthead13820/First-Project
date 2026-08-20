#!/usr/bin/env python3
"""
PS Remote Play control-testing overlay.

Transparent always-on-top HUD + movable panel for right-stick and
L2/R2 analog values. Optional keyboard hold-to-set shortcuts.
Simulation mode forwards axes through a pluggable backend.

Usage (Windows):
    python -m venv .venv
    .venv\\Scripts\\activate
    pip install -r requirements.txt
    python main.py

Backend selection:
    python main.py --backend simulation   # default: logs outbound frames
    python main.py --backend null         # UI only, no output path
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running as ``python main.py`` from the project root without install.
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Windows overlay for testing PS Remote Play control axes."
    )
    parser.add_argument(
        "--backend",
        default="simulation",
        choices=["simulation", "null"],
        help="Virtual-controller backend (default: simulation).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    from overlay.app import run

    return run(backend_kind=args.backend)


if __name__ == "__main__":
    raise SystemExit(main())
