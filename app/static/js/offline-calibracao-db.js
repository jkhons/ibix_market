/**
 * PDV Ibix - IndexedDB para Calibração Offline
 * Armazena processos locais, cache de leitura e fila de sincronização
 */
(function () {
  'use strict';

  const DB_NAME = 'certipeso-offline-calibracao';
  const DB_VERSION = 1;
  const CACHE_TTL_MS = 24 * 60 * 60 * 1000;

  let db = null;

  function openDB() {
    if (db) return Promise.resolve(db);
    return new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onerror = () => reject(req.error);
      req.onsuccess = () => {
        db = req.result;
        resolve(db);
      };
      req.onupgradeneeded = (e) => {
        const d = e.target.result;
        if (!d.objectStoreNames.contains('sync_queue')) {
          const q = d.createObjectStore('sync_queue', { keyPath: 'id', autoIncrement: true });
          q.createIndex('order', 'order', { unique: false });
          q.createIndex('createdAt', 'createdAt', { unique: false });
        }
        if (!d.objectStoreNames.contains('cache_leitura')) {
          d.createObjectStore('cache_leitura', { keyPath: 'key' });
        }
        if (!d.objectStoreNames.contains('processos_locais')) {
          d.createObjectStore('processos_locais', { keyPath: 'temp_id' });
        }
        if (!d.objectStoreNames.contains('balancas_locais')) {
          const b = d.createObjectStore('balancas_locais', { keyPath: 'id', autoIncrement: true });
          b.createIndex('processo_temp_id', 'processo_temp_id', { unique: false });
        }
      };
    });
  }

  function cacheKey(url) {
    return (url || '').replace(/^\//, '') || 'default';
  }

  window.OfflineCalibracaoDB = {
    addToSyncQueue: function (method, url, body, tempIds) {
      return openDB().then(function (database) {
        return new Promise(function (resolve, reject) {
          const tx = database.transaction('sync_queue', 'readwrite');
          const store = tx.objectStore('sync_queue');
          const countReq = store.count();
          countReq.onsuccess = function () {
            const item = {
              order: countReq.result,
              method: method,
              url: url,
              body: body || null,
              tempIds: tempIds || null,
              createdAt: Date.now()
            };
            const addReq = store.add(item);
            addReq.onsuccess = function () {
              resolve(addReq.result);
            };
            addReq.onerror = function () {
              reject(addReq.error);
            };
          };
        });
      });
    },

    getSyncQueue: function () {
      return openDB().then(function (database) {
        return new Promise(function (resolve, reject) {
          const tx = database.transaction('sync_queue', 'readonly');
          const req = tx.objectStore('sync_queue').getAll();
          req.onsuccess = function () {
            const items = req.result || [];
            items.sort(function (a, b) {
              return (a.order !== undefined ? a.order : a.id) - (b.order !== undefined ? b.order : b.id);
            });
            resolve(items);
          };
          req.onerror = function () {
            reject(req.error);
          };
        });
      });
    },

    removeSyncQueueItem: function (id) {
      return openDB().then(function (database) {
        return new Promise(function (resolve, reject) {
          const tx = database.transaction('sync_queue', 'readwrite');
          const req = tx.objectStore('sync_queue').delete(id);
          req.onsuccess = function () {
            resolve();
          };
          req.onerror = function () {
            reject(req.error);
          };
        });
      });
    },

    setCacheLeitura: function (url, data) {
      const key = cacheKey(url);
      return openDB().then(function (database) {
        return new Promise(function (resolve, reject) {
          const tx = database.transaction('cache_leitura', 'readwrite');
          const req = tx.objectStore('cache_leitura').put({
            key: key,
            data: data,
            timestamp: Date.now()
          });
          req.onsuccess = function () {
            resolve();
          };
          req.onerror = function () {
            reject(req.error);
          };
        });
      });
    },

    getCacheLeitura: function (url) {
      const key = cacheKey(url);
      return openDB().then(function (database) {
        return new Promise(function (resolve, reject) {
          const tx = database.transaction('cache_leitura', 'readonly');
          const req = tx.objectStore('cache_leitura').get(key);
          req.onsuccess = function () {
            const row = req.result;
            if (!row) {
              resolve(null);
              return;
            }
            const age = Date.now() - (row.timestamp || 0);
            if (age > CACHE_TTL_MS) {
              resolve(null);
              return;
            }
            resolve(row.data);
          };
          req.onerror = function () {
            reject(req.error);
          };
        });
      });
    },

    clearExpiredCache: function () {
      return openDB().then(function (database) {
        return new Promise(function (resolve, reject) {
          const tx = database.transaction('cache_leitura', 'readwrite');
          const store = tx.objectStore('cache_leitura');
          const req = store.openCursor();
          const keysToDelete = [];
          req.onsuccess = function () {
            const cursor = req.result;
            if (cursor) {
              const age = Date.now() - (cursor.value.timestamp || 0);
              if (age > CACHE_TTL_MS) {
                keysToDelete.push(cursor.primaryKey);
              }
              cursor.continue();
            } else {
              keysToDelete.forEach(function (k) {
                store.delete(k);
              });
              resolve();
            }
          };
          req.onerror = function () {
            reject(req.error);
          };
        });
      }).catch(function () {});
    }
  };
})();
