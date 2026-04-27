/**
 * PDV Ibix - Fetch Offline para Calibração
 * Enfileira operações offline e sincroniza ao voltar online
 */
(function () {
  'use strict';

  var CACHEABLE_PREFIXES = [
    '/api/v1/clientes',
    '/api/v1/processos',
    '/api/v1/aux-cadastros',
    '/api/v1/procedimentos-metodo',
    '/api/v1/lacres-selos'
  ];

  function isCacheableUrl(url) {
    var path = url.split('?')[0];
    return CACHEABLE_PREFIXES.some(function (p) {
      return path.indexOf(p) === 0;
    });
  }

  function isCalibracaoUrl(url) {
    return url.indexOf('/api/v1/processos') === 0 ||
      url.indexOf('/api/v1/clientes') === 0 ||
      url.indexOf('/api/v1/aux-cadastros') === 0 ||
      url.indexOf('/api/v1/procedimentos-metodo') === 0 ||
      url.indexOf('/api/v1/lacres-selos') === 0;
  }

  function isCalibracaoPage() {
    return false;
  }

  function getToken() {
    if (typeof getCookie === 'function') return getCookie('pdv_automscale_token');
    var v = ('; ' + document.cookie).split('; pdv_automscale_token=');
    return v.length === 2 ? v.pop().split(';').shift() : null;
  }

  function showOfflineBanner() {
    var el = document.getElementById('pwa-offline-banner');
    if (el) {
      el.classList.remove('d-none');
      if (typeof feather !== 'undefined' && feather.replace) feather.replace();
    }
  }

  function hideOfflineBanner() {
    var el = document.getElementById('pwa-offline-banner');
    if (el) el.classList.add('d-none');
  }

  function showSyncToast(message, success) {
    var container = document.getElementById('pwa-sync-toast-container');
    if (!container) return;
    var toast = document.createElement('div');
    toast.className = 'alert alert-' + (success ? 'success' : 'warning') + ' alert-dismissible fade show';
    toast.style.cssText = 'position:fixed;bottom:1rem;right:1rem;z-index:9999;max-width:320px;';
    toast.innerHTML = message + '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>';
    container.appendChild(toast);
    setTimeout(function () {
      if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, 5000);
  }

  function processSyncQueue() {
    if (!window.OfflineCalibracaoDB) return Promise.resolve();
    return window.OfflineCalibracaoDB.getSyncQueue().then(function (items) {
      if (!items || items.length === 0) return Promise.resolve();
      var token = getToken();
      var mapTempToReal = {};
      var order = 0;
      function runNext() {
        if (order >= items.length) {
          showSyncToast('Sincronização concluída. ' + items.length + ' item(ns) enviado(s).', true);
          return;
        }
        var item = items[order];
        var url = item.url;
        Object.keys(mapTempToReal).forEach(function (temp) {
          url = url.replace(temp, mapTempToReal[temp]);
        });
        var opts = {
          method: item.method,
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include'
        };
        if (token) opts.headers['Authorization'] = 'Bearer ' + token;
        if (item.body && (item.method === 'POST' || item.method === 'PATCH' || item.method === 'PUT')) {
          var body = item.body;
          if (typeof body === 'object' && !(body instanceof String)) {
            Object.keys(mapTempToReal).forEach(function (temp) {
              var real = mapTempToReal[temp];
              try {
                body = JSON.parse(JSON.stringify(body).split(temp).join(String(real)));
              } catch (e) {}
            });
            opts.body = JSON.stringify(body);
          } else {
            opts.body = item.body;
          }
        }
        fetch(url, opts).then(function (res) {
          if (res.ok && (item.method === 'POST')) {
            return res.json().then(function (data) {
              var newId = data.id;
              if (item.tempIds && item.tempIds.processo_id && newId) {
                mapTempToReal[item.tempIds.processo_id] = newId;
              }
              if (item.tempIds && item.tempIds.balanca_id && data.id) {
                mapTempToReal[item.tempIds.balanca_id] = data.id;
              }
              return window.OfflineCalibracaoDB.removeSyncQueueItem(item.id);
            }).catch(function () {
              return window.OfflineCalibracaoDB.removeSyncQueueItem(item.id);
            });
          } else if (res.ok) {
            return window.OfflineCalibracaoDB.removeSyncQueueItem(item.id);
          } else {
            showSyncToast('Falha ao sincronizar. Tente novamente.', false);
            return Promise.reject(new Error('Sync failed'));
          }
        }).then(function () {
          order++;
          runNext();
        }).catch(function () {
          order++;
          runNext();
        });
      }
      runNext();
    });
  }

  function offlineCalibracaoFetch(url, options) {
    options = options || {};
    var method = (options.method || 'GET').toUpperCase();
    var isMutating = ['POST', 'PUT', 'PATCH', 'DELETE'].indexOf(method) >= 0;
    var online = navigator.onLine;

    function doRealFetch() {
      var opts = {
        credentials: 'include',
        headers: options.headers || {}
      };
      if (options.method) opts.method = options.method;
      if (options.body) opts.body = options.body;
      opts.headers['Content-Type'] = opts.headers['Content-Type'] || 'application/json';
      var token = getToken();
      if (token) opts.headers['Authorization'] = 'Bearer ' + token;
      return fetch(url, opts).then(function (res) {
        if (res.ok && method === 'GET' && isCacheableUrl(url)) {
          return res.clone().json().then(function (data) {
            if (window.OfflineCalibracaoDB) {
              window.OfflineCalibracaoDB.setCacheLeitura(url, data).catch(function () {});
            }
            return res;
          }).catch(function () {
            return res;
          });
        }
        return res;
      });
    }

    if (online) {
      return doRealFetch().catch(function (err) {
        if (err.message === 'Failed to fetch' || err.name === 'TypeError') {
          if (isMutating && window.OfflineCalibracaoDB) {
            var body = options.body;
            try {
              body = typeof body === 'string' ? JSON.parse(body) : body;
            } catch (e) {}
            return window.OfflineCalibracaoDB.addToSyncQueue(method, url, body).then(function () {
              showOfflineBanner();
              if (method === 'POST' && url.indexOf('/api/v1/processos') >= 0 && !url.match(/\/processos\/\d+/)) {
                return new Response(JSON.stringify({ id: 'temp_' + Date.now(), message: 'Salvo localmente' }), { status: 200, headers: { 'Content-Type': 'application/json' } });
              }
              return new Response(JSON.stringify({ message: 'Salvo localmente. Sincronizará quando online.' }), { status: 200, headers: { 'Content-Type': 'application/json' } });
            });
          }
        }
        throw err;
      });
    }

    if (method === 'GET' && isCacheableUrl(url) && window.OfflineCalibracaoDB) {
      return window.OfflineCalibracaoDB.getCacheLeitura(url).then(function (cached) {
        if (cached) {
          return new Response(JSON.stringify(cached), { status: 200, headers: { 'Content-Type': 'application/json' } });
        }
        return new Response(JSON.stringify({ detail: 'Sem conexão e sem cache' }), { status: 503, statusText: 'Offline' });
      });
    }

    if (isMutating && window.OfflineCalibracaoDB) {
      var body = options.body;
      try {
        body = typeof body === 'string' ? JSON.parse(body) : body;
      } catch (e) {}
      var tempIds = null;
      if (method === 'POST' && url.indexOf('/api/v1/processos') >= 0 && !url.match(/\/processos\/\d+/)) {
        tempIds = { processo_id: 'temp_' + Date.now() };
      }
      return window.OfflineCalibracaoDB.addToSyncQueue(method, url, body, tempIds).then(function () {
        showOfflineBanner();
        if (tempIds) {
          return new Response(JSON.stringify({ id: tempIds.processo_id, message: 'Salvo localmente' }), { status: 200, headers: { 'Content-Type': 'application/json' } });
        }
        return new Response(JSON.stringify({ message: 'Salvo localmente' }), { status: 200, headers: { 'Content-Type': 'application/json' } });
      });
    }

    return Promise.reject(new Error('Offline'));
  }

  function patchAuthenticatedFetch() {
    if (!isCalibracaoPage()) return;
    var orig = window.authenticatedFetch;
    if (!orig) return;
    window.authenticatedFetch = function (url, options) {
      if (!isCalibracaoUrl(url)) return orig(url, options);
      return offlineCalibracaoFetch(url, options);
    };
  }

  window.offlineCalibracaoFetch = offlineCalibracaoFetch;
  window.processSyncQueueCalibracao = processSyncQueue;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      patchAuthenticatedFetch();
      if (!navigator.onLine) showOfflineBanner();
      window.addEventListener('online', function () {
        hideOfflineBanner();
        processSyncQueue();
      });
    });
  } else {
    patchAuthenticatedFetch();
    if (!navigator.onLine) showOfflineBanner();
    window.addEventListener('online', function () {
      hideOfflineBanner();
      processSyncQueue();
    });
  }
})();
