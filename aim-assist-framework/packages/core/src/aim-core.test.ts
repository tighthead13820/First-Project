import { describe, it, expect, beforeEach } from "vitest";
import {
  AimAssistEngine,
  DEFAULT_AIM_CONFIG,
  angleDelta,
  calculateAimAngles,
  calculateAngularDistance,
  forwardFromAngles,
  getAimPoint,
  isInsideAimFov,
  lerpAngle,
  predictTargetPosition,
  selectBestTarget,
  smoothAimAngles,
  vec3,
  type AimConfig,
  type CameraState,
  type IGameAdapter,
  type Target,
} from "./index.js";

function makeTarget(overrides: Partial<Target> & { id: number }): Target {
  const base = vec3(0, 1.25, -10);
  const head = vec3(base.x, base.y + 0.4, base.z);
  const { id, ...rest } = overrides;
  return {
    id,
    name: rest.name ?? `T${id}`,
    headPosition: rest.headPosition ?? head,
    chestPosition: rest.chestPosition ?? base,
    velocity: rest.velocity ?? vec3(0, 0, 0),
    alive: rest.alive ?? true,
    visible: rest.visible ?? true,
    team: rest.team ?? 1,
    ...rest,
  };
}

class MockAdapter implements IGameAdapter {
  constructor(
    public camera: CameraState,
    public targets: Target[] = []
  ) {}

  getCameraState(): CameraState {
    return this.camera;
  }

  getTargets(): Target[] {
    return this.targets;
  }

  applyCameraAngles(pitch: number, yaw: number): void {
    this.camera.pitch = pitch;
    this.camera.yaw = yaw;
    this.camera.forward = forwardFromAngles(yaw, pitch);
  }

  worldToScreen(): null {
    return null;
  }
}

function cameraAtOrigin(): CameraState {
  return {
    position: vec3(0, 1.7, 0),
    pitch: 0,
    yaw: 0,
    fov: 75,
    forward: forwardFromAngles(0, 0),
  };
}

describe("angular distance", () => {
  it("target directly ahead has ~0 angular distance", () => {
    const forward = forwardFromAngles(0, 0);
    const to = vec3(0, 1.7, -20);
    const from = vec3(0, 1.7, 0);
    const dir = vec3(to.x - from.x, to.y - from.y, to.z - from.z);
    const ang = calculateAngularDistance(forward, dir);
    expect(ang).toBeLessThan(0.01);
  });

  it("target behind camera is ~PI radians away", () => {
    const forward = forwardFromAngles(0, 0);
    const behind = vec3(0, 0, 1);
    const ang = calculateAngularDistance(forward, behind);
    expect(ang).toBeCloseTo(Math.PI, 2);
  });
});

describe("FOV boundary", () => {
  it("accepts target exactly on FOV boundary", () => {
    const halfDeg = 6;
    const halfRad = (halfDeg * Math.PI) / 180;
    expect(isInsideAimFov(halfRad, 12)).toBe(true);
  });

  it("rejects target just outside FOV boundary", () => {
    const halfDeg = 6.01;
    const halfRad = (halfDeg * Math.PI) / 180;
    expect(isInsideAimFov(halfRad, 12)).toBe(false);
  });
});

describe("selectBestTarget", () => {
  let config: AimConfig;
  let adapter: MockAdapter;

  beforeEach(() => {
    config = { ...DEFAULT_AIM_CONFIG, teamCheck: false, visibilityCheck: false };
    adapter = new MockAdapter(cameraAtOrigin());
  });

  it("picks closer-to-crosshair target among two in FOV", () => {
    const center = makeTarget({
      id: 1,
      chestPosition: vec3(0, 1.25, -20),
      headPosition: vec3(0, 1.65, -20),
    });
    const offCenter = makeTarget({
      id: 2,
      chestPosition: vec3(3, 1.25, -20),
      headPosition: vec3(3, 1.65, -20),
    });
    adapter.targets = [offCenter, center];
    const { best } = selectBestTarget(adapter, adapter.camera, adapter.targets, config);
    expect(best?.target.id).toBe(1);
  });

  it("rejects dead target", () => {
    adapter.targets = [
      makeTarget({ id: 1, alive: false, chestPosition: vec3(0, 1.25, -10) }),
    ];
    const { best, evaluations } = selectBestTarget(
      adapter,
      adapter.camera,
      adapter.targets,
      config
    );
    expect(best).toBeNull();
    expect(evaluations[0].reason).toBe("dead");
  });

  it("rejects same-team target when teamCheck enabled", () => {
    config.teamCheck = true;
    config.localTeam = 1;
    adapter.targets = [
      makeTarget({ id: 1, team: 1, chestPosition: vec3(0, 1.25, -10) }),
    ];
    const { best, evaluations } = selectBestTarget(
      adapter,
      adapter.camera,
      adapter.targets,
      config
    );
    expect(best).toBeNull();
    expect(evaluations[0].reason).toBe("same_team");
  });

  it("rejects invisible target when visibilityCheck enabled", () => {
    config.visibilityCheck = true;
    adapter.targets = [
      makeTarget({ id: 1, visible: false, chestPosition: vec3(0, 1.25, -10) }),
    ];
    const { evaluations } = selectBestTarget(
      adapter,
      adapter.camera,
      adapter.targets,
      config
    );
    expect(evaluations[0].reason).toBe("invisible");
  });
});

