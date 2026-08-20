import * as THREE from "three";
import {
  SimulatorAdapter,
  DummyRegistry,
  spawnDefaultDummies,
  createConfigPanel,
  renderDebugOverlay,
  drawFovCircle,
  AimAssistEngine,
  DEFAULT_AIM_CONFIG,
} from "./simulatorAdapter.js";

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
document.body.prepend(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x141824);
scene.fog = new THREE.Fog(0x141824, 40, 120);

const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 300);
camera.rotation.order = "YXZ";

const ground = new THREE.Mesh(
  new THREE.PlaneGeometry(80, 80),
  new THREE.MeshStandardMaterial({ color: 0x2a3040 })
);
ground.rotation.x = -Math.PI / 2;
scene.add(ground);
scene.add(new THREE.GridHelper(80, 40, 0x445566, 0x333344));
scene.add(new THREE.AmbientLight(0x404060, 0.7));
const sun = new THREE.DirectionalLight(0xffffff, 1);
sun.position.set(10, 20, 8);
scene.add(sun);

const registry = new DummyRegistry(scene);
spawnDefaultDummies(registry);

const adapter = new SimulatorAdapter(scene, camera, registry);
const config = { ...DEFAULT_AIM_CONFIG };
const engine = new AimAssistEngine(config);
createConfigPanel(config, () => { engine.config = config; });

const player = { speed: 8, yaw: 0, pitch: 0 };
camera.position.set(0, 1.7, 8);
const keys = {};
document.addEventListener("keydown", (e) => { keys[e.code] = true; });
document.addEventListener("keyup", (e) => { keys[e.code] = false; });

let pointerLocked = false;
renderer.domElement.onclick = () => renderer.domElement.requestPointerLock();
document.addEventListener("pointerlockchange", () => {
  pointerLocked = document.pointerLockElement === renderer.domElement;
});
document.addEventListener("mousemove", (e) => {
  if (!pointerLocked) return;
  player.yaw -= e.movementX * 0.002;
  player.pitch -= e.movementY * 0.002;
  player.pitch = THREE.MathUtils.clamp(player.pitch, -1.5, 1.5);
});

const clock = new THREE.Clock();
let fps = 60;
let updateHz = 0;
let updateAccum = 0;
let updateCount = 0;
const fovCanvas = document.getElementById("fov-overlay");

function animate() {
  requestAnimationFrame(animate);
  const dt = Math.min(clock.getDelta(), 0.05);
  fps = fps * 0.9 + (1 / dt) * 0.1;

  const forward = new THREE.Vector3(Math.sin(player.yaw), 0, -Math.cos(player.yaw));
  const right = new THREE.Vector3(Math.cos(player.yaw), 0, Math.sin(player.yaw));
  const move = new THREE.Vector3();
  if (keys.KeyW) move.add(forward);
  if (keys.KeyS) move.sub(forward);
  if (keys.KeyD) move.add(right);
  if (keys.KeyA) move.sub(right);
  if (move.lengthSq()) {
    move.normalize().multiplyScalar(player.speed * dt);
    camera.position.add(move);
  }

  camera.rotation.y = player.yaw;
  camera.rotation.x = player.pitch;

  registry.update(dt);
  engine.config = config;
  adapter.localTeam = config.localTeam;
  const result = engine.updateAimAssist(adapter, dt);
  if (result.smoothedAngles) {
    player.yaw = result.smoothedAngles.yaw;
    player.pitch = result.smoothedAngles.pitch;
  }

  registry.setHighlight(result.selectedTarget?.id ?? null);

  updateCount++;
  updateAccum += dt;
  if (updateAccum >= 1) {
    updateHz = updateCount / updateAccum;
    updateCount = 0;
    updateAccum = 0;
  }

  if (config.debugOverlay) {
    renderDebugOverlay(result, config, fps, updateHz);
    drawFovCircle(fovCanvas, camera, config.aimFov, result.selectedTarget);
  } else {
    document.getElementById("debug-panel").textContent = "Debug overlay disabled";
    fovCanvas.getContext("2d").clearRect(0, 0, fovCanvas.width, fovCanvas.height);
  }

  renderer.render(scene, camera);
}

animate();

window.addEventListener("resize", () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});
