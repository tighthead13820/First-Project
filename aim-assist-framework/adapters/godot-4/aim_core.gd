class_name AimCore
extends RefCounted
## Game-independent aim maths (mirrors packages/core/src).

static func forward_from_angles(yaw: float, pitch: float) -> Vector3:
	var cp := cos(pitch)
	return Vector3(cp * sin(yaw), -sin(pitch), -cp * cos(yaw)).normalized()

static func calculate_aim_angles(from: Vector3, to: Vector3) -> Vector2:
	var d := (to - from).normalized()
	return Vector2(atan2(d.x, -d.z), asin(clampf(-d.y, -1.0, 1.0)))

static func angular_distance(a: Vector3, b: Vector3) -> float:
	return acos(clampf(a.normalized().dot(b.normalized()), -1.0, 1.0))

static func is_inside_fov(angle_rad: float, fov_deg: float) -> bool:
	return angle_rad <= deg_to_rad(fov_deg * 0.5)

static func predict_position(aim: Vector3, velocity: Vector3, cam: Vector3, speed: float) -> Vector3:
	var t := aim.distance_to(cam) / maxf(speed, 0.001)
	return aim + velocity * t

static func smooth_angles(current: Vector2, desired: Vector2, h: float, v: float) -> Vector2:
	return Vector2(
		_lerp_angle(current.x, desired.x, h),
		_lerp_angle(current.y, desired.y, v)
	)

static func _lerp_angle(from: float, to: float, w: float) -> float:
	var d := wrapf(to - from, -PI, PI)
	return from + d * clampf(w, 0.0, 1.0)

static func select_best_target(
	camera_pos: Vector3,
	camera_forward: Vector3,
	targets: Array,
	fov_deg: float,
	max_dist: float,
	use_team: bool,
	local_team: int
) -> Dictionary:
	var best: Dictionary = {}
	var best_angle := INF
	for t in targets:
		if not t.alive:
			continue
		if use_team and t.team == local_team:
			continue
		var aim: Vector3 = t.head if t.bone == "head" else t.chest
		var dist := camera_pos.distance_to(aim)
		if dist > max_dist:
			continue
		var dir := (aim - camera_pos).normalized()
		var ang := angular_distance(camera_forward, dir)
		if not is_inside_fov(ang, fov_deg):
			continue
		if ang < best_angle:
			best_angle = ang
			best = {"target": t, "angle": ang, "distance": dist, "aim": aim}
	return best
