function pdvGetCookie(name) {
    const value = "; " + document.cookie;
    const parts = value.split("; " + name + "=");
    if (parts.length === 2) return parts.pop().split(";").shift();
    return null;
}

/** Token JWT: cookies ou sessionStorage (mesma origem que certipeso.js). */
function getPdvAuthToken() {
    try {
        return (
            pdvGetCookie("pdv_solumatica_token") ||
            pdvGetCookie("pdv_automscale_token") ||
            sessionStorage.getItem("pdv_solumatica_token") ||
            sessionStorage.getItem("pdv_automscale_token") ||
            null
        );
    } catch (_) {
        return pdvGetCookie("pdv_solumatica_token") || pdvGetCookie("pdv_automscale_token") || null;
    }
}

/**
 * Chamadas à API do PDV: credenciais + Bearer quando houver token.
 * Se existir window.authenticatedFetch (ex.: página com certipeso.js), reutiliza.
 */
async function apiFetch(url, options = {}) {
    if (typeof window.authenticatedFetch === "function") {
        return window.authenticatedFetch(url, options);
    }
    const token = getPdvAuthToken();
    const headers = { ...(options.headers || {}) };
    if (token) {
        headers.Authorization = "Bearer " + token;
    }
    return fetch(url, {
        credentials: "include",
        ...options,
        headers,
    });
}

const state = {
    buscaTimeout: null,
    produtos: [],
    carrinho: [],
    clientes: [],
    clientesFiltrados: [],
    clienteSelecionado: null,
    tipoPagamento: null,
    valorRecebido: null,
    submitting: false,
    caixaId: null,
    aberturaCaixaId: null,
    cupomConfig: { cupom_impressao_modo: "manual", cupom_tipo: "nao_fiscal" },
};

const modals = {
    carrinho: null,
    clientes: null,
    finalizar: null,
};

/** URL da foto do produto: path relativo vira /static/...; path já com / é usado como está. */
function urlFotoProduto(path) {
    if (!path) return "";
    const p = String(path).trim();
    return p.startsWith("/") ? p : "/static/" + p;
}

document.addEventListener("DOMContentLoaded", () => {
    const params = new URLSearchParams(window.location.search);
    const raw = params.get("caixa_id") || params.get("pdv_id");
    let presetCaixa = null;
    if (raw) {
        const n = parseInt(raw, 10);
        if (Number.isFinite(n)) presetCaixa = n;
    }

    /* Inicia já o GET de caixas (não fica preso em “Carregando…” se algo síncrono falhar depois). */
    const caixaReady = (async () => {
        await inicializarSeletorCaixa(presetCaixa);
    })();

    initModalControllers();
    bindStaticEvents();
    renderResumo();
    renderCarrinhoPreview();

    void (async () => {
        await caixaReady;
        await carregarClientesIniciais();
        apiFetch("/api/v1/tenant-config/cupom")
            .then((r) => (r.ok ? r.json() : null))
            .then((data) => {
                if (data) state.cupomConfig = data;
            });
        buscarProdutosPDV("");
    })();
});

/** Lista caixas da empresa fiscal, preenche o select e aplica caixa da URL ou único caixa. */
async function inicializarSeletorCaixa(caixaIdPreset) {
    const sel = document.getElementById("pdv-select-caixa");
    if (!sel) return;

    try {
        const r = await apiFetch("/api/v1/caixas/", { headers: { Accept: "application/json" } });
        if (!r.ok) {
            let msg = "Não foi possível listar caixas.";
            if (r.status === 400) {
                msg = "Configure a empresa fiscal (Fiscal → Empresa) para usar caixas.";
            }
            sel.innerHTML = "";
            const o = document.createElement("option");
            o.value = "";
            o.textContent = msg;
            sel.appendChild(o);
            return;
        }
        const list = await r.json();
        const arr = Array.isArray(list) ? list : [];

        sel.innerHTML = "";
        if (arr.length === 0) {
            const o = document.createElement("option");
            o.value = "";
            o.textContent = "Nenhum caixa cadastrado";
            sel.appendChild(o);
            const idEl = document.getElementById("pdv-header-identificador");
            if (idEl) {
                idEl.textContent = "Cadastre um caixa em Negócios → Caixa e abra o turno.";
                idEl.style.display = "";
            }
            return;
        }

        const opt0 = document.createElement("option");
        opt0.value = "";
        opt0.textContent = "Selecione o caixa…";
        sel.appendChild(opt0);
        arr.forEach((c) => {
            const o = document.createElement("option");
            o.value = String(c.id);
            o.textContent = (c.identificador || "Caixa") + " (#" + c.id + ")";
            sel.appendChild(o);
        });

        let aplicarId = caixaIdPreset;
        if (aplicarId == null && arr.length === 1) {
            aplicarId = arr[0].id;
        }
        if (aplicarId != null && arr.some((c) => c.id === aplicarId)) {
            sel.value = String(aplicarId);
            await aplicarCaixaSelecionado(aplicarId);
        }

        sel.addEventListener("change", onCaixaSelectChange);
    } catch (e) {
        sel.innerHTML = "";
        const o = document.createElement("option");
        o.value = "";
        o.textContent = "Erro ao carregar caixas";
        sel.appendChild(o);
    }
}

