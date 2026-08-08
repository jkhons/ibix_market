# MAPA RBAC - SISTEMA PDV AUTOMSCALE

## Visão Geral

Este documento é a **fonte única de verdade** sobre o sistema RBAC (Role-Based Access Control) do PDV Ibix, consolidando informações sobre níveis administrativos, papéis organizacionais, permissões e hierarquia.

**Modelo Atual:** Hierárquico — Superadministrador → Administrador → Cliente Administrador → Técnico / Subcliente. Escopo por role (clientes permitidos). Dados e APIs seguem obrigatoriamente essa hierarquia.

**Última Atualização:** 2026-06-18 — **PII LGPD (br36):** § 0.14 — `pii:visualizar` para Cliente Administrador; máscara na API sem corromper banco; roles nativas com reveal. — Anterior 2026-03-03 — **Vínculo Empresa Fiscal e Usuário:** Adicionada seção descrevendo o fluxo de conexão entre empresa fiscal (sem usuário) e usuário (sem empresa fiscal): mesmo Cliente; passos em `/fiscal/empresa` (campo Cliente) e `/usuarios` (clientes vinculados ao Administrador, só Superadmin); Cliente Administrador via cliente_id da empresa = um dos clientes do CA. Referência cruzada com MAPA_DO_SISTEMA.md. — Anterior 2026-03-02: **Funções (Roles) e Permissões apenas Superadministrador:** O card "Funções (Roles) e Permissões" na página `/usuarios` e a rota `/roles` (página e APIs `/api/v1/roles`, `/api/v1/permissoes`) são acessíveis **apenas** por Superadministrador. O Administrador continua acessando `/usuarios` (lista de usuários, Representantes, criar/editar usuários no escopo), mas não vê o card de roles/permissões nem a página `/roles`; ao acessar `/roles` ou as APIs de roles/permissoes recebe 403. — Anterior: 2026-02-18 — **APIs e tabelas removidas (aux_cadastros, qualidade, lacres, historico_selos):** As APIs `/api/v1/aux-cadastros`, `/api/v1/certificados-auxiliares`, `/api/v1/inspetores-aprovadores`, `/api/v1/historico-selos`, `/api/v1/lacres-selos`, `/api/v1/procedimentos-metodo`, `/api/v1/reclamacoes`, `/api/v1/treinamentos-competencia`, `/api/v1/auditorias-internas` e as tabelas correspondentes foram removidas (migration ii88kk914a4). As referências neste mapa a esses módulos/APIs ficam como histórico; rotas HTML e permissões relacionadas (qualidade:*, negocios:lacres) podem ser limpas em sidebar/seeds em tarefa futura. — Anterior: 2026-02-12 — **Portal Cliente Final (Subcliente):** Subcliente **não** acessa Minhas vendas nem Resumo financeiro (migração x34zz247m3v9 remove permissão `negocios.venda:visualizar` da role Subcliente). Rotas `/portal`, `/portal/certificados`, `/portal/equipamentos`, `/portal/informacoes`, `/portal/ordens-servico`, `/portal/notas-fiscais`, `/portal/historico`, `/portal/downloads`, `/portal/minha-conta`; sidebar exclusivo com Informações, Ordens de serviço, Notas fiscais (sem Resumo financeiro nem Minhas vendas). GET ordens-servico e GET notas-servico permitidos com escopo (Subcliente vê por destinatário em notas). APIs de portal: `GET /api/v1/portal/resumo-gastos`, `GET /api/v1/portal/equipamentos/valores-servicos`. Valores por equipamento (concerto, lacre, peças) na página Equipamentos do portal. — Anterior: 2026-02-09 (Portal Subcliente com vendas read-only; d01pp246k7s2). — **Criação de usuário em dois contextos distintos (padrões):** (1) **Clientes** — modal "Criar usuário" na tela Clientes: `POST /api/v1/clientes/{id}/usuarios` cria **sempre** role **Subcliente**, vínculo em **AreaCliente**; acesso: Superadministrador/Administrador ou Cliente Administrador quando `cliente_id` está no escopo (`require_admin_or_ca_scope_para_criar_usuario`). (2) **Minha equipe** — vincular/criar técnico: `POST /api/v1/minha-equipe/tecnicos` cria/vincula **sempre** role **Técnico**, vínculo em **ClienteAdministradorTecnico**; acesso: apenas Cliente Administrador. Sem escolha de função em cada fluxo: lugares distintos, funções distintas. Ver § 0.11 e padrões em § 0.12. — Anterior: 2026-02-08 (Cliente Administrador sem `/usuarios` e `/configuracoes`; E-mail por cliente; Vincular técnico; E-Relatórios).

---

**Configurações WhatsApp:** GET/POST `/api/v1/configuracoes/whatsapp/` são acessíveis **apenas** por usuários com role **Superadministrador** (`require_superadmin()` em `app/api/v1/configuracoes.py`). A seção "Integração WhatsApp" na página `/configuracoes` é exibida somente quando `user_role == 'Superadministrador'` (template `configuracoes/index.html`). A permissão **`configuracoes:whatsapp`** (módulo `configuracoes`, ação `whatsapp`) foi inserida e atribuída **apenas** à role Superadministrador pela migração `a78dd581k6l3_seed_configuracoes_whatsapp_superadmin.py`, de modo que o módulo de configuração do WhatsApp apareça na gestão de Funções e Permissões (`/roles`) para essa role.

---

## 0. HIERARQUIA IMPLEMENTADA (OBRIGATÓRIA)

O sistema e os dados **obrigatoriamente** seguem esta estrutura:

| Nível | Role | Escopo | O que gerencia |
|-------|------|--------|----------------|
| 1 | **Superadministrador** | Tudo | Todos os administradores, todas as roles/permissões, todo o sistema. Único que define "clientes vinculados" de cada Administrador. |
| 2 | **Administrador** | Clientes alocados a ele | Apenas os **clientes** (empresas) cujo ID está em `administrador_clientes` para seu `usuario_id`. Definido pelo Superadmin na tela Usuários (modal edição, seção "Clientes que pode acessar"). Acessa `/usuarios` (lista, Representantes, criar/editar usuários no escopo); **não** acessa o card "Funções (Roles) e Permissões" nem a página `/roles` (apenas Superadministrador). |
| 3 | **Cliente Administrador** | Cliente (Empresa Fiscal) e seus Subclientes | Escopo: clientes em `cliente_administrador_clientes`; técnicos em `cliente_administrador_tecnicos`. **Minha equipe** (`/minha-equipe`, API `/api/v1/minha-equipe/*`): criar Subclientes, listar/adicionar usuários por cliente, vincular/desvincular técnicos; item **Minha equipe** no sidebar aparece **ao final do menu** (apenas para esta role). **Vincular técnico:** se o usuário não existir, cria automaticamente usuário com role Técnico (exige nome e senha); se existir, vincula por email. GET `/minha-equipe/tecnicos/disponiveis` retorna lista vazia. **Sem acesso** a `/usuarios` nem `/configuracoes`. Sidebar: seção "Configurações" (Empresa Fiscal, Emissão NF) e "Gerenciamento de Usuários" só para Superadministrador e Administrador. |
| 4 | **Técnico** | Operações | Escopo de clientes = **clientes do Cliente Administrador** ao qual está vinculado (`cliente_administrador_tecnicos` → `cliente_administrador_clientes`); sem vínculo = não vê nenhum cliente. **Login:** email + senha na mesma tela `/login` (como qualquer usuário). Um técnico pertence a **um único** Cliente Administrador. |
| 5 | **Subcliente** | Um Subcliente | `cliente_id` do token ou `areas_cliente`: um único cliente (Subcliente = cliente da Empresa Fiscal). **Sem acesso** a Minhas vendas nem Resumo financeiro (migração x34zz247m3v9). **Portal Cliente Final** (`/portal`, `/portal/*`): dashboard, certificados, equipamentos, **Informações** (gastos), **Ordens de serviço**, **Notas fiscais**, histórico/agenda, downloads, minha conta; valores por equipamento (concerto, lacre, peças) em `/portal/equipamentos`. Menu restrito (sem cadastros, configurações, usuários). APIs: GET ordens-servico, GET notas-servico (filtro por destinatário), GET vendas/certificados/equipamentos/agendamentos com escopo; GET `/api/v1/portal/resumo-gastos` e `/api/v1/portal/equipamentos/valores-servicos`; POST/PUT/DELETE bloqueados por `forbid_cliente_access`. Um CF não vê dados de outro CF (escopo obrigatório). |

### 0.1 Terminologia – Cliente (Empresa Fiscal) e Subcliente (obrigatório)

Para evitar ambiguidade em toda a documentação e no código:

