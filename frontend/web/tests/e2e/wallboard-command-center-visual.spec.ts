import { expect, Page, test } from "@playwright/test";

const tenantId = "00000000-0000-0000-0000-000000000301";
const siteId = "00000000-0000-0000-0000-000000000401";
let snapshotMode: "normal" | "critical" | "empty" = "normal";
let snapshotUnavailable = false;
let openingEnabled = false;

const profiles = ["workforce", "infrastructure"].map((type, profileIndex) => ({
  id: `00000000-0000-0000-0000-0000000005${profileIndex + 1}`,
  tenantId,
  name: type === "workforce" ? "Workforce TV" : "Infrastructure TV",
  wallboardType: type,
  enabled: true,
  refreshSeconds: 30,
  fullscreen: true,
  nightMode: true,
  burnInPrevention: true,
  showClock: true,
  showLastUpdate: true,
  showConnectionStatus: true,
  config: {
    quality: "low",
    motionIntensity: "minimal",
    openingEnabled: false,
    controlsAutoHideSeconds: 2,
    sceneSequence: ["command"]
  },
  playlists: [
    {
      id: `00000000-0000-0000-0000-0000000006${profileIndex + 1}`,
      name: "Visão geral",
      enabled: true,
      rotationEnabled: false,
      defaultDurationSeconds: 30,
      transition: "fade",
      schedule: {},
      alertPriorityEnabled: true,
      autoReturnSeconds: 60,
      items: [
        {
          id: `00000000-0000-0000-0000-0000000007${profileIndex + 1}`,
          siteId: null,
          siteName: null,
          panelKey: "overview",
          title: "Visão geral",
          position: 0,
          durationSeconds: 30,
          enabled: true,
          config: {}
        }
      ]
    }
  ]
}));

test.beforeEach(async ({ page }) => {
  snapshotMode = "normal";
  snapshotUnavailable = false;
  openingEnabled = false;
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.addInitScript(() => {
    const fixedTime = new Date("2026-07-30T16:00:00Z").getTime();
    const NativeDate = Date;
    class FixedDate extends NativeDate {
      constructor(...args: ConstructorParameters<typeof Date>) {
        super(args.length ? (args[0] as string | number) : fixedTime);
      }
      static now() {
        return fixedTime;
      }
    }
    window.Date = FixedDate as DateConstructor;

    const nativeFetch = window.fetch.bind(window);
    window.fetch = (input, init) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
      if (url.includes("/realtime/events")) {
        const stream = new ReadableStream({
          start(controller) {
            controller.enqueue(new TextEncoder().encode("data: {\"type\":\"ready\"}\n\n"));
          }
        });
        return Promise.resolve(
          new Response(stream, {
            status: 200,
            headers: { "Content-Type": "text/event-stream" }
          })
        );
      }
      return nativeFetch(input, init);
    };
  });

  await page.route("**/auth/login", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        accessToken: "visual-read-only-token",
        tokenType: "bearer",
        user: { id: "visual", name: "TV Visual", role: "read_only", tenantId }
      })
    })
  );
  await page.route("**/wallboards/profiles", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(
        profiles.map((profile) => ({
          ...profile,
          config: {
            ...profile.config,
            openingEnabled,
            openingMode: "reduced",
            openingDurationSeconds: 1.5
          }
        }))
      )
    })
  );
  await page.route("**/wallboards/snapshot?**", (route) => {
    if (snapshotUnavailable) {
      return route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({ detail: "indisponibilidade controlada" })
      });
    }
    const type = new URL(route.request().url()).searchParams.get("type") ?? "workforce";
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(snapshot(type, snapshotMode))
    });
  });
  await page.route("**/healthz", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        status: "ok",
        service: "vulcan-api",
        timestamp: "2026-07-30T16:00:00Z",
        dataOrigin: "real",
        checks: [
          { name: "database", status: "ok", detail: "PostgreSQL pronto", latencyMs: 2.4 },
          { name: "schema", status: "ok", detail: "Migrations atuais", latencyMs: 0.8 }
        ]
      })
    })
  );
  await page.route("**/version", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        product: "Vulcan",
        service: "vulcan-api",
        version: "0.5.0",
        commit: "visualtest",
        build: "visual-regression",
        eventSchemaVersion: "2026-07-vulcan-event.v1"
      })
    })
  );
});

