# Homepage Loja — 7 blocos estratégicos: mapeamento desktop e mobile

## Objetivo

Garantir que o plano da homepage em 7 blocos (e os 10 passos visuais) esteja **100% mapeado para desktop e mobile**, sem lacunas de responsividade, e que a implementação inclua explicitamente cada breakpoint onde houver comportamento distinto.

---

## Breakpoints de referência (usados no código atual)

| Breakpoint | Uso no projeto |
|------------|----------------|
| **575px**  | Faixa destaques (slide menor), grid lojas 1 col, trust 1 col |
| **576px**  | Listagem (padding), Bootstrap col-sm |
| **767px**  | Hero 1 col, trust 2 cols, listagem/produto CTA |
| **768px**  | Header (busca maior, nav-belt), section-block padding, base_loja nav-fill order |
| **991px**  | Grid lojas 2 cols |
| **992px**  | Listagem padding, Bootstrap col-lg (4 cols) |

**Recomendação:** Unificar onde fizer sentido: usar **768px** para “tablet/desktop” e **576px** para “mobile estreito” de forma consistente entre `loja.css` e `base_loja.html` (hoje base_loja usa 768px, loja.css usa 767px no hero — pode manter 767px para “até mobile” se desejado).

---

## Ordem visual completa da homepage (10 passos)

1. **HEADER** (busca dominante)  
2. **CATEGORIAS**  
3. **HERO**  
4. **PRODUTOS EM DESTAQUE** (faixa/carrossel)  
5. **OFERTAS DA SEMANA**  
6. **MAIS PROCURADOS**  
7. **TODOS OS PRODUTOS** (grid principal)  
8. **LOJAS EM DESTAQUE**  
9. **BLOCO DE CONFIANÇA**  
10. **FOOTER**

---

## Mapeamento por bloco: Desktop vs Mobile e lacunas

### 1. Header (busca dominante)

| Contexto | Comportamento atual | Arquivo | Lacuna? |
|----------|---------------------|--------|---------|
| **Desktop (≥768px)** | Nav-belt em linha; busca max-width 700px; min-height 80px; busca 48px altura | loja.css, base_loja | Não |
| **Mobile (&lt;768px)** | base_loja: `.loja-nav-fill { order: 3; width: 100%; }` — busca vai para baixo e ocupa largura total | base_loja inline | **Sim (menor):** sem media para logo/nav em telas muito estreitas (&lt;360px); possível corte de texto “Explorar”/“Conta” |
| **Touch** | Botão busca min-height 44px (loja.css) | loja.css | Não |

**Ação no plano:** Incluir no escopo: (a) manter busca como elemento mais largo no topo em desktop; (b) em mobile, garantir que logo + ícones não quebrem (ex.: min-width no nav-left, ou esconder texto em &lt;360px só ícones); (c) opcional: `-webkit-overflow-scrolling: touch` se houver scroll horizontal em algum subelemento do header.

---

### 2. Barra de categorias

| Contexto | Comportamento atual | Arquivo | Lacuna? |
|----------|---------------------|--------|---------|
| **Desktop** | Strip branca; chips em linha; overflow-x: auto (scroll se muitos) | loja.css | Não |
| **Mobile** | Mesmo: lista horizontal com scroll (overflow-x: auto) | loja.css | **Sim (menor):** falta `-webkit-overflow-scrolling: touch` para scroll suave em iOS; sem scroll-snap (opcional) |
| **Acessibilidade** | Chips com padding e hit area razoável | — | Ok |

**Ação no plano:** (a) Adicionar em `.loja-categorias-list`: `-webkit-overflow-scrolling: touch`. (b) Opcional: `scroll-snap-type: x proximity` e `scroll-snap-align: start` nos chips para comportamento “prateleira” no mobile.

---

### 3. Hero principal

| Contexto | Comportamento atual | Arquivo | Lacuna? |
|----------|---------------------|--------|---------|
| **Desktop (≥768px)** | Grid 1.2fr 0.8fr; copy + banner lado a lado; min-height 260px | loja.css | Não |
| **Mobile (≤767px)** | Grid 1fr; banner abaixo do copy; min-height 0; h1 1.65rem; banner min-height 120px; padding reduzido | loja.css | Não |
| **Touch** | Áreas de toque nos botões (padding suficiente) | — | Ok |

