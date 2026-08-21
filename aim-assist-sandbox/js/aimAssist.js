import * as THREE from "three";
import {
  forwardFromAngles,
  anglesFromDirection,
  angleBetween,
  lerpAngle,
  getBoneWorldPosition,
  predictPosition,
} from "./math.js";

/**
 * Aim-assist pipeline (each frame):
 *
 * 1. Build camera forward vector from current yaw/pitch.
 * 2. For each target within maxRange:
 *      a. Compute aim point (head/chest, optionally predicted).
 *      b. Build direction vector: aimPoint - cameraPos.
 *      c. Check cone: angle(forward, direction) <= fov/2.
 * 3. Among valid targets, pick the one with smallest angle to crosshair.
 * 4. Compute desired yaw/pitch toward that aim point.
 * 5. Smoothly interpolate current yaw/pitch toward desired values.
 */

const _toTarget = new THREE.Vector3();
const _forward = new THREE.Vector3();
const _aimPoint = new THREE.Vector3();
const _angles = { yaw: 0, pitch: 0 };

export class AimAssist {
  constructor() {
    this.enabled = true;
    /** Full cone width of the aim-assist FOV, in degrees. */
    this.fovDeg = 12;
    /** Interpolation factor per frame (0–1). Lower = smoother. */
    this.smoothing = 0.15;
    this.targetBone = "chest";
    this.maxRange = 50;
    this.predictionEnabled = false;
    this.projectileSpeed = 200;

    /**
     * When true, skip FOV / range filters and always lock the first target.
     * Used to verify HUD/marker wiring independently of selection maths.
     */
    this.debugForceFirstTarget = false;

    /** When true, ignore maxRange so only the angular FOV test remains. */
    this.debugIgnoreRange = false;

    /** Currently locked target reference, or null. */
    this.selectedTarget = null;
    /** Per-target evaluation snapshot for debug overlay / colour states. */
    this.evaluations = [];
    /** Camera/forward snapshot from last update (for debug lines / logs). */
    this.lastCameraDebug = null;
    /** Debug readout for the HUD. */
    this.debugInfo = "";
  }

  /**
   * Run one aim-assist tick.
   *
   * @param {object} cameraState - { position: Vector3, yaw: number, pitch: number }
   * @param {Array} targets - moving dummy targets
   * @returns {{ yaw: number, pitch: number }} updated camera angles
   */
  update(cameraState, targets) {
    const { position, yaw, pitch } = cameraState;

    if (!this.enabled) {
      this.selectedTarget = null;
      this.evaluations = [];
      this.debugInfo = "Aim assist disabled";
      return { yaw, pitch };
    }

    forwardFromAngles(yaw, pitch, _forward);

    // fovDeg is the FULL cone width; compare against half in radians.
    const fovHalfRad = (this.fovDeg * Math.PI) / 180 / 2;
    const evaluations = [];
    let bestTarget = null;
    let bestAngle = Infinity;
    let bestAimPoint = null;
    let nearest = null;

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

      if (!nearest || angle < nearest.angle) {
        nearest = evaluation;
      }

      if (passes && angle < bestAngle) {
        bestAngle = angle;
        bestTarget = target;
        bestAimPoint = aimPoint;
      }
    }

    // Temporary isolation mode: prove rendering works even if FOV maths fail.
    if (this.debugForceFirstTarget && targets.length > 0) {
      const forced = evaluations[0];
      bestTarget = forced.target;
      bestAimPoint = forced.aimPoint;
      bestAngle = forced.angle;
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

    this.debugInfo = this.buildDebugInfo(nearest, bestTarget, bestAngle, bestAimPoint);

    if (!bestTarget || !bestAimPoint) {
      return { yaw, pitch };
    }

    // Direction from camera to aim point → desired yaw/pitch
    _toTarget.copy(bestAimPoint).sub(position).normalize();
    anglesFromDirection(_toTarget, _angles);

    const newYaw = lerpAngle(yaw, _angles.yaw, this.smoothing);
    const newPitch = lerpAngle(pitch, _angles.pitch, this.smoothing);

    return { yaw: newYaw, pitch: newPitch };
  }

  buildDebugInfo(nearest, bestTarget, bestAngle, bestAimPoint) {
    const cam = this.lastCameraDebug;
    const lines = [];

    if (cam) {
      lines.push(
        `Cam: (${cam.position.x.toFixed(1)}, ${cam.position.y.toFixed(1)}, ${cam.position.z.toFixed(1)})`
      );
      lines.push(
        `Fwd: (${cam.forward.x.toFixed(2)}, ${cam.forward.y.toFixed(2)}, ${cam.forward.z.toFixed(2)})`
      );
      lines.push(
        `FOV: ${cam.fovDeg.toFixed(1)}° (half ${cam.fovHalfDeg.toFixed(2)}°)`
      );
    }

    if (nearest) {
      lines.push(
        `Nearest: ${nearest.target.id}  ∠${nearest.angleDeg.toFixed(2)}°  ` +
          `dot=${nearest.dot.toFixed(3)}  ` +
          (nearest.insideFov ? "IN FOV" : "OUTSIDE FOV")
      );
      lines.push(
        `  aim (${nearest.aimPoint.x.toFixed(1)}, ${nearest.aimPoint.y.toFixed(1)}, ${nearest.aimPoint.z.toFixed(1)})  ` +
          `d=${nearest.distance.toFixed(1)}m`
      );
    } else {
      lines.push("Nearest: none");
    }

    if (bestTarget && bestAimPoint) {
      lines.push(
        `Selected: ${bestTarget.id}  ∠${((bestAngle * 180) / Math.PI).toFixed(2)}°  bone=${this.targetBone}`
      );
      if (this.debugForceFirstTarget) lines.push("Force-first DEBUG ON");
    } else {
      lines.push("Selected: none");
    }

    return lines.join("\n");
  }

  /** One-shot console dump of the full selection pipeline. */
  logPipelineOnce() {
    const cam = this.lastCameraDebug;
    if (!cam) {
      console.warn("[aim] no camera debug yet");
      return;
    }
    console.group("[aim] selection pipeline");
    console.log("camera position", cam.position);
    console.log("camera forward", cam.forward);
    console.log("yaw/pitch (rad)", cam.yaw, cam.pitch);
    console.log("FOV deg / half", cam.fovDeg, cam.fovHalfDeg);
    for (const ev of this.evaluations) {
      console.log(ev.target.id, {
        aimPoint: ev.aimPoint,
        direction: ev.direction,
        dot: ev.dot,
        angleDeg: ev.angleDeg,
        inRange: ev.inRange,
        insideFov: ev.insideFov,
        passes: ev.passes,
      });
    }
    console.log("selected", this.selectedTarget?.id ?? null);
    console.groupEnd();
  }
}
