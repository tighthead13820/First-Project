# Universal Aim-Assist Research Framework

A modular, **legitimate-research-only** framework that separates **game-independent aiming mathematics** from **environment-specific adapters**. Use it in games, simulations, and test environments **you own** or that expose a **supported modding/plugin API**.

## What this is NOT

This project deliberately excludes:

- DLL / process injection
- Arbitrary process memory read/write
- Anti-cheat bypasses
- Kernel drivers
- API hooking into third-party games
- Packet manipulation
- Input spoofing to defeat protections
- Stealth / evasion

If an environment cannot supply camera and target state through its official API, **do not integrate it** — document the limitation instead.

## Architecture

```
Game / Simulation
        ↓
   Game Adapter          ← IGameAdapter: normalize engine state
        ↓
 Normalized Target + Camera Data
        ↓
      Aim Core            ← pure maths, zero engine code
        ↓
 Target Selection         ← FOV cone, team/alive/visibility filters
        ↓
 Prediction               ← velocity × travel time, optional gravity
        ↓
 Desired Aim Angles        ← pitch/yaw from camera to aim point
        ↓
 Smoothing                ← horizontal/vertical, lock + switch delay
        ↓
 Game Adapter             ← optional applyCameraAngles()
        ↓
 Camera / Debug Overlay
```

## Repository layout

```
aim-assist-framework/
├── packages/
│   ├── core/                 Aim Core (TypeScript, tested)
│   ├── simulator/            Adapter A — built-in 3D test environment
│   └── browser-bridge/       Adapter B — bridge to aim-assist-sandbox
├── adapters/
│   ├── godot-4/              Adapter C — Godot 4 GDScript example
│   └── bo2-plutonium/        Adapter D — Plutonium T6 GSC (private MP)
├── README.md
aim-assist-sandbox/           Existing browser sandbox (unchanged core)
bo2-plutonium-target-tracker/ Earlier minimal GSC debug script
```

## Quick start

```bash
cd aim-assist-framework
npm install
npm test          # 19 deterministic maths tests
npm run build     # compile core + browser-bridge
npm run simulator # http://localhost:5173 — full test environment
```

## 1. How the architecture works

**Aim Core** (`packages/core`) exposes pure functions and `AimAssistEngine`. It never imports Three.js, Godot, or GSC.

**Adapters** implement `IGameAdapter`:

```typescript
interface IGameAdapter {
  getCameraState(): CameraState;
  getTargets(): Target[];
  applyCameraAngles?(pitch: number, yaw: number): void;
  worldToScreen(position: Vec3): Vec2 | null;
}
```

Each frame: adapter supplies data → core selects target → computes desired angles → smooths → adapter optionally applies rotation.

## 2. Why Aim Core is game-independent

All engine-specific concepts are normalized into `Target` and `CameraState` before entering the core. The core only uses vector algebra, dot products, and angle interpolation — the same operations whether the source is Three.js, Godot, or a unit test mock.

## 3. How adapters supply game state