describe("prediction", () => {
  it("predicts moving target forward along velocity", () => {
    const aim = vec3(0, 0, 0);
    const vel = vec3(10, 0, 0);
    const cam = vec3(-100, 0, 0);
    const predicted = predictTargetPosition(aim, vel, cam, 100);
    // distance=100, t=1, x += 10
    expect(predicted.x).toBeCloseTo(10, 3);
  });

  it("high-speed lateral movement increases lead", () => {
    const slow = predictTargetPosition(vec3(0, 0, 0), vec3(5, 0, 0), vec3(0, 0, -50), 100);
    const fast = predictTargetPosition(vec3(0, 0, 0), vec3(20, 0, 0), vec3(0, 0, -50), 100);
    expect(fast.x).toBeGreaterThan(slow.x);
  });

  it("zero projectile velocity is clamped safely", () => {
    const predicted = predictTargetPosition(vec3(0, 0, -10), vec3(5, 0, 0), vec3(0, 0, 0), 0);
    expect(Number.isFinite(predicted.x)).toBe(true);
  });
});

describe("smoothing and yaw wrap", () => {
  it("converges toward desired angles", () => {
    let current = { pitch: 0, yaw: 0 };
    const desired = { pitch: 0.2, yaw: 0.5 };
    for (let i = 0; i < 50; i++) {
      current = smoothAimAngles(current, desired, 0.3, 0.3);
    }
    expect(Math.abs(current.yaw - desired.yaw)).toBeLessThan(0.02);
    expect(Math.abs(current.pitch - desired.pitch)).toBeLessThan(0.02);
  });

  it("yaw wraps around ±180° shortest path", () => {
    const delta = angleDelta(Math.PI - 0.1, -Math.PI + 0.1);
    expect(Math.abs(delta)).toBeLessThan(0.3);
    const lerped = lerpAngle(Math.PI - 0.1, -Math.PI + 0.1, 0.5);
    expect(Number.isFinite(lerped)).toBe(true);
  });
});

describe("AimAssistEngine integration", () => {
  it("target disappearing clears selection", () => {
    const config = {
      ...DEFAULT_AIM_CONFIG,
      teamCheck: false,
      updateRate: 1000,
    };
    const engine = new AimAssistEngine(config);
    const adapter = new MockAdapter(cameraAtOrigin(), [
      makeTarget({ id: 1, chestPosition: vec3(0, 1.25, -10) }),
    ]);
    const r1 = engine.updateAimAssist(adapter, 0.016);
    expect(r1.selectedTarget?.id).toBe(1);
    adapter.targets = [];
    const r2 = engine.updateAimAssist(adapter, 0.016);
    expect(r2.selectedTarget).toBeNull();
  });

  it("target dying is rejected on next tick", () => {
    const engine = new AimAssistEngine({
      ...DEFAULT_AIM_CONFIG,
      teamCheck: false,
      updateRate: 1000,
    });
    const t = makeTarget({ id: 1, chestPosition: vec3(0, 1.25, -10) });
    const adapter = new MockAdapter(cameraAtOrigin(), [t]);
    engine.updateAimAssist(adapter, 0.016);
    t.alive = false;
    const r = engine.updateAimAssist(adapter, 0.016);
    expect(r.selectedTarget).toBeNull();
  });

  it("target changing teams gets filtered when teamCheck on", () => {
    const engine = new AimAssistEngine({
      ...DEFAULT_AIM_CONFIG,
      localTeam: 0,
      teamCheck: true,
      updateRate: 1000,
    });
    const t = makeTarget({ id: 1, team: 1, chestPosition: vec3(0, 1.25, -10) });
    const adapter = new MockAdapter(cameraAtOrigin(), [t]);
    const r1 = engine.updateAimAssist(adapter, 0.016);
    expect(r1.selectedTarget?.id).toBe(1);
    t.team = 0;
    const r2 = engine.updateAimAssist(adapter, 0.016);
    expect(r2.selectedTarget).toBeNull();
  });

  it("keeps locked target while switch cooldown active", () => {
    const engine = new AimAssistEngine({
      ...DEFAULT_AIM_CONFIG,
      aimFov: 20,
      teamCheck: false,
      targetSwitchDelay: 0.5,
      updateRate: 1000,
    });
    const a = makeTarget({ id: 1, chestPosition: vec3(0, 1.25, -10) });
    const b = makeTarget({ id: 2, chestPosition: vec3(2, 1.25, -10) });
    const adapter = new MockAdapter(cameraAtOrigin(), [a, b]);
    engine.updateAimAssist(adapter, 0.016);
    adapter.camera.yaw = 0.05;
    adapter.camera.forward = forwardFromAngles(0.05, 0);
    const r = engine.updateAimAssist(adapter, 0.016);
    expect(r.selectedTarget?.id).toBe(1);
  });
});

describe("getAimPoint", () => {
  it("selects head vs chest", () => {
    const t = makeTarget({ id: 1 });
    expect(getAimPoint(t, "head").y).toBeGreaterThan(getAimPoint(t, "chest").y);
  });
});

describe("calculateAimAngles", () => {
  it("points at target above horizon (negative pitch in Y-up convention)", () => {
    const angles = calculateAimAngles(vec3(0, 0, 0), vec3(0, 10, -10));
    expect(angles.pitch).toBeLessThan(0);
  });
});
