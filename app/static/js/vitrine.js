/**
 * Vitrine Loja - API e carrinho (localStorage)
 * Base URL da API: /api/v1/loja
 */
(function () {
  "use strict";

  const API_BASE = "/api/v1/loja";
  const MARKETING_VITRINE_URL = "/api/v1/marketing-vitrine/vitrine-home";
  const CART_KEY_PREFIX = "loja_carrinho_";

  /** Retorna a chave do carrinho conforme o usuário atual (anonimo vs consumidor). Carrinho isolado por sessão. */
  function getCartKey() {
    var cid = typeof window.LOJA_CONSUMIDOR_ID !== "undefined" && window.LOJA_CONSUMIDOR_ID != null
      ? window.LOJA_CONSUMIDOR_ID
      : null;
    return cid != null ? CART_KEY_PREFIX + "c" + cid : CART_KEY_PREFIX + "anonimo";
  }

  /** Breakpoint: viewport ≤767px = mobile; ≥768px = desktop (alinha a loja.css e body.loja-mobile) */
  var MOBILE_BREAKPOINT = "(max-width: 767px)";

  /** Detecta mobile vs desktop e atualiza body + Vitrine. Sempre deixa exatamente uma das classes (nunca as duas). */
  function detectViewport() {
    var mqMobile = window.matchMedia && window.matchMedia(MOBILE_BREAKPOINT);
    var isMobile = mqMobile ? !!mqMobile.matches : window.innerWidth < 768;
    var isDesktop = !isMobile;
    var body = document.body;
    if (body) {
      var want = isMobile ? "loja-mobile" : "loja-desktop";
      body.classList.remove("loja-mobile", "loja-desktop");
      body.classList.add(want);
    }
    if (window.Vitrine) {
      window.Vitrine.isMobile = isMobile;
      window.Vitrine.isDesktop = isDesktop;
    }
    return { isMobile: isMobile, isDesktop: isDesktop };
  }

  function getCart() {
    try {
      var key = getCartKey();
      var raw = localStorage.getItem(key);
      if (!raw && key === CART_KEY_PREFIX + "anonimo") {
        var legacy = localStorage.getItem("loja_carrinho");
        if (legacy) {
          localStorage.setItem(key, legacy);
          localStorage.removeItem("loja_carrinho");
          raw = legacy;
        }
      }
      return raw ? JSON.parse(raw) : { items: [] };
    } catch {
      return { items: [] };
    }
  }

  function setCart(cart) {
    localStorage.setItem(getCartKey(), JSON.stringify(cart));
    if (typeof window.VitrineUpdateCartBadge === "function") {
      window.VitrineUpdateCartBadge();
    }
  }

  /** Retorna loja_id do contexto (primeiro item do carrinho ou parâmetro URL ?loja_id=). Usado em login/cadastro. */
  function getContextLojaId() {
    const cart = getCart();
    const first = (cart.items || [])[0];
    if (first && first.loja_id != null) return parseInt(first.loja_id, 10);
    try {
      const params = new URLSearchParams(window.location.search);
      const id = params.get("loja_id");
      if (id != null) return parseInt(id, 10);
    } catch (_) {}
    return null;
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

  /** Adiciona ou atualiza item no carrinho. Item: { anuncio_id, titulo, preco, quantidade, loja_id, slug_loja?, nome_loja?, imagem_url? } */
  function addToCart(item) {
    const cart = getCart();
    const items = cart.items || [];
    const idx = items.findIndex(function (i) {
      return i.anuncio_id === item.anuncio_id;
    });
    const qty = Math.max(1, parseInt(item.quantidade, 10) || 1);
    if (idx >= 0) {
      items[idx].quantidade = (items[idx].quantidade || 0) + qty;
      if (item.imagem_url != null) items[idx].imagem_url = item.imagem_url;
    } else {
      items.push({
        anuncio_id: item.anuncio_id,
        titulo: item.titulo || "",
        preco: item.preco,
        quantidade: qty,
        loja_id: item.loja_id,
        slug_loja: item.slug_loja || null,
        nome_loja: item.nome_loja || null,
        imagem_url: item.imagem_url || null,
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

  /**
   * Checkout pode retornar redirect (cartão/boleto) ou PIX antes do pagamento concluir.
   * Não limpar o carrinho nesse momento — só após "Obrigado" via applyPendingCartClearIfAny().
   */
  var CART_CLEAR_PENDING_KEY = "loja_cart_clear_pending";

  function setPendingCartClear(payload) {
    try {
      sessionStorage.setItem(CART_CLEAR_PENDING_KEY, JSON.stringify(payload || {}));
    } catch (e) {}
  }

  function cancelPendingCartClear() {
    try {
      sessionStorage.removeItem(CART_CLEAR_PENDING_KEY);
    } catch (e) {}
  }

  function applyPendingCartClearIfAny() {
    try {
      var raw = sessionStorage.getItem(CART_CLEAR_PENDING_KEY);
      if (!raw) return;
      var o = JSON.parse(raw);
      sessionStorage.removeItem(CART_CLEAR_PENDING_KEY);
      if (!o || typeof o !== "object") return;
      if (o.type === "full") {
        clearCart();
        return;
      }
      if (o.type === "loja" && o.loja_id != null && !isNaN(Number(o.loja_id))) {
        var lid = parseInt(o.loja_id, 10);
        var cart = getCart();
        cart.items = (cart.items || []).filter(function (i) {
          return i.loja_id !== lid;
        });
        setCart(cart);
      }
    } catch (e) {}
  }

  /** GET categorias */
  function getCategorias() {
    return fetch(API_BASE + "/categorias?ativa=true")
      .then(function (r) {
        if (!r.ok) throw new Error("Falha ao carregar categorias");
        return r.json();
      });
  }

  /** GET marketing vitrine (home): config + destaques + ofertas_semana (sem cache). */
  function getMarketingVitrineHome() {
    return fetch(MARKETING_VITRINE_URL, { cache: "no-store" }).then(function (r) {
      if (!r.ok) throw new Error("Falha ao carregar vitrine marketing");
      return r.json();
    });
  }

  var GEO_STORAGE_KEY = "ibix_geo_location";

  function getGeoLocation() {
    try {
      var raw = localStorage.getItem(GEO_STORAGE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (e) { return null; }
  }

  function setGeoLocation(data) {
    try { localStorage.setItem(GEO_STORAGE_KEY, JSON.stringify(data)); } catch (e) {}
  }

  function clearGeoLocation() {
    try { localStorage.removeItem(GEO_STORAGE_KEY); } catch (e) {}
  }

  /** GET anuncios: params = { categoria_id?, categoria_ids?, cliente_ids?, q?, skip?, limit?, sort?, lat?, lng?, geo_cidade?, geo_uf? } */
  function getAnuncios(params) {
    params = params || {};
    const sp = new URLSearchParams();
    var slugCtx =
      typeof window.LOJA_SLUG_CONTEXT !== "undefined" && window.LOJA_SLUG_CONTEXT
        ? String(window.LOJA_SLUG_CONTEXT).trim()
        : "";
    var hasClienteFilter = Array.isArray(params.cliente_ids) && params.cliente_ids.length > 0;
    if (!params.loja_slug && slugCtx && !hasClienteFilter) {
      params.loja_slug = slugCtx;
    }
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
    if (params.loja_slug) sp.set("loja_slug", params.loja_slug);
    if (params.q) sp.set("q", params.q);
    if (params.sort) sp.set("sort", params.sort);
    if (params.somente_promocao === true) sp.set("somente_promocao", "true");
    else if (params.somente_promocao === false) sp.set("somente_promocao", "false");

    var geo = getGeoLocation();
    var geoLat = params.lat != null ? params.lat : (geo ? geo.lat : null);
    var geoLng = params.lng != null ? params.lng : (geo ? geo.lng : null);
    var geoCidade = params.geo_cidade || (geo ? geo.cidade : null);
    var geoUf = params.geo_uf || (geo ? geo.uf : null);
    if (geoLat != null && geoLng != null) {
      sp.set("lat", geoLat);
      sp.set("lng", geoLng);
    }
    if (geoCidade) sp.set("geo_cidade", geoCidade);
    if (geoUf) sp.set("geo_uf", geoUf);

    sp.set("skip", (params.skip != null ? params.skip : 0));
    sp.set("limit", (params.limit != null ? params.limit : 24));
    var requestUrl = API_BASE + "/anuncios?" + sp.toString();
    var attempt = 0;
    function doFetch() {
      attempt += 1;
      return fetch(requestUrl, { cache: "no-store" })
        .then(function (r) {
          if (!r.ok) {
            if ((r.status === 502 || r.status === 503 || r.status === 504) && attempt < 2) {
              return doFetch();
            }
            throw new Error("Falha ao carregar produtos (HTTP " + r.status + ")");
          }
          return r.json();
        });
    }
    return doFetch();
  }

  /** GET /loja/geo/geocodificar — CEP + número → { lat, lng, cidade, uf, precision, ... } */
  function geocodeAddress(payload) {
    payload = payload || {};
    var sp = new URLSearchParams();
    if (payload.cep) sp.set("cep", payload.cep);
    if (payload.numero) sp.set("numero", payload.numero);
    if (payload.complemento) sp.set("complemento", payload.complemento);
    if (payload.cidade) sp.set("cidade", payload.cidade);
    if (payload.uf) sp.set("uf", payload.uf);
    return fetch(API_BASE + "/geo/geocodificar?" + sp.toString())
      .then(function (r) {
        return r.json().then(function (data) {
          if (!r.ok) throw new Error(data && data.detail ? data.detail : "Falha ao localizar endereço");
          return data;
        });
      });
  }

  /** GET /loja/anuncios/perto-de-voce — produtos aleatórios ordenados por rota real */
  function getAnunciosPertoDeVoce(params) {
    params = params || {};
    var geo = getGeoLocation();
    var lat = params.lat != null ? params.lat : (geo ? geo.lat : null);
    var lng = params.lng != null ? params.lng : (geo ? geo.lng : null);
    if (lat == null || lng == null) {
      return Promise.resolve({ items: [], total: 0 });
    }
    var sp = new URLSearchParams();
    sp.set("lat", lat);
    sp.set("lng", lng);
    sp.set("limit", params.limit != null ? params.limit : 12);
    if (params.pool != null) sp.set("pool", params.pool);
    if (params.bbox_km != null) sp.set("bbox_km", params.bbox_km);
    var slugCtx =
      typeof window.LOJA_SLUG_CONTEXT !== "undefined" && window.LOJA_SLUG_CONTEXT
        ? String(window.LOJA_SLUG_CONTEXT).trim()
        : "";
    if (slugCtx) sp.set("loja_slug", slugCtx);
    return fetch(API_BASE + "/anuncios/perto-de-voce?" + sp.toString(), { cache: "no-store" })
      .then(function (r) {
        if (!r.ok) throw new Error("Falha ao carregar perto-de-voce (HTTP " + r.status + ")");
        return r.json();
      });
  }

  /** GET /loja/anuncios/proximos — comércio mais próximo que vende `q` */
  function getAnunciosProximosPorBusca(params) {
    params = params || {};
    var geo = getGeoLocation();
    var lat = params.lat != null ? params.lat : (geo ? geo.lat : null);
    var lng = params.lng != null ? params.lng : (geo ? geo.lng : null);
    if (!params.q || !String(params.q).trim()) {
      return Promise.resolve({ items: [], total: 0 });
    }
    if (lat == null || lng == null) {
      return Promise.resolve({ items: [], total: 0 });
    }
    var sp = new URLSearchParams();
    sp.set("q", String(params.q).trim());
    sp.set("lat", lat);
    sp.set("lng", lng);
    sp.set("limit", params.limit != null ? params.limit : 12);
    if (params.max_km != null) sp.set("max_km", params.max_km);
    if (params.top_n_lojas != null) sp.set("top_n_lojas", params.top_n_lojas);
    return fetch(API_BASE + "/anuncios/proximos?" + sp.toString(), { cache: "no-store" })
      .then(function (r) {
        if (!r.ok) throw new Error("Falha ao carregar lojas próximas (HTTP " + r.status + ")");
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

  /** GET anuncios semelhantes por id */
  function getAnunciosSemelhantes(id, limit) {
    var sp = new URLSearchParams();
    sp.set("limit", (limit != null ? limit : 8));
    return fetch(API_BASE + "/anuncios/" + id + "/semelhantes?" + sp.toString()).then(function (r) {
      if (!r.ok) throw new Error("Falha ao carregar produtos semelhantes");
      return r.json();
    });
  }

  /** POST checkout: body conforme API (itens, comprador_*, endereco_entrega, tipo_entrega, payment_method...). */
  function postCheckout(body) {
    return fetch(API_BASE + "/checkout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      credentials: "same-origin",
    });
  }

  /** POST checkout unificado: itens com loja_id por item; um pagamento (modo plataforma). */
  function postCheckoutUnificado(body) {
    return fetch(API_BASE + "/checkout-unificado", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      credentials: "same-origin",
    });
  }

  /** Exibe modal com código PIX para copiar. Usado em checkout e retry. Retorna true (indica que tratou). */
  function showPixModal(data) {
    var code = (data && (data.copy_paste_code || data.qr_code)) || "";
    if (!code) return;
    var id = (data && (data.id || data.pedido_id)) ? String(data.id || data.pedido_id) : "";
    var numero = (data && data.numero_pedido) ? String(data.numero_pedido) : "";
    var email = (data && data.comprador_email) ? String(data.comprador_email) : "";
    var obrigadoHref;
    if (data && data.session_uuid && data.pedidos && data.pedidos.length) {
      var nums = data.pedidos.map(function (p) { return p.numero_pedido; }).join(", ");
      var firstId = data.pedidos[0].id != null ? String(data.pedidos[0].id) : "";
      obrigadoHref =
        "/loja/obrigado?session=" +
        encodeURIComponent(data.session_uuid) +
        "&numero_pedido=" +
        encodeURIComponent(nums) +
        "&pedido_id=" +
        encodeURIComponent(firstId) +
        (email ? "&email=" + encodeURIComponent(email) : "");
    } else {
      obrigadoHref =
        "/loja/obrigado?pedido_id=" +
        id +
        "&numero_pedido=" +
        encodeURIComponent(numero) +
        "&email=" +
        encodeURIComponent(email);
    }
    var existing = document.getElementById("loja-pix-modal");
    if (existing) existing.remove();
    var overlay = document.createElement("div");
    overlay.id = "loja-pix-modal";
    overlay.style.cssText = "position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.6);display:flex;align-items:center;justify-content:center;z-index:9999;";
    var box = document.createElement("div");
    box.style.cssText = "background:#fff;padding:24px;border-radius:8px;max-width:400px;width:90%;box-shadow:0 4px 20px rgba(0,0,0,0.15);";
    box.innerHTML =
      "<h3 style=\"margin-top:0;\">Pague com PIX</h3>" +
      "<p class=\"text-muted small\">Copie o c\u00f3digo abaixo e cole no app do seu banco:</p>" +
      "<textarea readonly id=\"loja-pix-code\" style=\"width:100%;height:80px;font-size:11px;font-family:monospace;resize:none;padding:8px;\"></textarea>" +
      "<button type=\"button\" class=\"btn btn-primary mt-2\" id=\"loja-pix-copy\">Copiar c\u00f3digo</button>" +
      "<p class=\"mt-3 mb-0 small\"><a href=\"" +
      obrigadoHref +
      "\">Ir para acompanhar pedido</a></p>";
    var ta = box.querySelector("#loja-pix-code");
    if (ta) ta.value = code;
    overlay.appendChild(box);
    document.body.appendChild(overlay);
    var copyBtn = document.getElementById("loja-pix-copy");
    if (copyBtn) {
      copyBtn.onclick = function () {
        ta.select();
        try {
          document.execCommand("copy");
          copyBtn.textContent = "Copiado!";
        } catch (e) {
          navigator.clipboard && navigator.clipboard.writeText(code).then(function () {
            copyBtn.textContent = "Copiado!";
          });
        }
      };
    }
    overlay.onclick = function (e) {
      if (e.target === overlay) {
        overlay.remove();
        window.location.href = obrigadoHref;
      }
    };
  }

  /**
   * Trata resposta de pagamento (checkout ou retry).
   * Se redirect_url: redireciona e retorna true.
   * Se checkout_type==="qr_code" e qr_code/copy_paste_code: exibe modal PIX e retorna true.
   * Caso contr\u00e1rio retorna false.
   */
  function handlePagamentoResponse(data) {
    if (!data) return false;
    if (data.redirect_url) {
      window.location.href = data.redirect_url;
      return true;
    }
    if ((data.checkout_type === "qr_code" || data.checkout_type === "qr-code") && (data.qr_code || data.copy_paste_code)) {
      showPixModal(data);
      return true;
    }
    return false;
  }

  /** J1: Consome payload do checkout; se houver redirect_url ou PIX, trata e retorna true. Caso contr\u00e1rio retorna false. */
  function handleCheckoutResponse(data) {
    return handlePagamentoResponse(data);
  }

  /** POST login (lojaId opcional: contexto tenant para vitrine) */
  function postLogin(email, senha, lojaId) {
    const body = { email: email, senha: senha };
    if (lojaId != null) body.loja_id = lojaId;
    return fetch(API_BASE + "/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      credentials: "same-origin",
    });
  }

  /** POST cadastro (data pode incluir loja_id para contexto tenant) */
  function postCadastro(data) {
    return fetch(API_BASE + "/cadastro", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
      credentials: "same-origin",
    });
  }

  /** POST login social (Google/Facebook/Apple). */
  function postSocialLogin(payload) {
    return fetch(API_BASE + "/auth/social/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload || {}),
      credentials: "same-origin",
    });
  }

  /** POST confirmação de vínculo social com senha da conta existente. */
  function postSocialConfirmLink(linkToken, senha) {
    return fetch(API_BASE + "/auth/social/confirm-link", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ link_token: linkToken, senha: senha }),
      credentials: "same-origin",
    });
  }

  /** GET config OAuth público (client IDs habilitados no servidor). */
  function getSocialAuthConfig() {
    return fetch(API_BASE + "/auth/social/config", { credentials: "same-origin" }).then(function (r) {
      if (!r.ok) throw new Error("Falha ao carregar configuração de login social");
      return r.json();
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

  /** GET minha-conta/enderecos (cookie consumidor) */
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

  /** POST minha-conta/enderecos */
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

  /** DELETE minha-conta/enderecos/{id} — resposta 204 sem corpo */
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

  /** GET pedido/meu - pedido do consumidor logado (para acompanhamento na conta) */
  function getMeuPedido(numeroPedido) {
    return fetch(API_BASE + "/pedido/meu?numero_pedido=" + encodeURIComponent(numeroPedido || ""), {
      credentials: "same-origin",
    }).then(function (r) {
      if (r.status === 401) throw new Error("UNAUTH");
      if (r.status === 404) throw new Error("NOT_FOUND");
      if (r.status === 403) throw new Error("FORBIDDEN");
      if (!r.ok) return r.json().then(function (d) { throw new Error(d.detail || "Erro ao carregar pedido"); });
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

  /** Desconto percentual (0 se não houver promoção válida). */
  function calcDescontoPercent(item) {
    if (
      item.preco_original != null &&
      item.preco_promocional != null &&
      Number(item.preco_original) > 0 &&
      Number(item.preco_promocional) > 0 &&
      Number(item.preco_promocional) < Number(item.preco_original)
    ) {
      return Math.round(((item.preco_original - item.preco_promocional) / item.preco_original) * 100);
    }
    return 0;
  }

  /** Estoque baixo: entre 1 e 5 unidades. */
  function isEstoqueBaixo(item) {
    var e = Number(item.estoque_atual || 0);
    return e > 0 && e <= 5;
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

  /** Hero / cards: imagem OG dedicada (API) se houver, senão primeira da galeria. */
  function imagemPrincipalAnuncio(anuncio) {
    var og = anuncio && anuncio.og_image_url ? String(anuncio.og_image_url).trim() : "";
    if (og) return og;
    var imgs = ensureImagensArray(anuncio && anuncio.imagens);
    return imgs[0] || "";
  }

  /** Carrinho: foto do produto (galeria); OG só se não houver imagens. */
  function imagemCarrinhoAnuncio(anuncio) {
    var imgs = ensureImagensArray(anuncio && anuncio.imagens);
    if (imgs.length) return imgs[0];
    var og = anuncio && anuncio.og_image_url ? String(anuncio.og_image_url).trim() : "";
    return og || null;
  }

  /** Label amigável do estado do pagamento (J4: pendente, pago, recusado, cancelado, expirado, estornado). */
  function statusPagamentoLabel(status) {
    if (status == null || status === "") return "—";
    var s = String(status).toLowerCase();
    if (s === "pago" || s === "paid") return "Pago";
    if (s === "pendente" || s === "aguardando_pagamento") return "Pendente";
    if (s === "recusado" || s === "refused" || s === "rejeitado") return "Recusado";
    if (s === "cancelado" || s === "cancelled") return "Cancelado";
    if (s === "expirado" || s === "expired") return "Expirado";
    if (s === "estornado" || s === "refunded") return "Estornado";
    if (s.indexOf("parcial") !== -1) return "Parcialmente estornado";
    return status;
  }

  /** Retorna true se o pedido pode exibir botão 'Pagar agora' (nova tentativa). */
  function canShowPagarAgora(statusPagamento) {
    if (!statusPagamento) return false;
    var s = String(statusPagamento).toLowerCase();
    return s === "pendente" || s === "aguardando_pagamento";
  }

  /** Data URI SVG placeholder quando o produto não tem foto. */
  var PLACEHOLDER_IMG = "data:image/svg+xml," + encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">' +
    '<rect fill="#eee" width="200" height="200"/>' +
    '<text x="50%" y="50%" fill="#999" text-anchor="middle" dy=".3em" font-size="14" font-family="sans-serif">Sem imagem</text>' +
    "</svg>"
  );

  function slugifyText(text) {
    return (text || "produto").toLowerCase()
      .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/-{2,}/g, "-")
      .replace(/^-|-$/g, "") || "produto";
  }

  /**
   * Sanitiza redirect pós-login/cadastro (evita open redirect). Aceita só path relativo sob /loja/.
   * @param {string|null|undefined} rawNext valor bruto do query param next
   * @param {string|null} fallback se null/undefined, retorna fallback; se raw inválido, retorna fallback
   * @returns {string|null}
   */
  function getSafeLojaRedirectNext(rawNext, fallback) {
    if (rawNext == null || rawNext === "") {
      return fallback != null ? fallback : null;
    }
    var s = String(rawNext).trim();
    if (!s) return fallback != null ? fallback : null;
    try {
      s = decodeURIComponent(s.replace(/\+/g, " "));
    } catch (e) {
      return fallback != null ? fallback : null;
    }
    if (s.indexOf("://") !== -1 || s.slice(0, 2) === "//" || s.charAt(0) !== "/") {
      return fallback != null ? fallback : null;
    }
    if (s.indexOf("/loja/") !== 0) return fallback != null ? fallback : null;
    if (s.indexOf("..") !== -1) return fallback != null ? fallback : null;
    var path = (s.split("?")[0] || "").split("#")[0];
    if (!path || path.length > 512) return fallback != null ? fallback : null;
    return path;
  }

  function produtoUrl(titulo, id) {
    return "/loja/produto/" + slugifyText(titulo) + "-" + id;
  }

  /** URL canónica da página de produto (sem query) — partilha e OG alinhados ao path público. */
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
   * Partilha para o Instagram a partir do browser: a Meta não expõe URL tipo sharer com legenda (cf. Facebook/WhatsApp).
   * O fluxo suportado para o compositor receber foto + texto é a Web Share API com File (equivalente web ao intent Android).
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

  var viewport = detectViewport();
  window.Vitrine = {
    API_BASE: API_BASE,
    isMobile: viewport.isMobile,
    isDesktop: viewport.isDesktop,
    /** Atualiza detecção viewport (útil após resize). Retorna { isMobile, isDesktop }. */
    detectViewport: detectViewport,
    getCart: getCart,
    setCart: setCart,
    getCartCount: getCartCount,
    getContextLojaId: getContextLojaId,
    addToCart: addToCart,
    removeFromCart: removeFromCart,
    setCartItemQty: setCartItemQty,
    clearCart: clearCart,
    setPendingCartClear: setPendingCartClear,
    cancelPendingCartClear: cancelPendingCartClear,
    applyPendingCartClearIfAny: applyPendingCartClearIfAny,
    getCategorias: getCategorias,
    getMarketingVitrineHome: getMarketingVitrineHome,
    getAnuncios: getAnuncios,
    getAnuncio: getAnuncio,
    getAnunciosSemelhantes: getAnunciosSemelhantes,
    getAnunciosPertoDeVoce: getAnunciosPertoDeVoce,
    getAnunciosProximosPorBusca: getAnunciosProximosPorBusca,
    geocodeAddress: geocodeAddress,
    postCheckout: postCheckout,
    postCheckoutUnificado: postCheckoutUnificado,
    handleCheckoutResponse: handleCheckoutResponse,
    handlePagamentoResponse: handlePagamentoResponse,
    showPixModal: showPixModal,
    postLogin: postLogin,
    postCadastro: postCadastro,
    postSocialLogin: postSocialLogin,
    postSocialConfirmLink: postSocialConfirmLink,
    getSocialAuthConfig: getSocialAuthConfig,
    getMinhaConta: getMinhaConta,
    putMinhaConta: putMinhaConta,
    getMinhaContaEnderecos: getMinhaContaEnderecos,
    postMinhaContaEndereco: postMinhaContaEndereco,
    deleteMinhaContaEndereco: deleteMinhaContaEndereco,
    getMeusPedidos: getMeusPedidos,
    getMeuPedido: getMeuPedido,
    formatPreco: formatPreco,
    formatPrecoCard: formatPrecoCard,
    precoEfetivo: precoEfetivo,
    calcDescontoPercent: calcDescontoPercent,
    isEstoqueBaixo: isEstoqueBaixo,
    escapeHtml: escapeHtml,
    ensureImagensArray: ensureImagensArray,
    imagemPrincipalAnuncio: imagemPrincipalAnuncio,
    imagemCarrinhoAnuncio: imagemCarrinhoAnuncio,
    statusPagamentoLabel: statusPagamentoLabel,
    canShowPagarAgora: canShowPagarAgora,
    PLACEHOLDER_IMG: PLACEHOLDER_IMG,
    slugify: slugifyText,
    produtoUrl: produtoUrl,
    produtoPublicPageUrl: produtoPublicPageUrl,
    vitrineUrlComUtmCompartilhamento: vitrineUrlComUtmCompartilhamento,
    copyProductLink: copyProductLink,
    openFacebookShareProduct: openFacebookShareProduct,
    openWhatsAppShareProduct: openWhatsAppShareProduct,
    openInstagramShareProduct: openInstagramShareProduct,
    buildProductShareText: buildProductShareText,
    getSafeLojaRedirectNext: getSafeLojaRedirectNext,
    getGeoLocation: getGeoLocation,
    setGeoLocation: setGeoLocation,
    clearGeoLocation: clearGeoLocation,
    GEO_STORAGE_KEY: GEO_STORAGE_KEY,
  };

  window.VitrineUpdateCartBadge = updateCartBadge;

  (function initViewportListener() {
    var mq = window.matchMedia && window.matchMedia(MOBILE_BREAKPOINT);
    if (mq && mq.addEventListener) {
      mq.addEventListener("change", function () {
        detectViewport();
      });
    } else {
      window.addEventListener("resize", function () {
        detectViewport();
      });
    }
  })();

  document.addEventListener("DOMContentLoaded", function () {
    updateCartBadge();
  });

  /**
   * Ibix Vitrine: header sticky + scroll inteligente (somente UI da vitrine).
   * - Scroll down: header compacta
   * - Scroll up: header expande
   */
  (function initIbixHeaderScroll() {
    function getHeader() {
      return document.querySelector(".loja-header");
    }
    var header = getHeader();
    if (!header) return;

    var lastY = window.scrollY || 0;
    var ticking = false;
    var compactClass = "loja-header--compact";
    var threshold = 18;

    function onScroll() {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(function () {
        var y = window.scrollY || 0;
        var dy = y - lastY;
        var abs = Math.abs(dy);

        if (y <= 8) {
          header.classList.remove(compactClass);
        } else if (abs >= threshold) {
          if (dy > 0) header.classList.add(compactClass);
          else header.classList.remove(compactClass);
        }

        lastY = y;
        ticking = false;
      });
    }

    window.addEventListener("scroll", onScroll, { passive: true });
  })();
})();