- **Cliente** = **Empresa Fiscal**. É a empresa que emite notas fiscais, contrata o sistema e é representada pela role **Cliente Administrador**. Cadastro público cria um registro em `clientes` e um usuário com role Cliente Administrador, vinculado em `cliente_administrador_clientes`. O Cliente Administrador pode ter várias Empresas Fiscais (matriz + filiais) em `cliente_administrador_clientes` e gerencia Subclientes e técnicos em **Minha equipe** (`/minha-equipe`).
- **Subcliente** = **Cliente da Empresa Fiscal**. É o destinatário das notas fiscais emitidas pela Empresa Fiscal. Usuário com role **Subcliente** vinculado a um único cliente (via `areas_cliente` ou `cliente_id` no token), **gerenciado pelo Cliente Administrador**. O Cliente Administrador cria e gerencia esses usuários (role Subcliente) em Minha equipe.

**Resumo:** **Cliente** = Empresa Fiscal (emissor de notas); **Subcliente** = Cliente da Empresa Fiscal (destinatário das notas). Role **Cliente Administrador** representa o Cliente; role **Subcliente** representa o Subcliente.

**Uso fiscal:** Na emissão de notas (NF-e, NFC-e, NFS-e), o **emissor** é a Empresa Fiscal (Cliente Administrador) e o **destinatário** é o Subcliente.

**Tabelas de escopo:** `app/core/scope.py` — `get_allowed_cliente_ids()` / `get_cliente_scope()`; `administrador_clientes` (usuario_id, cliente_id); `cliente_administrador_clientes` (usuario_id, cliente_id); `cliente_administrador_tecnicos` (usuario_id_cliente_admin, usuario_id_tecnico). **Vínculo Cliente Administrador → Administrador:** tabela `administrador_cliente_administradores` (usuario_id_administrador, usuario_id_cliente_administrador); cada Cliente Administrador vinculado a no máximo um Administrador; modelo `app/models/administrador_cliente_administrador.py`. **APIs de clientes** e listagens filtram por `ClienteScope.allowed_ids` quando `must_filter_by_cliente()` é verdadeiro. Superadministrador não filtra (`is_superadmin`). Apenas **Superadministrador** pode GET/PUT `/api/v1/usuarios/{id}/clientes-vinculados` (roles: `require_superadmin()`). O vínculo Cliente Administrador ↔ Administrador deve ser gerenciado apenas por Superadministrador (endpoint a definir, espelhando clientes-vinculados).

**Escopo por cliente (módulos com `cliente_id` ou equivalente):** agendamentos (`agendamentos`) — *(tabelas contratos_afericao, afericoes_programadas, comprovantes_afericao removidas)*, vendas (`vendas`), estoque (listagem + estatísticas + alertas), revisões de direção (`revisoes_direcao`) — filtram por `ClienteScope` quando `must_filter_by_cliente()`. **Removidos (2026-02-18):** histórico de selos, reclamações, procedimentos_metodo, auditorias_internas, aux_cadastros, treinamentos_competencia, lacres_selos (APIs e tabelas; migration ii88kk914a4). **Módulo qualidade:** revisoes-direcao permanece; rotas HTML de procedimentos-metodo, treinamentos-competencia, auditorias-internas, reclamacoes e APIs correspondentes foram removidas. **Migrações:** q66rr468e8s2 (cliente_id em qualidade); y34zz236m1v8 (remove usuarios:* da role Cliente Administrador); z45aa347n2w9 (remove configuracoes da role Cliente Administrador). Cliente Administrador **não** acessa `/usuarios` nem `/configuracoes`; gestão em Minha equipe.

### 0.12 Tenant, Estabelecimento e Cliente final (módulo Orçamento e Pedido)

- **Tenant (SaaS):** Tenant = organização que assina planos (`tenants`; `usuarios.tenant_id`). Quem "é" o tenant = tipicamente o **Cliente Administrador**. Estabelecimentos (clientes) não têm tenant_id direto: pertencem ao tenant **via** o CA (tabela `cliente_administrador_clientes`: CA → vários `cliente_id`). Resolução: `resolve_tenant_pagador(db, user_id, role)`; `resolve_tenant_id_from_cliente_id(db, cliente_id)`.
- **Estabelecimento vs. Cliente final:** Na tabela `clientes`: (1) estabelecimento = emissor (orçamento, pedido, NF); (2) cliente final = destinatário. No módulo Orçamento e Pedido: **cliente_id** = sempre estabelecimento (loja que emite); **destinatario_id** (orçamento, opcional) = cliente final (FK `clientes.id`); pedido não tem destinatario_id no model atual.
- **ClienteScope e isolamento:** APIs orçamento/pedido usam listagem por `allowed_ids`, obter por escopo (_orcamento_no_escopo, _pedido_no_escopo), criar com validação de body.cliente_id e body.orcamento_id; produto validado no estabelecimento (ProdutoCliente.cliente_id == body.cliente_id).
- **Permissões:** Pendente criar e atribuir `negocios.orçamento:*`, `negocios.pedido:*` e itens "Orçamentos" e "Pedidos" no sidebar; modelo atual (role_permissoes + ClienteScope) é o correto.
- **forbid_cliente_access:** ROLES_COM_ACESSO_ADMIN = Superadministrador, Administrador, Cliente Administrador. CA, Administrador e Superadministrador podem escrever (criar/editar/emitir/converter orçamento e pedido) dentro do escopo; Subcliente com cliente_id no token é bloqueado nessas rotas.

### 0.13 Multi-brand — gating de módulo por marca

**Mapa:** [MAPA_MULTIBRAND.md](MAPA_MULTIBRAND.md)

Módulos efetivos para o usuário/request = **`brand_modules(marca corrente) ∩ tenant_entitlements ∩ permissões RBAC`**.

| Camada | Verificação |
|--------|-------------|
| Sidebar / menu HTML | `check_html_module_permission` — módulo deve existir no catálogo da marca **e** nas permissões do usuário |
| Rotas HTML vitrine/marketplace | `marketplace_brand_gate_middleware` — paths listados em `app/core/brand_module_gating.py` |
| API marketplace | `MARKETPLACE_ROUTER_DEPENDENCIES`, `assert_marketplace_ibix_brand` |

**Regras:**

- **Solumática:** catálogo `core` apenas — marketplace retorna **403** (HTML e API)
- **Ibix:** `core` + `marketplace`
- Módulos futuros (`certificados`, `calibracao`): bloquear com 403 até implementação real; não simular acesso
- **Sem fallback:** indisponível na marca ≠ redirecionar para Ibix nem ocultar item sem erro

**Contexto de request:** `request.state.brand`, `request.state.brand_module_slugs` (preenchidos no middleware de resolução de marca).

### 0.14 PII — visualização e máscara LGPD (br34/br36)

**Mapas:** [MAPA_DE_API.md](MAPA_DE_API.md) (Clientes), [MAPA_MULTIBRAND.md](MAPA_MULTIBRAND.md) § 6

| Permissão | Módulo | Ação | Quem tem |
|-----------|--------|------|----------|
| `pii:visualizar` | `pii` | `visualizar` | Superadministrador, Administrador; **Cliente Administrador** (br36) |

**Regra de exibição** ([pii_access.py](../app/core/pii_access.py), [pii.py](../app/core/pii.py)):

- Roles **Superadministrador**, **Administrador** e **Cliente Administrador** veem CPF/CNPJ/telefone/e-mail completos na listagem de clientes do tenant (sem depender de permissão explícita).
- Demais roles só veem dados completos com `pii:visualizar` atribuída via `role_permissoes`.
- Sem permissão: API aplica máscara (ex.: CNPJ `**.***.***/****-24`) — **dados no banco não são alterados**.
- Alteração de campos PII exige `pii:visualizar` + registro de auditoria `pii_alteracao_cliente`.

**Migração:** `br36_ca_pii_visualizar` — seed `pii:visualizar` na role Cliente Administrador.

---

## 0. ESPECIFICAÇÃO: ROLES, RBAC, PERMISSÕES E GRUPOS

### 0.1 Roles = Grupos

Não existe tabela **`grupos`** separada. As **roles** (`roles`) funcionam como **grupos de usuários**: cada usuário pertence a **uma** role (`usuarios.role_id` → `roles.id`). No modelo, a tabela `roles` tem o comentário *"grupos de usuários (roles)"*. Portanto, **role = grupo** no PDV Ibix.

### 0.2 Estrutura RBAC (tabelas e relacionamentos)

| Tabela | Descrição |
|--------|-----------|
| **`roles`** | Grupos de usuários (papéis). Campos: `id`, `nome`, `descricao`, `ativo`. |
| **`permissoes`** | Ações do sistema. Campos: `id`, `nome`, `modulo`, `acao`, `descricao`, `ativo`. |
| **`role_permissoes`** | Relação N:N entre roles e permissões. Campos: `id`, `role_id`, `permissao_id`. UNIQUE(`role_id`, `permissao_id`). |
| **`usuarios`** | Usuários. Campo `role_id` (FK → `roles`). |

