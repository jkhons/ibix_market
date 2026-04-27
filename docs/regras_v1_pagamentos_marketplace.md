# Regras V1 — Pagamentos do Marketplace

Documento de definições aprovadas (Bloco 0). Todas as implementações devem respeitar estas regras.

---

## B0.1 — Regra de `is_active` (PaymentTransaction)

- **is_active = True** significa: tentativa vigente do pedido (a que o usuário está sendo direcionado ou a que já venceu).
- Ao **criar nova tentativa** para o mesmo pedido: todas as tentativas anteriores daquele pedido passam a **is_active = False**.
- Se uma tentativa for **paga** (status paid): ela permanece **is_active = True**; as demais do pedido ficam **is_active = False**.
- Apenas **uma** tentativa por pedido pode estar **is_active = True** em um dado momento (vencedora ou "em jogo").

---

## B0.2 — Expiração da reserva de estoque

- **Prazo padrão da reserva:** definido por política (ex.: 30 min para Pix, tempo máximo para cartão pendente conforme gateway).
- **Quem libera a reserva:**
  - **Job periódico:** libera reservas com `reserved_until` vencido.
  - **Cancelamento manual:** ao cancelar pedido, liberar reserva.
  - **Expiração do pedido:** ao marcar pedido como expirado, liberar reserva.
- Campo obrigatório no modelo de reserva: **reserved_until** (datetime).

---

## B0.3 — Idempotência de billing_usage_events

- Chave lógica única para evitar cobrança duplicada: **(payment_transaction_id, event_type, source_refund_id)** ou equivalente que identifique univocamente o evento faturável.
- Antes de inserir evento faturável: verificar se já existe registro com essa chave; se existir, **não** inserir novamente.

---

## B0.4 — Refund parcial (V1)

- **V1:** refund parcial tratado como **reversão financeira proporcional por valor** (não por item explícito).
- Não é obrigatório na V1 modelar "item X devolvido, item Y mantido".
- Reversão da cobrança da plataforma é calculada de forma proporcional ao valor estornado.
- Refund por item detalhado fica para versão futura.

---

## B0.5 — Regras de transição de status

- **PaymentTransaction e PedidoMarketplace:** usar matriz de transições seguras.
- **paid** não pode voltar para **pending** (exceto fluxos excepcionais, ex.: chargeback, com regra própria).
- **refunded:** atualizar apenas após confirmação de estorno no gateway.
- **Duplicidade:** se o evento já foi processado (processed_at preenchido e estado já reflete o evento), **ignorar** de forma segura (idempotência).

---

## Contexto único em PaymentTransaction

- Uma linha de PaymentTransaction pertence a **exatamente um** contexto:
  - **PDV:** venda_id e/ou pdv_id preenchidos; pedido_id nulo.
  - **Marketplace:** pedido_id preenchido; venda_id/pdv_id nulos para esse fluxo.
- Contextos **não** coexistem na mesma linha. Validar na aplicação.

---

## Front obrigatório para V1

- A V1 de pagamentos do marketplace só é considerada concluída com a Fase J (front) implementada: J1–J4 obrigatórios para go-live (redirect_url, páginas success/cancel, "Pagar agora" / "Tentar outro meio", exibição de estado).

---

## Segurança e requisitos não-funcionais (V1)

- **Redirect URL:** O front redireciona apenas para `redirect_url` devolvida pelo backend (originada no gateway, ex.: Mercado Pago). O backend não repassa URL arbitrária; a URL é gerada pela API do provedor.
- **Credenciais:** Nunca em log ou resposta de API; armazenamento criptografado em repouso (PaymentProviderConfig).
- **Dados de pagamento:** Não armazenar número completo de cartão nem CVV; apenas referências (provider_payment_id, last4 se o gateway enviar).
- **Refund admin:** Endpoint de estorno exige autenticação/autorização em produção; trilha de auditoria com `requested_by_user_id` e timestamp.
- **OAuth:** Modelo e interface preparados (connect_account, account_external_id); fluxo completo (callback, state, refresh token) em fase posterior. V1 aceita token configurado manualmente.
- **URL de webhook:** Padrão estável por provider; ex.: `{base}/api/webhooks/mercadopago`.
