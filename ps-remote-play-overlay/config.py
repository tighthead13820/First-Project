"""
Application configuration and default keyboard bindings.

Edit SHORTCUTS to change which keys manually drive axes while held.
Values are applied only for the duration of the key press; releasing
the key restores the slider / previous non-shortcut value.
"""

from __future__ import annotations

# How often the HUD and backends refresh (milliseconds).
UI_TICK_MS = 33  # ~30 Hz — fine for testing; raise for smoother feel.

# Default window geometry.
PANEL_WIDTH = 340
PANEL_HEIGHT = 620
HUD_WIDTH = 220
HUD_HEIGHT = 120

# Keyboard shortcuts (Qt key names as strings; resolved at runtime).
# Hold a key to force that axis to the listed value; release to restore.
SHORTCUTS: dict[str, dict[str, float]] = {
    # Right stick
    "Left": {"rx": -1.0},
    "Right": {"rx": 1.0},
    "Up": {"ry": -1.0},  # up = negative Y (common gamepad convention)
    "Down": {"ry": 1.0},
    # Triggers
    "Q": {"l2": 1.0},
    "E": {"r2": 1.0},
    # Centre stick quickly
    "C": {"rx": 0.0, "ry": 0.0},
}

# Soft clamp helpers used across modules.
RX_RANGE = (-1.0, 1.0)
RY_RANGE = (-1.0, 1.0)
TRIGGER_RANGE = (0.0, 1.0)