**Relacionamentos:**
- `usuarios` → `roles` (N:1)
- `roles` ↔ `permissoes` (N:N via `role_permissoes`)

**Componentes:** `app/models/role.py`, `app/models/permissao.py`, `app/models/role_permissao.py`; APIs em `app/api/v1/roles.py`, `app/api/v1/permissoes.py`; middleware em `app/core/middleware.py`.

### 0.3 Formato das permissões

- **`nome`:** Identificador único da permissão. Sugestão: `modulo:recurso:acao` (ex.: `certificacao:certificados:visualizar`, `negocios.venda:visualizar`).
- **`modulo`:** Agrupamento lógico (ex.: `calibracao`, `certificados`, `usuarios`). Usado para filtros, listagem por módulo e verificação de acesso em rotas HTML.
- **`acao`:** Tipo de ação (ex.: `visualizar`, `criar`, `editar`, `gerenciar`).

A API `GET /api/v1/permissoes/agrupadas/modulos` retorna permissões agrupadas por `modulo`. A UI de gestão de roles usa esse agrupamento.

### 0.4 Módulos (grupos lógicos de permissões)

Módulos são os valores de `permissoes.modulo` usados para **controle de acesso em rotas HTML** e **sidebar**. O usuário precisa ter **ao menos uma permissão** com aquele `modulo` para acessar a rota ou ver o item no menu.

**Lista de módulos utilizados no sistema (rotas HTML e sidebar):**

| Módulo | Uso |
|--------|-----|
| `dashboard` | Dashboard principal |
| `clientes` | Clientes |
| `equipamentos` | Equipamentos |
| `agendamentos` | Agendamento *(item sidebar removido; API permanece)* |
| ~~`contratos`~~ | ~~Contratos~~ *(módulo e sidebar removidos)* |
| `certificados` | Certificados (listagem e cadastro) |
| `fiscal.empresa` | Empresa fiscal |
| `fiscal.empresa.ver_cliente` (permissão; módulo `fiscal`) | Visualizar campo Cliente na tela Empresa Fiscal; **atribuída apenas a Administrador e Superadministrador**. Cliente Administrador não vê o campo nem a coluna Cliente; o vínculo é definido automaticamente pelo escopo. Migração `w33xx126m2v8`. |
| `fiscal.notas-fiscais` | Notas fiscais |
| `fiscal` (permissoes: visualizar_documentos, baixar_xml, baixar_pdf, exportar_relatorios) | Área do contador (dashboard fiscal, listagem, downloads XML/PDF, exportações). **UI de notas fiscais** (`/fiscal/notas-fiscais`): botões Baixar XML e Baixar PDF exibidos somente se o usuário tiver `fiscal:baixar_xml` e `fiscal:baixar_pdf` (atributos `data-can-baixar-xml` e `data-can-baixar-pdf` no template, lidos pelo JS). |
| `negocios.venda` | Venda |
| `negocios.estoque` | Estoque |
| `negocios.financeiro` | Financeiro |
| `negocios.ordem-servico` | Ordem de serviço |
| `negocios.lacres-selos` | Lacres e selos *(API e tabelas removidas 2026-02-18)* |
| `termobarohigrometro` | *(permissões removidas 2026-07-16 — legado Certipeso)* |
| `peso` | *(permissões removidas 2026-07-16 — legado Certipeso)* |
| `inspetores` | *(permissões removidas 2026-07-16 — legado Certipeso)* |
| `calibracao` | *(permissões RBAC removidas 2026-07-16; módulo brand reservado futuro Certipeso)* |
| `afericao` | Procedimentos / Aferição |
| `qualidade` | Qualidade ISO 17025: apenas **revisoes-direcao** ativo. *(procedimentos-metodo, treinamentos-competencia, reclamacoes, auditorias-internas removidos 2026-02-18.)* Rotas HTML usam `check_html_module_permission(request, db, "qualidade", ...)` para revisões. |
| `configuracoes` | Configurações |
| `usuarios` | Usuários |
| `form_builder` | Form Builder (Templates de Formulários) |
| `negocios.relatorios:visualizar` (nome da permissão; módulo `negocios`) | Relatórios unificados: sidebar exibe um único item **Relatórios** → `/negocio/relatorios` (para quem tem esta permissão ou `negocios.venda:visualizar`). A rota `/relatorios` redireciona (302) para `/negocio/relatorios`. API `/api/v1/relatorios` (catálogo/jobs) com `require_permission("negocios.relatorios:visualizar")`. Página HTML operacional `/negocio/relatorios` usa módulo `negocios`. Atribuída a Superadministrador, Administrador e Cliente Administrador (migração `rb01_cleanup_permissoes_certipeso`). |
| `auditoria` | *(permissões removidas 2026-07-16 — legado Certipeso)* |
| `certificados` | *(permissões RBAC removidas 2026-07-16; módulo brand reservado futuro Certipeso; não confundir com certificado fiscal A1)* |
| `pdv` | PDV (Ponto de Venda): operar, vendas, estoque_consultar, caixa_fechar, sangria_suprimento. Role **Operador PDV** (migração cc22ee469u8). CRUD de PDVs em `/api/v1/pdvs` usa `forbid_cliente_access` (Super Admin, Admin, CA); escopo por `ClienteScope`. |
| `marketplace` | Marketplace e Vitrine: `marketplace:visualizar`, `marketplace:configurar_loja`, `marketplace:publicar`, `marketplace:gerenciar_pedidos`, `marketplace:financeiro`. Sidebar: **Marketplace** → `/negocio/marketplace` (visível com `marketplace:visualizar`). Vitrine pública em `/loja` e páginas no raiz `/{slug}` e `/categoria/...` (ver MAPA_DO_SISTEMA); auth consumidor via cookie `loja_consumidor_token`. Seed mk02 atribui permissões a Superadministrador, Administrador e Cliente Administrador. **Regras adicionais (2026-05-15):** transporte/frete da loja foi extraído para `app/api/v1/transporte.py`. `PATCH /api/v1/transporte/loja/{loja_id}` requer `marketplace:configurar_loja` + escopo: **CA salva a própria loja**; Superadministrador / Administrador com escopo amplo salva qualquer loja. `PATCH /api/v1/marketplace/loja/{id}` **rejeita** campos de transporte (`formato_frete`, `taxa_entrega_fixa`, `entrega_gratis_apos`, `tipo_entrega`, `raio_entrega_km`) com HTTP 400. Edição de SEO avançado (`seo_title`, `seo_description`, `og_image_url`, `seo_enabled`) continua restrita a Superadministrador. Frete por anúncio/produto continua disponível para CA/Admin/Super via `marketplace:publicar`. CRUD de `LojaAreaEntrega` (POST/PATCH/DELETE em `/api/v1/marketplace/.../areas-entrega`) continua restrito a Superadministrador (`require_superadmin()`); leitura adicional em `/api/v1/transporte/loja/{id}/areas`. **GET** `/api/v1/marketplace/lojas` — apenas Superadministrador. **Sidebar (Superadministrador):** item **SEO vitrine (lojas)** → `/admin/marketplace-seo-lojas` (edição de SEO por loja; não confundir com `/negocio/marketplace`); item **Marketing Vitrine** → `/admin/marketing-vitrine` — **única** tela de **configuração e parametrização de todos os cards** da home da vitrine (Destaques, Ofertas da semana, cabeçalho de ofertas); APIs `/api/v1/marketing-vitrine/*` com `require_superadmin` — **Administrador e Cliente Administrador não** cadastram esses cards. Ver MAPA_DO_SISTEMA § 12 e MAPA_DE_API § 19 (regra de governança). |

Algumas entradas do **sidebar** checam o **nome completo** da permissão (ex.: `negocios.venda:visualizar`, `negocios.ordem-servico:visualizar`) em vez de só o módulo. O `user_permissions` contém **módulos** + **nomes** de permissões (ver 0.6).

### 0.5 Roles utilizadas no código

