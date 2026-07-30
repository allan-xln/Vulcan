import { chromium } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

const baseUrl = (process.env.VULCAN_SOAK_BASE_URL ?? "http://127.0.0.1:3000").replace(/\/$/, "");
const username = process.env.VULCAN_SOAK_USERNAME;
const password = process.env.VULCAN_SOAK_PASSWORD;
const durationMinutes = boundedNumber(process.env.VULCAN_SOAK_MINUTES, 180, 1, 1_440);
const sampleSeconds = boundedNumber(process.env.VULCAN_SOAK_SAMPLE_SECONDS, 60, 5, 3_600);
const routeSwitchSeconds = boundedNumber(
  process.env.VULCAN_SOAK_ROUTE_SWITCH_SECONDS,
  600,
  30,
  7_200
);
const disconnectSeconds = boundedNumber(
  process.env.VULCAN_SOAK_DISCONNECT_SECONDS,
  1_200,
  60,
  14_400
);
const outputDirectory =
  process.env.VULCAN_SOAK_OUTPUT_DIR ??
  path.join("/tmp", `vulcan-wallboard-soak-${new Date().toISOString().replaceAll(/[:.]/g, "-")}`);

if (!username || !password) {
  throw new Error("Defina VULCAN_SOAK_USERNAME e VULCAN_SOAK_PASSWORD.");
}

await mkdir(outputDirectory, { recursive: true, mode: 0o700 });
const browser = await chromium.launch({
  headless: true,
  args: [
    "--enable-precise-memory-info",
    "--use-angle=swiftshader",
    "--enable-unsafe-swiftshader"
  ]
});
const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
const page = await context.newPage();
const client = await context.newCDPSession(page);
await client.send("Performance.enable");
const consoleErrors = [];
const pageErrors = [];
let sseConnections = 0;
let sseFailures = 0;
let forcedDisconnects = 0;

page.on("console", (message) => {
  if (message.type() === "error") consoleErrors.push(message.text());
});
page.on("pageerror", (error) => pageErrors.push(error.message));
page.on("request", (request) => {
  if (request.url().includes("/realtime/events")) sseConnections += 1;
});
page.on("requestfailed", (request) => {
  if (request.url().includes("/realtime/events")) sseFailures += 1;
});

await page.addInitScript(() => {
  const state = {
    listeners: 0,
    timeouts: 0,
    intervals: 0,
    animationFrames: 0
  };
  Object.defineProperty(window, "__vulcanSoak", { value: state });

  const listenerRegistry = new WeakMap();
  const originalAdd = EventTarget.prototype.addEventListener;
  const originalRemove = EventTarget.prototype.removeEventListener;
  EventTarget.prototype.addEventListener = function (type, listener, options) {
    if (listener) {
      let byType = listenerRegistry.get(this);
      if (!byType) {
        byType = new Map();
        listenerRegistry.set(this, byType);
      }
      let listeners = byType.get(type);
      if (!listeners) {
        listeners = new Set();
        byType.set(type, listeners);
      }
      if (!listeners.has(listener)) {
        listeners.add(listener);
        state.listeners += 1;
      }
    }
    return originalAdd.call(this, type, listener, options);
  };
  EventTarget.prototype.removeEventListener = function (type, listener, options) {
    const listeners = listenerRegistry.get(this)?.get(type);
    if (listener && listeners?.delete(listener)) state.listeners = Math.max(0, state.listeners - 1);
    return originalRemove.call(this, type, listener, options);
  };

  const originalSetTimeout = window.setTimeout.bind(window);
  const originalClearTimeout = window.clearTimeout.bind(window);
  const activeTimeouts = new Set();
  window.setTimeout = (handler, timeout, ...args) => {
    let id;
    const wrapped = (...callbackArgs) => {
      activeTimeouts.delete(id);
      state.timeouts = activeTimeouts.size;
      if (typeof handler === "function") return handler(...callbackArgs);
      return undefined;
    };
    id = originalSetTimeout(wrapped, timeout, ...args);
    activeTimeouts.add(id);
    state.timeouts = activeTimeouts.size;
    return id;
  };
  window.clearTimeout = (id) => {
    activeTimeouts.delete(id);
    state.timeouts = activeTimeouts.size;
    return originalClearTimeout(id);
  };

  const originalSetInterval = window.setInterval.bind(window);
  const originalClearInterval = window.clearInterval.bind(window);
  const activeIntervals = new Set();
  window.setInterval = (handler, timeout, ...args) => {
    const id = originalSetInterval(handler, timeout, ...args);
    activeIntervals.add(id);
    state.intervals = activeIntervals.size;
    return id;
  };
  window.clearInterval = (id) => {
    activeIntervals.delete(id);
    state.intervals = activeIntervals.size;
    return originalClearInterval(id);
  };

  const originalRequestAnimationFrame = window.requestAnimationFrame.bind(window);
  const originalCancelAnimationFrame = window.cancelAnimationFrame.bind(window);
  const activeFrames = new Set();
  window.requestAnimationFrame = (callback) => {
    let id;
    id = originalRequestAnimationFrame((time) => {
      activeFrames.delete(id);
      state.animationFrames = activeFrames.size;
      callback(time);
    });
    activeFrames.add(id);
    state.animationFrames = activeFrames.size;
    return id;
  };
  window.cancelAnimationFrame = (id) => {
    activeFrames.delete(id);
    state.animationFrames = activeFrames.size;
    return originalCancelAnimationFrame(id);
  };
});

