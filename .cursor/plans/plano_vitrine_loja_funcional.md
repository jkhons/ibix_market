---
name: Plano vitrine loja funcional
overview: "Plano para deixar a vitrine (loja pública) funcional, no padrão dos grandes players (Amazon, Mercado Livre), com foco em desempenho, segurança, disponibilidade e experiência do usuário (comprador e CA). A API da vitrine já existe; os templates são esqueletos sem JS nem formulários. Este plano cobre front-end completo, carrinho, rate limit, ordenação, cache, UX e guias técnicos."
todos: []
isProject: false
---

# Plano: Vitrine loja funcional (padrão grandes players)

## Objetivo

Tornar a **vitrine central** (`/loja`) totalmente funcional: listagem de produtos, detalhe, carrinho, cadastro, login, checkout e pós-compra, com **desempenho**, **segurança**, **disponibilidade** e **experiência** alinhados aos grandes marketplaces (Amazon, Mercado Livre). A API em [app/api/v1/loja.py](app/api/v1/loja.py) já atende o fluxo; falta implementar o front (templates + JS) e reforçar backend onde necessário.

---

## 1. Situação atual (resumo da análise)

| Área | O que existe | O que falta |
|------|----------------|-------------|
| **API** | GET categorias, GET anuncios (filtros, paginação), GET anuncios/{id}, POST cadastro/login, GET/PUT minha-conta, endereços, meus-pedidos, POST checkout. | Ordenação configurável (preço, nome); rate limit em endpoints públicos; mapeamento slug→categoria_id na rota categoria. |
| **Templates** | base_loja.html (navbar), index/produto/cadastro/login/carrinho/checkout/obrigado/meus_pedidos/minha_conta com títulos e placeholders. | Formulários; JS que chame a API; renderização de listagem/produto/carrinho; estado logado/visitante no header. |
| **Carrinho** | Conceito (localStorage/sessão). | UI de itens e totais; persistência opcional (API carrinho) ou só localStorage; integração com checkout. |
| **Segurança** | Pydantic valida inputs; JWT em cookie httponly; respostas sem senha. | Rate limit em login/cadastro/checkout e GETs públicos; escape XSS em avaliações/textos; CSRF se forms HTML. |
| **UX** | Página obrigado e logout. | Feedback de erros (estoque, 400); número do pedido pós-compra; navegação por categoria/busca; responsividade e acessibilidade. |

**Conclusão:** Back-end do fluxo está implementado; **front (templates + JS) não implementa nenhum passo**. Vitrine inutilizável pelo usuário final até o front e os reforços de segurança/performance serem feitos.

---

## 2. Princípios (grandes players, desempenho, segurança, disponibilidade, UX)

- **Desempenho:** Listagem com paginação e lazy load de imagens; cache HTTP (Cache-Control) para categorias e listagem curta; resposta da API enxuta (evitar N+1); ordenação e filtros no backend.
- **Segurança:** Rate limit em login, cadastro e checkout (e opcionalmente em GET /anuncios por IP); sanitização/escape de conteúdo gerado pelo usuário (avaliações, nome); cookie consumidor com SameSite e Secure em produção; não expor IDs internos desnecessários.
- **Disponibilidade:** Tratamento de erro da API no front (retry suave, mensagem amigável); health da aplicação já cobre a vitrine; evitar dependências síncronas que derrubem a página (ex.: fallback se API falhar).
- **UX comprador:** Navegação clara (categorias, busca); cards de produto com preço, imagem, estoque “disponível”; carrinho visível (contador no header); checkout em poucos passos; confirmação com número do pedido e link para “Meus pedidos”; mensagens de erro claras (ex.: “Produto X sem estoque”).
- **UX CA:** Já coberta em “Minha loja” (/negocio/marketplace/minha-loja). Na vitrine, o CA não é ator; garantir apenas que anúncios e lojas ativas apareçam corretamente e que pedidos/notificações sigam o [plano_marketplace.md](.cursor/plans/plano_marketplace.md).

---

## 3. Blocos de trabalho

### 3.1 Front-end vitrine (templates + JS)

**Base e navegação**

- **base_loja.html:** Incluir JS da vitrine (ex.: `loja.js` ou `vitrine.js` em `app/static/js/`). Header: exibir “Entrar” + “Minha conta” + “Meus pedidos” + “Carrinho” quando visitante; quando logado, trocar “Entrar” por “Sair” e nome/email (opcional). Contador de itens no carrinho no ícone (ler de localStorage ou estado).
- **Categorias no header ou sidebar:** GET `/api/v1/loja/categorias` e montar menu ou dropdown; link para `/loja/categoria/{slug}`. Na rota categoria, obter `categoria_id` a partir do slug (buscar categoria por slug no backend ou passar no contexto) e chamar GET `/anuncios?categoria_id=X`.