async function onCaixaSelectChange() {
    const sel = document.getElementById("pdv-select-caixa");
    if (!sel || !sel.value) {
        state.caixaId = null;
        state.aberturaCaixaId = null;
        atualizarUrlCaixa(null);
        const idEl = document.getElementById("pdv-header-identificador");
        if (idEl) {
            idEl.textContent = "";
            idEl.style.display = "none";
        }
        validarConfirmacaoFinal();
        return;
    }
    const id = parseInt(sel.value, 10);
    if (!Number.isFinite(id)) return;
    await aplicarCaixaSelecionado(id);
    await carregarClientesIniciais();
    validarConfirmacaoFinal();
}

async function aplicarCaixaSelecionado(caixaId) {
    state.caixaId = caixaId;
    state.aberturaCaixaId = null;
    await atualizarPainelCaixaETurno(caixaId);
    atualizarUrlCaixa(caixaId);
    validarConfirmacaoFinal();
}

function atualizarUrlCaixa(caixaId) {
    try {
        const u = new URL(window.location.href);
        if (caixaId != null) {
            u.searchParams.set("caixa_id", String(caixaId));
            u.searchParams.delete("pdv_id");
        } else {
            u.searchParams.delete("caixa_id");
            u.searchParams.delete("pdv_id");
        }
        window.history.replaceState({}, "", u.pathname + u.search);
    } catch (e) {
        /* ignore */
    }
}

/** Atualiza nome do caixa no cabeçalho, estado do turno (abertura_caixa_id) e mensagem se não houver turno. */
async function atualizarPainelCaixaETurno(caixaId) {
    const el = document.getElementById("pdv-header-identificador");
    if (!el) return;
    try {
        const rCx = await apiFetch("/api/v1/caixas/" + caixaId, { headers: { Accept: "application/json" } });
        const cx = rCx.ok ? await rCx.json() : null;
        const nome = cx && cx.identificador ? String(cx.identificador) : "Caixa #" + caixaId;

        const rAb = await apiFetch("/api/v1/aberturas-caixa/caixa-aberta?caixa_id=" + caixaId, {
            headers: { Accept: "application/json" },
        });
        const ab = rAb.ok ? await rAb.json() : null;

        if (ab && ab.id) {
            state.aberturaCaixaId = ab.id;
            el.textContent = "Caixa: " + nome + " · turno aberto";
        } else {
            state.aberturaCaixaId = null;
            el.textContent = "Caixa: " + nome + " · abra o turno (link Turno / cadastro)";
        }
        el.style.display = "";
    } catch (e) {
        /* ignore */
    }
    validarConfirmacaoFinal();
}

function initModalControllers() {
    if (!window.createModalTemplate) {
        throw new Error("Template de modal não disponível");
    }
    modals.carrinho = window.createModalTemplate({ overlayId: "pdv-modal-carrinho" });
    modals.clientes = window.createModalTemplate({ overlayId: "pdv-modal-clientes" });
    modals.finalizar = window.createModalTemplate({ overlayId: "pdv-modal-finalizar" });
}

function bindStaticEvents() {
    const map = [
        ["pdv-btn-close", fecharPDV],
        ["pdv-btn-cliente", abrirModalClientes],
        ["pdv-btn-abrir-carrinho", abrirModalCarrinho],
        ["pdv-btn-fechar-carrinho", fecharModalCarrinho],
        ["pdv-btn-finalizar-carrinho", abrirModalFinalizar],
        ["pdv-btn-fechar-clientes", fecharModalClientes],
        ["pdv-btn-fechar-finalizar", fecharModalFinalizar],
        ["pdv-btn-cancelar-finalizar", fecharModalFinalizar],
        ["pdv-btn-confirmar-venda", finalizarVenda],
    ];
    map.forEach(([id, handler]) => {
        const el = document.getElementById(id);
        if (el) el.addEventListener("click", handler);
    });

    const buscaProdutoInput = document.getElementById("pdv-busca-produto");
    if (buscaProdutoInput) {
        buscaProdutoInput.addEventListener("input", onBuscaProdutoInput);
        buscaProdutoInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                e.preventDefault();
                buscarProdutosPDV();
            }
        });
    }

    const buscaClienteInput = document.getElementById("pdv-busca-cliente");
    if (buscaClienteInput) buscaClienteInput.addEventListener("input", filtrarClientes);

    const valorRecebidoInput = document.getElementById("pdv-valor-recebido");
    if (valorRecebidoInput) {
        valorRecebidoInput.addEventListener("input", () => {
            state.valorRecebido = Number(valorRecebidoInput.value || 0);
            renderPagamentoResumo();
            validarConfirmacaoFinal();
        });
    }

    bindDelegatedEvents();
}

