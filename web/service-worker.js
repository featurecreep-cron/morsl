const CACHE_NAME = 'morsl-v1';
const ADMIN_PATHS = new Set([
  '/admin', '/admin.html', '/js/admin.js', '/js/icon-picker.js', '/css/admin.css',
]);
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/js/app.js',
  '/js/shared.js',
  '/js/icons.js',
  '/js/theme-registry.js',
  '/css/styles.css',
  '/manifest.json',
];

// Install: pre-cache static assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

// Activate: clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Fetch: network-first for static assets, never cache API responses
self.addEventListener('fetch', (event) => {
  // Only handle http/https requests (ignore chrome-extension://, etc.)
  if (!event.request.url.startsWith('http')) return;

  const url = new URL(event.request.url);

  // Never cache API responses — they must always be fresh
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(fetch(event.request));
    return;
  }

  // Never cache admin assets — they're not needed for offline use
  if (ADMIN_PATHS.has(url.pathname)) {
    event.respondWith(fetch(event.request));
    return;
  }

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        // Only cache static assets for offline fallback
        if (response.ok && response.type === 'basic') {
          const cacheable = /\.(js|css|html|png|svg|ico|woff2?)$/.test(url.pathname)
            || url.pathname === '/' || url.pathname === '/manifest.json';
          if (cacheable) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
          }
        }
        return response;
      })
      .catch(() => caches.match(event.request))
  );
});
