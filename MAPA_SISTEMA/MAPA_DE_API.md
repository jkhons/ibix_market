# MAPA DE API - SISTEMA PDV AUTOMSCALE

## Visão Geral

Este documento mapeia todas as APIs REST do PDV Ibix, organizadas por módulo, com métodos HTTP, parâmetros, autenticação e permissões RBAC necessárias.

**Base URL:** `http://127.0.0.1:8000/api/v1`

**Remoção 2026-02-18:** As seguintes APIs e tabelas foram removidas (migration ii88kk914a4): `/api/v1/aux-cadastros`, `/api/v1/certificados-auxiliares`, `/api/v1/inspetores-aprovadores`, `/api/v1/historico-selos`, `/api/v1/lacres-selos`, `/api/v1/procedimentos-metodo`, `/api/v1/reclamacoes`, `/api/v1/treinamentos-competencia`, `/api/v1/auditorias-internas`. As seções deste mapa que descrevem essas APIs ficam como referência histórica.

---

## DOCUMENTAÇÃO INTERATIVA DA API

### Acesso à Documentação
A documentação interativa da API está **desabilitada por padrão** no FastAPI.

- **Swagger UI:** desabilitado (ativar via `docs_url="/docs"` em `main.py`)
- **ReDoc:** desabilitado (ativar via `redoc_url="/redoc"` em `main.py`)
- **Schema OpenAPI:** desabilitado (ativar via `openapi_url="/openapi.json"` em `main.py`)

### Proteção de Segurança

**IMPORTANTE:** Todas as rotas de documentação exigem **autenticação e permissão de SUPER_ADMIN**:
- ✅ **Autenticação obrigatória:** Token JWT válido necessário
- ✅ **Permissão exigida:** Apenas usuários com nível **SUPER_ADMIN** podem acessar

---

## 1. AUTENTICAÇÃO E USUÁRIOS (`/api/v1/auth`)

### Login e Tokens
- **POST** `/auth/login` - Autenticação de usuário PDV (CA, Admin, técnico, etc.)
  - Body: `UserLogin` (`email`, `password`)
  - Response: `LoginResponse` + cookies HttpOnly
  - Dependency DB: **`get_db_pre_auth()`** — com `RLS_ENABLED=true`, bypass temporário para localizar `usuarios` antes do `tenant_id` ser conhecido (ver MAPA_MULTIBRAND § 6)
  - **Cookies setados:** `pdv_solumatica_token` e `pdv_automscale_token` (mesmo JWT)
    - `httponly=true` (JS **não** lê via `document.cookie`; front usa `credentials: 'include'` + `sessionStorage` opcional pós-login)
    - `secure` quando HTTPS / `X-Forwarded-Proto: https`
    - `samesite=lax`, host-only ([brand_cookie.py](../app/core/brand_cookie.py))
  - Pós-login: `assert_user_tenant_matches_request_brand` — CA só entra no domínio da marca do tenant
  - **Rate limit:** restritivo por IP (`check_login_rate_limit`)

- **POST** `/auth/refresh` - Renovar token de acesso
  - Body: `TokenRefreshRequest` (refresh_token)
  - Response: `TokenResponse`
  - Autenticação: Não requerida

- **POST** `/auth/logout` - Encerrar sessão PDV
  - Autenticação: cookie ou Bearer (`AuthMiddleware.get_current_user`)
  - Invalida JWT na blacklist Redis (`jti`)
  - **Sempre** remove cookies `pdv_solumatica_token` e `pdv_automscale_token` via `clear_pdv_auth_cookies()`
  - Front: `user-dropdown.js` → `POST` com `credentials: 'include'` (não depende de token legível no JS)

- **GET** `/logout` (HTML) - Logout via link/navegação
  - Invalida token + `clear_pdv_auth_cookies()` + redirect 302 → `/login`
  - Fallback quando JS do dropdown não intercepta o clique

- **POST** `/auth/forgot-password` — Esqueci minha senha (PDV). Body: `{ "email": "..." }`. Dependency: `get_db_pre_auth`. Resposta sempre genérica. Rate limit: `check_forgot_password_rate_limit`. Link `/auth/redefinir-senha?token=...`.
- **GET** `/auth/redefinir-senha/valida?token=...` — Valida token. Dependency: `get_db_pre_auth`.
- **POST** `/auth/redefinir-senha` — Redefine senha. Dependency: `get_db_pre_auth`. Rate limit: `check_reset_password_rate_limit`.

### Informações do Usuário
- **GET** `/auth/me` - Obter informações do usuário atual
  - Response: `UsuarioResponse`
  - Autenticação: Requerida (Bearer Token)

- **GET** `/auth/roles` - Listar roles (para select na UI de usuários)
  - Response: `[{ "id", "nome", "descricao", "ativo" }, ...]`
  - Permissão: `usuarios:visualizar`
  - **Cliente Administrador:** retorna apenas roles **Técnico** e **Subcliente** (hierarquia abaixo); Superadministrador e Administrador recebem todas as roles ativas.

---

## 2. CLIENTES (`/api/v1/clientes`)

**Escopo:** Listagens e operações respeitam `ClienteScope` (Superadministrador = todos; Administrador = `administrador_clientes`; Cliente Administrador = `cliente_administrador_clientes`; Subcliente/AreaCliente = um). Ver `app/core/scope.py` e `MAPA_RBAC.md`. **Nota:** Cliente = Empresa Fiscal; Subcliente = Cliente da Empresa Fiscal. API de clientes opera sobre ambos conforme escopo.

**PII (LGPD — br34/br36):** Respostas passam por `apply_cliente_pii_mask` ([pii.py](../app/core/pii.py)). Campos mascarados sem permissão: `cpf`, `cnpj`, `telefone`, `email` (ex.: CNPJ → `**.***.***/****-XX`). Quem vê dados completos: **Superadministrador**, **Administrador**, **Cliente Administrador** (`pii:visualizar` ou role nativa — ver MAPA_RBAC § 0.14). Alteração de PII exige `pii:visualizar` + audit `pii_alteracao_cliente`.

- **GET** `/clientes/` - Listar clientes
  - Query params: `nome`, `cnpj`, `cidade`, `uf`, `pagina`, `por_pagina`
  - Response: `ClienteListResponse`
  - Permissão: `certificacao:clientes:visualizar`
  - Autenticação: Requerida

- **POST** `/clientes/` - Criar cliente
  - Body: `ClienteCreate` (nome, cnpj, cep, endereco, cidade, uf, contato, telefone, email)
  - Response: `ClienteResponse`
  - Permissão: `certificacao:clientes:gerenciar`
  - Autenticação: Requerida
  - **Validações:**
    - CNPJ válido e único
    - CEP válido (formato: XXXXX-XXX)
    - Email válido
  - **Erros de validação:** retorna `422 Unprocessable Entity` com detalhes por campo

- **GET** `/clientes/{id}` - Obter cliente específico
  - Response: `ClienteResponse`
  - Permissão: `certificacao:clientes:visualizar`
  - Autenticação: Requerida

- **PUT** `/clientes/{id}` - Atualizar cliente
  - Body: `ClienteUpdate`
  - Response: `ClienteResponse`
  - Permissão: `certificacao:clientes:gerenciar`
  - Autenticação: Requerida

- **DELETE** `/clientes/{id}` - Remover cliente
  - Response: `204 No Content`
  - Permissão: `certificacao:clientes:gerenciar`
  - Autenticação: Requerida

- **POST** `/clientes/{cliente_id}/usuarios` - Criar usuário do cliente (role **Subcliente**)
  - Body: `UsuarioClienteCreate` (nome, email, senha, cliente_id; ativo opcional). Sem escolha de função: sempre Subcliente.
  - Response: `UsuarioResponse`
  - Autenticação: Requerida. **Autorização:** Superadministrador/Administrador ou Cliente Administrador quando `cliente_id` está no escopo (`require_admin_or_ca_scope_para_criar_usuario`). Não usa `require_permission`.
  - **Comportamento:** Cria usuário com role Subcliente e registro em `areas_cliente` (acesso dentro da organização do CA). Lugar e função distintos de `/minha-equipe/tecnicos` (que cria/vincula Técnico). Ver MAPA_RBAC.md § 0.11 e 0.12.

---

## 3. EQUIPAMENTOS (`/api/v1/equipamentos`)

- **GET** `/equipamentos/` - Listar equipamentos
  - Query params: `skip`, `limit`, `cliente_id`, `tipo_equipamento_id`, `busca`
  - Response: `List[EquipamentoResponse]`
  - Permissão: `certificacao:equipamentos:visualizar`
  - Autenticação: Requerida

- **POST** `/equipamentos/` - Criar equipamento
  - Body: `EquipamentoCreate` (fabricante, modelo, numero_serie, patrimonio, unidade, resolucao, capacidade, cliente_id, tipo_equipamento_id)
  - Response: `EquipamentoResponse`
  - Permissão: `certificacao:equipamentos:gerenciar`
  - Autenticação: Requerida

- **GET** `/equipamentos/{id}` - Obter equipamento específico
  - Response: `EquipamentoResponse`
  - Permissão: `certificacao:equipamentos:visualizar`
  - Autenticação: Requerida

- **PUT** `/equipamentos/{id}` - Atualizar equipamento
  - Body: `EquipamentoUpdate`
  - Response: `EquipamentoResponse`
  - Permissão: `certificacao:equipamentos:gerenciar`
  - Autenticação: Requerida

- **DELETE** `/equipamentos/{id}` - Remover equipamento
  - Response: `204 No Content`
  - Permissão: `certificacao:equipamentos:gerenciar`
  - Autenticação: Requerida

---

## 4. TIPOS DE EQUIPAMENTO (`/api/v1/tipo-equipamento`)

- **GET** `/tipo-equipamento/` - Listar tipos de equipamento
  - Query params: `skip`, `limit`, `ativo`
  - Response: `List[TipoEquipamentoResponse]`
  - Permissão: `certificacao:equipamentos:visualizar`
  - Autenticação: Requerida

- **POST** `/tipo-equipamento/` - Criar tipo de equipamento
  - Body: `TipoEquipamentoCreate` (nome, descricao)
  - Response: `TipoEquipamentoResponse`
  - Permissão: `certificacao:equipamentos:gerenciar`
  - Autenticação: Requerida

- **GET** `/tipo-equipamento/{id}` - Obter tipo específico
  - Response: `TipoEquipamentoResponse`
  - Permissão: `certificacao:equipamentos:visualizar`
  - Autenticação: Requerida

- **PUT** `/tipo-equipamento/{id}` - Atualizar tipo
  - Body: `TipoEquipamentoUpdate`
  - Response: `TipoEquipamentoResponse`
  - Permissão: `certificacao:equipamentos:gerenciar`
  - Autenticação: Requerida

- **DELETE** `/tipo-equipamento/{id}` - Remover tipo
  - Response: `204 No Content`
  - Permissão: `certificacao:equipamentos:gerenciar`
  - Autenticação: Requerida

---

## 5. CERTIFICADOS (`/api/v1/certificados`)

- **GET** `/certificados/` - Listar certificados
  - Query params: `skip`, `limit`, `numero`, `tipo`, `equipamento_id`, `cliente_id`, `numero_serie`, `status`, `data_inicio`, `data_fim`, `origem_calibracao` (bool), `processo_id`
  - Response: `List[CertificadoResponse]`
  - Escopo SaaS: `ClienteScope` (Admin/Cliente Admin filtram por `allowed_ids`; Técnico vê clientes do CA vinculado)
  - `origem_calibracao=true`: apenas certificados com `processo_id` não nulo (emitidos via procedimentos/calibração)
  - Permissão: `certificacao:certificados:visualizar`
  - Autenticação: Requerida

- **POST** `/certificados/` - Criar certificado
  - Body: `CertificadoCreate` (numero, tipo, data_emissao, data_validade, equipamento_id, responsavel_id, cliente_id opcional)
  - Response: `CertificadoResponse` ou **403 Forbidden** quando ISO 17025 ativo
  - Permissão: `certificacao:certificados:criar`
  - Autenticação: Requerida
  - **ISO 17025:** Quando `configuracoes.iso_17025_certificados_apenas_processo = true`, retorna 403 com mensagem orientando emissão via Procedimentos > Calibração. Em modo ISO, use `POST /processos/{id}/certificados`.
  - **Validações:**
    - Número único (formato: YYYY-XXXX)
    - Equipamento deve existir
    - Cliente deve existir (se fornecido)
    - Data validade >= data emissão

- **GET** `/certificados/{id}` - Obter certificado específico
  - Response: `CertificadoResponse`
  - Permissão: `certificacao:certificados:visualizar`
  - Autenticação: Requerida

- **PUT** `/certificados/{id}` - Atualizar certificado
  - Body: `CertificadoUpdate`
  - Response: `CertificadoResponse`
  - Permissão: `certificacao:certificados:editar`
  - Autenticação: Requerida

- **DELETE** `/certificados/{id}` - Remover certificado
  - Response: `204 No Content`
  - Permissão: `certificacao:certificados:deletar`
  - Autenticação: Requerida

- **POST** `/certificados/{id}/aprovar` - Aprovar certificado
  - Response: `CertificadoResponse`
  - Permissão: `certificacao:certificados:aprovar`
  - Autenticação: Requerida
  - **Validações:**
    - Certificado deve estar em status válido para aprovação
    - Usuário deve ser aprovador cadastrado

- **POST** `/certificados/{id}/validar` - Validar certificado
  - Response: `CertificadoResponse`
  - Permissão: `certificacao:certificados:validar`
  - Autenticação: Requerida

  - Permissão: `certificacao:certificados:visualizar`
  - Autenticação: Requerida

- **POST** `/certificados/{id}/pdf` - Enfileirar geração de PDF (job assíncrono)
  - Response: `{ message, certificado_id }`
  - Permissão: `certificados:gerar_pdf`
  - Autenticação: Bearer
  - **Validações:**
    - Certificado deve existir
    - Certificado não pode estar cancelado
    - Se PDF já está em geração, retorna: `{"message": "PDF ja em geracao"}`
    - Se PDF já está pronto, retorna: `{"message": "PDF ja disponivel"}`
  - **Comportamento:**
    - Enfileira job assíncrono via `BackgroundTasks`
    - Atualiza `certificado_pdf_status` para `"pendente"`
    - Job executa `run_gerar_pdf()` do serviço `app/services/pdf_certificado_job.py`
    - Geração usa ReportLab (se disponível) ou fallback mínimo
    - PDF salvo via `IStorage` (FilesystemStorage) em `{ano}/{certificado_id}.pdf`
    - Atualiza campos: `certificado_pdf_path`, `certificado_pdf_hash`, `certificado_pdf_gerado_em`
    - Status final: `"gerando"` → `"pronto"` ou `"erro"`

- **GET** `/certificados/{id}/pdf` - Download do PDF (quando pronto)
  - Response: `FileResponse` (PDF) ou `202` se pendente/gerando
  - Permissão: `certificados:baixar`
  - Autenticação: Bearer
  - **Comportamento:**
    - Se `certificado_pdf_status == "pronto"` e `certificado_pdf_path` existe: retorna PDF
    - Se `certificado_pdf_status` em `("pendente", "gerando")`: retorna `202 Accepted`
    - Se PDF não gerado ou erro: retorna `404 Not Found`
    - Nome do arquivo: `certificado-{numero ou id}.pdf`

- **POST** `/certificados/{id}/cancelar` - Cancelar certificado (motivo obrigatório)
  - Body: `{ motivo: str }`
  - Permissão: `certificados:cancelar`
  - Autenticação: Bearer

- **POST** `/certificados/{id}/reemitir` - Reemitir (novo número; antigo → `substituido`)
  - Response: `{ certificado_id, numero, substitui_certificado_id }`
  - Permissão: `certificados:reemitir`
  - Autenticação: Bearer

- **GET** `/certificados/{id}/export` - Exportar certificado (JSON/XML)
  - Query: `format=json|xml`
  - Permissão: `certificados:exportar`
  - Autenticação: Bearer

- **POST** `/certificados/{id}/emitir` - Emitir certificado (snapshot XML oficial)
  - Gera snapshot XML imutável, grava em `certificado_snapshot`, trava certificado como emitido
  - Response: `{ message, certificado_id, snapshot_id, versao, hash_sha256 }`
  - Permissão: `certificados:emitir`
  - Autenticação: Bearer
  - **ISO 17025:** Quando ativo, exige `certificado.processo_id` e processo em etapa `concluido_total`/`concluido_parcial`/`concluido`/`reprovado`. Certificados sem processo retornam 400.
  - Validações: certificado não pode estar emitido, cancelado ou substituído

- **GET** `/certificados/{id}/snapshot` - Download do snapshot XML oficial
  - Retorna XML do snapshot ATIVO; se não houver, gera sob demanda
  - Response: `application/xml`
  - Permissão: `certificados:baixar`
  - Autenticação: Bearer

**Emissão por processo (ISO 17025 — fluxo principal):**

- **POST** `/api/v1/processos/{processo_id}/certificados` - Emitir certificados
  - Body: `{ processo_balanca_id }` ou `{ emitir_todos: true }`
  - Permissão: `certificados:emitir`
  - Autenticação: Bearer
  - **Cria Certificado + CertificadoSnapshot (XML oficial)** automaticamente. Processo deve estar concluído.

- **GET** `/api/v1/processos/{processo_id}/certificados` - Listar certificados do processo
  - Response: `{ processo_id, certificados: [...] }`
  - Autenticação: Bearer

---

## 6. CADASTROS AUXILIARES UNIFICADOS (`/api/v1/aux-cadastros`)

**⚠️ IMPORTANTE:** Esta é a **API principal unificada** para todos os tipos de cadastros auxiliares. Os endpoints em `/certificados-auxiliares` e `/inspetores-aprovadores` são **fachadas de compatibilidade** que internamente usam esta API.

**Estrutura Unificada:**
- **Tabela:** `aux_cadastros` (substitui `certificados_auxiliares`, `certificados_pesos`, `inspetores_aprovadores`)
- **Categorias:** `aux_categorias` (TERMOBAROHIGROMETRO, PESO, **PESOPADRAO**, INSPETOR_APROVADOR)
- **PESOPADRAO:** Código da categoria sem underscore; nome ex.: "PESO PADRAO". `atributos_json` inclui `valor_nominal`, `unidade`, `classe`, `carga_kg`, `sobrecarga_kg`.
- **Arquivos:** `aux_arquivos` (substitui campos de arquivo nas tabelas antigas)
- **Vínculos:** `processo_balanca_aux_cadastros` (tabela intermediária unificada)

### 6.0.1. API Principal - Cadastros Auxiliares

**Escopo (obrigatório):** Todas as operações são filtradas por **responsável**: apenas cadastros com `responsavel_id == usuário logado`. Listagem retorna só cadastros do usuário; GET/PUT/DELETE por ID e endpoints de arquivos (upload, listar, principal, download) verificam propriedade (senão 404); na criação, `responsavel_id` é sempre definido como o usuário logado. GET `/inspetores-aprovadores` também filtra por `responsavel_id`. Implementação: `app/api/v1/aux_cadastros.py` (helper `_cadastro_pertence_ao_usuario`). A página `/certificados-auxiliares` chama GET `/aux-cadastros`; cada usuário vê apenas seus certificados auxiliares.

- **GET** `/aux-cadastros/` - Listar cadastros auxiliares
  - Query params: `categoria_codigo` (TERMOBAROHIGROMETRO, PESO, PESOPADRAO, INSPETOR_APROVADOR), `ativo`, `skip`, `limit`
  - Response: `AuxCadastroListResponse`
  - Escopo: apenas `responsavel_id == current_user.id`
  - Permissão: `certificacao:aux_cadastros:visualizar`
  - Autenticação: Requerida

- **GET** `/aux-cadastros/{id}` - Obter cadastro auxiliar específico
  - Response: `AuxCadastroResponse`
  - Escopo: 404 se cadastro não for do usuário logado
  - Permissão: `certificacao:aux_cadastros:visualizar`
  - Autenticação: Requerida

- **POST** `/aux-cadastros/` - Criar cadastro auxiliar
  - Body: `AuxCadastroCreate` (categoria_id, nome_titulo, identificador, atributos_json, etc.)
  - Response: `AuxCadastroResponse`
  - Escopo: `responsavel_id` definido como usuário logado (ignora valor do body)
  - Permissão: `certificacao:aux_cadastros:gerenciar`
  - Autenticação: Requerida
  - **Validações:**
    - Unicidade: `(categoria_id, identificador)`
    - Unicidade: `certificado_numero` (quando preenchido, após normalização)
    - Para INSPETOR_APROVADOR: unicidade de CPF e email (via generated columns)

- **PUT** `/aux-cadastros/{id}` - Atualizar cadastro auxiliar
  - Body: `AuxCadastroUpdate`
  - Response: `AuxCadastroResponse`
  - Escopo: 404 se cadastro não for do usuário logado
  - Permissão: `certificacao:aux_cadastros:gerenciar`
  - Autenticação: Requerida

- **DELETE** `/aux-cadastros/{id}` - Remover cadastro auxiliar
  - Response: `204 No Content`
  - Escopo: 404 se cadastro não for do usuário logado
  - Permissão: `certificacao:aux_cadastros:gerenciar`
  - Autenticação: Requerida

- **POST** `/aux-cadastros/{id}/arquivos` - Upload de arquivo
  - Body: FormData (arquivo, tipo_arquivo, principal)
  - Response: `AuxArquivoResponse`
  - Escopo: 404 se cadastro não for do usuário logado
  - Permissão: `certificacao:aux_cadastros:gerenciar`
  - Autenticação: Requerida

- **GET** `/aux-cadastros/{id}/arquivos` - Listar arquivos do cadastro
  - Response: `List[AuxArquivoResponse]`
  - Escopo: 404 se cadastro não for do usuário logado
  - Permissão: `certificacao:aux_cadastros:visualizar`
  - Autenticação: Requerida

### 6.0.2. Vínculos com Processos de Calibração

- **POST** `/processos/{processo_id}/balancas/{balanca_id}/aux-cadastros` - Adicionar vínculo auxiliar
  - Body: `{ aux_cadastro_id: int, papel: "equipamento_auxiliar" | "peso_padrao" | "inspetor" | "aprovador", ordem?: int }`
  - Response: `ProcessoBalancaAuxCadastroResponse`
  - Permissão: `processos:editar`
  - Autenticação: Requerida
  - **Validações:**
    - `ordem` obrigatória apenas para `papel="peso_padrao"`
    - Unicidade: `(processo_balanca_calibracao_id, aux_cadastro_id, papel)`

- **GET** `/processos/{processo_id}/balancas/{balanca_id}/aux-cadastros` - Listar vínculos auxiliares
  - Query params: `papel` (opcional, filtrar por papel)
  - Response: `List[ProcessoBalancaAuxCadastroResponse]`
  - Permissão: `processos:visualizar`
  - Autenticação: Requerida

- **DELETE** `/processos/{processo_id}/balancas/{balanca_id}/aux-cadastros/{vinculo_id}` - Remover vínculo auxiliar
  - Response: `204 No Content`
  - Permissão: `processos:editar`
  - Autenticação: Requerida

**Endpoints de Conveniência (opcionais):**
- `GET /processos/{id}/balancas/{bid}/equipamentos-auxiliares` → Filtra `papel='equipamento_auxiliar'`
- `GET /processos/{id}/balancas/{bid}/pesos-padrao` → Filtra `papel='peso_padrao'`, ordena por `ordem`
- `GET /processos/{id}/balancas/{bid}/inspetores` → Filtra `papel='inspetor'`
- `GET /processos/{id}/balancas/{bid}/aprovadores` → Filtra `papel='aprovador'`

