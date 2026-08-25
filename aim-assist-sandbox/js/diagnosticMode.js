import * as THREE from "three";
import { DummyTarget } from "./targets.js";
import {
  anglesFromDirection,
  anglesFromDirectionLegacy,
  forwardFromAngles,
  angleBetween,
  projectWorldToScreenPixels,
} from "./math.js";

/**
 * Strict one-target diagnostic mode.
 *
 * Pipeline each frame (no mouse look, no prediction, no smoothing):
 *   1. Read exact head world position from head marker
 *   2. Compute yaw/pitch to look at head (fixed Three.js YXZ convention)
 *   3. Write player.yaw/pitch ONCE → applyCameraTransform ONCE
 *   4. updateMatrixWorld(true)
 *   5. Project head → compare to screen centre
 */

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
document.body.prepend(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x12121c);

const camera = new THREE.PerspectiveCamera(
  75,
  window.innerWidth / window.innerHeight,
  0.1,
  200
);

scene.add(new THREE.AmbientLight(0xffffff, 0.8));
const sun = new THREE.DirectionalLight(0xffffff, 0.9);
sun.position.set(5, 10, 7);
scene.add(sun);

scene.add(new THREE.GridHelper(40, 20, 0x444466, 0x333344));

// Exactly one stationary target (velocity zero, no bounds bounce).
const target = new DummyTarget(scene, {
  x: 4,
  z: -2,
  vx: 0,
  vz: 0,
  minX: 4,
  maxX: 4,
  minZ: -2,
  maxZ: -2,
});
target.setVisualState("selected");

const player = {
  position: new THREE.Vector3(0, 1.7, 12),
  yaw: 0,
  pitch: 0,
};

const readoutEl = document.getElementById("diag-readout");
const passBanner = document.getElementById("pass-banner");

const _headWorld = new THREE.Vector3();
const _toHead = new THREE.Vector3();
const _forward = new THREE.Vector3();
const _desiredAngles = { yaw: 0, pitch: 0 };
const _legacyAngles = { yaw: 0, pitch: 0 };
const _screen = { x: 0, y: 0, ndcX: 0, ndcY: 0, ndcZ: 0 };
const _legacyScreen = { x: 0, y: 0, ndcX: 0, ndcY: 0, ndcZ: 0 };

/** Single write site for camera orientation. */
function applyCameraTransform() {
  camera.position.copy(player.position);
  camera.rotation.order = "YXZ";
  camera.rotation.y = player.yaw;
  camera.rotation.x = player.pitch;
  camera.rotation.z = 0;
}

function syncRendererAndCameraAspect() {
  const canvas = renderer.domElement;
  const w = canvas.clientWidth;
  const h = canvas.clientHeight;
  if (canvas.width !== w * renderer.getPixelRatio() || canvas.height !== h * renderer.getPixelRatio()) {
    renderer.setSize(w, h, false);
  }
  if (Math.abs(camera.aspect - w / h) > 1e-6) {
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }
}

function measureLegacyError() {
  const cam = camera.clone();
  cam.position.copy(player.position);
  cam.rotation.order = "YXZ";
  cam.rotation.y = _legacyAngles.yaw;
  cam.rotation.x = _legacyAngles.pitch;
  cam.rotation.z = 0;
  cam.updateMatrixWorld(true);
  const canvas = renderer.domElement;
  projectWorldToScreenPixels(_headWorld, cam, canvas.clientWidth, canvas.clientHeight, _legacyScreen);
  const cx = canvas.clientWidth / 2;
  const cy = canvas.clientHeight / 2;
  const pxErr = _legacyScreen.x - cx;
  const pyErr = _legacyScreen.y - cy;
  const total = Math.hypot(pxErr, pyErr);
  const fwd = new THREE.Vector3();
  cam.getWorldDirection(fwd);
  const ang = (angleBetween(fwd, _toHead) * 180) / Math.PI;
  return { pxErr, pyErr, total, ang, cx, cy };
}

