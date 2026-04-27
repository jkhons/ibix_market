# Verificação de implementação — Plano Faturamento e NFS-e

**Data da verificação:** 2026-03-02  
**Plano:** `.cursor/plans/plano_faturamento_nfse_implementacao.plan.md`  
**Documento base:** `docs/MODULO_FATURAMENT_V2.MD`

---

## Resultado geral: **NÃO implementado 100%**

O plano **não foi implementado por completo**. Existe uma base parcial (notas_servico, emissão/cancelamento NFS-e, integração OS→rascunho NFS-e) com **modelo e fluxo diferentes** do desenhado no plano (que prevê tabelas `nfse_*`, tenant_id, origin_type SUBSCRIPTION/OS, worker assíncrono, etc.). Abaixo o status por fase.

---

## Fase 0 — Migrações de schema

| Item | Exigido pelo plano | Status no código |
|------|--------------------|------------------|
| `empresa.municipio_ibge` | INT NULL | ❌ **Não existe** — modelo `Empresa` não tem o campo |
| `clientes.municipio_ibge` | INT NULL | ❌ **Não existe** — modelo `Cliente` não tem o campo |
| `ordem_servico.empresa_id` | BIGINT NULL, FK empresa | ❌ **Não existe** — `OrdemServico` não tem empresa_id; emissor é inferido por `Empresa.cliente_id == ordem.cliente_id` |
| `tenants.default_empresa_id` | BIGINT NULL, FK empresa | ❌ **Não existe** — modelo `Tenant` não tem o campo |
| `tenants.ca_cliente_id` | BIGINT NULL, FK clientes | ❌ **Não existe** — modelo `Tenant` não tem o campo |

**Conclusão Fase 0:** ❌ **0%** — Nenhuma migração do plano (IBGE, emissor OS, padrões tenant) foi aplicada.

---

## Fase 1 — DDL e modelos (módulo NFS-e)

| Item | Exigido pelo plano | Status no código |
|------|--------------------|------------------|
| Tabela `nfse_invoices` | Documento universal com tenant_id, origin_type, origin_id | ❌ **Não existe** — o sistema usa `notas_servico` (sem tenant_id, sem origin_type/origin_id no formato do plano) |
| Tabela `nfse_rps` | Controle de RPS por emissor | ❌ **Não existe** |
| Tabela `nfse_credentials` | Certificado A1 por empresa | ❌ **Não existe** — certificado está em `empresa` (certificado_a1_*, senha_certificado) |
| Tabela `nfse_message_logs` | Request/response redigido | ❌ **Não existe** — existe `fiscal_evento` (genérico por documento_tipo) e `fiscal_download_log`, não a estrutura nfse_message_logs |
| Tabela `nfse_provider_configs` | Config por empresa/município | ❌ **Não existe** |
| Modelos SQLAlchemy NfseInvoice, NfseRps, etc. | Conforme DDL do doc | ❌ **Não existem** |
| Contratos Pydantic NfseInvoiceCreate, NfseInvoiceCreateFromSubscription, etc. | Conforme doc | ❌ **Não encontrados** |

**Conclusão Fase 1:** ❌ **0%** — Nenhuma tabela `nfse_*` do plano existe; o desenho atual é `notas_servico` + `fiscal_evento` / `fiscal_download_log`.

---

## Fase 2 — Core NFS-e (validações, ISS, RPS, ProviderRouter)

| Item | Exigido pelo plano | Status no código |
|------|--------------------|------------------|
| Validações (IBGE, IM, tomador) | Antes de enfileirar | ❌ Parcial — não há validação de municipio_ibge (campo inexistente) |
| Cálculo ISS (base, deduções, retenções) | Motor de cálculo | ⚠️ Parcial — NotaServico tem base_calculo_iss, aliquota_iss, valor_iss; não há “core” separado |
| Geração e reserva de RPS | Transacional, por empresa/série/número | ❌ **Não existe** — não há tabela nfse_rps nem reserva de RPS |
| ProviderRouter (NACIONAL / SP_CAPITAL por município) | Escolha de provider por municipio_ibge | ❌ **Não existe** — provedor é por empresa (provedor_fiscal) ou global (configuração), não por município IBGE |
| Regras de bloqueio (default_empresa, ca_cliente, IBGE, certificado) | Bloquear emissão subscription | ❌ Não aplicável — não há fluxo subscription → NFS-e |

**Conclusão Fase 2:** ❌ **~10%** — Lógica de emissão existe em `FiscalEmissaoService`/provedor, mas sem RPS, sem ProviderRouter e sem campos IBGE.

---

## Fase 3 — Certificado A1