---

## 6. CERTIFICADOS AUXILIARES (Fachadas de Compatibilidade)

**⚠️ NOTA:** Os endpoints abaixo são **fachadas de compatibilidade** que internamente usam `/api/v1/aux-cadastros`. Para novos desenvolvimentos, use a API unificada acima.

O sistema possui 3 tipos de certificados auxiliares gerenciados através de diferentes endpoints:

### 6.1. TERMOBAROHIGROMETRO (`/api/v1/certificados-auxiliares`)

**Tabela:** `certificados_auxiliares` (legado) → **Internamente:** `aux_cadastros` com categoria TERMOBARO

**Tabela:** `certificados_auxiliares` (com `tipo = 'equipamento'`)

- **GET** `/certificados-auxiliares/` - Listar certificados auxiliares
  - Query params: `skip`, `limit`, `tipo`, `ativo`, `nome`
  - Response: `List[CertificadoAuxiliarResponse]`
  - Permissão: `termobarohigrometro` ou `certificacao:certificados_auxiliares:visualizar`
  - Autenticação: Requerida

- **POST** `/certificados-auxiliares/` - Criar certificado auxiliar
  - Body: `CertificadoAuxiliarCreate` (nome, tipo='equipamento', fabricante, modelo, numero_serie, certificado_numero, data_calibracao, data_validade, responsavel_id)
  - Response: `CertificadoAuxiliarResponse`
  - Permissão: `termobarohigrometro` ou `certificacao:certificados_auxiliares:gerenciar`
  - Autenticação: Requerida

- **GET** `/certificados-auxiliares/{id}` - Obter certificado auxiliar específico
  - Response: `CertificadoAuxiliarResponse`
  - Permissão: `termobarohigrometro` ou `certificacao:certificados_auxiliares:visualizar`
  - Autenticação: Requerida

- **PUT** `/certificados-auxiliares/{id}` - Atualizar certificado auxiliar
  - Body: `CertificadoAuxiliarUpdate`
  - Response: `CertificadoAuxiliarResponse`
  - Permissão: `termobarohigrometro` ou `certificacao:certificados_auxiliares:gerenciar`
  - Autenticação: Requerida

- **DELETE** `/certificados-auxiliares/{id}` - Remover certificado auxiliar
  - Response: `204 No Content`
  - Permissão: `termobarohigrometro` ou `certificacao:certificados_auxiliares:gerenciar`
  - Autenticação: Requerida

### 6.2. PESO (`/api/v1/certificados-auxiliares/peso`)

**Tabela:** `certificados_pesos` (legado) → **Internamente:** `aux_cadastros` com categoria PESO (fachada para peso sem carga/sobrecarga).

**Nota PESOPADRAO:** A categoria **PESOPADRAO** (código sem underscore; nome "PESO PADRAO") é distinta: cadastro via **API unificada** `POST/PUT /api/v1/aux-cadastros` com `atributos_json` contendo `valor_nominal`, `unidade`, `classe`, `carga_kg`, `sobrecarga_kg`. Interface: `/certificados-auxiliares/cadastro` ao selecionar categoria "PESO PADRAO".

- **GET** `/certificados-auxiliares/peso` - Listar certificados de peso
  - Query params: `skip`, `limit`, `ativo`, `identificacao`, `classe`
  - Response: `CertificadoPesoListResponse`
  - Permissão: `peso` ou `certificacao:certificados_pesos:visualizar`
  - Autenticação: Requerida

- **POST** `/certificados-auxiliares/peso` - Criar certificado de peso
  - Body: `CertificadoPesoCreate` (identificacao, valor_nominal, unidade, classe, certificado_numero, data_calibracao, data_validade)
  - Response: `CertificadoPesoResponse`
  - Permissão: `peso` ou `certificacao:certificados_pesos:gerenciar`
  - Autenticação: Requerida

- **GET** `/certificados-auxiliares/peso/{id}` - Obter certificado de peso específico
  - Response: `CertificadoPesoResponse`
  - Permissão: `peso` ou `certificacao:certificados_pesos:visualizar`
  - Autenticação: Requerida

- **PUT** `/certificados-auxiliares/peso/{id}` - Atualizar certificado de peso
  - Body: `CertificadoPesoUpdate`
  - Response: `CertificadoPesoResponse`
  - Permissão: `peso` ou `certificacao:certificados_pesos:gerenciar`
  - Autenticação: Requerida

- **DELETE** `/certificados-auxiliares/peso/{id}` - Remover certificado de peso
  - Response: `204 No Content`
  - Permissão: `peso` ou `certificacao:certificados_pesos:gerenciar`
  - Autenticação: Requerida

- **POST** `/certificados-auxiliares/peso/{id}/upload-pdf` - Upload de PDF
  - Body: FormData com arquivo PDF
  - Response: `CertificadoPesoResponse`
  - Permissão: `peso` ou `certificacao:certificados_pesos:gerenciar`
  - Autenticação: Requerida

- **GET** `/certificados-auxiliares/peso/{id}/download-pdf` - Download de PDF
  - Response: Arquivo PDF
  - Permissão: `peso` ou `certificacao:certificados_pesos:visualizar`
  - Autenticação: Requerida

### 6.3. INSPETORES/APROVADORES (`/api/v1/inspetores-aprovadores`)

**Tabela:** `inspetores_aprovadores` (legado) → **Internamente:** `aux_cadastros` com categoria INSPETOR_APROVADOR

**Uso no módulo de calibração:** A página `/procedimentos/calibracao` deve consumir **esta API** para o card Inspetor/Aprovador (dados JSON). **Não** usar `/certificados/inspetores` (rota HTML). Ex.: `GET /inspetores-aprovadores?tipo=inspetor&ativo=true`, `GET /inspetores-aprovadores?tipo=aprovador&ativo=true`. Ver MAPA_FLUXO/FLUXO_CERTIFICACAO_CALIBRACAO.md (Parte 2).

- **GET** `/inspetores-aprovadores/` - Listar inspetores/aprovadores
  - Query params: `skip`, `limit`, `nome`, `cpf`, `email`, `tipo`, `ativo`, `cargo`
  - Response: `InspetorAprovadorListResponse`
  - Permissão: `inspetores` ou `configuracoes:inspetores_aprovadores:visualizar`
  - Autenticação: Requerida

- **POST** `/inspetores-aprovadores/` - Criar inspetor/aprovador
  - Body: `InspetorAprovadorCreate` (nome, cpf, email, cargo, tipo, dados pessoais, endereço, dados profissionais)
  - Response: `InspetorAprovadorResponse`
  - Permissão: `inspetores` ou `configuracoes:inspetores_aprovadores:gerenciar`
  - Autenticação: Requerida

- **GET** `/inspetores-aprovadores/{id}` - Obter inspetor/aprovador específico
  - Response: `InspetorAprovadorResponse`
  - Permissão: `inspetores` ou `configuracoes:inspetores_aprovadores:visualizar`
  - Autenticação: Requerida

- **PUT** `/inspetores-aprovadores/{id}` - Atualizar inspetor/aprovador
  - Body: `InspetorAprovadorUpdate`
  - Response: `InspetorAprovadorResponse`
  - Permissão: `inspetores` ou `configuracoes:inspetores_aprovadores:gerenciar`
  - Autenticação: Requerida

- **DELETE** `/inspetores-aprovadores/{id}` - Remover inspetor/aprovador
  - Response: `204 No Content`
  - Permissão: `inspetores` ou `configuracoes:inspetores_aprovadores:gerenciar`
  - Autenticação: Requerida

---

> **Nota (fev/2025):** APIs e tabelas **removidas** — `/api/v1/afericoes`, `/api/v1/contratos-afericao`; tabelas droppadas: `afericoes_programadas`, `comprovantes_afericao`, `contratos_afericao` (migration hh77jj803z3). Agendamentos permanece ativo, sem vínculo a contratos; coluna `contrato_afericao_id` removida.

---

## 7. ENSAIOS (`/api/v1/ensaios`)

- **GET** `/ensaios/excentricidade/{certificado_id}` - Listar ensaios de excentricidade
  - Response: `List[EnsaioExcentricidadeResponse]`
  - Permissão: `certificacao:certificados:visualizar`
  - Autenticação: Requerida

- **POST** `/ensaios/excentricidade/` - Criar ensaio de excentricidade
  - Body: `EnsaioExcentricidadeCreate` (certificado_id, posicao, valor)
  - Response: `EnsaioExcentricidadeResponse`
  - Permissão: `certificacao:certificados:editar`
  - Autenticação: Requerida

- **GET** `/ensaios/mobilidade/{certificado_id}` - Listar ensaios de mobilidade
  - Response: `List[EnsaioMobilidadeResponse]`
  - Permissão: `certificacao:certificados:visualizar`
  - Autenticação: Requerida

- **POST** `/ensaios/mobilidade/` - Criar ensaio de mobilidade
  - Body: `EnsaioMobilidadeCreate` (certificado_id, tipo, valor)
  - Response: `EnsaioMobilidadeResponse`
  - Permissão: `certificacao:certificados:editar`
  - Autenticação: Requerida

---

## 8. PROCESSOS (`/api/v1/processos`)

Sistema de processos de certificação que suporta múltiplos equipamentos por processo, com dados individuais de calibração para cada equipamento.

### Endpoints Principais

- **POST** `/processos` - Criar novo processo com múltiplos equipamentos
  - Body: `ProcessoCreate`
    ```json
    {
      "tipo_processo": "calibracao",
      "cliente_id": 1,
      "agendamento_id": 1,
      "contrato_id": null,
      "equipamentos": [1, 2, 3]
    }
    ```
  - Response: `ProcessoResponse` (201 Created)
  - Permissão: `processos:criar`
  - Autenticação: Requerida
  - **Validações:**
    - Cliente deve existir
    - Pelo menos 1 equipamento deve ser fornecido
    - Todos os equipamentos devem pertencer ao cliente
    - Gera número do processo automaticamente: `PROC-{ano}-{sequencial}`

- **GET** `/processos` - Listar processos com contagem de equipamentos
  - Query params: `skip`, `limit`, `cliente_id`, `tipo_processo`, `status_global`
  - Response: `List[ProcessoResponse]`
  - Permissão: `processos:visualizar`
  - Autenticação: Requerida

- **GET** `/processos/{processo_id}` - Buscar processo com todos os equipamentos
  - Response: `ProcessoResponse` com lista de `processo_equipamentos` e campos `inspetor_aux_cadastro_id`, `aprovador_aux_cadastro_id`
  - Permissão: `processos:visualizar`
  - Autenticação: Requerida

- **PATCH** `/processos/{processo_id}` - Atualizar dados gerais do processo
  - Body: `ProcessoUpdate` (campos parciais)
  - Response: `ProcessoResponse`
  - Permissão: `processos:editar`
  - Autenticação: Requerida

- **PATCH** `/processos/{processo_id}/responsaveis` - Definir inspetor/aprovador do processo (Etapa 3)
  - Body: `{"inspetor_aux_cadastro_id": 123, "aprovador_aux_cadastro_id": 456}`
  - Response: `ProcessoResponse` (com campos `inspetor_aux_cadastro_id` e `aprovador_aux_cadastro_id` atualizados)
  - Permissão: `processos:editar`
  - Autenticação: Requerida
  - **Validações:**
    - IDs devem existir em `aux_cadastros`
    - Categoria do `aux_cadastro` deve ser `INSPETOR_APROVADOR`
    - `atributos_json.tipo` deve ser compatível com o papel (inspetor/aprovador/ambos)
  - **Comportamento:**
    - Atualiza `processos.inspetor_aux_cadastro_id` e `processos.aprovador_aux_cadastro_id`
    - Estes valores são replicados para todos os certificados gerados do processo na emissão

### Endpoints de Equipamentos do Processo

- **POST** `/processos/{processo_id}/equipamentos` - Associar equipamentos ao processo
  - Body: `{"equipamentos": [1, 2, 3]}`
  - Response: `List[ProcessoEquipamentoResponse]`
  - Permissão: `processos:editar`
  - Autenticação: Requerida
  - **Comportamento:**
    - Cria automaticamente registros em `processo_equipamentos` se não existirem
    - Define ordem sequencial automaticamente

- **GET** `/processos/{processo_id}/equipamentos` - Listar equipamentos do processo
  - Response: `List[ProcessoEquipamentoResponse]`
  - Permissão: `processos:visualizar`
  - Autenticação: Requerida

### Endpoints de Etapas do Processo

- **PATCH** `/processos/{processo_id}/pre-checagem` - Atualizar pré-checagem
  - Body: `PreChecagemUpdate`
    ```json
    {
      "pre_checagem_data": "2025-01-15T10:00:00",
      "pre_checagem_tecnico_id": 1,
      "pre_checagem_resultado": "aprovado",
      "pre_checagem_checklist": {
        "condicoes_fisicas": "ok",
        "nivelamento": "ok",
        "energia_adequada": "ok"
      },
      "pre_checagem_observacoes": "...",
      "pre_checagem_foto": "/uploads/foto.jpg"
    }
    ```
  - Response: `ProcessoResponse`
  - Permissão: `processos:editar`
  - Autenticação: Requerida

- **PATCH** `/processos/{processo_id}/ensaio` - Atualizar ensaio inicial/final
  - Body: `EnsaioUpdate`
    ```json
    {
      "ensaio_inicial_data": "2025-01-15T11:00:00",
      "ensaio_inicial_resultado": "aprovado",
      "temperatura_ambiente": 23.5,
      "umidade_relativa": 55.0,
      "medicoes_json": [
        {
          "ponto": 1,
          "valor_nominal": 10.000,
          "leitura_1": 10.001,
          "leitura_2": 10.002,
          "leitura_3": 10.001,
          "media": 10.0013,
          "erro": 0.0013,
          "dentro_tolerancia": true
        }
      ]
    }
    ```
  - Response: `ProcessoResponse`
  - Permissão: `processos:editar`
  - Autenticação: Requerida

- **PATCH** `/processos/{processo_id}/ajuste` - Registrar ajuste técnico
  - Body: `AjusteUpdate`
    ```json
    {
      "ajuste_realizado": true,
      "ajuste_data_inicio": "2025-01-15T12:00:00",
      "ajuste_data_fim": "2025-01-15T13:30:00",
      "ajuste_tecnico_id": 1,
      "ajuste_tipo": "eletronico",
      "ajuste_pontos": {
        "ponto_zero": true,
        "ponto_span": true,
        "linearidade": false
      },
      "ajuste_descricao": "...",
      "ajuste_foto": "/uploads/ajuste.jpg"
    }
    ```
  - Response: `ProcessoResponse`
  - Permissão: `processos:editar`
  - Autenticação: Requerida

### Validação e Finalização

- **GET** `/processos/{processo_id}/auditoria-certificado` - Obter auditoria completa do processo (2026-02-01)
  - Response: `AuditoriaProcessoResponse` (JSON consolidado)
  - Estrutura da resposta:
    ```json
    {
      "processo_id": int,
      "numero_processo": string,
      "responsaveis": {
        "inspetor_id": int,
        "inspetor_nome": string,
        "aprovador_id": int,
        "aprovador_nome": string
      },
      "regras": {
        "exige_excentricidade": true,
        "exige_mobilidade": true,
        "datas_no_front": false,
        "conclusao_fixa": "CONFORME"
      },
      "equipamentos": [
        {
          "equipamento_id": int,
          "processo_balanca_id": int,
          "processo_equipamento_id": int,
          "nome": string,
          "datas_calculadas": {
            "ajuste": "YYYY-MM-DD",
            "emissao": "YYYY-MM-DD",
            "validade": "YYYY-MM-DD"
          },
          "blocos": {
            "ambientais_ok": bool,
            "pesos_ok": bool,
            "indicacao_ok": bool,
            "excentricidade_ok": bool,
            "mobilidade_ok": bool
          },
          "is_completo": bool,
          "missing": [string]
        }
      ],
      "resumo": {
        "total_equipamentos": int,
        "completos": int,
        "incompletos": int,
        "pode_fechar_processo": bool,
        "equipamentos_prontos_para_emitir": [int]
      }
    }
    ```
  - **Datas calculadas automaticamente:**
    - `ajuste`: data_conclusao do processo (ou date.today() como fallback)
    - `emissao`: date.today() (sempre atual)
    - `validade`: ajuste + 365 dias (12 meses)
  - **Blocos de validação:**
    - `ambientais_ok`: temperatura/umidade/pressão inicial e final preenchidos
    - `pesos_ok`: pelo menos 1 peso vinculado à balança
    - `indicacao_ok`: ensaio inicial e final com pelo menos 1 ponto cada
    - `excentricidade_ok`: JSON de excentricidade preenchido
    - `mobilidade_ok`: JSON de mobilidade preenchido
  - **Resumo:**
    - `pode_fechar_processo`: true se inspetor+aprovador definidos E completos >= 1
    - `equipamentos_prontos_para_emitir`: IDs dos equipamentos com is_completo=true
  - Permissão: `certificacao:processos:visualizar`
  - Autenticação: Requerida
  - **Service:** `ProcessoAuditoriaCertificadoService.build(db, processo_id)`

- **GET** `/processos/{processo_id}/validacao-final` - Validar completude do processo (legado, mantido para compatibilidade)
  - Response: validação básica sem datas calculadas nem nomes de responsáveis
  - Permissão: `certificacao:processos:visualizar`
  - Autenticação: Requerida

- **POST** `/processos/{processo_id}/finalizar` - Finalizar processo (regra atualizada em 2026-02-01)
  - **Nova regra:** Permite finalizar quando **pelo menos 1 equipamento completo** (antes exigia todos)
  - **Bloqueios:**
    - ❌ Inspetor não definido
    - ❌ Aprovador não definido
    - ❌ 0 equipamentos completos
  - **Etapa final definida:**
    - `concluido_total`: se completos == total_equipamentos
    - `concluido_parcial`: se completos >= 1 e completos < total_equipamentos
  - **Campos atualizados:**
    - `etapa_atual`: 'concluido_total' ou 'concluido_parcial'
    - `resultado_final`: 'aprovado'
    - `data_conclusao`: datetime.now() (se ainda não preenchida)
  - Response: `ProcessoFinalizadoResponse`
    ```json
    {
      "id": int,
      "numero_processo": string,
      "etapa_atual": string,
      "resultado_final": string,
      "data_conclusao": string (ISO),
      "mensagem": string,
      "equipamentos_completos": int,
      "total_equipamentos": int,
      "equipamentos_prontos_para_emitir": [int]
    }
    ```
  - **Erro 400** (bloqueio): retorna `detail` com estrutura:
    ```json
    {
      "message": "Processo não pode ser finalizado",
      "erros": ["Inspetor não definido", "..."],
      "resumo": {...},
      "equipamentos": [...]
    }
    ```
  - Permissão: `certificacao:processos:gerenciar`
  - Autenticação: Requerida
  - **Service:** `ProcessoAuditoriaCertificadoService.validate_or_raise(db, processo_id)`

- **PATCH** `/processos/{processo_id}/finalizar` - (rota legada, usar POST)
  - Body: `FinalizarProcessoUpdate`
    ```json
    {
      "resultado_final": "aprovado",
      "data_conclusao": "2025-01-15T16:00:00",
      "certificado_id": 123
    }
    ```
  - Response: `ProcessoResponse`
  - Permissão: `processos:editar`
  - Autenticação: Requerida
  - **Ações automáticas:**
    - Atualiza `status_global` para 'concluido'
    - Vincula certificado se fornecido
    - Registra data de conclusão

### Endpoints de Processo por Equipamento

- **PATCH** `/processos/{processo_id}/equipamentos/{equipamento_id}/pre-checagem` - Pré-checagem de equipamento específico
  - Body: `PreChecagemEquipamentoUpdate`
  - Response: `ProcessoEquipamentoResponse`
  - Permissão: `processos:editar`
  - Autenticação: Requerida

- **PATCH** `/processos/{processo_id}/equipamentos/{equipamento_id}/ensaio` - Ensaio de equipamento específico
  - Body: `EnsaioEquipamentoUpdate`
  - Response: `ProcessoEquipamentoResponse`
  - Permissão: `processos:editar`
  - Autenticação: Requerida

- **PATCH** `/processos/{processo_id}/equipamentos/{equipamento_id}/ajuste` - Ajuste de equipamento específico
  - Body: `AjusteEquipamentoUpdate`
  - Response: `ProcessoEquipamentoResponse`
  - Permissão: `processos:editar`
  - Autenticação: Requerida

### Endpoints de Materiais

- **GET** `/material-venda` - Listar materiais (estoque ou por processo)
  - Query params: `tipo_material`, `categoria`, `processo_id`, `ativo`
  - Response: `List[MaterialVendaResponse]`
  - Permissão: `processos:visualizar`
  - Autenticação: Requerida

- **POST** `/material-venda` - Adicionar material ao processo
  - Body: `MaterialVendaCreate`
    ```json
    {
      "tipo_material": "lacre",
      "processo_id": 1,
      "equipamento_id": 1,
      "lacre_anterior": "LAC-001",
      "lacre_anterior_status": "intacto",
      "lacre_novo": "LAC-002",
      "foto_lacre_anterior": "/uploads/lacre_ant.jpg",
      "foto_lacre_novo": "/uploads/lacre_novo.jpg"
    }
    ```
  - Response: `MaterialVendaResponse`
  - Permissão: `processos:editar`
  - Autenticação: Requerida

- **GET** `/material-venda/processo/{processo_id}` - Listar materiais de um processo
  - Response: `List[MaterialVendaResponse]`
  - Permissão: `processos:visualizar`
  - Autenticação: Requerida

#### 9.1. Processos – Balanças e vínculos (módulo de calibração)

O fluxo de calibração (`/procedimentos/calibracao`, `/procedimentos/novo-processo`) usa **balanças** por processo e vínculos em `processo_balanca_aux_cadastros` (pesos, equip. aux., inspetor, aprovador).

- **GET** `/processos/{processo_id}/balancas/{balanca_id}` - Obter balança com dados de calibração e medições salvas
  - Response: dados da balança (`processo_balanca_calibracao`), condições ambientais, **medicoes_inicial**, **medicoes_final** (de `processo_equipamentos.medicoes_json` / `ensaio_final_medicoes_json`; **quando tipo_ensaio é mobilidade**, `medicoes_final` é exposto a partir de `processo_balanca_calibracao.ensaios_mobilidade_json` para restauração da tabela Mobilidade), **composicao_pesos_atual** (de `processo_balanca_calibracao.composicao_pesos_json`: carga, certificado_numero, pesos_ids, pesos_resumo para restaurar etapa 2 ao editar), **tipo_ensaio** (inferido: excentricidade > mobilidade > indicacao a partir de `ensaios_excentricidade_json` / `ensaios_mobilidade_json`). Usado pelo frontend para restaurar conjunto, carga e medições ao editar.
  - Permissão: `processos:visualizar`
  - Autenticação: Requerida

- **PUT** `/processos/{processo_id}/balancas/{balanca_id}/composicao-pesos` - Salvar composição atual (Etapa 2: carga + peças)
  - Body: `{ carga: number, certificado_numero?: string, pesos_ids: number[], pesos_resumo?: object[] }`
  - Response: `{ message, composicao_pesos_atual }`. Grava em `processo_balanca_calibracao.composicao_pesos_json`.
  - Permissão: `processos:editar`
  - Autenticação: Requerida

