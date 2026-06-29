const CACHE = "kickdl-pages-v1";
const STATIC = [
  "/kick-downloader/",
  "/kick-downloader/favicon.png",
  "/kick-downloader/icon-192x192.png",
  "/kick-downloader/icon-512x512.png",
  "/kick-downloader/manifest.json"
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