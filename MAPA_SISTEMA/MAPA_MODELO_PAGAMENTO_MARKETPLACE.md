# Modelo Secundário de Pagamento — PDV Ibix (Marketplace / Intermediação)

## Visão Geral

Este documento é a **fonte única de verdade** sobre o **modelo de pagamento de intermediação** do sistema: vendas online (cliente paga no app, plataforma repassa) e vendas offline (cliente paga ao lojista, plataforma cobra depois), além do tratamento de **frete** (lojista vs. plataforma) e das regras financeiras e de repasse.

**Escopo:** Não cobre a assinatura SaaS (ver `MAPA_PAGAMENTO.md`). Cobre o fluxo de dinheiro entre consumidor, plataforma e lojista em cenários marketplace/interior: baixo custo, sem split financeiro (split apenas contábil), escalável e competitivo.

**Referências cruzadas:** Frete e transporte em `MAPA_Frete_Transporte.md`; regras obrigatórias em `MAPA_DE_REGRAS.md`; APIs e endpoints em `MAPA_DE_API.md`; **implementação vitrine multi-loja (sessão unificada, rateio por tenant)** em `MAPA_DO_SISTEMA.md` § 12, `MAPA_PAGAMENTO.md` § 2.6 e serviço `app/services/payments/marketplace_unified_payment_scope.py`.

---

## 1. Modelo formalizado

### 1.1 Venda ONLINE

| Aspecto | Descrição |
|--------|-----------|
| **Quem paga** | Cliente paga no app. |
| **Quem recebe** | Plataforma recebe. |
| **Comissão** | Plataforma desconta comissão. |
| **Repasse** | Plataforma repassa ao lojista (produto − comissão). |
| **Modelo** | **Intermediação com repasse.** |

### 1.2 Venda OFFLINE

| Aspecto | Descrição |
|--------|-----------|
| **Quem paga** | Cliente paga direto ao lojista. |
| **Registro** | Plataforma registra o pedido. |
| **Cobrança** | Plataforma cobra comissão via boleto (ou Pix / fatura semanal). |
| **Modelo** | **Cobrança posterior.** |

### 1.3 Frete

| Tipo | Quem define | Quem recebe | Quem paga a entrega | Observação |
|------|-------------|-------------|---------------------|------------|
| **A) Frete do lojista** | Lojista define. | Lojista recebe. | Lojista paga a entrega. | Simples e seguro. |
| **B) Frete gerenciado pela plataforma** | Plataforma/regras. | Cliente paga frete → plataforma recebe. | Plataforma paga entregador. | Ponto crítico: risco logístico e margem obrigatória (ver § 4). |

---

## 2. Arquitetura correta (como deve funcionar)

### 2.1 ONLINE (sem split financeiro)

Fluxo ideal:

1. Cliente paga.
2. Gateway processa.
3. Valor entra na conta da plataforma.
4. Sistema registra:
   - `valor_produto`
   - `valor_frete`
   - `comissao`
   - `valor_lojista`
   - `valor_frete_plataforma` (quando frete é da plataforma)
5. Plataforma repassa:
   - **Lojista:** produto − comissão.
   - **Entregador:** frete (quando a plataforma gerencia o frete).

### 2.2 OFFLINE

1. Cliente paga direto ao lojista.
2. Plataforma registra o pedido.
3. Gera cobrança ao lojista:
   - Boleto, ou
   - Pix, ou
   - Fatura semanal (agrupada).

### 2.3 Checkout unificado marketplace (carrinho multi-loja — **implementado 2026-05-15**)

Este fluxo mantém o princípio do § 8: **uma cobrança no gateway** (sem split financeiro no provedor); o **parcelamento entre lojistas / CAs** é **somente interno** (contábil e operacional), por **pedido** e por **`tenant_id` do pedido** (`pedidos_marketplace.tenant_id` = cliente/estabelecimento dono da loja).

