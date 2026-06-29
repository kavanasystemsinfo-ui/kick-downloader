const CACHE = "kick-downloader-v1";
const STATIC = [
  "/",
  "/static/favicon.png",
  "/static/icon-192x192.png",
  "/static/icon-512x512.png",
  "/static/manifest.json"
];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(STATIC))
  );
  self.skipWaiting();
});

self.addEventListener("fetch", (e) => {
  e.respondWith(
    caches.match(e.request).then((r) => r || fetch(e.request))
  );
});