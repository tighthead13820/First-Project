import * as THREE from "three";
import {
  AimAssistEngine,
  DEFAULT_AIM_CONFIG,
  forwardFromAngles,
  fovRadiusPixels,
} from "@aim-framework/core";

/** Adapter A — built-in simulator implementing IGameAdapter. */
export class SimulatorAdapter {
  constructor(scene, camera, dummyRegistry) {
    this.scene = scene;
    this.camera = camera;
    this.dummyRegistry = dummyRegistry;
    this.localTeam = 0;
  }

  getCameraState() {
    const p = this.camera.position;
    const yaw = this.camera.rotation.y;
    const pitch = this.camera.rotation.x;
    return {
      position: { x: p.x, y: p.y, z: p.z },
      forward: forwardFromAngles(yaw, pitch),
      pitch,
      yaw,
      fov: this.camera.fov,
    };
  }

  getTargets() {
    return this.dummyRegistry.getTargets(this.localTeam);
  }

  applyCameraAngles(pitch, yaw) {
    this.camera.rotation.order = "YXZ";
    this.camera.rotation.y = yaw;
    this.camera.rotation.x = pitch;
  }

  worldToScreen(position) {
    const v = new THREE.Vector3(position.x, position.y, position.z);
    v.project(this.camera);
    if (v.z > 1) return null;
    return {
      x: (v.x * 0.5 + 0.5) * window.innerWidth,
      y: (-v.y * 0.5 + 0.5) * window.innerHeight,
    };
  }
}

export class DummyRegistry {
  constructor(scene) {
    this.scene = scene;
    this.dummies = [];
    this.nextId = 1;
  }

  add(config) {
    const id = this.nextId++;
    const geo = new THREE.CapsuleGeometry(0.35, 1.2, 4, 8);
    const mat = new THREE.MeshStandardMaterial({ color: config.color ?? 0x8899aa });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.position.copy(config.position);
    this.scene.add(mesh);

    const dummy = {
      id,
      name: config.name ?? `Dummy-${id}`,
      mesh,
      baseMat: mat,
      velocity: config.velocity.clone(),
      team: config.team ?? 1,
      alive: true,
      visible: config.visible ?? true,
      pattern: config.pattern ?? "linear",
      headHeight: 1.65,
      chestHeight: 1.25,
      bounds: config.bounds,
      highlightMat: new THREE.MeshStandardMaterial({
        color: 0x44ff88,
        emissive: 0x114422,
      }),
    };
    this.dummies.push(dummy);
    return dummy;
  }

  getTargets(localTeam) {
    return this.dummies.map((d) => {
      const base = d.mesh.position;
      return {
        id: d.id,
        name: d.name,
        headPosition: { x: base.x, y: base.y + d.headHeight - 0.9, z: base.z },
        chestPosition: { x: base.x, y: base.y + d.chestHeight - 0.9, z: base.z },
        velocity: { x: d.velocity.x, y: d.velocity.y, z: d.velocity.z },
        alive: d.alive,
        visible: d.visible,
        team: d.team,
      };
    });
  }

  update(dt) {
    for (const d of this.dummies) {
      if (!d.alive) continue;
      const p = d.mesh.position;
      if (d.pattern === "linear" && d.bounds) {
        p.addScaledVector(d.velocity, dt);
        if (p.x < d.bounds.minX || p.x > d.bounds.maxX) d.velocity.x *= -1;
        if (p.z < d.bounds.minZ || p.z > d.bounds.maxZ) d.velocity.z *= -1;
      } else if (d.pattern === "circle") {
        d._angle = (d._angle ?? 0) + dt * d.speed;
        p.x = d.center.x + Math.cos(d._angle) * d.radius;
        p.z = d.center.z + Math.sin(d._angle) * d.radius;
        d.velocity.set(-Math.sin(d._angle) * d.speed * d.radius, 0, Math.cos(d._angle) * d.speed * d.radius);
      } else if (d.pattern === "approach") {
        // Moves toward origin on XZ
        const dir = new THREE.Vector3(-p.x, 0, -p.z).normalize();
        d.velocity.copy(dir.multiplyScalar(d.speed));
        p.addScaledVector(d.velocity, dt);
      }
    }
  }

  setHighlight(id) {
    for (const d of this.dummies) {
      d.mesh.material = d.id === id ? d.highlightMat : d.baseMat;
    }
  }
}

export function spawnDefaultDummies(registry) {
  registry.add({
    name: "Stationary-A",
    position: new THREE.Vector3(-6, 0.9, -8),
    velocity: new THREE.Vector3(0, 0, 0),
    team: 1,
    bounds: { minX: -6, maxX: -6, minZ: -8, maxZ: -8 },
  });
  registry.add({
    name: "Lateral-Fast",
    position: new THREE.Vector3(0, 0.9, -12),
    velocity: new THREE.Vector3(4, 0, 0),
    team: 1,
    bounds: { minX: -8, maxX: 8, minZ: -12, maxZ: -12 },
  });
  registry.add({
    name: "Approach",
    position: new THREE.Vector3(0, 0.9, -25),
    velocity: new THREE.Vector3(0, 0, 2),
    pattern: "approach",
    speed: 3,
    team: 1,
  });
  registry.add({
    name: "Circle",
    position: new THREE.Vector3(8, 0.9, -10),
    velocity: new THREE.Vector3(0, 0, 0),
    pattern: "circle",
    center: new THREE.Vector3(8, 0.9, -10),
    radius: 4,
    speed: 1.2,
    team: 1,
  });
  registry.add({
    name: "Ally",
    position: new THREE.Vector3(-4, 0.9, -6),
    velocity: new THREE.Vector3(1, 0, 0),
    team: 0,
    color: 0x6688ff,
    bounds: { minX: -8, maxX: 0, minZ: -6, maxZ: -6 },
  });
}