- **PATCH** `/processos/{processo_id}/balancas/{balanca_id}` - Atualizar dados da balança (local, lacre, condições ambientais)
  - Body: campos parciais da balança
  - Response: balança atualizada
  - Permissão: `processos:editar`
  - Autenticação: Requerida

- **POST** `/processos/{processo_id}/balancas/{balanca_id}/ensaios/medicoes-final` - Salvar medições do ensaio final
  - Body: `{ medicoes: [ ... ], tipo_ensaio?: "excentricidade"|"indicacao"|"mobilidade" }`. **Excentricidade/Indicação:** cada item com `ponto`, `carga`, `pesos_ids`, `pesos_resumo`, `certificado_numero`, `validade_min`, `leitura_1`, `leitura_2`, `leitura_3`, `leitura_4`. **Mobilidade:** uma medição com `ponto: 1`, `carga`, `sobrecarga`, `leitura_antes`, `leitura_depois`, `padrao_utilizado`, `padrao_utilizado_id` (sem pesos_ids/pesos_resumo; validação de pesos vencidos não se aplica).
  - Response: confirmação e dados salvos em `processo_equipamentos.ensaio_final_medicoes_json` (e duplicado em `medicoes_json` para ensaio inicial). Para **mobilidade**, também gravado em `processo_balanca_calibracao.ensaios_mobilidade_json` para restauração no GET balança.
  - **422 Unprocessable Entity:** quando pesos estão vencidos (`data_validade < data_ensaio`) — aplica-se a excentricidade/indicação; mensagem detalhada (ex.: "Peças vencidas: P10-1 (vencido há X dia(s)..."). O frontend exibe modal inline "Pesos padrão vencidos" por 2 segundos e mantém o bloqueio.

**Endpoints Unificados (Recomendados):**
- `GET/POST/DELETE /processos/{id}/balancas/{bid}/aux-cadastros` - API unificada para todos os vínculos
- Query param `papel` para filtrar: `equipamento_auxiliar`, `peso_padrao`, `inspetor`, `aprovador`

**Endpoints de Conveniência (Compatibilidade):**
- `GET/POST/DELETE /processos/{id}/balancas/{bid}/certificados-peso` → Filtra `papel='peso_padrao'`
- `GET/POST/DELETE /processos/{id}/balancas/{bid}/equipamentos-auxiliares` → Filtra `papel='equipamento_auxiliar'`
- `GET/POST/DELETE /processos/{id}/balancas/{bid}/inspetores` → Filtra `papel='inspetor'`
- `GET/POST/DELETE /processos/{id}/balancas/{bid}/aprovadores` → Filtra `papel='aprovador'`

**Lista completa:** Ver MAPA_FLUXO/FLUXO_CERTIFICACAO_CALIBRACAO.md e Seção 6.0.2 acima.

**Referência:** Ver `Scripts_auxiliares/IMPLEMENTACAO_MULTIPLOS_EQUIPAMENTOS.md` e `Scripts_auxiliares/Calibracao.md` para documentação completa; MAPA_FLUXO/FLUXO_CERTIFICACAO_CALIBRACAO.md para estado atual do módulo de calibração.

---

## 10. AGENDAMENTOS (`/api/v1/agendamentos`)

Sistema completo de agendamento de serviços (calibração, aferição, manutenção, inspeção) integrado ao PDV Ibix, com vinculação opcional com contratos de aferição.

### Endpoints Principais

- **POST** `/agendamentos` - Criar novo agendamento
  - Body: `AgendamentoCreate`
    ```json
    {
      "cliente_id": 1,
      "equipamento_id": 1,
      "contrato_afericao_id": null,
      "data_agendamento": "2025-01-15",
      "hora_agendamento": "14:00:00",
      "duracao_estimada": 120,
      "tipo_servico": "calibracao",
      "status": "pendente",
      "responsavel": "João Silva",
      "observacoes": "Observações adicionais",
      "tipo_agendamento": "contrato",
      "equipamentos_ids": [1, 2, 3]
    }
    ```
  - Response: `AgendamentoResponse` (201 Created)
  - Permissão: `agendamentos:criar`
  - Autenticação: Requerida
  - **Validações:**
    - Cliente deve existir
    - Equipamento deve existir (se fornecido)
    - Contrato deve existir (se fornecido)
    - Data/hora válidas

- **GET** `/agendamentos` - Listar agendamentos com filtros
  - Query params:
    - `cliente_id` - Filtrar por cliente
    - `equipamento_id` - Filtrar por equipamento
    - `contrato_afericao_id` - Filtrar por contrato
    - `tipo_servico` - Filtrar por tipo (calibracao, afericao, manutencao, inspecao, outro)
    - `status` - Filtrar por status (pendente, confirmado, em_andamento, concluido, cancelado)
    - `data_inicio` - Data inicial (formato: YYYY-MM-DD)
    - `data_fim` - Data final (formato: YYYY-MM-DD)
    - `responsavel` - Filtrar por responsável
    - `skip` - Paginação (padrão: 0)
    - `limit` - Limite por página (padrão: 50)
  - Response: `AgendamentoListResponse`
    ```json
    {
      "items": [...],
      "total": 150,
      "pagina": 1,
      "por_pagina": 10,
      "total_paginas": 15
    }
    ```
  - Permissão: `agendamentos:visualizar`
  - Autenticação: Requerida
  - **Filtros por Role:**
    - Admin Cliente: Apenas agendamentos do seu cliente
    - Técnico: Apenas seus agendamentos
    - Cliente: Apenas seus agendamentos

- **GET** `/agendamentos/estatisticas` - Estatísticas de agendamentos
  - Response: `AgendamentoEstatisticas`
    ```json
    {
      "total": 150,
      "pendentes": 20,
      "confirmados": 50,
      "em_andamento": 10,
      "concluidos": 60,
      "cancelados": 10,
      "hoje": 5,
      "proximos_7_dias": 15,
      "proximos_30_dias": 45
    }
    ```
  - Permissão: `agendamentos:visualizar`
  - Autenticação: Requerida

- **GET** `/agendamentos/{agendamento_id}` - Obter agendamento específico com dados relacionados
  - Response: `AgendamentoResponse`
    ```json
    {
      "id": 1,
      "cliente_id": 1,
      "cliente_nome": "Empresa ABC",
      "cliente_cnpj": "12345678000190",
      "equipamento_id": 1,
      "equipamento_fabricante": "Toledo",
      "equipamento_modelo": "2098",
      "equipamento_numero_serie": "12345678",
      "equipamento_info": "Toledo 2098 - 12345678",
      "contrato_numero": "CONT-2025-001",
      "certificado_numero": "CERT-2025-001",
      "data_agendamento": "2025-01-15",
      "hora_agendamento": "14:00:00",
      "tipo_servico": "calibracao",
      "status": "confirmado",
      "responsavel": "João Silva",
      "observacoes": "...",
      "created_at": "2025-01-10T10:00:00",
      "updated_at": "2025-01-10T10:00:00"
    }
    ```
  - Permissão: `agendamentos:visualizar`
  - Autenticação: Requerida

- **PUT** `/agendamentos/{agendamento_id}` - Atualizar agendamento
  - Body: `AgendamentoUpdate` (campos parciais)
  - Response: `AgendamentoResponse`
  - Permissão: `agendamentos:editar`
  - Autenticação: Requerida
  - **Validações automáticas:**
    - Cliente, equipamento e contrato devem existir
    - Status válido
    - Data/hora válidas

- **DELETE** `/agendamentos/{agendamento_id}` - Deletar agendamento
  - Response: `204 No Content`
  - Permissão: `agendamentos:gerenciar`
  - Autenticação: Requerida

### Endpoints Mobile

- **GET** `/mobile/agendamentos/tecnicos` - Lista agendamentos do técnico logado
  - Query params: `data`, `status`
  - Response: `List[AgendamentoMobileResponse]` (otimizado para mobile)
  - Ordenação: Próximos primeiro
  - Permissão: `agendamentos:visualizar`
  - Autenticação: Requerida

- **POST** `/mobile/agendamentos/{id}/iniciar` - Marca agendamento como "em_andamento"
  - Body: Vazio
  - Response: `AgendamentoResponse`
  - Registra hora de início automaticamente
  - Valida se técnico pode iniciar
  - Permissão: `agendamentos:editar`
  - Autenticação: Requerida

- **POST** `/mobile/agendamentos/{id}/concluir` - Marca como "concluído"
  - Body: `{"certificado_id": 123}` (opcional)
  - Response: `AgendamentoResponse`
  - Cria certificado automaticamente se fornecido
  - Registra data/hora de conclusão
  - Permissão: `agendamentos:editar`
  - Autenticação: Requerida

- **GET** `/mobile/agendamentos/hoje` - Retorna agendamentos do dia do técnico
  - Response: `List[AgendamentoMobileResponse]`
  - Permissão: `agendamentos:visualizar`
  - Autenticação: Requerida

### Schema Mobile Otimizado

**AgendamentoMobileResponse:**
```json
{
  "id": 1,
  "data_agendamento": "2025-01-15",
  "hora_agendamento": "14:00:00",
  "cliente_nome": "Empresa ABC",
  "cliente_endereco": "Rua Exemplo, 123",
  "cliente_telefone": "(11) 99999-9999",
  "equipamento_info": "Toledo 2098 - 12345678",
  "tipo_servico": "calibracao",
  "status": "confirmado",
  "observacoes": "...",
  "pode_iniciar": true,
  "pode_concluir": false
}
```

### Permissões por Role

| Role | Criar | Visualizar | Editar | Excluir | Atribuir Técnico |
|------|:-----:|:----------:|:------:|:-------:|:----------------:|
| **Administrador Master** | ✅ | ✅ Todos | ✅ Todos | ✅ Todos | ✅ |
| **Administrador Cliente** | ✅ | ✅ Seu cliente | ✅ Seu cliente | ✅ Seu cliente | ✅ Seu cliente |
| **Técnico Master** | ✅ | ✅ Todos | ✅ Todos | ❌ | ✅ |
| **Técnico** | ✅ | ✅ Seus agendamentos | ✅ Seus agendamentos | ❌ | ❌ |
| **Técnico Cliente** | ✅ | ✅ Seu cliente | ✅ Seu cliente | ❌ | ❌ |
| **Operador Agendamento** | ✅ | ✅ Todos | ✅ Todos | ✅ | ✅ |
| **Cliente** | ✅ Solicitar | ✅ Seus agendamentos | ❌ | ❌ | ❌ |
| **Visualizador** | ❌ | ✅ Todos | ❌ | ❌ | ❌ |
| **Auditor** | ❌ | ✅ Todos | ❌ | ❌ | ❌ |

**Referência:** Ver `Scripts_auxiliares/AGENDAMENTO_SISTEMA.md` para documentação completa do sistema de agendamento

---

## 11. USUÁRIOS (`/api/v1/usuarios`)

**Acesso:** Apenas **Superadministrador** e **Administrador** (permissão `usuarios:visualizar` e demais). **Cliente Administrador não acessa** esta API (migração y34zz236m1v8 removeu permissões usuarios da role Cliente Administrador); gestão de sub-clientes e técnicos em **Minha equipe** (`/api/v1/minha-equipe`). Ver [MAPA_RBAC.md](MAPA_RBAC.md) (Apêndice B — Acesso por Role).

**Escopo:** **Superadministrador:** todos. **Administrador:** ele mesmo + Cliente Administradores em `administrador_cliente_administradores`.

- **GET** `/usuarios/` - Listar usuários
  - Query params: `skip`, `limit`, `ativo`, `nome`, `role_id`
  - Response: `UsuarioListResponse` (usuarios, total, skip, limit)
  - Permissão: `usuarios:visualizar`
  - **Cliente Administrador:** 403 (sem acesso).

- **POST** `/usuarios/` - Criar usuário
  - Body: `UsuarioCreate` (nome, email, senha, cargo, ativo, role_id)
  - Response: `UsuarioResponse`
  - Permissão: `usuarios:criar`
  - **Cliente Administrador:** 403 (sem acesso).

- **GET** `/usuarios/{id}` - Obter usuário específico
  - Response: `UsuarioResponse`
  - Permissão: `usuarios:visualizar`
  - **Cliente Administrador:** 403 (sem acesso).

- **PUT** `/usuarios/{id}` - Atualizar usuário
  - Body: `UsuarioUpdate`
  - Response: `UsuarioResponse`
  - Permissão: `usuarios:editar`
  - **Cliente Administrador:** 403 (sem acesso).

- **DELETE** `/usuarios/{id}` - Remover usuário
  - Response: `204 No Content`
  - Permissão: `usuarios:excluir`
  - Autenticação: Requerida

- **GET** `/usuarios/{usuario_id}/clientes-vinculados` - Listar clientes que o Administrador pode acessar
  - Response: `{"cliente_ids": [int]}`
  - **Apenas Superadministrador** (`require_superadmin()`)
  - Autenticação: Requerida

- **PUT** `/usuarios/{usuario_id}/clientes-vinculados` - Definir clientes que o Administrador pode acessar
  - Body: `{"cliente_ids": [int]}`
  - **Apenas Superadministrador**; usuário alvo deve ser role Administrador. Persiste em `administrador_clientes`.
  - Autenticação: Requerida

---

## 11b. MINHA EQUIPE (`/api/v1/minha-equipe`) — Cliente Administrador

**Acesso:** Apenas role **Cliente Administrador** (`require_cliente_administrador()`). Escopo: clientes em `cliente_administrador_clientes`; técnicos em `cliente_administrador_tecnicos`. **Isolamento:** Cliente Administrador não vê técnicos de outras organizações; um técnico pertence a **um único** Cliente Administrador. **Distinção:** Aqui criamos/vinculamos **Técnico** (e, em outra rota, Subcliente por cliente); na tela **Clientes**, o modal "Criar usuário" usa `POST /api/v1/clientes/{id}/usuarios` e cria **Subcliente** — lugares distintos, funções distintas (MAPA_RBAC.md § 0.11, 0.12).

- **POST** `/minha-equipe/clientes` - Criar Subcliente e vincular ao Cliente Administrador
  - Body: `ClienteCreate`
  - Response: `ClienteResponse`
  - Autenticação: Requerida

- **GET** `/minha-equipe/clientes/{cliente_id}/usuarios` - Listar usuários (role Subcliente) do Subcliente
  - Só se `cliente_id` estiver no escopo do Cliente Administrador
  - Autenticação: Requerida

- **POST** `/minha-equipe/clientes/{cliente_id}/usuarios` - Adicionar usuário ao Subcliente (role Subcliente, AreaCliente)
  - Body: `SubClienteUsuarioCreate` (nome, email, senha)
  - Autenticação: Requerida

- **GET** `/minha-equipe/tecnicos` - Listar técnicos vinculados **apenas** a este Cliente Administrador
  - Autenticação: Requerida

- **GET** `/minha-equipe/tecnicos/disponiveis` - Retorna lista **vazia** (Cliente Administrador não vê técnicos de outras organizações; vínculo apenas por email).

- **POST** `/minha-equipe/tecnicos` - Vincular técnico à equipe (por **email**; `usuario_id` opcional). Cria sempre usuário com role **Técnico** e vínculo em `ClienteAdministradorTecnico`; se usuário não existir, exige nome e senha.
  - Body: `VincularTecnicoRequest` (email obrigatório para novo; `usuario_id`, `nome`, `senha` opcionais). **Se o usuário não existir:** cria automaticamente usuário com role Técnico (exige `nome` e `senha`). Se existir, vincula por email.
  - Um técnico só pode pertencer a **um** Cliente Administrador: 400 se já vinculado a outro CA.
  - Autenticação: Requerida

- **DELETE** `/minha-equipe/tecnicos/{usuario_id_tecnico}` - Desvincular técnico (apenas da própria equipe)
  - Autenticação: Requerida

---

## 12. ROLES E PERMISSÕES (`/api/v1/roles` e `/api/v1/permissoes`)

**Acesso:** Superadministrador ou Administrador. **Administrador** não vê a role Superadministrador na listagem; não pode GET/PUT/DELETE essa role nem ver/editar suas permissões (403).

### Roles
- **GET** `/roles/` - Listar roles
  - Response: `{roles: List[RoleResponse], total: int}`. Administrador: lista sem a role Superadministrador.
  - Autenticação: Requerida (Bearer)

- **POST** `/roles/` - Criar role
  - Body: `RoleCreate` (nome, descricao)
  - Response: `RoleResponse`
  - Permissão: `configuracoes:roles:gerenciar`
  - Autenticação: Requerida

### Permissões
- **GET** `/permissoes/` - Listar permissões
  - Response: `List[PermissaoResponse]`
  - Permissão: `configuracoes:permissoes:visualizar`
  - Autenticação: Requerida

- **POST** `/permissoes/` - Criar permissão
  - Body: `PermissaoCreate` (recurso, acao, descricao)
  - Response: `PermissaoResponse`
  - Permissão: `configuracoes:permissoes:gerenciar`
  - Autenticação: Requerida

---

## 13. INSPETORES E APROVADORES (`/api/v1/inspetores-aprovadores`)

- **GET** `/inspetores-aprovadores/` - Listar inspetores e aprovadores
  - Query params: `skip`, `limit`, `tipo`, `ativo`
  - Response: `List[InspetorAprovadorResponse]`
  - Permissão: `configuracoes:inspetores_aprovadores:visualizar`
  - Autenticação: Requerida

- **POST** `/inspetores-aprovadores/` - Criar inspetor/aprovador
  - Body: `InspetorAprovadorCreate` (nome, crea, tipo)
  - Response: `InspetorAprovadorResponse`
  - Permissão: `configuracoes:inspetores_aprovadores:gerenciar`
  - Autenticação: Requerida

- **GET** `/inspetores-aprovadores/{id}` - Obter inspetor/aprovador específico
  - Response: `InspetorAprovadorResponse`
  - Permissão: `configuracoes:inspetores_aprovadores:visualizar`
  - Autenticação: Requerida

- **PUT** `/inspetores-aprovadores/{id}` - Atualizar inspetor/aprovador
  - Body: `InspetorAprovadorUpdate`
  - Response: `InspetorAprovadorResponse`
  - Permissão: `configuracoes:inspetores_aprovadores:gerenciar`
  - Autenticação: Requerida

- **DELETE** `/inspetores-aprovadores/{id}` - Remover inspetor/aprovador
  - Response: `204 No Content`
  - Permissão: `configuracoes:inspetores_aprovadores:gerenciar`
  - Autenticação: Requerida

---

## 13b. RELATÓRIOS (`/api/v1/relatorios`)

**Acesso:** Permissão `negocios.relatorios:visualizar` (router com `require_permission`). Atribuída a **Superadministrador**, **Administrador** e **Cliente Administrador** (migração `rb01_cleanup_permissoes_certipeso`; substitui legado `certificacao:relatorios:visualizar`). Página HTML `/negocio/relatorios` usa módulo `negocios` (não esta permissão). Autenticação obrigatória.

**Endpoints implementados:** GET catálogo, POST jobs (gerar relatório), GET jobs/{id}, GET jobs/{id}/download. Worker Celery processa a tarefa `generate_report` (Redis como broker).

- **GET** `/relatorios/tendencias-ensaios` - Tendências de ensaios (ISO 17025 7.7)
  - Query params: `periodo_inicio` (date), `periodo_fim` (date), `equipamento_id`, `cliente_id`
  - Response: `TendenciasEnsaiosResponse` (`serie: List[SerieTendenciaItem]`, `periodo_inicio`, `periodo_fim`)
  - Autenticação: Requerida
  - **Comportamento:** Endpoint preparado para agregação sobre `processo_equipamento.medicoes_json` e `ensaio_final_medicoes_json`; atualmente retorna série vazia. Frontend pode consumir para gráficos de tendências.

---

## 14. CONFIGURAÇÕES (`/api/v1/configuracoes`)

**Acesso:** Apenas **Administrador** e **Superadministrador** (`require_superadmin_or_admin()` no router). Cliente Administrador e demais roles recebem 403. Exceção: endpoints de WhatsApp (GET/POST `/configuracoes/whatsapp/`) exigem apenas **Superadministrador** (`require_superadmin()`). Implementação: `app/api/v1/configuracoes.py` (dependencies do router).

- **GET** `/configuracoes/` - Listar configurações
  - Query params: `chave`
  - Response: `List[ConfiguracaoResponse]`
  - Permissão: `configuracoes:sistema:visualizar`
  - Autenticação: Requerida

- **GET** `/configuracoes/{chave}` - Obter configuração específica
  - Response: `ConfiguracaoResponse`
  - Permissão: `configuracoes:sistema:visualizar`
  - Autenticação: Requerida

- **PUT** `/configuracoes/{chave}` - Atualizar configuração
  - Body: `ConfiguracaoUpdate` (valor, descricao)
  - Response: `ConfiguracaoResponse`
  - Permissão: `configuracoes:sistema:configurar`
  - Autenticação: Requerida

**Configurações Importantes:**
- `certificados.proximo_numero` - Próximo número sequencial de certificado
- `iso_17025_certificados_apenas_processo` - (default true) Quando ativo, bloqueia POST `/certificados` e exige emissão via `POST /processos/{id}/certificados`. Rotas `/certificados/novo` e `/certificados/editar` redirecionam para Procedimentos > Calibração.
- `sistema.nome` - Nome do sistema
- `sistema.logo` - Caminho do logo

**Políticas de Qualidade (ISO 17025 Fase 3.1):**
- **GET** `/configuracoes/politicas-qualidade/` - Obter políticas de imparcialidade e confidencialidade
  - Response: `PoliticasQualidadeResponse` (chaves `politica.imparcialidade`, `politica.confidencialidade`)
  - Autenticação: Requerida
- **PUT** `/configuracoes/politicas-qualidade/` - Atualizar políticas de qualidade
  - Body: `PoliticasQualidadeUpdate` (valores opcionais)
  - Autenticação: Requerida

**Configurações WhatsApp (apenas Superadministrador):**
- **GET** `/configuracoes/whatsapp/` - Obter configurações da integração WhatsApp
  - Response: `ConfiguracaoWhatsAppResponse` (ativo, phone_number_id, verify_token mascarado, business_account_id, token_preenchido)
  - Acesso: **Apenas Superadministrador** (`require_superadmin()`)
  - Autenticação: Requerida
- **POST** `/configuracoes/whatsapp/` - Salvar configurações da integração WhatsApp
  - Body: `ConfiguracaoWhatsAppRequest` (ativo, phone_number_id, token, verify_token, business_account_id)
  - Acesso: **Apenas Superadministrador**
  - Autenticação: Requerida
- A permissão **`configuracoes:whatsapp`** (módulo `configuracoes`, ação `whatsapp`) está atribuída somente à role Superadministrador (migração `a78dd581k6l3`); visível na gestão de Funções e Permissões (`/roles`).
  - Chaves gravadas em `configuracoes`: whatsapp.ativo, whatsapp.phone_number_id, whatsapp.token, whatsapp.verify_token, whatsapp.business_account_id

**Integração Multipropósito (Fase 5) — Webhook `venda.fechada` por tenant:**
- **GET** `/configuracoes/integracoes/webhook-venda-fechada/?tenant_id={id}` - Obter configuração do webhook por tenant
  - Query params: `tenant_id` (obrigatório, inteiro > 0)
  - Response: `IntegracaoWebhookVendaFechadaResponse` (`tenant_id`, `enabled`, `webhook_url`, `timeout_seconds`, `has_token`)
  - Acesso: **Apenas Superadministrador**
  - Autenticação: Requerida