function animate() {
  requestAnimationFrame(animate);

  syncRendererAndCameraAspect();

  // 1. Exact head world position (from visual marker, not mesh centre).
  target.headMarker.getWorldPosition(_headWorld);

  // Legacy broken math reference (before fix).
  _toHead.copy(_headWorld).sub(player.position).normalize();
  anglesFromDirectionLegacy(_toHead, _legacyAngles);
  const legacy = measureLegacyError();

  // 2. Desired camera rotation (fixed Three.js YXZ convention).
  anglesFromDirection(_toHead, _desiredAngles);
  const desiredYaw = _desiredAngles.yaw;
  const desiredPitch = _desiredAngles.pitch;

  // 3. Apply rotation — ONLY write to player.yaw/pitch, then applyCameraTransform.
  player.yaw = desiredYaw;
  player.pitch = desiredPitch;
  applyCameraTransform();

  // 4. Force matrix update before projection.
  camera.updateMatrixWorld(true);

  // 5. Project same head point; compare to screen centre.
  const canvas = renderer.domElement;
  const screenW = canvas.clientWidth;
  const screenH = canvas.clientHeight;
  const centerX = screenW / 2;
  const centerY = screenH / 2;

  projectWorldToScreenPixels(_headWorld, camera, screenW, screenH, _screen);

  const pixelErrX = _screen.x - centerX;
  const pixelErrY = _screen.y - centerY;
  const totalPixelErr = Math.hypot(pixelErrX, pixelErrY);

  camera.getWorldDirection(_forward);
  const angularErrDeg = (angleBetween(_forward, _toHead) * 180) / Math.PI;

  const passAngular = angularErrDeg < 0.1;
  const passPixel = totalPixelErr < 2;
  const pass = passAngular && passPixel;

  passBanner.className = pass ? "pass" : "fail";
  passBanner.textContent = pass
    ? `PASS — angular ${angularErrDeg.toFixed(4)}° · pixel ${totalPixelErr.toFixed(3)}px`
    : `FAIL — angular ${angularErrDeg.toFixed(4)}° (need <0.1°) · pixel ${totalPixelErr.toFixed(3)}px (need <2px)`;

  readoutEl.textContent = [
    "=== BEFORE FIX (legacy yaw/pitch signs) ===",
    `Legacy pixel error X/Y: ${legacy.pxErr.toFixed(3)} / ${legacy.pyErr.toFixed(3)}`,
    `Legacy total pixel error: ${legacy.total.toFixed(3)} px`,
    `Legacy angular error: ${legacy.ang.toFixed(4)}°`,
    "",
    "=== AFTER FIX (this frame) ===",
    `Head world position: ${_headWorld.x.toFixed(4)}, ${_headWorld.y.toFixed(4)}, ${_headWorld.z.toFixed(4)}`,
    `Camera world position: ${camera.position.x.toFixed(4)}, ${camera.position.y.toFixed(4)}, ${camera.position.z.toFixed(4)}`,
    `Camera forward vector: ${_forward.x.toFixed(6)}, ${_forward.y.toFixed(6)}, ${_forward.z.toFixed(6)}`,
    `Desired yaw (rad/deg): ${desiredYaw.toFixed(6)} / ${((desiredYaw * 180) / Math.PI).toFixed(4)}°`,
    `Desired pitch (rad/deg): ${desiredPitch.toFixed(6)} / ${((desiredPitch * 180) / Math.PI).toFixed(4)}°`,
    `Applied yaw (rad/deg): ${player.yaw.toFixed(6)} / ${((player.yaw * 180) / Math.PI).toFixed(4)}°`,
    `Applied pitch (rad/deg): ${player.pitch.toFixed(6)} / ${((player.pitch * 180) / Math.PI).toFixed(4)}°`,
    `Projected head X/Y: ${_screen.x.toFixed(3)} / ${_screen.y.toFixed(3)}`,
    `Screen centre X/Y: ${centerX.toFixed(3)} / ${centerY.toFixed(3)}`,
    `Pixel error X/Y: ${pixelErrX.toFixed(3)} / ${pixelErrY.toFixed(3)}`,
    `Total pixel error: ${totalPixelErr.toFixed(3)} px`,
    `Angular error after rotation: ${angularErrDeg.toFixed(6)}°`,
    "",
    "=== RENDERER ===",
    `Canvas client: ${screenW} x ${screenH}`,
    `Canvas buffer: ${canvas.width} x ${canvas.height}`,
    `Pixel ratio: ${renderer.getPixelRatio()}`,
    `Camera aspect: ${camera.aspect.toFixed(6)}`,
    `Camera FOV: ${camera.fov}°`,
  ].join("\n");

  renderer.render(scene, camera);
}

animate();

window.addEventListener("resize", syncRendererAndCameraAspect);
