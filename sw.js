/* Cache-first service worker so the game shell and runtime images play offline
   once the app is installed. */

var CACHE = "ipcf-v12-multiplane";
var CORE = [
  ".",
  "index.html",
  "manifest.webmanifest",
  "images/bg0-far.webp",
  "images/bg0-mid.webp",
  "images/bg0-near.webp",
  "images/bg1-far.webp",
  "images/bg1-mid.webp",
  "images/bg1-near.webp",
  "images/bg2-far.webp",
  "images/bg2-mid.webp",
  "images/bg2-near.webp",
  "images/bg3-far.webp",
  "images/bg3-mid.webp",
  "images/bg3-near.webp",
  "images/bg4-far.webp",
  "images/bg4-mid.webp",
  "images/bg4-near.webp",
  "images/bg5-far.webp",
  "images/bg5-mid.webp",
  "images/bg5-near.webp",
  "images/bg7-far.webp",
  "images/bg7-mid.webp",
  "images/bg7-near.webp",
  "images/background.webp",
  "images/boss-card-cruiser-v5.webp",
  "images/boss-card-dreadnought-v5.webp",
  "images/boss-card-gun-deck-v5.webp",
  "images/boss3d-cruiser.webp",
  "images/boss3d-cruiser-damaged.webp",
  "images/boss3d-cruiser-wrecked.webp",
  "images/boss3d-dread.webp",
  "images/boss3d-dread-damaged.webp",
  "images/boss3d-dread-wrecked.webp",
  "images/boss3d-gundeck.webp",
  "images/boss3d-gundeck-damaged.webp",
  "images/boss3d-gundeck-wrecked.webp",
  "images/boss-damaged.webp",
  "images/boss-gantry-v4.webp",
  "images/boss-wrecked.webp",
  "images/boss.webp",
  "images/boss2.webp",
  "images/bullet.webp",
  "images/cloud_0.webp",
  "images/cloud_1.webp",
  "images/cloud_2.webp",
  "images/cloud_3.webp",
  "images/cloud_4.webp",
  "images/cloud_5.webp",
  "images/cloud_6.webp",
  "images/cloud_7.webp",
  "images/cloud_8.webp",
  "images/dino-plush.webp",
  "images/dreadnought-damaged.webp",
  "images/dreadnought-wrecked.webp",
  "images/fish_0.webp",
  "images/fish_1.webp",
  "images/fish_2.webp",
  "images/fish_3.webp",
  "images/fish_4.webp",
  "images/fish_5.webp",
  "images/fish_6.webp",
  "images/fish3d-v5_0.webp",
  "images/fish3d-v5_1.webp",
  "images/fish3d-v5_2.webp",
  "images/fish3d-v5_3.webp",
  "images/fish3d-v5_4.webp",
  "images/fish3d-v5_5.webp",
  "images/fish3d-v5_6.webp",
  "images/gun-deck-damaged.webp",
  "images/gun-deck-v4.webp",
  "images/gun-deck-wrecked.webp",
  "images/hazards-v3.webp",
  "images/hero-flight-strip-v5.webp",
  "images/hero-strip-3d-v1.webp",
  "images/hero-strip-3d-v6.webp",
  "images/hero-spin-v5.webp",
  "images/ring-3d-v1.webp",
  "images/heropenguin.webp",
  "images/icon-192.png",
  "images/icon-512.png",
  "images/icon-maskable-512.png",
  "images/medal-bronze.webp",
  "images/medal-gold.webp",
  "images/medal-silver.webp",
  "images/missions-v3.webp",
  "images/part_0.webp",
  "images/part_1.webp",
  "images/part_2.webp",
  "images/part_3.webp",
  "images/part_4.webp",
  "images/penguin_panic_0.webp",
  "images/penguin_panic_1.webp",
  "images/penguin_panic_2.webp",
  "images/plane-aurora-v5.webp",
  "images/plane-classic-v5.webp",
  "images/plane-midnight-v5.webp",
  "images/plane-sunset-v5.webp",
  "images/powerups-obstacle-v2.webp",
  "images/powerups-3d.webp",
  "images/rings.webp",
  "images/story-captain-albatross-v5.webp",
  "images/story-determined-v5.webp",
  "images/story-festival-v5.webp",
  "images/title-hero-v5.webp",
  "images/title-wordmark-v5.webp",
  "images/victory-penguin-v6.webp",
  "images/world-aurora-v5.webp",
  "images/world-dusty-hills-v5.webp",
  "images/world-outer-space-v5.webp",
  "images/world-snowy-peaks-v5.webp",
  "images/world-storm-v5.webp",
  "images/world-sunset-v5.webp"
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
    /* Runtime requests carry "?v=N" while precache stores bare paths, so the
       primary lookup ignores the query string (exact match kept as a fallback). */
    caches.match(e.request, { ignoreSearch: true }).then(function (hit) {
      return hit || caches.match(e.request).then(function (exact) {
        return exact || fetch(e.request).then(function (res) {
          if (res.status === 200 && (e.request.url.indexOf(self.location.origin) === 0)) {
            var copy = res.clone();
            /* store under the SAME bare key the precache uses, so versioned
               URLs don't accumulate duplicate cache entries */
            var bare = e.request.url.split("?")[0];
            caches.open(CACHE).then(function (c) { c.put(bare, copy); });
          }
          return res;
        });
      });
    }).catch(function () { return caches.match("index.html", { ignoreSearch: true }); })
  );
});
