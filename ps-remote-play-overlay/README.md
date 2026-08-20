# PS Remote Play Control Overlay

Windows Python desktop overlay for **testing** PlayStation Remote Play control axes (right stick + L2/R2). Transparent always-on-top HUD, small movable panel, optional hold-to-set keyboard shortcuts, and a pluggable virtual-controller backend.

This project does **not** inject into games or Remote Play. It is a local tester with a clean seam where a legitimate virtual-controller driver (e.g. ViGEm + `vgamepad`) can be connected later.

---

## Features

- Transparent, always-on-top HUD showing live **RX / RY / L2 / R2**
- Small movable control panel
- Right-stick **X** and **Y** sliders (`-1.0` … `+1.0`) plus **Reset to centre**
- **L2** and **R2** analog sliders (`0.0` … `1.0`)
- Optional keyboard shortcuts that set values **only while keys are held**
- **Simulation mode** toggle — when on, axes are pushed through the active backend
- Modular layout so a real virtual-pad backend can replace the simulator

---

## Requirements

- Windows 10/11 (designed for desktop overlay use)
- Python **3.10+**
- Dependencies in `requirements.txt` (primarily **PySide6**)

> The UI can start on other OSes for development, but always-on-top / translucent behaviour is validated for Windows.

---

## Installation

```bat
cd ps-remote-play-overlay
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

---

## Run

```bat
python main.py
```

Backend options:

```bat
python main.py --backend simulation
python main.py --backend null
```

| Backend       | Behaviour |
|---------------|-----------|
| `simulation`  | Default. When **Simulation mode** is checked, each tick logs frames that would be sent to a virtual pad. |
| `null`        | UI only. Never emits output. |

---

## Keyboard shortcuts (hold to set)

Configured in `config.py` → `SHORTCUTS`:

| Key    | Effect                          |
|--------|---------------------------------|
| ← / →  | Right stick X = -1.0 / +1.0     |
| ↑ / ↓  | Right stick Y = -1.0 / +1.0     |
| Q      | L2 = 1.0                        |
| E      | R2 = 1.0                        |
| C      | Right stick → centre (0, 0)     |

Releasing a key restores the **slider baseline**. Edit `config.py` to change bindings.

---

## Project layout

```
ps-remote-play-overlay/
├── main.py                 # CLI entry point
├── config.py               # Ranges, tick rate, shortcut map
├── requirements.txt
├── README.md
├── controls/
│   ├── state.py            # ControllerState (single source of truth)
│   └── keyboard.py         # Hold-to-set shortcut filter
├── backend/
│   ├── base.py             # VirtualControllerBackend ABC
│   ├── null_backend.py     # No-op backend
│   ├── simulation_backend.py
│   └── __init__.py         # create_backend() factory
├── overlay/
│   ├── app.py              # Wires UI + backend + tick loop
│   ├── panel.py            # Movable control panel
│   └── hud.py              # Transparent always-on-top readout
└── tests/
    └── test_state.py       # Unit tests (no GUI)
```

### How each module works

1. **`controls/state.py`** — Holds `rx`, `ry`, `l2`, `r2`, and `simulation_mode`. Sliders and shortcuts write here (or layer overrides on top). Listeners refresh the UI.
2. **`controls/keyboard.py`** — Application event filter. While a bound key is held, its axis dict is merged over the slider baseline each tick.
3. **`overlay/panel.py`** — Always-on-top tool window with sliders, reset button, simulation checkbox, and a live text readout.
4. **`overlay/hud.py`** — Frameless translucent window that mirrors the effective axes.
5. **`overlay/app.py`** — Creates Qt app, panel, HUD, keyboard filter, timer (~30 Hz), and calls `backend.push(...)`.
6. **`backend/base.py`** — Abstract `connect` / `disconnect` / `push` API.
7. **`backend/simulation_backend.py`** — Records and prints frames when simulation mode is on. Contains a commented sketch for a future ViGEm/`vgamepad` backend.
8. **`backend/null_backend.py`** — Silent stub for UI dry-runs.
9. **`config.py`** — Tunables only; no logic.

---

## Simulation mode

1. Open the control panel.
2. Check **Simulation mode (send controller output)**.
3. Move sliders or hold shortcuts.
4. With the default `simulation` backend, the console prints throttled lines such as:

   ```text
   [simulation] RX=+0.50 RY=-0.20 L2=0.00 R2=1.00
   ```

When simulation mode is **off**, backends that respect the flag (including `SimulationBackend`) do not emit frames.

---

## Plugging in a real virtual controller later

1. Subclass `VirtualControllerBackend` in a new module (e.g. `backend/vigem_backend.py`).
2. In `connect()`, open your virtual pad.
3. In `push(state)`, map `state.rx/ry/l2/r2` onto the driver and call update — **only when** `state.simulation_mode` is true (or rename that flag to “output enabled” if you prefer).
4. Register the class in `backend.create_backend()`.
5. Run with `python main.py --backend <your-name>`.

A commented example using `vgamepad` lives at the top of `backend/simulation_backend.py`. You will also need the matching Windows driver (commonly ViGEmBus) installed separately.

---

## Tests

```bat
python -m unittest tests.test_state -v
```

These cover clamping, reset, listeners, override merging, and simulation gating — no display required.

---

## Notes

- Y axis follows common gamepad convention: **up = negative**, **down = positive**.
- The HUD and panel use `WindowStaysOnTopHint` so they remain visible over Remote Play.
- This repository is for **control testing and tooling**. Respect game and platform terms of service when connecting any virtual device.
