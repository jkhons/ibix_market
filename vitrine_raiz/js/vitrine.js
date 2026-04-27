/**
 * Vitrine Loja - API e carrinho (localStorage)
 * Base URL da API: /api/v1/loja
 */
(function () {
  "use strict";

  const API_BASE = "/api/v1/loja";
  const CART_KEY = "loja_carrinho";

  function getCart() {
    try {
      const raw = localStorage.getItem(CART_KEY);
      return raw ? JSON.parse(raw) : { items: [] };
    } catch {
      return { items: [] };
    }
  }

  function setCart(cart) {
    localStorage.setItem(CART_KEY, JSON.stringify(cart));
    if (typeof window.VitrineUpdateCartBadge === "function") {
      window.VitrineUpdateCartBadge();
    }
  }

  /** Retorna quantidade total de itens no carrinho */
  function getCartCount() {
    const cart = getCart();
    return (cart.items || []).reduce(function (acc, item) {
      return acc + (item.quantidade || 0);
    }, 0);
  }

  /** Atualiza o badge do carrinho no header */
  function updateCartBadge() {
    const el = document.getElementById("loja-cart-count");
    if (el) {
      const n = getCartCount();
      el.textContent = n;
      el.style.display = n > 0 ? "" : "none";
    }
  }

  /** Adiciona ou atualiza item no carrinho. Item: { anuncio_id, titulo, preco, quantidade, loja_id, slug_loja?, nome_loja? } */
  function addToCart(item) {
    const cart = getCart();
    const items = cart.items || [];
    const idx = items.findIndex(function (i) {
      return i.anuncio_id === item.anuncio_id;
    });
    const qty = Math.max(1, parseInt(item.quantidade, 10) || 1);
    if (idx >= 0) {
      items[idx].quantidade = (items[idx].quantidade || 0) + qty;
    } else {
      items.push({
        anuncio_id: item.anuncio_id,
        titulo: item.titulo || "",
        preco: item.preco,
        quantidade: qty,
        loja_id: item.loja_id,
        slug_loja: item.slug_loja || null,
        nome_loja: item.nome_loja || null,
      });
    }
    cart.items = items;
    setCart(cart);
    return getCartCount();
  }

  /** Remove item do carrinho por anuncio_id */
  function removeFromCart(anuncioId) {
    const cart = getCart();
    cart.items = (cart.items || []).filter(function (i) {
      return i.anuncio_id !== anuncioId;
    });
    setCart(cart);
  }

  /** Altera quantidade de um item (0 = remove) */
  function setCartItemQty(anuncioId, qty) {
    const cart = getCart();
    const items = cart.items || [];
    if (qty <= 0) {
      cart.items = items.filter(function (i) {
        return i.anuncio_id !== anuncioId;
      });
    } else {
      const it = items.find(function (i) {
        return i.anuncio_id === anuncioId;
      });
      if (it) it.quantidade = qty;
    }
    setCart(cart);
  }

  /** Remove todos os itens do carrinho (localStorage). */
  function clearCart() {
    setCart({ items: [] });
  }

  /** GET categorias */
  function getCategorias() {
    return fetch(API_BASE + "/categorias?ativa=true")
      .then(function (r) {
        if (!r.ok) throw new Error("Falha ao carregar categorias");
        return r.json();
      });
  }

  /** GET anuncios: params = { categoria_id?, categoria_ids?, cliente_ids?, q?, skip?, limit?, sort? } */
  function getAnuncios(params) {
    params = params || {};
    const sp = new URLSearchParams();
    if (params.categoria_id != null) sp.set("categoria_id", params.categoria_id);
    if (Array.isArray(params.categoria_ids) && params.categoria_ids.length) {
      params.categoria_ids.forEach(function (id) {
        if (id != null) sp.append("categoria_ids", id);
      });
    }
    if (Array.isArray(params.cliente_ids) && params.cliente_ids.length) {
      params.cliente_ids.forEach(function (id) {
        if (id != null) sp.append("cliente_ids", id);
      });
    }
    if (params.q) sp.set("q", params.q);
    if (params.sort) sp.set("sort", params.sort);
    if (params.somente_promocao === true) sp.set("somente_promocao", "true");
    else if (params.somente_promocao === false) sp.set("somente_promocao", "false");
    sp.set("skip", (params.skip != null ? params.skip : 0));
    sp.set("limit", (params.limit != null ? params.limit : 24));
    return fetch(API_BASE + "/anuncios?" + sp.toString())
      .then(function (r) {
        if (!r.ok) throw new Error("Falha ao carregar produtos");
        return r.json();
      });
  }

  /** GET anuncio por id */
  function getAnuncio(id) {
    return fetch(API_BASE + "/anuncios/" + id).then(function (r) {
      if (!r.ok) throw new Error("Produto não encontrado");
      return r.json();
    });
  }

  /** POST checkout: body conforme API (itens, comprador_*, endereco_entrega, tipo_entrega...) */
  function postCheckout(body) {
    return fetch(API_BASE + "/checkout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      credentials: "same-origin",
    });
  }

  /** POST checkout unificado (várias lojas, um pagamento). */
  function postCheckoutUnificado(body) {
    return fetch(API_BASE + "/checkout-unificado", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      credentials: "same-origin",
    });
  }

  /** POST login */
  function postLogin(email, senha) {
    return fetch(API_BASE + "/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email, senha: senha }),
      credentials: "same-origin",
    });
  }

  /** POST cadastro */
  function postCadastro(data) {
    return fetch(API_BASE + "/cadastro", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
      credentials: "same-origin",
    });
  }

  /** GET minha-conta (requer cookie) */
  function getMinhaConta() {
    return fetch(API_BASE + "/minha-conta", { credentials: "same-origin" }).then(function (r) {
      if (!r.ok) throw new Error("Não autenticado");
      return r.json();
    });
  }

  /** PUT minha-conta */
  function putMinhaConta(data) {
    return fetch(API_BASE + "/minha-conta", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
      credentials: "same-origin",
    });
  }

  function _parseLojaApiErrorDetail(d) {
    if (!d) return null;
    var det = d.detail;
    if (typeof det === "string") return det;
    if (Array.isArray(det)) {
      return det
        .map(function (x) {
          return (x && x.msg) || (typeof x === "string" ? x : "");
        })
        .filter(Boolean)
        .join("; ");
    }
    return null;
  }

  function getMinhaContaEnderecos() {
    return fetch(API_BASE + "/minha-conta/enderecos", { credentials: "same-origin" }).then(function (r) {
      if (!r.ok) {
        return r.json().then(function (d) {
          throw new Error(_parseLojaApiErrorDetail(d) || "Falha ao carregar endereços");
        }).catch(function (e) {
          if (e instanceof Error && e.message) throw e;
          throw new Error("Falha ao carregar endereços");
        });
      }
      return r.json();
    });
  }

  function postMinhaContaEndereco(body) {
    return fetch(API_BASE + "/minha-conta/enderecos", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(body),
    }).then(function (r) {
      if (!r.ok) {
        return r.json().then(function (d) {
          throw new Error(_parseLojaApiErrorDetail(d) || "Erro ao salvar endereço");
        }).catch(function (e) {
          if (e instanceof Error && e.message) throw e;
          throw new Error("Erro ao salvar endereço");
        });
      }
      return r.json();
    });
  }

  function deleteMinhaContaEndereco(enderecoId) {
    var id = Number(enderecoId);
    if (!(id > 0)) return Promise.reject(new Error("Endereço inválido"));
    return fetch(API_BASE + "/minha-conta/enderecos/" + id, {
      method: "DELETE",
      credentials: "same-origin",
    }).then(function (r) {
      if (r.status === 204) return;
      if (!r.ok) {
        return r.json().then(function (d) {
          throw new Error(_parseLojaApiErrorDetail(d) || "Erro ao remover endereço");
        }).catch(function (e) {
          if (e instanceof Error && e.message) throw e;
          throw new Error("Erro ao remover endereço");
        });
      }
    });
  }

  /** GET meus-pedidos */
  function getMeusPedidos() {
    return fetch(API_BASE + "/meus-pedidos", { credentials: "same-origin" }).then(function (r) {
      if (!r.ok) throw new Error("Falha ao carregar pedidos");
      return r.json();
    });
  }

  /** Formata preço para exibição */
  function formatPreco(val) {
    if (val == null) return "—";
    return "R$ " + Number(val).toFixed(2).replace(".", ",");
  }

  /** Formata preço para card (estilo ML: parte inteira + centavos em sobrescrito) */
  function formatPrecoCard(val) {
    if (val == null) return "—";
    var s = "R$ " + Number(val).toFixed(2).replace(".", ",");
    var i = s.lastIndexOf(",");
    if (i === -1) return s;
    return s.slice(0, i) + '<span class="loja-price-cents">' + escapeHtml(s.slice(i)) + "</span>";
  }

  /** Preço efetivo do anúncio (promocional ou original) */
  function precoEfetivo(item) {
    var p = item.preco_promocional != null && item.preco_promocional > 0
      ? item.preco_promocional
      : item.preco_original;
    return p != null ? p : 0;
  }

  /** Escapa HTML para evitar XSS */
  function escapeHtml(s) {
    if (s == null) return "";
    var div = document.createElement("div");
    div.textContent = s;
    return div.innerHTML;
  }

  /** Garante que imagens seja sempre um array de URLs (API pode enviar lista ou JSON string). */
  function ensureImagensArray(imagens) {
    if (Array.isArray(imagens)) return imagens.filter(Boolean);
    if (typeof imagens === "string") {
      try {
        var parsed = JSON.parse(imagens);
        return Array.isArray(parsed) ? parsed.filter(Boolean) : [];
      } catch (e) {
        return imagens ? [imagens] : [];
      }
    }
    return [];
  }

  function imagemPrincipalAnuncio(anuncio) {
    var og = anuncio && anuncio.og_image_url ? String(anuncio.og_image_url).trim() : "";
    if (og) return og;
    var imgs = ensureImagensArray(anuncio && anuncio.imagens);
    return imgs[0] || "";
  }

  function imagemCarrinhoAnuncio(anuncio) {
    var imgs = ensureImagensArray(anuncio && anuncio.imagens);
    if (imgs.length) return imgs[0];
    var og = anuncio && anuncio.og_image_url ? String(anuncio.og_image_url).trim() : "";
    return og || null;
  }

  function produtoPublicPageUrl() {
    try {
      return window.location.origin + window.location.pathname;
    } catch (_) {
      return typeof window !== "undefined" && window.location ? window.location.href : "";
    }
  }

  /** UTMs só para partilha — nunca usar na canonical/OG (Fase 02). */
  function vitrineUrlComUtmCompartilhamento(baseUrl) {
    try {
      var u = new URL(baseUrl, window.location.origin);
      u.searchParams.set("utm_source", "compartilhamento");
      u.searchParams.set("utm_medium", "cliente");
      u.searchParams.set("utm_campaign", "vitrine_social");
      return u.toString();
    } catch (e) {
      return baseUrl;
    }
  }

  function emitLojaToast(msg) {
    if (typeof window.dispatchEvent !== "function" || !msg) return;
    try {
      window.dispatchEvent(new CustomEvent("loja-toast", { detail: { msg: msg } }));
    } catch (_) {}
  }

  function copyProductLink(url) {
    var u = url || produtoPublicPageUrl();
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(u).then(function () {
        emitLojaToast("Link copiado!");
      }).catch(function () {
        window.prompt("Copie o link:", u);
      });
    }
    window.prompt("Copie o link:", u);
    return Promise.resolve();
  }

  function openFacebookShareProduct(u) {
    var url = u || produtoPublicPageUrl();
    var sh = "https://www.facebook.com/sharer/sharer.php?u=" + encodeURIComponent(url);
    window.open(sh, "_blank", "noopener,noreferrer");
  }

  function openWhatsAppShareProduct(text) {
    var url = "https://wa.me/?text=" + encodeURIComponent(text);
    window.open(url, "_blank", "noopener,noreferrer");
  }

  function absoluteUrlForShare(u) {
    if (!u || typeof u !== "string") return "";
    var s = u.trim();
    if (!s) return "";
    if (/^data:/i.test(s)) return s;
    try {
      return new URL(s, window.location.origin).href;
    } catch (_) {
      return s;
    }
  }

  function shareImageFileName(mime) {
    var m = (mime || "").toLowerCase();
    if (m.indexOf("png") !== -1) return "ibix-produto.png";
    if (m.indexOf("webp") !== -1) return "ibix-produto.webp";
    if (m.indexOf("gif") !== -1) return "ibix-produto.gif";
    return "ibix-produto.jpg";
  }

  function fetchImageBlobForInstagram(absUrl) {
    if (!absUrl || /^data:image\/svg/i.test(absUrl)) return Promise.resolve(null);
    return fetch(absUrl, { mode: "cors", credentials: "omit", cache: "no-store" })
      .then(function (r) {
        if (!r.ok) return null;
        return r.blob();
      })
      .catch(function () {
        return null;
      })
      .then(function (blob) {
        if (!blob || !blob.size) return null;
        var t = (blob.type || "").toLowerCase();
        if (t.indexOf("image/") !== 0) return null;
        if (t.indexOf("svg") !== -1) return null;
        return blob;
      });
  }

  function blobToShareableImageFile(blob) {
    var name = shareImageFileName(blob.type);
    try {
      return new File([blob], name, { type: blob.type || "image/jpeg", lastModified: Date.now() });
    } catch (_) {
      return blob;
    }
  }

  function normalizeInstagramShareArg(config) {
    if (config == null) return { text: "", imageUrl: "" };
    if (typeof config === "string") return { text: config, imageUrl: "" };
    return {
      text: config.text != null ? String(config.text) : "",
      imageUrl: config.imageUrl != null ? String(config.imageUrl) : "",
    };
  }

  /**
   * Instagram (feed): sem URL sharer público; Web Share com ficheiro de imagem entrega ao compositor via SO/app.
   * @see https://developers.facebook.com/docs/instagram-platform/sharing-to-feed/
   */
  function openInstagramShareProduct(config) {
    var norm = normalizeInstagramShareArg(config);
    var text = norm.text;
    var absUrl = absoluteUrlForShare(norm.imageUrl);
    if (!absUrl && typeof document !== "undefined") {
      var el = document.getElementById("loja-produto-img-main");
      var raw = el && (el.currentSrc || el.src || (el.getAttribute && el.getAttribute("src")));
      absUrl = absoluteUrlForShare(raw || "");
    }

    function tryShare(payload) {
      if (!navigator.share) return Promise.reject(new Error("no-share"));
      var p = Object.assign({ title: "" }, payload);
      if (navigator.canShare && !navigator.canShare(p)) return Promise.reject(new Error("cannot-share"));
      return navigator.share(p).catch(function (err) {
        if (err && err.name === "AbortError") return undefined;
        return Promise.reject(err);
      });
    }

    function openInstagramCreate() {
      window.open("https://www.instagram.com/create/story", "_blank", "noopener,noreferrer");
    }

    return fetchImageBlobForInstagram(absUrl)
      .then(function (blob) {
        if (!blob) return Promise.reject(new Error("no-blob"));
        var file = blobToShareableImageFile(blob);
        var withCaption = { files: [file] };
        if (text) withCaption.text = text;
        return tryShare(withCaption).catch(function () {
          return tryShare({ files: [file] });
        });
      })
      .catch(function () {
        if (text) return tryShare({ text: text });
        return Promise.reject(new Error("no-text"));
      })
      .catch(function () {
        openInstagramCreate();
      })
      .then(function () {
        return undefined;
      });
  }

  function buildProductShareText(anuncio, pageUrl) {
    var u = pageUrl || produtoPublicPageUrl();
    var t = anuncio && anuncio.titulo ? String(anuncio.titulo) : "Produto";
    var p = anuncio ? formatPreco(precoEfetivo(anuncio)) : "";
    return t + (p ? " — " + p : "") + "\n" + u;
  }

  /** Data URI SVG placeholder quando o produto não tem foto. */
  var PLACEHOLDER_IMG = "data:image/svg+xml," + encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">' +
    '<rect fill="#eee" width="200" height="200"/>' +
    '<text x="50%" y="50%" fill="#999" text-anchor="middle" dy=".3em" font-size="14" font-family="sans-serif">Sem imagem</text>' +
    "</svg>"
  );

  window.Vitrine = {
    API_BASE: API_BASE,
    getCart: getCart,
    setCart: setCart,
    getCartCount: getCartCount,
    addToCart: addToCart,
    removeFromCart: removeFromCart,
    setCartItemQty: setCartItemQty,
    clearCart: clearCart,
    getCategorias: getCategorias,
    getAnuncios: getAnuncios,
    getAnuncio: getAnuncio,
    postCheckout: postCheckout,
    postCheckoutUnificado: postCheckoutUnificado,
    postLogin: postLogin,
    postCadastro: postCadastro,
    getMinhaConta: getMinhaConta,
    putMinhaConta: putMinhaConta,
    getMinhaContaEnderecos: getMinhaContaEnderecos,
    postMinhaContaEndereco: postMinhaContaEndereco,
    deleteMinhaContaEndereco: deleteMinhaContaEndereco,
    getMeusPedidos: getMeusPedidos,
    formatPreco: formatPreco,
    formatPrecoCard: formatPrecoCard,
    precoEfetivo: precoEfetivo,
    escapeHtml: escapeHtml,
    ensureImagensArray: ensureImagensArray,
    imagemPrincipalAnuncio: imagemPrincipalAnuncio,
    imagemCarrinhoAnuncio: imagemCarrinhoAnuncio,
    PLACEHOLDER_IMG: PLACEHOLDER_IMG,
    produtoPublicPageUrl: produtoPublicPageUrl,
    vitrineUrlComUtmCompartilhamento: vitrineUrlComUtmCompartilhamento,
    copyProductLink: copyProductLink,
    openFacebookShareProduct: openFacebookShareProduct,
    openWhatsAppShareProduct: openWhatsAppShareProduct,
    openInstagramShareProduct: openInstagramShareProduct,
    buildProductShareText: buildProductShareText,
  };

  window.VitrineUpdateCartBadge = updateCartBadge;

  document.addEventListener("DOMContentLoaded", function () {
    updateCartBadge();
  });
})();