function bindDelegatedEvents() {
    const produtosContainer = document.getElementById("pdv-produtos-container");
    if (produtosContainer) {
        produtosContainer.addEventListener("click", (e) => {
            const actionEl = e.target.closest("[data-action='add-produto']");
            if (!actionEl) return;
            const produtoId = Number(actionEl.dataset.produtoId);
            if (Number.isFinite(produtoId)) adicionarAoCarrinho(produtoId);
        });
    }

    const carrinhoBody = document.getElementById("pdv-modal-carrinho-body");
    if (carrinhoBody) {
        carrinhoBody.addEventListener("click", (e) => {
            const actionEl = e.target.closest("[data-action]");
            if (!actionEl) return;
            const action = actionEl.dataset.action;
            const index = Number(actionEl.dataset.index);
            if (!Number.isFinite(index)) return;
            if (action === "increase") atualizarQuantidade(index, state.carrinho[index].quantidade + 1);
            if (action === "decrease") atualizarQuantidade(index, state.carrinho[index].quantidade - 1);
            if (action === "remove") removerDoCarrinho(index);
        });
        carrinhoBody.addEventListener("change", (e) => {
            const qtyInput = e.target.closest("[data-action='set-quantity']");
            if (!qtyInput) return;
            const index = Number(qtyInput.dataset.index);
            if (!Number.isFinite(index)) return;
            atualizarQuantidade(index, Number(qtyInput.value || 0));
        });
    }

    const clientesList = document.getElementById("pdv-clientes-list");
    if (clientesList) {
        clientesList.addEventListener("click", (e) => {
            const item = e.target.closest("[data-cliente-id]");
            if (!item) return;
            const clienteId = Number(item.dataset.clienteId);
            const clienteNome = item.dataset.clienteNome || "";
            const clienteEmail = item.dataset.clienteEmail || "";
            if (!Number.isFinite(clienteId) || !clienteNome) return;
            selecionarCliente(clienteId, clienteNome, true, clienteEmail);
        });
    }

    const cardsPagamento = document.getElementById("pdv-pagamento-cards");
    if (cardsPagamento) {
        cardsPagamento.addEventListener("click", (e) => {
            const card = e.target.closest(".pdv-pagamento-card[data-pagamento]");
            if (!card) return;
            selecionarPagamento(card.dataset.pagamento);
        });
    }
}

function onBuscaProdutoInput(e) {
    const termo = (e.target.value || "").trim();
    if (state.buscaTimeout) clearTimeout(state.buscaTimeout);
    // Atualiza a lista a cada letra (debounce curto para resposta imediata)
    state.buscaTimeout = setTimeout(() => {
        buscarProdutosPDV(termo);
    }, 180);
}

async function carregarClientesIniciais() {
    const clientes = await buscarClientes();
    let clientePadrao = null;
    // Se abriu com ?caixa_id=X, usar o estabelecimento (cliente_id) retornado pelo cadastro de caixa
    if (state.caixaId) {
        try {
            const rCx = await apiFetch("/api/v1/caixas/" + state.caixaId);
            if (rCx.ok) {
                const cx = await rCx.json();
                if (cx && cx.cliente_id != null) {
                    clientePadrao = clientes.find((c) => c.id === cx.cliente_id);
                }
            }
        } catch (e) {
            console.warn("Erro ao obter caixa:", e);
        }
    }
    if (!clientePadrao) {
        try {
            const response = await apiFetch("/api/v1/clientes/pdv-cliente-padrao/");
            if (response.ok) {
                const data = await response.json();
                if (data && data.cliente_id != null) {
                    clientePadrao = clientes.find((c) => c.id === data.cliente_id);
                }
            }
        } catch (e) {
            console.warn("Erro ao obter cliente padrão PDV:", e);
        }
    }
    if (!clientePadrao) {
        clientePadrao = clientes.find((c) => (c.nome || "").trim().toLowerCase() === "consumidor final");
    }
    if (clientePadrao) {
        selecionarCliente(clientePadrao.id, clientePadrao.nome, false, clientePadrao.email || "");
    } else {
        atualizarClienteSelecionado(null);
        toastErro('Nenhum cliente padrão configurado e "Consumidor Final" não encontrado. Selecione manualmente.');
    }
}

async function buscarClientes() {
    const response = await apiFetch("/api/v1/clientes/todos");
    if (!response.ok) throw new Error(`Falha ao carregar clientes (HTTP ${response.status})`);
    const payload = await response.json();
    if (!Array.isArray(payload)) throw new Error("Formato inválido na lista de clientes");
    state.clientes = payload;
    state.clientesFiltrados = payload;
    return payload;
}

