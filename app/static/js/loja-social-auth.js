/**
 * Login/cadastro social na vitrine (Google, Facebook, Apple).
 * Depende de window.Vitrine (vitrine.js) e de GET /api/v1/loja/auth/social/config.
 */
(function () {
  "use strict";

  function getErrorEl(errorElId) {
    return errorElId ? document.getElementById(errorElId) : null;
  }

  function showError(errorEl, msg) {
    if (!errorEl) return;
    errorEl.textContent = msg || "Erro.";
    errorEl.style.display = "block";
  }

  function hideError(errorEl) {
    if (!errorEl) return;
    errorEl.style.display = "none";
  }

  /** Destino após login social bem-sucedido (honra ?next= com allowlist em Vitrine). */
  function getPostSocialAuthRedirectUrl() {
    try {
      var p = new URLSearchParams(window.location.search);
      var raw = p.get("next");
      if (window.Vitrine && typeof window.Vitrine.getSafeLojaRedirectNext === "function") {
        return window.Vitrine.getSafeLojaRedirectNext(raw, "/") || "/";
      }
    } catch (e) {}
    return "/";
  }

  function loadScriptOnce(src, testFn) {
    return new Promise(function (resolve, reject) {
      if (testFn && testFn()) return resolve();
      var existing = document.querySelector('script[data-loja-social-src="' + src + '"]');
      if (existing) {
        existing.addEventListener("load", function () {
          resolve();
        });
        existing.addEventListener("error", function () {
          reject(new Error("Falha ao carregar script"));
        });
        return;
      }
      var s = document.createElement("script");
      s.async = true;
      s.defer = true;
      s.src = src;
      s.setAttribute("data-loja-social-src", src);
      s.onload = function () {
        resolve();
      };
      s.onerror = function () {
        reject(new Error("Falha ao carregar script"));
      };
      document.head.appendChild(s);
    });
  }

  function parseApiError(r, data) {
    if (r.status === 429) return "Muitas tentativas. Aguarde um instante e tente novamente.";
    var d = data && data.detail;
    if (Array.isArray(d)) {
      return d
        .map(function (x) {
          return (x && x.msg) || (typeof x === "string" ? x : "");
        })
        .filter(Boolean)
        .join("; ");
    }
    if (typeof d === "string") return d;
    return "Erro ao processar solicitação.";
  }

  function handleSocialResponse(r, errorElId) {
    var errEl = getErrorEl(errorElId);
    return r.json().then(function (data) {
      if (!r.ok) {
        throw new Error(parseApiError(r, data));
      }
      if (data.status === "authenticated") {
        window.location.href = getPostSocialAuthRedirectUrl();
        return;
      }
      if (data.status === "pending_link" && data.link_token) {
        var needsPwd = data.requires_password !== false;
        openLinkModal(data.link_token, data.message, errorElId, needsPwd);
        return;
      }
      throw new Error(data.detail || "Resposta inesperada do servidor.");
    }).catch(function (e) {
      showError(errEl, e.message || String(e));
    });
  }

  function openLinkModal(linkToken, message, errorElId, requiresPassword) {
    var needsPwd = requiresPassword !== false;
    var modal = document.getElementById("modalSocialLinkCustom");
    var msgEl = document.getElementById("modal-social-link-msg");
    var input = document.getElementById("modal-social-link-senha");
    var errModal = document.getElementById("modal-social-link-error");
    var senhaBlock = document.getElementById("modal-social-link-senha-block");
    if (!modal || !input) return;
    if (senhaBlock) senhaBlock.style.display = needsPwd ? "" : "none";
    if (msgEl) msgEl.textContent = message || "Este e-mail já possui conta. Digite sua senha para vincular o login social.";
    input.value = "";
    if (errModal) {
      errModal.textContent = "";
      errModal.style.display = "none";
    }
    modal.style.display = "block";
    document.body.style.overflow = "hidden";

    function close() {
      modal.style.display = "none";
      document.body.style.overflow = "";
      confirmBtn.onclick = null;
      cancelBtn.onclick = null;
      modal.onclick = null;
    }

    var confirmBtn = document.getElementById("modal-social-link-confirm");
    var cancelBtn = document.getElementById("modal-social-link-close");
    if (cancelBtn) cancelBtn.onclick = close;
    modal.onclick = function (ev) {
      if (ev.target === modal) close();
    };

    if (confirmBtn) {
      confirmBtn.onclick = function () {
        var senha = needsPwd ? (input.value || "").trim() : "";
        if (needsPwd && !senha) {
          if (errModal) {
            errModal.textContent = "Informe sua senha.";
            errModal.style.display = "block";
          }
          return;
        }
        if (errModal) {
          errModal.textContent = "";
          errModal.style.display = "none";
        }
        hideError(getErrorEl(errorElId));
        window.Vitrine.postSocialConfirmLink(linkToken, senha).then(function (r) {
          return r.json().then(function (data) {
            if (!r.ok) {
              var msg = parseApiError(r, data);
              if (errModal) {
                errModal.textContent = msg;
                errModal.style.display = "block";
              } else {
                showError(getErrorEl(errorElId), msg);
              }
              return;
            }
            if (data.status === "authenticated") {
              window.location.href = getPostSocialAuthRedirectUrl();
              return;
            }
            var unexpected = data.detail || "Não foi possível confirmar o vínculo.";
            if (errModal) {
              errModal.textContent = unexpected;
              errModal.style.display = "block";
            }
          });
        });
      };
    }
  }

  window.fecharModalSocialLink = function () {
    var modal = document.getElementById("modalSocialLinkCustom");
    if (modal) {
      modal.style.display = "none";
      document.body.style.overflow = "";
    }
  };

  var fbInitialized = false;

  function ensureFacebook(appId, done) {
    if (!document.getElementById("fb-root")) {
      var root = document.createElement("div");
      root.id = "fb-root";
      document.body.insertBefore(root, document.body.firstChild);
    }
    function finish() {
      if (!window.FB) return;
      if (!fbInitialized) {
        window.FB.init({
          appId: appId,
          cookie: true,
          xfbml: false,
          version: "v20.0",
        });
        fbInitialized = true;
      }
      done();
    }
    if (window.FB && fbInitialized) {
      finish();
      return;
    }
    window.fbAsyncInit = finish;
    if (document.querySelector('script[src*="connect.facebook.net"]')) {
      return;
    }
    var s = document.createElement("script");
    s.async = true;
    s.defer = true;
    s.crossOrigin = "anonymous";
    s.src = "https://connect.facebook.net/pt_BR/sdk.js";
    document.body.appendChild(s);
  }

  function runGoogle(clientId, payloadBase, errorElId) {
    loadScriptOnce("https://accounts.google.com/gsi/client", function () {
      return window.google && window.google.accounts && window.google.accounts.oauth2;
    })
      .then(function () {
        var client = google.accounts.oauth2.initTokenClient({
          client_id: clientId,
          scope: "openid email profile",
          callback: function (resp) {
            if (resp.error) {
              showError(getErrorEl(errorElId), resp.error || "Login Google cancelado.");
              return;
            }
            if (!resp.access_token) {
              showError(getErrorEl(errorElId), "Google não retornou token.");
              return;
            }
            hideError(getErrorEl(errorElId));
            var body = Object.assign({}, payloadBase, {
              provider: "google",
              access_token: resp.access_token,
            });
            window.Vitrine.postSocialLogin(body).then(function (r) {
              return handleSocialResponse(r, errorElId);
            });
          },
        });
        client.requestAccessToken();
      })
      .catch(function (e) {
        showError(getErrorEl(errorElId), e.message || "Erro ao carregar Google");
      });
  }

  var appleInitKey = "";

  function runApple(clientId, payloadBase, errorElId) {
    var path = window.location.pathname || "/loja/login";
    var redirectURI = window.location.origin + path.split("?")[0];
    loadScriptOnce(
      "https://appleid.cdn-apple.com/appleauth/static/jsapi/appleid/1/en_US/appleid.auth.js",
      function () {
        return window.AppleID && window.AppleID.auth;
      }
    )
      .then(function () {
        var key = clientId + "|" + redirectURI;
        if (appleInitKey !== key) {
          AppleID.auth.init({
            clientId: clientId,
            scope: "name email",
            redirectURI: redirectURI,
            usePopup: true,
          });
          appleInitKey = key;
        }
        return AppleID.auth.signIn();
      })
      .then(function (res) {
        var idToken = res && res.authorization && res.authorization.id_token;
        if (!idToken) throw new Error("Apple não retornou identificação.");
        hideError(getErrorEl(errorElId));
        var body = Object.assign({}, payloadBase, {
          provider: "apple",
          id_token: idToken,
        });
        return window.Vitrine.postSocialLogin(body);
      })
      .then(function (r) {
        if (r && typeof r.json === "function") return handleSocialResponse(r, errorElId);
      })
      .catch(function (e) {
        if (e && (e.error === "popup_closed_by_user" || (e.message && e.message.indexOf("popup") !== -1)))
          return;
        showError(getErrorEl(errorElId), e.message || "Erro no login com Apple");
      });
  }

  function runFacebook(appId, payloadBase, errorElId) {
    ensureFacebook(appId, function () {
      window.FB.login(
        function (response) {
          if (!response.authResponse || !response.authResponse.accessToken) {
            showError(getErrorEl(errorElId), "Login Facebook cancelado ou sem permissão.");
            return;
          }
          hideError(getErrorEl(errorElId));
          var body = Object.assign({}, payloadBase, {
            provider: "facebook",
            access_token: response.authResponse.accessToken,
          });
          window.Vitrine.postSocialLogin(body).then(function (r) {
            return handleSocialResponse(r, errorElId);
          });
        },
        { scope: "email", return_scopes: true }
      );
    });
  }

  function buildPayload(page) {
    var base = { aceite_termos: true, nome_fallback: null };
    if (page === "cadastro") {
      var termos = document.getElementById("loja-cadastro-termos");
      var nomeEl = document.getElementById("loja-cadastro-nome");
      base.aceite_termos = termos ? !!termos.checked : false;
      base.nome_fallback = nomeEl && nomeEl.value ? nomeEl.value.trim() : null;
    }
    return base;
  }

  function init(options) {
    if (!window.Vitrine || typeof window.Vitrine.getSocialAuthConfig !== "function") return;
    var page = (options && options.page) || "login";
    var errorElId = options && options.errorElId;
    var wrap = document.getElementById("loja-social-auth");
    if (!wrap) return;

    window.Vitrine.getSocialAuthConfig()
      .then(function (cfg) {
        var g = cfg.google_client_id;
        var f = cfg.facebook_app_id;
        var a = cfg.apple_client_id;
        if (!g && !f && !a) {
          wrap.style.display = "none";
          return;
        }

        var row = wrap.querySelector(".loja-social-auth-buttons");
        if (row) row.style.display = "flex";

        var btnG = document.getElementById("loja-social-btn-google");
        var btnF = document.getElementById("loja-social-btn-facebook");
        var btnA = document.getElementById("loja-social-btn-apple");
        if (btnG) btnG.style.display = g ? "inline-flex" : "none";
        if (btnF) btnF.style.display = f ? "inline-flex" : "none";
        if (btnA) btnA.style.display = a ? "inline-flex" : "none";

        function validateCadastroTerms() {
          if (page !== "cadastro") return true;
          var termos = document.getElementById("loja-cadastro-termos");
          if (termos && !termos.checked) {
            showError(getErrorEl(errorElId), "Aceite os termos de uso para criar conta com rede social.");
            return false;
          }
          return true;
        }

        if (btnG && g) {
          btnG.onclick = function () {
            hideError(getErrorEl(errorElId));
            if (!validateCadastroTerms()) return;
            runGoogle(g, buildPayload(page), errorElId);
          };
        }
        if (btnF && f) {
          btnF.onclick = function () {
            hideError(getErrorEl(errorElId));
            if (!validateCadastroTerms()) return;
            runFacebook(f, buildPayload(page), errorElId);
          };
        }
        if (btnA && a) {
          btnA.onclick = function () {
            hideError(getErrorEl(errorElId));
            if (!validateCadastroTerms()) return;
            runApple(a, buildPayload(page), errorElId);
          };
        }
      })
      .catch(function () {
        /* sem config no servidor: oculta bloco */
      });
  }

  window.LojaSocialAuth = {
    init: init,
  };
})();