test("matches the reviewed Workforce and Infrastructure TV compositions", async ({ page }) => {
  await authenticate(page, "/wallboard/workforce?scene=command");

  for (const resolution of [
    { name: "1080p", width: 1920, height: 1080 },
    { name: "1440p", width: 2560, height: 1440 },
    { name: "4k", width: 3840, height: 2160 }
  ]) {
    await page.setViewportSize(resolution);
    await expect(page.locator("[data-command-center='workforce']")).toBeVisible();
    await expect(page).toHaveScreenshot(`workforce-${resolution.name}.png`, {
      animations: "disabled",
      caret: "hide",
      maxDiffPixelRatio: 0.001
    });
  }

  await page.goto("/wallboard/infra?scene=command", { waitUntil: "domcontentloaded" });
  for (const resolution of [
    { name: "1080p", width: 1920, height: 1080 },
    { name: "1440p", width: 2560, height: 1440 },
    { name: "4k", width: 3840, height: 2160 }
  ]) {
    await page.setViewportSize(resolution);
    await expect(page.locator("[data-command-center='infrastructure']")).toBeVisible();
    await expect(page).toHaveScreenshot(`infrastructure-${resolution.name}.png`, {
      animations: "disabled",
      caret: "hide",
      maxDiffPixelRatio: 0.001
    });
  }
});

test("covers critical takeover, honest empty state and session reload", async ({ page }) => {
  snapshotMode = "critical";
  await authenticate(page, "/wallboard/infra?scene=command");
  await expect(page.getByText(/Falha crítica de conectividade/)).toBeVisible();
  await expect(page).toHaveScreenshot("critical-takeover-1080p.png", {
    animations: "disabled",
    caret: "hide",
    maxDiffPixelRatio: 0.001
  });

  snapshotMode = "empty";
  await page.reload({ waitUntil: "domcontentloaded" });
  await expect(page.getByLabel("Usuário")).not.toBeVisible();
  await expect(page.getByText("Sem coleta", { exact: true }).first()).toBeVisible();
  await expect(page.locator("[data-quality='low']")).toBeVisible();
});

test("requests fullscreen and reconnects without losing the wallboard session", async ({
  context,
  page
}) => {
  await authenticate(page, "/wallboard/workforce?scene=command");

  await page.evaluate(() => {
    const state = window as Window & { __vulcanFullscreenRequested?: boolean };
    state.__vulcanFullscreenRequested = false;
    Object.defineProperty(document.documentElement, "requestFullscreen", {
      configurable: true,
      value: () => {
        state.__vulcanFullscreenRequested = true;
        return Promise.resolve();
      }
    });
  });
  await page.getByRole("button", { name: "Tela cheia" }).click();
  await expect
    .poll(() =>
      page.evaluate(
        () => (window as Window & { __vulcanFullscreenRequested?: boolean }).__vulcanFullscreenRequested
      )
    )
    .toBe(true);

  await context.setOffline(true);
  await expect(page.locator("[data-command-center]")).toHaveAttribute("data-connection", "offline");

  await context.setOffline(false);
  await expect(page.locator("[data-command-center]")).not.toHaveAttribute(
    "data-connection",
    "offline"
  );
  await expect(page.getByLabel("Usuário")).not.toBeVisible();
});

test("shows the cinematic opening only once in the same session", async ({ page }) => {
  openingEnabled = true;
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await authenticate(page, "/wallboard/workforce?scene=command");

  await expect(page.getByLabel("Inicializando Vulcan Command Center")).toBeVisible();

  await page.reload({ waitUntil: "domcontentloaded" });
  await expect(page.locator("[data-command-center='workforce']")).toBeVisible();
  await expect(page.getByLabel("Inicializando Vulcan Command Center")).toHaveCount(0);
  await expect(page.getByLabel("Usuário")).not.toBeVisible();
});