- **PUT** `/configuracoes/integracoes/webhook-venda-fechada/?tenant_id={id}` - Salvar configuração do webhook por tenant
  - Query params: `tenant_id` (obrigatório)
  - Body: `IntegracaoWebhookVendaFechadaUpdate` (`enabled?`, `webhook_url?`, `token?`, `timeout_seconds?`)
  - Regras: se `enabled=true` sem `webhook_url`, retorna `400` (sem fallback)
  - Acesso: **Apenas Superadministrador**
  - Autenticação: Requerida
- Evento emitido no backend: `venda.fechada` após venda finalizada; envio assíncrono via Celery (`dispatch_venda_fechada_webhook`) com retry.

**E-mail separado por cliente (flag global; apenas Superadministrador altera):**
- **GET** `/configuracoes/email/separado-por-cliente/` - Obter se a funcionalidade está ativa
  - Response: `EmailSeparadoPorClienteResponse` (ativo: bool)
  - Acesso: quem acessa config e-mail (Superadministrador/Administrador)
  - Autenticação: Requerida
- **PUT** `/configuracoes/email/separado-por-cliente/` - Ativar/desativar e-mail separado por cliente
  - Body: `EmailSeparadoPorClienteUpdate` (ativo: bool)
  - Acesso: **Apenas Superadministrador** (`require_superadmin()`)
  - Chave gravada: `email_separado_por_cliente_ativo` ("true"/"false")

**E-mail por função:** GET/POST `/configuracoes/email/funcoes/` - listar/salvar remetente (from_email, from_name) por função (certificados, nota_fiscal, etc.). Chaves `email_funcao_{codigo}_from`, `email_funcao_{codigo}_from_name`.

---

## 14.1 E-MAIL POR CLIENTE (`/api/v1/email-cliente`)

Configuração de remetente de e-mail (from_email, from_name) por cliente, para uso por **Cliente Administrador** (e Admin/Superadmin). Só tem efeito quando a flag `email_separado_por_cliente_ativo` está ativa (alterada apenas por Superadministrador em `/configuracoes/email/separado-por-cliente/`).

**Acesso:** **Superadministrador, Administrador ou Cliente Administrador** (`require_superadmin_or_admin_or_cliente_admin()` em `app/api/v1/email_cliente.py`). Para Cliente Administrador, apenas clientes no escopo (`cliente_administrador_clientes`) são acessíveis.

**Contrato operacional CA x CF/Subcliente (obrigatório):**
- Para role **Cliente Administrador (CA)**, este módulo deve priorizar o contexto da **empresa cliente do SaaS** (empresa fiscal / emissor), e não tratar **CF/Subcliente** como cadastro principal do CA.
- `GET /email-cliente/`, `GET /email-cliente/{cliente_id}` e `PUT /email-cliente/{cliente_id}` devem respeitar esse recorte fiscal do CA.

- **GET** `/email-cliente/` - Listar clientes do escopo com from_email/from_name e flag ativo
  - Response: `EmailClienteListResponse` (clientes: lista de { cliente_id, nome, from_email, from_name }, ativo: bool)
  - Autenticação: Requerida
- **GET** `/email-cliente/{cliente_id}` - Obter from_email/from_name do cliente
  - Response: `EmailClienteGetResponse` (cliente_id, from_email, from_name)
  - Cliente_id deve estar no escopo do usuário
  - Autenticação: Requerida
- **PUT** `/email-cliente/{cliente_id}` - Salvar from_email/from_name do cliente
  - Body: `EmailClienteUpdate` (from_email?, from_name?)
  - Chaves gravadas: `email_cliente.{cliente_id}.from`, `email_cliente.{cliente_id}.from_name`
  - Cliente_id deve estar no escopo do usuário
  - Autenticação: Requerida

Rota HTML `/email-cliente` renderiza `configuracoes/email_cliente.html`; acessível por Superadministrador, Administrador e Cliente Administrador (`main.py`).

---

## 14.2 WHATSAPP (`/api/v1/whatsapp`)

Integração com WhatsApp Business Cloud API (Meta). Webhook para validação e recebimento de eventos; envio de mensagens com identificação do usuário e da empresa (cliente) em cada texto.

**Webhook (sem autenticação; chamado pelo Meta):**
- **GET** `/whatsapp/webhook` - Validação do webhook
  - Query params: `hub.mode`, `hub.verify_token`, `hub.challenge`
  - Se `hub.mode=subscribe` e `hub.verify_token` igual ao configurado em `configuracoes` (whatsapp.verify_token), responde com `hub.challenge` (PlainText)
  - Autenticação: Não requerida
- **POST** `/whatsapp/webhook` - Receber eventos (mensagens, status)
  - Body: JSON do Meta (raw body usado para validação de assinatura)
  - Header: `X-Hub-Signature-256` (HMAC-SHA256 do body com App Secret; se `whatsapp.app_secret` configurado, obrigatório)
  - Persiste em `whatsapp_webhook_events` (payload, tipo_evento, from_phone)
  - Responde 200 para o Meta; 401 se assinatura inválida
  - Autenticação: Não requerida

**Envio (autenticado):**
- **POST** `/whatsapp/enviar` - Enviar mensagem por WhatsApp com identificação usuário/empresa
  - Body: `EnviarWhatsAppRequest` (numero_destino, texto, incluir_prefixo=true)
  - O sistema adiciona prefixo ao texto com nome do usuário e nome do cliente (empresa) via `app/core/chat_context.get_chat_context`; se usuário sem cliente, exibe "Sistema".
  - Response: `{ success, message_id }` ou erro 400 com detail
  - Autenticação: Requerida (Bearer ou cookie)
  - Serviço: `app/services/whatsapp_service.enviar_mensagem_whatsapp` (lê config em `configuracoes`, chama Meta Graph API v18.0)

---

## 15. FORM BUILDER (`/api/v1/form-builder`)

Sistema centralizado de criação e renderização de formulários dinâmicos baseados em templates JSON. Permite criar formulários customizados para processos, aferições, certificados e outros módulos do sistema.

**Nota (schemas Pydantic):** Os modelos de template (`TemplateSchema`, `TemplateCreate`, `TemplateUpdate`, `TemplateResponse`) usam o campo interno `form_schema` com `Field(alias="schema_json")` para evitar shadowing do `BaseModel`. A API continua a aceitar e retornar `schema_json` em JSON; o contrato HTTP permanece inalterado. Ver [CORRECOES_STARTUP_E_PYDANTIC_2026-01.md](CORRECOES_STARTUP_E_PYDANTIC_2026-01.md).

### 15.1. Renderização de Formulários

- **POST** `/form-builder/render` - Renderizar formulário a partir de template
  - Body: `RenderRequest`
    ```json
    {
      "template_id": 1,  // Opcional se template_schema fornecido
      "template_schema": {  // Opcional se template_id fornecido
        "layout": "column",
        "secoes": [...],
        "campos": [...]
      },
      "dados": {
        "campo_id": "valor"
      },
      "contexto": {
        "processo": {...},
        "afericao": {...}
      },
      "modo": "edicao"  // criacao, edicao, visualizacao
    }
    ```
  - Response: `RenderResponse`
    ```json
    {
      "html": "<div>...</div>",
      "campos": [
        {
          "id": "campo_id",
          "tipo": "text",
          "label": "Campo",
          "valor": "valor",
          "obrigatorio": true,
          "modo": "edicao"
        }
      ],
      "validacoes": {
        "campo_id": {
          "obrigatorio": true,
          "regras": []
        }
      }
    }
    ```
  - Permissão: `form_builder:render`
  - Autenticação: Requerida

### 15.2. Gerenciamento de Templates

- **GET** `/form-builder/templates` - Listar templates disponíveis
  - Query params: `tipo` (processo, afericao, certificado), `ativo` (bool), `skip`, `limit`
  - Response: `List[TemplateResponse]`
  - Permissão: `form_builder:templates:visualizar`
  - Autenticação: Requerida

- **GET** `/form-builder/templates/{template_id}` - Obter template específico
  - Response: `TemplateResponse`
  - Permissão: `form_builder:templates:visualizar`
  - Autenticação: Requerida

- **POST** `/form-builder/templates` - Criar novo template
  - Body: `TemplateCreate`
    ```json
    {
      "nome": "Template de Processo",
      "descricao": "Template para processos de calibração",
      "tipo": "processo",
      "schema_json": {
        "layout": "column",
        "secoes": [...],
        "campos": [...]
      }
    }
    ```
  - Response: `TemplateResponse`
  - Permissão: `form_builder:templates:gerenciar`
  - Autenticação: Requerida

- **PUT** `/form-builder/templates/{template_id}` - Atualizar template
  - Body: `TemplateUpdate`
  - Response: `TemplateResponse`
  - Permissão: `form_builder:templates:gerenciar`
  - Autenticação: Requerida

- **DELETE** `/form-builder/templates/{template_id}` - Deletar template
  - Response: `204 No Content`
  - Permissão: `form_builder:templates:gerenciar`
  - Autenticação: Requerida

### 15.3. Validação de Formulários

- **POST** `/form-builder/validate` - Validar dados de formulário
  - Body: `ValidateRequest`
    ```json
    {
      "template_schema": {
        "layout": "column",
        "secoes": [...],
        "campos": [...]
      },
      "dados": {
        "campo_id": "valor"
      },
      "contexto": {
        "processo": {...}
      }
    }
    ```
  - Response: `ValidateResponse`
    ```json
    {
      "valido": true,
      "erros": [
        {
          "campo": "campo_id",
          "mensagem": "Campo é obrigatório"
        }
      ]
    }
    ```
  - Permissão: `form_builder:validate`
  - Autenticação: Requerida

### Estrutura de Template Schema

```json
{
  "layout": "column",
  "secoes": [
    {
      "id": "secao_1",
      "titulo": "Dados Iniciais",
      "ordem": 1,
      "campos": ["campo_1", "campo_2"]
    }
  ],
  "campos": [
    {
      "id": "campo_1",
      "tipo": "text",
      "label": "Nome do Campo",
      "obrigatorio": true,
      "config": {
        "placeholder": "Digite...",
        "help": "Texto de ajuda",
        "binding": "processo.numero"
      },
      "regras": [
        {
          "tipo": "required_when",
          "campo": "outro_campo",
          "campo_atual": "campo_1"
        }
      ]
    }
  ]
}
```

### Tipos de Campos Suportados

- `text` - Campo de texto
- `number` - Campo numérico
- `date` - Campo de data
- `textarea` - Área de texto
- `select` - Lista suspensa
- `boolean` - Checkbox

### Bindings Dinâmicos

O sistema suporta bindings para preencher campos automaticamente:

- `processo.numero` - Número do processo
- `processo.tipo` - Tipo do processo
- `afericao.data` - Data da aferição
- `certificado.numero` - Número do certificado
- `usuario.nome` - Nome do usuário
- `usuario.email` - Email do usuário

### Componentes

- `app/api/v1/form_builder.py` - API principal do Form Builder
- `app/services/form_builder_renderer.py` - Serviço de renderização
- `app/templates/referencia/templates_os/` - Templates de referência (Certilog)
- `app/static/css/referencia/form_builder.css` - Estilos CSS
- `app/static/js/referencia/` - JavaScript de referência

### Arquivos de Referência

Os arquivos do sistema Certilog foram copiados para diretórios `referencia/` como referência para futuras implementações:

- Templates: `app/templates/referencia/templates_os/`
- CSS: `app/static/css/referencia/form_builder.css`
- JavaScript: `app/static/js/referencia/`
- APIs: `app/api/v1/referencia/`
- Services: `app/services/referencia/`

**Nota:** Os arquivos em `referencia/` são apenas para consulta e não devem ser usados diretamente. Adaptar conforme necessário para o contexto do PDV Ibix.

---

## 16. APIs MOBILE (`/api/v1/mobile`)

APIs otimizadas para aplicativo mobile nativo, com suporte offline e recursos nativos (câmera, GPS, Bluetooth).

### Autenticação Mobile

- **POST** `/auth/token` - Login mobile (Form URL-encoded)
  - Content-Type: `application/x-www-form-urlencoded`
  - Body: `username=admin@ibix.com.br&password=senha123`
  - Response: `TokenResponse`
    ```json
    {
      "success": true,
      "message": "Login realizado com sucesso",
      "token": {
        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
        "token_type": "bearer",
        "expires_in": 1800
      },
      "user": {
        "id": 1,
        "nome": "Administrador",
        "email": "admin@ibix.com.br",
        "role_nome": "Administrador"
      }
    }
    ```
  - Autenticação: Não requerida
  - **Tempo de expiração:** 30 minutos (1800 segundos)

### Endpoints Mobile de Agendamentos

- **GET** `/mobile/agendamentos/tecnicos` - Lista agendamentos do técnico logado
  - Query params: `data`, `status`
  - Response: `List[AgendamentoMobileResponse]` (otimizado)
  - Ordenação: Próximos primeiro
  - Permissão: `agendamentos:visualizar`
  - Autenticação: Requerida

- **GET** `/mobile/agendamentos/hoje` - Agendamentos do dia do técnico
  - Response: `List[AgendamentoMobileResponse]`
  - Permissão: `agendamentos:visualizar`
  - Autenticação: Requerida

- **POST** `/mobile/agendamentos/{id}/iniciar` - Iniciar execução do agendamento
  - Response: `AgendamentoResponse`
  - Registra `data_hora_inicio` automaticamente
  - Permissão: `agendamentos:editar`
  - Autenticação: Requerida

- **POST** `/mobile/agendamentos/{id}/concluir` - Concluir agendamento
  - Body: `{"certificado_id": 123}` (opcional)
  - Response: `AgendamentoResponse`
  - Cria certificado automaticamente se fornecido
  - Permissão: `agendamentos:editar`
  - Autenticação: Requerida

### Endpoints Mobile de Processos

- **GET** `/mobile/processos/tecnicos` - Processos do técnico logado
  - Query params: `status`, `data_inicio`, `data_fim`
  - Response: `List[ProcessoMobileResponse]`
  - Permissão: `processos:visualizar`
  - Autenticação: Requerida

- **POST** `/mobile/processos/{id}/pre-checagem` - Registrar pré-checagem (offline)
  - Body: `PreChecagemMobileCreate`
    ```json
    {
      "checklist": {
        "condicoes_fisicas": "ok",
        "nivelamento": "ok"
      },
      "foto_base64": "data:image/jpeg;base64,...",
      "observacoes": "..."
    }
    ```
  - Response: `ProcessoResponse`
  - Permissão: `processos:editar`
  - Autenticação: Requerida
  - **Offline:** Suporta sincronização posterior

- **POST** `/mobile/processos/{id}/ensaio` - Registrar ensaio (offline)
  - Body: `EnsaioMobileCreate`
    ```json
    {
      "medicoes": [
        {
          "ponto": 1,
          "valor_nominal": 10.000,
          "leitura_1": 10.001,
          "leitura_2": 10.002,
          "leitura_3": 10.001
        }
      ],
      "temperatura_ambiente": 23.5,
      "umidade_relativa": 55.0
    }
    ```
  - Response: `ProcessoResponse`
  - Permissão: `processos:editar`
  - Autenticação: Requerida
  - **Offline:** Suporta sincronização posterior

### Padrões de Resposta Mobile

**Paginação:**
```json
{
  "items": [...],
  "total": 150,
  "pagina": 1,
  "por_pagina": 10,
  "total_paginas": 15
}
```

**Códigos HTTP:**
| Código | Significado | Ação |
|--------|-------------|------|
| 200 | Sucesso | Tudo OK |
| 201 | Criado | Recurso criado |
| 204 | Sem conteúdo | Exclusão bem-sucedida |
| 400 | Bad Request | Dados inválidos |
| 401 | Unauthorized | Token inválido/expirado → Fazer login |
| 403 | Forbidden | Sem permissão |
| 404 | Not Found | Recurso não encontrado |
| 422 | Unprocessable | Validação falhou |
| 500 | Server Error | Erro interno |

### Regras Críticas Mobile

**NUNCA FAZER:**
- ❌ Valores mockados ou placeholders
- ❌ Preencher formulários com valores padrão
- ❌ Dados simulados para testes

**SEMPRE FAZER:**
- ✅ Campos vazios esperando input do usuário
- ✅ Dados reais da API
- ✅ Validações client-side
- ✅ Tratamento de erros 401/403/500
- ✅ Timeout de 30s configurado
- ✅ Storage seguro de token (criptografado)

### Segurança Mobile

**Storage de Dados:**
- Token → Secure Storage (criptografado)
- Dados do usuário → SharedPreferences (JSON)
- Timeout de requisições: 30 segundos

**Tratamento de Erros:**
- 401 → Redirecionar para login
- 403 → Mostrar mensagem de permissão negada
- 500 → Mostrar mensagem de erro de conexão

**Referência:** Ver `Scripts_auxiliares/GUIA_DESENVOLVEDOR_MOBILE.md` e `Scripts_auxiliares/calibracao_mobile.md` para documentação completa

---

## 17. BILLING — Assinatura e Mercado Pago

**Documentação completa:** **MAPA_PAGAMENTO.md** (trial 30d, Checkout Pro, SubscriptionGuard, job diário, e-mails, RBAC).

### 17.1 Cliente (CA / Subcliente) — prefix `/api/v1/billing`

- **GET** `/billing/my-subscription` — Status da assinatura (resolve_tenant_pagador). Response: server_today, status, period_end, next_charge_at, grace_days, trial_days_left, grace_days_left, is_in_trial, is_past_due, is_blocked. Autenticação: JWT.
- **GET** `/billing/meus-limites` — **Limites de PDVs do tenant:** max_pdvs, pdvs_usados, pdvs_disponiveis, pode_criar_pdv, valor_mensal_centavos, valor_exibicao. Autenticação: JWT.
- **POST** `/billing/pay-now` — Gera preferência Checkout Pro; retorna init_point, preference_id. Autenticação: JWT.
- **GET** `/billing/my-payments?limit=50` — Lista pagamentos da assinatura. Autenticação: JWT.

### 17.0 Admin Dashboard (Super Admin) — prefix `/api/v1/admin/dashboard`

- **GET** `/admin/dashboard` — Dados do dashboard Super Admin (clientes novos, cadastros, usuários ativos 24h, últimos logins, pagamentos, **visitantes_vitrine**). Dependency: `require_superadmin_or_admin()` (payload Super Admin vs Administrador).
  - Query opcional Super Admin: `brand_id` — em marca origem (Ibix) filtra tenants; ausência = visão global. Em marca derivada (Solumática) o Host fixa o escopo (`resolve_admin_brand_scope`).
  - Resposta inclui `brand_scope` (`brand_id`, `brand_nome`, `scope_locked`, `scope_label`) e `brand_id_filtro`.
  - `visitantes_vitrine`: `{ hoje, ultimos_7_dias, ultimos_30_dias }` — cada um `{ humanos, bots, cloud }` (IPs únicos por `tipo_visitante` em paths da vitrine pública: `/loja`, `/loja/*`, `/categoria/*`, `/lojas-parceiras`, `/{slug}` não reservado). Serviço: `app/services/vitrine_access_analytics_service.py`.
  - Query opcional: `incluir_analytics=true`, `periodo=hoje|ultimos_7_dias|ultimos_30_dias`, `tipo_visitante=HUMANO|BOT|CLOUD|TODOS` (default analytics: `HUMANO`). Período inválido → HTTP 400.
  - Com `incluir_analytics=true`: bloco `visitantes_vitrine_analytics` com `paginas_top` (paths de produto mesclados por `anuncio_id`), `produtos_top` (IPs únicos corretos por produto), `lojas_top` (/{slug}), `funil`, `nota_metrica`. UI: `/admin/dashboard` (Superadministrador); filtro tipo visitante no front.

### 17.2 Super Admin — prefix `/api/v1/admin/billing`

- **GET** `/admin/billing/tenants?status=&q=&page=&per_page=&apenas_com_ca=` — Lista tenants (status assinatura, vencimento, dias atraso). **apenas_com_ca=true:** só tenants com pelo menos um usuário role "Cliente Administrador" (apenas C; usado no select Específico da página Valor e descontos; per_page até 10000). Dependency: require_superadmin().
- **GET** `/admin/billing/tenant/{tenant_id}` — Detalhe: assinatura, pagamentos.
- **POST** `/admin/billing/tenant/{tenant_id}/create-charge` — Retorna init_point (copiar link).
- **POST** `/admin/billing/tenant/{tenant_id}/block` — subscription.status = bloqueada, Tenant.ativo = False.
- **POST** `/admin/billing/tenant/{tenant_id}/unblock` — Tenant.ativo = True.
- **GET** `/admin/billing/config` — mp_configured, app_url (sem expor segredos).
- **POST** `/admin/billing/config` — Salva Access Token, Webhook Secret, APP_URL (configuracoes).
- **GET** `/admin/billing/config/validate` — Validação real do token MP (GET api.mercadolibre.com/users/me). Response: mp_valid, mp_message.
- **POST** `/admin/billing/onboarding/convite-lojista` — Envia e-mail de captação de lojista (body: `email`, `nome_destinatario`, `mensagem`); resposta inclui `cadastro_url`.
- **GET** `/admin/billing/onboarding/convite-lojista-template` — HTML efetivo do e-mail de convite a lojistas (`html`, `is_custom`). Override em `configuracoes` (`email_template_platform_convite_cadastro_lojista`) ou arquivo `emails/platform_convite_cadastro_lojista.html`.
- **PATCH** `/admin/billing/onboarding/convite-lojista-template` — Body `{ "html": "<!DOCTYPE ..." }` salva override; `{ "reset_to_default": true }` remove override. Exige `{{cadastro_url}}` no HTML salvo.
- **GET** `/admin/billing/preco` — Valor mensal (centavos), valor_aplicar_a, desconto_percent, desconto_escopo, desconto_tenant_ids.
- **POST** `/admin/billing/preco` — Salva valor mensal e regras de desconto (configuracoes).
- **POST** `/admin/billing/preco/aplicar-valor-todos` — Body: `respeitar_codigos_promocionais` (boolean, default true). Atualiza valor_mensal_centavos de todas as assinaturas: true = mantém desconto de código onde houver codigo_desconto_id; false = aplica o mesmo valor a todas (ignora códigos). Contrato comercial ativo sempre prevalece.
- **GET** `/admin/billing/marketplace-taxas/regras` — Query `ativo` (bool, opcional). Lista regras de taxas marketplace (faixas plataforma + gateway). Apenas Super Admin.
- **POST** `/admin/billing/marketplace-taxas/regras` — Cria regra. Body: `nome`, `escopo` (`geral` | `tenant`), `tenant_id` (obrigatório se `escopo=tenant`), `ativo`, `payload` (objeto: `faixas_plataforma` com `preco_min`, `preco_max` opcional, `modo` `fixo`|`percent`, `valor`; `gateway_pix`, `gateway_credito`, `gateway_debito` cada um com `modo` e `valor`). Só uma regra Geral ativa e só uma regra ativa por tenant.
- **PATCH** `/admin/billing/marketplace-taxas/regras/{id}` — Atualiza nome, ativo ou payload completo.
- **DELETE** `/admin/billing/marketplace-taxas/regras/{id}` — Remove regra.

### 17.3 Webhook Mercado Pago (sem JWT)

