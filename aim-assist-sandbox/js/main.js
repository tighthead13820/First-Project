import * as THREE from "three";
import { AimAssist } from "./aimAssist.js";
import { createTargets } from "./targets.js";
import { UI } from "./ui.js";
import { forwardFromAngles } from "./math.js";

// ---------------------------------------------------------------------------
// Scene setup
// ---------------------------------------------------------------------------

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
document.body.prepend(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x1a1a28);
scene.fog = new THREE.Fog(0x1a1a28, 30, 90);

const camera = new THREE.PerspectiveCamera(
  75,
  window.innerWidth / window.innerHeight,
  0.1,
  200
);

const ground = new THREE.Mesh(
  new THREE.PlaneGeometry(60, 60),
  new THREE.MeshStandardMaterial({ color: 0x2a2a38, roughness: 0.9 })
);
ground.rotation.x = -Math.PI / 2;
ground.receiveShadow = true;
scene.add(ground);
scene.add(new THREE.GridHelper(60, 30, 0x444466, 0x333344));

scene.add(new THREE.AmbientLight(0x404060, 0.6));
const sun = new THREE.DirectionalLight(0xffffff, 1.0);
sun.position.set(10, 20, 5);
sun.castShadow = true;
sun.shadow.mapSize.set(1024, 1024);
scene.add(sun);

const targets = createTargets(scene);
const aimAssist = new AimAssist();
const ui = new UI(aimAssist, camera);

// ---------------------------------------------------------------------------
// ONE authoritative look state. Mouse and aim-assist both write HERE.
// Camera rotation is applied ONCE at the end of the frame.
// ---------------------------------------------------------------------------

const player = {
  position: new THREE.Vector3(0, 1.7, 12),
  yaw: 0,
  pitch: 0,
  speed: 8,
};

const PITCH_LIMIT = (89 * Math.PI) / 180;

/** Buffered mouse deltas — applied once per frame before aim-assist. */
const mouseDelta = { yaw: 0, pitch: 0 };

let pointerLocked = false;

renderer.domElement.addEventListener("click", () => {
  renderer.domElement.requestPointerLock();
});

document.addEventListener("pointerlockchange", () => {
  pointerLocked = document.pointerLockElement === renderer.domElement;
});

document.addEventListener("mousemove", (e) => {
  if (!pointerLocked) return;
  const sensitivity = 0.002;
  // Accumulate only — do NOT write camera.rotation here.
  mouseDelta.yaw -= e.movementX * sensitivity;
  mouseDelta.pitch -= e.movementY * sensitivity;
});

const keys = {};
document.addEventListener("keydown", (e) => {
  keys[e.code] = true;
});
document.addEventListener("keyup", (e) => {
  keys[e.code] = false;
});

function consumeMouseLook() {
  player.yaw += mouseDelta.yaw;
  player.pitch += mouseDelta.pitch;
  player.pitch = THREE.MathUtils.clamp(player.pitch, -PITCH_LIMIT, PITCH_LIMIT);
  mouseDelta.yaw = 0;
  mouseDelta.pitch = 0;
}

function updateMovement(dt) {
  const forward = new THREE.Vector3(
    Math.sin(player.yaw),
    0,
    -Math.cos(player.yaw)
  );
  const right = new THREE.Vector3(
    Math.cos(player.yaw),
    0,
    Math.sin(player.yaw)
  );

  const move = new THREE.Vector3();
  if (keys["KeyW"]) move.add(forward);
  if (keys["KeyS"]) move.sub(forward);
  if (keys["KeyD"]) move.add(right);
  if (keys["KeyA"]) move.sub(right);
  if (keys["Space"]) move.y += 1;
  if (keys["ShiftLeft"] || keys["ShiftRight"]) move.y -= 1;

  if (move.lengthSq() > 0) {
    move.normalize().multiplyScalar(player.speed * dt);
    player.position.add(move);
    player.position.y = THREE.MathUtils.clamp(player.position.y, 0.5, 20);
  }
}

function applyCameraTransform() {
  camera.position.copy(player.position);
  camera.rotation.order = "YXZ";
  camera.rotation.y = player.yaw;
  camera.rotation.x = player.pitch;
}

// ---------------------------------------------------------------------------
// Debug visuals: target lines + camera forward ray + desired aim ray
// ---------------------------------------------------------------------------

