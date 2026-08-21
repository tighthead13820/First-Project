# Vendored copy of the first-person aim-assist sandbox (JS / Three.js).

This folder is the browser sandbox from the aim-assist-sandbox branch.
The overlay does **not** execute these JS files directly.

Instead:

1. Click **Load sandbox** in the control panel to run
   `scripts/builtin_sandbox_aim.py` — a Python port of `js/aimAssist.js`.
2. Or click **Import folder…** and point at another aim-assist-sandbox
   tree; it will be copied here and the Python port will be activated.
3. Upload your own `.py` aim scripts with **Upload .py…**.

See the overlay README for the AimScript plugin contract.
