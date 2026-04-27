# FLUXO DE CADASTROS — Cliente, Equipamento e Fornecedor

Fluxos de criação, atualização e gestão de **clientes**, **equipamentos** e **fornecedores**. Cliente é entidade central; equipamento exige cliente; fornecedor é vinculado ao estabelecimento.  
**APIs:** `app/api/v1/clientes.py`, `app/api/v1/equipamentos.py`, `app/api/v1/fornecedores_cliente.py`, `app/api/v1/produtos_fornecedor.py`  
**Tabelas:** `clientes`, `equipamentos`, `fornecedores_cliente`, `produtos_fornecedor`

**Terminologia:** Registros em `clientes` podem representar **Cliente (Empresa Fiscal)** ou **Subcliente (Cliente da Empresa Fiscal)**. Cliente = emissor de notas; Subcliente = destinatário. Ver MAPA_RBAC.md seção "Terminologia – Cliente (Empresa Fiscal) e Subcliente".

---

## Parte 1 — Cliente

### Visão
Cliente obrigatório para equipamentos, contratos, agendamentos e certificados. Cadastro via API `/clientes` ou, para Subclientes, via Minha equipe (`POST /minha-equipe/clientes`).

### Pré-requisitos
- Usuário autenticado; permissão RBAC para criar/editar clientes.

### Fluxo de Criação (resumo)
Permissão → Preencher dados → Validar CNPJ (único, formato) → CEP opcional (ViaCEP) → Criar registro.

### Campos obrigatórios
`nome`, `cnpj` (único), `endereco`, `cidade`, `uf`, `contato`, `telefone`, `email`. Opcional: `cep`.

### Validações
- CNPJ: formato XX.XXX.XXX/XXXX-XX, dígitos verificadores, unicidade (`app/utils/cnpj_validator.py`).
- CEP: ViaCEP para preencher endereço.
- Erros: 400 (CNPJ/email inválido), 403 (sem permissão).

### APIs
- `POST /api/v1/clientes` — criar
- `GET /api/v1/clientes` — listar (filtros: nome, cidade, paginação)
- `GET /api/v1/clientes/{id}` — obter
- `PUT /api/v1/clientes/{id}` — atualizar
- `DELETE /api/v1/clientes/{id}` — excluir (restrito se houver equipamentos/contratos/agendamentos)
- `GET /api/v1/clientes/buscar/cnpj/{cnpj}` — buscar por CNPJ

### Regras
- CNPJ único no sistema. Exclusão: verificar relacionamentos (equipamentos, contratos, agendamentos).

---

## Parte 2 — Equipamento

### Visão
Equipamento sempre vinculado a um cliente; associado a certificados, agendamentos, processos e ordens de serviço.

### Pré-requisitos
- Cliente cadastrado (obrigatório); tipo de equipamento (opcional); permissão para criar/editar equipamentos.

### Fluxo de Cadastro (resumo)
Permissão → Selecionar cliente → Preencher dados (fabricante, modelo, numero_serie, unidade) → Tipo opcional → Criar registro.

### Campos obrigatórios
`cliente_id`, `fabricante`, `modelo`, `numero_serie`, `unidade`. Opcionais: `tipo_equipamento_id`, `patrimonio`, `resolucao`, `capacidade`, `local_calibracao`, `etiqueta_verificado`, `selo_inmetro_reparo`.

### Validações
- Cliente deve existir (404 se não).
- Tipo de equipamento, se informado, deve existir.
- Erros: 400 (dados inválidos), 403 (sem permissão), 404 (cliente/tipo não encontrado).

### APIs
- `POST /api/v1/equipamentos` — criar
- `GET /api/v1/equipamentos` — listar (filtro `cliente_id`, paginação)
- `GET /api/v1/equipamentos/{id}` — obter
- `PUT /api/v1/equipamentos/{id}` — atualizar
- `DELETE /api/v1/equipamentos/{id}` — excluir (restrito se houver certificados/agendamentos/processos)

### Regras
- Cliente obrigatório. Exclusão: verificar certificados, agendamentos, processos.

---

## Parte 3 — Fornecedor por Estabelecimento

### Visão
Fornecedor vinculado a um estabelecimento (cliente_id). Pode ser criado manualmente pela tela `/negocio/fornecedores` ou automaticamente pela importação de XML na Entrada NF-e (`nfe_entrada_service._buscar_ou_criar_emitente`).

### Pré-requisitos
- Usuário autenticado com permissão `negocios.estoque:visualizar` (ou `negocios` / Superadministrador).
- Estabelecimento definido (empresa fiscal do CA). Na rota HTML `/negocio/fornecedores`, **Cliente Administrador** não vê seletor de estabelecimento: o `cliente_id` é sempre o retornado por `get_empresa_fiscal_cliente_id` (igual à Entrada NF-e). Seletor permanece para Superadministrador e para perfis com vários `cliente_id` no escopo (ex.: Administrador com várias lojas).

### Fluxo de Criação Manual
Acessar `/negocio/fornecedores` → "Novo Fornecedor" → Preencher Nome (obrigatório), CNPJ (validado), Contato, Email, Telefone → Salvar. CNPJ é normalizado para dígitos-only (14 chars) e validado via `CNPJValidator`. Se CNPJ duplicado no mesmo estabelecimento → **409 Conflict**.

### Fluxo de Criação Automática (via XML)
Importar NF-e em `/negocio/entrada-nfe` → `nfe_entrada_service.importar_xml` → `_buscar_ou_criar_emitente(...)` → Busca fornecedor por `(cliente_id, cnpj_digitos)`. Se não existe, cria com `nome = razão social do emitente` e `telefone` a partir de `emit/enderEmit/fone` quando existir no XML. Se já existe e `telefone` está vazio, preenche com o fone do XML. Ao conciliar itens, cria vínculos em `produtos_fornecedor` (mapa cProd → produto interno).

### Campos
`nome` (obrigatório), `cnpj` (opcional, 14 dígitos, único por estabelecimento), `contato`, `email`, `telefone`, `ativo`.

### Validações
- CNPJ: dígitos verificadores (`CNPJValidator`), unicidade por `(cliente_id, cnpj)` — UniqueConstraint parcial no banco (migration `fc01`).
- Escopo: `ClienteScope` + `forbid_cliente_access` em todas as rotas.
- Auditoria: `audit_action()` em criar/atualizar/excluir.

### APIs
- `GET /api/v1/fornecedores-cliente/` — listar (query: cliente_id, ativo, busca)
- `GET /api/v1/fornecedores-cliente/{id}` — obter
- `POST /api/v1/fornecedores-cliente/` — criar (409 se CNPJ duplicado)
- `PATCH /api/v1/fornecedores-cliente/{id}` — atualizar
- `DELETE /api/v1/fornecedores-cliente/{id}` — excluir
- `GET /api/v1/produtos-fornecedor/?fornecedor_cliente_id={id}` — listar vínculos produto ↔ fornecedor
- `DELETE /api/v1/produtos-fornecedor/{vinculo_id}` — excluir vínculo

### Regras
- CNPJ único por estabelecimento (quando informado). Múltiplos fornecedores sem CNPJ são permitidos.
- Exclusão de fornecedor: cascade em `produtos_fornecedor`; NF-e documents ficam com `emitente_fornecedor_id = NULL` (SET NULL).
- Produtos vinculados podem ser desvinculados manualmente; o vínculo é recriado na próxima importação de NF-e.

---

**Referências:** MAPA_SISTEMA (estrutura e APIs); MAPA_SISTEMA/INDICE.md para índice geral.