async function abrirModalClientes() {
    try {
        if (!state.clientes.length) await buscarClientes();
        const buscaInput = document.getElementById("pdv-busca-cliente");
        if (buscaInput) buscaInput.value = "";
        state.clientesFiltrados = state.clientes;
        renderClientes();
        modals.clientes.open("flex");
    } catch (error) {
        toastErro(error.message || "Erro ao carregar clientes");
    }
}

function fecharModalClientes() {
    modals.clientes.close();
}

function filtrarClientes(e) {
    const termo = ((e?.target?.value || "") + "").trim().toLowerCase();
    if (!termo) {
        state.clientesFiltrados = state.clientes;
    } else {
        state.clientesFiltrados = state.clientes.filter((cliente) => {
            const nome = (cliente.nome || "").toLowerCase();
            const cnpj = (cliente.cnpj || "").toLowerCase();
            return nome.includes(termo) || cnpj.includes(termo);
        });
    }
    renderClientes();
}

function renderClientes() {
    const list = document.getElementById("pdv-clientes-list");
    if (!list) return;
    if (!state.clientesFiltrados.length) {
        list.innerHTML = `<div class="pdv-empty-state"><i class="fas fa-user-slash"></i><p>Nenhum cliente encontrado</p></div>`;
        return;
    }

    list.innerHTML = state.clientesFiltrados.map((cliente) => {
        const nome = escapeHtml(cliente.nome || "");
        const cnpj = escapeHtml(cliente.cnpj || "Sem CNPJ");
        const selected = state.clienteSelecionado && state.clienteSelecionado.id === cliente.id ? "selected" : "";
        const emailAttr = escapeHtml(cliente.email || "");
        return `
            <article class="pdv-cliente-item ${selected}" data-cliente-id="${cliente.id}" data-cliente-nome="${nome}" data-cliente-email="${emailAttr}">
                <div>
                    <p class="pdv-cliente-item-nome">${nome}</p>
                    <p class="pdv-cliente-item-cnpj">${cnpj}</p>
                </div>
                <button type="button" class="pdv-cliente-item-btn">Selecionar</button>
            </article>
        `;
    }).join("");
}

function selecionarCliente(id, nome, showToast = true, email = "") {
    state.clienteSelecionado = { id, nome, email: (email || "").trim() };
    atualizarClienteSelecionado(state.clienteSelecionado);
    fecharModalClientes();
    if (showToast) toastSucesso(`Cliente "${nome}" selecionado`);
}

function atualizarClienteSelecionado(cliente) {
    const btn = document.getElementById("pdv-btn-cliente");
    if (!btn) return;
    const texto = cliente?.nome || "Selecionar cliente";
    btn.title = texto;
    btn.setAttribute("aria-label", texto);
}

async function buscarProdutosPDV(termoParam = null) {
    const buscaInput = document.getElementById("pdv-busca-produto");
    const termo = (termoParam !== undefined && termoParam !== null ? termoParam : (buscaInput?.value || "")).trim();

    try {
        const url = termo.length > 0
            ? `/api/v1/vendas/produtos?busca=${encodeURIComponent(termo)}`
            : "/api/v1/vendas/produtos";
        const response = await apiFetch(url);
        if (!response.ok) throw new Error(`Falha na busca de produtos (HTTP ${response.status})`);
        let produtos = await response.json();
        if (!Array.isArray(produtos)) throw new Error("Formato inválido na lista de produtos");
        // Sempre ordenar A-Z por nome (locale pt-BR)
        produtos = produtos.slice().sort((a, b) => (a.nome || "").localeCompare(b.nome || "", "pt-BR"));
        state.produtos = produtos;
        renderProdutos(produtos);
        const meta = document.getElementById("pdv-produtos-meta");
        if (meta) meta.textContent = termo.length > 0
            ? `${produtos.length} produto(s) encontrado(s)`
            : `${produtos.length} produto(s) cadastrado(s)`;
    } catch (error) {
        renderProdutos([]);
        toastErro(error.message || "Erro ao buscar produtos");
    }
}

function renderProdutos(produtos) {
    const container = document.getElementById("pdv-produtos-container");
    if (!container) return;
    if (!produtos.length) {
        container.innerHTML = `<div class="pdv-empty-state"><i class="fas fa-search"></i><p>Nenhum produto na pesquisa atual</p></div>`;
        return;
    }

    container.innerHTML = produtos.map((produto) => {
        const nome = escapeHtml(produto.nome || "");
        const price = Number(produto.valor_venda || 0);
        const foto = urlFotoProduto(produto.foto_peca);
        const media = foto
            ? `<img src="${escapeHtml(foto)}" class="pdv-product-item-image" alt="${nome}">`
            : `<div class="pdv-product-item-image pdv-product-item-placeholder"><i class="fas fa-box"></i></div>`;
        return `
            <article class="pdv-product-item">
                ${media}
                <div>
                    <p class="pdv-product-item-name">${nome}</p>
                    <p class="pdv-product-item-price">${formatarMoeda(price)}</p>
                </div>
                <button type="button" class="pdv-btn pdv-btn-primary" data-action="add-produto" data-produto-id="${produto.id}">
                    <i class="fas fa-plus"></i>
                </button>
            </article>
        `;
    }).join("");
}

