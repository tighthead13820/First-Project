#!/usr/bin/env python3
"""
Send sample UDP target packets to ExternalNetworkTargetSource.

Usage:
  python tools/send_network_targets.py
  python tools/send_network_targets.py --host 127.0.0.1 --port 5555
"""

from __future__ import annotations

import argparse
import json
import math
import socket
import time


def main() -> int:
    parser = argparse.ArgumentParser(description="UDP target telemetry sender")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5555)
    parser.add_argument("--hz", type=float, default=30.0)
    args = parser.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    t0 = time.time()
    print(f"Sending to udp://{args.host}:{args.port} at {args.hz} Hz (Ctrl+C to stop)")
    try:
        while True:
            t = time.time() - t0
            cx, cy = 960.0, 540.0
            payload = {
                "screen_width": 1920,
                "screen_height": 1080,
                "targets": [
                    {
                        "id": "bot_orbit",
                        "head_x": cx + math.sin(t) * 180,
                        "head_y": cy + math.cos(t * 0.8) * 90,
                        "alive": True,
                        "visible": True,
                    },
                    {
                        "id": "bot_left",
                        "head_x": 720,
                        "head_y": 520 + math.sin(t * 1.3) * 40,
                    },
                ],
            }
            sock.sendto(json.dumps(payload).encode("utf-8"), (args.host, args.port))
            time.sleep(1.0 / max(args.hz, 1.0))
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        sock.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