- **POST** `/api/webhooks/mercadopago` — Notificações de pagamento MP. Validação: headers `x-signature`, `x-request-id` (HMAC com MP_WEBHOOK_SECRET). Idempotência: tabela `webhook_events` (event_key = payment:{id}). Processamento: GET payment no MP, criar Payment, atualizar Subscription e Tenant. Response: 200 `{"status": "ok"}`. Router: `app/api/webhooks_mercadopago.py` (prefix `/api/webhooks`).

### 17.4 Webhook genérico (gateway SaaS) — prefix `/api/v1/billing`

- **POST** `/billing/webhook` — Receber webhook do gateway (SaaS plano/módulos). Idempotência por `X-Webhook-Id`; assinatura por `X-Webhook-Signature` (WEBHOOK_BILLING_SECRET); replay por `X-Webhook-Timestamp`. Tabela: `billing_events`.

### 17.5 Preços PDV (Super Admin) — prefix `/api/v1/admin/precos-pdv`

- **GET** `/admin/precos-pdv/` — Lista todos os preços (histórico). Dependency: require_superadmin().
- **GET** `/admin/precos-pdv/vigente` — Preço vigente (ativo, mais recente).
- **POST** `/admin/precos-pdv/` — Criar novo preço (valor_base_centavos, valor_pdv_adicional_centavos, vigencia_inicio).
- **PATCH** `/admin/precos-pdv/{id}` — Atualizar preço (valor_base, adicional, ativo).

### 17.5.1 Preços (Público) — prefix `/api/v1/precos`

- **GET** `/precos/vigente` — Retorna preço vigente **sem autenticação**. Usado pela landing page `/precos`.

### 17.5.2 Landing (Fale conosco) — prefix `/api/v1/landing`

- **POST** `/landing/fale-conosco` — **Público (sem autenticação).** Recebe o formulário "Fale conosco" da página inicial (landing). Body: `FaleConoscoRequest` — `nome`, `email`, `mensagem` (opcionais: `whatsapp`, `empresa`, `area_atuacao`, `consentimento_lgpd`, `consentimento_finalidade`). Envia e-mail para info@certilog.com.br (função help_center). Sem integração com CRM. Arquivo: `app/api/v1/landing.py`. A URL base da landing (canonical, og:url, links) é derivada do host da requisição (`request.base_url`) para que auto.ibix e www.ibix.com.br tenham cada um sua base; ver `_landing_base_url` em `main.py`.

### 17.5.3 SEO e Indexação — rotas públicas (sem autenticação)

- **GET** `/robots.txt` — `PlainTextResponse` com regras de indexação: permite páginas públicas (/, /login, /cadastro, /termos-de-uso, etc.), bloqueia /dashboard, /api/, /admin/. Inclui `Sitemap: {base}/sitemap.xml`. Coexiste com rotas dinâmicas da aplicação (ex.: vitrine no raiz); crawlers usam o path exato listado no sitemap.
- **GET** `/sitemap.xml` — Sitemap XML dinâmico (`application/xml`). Inclui home, páginas estáticas relevantes, categorias ativas (`CategoriaPlataforma`), produtos publicados (`AnuncioPlataforma.status == "publicado"`, limite 5.000), **URLs de loja no domínio raiz** `/{slug}` (lojas ativas com slug) e **páginas de categoria local** `/categoria/{categoria}-{cidade}` (combinações distintas persistidas em `lojas_marketplace.slug_categoria_cidade`; resolução no servidor por dado no banco, não por corte ingênuo de string). Implementação em `main.py` (`_landing_base_url` para URLs absolutas).
- **Handler 404** — Exception handler global: retorna `errors/404.html` (HTML) para browsers (`Accept: text/html`) e JSON `{"detail": "Not Found"}` para APIs. Registrado em `main.py` via `@app.exception_handler(404)`.

### 17.8 Hierarquia do Sistema (Super Admin) — prefix `/api/v1/admin/hierarquia`

- **GET** `/admin/hierarquia` — Árvore completa: Tenants → Usuários (por role) → Vínculos. Dependency: `require_superadmin()`. Arquivo: `app/api/v1/admin_hierarquia.py`.
  - Response:
    ```json
    {
      "tenants": [
        {
          "id": 1, "nome": "...", "slug": "...", "ativo": true,
          "subscription": { "status": "ativa", "period_end": "2026-03-01", "qtd_pdvs": 3 },
          "total_usuarios": 5,
          "usuarios_por_role": {
            "Administrador": [
              {
                "id": 1, "nome": "...", "email": "...", "cargo": "...", "ativo": true, "role": "Administrador",
                "clientes_vinculados": [{ "id": 1, "nome": "...", "cnpj": "...", "cidade": "...", "uf": "..." }],
                "cas_vinculados": [{ "id": 2, "nome": "...", "email": "...", "role": "Cliente Administrador" }]
              }
            ],
            "Cliente Administrador": [
              {
                "id": 2, "nome": "...", "email": "...", "cargo": "...", "ativo": true, "role": "Cliente Administrador",
                "clientes_vinculados": [{ "id": 3, "nome": "...", "cnpj": "..." }],
                "tecnicos_vinculados": [{ "id": 5, "nome": "...", "email": "..." }]
              }
            ],
            "Contador": [
              {
                "id": 10, "nome": "...", "email": "...", "cargo": "...", "ativo": true, "role": "Contador",
                "vinculado_a_ca": { "id": 2, "nome": "...", "email": "..." }
              }
            ]
          }
        }
      ],
      "orphan_users": [{ "id": 99, "nome": "...", "email": "...", "role": "Administrador" }],
      "stats": {
        "total_tenants": 5, "total_usuarios": 50, "total_clientes": 100, "total_roles": 9,
        "usuarios_por_role": { "Administrador": 3, "Cliente Administrador": 10, "Técnico": 15 }
      },
      "roles": [{ "id": 1, "nome": "Administrador" }, { "id": 6, "nome": "Superadministrador" }]
    }
    ```
  - **Vínculos por role:**
    - **Administrador**: `clientes_vinculados` (tabela `administrador_clientes`), `cas_vinculados` (tabela `administrador_cliente_administradores`)
    - **Cliente Administrador**: `clientes_vinculados` (tabela `cliente_administrador_clientes`), `tecnicos_vinculados` (tabela `cliente_administrador_tecnicos`)
    - **Contador**: `vinculado_a_ca` (campo `contador_vinculado_cliente_administrador_id` em `usuarios`)
  - **orphan_users**: usuários com `tenant_id = NULL`
  - Rota HTML: `GET /admin/hierarquia` — visualização interativa em árvore (expansível, busca, badges por role)

### 17.6 Contratos Comerciais (Super Admin / Admin) — prefix `/api/v1/contratos-comerciais`

- **GET** `/contratos-comerciais/?tenant_id=&status=` — Lista contratos.
- **GET** `/contratos-comerciais/{id}` — Detalhe do contrato.
- **POST** `/contratos-comerciais/` — Criar contrato (tenant_id, vigencia_inicio, qtd_pdvs_contratados). Valor calculado automaticamente com precos_pdv vigente. Sincroniza subscriptions.qtd_pdvs_contratados. Dependency: require_superadmin_or_admin().
- **GET** `/contratos-comerciais/{id}/aditivos` — Lista aditivos do contrato.
- **POST** `/contratos-comerciais/{id}/aditivos` — Criar aditivo (qtd_pdvs_nova, motivo). Atualiza contrato e subscription.

### 17.7 Códigos de Desconto e Divulgadores (Super Admin / Admin) — prefix `/api/v1`

- **GET** `/divulgadores?ativo=` — Lista divulgadores. Dependency: require_superadmin_or_admin().
- **POST** `/divulgadores` — Criar divulgador (nome, cpf_cnpj, email).
- **PATCH** `/divulgadores/{id}` — Atualizar divulgador.
- **GET** `/divulgadores/{id}/regras` — Regras de comissão do divulgador.
- **POST** `/divulgadores/{id}/regras` — Criar regra de comissão.
- **GET** `/codigos-desconto?ativo=` — Lista códigos.
- **GET** `/codigos-desconto/{id}` — Detalhe do código.
- **POST** `/codigos-desconto` — Criar código. Body: `representante_usuario_id` (id do usuário Administrador; backend encontra ou cria divulgador) ou `divulgador_id` (pelo menos um obrigatório); codigo, tipo_promocao, descontos.
- **PATCH** `/codigos-desconto/{id}` — Atualizar código.
- **GET** `/codigos-desconto/validar/{codigo}` — **Público (sem JWT).** Verifica se código é válido e ativo. Response: CodigoDescontoResponse ou 404.

**Referência:** MAPA_PAGAMENTO.md; MAPA_DO_SISTEMA.md (tabelas subscriptions, payments, webhook_events, billing_notificacoes, billing_events, precos_pdv, contrato_comercial, contrato_aditivos, codigos_desconto, divulgadores, divulgador_regras); variáveis MP_ACCESS_TOKEN, MP_WEBHOOK_SECRET, APP_URL.

---

## Negócios (Dashboard e Vendas)

**Escopo:** Operações respeitam `ClienteScope` (Superadministrador/Administrador = todos; Cliente Administrador = clientes vinculados). Rotas usam `forbid_cliente_access` e `get_cliente_scope_dep`. Referência: `app/core/scope.py`, MAPA_RBAC.md.

### Dashboard (Negócios / PDV)

- **GET** `/negocios/dashboard` — Resumo para a página **Dashboard** (`GET /dashboard` e `GET /negocio/dashboard`; template `meu_negocio/dashboard.html`; consumo via `window.authenticatedFetch('/api/v1/negocios/dashboard')`).
  - Response (estrutura atual): `{ vendas, produtos_mais_vendidos, estoque, ordens_servico }` — ver implementação em `app/api/v1/dashboard_negocios.py`.
  - Autenticação: obrigatória. **Escopo:** `ClienteScope` (`get_cliente_scope_dep`); sem estabelecimentos no escopo do CA, retorno com totais zerados para vendas e sem estoque agregado onde aplicável.
  - **Fonte de dados das vendas:** KPIs combinam **`Venda`** (PDV / gestão interna) com pedidos **líquidos** da vitrine em **`PedidosMarketplace`** (`pedidos_marketplace`), no mesmo espírito da listagem **Negócio → Pedidos**: escopo pela **`LojaMarketplace.cliente_id`** (join loja ↔ pedido). Pedidos só contam quando estão efetivamente pagos ou confirmados sem pagamento pendente/estornado (ver `_query_pedidos_marketplace_liquidos` em `dashboard_negocios.py`). Assim, vitrine e PDV aparecem unificados nos cards e nas vendas recentes quando as regras de negócio coincidem.
  - **Modelo subjacente:** continua a existir **`Venda`** ≠ registro isolado em **`PedidosMarketplace`**; o dashboard apenas **agrega** vistas para o CA.

- **GET** `/negocios/dashboard/graficos` — Séries para os gráficos do mesmo template (`authenticatedFetch('/api/v1/negocios/dashboard/graficos')`).
  - Query opcional: `data_inicio`, `data_fim`, `cliente_id`, `caixa_id` (período limitado por `MAX_PERIODO_DIAS` no backend).
  - Response: `{ vendas_por_periodo, vendas_por_forma_pagamento, vendas_por_vendedor, horarios_pico, vendas_por_categoria }`.
  - **Fonte:** séries mesclam **`Venda`** com **`PedidosMarketplace`** (pedidos líquidos, mesmo escopo loja/`cliente_id`), exceto quando **`caixa_id`** está presente — nesse caso aplicam-se apenas vendas da abertura daquele caixa (PDV), sem vitrine.
  - Autenticação: obrigatória; escopo igual ao dashboard.

**Documentação de evolução (2026-04):** Comportamento “venda na vitrine não aparecia no dashboard CA” devia-se ao dashboard considerar só **`Venda`**. **Implementação atual:** merge marketplace nos KPIs e nos gráficos em `app/api/v1/dashboard_negocios.py`; template `meu_negocio/dashboard.html` trata respostas HTTP e números nos gráficos (Chart.js).

- **GET** `/vendas/estatisticas` - Estatísticas de vendas
  - Response: `{ total_vendas, valor_total_vendas, vendas_pendentes, valor_medio_venda }`
  - Autenticação: Requerida
  - **Escopo cliente:** Se o token tiver `cliente_id`, calcula somente as vendas do cliente

### Entrada de Notas NFe (`/nfe-entrada`)

Importação de XML de NF-e de entrada (compras), conciliação de itens e lançamento no estoque. Escopo por `cliente_id` (estabelecimento). Rotas: `app/api/v1/nfe_entrada.py`.

- **POST** `/nfe-entrada/importar?cliente_id=` - Importar um XML (multipart campo `arquivo`). Response: `NfeImportResponse` (documento com `emitente_nome`, avisos).
- **POST** `/nfe-entrada/importar-lote?cliente_id=` - Importar vários XMLs em **uma requisição** (multipart: repetir o campo `arquivos` para cada arquivo; máximo 500). Evita estourar o rate limit por tenant do middleware ao importar dezenas de notas. Response 200: `NfeImportLoteResponse` (`resultados[]` com `arquivo`, `sucesso`, `erro`, `documento`, `avisos`; `total_ok`, `total_erro`). XMLs de evento (`procEventoNFe` etc.) retornam erro descritivo por arquivo.
- **GET** `/nfe-entrada/documentos?cliente_id=&limit=100` - Listar documentos. Query opcional: `entrada_saida`, `status_filtro`, `skip`. Response: `{ items, total, skip, limit }` — cada item inclui **`emitente_nome`** (nome do emissor, preenchido a partir de `emitente_fornecedor.nome`); schema `NfeDocumentoResponse` com campo opcional `emitente_nome`.
- **GET** `/nfe-entrada/documentos/{nfe_id}/itens?cliente_id=` - Listar itens do documento para conciliação.
- **PATCH** `/nfe-entrada/itens/{nfe_item_id}/vincular` - Vincular item a produto interno.
- **POST** `/nfe-entrada/documentos/{nfe_id}/confirmar-lancar?cliente_id=` - Confirmar conciliação e lançar no estoque. Gera movimentações de entrada e atualiza `produtos_cliente.quantidade_atual`. Response 200: `NfeConfirmarLancarResponse` (`movimentacoes_criadas`, `mensagem`). **Validações (400):** todos os itens devem estar vinculados; se não, `detail`: "Existem itens não vinculados. Vincule todos os itens antes de confirmar e lançar."; se o documento já tiver movimentação com esse `nfe_documento_id`, `detail`: "Documento já lançado no estoque."; outros erros (produto não encontrado para o estabelecimento, quantidade inválida) retornam `detail` com mensagem concatenada dos erros. Regra atômica: qualquer falha no bloco principal causa rollback do documento inteiro. **Front:** tela de conciliação exibe o `detail` completo no alert em caso de erro (se `detail` for array, unido com "; ").
- **GET** `/nfe-entrada/documentos/{nfe_id}/custos` - Custos rateados (pré-visualização).

### Ordens de Serviço (`/ordens-servico`)

- **GET** `/ordens-servico/` - Listar ordens de serviço com paginação (query: busca, cliente_id, status, responsavel_id, tipo, prioridade, `skip`, `limit`)
  - Response: `{ ordens, total, skip, limit }` — inclui `venda_id`, `venda_numero` quando a OS já foi enviada para vendas
  - Autenticação: Requerida

- **GET** `/ordens-servico/{ordem_id}` - Obter ordem por ID
  - Response: `OrdemServicoResponse` (inclui `venda_id`, `venda_numero` se houver venda vinculada)
  - Autenticação: Requerida

- **POST** `/ordens-servico/` - Criar ordem de serviço
  - Body: `OrdemServicoCreate`
  - Response: `OrdemServicoResponse`
  - Autenticação: Requerida

- **PUT** `/ordens-servico/{ordem_id}` - Atualizar ordem
  - Body: `OrdemServicoUpdate`
  - Response: `OrdemServicoResponse`
  - Autenticação: Requerida

- **POST** `/ordens-servico/{ordem_id}/enviar-para-vendas` - Enviar OS concluída para vendas (cobrança)
  - Cria **uma** Venda a partir da OS (relação 1:1). Requer: status da OS = `concluida`; OS ainda sem venda vinculada.
  - Response: `201 Created`, body `VendaResponse` com rastreio (`venda_origens`: OS imediata; orçamento raiz se `orcamento_origem_id`).
  - Erros: `400` se OS não concluída; `404` se OS não encontrada ou fora do escopo; `409 Conflict` se a OS já foi enviada para vendas.
  - Implementação: `ordem_servico_venda_service.criar_venda_a_partir_da_os` + `_venda_response_orm`.
  - Autenticação: Requerida

- **GET** `/ordens-servico/{ordem_id}/pdf` - PDF da ordem (template tenant ou fallback).
  - Autenticação: Requerida

- **DELETE** `/ordens-servico/{ordem_id}` - Excluir ordem (status permitidos conforme regra de negócio)
  - Response: `204 No Content`
  - Autenticação: Requerida

### Documentos de impressão (`/documentos-impressao`)

- **GET** `/documentos-impressao/templates` — Lista templates do tenant (query `tipo=orcamento|ordem_servico`).
- **POST** `/documentos-impressao/templates` — Criar template (HTML Jinja + CSS opcional).
- **PUT** `/documentos-impressao/templates/{id}` — Editar.
- **POST** `/documentos-impressao/templates/{id}/definir-padrao` — Marcar padrão por tipo.
- **POST** `/documentos-impressao/preview?formato=html|pdf` — Preview com dados mock + `brand.*`.
- Escopo: `tenant_id` + RLS; `forbid_cliente_access`. UI HTML: `/negocio/formatos-impressao`.

### Vendas (`/vendas`)

- **GET** `/vendas/` - Listar vendas com paginação
  - Query: `skip` (default 0), `limit` (default 100, max 1000), `data_inicio`, `data_fim` (YYYY-MM-DD)
  - Response: `{ vendas, total, skip, limit }` — inclui rastreio comercial: `orcamento_id`, `numero_orcamento`, `ordem_servico_id`, `ordem_servico_codigo`, `origem_imediata_*`, `origem_raiz_*`.
  - Autenticação: Requerida

- **GET** `/vendas/{venda_id}` - Obter venda por ID
  - Response: detalhes da venda (dict); inclui campos de origem acima + `origem_cadeia` (breadcrumb com timestamps de `venda_origens`).
  - Autenticação: Requerida

- **POST** `/vendas/` - Criar venda (manual; número gerado por `app/services/venda_numero.gerar_numero_venda`).
  - Body: `VendaCreate`
  - Response: `VendaResponse` (com campos de origem; origem manual registrada em `venda_origens`)
  - Autenticação: Requerida

- **POST** `/vendas/pedido-pendente` - Cria venda PENDENTE; registra origem `manual` em `venda_origens`.

**Schemas de resposta (Pydantic v2):** `VendaResponse` e `VendaItemResponse` possuem `model_config = ConfigDict(from_attributes=True)` para permitir construção a partir do ORM (ex.: no endpoint enviar-para-vendas). Os itens incluem `created_at` e `updated_at` (herdados de `BaseModel` nos modelos SQLAlchemy).

**Subcliente (Portal):** GET `/vendas/`, GET `/vendas/{venda_id}` e GET `/vendas/estatisticas` são acessíveis à role Subcliente (escopo por `cliente_id`). POST e POST `/{venda_id}/estornar` usam `forbid_cliente_access` e retornam 403 para Subcliente.

### PDVs (`/pdvs`) – Fase 1 Hierarquia

- **GET** `/pdvs/` - Listar PDVs no escopo (query: `cliente_id` opcional para filtrar por estabelecimento)
  - Response: lista `PDVResponse`
  - Escopo: Super Admin = todos; Admin = `administrador_clientes`; CA = `cliente_administrador_clientes`
  - Autenticação: Requerida; `forbid_cliente_access` (apenas Super Admin, Admin, CA)

- **GET** `/pdvs/{pdv_id}` - Obter PDV por ID (deve estar no escopo)
  - Response: `PDVResponse`

- **POST** `/pdvs/` - Criar PDV (cliente_id no escopo; UNIQUE identificador por cliente)
  - Body: `PDVCreate`
  - Response: `201 Created`, `PDVResponse`

- **PATCH** `/pdvs/{pdv_id}` - Atualizar PDV
  - Body: `PDVUpdate`
  - Response: `PDVResponse`

- **DELETE** `/pdvs/{pdv_id}` - Excluir PDV
  - Response: `204 No Content`

- **POST** `/pdvs/{pdv_id}/clonar-config` - Copiar configuracoes_hardware do PDV origem para outro PDV (body: `{ "pdv_destino_id": int }`)
  - Response: `PDVResponse` (PDV destino atualizado)

- **GET** `/pdvs/export-configuracoes` - Exportar configurações de todos os PDVs no escopo (backup para Disaster Recovery – Fase 6.1)
  - Response: lista `PDVConfigExportItem` (pdv_id, cliente_id, identificador, localizacao, configuracoes_hardware, updated_at)
  - Escopo: Super Admin = todos; Admin/CA = apenas PDVs dos estabelecimentos no escopo
  - Uso: rotinas de backup externas ou integração com script de backup; o script `scripts/backup_pdv-solumatica.sh` já inclui `pdvs_configuracoes.json` no backup

### Aberturas de Caixa (`/aberturas-caixa`) – Fase 1 (turno PDV)

Caixa por turno: uma abertura = um turno em um PDV; vendas vinculam `abertura_caixa_id`. Acesso: Super Admin, Administrador, Cliente Administrador (escopo por `cliente_id` do PDV) e **Operador PDV** (pode abrir/fechar no terminal).

- **GET** `/aberturas-caixa/` - Listar aberturas com paginação (query: `pdv_id`, `status`, `skip`, `limit`)
  - Response: `{ items, total, skip, limit }` — cada item é `AberturaCaixaResponse`
  - Escopo: Admin/CA = apenas PDVs dos estabelecimentos permitidos; Operador PDV = qualquer PDV

- **GET** `/aberturas-caixa/caixa-aberta?pdv_id={id}` - Obter caixa aberta do PDV (para vincular venda ao turno)
  - Response: `AberturaCaixaResponse` ou null se não houver caixa aberta

- **GET** `/aberturas-caixa/{abertura_id}` - Obter abertura por ID (deve estar no escopo)

- **POST** `/aberturas-caixa/abrir` - Abrir caixa (iniciar turno). Body: `AberturaCaixaAbrir` (pdv_id, valor_inicial). Apenas uma abertura aberta por PDV.
  - Response: `201 Created`, `AberturaCaixaResponse`
  - Usuário logado é registrado como `usuario_id` da abertura

- **PATCH** `/aberturas-caixa/{abertura_id}/fechar` - Fechar caixa (encerrar turno). Body: `AberturaCaixaFechar` (valor_final)
  - Response: `AberturaCaixaResponse` (data_fechamento e status atualizados)

### Estabelecimentos fiscais (`/estabelecimentos-fiscais`) – Fase 3.1.1

Configuração fiscal por estabelecimento (cliente_id). Escopo por `ClienteScope`; `forbid_cliente_access`.

**Contrato operacional CA x CF/Subcliente (obrigatório):**
- Para role **Cliente Administrador (CA)**, este módulo opera no contexto da **empresa cliente do SaaS** (Empresa Fiscal / emissor).
- **Não** deve tratar **CF/Subcliente** como CA neste módulo.
- Filtro de escopo para CA considera clientes no contexto fiscal (empresa emissora), incluindo o cliente próprio do CA.

