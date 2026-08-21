import { fovRadiusPixels } from "./math.js";

/**
 * Wire up the settings panel and 2D FOV overlay canvas.
 */
export class UI {
  constructor(aimAssist, camera) {
    this.aimAssist = aimAssist;
    this.camera = camera;

    this.fovCanvas = document.getElementById("fov-overlay");
    this.fovCtx = this.fovCanvas.getContext("2d");
    this.readout = document.getElementById("target-readout");

    this.bindSettings();
    this.resizeOverlay();
    window.addEventListener("resize", () => this.resizeOverlay());
  }

  bindSettings() {
    const bind = (id, apply) => {
      const el = document.getElementById(id);
      el.addEventListener("input", () => apply(el));
    };

    bind("aim-assist-enabled", (el) => {
      this.aimAssist.enabled = el.checked;
    });

    bind("fov", (el) => {
      this.aimAssist.fovDeg = parseFloat(el.value);
      document.getElementById("fov-value").textContent = el.value;
    });

    bind("smoothing", (el) => {
      this.aimAssist.smoothing = parseFloat(el.value);
      document.getElementById("smoothing-value").textContent = el.value;
    });

    bind("target-bone", (el) => {
      this.aimAssist.targetBone = el.value;
    });

    bind("max-range", (el) => {
      this.aimAssist.maxRange = parseFloat(el.value);
      document.getElementById("max-range-value").textContent = el.value;
    });

    bind("prediction-enabled", (el) => {
      this.aimAssist.predictionEnabled = el.checked;
    });

    bind("projectile-speed", (el) => {
      this.aimAssist.projectileSpeed = parseFloat(el.value);
      document.getElementById("projectile-speed-value").textContent = el.value;
    });

    bind("debug-ignore-range", (el) => {
      this.aimAssist.debugIgnoreRange = el.checked;
    });

    bind("debug-force-first", (el) => {
      this.aimAssist.debugForceFirstTarget = el.checked;
    });

    const linesToggle = document.getElementById("debug-aim-lines");
    this.drawAimLines = linesToggle.checked;
    linesToggle.addEventListener("input", () => {
      this.drawAimLines = linesToggle.checked;
    });

    document.getElementById("debug-log-pipeline").addEventListener("click", () => {
      this.aimAssist.logPipelineOnce();
    });
  }

  resizeOverlay() {
    this.fovCanvas.width = window.innerWidth;
    this.fovCanvas.height = window.innerHeight;
  }

  /** Draw the aim-assist FOV circle centered on the crosshair. */
  drawFovOverlay() {
    const ctx = this.fovCtx;
    const w = this.fovCanvas.width;
    const h = this.fovCanvas.height;
    ctx.clearRect(0, 0, w, h);

    if (!this.aimAssist.enabled) return;

    const radius = fovRadiusPixels(
      this.aimAssist.fovDeg,
      this.camera.fov,
      h
    );

    const cx = w / 2;
    const cy = h / 2;

    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.strokeStyle = this.aimAssist.selectedTarget
      ? "rgba(68, 255, 136, 0.85)"
      : "rgba(125, 211, 252, 0.55)";
    ctx.lineWidth = 2;
    ctx.stroke();

    // Faint fill when a target is locked
    if (this.aimAssist.selectedTarget) {
      ctx.fillStyle = "rgba(68, 255, 136, 0.06)";
      ctx.fill();
    }
  }

  updateReadout() {
    this.readout.textContent = this.aimAssist.debugInfo;
  }
}