- **`Superadministrador`:** Acesso total; todas as permissões (get_user_permissions retorna todas); gerencia administradores e clientes vinculados. Uso: `require_superadmin()`; apenas Superadmin pode GET/PUT `usuarios/{id}/clientes-vinculados`. Administrador **não** vê nem edita a role Superadministrador (APIs roles/permissoes filtram ou retornam 403).
- **`Administrador`:** Escopo = clientes em `administrador_clientes`. Acesso a gestão de usuários em `/usuarios` (lista, Representantes, criar/editar usuários no escopo). **Não** acessa o card "Funções (Roles) e Permissões" em `/usuarios` nem a página `/roles`; APIs `GET/POST/PUT/DELETE /api/v1/roles` e `/api/v1/permissoes` exigem **apenas Superadministrador** (`require_superadmin()`). Uso: `require_admin` → `require_role(["Administrador"])`.
- **`Cliente Administrador`:** Cliente do sistema = Empresa Fiscal (emissor de notas). Escopo = clientes em `cliente_administrador_clientes`; gerencia Subclientes e técnicos em **Minha equipe** (`/minha-equipe`, API `/api/v1/minha-equipe/*`). **Não acessa** `/usuarios` nem `/configuracoes` (apenas Superadministrador e Administrador). Vincular técnico: se usuário não existir, cria automaticamente usuário com role Técnico (exige nome e senha); se existir, vincula por email; não vê lista de técnicos de outras organizações.
- **`Técnico`:** Uso: `require_technician` → `require_role(["Administrador", "Técnico"])`. Escopo de clientes = **clientes do Cliente Administrador** ao qual está vinculado (`cliente_administrador_tecnicos` → `cliente_administrador_clientes`); sem vínculo = não vê nenhum cliente. **Login:** email + senha em `/login` (como qualquer usuário). Um técnico pertence a um único Cliente Administrador.
- **`Subcliente`:** Cliente da Empresa Fiscal (destinatário das notas); usuário gerenciado pelo Cliente Administrador; um único cliente (token ou AreaCliente). Uso: `require_client` → `require_role(["Subcliente"])`.
- **`Contador`:** Área do contador (módulo faturamento fiscal). Visão e exportação de documentos fiscais; **não** pode editar/cancelar notas. Permissões: `fiscal:visualizar_documentos`, `fiscal:baixar_xml`, `fiscal:baixar_pdf`, `fiscal:exportar_relatorios`, `clientes:visualizar` (somente leitura). Uso: rotas da área do contador e APIs de download/exportação verificam essas permissões; APIs de PATCH/DELETE e cancelamento de notas devem bloquear role Contador (ou exigir 2FA/aprovação, se definido).
- **`Operador PDV`:** Operação de caixa e vendas no PDV (Plano Hierarquia 5 níveis – Fase 1). Permissões: `pdv:operar`, `pdv:vendas`, `pdv:estoque_consultar`, `pdv:caixa_fechar`, `pdv:sangria_suprimento`. Sem relatórios gerenciais, custos globais ou configurações fiscais. Escopo em `get_allowed_cliente_ids`: lista vazia (operador atua no terminal; vínculo por estabelecimento/CA pode ser estendido depois). CRUD de PDVs (criar/listar/editar terminais) é apenas Administrador ou Cliente Administrador; Operador não acessa `/api/v1/pdvs` de gestão.

Usuário com **AreaCliente** (área do cliente): permissões fixas (dashboard, equipamentos, certificados); sem acesso a clientes/vendas; rotas HTML e APIs bloqueadas conforme `forbid_cliente_access` e escopo.

### 0.6 Verificação de permissões

**Rotas HTML (`main.py`):**  
Para várias páginas, o sistema verifica se o usuário possui **qualquer permissão** com `Permissao.modulo == '<modulo>'` (ex.: `calibracao`, `afericao`, `certificados`) via `check_html_module_permission(request, db, modulo, ...)`. Para controle por permissão específica, usa-se `check_html_permission(request, db, permission_name, ...)` (ex.: `/relatorios` exige `negocios.relatorios:visualizar`).

**Sidebar:**  
O contexto do template recebe `user_permissions`, obtido por `get_user_permissions(user_id, db)`: **lista** que concatena `modulos` (distintos) + `nomes` de permissões da role do usuário. O sidebar usa `'<modulo>' in user_permissions` ou `'<modulo>:<recurso>:<acao>' in user_permissions` conforme o item (ver `app/templates/components/sidebar.html`).

**Relatórios (unificado):** O sidebar exibe um único item **Relatórios** (→ `/negocio/relatorios`) para usuários com `negocios.relatorios:visualizar` ou `negocios.venda:visualizar`. A rota `/relatorios` redireciona para `/negocio/relatorios`. **Subcliente** não vê Minhas vendas; utiliza apenas o Portal (Informações, Ordens de serviço, Notas fiscais). **Resumo financeiro** foi removido do sidebar (antes apontava para `/negocio/dashboard`).

**APIs:**  
- Por **role:** `require_admin`, `require_technician`, `require_client` checam o **nome** da role.  
- Por **permissão:** `require_permission(required_permission)` verifica `Permissao.nome == required_permission` (via `role_permissoes`).

### 0.7 APIs de gestão (roles e permissões)

- **Roles:** `GET/POST /api/v1/roles`, `GET/PUT/DELETE /api/v1/roles/{id}`. Exigem **apenas Superadministrador** (`_ensure_superadmin_only` em `app/api/v1/roles.py`). Administrador recebe 403 ao chamar essas APIs.
- **Permissões:** `GET/POST /api/v1/permissoes`, `GET/PUT/DELETE /api/v1/permissoes/{id}`; `GET /api/v1/permissoes/modulo/{modulo}`; `GET /api/v1/permissoes/agrupadas/modulos` (opcional `role_id`); `GET/PUT /api/v1/permissoes/role/{role_id}`. Exigem **apenas Superadministrador** (`require_superadmin()` em `app/api/v1/permissoes.py`). Administrador recebe 403.
- **Clientes vinculados ao Administrador:** `GET/PUT /api/v1/usuarios/{usuario_id}/clientes-vinculados`. **Apenas Superadministrador** (`require_superadmin()`). Define quais clientes o Administrador pode acessar (tabela `administrador_clientes`).
- **Cliente Administrador vinculado a Administrador:** Tabela `administrador_cliente_administradores` (usuario_id_administrador, usuario_id_cliente_administrador). Cada Cliente Administrador vinculado a no máximo um Administrador. Apenas Superadministrador pode definir/alterar esse vínculo (endpoint a definir, espelhando clientes-vinculados).

**Referências:** `Scripts_auxiliares/RBAC_COMPLETO.md` (roles implementadas e propostas, seeds); `MAPA_DO_BANCO_DE_DADOS.md` (tabelas `roles`, `permissoes`, `role_permissoes`).

### 0.8 Resumo – Grupos

- **Grupos de usuários:** As **roles** são os grupos. Cada usuário pertence a uma role. Não há tabela `grupos` separada.
- **Grupos de permissões:** Os **módulos** (`permissoes.modulo`) agrupam permissões. A UI e as rotas HTML usam o módulo para “acesso a este conjunto de funcionalidades” (ex.: tudo que depende de `calibracao`).

### 0.9 Permissões MVP Emissão de Certificados

Permissões específicas do módulo de emissão (Calibração → Certificado → PDF → Entrega). Criadas pela migração `h2i3j4k5l6m7_permissoes_certificados_mvp`. Módulo `certificados`; mapear para roles conforme matriz atual.

| nome | descricao | modulo | acao |
|------|-----------|--------|------|
| `certificados:emitir` | Emitir certificados por processo/balança | certificados | emitir |
| `certificados:gerar_pdf` | Enfileirar geração de PDF | certificados | gerar_pdf |
| `certificados:enviar_email` | Enviar certificado por e-mail | certificados | enviar_email |
| `certificados:cancelar` | Cancelar certificado (motivo obrigatório) | certificados | cancelar |
| `certificados:reemitir` | Reemitir (novo número, histórico) | certificados | reemitir |
| `certificados:baixar` | Baixar PDF | certificados | baixar |
| `certificados:exportar` | Exportar JSON/XML | certificados | exportar |

---

## 0.10 Inventário de Permissões por API e Mapeamento Endpoint → Permissão

**Objetivo:** Listar todos os endpoints que usam `require_permission` e garantir que cada permissão exista na tabela `permissoes` e em seeds/migrations. Manter esta seção atualizada ao adicionar novos endpoints.

### Permissões usadas na API (require_permission)

