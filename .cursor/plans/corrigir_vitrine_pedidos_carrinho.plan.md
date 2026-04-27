---
name: Corrigir vitrine pedidos/carrinho
overview: Corrigir a resolução do comprador no checkout quando o consumidor logado tem `tenant_id` nulo (legado) e alinhar o front para limpar o carrinho ao redirecionar para o gateway no fluxo de uma loja; cobrir o espelho em `vitrine_raiz` e teste unitário do serviço.
todos:
  - id: backend-resolve
    content: Estender `resolve_comprador_para_loja` (email match + `tenant_id` NULL ou igual) e docstring; manter regra e-mail != body => guest
    status: pending
  - id: test-resolve
    content: Teste unitário pytest para consumidor com `tenant_id` NULL + mesma loja/body
    status: pending
  - id: frontend-cart
    content: "No `then` de postCheckout (uma loja): remover itens da loja no início, depois handleCheckoutResponse; eliminar o bloco duplicado de filter/setCart. Repetir em vitrine_raiz."
    status: pending
  - id: smoke-validate
    content: "Checklist manual: meus-pedidos + carrinho após redirect e após modal PIX"
    status: pending
isProject: false
---

# Plano: pedidos em “Meus pedidos” + carrinho após pagamento (vitrine)

> Espelho do plano; fonte: ver também `.cursor` plans do ambiente. Conteúdo alinhado à revisão (lacunas corrigidas).

## Diagnóstico (já mapeado no código)

- **Listagem** `GET /api/v1/loja/meus-pedidos` filtra `PedidoMarketplace.comprador_id == consumidor.id` do JWT.
- **Checkout** chama `resolve_comprador_para_loja` em `app/services/marketplace_checkout_pedido_service.py`, usado por checkout simples e unificado (`app/api/v1/loja.py` ~1833 e ~2050).
- Só reutiliza a sessão se `consumidor_sessao.tenant_id == loja.cliente_id`. Contas com `tenant_id` NULL falham e o pedido cai em guest com **outro** `id`.
- **Carrinho:** no ramo de uma loja, `handleCheckoutResponse` retorna cedo (redirect/PIX) e o `filter` + `setCart` não corre.

## 1) Backend

**Ficheiro:** `app/services/marketplace_checkout_pedido_service.py` — `resolve_comprador_para_loja`.

- Se `consumidor_sessao` existir, e-mail do body **igual** ao da sessão, e (`tenant_id == loja.cliente_id` **ou** `tenant_id is None`) → retornar `consumidor_sessao` e o segundo valor como no branch atual (não guest criado).
- E-mail do body **diferente** da sessão → não reutilizar; `get_or_create` com o body.
- Não alargar a “tenant A / loja tenant B” com ambos preenchidos.

**Teste:** pytest com `tenant_id=None`, mesma loja, mesmo e-mail.

## 2) Definitivo vs histórico

| Âmbito | Entrega do PR |
|--------|----------------|
| Comportamento novo | `comprador_id` alinhado ao JWT nos casos cobertos. |
| Pedidos antigos | Não corrigidos automaticamente; reparação = PR/script à parte. |

## 3) Front — uma única implementação (lacuna corrigida)

1. **Primeiro** no `then` de `postCheckout` (uma loja): `getCart` → remover itens com `loja_id === lojaId` → `setCart` → `VitrineUpdateCartBadge` se existir.
2. **Depois** `handleCheckoutResponse` / redirect / PIX.
3. **Remover** o bloco **duplicado** que hoje só corre quando não há return cedo (evitar double filter; o ramo “obrigado” mantém só o que for preciso após o primeiro bloco).

**Ficheiros:** `app/templates/loja/checkout.html`, `vitrine_raiz/templates/checkout.html`.

**Checkout unificado:** sem mudança obrigatória; regressão manual.

**PIX:** coberto porque a limpeza não depende de evitar o `return` cedo.

## 4) Validação manual

- NULL tenant + login + compra → meus pedidos.
- Uma loja + MP redirect + `localStorage`.
- Modal PIX se disponível.
- Regressão tenant = CA; guest anónimo.

## 5) Doc MAPA (opcional)

Uma frase no MAPA se a equipa quiser.

---

**Resumo:** Backend + reordenar `then` do checkout uma loja + remover duplicata + teste; webhooks inalterados.