**Ação no plano:** Nenhuma lacuna de responsividade; ao refinar visual (gradient, sombra), manter os media 767px.

---

### 4. Produtos em destaque (faixa / carrossel)

| Contexto | Comportamento atual | Arquivo | Lacuna? |
|----------|---------------------|--------|---------|
| **Desktop** | Slides 180px; scroll horizontal; scroll-snap-type: x mandatory | loja.css + index inline | Não |
| **Mobile (≤575px)** | Slides 155px; min-height card 220px; fontes menores (título, preço, pill) | loja.css | Não |
| **Touch** | index: `-webkit-overflow-scrolling: touch` no faixa-inner | index.html | Ok |

**Ação no plano:** Nenhuma lacuna; garantir que, ao alterar estilos da faixa (fundo “prateleira”), os media 575px continuem aplicados.

---

### 5A. Ofertas da semana | 5B. Mais procurados

| Contexto | Comportamento atual | Arquivo | Lacuna? |
|----------|---------------------|--------|---------|
| **Desktop (≥992px)** | 4 col (col-lg-3) | index + Bootstrap | Não |
| **Tablet (768–991px)** | 3 col (col-md-4) | index + Bootstrap | Não |
| **Mobile (&lt;768px)** | 2 col (col-6) | index + Bootstrap | Não |
| **Seção (bloco)** | section-block: padding 1.5rem / 2rem; container padding 1rem / 1.5rem conforme 768px | loja.css | Não |

**Ação no plano:** Nenhuma lacuna; ao dar “leve diferenciação de fundo” entre ofertas e em alta, garantir que seja por classe (ex.: .loja-ofertas vs .loja-em-alta) sem quebrar em mobile.

---

### 6. Grid principal (Todos os produtos)

| Contexto | Comportamento atual | Arquivo | Lacuna? |
|----------|---------------------|--------|---------|
| **Desktop** | .loja-card-listagem-wrap padding 2rem; body 1rem/1.25rem/1.5rem em 576/768/992 | loja.css | Não |
| **Mobile** | Header da listagem: flex-wrap (título + select ordenar podem stackar); body padding 1rem | loja.css | **Sim (menor):** em telas muito estreitas o “Ordenar: [select]” pode ficar apertado; não há media específico para .loja-card-listagem-header em &lt;576px |
| **Grid de cards** | col-6 / col-md-4 / col-lg-3 (igual ofertas/em alta) | index | Não |

**Ação no plano:** (a) Considerar em &lt;576px: título em linha inteira e select em linha seguinte, ou label “Ordenar” abreviado. (b) Garantir que “Carregar mais” tenha largura mínima confortável em mobile.

---

### 7. Lojas em destaque

| Contexto | Comportamento atual | Arquivo | Lacuna? |
|----------|---------------------|--------|---------|
| **Desktop (≥992px)** | 4 col (grid-template-columns: repeat(4, 1fr)); gap 1rem | loja.css | Não |
| **Tablet (576–991px)** | 2 col (@media max-width: 991px) | loja.css | Não |
| **Mobile (≤575px)** | 1 col | loja.css | Não |

**Ação no plano:** Nenhuma lacuna de layout; ao refinar card (padding 18px, hover), manter os três breakpoints.

---

### 8. Bloco de confiança

| Contexto | Comportamento atual | Arquivo | Lacuna? |
|----------|---------------------|--------|---------|
| **Desktop** | 4 col (grid); cards em linha | loja.css | Não |
| **Tablet (≤767px)** | 2 col | loja.css | Não |
| **Mobile (≤575px)** | 1 col | loja.css | Não |
| **Conteúdo** | Ícones + texto; font-size reduzido em .loja-beneficio-text | — | Ok |

**Ação no plano:** Nenhuma lacuna; em mobile o bloco fica mais discreto (1 col), alinhado à “área de confiança mais discreta”.