test("keeps the last valid snapshot identified as stale and recovers", async ({
  context,
  page
}) => {
  await authenticate(page, "/wallboard/infra?scene=command");
  snapshotUnavailable = true;

  await context.setOffline(true);
  await context.setOffline(false);
  await expect(page.locator("[data-command-center]")).toHaveAttribute(
    "data-connection",
    "stale",
    { timeout: 20_000 }
  );
  await expect(page.getByText(/Exibindo a última informação válida/)).toBeVisible();
  await expect(page.getByText("ERS / VULCAN", { exact: true })).toBeVisible();

  snapshotUnavailable = false;
  await context.setOffline(true);
  await context.setOffline(false);
  await expect(page.locator("[data-command-center]")).not.toHaveAttribute(
    "data-connection",
    "stale",
    { timeout: 15_000 }
  );
  await expect(page.getByLabel("Usuário")).not.toBeVisible();
});

async function authenticate(page: Page, path: string) {
  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.goto(path, { waitUntil: "domcontentloaded" });
  await page.getByLabel("Usuário").fill("visual");
  await page.getByLabel("Senha").fill("visual");
  await page.getByRole("button", { name: "Acessar painel" }).click();
  await page.locator("[data-command-center]").waitFor();
  await page.waitForTimeout(100);
}

function snapshot(type: string, mode: "normal" | "critical" | "empty") {
  const empty = mode === "empty";
  return {
    tenantId,
    wallboardType: type,
    dataOrigin: "real",
    generatedAt: "2026-07-30T16:00:00Z",
    siteId: null,
    siteName: null,
    kpis: empty
      ? {
          activePeople: 0,
          events24h: 0,
          onlineAgents: 0,
          delayedAgents: 0,
          offlineAgents: 0,
          assets: 0,
          onlineAssets: 0,
          degradedAssets: 0,
          offlineAssets: 0,
          unknownAssets: 0,
          availability: null
        }
      : {
          activePeople: 42,
          events24h: 7421,
          onlineAgents: 118,
          delayedAgents: 3,
          offlineAgents: 2,
          assets: 124,
          onlineAssets: 113,
          degradedAssets: 4,
          offlineAssets: 3,
          unknownAssets: 4,
          availability: 95.8,
          servers: 12,
          virtualMachines: 28,
          switches: 14,
          accessPoints: 23,
          printers: 17
        },
    sites: empty
      ? []
      : [
          { id: siteId, code: "SJP", name: "Matriz", active_people: 30, assets: 88 },
          { id: "site-2", code: "PNG", name: "Filial Portuária", active_people: 12, assets: 36 }
        ],
    statusGroups: [],
    activity: [],
    alerts:
      mode === "critical"
        ? [
            {
              id: "critical-visual",
              title: "Falha crítica de conectividade",
              severity: "critical",
              status: "open",
              impact: "A filial portuária perdeu acesso aos serviços operacionais.",
              last_occurred_at: "2026-07-30T15:59:00Z"
            }
          ]
        : [],
    integrations: empty
      ? []
      : [
          {
            adapter_type: "unifi",
            name: "UniFi Controller",
            status: "ready",
            last_success_at: "2026-07-30T15:58:00Z"
          },
          {
            adapter_type: "proxmox",
            name: "Proxmox Cluster",
            status: "ready",
            last_success_at: "2026-07-30T15:57:00Z"
          }
        ],
    applications: [],
    agents: [],
    topologyNodes: empty
      ? []
      : [
          node("firewall", "Firewall Matriz", "firewall", "online"),
          node("switch", "Switch Core", "switch", "online"),
          node("server", "Servidor Operacional", "server", "degraded"),
          node("printer", "Impressora Expedição", "printer", "offline")
        ],
    topologyLinks: empty
      ? []
      : [
          link("firewall", "switch"),
          link("switch", "server"),
          link("switch", "printer")
        ]
  };
}

function node(id: string, name: string, assetType: string, status: string) {
  return {
    id,
    siteId,
    siteName: "Matriz",
    name,
    assetType,
    status,
    criticality: "high",
    source: "visual-test",
    ipAddress: null,
    lastSeenAt: "2026-07-30T16:00:00Z",
    details: {}
  };
}

function link(sourceAssetId: string, targetAssetId: string) {
  return {
    id: `${sourceAssetId}-${targetAssetId}`,
    sourceAssetId,
    targetAssetId,
    relationshipType: "uplink",
    status: "active",
    confidence: 1,
    source: "visual-test",
    observedAt: "2026-07-30T16:00:00Z",
    details: {}
  };
}
