/**
 * PDV Ibix - Registro da PWA Calibração
 * Instala o Service Worker para tela cheia (sem barra de URL) e cache offline
 */
(function () {
  'use strict';
  if (!('serviceWorker' in navigator)) return;

  navigator.serviceWorker.register('/sw-calibracao.js', { scope: '/' })
    .then(function (reg) {
      reg.addEventListener('updatefound', function () {
        var worker = reg.installing;
        worker.addEventListener('statechange', function () {
          if (worker.state === 'installed' && navigator.serviceWorker.controller) {
            if (typeof window.showPWAUpdateToast === 'function') {
              window.showPWAUpdateToast();
            }
          }
        });
      });
    })
    .catch(function () {});
})();