- **GET** `/estabelecimentos-fiscais/` - Listar (query: `cliente_id`, `ativo`)
- **GET** `/estabelecimentos-fiscais/{estabelecimento_id}` - Obter por ID
- **POST** `/estabelecimentos-fiscais/` - Criar. Body: `EstabelecimentoFiscalCreate` (cliente_id, cnpj, ie, crt, certificado_digital_path, regime_tributario, serie_nfe, aliquotas_uf, ativo)
- **PATCH** `/estabelecimentos-fiscais/{estabelecimento_id}` - Atualizar
- **DELETE** `/estabelecimentos-fiscais/{estabelecimento_id}` - Excluir

### Empresa fiscal e certificado A1 (`/api/v1/fiscal/empresa`) – Módulo fiscal NF-e

Configuração da empresa fiscal (emissor) e upload do certificado A1. Escopo por `ClienteScope`: empresa deve pertencer ao CA do usuário.

- **POST** `/api/v1/fiscal/empresa/{empresa_id}/certificado` — Upload de certificado A1 (.pfx/.p12). Body: multipart/form-data com arquivo e campo `senha_certificado`. Escopo: empresa deve pertencer ao CA do usuário (ClienteScope); 403 se empresa de outro CA. A senha é criptografada em repouso (Fernet). Response pode incluir `certificado_validade` para atualizar o frontend.
- **GET/PUT** empresa fiscal: já cobertos pelo módulo fiscal. A empresa inclui `provedor_fiscal` (stub vs local). No PUT, não enviar blob/senha do certificado quando o upload foi feito via endpoint dedicado.

### Regras Fiscais ICMS (`/api/v1/fiscal/regras-fiscais-icms`) – Motor tributário NF-e (2026-03)

Regras parametrizadas para decisão fiscal por item (CFOP, CST/CSOSN, origem, alíquotas). Vinculadas por `empresa_id`; isolamento por ClienteScope (empresa → cliente). Permissões: `fiscal.empresa` ou `fiscal.notas-fiscais`.

- **GET** `/api/v1/fiscal/regras-fiscais-icms` — Listar regras. Query: `empresa_id`, `ativo`, `crt`, `tipo_operacao`, `limit` (max 500).
- **GET** `/api/v1/fiscal/regras-fiscais-icms/{regra_id}` — Obter regra por ID.
- **POST** `/api/v1/fiscal/regras-fiscais-icms` — Criar regra. Body: `RegraFiscalIcmsCreate` (empresa_id obrigatório).
- **PUT** `/api/v1/fiscal/regras-fiscais-icms/{regra_id}` — Atualizar regra. Body: `RegraFiscalIcmsUpdate` (campos parciais; não inclui empresa_id).
- **DELETE** `/api/v1/fiscal/regras-fiscais-icms/{regra_id}` — Excluir regra.

### Venda pagamentos (`/venda-pagamentos`) – Fase 3.2 (fracionamento)

Múltiplos pagamentos por venda. Escopo via venda.cliente_id.

- **GET** `/venda-pagamentos/?venda_id={id}` - Listar pagamentos da venda (venda deve estar no escopo)
- **POST** `/venda-pagamentos/` - Adicionar pagamento. Body: `VendaPagamentoCreate` (venda_id, forma, valor, status?, id_externo?, observacao?)
- **GET** `/venda-pagamentos/{pagamento_id}` - Obter pagamento por ID

### Movimentos de caixa (`/movimentos-caixa`) – Fase 3.2 (sangria/suprimento)

Sangria e suprimento por abertura de caixa. Mesmas roles de caixa (Super Admin, Admin, CA, Operador PDV); escopo via PDV do estabelecimento. **Senha mestra (Fase 3):** se o estabelecimento tiver senha mestra configurada, o body de POST deve incluir `senha_mestra`; caso contrário 400/403.

- **POST** `/movimentos-caixa/senha-mestra` - Configurar senha mestra do caixa para o estabelecimento. Body: `{ "cliente_id": int, "senha_mestra": string }`. Apenas Admin ou CA no escopo; senha mínima 4 caracteres. Response: 204 No Content.
- **GET** `/movimentos-caixa/?abertura_caixa_id={id}` - Listar movimentos (query opcional: `tipo` = sangria | suprimento)
- **POST** `/movimentos-caixa/` - Registrar movimento. Body: `MovimentoCaixaCreate` (abertura_caixa_id, tipo, valor, observacao?, **senha_mestra?**). tipo obrigatório: "sangria" ou "suprimento". Se estabelecimento tiver senha mestra configurada, senha_mestra é obrigatória.
- **GET** `/movimentos-caixa/{movimento_id}` - Obter movimento por ID

### Google Custom Search — imagens (`/integracoes`) e admin (`/admin/integracoes/google-cse`)

Busca de imagens para cadastro de produto (estoque). Credenciais: tabela `configuracoes` (`google_cse_api_key`, `google_cse_engine_id`) com **prioridade sobre** env `GOOGLE_CUSTOM_SEARCH_*`. Sufixo de query: `google_cse_query_suffix` (concatenado ao nome). **Cota:** colunas em `tenants` (`google_cse_limite_diario`, `google_cse_uso_dia`, `google_cse_uso_data`); **1 GET** de busca consome 1 unidade; POST `fetch` não consome. **Bypass de cota:** roles `Superadministrador` e `Administrador`.

- **GET** `/integracoes/google-custom-search-imagens/cota` — `{ aplica_cota, limite_diario, uso_hoje, restante }` ou bypass sem cota.
- **GET** `/integracoes/google-custom-search-imagens?q=&num=` — `searchType=image`; resposta inclui `query_efetiva`.
- **POST** `/integracoes/google-custom-search-imagens/fetch` — body `{ "url" }` → `data_url` base64.

**Superadmin apenas** (`require_superadmin`): prefixo `/admin/integracoes/google-cse`

- **GET** `/config` — engine_id, api_key_configured, api_key_masked, query_suffix, plataforma_limite_diario
- **PATCH** `/config` — api_key?, engine_id?, query_suffix?, plataforma_limite_diario?
- **GET** `/resumo` — credenciais_prontas, uso_total_hoje, plataforma_limite_diario, tenants_com_uso_hoje
- **GET** `/tenants` — lista com limite_diario, uso_hoje, restante
- **PATCH** `/tenants/{tenant_id}` — body `{ "google_cse_limite_diario": int }`
- **GET** `/tenants/{tenant_id}/historico` — últimos logs de busca

Página HTML: `GET /admin/integracoes/google-custom-search` (apenas Superadministrador).

**Credencial correta (Custom Search JSON API):** use uma **Chave de API** criada em **APIs e serviços → Credenciais → Criar credenciais → Chave de API**. O formato clássico costuma ser **`AIza...`**. Chaves em formato **`AQ...`** (outros fluxos do Google Cloud) ou **client_secret OAuth** **não** substituem essa chave: a API `customsearch/v1` rejeita (ex.: 401). No mesmo projeto, **ative** a API **Custom Search API**; em restrições da chave, limite à **Custom Search API** (e por IP do servidor, se desejar). O **Search Engine ID (`cx`)** vem do Programmable Search Engine — é diferente da chave. **Erro 403** *"This project does not have the access to Custom Search JSON API"*: costuma exigir **conta de faturamento vinculada ao projeto** (mesmo para uso dentro da cota gratuita), além da API ativada no **mesmo** projeto da chave.

### Produtos por estabelecimento (`/produtos-cliente`) – Fase 2

Catálogo de produtos por estabelecimento (cliente_id = loja). Escopo: Super Admin = todos; Admin/CA = estabelecimentos em `administrador_clientes` / `cliente_administrador_clientes`. Autenticação e `forbid_cliente_access` (apenas Super Admin, Admin, CA). **Campos do produto:** `ProdutoClienteCreate` / `ProdutoClienteUpdate` / `ProdutoClienteResponse` incluem `cfop_padrao`, `referencia`, **`categoria_id`** (FK material_categoria) e **`tipo_material_id`** (FK tipo_material). O modal Novo/Editar Produto em `/negocio/estoque` usa selects dinâmicos para Categoria e Tipo de Material (APIs material-categorias e tipo-material). Ver MAPA_DO_SISTEMA (Produtos por estabelecimento; Categorias e tipos de material).

- **GET** `/produtos-cliente/` - Listar produtos com paginação (query: `cliente_id`, `busca`, `ativo`, **`categoria_id`**, **`tipo_material_id`**, `sem_imagem`, `sem_tipo`, `sem_categoria`, `sem_preco_venda`, `sem_descricao`, `skip`, `limit`)
  - Response: `{ items, total, skip, limit }` — cada item é `ProdutoClienteResponse` (inclui `cliente_nome` quando disponível)
  - **Superadministrador — visão global:** Quando `cliente_id` é **omitido**, retorna produtos de **todos** os estabelecimentos (sem filtro por `ClienteScope`). Cada item traz `cliente_id` e `cliente_nome` da loja. Útil para catálogo global, busca cross-tenant e operações administrativas. **Admin/CA** continuam obrigados a informar `cliente_id` dentro do escopo (403 se fora do escopo)

- **GET** `/produtos-cliente/{produto_id}` - Obter produto por ID (deve estar no escopo)

- **POST** `/produtos-cliente/` - Criar produto. Body: `ProdutoClienteCreate`. UNIQUE(codigo, cliente_id). Aceita categoria_id e tipo_material_id.

- **PATCH** `/produtos-cliente/{produto_id}` - Atualizar produto (inclui cfop_padrao, referencia, categoria_id, tipo_material_id, valor_custo, etc.)

- **DELETE** `/produtos-cliente/{produto_id}` - Excluir produto

- **GET** `/produtos-cliente/por-codigo-barras?codigo_barras=&cliente_id=` - Obter produto do estabelecimento pelo código de barras (para PDV).
- **GET** `/produtos-cliente/{produto_id}/codigos-barras` - Listar códigos de barras do produto.
- **POST** `/produtos-cliente/{produto_id}/codigos-barras` - Adicionar código de barras (body: codigo_barras, principal). Código globalmente único.
- **DELETE** `/produtos-cliente/{produto_id}/codigos-barras/{codigo_id}` - Remover código de barras.

### Categorias de material (`/material-categorias`) – Estoque

Cadastro de categorias para classificação de produtos (ex.: Padaria, Mercearia, Bebidas). Mesmo escopo e permissão que estoque (negocios.estoque). Schemas: `app/schemas/material_categoria.py`.

- **GET** `/material-categorias/` - Listar categorias (query opcional: `ativo`). Response: lista de MaterialCategoriaResponse.
- **POST** `/material-categorias/` - Criar categoria. Body: MaterialCategoriaCreate.
- **PATCH** `/material-categorias/{id}` - Atualizar categoria. Body: MaterialCategoriaUpdate.

### Tipos de material (`/tipo-material`) – Estoque

Cadastro de tipos de material (ex.: Produto Acabado, Consumível, Serviço). Mesmo escopo e permissão que estoque. Schemas: `app/schemas/tipo_material.py`.

- **GET** `/tipo-material/` - Listar tipos (query opcional: `ativo`). Response: lista de TipoMaterialResponse.
- **POST** `/tipo-material/` - Criar tipo. Body: TipoMaterialCreate.
- **PATCH** `/tipo-material/{id}` - Atualizar tipo. Body: TipoMaterialUpdate.

### Movimentações de estoque (`/movimentacoes-estoque`) – Fase 2

Registrar entrada/saída/ajuste e atualizar `produto_cliente.quantidade_atual`. Escopo por cliente_id do produto.

- **GET** `/movimentacoes-estoque/` - Listar com paginação (query: produto_cliente_id, cliente_id, tipo, `skip`, `limit`)
  - Response: `{ items, total, skip, limit }` — cada item é `MovimentacaoEstoqueResponse`
- **POST** `/movimentacoes-estoque/` - Registrar movimentação. Body: produto_cliente_id, tipo (entrada|saida|ajuste), quantidade, valor_unitario?, documento_ref?, observacao?. Entrada soma; saída/ajuste subtraem da quantidade_atual.

### Fornecedores por estabelecimento (`/fornecedores-cliente`) – Fase 2

- **GET** `/fornecedores-cliente/` - Listar (query: cliente_id, ativo, busca). Busca filtra por nome ou CNPJ (ilike).
- **GET** `/fornecedores-cliente/{fornecedor_id}` - Obter por ID.
- **POST** `/fornecedores-cliente/` - Criar. Body: FornecedorClienteCreate. CNPJ validado e normalizado para dígitos-only (14 chars) via CNPJValidator. Retorna **409 Conflict** se já existe fornecedor com mesmo CNPJ no estabelecimento.
- **PATCH** `/fornecedores-cliente/{fornecedor_id}` - Atualizar. Mesma validação de CNPJ duplicado (excluindo o próprio registro).
- **DELETE** `/fornecedores-cliente/{fornecedor_id}` - Excluir.
- **Auditoria:** todas as operações de escrita registram `audit_action()` com tenant_id.
- **Integridade:** UniqueConstraint parcial em `(cliente_id, cnpj)` quando CNPJ não é NULL (migration `fc01`).
- **Frontend:** Tela dedicada em `/negocio/fornecedores` (sidebar > Negócios > Fornecedores). **Cliente Administrador:** sem seletor de estabelecimento; contexto = `get_empresa_fiscal_cliente_id`. Superadmin / escopo multi-loja: seletor opcional (`?cliente_id=`).

### Produtos Fornecedor — vínculo produto ↔ fornecedor (`/produtos-fornecedor`)

- **GET** `/produtos-fornecedor/?fornecedor_cliente_id={id}` - Listar vínculos de um fornecedor com join em ProdutoCliente (nome, código). Valida escopo do fornecedor. Response: lista de `ProdutoFornecedorResponse` (JSON com `created_at` em ISO-8601, `preco_compra` numérico).
- **DELETE** `/produtos-fornecedor/{vinculo_id}` - Excluir vínculo (hard delete). Vínculo pode ser recriado pela próxima importação de NF-e.
- **Observação:** vínculos são criados automaticamente pelo fluxo de conciliação da Entrada NF-e (`nfe_entrada_service.vincular_item` com `atualizar_mapa=True`). A tabela `produtos_fornecedor` mapeia `(fornecedor_cliente_id, codigo_fornecedor)` → `produto_cliente_id`.

### Pagamentos – Módulo multiprovedor (`/payments`) – Fase 3.3 (fases 1 e 2 operacionais)

Configs por estabelecimento; processamento real pós-venda; status por UUID; retentativa por UUID; webhook por provedor. Escopo por estabelecimento (cliente_id). Autenticação e `forbid_cliente_access` nas rotas de config/process/retry.

**Contrato operacional CA x CF/Subcliente (obrigatório):**
- Para role **Cliente Administrador (CA)**, a configuração e operação de gateway em `/payments/*` devem usar o contexto da **empresa cliente do SaaS** (estabelecimento/empresa fiscal do CA).
- **CF/Subcliente** não é o ator configurador do gateway neste módulo.
- Frontend de pagamentos deve listar estabelecimentos no contexto fiscal do CA (não lista de subclientes operacionais por padrão).

- **GET** `/payments/configs?estabelecimentoId={cliente_id}` - Listar configs de provedores do estabelecimento
- **GET** `/payments/configs/{estabelecimento_id}` - Listar configs por path (equivalente ao query acima)
- **POST** `/payments/configs` - Criar config. Body: `PaymentProviderConfigCreate` (cliente_id, provider_code, **credentials?** dict em plain para criptografar, ou credentials_encrypted?; fee_configs?, routing_rules?, is_active, is_default, test_mode). **Providers permitidos:** `mercadopago`, `pagbank`, `pagarme`. Credenciais são criptografadas em repouso (PAYMENT_CREDENTIALS_SECRET ou PAYMENT_CREDENTIALS_PASSWORD no env).
- **POST** `/payments/process` - Processar pagamento via **PaymentOrchestrator**: carrega configs ativas do estabelecimento, seleciona provedor permitido, charge real, **SplitEngine** aplica split_rules e persiste transaction_splits. Body: `PaymentProcessRequest`. Response: `PaymentProcessResponse` (transaction_uuid, status, provider_transaction_id, payment_details, message, retry_allowed).
- **POST** `/payments/retry/{transaction_uuid}` - Retentar pagamento para transação pendente/falha (gera nova tentativa com nova idempotency_key). Escopo igual ao comprovante quando `checkout_session_id` (participante da sessão). **2026-05-15**
- **GET** `/payments/status/{transaction_uuid}` - Obter status da transação. Response: `PaymentStatusResponse` (uuid, status, payment_method, amount, venda_id?, provider_transaction_id?, paid_at?, refunded_at?, reconciliation_status?, reconciliation_date?). Escopo ampliado para participante da sessão unificada. **2026-05-15**
- **GET** `/payments/transactions?estabelecimentoId={cliente_id}&status={pending|failed|paid,authorized|all}&data_inicio={YYYY-MM-DD}&data_fim={YYYY-MM-DD}&skip={n}&limit={n}` - Listar transações **no escopo do estabelecimento**. Inclui linhas cuja `PaymentTransaction.cliente_id` é o CA **e** linhas de **checkout unificado marketplace** em que existe pedido na sessão (`checkout_session_id` + `marketplace_checkout_session_pedidos`) com `pedidos_marketplace.tenant_id` = esse `cliente_id`. Com **`estabelecimentoId`**, `amount`, `cliente_id`, `numero_pedido` e `pedido_id` na response refletem a **parcela daquele tenant** (vários `numero_pedido` concatenados se o mesmo CA tiver mais de um pedido na sessão); sem `estabelecimentoId` (lista “todos” no escopo permitido ao usuário), mantém-se o comportamento agregador por linha física (`amount` total da transação, `cliente_id` âncora). Implementação: `app/services/payments/marketplace_unified_payment_scope.py` + `listar_transacoes` em `app/api/v1/payments.py`. **2026-05-15**
- **GET** `/payments/transactions/{transaction_uuid}/comprovante` - Retorna HTML do comprovante de pagamento (imprimível). Usado pelo front com fetch (evita problema de cookie em navegação). Autenticação: Bearer ou cookie. Escopo ampliado: CA que **participa** da mesma sessão unificada pode acessar (não apenas o `cliente_id` da linha). **2026-05-15**
- **POST** `/payments/reconcile/{transaction_uuid}` - Reconcilia transação marketplace: busca status no Mercado Pago e atualiza PaymentTransaction + PedidoMarketplace. Escopo igual ao comprovante para sessão unificada. **2026-05-15**
- **POST** `/payments/webhook/{provider_code}` - Webhook dos provedores (aceita `mercadopago`, `pagbank`, `pagarme`). Processa payload JSON, identifica order_id/status, mapeia para status interno e atualiza `payment_transactions` com reconciliação.
- **GET** `/payments/connect/pagbank/start?estabelecimentoId={id}` - Inicia fluxo OAuth PagBank Connect: redireciona CA para PagBank autorizar. State assinado (HMAC-SHA256 com SECRET_KEY, TTL 15min).
- **GET** `/payments/connect/pagbank/callback?code={code}&state={state}` - Callback OAuth PagBank: troca code por access_token/refresh_token, salva em `payment_provider_configs` como credenciais criptografadas. Redireciona para `/negocio/recebiveis?connect=pagbank_success` ou `pagbank_error`.
- **GET** `/payments/modo-recebimento?clienteId={id}` - Retorna `modo_recebimento` da Empresa Fiscal vinculada ao cliente e se o usuário pode mutar gateway. `clienteId` é **opcional** (omitir = só política de edição, p.ex. filtro «Todos» em Recebíveis). Response: `{ "modo_recebimento": "direto"|"plataforma"|null, "cliente_id": int|null, "gateway_configuracao_permitida": bool }` (`permitida` = Superadmin ou `payment_lojas_gateway_self_service`).

### API Repasses (`/negocio/financeiro/repasses/`) – SuperAdmin only

- **Marketplace sessão unificada (2026-05-15):** transações `PaymentTransaction` com `checkout_session_id` entram no **saldo/bruto por CA** quando o CA é **participante** (pedido na sessão com `tenant_id` = `cliente_id`), não apenas quando é o `cliente_id` gravado na transação (âncora). Valores por linha (`amount`, taxas) usam o **rateio** do pedido pertencente àquele tenant (`filter_transactions_query_for_estabelecimento`, `amount_payment_transaction_para_estabelecimento` em `marketplace_unified_payment_scope.py`).
- **GET** `/negocio/financeiro/repasses/resumo` - Saldos pendentes de repasse agrupados por CA (modo=plataforma). Response: lista de `ResumoCA` (cliente_id, cliente_nome, total_vendas_bruto, total_taxa, total_repassado, saldo_pendente). **Bruto e contagem** consideram o rateio acima quando aplicável.
- **GET** `/negocio/financeiro/repasses/extrato?cliente_id={id}&status={pendente|repassado|cancelado}&page={n}&per_page={n}` - Extrato de repasses com filtros e paginação.
- **POST** `/negocio/financeiro/repasses/` - Criar repasse manual. Body: `RepasseCreate` (cliente_id, valor_bruto, valor_taxa, valor_liquido, periodo_inicio, periodo_fim, comprovante?, observacao?).
- **PUT** `/negocio/financeiro/repasses/{id}` - Atualizar status/comprovante/observação. Body: `RepasseUpdate` (status?, comprovante?, observacao?). Ao marcar `repassado`, `data_repasse` é preenchido automaticamente.
- **GET** `/negocio/financeiro/repasses/taxas` - Lista taxas configuradas por empresa fiscal (modo=plataforma).
- **GET** `/negocio/financeiro/repasses/transacoes?cliente_id={id}&limit={n}` - Transações modo plataforma pagas/autorizadas; com **`cliente_id`**, inclui sessão unificada e valores rateados (**2026-05-15**).
- **GET** `/negocio/financeiro/repasses/sugestao?cliente_id=…&periodo_inicio&periodo_fim` - Bruto/contagem/taxa sugeridos no período; com mesmo critério de participação na sessão (**2026-05-15**).

### Webhook Mercado Pago (`/api/webhooks/mercadopago`) – Fase 2

- **POST** `/api/webhooks/mercadopago` - Recebe evento de pagamento Mercado Pago com assinatura (`x-signature`).
- Fluxo:
  1. valida assinatura;
  2. busca pagamento no Mercado Pago;
  3. reconcilia `payment_transactions` por `external_reference` (idempotency_key);
  4. atualiza status (`paid/authorized/pending/failed`), `provider_transaction_id`, `paid_at`, `reconciliation_status`;
  5. sincroniza `venda_pagamentos` vinculado à venda (`confirmado`/`pendente`);
  6. fallback para fluxo de billing quando o evento não for de venda.

### Onboarding e importação em lote (`/onboarding`) – Fase 1.4

- **GET** `/onboarding/template/clientes` - Download do CSV modelo para importação de clientes/estabelecimentos (colunas: nome, cnpj, cep, endereco, cidade, uf, contato, telefone, email)
  - Response: arquivo CSV (attachment)
  - Autenticação: Requerida; `forbid_cliente_access`

- **POST** `/onboarding/import/clientes` - Importar clientes em lote (JSON array de objetos ClienteCreate)
  - Body: lista de `ClienteImportItem` (mesmo schema de ClienteCreate)
  - Response: `{ "criados": int, "erros": [ { "linha", "cnpj", "erro" } ] }`
  - Cliente Administrador: novos clientes são vinculados ao seu escopo (`cliente_administrador_clientes`)
  - Autenticação: Requerida; `forbid_cliente_access`

---

## 18. ORÇAMENTOS E PEDIDOS (`/api/v1/orcamentos`, `/api/v1/pedidos`)

