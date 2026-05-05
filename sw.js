const CACHE_NAME = 'carbon-tree-v1';
const urlsToCache = [
  './index.html',
  './manifest.json'
];

// 安裝 Service Worker 並快取檔案
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
  );
});

// 攔截網路請求，若有快取就讀取快取，沒有就透過網路抓取
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => response || fetch(event.request))
  );
});