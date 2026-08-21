import { add, distance, scale } from "./vec.js";
import type { Target, TargetPoint, Vec3 } from "./types.js";

/** Resolve which world point to aim at on a target. */
export function getAimPoint(target: Target, point: TargetPoint): Vec3 {
  switch (point) {
    case "head":
      return { ...target.headPosition };
    case "chest":
      return { ...target.chestPosition };
    case "custom":
      return target.customPosition
        ? { ...target.customPosition }
        : { ...target.chestPosition };
  }
}

/**
 * Linear movement prediction:
 *   travelTime = distance(camera, aimPoint) / projectileVelocity
 *   predicted  = aimPoint + velocity * travelTime
 */
export function predictTargetPosition(
  aimPoint: Vec3,
  velocity: Vec3,
  cameraPosition: Vec3,
  projectileVelocity: number
): Vec3 {
  const safeVelocity = Math.max(projectileVelocity, 1e-6);
  const travelTime = distance(aimPoint, cameraPosition) / safeVelocity;
  return add(aimPoint, scale(velocity, travelTime));
}

/**
 * Optional gravity compensation (drop correction along -Y).
 * Solves a simplified ballistic drop: offset.y += 0.5 * g * t²
 */
export function applyGravityCompensation(
  predicted: Vec3,
  cameraPosition: Vec3,
  projectileVelocity: number,
  gravity: number
): Vec3 {
  const safeVelocity = Math.max(projectileVelocity, 1e-6);
  const travelTime = distance(predicted, cameraPosition) / safeVelocity;
  return {
    x: predicted.x,
    y: predicted.y + 0.5 * gravity * travelTime * travelTime,
    z: predicted.z,
  };
}

export function buildPredictedAimPoint(
  target: Target,
  point: TargetPoint,
  cameraPosition: Vec3,
  projectileVelocity: number,
  predictionEnabled: boolean,
  gravityCompensation: boolean,
  gravity: number
): { raw: Vec3; predicted: Vec3 } {
  const raw = getAimPoint(target, point);
  if (!predictionEnabled) {
    return { raw, predicted: raw };
  }
  let predicted = predictTargetPosition(
    raw,
    target.velocity,
    cameraPosition,
    projectileVelocity
  );
  if (gravityCompensation) {
    predicted = applyGravityCompensation(
      predicted,
      cameraPosition,
      projectileVelocity,
      gravity
    );
  }
  return { raw, predicted };
}
