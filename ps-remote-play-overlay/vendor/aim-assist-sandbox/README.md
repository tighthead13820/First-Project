# Aim-Assist Target-Tracking Sandbox

A self-contained, browser-based first-person sandbox for studying target detection, cone-of-view filtering, angle math, smoothing, and movement prediction. It does **not** interact with any external game or process.

## Quick start

Serve the folder over HTTP (ES modules require a local server):

```bash
cd aim-assist-sandbox
python3 -m http.server 8080
```

Open [http://localhost:8080](http://localhost:8080) in a modern browser.

Alternatively, with Node.js:

```bash
npx --yes serve aim-assist-sandbox -p 8080
```

## Controls

| Input | Action |
|-------|--------|
| Click canvas | Capture mouse (pointer lock) |
| Mouse | Look around |
| W / A / S / D | Move horizontally |
| Space / Shift | Move up / down |
| Esc | Release mouse |

## Settings panel

| Setting | Description |
|---------|-------------|
| **Aim assist** | Toggle the assist system on/off |
| **FOV (°)** | Half-angle of the detection cone around the crosshair |
| **Smoothing** | How quickly the camera rotates toward the target (0.01 = very smooth, 1 = instant) |
| **Target bone** | Aim at **head** or **chest** offset on each dummy |
| **Max range (m)** | Ignore targets beyond this distance |
| **Prediction** | Extrapolate target position using velocity and projectile travel time |
| **Projectile speed** | Used only when prediction is enabled |

## Visual feedback

- **Blue circle** — aim-assist FOV cone projected onto the screen (centered on the crosshair).
- **Green circle + fill** — a target is currently selected inside the cone.
- **Green highlight** — the locked dummy target in the 3D scene.
- **HUD readout** — distance, cone angle, and computed yaw/pitch for the selected target.

## Project layout

```
aim-assist-sandbox/
├── index.html          Entry point and settings UI
├── css/style.css       HUD styling
├── js/
│   ├── main.js         Scene, camera, input, game loop
│   ├── math.js         Vector/angle utilities (heavily commented)
│   ├── aimAssist.js    Target selection and smooth rotation
│   ├── targets.js      Moving dummy targets
│   └── ui.js           Settings bindings and FOV overlay
└── README.md
```

## How the aim assist works

Each frame, the system runs this pipeline:

1. **Forward vector** — Build a unit vector from the camera's current yaw and pitch using spherical-to-Cartesian conversion (see `forwardFromAngles` in `js/math.js`).

2. **Aim point** — For each dummy, compute a world position at the chosen bone height (head or chest). If prediction is on, offset that point by `velocity × travelTime`, where `travelTime = distance / projectileSpeed`.

3. **Cone test** — Compute the angle between the forward vector and the direction to the aim point via the dot product: `θ = acos(forward · toTarget)`. Keep targets where `θ ≤ FOV/2` and `distance ≤ maxRange`.

4. **Best target** — Among valid targets, pick the one with the **smallest** angle to the crosshair (closest to center of screen).

5. **Desired angles** — Convert the direction vector to yaw/pitch: `pitch = asin(-dy)`, `yaw = atan2(dx, -dz)`.

6. **Smooth rotation** — Interpolate current yaw/pitch toward the desired values using shortest-path angle lerping (handles the ±π wrap-around).

## Vector math reference

All formulas are documented inline in `js/math.js`. Key ideas:

- **Dot product for angle**: `cos θ = a · b` when both vectors are unit length.
- **atan2 for yaw**: Returns the full -π…π range, unlike `atan` which loses quadrant information.
- **Angle delta wrapping**: When interpolating yaw, add/subtract 2π so rotation takes the shortest path.
- **Screen FOV circle**: `radius = tan(aimFov/2) × focalLength`, where focal length is derived from the camera's vertical FOV.

## Educational use

This sandbox is intended for learning about:

- Field-of-view target filtering
- Crosshair-proximity target prioritization
- First-person yaw/pitch decomposition
- Exponential smoothing / interpolation
- Lead targeting (simple linear prediction)

It is **not** designed for use with real games or external processes.
