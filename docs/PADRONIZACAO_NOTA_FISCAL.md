# Padronização: Modelo e Formulário de Emissão de Nota Fiscal

**Objetivo:** Garantir que o **modelo** (DB), os **schemas** (API) e os **formulários** (tela Nova Nota + itens) estejam 100% alinhados e compatíveis com a NF-e (layout SEFAZ).

---

## 1. Checklist de conformidade

| Camada | Item | Status | Observação |
|--------|------|--------|------------|
| **Modelo** | Campos da capa (NotaFiscal) | ✅ | Completo; comentários corretos. |
| **Modelo** | Campos do item (NotaFiscalItem) | ✅ | NCM, CFOP, CST, PIS/COFINS, ICMS, etc. |
| **Modelo** | Enums (Tipo, Status, Origem, Ambiente) | ✅ | Status inclui RASCUNHO e ENVIADA. |
| **Schema** | StatusNotaEnum | ✅ | **Corrigido:** RASCUNHO e ENVIADA adicionados; default da capa é RASCUNHO. |
| **Schema** | NotaFiscalBase / Response | ✅ | **Corrigido:** pedido_id e origem_documento (OrigemDocumentoFiscalEnum) incluídos. |
| **Schema** | NotaFiscalCreate | ✅ | **Corrigido:** pedido_id e origem_documento opcionais; min_items → min_length (Pydantic v2). |
| **Form (Nova Nota)** | Campos da capa | ✅ | Série, natureza_operacao, ambiente, data_saida implementados no modal e no payload. |
| **Form (Nova Nota)** | Itens | ✅ | NCM, CFOP, origem (0–8), CST/CSOSN implementados; hint por regime (CRT) da empresa. |
| **Form ↔ API** | Cancelar nota | ✅ | **Corrigido:** API passou a aceitar **body** `{ "justificativa": "..." }` (CancelarNotaBody). |
| **Form ↔ API** | Status ao salvar nova nota | ✅ | **Corrigido:** payload envia **status: 'rascunho'** ao salvar nova nota. |

---

## 2. Tamanhos de campos (NF-e / SEFAZ)

| Campo | Layout comum | Nosso modelo | Ação |
|-------|----------------|--------------|------|
| NCM | 8 dígitos (ou 8+2) | String(10) | ✅ OK; pode aceitar 8 ou 10. |
| CFOP | 4 dígitos | String(10) | ✅ OK. |
| CST ICMS | 2–3 dígitos | String(5) | ✅ OK. |
| CSOSN | 3 dígitos | String(5) | ✅ OK. |
| Chave NF-e | 44 caracteres | String(44) | ✅ OK. |
| Número nota | 1–9 dígitos | String(20) | ✅ OK. |
| Série | 1–3 dígitos | String(10) | ✅ OK. |

Nenhuma alteração obrigatória no tamanho dos campos do modelo.

---

## 3. Ajustes realizados / a realizar

### 3.1 Schema (API) – alinhar com o modelo ✅ Feito

- **StatusNotaEnum no schema:** incluídos `RASCUNHO` e `ENVIADA`; criado `OrigemDocumentoFiscalEnum`.
- **NotaFiscalBase / Create / Response:** incluídos `pedido_id` e `origem_documento` (enum opcional); default de status é `RASCUNHO`.
- **CancelarNotaBody:** schema para body do cancelamento com `justificativa` (min_length=15).

### 3.2 Formulário “Nova Nota Fiscal”

- **Capa:**  
  - Manter número, data emissão, empresa, destinatário, tipo (NFe/NFCe).  
  - Incluir: **Série** (default "1"), **Natureza da operação** (opcional), **Ambiente** (homologação/produção), **Data de saída** (opcional).  
  - **Modelo:** continuar derivado do tipo (55/65) no front; não precisa campo separado se for automático.
- **Itens:**  
  - Incluir colunas/campos: **NCM**, **CFOP**, **Origem (0–8)**, **CST ICMS** ou **CSOSN** (conforme regime).  
  - Podem ser opcionais na tela mas recomendados para envio real; validação pode exigir antes de “Enviar”.

### 3.3 Comportamento ao salvar nova nota

- Enviar no payload **status: "rascunho"** quando o usuário clicar em “Salvar (criar rascunho)”.
- Ou: no backend, na rota de criação, forçar `status = RASCUNHO` quando não informado (e não permitir criar já “autorizado”).

### 3.4 Cancelamento (justificativa) ✅ Feito

- **Solução aplicada:** Backend passou a aceitar **body** com `{ "justificativa": "..." }` via schema `CancelarNotaBody`; o front já enviava assim, então o cancelamento passa a funcionar.

---

## 4. Resumo: modelo vs schema vs formulário

| Campo / aspecto | Modelo | Schema | Form Nova Nota |
|-----------------|--------|--------|-----------------|
| numero | ✅ | ✅ | ✅ |
| serie | ✅ | ✅ (default "1") | ✅ (campo Série, default "1") |
| tipo | ✅ | ✅ | ✅ |
| modelo | ✅ | ✅ | ✅ (derivado no JS) |
| data_emissao | ✅ | ✅ | ✅ |
| data_saida | ✅ | ✅ | ✅ |
| empresa_id | ✅ | ✅ | ✅ |
| cliente_id | ✅ | ✅ | ✅ |
| venda_id | ✅ | ✅ | ❌ (não usado na tela) |
| pedido_id | ✅ | ❌ | ❌ |
| emitido_por_id | ✅ | ✅ | ✅ (userId) |
| origem_documento | ✅ | ❌ | ❌ |
| valor_* | ✅ | ✅ | ✅ (total, produtos; outros zerados) |
| status | ✅ (RASCUNHO default) | ⚠️ (falta RASCUNHO/ENVIADA; default PENDENTE) | ✅ (envia status: 'rascunho') |
| ambiente | ✅ | ✅ | ✅ |
| natureza_operacao | ✅ | ✅ | ✅ |
| **Item: NCM** | ✅ | ✅ | ✅ |
| **Item: CFOP** | ✅ | ✅ | ✅ |
| **Item: CST/CSOSN** | ✅ | ✅ | ✅ |
| **Item: origem** | ✅ | ✅ | ✅ |

---

## 5. Ordem sugerida de implementação

1. **Schema:** Incluir RASCUNHO e ENVIADA no StatusNotaEnum; incluir pedido_id e origem_documento na base/response/create.
2. **API cancelar:** Aceitar justificativa no body (JSON); manter query como alternativa se desejar.
3. **Front salvar nova nota:** Enviar `status: "rascunho"` no payload.
4. **Form Nova Nota (capa):** Série (ou manter "1"), natureza da operação, ambiente, data de saída.
5. **Form Nova Nota (itens):** NCM, CFOP, origem, CST ou CSOSN (conforme regime do emitente).

Quando esses pontos estiverem implementados, o **modelo**, o **schema** e o **formulário** de emissão de nota fiscal estarão padronizados e prontos para envio real (com provedor e certificado do CA).