| Módulo API | Permissão | Endpoint(s) | Migration/Seed |
|------------|-----------|-------------|----------------|
| email_cliente | `email_cliente` | GET/POST router | b67cc569p4y1 |
| usuarios | `usuarios:visualizar` | GET /, GET /{id} | l11nn913h8o2, p55rr357j2s6 |
| usuarios | `usuarios:criar` | POST / | idem |
| usuarios | `usuarios:editar` | PUT /{id} | idem |
| usuarios | `usuarios:excluir` | DELETE /{id} | idem |
| certificados | `certificados:emitir` | POST emitir | h2i3j4k5l6m7 (MVP) |
| certificados | `certificados:baixar` | GET baixar PDF | idem |
| notas_fiscais / notas_servico | `fiscal:baixar_xml` | GET XML | t99uu791h9q3 |
| notas_fiscais / notas_servico | `fiscal:baixar_pdf` | GET PDF | t99uu791h9q3 |
| fiscal_relatorios | `fiscal:exportar_relatorios` | Router | t99uu791h9q3 |
| *(treinamentos_competencia removido 2026-02-18)* | - | - | - |
| *(procedimentos_metodo removido 2026-02-18)* | - | - | - |
| revisoes_direcao | `qualidade:revisoes_direcao:*` | CRUD | i88kk680e5l9 |
| *(auditorias_internas removido 2026-02-18)* | - | - | - |
| acoes_corretivas | `qualidade:acoes_corretivas:*` | CRUD | h77jj579d4k8 |
| *(reclamacoes removido 2026-02-18)* | - | - | - |
| auth | `usuarios:visualizar` | GET /me (perfil) | l11nn913h8o2 |
| clientes | `clientes:visualizar` | GET /, GET /todos, GET /{id}, GET buscar/cnpj | p55rr357j2s6 |
| clientes | `clientes:criar` | POST / | p55rr357j2s6 |
| clientes | `clientes:editar` | PUT /{id} | p55rr357j2s6 |
| clientes | `clientes:excluir` | DELETE /{id} | p55rr357j2s6 |
| equipamentos | `equipamentos:visualizar` | GET /, GET /{id}, GET /estatisticas | p55rr357j2s6 |
| equipamentos | `equipamentos:criar` | POST / | p55rr357j2s6 |
| equipamentos | `equipamentos:editar` | PUT /{id} | p55rr357j2s6 |
| equipamentos | `equipamentos:excluir` | DELETE /{id} | p55rr357j2s6 |
| *(APIs afericoes e contratos_afericao removidas; tabelas droppadas)* | - | - | - |
| agendamentos | `agendamentos:visualizar` | GET /agendamentos, GET /agendamentos/estatisticas, GET /{id} | p55rr357j2s6 |
| agendamentos | `agendamentos:criar` | POST /agendamentos | p55rr357j2s6 |
| agendamentos | `agendamentos:editar` | PUT /{id} | p55rr357j2s6 |
| agendamentos | `agendamentos:excluir` | DELETE /{id} | p55rr357j2s6 |
| estoque | `negocios:visualizar` | GET "", GET /categorias, GET /alertas, GET /estatisticas, GET /{id} | p55rr357j2s6 |
| estoque | `negocios:criar` | POST "" | p55rr357j2s6 |
| estoque | `negocios:editar` | PATCH /{id} | p55rr357j2s6 |
| estoque | `negocios:excluir` | DELETE /{id} | p55rr357j2s6 |
| *(lacres_selos API removida 2026-02-18)* | - | - | - |
| relatorios | `negocios.relatorios:visualizar` | Router E-Relatórios (catálogo, jobs, download); sidebar Relatórios | rb01_cleanup_permissoes_certipeso |

### 0.11 Criação de usuário em dois contextos distintos (Clientes x Minha equipe)

Dois fluxos criam usuários sob o Cliente Administrador (ou Admin), com **lugar e função distintos**; em cada um a role é **fixa** (sem seletor de função na UI).

| Aspecto | **Clientes** — modal "Criar usuário" | **Minha equipe** — vincular/criar técnico |
|--------|--------------------------------------|------------------------------------------|
| **Onde** | Tela Clientes → botão "Criar usuário" no cliente | Tela Minha equipe → vincular/criar técnico |
| **API** | `POST /api/v1/clientes/{cliente_id}/usuarios` | `POST /api/v1/minha-equipe/tecnicos` |
| **Role criada** | **Subcliente** (sempre) | **Técnico** (sempre) |
| **Vínculo** | **AreaCliente** (usuário ↔ cliente) | **ClienteAdministradorTecnico** (técnico ↔ CA) |
| **Quem pode** | Superadministrador, Administrador ou Cliente Administrador (quando cliente no escopo) | Apenas Cliente Administrador |
| **Uso** | Usuário que acessa dados **daquele cliente** (subcliente) | Técnico que opera na **equipe do CA** (vê clientes do CA) |

- **Clientes:** `app/api/v1/clientes.py` → `criar_usuario_cliente`; `app/services/usuario_service.py` → `UsuarioService.criar_usuario_cliente` (sempre role Subcliente, cria registro em `areas_cliente`).
- **Minha equipe:** `app/api/v1/minha_equipe.py` → `vincular_tecnico` / `adicionar_usuario_sub_cliente`; técnicos via `ClienteAdministradorTecnico`; usuários Subcliente por cliente via `POST /minha-equipe/clientes/{cliente_id}/usuarios` (também role Subcliente + AreaCliente, mas rota exclusiva da área Minha equipe).

### 0.12 Padrões usados (criação de usuário e escopo)

- **Clientes — POST /clientes/{id}/usuarios**
  - **Autorização:** `forbid_cliente_access` + dependência customizada `require_admin_or_ca_scope_para_criar_usuario(cliente_id)`.
  - **Regra:** Superadministrador/Administrador passam; Cliente Administrador só se `cliente_id in scope.allowed_ids` (senão 403 "Cliente fora do seu escopo").
  - **Serviço:** `UsuarioService.criar_usuario_cliente` — sempre resolve role "Subcliente", cria usuário e `AreaCliente` (nome_area `visualizador`). Não usa `require_permission` (acesso por role + escopo).
- **Minha equipe — POST /minha-equipe/tecnicos**
  - **Autorização:** router com `dependencies=[Depends(require_cliente_administrador())]`; escopo implícito (CA só gerencia sua equipe).
  - **Regra:** Se usuário não existe, cria com role Técnico (exige nome e senha); se existe, exige que já seja Técnico; vínculo em `ClienteAdministradorTecnico`.
- **Escopo:** `get_cliente_scope_dep` + `ClienteScope.allowed_ids` / `must_filter_by_cliente()`; para CA, `allowed_ids` vem de `cliente_administrador_clientes`.
- **Nomes de role no código:** "Superadministrador", "Administrador", "Cliente Administrador", "Técnico", "Subcliente" (evitar hardcode em muitos pontos; este endpoint de clientes/usuarios usa dependência dedicada por requisito de escopo por cliente).

### APIs protegidas apenas por role (sem require_permission)

Estas APIs usam `forbid_cliente_access`, `require_admin`, `require_superadmin_or_admin`, `require_admin_or_ca_scope_para_criar_usuario` (clientes) ou `get_current_user` sem verificação de permissão granular: processos_v1, notificacoes, form_builder, vendas, ordens_servico, whatsapp, configuracoes, minha_equipe, empresa, roles, permissoes, mdfe, cupons_fiscais, tipo_equipamento, ensaios, templates_contratos, dashboard_negocios, help_center, billing. *(APIs certificados_auxiliares, aux_cadastros, historico_selos, inspetores_aprovadores removidas 2026-02-18.)* **Clientes:** GET/PUT/DELETE usam `require_permission("clientes:*")`; exceção: `POST /clientes/{id}/usuarios` usa role + escopo (§ 0.11, 0.12). (Agendamentos, estoque usam require_permission; ver tabela acima.)

**Regra ao adicionar novo endpoint:** Se o recurso tiver ações distintas (visualizar/criar/editar/excluir), usar `require_permission("modulo:acao")` e garantir que a permissão exista em `permissoes` (migration/seed) e esteja atribuída às roles corretas.

---

## 1. Níveis Administrativos (Modelo Base — Referência Teórica)

**Nota:** Os níveis abaixo (SUPER_ADMIN, TENANT_ADMIN, etc.) são **referência teórica**. A **implementação em produção** usa os **nomes em português** das roles: **Superadministrador**, **Administrador**, **Cliente Administrador**, **Técnico**, **Subcliente** (ver Seção 0). O código e as tabelas (`roles.nome`) usam exclusivamente esses nomes.

O PDV Ibix utiliza uma hierarquia de roles baseada em níveis numéricos que formam a base do controle de acesso:

### Hierarquia de Níveis

1. **SUPER_ADMIN** (Nível 1)
   - Acesso total ao sistema
   - Gerenciamento de todos os tenants
   - Configurações globais
   - Único nível que ultrapassa limites de tenant

2. **TENANT_ADMIN** (Nível 2)
   - Administrador do tenant
   - Gerenciamento de usuários do tenant
   - Configurações do tenant
   - Gestão de níveis e permissões dentro do tenant

3. **TENANT_MANAGER** (Nível 3)
   - Gerente/Gestor
   - Gerenciamento de processos
   - Aprovações e validações
   - Acesso a dashboards e relatórios gerenciais

4. **TENANT_OPERATOR** (Nível 4)
   - Operador/Técnico
   - Criação de certificados e aferições
   - Execução de operações
   - Visualização de dados

5. **TENANT_VIEWER** (Nível 5)
   - Visualizador
   - Apenas leitura
   - Sem modificações
   - Acesso restrito a visualização de dados e relatórios

