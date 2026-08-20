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
    /** Half-angle of the aim-assist cone, in degrees. */
    this.fovDeg = 12;
    /** Interpolation factor per frame (0–1). Lower = smoother. */
    this.smoothing = 0.15;
    this.targetBone = "chest";
    this.maxRange = 50;
    this.predictionEnabled = false;
    this.projectileSpeed = 200;

    /** Currently locked target reference, or null. */
    this.selectedTarget = null;
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
      this.debugInfo = "Aim assist disabled";
      return { yaw, pitch };
    }

    forwardFromAngles(yaw, pitch, _forward);

    const fovHalfRad = (this.fovDeg * Math.PI) / 180 / 2;
    let bestTarget = null;
    let bestAngle = Infinity;
    let bestAimPoint = null;

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

      const distance = _aimPoint.distanceTo(position);
      if (distance > this.maxRange) continue;

      _toTarget.copy(_aimPoint).sub(position).normalize();
      const angle = angleBetween(_forward, _toTarget);

      if (angle <= fovHalfRad && angle < bestAngle) {
        bestAngle = angle;
        bestTarget = target;
        bestAimPoint = _aimPoint.clone();
      }
    }

    this.selectedTarget = bestTarget;

    if (!bestTarget) {
      this.debugInfo = "No target in FOV cone";
      return { yaw, pitch };
    }

    // Direction from camera to aim point → desired yaw/pitch
    _toTarget.copy(bestAimPoint).sub(position).normalize();
    anglesFromDirection(_toTarget, _angles);

    const newYaw = lerpAngle(yaw, _angles.yaw, this.smoothing);
    const newPitch = lerpAngle(pitch, _angles.pitch, this.smoothing);

    const dist = bestAimPoint.distanceTo(position);
    this.debugInfo = [
      `Target: ${bestTarget.id}`,
      `Bone: ${this.targetBone}`,
      `Distance: ${dist.toFixed(1)} m`,
      `Cone angle: ${((bestAngle * 180) / Math.PI).toFixed(2)}°`,
      `Desired yaw: ${(((_angles.yaw * 180) / Math.PI) % 360).toFixed(1)}°`,
      `Desired pitch: ${((_angles.pitch * 180) / Math.PI).toFixed(1)}°`,
      this.predictionEnabled ? "Prediction: ON" : "Prediction: OFF",
    ].join("\n");

    return { yaw: newYaw, pitch: newPitch };
  }
}