| Aspecto | Comportamento no sistema |
|--------|---------------------------|
| **Cliente** | Um único pagamento (ex.: PIX) no valor total do carrinho. |
| **Gateway** | Preferência/order com valor agregado; `external_reference` no formato **`mcs:{session_uuid}`**. |
| **Pedidos** | **N** linhas em `pedidos_marketplace` (uma por loja/`loja_id`) ligadas por **`marketplace_checkout_sessions`** + **`marketplace_checkout_session_pedidos`**. |
| **`PaymentTransaction`** | **Uma** linha com `checkout_session_id` preenchido, `amount` = soma dos totais, e no registro físico **`cliente_id` / `pedido_id` do pedido âncora** (primeiro da ordenação na sessão) — apenas **rótulo de titularidade no DB**, não o rateio oficial por si só. |
| **Split interno por CA** | Para cada tenant, **soma dos `pedido.total`** dos pedidos da mesma sessão cujo **`tenant_id`** = aquele CA. Esse valor é o “**bruto atribuível**” ao lojista nesta cobrança. |
| **Recebíveis (painel CA)** | **`GET /api/v1/payments/transactions?estabelecimentoId=`** lista a transação se o CA é âncora **ou** **participante** da sessão; com filtro por estabelecimento, **`amount`**, **`cliente_id`** e referência de pedido refletem o **trecho daquele tenant**. Serviço: `marketplace_unified_payment_scope.py`. |
| **Billing uso SaaS** | Em confirmação de pagamento, **`BillingUsageEvent` / `record_payment_billing`** consome **`cliente_id = pedido.tenant_id`** **por pedido** (vários eventos ligados ao mesmo `payment_transaction_id`). |
| **Repasses (SuperAdmin)** | Listagem de transações, sugestão e resumo por `cliente_id` incluem sessões em que o CA participa e aplicam **o mesmo rateio por tenant** (taxas da empresa **daquele** CA sobre o valor atribuível). |

**Implicação para este documento:** o “**valor_lojista**” e a “**comissão**” sobre a venda online, em cenário multi-loja, devem ser computados **por pedido** (ou agregados por tenant a partir dos pedidos da sessão), **não** tomando apenas `PaymentTransaction.cliente_id` como se fosse único titular quando `checkout_session_id` está presente.

---

## 3. Ponto crítico: frete da plataforma

Se a plataforma gerencia o frete:

- Recebe o frete do cliente.
- Paga o entregador.
- Assume o risco logístico.

**Riscos:** atraso de entrega, falha do entregador, reclamação do cliente, chargeback (se venda online). **Quem paga:** a plataforma.

Por isso o frete da plataforma deve ser tratado com **margem garantida** e regras claras (ver § 4 e § 7).

---

## 4. Estruturação correta do frete da plataforma

### 4.1 Regra essencial

**Frete nunca pode depender do valor do pedido.** Tratar sempre em separado:

| Conceito | Descrição |
|----------|-----------|
| `frete_cliente` | Valor pago pelo cliente. |
| `custo_entregador` | Valor pago ao entregador. |
| `lucro_frete` | `frete_cliente − custo_entregador`. |

### 4.2 Exemplo

- Cliente paga frete: R$ 12  
- Plataforma paga entregador: R$ 9  
- **Lucro frete:** R$ 3  

**Se fizer errado:** cliente paga R$ 8 e entregador custa R$ 10 → plataforma perde dinheiro.

### 4.3 Regra de margem

Nunca operar no zero: **sempre** `frete_cliente > custo_entregador` (margem mínima definida por política).

---

## 5. Modelo financeiro completo (exemplo)

| Item | Valor |
|------|--------|
| Produto | R$ 100 |
| Frete | R$ 12 |
| Comissão | 12% |
| **Cliente paga** | **R$ 112** |

**Plataforma recebe:** R$ 112.

**Distribuição:**

| Destino | Cálculo | Valor |
|---------|---------|--------|
| Comissão | 12% sobre R$ 100 | R$ 12 |
| Lojista | R$ 100 − R$ 12 | R$ 88 |
| Frete | Cliente pagou R$ 12; entregador custa R$ 9 | Lucro frete R$ 3 |

**Resultado plataforma:** Comissão R$ 12 + Lucro frete R$ 3 = **R$ 15**.

---

## 6. Estrutura necessária no sistema

Separar claramente no domínio:

### 6.1 Pedido (ou equivalente)

| Campo | Descrição |
|-------|-----------|
| `valor_produto` | Soma dos produtos. |
| `valor_frete` | Valor de frete (pago pelo cliente). |
| `forma_pagamento` | Online / offline, etc. |
| `tipo_frete` | Lojista / Plataforma. |

