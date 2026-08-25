import { clamp, dot, normalize, sub } from "./vec.js";
import type { AimAngles, Vec3 } from "./types.js";

const DEG = Math.PI / 180;
const RAD = 180 / Math.PI;

/**
 * Build a unit forward vector from yaw/pitch (radians).
 *
 * Three.js / Y-up convention (matches browser sandbox):
 *   forward.x =  cos(pitch) * sin(yaw)
 *   forward.y = -sin(pitch)
 *   forward.z = -cos(pitch) * cos(yaw)
 */
export function forwardFromAngles(yaw: number, pitch: number): Vec3 {
  const cosPitch = Math.cos(pitch);
  return normalize({
    x: cosPitch * Math.sin(yaw),
    y: -Math.sin(pitch),
    z: -cosPitch * Math.cos(yaw),
  });
}

/**
 * Extract yaw/pitch (radians) from a unit direction.
 *   pitch = asin(-dy)
 *   yaw   = atan2(dx, -dz)
 */
export function anglesFromDirection(direction: Vec3): AimAngles {
  const d = normalize(direction);
  return {
    pitch: Math.asin(clamp(-d.y, -1, 1)),
    yaw: Math.atan2(d.x, -d.z),
  };
}

/** Calculate pitch/yaw from camera position to a world aim point. */
export function calculateAimAngles(from: Vec3, to: Vec3): AimAngles {
  return anglesFromDirection(sub(to, from));
}

/**
 * Angular distance between two unit vectors (radians).
 * cos(θ) = a · b  →  θ = acos(clamp(a·b, -1, 1))
 */
export function calculateAngularDistance(a: Vec3, b: Vec3): number {
  return Math.acos(clamp(dot(normalize(a), normalize(b)), -1, 1));
}

/** Shortest signed delta between two angles (radians), wrapping at ±π. */
export function angleDelta(from: number, to: number): number {
  let delta = to - from;
  while (delta > Math.PI) delta -= 2 * Math.PI;
  while (delta < -Math.PI) delta += 2 * Math.PI;
  return delta;
}

/** Smoothly interpolate current angle toward target along shortest path. */
export function lerpAngle(current: number, target: number, factor: number): number {
  return current + angleDelta(current, target) * clamp(factor, 0, 1);
}

export function degreesToRadians(deg: number): number {
  return deg * DEG;
}

export function radiansToDegrees(rad: number): number {
  return rad * RAD;
}

export function smoothAimAngles(
  current: AimAngles,
  desired: AimAngles,
  horizontalFactor: number,
  verticalFactor: number
): AimAngles {
  return {
    yaw: lerpAngle(current.yaw, desired.yaw, horizontalFactor),
    pitch: lerpAngle(current.pitch, desired.pitch, verticalFactor),
  };
}
