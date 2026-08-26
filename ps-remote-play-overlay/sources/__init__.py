"""Target input sources for the live aim pipeline."""

from .base import TargetSource
from .mock_screen_source import MockScreenTargetSource
from .network_source import ExternalNetworkTargetSource, parse_network_payload
from .world_mock_source import WorldMockTargetSource


def create_target_source(
    kind: str = "mock-screen",
    *,
    host: str = "127.0.0.1",
    port: int = 5555,
) -> TargetSource:
    """Factory used by main.py / OverlayApp."""
    key = (kind or "mock-screen").strip().lower()
    if key in {"mock-screen", "mock", "screen"}:
        return MockScreenTargetSource()
    if key in {"mock-world", "world"}:
        return WorldMockTargetSource()
    if key in {"network", "udp", "external-network", "external"}:
        return ExternalNetworkTargetSource(host=host, port=port, auto_start=True)
    raise ValueError(
        f"Unknown target source '{kind}'. "
        "Use mock-screen, mock-world, or network."
    )


__all__ = [
    "TargetSource",
    "MockScreenTargetSource",
    "WorldMockTargetSource",
    "ExternalNetworkTargetSource",
    "parse_network_payload",
    "create_target_source",
]
