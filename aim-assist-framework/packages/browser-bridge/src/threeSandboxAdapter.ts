/**
 * Adapter B — connects @aim-framework/core to the existing Three.js sandbox
 * without rewriting aim-assist-sandbox/js/main.js.
 *
 * Value mapping (sandbox → framework):
 * | Sandbox                          | Framework field              |
 * |----------------------------------|------------------------------|
 * | player.position                  | CameraState.position         |
 * | forwardFromAngles(yaw, pitch)    | CameraState.forward          |
 * | player.yaw / player.pitch        | CameraState.yaw / pitch      |
 * | camera.fov                       | CameraState.fov              |
 * | target.mesh.position + headHeight| Target.headPosition          |
 * | target.mesh.position + chestHeight| Target.chestPosition        |
 * | target.velocity                  | Target.velocity              |
 * | target mesh alive (always true)  | Target.alive                 |
 * | true (no LOS yet)                | Target.visible               |
 * | 1 (all enemies in sandbox)       | Target.team                  |
 * | apply via player.yaw/pitch       | applyCameraAngles            |
 * | THREE.Vector3.project(camera)    | worldToScreen                |
 */

import {
  AimAssistEngine,
  forwardFromAngles,
  type AimConfig,
  type CameraState,
  type IGameAdapter,
  type Target,
  type Vec2,
  type Vec3,
} from "@aim-framework/core";

/** Minimal surface the sandbox exposes — matches aim-assist-sandbox/js/*.js */
export interface SandboxPlayer {
  position: { x: number; y: number; z: number };
  yaw: number;
  pitch: number;
}

export interface SandboxDummyTarget {
  id: string;
  mesh: { position: { x: number; y: number; z: number } };
  velocity: { x: number; y: number; z: number };
  headHeight: number;
  chestHeight: number;
}

export interface SandboxThreeCamera {
  fov: number;
  /** Must implement project(vec3) like THREE.PerspectiveCamera */
  project(v: { x: number; y: number; z: number }): { x: number; y: number; z: number };
}

export class ThreeSandboxAdapter implements IGameAdapter {
  private numericIds = new Map<string, number>();
  private nextId = 1;

  constructor(
    private getPlayer: () => SandboxPlayer,
    private getSandboxTargets: () => SandboxDummyTarget[],
    private camera: SandboxThreeCamera,
    private viewport: () => { width: number; height: number },
    private localTeam = 0
  ) {}

  getCameraState(): CameraState {
    const p = this.getPlayer();
    return {
      position: { x: p.position.x, y: p.position.y, z: p.position.z },
      forward: forwardFromAngles(p.yaw, p.pitch),
      pitch: p.pitch,
      yaw: p.yaw,
      fov: this.camera.fov,
    };
  }

  getTargets(): Target[] {
    return this.getSandboxTargets().map((t) => this.toTarget(t));
  }

  applyCameraAngles(pitch: number, yaw: number): void {
    const p = this.getPlayer();
    p.pitch = pitch;
    p.yaw = yaw;
  }

  worldToScreen(position: Vec3): Vec2 | null {
    const v = { ...position };
    this.camera.project(v);
    if (v.z > 1) return null;
    const { width, height } = this.viewport();
    return {
      x: (v.x * 0.5 + 0.5) * width,
      y: (-v.y * 0.5 + 0.5) * height,
    };
  }

  private toTarget(t: SandboxDummyTarget): Target {
    if (!this.numericIds.has(t.id)) {
      this.numericIds.set(t.id, this.nextId++);
    }
    const base = t.mesh.position;
    return {
      id: this.numericIds.get(t.id)!,
      name: t.id,
      headPosition: { x: base.x, y: base.y + t.headHeight - 0.9, z: base.z },
      chestPosition: { x: base.x, y: base.y + t.chestHeight - 0.9, z: base.z },
      velocity: { x: t.velocity.x, y: t.velocity.y, z: t.velocity.z },
      alive: true,
      visible: true,
      team: 1,
    };
  }
}

export { AimAssistEngine, type AimConfig };