function adicionarAoCarrinho(produtoId) {
    const produto = state.produtos.find((p) => p.id === produtoId);
    if (!produto) {
        toastErro("Produto não encontrado na lista atual");
        return;
    }
    const estoque = Number(produto.quantidade_atual || 0);
    if (estoque <= 0) {
        toastErro("Produto sem estoque disponível");
        return;
    }
    const existente = state.carrinho.find((item) => item.id === produto.id);
    if (existente) {
        if (existente.quantidade >= estoque) {
            toastErro("Quantidade atingiu o limite de estoque");
            return;
        }
        existente.quantidade += 1;
    } else {
        state.carrinho.push({
            id: produto.id,
            codigo: produto.codigo || "",
            nome: produto.nome || "",
            unidade_medida: produto.unidade_medida || "UN",
            estoque,
            quantidade: 1,
            valor_unitario: Number(produto.valor_venda || 0),
            foto_peca: produto.foto_peca || null,
        });
    }
    renderResumo();
    renderCarrinhoPreview();
    toastSucesso("Produto adicionado ao carrinho");
}

function atualizarQuantidade(index, quantidade) {
    const item = state.carrinho[index];
    if (!item) return;
    const qtd = Number(quantidade);
    if (!Number.isFinite(qtd) || qtd <= 0) {
        removerDoCarrinho(index);
        return;
    }
    if (qtd > item.estoque) {
        toastErro(`Estoque máximo: ${item.estoque}`);
        item.quantidade = item.estoque;
    } else {
        item.quantidade = qtd;
    }
    renderResumo();
    renderCarrinhoPreview();
    renderCarrinhoModal();
    renderPagamentoResumo();
}

function removerDoCarrinho(index) {
    if (!state.carrinho[index]) return;
    state.carrinho.splice(index, 1);
    renderResumo();
    renderCarrinhoPreview();
    renderCarrinhoModal();
    renderPagamentoResumo();
}

function renderResumo() {
    const totalItens = state.carrinho.reduce((acc, item) => acc + item.quantidade, 0);
    const total = getTotalVenda();
    const textEl = document.getElementById("pdv-resumo-texto");
    const totalEl = document.getElementById("pdv-resumo-total");
    if (textEl) textEl.textContent = totalItens ? `${totalItens} item(ns) no carrinho` : "Carrinho vazio";
    if (totalEl) totalEl.textContent = formatarMoeda(total);
}

function renderCarrinhoPreview() {
    const preview = document.getElementById("pdv-cart-preview");
    if (!preview) return;
    if (!state.carrinho.length) {
        preview.innerHTML = `<p class="pdv-cart-preview-empty">Nenhum item no carrinho</p>`;
        return;
    }
    const firstItems = state.carrinho.slice(0, 3);
    const html = firstItems.map((item) => {
        const subtotal = item.quantidade * item.valor_unitario;
        return `<div class="pdv-preview-item"><div><strong>${escapeHtml(item.nome)}</strong><br><small>${item.quantidade} x ${formatarMoeda(item.valor_unitario)}</small></div><strong>${formatarMoeda(subtotal)}</strong></div>`;
    }).join("");
    const extra = state.carrinho.length > 3 ? `<small>+${state.carrinho.length - 3} item(ns)</small>` : "";
    preview.innerHTML = html + extra;
}

function abrirModalCarrinho() {
    if (!state.carrinho.length) {
        toastErro("Carrinho vazio");
        return;
    }
    renderCarrinhoModal();
    modals.carrinho.open("flex");
}

function fecharModalCarrinho() {
    modals.carrinho.close();
}

