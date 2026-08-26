/**
 * Optional framework mode for aim-assist-sandbox.
 *
 * Load with: index.html?framework=1
 * Requires built packages:
 *   npm run build -w @aim-framework/core
 *   npm run build -w @aim-framework/browser-bridge
 *
 * This file is the ONLY change inside the legacy sandbox folder.
 */
import { AimAssistEngine, DEFAULT_AIM_CONFIG } from "../../aim-assist-framework/packages/core/dist/index.js";
import { ThreeSandboxAdapter } from "../../aim-assist-framework/packages/browser-bridge/dist/index.js";

export function createFrameworkBridge({ player, targets, camera }) {
  const config = { ...DEFAULT_AIM_CONFIG, localTeam: 0, teamCheck: false };
  const engine = new AimAssistEngine(config);
  const adapter = new ThreeSandboxAdapter(
    () => player,
    () => targets,
    camera,
    () => ({ width: window.innerWidth, height: window.innerHeight })
  );
  return { engine, adapter, config };
}
