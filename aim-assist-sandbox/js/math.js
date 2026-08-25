import * as THREE from "three";

/**
 * Vector and angle utilities for first-person aim assist.
 *
 * Coordinate system (Three.js default):
 *   +X = right, +Y = up, -Z = forward (camera looks down -Z when yaw=pitch=0)
 *
 * Yaw rotates around Y (left/right). Pitch rotates around X (up/down).
 */

/** Reusable scratch vectors to avoid per-frame allocations. */
const _scratchA = new THREE.Vector3();
const _scratchB = new THREE.Vector3();
const _scratchC = new THREE.Vector3();

/**
 * Build a unit forward vector from yaw/pitch (radians).
 *
 * Spherical-to-Cartesian conversion:
 *   forward.x =  cos(pitch) * sin(yaw)
 *   forward.y = -sin(pitch)
 *   forward.z = -cos(pitch) * cos(yaw)
 *
 * Intuition: yaw spins in the XZ plane; pitch tilts the vector up/down.
 */
export function forwardFromAngles(yaw, pitch, out = new THREE.Vector3()) {
  const cosPitch = Math.cos(pitch);
  out.set(
    cosPitch * Math.sin(yaw),
    -Math.sin(pitch),
    -cosPitch * Math.cos(yaw)
  );
  return out.normalize();
}

/**
 * Extract yaw and pitch (radians) from a unit direction vector.
 *
 * Given direction d = (dx, dy, dz):
 *   pitch = asin(-dy)           // vertical angle from horizontal plane
 *   yaw   = atan2(dx, -dz)      // horizontal angle from forward (-Z)
 *
 * atan2 handles all quadrants correctly (unlike plain atan).
 */
export function anglesFromDirection(direction, out = { yaw: 0, pitch: 0 }) {
  const dx = direction.x;
  const dy = direction.y;
  const dz = direction.z;

  out.pitch = Math.asin(clamp(dy, -1, 1) * -1);
  out.yaw = Math.atan2(dx, -dz);
  return out;
}

/**
 * Angular distance (radians) between two unit vectors.
 *
 * Uses the dot product identity:
 *   cos(theta) = a · b   (when |a| = |b| = 1)
 *   theta = acos(clamp(a · b, -1, 1))
 *
 * This is the "cone angle" between look direction and target direction.
 */
export function angleBetween(a, b) {
  return Math.acos(clamp(a.dot(b), -1, 1));
}

/**
 * Shortest signed delta from `from` to `to`, wrapping at ±PI.
 * Essential for smooth yaw interpolation across the -PI/PI seam.
 */
export function angleDelta(from, to) {
  let delta = to - from;
  while (delta > Math.PI) delta -= 2 * Math.PI;
  while (delta < -Math.PI) delta += 2 * Math.PI;
  return delta;
}

/**
 * Frame-rate-independent exponential angle smoothing.
 *
 *   alpha = 1 - exp(-responseSpeed * dt)
 *   new   = current + shortestDelta * alpha
 *
 * responseSpeed is in "response units" per second (higher = snappier).
 * Do NOT use a fixed per-frame factor — that becomes tiny or huge with FPS.
 */
export function expSmoothAngle(current, target, responseSpeed, dt) {
  const alpha = 1 - Math.exp(-Math.max(responseSpeed, 0) * Math.max(dt, 0));
  return current + angleDelta(current, target) * alpha;
}

/**
 * Legacy per-frame lerp (frame-rate dependent). Kept for reference/tests only.
 * smoothing in (0, 1]: higher = faster snap, lower = smoother glide.
 */
export function lerpAngle(current, target, smoothing) {
  return current + angleDelta(current, target) * clamp(smoothing, 0, 1);
}

/**
 * World-space aim point on a target (head or chest).
 *
 * Bone heights (headHeight / chestHeight) are measured from the *feet*
 * (ground-relative, y = 0). The capsule mesh is centred at
 * mesh.position.y = feetY + meshCenterOffset (default 0.9), so we must
 * NOT add mesh.position.y + height — that double-counts the center offset
 * and places the aim point ~0.9 m too high.
 *
 * Correct: feetY = mesh.y - meshCenterOffset; aimY = feetY + boneHeight
 *        = mesh.y + (boneHeight - meshCenterOffset)
 * which matches the visual headMarker local offset.
 */
export function getBoneWorldPosition(target, bone, out = _scratchA) {
  const base = target.mesh.position;
  const height = bone === "head" ? target.headHeight : target.chestHeight;
  const centerOffset = target.meshCenterOffset ?? 0.9;
  return out.set(base.x, base.y + (height - centerOffset), base.z);
}

/**
 * Predict where a target will be when a projectile arrives.
 *
 * travelTime = distance(camera, target) / projectileSpeed
 * predicted  = currentPos + velocity * travelTime
 *
 * This is linear extrapolation (constant velocity). It ignores acceleration
 * and gravity — adequate for this educational sandbox.
 */
export function predictPosition(
  currentPos,
  velocity,
  cameraPos,
  projectileSpeed,
  out = _scratchB
) {
  const distance = currentPos.distanceTo(cameraPos);
  const travelTime = distance / Math.max(projectileSpeed, 0.001);
  return out.copy(currentPos).addScaledVector(velocity, travelTime);
}

/**
 * Convert an FOV half-angle (radians) to a screen-space circle radius in pixels.
 *
 * At the center of the screen, a cone of half-angle θ projects to a circle
 * whose radius r satisfies:
 *   tan(θ) = r / focalLength
 *   r = tan(θ) * (screenHeight / 2) / tan(vfov / 2)
 *
 * We use the camera vertical FOV to derive focal length in pixels.
 */
export function fovRadiusPixels(aimFovDeg, cameraVfovDeg, screenHeight) {
  const aimHalfRad = (aimFovDeg * Math.PI) / 180 / 2;
  const vfovHalfRad = (cameraVfovDeg * Math.PI) / 180 / 2;
  const focalLengthPx = screenHeight / 2 / Math.tan(vfovHalfRad);
  return Math.tan(aimHalfRad) * focalLengthPx;
}

/**
 * True when a world point projects inside the camera viewport (NDC bounds).
 * Uses the camera's current world matrix — call after camera transform is applied.
 */
export function isWorldPointOnScreen(worldPoint, camera, marginNdc = 0.02) {
  _scratchC.copy(worldPoint).project(camera);
  const x = _scratchC.x;
  const y = _scratchC.y;
  const z = _scratchC.z;
  const min = -1 + marginNdc;
  const max = 1 - marginNdc;
  return z > -1 && z < 1 && x >= min && x <= max && y >= min && y <= max;
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

export { _scratchC as scratchVector };
