import * as THREE from "three";
import {
  forwardFromAngles,
  anglesFromDirection,
  angleBetween,
  angleDelta,
  expSmoothAngle,
  getBoneWorldPosition,
  predictPosition,
  isWorldPointOnScreen,
} from "./math.js";

/**
 * Aim-assist pipeline (each frame):
 *
 * 1. Build camera forward vector from current yaw/pitch.
 * 2. Select best target inside FOV (unchanged detection logic).
 * 3. Re-read the CURRENT aim point on the selected target (no frozen coords).
 * 4. Desired yaw/pitch from camera → aim point.
 * 5. Snap OR exponential-smooth toward those angles (frame-rate independent).
 * 6. Return authoritative yaw/pitch for main.js to apply once.
 */

const _toTarget = new THREE.Vector3();
const _forward = new THREE.Vector3();
const _aimPoint = new THREE.Vector3();
const _angles = { yaw: 0, pitch: 0 };
const _postForward = new THREE.Vector3();

export class AimAssist {
  constructor() {
    this.enabled = true;
    /** Acquire cone width (degrees). Ignored when screenWideSelect is true. */
    this.fovDeg = 12;
    /**
     * When true, any target visible on screen (within camera FOV) can be acquired.
     * This matches "enemy anywhere on screen → track head".
     */
    this.screenWideSelect = true;
    /** Camera vertical FOV in degrees — synced from main.js each frame. */
    this.cameraVfov = 75;

    this.smoothing = 0.15;
    /** Used only when snapAimDebug is false. */
    this.responseSpeed = 35;

    this.targetBone = "head";
    this.maxRange = 100;
    this.predictionEnabled = true;
    this.projectileSpeed = 200;

    /** Snap crosshair to head every frame (default ON for this sandbox). */
    this.snapAimDebug = true;

    this.lockedTarget = null;
    /** Release lock only when target leaves the screen (1.0 = same as acquire). */
    this.releaseFovMultiplier = 1.0;

    this.debugForceFirstTarget = false;
    this.debugIgnoreRange = false;

    this.selectedTarget = null;
    this.evaluations = [];
    this.lastCameraDebug = null;
    this.tracking = null;
    this.debugInfo = "";
  }

  /** FOV degrees used for acquire + overlay drawing. */
  getAcquireFovDeg() {
    if (this.screenWideSelect) {
      return this.cameraVfov * 0.98;
    }
    return this.fovDeg;
  }

  getReleaseFovDeg() {
    return this.getAcquireFovDeg() * this.releaseFovMultiplier;
  }