function renderCarrinhoModal() {
    const body = document.getElementById("pdv-modal-carrinho-body");
    const total = document.getElementById("pdv-modal-total-valor");
    if (!body || !total) return;

    if (!state.carrinho.length) {
        body.innerHTML = `<div class="pdv-empty-state"><i class="fas fa-shopping-cart"></i><p>Carrinho vazio</p></div>`;
        total.textContent = formatarMoeda(0);
        return;
    }

    body.innerHTML = state.carrinho.map((item, index) => {
        const media = item.foto_peca
            ? `<img src="${escapeHtml(urlFotoProduto(item.foto_peca))}" class="pdv-carrinho-item-image" alt="${escapeHtml(item.nome)}">`
            : `<div class="pdv-carrinho-item-image pdv-carrinho-item-placeholder"><i class="fas fa-box"></i></div>`;
        const subtotal = item.quantidade * item.valor_unitario;
        return `
            <article class="pdv-carrinho-item">
                ${media}
                <div>
                    <p class="pdv-carrinho-item-name">${escapeHtml(item.nome)}</p>
                    <p class="pdv-carrinho-item-code">${escapeHtml(item.codigo)}</p>
                    <p class="pdv-carrinho-item-price-unit">${formatarMoeda(item.valor_unitario)} / ${escapeHtml(item.unidade_medida)}</p>
                    <div class="pdv-carrinho-item-controls">
                        <div class="pdv-carrinho-item-qty">
                            <button type="button" data-action="decrease" data-index="${index}">-</button>
                            <input type="number" min="1" max="${item.estoque}" value="${item.quantidade}" data-action="set-quantity" data-index="${index}">
                            <button type="button" data-action="increase" data-index="${index}">+</button>
                        </div>
                        <div class="pdv-carrinho-item-foot">
                            <span class="pdv-carrinho-item-total">${formatarMoeda(subtotal)}</span>
                            <button type="button" class="pdv-carrinho-item-remove" data-action="remove" data-index="${index}">Remover</button>
                        </div>
                    </div>
                </div>
            </article>
        `;
    }).join("");
    total.textContent = formatarMoeda(getTotalVenda());
}

function abrirModalFinalizar() {
    if (!state.carrinho.length) {
        toastErro("Carrinho vazio");
        return;
    }
    modals.carrinho.close();
    state.tipoPagamento = null;
    state.valorRecebido = null;
    limparSelecaoPagamento();
    renderPagamentoResumo();
    validarConfirmacaoFinal();
    modals.finalizar.open("flex");
}

function fecharModalFinalizar() {
    modals.finalizar.close();
}

function selecionarPagamento(tipo) {
    if (state.submitting) return;
    state.tipoPagamento = tipo;
    limparSelecaoPagamento();
    document.querySelectorAll(".pdv-pagamento-card[data-pagamento]").forEach((card) => {
        if (card.dataset.pagamento === tipo) card.classList.add("selected");
    });

    const moneyBox = document.getElementById("pdv-money-box");
    if (moneyBox) {
        moneyBox.style.display = tipo === "dinheiro" ? "grid" : "none";
    }
    renderPagamentoResumo();
    validarConfirmacaoFinal();

    // Fluxo solicitado: ao escolher forma eletrônica, inicia automaticamente a finalização.
    if (formaPagamentoUsaGateway(tipo) && state.clienteSelecionado?.id && state.carrinho.length) {
        finalizarVenda();
    }
}

function limparSelecaoPagamento() {
    document.querySelectorAll(".pdv-pagamento-card.selected").forEach((card) => card.classList.remove("selected"));
}

function renderPagamentoResumo() {
    const total = getTotalVenda();
    const totalEl = document.getElementById("pdv-finalizar-total-valor");
    if (totalEl) totalEl.textContent = formatarMoeda(total);

    const trocoEl = document.getElementById("pdv-troco-valor");
    if (!trocoEl) return;
    if (state.tipoPagamento !== "dinheiro") {
        trocoEl.textContent = formatarMoeda(0);
        return;
    }
    const valorRecebido = Number(state.valorRecebido || 0);
    const troco = valorRecebido > total ? valorRecebido - total : 0;
    trocoEl.textContent = formatarMoeda(troco);
}

function validarConfirmacaoFinal() {
    const btnConfirmar = document.getElementById("pdv-btn-confirmar-venda");
    if (!btnConfirmar) return;
    const total = getTotalVenda();
    const possuiCliente = !!state.clienteSelecionado?.id;
    const possuiCarrinho = state.carrinho.length > 0;
    const possuiPagamento = !!state.tipoPagamento;
    const possuiTurnoCaixa = !!state.aberturaCaixaId;
    let pagamentoValido = possuiPagamento;
    if (state.tipoPagamento === "dinheiro") {
        pagamentoValido = Number(state.valorRecebido || 0) >= total;
    }
    btnConfirmar.disabled = !(possuiCliente && possuiCarrinho && pagamentoValido && possuiTurnoCaixa && !state.submitting);
}

