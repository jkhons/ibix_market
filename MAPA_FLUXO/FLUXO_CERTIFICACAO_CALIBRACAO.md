# FLUXO DE CERTIFICAÇÃO E CALIBRAÇÃO

Geração de certificados (independente ou via processo) e processo completo de calibração até emissão.  
**APIs:** `app/api/v1/certificados.py`, `app/api/v1/processos_v1.py`  
**Tabelas:** `certificados`, `processos`, `processo_balanca_calibracao`, `processo_equipamentos`

---

## Parte 1 — Certificado

### Visão
Certificado vinculado a equipamento (obrigatório), cliente (opcional), processo (obrigatório em modo ISO 17025). Número YYYY-XXXX; status: rascunho → emitido | cancelado; emitido → substituido | cancelado.

### ISO 17025 (obrigatório)
**Certificados surgem exclusivamente de procedimentos completos.** Config `iso_17025_certificados_apenas_processo` (default true). Quando ativo: POST `/certificados` bloqueado; `/certificados/novo` e `/editar` redirecionam para Procedimentos > Calibração. Emissão via `POST /processos/{id}/certificados` cria Certificado + CertificadoSnapshot (XML oficial) automaticamente.

### Pré-requisitos
- Equipamento cadastrado; processo aprovado (se via processo); permissão para certificados.

### Criação
- **Modo ISO 17025 (padrão):** Criação apenas via processo. Finalizar processo → Emitir certificados em `/procedimentos/emitir-certificados/{id}`. Cria Certificado + snapshot XML.
- **Independente (apenas se config false):** Selecionar equipamento → Preencher dados → Criar.
- **Via processo:** Processo concluído → POST `/processos/{id}/certificados` → Copiar dados processo/balança → Gerar número → Vincular processo_balanca_calibracao_id → Criar Certificado + CertificadoSnapshot.

### Campos obrigatórios
`equipamento_id`, `responsavel_id`, `numero` (único, YYYY-XXXX), `tipo` (calibracao|afericao), `data_emissao`, `data_validade`. Opcionais: `cliente_id`, `processo_id`, `processo_balanca_calibracao_id`, `data_ajuste`, `status`, `observacoes`; inspetor/aprovador via `inspetor_aux_cadastro_id`, `aprovador_aux_cadastro_id`.

### Validações
- Equipamento existe; número único; data_validade > data_emissao; se via processo, processo aprovado. Erros: 400 (número/datas), 403, 404.

### APIs
- `POST /api/v1/certificados` — criar
- `GET /api/v1/certificados` — listar
- `GET /api/v1/certificados/{id}` — obter
- `POST /api/v1/certificados/{id}/aprovar` — aprovar (status → emitido)
- `GET /api/v1/certificados/{id}/pdf` — download PDF (ou status pendente/gerando/erro)
- `POST /api/v1/certificados/{id}/pdf` — enfileirar geração PDF

### Regras
- Número único, sequencial (configuracoes). PDF: job assíncrono; armazenamento em `certificado_pdf_path`; hash em `certificado_pdf_hash`.

---

## Parte 2 — Calibração (processo até certificado)

### Visão
Processo com N balanças; etapas: dados iniciais → dados por balança (pesos, equip. aux., inspetor/aprovador) → execução (pré-checagem, ensaios, finalizar) → emissão certificados (equipamentos completos).

### Pré-requisitos
- Cliente e equipamento(s); agendamento ou contrato (opcional); permissão processos.

### Etapa 1 — Dados iniciais
Cliente → Origem (agendamento | contrato | avulso) → Tipo (calibracao|afericao|manutencao|inspecao) → Número processo (PROC-YYYY-NNNNN) → Seleção de equipamentos.

### Etapa 2 — Dados por balança
Por equipamento: criar `processo_balanca_calibracao` → Dados técnicos (local, lacres, portaria) → Vincular certificados de peso (`processo_balanca_aux_cadastros`, papel peso_padrao) → Vincular equipamentos auxiliares (termobarohigrômetro) → Condições ambientais (temperatura, umidade, pressão, massa_ar inicial/final).

### Etapa 3 — Responsáveis
Inspetor e aprovador no **nível do processo** (uma vez): `processos.inspetor_aux_cadastro_id`, `processos.aprovador_aux_cadastro_id`. Endpoint: `PATCH /api/v1/processos/{id}/responsaveis`.

### Etapa 4 — Revisão e finalização
- `GET /api/v1/processos/{id}/auditoria-certificado` — DTO com responsáveis (nomes), datas calculadas (ajuste, emissão, validade), blocos por equipamento (ambientais_ok, pesos_ok, indicacao_ok, excentricidade_ok, mobilidade_ok), resumo (pode_fechar_processo, equipamentos_prontos_para_emitir).
- **Finalizar:** `POST /api/v1/processos/{id}/finalizar`. Regra: ≥1 equipamento completo; inspetor e aprovador definidos. Estado: `concluido_total` ou `concluido_parcial`.

### Execução (por balança)
- Pré-checagem → Ensaio inicial → (se necessário) Ajuste → Ensaio final. Ensaios: excentricidade/indicação (composição de pesos, medições); mobilidade (PESOPADRAO, carga/sobrecarga).
- Medições: `POST .../balancas/{id}/ensaios/medicoes-final`. Validações: pesos vinculados, validade, soma = carga. 422 se pesos vencidos.

### Emissão (ISO 17025)
- Apenas equipamentos com `is_completo=true` (lista `equipamentos_prontos_para_emitir`).
- Emissão via `POST /processos/{id}/certificados` cria Certificado + **CertificadoSnapshot (XML oficial)** por balança; geração PDF em background.

### Endpoints principais (processos)
- `GET/POST /api/v1/processos` — listar, criar
- `GET/PATCH /api/v1/processos/{id}` — obter, atualizar
- `PATCH /api/v1/processos/{id}/responsaveis` — definir inspetor/aprovador
- `GET /api/v1/processos/{id}/balancas` — listar balanças
- `PATCH /api/v1/processos/{id}/balancas/{bid}` — dados da balança
- `POST /api/v1/processos/{id}/balancas/{bid}/aux-cadastros` — vincular peso/equip. aux.
- `PUT .../composicao-pesos` — salvar composição atual
- `POST .../ensaios/medicoes-final` — salvar medições ensaio
- `GET /api/v1/processos/{id}/auditoria-certificado` — auditoria
- `POST /api/v1/processos/{id}/finalizar` — finalizar processo

### Regras
- Datas (ajuste, emissão, validade) calculadas no backend; frontend somente leitura. Conclusão fixa "CONFORME". Excentricidade e mobilidade obrigatórias (por equipamento). Ver MAPA_SISTEMA (Apêndice A — Auditoria).

---

**Referências:** MAPA_SISTEMA (Banco, Auditoria, Impacto); INDICE.md (este diretório).
