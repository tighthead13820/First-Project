import {
  anglesFromDirection,
  calculateAimAngles,
  forwardFromAngles,
  smoothAimAngles,
} from "./angles.js";
import { selectBestTarget } from "./selection.js";
import type {
  AimAssistResult,
  AimConfig,
  AimAngles,
  IGameAdapter,
} from "./types.js";

interface EngineState {
  currentPitch: number;
  currentYaw: number;
  lockedTargetId: number | null;
  switchCooldown: number;
  pendingRetarget: boolean;
  accumulator: number;
}

/**
 * Game-independent aim assist engine.
 * Pulls normalized state from an adapter, runs selection + smoothing,
 * optionally writes angles back through the adapter.
 */
export class AimAssistEngine {
  private state: EngineState = {
    currentPitch: 0,
    currentYaw: 0,
    lockedTargetId: null,
    switchCooldown: 0,
    pendingRetarget: false,
    accumulator: 0,
  };

  constructor(public config: AimConfig) {}

  /** Reset lock / smoothing state (e.g. on respawn). */
  reset(): void {
    this.state.lockedTargetId = null;
    this.state.switchCooldown = 0;
    this.state.pendingRetarget = false;
    this.state.accumulator = 0;
  }

  /**
   * One simulation step. Respects updateRate throttling.
   * Returns debug-friendly result even when disabled.
   */
  updateAimAssist(adapter: IGameAdapter, deltaTime: number): AimAssistResult {
    const camera = adapter.getCameraState();
    this.state.currentPitch = camera.pitch;
    this.state.currentYaw = camera.yaw;

    const currentAngles: AimAngles = {
      pitch: this.state.currentPitch,
      yaw: this.state.currentYaw,
    };

    const minStep = 1 / Math.max(this.config.updateRate, 1);
    this.state.accumulator += deltaTime;
    if (this.state.accumulator < minStep) {
      return {
        selectedTarget: null,
        selectedEvaluation: null,
        evaluations: [],
        desiredAngles: null,
        smoothedAngles: null,
        currentAngles,
        deltaTime,
      };
    }
    this.state.accumulator = 0;
    this.state.switchCooldown = Math.max(
      0,
      this.state.switchCooldown - deltaTime
    );

    const targets = adapter.getTargets();
    const { best, evaluations } = selectBestTarget(
      adapter,
      camera,
      targets,
      this.config
    );

    if (!this.config.enabled || !best) {
      return {
        selectedTarget: best?.target ?? null,
        selectedEvaluation: best,
        evaluations,
        desiredAngles: null,
        smoothedAngles: null,
        currentAngles,
        deltaTime,
      };
    }

    let selected = best;

    // Target-lock persistence: keep the locked target while it stays eligible.
    // When it becomes ineligible, wait targetSwitchDelay before picking a new one.
    if (this.state.lockedTargetId !== null) {
      const lockedEval = evaluations.find(
        (e) =>
          e.target.id === this.state.lockedTargetId &&
          e.target.alive &&
          (!this.config.teamCheck || e.target.team !== this.config.localTeam) &&
          (!this.config.visibilityCheck || e.target.visible) &&
          e.insideFov &&
          e.distance <= this.config.maxDistance
      );

      if (lockedEval) {
        selected = lockedEval;
        selected.reason = "selected";
        this.state.pendingRetarget = false;
      } else {
        if (!this.state.pendingRetarget) {
          this.state.pendingRetarget = true;
          this.state.switchCooldown = this.config.targetSwitchDelay;
        }
        if (this.state.switchCooldown > 0) {
          return {
            selectedTarget: null,
            selectedEvaluation: null,
            evaluations,
            desiredAngles: null,
            smoothedAngles: null,
            currentAngles,
            deltaTime,
          };
        }
        this.state.pendingRetarget = false;
        this.state.lockedTargetId = best.target.id;
        selected = best;
      }
    } else {
      this.state.lockedTargetId = best.target.id;
    }

    const desired = calculateAimAngles(
      camera.position,
      selected.predictedAimPoint
    );

    const hSmooth =
      this.config.horizontalSmoothing > 0
        ? this.config.horizontalSmoothing
        : this.config.smoothing;
    const vSmooth =
      this.config.verticalSmoothing > 0
        ? this.config.verticalSmoothing
        : this.config.smoothing;

    const smoothed = smoothAimAngles(
      currentAngles,
      desired,
      hSmooth,
      vSmooth
    );

    this.state.currentPitch = smoothed.pitch;
    this.state.currentYaw = smoothed.yaw;

    adapter.applyCameraAngles?.(smoothed.pitch, smoothed.yaw);

    return {
      selectedTarget: selected.target,
      selectedEvaluation: selected,
      evaluations,
      desiredAngles: desired,
      smoothedAngles: smoothed,
      currentAngles: smoothed,
      deltaTime,
    };
  }

  /** Expose forward vector from current internal angles (debug). */
  getForwardVector(): ReturnType<typeof forwardFromAngles> {
    return forwardFromAngles(this.state.currentYaw, this.state.currentPitch);
  }

  /** Direction-based angles helper for tests. */
  static anglesToPoint(from: { x: number; y: number; z: number }, to: { x: number; y: number; z: number }) {
    return calculateAimAngles(from, to);
  }

  static directionToAngles(direction: { x: number; y: number; z: number }) {
    return anglesFromDirection(direction);
  }
}

export function updateAimAssist(
  engine: AimAssistEngine,
  adapter: IGameAdapter,
  deltaTime: number
): AimAssistResult {
  return engine.updateAimAssist(adapter, deltaTime);
}
