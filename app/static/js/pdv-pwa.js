(() => {
  const MANIFEST_URL = "/negocio/venda/pdv/manifest.webmanifest";
  const SW_URL = "/negocio/venda/pdv/sw.js?v=2026-02-22-3";
  const SW_SCOPE = "/negocio/venda/pdv";
  const IOS_HINT =
    'No iPhone/iPad: toque em "Compartilhar" e depois em "Adicionar à Tela de Início".';
  const GENERIC_HINT =
    "Instalação não disponível agora neste navegador. Use Chrome/Edge atualizado para instalar.";
  const DISMISS_STORAGE_KEY = "pdv_pwa_install_dismissed";
  let deferredInstallPrompt = null;
  let installButton = null;
  let installHint = null;

  function canRegisterSW() {
    return "serviceWorker" in navigator && window.isSecureContext;
  }

  function isStandaloneMode() {
    return (
      window.matchMedia("(display-mode: standalone)").matches ||
      window.navigator.standalone === true
    );
  }

  function isIos() {
    return /iphone|ipad|ipod/i.test(window.navigator.userAgent || "");
  }

  function showHint(message) {
    if (!installHint) return;
    installHint.textContent = message;
    installHint.style.display = "block";
  }

  function hideHint() {
    if (!installHint) return;
    installHint.textContent = "";
    installHint.style.display = "none";
  }

  function showInstallButton(show) {
    if (!installButton) return;
    installButton.style.display = show ? "inline-flex" : "none";
  }

  function isInstallDismissed() {
    try {
      return window.localStorage.getItem(DISMISS_STORAGE_KEY) === "1";
    } catch (_error) {
      return false;
    }
  }

  function markInstallDismissed() {
    try {
      window.localStorage.setItem(DISMISS_STORAGE_KEY, "1");
    } catch (_error) {
      // Ignora indisponibilidade de storage.
    }
  }

  function refreshInstallUi() {
    if (isStandaloneMode()) {
      showInstallButton(false);
      hideHint();
      return;
    }

    if (isInstallDismissed()) {
      showInstallButton(false);
      hideHint();
      return;
    }

    if (deferredInstallPrompt) {
      showInstallButton(true);
      hideHint();
      return;
    }

    if (isIos()) {
      showInstallButton(true);
      showHint(IOS_HINT);
      return;
    }

    showInstallButton(false);
  }

  async function registerPwa() {
    if (!canRegisterSW()) return;
    try {
      const registration = await navigator.serviceWorker.register(SW_URL, {
        scope: SW_SCOPE,
        updateViaCache: "none",
      });
      // Força checagem de atualização sempre que o PDV é aberto.
      await registration.update();
    } catch (error) {
      console.warn("Falha ao registrar Service Worker do PDV:", error);
    }
  }

  function ensureManifestLink() {
    const existing = document.querySelector('link[rel="manifest"]');
    if (existing) return;
    const link = document.createElement("link");
    link.rel = "manifest";
    link.href = MANIFEST_URL;
    document.head.appendChild(link);
  }

  function addMobileMeta() {
    const metas = [
      { name: "theme-color", content: "#1f2e43" },
      { name: "apple-mobile-web-app-capable", content: "yes" },
      { name: "apple-mobile-web-app-status-bar-style", content: "black-translucent" },
      { name: "apple-mobile-web-app-title", content: "PDV" },
      { name: "mobile-web-app-capable", content: "yes" },
    ];
    metas.forEach((metaData) => {
      if (document.querySelector(`meta[name="${metaData.name}"]`)) return;
      const meta = document.createElement("meta");
      meta.name = metaData.name;
      meta.content = metaData.content;
      document.head.appendChild(meta);
    });
  }

  function enforceNoZoom() {
    const viewportContent =
      "width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover";
    const viewport = document.querySelector('meta[name="viewport"]');
    if (viewport) {
      viewport.setAttribute("content", viewportContent);
    } else {
      const meta = document.createElement("meta");
      meta.name = "viewport";
      meta.content = viewportContent;
      document.head.appendChild(meta);
    }

    // iOS Safari/PWA: bloqueia gesto de pinça.
    document.addEventListener(
      "gesturestart",
      (event) => {
        event.preventDefault();
      },
      { passive: false }
    );

    // Bloqueia duplo toque para zoom em alguns browsers mobile.
    let lastTouchEnd = 0;
    document.addEventListener(
      "touchend",
      (event) => {
        const now = Date.now();
        if (now - lastTouchEnd <= 300) {
          event.preventDefault();
        }
        lastTouchEnd = now;
      },
      { passive: false }
    );
  }

  async function onInstallClick() {
    if (isStandaloneMode()) {
      showHint("O app já está em modo instalado.");
      return;
    }

    if (deferredInstallPrompt) {
      deferredInstallPrompt.prompt();
      let choiceResult = null;
      try {
        choiceResult = await deferredInstallPrompt.userChoice;
      } catch (_error) {
        // Navegador pode rejeitar leitura de userChoice em cenários específicos.
      }
      if (choiceResult && choiceResult.outcome === "dismissed") {
        markInstallDismissed();
      }
      deferredInstallPrompt = null;
      refreshInstallUi();
      return;
    }

    if (isIos()) {
      showHint(IOS_HINT);
      markInstallDismissed();
      showInstallButton(false);
      return;
    }

    showHint(GENERIC_HINT);
    markInstallDismissed();
    showInstallButton(false);
  }

  function bindInstallEvents() {
    installButton = document.getElementById("pdv-btn-install-app");
    installHint = document.getElementById("pdv-install-hint");
    if (installButton) {
      installButton.addEventListener("click", onInstallClick);
    }

    window.addEventListener("beforeinstallprompt", (event) => {
      event.preventDefault();
      deferredInstallPrompt = event;
      refreshInstallUi();
    });

    window.addEventListener("appinstalled", () => {
      deferredInstallPrompt = null;
      showHint("Aplicativo PDV instalado com sucesso.");
      setTimeout(() => hideHint(), 2500);
      refreshInstallUi();
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    ensureManifestLink();
    addMobileMeta();
    enforceNoZoom();
    bindInstallEvents();
    refreshInstallUi();
    registerPwa();
  });
})();