const startedAt = Date.now();
const deadline = startedAt + durationMinutes * 60_000;
let nextRouteSwitch = startedAt + routeSwitchSeconds * 1_000;
let nextDisconnect = startedAt + disconnectSeconds * 1_000;
let activeType = "workforce";
const samples = [];

try {
  await page.goto(`${baseUrl}/wallboard/workforce`, {
    waitUntil: "domcontentloaded",
    timeout: 60_000
  });
  await page.getByLabel("Usuário").fill(username);
  await page.getByLabel("Senha").fill(password);
  await page.getByRole("button", { name: "Acessar painel" }).click();
  await page.locator("[data-command-center='workforce']").waitFor({ timeout: 60_000 });
  await page.waitForTimeout(3_000);
  await page.screenshot({ path: path.join(outputDirectory, "initial.png") });

  while (Date.now() < deadline) {
    const now = Date.now();
    if (now >= nextRouteSwitch) {
      activeType = activeType === "workforce" ? "infra" : "workforce";
      await page.goto(`${baseUrl}/wallboard/${activeType}`, {
        waitUntil: "domcontentloaded",
        timeout: 60_000
      });
      await page.locator("[data-command-center]").waitFor({ timeout: 60_000 });
      nextRouteSwitch = now + routeSwitchSeconds * 1_000;
    }
    if (now >= nextDisconnect) {
      await context.setOffline(true);
      await page.waitForTimeout(8_000);
      await context.setOffline(false);
      forcedDisconnects += 1;
      nextDisconnect = now + disconnectSeconds * 1_000;
    }

    const performanceMetrics = await client.send("Performance.getMetrics");
    const metric = (name) =>
      performanceMetrics.metrics.find((candidate) => candidate.name === name)?.value ?? null;
    const sample = await page.evaluate(() => {
      const root = document.querySelector("[data-command-center]");
      const soak = window.__vulcanSoak ?? {};
      const memory = performance.memory;
      return {
        at: new Date().toISOString(),
        heapBytes: memory?.usedJSHeapSize ?? null,
        heapLimitBytes: memory?.jsHeapSizeLimit ?? null,
        listeners: soak.listeners ?? null,
        timeouts: soak.timeouts ?? null,
        intervals: soak.intervals ?? null,
        animationFrames: soak.animationFrames ?? null,
        canvases: document.querySelectorAll("canvas").length,
        webglCanvases: document.querySelectorAll(".command-topology-stage canvas").length,
        connection: root?.getAttribute("data-connection") ?? null,
        quality: root?.getAttribute("data-quality") ?? null,
        fps: Number(root?.getAttribute("data-fps")) || null,
        scene: root?.getAttribute("data-scene") ?? null,
        wallboard: root?.getAttribute("data-command-center") ?? null,
        panel: new URL(window.location.href).searchParams.get("panel") ?? "overview",
        criticalTakeover: Boolean(document.querySelector(".command-critical-takeover"))
      };
    });
    samples.push({
      ...sample,
      taskDurationSeconds: metric("TaskDuration"),
      documents: metric("Documents"),
      nodes: metric("Nodes"),
      jsEventListeners: metric("JSEventListeners")
    });
    await page.waitForTimeout(sampleSeconds * 1_000);
  }

  await page.screenshot({ path: path.join(outputDirectory, "final.png") });
} finally {
  const completedAt = Date.now();
  const heapSamples = samples.map((sample) => sample.heapBytes).filter(Number.isFinite);
  const fpsSamples = samples.map((sample) => sample.fps).filter(Number.isFinite);
  const taskSamples = samples
    .map((sample) => sample.taskDurationSeconds)
    .filter(Number.isFinite);
  const observedSeconds = Math.max(1, (completedAt - startedAt) / 1_000);
  const report = {
    baseUrl,
    startedAt: new Date(startedAt).toISOString(),
    completedAt: new Date(completedAt).toISOString(),
    requestedMinutes: durationMinutes,
    observedMinutes: Number(((completedAt - startedAt) / 60_000).toFixed(2)),
    samples: samples.length,
    heap: {
      initialBytes: heapSamples[0] ?? null,
      finalBytes: heapSamples.at(-1) ?? null,
      peakBytes: heapSamples.length ? Math.max(...heapSamples) : null
    },
    fps: {
      minimum: fpsSamples.length ? Math.min(...fpsSamples) : null,
      average: fpsSamples.length
        ? Number((fpsSamples.reduce((sum, value) => sum + value, 0) / fpsSamples.length).toFixed(1))
        : null,
      maximum: fpsSamples.length ? Math.max(...fpsSamples) : null
    },
    cpu: {
      approximatePagePercent:
        taskSamples.length > 1
          ? Number(
              (
                ((taskSamples.at(-1) - taskSamples[0]) / observedSeconds) *
                100
              ).toFixed(2)
            )
          : null
    },
    stability: {
      listeners: summarize(samples, "listeners"),
      timeouts: summarize(samples, "timeouts"),
      intervals: summarize(samples, "intervals"),
      animationFrames: summarize(samples, "animationFrames"),
      canvases: summarize(samples, "canvases"),
      webglCanvases: summarize(samples, "webglCanvases"),
      domNodes: summarize(samples, "nodes"),
      browserEventListeners: summarize(samples, "jsEventListeners"),
      qualities: unique(samples, "quality"),
      connections: unique(samples, "connection"),
      wallboards: unique(samples, "wallboard"),
      scenes: unique(samples, "scene"),
      panels: unique(samples, "panel"),
      criticalTakeoverStates: [...new Set(samples.map((sample) => sample.criticalTakeover))]
    },
    sse: {
      connections: sseConnections,
      requestFailures: sseFailures,
      forcedDisconnects
    },
    consoleErrors: [...new Set(consoleErrors)],
    pageErrors: [...new Set(pageErrors)],
    samplesDetail: samples
  };
  await writeFile(
    path.join(outputDirectory, "report.json"),
    `${JSON.stringify(report, null, 2)}\n`,
    { mode: 0o600 }
  );
  console.log(JSON.stringify({ ...report, samplesDetail: undefined, outputDirectory }, null, 2));
  await browser.close();
}

function boundedNumber(raw, fallback, minimum, maximum) {
  const value = Number(raw);
  if (!Number.isFinite(value)) return fallback;
  return Math.min(maximum, Math.max(minimum, value));
}

function summarize(samples, key) {
  const values = samples.map((sample) => sample[key]).filter(Number.isFinite);
  return {
    initial: values[0] ?? null,
    final: values.at(-1) ?? null,
    minimum: values.length ? Math.min(...values) : null,
    maximum: values.length ? Math.max(...values) : null
  };
}

function unique(samples, key) {
  return [...new Set(samples.map((sample) => sample[key]).filter(Boolean))].sort();
}