### 6.2 Financeiro (repasse / cobrança)

| Campo | Descrição |
|-------|-----------|
| `comissao_plataforma` | Comissão sobre produto (e regras). |
| `valor_lojista` | Valor a repassar ao lojista. |
| `custo_frete` | Custo pago ao entregador (quando frete plataforma). |
| `lucro_frete` | `valor_frete − custo_frete` (quando frete plataforma). |
| `status_repasse` | Pendente, agendado, repassado, etc. |

### 6.3 Checkout unificado (vários pedidos, um pagamento gateway)

| Entidade | Papel |
|----------|--------|
| `marketplace_checkout_sessions` | Agrupa os pedidos e o estado da sessão (`mcs:{uuid}` no gateway). |
| `marketplace_checkout_session_pedidos` | Liga sessão ↔ `pedidos_marketplace` em ordem. |
| `payment_transactions` (uma linha) | Cobrança agregada; **rateio** para comissão/repasse contábil = somar totais dos pedidos **por `tenant_id`**. |

---


## 7. Regras obrigatórias para segurança

| Regra | Descrição |
|-------|-----------|
| **1. Repasse não imediato** | Nunca repassar ao lojista no mesmo dia. Usar **D+7** ou **D+14**. Motivo: chargeback, fraude, erro de pedido. |
| **2. Controle de lojista** | Validação de CNPJ; limite de venda inicial; bloqueio se inadimplente. |
| **3. Frete da plataforma com margem** | Nunca operar no zero. Sempre `frete_cliente > custo_entregador`. |

---

## 8. Split — decisão final

| Opção | Decisão | Motivo |
|-------|---------|--------|
| **Split financeiro (gateway)** | **Não usar** no início. | Caro, desnecessário, reduz margem. |
| **Split interno (contábil)** | **Usar.** | Registro interno de valor_produto, comissao, valor_lojista, valor_frete, custo_frete, lucro_frete; repasse manual ou via transferência única. |

**Modelo correto:** intermediação com repasse pela plataforma (sem split no gateway).

---

## 9. Modelo ajustado e resumido

| Canal | Fluxo |
|-------|--------|
| **ONLINE** | Cliente paga → plataforma recebe → plataforma repassa (após D+7/D+14). |
| **ONLINE multi-loja (checkout unificado)** | Cliente um pagamento só → gateway um débito → **N pedidos**; **atribuição contábil/operacional por `tenant_id` do pedido** (Recebíveis, billing uso, base de repasse). |
| **OFFLINE** | Lojista recebe → plataforma cobra depois (boleto/Pix/fatura). |
| **FRETE** | Padrão: lojista; opcional: plataforma com margem (frete_cliente > custo_entregador). |
| **SPLIT** | Não usar split no gateway; split apenas contábil interno. |

---

## 10. Conclusão

Modelo adequado para interior:

- Baixo custo.
- Sem dependência de fintech com split.
- Escalável.
- Competitivo.

---

## Referência rápida (campos e regras)

| Área | Campos / Regras |
|------|------------------|
| **Pedido** | valor_produto, valor_frete, forma_pagamento, tipo_frete (lojista / plataforma). |
| **Financeiro** | comissao_plataforma, valor_lojista, custo_frete, lucro_frete, status_repasse. |
| **Sessão unificada** | `checkout_session_id` na transação + pedidos ligados (`marketplace_checkout_session_pedidos`); rateio por soma de `pedido.total` por `tenant_id`. |
| **Repasse** | D+7 ou D+14; nunca mesmo dia. |
| **Frete plataforma** | frete_cliente, custo_entregador, lucro_frete; sempre margem positiva. |
| **Lojista** | CNPJ validado; limite inicial; bloqueio se inadimplente. |

---

**Última atualização:** 2026-05-15 — § 2.3 checkout unificado multi-loja (split contábil por `pedido.tenant_id`; `PaymentTransaction` âncora; Recebíveis, billing uso e repasse SuperAdmin); tabela § 9 e referência rápida. **Anterior:** 2026-03-17 — criação do documento; modelo formalizado (online/offline, frete, repasse, regras de segurança e split contábil).