**Escopo:** ClienteScope e `forbid_cliente_access` (mesmo padrão de vendas/pagamentos). Filtro por `cliente_id` (estabelecimento). Listagens e operações respeitam `get_cliente_scope_dep`; rotas de escrita exigem Superadministrador, Administrador ou Cliente Administrador.

### Orçamentos (`/api/v1/orcamentos`)

- **GET** `/orcamentos` — Lista orçamentos (skip, limit, status, cliente_id). Response: `{ orcamentos, total, skip, limit }`.
- **GET** `/orcamentos/{id}` — Detalhe com itens. Response: `OrcamentoResponse`.
- **POST** `/orcamentos` — Criar orçamento em rascunho. Body: `OrcamentoCreate` (cliente_id, destinatario_id opcional, data_validade, observacoes, condicoes_pagamento, itens).
- **POST** `/orcamentos/{id}/emitir` — Alterar status de rascunho para emitido.
- **POST** `/orcamentos/{id}/converter` — Converter orçamento em pedido. Body: `OrcamentoConverterRequest` (reservar_estoque opcional). Response: `{ message, pedido_id, numero_pedido }`.
- **POST** `/orcamentos/{id}/converter-os` — Converter em ordem de serviço (body: `tipo_id`). Grava `ordem_servico.orcamento_origem_id`. Audit `orcamento_convertido_os`.
- **POST** `/orcamentos/{id}/converter-venda` — Cria venda PENDENTE + `venda_origens` + `vendas.orcamento_id`. Redirect UI: `/negocio/venda?finalizar={venda_id}`.
- **GET** `/orcamentos/{id}/pdf` — PDF via template tenant ou fallback legado (`documento_impressao_service`).

**Pendentes menores:** DELETE `/orcamentos/{id}` (apenas rascunho), POST enviar-email/whatsapp.

### Pedidos (`/api/v1/pedidos`)

- **GET** `/pedidos` — Lista pedidos (skip, limit, status, cliente_id). Response: `{ pedidos, total, skip, limit }`.
- **GET** `/pedidos/{id}` — Detalhe com itens. Response: `PedidoResponse`.
- **GET** `/pedidos/{id}/cupom` — Conteúdo do cupom não fiscal para impressão (`CupomConteudoResponse`: `tipo` nao_fiscal|fiscal, `linhas`, `html`). Respeita `tenant.cupom_tipo` fiscal (retorno vazio de não fiscal). Auth: `get_current_user` + escopo ClienteScope.
- **POST** `/pedidos` — Criar pedido (rascunho). Body: `PedidoCreate` (cliente_id, orcamento_id opcional, data_prevista_entrega, observacoes, itens). Se orcamento_id informado, orçamento é validado e marcado como convertido.

**Pendentes:** PUT `/pedidos/{id}`, DELETE ou POST `/pedidos/{id}/cancelar`, POST `/pedidos/{id}/reservar-estoque`, POST `/pedidos/{id}/liberar-reserva`, POST `/pedidos/{id}/faturar`, GET `/pedidos/{id}/pdf`.

### Relatório

- **GET** `/relatorios/conversao-orcamentos` — Pendente. Período e cliente_id opcional; orçamentos emitidos vs convertidos; taxa de conversão.

### Schemas

- `app/schemas/orcamento.py`: OrcamentoCreate, OrcamentoUpdate, OrcamentoResponse, OrcamentoListResponse, OrcamentoConverterRequest, OrcamentoItemCreate/Response.
- `app/schemas/pedido.py`: PedidoCreate, PedidoUpdate, PedidoResponse, PedidoListResponse, PedidoFaturarRequest/FaturarBody, PedidoItemCreate/Response.

---

## 19. MARKETPLACE E LOJA (VITRINE) (`/api/v1/marketplace`, `/api/v1/loja`, `/api/v1/marketing-vitrine`, `/api/v1/marketing/ibix-lancamento`)

**Escopo gestão:** ClienteScope (Superadmin sem filtro; Admin/CA por allowed_ids). Autenticação: JWT PDV (cookie `pdv_solumatica_token` ou Bearer). **Vitrine:** rotas públicas sem auth PDV; rotas “minha-conta / meus-pedidos / avaliar” exigem consumidor (cookie `loja_consumidor_token` ou Bearer com tipo=consumidor).

**OAuth Google (login na vitrine `/loja`):** `LOJA_OAUTH_GOOGLE_CLIENT_ID` e `LOJA_OAUTH_GOOGLE_CLIENT_SECRET` (secret só servidor, `.env`) em `app/core/config.py`. **Não** confundir com **Google Custom Search** (busca de imagens no estoque: API Key + `cx`). Console Google, origens JS e URIs de redirecionamento: **[MAPA_GOOGLE_OAUTH_VITRINE.md](MAPA_GOOGLE_OAUTH_VITRINE.md)**.

### Gestão Marketplace (`/api/v1/marketplace`)

- **GET** `/marketplace/categorias` — Lista categorias plataforma (ativa, skip, limit). Permissão: `marketplace:visualizar`; `forbid_cliente_access`.
- **POST** `/marketplace/categorias` — Criar categoria. Permissão: `marketplace:configurar_loja`.
- **GET** `/marketplace/categorias/{id}` — Obter categoria. Permissão: `marketplace:visualizar`.
- **PATCH** `/marketplace/categorias/{id}` — Atualizar categoria. Permissão: `marketplace:configurar_loja`.
- **GET** `/marketplace/loja?cliente_id=` — Obter loja do estabelecimento. Escopo: cliente_id no escopo. Permissão: `marketplace:visualizar`.
- **GET** `/marketplace/lojas` — Lista todas as lojas marketplace (query opcional `status`, `skip`, `limit`; resposta `{ items, total }`). **Apenas Superadministrador** (`require_superadmin()` em `app/api/v1/marketplace.py`). Usado pela tela admin de SEO da vitrine.
- **POST** `/marketplace/loja` — Ativar/criar loja (body: LojaMarketplaceCreate). Escopo: cliente_id no escopo. Permissão: `marketplace:configurar_loja`.
- **PATCH** `/marketplace/loja/{loja_id}` — Atualizar loja. Escopo: loja do escopo. Permissão: `marketplace:configurar_loja`. **Regras (400 se violadas):** campos de transporte (`formato_frete`, `taxa_entrega_fixa`, `entrega_gratis_apos`, `tipo_entrega`, `raio_entrega_km`) **não** são mais aceitos — usar `PATCH /api/v1/transporte/loja/{loja_id}` (ver § Transporte). **Regras RBAC (403):** campos de SEO avançado `seo_title`, `seo_description`, `og_image_url`, `seo_enabled` — somente Superadministrador. Administrador e Cliente Administrador podem editar demais campos permitidos pelo schema (nome, slug, local SEO, `nome_fantasia`, descrições, imagens, etc.) dentro do escopo.

#### Transporte (módulo dedicado — `app/api/v1/transporte.py`)

- **GET** `/transporte/loja/{loja_id}` — Configuração de transporte da loja. Permissão: `marketplace:visualizar` + escopo. Response: `modo` (`retirada` \| `ambos`), `submodo` (`propria_gratis` \| `propria_valor` \| `plataforma`, quando `modo=ambos`), `taxa_entrega_fixa`, `entrega_gratis_apos`, `raio_entrega_km`, `formato_frete` (reflexo do banco), `tipo_entrega`.
- **PATCH** `/transporte/loja/{loja_id}` — Atualiza modo/submodo/valores. Permissão: `marketplace:configurar_loja` + escopo. CA salva a própria loja; Superadministrador / Administrador com escopo amplo salvam qualquer loja. Validações: `modo=retirada` zera taxas; `modo=ambos` exige `submodo`; `submodo=propria_valor` exige `taxa_entrega_fixa ≥ 0` (`entrega_gratis_apos` opcional).
- **GET** `/transporte/loja/{loja_id}/regras?cidade&uf` — Público (sem auth). Mesmo contrato do legado `GET /loja/{loja_id}/frete` (que vira alias **deprecado**). Aplica `LojaAreaEntrega` quando a localidade está coberta; senão devolve `taxa_entrega_fixa` da loja.
- **GET** `/transporte/loja/{loja_id}/areas?ativo` — Alias somente leitura para áreas de entrega da loja (CRUD em `/marketplace/loja/{id}/areas-entrega` continua com `require_superadmin()`, **sem mudança de permissão**).
- **GET** `/marketplace/status-pedido` — Lista status de pedido da loja (query `incluir_inativos`: bool, default false). Sem incluir_inativos: apenas ativos (CA usa para filtro/modal). Com `incluir_inativos=true`: todos; acesso apenas Super Admin. Permissão leitura: `marketplace:visualizar`.
- **POST** `/marketplace/status-pedido` — Criar status (body: codigo, label, ordem, ativo). Apenas Super Admin.
- **PATCH** `/marketplace/status-pedido/{id}` — Atualizar status (label, ordem, ativo). Apenas Super Admin.
- **PATCH** `/marketplace/status-pedido/{id}/desativar` — Desativa status (ativo=false). Apenas Super Admin.
- **GET** `/marketplace/taxas-vigentes` — Query: `cliente_id` (obrigatório, estabelecimento), `preco` (opcional, decimal). Resolve a regra de taxas marketplace para o `tenant_id` do usuário (regra `tenant` ativa tem prioridade sobre regra **Geral**). Resposta: `nome_regra`, `escopo_aplicado`, `payload` (faixas + gateway), e `preview` (custos estimados) se `preco` foi informado. Escopo `cliente_id`. Permissão: `marketplace:visualizar`.
- **GET** `/marketplace/anuncios` — Lista anúncios (loja_id, cliente_id, status, skip, limit). Escopo por loja/cliente. Permissão: `marketplace:visualizar`.
- **POST** `/marketplace/anuncios` — Criar anúncio (body: AnuncioPlataformaCreate). Valida produto em produtos_cliente do estabelecimento da loja. Permissão: `marketplace:publicar`. Suporta frete por produto (`frete_sobrescrever_loja`, `formato_frete_produto`, `taxa_entrega_fixa_produto`, `entrega_gratis_apos_produto`). Opcionais: `custo_plataforma_estimado`, `custo_cartao_estimado` (planejamento; não expostos na vitrine pública).
- **GET** `/marketplace/anuncios/{id}` — Obter anúncio. Escopo: loja no escopo. Permissão: `marketplace:visualizar`.
- **PATCH** `/marketplace/anuncios/{id}` — Atualizar anúncio. Permissão: `marketplace:publicar`. Suporta override de frete por produto com precedência sobre a loja. Opcionais: `custo_plataforma_estimado`, `custo_cartao_estimado`.
- **POST** `/marketplace/sync/estoque?loja_id=` — Sincroniza estoque dos anúncios a partir de produtos_cliente; registra em SyncControle. Permissão: `marketplace:publicar`.
- **GET** `/marketplace/loja/{loja_id}/pedidos` — Lista pedidos da loja (status_pedido, status_pagamento, skip, limit). Itens incluem `nome_produto_snapshot`. Permissão: `marketplace:gerenciar_pedidos`.
- **GET** `/marketplace/pedidos/{pedido_id}/cupom` — Cupom não fiscal do pedido marketplace (`CupomConteudoResponse`). Permissão: `marketplace:gerenciar_pedidos`; escopo pela loja do pedido.
- **PATCH** `/marketplace/pedidos/{pedido_id}` — Atualizar status_pedido e/ou status_pagamento. Validação: se status_pedido informado, deve existir em `status_pedido_marketplace` com ativo=true; caso contrário 400. Permissão: `marketplace:gerenciar_pedidos`.
- **GET** `/marketplace/loja/{loja_id}/extrato` — Lista extrato financeiro da loja (tipo opcional, skip, limit). Permissão: `marketplace:financeiro`.
- **POST** `/marketplace/admin/reparar-comprador-pedidos` — **Apenas Superadministrador** (`require_superadmin()`). Reparação retroativa de `PedidoMarketplace.comprador_id` para pedidos criados antes da fix em `resolve_comprador_para_loja`: identifica pares `(REGISTERED, GUEST)` no mesmo `tenant_id` com mesmo e-mail (case-insensitive) e reatribui `comprador_id` dos pedidos do guest para o registered. Body: `ReparacaoCompradorRequest` (`tenant_id` obrigatório; `email` opcional; `dry_run` default `true`). Resposta: `ReparacaoCompradorResultado` com `total_candidatos`, `total_aplicados`, `total_conflitos` e `pares` (cada par com `motivo_skip`: `dry_run`, `multiple_registered` ou `no_orders`). **Não deleta** consumidores guest (histórico append-only). Em modo `apply` (`dry_run=false`) grava um `audit_log` por execução (`acao=reatribuir_comprador_pedidos`) e um `pedido_status_evento` por pedido reatribuído (`tipo_evento=reatribuicao_comprador`, `actor_type=super_admin`). Serviço em `app/services/marketplace_reparacao_comprador_service.py`; teste em `tests/test_marketplace_reparacao_comprador.py`.

**Contrato LojaMarketplace (gestão):** schemas em `app/schemas/marketplace.py`. Campos de vitrine/SEO de conteúdo: `nome_fantasia`, `descricao_curta`, `descricao_longa`, além de `descricao` (legado); campos locais normalizados `categoria_principal`, `cidade_seo`, `estado_seo`; `slug_categoria_cidade` derivado no backend a partir de categoria + cidade. **Sincronização de descrição:** em `PATCH`, se o cliente envia `descricao` ou `descricao_longa`, o backend alinha `descricao` (legado) com a descrição longa (`_sync_loja_descricao_campos` em `app/api/v1/marketplace.py`).

**Rotas HTML (admin — vitrine SEO):** `GET /admin/marketplace-seo-lojas` — apenas Superadministrador (mesmo padrão de verificação de role que `/admin/email`); template `app/templates/admin/marketplace_seo_lojas.html`; consome `GET /api/v1/marketplace/lojas` e `PATCH /api/v1/marketplace/loja/{id}` com `window.authenticatedFetch`. Item de menu no sidebar: **SEO vitrine (lojas)** (somente role Superadministrador).

### Marketing Vitrine — home (`/api/v1/marketing-vitrine`)

Configuração **global** (singleton) e **cards** da home da vitrine (`/loja`): destaques, oferta da semana (Oferta relâmpago) e **oferta em destaque agora**. Schemas em `app/schemas/marketing_vitrine.py`; serviço em `app/services/marketing_vitrine_service.py`.

**Regra de governança (gravada):** Todos os **cards de marketing** da vitrine pública — faixa «Destaques», grade «Ofertas da semana» / Oferta relâmpago, grade «Oferta em destaque agora» e **cabeçalho** (`cabecalho_ofertas` nos blocos `oferta_semana` e `destaque_agora`, parâmetros de preenchimento automático quando não há cards de produto) — são **configurados e parametrizados exclusivamente** pelo **Superadministrador** na rota HTML **`/admin/marketing-vitrine`**, persistidos em `marketing_vitrine_config` e `marketing_vitrine_cards`. **Não** existe outra tela de cadastro de cards nem lista fixa de cards no código como fonte de verdade; Administrador e Cliente Administrador **não** acessam essas APIs (todas usam `require_superadmin`). A home `/loja` pode aplicar **fallback** de listagem (anúncios recentes ou promocionais) quando o payload público não traz itens — ver MAPA_DO_SISTEMA § 12; isso não substitui o cadastro de cards quando se deseja controle editorial.

- **GET** `/marketing-vitrine/vitrine-home` — **Público** (sem auth PDV). Resposta JSON: `config` inclui `mostrar_todos_produtos`, `titulo_ofertas_semana`, `subtitulo_ofertas_semana`, `limite_ofertas_semana`, filtros de ofertas (`ofertas_cliente_ids`, `ofertas_embaralhar`, `ofertas_somente_desconto`), campos equivalentes da seção hero (`titulo_destaque_agora`, `subtitulo_destaque_agora`, `limite_destaque_agora`, `destaque_agora_cliente_ids`, `destaque_agora_embaralhar`, `destaque_agora_somente_desconto`), `ativo`, além de flags de seção (`mostrar_hero_carrossel`, `mostrar_secao_em_alta`, `mostrar_secao_lojas_destaque`) e títulos (`titulo_faixa_destaques`, `titulo_em_alta`, `subtitulo_em_alta`); `destaques`, `ofertas_semana`, `destaque_agora` (itens `livre` ou `anuncio`), `generated_at`. Cabeçalhos: `Cache-Control: no-store`, `Pragma: no-cache`. Limite até 8 itens por bloco; vigência e publicação de anúncio aplicadas no backend.
- **GET** `/marketing-vitrine/config` — Config singleton. **Apenas Superadministrador.**
- **PATCH** `/marketing-vitrine/config` — Body: `MarketingVitrineConfigUpdate` (inclui `destaque_layout`: `carrossel` \| `grade`, `destaque_mostrar_setas`, `destaque_scroll_snap`, `destaque_embaralhar` — embaralha a ordem dos cards da faixa Destaques a cada resposta pública). **Apenas Superadministrador.**
- **GET** `/marketing-vitrine/cards` — Lista cards (query opcional `tipo_bloco`: `destaque` | `oferta_semana` | `destaque_agora`). **Apenas Superadministrador.**
- **GET** `/marketing-vitrine/anuncios-picklist` — Query opcional `q` (busca no título), `limit` (1–500, default 200), `cliente_id` (CA/tenant; pode repetir o parâmetro para filtrar por **vários** clientes), `embaralhar` (`true|false`, ordem aleatória no resultado). Resposta `{ "items": [{ "id", "titulo", "nome_loja" }] }`: anúncios **publicados**, loja **ativa**, com **imagem** válida para vitrine (mesmas regras de `anuncio_id` em POST/PATCH de cards). **Apenas Superadministrador** (uso típico: `/admin/marketing-vitrine`, card tipo «Anúncio»).
- **GET** `/marketing-vitrine/clientes-ca-picklist` — Lista somente **CAs/tenants** com loja marketplace **ativa** (base para filtros do card tipo «Anúncio» no admin). Resposta: `[{ "id", "nome" }]`. **Apenas Superadministrador**.
- **POST** `/marketing-vitrine/cards` — Body: `MarketingVitrineCardCreate` (`tipo_card` livre exige título, imagem e link; `anuncio` exige `anuncio_id` publicável com loja ativa e imagem válida). **Apenas Superadministrador.**
- **PATCH** `/marketing-vitrine/cards/{card_id}` — Body: `MarketingVitrineCardUpdate`. **Apenas Superadministrador.**
- **DELETE** `/marketing-vitrine/cards/{card_id}` — **Apenas Superadministrador** (204).

**Rota HTML (admin):** `GET /admin/marketing-vitrine` — apenas Superadministrador; template `app/templates/admin/marketing_vitrine.html`; consome as APIs acima com `window.authenticatedFetch`. Item de menu no sidebar: **Marketing Vitrine**.

### Marketing Ibix Lançamento — campanha operacional (`/api/v1/marketing/ibix-lancamento`)

Painel operacional da campanha de pré-lançamento (40 dias). Fonte editorial: pasta `MARKETING_ESTRUTURADO/` no repositório. Persistência: `marketing_campanhas`, `marketing_posts` (migrações `me01`, `me02` — guia + copies Bloco A). Router: `app/api/v1/marketing/marketing_ibix_lancamento.py`.

**Governança:** somente **Superadministrador** (`require_superadmin()`). Brand gate marketplace (403 em marcas sem módulo). Sem publicação automática em redes sociais; PATCH altera apenas status operacional (não altera tema/data/legenda/cortes). Bloco A traz `legenda_reels`, `cortes`, `duracao`, `telas_necessarias`; B–D sem roteiro até seed futuro (UI mostra ausência explícita).

- **GET** `/marketing/ibix-lancamento/campanha` — Campanha ativa (`slug=ibix_market_40d`) + resumo (totais, progresso por bloco, post de hoje / próximo pendente; timezone `America/Sao_Paulo`). **404** se campanha ausente.
- **PATCH** `/marketing/ibix-lancamento/campanha` — Body: `proximo_passo` e/ou `status` (`ativa`|`encerrada`).
- **GET** `/marketing/ibix-lancamento/posts` — Query opcional `bloco` (A–D), `status_copy`, `status_publicacao`.
- **GET** `/marketing/ibix-lancamento/posts/{numero}` — Detalhe do post.
- **PATCH** `/marketing/ibix-lancamento/posts/{numero}` — Status copy/produção/publicação, checklist, telas_ok, notas, reuso_origem_numero.

**Rota HTML (admin):** `GET /admin/marketing-ibix-lancamento` — Superadministrador; template `admin/marketing_ibix_lancamento.html`; menu **Marketing Ibix — Lançamento** (com `brand_has_marketplace`).

### Vitrine e consumidor (`/api/v1/loja`)

