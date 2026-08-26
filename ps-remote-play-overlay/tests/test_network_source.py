"""
Unit tests for ExternalNetworkTargetSource / UDP JSON parsing.

Does not require a live socket for parse tests; binds an ephemeral port
for the threaded reader smoke test.
"""

from __future__ import annotations

import json
import socket
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sources.network_source import (  # noqa: E402
    ExternalNetworkTargetSource,
    parse_network_payload,
)


class ParsePayloadTests(unittest.TestCase):
    def test_dict_with_targets(self) -> None:
        raw = json.dumps(
            {
                "screen_width": 1920,
                "screen_height": 1080,
                "targets": [
                    {"id": "bot_1", "head_x": 1100, "head_y": 480},
                    {"id": "bot_2", "x": 800, "y": 520},
                ],
            }
        )
        targets, w, h = parse_network_payload(raw)
        self.assertEqual(w, 1920)
        self.assertEqual(h, 1080)
        self.assertEqual(len(targets), 2)
        self.assertEqual(targets[0].id, "bot_1")
        self.assertEqual(targets[0].head_x, 1100.0)
        self.assertEqual(targets[1].chest_y, 545.0)  # 520 + 25 default

    def test_bare_list(self) -> None:
        raw = json.dumps([{"id": "a", "head_x": 960, "head_y": 540}])
        targets, w, h = parse_network_payload(raw)
        self.assertIsNone(w)
        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0].head_x, 960.0)

    def test_empty_and_invalid(self) -> None:
        self.assertEqual(parse_network_payload(""), ([], None, None))
        with self.assertRaises(json.JSONDecodeError):
            parse_network_payload("{not json")


class NetworkSourceThreadTests(unittest.TestCase):
    def test_udp_packet_updates_targets(self) -> None:
        # Bind ephemeral port to avoid colliding with a running app on 5555.
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
        probe.close()

        src = ExternalNetworkTargetSource(
            host="127.0.0.1",
            port=port,
            auto_start=True,
            stale_seconds=2.0,
        )
        try:
            payload = json.dumps(
                {
                    "targets": [
                        {"id": "net_a", "head_x": 1000, "head_y": 500},
                    ]
                }
            ).encode("utf-8")
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(payload, ("127.0.0.1", port))
            sock.close()

            # Wait for reader thread
            deadline = time.time() + 2.0
            targets = []
            while time.time() < deadline:
                targets = src.get_targets()
                if targets:
                    break
                time.sleep(0.02)

            self.assertEqual(len(targets), 1)
            self.assertEqual(targets[0].id, "net_a")
            self.assertEqual(targets[0].head_x, 1000.0)
            self.assertTrue(src.stats()["packets_received"] >= 1)
        finally:
            src.stop()


if __name__ == "__main__":
    unittest.main()
