---
name: Motor tributário ICMS NF-e
overview: Implementar motor de decisão fiscal parametrizado que define automaticamente CFOP, origem, CST/CSOSN, alíquota ICMS e campos de ST por item da NF-e, com base em regras por empresa e contexto da operação. Sistema SaaS multi-tenant com isolamento por CA.
todos: []
isProject: false
---

# Motor tributário de ICMS para NF-e

## Contexto do sistema

**SaaS multi-tenant**: O sistema é SaaS com tenants. Cada tenant (Cliente Administrador – CA) tem ambiente protegido e separado dos demais. Regras fiscais, empresas e notas pertencem ao escopo do tenant; consultas e operações devem respeitar sempre o isolamento por CA. Empresa pertence a um cliente (CA); regras fiscais são por `empresa_id`, indiretamente isoladas por tenant.

**ST na fase 1**: Tratar ST como **simplificação operacional**, não como solução tributária definitiva. Os tipos `venda_interna_st` e `venda_interestadual_st` são suficientes para começar; no futuro ST poderá depender de NCM, CEST, UF, protocolos e regras estaduais.

---

## Objetivo

Centralizar no backend a decisão fiscal de CFOP, origem da mercadoria, CST/CSOSN, alíquota ICMS e campos de ST por item da NF-e, com base em regras parametrizadas por empresa e contexto da operação.

---

## Decisões de negócio fechadas

- CRT 1 e CRT 2 usam CSOSN no XML.
- CRT 3 usa CST no XML.
- O motor decide qual código ICMS usar; não usar classificação comercial resumida.
- Frontend não envia nem escolhe CST, CSOSN ou CFOP.
- Produto não é mais fonte final de CFOP/CST/CSOSN/origem; produto serve apenas como base de classificação (NCM, CEST).
- A decisão tributária depende de empresa + destinatário + operação + item.
- Se não houver regra aplicável, bloquear emissão.
- Se houver ambiguidade, bloquear emissão.
- Persistir auditoria da decisão aplicada por item.

---

## 1. Nova tabela `regras_fiscais_icms`

Tabela vinculada **apenas por `empresa_id`**. Isolamento por tenant garantido via empresa → cliente (CA).

### Campos de filtro (todos opcionais; null = qualquer)

- id, empresa_id, ativo, ordem_prioridade
- crt, tipo_operacao, tipo_destinatario, uf_destinatario
- ncm_prefix, ncm_exato, cest, cfop_filtro
- finalidade_emissao, consumidor_final, contribuinte_icms
- vigencia_inicio, vigencia_fim
- observacao_interna, created_at, updated_at

### Campos de resultado

- cfop, origem_mercadoria
- cst_icms, csosn
- aliquota_icms, modalidade_bc_icms, percentual_reducao_bc
- gera_icms_st, aliquota_icms_st, modalidade_bc_icms_st, percentual_mva_st
- permite_credito_icms

### Regras de consistência

- Nunca permitir `cst_icms` e `csosn` preenchidos ao mesmo tempo.
- Para CRT 1/2, regra não pode devolver `cst_icms`.
- Para CRT 3, regra não pode devolver `csosn`.

---

## 2. Enums

- **TipoOperacaoFiscalEnum**: venda_interna, venda_interestadual, venda_interna_st, venda_interestadual_st, qualquer
- **TipoDestinatarioFiscalEnum**: pf, pj, qualquer

---

## 3. Migration

- Criar migration Alembic para `regras_fiscais_icms`.
- Adicionar em `notas_fiscais_itens`:
  - regra_fiscal_icms_id (nullable)
  - motor_contexto_json (nullable)
  - motor_resultado_json (nullable)
  - motor_versao (nullable)
- Usar **JSONB** no PostgreSQL para `motor_contexto_json` e `motor_resultado_json`.

---

## 4. Motor tributário

Criar [app/services/fiscal/motor_tributario_icms.py](app/services/fiscal/motor_tributario_icms.py):

- dataclass ou schema `ContextoFiscalItem`
- dataclass ou schema `DecisaoFiscalItem`
- função principal para resolver a melhor regra