---

### 9. Footer

| Contexto | Comportamento atual | Arquivo | Lacuna? |
|----------|---------------------|--------|---------|
| **Desktop** | .container .d-flex .flex-wrap; duas áreas (esquerda / direita) | base_loja | Não |
| **Mobile** | flex-wrap faz itens quebrarem; não há media específico para footer | base_loja | **Sim (menor):** em &lt;360px links e créditos podem ficar muito apertados; gap já existe (gap-2) |
| **Acessibilidade** | Links e texto legíveis | — | Ok |

**Ação no plano:** (a) Opcional: @media (max-width: 575px) ou 480px para footer: flex-direction column, align-items center ou stack vertical com gap. (b) Garantir que nenhum texto do footer tenha min-width que force overflow horizontal.

---

### 10. Main (wrapper geral) e Body

| Contexto | Comportamento atual | Arquivo | Lacuna? |
|----------|---------------------|--------|---------|
| **Desktop** | main.loja-main padding-top 1.5rem, bottom 3rem (768px) | loja.css | Não |
| **Mobile** | padding-top 1.25rem, bottom 2.5rem | loja.css | Não |
| **Body** | body.loja-page background; viewport já em base | base_loja | Não |

**Ação no plano:** Nenhuma lacuna.

---

## Resumo de lacunas e ações

| # | Bloco | Lacuna | Ação recomendada |
|---|--------|--------|-------------------|
| 1 | Header | Mobile muito estreito: logo/nav podem apertar | Media &lt;360px ou 400px: reduzir logo, ou só ícones nos nav-items; garantir que busca continue dominante |
| 2 | Categorias | Scroll em iOS menos suave | Adicionar -webkit-overflow-scrolling: touch em .loja-categorias-list |
| 6 | Grid principal | Header “Ordenar” em telas muito estreitas | Media &lt;576px: stack título/select ou abreviar label; botão “Carregar mais” full-width ou min-width |
| 9 | Footer | Muito estreito: itens podem colar | Opcional: media &lt;575px para footer em coluna ou centralizado |

Demais blocos (Hero, Faixa, Ofertas, Em alta, Lojas, Confiança, Main) estão cobertos por breakpoints existentes sem lacuna identificada.

---

## Checklist de implementação (desktop + mobile)

Ao executar o guia visual e os 7 blocos:

- [ ] **Paleta e fundo:** variáveis e body/main — verificar em 320px e 1920px (sem overflow-x).
- [ ] **Header:** desktop (busca mais larga); mobile (order 3, full width); &lt;360px (logo/nav sem quebrar).
- [ ] **Categorias:** desktop e mobile com scroll horizontal; adicionar -webkit-overflow-scrolling: touch.
- [ ] **Hero:** desktop 2 col; ≤767px 1 col, tipografia e padding já definidos.
- [ ] **Faixa destaques:** desktop 180px slides; ≤575px 155px e fontes menores.
- [ ] **Ofertas / Em alta:** grid col-6 / col-md-4 / col-lg-3 em todos os breakpoints; blocos com padding responsivo.
- [ ] **Listagem:** wrap e padding 576/768/992; header (título + ordenar) em mobile; “Carregar mais” acessível.
- [ ] **Lojas em destaque:** 4 / 2 / 1 col (992, 991, 575).
- [ ] **Confiança:** 4 / 2 / 1 col (767, 575).
- [ ] **Footer:** flex-wrap; opcional media para coluna em &lt;575px.
- [ ] **Página de produto** (fora da home): já possui 767px para galeria e CTA; manter.

---

## Conclusão

O plano está **mapeado para desktop e mobile** para os 10 passos. As únicas lacunas são **menores** e concentradas em:

1. Header em viewports muito estreitos (&lt;360px).  
2. Scroll da barra de categorias em iOS (uma linha de CSS).  
3. Header do grid “Todos os produtos” em mobile estreito (ordenar + título).  
4. Footer em mobile muito estreito (opcional).

Incluindo as ações recomendadas na implementação, **não há lacuna sem cobertura** no plano.
