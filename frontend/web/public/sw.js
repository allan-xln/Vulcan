const CACHE_NAME = "vulcan-shell-v1";
const SHELL_ASSETS = ["/", "/manifest.webmanifest", "/vulcan-symbol.svg", "/vulcan-logo.svg"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(SHELL_ASSETS))
      .then(() => self.skipWaiting())
      .catch(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (request.mode === "navigate") {
    event.respondWith(fetch(request).catch(() => caches.match("/")));
    return;
  }

  if (url.pathname.endsWith(".svg") || url.pathname === "/manifest.webmanifest") {
    event.respondWith(caches.match(request).then((cached) => cached || fetch(request)));
  }
});

self.addEventListener("message", (event) => {
  const payload = event.data || {};
  if (payload.type !== "VULCAN_SHOW_NOTIFICATION") return;

  const title = payload.title || "Vulcan";
  const options = {
    body: payload.body || "Novo alerta operacional.",
    tag: payload.tag || `vulcan-${Date.now()}`,
    renotify: Boolean(payload.renotify),
    icon: "/vulcan-symbol.svg",
    badge: "/vulcan-symbol.svg",
    requireInteraction: Boolean(payload.requireInteraction),
    silent: false,
    data: {
      url: payload.url || "/?view=notifications"
    },
    actions: [
      { action: "open", title: "Abrir Vulcan" },
      { action: "dismiss", title: "Dispensar" }
    ]
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  if (event.action === "dismiss") return;
  const targetUrl = event.notification.data?.url || "/?view=notifications";
  const absoluteUrl = new URL(targetUrl, self.location.origin).href;

  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((clients) => {
      for (const client of clients) {
        if ("focus" in client) {
          client.navigate(absoluteUrl);
          return client.focus();
        }
      }
      return self.clients.openWindow(absoluteUrl);
    })
  );
});