### Entrada do contexto (ContextoFiscalItem)

- empresa_id, crt, uf_emitente
- uf_destinatario (opcional)
- tipo_destinatario, tipo_operacao
- ncm (obrigatório)
- cest (opcional), cfop_sugerido (opcional)

### Saída mínima (DecisaoFiscalItem)

- cfop, origem_mercadoria, cst_icms, csosn
- aliquota_icms, modalidade_bc_icms, percentual_reducao_bc
- aliquota_icms_st, modalidade_bc_icms_st, percentual_mva_st
- regra_fiscal_id, mensagem_motor

---

## 5. Lógica do motor

1. Carregar regras da empresa com `ativo = true` e dentro da vigência (vigencia_inicio, vigencia_fim).
2. Aplicar filtros compatíveis.
3. **Se uf_destinatario do contexto for null**: só aceitar regras com `uf_destinatario` null. O motor nunca inventa tributação.
4. Ordenar primeiro por `ordem_prioridade` ASC.
5. Dentro da mesma prioridade, desempatar por especificidade calculada:
  - ncm_exato > ncm_prefix > sem ncm
  - uf_destinatario preenchido > null
  - tipo_destinatario específico > qualquer
  - crt específico > null
6. Se ainda houver empate real, lançar erro de ambiguidade.
7. Validar compatibilidade do resultado com CRT da empresa antes de aplicar.
8. Nunca retornar CST e CSOSN ao mesmo tempo.

---

## 6. Política de falha (erro bloqueante)

- Nenhuma regra encontrada
- Múltiplas regras equivalentes (ambiguidade)
- Regra incompatível com CRT
- Retorno com CST e CSOSN simultâneos
- Item sem NCM

**Sem fallback silencioso.**

---

## 7. Integração com emissão

Alterar [app/services/fiscal/emissao_service.py](app/services/fiscal/emissao_service.py):

- Derivar **uma vez por nota**: CRT do emitente, UF emitente, UF destinatário, tipo destinatário, tipo de operação.
- Para cada item:
  - Preencher NCM e CEST a partir do ProdutoCliente somente se faltar.
  - Chamar o motor tributário.
  - Preencher no item: cfop, origem, cst_icms, csosn, aliquota_icms, campos de ST, regra_fiscal_icms_id, motor_contexto_json, motor_resultado_json, motor_versao.
- Ajustar `_preencher_fiscal_itens_desde_produto_cliente` para **não** copiar cfop_padrao, origem_mercadoria, csosn, cst_icms quando o motor estiver ativo.

---

## 8. Validação bloqueante

Em `validar_nota_fiscal`:

- Bloquear se qualquer item estiver sem decisão fiscal válida.
- Mensagem padrão: *"Item X (NCM Y): nenhuma regra fiscal ICMS aplicável para esta empresa e operação. Cadastre uma regra em Regras Fiscais."*
- Bloquear também para ambiguidade e incompatibilidade de CRT.

---

## 9. Auditabilidade

Persistir por item:

- regra_fiscal_icms_id
- motor_contexto_json
- motor_resultado_json
- motor_versao

Objetivo: rastrear qual regra foi aplicada, com qual contexto e qual resultado.

---

## 10. Casos mínimos de teste (unitários)

- CRT 1 venda interna sem ST
- CRT 1 venda interestadual
- CRT 3 venda interna
- CRT 3 venda interestadual
- Regra por NCM exato
- Regra por NCM prefixo
- Fallback genérico
- UF destinatário ausente
- Ausência de regra
- Ambiguidade de regra
- Regra incompatível com CRT

---

## Arquivos principais


| Ação    | Arquivo                                                       |
| ------- | ------------------------------------------------------------- |
| Criar   | `app/models/regra_fiscal_icms.py`                             |
| Criar   | `app/services/fiscal/motor_tributario_icms.py`                |
| Criar   | `app/database/migrations/versions/xxx_regras_fiscais_icms.py` |
| Alterar | `app/services/fiscal/emissao_service.py`                      |
| Alterar | `app/models/nota_fiscal.py`                                   |
| Alterar | `app/models/__init__.py`                                      |


