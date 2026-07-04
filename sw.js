/* Cache-first service worker so the game plays offline once installed.
   Core files are precached; every image is cached the first time it loads,
   so after one full play-through the whole game works with no internet. */

var CACHE = "ipcf-v1-pwa";
var CORE = [
  ".",
  "index.html",
  "manifest.webmanifest",
  "images/icon-192.png",
  "images/icon-512.png",
  "images/icon-maskable-512.png",
  "images/background.webp",
  "images/title-hero-v5.webp",
  "images/title-wordmark-v5.webp",
  "images/hero-flight-strip-v5.webp",
  "images/rings.webp"
];

self.addEventListener("install", function (e) {
  e.waitUntil(
    caches.open(CACHE).then(function (c) { return c.addAll(CORE); }).then(function () {
      return self.skipWaiting();
    })
  );
});

self.addEventListener("activate", function (e) {
  e.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.map(function (k) {
        if (k !== CACHE) return caches.delete(k);
      }));
    }).then(function () { return self.clients.claim(); })
  );
});

self.addEventListener("fetch", function (e) {
  if (e.request.method !== "GET") return;
  e.respondWith(
    caches.match(e.request).then(function (hit) {
      return hit || fetch(e.request).then(function (res) {
        if (res.status === 200 && (e.request.url.indexOf(self.location.origin) === 0)) {
          var copy = res.clone();
          caches.open(CACHE).then(function (c) { c.put(e.request, copy); });
        }
        return res;
      });
    }).catch(function () { return caches.match("index.html"); })
  );
});
