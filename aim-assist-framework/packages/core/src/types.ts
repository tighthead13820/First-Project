/**
 * Game-independent types for the aim-assist research framework.
 * Adapters normalize engine-specific state into these structures.
 */

export interface Vec2 {
  x: number;
  y: number;
}

export interface Vec3 {
  x: number;
  y: number;
  z: number;
}

/** Which bone/point on a target to aim at. */
export type TargetPoint = "head" | "chest" | "custom";

/** Normalized target supplied by any game adapter. */
export interface Target {
  id: number;
  name?: string;
  headPosition: Vec3;
  chestPosition: Vec3;
  /** Used when targetPoint === "custom". */
  customPosition?: Vec3;
  velocity: Vec3;
  alive: boolean;
  visible: boolean;
  team: number;
}

/** Normalized camera / view state. */
export interface CameraState {
  position: Vec3;
  forward: Vec3;
  pitch: number;
  yaw: number;
  /** Vertical field of view in degrees (for world-to-screen). */
  fov: number;
}

export interface AimConfig {
  enabled: boolean;
  aimFov: number;
  maxDistance: number;
  targetPoint: TargetPoint;
  /** Legacy combined smoothing (0–1). Used when axis-specific values are unset. */
  smoothing: number;
  horizontalSmoothing: number;
  verticalSmoothing: number;
  predictionEnabled: boolean;
  projectileVelocity: number;
  gravityCompensation: boolean;
  /** Gravity magnitude (units/s²) when gravityCompensation is on. */
  gravity: number;
  targetSwitchDelay: number;
  visibilityCheck: boolean;
  teamCheck: boolean;
  /** Local player's team id for teamCheck. */
  localTeam: number;
  updateRate: number;
  debugOverlay: boolean;
}

export const DEFAULT_AIM_CONFIG: AimConfig = {
  enabled: true,
  aimFov: 12,
  maxDistance: 100,
  targetPoint: "chest",
  smoothing: 0.15,
  horizontalSmoothing: 0.15,
  verticalSmoothing: 0.15,
  predictionEnabled: false,
  projectileVelocity: 200,
  gravityCompensation: false,
  gravity: 9.81,
  targetSwitchDelay: 0.25,
  visibilityCheck: false,
  teamCheck: true,
  localTeam: 0,
  updateRate: 60,
  debugOverlay: true,
};

/** Why a target was rejected or how it was classified. */
export type TargetRejectReason =
  | "valid"
  | "selected"
  | "dead"
  | "same_team"
  | "invisible"
  | "outside_fov"
  | "out_of_range"
  | "not_best_angle";

export interface TargetEvaluation {
  target: Target;
  aimPoint: Vec3;
  predictedAimPoint: Vec3;
  distance: number;
  angularDistance: number;
  insideFov: boolean;
  reason: TargetRejectReason;
  screenHead: Vec2 | null;
  screenChest: Vec2 | null;
  screenAim: Vec2 | null;
}

export interface AimAngles {
  pitch: number;
  yaw: number;
}

export interface AimAssistResult {
  selectedTarget: Target | null;
  selectedEvaluation: TargetEvaluation | null;
  evaluations: TargetEvaluation[];
  desiredAngles: AimAngles | null;
  smoothedAngles: AimAngles | null;
  currentAngles: AimAngles;
  deltaTime: number;
}

/**
 * Adapter interface — each supported environment implements this.
 * C++ equivalent:
 *   class IGameAdapter {
 *     virtual CameraState GetCameraState() = 0;
 *     virtual std::vector<Target> GetTargets() = 0;
 *     virtual void ApplyCameraAngles(float pitch, float yaw) = 0;
 *     virtual std::optional<Vec2> WorldToScreen(Vec3 position) = 0;
 *   };
 */
export interface IGameAdapter {
  getCameraState(): CameraState;
  getTargets(): Target[];
  /** Optional: apply smoothed aim angles back to the environment. */
  applyCameraAngles?(pitch: number, yaw: number): void;
  /** Project world position to normalized screen [0,1] or pixel coords per adapter. */
  worldToScreen(position: Vec3): Vec2 | null;
}