**Listagem (/loja, /loja/categoria/{slug}, /loja/busca)**

- **index.html:** JS ao carregar: ler `categoria_slug` ou `q` (busca) do contexto (ou query string); chamar GET `/api/v1/loja/anuncios` com `categoria_id` (se houver), `q` (se houver), `skip`, `limit`. Renderizar grid de cards (imagem, título, preço promocional ou original, loja, link para `/loja/produto/{id}`). Paginação “Carregar mais” ou páginas (manter `skip`/`limit`). Placeholder de imagem se não houver; lazy load com `loading="lazy"`.
- **Busca:** Rota `/loja/busca` com query `q`; mesma listagem com parâmetro `q` na API.

**Detalhe do produto (/loja/produto/{id})**

- **produto.html:** JS com `anuncio_id` da rota; GET `/api/v1/loja/anuncios/{id}`. Exibir galeria (imagens), título, descrição, preço, loja, estoque (“Disponível” / “Últimas unidades”), botão “Adicionar ao carrinho” (quantidade). Ao adicionar: atualizar localStorage (estrutura ex.: `[{ anuncio_id, quantidade, titulo, preco, loja_id }]`) e contador do header; opcionalmente redirecionar para carrinho ou mostrar toast.

**Carrinho (/loja/carrinho)**

- Listar itens do localStorage (anuncio_id, quantidade, título, preço, loja_id). Calcular subtotal por item e total. Botão “Remover” por item; “Alterar quantidade” (validar máx. estoque se possível via API). **Importante:** checkout atual exige um único `loja_id` por pedido; se o carrinho tiver itens de mais de uma loja, exibir agrupado por loja e “Finalizar compra” por loja (um checkout por loja) ou desabilitar mix e orientar o usuário (conforme [plano_marketplace.md](.cursor/plans/plano_marketplace.md) — carrinho multi-loja a definir). Botão “Ir ao checkout” levando para `/loja/checkout` com query ou estado da loja escolhida.

**Checkout (/loja/checkout)**

- Formulário: nome, e-mail, telefone, documento (opcional), endereço de entrega (texto ou campos), tipo de entrega. Itens do carrinho (loja única) em resumo; total. Ao enviar: montar body `PedidoCheckoutCreate` (loja_id, itens, comprador_*, endereco_entrega, tipo_entrega, desconto, taxa_entrega) e POST `/api/v1/loja/checkout`. Se 200: limpar carrinho (localStorage), redirecionar para `/loja/obrigado?pedido_id={id}`. Se 400: exibir `detail` (ex.: “Estoque insuficiente para o anúncio X”). Se 401/500: mensagem genérica e retry.

**Obrigado (/loja/obrigado)**

- Ler `pedido_id` da query; exibir “Obrigado! Seu pedido #X foi recebido.” e link para “Meus pedidos” e “Voltar à loja”.

**Cadastro (/loja/cadastro)**

- Formulário: nome, e-mail, senha, confirmação de senha, telefone (opcional), documento (opcional), checkbox “Aceito os termos”. POST `/api/v1/loja/cadastro`. Sucesso: redirecionar para login ou auto-login (se a API retornar token). Erro 400: exibir `detail` (ex.: “E-mail já cadastrado”).

**Login (/loja/login)**

- Formulário: e-mail, senha. POST `/api/v1/loja/login`. Sucesso: salvar cookie (já feito pela API se chamada com credentials); redirecionar para `/loja` ou `next`. Erro 401: “E-mail ou senha incorretos”.

**Minha conta (/loja/minha-conta)**

- GET `/api/v1/loja/minha-conta` (com cookie). Exibir dados; formulário de edição (nome, telefone, documento) com PUT `/minha-conta`. Endereços: GET/POST endereços; listar e adicionar.

**Meus pedidos (/loja/meus-pedidos)**

- GET `/api/v1/loja/meus-pedidos` (com cookie). Tabela ou cards: número, data, total, status; link para detalhe (se houver endpoint ou expandir na própria página).

**Arquivos sugeridos**