async function finalizarVenda() {
    if (state.submitting) return;
    if (!state.clienteSelecionado?.id) {
        toastErro("Selecione um cliente antes de finalizar");
        return;
    }
    if (!state.carrinho.length) {
        toastErro("Carrinho vazio");
        return;
    }
    if (!state.tipoPagamento) {
        toastErro("Selecione uma forma de pagamento");
        return;
    }
    if (!state.aberturaCaixaId) {
        toastErro("Selecione o caixa no topo e abra um turno em Negócios → Caixa (Turno / cadastro).");
        return;
    }

    const subtotal = getSubtotalItens();
    const desconto = 0;
    const acrescimo = 0;
    const total = subtotal - desconto + acrescimo;
    const valorPago = state.tipoPagamento === "dinheiro" ? Number(state.valorRecebido || 0) : total;
    if (valorPago < total) {
        toastErro("Valor pago não pode ser menor que o total");
        return;
    }
    const troco = valorPago - total;

    const payload = {
        cliente_id: state.clienteSelecionado.id,
        tipo_pagamento: state.tipoPagamento,
        observacoes: "Venda via PDV",
        subtotal,
        desconto,
        acrescimo,
        total,
        valor_pago: valorPago,
        troco,
        abertura_caixa_id: state.aberturaCaixaId,
        itens: state.carrinho.map((item) => ({
            produto_cliente_id: item.id,
            quantidade: Number(item.quantidade),
            valor_unitario: Number(item.valor_unitario),
            valor_total: Number((item.quantidade * item.valor_unitario).toFixed(2)),
            desconto_item: 0,
            observacoes: null,
        })),
    };

    const btnConfirmar = document.getElementById("pdv-btn-confirmar-venda");
    const originalLabel = btnConfirmar ? btnConfirmar.innerHTML : "";
    state.submitting = true;
    if (btnConfirmar) {
        btnConfirmar.disabled = true;
        btnConfirmar.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processando...';
    }

    try {
        const response = await apiFetch("/api/v1/vendas/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        if (!response.ok) {
            const errorData = await response.json().catch(() => null);
            throw new Error(errorData?.detail || `Falha ao criar venda (HTTP ${response.status})`);
        }
        const venda = await response.json();
        const gatewayResult = await processarPagamentoDaVenda(venda, total);
        state.carrinho = [];
        state.tipoPagamento = null;
        state.valorRecebido = null;
        renderResumo();
        renderCarrinhoPreview();
        renderCarrinhoModal();
        fecharModalFinalizar();
        const buscaInput = document.getElementById("pdv-busca-produto");
        if (buscaInput) buscaInput.value = "";
        // Recarrega todos os produtos ordenados A-Z após finalizar venda
        buscarProdutosPDV("");
        if (gatewayResult.gatewayAplicado && gatewayResult.status !== "approved") {
            toastErro(
                `Venda ${venda.numero_venda || ""} concluída, porém pagamento ficou ${gatewayResult.status}.`
            );
        } else {
            toastSucesso(`Venda ${venda.numero_venda || ""} finalizada com sucesso`);
        }
        if (state.cupomConfig.cupom_tipo === "nao_fiscal") {
            if (state.cupomConfig.cupom_impressao_modo === "automatico") {
                imprimirCupomVenda(venda.id);
            } else {
                mostrarBotaoImprimirCupomPDV(venda.numero_venda, venda.id);
            }
        }
    } catch (error) {
        toastErro(error.message || "Erro ao finalizar venda");
    } finally {
        state.submitting = false;
        if (btnConfirmar) {
            btnConfirmar.innerHTML = originalLabel;
            validarConfirmacaoFinal();
        }
    }
}

function imprimirCupomVenda(vendaId) {
    apiFetch("/api/v1/vendas/" + vendaId + "/cupom")
        .then((r) => (r.ok ? r.json() : null))
        .then((data) => {
            if (!data || data.tipo === "fiscal") return;
            const hasContent = (data.html && data.html.trim()) || (Array.isArray(data.linhas) && data.linhas.length > 0);
            if (!hasContent) return;
            let el = document.getElementById("pdv-cupom-print-area");
            if (!el) {
                el = document.createElement("div");
                el.id = "pdv-cupom-print-area";
                el.setAttribute("aria-hidden", "true");
                el.style.cssText = "position:absolute;left:-9999px;top:0;width:280px;";
                document.body.appendChild(el);
            }
            el.innerHTML =
                data.html ||
                (Array.isArray(data.linhas)
                    ? data.linhas.map((l) => {
                          const t = String(l || "\u00a0")
                              .replace(/</g, "&lt;")
                              .replace(/>/g, "&gt;");
                          return "<div>" + t + "</div>";
                      })
                    : []
                ).join("");
            if (!document.getElementById("pdv-cupom-print-style")) {
                const style = document.createElement("style");
                style.id = "pdv-cupom-print-style";
                style.textContent = "@media print{body *{visibility:hidden}#pdv-cupom-print-area,#pdv-cupom-print-area *{visibility:visible}#pdv-cupom-print-area{position:absolute;left:0;top:0;width:100%}}";
                document.head.appendChild(style);
            }
            window.print();
        });
}

function mostrarBotaoImprimirCupomPDV(numeroVenda, vendaId) {
    const msg = "Venda " + (numeroVenda || "") + " finalizada.";
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "pdv-btn pdv-btn-ghost pdv-btn-sm";
    btn.textContent = "Imprimir cupom";
    btn.style.marginTop = "8px";
    btn.addEventListener("click", () => {
        imprimirCupomVenda(vendaId);
        if (toastEl && toastEl.parentNode) toastEl.parentNode.removeChild(toastEl);
    });
    const toastEl = document.createElement("div");
    toastEl.className = "pdv-toast pdv-toast-success";
    toastEl.setAttribute("role", "status");
    toastEl.style.marginTop = "8px";
    toastEl.innerHTML = "<span>" + msg + "</span>";
    toastEl.appendChild(btn);
    const stack = document.getElementById("pdv-toast-stack");
    if (stack) stack.appendChild(toastEl);
    setTimeout(() => {
        if (toastEl.parentNode) toastEl.remove();
    }, 15000);
}

