extends Node3D
## Adapter C — obtains state via Godot 4 documented node APIs.

@export var camera: Camera3D
@export var aim_fov := 12.0
@export var max_distance := 100.0
@export var smoothing := 0.15
@export var enabled := true

var _targets: Array = []
var _yaw := 0.0
var _pitch := 0.0
var _selected: Dictionary = {}

func _ready() -> void:
	_spawn_dummies()

func _spawn_dummies() -> void:
	for i in 4:
		var body := CharacterBody3D.new()
		body.position = Vector3(i * 3 - 4, 1, -10 - i * 2)
		body.velocity = Vector3(randf_range(-2, 2), 0, randf_range(-1, 1))
		add_child(body)
		var mesh := MeshInstance3D.new()
		mesh.mesh = CapsuleMesh.new()
		(body.get_node_or_null(".") as Node)
		body.add_child(mesh)
		_targets.append({
			"id": i,
			"name": "Dummy-%d" % i,
			"node": body,
			"alive": true,
			"team": 1,
			"bone": "chest",
			"head": body.global_position + Vector3(0, 1.6, 0),
			"chest": body.global_position + Vector3(0, 1.2, 0),
		})

func _process(delta: float) -> void:
	for t in _targets:
		var body: CharacterBody3D = t.node
		body.velocity = body.velocity.normalized() * 2.0 if body.velocity.length() > 0.1 else Vector3(1, 0, 0)
		body.move_and_slide()
		t.head = body.global_position + Vector3(0, 1.6, 0)
		t.chest = body.global_position + Vector3(0, 1.2, 0)

	if not enabled or camera == null:
		return

	var forward := -camera.global_transform.basis.z
	_selected = AimCore.select_best_target(
		camera.global_position,
		forward,
		_targets,
		aim_fov,
		max_distance,
		true,
		0
	)

	if _selected.is_empty():
		return

	var desired := AimCore.calculate_aim_angles(camera.global_position, _selected.aim)
	var current := Vector2(_yaw, _pitch)
	var smoothed := AimCore.smooth_angles(current, desired, smoothing, smoothing)
	_yaw = smoothed.x
	_pitch = smoothed.y
	camera.rotation = Vector3(_pitch, _yaw, 0)

func get_debug_text() -> String:
	if _selected.is_empty():
		return "No target"
	return "Target: %s  d=%.1f  ang=%.1f°" % [
		_selected.target.name,
		_selected.distance,
		rad_to_deg(_selected.angle)
	]

func world_to_screen(world: Vector3) -> Vector2:
	return camera.unproject_position(world) if camera else Vector2.ZERO