- [app/templates/loja/base_loja.html](app/templates/loja/base_loja.html) — header condicional, inclusão do JS.
- [app/templates/loja/index.html](app/templates/loja/index.html) — listagem.
- [app/templates/loja/produto.html](app/templates/loja/produto.html) — detalhe + adicionar ao carrinho.
- [app/templates/loja/carrinho.html](app/templates/loja/carrinho.html) — itens e totais.
- [app/templates/loja/checkout.html](app/templates/loja/checkout.html) — formulário e envio.
- [app/templates/loja/obrigado.html](app/templates/loja/obrigado.html) — pedido_id na URL.
- [app/templates/loja/cadastro.html](app/templates/loja/cadastro.html), [app/templates/loja/login.html](app/templates/loja/login.html), [app/templates/loja/minha_conta.html](app/templates/loja/minha_conta.html), [app/templates/loja/meus_pedidos.html](app/templates/loja/meus_pedidos.html) — formulários e listagens.
- **Novo:** [app/static/js/vitrine.js](app/static/js/vitrine.js) (ou módulos separados: vitrine-listagem.js, vitrine-produto.js, vitrine-carrinho.js, vitrine-checkout.js) — chamadas à API, renderização, carrinho em localStorage, tratamento de erros.

---

### 3.2 API — ajustes e melhorias

- **Ordenação de anúncios:** Adicionar query `sort` (ex.: `preco_asc`, `preco_desc`, `nome`, `recent`) em GET `/anuncios`; aplicar `order_by` no backend (ex.: `AnuncioPlataforma.preco_promocional`, `AnuncioPlataforma.titulo`, `AnuncioPlataforma.updated_at`).
- **Categoria por slug:** Rota HTML `/loja/categoria/{slug}` precisa de `categoria_id` para o front. Opção 1: endpoint GET `/api/v1/loja/categorias?slug=X` ou GET `/api/v1/loja/categorias/by-slug/{slug}` retornando uma categoria; front chama depois GET `/anuncios?categoria_id=Y`. Opção 2: no main.py, na rota da categoria, buscar categoria por slug e passar `categoria_id` no contexto do template.
- **Resposta de listagem:** Garantir que não haja N+1 (joins com loja já usados). Campos mínimos no listagem (id, titulo, preco_original, preco_promocional, imagens, slug_loja, nome_loja) já estão em `AnuncioVitrineResponse`.
- **Paginação:** Já existe `skip` e `limit`; manter `total` para o front exibir “X resultados” e páginas.

Arquivo: [app/api/v1/loja.py](app/api/v1/loja.py).

---

### 3.3 Segurança

- **Rate limit:** Aplicar limite por IP (e por usuário quando logado) em: POST `/api/v1/loja/login`, POST `/api/v1/loja/cadastro`, POST `/api/v1/loja/checkout`. Opcional: limite em GET `/anuncios` e GET `/anuncios/{id}` para reduzir scraping/abuso. Usar middleware existente ou decorator (ex.: `check_rate_limit` ou novo `rate_limit_loja`) com Redis ou in-memory; retornar 429 com `Retry-After`.
- **XSS:** Garantir que campos de texto vindos do usuário (avaliação, nome exibido) sejam escapados no front ao renderizar em HTML. Se a API devolver HTML, não confiar; se devolver texto puro, usar `textContent` ou escape no template (Jinja2 escapa por padrão; em JS, não usar `innerHTML` com dados da API sem sanitização).
- **CSRF:** Se no futuro houver formulários HTML que postem para a mesma origem (ex.: formulário de checkout em HTML puro), adicionar token CSRF. Enquanto o checkout for via `fetch`/JSON com cookie, o próprio SameSite do cookie mitiga; documentar que formulários submetidos por JS com credentials incluem o cookie.

Arquivos: [app/api/v1/loja.py](app/api/v1/loja.py), eventual middleware em [app/core/](app/core/), [app/main.py](app/main.py) (registro de rotas da loja).

---

### 3.4 Desempenho

- **Cache HTTP:** GET `/api/v1/loja/categorias` e GET `/api/v1/loja/anuncios` (sem parâmetros de sessão) podem ter `Cache-Control: public, max-age=60` (1 minuto) ou maior para reduzir carga. Evitar cache em respostas com dados por usuário (minha-conta, meus-pedidos).
- **Imagens:** Anúncios com `imagens` (URLs): no front, usar `loading="lazy"` e dimensões fixas para evitar layout shift. Considerar CDN ou storage com URLs estáveis se ainda não houver.
- **Lazy load na listagem:** Carregar apenas a primeira página; “Carregar mais” ou paginação sob demanda.

---

### 3.5 Disponibilidade e resiliência

