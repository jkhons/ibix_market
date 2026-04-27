# Validação do plano de estabilização NF-e

Data da validação: 2026-03-12

## Checklist de conclusão (conforme plano)

### Entrega 1 — Validação fiscal forte
| Item | Status | Onde |
|------|--------|------|
| Validação barra série/número não numéricos com mensagem clara | OK | `emissao_service.validar_nota_fiscal` + `_apenas_digitos_valido` |
| CRT 1–3, modelo 55, tpAmb | OK | Validação de modelo (55/65), ambiente (homologacao/producao), CRT obrigatório 1–3 |
| Totais consistentes (soma itens, descontos, frete, total nota) com bloqueio | OK | `_validar_totais_nota` com tolerância 0,02 |
| cUF derivado do emitente e coerente com URL SEFAZ | OK | `get_url_autorizacao(uf_emitente, amb_env)` não nulo |
| IE com regra explícita (contribuinte) | OK | IE obrigatória para emissão NF-e |

### Entrega 2 — Pós-assinatura
| Item | Status | Onde |
|------|--------|------|
| Pós-assinatura valida Reference URI = #Id infNFe, uma referência, infNFe presente, XML serializável | OK | `nfe_assinador._validar_xml_assinado` + chamada em `assinar_nfe` |

### Entrega 3 — Logs e retorno HTTP
| Item | Status | Onde |
|------|--------|------|
| Logs com URL, UF, ambiente, cert serial/subject, status_http, content_type, duracao_ms | OK | `sefaz_client`: url, uf, ambiente, status_http, http_content_type; `provedor_local`: cert_serial, cert_subject (truncado), duracao_ms |
| Retorno do cliente com status_http e http_content_type | OK | `enviar_nfe_autorizacao` e `enviar_evento_cancelamento` retornam ambos |

### Entrega 4 — Persistência no evento
| Item | Status | Onde |
|------|--------|------|
| Resposta bruta (e Content-Type) persistida no evento | OK | `FiscalEvento.resposta_bruta`, `http_content_type`, `status_http`; `_registrar_evento` recebe e grava |
| raw_response em sucesso truncado | OK | `sefaz_client` retorna `raw_response` sempre (truncado 2000 chars) |

### Entrega 5 — Tabela nfe_tentativa_envio
| Item | Status | Onde |
|------|--------|------|
| Tabela nfe_tentativa_envio criada com todos os campos | OK | Modelo + migration com tipo_erro, servico, ambiente_sefaz, cert_serial, cert_subject, xml_hash_sha256, tentativa_numero, duracao_ms, http_content_type, etc. |
| Hash + truncado no banco | OK | xml_hash_sha256; resposta_bruta truncada 50.000 chars |
| Persistência a cada tentativa | OK | `emissao_service.enviar_nfe` insere `NFeTentativaEnvio` após envio (sucesso ou falha, inclusive falha de assinatura) |

### Entrega 6 — Testes e idempotência
| Item | Status | Onde |
|------|--------|------|
| Testes automatizados | OK | `tests/test_fiscal_estabilizacao.py`: _apenas_digitos_valido, _validar_totais_nota, validar_nota_fiscal (série/número), idempotência |
| Idempotência: bloqueio de reenvio quando nota já autorizada | OK | `emissao_service.enviar_nfe`: `if nota.status == StatusNotaEnum.AUTORIZADO: return False, "Nota já autorizada. Reenvio não permitido.", None` |

### Fase 3B (após 3A)
| Item | Status |
|------|--------|
| Refatoração em 5 serviços e limpeza de acoplamentos | Pendente (conforme plano: após 3A) |

---

## Matriz de decisão (política de falha)

- **Erro de validação**: bloqueio com mensagem por campo; não gera XML; não envia; não registra tentativa de envio (apenas evento de envio não é criado).
- **Erro de assinatura**: retorno com `payload_retorno.tipo_erro = "assinatura"`; registra tentativa com tipo_erro=assinatura.
- **Erro de conexão/SSL/timeout**: retorno com mensagem; registra tentativa com tipo_erro=conexao ou http_html.
- **Rejeição fiscal (cStat ≠ 100/101/135)**: devolve cStat/xMotivo; registra tentativa com tipo_erro=rejeicao_fiscal.
- **Autorização 100**: atualiza nota; persiste protocolo/chave; registra tentativa; **bloqueia reenvio** (idempotência).

---

## Ajuste realizado na validação

- **Logs (Entrega 3)**: Inclusão de `cert_subject` (truncado a 100 caracteres) no `log_struct` de `provedor_local`, para atender ao requisito “serial e subject do certificado” nos logs.
