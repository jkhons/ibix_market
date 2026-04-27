# Índice MAPA_FLUXO — Fluxos de Negócio PDV Ibix

**Uso:** Consulte este arquivo primeiro para escolher **um** fluxo e reduzir tokens.

---

## Arquivos (6 fluxos + índice)

| Arquivo | Conteúdo |
|---------|----------|
| **FLUXO_NOVO_CLIENTE_ADMINISTRADOR.md** | Novo CA: cadastro público → login → subclientes/equipamentos → certificado → OS → faturamento |
| **FLUXO_CADASTROS.md** | Cliente (CNPJ, CEP, CRUD) + Equipamento (por cliente, tipo, CRUD) |
| **FLUXO_CONTRATOS_AGENDAMENTO.md** | Contrato de aferição (periodicidade, equipamentos) + Agendamento (com/sem contrato, status) |
| **FLUXO_CERTIFICACAO_CALIBRACAO.md** | Certificado (criação, aprovação, PDF) + Calibração (etapas 1–4, auditoria, finalizar, emissão) |
| **FLUXO_ORDEM_SERVICO.md** | Ordem de serviço (criação, status, equipamentos, vínculos) |
| **FLUXO_FINANCEIRO.md** | Vendas, notas fiscais, notas de serviço, pagamentos |
| **INDICE.md** | Este índice |

---

## Quando usar cada fluxo

- **Cliente, equipamento, CNPJ, CEP** → FLUXO_CADASTROS.md
- **Contrato, periodicidade, aferição programada** → FLUXO_CONTRATOS_AGENDAMENTO.md
- **Agendamento, pendente, confirmado, avulso** → FLUXO_CONTRATOS_AGENDAMENTO.md
- **Certificado, número YYYY-XXXX, aprovar, PDF** → FLUXO_CERTIFICACAO_CALIBRACAO.md
- **Calibração, processo, balança, auditoria, finalizar, inspetor, aprovador** → FLUXO_CERTIFICACAO_CALIBRACAO.md
- **Novo Cliente Administrador, cadastro público, CA** → FLUXO_NOVO_CLIENTE_ADMINISTRADOR.md
- **Ordem de serviço, OS** → FLUXO_ORDEM_SERVICO.md
- **Venda, nota fiscal, financeiro** → FLUXO_FINANCEIRO.md

---

## Sequência geral (visão)

```
Cliente → Equipamento → [Contrato opcional] → Agendamento → Processo (calibração) → Certificado
                                                                  ↓
                                            Ordem de Serviço → Financeiro (venda, NF)
```

---

## Palavras-chave para busca (Cursor)

| Buscar por | Abrir |
|------------|--------|
| cliente, CNPJ, CEP, equipamento, fabricante, numero_serie | FLUXO_CADASTROS.md |
| contrato, periodicidade, agendamento, avulso, tipo_servico | FLUXO_CONTRATOS_AGENDAMENTO.md |
| certificado, emitir, aprovar, PDF, processo, calibração, auditoria, finalizar | FLUXO_CERTIFICACAO_CALIBRACAO.md |
| ordem de serviço, ordem_servico | FLUXO_ORDEM_SERVICO.md |
| novo CA, cadastro público, Cliente Administrador, fluxo completo | FLUXO_NOVO_CLIENTE_ADMINISTRADOR.md |
| venda, nota fiscal, financeiro | FLUXO_FINANCEIRO.md |

---

## Regra para o Cursor

Abra **apenas** o fluxo indicado acima para a tarefa. Para visão de arquitetura/banco/APIs use MAPA_SISTEMA (ver MAPA_SISTEMA/INDICE.md).

---

**Última atualização:** 2026-02-10