| Adapter | Environment | API source |
|---------|-------------|------------|
| A — Simulator | `@aim-framework/simulator` | Three.js `PerspectiveCamera`, mesh positions |
| B — Browser | `@aim-framework/browser-bridge` | Existing sandbox `player`, `targets`, `camera` |
| C — Godot 4 | `adapters/godot-4/` | `Camera3D`, `CharacterBody3D` ([documented](https://docs.godotengine.org/en/stable/classes/class_camera3d.html)) |
| D — BO2 | `adapters/bo2-plutonium/` | Plutonium T6 GSC: `geteye`, `gettagorigin`, `level.players` |

## 4. Target selection

For each valid target:

1. Resolve aim point (`head` / `chest` / `custom`).
2. Optionally predict with `position + velocity × (distance / projectileVelocity)`.
3. Compute angular distance from camera forward to aim point: `θ = acos(forward · dir)`.
4. Reject if `θ > aimFov/2` or `distance > maxDistance`.
5. Pick the **smallest θ** (closest to crosshair, not nearest in world space).

Filters: `alive`, `teamCheck`, `visibilityCheck` (adapter must set `Target.visible` honestly).

## 5. Pitch / yaw calculations

Given direction **d** from camera to aim point (unit vector):

```
pitch = asin(-dy)
yaw   = atan2(dx, -dz)
```

(Y-up, forward ≈ −Z when yaw = pitch = 0 — matches the browser sandbox.)

Inverse (forward from angles):

```
forward.x =  cos(pitch) · sin(yaw)
forward.y = -sin(pitch)
forward.z = -cos(pitch) · cos(yaw)
```

## 6. FOV testing

Circular cone in **angular space**, not screen pixels:

```
insideFOV = angularDistance <= aimFov / 2
```

The debug overlay also draws a screen-space FOV circle using `fovRadiusPixels()` for visual confirmation.

## 7. Smoothing

Separate horizontal (yaw) and vertical (pitch) factors in `[0, 1]`:

```
newAngle = current + angleDelta(current, desired) × smoothing
```

`angleDelta` wraps at ±π so rotation always takes the shortest path.

**Target-lock persistence**: while the locked target stays eligible, keep it even if another target has a smaller angle. When the lock is lost, `targetSwitchDelay` must elapse before acquiring a new target.

## 8. Prediction

Linear lead:

```
travelTime = distance(camera, aimPoint) / projectileVelocity
predicted  = aimPoint + velocity × travelTime
```

Optional gravity module adds `0.5 × g × t²` to the Y component.

`projectileVelocity ≤ 0` is clamped to prevent division by zero.

## 9. World-to-screen projection

Core provides `worldToScreenNdc()` for tests. Adapters should use engine matrices:

- **Three.js**: `vector.project(camera)` → NDC → pixel coords
- **Godot 4**: `Camera3D.unproject_position()`
- **BO2 GSC**: ❌ not available — use waypoint HUD instead

## 10. Creating another legitimate adapter

1. Copy `IGameAdapter` from `packages/core/src/types.ts`.
2. Map native entities → `Target` (id, head/chest positions, velocity, alive, visible, team).
3. Map camera → `CameraState` (position, forward or yaw/pitch, fov).
4. Instantiate `AimAssistEngine` with your `AimConfig`.
5. Each tick: `engine.updateAimAssist(adapter, deltaTime)`.
6. Render debug overlay from `AimAssistResult.evaluations` (reason codes: `selected`, `outside_fov`, `dead`, `same_team`, `invisible`, …).

**Stop** if you need memory scanners, hooks, or injected DLLs — that is out of scope.

---

## Adapter A — Built-in simulator

```bash
npm run simulator
```

Features: moving/stationary dummies, lateral + approach + circle paths, ally team member, live config panel, full debug overlay, FOV circle, head/chest markers via `worldToScreen`.

Controls: click to capture mouse, WASD move, mouse look.

## Adapter B — Browser sandbox bridge

Mapping (do **not** rewrite the whole sandbox):

| Sandbox (`aim-assist-sandbox/js`) | Framework |
|-----------------------------------|-----------|
| `player.position` | `CameraState.position` |
| `forwardFromAngles(yaw, pitch)` | `CameraState.forward` |
| `player.yaw` / `player.pitch` | `CameraState.yaw` / `.pitch` |
| `camera.fov` | `CameraState.fov` |
| `target.mesh.position + headHeight` | `Target.headPosition` |
| `target.mesh.position + chestHeight` | `Target.chestPosition` |
| `target.velocity` | `Target.velocity` |
| `player.yaw/pitch` assignment | `applyCameraAngles()` |

See `packages/browser-bridge/src/threeSandboxAdapter.ts` and optional `aim-assist-sandbox/js/framework-bridge.js`.

Build first: `npm run build`, then load sandbox with framework bundle paths configured.

## Adapter C — Godot 4

Open `adapters/godot-4/` in Godot 4.2+. Scripts mirror core function names in GDScript. Uses only documented node APIs.

## Adapter D — BO2 Plutonium (GSC)

Copy `adapters/bo2-plutonium/scripts/mp/aim_framework_bo2.gsc` to:

`%localappdata%\Plutonium\storage\t6\scripts\mp\`

Private FFA match → spawn → verify HUD. **Debug only** — does not call `setplayerangles()`. Full instructions: `adapters/bo2-plutonium/README.md`.

---

## Configuration (`AimConfig`)

| Field | Description |
|-------|-------------|
| `enabled` | Master toggle |
| `aimFov` | Full cone width (degrees) |
| `maxDistance` | Max targeting range (world units) |
| `targetPoint` | `head` / `chest` / `custom` |
| `smoothing` | Fallback smoothing factor |
| `horizontalSmoothing` / `verticalSmoothing` | Per-axis smoothing |
| `predictionEnabled` | Lead target by velocity |
| `projectileVelocity` | m/s (or game units/s) for travel time |
| `gravityCompensation` | Optional drop correction |
| `targetSwitchDelay` | Seconds after lock lost |
| `visibilityCheck` | Require `Target.visible === true` |
| `teamCheck` | Skip `Target.team === localTeam` |
| `updateRate` | Max aim ticks per second |
| `debugOverlay` | Show debug UI |

## Automated tests

```bash
npm test
```

Covers: ahead / behind camera, FOV boundary, two-target angular pick, prediction, lateral speed, zero velocity, disappearing/dead/team-change targets, lock persistence, smoothing convergence, yaw wrap.

## License / ethics

For education and research on systems **you control**. Do not use against live multiplayer services without permission. Adapters D (BO2) is limited to Plutonium private/custom matches with GSC — not console, not official servers.
