/**
 * Service Worker for GRACE
 * ========================
 * Enables offline functionality, caching, and background sync.
 */

const CACHE_NAME = 'grace-cache-v1';
const STATIC_CACHE = 'grace-static-v1';
const DYNAMIC_CACHE = 'grace-dynamic-v1';
const API_CACHE = 'grace-api-v1';

// Static assets to cache on install
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/favicon.ico',
];

// API routes to cache
const CACHEABLE_API_ROUTES = [
  '/api/models',
  '/api/health',
  '/api/system/health',
];

// =============================================================================
// Install Event
// =============================================================================

self.addEventListener('install', (event) => {
  console.log('[SW] Installing service worker...');

  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => {
        console.log('[SW] Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => self.skipWaiting())
  );
});

// =============================================================================
// Activate Event
// =============================================================================

self.addEventListener('activate', (event) => {
  console.log('[SW] Activating service worker...');

  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((name) => {
              // Delete old caches
              return name.startsWith('grace-') &&
                     name !== STATIC_CACHE &&
                     name !== DYNAMIC_CACHE &&
                     name !== API_CACHE;
            })
            .map((name) => {
              console.log('[SW] Deleting old cache:', name);
              return caches.delete(name);
            })
        );
      })
      .then(() => self.clients.claim())
  );
});

// =============================================================================
// Fetch Event
// =============================================================================

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // Skip WebSocket connections
  if (url.protocol === 'ws:' || url.protocol === 'wss:') {
    return;
  }

  // Handle API requests
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(handleApiRequest(request));
    return;
  }

  // Handle static assets
  if (isStaticAsset(url.pathname)) {
    event.respondWith(handleStaticRequest(request));
    return;
  }

  // Handle navigation requests (SPA)
  if (request.mode === 'navigate') {
    event.respondWith(handleNavigationRequest(request));
    return;
  }

  // Default: Network first, cache fallback
  event.respondWith(networkFirst(request, DYNAMIC_CACHE));
});

// =============================================================================
// Request Handlers
// =============================================================================

async function handleApiRequest(request) {
  const url = new URL(request.url);

  // Check if this API route is cacheable
  const isCacheable = CACHEABLE_API_ROUTES.some((route) =>
    url.pathname.startsWith(route)
  );

  if (isCacheable) {
    // Stale-while-revalidate for cacheable APIs
    return staleWhileRevalidate(request, API_CACHE, 300); // 5 min max age
  }

  // Network only for other API requests
  try {
    return await fetch(request);
  } catch (error) {
    return new Response(
      JSON.stringify({ error: 'Network unavailable', offline: true }),
      {
        status: 503,
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
}

async function handleStaticRequest(request) {
  // Cache first for static assets
  return cacheFirst(request, STATIC_CACHE);
}

async function handleNavigationRequest(request) {
  try {
    // Try network first
    const response = await fetch(request);

    // Cache successful responses
    if (response.ok) {
      const cache = await caches.open(DYNAMIC_CACHE);
      cache.put(request, response.clone());
    }

    return response;
  } catch (error) {
    // Fallback to cached index.html for SPA
    const cache = await caches.open(STATIC_CACHE);
    const cached = await cache.match('/index.html');

    if (cached) {
      return cached;
    }

    // Offline page fallback
    return new Response(
      `<!DOCTYPE html>
      <html>
        <head>
          <title>GRACE - Offline</title>
          <style>
            body { font-family: system-ui; text-align: center; padding: 50px; }
            h1 { color: #333; }
            p { color: #666; }
            button { padding: 10px 20px; cursor: pointer; }
          </style>
        </head>
        <body>
          <h1>You're Offline</h1>
          <p>GRACE requires an internet connection to function.</p>
          <button onclick="location.reload()">Retry</button>
        </body>
      </html>`,
      { headers: { 'Content-Type': 'text/html' } }
    );
  }
}

// =============================================================================
// Caching Strategies
// =============================================================================

async function cacheFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);

  if (cached) {
    return cached;
  }

  try {
    const response = await fetch(request);
    if (response.ok) {
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    return new Response('Resource not available', { status: 503 });
  }
}

async function networkFirst(request, cacheName) {
  try {
    const response = await fetch(request);

    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }

    return response;
  } catch (error) {
    const cache = await caches.open(cacheName);
    const cached = await cache.match(request);

    if (cached) {
      return cached;
    }

    return new Response('Network unavailable', { status: 503 });
  }
}

async function staleWhileRevalidate(request, cacheName, maxAgeSeconds = 60) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);

  // Fetch in background
  const fetchPromise = fetch(request)
    .then((response) => {
      if (response.ok) {
        // Store with timestamp
        const cloned = response.clone();
        const headers = new Headers(cloned.headers);
        headers.set('sw-cached-at', Date.now().toString());

        cache.put(request, new Response(cloned.body, {
          status: cloned.status,
          statusText: cloned.statusText,
          headers,
        }));
      }
      return response;
    })
    .catch(() => cached);

  // Return cached if fresh enough
  if (cached) {
    const cachedAt = cached.headers.get('sw-cached-at');
    if (cachedAt) {
      const age = (Date.now() - parseInt(cachedAt)) / 1000;
      if (age < maxAgeSeconds) {
        return cached;
      }
    }
    // Return stale while revalidating
    return cached;
  }

  return fetchPromise;
}

// =============================================================================
// Utility Functions
// =============================================================================

function isStaticAsset(pathname) {
  const staticExtensions = [
    '.js', '.css', '.png', '.jpg', '.jpeg', '.gif', '.svg',
    '.ico', '.woff', '.woff2', '.ttf', '.eot'
  ];
  return staticExtensions.some((ext) => pathname.endsWith(ext));
}

// =============================================================================
// Background Sync
// =============================================================================

self.addEventListener('sync', (event) => {
  console.log('[SW] Background sync:', event.tag);

  if (event.tag === 'sync-messages') {
    event.waitUntil(syncMessages());
  }
});

async function syncMessages() {
  // Retrieve queued messages from IndexedDB and send
  console.log('[SW] Syncing queued messages...');
  // Implementation would retrieve from IndexedDB and POST to server
}

// =============================================================================
// Push Notifications
// =============================================================================

self.addEventListener('push', (event) => {
  console.log('[SW] Push notification received');

  let data = { title: 'GRACE', body: 'New notification' };

  if (event.data) {
    try {
      data = event.data.json();
    } catch (e) {
      data.body = event.data.text();
    }
  }

  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: '/favicon.ico',
      badge: '/favicon.ico',
      tag: data.tag || 'grace-notification',
      data: data.data,
    })
  );
});

self.addEventListener('notificationclick', (event) => {
  console.log('[SW] Notification clicked');

  event.notification.close();

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then((clientList) => {
        // Focus existing window or open new one
        for (const client of clientList) {
          if (client.url.includes(self.location.origin) && 'focus' in client) {
            return client.focus();
          }
        }
        return clients.openWindow('/');
      })
  );
});

// =============================================================================
// Message Handler (for communication with main app)
// =============================================================================

self.addEventListener('message', (event) => {
  console.log('[SW] Message received:', event.data);

  if (event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }

  if (event.data.type === 'CLEAR_CACHE') {
    event.waitUntil(
      caches.keys().then((names) =>
        Promise.all(names.map((name) => caches.delete(name)))
      )
    );
  }

  if (event.data.type === 'CACHE_URLS') {
    const urls = event.data.urls || [];
    event.waitUntil(
      caches.open(DYNAMIC_CACHE).then((cache) => cache.addAll(urls))
    );
  }
});

console.log('[SW] Service worker loaded');