| Item | Exigido pelo plano | Status no código |
|------|--------------------|------------------|
| Upload A1 por empresa | Tela/rota | ⚠️ Verificar — empresa tem certificado_a1_path, certificado_a1_blob, senha_certificado, certificado_validade |
| Validação imediata (senha, subject, validade) | Ao upload | ⚠️ Não verificado em detalhe |
| Monitor expiração (30/15/7 dias) | Rotina/job | ❌ **Não encontrado** — nenhum job/task de alerta de expiração de certificado |
| Senha criptografada em repouso | Segurança | ⚠️ Campo existe; uso de criptografia não verificado |
| RBAC (apenas admin CA altera certificado) | Permissões | ⚠️ Depende do escopo atual de empresa (cliente_id) |

**Conclusão Fase 3:** ⚠️ **~40%** — Campos de certificado existem na empresa; falta monitor de expiração e garantia formal de criptografia/redação.

---

## Fase 4 — Provider NFS-e Nacional

| Item | Exigido pelo plano | Status no código |
|------|--------------------|------------------|
| Interface issue / poll / cancel | Adapter | ⚠️ Parcial — `IProvedorFiscal`: enviar_nfse, cancelar_nfse, consultar_status_nfse existem |
| Provider Nacional (padrão 2026) | Emitir/consultar/cancelar contra portal nacional | ❌ **Não implementado** — `ProvedorLocal` e `ProvedorStub` têm stubs para NFS-e; não há integração real com portal NFS-e nacional |
| Gravar nfse_message_logs (redigido) | Auditoria | ❌ Não existe tabela; existe registro em `fiscal_evento` (payload_raw) |

**Conclusão Fase 4:** ❌ **~25%** — Interface e chamadas existem; provider real “Nacional” e logs no formato do plano não.

---

## Fase 5 — Worker/Jobs

| Item | Exigido pelo plano | Status no código |
|------|--------------------|------------------|
| job_issue_nfse(invoice_id) | Fila assíncrona | ❌ **Não existe** — emissão é síncrona via API (enviar_nfse) |
| job_poll_nfse(invoice_id) | Consulta até AUTHORIZED/REJECTED | ❌ **Não existe** |
| job_cancel_nfse(invoice_id, reason) | Fila | ❌ **Não existe** — cancelamento é síncrono na API |
| job_generate_pdf_nfse(invoice_id) | PDF após autorização | ⚠️ Existe endpoint de download de PDF para nota_servico; não como job em fila |
| Idempotência (UNIQUE origin_type+origin_id) | Evitar duplicata | ❌ Não aplicável — não há nfse_invoices |
| Retry com backoff | Política definida | ❌ Não há jobs NFS-e na fila |

**Conclusão Fase 5:** ❌ **0%** — Não há workers/jobs para NFS-e; fluxo atual é síncrono (API).

---

## Fase 6 — Integração com origens (Subscription e OS)

| Item | Exigido pelo plano | Status no código |
|------|--------------------|------------------|
| Subscription → nfse_invoices (default_empresa_id, ca_cliente_id) | Criar nota ao fechar ciclo | ❌ **Não existe** — não há default_empresa_id/ca_cliente_id; não há geração de NFS-e a partir de subscription |
| OS → nfse_invoices (empresa_id na OS) | Criar nota ao “Faturar” | ⚠️ **Parcial** — existe `_criar_rascunho_nfse_ao_concluir_os`: cria **NotaServico** (não nfse_invoices) com empresa inferida por `Empresa.cliente_id == ordem.cliente_id` (ordem_servico não tem empresa_id) |
| Idempotência subscription (UNIQUE tenant_id, origin_type, origin_id) | Evitar duplicata | ❌ Não aplicável |

**Conclusão Fase 6:** ❌ **~20%** — Só existe criação de rascunho de NotaServico ao concluir OS; nada para subscription e modelo do plano (nfse_invoices).

---

## Fase 7 — UI (configuração e operação)

| Item | Exigido pelo plano | Status no código |
|------|--------------------|------------------|
| Config fiscal CA (default_empresa, ca_cliente) | Uma vez por CA | ❌ **Não existe** — tenant não tem esses campos; não há tela para isso |
| Assistente IBGE (empresa e cliente) | Preencher municipio_ibge a partir de cidade+UF | ❌ **Não existe** — não há campo municipio_ibge nem tela assistente |
| Tela Pendências fiscais (REJECTED, reprocessar) | Listar e “tentar novamente” | ❌ **Não existe** — “pendências” encontradas são de pagamentos, não fiscais |
| Config por município (admin) | Provider / padrão nacional por IBGE | ❌ **Não existe** |
| Status e download XML/PDF | Por nota | ✅ **Existe** — API de download XML/PDF para notas_servico |

**Conclusão Fase 7:** ❌ **~15%** — Apenas download de XML/PDF; falta toda a UI de config CA, IBGE e pendências fiscais.

---

## Fase 8 — RBAC e segurança