- **Front:** Em chamadas à API, tratar timeout e status 5xx: exibir mensagem “Temporariamente indisponível. Tente novamente.” e botão de retry. Não travar a página se a listagem falhar (ex.: mostrar lista vazia com mensagem).
- **Backend:** Health check já cobre a aplicação; garantir que o worker Celery (NF-e e notificação pós-checkout) não bloqueie a resposta do checkout (já é assíncrono com `.delay()`).
- **Checkout:** Se o checkout retornar 500, o front não deve limpar o carrinho; permitir nova tentativa.

---

### 3.6 Experiência do usuário (comprador)

- **Navegação:** Breadcrumb em listagem (Home > Categoria X) e no produto (Home > Categoria > Produto). Busca visível no header (input + botão ou Enter).
- **Feedback:** Spinner ou skeleton durante carregamento; mensagens de erro claras (estoque, “E-mail já cadastrado”, “Dados inválidos”); toast ou inline para “Adicionado ao carrinho”.
- **Mobile:** Layout responsivo (grid de produtos em colunas adaptáveis); formulários e botões com área de toque adequada; header colapsável se necessário.
- **Acessibilidade:** Labels em inputs; contraste; foco visível; semântica (headings, landmarks). Evitar dependência só de cor para informação.

---

### 3.7 CA (Cliente Administrador)

- O CA não usa a vitrine como comprador; usa “Minha loja” para gestão. Garantir apenas que: (1) anúncios publicados e lojas ativas apareçam na vitrine; (2) após checkout, o CA receba notificação e veja pedido/extrato conforme [plano_marketplace.md](.cursor/plans/plano_marketplace.md). Nenhuma alteração específica de UX do CA na vitrine além da consistência de dados.

---

## 4. Ordem de implementação sugerida

1. **Base e listagem:** base_loja.html (header condicional, JS global), vitrine.js (fetch de categorias e anúncios), index.html (renderização de cards e paginação). Rota categoria: passar `categoria_id` ou endpoint by-slug.
2. **Detalhe do produto:** produto.html + JS (GET anuncio/{id}, botão adicionar ao carrinho, atualizar localStorage e contador).
3. **Carrinho:** carrinho.html + JS (ler localStorage, exibir itens e totais, remover/alterar quantidade). Regra: um checkout por loja (exibir aviso se houver itens de várias lojas e orientar).
4. **Checkout:** checkout.html + formulário + JS (montar body, POST checkout, tratar 200/400/5xx, redirecionar para obrigado com pedido_id).
5. **Obrigado:** obrigado.html com pedido_id na URL e link para meus pedidos.
6. **Cadastro e login:** formulários e POST; header com estado logado/visitante.
7. **Minha conta e meus pedidos:** formulário de edição e listagem de pedidos.
8. **API:** ordenação (sort), categoria by-slug ou contexto na rota.
9. **Segurança:** rate limit em login, cadastro e checkout.
10. **Desempenho e polish:** cache HTTP, lazy load, mensagens de erro e retry, responsividade e acessibilidade.

---

## 5. Arquivos envolvidos (resumo)

| Área | Arquivos |
|------|----------|
| Templates loja | app/templates/loja/*.html (base, index, produto, carrinho, checkout, obrigado, cadastro, login, minha_conta, meus_pedidos) |
| JS vitrine | app/static/js/vitrine.js (ou módulos) |
| API loja | app/api/v1/loja.py (ordenação, categoria by-slug, rate limit) |
| Rotas HTML | main.py (passar categoria_id ou slug para template categoria/busca) |
| Segurança | app/core/ ou middleware (rate limit); templates (escape/XSS) |
| Documentação | MAPA_DO_SISTEMA.md § 12 (vitrine funcional); MAPA_DE_API.md Seção 19 |

---

## 6. Referências

- [plano_marketplace.md](.cursor/plans/plano_marketplace.md) — ecossistema, checkout por loja, carrinho multi-loja (a definir).
- [MAPA_DO_SISTEMA.md](MAPA_SISTEMA/MAPA_DO_SISTEMA.md) § 12 — Módulo Marketplace e Vitrine.
- [app/api/v1/loja.py](app/api/v1/loja.py) — endpoints atuais da vitrine.

---

**Conclusão:** O plano cobre a vitrine do estado atual (API pronta, front esqueleto) até uma loja funcional, segura e com boa experiência, alinhada a boas práticas de desempenho, segurança e disponibilidade, e preparada para evoluções (pagamento no checkout, carrinho multi-loja) descritas no plano marketplace.
