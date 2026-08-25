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
      // Sync initial DOM state into AimAssist (checkboxes / ranges).
      apply(el);
    };

    bind("aim-assist-enabled", (el) => {
      this.aimAssist.enabled = el.checked;
    });

    bind("snap-aim-debug", (el) => {
      this.aimAssist.snapAimDebug = el.checked;
    });

    bind("screen-wide-select", (el) => {
      this.aimAssist.screenWideSelect = el.checked;
    });

    bind("fov", (el) => {
      this.aimAssist.fovDeg = parseFloat(el.value);
      document.getElementById("fov-value").textContent = el.value;
    });

    bind("response-speed", (el) => {
      this.aimAssist.responseSpeed = parseFloat(el.value);
      document.getElementById("response-speed-value").textContent = el.value;
    });

    // Smoothing is legacy-only: do not auto-apply on init (would overwrite responseSpeed).
    const smoothingEl = document.getElementById("smoothing");
    smoothingEl.addEventListener("input", () => {
      this.aimAssist.smoothing = parseFloat(smoothingEl.value);
      document.getElementById("smoothing-value").textContent = smoothingEl.value;
      const mapped = 1 + this.aimAssist.smoothing * 39;
      this.aimAssist.responseSpeed = mapped;
      const rs = document.getElementById("response-speed");
      rs.value = String(mapped);
      document.getElementById("response-speed-value").textContent =
        mapped.toFixed(1);
    });
    document.getElementById("smoothing-value").textContent = smoothingEl.value;

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
    
    // Initialize snap-aim state from checkbox
    const snapCheckbox = document.getElementById("snap-aim-debug");
    this.aimAssist.snapAimDebug = snapCheckbox.checked;
  }

  resizeOverlay() {
    this.fovCanvas.width = window.innerWidth;
    this.fovCanvas.height = window.innerHeight;
  }

  /** Draw aim-assist region: full viewport when screen-wide, else FOV circle. */
  drawFovOverlay() {
    const ctx = this.fovCtx;
    const w = this.fovCanvas.width;
    const h = this.fovCanvas.height;
    ctx.clearRect(0, 0, w, h);

    if (!this.aimAssist.enabled) return;

    const cx = w / 2;
    const cy = h / 2;
    const locked =
      Boolean(this.aimAssist.selectedTarget) &&
      Boolean(this.aimAssist.tracking?.tracking);
    const stroke = locked
      ? "rgba(68, 255, 136, 0.85)"
      : "rgba(125, 211, 252, 0.55)";
    const fill = "rgba(68, 255, 136, 0.06)";

    if (this.aimAssist.screenWideSelect) {
      const inset = 2;
      ctx.strokeStyle = stroke;
      ctx.lineWidth = 2;
      ctx.strokeRect(inset, inset, w - inset * 2, h - inset * 2);
      if (locked) {
        ctx.fillStyle = fill;
        ctx.fillRect(inset, inset, w - inset * 2, h - inset * 2);
      }
      return;
    }

    const radius = fovRadiusPixels(
      this.aimAssist.getAcquireFovDeg(),
      this.camera.fov,
      h
    );

    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.strokeStyle = stroke;
    ctx.lineWidth = 2;
    ctx.stroke();

    if (locked) {
      ctx.fillStyle = fill;
      ctx.fill();
    }
  }

  updateReadout() {
    this.readout.textContent = this.aimAssist.debugInfo;
  }
}
