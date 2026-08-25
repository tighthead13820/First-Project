import { getAngularDistanceToPoint, isInsideAimFov } from "./fov.js";
import { buildPredictedAimPoint } from "./prediction.js";
import { distance } from "./vec.js";
import type {
  AimConfig,
  CameraState,
  IGameAdapter,
  Target,
  TargetEvaluation,
  TargetRejectReason,
} from "./types.js";

export interface SelectBestTargetResult {
  best: TargetEvaluation | null;
  evaluations: TargetEvaluation[];
}

function classifyReason(
  target: Target,
  insideFov: boolean,
  inRange: boolean,
  config: AimConfig,
  isBest: boolean
): TargetRejectReason {
  if (!target.alive) return "dead";
  if (config.teamCheck && target.team === config.localTeam) return "same_team";
  if (config.visibilityCheck && !target.visible) return "invisible";
  if (!inRange) return "out_of_range";
  if (!insideFov) return "outside_fov";
  if (isBest) return "selected";
  return "not_best_angle";
}

/**
 * Evaluate every target and select the one with smallest angular distance
 * to the crosshair (inside FOV cone and within max distance).
 */
export function selectBestTarget(
  adapter: IGameAdapter,
  camera: CameraState,
  targets: Target[],
  config: AimConfig
): SelectBestTargetResult {
  const evaluations: TargetEvaluation[] = [];
  let best: TargetEvaluation | null = null;
  let bestAngle = Infinity;

  for (const target of targets) {
    const { raw, predicted } = buildPredictedAimPoint(
      target,
      config.targetPoint,
      camera.position,
      config.projectileVelocity,
      config.predictionEnabled,
      config.gravityCompensation,
      config.gravity
    );

    const dist = distance(camera.position, predicted);
    const angular = getAngularDistanceToPoint(
      camera.forward,
      camera.position,
      predicted
    );
    const insideFov = isInsideAimFov(angular, config.aimFov);
    const inRange = dist <= config.maxDistance;

    const eligible =
      target.alive &&
      (!config.teamCheck || target.team !== config.localTeam) &&
      (!config.visibilityCheck || target.visible) &&
      insideFov &&
      inRange;

    const evaluation: TargetEvaluation = {
      target,
      aimPoint: raw,
      predictedAimPoint: predicted,
      distance: dist,
      angularDistance: angular,
      insideFov,
      reason: "valid",
      screenHead: adapter.worldToScreen(target.headPosition),
      screenChest: adapter.worldToScreen(target.chestPosition),
      screenAim: adapter.worldToScreen(predicted),
    };

    if (eligible && angular < bestAngle) {
      if (best) best.reason = "not_best_angle";
      bestAngle = angular;
      best = evaluation;
      evaluation.reason = "selected";
    } else {
      evaluation.reason = classifyReason(
        target,
        insideFov,
        inRange,
        config,
        false
      );
    }

    evaluations.push(evaluation);
  }

  return { best, evaluations };
}
