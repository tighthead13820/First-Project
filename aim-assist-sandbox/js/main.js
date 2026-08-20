import * as THREE from "three";
import { AimAssist } from "./aimAssist.js";
import { createTargets } from "./targets.js";
import { UI } from "./ui.js";

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

// Ground
const ground = new THREE.Mesh(
  new THREE.PlaneGeometry(60, 60),
  new THREE.MeshStandardMaterial({ color: 0x2a2a38, roughness: 0.9 })
);
ground.rotation.x = -Math.PI / 2;
ground.receiveShadow = true;
scene.add(ground);

// Grid helper for spatial reference
const grid = new THREE.GridHelper(60, 30, 0x444466, 0x333344);
scene.add(grid);

// Lighting
const ambient = new THREE.AmbientLight(0x404060, 0.6);
scene.add(ambient);
const sun = new THREE.DirectionalLight(0xffffff, 1.0);
sun.position.set(10, 20, 5);
sun.castShadow = true;
sun.shadow.mapSize.set(1024, 1024);
scene.add(sun);

// Targets
const targets = createTargets(scene);

// Aim assist + UI
const aimAssist = new AimAssist();
const ui = new UI(aimAssist, camera);

// ---------------------------------------------------------------------------
// First-person camera state
// ---------------------------------------------------------------------------

const player = {
  position: new THREE.Vector3(0, 1.7, 12),
  yaw: 0,
  pitch: 0,
  speed: 8,
};

const PITCH_LIMIT = (89 * Math.PI) / 180;

// Pointer lock for mouse look
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
  player.yaw -= e.movementX * sensitivity;
  player.pitch -= e.movementY * sensitivity;
  player.pitch = THREE.MathUtils.clamp(player.pitch, -PITCH_LIMIT, PITCH_LIMIT);
});

// Keyboard movement
const keys = {};
document.addEventListener("keydown", (e) => {
  keys[e.code] = true;
});
document.addEventListener("keyup", (e) => {
  keys[e.code] = false;
});

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
  // YXZ order: yaw around world Y, then pitch around local X
  camera.rotation.order = "YXZ";
  camera.rotation.y = player.yaw;
  camera.rotation.x = player.pitch;
}

// ---------------------------------------------------------------------------
// Main loop
// ---------------------------------------------------------------------------

const clock = new THREE.Clock();

function animate() {
  requestAnimationFrame(animate);
  const dt = Math.min(clock.getDelta(), 0.05);

  updateMovement(dt);

  for (const target of targets) {
    target.update(dt);
  }

  // Aim assist adjusts yaw/pitch before camera is applied
  const assisted = aimAssist.update(player, targets);
  player.yaw = assisted.yaw;
  player.pitch = assisted.pitch;

  // Highlight selected target
  for (const target of targets) {
    target.setHighlighted(target === aimAssist.selectedTarget);
  }

  applyCameraTransform();

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
