import { calculateAngularDistance, degreesToRadians } from "./angles.js";
import type { Vec3 } from "./types.js";

/**
 * Circular FOV test: is angular distance within half the configured FOV?
 * aimFov is the full cone width in degrees (same as sandbox slider).
 */
export function isInsideAimFov(
  angularDistanceRad: number,
  aimFovDeg: number
): boolean {
  const half = degreesToRadians(aimFovDeg * 0.5);
  return angularDistanceRad <= half;
}

/** Angular distance from camera forward to a world aim point. */
export function getAngularDistanceToPoint(
  cameraForward: Vec3,
  cameraPosition: Vec3,
  aimPoint: Vec3
): number {
  const toTarget = {
    x: aimPoint.x - cameraPosition.x,
    y: aimPoint.y - cameraPosition.y,
    z: aimPoint.z - cameraPosition.z,
  };
  const len = Math.hypot(toTarget.x, toTarget.y, toTarget.z);
  if (len < 1e-9) return 0;
  toTarget.x /= len;
  toTarget.y /= len;
  toTarget.z /= len;
  return calculateAngularDistance(cameraForward, toTarget);
}

/**
 * Project a world point to normalized device coordinates (NDC) in [-1, 1].
 * Pure math version for tests; adapters may use engine matrices instead.
 *
 * Assumes Y-up, camera at `eye` looking along `forward`, with `up` = (0,1,0).
 */
export function worldToScreenNdc(
  world: Vec3,
  eye: Vec3,
  forward: Vec3,
  fovDeg: number,
  aspect = 16 / 9
): { ndc: { x: number; y: number }; behind: boolean } {
  const up = { x: 0, y: 1, z: 0 };
  const f = normalizeLike(forward);
  let r = cross(f, up);
  if (Math.hypot(r.x, r.y, r.z) < 1e-6) r = { x: 1, y: 0, z: 0 };
  r = normalizeLike(r);
  const u = cross(r, f);

  const rel = { x: world.x - eye.x, y: world.y - eye.y, z: world.z - eye.z };
  const cx = dotLike(rel, r);
  const cy = dotLike(rel, u);
  const cz = dotLike(rel, f);

  if (cz <= 1e-6) {
    return { ndc: { x: 0, y: 0 }, behind: true };
  }

  const tanHalf = Math.tan((fovDeg * Math.PI) / 360);
  const ndcX = (cx / cz) / (tanHalf * aspect);
  const ndcY = (cy / cz) / tanHalf;
  return { ndc: { x: ndcX, y: ndcY }, behind: false };
}

function cross(a: Vec3, b: Vec3): Vec3 {
  return {
    x: a.y * b.z - a.z * b.y,
    y: a.z * b.x - a.x * b.z,
    z: a.x * b.y - a.y * b.x,
  };
}

function dotLike(a: Vec3, b: Vec3): number {
  return a.x * b.x + a.y * b.y + a.z * b.z;
}

function normalizeLike(v: Vec3): Vec3 {
  const len = Math.hypot(v.x, v.y, v.z) || 1;
  return { x: v.x / len, y: v.y / len, z: v.z / len };
}

/** FOV circle radius in pixels (matches browser sandbox ui.js). */
export function fovRadiusPixels(
  aimFovDeg: number,
  cameraVfovDeg: number,
  screenHeight: number
): number {
  const aimHalfRad = (aimFovDeg * Math.PI) / 180 / 2;
  const vfovHalfRad = (cameraVfovDeg * Math.PI) / 180 / 2;
  const focalLengthPx = screenHeight / 2 / Math.tan(vfovHalfRad);
  return Math.tan(aimHalfRad) * focalLengthPx;
}
