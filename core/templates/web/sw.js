{% load static %}
/* LaaCLab service worker: cache-first for the shell/static assets, stale-
   while-revalidate for API GETs, offline fallback for navigations. Served at
   the root scope (/sw.js) by core.views.service_worker so it can control the
   whole site. `{{ version }}` bumps the cache name to invalidate old caches
   on `activate`. */
const CACHE = "laaclab-{{ version }}";
const PRECACHE = [
  "/offline/",
  "{% static 'web/vendor/bootstrap/bootstrap.min.css' %}",
  "{% static 'web/vendor/bootstrap/bootstrap.bundle.min.js' %}",
  "{% static 'web/vendor/material-symbols/material-symbols.css' %}",
  "{% static 'web/vendor/material-symbols/material-symbols-outlined.woff2' %}",
  "{% static 'web/css/theme.css' %}",
  "{% static 'web/css/styles.css' %}",
  "{% static 'web/js/app.js' %}",
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(PRECACHE)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((keys) =>
    Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
  ).then(() => self.clients.claim()));
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET") return;                 // só GET
  if (url.pathname.startsWith("/api/")) {                  // APIs: stale-while-revalidate
    e.respondWith(caches.open(CACHE).then(async (c) => {
      const cached = await c.match(e.request);
      const net = fetch(e.request).then((res) => { c.put(e.request, res.clone()); return res; }).catch(() => cached);
      return cached || net;
    }));
    return;
  }
  if (PRECACHE.includes(url.pathname) || url.pathname.startsWith("/static/")) { // estáticos: cache-first
    e.respondWith(caches.match(e.request).then((r) => r || fetch(e.request)));
    return;
  }
  if (e.request.mode === "navigate") {                     // navegações: rede, fallback offline
    e.respondWith(fetch(e.request).catch(() => caches.match("/offline/")));
  }
});

/* Web Push: system notification on a push message, focus/open the target
   URL on click. `e.data` is attacker-controlled from the SW's point of view
   (any push service), so `.json()` is parsed defensively. */
self.addEventListener("push", (e) => {
  let d = {};
  try { d = e.data.json(); } catch (_) { /* no/invalid payload: fall back to defaults */ }
  e.waitUntil(self.registration.showNotification(d.title || "LaaCLab", {
    body: d.body || "",
    data: { url: d.url || "/" },
    icon: "{% static 'web/img/icon-192.png' %}",
    badge: "{% static 'web/img/icon-192.png' %}",
  }));
});

self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  e.waitUntil(clients.matchAll({ type: "window" }).then((cs) => {
    const url = e.notification.data.url || "/";
    for (const c of cs) if (c.url.includes(url) && "focus" in c) return c.focus();
    return clients.openWindow(url);
  }));
});

/* Logout hygiene: drop the cached /api/ responses (stale-while-revalidate
   cache above) so a shared machine never serves the previous user's data
   after signing out. Triggered by app.js / the allauth logout page via
   `navigator.serviceWorker.controller.postMessage({type: "clear-cache"})`.
   Only the /api/ entries are dropped — the precached shell/static assets
   are user-independent and stay cached. */
self.addEventListener("message", (e) => {
  if (!e.data || e.data.type !== "clear-cache") return;
  e.waitUntil(caches.open(CACHE).then((c) => c.keys().then((reqs) =>
    Promise.all(reqs.filter((r) => new URL(r.url).pathname.startsWith("/api/")).map((r) => c.delete(r)))
  )));
});
