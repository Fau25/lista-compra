const VERSION = "mi-compra-v12";
const APP = ["./", "index.html", "manifest.json", "icono-180.png", "icono-192.png"];
const DATOS = ["catalogo.json"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(VERSION).then(c => c.addAll(APP.concat(DATOS))).then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== VERSION && k !== "mc-fotos").map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});
self.addEventListener("fetch", e => {
  const r = e.request, u = new URL(r.url);
  if (r.method !== "GET" || u.hostname.endsWith("script.google.com") || (u.hostname.endsWith("googleusercontent.com") && !u.hostname.startsWith("lh3."))) return;
  // Fotos de productos y fuentes: primero la copia guardada
  if (u.hostname.includes("imgix.net") || u.hostname.includes("fonts.g") || u.hostname.startsWith("lh3.") || u.pathname.includes("/fotos/")) {
    e.respondWith(caches.open("mc-fotos").then(async c => {
      const hit = await c.match(r); if (hit) return hit;
      try { const res = await fetch(r); if (res.ok || res.type === "opaque") c.put(r, res.clone()); return res; }
      catch (err) { return hit || Response.error(); }
    }));
    return;
  }
  if (u.origin !== location.origin) return;
  // App y datos: red con espera corta; si tarda o no hay conexión, copia guardada
  e.respondWith(caches.open(VERSION).then(async c => {
    const copia = await c.match(r, { ignoreSearch: true });
    const red = fetch(r).then(res => { if (res.ok) c.put(r, res.clone()); return res; }).catch(() => copia);
    if (!copia) return red;
    const lento = new Promise(ok => setTimeout(() => ok(copia), 800));
    return Promise.race([red, lento]);
  }));
});