### Fluxo de Permissões

```
┌─────────────────┐
│   SUPER_ADMIN   │ ← Acesso total, pode tudo
└────────┬────────┘
         │
┌────────▼────────┐
│  TENANT_ADMIN   │ ← Gerencia usuários, configurações do tenant
└────────┬────────┘
         │
┌────────▼────────┐
│ TENANT_MANAGER  │ ← Gestor (aprovar, validar, relatórios)
└────────┬────────┘
         │
┌────────▼────────┐
│TENANT_OPERATOR  │ ← Operador (criar certificados, aferições)
└────────┬────────┘
         │
┌────────▼────────┐
│ TENANT_VIEWER   │ ← Apenas visualização
└─────────────────┘
```

---

## 2. Mapeamento de Perfis Funcionais

### 2.1 Operador/Técnico (Cria Certificados e Aferições)

**Nível RBAC Base:** `TENANT_OPERATOR` (nível 4)

#### Permissões CORRETAS

✅ **DEVE TER:**
- `certificacao:certificados:criar` - Criar novo certificado
- `certificacao:certificados:visualizar` - Visualizar certificados
- `certificacao:certificados:editar` - Editar certificados
- `afericoes:afericoes:criar` - Criar nova aferição
- `afericoes:afericoes:visualizar` - Visualizar aferições
- `afericoes:afericoes:editar` - Editar aferições
- `certificacao:equipamentos:visualizar` - Ver equipamentos
- `certificacao:clientes:visualizar` - Ver clientes

❌ **NÃO DEVE TER:**
- `certificacao:certificados:aprovar` - Aprovar certificados (apenas gestores)
- `certificacao:certificados:deletar` - Deletar certificados (apenas gestores)
- `certificacao:equipamentos:gerenciar` - Gerenciar equipamentos (apenas gestores)
- `certificacao:clientes:gerenciar` - Gerenciar clientes (apenas gestores)
- `negocios.relatorios:visualizar` - Relatórios (Superadministrador, Administrador e Cliente Administrador; Técnico/Operador não têm)

**Funcionalidades:**
- Criar certificados através de processo de aferição
- Registrar dados técnicos e condições ambientais
- Realizar ensaios (excentricidade, mobilidade)
- Visualizar histórico de certificados
- Editar certificados em rascunho

**API Endpoints:**
- `POST /api/v1/certificados/` - Criar certificado
- `GET /api/v1/certificados/` - Listar certificados
- `PUT /api/v1/certificados/{id}` - Atualizar certificado
- *(APIs afericoes e contratos_afericao removidas; tabelas droppadas)*

**Restrições:**
- Não pode aprovar certificados
- Não pode deletar certificados
- Não pode gerenciar equipamentos ou clientes
- Não tem acesso a relatórios gerenciais

---

### 2.2 Gestor/Manager (Aprova e Valida)

**Nível RBAC Base:** `TENANT_MANAGER` (nível 3)

#### Permissões CORRETAS

✅ **DEVE TER:**
- `certificacao:dashboard:visualizar` - Acessar dashboard com KPIs
- `certificacao:certificados:visualizar` - Ver todos os certificados
- `certificacao:certificados:aprovar` - Aprovar certificados
- `certificacao:certificados:validar` - Validar certificados
- `certificacao:certificados:editar` - Editar qualquer certificado
- `certificacao:certificados:deletar` - Deletar certificados
- `certificacao:equipamentos:visualizar` - Ver todos os equipamentos
- `certificacao:equipamentos:gerenciar` - Criar/editar equipamentos
- `certificacao:clientes:visualizar` - Ver todos os clientes
- `certificacao:clientes:gerenciar` - Criar/editar clientes
- `negocios.relatorios:visualizar` - Acessar relatórios (E-Relatórios; mesma permissão para Cliente Administrador)
- *(Permissões afericoes legadas; API removida - usar contratos/agendamentos)*

**Funcionalidades:**

**Dashboard e Visão Geral:**
- KPIs principais (total certificados, vencendo, vencidos)
- Gráficos de certificados por status
- Alertas de certificados próximos ao vencimento

**Aprovação e Validação:**
- Aprovar certificados criados por operadores
- Validar dados técnicos e ensaios
- Rejeitar certificados com problemas
- Assinar digitalmente como aprovador

**Gestão:**
- Gerenciar equipamentos e clientes
- Configurar tipos de equipamento
- Gerenciar inspetores e aprovadores
- Configurar templates de certificados

**Relatórios:**
- Relatórios de certificados emitidos
- Análise de vencimentos
- Estatísticas de aferições
- Exportação (PDF/Excel)

**API Endpoints:**
- `GET /api/v1/certificacao/dashboard` - Dashboard com KPIs
- `POST /api/v1/certificados/{id}/aprovar` - Aprovar certificado
- `POST /api/v1/certificados/{id}/validar` - Validar certificado
- `GET /api/v1/certificacao/relatorios/*` - Todos os relatórios

**Restrições:**
- Não pode criar novos usuários (apenas TENANT_ADMIN)
- Não pode alterar configurações do sistema
- Não tem acesso a outros tenants

---

### 2.3 Administrador (Gerencia Sistema)

**Nível RBAC Base:** `TENANT_ADMIN` (nível 2)

#### Permissões CORRETAS

✅ **DEVE TER:**
- `certificacao:*` - Todas as permissões de certificação
- `afericoes:*` - (API removida; permissões legadas no BD)
- `configuracoes:usuarios:gerenciar` - Gerenciar usuários
- `configuracoes:roles:gerenciar` - Gerenciar roles
- `configuracoes:permissoes:gerenciar` - Gerenciar permissões
- `configuracoes:sistema:configurar` - Configurar sistema

**Funcionalidades:**
- Gerenciar todos os usuários do tenant
- Atribuir roles e permissões
- Configurar sistema (email, templates, etc.)
- Acesso total aos módulos de certificação

---

## 3. Estrutura de Permissões

### 3.1 Formato de Permissões

**Padrão:** `modulo:recurso:acao`

**Exemplos:**
- `certificacao:certificados:criar` - Criar certificado
- `certificacao:certificados:visualizar` - Visualizar certificados
- `certificacao:certificados:editar` - Editar certificado
- `certificacao:certificados:aprovar` - Aprovar certificado
- `certificacao:certificados:deletar` - Deletar certificado
- `afericoes:afericoes:criar` - (API removida; legado)
- `afericoes:afericoes:visualizar` - (API removida; legado)
- `certificacao:equipamentos:visualizar` - Visualizar equipamentos
- `certificacao:equipamentos:gerenciar` - Gerenciar equipamentos
- `certificacao:clientes:visualizar` - Visualizar clientes
- `certificacao:clientes:gerenciar` - Gerenciar clientes
- `negocios.relatorios:visualizar` - Visualizar relatórios

### 3.2 Verificação de Permissões

**Processo:**
1. Extração do usuário do token JWT
2. Busca do nível administrativo
3. Busca de permissões específicas
4. Verificação de escopo (global/tenant/user)
5. Verificação de hierarquia (se aplicável)
6. Autorização ou negação

---

## 4. Permissões por Módulo

### 4.1 Módulo de Certificação

**Recursos:**
- `certificados` - Certificados de calibração
- `certificados_auxiliares` - Certificados auxiliares
- `certificados_pesos` - Certificados de pesos padrão
- `equipamentos` - Equipamentos
- `clientes` - Clientes
- `tipo_equipamento` - Tipos de equipamento

**Ações:**
- `criar` - Criar novo recurso
- `visualizar` - Visualizar recursos
- `editar` - Editar recursos
- `deletar` - Deletar recursos
- `aprovar` - Aprovar certificados
- `validar` - Validar certificados
- `gerenciar` - Gerenciar recursos (CRUD completo)

### 4.2 Módulo de Aferições / Contratos

> **Atualização (fev/2025):** APIs `/api/v1/afericoes` e `/api/v1/contratos-afericao` **removidas**. Tabelas `afericoes_programadas`, `comprovantes_afericao`, `contratos_afericao` droppadas (migration hh77jj803z3). Sidebar: itens Contratos e Agendamento removidos.

**Recursos (ativos):**
- `agendamentos` - Agendamentos (sem vínculo a contratos)
- `ensaios` - Ensaios técnicos
- `processos` - Processos de certificação

**Ações:**
- `criar` - Criar novo contrato/agendamento/ensaio/processo
- `visualizar` - Visualizar recursos
- `editar` - Editar recursos
- `deletar` - Deletar recursos
- `gerenciar` - Gerenciar recursos (CRUD completo)

### 4.3 Módulo de Configurações