const debugLineMaterialOutside = new THREE.LineBasicMaterial({ color: 0x64748b });
const debugLineMaterialInside = new THREE.LineBasicMaterial({ color: 0xfbbf24 });
const debugLineMaterialSelected = new THREE.LineBasicMaterial({ color: 0x44ff88 });
const debugLines = targets.map(() => {
  const geo = new THREE.BufferGeometry().setFromPoints([
    new THREE.Vector3(),
    new THREE.Vector3(),
  ]);
  const line = new THREE.Line(geo, debugLineMaterialOutside);
  line.visible = false;
  scene.add(line);
  return line;
});

function makeRay(color) {
  const geo = new THREE.BufferGeometry().setFromPoints([
    new THREE.Vector3(),
    new THREE.Vector3(),
  ]);
  const line = new THREE.Line(geo, new THREE.LineBasicMaterial({ color }));
  line.visible = false;
  scene.add(line);
  return line;
}

const forwardRay = makeRay(0x60a5fa); // blue = current look
const desiredRay = makeRay(0xf472b6); // pink = desired aim
const aimPointMarker = new THREE.Mesh(
  new THREE.SphereGeometry(0.08, 8, 8),
  new THREE.MeshBasicMaterial({ color: 0xf472b6 })
);
aimPointMarker.visible = false;
scene.add(aimPointMarker);

function setLineEndpoints(line, a, b) {
  const pos = line.geometry.attributes.position;
  pos.setXYZ(0, a.x, a.y, a.z);
  pos.setXYZ(1, b.x, b.y, b.z);
  pos.needsUpdate = true;
  line.geometry.computeBoundingSphere();
  line.visible = true;
}

function updateDebugLines() {
  const show = ui.drawAimLines;
  const camPos = player.position;

  for (let i = 0; i < targets.length; i++) {
    const line = debugLines[i];
    const ev = aimAssist.evaluations[i];
    if (!show || !ev) {
      line.visible = false;
      continue;
    }
    setLineEndpoints(line, camPos, ev.aimPoint);
    if (ev.target === aimAssist.selectedTarget) {
      line.material = debugLineMaterialSelected;
    } else if (ev.insideFov) {
      line.material = debugLineMaterialInside;
    } else {
      line.material = debugLineMaterialOutside;
    }
  }

  if (!show) {
    forwardRay.visible = false;
    desiredRay.visible = false;
    aimPointMarker.visible = false;
    return;
  }

  // Current camera forward ray (from authoritative yaw/pitch AFTER aim update)
  const fwd = forwardFromAngles(player.yaw, player.pitch);
  setLineEndpoints(
    forwardRay,
    camPos,
    {
      x: camPos.x + fwd.x * 8,
      y: camPos.y + fwd.y * 8,
      z: camPos.z + fwd.z * 8,
    }
  );

  const tracking = aimAssist.tracking;
  if (tracking) {
    const aim = tracking.aimPoint;
    setLineEndpoints(desiredRay, camPos, aim);
    aimPointMarker.position.copy(aim);
    aimPointMarker.visible = true;
  } else {
    desiredRay.visible = false;
    aimPointMarker.visible = false;
  }
}

function updateTargetColours() {
  for (const ev of aimAssist.evaluations) {
    if (ev.target === aimAssist.selectedTarget) {
      ev.target.setVisualState("selected");
    } else if (ev.insideFov && ev.inRange) {
      ev.target.setVisualState("insideFov");
    } else {
      ev.target.setVisualState("valid");
    }
  }
}

// ---------------------------------------------------------------------------
// Main loop — single authority pipeline
// ---------------------------------------------------------------------------

const clock = new THREE.Clock();

function animate() {
  requestAnimationFrame(animate);
  const dt = Math.min(clock.getDelta(), 0.05);

  // 1. Mouse look into shared yaw/pitch (once)
  consumeMouseLook();

  // 2. Movement uses the same yaw
  updateMovement(dt);

  // 3. Targets move
  for (const target of targets) {
    target.update(dt);
  }

  // 4. Sync camera to current look (needed for screen-space target detection)
  applyCameraTransform();
  aimAssist.cameraVfov = camera.fov;

  // 5. Aim assist reads + writes the SAME player.yaw / player.pitch
  const assisted = aimAssist.update(player, targets, dt, camera);
  player.yaw = assisted.yaw;
  player.pitch = THREE.MathUtils.clamp(assisted.pitch, -PITCH_LIMIT, PITCH_LIMIT);

  // 6. Apply camera ONCE from authoritative state after aim assist
  applyCameraTransform();

  updateTargetColours();
  updateDebugLines();

  ui.drawFovOverlay();
  ui.updateReadout();

  renderer.render(scene, camera);
}

animate();

window.addEventListener("resize", () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});
