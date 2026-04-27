# Contexto da Conversa — Áreas de Entrega, CEP e Modal

**Data:** 2026-03-23  
**Assunto:** Correções na página de Áreas de Entrega, fluxo CEP e padrão de modais (MAPA_DE_REGRAS)

---

## 1. Plano de implementação do CEP

O plano está em `MAPA_SISTEMA/MAPA_Frete_Transporte.md` (§ 8.8 e 8.9):
- **Áreas de abrangência:** tabela `loja_areas_entrega` (cidade, UF, taxa, prazo) por loja
- **Checkout com CEP estruturado:** ViaCEP no blur, campos estruturados, API `GET /loja/{id}/frete?cidade=X&uf=Y`
- **Cadastro:** SuperAdmin em `/negocio/marketplace/areas-entrega`

---

## 2. Problema: botão "Adicionar cidade" desativado

**Causas identificadas:**

1. **Bloco errado no template:** O template usava `{% block scripts %}` mas o `base.html` define `{% block extra_js %}`. O script nunca era renderizado.
2. **Token errado no getHeaders():** A página buscava `localStorage.getItem("access_token")` enquanto o PDV usa cookie `pdv_solumatica_token` ou `pdv_automscale_token`.

**Correções aplicadas:**
- Alterado para `{% block extra_js %}`
- `getHeaders()` passou a usar `getToken()` (cookie + sessionStorage do PDV) e `window.getAuthToken()`
- Adicionado `credentials: "include"` nas requisições fetch

---

## 3. Frete na vitrine

**Onde é configurado:** Não é hardcoded. Valores vêm da API:
- `GET /api/v1/loja/{loja_id}/frete` — regras gerais
- `GET /api/v1/loja/{loja_id}/frete?cidade=X&uf=Y` — taxa por cidade

**Fallback:** Quando não há áreas em `loja_areas_entrega`, a API usa `taxa_entrega_fixa` da loja para qualquer cidade.

---

## 4. Identificação da loja

- **id** (PK): principal em APIs e backend
- **slug**: filtros na vitrine (`loja_slug`)
- **cliente_id**: vínculo com estabelecimento (1:1)

CA/empresa fiscal **não é** loja automaticamente. Loja é configuração opcional em "Minha loja".

---

## 5. Modal não seguia MAPA_DE_REGRAS

**Regra obrigatória (MAPA_DE_REGRAS.md § Padrão de Modais):**
- ❌ Não usar Bootstrap Modal (`modal fade`, `data-bs-dismiss`, `bootstrap.Modal`)
- ✅ Usar CSS inline, `display: block/none`, `z-index: 10000`
- ✅ Id `modal{Nome}Custom`, funções `abrirModal{Nome}()` e `fecharModal{Nome}()`
- ✅ Expor no `window` para onclick em IIFE

**Correção aplicada:** Modal convertido para padrão CSS inline com `id="modalAreaCustom"`, `abrirModalArea()`, `fecharModalArea()`, `window.fecharModalArea`.

---

## 6. Fluxo de configuração de CEP

1. SuperAdmin acessa `/negocio/marketplace/areas-entrega`
2. Seleciona loja no dropdown (API `/marketplace/lojas`)
3. Clica "Adicionar cidade" → abre modal
4. Informa CEP auxiliar (ViaCEP preenche cidade/UF) ou digita manualmente
5. Informa taxa e prazo → Salvar
6. Registro em `loja_areas_entrega`

No checkout: comprador digita CEP → ViaCEP → cidade/UF → `GET /loja/{id}/frete?cidade=&uf=` → API retorna taxa ou indisponível.

---

## 7. Arquivos alterados

- `app/templates/marketplace/areas_entrega.html`
  - `{% block scripts %}` → `{% block extra_js %}`
  - `getHeaders()` com token PDV (cookie/sessionStorage)
  - Modal Bootstrap substituído por padrão CSS inline (MAPA_DE_REGRAS)
  - `credentials: "include"` em todas as fetches
  - Tratamento de erro melhorado em `loadLojas()`

---

## 8. Lojas cadastradas (consulta no banco)

```
Total: 1
id=1 | cliente_id=58 | nome_loja=Automscale | slug=Automscale | status=ativo
```

---

## 9. Referências

- MAPA_Frete_Transporte.md — plano CEP, áreas, ViaCEP
- MAPA_DE_REGRAS.md — padrão de modais (CSS inline)
- app/api/v1/loja.py — endpoint GET /{loja_id}/frete
- app/api/v1/marketplace.py — endpoints areas-entrega e lojas