  /**
   * @param {object} cameraState - { position, yaw, pitch }
   * @param {Array} targets
   * @param {number} dt - seconds since last frame (required for smooth mode)
   * @param {THREE.PerspectiveCamera} [renderCamera] - for screen-space visibility
   */
  update(cameraState, targets, dt = 1 / 60, renderCamera = null) {
    const { position, yaw, pitch } = cameraState;

    if (!this.enabled) {
      this.selectedTarget = null;
      this.lockedTarget = null;
      this.evaluations = [];
      this.tracking = null;
      this.debugInfo = "Aim assist disabled";
      return { yaw, pitch };
    }

    forwardFromAngles(yaw, pitch, _forward);

    const acquireHalfRad = (this.getAcquireFovDeg() * Math.PI) / 180 / 2;
    const releaseHalfRad = (this.getReleaseFovDeg() * Math.PI) / 180 / 2;
    const evaluations = [];
    let bestTarget = null;
    let bestAngle = Infinity;
    let nearest = null;

    // --- Detection (unchanged logic) ---
    for (const target of targets) {
      getBoneWorldPosition(target, this.targetBone, _aimPoint);

      if (this.predictionEnabled) {
        predictPosition(
          _aimPoint,
          target.velocity,
          position,
          this.projectileSpeed,
          _aimPoint
        );
      }

      const aimPoint = _aimPoint.clone();
      const distance = aimPoint.distanceTo(position);
      _toTarget.copy(aimPoint).sub(position);
      const dirLen = _toTarget.length();
      if (dirLen > 1e-8) _toTarget.multiplyScalar(1 / dirLen);
      const angle = angleBetween(_forward, _toTarget);
      const angleDeg = (angle * 180) / Math.PI;
      const dot = _forward.dot(_toTarget);
      const inRange = this.debugIgnoreRange || distance <= this.maxRange;
      const inFront = dot > 0;
      const onScreen =
        renderCamera != null
          ? isWorldPointOnScreen(aimPoint, renderCamera)
          : inFront && angle <= acquireHalfRad;
      const insideFov = this.screenWideSelect
        ? onScreen && inFront
        : inFront && angle <= acquireHalfRad;
      const passes = inRange && insideFov;

      const evaluation = {
        target,
        aimPoint,
        distance,
        angle,
        angleDeg,
        dot,
        direction: _toTarget.clone(),
        inRange,
        inFront,
        onScreen,
        insideFov,
        passes,
      };
      evaluations.push(evaluation);

      if (!nearest || angle < nearest.angle) nearest = evaluation;

      if (passes && angle < bestAngle) {
        bestAngle = angle;
        bestTarget = target;
      }
    }

    if (this.debugForceFirstTarget && targets.length > 0) {
      bestTarget = evaluations[0].target;
      bestAngle = evaluations[0].angle;
    }

    this.evaluations = evaluations;

    // --- Target lock ---
    let lockEval = null;

    if (this.screenWideSelect) {
      // Screen-wide: always track the on-screen target closest to crosshair.
      this.lockedTarget = bestTarget;
      lockEval = bestTarget
        ? (evaluations.find((e) => e.target === bestTarget) ?? null)
        : null;
    } else {
      if (this.lockedTarget) {
        lockEval =
          evaluations.find((e) => e.target === this.lockedTarget) ?? null;
        const stillLocked =
          lockEval &&
          lockEval.inRange &&
          lockEval.inFront !== false &&
          lockEval.angle <= releaseHalfRad;

        if (!stillLocked) {
          this.lockedTarget = null;
          lockEval = null;
        }
      }

      if (!this.lockedTarget && bestTarget) {
        this.lockedTarget = bestTarget;
        lockEval =
          evaluations.find((e) => e.target === bestTarget) ?? null;
      }
    }

    const trackTarget = this.lockedTarget;
    this.selectedTarget = trackTarget;

    this.lastCameraDebug = {
      position: position.clone(),
      forward: _forward.clone(),
      yaw,
      pitch,
      fovDeg: this.getAcquireFovDeg(),
      fovHalfDeg: (acquireHalfRad * 180) / Math.PI,
      releaseHalfDeg: (releaseHalfRad * 180) / Math.PI,
      screenWide: this.screenWideSelect,
    };

    if (!trackTarget) {
      this.tracking = null;
      this.debugInfo = this.buildDebugInfo(nearest, null, lockEval);
      return { yaw, pitch };
    }

    // --- Actuation: live aim point on LOCKED target every frame ---
    getBoneWorldPosition(trackTarget, this.targetBone, _aimPoint);
    if (this.predictionEnabled) {
      predictPosition(
        _aimPoint,
        trackTarget.velocity,
        position,
        this.projectileSpeed,
        _aimPoint
      );
    }
    const liveAimPoint = _aimPoint.clone();

    _toTarget.copy(liveAimPoint).sub(position).normalize();
    anglesFromDirection(_toTarget, _angles);
    const desiredYaw = _angles.yaw;
    const desiredPitch = _angles.pitch;

    const yawError = angleDelta(yaw, desiredYaw);
    const pitchError = angleDelta(pitch, desiredPitch);

    let newYaw;
    let newPitch;
    if (this.snapAimDebug) {
      // Zero-smoothing SNAP: exact look-at angles every frame.
      newYaw = desiredYaw;
      newPitch = desiredPitch;
    } else {
      // Frame-rate-independent exponential smoothing.
      newYaw = expSmoothAngle(yaw, desiredYaw, this.responseSpeed, dt);
      newPitch = expSmoothAngle(pitch, desiredPitch, this.responseSpeed, dt);
    }

    // Post-actuation residual: angle between NEW forward and target direction.
    forwardFromAngles(newYaw, newPitch, _postForward);
    const postError = angleBetween(_postForward, _toTarget);
    const preError = angleBetween(_forward, _toTarget);

    this.tracking = {
      targetId: trackTarget.id,
      aimPoint: liveAimPoint,
      desiredDirection: _toTarget.clone(),
      currentYaw: yaw,
      currentPitch: pitch,
      desiredYaw,
      desiredPitch,
      newYaw,
      newPitch,
      yawErrorDeg: (yawError * 180) / Math.PI,
      pitchErrorDeg: (pitchError * 180) / Math.PI,
      preErrorDeg: (preError * 180) / Math.PI,
      postErrorDeg: (postError * 180) / Math.PI,
      responseSpeed: this.responseSpeed,
      snap: this.snapAimDebug,
      tracking: true,
      locked: true,
      insideAcquireFov: this.screenWideSelect
        ? (lockEval?.onScreen ?? false)
        : (lockEval?.insideFov ?? false),
    };

    this.debugInfo = this.buildDebugInfo(nearest, trackTarget, lockEval);
    return { yaw: newYaw, pitch: newPitch };
  }

  buildDebugInfo(nearest, trackTarget, lockEval) {
    const t = this.tracking;
    const lines = [];

    if (trackTarget && t) {
      lines.push(`Target: ${t.targetId} (${this.screenWideSelect ? "TRACKING" : "LOCKED"} → ${this.targetBone})`);
      lines.push(
        this.screenWideSelect
          ? `Mode: screen-wide (camera FOV ${this.cameraVfov.toFixed(0)}°)`
          : `Mode: cone ${this.fovDeg.toFixed(1)}°`
      );
      lines.push(
        `On screen: ${t.insideAcquireFov ? "YES" : "NO"}`
      );
      lines.push(`Current error: ${t.preErrorDeg.toFixed(2)}°`);
      lines.push(`Yaw error: ${t.yawErrorDeg.toFixed(2)}°`);
      lines.push(`Pitch error: ${t.pitchErrorDeg.toFixed(2)}°`);
      lines.push(
        `Post-apply error: ${t.postErrorDeg.toFixed(3)}°`
      );
      lines.push(`Response speed: ${t.responseSpeed}`);
      lines.push(`Tracking: YES`);
      lines.push(`Snap test: ${t.snap ? "ON" : "OFF"}`);
    } else {
      lines.push("Tracking: NO");
      lines.push(`Snap test: ${this.snapAimDebug ? "ON" : "OFF"}`);
      if (nearest) {
        lines.push(
          `Nearest: ${nearest.target.id} ∠${nearest.angleDeg.toFixed(2)}° ` +
            (nearest.insideFov ? "IN FOV" : "OUTSIDE")
        );
      } else {
        lines.push("Nearest: none");
      }
    }

    return lines.join("\n");
  }

  logPipelineOnce() {
    console.group("[aim] tracking / selection");
    console.log("tracking", this.tracking);
    console.log("selected", this.selectedTarget?.id ?? null);
    console.log("evaluations", this.evaluations);
    console.groupEnd();
  }
}
