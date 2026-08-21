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
- **Aim script loader** — upload a `.py` plugin, load the bundled sandbox port, or import an `aim-assist-sandbox` folder
- Modular layout so a real virtual-pad backend can replace the simulator
- Vendored copy of the first-person aim-assist sandbox under `vendor/aim-assist-sandbox/`

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
│   ├── app.py              # Wires UI + backend + scripts + tick loop
│   ├── panel.py            # Movable control panel (+ script buttons)
│   └── hud.py              # Transparent always-on-top readout
├── scripts/
│   ├── api.py              # AimScript plugin contract
│   ├── loader.py           # Upload / import / builtin loaders
│   ├── builtin_sandbox_aim.py  # Python port of aimAssist.js
│   ├── example_circle.py   # Sample uploadable script
│   └── uploaded/           # Copies of user-uploaded scripts
├── aimbridge/
│   ├── math3d.py           # Port of sandbox js/math.js
│   ├── mock_scene.py       # Synthetic targets for script testing
│   └── host.py             # Runs loaded script → drives stick
├── vendor/
│   └── aim-assist-sandbox/ # Original JS Three.js sandbox (reference)
└── tests/
    ├── test_state.py
    └── test_scripts.py
```

### How each module works

1. **`controls/state.py`** — Holds `rx`, `ry`, `l2`, `r2`, and `simulation_mode`. Sliders and shortcuts write here (or layer overrides on top). Listeners refresh the UI.
2. **`controls/keyboard.py`** — Application event filter. While a bound key is held, its axis dict is merged over the slider baseline each tick.
3. **`overlay/panel.py`** — Always-on-top tool window with sliders, reset button, simulation checkbox, script upload/load controls, and live readouts.
4. **`overlay/hud.py`** — Frameless translucent window that mirrors the effective axes.
5. **`overlay/app.py`** — Creates Qt app, panel, HUD, keyboard filter, script host, timer (~30 Hz), and calls `backend.push(...)`.
6. **`backend/base.py`** — Abstract `connect` / `disconnect` / `push` API.
7. **`backend/simulation_backend.py`** — Records and prints frames when simulation mode is on. Contains a commented sketch for a future ViGEm/`vgamepad` backend.
8. **`backend/null_backend.py`** — Silent stub for UI dry-runs.
9. **`scripts/`** — Plugin API + loader. Uploaded `.py` files must expose `create_script()` or a `Script` class.
10. **`aimbridge/`** — Math port, mock target scene, and `ScriptHost` that feeds frames into the loaded script.
11. **`config.py`** — Tunables only; no logic.

---

## Loading the aim-assist sandbox into the overlay

The original sandbox is JavaScript/Three.js (`vendor/aim-assist-sandbox/`). The overlay runs a **Python port** of the same pipeline so it can drive stick axes inside PySide.

### In the control panel

| Button | What it does |
|--------|----------------|
| **Load sandbox** | Loads `scripts/builtin_sandbox_aim.py` (port of `js/aimAssist.js`) |
| **Upload .py…** | Copies a Python aim script into `scripts/uploaded/` and loads it |
| **Import folder…** | Copies an `aim-assist-sandbox` tree into `vendor/` (must contain `js/aimAssist.js`) and activates the Python port |
| **Drive stick from loaded script** | Enables the host: mock targets → script → RX/RY each tick |

### Quick try

1. `python main.py`
2. Click **Load sandbox**
3. Check **Drive stick from loaded script**
4. Optionally check **Simulation mode** to log outbound frames
5. Watch RX/RY and the script debug panel track the mock dummies

Upload the included sample instead:

1. **Upload .py…** → choose `scripts/example_circle.py`
2. Enable **Drive stick from loaded script**
3. Stick oscillates in a circle (verifies upload wiring)

### Writing your own script

```python
from scripts.api import AimFrame, StickCommand

class Script:
    name = "my-script"

    def reset(self) -> None:
        pass

    def update(self, frame: AimFrame) -> StickCommand:
        # frame.camera / frame.targets are sandbox-style samples
        return StickCommand(rx=0.0, ry=0.0, debug="idle")

def create_script():
    return Script()
```

Scripts receive normalized camera/target frames from `aimbridge` (or a future adapter). They must not read game memory — feed data in through the frame API.

---

## Simulation mode

1. Open the control panel.
2. Check **Simulation mode (send controller output)**.
3. Move sliders, hold shortcuts, or enable a loaded aim script.
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
python -m unittest tests.test_state tests.test_scripts -v
```

These cover clamping, reset, listeners, override merging, simulation gating, script upload, and the sandbox aim port — no display required.

---

## Notes

- Y axis follows common gamepad convention: **up = negative**, **down = positive**.
- The HUD and panel use `WindowStaysOnTopHint` so they remain visible over Remote Play.
- This repository is for **control testing and tooling**. Respect game and platform terms of service when connecting any virtual device.