function formaPagamentoParaGateway(forma) {
    const mapping = {
        cartao_credito: "credit",
        cartao_debito: "debit",
        pix: "pix",
        boleto: "boleto",
        dinheiro: "cash",
        transferencia: "transfer",
    };
    return mapping[forma] || forma;
}

function formaPagamentoUsaGateway(forma) {
    return ["cartao_credito", "cartao_debito", "pix", "boleto"].includes(forma);
}

function gerarIdempotencyKey(prefixo, vendaId, sufixo = "") {
    const randomPart = (window.crypto && crypto.randomUUID) ? crypto.randomUUID() : String(Date.now());
    return `${prefixo}:${vendaId}:${sufixo}:${randomPart}`;
}

async function processarPagamentoDaVenda(venda, total) {
    if (!venda || !venda.id) return { gatewayAplicado: false, status: "not_applicable" };
    if (!formaPagamentoUsaGateway(state.tipoPagamento)) {
        return { gatewayAplicado: false, status: "approved" };
    }
    const estabelecimentoId = Number(venda?.cliente_id || state.clienteSelecionado?.id || 0);
    if (!estabelecimentoId) {
        return { gatewayAplicado: true, status: "pending" };
    }
    const method = formaPagamentoParaGateway(state.tipoPagamento);
    const payerEmail = (state.clienteSelecionado && state.clienteSelecionado.email) || "";
    if (method === "pix" && !payerEmail) {
        throw new Error("Selecione um cliente com e-mail cadastrado para pagar com PIX (Mercado Pago).");
    }
    const body = {
        estabelecimento_id: estabelecimentoId,
        venda_id: venda.id,
        amount: Number(total.toFixed(2)),
        method,
        idempotency_key: gerarIdempotencyKey("pdv", venda.id, method),
        ...(state.caixaId != null ? { caixa_id: state.caixaId } : {}),
        ...(method === "pix" ? { method_details: { payer_email: payerEmail } } : {}),
    };
    const response = await apiFetch("/api/v1/payments/process", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
    const payload = await response.json().catch(() => null);
    if (!response.ok) {
        throw new Error(payload?.detail || "Falha ao processar pagamento no gateway.");
    }
    const status = (payload?.status || "").toLowerCase();
    const pix = payload?.payment_details?.pix;
    if (pix && pix.copia_cola) {
        const copia = pix.copia_cola;
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(copia).then(
                () => pushToast("success", "PIX gerado. Código copiado — cole no app do banco."),
                () => pushToast("success", "PIX gerado. Use o código em pagamentos ou o link se disponível."),
            );
        } else {
            pushToast("success", "PIX gerado. Copie o código na tela de detalhes do pagamento.");
        }
        if (payload.payment_details.ticket_url) {
            window.open(payload.payment_details.ticket_url, "_blank", "noopener,noreferrer");
        }
    } else if (payload?.payment_details?.checkout_url) {
        window.open(payload.payment_details.checkout_url, "_blank", "noopener,noreferrer");
    }
    return {
        gatewayAplicado: true,
        status: status === "paid" || status === "authorized" ? "approved" : status || "pending",
    };
}

function getSubtotalItens() {
    return Number(
        state.carrinho
            .reduce((acc, item) => acc + Number(item.quantidade) * Number(item.valor_unitario), 0)
            .toFixed(2),
    );
}

function getTotalVenda() {
    return getSubtotalItens();
}

function fecharPDV() {
    if (window.history.length > 1) {
        window.history.back();
        return;
    }
    window.location.href = "/negocio/venda";
}

function formatarMoeda(valor) {
    return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(Number(valor || 0));
}

function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = String(value || "");
    return div.innerHTML;
}

function pushToast(kind, message) {
    const stack = document.getElementById("pdv-toast-stack");
    if (!stack) return;
    const icon = kind === "success" ? "fa-check-circle" : "fa-exclamation-circle";
    const toast = document.createElement("article");
    toast.className = `pdv-toast pdv-toast--${kind}`;
    toast.innerHTML = `<i class="fas ${icon}"></i><span>${escapeHtml(message)}</span>`;
    stack.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add("show"));
    setTimeout(() => {
        toast.classList.remove("show");
        setTimeout(() => {
            if (toast.parentNode === stack) stack.removeChild(toast);
        }, 180);
    }, 2800);
}

function toastSucesso(message) {
    pushToast("success", message);
}

function toastErro(message) {
    pushToast("error", message);
}

