/**
 * PDV Ibix - Service Worker PWA Calibração
 * Cache de estáticos para funcionamento offline (tela cheia, sem barra de URL)
 */
const CACHE_NAME = 'pdv-automscale-calibracao-v1';
const STATIC_ASSETS = [
  '/static/css/dashboard.css',
  '/static/css/certipeso.css',
  '/static/css/calibracao-mobile.css',
  '/static/css/novo-processo-mobile.css',
  '/static/css/fix-buttons.css',
  '/static/js/app.js',
  '/static/js/certipeso.js',
  '/static/js/dashboard.js',
  '/static/js/pesos_ensaios_mobile.js',
  '/static/js/aux-cadastros.js',
  '/static/js/etapa3_certificado.js',
  '/static/js/breadcrumbs.js',
  '/static/js/alert-system.js',
  '/static/img/icons/icon-48x48.png',
  '/static/img/icons/iconcertipeso.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS.map(u => new Request(u, { cache: 'reload' }))).catch(() => {});
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((names) => {
      return Promise.all(names.filter((n) => n !== CACHE_NAME).map((n) => caches.delete(n)));
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname.startsWith('/api/')) return;

  const isStatic = STATIC_ASSETS.some((p) => url.pathname === p || url.pathname.startsWith('/static/'));
  if (!isStatic) return;

  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) return cached;
      return fetch(event.request).then((res) => {
        const clone = res.clone();
        if (res.status === 200 && (event.request.method === 'GET')) {
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return res;
      }).catch(() => {
        if (event.request.destination === 'document') {
          return caches.match('/certificados').then((r) => r || new Response('Offline', { status: 503, statusText: 'Offline' }));
        }
        return new Response('', { status: 503, statusText: 'Offline' });
      });
    })
  );
});
