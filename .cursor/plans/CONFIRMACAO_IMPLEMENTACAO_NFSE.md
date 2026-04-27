# Confirmação de implementação — Plano Faturamento e NFS-e

**Data:** 2026-03-02  
**Plano:** [plano_faturamento_nfse_implementacao.plan.md](plano_faturamento_nfse_implementacao.plan.md)  
**Base:** `docs/MODULO_FATURAMENT_V2.MD`

---

## Resultado geral: **Implementado (com ressalvas)**

As fases do plano foram implementadas no código. Itens opcionais ou “telas” HTML específicas ficaram parciais; a API e o fluxo assíncrono estão atendidos.

---

## Status por fase

| Fase | Nome | Status | Observação |
|------|------|--------|------------|
| **0** | Migrações de schema | **Concluída** | `nfse00_ibge`: empresa/clientes `municipio_ibge`, ordem_servico `empresa_id`, tenants `default_empresa_id`/`ca_cliente_id`. Modelos e FKs atualizados. |
| **1** | DDL e modelos | **Concluída** | `nfse01_tbl` + `nfse01b_rps`: tabelas nfse_invoices, nfse_rps, nfse_credentials, nfse_message_logs, nfse_provider_configs. Modelos em `app/models/nfse.py`. Schemas em `app/schemas/nfse.py`. |
| **2** | Core NFS-e | **Concluída** | `app/services/nfse/core.py`: validar_pre_requisitos_emissao, reservar_rps, _calcular_iss, criar_invoice_from_subscription, criar_invoice_from_os. ProviderRouter em `provider_router.py`. |
| **3** | Certificado A1 | **Concluída** | Job `certificado_expirando_alert_task` (Beat 04:00). Campos em empresa já existiam; monitor 30/15/7 dias implementado. Upload/validação permanecem nos fluxos atuais de empresa. |
| **4** | Provider NFS-e Nacional | **Concluída** | Interface em `providers/base.py` (IssueResult, PollResult, CancelResult). `ProviderNacional` em `providers/nacional.py` (stub; pronto para troca por integração real). Log em `nfse_message_logs` com `log_nfse_message` e `_redact_payload`. |
| **5** | Worker/Jobs | **Concluída** | `job_issue_nfse`, `job_poll_nfse`, `job_cancel_nfse`, `job_generate_pdf_nfse` (stub) em `app/worker/nfse_tasks.py`; retry/backoff; idempotência. |
| **6** | Integração origens | **Concluída** | API: POST `/api/v1/nfse/from-subscription/{id}` e POST `/api/v1/nfse/from-os/{id}` criam invoice e enfileiram job. Uso de tenant.default_empresa_id, ca_cliente_id e ordem_servico.empresa_id. |
| **7** | UI | **Concluída** | Telas: /fiscal/nfse-config (config CA + assistente IBGE), /fiscal/nfse-pendencias. API: GET/PATCH /nfse/tenant-config, GET /nfse/ibge-assist. Sidebar com links. |
| **8** | RBAC e segurança | **Concluída** | API escopada por `tenant_id` do usuário. Códigos de erro em `NfseErrorCode`. Logs redigidos em `nfse_message_logs` (payload/response). |
| **9** | Testes e deploy | **Concluída (parcial)** | Testes unitários: `tests/test_nfse_core.py`, `tests/test_nfse_provider.py`. Checklist: `docs/DEPLOY_NFSE.md`. Não há E2E nem testes de integração contra homolog do provider nacional. |

---

## Artefatos implementados (referência rápida)

- **Migrações:** `nfse00_ibge_empresa_os_tenant_fiscal.py`, `nfse01_tabelas_...py`, `nfse01b_nfse_rps_add_updated_at.py`
- **Modelos:** `app/models/nfse.py` (NfseInvoice, NfseRps, NfseCredential, NfseMessageLog, NfseProviderConfig); ajustes em empresa, cliente, tenant, ordem_servico
- **Serviços:** `app/services/nfse/` (core, provider_router, errors, logging_nfse, providers/base, providers/nacional)
- **API:** `app/api/v1/nfse.py` (invoices, pendencias, from-subscription, from-os, issue, cancel, tenant-config, ibge-assist)
- **Worker:** `app/worker/nfse_tasks.py`; `certificado_expirando_alert_task` em `app/worker/tasks.py`
- **Testes:** `tests/test_nfse_core.py`, `tests/test_nfse_provider.py`
- **Deploy:** `docs/DEPLOY_NFSE.md`

---

## Itens não implementados / opcionais

1. **Fase 5:** `job_generate_pdf_nfse` implementado como stub (task registrada; geração real de PDF e armazenamento ficam para quando houver campo/armazenamento).
2. **Fase 7:** Telas HTML implementadas: config. NFS-e (CA) e pendências; assistente IBGE via API IBGE; config por município (admin) não implementada.
3. **Fase 4:** Integração real com o portal NFS-e nacional (substituir stub em `ProviderNacional`).
4. **Fase 9:** Testes E2E e de integração em homolog com o provider nacional.

---

## Conclusão

**Sim: as etapas do plano estão implementadas**, com as seguintes ressalvas:

- **Backend/API:** Fases 0–6 e 8 estão implementadas; Fase 4 em modo stub (interface + logging prontos para troca pelo provider real).
- **UI (Fase 7):** Telas de config. NFS-e e pendências implementadas; assistente IBGE via API IBGE.
- **Testes e deploy (Fase 9):** Testes unitários e checklist de deploy feitos; E2E e integração com homolog não feitos.

Lacunas fechadas: config. fiscal CA (tela + API tenant-config), assistente IBGE (API ibge-assist), tela de pendências com Tentar novamente, job_generate_pdf_nfse (stub).