- **GET** `/loja/auth/social/config` — Retorna apenas client IDs públicos (`google_client_id`, `facebook_app_id`, `apple_client_id`). Sem secrets.
- **POST** `/loja/auth/social/login` — Login/cadastro via provedor social (ex.: Google). Body: `ConsumidorSocialLogin` (provider, `id_token`/`access_token`, `aceite_termos`, etc.). Resposta: autenticado, `pending_link` (vincular a conta existente) ou erro. Rate limit: login loja.
- **POST** `/loja/auth/social/confirm-link` — Confirma vínculo quando o e-mail já existe (consumidor informa senha + `link_token`). Rate limit: login loja.
- **GET** `/loja/categorias` — Lista categorias ativas (público).
- **GET** `/loja/anuncios` — Lista anúncios publicados (categoria_id, loja_slug, q, sort, skip, limit). Ordenação: sort=recent|preco_asc|preco_desc|nome. Filtro estoque: sincronizado com estoque_atual>0; manual com estoque_atual null ou >0. Cache-Control: public, max-age=60. Retorna `frete_formato_efetivo`, `frete_origem_regra`, `frete_gratis`.
- **GET** `/loja/anuncios/{id}` — Detalhe anúncio público. Retorna também `produto_ca_descricao` (descrição do produto em `produtos_cliente`), `categoria_id` (categoria de estoque do produto base) e metadados de frete efetivo (`frete_formato_efetivo`, `frete_origem_regra`, `frete_gratis`).
- **GET** `/loja/anuncios/{anuncio_id}/semelhantes` — Lista anúncios semelhantes por categoria de estoque do produto base, em ordem aleatória. Query: `limit` (1..16, default 8). Exclui o próprio anúncio. Se o produto base não tiver categoria, retorna lista vazia com `motivo="produto_sem_categoria"`.
- **POST** `/loja/cadastro` — Cadastro consumidor (body: ConsumidorCadastro). Sem auth.
- **POST** `/loja/login` — Login consumidor; retorna token e seta cookie `loja_consumidor_token`. Body: ConsumidorLogin (`email`, `senha`, `loja_id` opcional). Quando `loja_id` enviado (carrinho ou URL `?loja_id=`): busca consumidor com `tenant_id == loja.cliente_id`; se não encontrar, fallback para consumidor platform-wide (`tenant_id IS NULL`). Após sucesso, front redireciona para `/`.
- **POST** `/loja/logout` — Remove cookie consumidor.
- **POST** `/loja/forgot-password` — Esqueci minha senha (Loja). Body: `{ "email", "loja_id" (opcional) }`. Resposta genérica. Rate limit: check_forgot_password_rate_limit. Link `/loja/redefinir-senha?token=...`.
- **GET** `/loja/redefinir-senha/valida?token=...` — Valida token redefinição Loja. Response: `{ "valid": true|false }`.
- **POST** `/loja/redefinir-senha` — Redefine senha consumidor. Body: `{ "token", "new_password", "confirm_password" }`. Rate limit: check_reset_password_rate_limit.
- **GET** `/loja/minha-conta` — Dados do consumidor logado. Auth: consumidor.
- **PUT** `/loja/minha-conta` — Atualizar nome/telefone/documento. Auth: consumidor.
- **GET** `/loja/minha-conta/enderecos` — Lista endereços. **POST** `/loja/minha-conta/enderecos` — Criar endereço. Auth: consumidor.
- **GET** `/loja/meus-pedidos` — Lista pedidos do consumidor. Auth: consumidor.
- **GET** `/loja/pedidos/{pedido_id}/timeline` — Timeline unificada (**pedido** + **entrega**) para o comprador autenticado. Golden rule: só retorna se `pedido.comprador_id == consumidor.id`; caso contrário 403. Resposta: `{ pedido_id, entrega_id|null, items[] }` com eventos ordenados por `created_at` (`origem`: `pedido` \| `entrega`; campos `tipo_evento`, `status_codigo`, `status_label`). Fonte: `pedido_status_eventos` + `entrega_eventos`. Auth: consumidor.
- **GET** `/loja/notificacoes` — Inbox do consumidor (`consumidor_notificacoes`): query `offset`, `limit` (1–100). Auth: consumidor.
- **PATCH** `/loja/notificacoes/lidas` — Marca notificações como lidas (`body.ids`). Auth: consumidor.
- **POST** `/loja/pedidos/{pedido_id}/avaliar` — Criar avaliação (nota 1–5, comentário). Apenas comprador do pedido. Auth: consumidor.
- **GET** `/loja/anuncios/{anuncio_id}/avaliacoes` — Lista avaliações do anúncio (público).
- **POST** `/loja/checkout` — Criar pedido: body PedidoCheckoutCreate (loja_id, itens com anuncio_id e quantidade, comprador_nome/email/telefone/documento, endereco_entrega, tipo_entrega, desconto, taxa_entrega, payment_method opcional). Itens agrupados por anuncio_id; valida estoque; **calcula frete por item com precedência `produto > loja` e soma no pedido**; baixa anuncio e produtos_cliente; atualiza loja total_vendas e faturamento_total; insere extrato_loja. Consumidor opcional (get_current_consumidor_optional). **Quando há gateway ativo** para o estabelecimento da loja: reserva estoque, cria checkout no provedor (Mercado Pago) e retorna `redirect_url` na response; a escolha da credencial (plataforma vs CA) segue `empresa.modo_recebimento` da empresa fiscal do dono da loja (ver MAPA_PAGAMENTO § 2.5.1). Response: PedidoCheckoutResponse.
- **POST** `/loja/checkout-unificado` — Carrinho **multi-loja** (modo recebimento **plataforma** obrigatório em todas as lojas participantes): cria **N** pedidos + **uma** `marketplace_checkout_sessions` e **um** pagamento agregado (`external_reference` `mcs:{uuid}`). Recebíveis, billing usage e repasse por CA seguem **rateio por `pedidos_marketplace.tenant_id`** (ver MAPA_DO_SISTEMA § 12 «Checkout unificado… 2026-05-15» e `marketplace_unified_payment_scope.py`). Response: contrato `PedidoCheckoutUnificadoResponse` em `loja.py`.

#### Geolocalização (vitrine pública)
- **GET** `/loja/geo/cidades?q=` — Lista cidades únicas com lojas ativas (autocomplete). Público.
- **GET** `/loja/geo/cidade-proxima?lat=&lng=` — Cidade com loja ativa mais próxima via Haversine. Rate limit: 30/min por IP.
- **GET** `/loja/geo/reverso?lat=&lng=` — Reverse geocoding (Nominatim server-side). Rate limit: 30/min por IP.
- **GET** `/loja/geo/geocodificar?cep=&numero=&complemento=` — **Geocodificação do endereço do consumidor.** `cep` obrigatório; `numero` e `complemento` **opcionais** (UI da vitrine pede só CEP). Usa `geo_service.geocode_address` com cadeia Google Geocoding (se `GOOGLE_MAPS_API_KEY` setada) → BrasilAPI + Nominatim. Quando `numero` não é informado e `geocode_address` não retorna ponto, faz fallback para `geocode_cep` (centro do CEP, `precision=locality`). Cache Redis 30 dias (`geo:addr:{cep}:{numero}`). Quando **`numero` foi informado** e o resultado vem como `locality`, retorna **422** (provável erro de digitação no número). Resposta: `{ lat, lng, precision, cidade, uf, bairro, endereco_formatado, provider }`. **404** quando o CEP não é resolvível por nenhum provedor. Rate limit: 30/min por IP.
- **GET** `/loja/anuncios` — Agora aceita `lat`, `lng`, `geo_cidade`, `geo_uf` opcionais. `sort=proximidade` ordena por distância Haversine SQL. Response inclui `distancia_km`, `cidade_loja`, `uf_loja`.
- **GET** `/loja/anuncios/perto-de-voce?lat=&lng=&limit=12&pool=40` — **"Perto de você" da home: produtos aleatórios ordenados por proximidade real.** Pré-filtra por bounding box (~50 km), seleciona aleatoriamente um pool diverso de anúncios (até 2 por loja), calcula matriz de distância via `routing_service.distance_matrix` (Google Distance Matrix ou OSRM público) e ordena por **duração de rota** (queda para Haversine quando rota indisponível, marcando `rota_estimada=true`). Limites: `limit` 1–24 (default 12), `pool` 5–120 (default 40). Resposta: lista `AnuncioVitrineResponse` com `distancia_rota_km`, `duracao_rota_min`, `rota_estimada`, `bairro_loja`, `distancia_km` (Haversine), `cidade_loja`, `uf_loja`. Cache-Control: public, max-age=60.
- **GET** `/loja/anuncios/proximos?q=&lat=&lng=&limit=20` — **Pós-busca: lojas mais próximas que vendem o produto pesquisado.** `q` obrigatório (busca em `titulo`, `descricao`, `produto.nome`, `produto.codigo`). Agrupa por loja (mantém a melhor oferta por preço/promo dentro de cada loja), faz pré-filtro Haversine (top-N por linha reta) e refina com `routing_service.distance_matrix`. Ordena por **duração de rota** crescente. `limit` 1–30 (default 20). Resposta: mesma estrutura de `perto-de-voce`. Cache-Control: public, max-age=60.

> **Consumo mobile (paridade — `mobile_marketplace/`, 2026-04-27):** os endpoints `geo/cidades`, `geo/cidade-proxima`, `geo/reverso`, `anuncios/perto-de-voce` e `anuncios/proximos` agora também são consumidos pelo app mobile via `services/geoService.ts`, com estado global em `store/geoStore.ts` (MMKV `ibix_geo_location`) e fluxo de permissão em `hooks/useGeo.ts` (Expo Location). UI: `components/geo/{LocationChip,CitySelectorSheet,NearbyAdsCarousel}` integrados em `app/(tabs)/index.tsx` (faixa "Perto de você") e `app/busca.tsx` (faixa "Mais perto de você que vendem isso").

**Schemas:** `app/schemas/marketplace.py` — CategoriaPlataforma, LojaMarketplace, AnuncioPlataforma, ConsumidorCadastro/Login/Response, EnderecoConsumidor, PedidoCheckoutCreate/Response, PedidoMarketplaceResponse/Update, StatusPedidoMarketplaceResponse/Create/Update, ExtratoLojaResponse, AvaliacaoCreate/Response, **AnuncioVitrineResponse** (+ distancia_km, cidade_loja, uf_loja, **bairro_loja, distancia_rota_km, duracao_rota_min, rota_estimada**).

**Referência:** Inventário completo (tabelas, modelos, telas, regra "não duplicar") em MAPA_DO_SISTEMA § 12.

### Notificações (painel CA — sino)

Rotas em `app/api/v1/notificacoes.py`. Autenticação: JWT usuário PDV (`get_current_user`).

- **GET** `/api/v1/notificacoes` — Lista até 80 registros de **`usuario_notificacoes`** do usuário logado (`notificacoes`, `total`, `nao_lidas`). Usado pelo sino do layout CA; marketplace grava entradas quando o pagamento é confirmado (tipo `marketplace_pedido_pago`) — ver MAPA_DO_SISTEMA § 12.
- **POST** `/api/v1/notificacoes/{notificacao_id}/marcar-lido` — Marca como lida (suporta id da `usuario_notificacoes` e compatibilidade com legado `NotificacaoLida`).

---

## Portal Subcliente (rotas HTML e escopo)

- **Rotas HTML:** `GET /portal`, `GET /portal/certificados`, `GET /portal/equipamentos`, `GET /portal/historico`, `GET /portal/downloads`, `GET /portal/minha-conta`. Exigem autenticação e role **Subcliente**; caso contrário 302 para `/login` ou 403.
- **APIs usadas pelo portal:** GET `/api/v1/certificados`, GET `/api/v1/certificados/{id}`, GET `/api/v1/certificados/{id}/pdf`, GET `/api/v1/equipamentos`, GET `/api/v1/agendamentos`, GET `/api/v1/vendas` (e estatísticas) — todos respeitam `ClienteScope` (Subcliente vê apenas o cliente vinculado em `areas_cliente`). Certificado fora do escopo retorna 404.

---

## Autenticação

Todas as rotas (exceto login, refresh e status) requerem autenticação via JWT Bearer Token:

```
Authorization: Bearer <access_token>
```

## Permissões RBAC

As permissões seguem o padrão: `modulo:recurso:acao`

**Exemplos:**
- `certificacao:certificados:criar` - Criar certificado
- `certificacao:certificados:visualizar` - Visualizar certificados
- `certificacao:certificados:aprovar` - Aprovar certificado
- `afericoes:afericoes:criar` - (API removida; permissão legada no BD)
- `certificacao:equipamentos:gerenciar` - Gerenciar equipamentos
- `certificacao:clientes:gerenciar` - Gerenciar clientes

## Níveis Administrativos

1. **SUPER_ADMIN** (Nível 1) - Acesso total
2. **TENANT_ADMIN** (Nível 2) - Administrador do tenant
3. **TENANT_MANAGER** (Nível 3) - Gerente/Gestor
4. **TENANT_OPERATOR** (Nível 4) - Operador/Técnico
5. **TENANT_VIEWER** (Nível 5) - Visualizador

---

## 20. MULTI-BRAND — resolução por Host, guards e escopo brand_id

**Mapa:** [MAPA_MULTIBRAND.md](MAPA_MULTIBRAND.md)

### 20.1 Contexto de request (não é endpoint)

- Middleware `brand_resolution_middleware` popula `request.state.brand` (`BrandContext`) e `request.state.brand_module_slugs`
- Host validado via `brand_domains`; host desconhecido → marca origem (Ibix)

### 20.2 Guards de módulo (marketplace)

Rotas com prefixo vitrine/marketplace exigem módulo `marketplace` no catálogo da marca:

| Prefixo / rota | Guard |
|----------------|-------|
| `/loja`, `/api/v1/loja/*` | `MARKETPLACE_ROUTER_DEPENDENCIES` |
| `/api/v1/marketing-vitrine/*` | idem |
| `/api/v1/marketing/ibix-lancamento/*` | idem |
| `/admin/marketing-ibix-lancamento` | `marketplace_brand_gate_middleware` |
| `/api/v1/marketplace/*` | idem |
| `/negocio/marketplace/*` (HTML) | `marketplace_brand_gate_middleware` |

Marca sem marketplace (ex. Solumática) → **403** JSON/HTML explícito.

### 20.3 Endpoints com `brand_id` implícito ou explícito

| Endpoint | Escopo de marca |
|----------|-----------------|
| `POST /api/v1/auth/login`, cadastro público | Tenant criado com `brand_id_from_request(request, db)` |
| `POST /api/v1/billing/*` (criação tenant CA) | Slug único por `(brand_id, slug)` |
| `GET/POST /api/v1/admin/lgpd/*` | Query/body `brand_id` opcional; default = marca do Host |
| `GET /api/v1/admin/dashboard` | `brand_id` query opcional (origem); derivada força Host; resposta `brand_scope` |
| `GET /api/v1/admin/billing/tenants` | Idem — lista tenants da marca |
| `GET /api/v1/admin/hierarquia` | Árvore filtrada por marca derivada |
| `GET /api/v1/usuarios/` | Superadmin: tenants da marca em host derivado |
| `GET /api/v1/vendas` e demais com `ClienteScope` | Superadmin derivado: `get_cliente_ids_for_brand` via `get_cliente_scope_dep` |
| `GET /api/v1/loja/auth/social/config` | `origin` + `apple_redirect_uri` da origem pública da marca |
| `GET/POST /api/v1/payments/connect/pagbank/*` | `redirect_uri` por `public_origin_from_request()` |

### 20.4 Cookies e CORS

- Cookies de sessão: host-only (`brand_cookie.apply_host_scoped_cookie`) — sem `Domain` compartilhado entre marcas
- CORS: origens de `CORS_ORIGINS` + `brand_domains` ativos ([hardening.py](../app/core/hardening.py))

---

## 21. ENTERPRISE — ciclo de vida do tenant (Fase 9)

**Mapa:** [MAPA_MULTIBRAND.md](MAPA_MULTIBRAND.md) § 13

Prefixo: `/api/v1/admin/tenant-lifecycle` — **Superadministrador** only.

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/tenant/{tenant_id}/status` | Estado (`ativo`, `suspenso`, `bloqueado_billing`); query `brand_id` opcional |
| POST | `/tenant/{tenant_id}/suspend` | Suspende tenant (`ativo=false`); body `motivo`, `brand_id` |
| POST | `/tenant/{tenant_id}/resume` | Reativa tenant |
| POST | `/tenant/{tenant_id}/offboarding` | Offboarding LGPD (`confirmar=true`); retenção fiscal documentada |

LGPD export/offboarding legado: `/api/v1/admin/lgpd/tenant/{id}/*` (mantido).

---

**Última Atualização:** 2026-07-31  
**Versão:** 2.4  
**Status:** Documentação Ativa - Referência Padrão  
**Adições:**
- **Seção 19 – Marketing Ibix Lançamento (2026-07-31):** prefixo `/api/v1/marketing/ibix-lancamento` (Superadmin + brand gate); HTML `/admin/marketing-ibix-lancamento`; tabelas `marketing_campanhas` / `marketing_posts` (me01).
- **Auth + RLS + logout (2026-06-18):** `get_db_pre_auth` no login/cadastro/recuperação de senha; cookies HttpOnly; `POST/GET /logout` com `clear_pdv_auth_cookies`; front `user-dropdown.js` / `certipeso.js` — sessão via cookie, não redirect cego por ausência de token no JS. Ver MAPA_MULTIBRAND § 6.
- **Clientes PII (2026-06-18):** máscara LGPD em listagem; CA com `pii:visualizar` (br36). MAPA_RBAC § 0.14.
- **Seção 20 – Multi-brand (2026-06-18):** resolução por Host, guards marketplace, escopo `brand_id` em auth/billing/LGPD/OAuth/pagamentos; referência MAPA_MULTIBRAND.
- **Seção 19 – Marketplace: timeline consumidor, inbox consumidor e API do sino CA (2026-04-30):** `GET /loja/pedidos/{pedido_id}/timeline`; `GET /loja/notificacoes` e `PATCH /loja/notificacoes/lidas`; nova subseção **Notificações (painel CA)** com `GET`/`POST` `/api/v1/notificacoes`. Detalhe de fluxos Celery e e-mails em MAPA_DO_SISTEMA § 12.
- **Seção 19 – Vitrine: Proximidade real (rota) (2026-04-27):** Novos endpoints públicos `GET /loja/geo/geocodificar` (CEP+número+complemento, precisão `rooftop|range_interpolated|geometric_center`, 404 quando só `locality`), `GET /loja/anuncios/perto-de-voce` (home: aleatórios ordenados por **duração de rota**, pool diverso por loja, queda para Haversine com `rota_estimada=true`) e `GET /loja/anuncios/proximos` (pós-busca: filtra por `q`, agrupa por loja com melhor oferta, ordena por rota real). `AnuncioVitrineResponse` ganha `bairro_loja`, `distancia_rota_km`, `duracao_rota_min`, `rota_estimada`. Backend usa `routing_service.distance_matrix` (Google Distance Matrix → OSRM público → Haversine) com cache Redis 24h por geohash do origem; `geo_service.geocode_address` cobre Google → BrasilAPI+Nominatim com cache 30 dias. Detalhes técnicos em MAPA_DO_SISTEMA § 14.
- **Seção 19 – Marketing Vitrine — regra de governança (2026-03-26):** Texto explícito em MAPA_DE_API: todos os cards da home são cadastrados **somente** pelo Superadmin em `/admin/marketing-vitrine` (sem tela paralela); alinhado a `require_superadmin` nas APIs.
- **Seção 19 – Marketing Vitrine (2026-03-26):** Novo prefixo `/api/v1/marketing-vitrine` — GET público `vitrine-home` (config + destaques + ofertas_semana, `no-store`); CRUD config e cards apenas Superadministrador; HTML `/admin/marketing-vitrine`. Tabelas `marketing_vitrine_config`, `marketing_vitrine_cards` (mv01); **mv02** adiciona flags/títulos de seções da home (hero, em alta, lojas em destaque, faixa destaques); **mv03** (`mv03_mv_sec_defaults`) define `mostrar_secao_em_alta` e `mostrar_secao_lojas_destaque` com default **true** (compatível com a home legada, sem esconder blocos por padrão). **mv04** (`mv04_mv_config_textos`) grava textos padrão no singleton (`titulo_ofertas_semana`, subtítulos, títulos de faixa/em alta). Front vitrine: `getMarketingVitrineHome` em `vitrine.js`; home `/loja` monta blocos a partir da API e do contexto servidor `marketing_vitrine` em `_loja_context`.
- **Seção 19 – Vitrine detalhe e semelhantes (2026-03-26):** `GET /loja/anuncios/{id}` passa a incluir `produto_ca_descricao` e `categoria_id`; novo `GET /loja/anuncios/{anuncio_id}/semelhantes` para recomendações por mesma categoria (aleatório, exclui item atual).
- **Seção 19 – POST /loja/login (2026-03-19):** Body `loja_id` opcional; quando enviado, busca consumidor tenant-scoped primeiro, fallback para platform-wide (`tenant_id IS NULL`); front redireciona para `/` após sucesso.
- **Seção 19 – POST /loja/checkout (2026-03-17):** Quando há gateway ativo, o checkout respeita empresa.modo_recebimento (plataforma = billing MP; direto = config CA). Ver MAPA_PAGAMENTO § 2.5.1.
- **Seção 19 – Marketplace e Loja (Vitrine) (2026-03-07):** Gestão `/api/v1/marketplace` (categorias, loja, anúncios, sync estoque, pedidos, extrato); vitrine `/api/v1/loja` (categorias, anúncios, cadastro/login/logout consumidor, minha-conta, endereços, meus-pedidos, avaliações, checkout). Permissões marketplace; auth consumidor (cookie `loja_consumidor_token`). Ver MAPA_DO_SISTEMA § 12 e MAPA_RBAC módulo marketplace.
- **Hierarquia (2026-02-22):** API `GET /api/v1/admin/hierarquia` (Superadmin only) — árvore completa Tenants → Usuários por role → Vínculos (Admin→Clientes, Admin→CAs, CA→Clientes, CA→Técnicos, Contador→CA). Página HTML `/admin/hierarquia` com visualização interativa (expand/collapse, busca, stats, badges). Link no dashboard admin.
- **Pagamento real fase 1 (2026-02-22):** `/payments/configs` aceita `mercadopago`, `pagbank` e `pagarme`; `/payments/process` com processamento real e `retry_allowed`; `/payments/retry/{transaction_uuid}` para retentativa de transações pendentes/falha; integração operacional nos fluxos de finalização de venda.
- **PagBank OAuth Connect (2026-03-16):** endpoints `/payments/connect/pagbank/start` e `/payments/connect/pagbank/callback` para fluxo OAuth. PagBankProvider e PagarMeProvider reais integrados (charge, refund, get_status). Webhooks implementados para todos os 3 gateways.
- **Pagamento real fase 2 (2026-02-22):** webhook Mercado Pago (`/api/webhooks/mercadopago`) com reconciliação automática de `payment_transactions` e sincronização de `venda_pagamentos` por venda.
- **Pagamento real fase 3 (2026-02-22):** endpoint operacional `/payments/transactions` para listar pendências por estabelecimento e suporte frontend para retentativa direta no módulo `/negocio/pagamentos`.
- **Pagamento real fase 4 (2026-02-22):** `/payments/transactions` com filtros de período + paginação (`skip/limit`); painel de pendências com filtros de status/data, paginação e trava anti-retentativa concorrente.
- **Fase 3+4 (2026-02-20):** Paginação real (`skip`/`limit`, `total`) em: vendas, produtos-cliente, aberturas-caixa, movimentacoes-estoque, ordens-servico. Migration de índices `pp55rr681x1` (vendas, estoque, OS, aberturas, payments). Endpoint público `GET /precos/vigente` (sem auth). Landing `/precos` e página `/planos` com dados do banco.
- **Fase 3 (2026-02-18):** Estabelecimentos fiscais (`/estabelecimentos-fiscais`) CRUD; Venda pagamentos (`/venda-pagamentos`) listar por venda_id, POST, GET por id; Movimentos de caixa (`/movimentos-caixa`) listar por abertura_caixa_id, POST sangria/suprimento, GET por id; Pagamentos (`/payments`) configs (GET/POST), process (POST stub), status (GET por transaction_uuid), webhook (POST por provider_code stub).
- **Fase 2 completa (2026-02-18):** Produtos por estabelecimento (`/produtos-cliente`) CRUD, por-codigo-barras, codigos-barras (GET/POST/DELETE); Movimentações (`/movimentacoes-estoque`) listar e POST entrada/saída/ajuste; Fornecedores (`/fornecedores-cliente`) CRUD. Vendas: itens com `estoque_id` ou `produto_cliente_id`, baixa e estorno em ProdutoCliente quando aplicável.
- **Negócios (2026-02-09):** Seção expandida: Ordens de Serviço (`/ordens-servico`) com `POST /ordens-servico/{ordem_id}/enviar-para-vendas` (cria Venda a partir da OS, 1:1; response `VendaResponse` via ORM); Vendas (`/vendas`) com listagem/GET incluindo `ordem_servico_id`/`ordem_servico_codigo`; schemas `VendaResponse` e `VendaItemResponse` com `from_attributes=True`.
- Seção 13b - Relatórios: `GET /api/v1/relatorios/tendencias-ensaios` (ISO 17025 Fase 3.2)
- Configurações: `GET/PUT /api/v1/configuracoes/politicas-qualidade/` (ISO 17025 Fase 3.1)
- **Autenticação unificada (2026-02-08):** APIs PDV Ibix usam `app.core.middleware.get_current_user` (retorno `Usuario`); proteção e permissões granulares de qualidade documentadas em MAPA_RBAC.md
- Seção 15 - Form Builder adicionada
- **Endpoint responsáveis processo (2026-01-27):** `PATCH /api/v1/processos/{id}/responsaveis` adicionado na Seção 9
- **Segurança/Login (2026-01-28):** cookie `pdv_solumatica_token` (JWT), rate limit de login e docs desabilitadas por padrão. Domínios produção: www.ibix.com.br.
