# SEO e visibilidade do Marketplace

Este documento descreve a configuração de **visibilidade em buscas (SEO)** e **compartilhamento em redes sociais** do Ibix Marketplace.

---

## 1. Configuração em produção

- **APP_URL:** Em produção, defina a variável `APP_URL` no `.env` com a URL pública do site (ex.: `https://www.ibix.com.br`), **sem barra no final**.
- Ela é usada para:
  - **Canonical** e **Open Graph** (og:url) em todas as páginas da loja/vitrine.
  - **sitemap.xml** e **robots.txt** (linha `Sitemap:`), para que os motores de busca usem o domínio correto.

Se `APP_URL` não estiver definida, o sistema usa a URL da requisição (`request.base_url`), que pode ser incorreta em ambientes com proxy reverso.

---

## 2. Arquitetura SEO

A **página principal indexável** é a **vitrine/loja** (raiz `/`), servida pelo template `loja/base_loja.html`. O foco de SEO é o marketplace (compras online), não o sistema PDV/SaaS.

### 2.1 SEO técnico (base_loja.html)

- **Canonical:** `link rel="canonical"` com URL absoluta usando `base_url`
- **Meta description:** Dinâmica por página via bloco `{% block seo_description %}`
- **Keywords:** Marketplace, compras online, produtos, ofertas
- **Open Graph:** `og:type`, `og:title`, `og:description`, `og:url`, `og:image`, `og:locale`, `og:site_name`
- **Twitter Card:** `twitter:card`, `twitter:title`, `twitter:description`, `twitter:image`
- **JSON-LD:** `WebSite` com `SearchAction` (busca de produtos) + `Organization`

### 2.2 SEO por página

| Página | Template | Description |
|--------|----------|-------------|
| Vitrine (/) | `loja/index.html` | "Compre em várias lojas..." (dinâmico por categoria/busca) |
| Produto | `loja/produto.html` | "{titulo} - Compre na Ibix..." + JSON-LD Product |
| Cadastro | `loja/cadastro.html` | "Crie sua conta gratuita..." |
| Login | `loja/login.html` | "Acesse sua conta..." |
| Categoria | `loja/index.html` | "Produtos de {categoria}..." |

### 2.3 SSR parcial (produto)

A rota `/loja/produto/{id}` busca dados do anúncio no servidor e passa ao template:
- `ssr_titulo`, `ssr_descricao`, `ssr_imagem`, `ssr_preco` — usados em meta tags e `<noscript>`
- JSON-LD `Product` com preço, disponibilidade e imagem para rich results no Google

### 2.4 Sitemap dinâmico

`GET /sitemap.xml` inclui:
- Páginas estáticas (/, /loja, /login, /cadastro, etc.)
- **Categorias ativas** (`/loja/categoria/{slug}`)
- **Produtos publicados** (`/loja/produto/{id}`) — até 5.000 anúncios

### 2.5 robots.txt

`GET /robots.txt` permite indexação de páginas públicas e bloqueia `/dashboard`, `/api/`, `/admin/`.

### 2.6 Redes sociais (Open Graph e Twitter Card)

- **og:image:** Logo em `static/img/landing/logoSfundo.png`. Para preview ideal, use uma imagem 1200×630 px.
- **og:site_name:** "Ibix" (vitrine)
- **Twitter Card:** `summary_large_image`

### 2.7 Performance (Core Web Vitals)

- `dashboard.css` carregado como não-bloqueante (`media="print" onload`)
- Scripts com `defer` para não bloquear renderização
- Preload do CSS crítico (`loja.css`)
- **Importante:** Otimizar `logoSfundo.png` (comprimir/converter para WebP) — atualmente muito grande

### 2.8 Página 404

Handler global retorna HTML amigável para browsers e JSON para APIs. Template: `errors/404.html`.

---

## 3. Próximos passos (fora do código)

1. **Google Search Console:** Adicionar propriedade `https://www.ibix.com.br`, verificar DNS/TXT, enviar sitemap
2. **Google Analytics / GA4:** Instalar tag para acompanhar tráfego orgânico
3. **Imagem OG:** Criar imagem 1200×630 px com logo + "Marketplace - Compre em várias lojas"
4. **Facebook Debugger / Twitter Validator:** Testar cards após deploy
5. **Monitorar indexação:** Acompanhar no Search Console quantas páginas foram indexadas
6. **Google Merchant Center (futuro):** Para produtos aparecerem na aba Shopping do Google

---

## 4. Referência técnica

| Item | Valor |
|------|--------|
| Template base da loja | `app/templates/loja/base_loja.html` |
| Template da landing institucional | `app/templates/pages/landing.html` |
| Rotas SEO | `GET /`, `GET /robots.txt`, `GET /sitemap.xml` |
| Função base_url | `_landing_base_url(request)` em `main.py` |
| Contexto da loja | `_loja_context()` em `main.py` (inclui `base_url`) |
| Configuração | `app/core/config.py` → `settings.APP_URL` |
| Handler 404 | `not_found_handler()` em `main.py` |

---

## Documentos relacionados

- [Checklist Google, sitemap e Perfil de Negócio](CHECKLIST_GOOGLE_INDEXACAO_IBIX.md)
