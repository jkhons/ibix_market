# Checklist — Refatoração Home e Vitrine (Fase 1)

Use este checklist ao implementar o plano. Marque com `[x]` ao concluir cada item.

---

## Etapa 1 — index.html (estrutura)

- [ ] Inserir **barra de categorias**: `<section class="loja-categorias-strip">` com `#loja-categorias-list` (vazio, preenchido via JS).
- [ ] Inserir **hero**: `<section class="loja-hero">` com copy, kicker, título, subtítulo, CTAs (#loja-ofertas, #loja-todos-produtos) e banner-card.
- [ ] Manter **destaques** (faixa existente); garantir que o título seja “Produtos em destaque” ou “Destaques”.
- [ ] Inserir **ofertas**: `<section id="loja-ofertas" class="loja-section">` com `#loja-ofertas-grid` (row g-3 loja-grid-produtos).
- [ ] Inserir **mais procurados**: seção com kicker “Em alta”, título “Mais procurados”, `#loja-em-alta-grid`.
- [ ] Envolver a **listagem principal** em `<section id="loja-todos-produtos" class="loja-card-listagem-wrap">` sem alterar IDs internos (#loja-anuncios, #loja-sort, #loja-load-more, #loja-empty, #loja-error).
- [ ] Renomear título da listagem para **“Todos os produtos”** (ou manter “Produtos” quando for categoria/busca).
- [ ] Inserir **lojas em destaque**: `<section class="loja-section loja-lojas-destaque">` com `#loja-lojas-grid` (vazio ou placeholder).
- [ ] Inserir **bloco confiança**: `<section class="loja-trust-strip">` com `.loja-trust-grid` e 4 `.loja-trust-box` (Compra segura, Entrega ou retirada, Lojas parceiras, Acompanhe seus pedidos).

---

## Etapa 2 — loja.css

- [ ] Adicionar `.loja-section`, `.loja-section-head`, `.loja-section-kicker`.
- [ ] Adicionar `.loja-categorias-strip`, `.loja-categorias-list`, `.loja-categoria-chip` (e hover).
- [ ] Adicionar `.loja-hero`, `.loja-hero-grid`, `.loja-hero-copy`, `.loja-kicker`, `.loja-hero-actions`, `.loja-hero-banner`, `.loja-hero-banner-card`; media query mobile (1 coluna, h1 1.5rem).
- [ ] Reforçar card: `.loja-card` border-radius 12px; `.loja-card-body` padding 1rem; `.loja-card-title` min-height 2.6em; `.loja-card-loja` .78rem; `.loja-card-price` 1.8rem; `.loja-card-meta`, `.loja-card-pill` (Últimas unidades).
- [ ] Adicionar `.loja-lojas-grid`, `.loja-loja-card`; responsivo 2 cols (991px), 1 col (575px).
- [ ] Adicionar `.loja-trust-strip`, `.loja-trust-grid`, `.loja-trust-box`.

---

## Etapa 3 — vitrine.js

- [ ] Implementar `calcDescontoPercent(item)`: retorna 0 ou inteiro; validar preco_original e preco_promocional.
- [ ] Implementar `isEstoqueBaixo(item)`: estoque_atual numérico > 0 e <= 5.
- [ ] Expor `calcDescontoPercent` e `isEstoqueBaixo` em `window.Vitrine`.

---

## Etapa 4 — Script inline index.html (loaders + card)

- [ ] **renderCard(item)** retorna **string HTML** do card (sem wrapper): imagem, badge “-X%” (calcDescontoPercent), título, nome_loja, preço antigo/atual, pill “Últimas unidades” (isEstoqueBaixo). Usar `Vitrine.escapeHtml` onde aplicável.
- [ ] Na **listagem principal**: wrapper `col-6 col-md-4 col-lg-3` + innerHTML = renderCard(item).
- [ ] Na **faixa destaques**: wrapper `loja-faixa-slide` + innerHTML = renderCard(item); remover montagem manual duplicada.
- [ ] **loadCategorias()**: getCategorias(), para cada item com `slug` criar chip com href `/loja/categoria/{slug}` e escapeHtml(nome); append em #loja-categorias-list. Se lista vazia, esconder .loja-categorias-strip.
- [ ] **loadOfertas()**: getAnuncios(limit 24), filtrar por preco_promocional, até 8 itens, wrapper col + renderCard em #loja-ofertas-grid. Se 0 ofertas, esconder #loja-ofertas.
- [ ] **loadEmAlta()**: getAnuncios(limit 8 ou 12) + shuffle/subset, wrapper col + renderCard em #loja-em-alta-grid. Se 0 itens, esconder seção.
- [ ] Chamar **feather.replace()** após injetar conteúdo dinâmico (categorias, ofertas, em alta), se houver ícones.
- [ ] Garantir que **categoria sem slug** não gera link quebrado (omitir ou link para /loja).

---

## Etapa 5 — Header (base_loja + loja.css)

- [ ] Em **loja.css** (ou base): `.loja-nav-fill { max-width: 700px; }` (e ajustes de flex/margin se necessário).
- [ ] Em **base_loja.html**: adicionar link **“Meus pedidos”** para `/loja/meus-pedidos`, visível quando `consumidor_logado`, entre Minha conta e Carrinho.

---

## Testes e validação

- [ ] Rodar: `pytest tests/test_marketplace_loja.py -v` — todos os testes de API e páginas devem passar.
- [ ] Rodar: `pytest tests/test_marketplace_loja.py -m refactor_home -v` — testes da home refatorada devem passar após Etapa 1.
- [ ] Abrir `/loja` no navegador: verificar ordem dos blocos (categorias → hero → destaques → ofertas → mais procurados → todos os produtos → lojas → confiança).
- [ ] Clicar em “Ver ofertas”: âncora #loja-ofertas.
- [ ] Clicar em “Explorar produtos”: âncora #loja-todos-produtos.
- [ ] Clicar em chip de categoria: navega para /loja/categoria/{slug} e listagem filtrada.
- [ ] Verificar card: badge “-X%” quando há promoção; “Últimas unidades” quando estoque <= 5; nome da loja e preços corretos.
- [ ] Verificar responsivo: hero em 1 coluna no mobile; grids e trust em colunas reduzidas.

---

## Lacunas (evitar falhas)

- [ ] Chips de categoria: usar apenas itens com `slug`; escapeHtml no nome.
- [ ] Seções vazias: esconder #loja-ofertas, .loja-categorias-strip ou bloco “mais procurados” quando não houver dados.
- [ ] Nenhum link para `/loja/categoria/undefined` (slug null check).
