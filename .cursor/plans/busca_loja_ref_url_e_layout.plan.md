# Plano único: Busca da loja funcional (ref URL + layout + ordem)

Objetivo: corrigir a busca da loja no estilo Mercado Livre — URL como ref, página de busca focada só em resultados, e na home “Todos os produtos” antes de “Mais procurados”.

---

## Arquivos

| Arquivo | Uso |
|---------|-----|
| [main.py](main.py) | Rota `GET /loja/busca`; passar `busca_ativa` e `busca_q` no contexto |
| [app/templates/loja/index.html](app/templates/loja/index.html) | Ordem das seções, condicionais `busca_ativa`, script (ref URL, título) |
| [app/templates/loja/base_loja.html](app/templates/loja/base_loja.html) | Formulário GET `/loja/busca` com `name="q"` (manter como está) |
| [app/api/v1/loja.py](app/api/v1/loja.py) | Sem alteração (já aceita `q`) |

---

## 1. Ordem das seções na home

**Trocar de posição:** “Todos os produtos” passa a vir **antes** de “Mais procurados”.

Em **index.html**, a ordem final das seções no HTML:

1. Barra de categorias  
2. Hero  
3. Destaques (faixa)  
4. Ofertas da semana  
5. **Todos os produtos** (`#loja-todos-produtos`)  
6. **Mais procurados** (`#loja-em-alta-section`)  
7. Lojas em destaque  
8. Bloco de confiança  

**Implementação:** Mover o bloco completo da seção “Todos os produtos” (até `</section>`) para **acima** do bloco “Mais procurados”. No script, a ordem de execução (loadOfertas, loadEmAlta, listagem principal) pode permanecer; apenas a ordem visual no DOM muda.

---

## 2. Ref na URL (busca funcional)

- **Formulário:** Manter `action="/loja/busca"` method GET, input `name="q"`. Submit leva a `/loja/busca?q=termo`.
- **Backend:** Manter leitura de `q` em `request.query_params` e `busca_q` no contexto.
- **Frontend (index.html, script):**
  - Definir `buscaQ` a partir da URL: `var buscaQ = (function(){ var p = new URLSearchParams(window.location.search); return p.get('q') || ''; })();` (ou equivalente), e usar em `load()` e no “Carregar mais”.
  - Ao carregar, se `window.location.pathname === '/loja/busca'`, preencher `document.getElementById('loja-header-busca-q').value` com o `q` da URL para o input do header refletir a ref.

---

## 3. Layout focado na busca (como Mercado Livre)

Quando há termo de busca (`q`), mostrar **apenas** a área de resultados (e opcionalmente o trust strip).

- **Backend (main.py):** Na rota `/loja/busca`, além de `busca_q=q`, passar `busca_ativa=True` quando `q` não estiver vazio.
- **Template (index.html):** Envolver as seções que devem sumir na busca em `{% if not busca_ativa %}` … `{% endif %}`:
  - Barra de categorias  
  - Hero  
  - Destaques  
  - Ofertas da semana  
  - Mais procurados (Em alta)  
  - Lojas em destaque  
- **Manter sempre visível:** “Todos os produtos” e o bloco de confiança (trust strip). Quando `busca_ativa`, a listagem é a primeira área de conteúdo abaixo do header.
- **Título na listagem:** Se `busca_ativa`, exibir título “Resultados para '{{ busca_q }}'” (ou “Nenhum resultado para '...'” quando total 0). Caso contrário, “Todos os produtos” / “{{ categoria_nome }}”.

---

## 4. Resumo de implementação

1. **index.html (HTML):** Trocar posição dos blocos “Todos os produtos” e “Mais procurados” (Todos os produtos em 5º, Mais procurados em 6º).  
2. **index.html (HTML):** Envolver categorias, hero, destaques, ofertas, em alta e lojas em `{% if not busca_ativa %} ... {% endif %}`.  
3. **index.html (HTML):** Título da listagem condicional: se `busca_ativa`, “Resultados para '...'”; senão, “Todos os produtos” / categoria.  
4. **index.html (script):** `buscaQ` lido da URL (`URLSearchParams`); sincronizar `#loja-header-busca-q` quando path for `/loja/busca`.  
5. **main.py:** Em `/loja/busca`, passar `busca_ativa=(q.strip() != '')` (e manter `busca_q=q`).  
6. **base_loja.html:** Sem mudança (form GET já correto).

Com isso, um único plano cobre: ordem das seções, busca com ref na URL e layout focado na busca.
