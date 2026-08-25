# PS Remote Play Control Overlay

Windows Python desktop overlay for **testing** PlayStation Remote Play control axes, with an integrated **aim_core** pipeline ported from the working `aim-assist-sandbox` (branch `cursor/fix-camera-yaw-pitch-7c02`).

Includes transparent HUD, movable panel, live aim-core automation (mock targets), ViGEm virtual-controller output, and the legacy script upload path.

---

## Important scope note

This overlay **does not** ship automated PS Remote Play screen capture or in-game object detection. The live pipeline uses **mock target sources** for end-to-end validation. The `TargetSource` interface is the extension point if you build your own adapter.

ViGEm sends whatever stick/trigger values the overlay computes — it does not read the game video.

---

## Live production pipeline

```
TargetSource (mock-screen / mock-world)
    ↓
aim_core (selection, head tracking, yaw/pitch error)
    ↓
StickControllerModel (pixel/angle → stick X/Y)
    ↓
ControllerState
    ↓
vgamepad / ViGEmBackend (when --backend vigem)
    ↓
Virtual DualShock 4 (Windows)
```

Enable in the panel: **Aim Core (LIVE)** → **Enable live aim core pipeline** + **Simulation mode**.

---

## Features

- Transparent axis HUD + full-screen **aim visualization** (crosshair, FOV, target marker, trail)
- **Production dashboard** with pixel error, yaw/pitch error, stick output, hardware bus status
- **aim_core** — pure Python, no GUI; fixed Three.js YXZ yaw/pitch signs
- Screen-space closest-to-centre selection, head tracking, snap/smooth modes, prediction
- **ViGEm** backend (`vigem`, `vigem-ds4`, `vigem-x360`)
- Legacy: sliders, keyboard shortcuts, script upload, mock 3D script host

---

## Requirements

- Windows 10/11
- Python **3.10+**
- PySide6
- For real pad output: [ViGEmBus](https://github.com/nefarius/ViGEmBus/releases) + `vgamepad`

---

## Installation (Windows)

```bat
cd ps-remote-play-overlay
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m unittest discover -s tests -v
```

---

## Run

### Mock live pipeline (development)

```bat
python main.py --live
```

### Real virtual DualShock 4

```bat
python main.py --backend vigem --live
```

1. Install ViGEmBus  
2. Enable **Simulation mode** in the panel (arms hardware output)  
3. Enable **Aim Core (LIVE)**  
4. Confirm a virtual DS4 in Windows Game Controllers  

### CLI options

| Flag | Description |
|------|-------------|
| `--backend simulation` | Log frames only (default) |
| `--backend vigem` | Virtual DualShock 4 |
| `--backend vigem-x360` | Virtual Xbox 360 |
| `--live` | Enable aim core on startup |
| `--source mock-screen` | Animated 2D screen targets (default) |
| `--source mock-world` | 3D world targets projected to screen |
| `--source network` | UDP JSON telemetry on `--network-port` (default 5555) |

Preflight: `--backend vigem` runs all unit tests before starting the hardware loop.

---

## Reused from aim-assist-sandbox

| Sandbox file | Python module | What was ported |
|--------------|---------------|-----------------|
| `js/math.js` | `aim_core/math3d.py` | `forwardFromAngles`, `anglesFromDirection`, `angleBetween`, `angleDelta`, `expSmoothAngle`, `getBoneWorldPosition`, `predictPosition`, FOV radius |
| `js/aimAssist.js` | `aim_core/engine.py` | Target selection, sticky lock, screen-wide select, snap/smooth, live aim point refresh |
| `js/aimAssist.js` | `aim_core/screen_engine.py` | Closest-to-centre screen selection, pixel→angle error |
| — | `aim_core/stick_model.py` | Yaw/pitch/pixel error → stick X/Y |

**Preserved yaw/pitch fix** (`cursor/fix-camera-yaw-pitch-7c02`):

```python
# forward (YXZ)
forward.x = -cos(pitch) * sin(yaw)
forward.y =  sin(pitch)
forward.z = -cos(pitch) * cos(yaw)

# angles from direction
pitch = asin(dy)
yaw   = -atan2(dx, -dz)
```

Legacy broken signs remain as `angles_from_direction_legacy()` for tests only.

---

## Project layout

```
ps-remote-play-overlay/
├── aim_core/               # Pure Python aim maths (no GUI)
│   ├── math3d.py           # Fixed YXZ port of math.js
│   ├── engine.py           # 3D world aim engine
│   ├── screen_engine.py    # 2D screen-space aim
│   └── stick_model.py      # Error → hardware stick
├── sources/                # TargetSource implementations
│   ├── base.py             # TargetSource ABC
│   ├── mock_screen_source.py
│   └── world_mock_source.py
├── pipeline/
│   └── live_engine.py      # Live loop → ControllerState → ViGEm
├── overlay/
│   ├── app.py              # Main shell
│   ├── panel.py            # Control + production dashboard
│   ├── hud.py              # Axis readout
│   └── aim_viz_hud.py      # Crosshair / target / FOV overlay
├── backend/                # simulation / null / vigem
├── controls/               # state + keyboard
├── scripts/                # Legacy uploadable scripts
└── tests/
    ├── test_aim_core.py    # Verification suite (run before ViGEm)
    ├── test_state.py
    └── test_scripts.py
```

---

## Network telemetry TargetSource

External apps can push target coordinates over UDP (no screen capture).

```bat
python main.py --backend vigem --live --source network
python tools/send_network_targets.py
```

Default bind: `127.0.0.1:5555`. Packet example:

```json
{
  "screen_width": 1920,
  "screen_height": 1080,
  "targets": [
    {"id": "bot_1", "head_x": 1100, "head_y": 480}
  ]
}
```

Flow: UDP JSON → `ExternalNetworkTargetSource` → closest-to-centre → stick model → `RealControllerHardware` (when Simulation + Aim Core LIVE are on).

---

## Aim state flow (when Aim Core LIVE is on)

1. `TargetSource.tick(dt)` advances mock targets  
2. `ScreenAimEngine.update()` selects closest visible head to screen centre  
3. Pixel error → yaw/pitch error → `StickControllerModel` → `stick_x/stick_y`  
4. Optional L2/R2 + recoil bias applied  
5. `ControllerState` updated → merged with keyboard overrides  
6. `ViGEmBackend.push()` when simulation mode is on  
7. Dashboard + aim viz HUD refreshed  

---

## TargetSource interface

```python
class TargetSource:
    def get_screen_targets(self) -> list[ScreenTarget]: ...
    def get_world_targets(self) -> list[WorldTarget]: ...
    def get_camera_state(self) -> CameraState: ...
    def tick(self, dt: float) -> None: ...
```

Each `ScreenTarget` includes: `id`, `screen_x/y`, `head_x/y`, `chest_x/y`, velocities, `alive`, `visible`, `team`.

---

## Tests

```bat
python -m unittest discover -s tests -v
```

`test_aim_core.py` covers: centre target → zero stick, left/right/up/down, moving targets, disappearing targets, multi-target selection, clamping, smoothing convergence, yaw/pitch sign orientation, prediction on/off, fixed vs legacy signs.

---

## Keyboard shortcuts

See `config.py` → `SHORTCUTS` (arrows, Q/E L2/R2, C = centre).

---

## Notes

- Y axis: **up = negative**, **down = positive** (gamepad convention; ViGEm backend flips Y for the driver).
- Aim Core LIVE and **Drive stick from script** are mutually exclusive (enabling one disables the other).
- Respect game and platform terms of service when using virtual controllers.
