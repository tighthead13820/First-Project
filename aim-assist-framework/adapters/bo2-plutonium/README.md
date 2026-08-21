# Adapter D — Plutonium T6 / Black Ops II (GSC)

**Legitimate integration only.** This adapter runs inside **Plutonium T6's supported GSC scripting layer** for private/custom matches. It does **not** inject into the BO2 process, read/write arbitrary memory, hook DirectX, or bypass anti-cheat.

The TypeScript `@aim-framework/core` package cannot execute inside the BO2 client. This GSC file is a **parallel implementation** of the same function names and pipeline so you can validate maths in-game and compare against unit tests.

## Pipeline (matches Aim Core)

```
GetViewDirection() → GetAimPoint() → GetAngleToTarget() → IsInsideAimFOV()
  → SelectBestTarget() → PredictTargetPosition() → CalculateAimAngles()
  → SmoothAimAngles() → UpdateAimAssist()
```

This debug stage calls **`SmoothAimAngles` for HUD display only** — it does **not** call `setplayerangles()` (that would be aim automation, not debug research).

## Install

Copy:

```
adapters/bo2-plutonium/scripts/mp/aim_framework_bo2.gsc
```

to:

```
%localappdata%\Plutonium\storage\t6\scripts\mp\aim_framework_bo2.gsc
```

Start Plutonium T6 → Private Match (FFA recommended) → spawn → `map_restart` if needed.

## Console dvars (live config)

| Dvar | Default | Maps to AimConfig |
|------|---------|-------------------|
| `aim_enabled` | 1 | enabled |
| `aim_fov` | 12 | aimFov |
| `aim_range` | 4000 | maxDistance (T6 units) |
| `aim_bone` | head | targetPoint |
| `aim_h_smooth` | 0.15 | horizontalSmoothing |
| `aim_v_smooth` | 0.15 | verticalSmoothing |
| `aim_predict` | 0 | predictionEnabled |
| `aim_bullet_speed` | 200 | projectileVelocity |
| `aim_team_check` | 1 | teamCheck |
| `aim_vis_check` | 0 | visibilityCheck |
| `aim_debug` | 1 | debugOverlay |

Toggle debug HUD: Action Slot 4 (`+actionslot 4`) or `aim_debug 0/1`.

## Mapping: GSC ↔ TypeScript core

| GSC | TypeScript |
|-----|------------|
| `GetViewOrigin()` → `geteye()` | `CameraState.position` |
| `GetViewDirection()` → `anglestoforward(getplayerangles())` | `CameraState.forward` |
| `GetAimPoint()` → `gettagorigin("j_head"/"j_spine4")` | `getAimPoint()` |
| `GetAngleToTarget()` → `acos(vectordot(...))` **degrees** | `calculateAngularDistance()` **radians** |
| `IsInsideAimFOV()` | `isInsideAimFov()` |
| `SelectBestTarget()` | `selectBestTarget()` |
| `PredictTargetPosition()` | `predictTargetPosition()` |
| `level.players` | `adapter.getTargets()` |

## What you should see

- Left HUD: selected name, distance, angle, desired vs current pitch/yaw, prediction flag
- Green waypoint on selected player's head/chest
- `Valid players: N` count

## Limitations (cannot implement via GSC)

| Feature | Status |
|---------|--------|
| 2D screen boxes | ❌ No WorldToScreen in GSC — waypoint used instead |
| Line-of-sight visibility | ⚠️ Optional `bullettrace` stub; off by default |
| Apply aim to camera | ❌ Intentionally omitted in debug stage (`setplayerangles` exists but is not called) |
| PS5 / official BO2 | ❌ Plutonium PC only |

See also: `bo2-plutonium-target-tracker/` (earlier minimal debug script).
