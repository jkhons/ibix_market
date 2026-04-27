# Checklist de deploy — Módulo NFS-e

Conforme `MODULO_FATURAMENT_V2.MD` e plano de implementação. Use este checklist antes de colocar o módulo NFS-e em produção.

## 1. Banco de dados

- [ ] Migrações aplicadas na ordem:
  - `nfse00_ibge` (municipio_ibge em empresa/clientes, empresa_id em ordem_servico, default_empresa_id/ca_cliente_id em tenants)
  - `nfse01_tbl` (tabelas nfse_invoices, nfse_rps, nfse_credentials, nfse_message_logs, nfse_provider_configs)
  - `nfse01b_rps` (updated_at em nfse_rps)
- [ ] Em ambientes com múltiplos heads do Alembic, executar merge e depois `alembic upgrade head` no branch desejado.

## 2. Variáveis de ambiente

- [ ] `CELERY_BROKER_URL` ou `REDIS_URL` configurado para o worker (emissão, poll, cancelamento assíncronos).
- [ ] (Opcional) Credenciais do provedor nacional quando houver integração real (não expor em log).

## 3. Celery (worker e beat)

- [ ] Worker com os módulos: `app.worker.tasks`, `app.worker.nfse_tasks`.
- [ ] Beat agendado para:
  - `certificado_expirando_alert_task` (ex.: 04:00) para alertas de certificado próximo do vencimento.
- [ ] Fila de tarefas acessível (Redis/RabbitMQ) para `job_issue_nfse`, `job_poll_nfse`, `job_cancel_nfse`.

## 4. Configuração por tenant (Cliente Administrador)

- [ ] Para cada tenant que for emitir NFS-e de assinatura:
  - `tenants.default_empresa_id`: empresa emissora padrão.
  - `tenants.ca_cliente_id`: cliente (tomador) padrão para NFS-e de subscription.
- [ ] Empresas e clientes com `municipio_ibge` preenchido quando exigido pela validação.
- [ ] Empresas com Inscrição Municipal (IM) preenchida.

## 5. API e segurança

- [ ] Rotas `/api/v1/nfse/*` protegidas (JWT); escopo por `tenant_id` do usuário.
- [ ] Apenas usuários com tenant_id válido podem criar/listar/cancelar NFS-e do próprio tenant.

## 6. Provedor nacional (integração real)

- [ ] Quando disponível: substituir o stub em `app/services/nfse/providers/nacional.py` pela chamada à API do portal nacional.
- [ ] Manter redação de payload/response em `_redact_payload` e gravação em `nfse_message_logs`.
- [ ] Tratar códigos de rejeição do provedor (ex.: `NfseErrorCode.rejeicao(codigo)`).

## 7. Observabilidade

- [ ] Logs do Celery (sucesso/falha das tasks) monitorados.
- [ ] Alertas para falhas recorrentes em `job_issue_nfse` (ex.: NETWORK_ERROR, RPS_UNAVAILABLE).
- [ ] (Opcional) Métricas de quantidade de NFS-e emitidas/canceladas por tenant.

## 8. Rollback

- [ ] Em caso de rollback: downgrade das migrações na ordem inversa (`nfse01b_rps` → `nfse01_tbl` → `nfse00_ibge`).
- [ ] Desativar agendamento Beat do `certificado_expirando_alert_task` se necessário.
