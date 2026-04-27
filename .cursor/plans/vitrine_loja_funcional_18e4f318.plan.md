---
name: Vitrine loja funcional
overview: "Deixar a vitrine central (/loja) totalmente funcional no padrão dos grandes players: front-end completo (listagem, produto, carrinho, checkout, cadastro, login), ajustes na API (ordenação, categoria por slug), segurança (rate limit), desempenho e UX comprador/CA."
todos:
  - id: base-listagem
    content: Base loja (header condicional) + vitrine.js + listagem index e categoria
    status: completed
  - id: produto-carrinho
    content: Página produto (detalhe + adicionar ao carrinho) e página carrinho
    status: completed
  - id: checkout-obrigado
    content: Checkout (form + POST) e obrigado com pedido_id
    status: completed
  - id: auth-conta-pedidos
    content: Cadastro, login, minha-conta, meus-pedidos
    status: completed
  - id: api-sort-categoria
    content: "API: ordenação (sort) e categoria por slug"
    status: completed
  - id: seguranca-polish
    content: Rate limit (login/cadastro/checkout) e polish (cache, lazy load, erros)
    status: completed
isProject: false
---

# Plano: Vitrine loja funcional (padrão grandes players)

## Situação atual

- **API** em [app/api/v1/loja.py](app/api/v1/loja.py): GET categorias/anuncios, POST cadastro/login/checkout, minha-conta, meus-pedidos. Pronta.
- **Templates** em [app/templates/loja/](app/templates/loja/): base_loja.html e páginas (index, produto, cadastro, login, carrinho, checkout, etc.) são **esqueletos** — sem formulários e sem JS que chame a API.
- **Carrinho:** só conceito (localStorage); sem UI. **Segurança:** sem rate limit em login/cadastro/checkout.

Objetivo: vitrine utilizável fim a fim, com desempenho, segurança, disponibilidade e boa UX.

---

## 1. Front-end vitrine

- **base_loja.html:** Header condicional (Entrar/Sair, Minha conta, Carrinho com contador). Incluir [app/static/js/vitrine.js](app/static/js/vitrine.js) (criar).
- **Listagem** ([app/templates/loja/index.html](app/templates/loja/index.html)): JS chama GET `/api/v1/loja/anuncios` (categoria_id, q, skip, limit); renderiza grid de cards (imagem, título, preço, link para `/loja/produto/{id}`); paginação ou "Carregar mais". Rota categoria: passar `categoria_id` (buscar por slug no backend ou contexto).
- **Produto** ([app/templates/loja/produto.html](app/templates/loja/produto.html)): GET `/anuncios/{id}`; galeria, título, descrição, preço, botão "Adicionar ao carrinho" (atualizar localStorage e contador).
- **Carrinho** ([app/templates/loja/carrinho.html](app/templates/loja/carrinho.html)): Ler localStorage; listar itens, totais; remover/alterar qtd. Um checkout por loja (aviso se itens de várias lojas). Botão "Ir ao checkout".
- **Checkout** ([app/templates/loja/checkout.html](app/templates/loja/checkout.html)): Formulário (nome, email, telefone, endereço, tipo_entrega). Montar body e POST `/api/v1/loja/checkout`. 200: limpar carrinho, redirecionar `/loja/obrigado?pedido_id={id}`. 400/5xx: exibir detail e não limpar carrinho.
- **Obrigado:** Mostrar pedido_id; links "Meus pedidos" e "Voltar à loja".
- **Cadastro / Login / Minha conta / Meus pedidos:** Formulários e chamadas à API correspondentes; estado logado no header.

---

## 2. API — ajustes

- **Ordenação:** Query `sort` em GET `/anuncios` (ex.: preco_asc, preco_desc, nome, recent); aplicar no backend.
- **Categoria por slug:** Endpoint GET por slug ou, na rota HTML `/loja/categoria/{slug}`, buscar categoria e passar `categoria_id` no contexto para o template.

