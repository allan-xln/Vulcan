import { describe, expect, it } from "vitest";

import {
  INFRASTRUCTURE_SCENES,
  WORKFORCE_SCENES,
  commandCenterConfig
} from "./config";
import type { WallboardProfile } from "./types";

function profile(config: Record<string, unknown>): WallboardProfile {
  return {
    id: "profile-1",
    name: "Wallboard de teste",
    wallboardType: "workforce",
    enabled: true,
    refreshSeconds: 30,
    fullscreen: true,
    nightMode: true,
    burnInPrevention: true,
    showClock: true,
    showLastUpdate: true,
    showConnectionStatus: true,
    config,
    playlists: []
  };
}

describe("commandCenterConfig", () => {
  it("uses the complete safe scene set when no explicit order exists", () => {
    expect(commandCenterConfig(null, "workforce").sceneSequence).toEqual(
      [...WORKFORCE_SCENES]
    );
    expect(commandCenterConfig(null, "infrastructure").sceneSequence).toEqual(
      [...INFRASTRUCTURE_SCENES]
    );
  });

  it("keeps only supported scenes and bounds performance settings", () => {
    const config = commandCenterConfig(
      profile({
        sceneSequence: ["topology", "command", "invented", 42],
        quality: "4k",
        targetFps: 12,
        visualIntensity: 500,
        openingDurationSeconds: 99,
        controlsAutoHideSeconds: 0,
        audioEnabled: true
      }),
      "infrastructure"
    );

    expect(config.sceneSequence).toEqual(["topology", "command"]);
    expect(config.quality).toBe("4k");
    expect(config.targetFps).toBe(30);
    expect(config.visualIntensity).toBe(100);
    expect(config.openingDurationSeconds).toBe(5);
    expect(config.controlsAutoHideSeconds).toBe(2);
    expect(config.audioEnabled).toBe(false);
  });

  it("falls back to safe defaults for invalid profile values", () => {
    const config = commandCenterConfig(
      profile({
        quality: "ultra",
        motionIntensity: "chaotic",
        transitionStyle: "explode",
        fallbackMode: "force-webgl"
      }),
      "workforce"
    );

    expect(config.quality).toBe("auto");
    expect(config.motionIntensity).toBe("balanced");
    expect(config.transitionStyle).toBe("scan");
    expect(config.fallbackMode).toBe("automatic");
  });
});
