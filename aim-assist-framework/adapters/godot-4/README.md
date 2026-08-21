# Godot 4 Example Adapter (Adapter C)

This folder demonstrates **Adapter C**: integrating the aim-core *pipeline* with a game engine you control, using **documented Godot 4 APIs only**.

Godot cannot import the TypeScript `@aim-framework/core` package directly. The scripts here mirror the same maths and function names so you can compare implementations side-by-side with `packages/core/src/`.

## Files

| File | Role |
|------|------|
| `aim_core.gd` | Pure GDScript port of selection/FOV/angles (no engine coupling) |
| `aim_adapter.gd` | `IGameAdapter`-equivalent: reads `Camera3D`, `CharacterBody3D` targets |
| `debug_overlay.gd` | On-screen debug labels + FOV hint |
| `main.tscn` | Test scene (attach scripts in editor) |

## Documented APIs used

- `Camera3D.global_position`, `Camera3D.global_transform.basis.z` — camera state
- `Camera3D.unproject_position()` — world-to-screen ([Godot docs](https://docs.godotengine.org/en/stable/classes/class_camera3d.html#class-camera3d-method-unproject-position))
- `Node3D.global_position` — target positions
- `CharacterBody3D.velocity` — target velocity for prediction
- `Input` / `_process(delta)` — apply smoothed rotation to camera

## How to run

1. Install [Godot 4.2+](https://godotengine.org/download).
2. Open this folder as a project (`project.godot`).
3. Run `main.tscn`.
4. Use WASD + mouse to move; dummy targets are auto-spawned.

## Creating another engine adapter

1. Read normalized `Target` + `CameraState` from your engine's public scripting layer.
2. Implement `get_targets()`, `get_camera_state()`, optional `apply_camera_angles()`, and `world_to_screen()`.
3. Call the same pipeline: `select_best_target` → `calculate_aim_angles` → `smooth_aim_angles`.
4. If the engine does not expose bone positions, use collision shapes or attachment nodes instead of memory reads.

If an engine does not expose camera or entity positions through its plugin/script API, **stop** — do not inject or read process memory.
