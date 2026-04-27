# FLUXO DE CONTRATOS E AGENDAMENTOS

Contratos de aferição periódica e agendamentos de serviços (com ou sem contrato).  
**APIs:** `app/api/v1/contratos_afericao.py`, `app/api/v1/agendamentos.py`  
**Tabelas:** `contratos_afericao`, `agendamentos`

---

## Parte 1 — Contrato de Aferição

### Visão
Contratos permitem programar aferições periódicas: periodicidade, valores, equipamentos contratados; geração opcional de aferições programadas.

### Pré-requisitos
- Cliente cadastrado; equipamentos do cliente (para equipamentos_contratados); permissão para contratos.

### Fluxo de Criação (resumo)
Permissão → Selecionar cliente → Número único → Período (data_inicio < data_fim) → Periodicidade (mensal, bimestral, trimestral, semestral, anual) → Equipamentos contratados (opcional) → Criar; opcionalmente gerar aferições programadas.

### Campos obrigatórios
`cliente_id`, `numero_contrato` (único), `data_inicio`, `data_fim`, `periodicidade`, `valor_mensal`. Opcionais: `equipamentos_contratados` (JSON), `status` (ativo/suspenso/cancelado/finalizado), `observacoes`, `contrato_descritivo`.

### Validações
- Cliente existe; número contrato único; data_inicio < data_fim; equipamentos do cliente; periodicidade válida. Erros: 400 (período/equipamentos), 403 (permissão), 404 (cliente).

### APIs
- `POST /api/v1/contratos-afericao` — criar
- `GET /api/v1/contratos-afericao` — listar (filtros: cliente, status)
- `GET /api/v1/contratos-afericao/{id}` — obter
- `PUT /api/v1/contratos-afericao/{id}` — atualizar
- `DELETE /api/v1/contratos-afericao/{id}` — excluir (verificar agendamentos/aferições programadas)

### Regras
- Número de contrato único. Equipamentos devem pertencer ao cliente.

---

## Parte 2 — Agendamento

### Visão
Agendamentos com ou sem contrato; tipos: calibração, aferição, manutenção, inspeção, outro. Podem originar processos de calibração e certificados.

### Pré-requisitos
- Cliente e equipamento(s) cadastrados; se vinculado a contrato, contrato ativo; permissão para agendamentos.

### Fluxo de Criação (resumo)
Permissão → Cliente → Equipamento(s) → Origem: **contrato** (selecionar contrato) ou **avulso** (justificativa) → Data/hora (não passado) → Tipo de serviço → Opcional: técnico responsável, equipamentos_ids (JSON) → Status inicial: pendente.

### Campos obrigatórios
`cliente_id`, `equipamento_id` (principal), `data_agendamento`, `hora_agendamento`, `tipo_servico` (calibracao|afericao|manutencao|inspecao|outro). Condicionais: `contrato_afericao_id` (se contrato), `justificativa_avulso` (se avulso). Opcionais: `equipamentos_ids` (JSON), `duracao_estimada`, `tecnico_responsavel_id`, `observacoes`.

### Status
pendente → confirmado → em_andamento → concluido | cancelado.

### Validações
- Cliente e equipamento existem; equipamento do cliente; se contrato: contrato ativo e do cliente; data/hora não no passado. Erros: 400 (contrato inativo, data inválida), 403, 404.

### APIs
- `POST /api/v1/agendamentos` — criar
- `GET /api/v1/agendamentos` — listar (filtros: cliente, status, data)
- `GET /api/v1/agendamentos/{id}` — obter
- `PUT /api/v1/agendamentos/{id}` — atualizar (ex.: confirmar, cancelar)
- `DELETE /api/v1/agendamentos/{id}` — excluir

### Regras
- Agendamento avulso exige justificativa. Múltiplos equipamentos via `equipamentos_ids` (JSON). Integração com processos: agendamento pode originar processo de calibração.

---

**Referências:** MAPA_SISTEMA (banco e APIs); INDICE.md (este diretório).