Arquivo: [app/api/v1/loja.py](app/api/v1/loja.py).

---

## 3. Segurança

- **Rate limit** por IP em POST `/loja/login`, `/loja/cadastro`, `/loja/checkout` (ex.: 5/min login, 3/min cadastro, 10/min checkout). Retornar 429 com Retry-After.
- **XSS:** Renderizar dados do usuário com escape (Jinja2 ou textContent no JS).

---

## 4. Desempenho e UX

- Cache-Control em GET categorias e GET anuncios (ex.: public, max-age=60).
- Imagens com `loading="lazy"`.
- Front: tratamento de timeout/5xx com mensagem e retry; feedback de erros (estoque, 400).

---

## 5. Ordem sugerida

1. Base + JS global + listagem (index + categoria).
2. Detalhe produto + adicionar ao carrinho.
3. Página carrinho.
4. Checkout + obrigado.
5. Cadastro, login, minha-conta, meus-pedidos.
6. API: sort e categoria por slug.
7. Rate limit e polish (cache, lazy load, mensagens).

---

## Arquivos principais


| Área      | Arquivos                                                                                                                                    |
| --------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| Templates | [app/templates/loja/](app/templates/loja/) (base, index, produto, carrinho, checkout, obrigado, cadastro, login, minha_conta, meus_pedidos) |
| JS        | [app/static/js/vitrine.js](app/static/js/vitrine.js) (novo)                                                                                 |
| API       | [app/api/v1/loja.py](app/api/v1/loja.py)                                                                                                    |
| Rotas     | [main.py](main.py) (contexto categoria/busca)                                                                                               |


Referência completa: [.cursor/plans/plano_vitrine_loja_funcional.md](.cursor/plans/plano_vitrine_loja_funcional.md).

---

## Checklist de verificação

### Front-end

- base_loja.html: header condicional (Entrar/Sair conforme login)
- base_loja.html: Minha conta, Meus pedidos, Carrinho com contador (badge)
- base_loja.html: inclui vitrine.js
- index.html: JS chama GET /api/v1/loja/anuncios (categoria_id, q, skip, limit, sort)
- index.html: grid de cards (imagem, título, preço, link produto)
- index.html: "Carregar mais" / paginação
- main.py: rota /loja/categoria/{slug} passa categoria_id e categoria_nome ao template
- produto.html: GET anuncios/{id}, galeria, título, descrição, preço
- produto.html: botão "Adicionar ao carrinho" (localStorage + contador)
- carrinho.html: listar itens do localStorage, totais
- carrinho.html: remover item, alterar quantidade
- carrinho.html: aviso quando itens de várias lojas
- carrinho.html: botão "Ir ao checkout"
- checkout.html: formulário (nome, email, telefone, documento, endereço, tipo_entrega)
- checkout.html: POST checkout; 200 → limpar carrinho e redirect obrigado?pedido_id=
- checkout.html: 400/5xx → exibir mensagem, não limpar carrinho
- obrigado.html: mostrar pedido_id; links Meus pedidos e Voltar à loja
- login.html / cadastro.html: formulários e POST à API
- minha_conta.html: GET/PUT minha-conta; formulário e salvamento
- meus_pedidos.html: GET meus-pedidos; listagem de pedidos

### API

- GET /anuncios: parâmetro sort (recent, preco_asc, preco_desc, nome)
- Categoria por slug: rota HTML resolve slug → categoria_id no contexto

### Segurança

- Rate limit POST /loja/login (5/min), 429 + Retry-After
- Rate limit POST /loja/cadastro (3/min), 429 + Retry-After
- Rate limit POST /loja/checkout (10/min), 429 + Retry-After
- XSS: Vitrine.escapeHtml no JS para dados da API

### Desempenho e UX

- Cache-Control public, max-age=60 em GET categorias e GET anuncios
- Imagens com loading="lazy"
- Tratamento de erros (mensagem em falhas de API / estoque / 400)

