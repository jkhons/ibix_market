// Template base de modal reutilizável (sem JS inline)
(function () {
  function createModalTemplate(config) {
    var overlay = document.getElementById(config.overlayId);
    if (!overlay) {
      throw new Error("Modal overlay não encontrado: " + config.overlayId);
    }

    function isOpen() {
      return overlay.style.display === "block" || overlay.style.display === "flex";
    }

    function open(displayType) {
      overlay.style.display = displayType || "block";
      document.body.style.overflow = "hidden";
      if (typeof config.onOpen === "function") config.onOpen();
    }

    function close() {
      overlay.style.display = "none";
      document.body.style.overflow = "";
      if (typeof config.onClose === "function") config.onClose();
    }

    function bindBackdropClose() {
      overlay.addEventListener("click", function (e) {
        if (e.target === overlay) {
          close();
        }
      });
    }

    function bindEscapeClose() {
      document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && isOpen()) {
          close();
        }
      });
    }

    if (config.backdropClose !== false) bindBackdropClose();
    if (config.escapeClose !== false) bindEscapeClose();

    return {
      open: open,
      close: close,
      isOpen: isOpen,
      element: overlay,
    };
  }

  window.createModalTemplate = createModalTemplate;
})();