| Item | Exigido pelo plano | Status no código |
|------|--------------------|------------------|
| Perfis (CA, fiscal_user, support_readonly) | Permissões por perfil | ⚠️ Escopo por cliente (ClienteScope) existe; permissões granulares “fiscal_emitir”/“fiscal_cancelar” não verificadas em detalhe |
| Filtro tenant_id em ações NFS-e | Sempre filtrar por tenant | ⚠️ Notas são por empresa → cliente_id; tenant vem de usuário; não há tenant_id em notas_servico |
| Logs redigidos (sem CPF/CNPJ/certificado em claro) | nfse_message_logs | ❌ Não existe tabela; fiscal_evento guarda payload_raw (risco de não redigido) |
| Códigos de erro padronizados (MUN_IBGE_MISSING, etc.) | last_error_code | ❌ Não aplicável — modelo atual não tem last_error_code/last_error_msg no formato do plano |

**Conclusão Fase 8:** ⚠️ **~30%** — Há controle de escopo por cliente; falta modelo e logs do plano e códigos de erro padronizados.

---

## Fase 9 — Testes, observabilidade e deploy

| Item | Exigido pelo plano | Status no código |
|------|--------------------|------------------|
| Testes unitários (criação nfse_invoices, RPS, validações, ProviderRouter) | Conforme doc | ❌ Não aplicável — não há nfse_invoices nem RPS; existe `tests/test_fiscal_module.py` (não verificado conteúdo) |
| Testes integração homolog (emissão, rejeição, cancelamento) | Provider nacional | ❌ Provider nacional não implementado |
| Testes E2E (ciclo mensalidade → NFS-e) | Fluxo completo | ❌ Não existe fluxo subscription → NFS-e |
| Alertas expiração certificado | 30/15/7 dias | ❌ Não encontrado |
| Métricas (fila, taxas, latência) | Dashboard operacional | ❌ Não encontrado para NFS-e |
| Checklist deploy (migrations, worker, secrets, monitor) | Documentado | ⚠️ Celery existe para billing/relatórios; não para NFS-e |

**Conclusão Fase 9:** ❌ **~5%** — Infraestrutura de testes e Celery existe; nada específico do plano NFS-e.

---

## Resumo executivo

| Fase | Nome | Status | % estimado |
|------|------|--------|------------|
| 0 | Migrações de schema | ❌ Não implementado | 0% |
| 1 | DDL e modelos nfse_* | ❌ Não implementado | 0% |
| 2 | Core NFS-e (RPS, ProviderRouter) | ❌ Quase nada | 10% |
| 3 | Certificado A1 | ⚠️ Parcial (campos; sem monitor) | 40% |
| 4 | Provider Nacional | ❌ Stubs apenas | 25% |
| 5 | Worker/Jobs | ❌ Não implementado | 0% |
| 6 | Integração Subscription/OS | ❌ Só OS→NotaServico rascunho | 20% |
| 7 | UI (config CA, IBGE, pendências) | ❌ Quase nada | 15% |
| 8 | RBAC e segurança | ⚠️ Parcial (escopo; sem logs/códigos) | 30% |
| 9 | Testes e deploy | ❌ Específico NFS-e não feito | 5% |

**Implementação geral do plano:** **~15%** — Há emissão/cancelamento de NFS-e sobre o modelo atual (`notas_servico` + provedor stub/local) e criação de rascunho ao concluir OS, mas **não** o desenho do plano (tabelas nfse_*, tenant_id, subscription→NFS-e, worker assíncrono, UI e regras descritas no MODULO_FATURAMENT_V2.MD).

---

## O que já existe (base atual)

- **Modelos:** `NotaServico`, `NotaServicoItem`, `fiscal_evento`, `fiscal_download_log`; `Empresa` com provedor_fiscal, certificado A1 (path/blob, senha, validade).
- **Migração:** `s88tt680g8p2` — provedor em empresa, ordem_servico_id em notas_servico, fiscal_evento, fiscal_download_log.
- **Serviços:** `FiscalEmissaoService.enviar_nfse`, `cancelar_nfse`; provedores `ProvedorLocal`, `ProvedorStub` com métodos NFS-e (stub/retorno simulado).
- **API:** Envio, cancelamento e download XML/PDF de notas de serviço; criação de rascunho de NFS-e ao concluir OS (empresa inferida pelo cliente da OS).
- **Integração OS:** Ao marcar OS como concluída, é criada uma `NotaServico` em rascunho vinculada à OS.

---

## Próximos passos recomendados

1. **Fase 0:** Aplicar migrações (municipio_ibge em empresa e clientes; empresa_id em ordem_servico; default_empresa_id e ca_cliente_id em tenants).
2. **Fase 1:** Criar tabelas e modelos `nfse_*` do plano (ou definir migração progressiva de notas_servico → nfse_invoices).
3. **Fases 2–5:** Implementar Core (RPS, ProviderRouter), Provider Nacional real, e jobs assíncronos (issue, poll, cancel).
4. **Fase 6:** Implementar fluxo subscription → NFS-e usando default_empresa_id e ca_cliente_id; alinhar OS → nfse_invoices (ou manter NotaServico e mapear conceitualmente).
5. **Fases 7–9:** Implementar UI (config CA, IBGE, pendências), reforçar RBAC/logs redigidos e códigos de erro, e testes + checklist de deploy conforme plano.
