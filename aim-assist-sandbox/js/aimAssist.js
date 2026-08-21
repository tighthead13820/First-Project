import * as THREE from "three";
import {
  forwardFromAngles,
  anglesFromDirection,
  angleBetween,
  angleDelta,
  expSmoothAngle,
  getBoneWorldPosition,
  predictPosition,
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
    /** Full cone width of the aim-assist FOV, in degrees. */
    this.fovDeg = 12;
    /**
     * @deprecated Prefer responseSpeed. Kept wired for the UI slider as a
     * coarse fallback mapper; actuation uses responseSpeed + dt.
     */
    this.smoothing = 0.15;
    /**
     * Exponential response speed (1/s). Typical useful range: 1–40.
     *   1–3 slow · 5–10 gentle · 12–20 responsive · 25–40 very fast
     */
    this.responseSpeed = 14;
    this.targetBone = "chest";
    this.maxRange = 50;
    this.predictionEnabled = false;
    this.projectileSpeed = 200;

    /** Bypass smoothing — apply exact desired yaw/pitch every frame. */
    this.snapAimDebug = false;

    this.debugForceFirstTarget = false;
    this.debugIgnoreRange = false;

    this.selectedTarget = null;
    this.evaluations = [];
    this.lastCameraDebug = null;
    /** Tracking diagnostics for the HUD. */
    this.tracking = null;
    this.debugInfo = "";
  }

  /**
   * @param {object} cameraState - { position, yaw, pitch }
   * @param {Array} targets
   * @param {number} dt - seconds since last frame (required for smooth mode)
   */
  update(cameraState, targets, dt = 1 / 60) {
    const { position, yaw, pitch } = cameraState;

    if (!this.enabled) {
      this.selectedTarget = null;
      this.evaluations = [];
      this.tracking = null;
      this.debugInfo = "Aim assist disabled";
      return { yaw, pitch };
    }

    forwardFromAngles(yaw, pitch, _forward);

    const fovHalfRad = (this.fovDeg * Math.PI) / 180 / 2;
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
      const insideFov = angle <= fovHalfRad;
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
    this.selectedTarget = bestTarget;
    this.lastCameraDebug = {
      position: position.clone(),
      forward: _forward.clone(),
      yaw,
      pitch,
      fovDeg: this.fovDeg,
      fovHalfDeg: (fovHalfRad * 180) / Math.PI,
    };

    if (!bestTarget) {
      this.tracking = null;
      this.debugInfo = this.buildDebugInfo(nearest, null);
      return { yaw, pitch };
    }

    // --- Actuation: ALWAYS re-read the live aim point (never freeze coords) ---
    getBoneWorldPosition(bestTarget, this.targetBone, _aimPoint);
    if (this.predictionEnabled) {
      predictPosition(
        _aimPoint,
        bestTarget.velocity,
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
      targetId: bestTarget.id,
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
    };

    this.debugInfo = this.buildDebugInfo(nearest, bestTarget);
    return { yaw: newYaw, pitch: newPitch };
  }

  buildDebugInfo(nearest, bestTarget) {
    const t = this.tracking;
    const lines = [];

    if (bestTarget && t) {
      lines.push(`Target: ${t.targetId}`);
      lines.push(`Current error: ${t.preErrorDeg.toFixed(2)}°`);
      lines.push(`Yaw error: ${t.yawErrorDeg.toFixed(2)}°`);
      lines.push(`Pitch error: ${t.pitchErrorDeg.toFixed(2)}°`);
      lines.push(
        `Desired yaw: ${((t.desiredYaw * 180) / Math.PI).toFixed(2)}°`
      );
      lines.push(
        `Actual yaw: ${((t.currentYaw * 180) / Math.PI).toFixed(2)}°`
      );
      lines.push(
        `Desired pitch: ${((t.desiredPitch * 180) / Math.PI).toFixed(2)}°`
      );
      lines.push(
        `Actual pitch: ${((t.currentPitch * 180) / Math.PI).toFixed(2)}°`
      );
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