**Recursos:**
- `usuarios` - Usuários
- `roles` - Roles (papéis)
- `permissoes` - Permissões
- `sistema` - Configurações do sistema
- `inspetores_aprovadores` - Inspetores e aprovadores

**Ações:**
- `visualizar` - Visualizar recursos
- `gerenciar` - Gerenciar recursos (CRUD completo)
- `configurar` - Configurar sistema

### 4.4 Módulo de Form Builder

**Módulo:** `form_builder`

**Permissões disponíveis:**
- `form_builder:render` - Renderizar formulário a partir de template
- `form_builder:templates:visualizar` - Visualizar templates de formulários
- `form_builder:templates:gerenciar` - Criar, editar e deletar templates
- `form_builder:validate` - Validar dados de formulário

**Uso:**
- Renderização de formulários dinâmicos para processos, aferições, certificados
- Gerenciamento de templates JSON
- Validação de dados de formulários

**Referências:** Ver `MAPA_DE_API.md` Seção 15 para documentação completa da API.

---

## 5. Matriz de Permissões

### Resumo de Permissões por Nível

| Permissão | Operador | Gestor | Admin | Notas |
|-----------|----------|--------|-------|-------|
| `certificacao:certificados:criar` | ✅ | ✅ | ✅ | Todos podem criar |
| `certificacao:certificados:visualizar` | ✅ (próprios) | ✅ (todos) | ✅ (todos) | Filtro automático por nível |
| `certificacao:certificados:editar` | ✅ (próprios) | ✅ (todos) | ✅ (todos) | Operador edita só seus |
| `certificacao:certificados:aprovar` | ❌ | ✅ | ✅ | Apenas gestores e admin |
| `certificacao:certificados:deletar` | ❌ | ✅ | ✅ | Apenas gestores e admin |
| `certificacao:equipamentos:visualizar` | ✅ | ✅ | ✅ | Todos podem visualizar |
| `certificacao:equipamentos:gerenciar` | ❌ | ✅ | ✅ | Apenas gestores e admin |
| `certificacao:clientes:visualizar` | ✅ | ✅ | ✅ | Todos podem visualizar |
| `certificacao:clientes:gerenciar` | ❌ | ✅ | ✅ | Apenas gestores e admin |
| `negocios.relatorios:visualizar` | ❌ | ✅ | ✅ | Superadministrador, Administrador e Cliente Administrador (E-Relatórios) |
| `afericoes:*` (API removida) | - | - | - | Legado; usar contratos/agendamentos |
| `configuracoes:usuarios:gerenciar` | ❌ | ❌ | ✅ | Apenas admin |
| `configuracoes:roles:gerenciar` | ❌ | ❌ | ✅ | Apenas admin |
| `configuracoes:permissoes:gerenciar` | ❌ | ❌ | ✅ | Apenas admin |

---

## 6. Verificações de Segurança Implementadas

### 1. Endpoints Protegidos
- ✅ Todas as rotas de certificação requerem autenticação
- ✅ Validação de permissões em todas as operações
- ✅ Filtros automáticos por nível de acesso

### 2. Páginas HTML Protegidas
- ✅ `/certificacao/*` - Requer autenticação
- ✅ `/certificacao/certificados` - Requer `certificacao:certificados:visualizar`
- ✅ `/certificacao/equipamentos` - Requer `certificacao:equipamentos:visualizar`
- ✅ `/certificacao/clientes` - Requer `certificacao:clientes:visualizar`
- ✅ `/certificacao/configuracoes` - Requer `configuracoes:sistema:configurar`

### 3. Validações Backend
- ✅ Verificação de permissões antes de operações
- ✅ Validação de escopo (tenant, usuário)
- ✅ Validação de hierarquia (não pode aprovar próprio certificado)

---

## 7. Exemplos de Uso e Configuração

### Exemplo 1: Configurando um Operador

**Usuário:** João Silva - Técnico de Calibração

**Nível RBAC:** `TENANT_OPERATOR`

**Permissões Específicas:**
```
certificacao:certificados:criar
certificacao:certificados:visualizar
certificacao:certificados:editar
contratos:visualizar (aferições via contratos/agendamentos)
certificacao:equipamentos:visualizar
certificacao:clientes:visualizar
```

**Resultado:** João pode criar certificados, realizar aferições, mas não pode aprovar ou gerenciar equipamentos/clientes.

---

### Exemplo 2: Configurando um Gestor

**Usuário:** Maria Santos - Gerente de Certificação

**Nível RBAC:** `TENANT_MANAGER`

**Permissões:**
```
certificacao:dashboard:visualizar
certificacao:certificados:visualizar
certificacao:certificados:aprovar
certificacao:certificados:validar
certificacao:certificados:editar
certificacao:certificados:deletar
certificacao:equipamentos:visualizar
certificacao:equipamentos:gerenciar
certificacao:clientes:visualizar
certificacao:clientes:gerenciar
negocios.relatorios:visualizar
contratos:visualizar (aferições via contratos/agendamentos)
```

**Resultado:** Maria tem acesso completo ao módulo de certificação, pode aprovar certificados, gerenciar equipamentos e clientes, mas não pode criar usuários.

---

## 8. Status de Implementação e Guia de Desenvolvimento

### Status Geral: Atualizado (2026-02-08)

**✅ Implementado:**
- ✅ Banco de dados RBAC completo (5 roles, permissões incluindo módulo qualidade)
- ✅ Autenticação JWT funcional (HS256, bcrypt)
- ✅ **Autenticação unificada:** APIs PDV Ibix usam `app.core.middleware.get_current_user` (retorno `Usuario`); migração concluída a partir de `app.core.auth.get_current_user` (dict)
- ✅ **Proteção de rotas:** Maioria das APIs com `Depends(get_current_user)` e, onde aplicável, `require_permission(...)` e `forbid_cliente_access` no router
- ✅ **APIs de qualidade:** Reclamações, ações corretivas, auditorias internas, revisões direção, procedimentos-metodo, treinamentos-competencia com `get_current_user` + `require_permission("qualidade:<recurso>:<acao>")` (visualizar/criar/editar/excluir)
- ✅ **Rotas HTML qualidade:** Uso de `check_html_module_permission(request, db, "qualidade", ...)` (incluindo `/reclamacoes`). Página `/reclamacoes` permite Cliente Administrador (bloqueio só quando `cliente_id` no token e role fora de `ROLES_COM_ACESSO_ADMIN`).
- ✅ **Certificados auxiliares (aux_cadastros):** Todas as operações (listagem, criar, obter, atualizar, excluir, inspetores-aprovadores, arquivos) escopadas por `responsavel_id == current_user.id`; usuário vê apenas seus cadastros.
- ✅ **Relatórios (unificado):** Um único item **Relatórios** no sidebar → `/negocio/relatorios`; visível para quem tem `negocios.relatorios:visualizar` ou `negocios.venda:visualizar`. Rota `/relatorios` redireciona (302) para `/negocio/relatorios`. API `/api/v1/relatorios` com `require_permission("negocios.relatorios:visualizar")`.
- ✅ Seed de permissões granulares do módulo qualidade (qualidade:reclamacoes:*, qualidade:acoes_corretivas:*, etc.) associadas a Superadministrador e Administrador
- ✅ Modelos e relacionamentos SQLAlchemy; API de autenticação completa; interface de gerenciamento de usuários

**Pendente / Recomendações:**
- ⚠️ Arquivo .env com SECRET_KEY segura (obrigatório em produção)
- ⚠️ Logs de auditoria (médio)
- ⚠️ Dashboard de permissões (médio)
- **Exceção:** O módulo `app/api/v1/referencia/` mantém stack CertiLog (app.core.rbac + auth.get_current_user + ComumUsuario); não migrado para middleware PDV Ibix

### Ações Urgentes (referência — em grande parte implementadas em 2026-02-08)

**1. Proteger Rotas da API (2-3h):**
```python
# Adicionar em TODAS as rotas:
from ...core.middleware import get_current_user

@router.get("/")
def minha_rota(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)  # ✅ ADICIONAR
):
    # Sua lógica aqui
    pass
```

**2. Criar Arquivo .env (30min):**
```bash
# Na raiz do projeto:
SECRET_KEY=sua_chave_segura_min_32_caracteres_aleatoria
ACCESS_TOKEN_EXPIRE_MINUTES=60
DATABASE_URL=postgresql://user:pass@localhost:5432/pdv_solumatica
```

**3. Implementar Verificação de Permissões (4-5h):**
```python
# Criar: app/core/permissions.py
def has_permission(user: Usuario, permission: str, db: Session) -> bool:
    """Verifica se usuário tem permissão específica"""
    if not user.role:
        return False
    
    # Administrador tem todas as permissões
    if user.role.nome == "Administrador":
        return True
    
    # Buscar permissão no banco
    perm = db.query(Permissao).join(
        RolePermissao
    ).filter(
        RolePermissao.role_id == user.role_id,
        Permissao.nome == permission,
        Permissao.ativo == True
    ).first()
    
    return perm is not None
```