export function createConfigPanel(config, onChange) {
  const panel = document.getElementById("config-panel");
  panel.innerHTML = `<h2>Aim Config</h2>`;
  const fields = [
    ["enabled", "checkbox", config.enabled],
    ["aimFov", "range", config.aimFov, 1, 45, 0.5],
    ["maxDistance", "range", config.maxDistance, 5, 200, 1],
    ["targetPoint", "select", config.targetPoint],
    ["smoothing", "range", config.smoothing, 0.01, 1, 0.01],
    ["horizontalSmoothing", "range", config.horizontalSmoothing, 0.01, 1, 0.01],
    ["verticalSmoothing", "range", config.verticalSmoothing, 0.01, 1, 0.01],
    ["predictionEnabled", "checkbox", config.predictionEnabled],
    ["projectileVelocity", "range", config.projectileVelocity, 50, 500, 10],
    ["gravityCompensation", "checkbox", config.gravityCompensation],
    ["targetSwitchDelay", "range", config.targetSwitchDelay, 0, 1, 0.05],
    ["visibilityCheck", "checkbox", config.visibilityCheck],
    ["teamCheck", "checkbox", config.teamCheck],
    ["updateRate", "range", config.updateRate, 10, 120, 1],
    ["debugOverlay", "checkbox", config.debugOverlay],
  ];

  for (const f of fields) {
    const [key, type, val, min, max, step] = f;
    const label = document.createElement("label");
    label.textContent = key;
    let input;
    if (type === "checkbox") {
      input = document.createElement("input");
      input.type = "checkbox";
      input.checked = val;
      input.oninput = () => { config[key] = input.checked; onChange(); };
    } else if (type === "select") {
      input = document.createElement("select");
      for (const opt of ["head", "chest", "custom"]) {
        const o = document.createElement("option");
        o.value = opt; o.textContent = opt;
        if (opt === val) o.selected = true;
        input.appendChild(o);
      }
      input.oninput = () => { config[key] = input.value; onChange(); };
    } else {
      input = document.createElement("input");
      input.type = "range";
      input.min = min; input.max = max; input.step = step; input.value = val;
      input.oninput = () => { config[key] = parseFloat(input.value); onChange(); };
    }
    label.appendChild(input);
    panel.appendChild(label);
  }
}

export function renderDebugOverlay(result, config, fps, updateHz) {
  const panel = document.getElementById("debug-panel");
  const sel = result.selectedEvaluation;
  let text = `FPS: ${fps.toFixed(0)}  |  Aim tick: ${updateHz.toFixed(0)} Hz\n`;
  text += `Assist: ${config.enabled ? "ON" : "OFF"}\n\n`;

  if (sel) {
    text += `SELECTED: ${sel.target.name} (#${sel.target.id})\n`;
    text += `Distance: ${sel.distance.toFixed(2)} m-units\n`;
    text += `Angular: ${((sel.angularDistance * 180) / Math.PI).toFixed(2)}°\n`;
    text += `Velocity: (${sel.target.velocity.x.toFixed(1)}, ${sel.target.velocity.y.toFixed(1)}, ${sel.target.velocity.z.toFixed(1)})\n`;
    text += `Predicted: (${sel.predictedAimPoint.x.toFixed(2)}, ${sel.predictedAimPoint.y.toFixed(2)}, ${sel.predictedAimPoint.z.toFixed(2)})\n`;
    if (result.desiredAngles) {
      text += `Current yaw/pitch: ${((result.currentAngles.yaw * 180) / Math.PI).toFixed(1)}° / ${((result.currentAngles.pitch * 180) / Math.PI).toFixed(1)}°\n`;
      text += `Desired yaw/pitch: ${((result.desiredAngles.yaw * 180) / Math.PI).toFixed(1)}° / ${((result.desiredAngles.pitch * 180) / Math.PI).toFixed(1)}°\n`;
    }
    text += `Smooth H/V: ${config.horizontalSmoothing} / ${config.verticalSmoothing}\n`;
    if (sel.screenAim) text += `Screen aim: ${sel.screenAim.x.toFixed(0)}, ${sel.screenAim.y.toFixed(0)}\n`;
  } else {
    text += `SELECTED: none\n`;
  }

  text += `\n--- Targets ---\n`;
  for (const ev of result.evaluations) {
    const cls =
      ev.reason === "selected" ? "status-selected" :
      ev.reason === "dead" ? "status-dead" :
      ev.reason === "same_team" ? "status-team" :
      ev.reason === "invisible" ? "status-invisible" :
      "status-outside";
    text += `[${ev.reason}] ${ev.target.name} ∠${((ev.angularDistance * 180) / Math.PI).toFixed(1)}° d=${ev.distance.toFixed(1)}\n`;
  }
  panel.textContent = text;
}

export function drawFovCircle(canvas, camera, aimFov, selected) {
  const ctx = canvas.getContext("2d");
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const r = fovRadiusPixels(aimFov, camera.fov, canvas.height);
  ctx.beginPath();
  ctx.arc(canvas.width / 2, canvas.height / 2, r, 0, Math.PI * 2);
  ctx.strokeStyle = selected ? "#44ff88" : "#7dd3fc";
  ctx.lineWidth = 2;
  ctx.stroke();
}

export { DEFAULT_AIM_CONFIG, AimAssistEngine };