### Métricas de Progresso (atualizado 2026-02-08)

| Componente | % | Status |
|------------|---|--------|
| **Backend Total** | 90% | ✅ |
| - Modelos RBAC | 100% | ✅ |
| - JWT/Auth | 100% | ✅ |
| - API Auth | 100% | ✅ |
| - Outras APIs (auth unificada + permissões) | 90% | ✅ |
| **Frontend Total** | 40% | ⚠️ |
| - Interface Usuários | 100% | ✅ |
| - Dashboard Permissões | 0% | ❌ |
| **Segurança Total** | 85% | ✅ |
| - JWT Implementado | 100% | ✅ |
| - Rotas Protegidas (middleware + forbid_cliente + require_permission qualidade) | 90% | ✅ |
| - Auditoria | 0% | ❌ |
| **GERAL** | **~75%** | ✅ |

### Comandos Úteis

**Verificar Sistema RBAC:**
```bash
# Testar tabelas e dados
python Scripts_auxiliares/test_rbac.py

# Popular banco de dados
python Scripts_auxiliares/insert_rbac_data.py

# Verificar configuração de auth
python Scripts_auxiliares/verificar_config_auth.py
```

**Testar API:**
```bash
# 1. Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@ibix.com.br", "password": "admin123"}'

# 2. Usar token
TOKEN="seu_token_aqui"
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

**Banco de Dados:**
```sql
-- Ver roles
SELECT * FROM roles;

-- Ver permissões por módulo
SELECT modulo, COUNT(*) as total 
FROM permissoes 
GROUP BY modulo;

-- Ver permissões de uma role
SELECT r.nome as role, p.nome as permissao
FROM roles r
JOIN role_permissoes rp ON r.id = rp.role_id
JOIN permissoes p ON rp.permissao_id = p.id
WHERE r.nome = 'Técnico';

-- Ver usuários e suas roles
SELECT u.nome, u.email, r.nome as role
FROM usuarios u
LEFT JOIN roles r ON u.role_id = r.id;
```

### Troubleshooting

**Problema: Token inválido**
- **Causa:** SECRET_KEY mudou ou token expirou
- **Solução:** Fazer login novamente

**Problema: Permissão negada**
- **Causa:** Usuário não tem permissão para a ação
- **Solução:** Verificar role e permissões do usuário no banco

**Problema: Usuário sem role**
- **Causa:** Usuário criado antes do RBAC
- **Solução:** `UPDATE usuarios SET role_id = 1 WHERE id = X;`

**Referência Completa:** Ver `Diretrizes/RBAC_COMPLETO.md` para documentação detalhada sobre implementação, status e plano de ação

---

## 9. Notas Importantes

1. **Multi-tenancy:** Todas as verificações incluem filtro por `tenant_id`
2. **Cache de Permissões:** Sistema usa cache TTL de 5 minutos para melhor performance
3. **Herança:** Roles de nível superior têm implicitamente permissões de níveis inferiores (lógica implementada)
4. **Auditoria:** Todas as ações são registradas em logs de auditoria
5. **Permissões Granulares:** Cada ação específica (criar, visualizar, editar, aprovar, deletar) é uma permissão separada
6. **Validação de Assinaturas:** Aprovação de certificados requer permissão específica e validação de inspetor/aprovador

---

---

## Apêndice A — Performance Auth/RBAC e Rotas HTML

**Objetivo:** Evitar múltiplos `verify_token`, queries duplicadas de Usuario e Permissão por request. Usar este apêndice como **referência obrigatória** ao criar ou alterar rotas HTML e dependências de API.

### Otimizações já aplicadas (referência de implementação)

1. **Rotas HTML — um contexto por request**
   - **Padrão:** `check_auth_for_html` → (opcional) `check_html_module_permission` para módulo → **uma** chamada a `get_template_context` → decidir acesso com `context["user_role"]` e `context["user_permissions"]` → retornar template.
   - **Rotas que seguem o padrão:** `/dashboard`, `/configuracoes`, `/configuracoes/email/templates`, `/negocio/estoque`, `/negocio/financeiro` (resumo financeiro). **Não** repetir `verify_token`, query em Usuario nem query Permissão/Role/RolePermissao na rota.
   - **Referência de código:** `main.py` — funções `dashboard`, `configuracoes`, `configuracoes_templates_email`, `negocio_estoque`, `negocio_financeiro`.

2. **`get_template_context` (main.py)**
   - Preenche e reutiliza `request.state`: `user_id`, `user_payload` (quando lê token), `user`, `user_permissions`. Segunda chamada na mesma requisição reutiliza `request.state.user` e `request.state.user_permissions` (evita nova query Usuario/permissoes).
   - Quando lê token, seta `request.state.user_id` e `request.state.user_payload` para as demais funções da mesma request.

3. **`check_auth_for_html` (app/core/middleware.py)**
   - Após validar token, seta `request.state.user_id` e `request.state.user_payload`, para `get_template_context` e `check_html_module_permission` não precisarem decodificar o token de novo.

4. **`require_permission` (app/core/middleware.py)**
   - Passou a usar **PermissionCache** (TTL 5 min) via `get_user_permissions(user_id, db)` em vez de query direta em Permissão/Role/RolePermissao em toda chamada de API. Reduz carga em listagens (ex.: clientes) e demais endpoints que usam `Depends(require_permission(...))`.

### Regra para novas rotas HTML

- **Sempre:** `auth_check = await check_auth_for_html(request, db)`; se necessário, `check_html_module_permission(request, db, "modulo", "mensagem")`.
- **Uma vez:** `context = get_template_context(request, db)`. Usar apenas `context["user_id"]`, `context["user_role"]`, `context["user_permissions"]` para 403 ou redirecionamento.
- **Não:** Chamar de novo `AuthConfig.verify_token`, `db.query(Usuario)` ou query em Permissão/Role/RolePermissao dentro da rota HTML.

### Pendências / melhorias futuras

- **get_cliente_scope_dep:** ainda pode implicar 2× uso de token (get_current_user + get_current_user_cliente) em APIs; considerar reutilizar `request.state.user_payload` quando disponível.
- **forbid_cliente_access:** reutilizar payload quando já em request.state (ex.: em rotas que passam por middleware que preenche state).
- **ClienteScope:** cache por request (ex.: request.state.cliente_scope) em rotas que usam get_cliente_scope_dep mais de uma vez (hoje FastAPI já cacheia Depends por request).

### Referências de código

- **main.py:** `get_template_context`, `check_html_module_permission`, rotas `dashboard`, `configuracoes`, `negocio_estoque`, `negocio_financeiro`.
- **app/core/middleware.py:** `check_auth_for_html`, `require_permission`, `get_user_permissions`, `PermissionCache`, `get_cliente_scope_dep`.
- **app/core/scope.py:** `get_allowed_cliente_ids`, `get_cliente_scope`.

---

## Apêndice B — Acesso por Role (Detalhes)

**Permissões do módulo usuarios:** `usuarios:visualizar`, `usuarios:criar`, `usuarios:editar`, `usuarios:excluir`, `usuarios:gerenciar_roles`. **Cliente Administrador não acessa** `/usuarios` nem `/configuracoes`; apenas Superadministrador e Administrador.

**Rotas HTML e restrição:** `/usuarios` → Superadministrador e Administrador (ambos veem lista de usuários, card Representantes, criar/editar no escopo). Na página `/usuarios`, o card **"Funções (Roles) e Permissões"** é exibido **apenas para Superadministrador** (template: `can_manage_roles` só quando `user_role == 'Superadministrador'`). **`/roles`** → apenas Superadministrador (rota em `main.py`: 403 para qualquer outra role). `/configuracoes` → Superadministrador e Administrador. `/fiscal/empresa` → campo Cliente visível apenas com `fiscal.empresa.ver_cliente` (Administrador e Superadministrador).

**E-mail por cliente:** GET/PUT `/configuracoes/email/separado-por-cliente/` — PUT apenas Superadministrador. Router `/api/v1/email-cliente`: Superadministrador, Administrador ou Cliente Administrador.

**APIs usuarios:** GET/POST/PUT/DELETE `/api/v1/usuarios/` — Cliente Administrador sem acesso (403). Usar Minha equipe (`/api/v1/minha-equipe/*`) para técnicos.

---

**Última Atualização:** 2026-03-02  
**Versão:** 1.5  
**Status:** Documentação Ativa - Referência Padrão  
**Adições:** Apêndice A reescrito com otimizações aplicadas (rotas HTML um contexto, get_template_context/check_auth_for_html/require_permission) e regra para novas rotas; referências de código para uso como padrão.
