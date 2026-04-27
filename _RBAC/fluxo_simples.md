┌──────────────────────────────────────────────┐
│           ADMINISTRADOR DO SISTEMA           │
│ (Gerencia toda a plataforma e os clientes)   │
└──────────────────────────────────────────────┘
                    │
                    ▼
      Cria e gerencia empresas clientes
                    │
                    ▼
┌──────────────────────────────────────────────┐
│           ADMINISTRADOR DO CLIENTE           │
│ (Controle interno da empresa contratante)    │
│ - Configura dados da empresa                 │
│ - Cadastra técnicos e clientes associados    │
│ - Gerencia certificados e relatórios         │
└──────────────────────────────────────────────┘
                    │
                    ├────────────┐
                    │            │
                    ▼            ▼
┌───────────────────────────┐   ┌─────────────────────────────┐
│       TÉCNICO CLIENTE     │   │        CLIENTE CLIENTE      │
│ (Executa as operações)    │   │ (Fornecedor / contratante)  │
│ - Realiza calibrações     │   │ - Consulta resultados       │
│ - Registra dados e fotos  │   │ - Visualiza relatórios      │
│ - Envia para aprovação    │   │ - Pode aprovar orçamentos   │
└───────────────────────────┘   └─────────────────────────────┘
                    │
                    ▼
          Dados e resultados enviados
                para aprovação
                    │
                    ▼
┌──────────────────────────────────────────────┐
│           ADMINISTRADOR DO CLIENTE           │
│ (Valida, aprova e emite certificados)        │
│ - Confirma execução dos técnicos             │
│ - Emite relatórios e certificados finais     │
└──────────────────────────────────────────────┘
                    │
                    ▼
        Sincroniza com o ADMINISTRADOR DO SISTEMA
       (monitoramento, auditoria e relatórios globais)




📋 Resumo dos Níveis
Nível	Papel	Escopo	Principais Ações
1	Administrador do Sistema	Global	Cria empresas, define planos e supervisiona tudo
2	Administrador do Cliente	Empresa própria	Gerencia técnicos, clientes e relatórios
3	Técnico do Cliente	Operacional	Executa serviços e registra resultados
4	Cliente do Cliente	Externo	Consulta e acompanha resultados





CERTIPESO - FLUXO DE PERMISSÕES E RELAÇÕES

┌─────────────────────────────────────────────┐
│        ADMINISTRADOR DO SISTEMA (GLOBAL)    │
│  - Controle total da plataforma             │
│  - Cria e gerencia empresas (clientes)      │
│  - Supervisiona planos, licenças e acessos  │
└─────────────────────────────────────────────┘
                     │
                     ▼
         ┌──────────────────────────┐
         │  ADMINISTRADOR CLIENTE   │
         │  (Gestão da própria empresa) 
         │  - Cadastra técnicos e clientes
         │  - Configura dados da empresa
         │  - Emite relatórios e certificados
         └──────────────────────────┘
                     │
         ┌────────────┴────────────┐
         ▼                         ▼
┌──────────────────────┐     ┌────────────────────────┐
│    TÉCNICO CLIENTE   │     │     CLIENTE CLIENTE    │
│ (Execução técnica)   │     │ (Acesso externo)       │
│ - Realiza serviços   │     │ - Visualiza relatórios │
│ - Registra dados     │     │ - Acompanha status     │
│ - Envia para validação│    │ - Aprova orçamentos    │
└──────────────────────┘     └────────────────────────┘
                     │
                     ▼
         ┌──────────────────────────┐
         │ ADMINISTRADOR CLIENTE    │
         │ - Valida e aprova dados  │
         │ - Emite certificados     │
         │ - Gera histórico interno │
         └──────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│ ADMINISTRADOR DO SISTEMA                    │
│ - Acompanha estatísticas globais            │
│ - Supervisiona empresas e usuários          │
│ - Garante conformidade e auditoria          │
└─────────────────────────────────────────────┘
🔁 Resumo hierárquico rápido
markdown
Copiar código
Administrador Sistema
 └── Administrador Cliente
      ├── Técnico Cliente
      └── Cliente Cliente




      CERTIPESO – FLUXO DE PERMISSÕES E RELAÇÕES

🧑‍💼 Administrador do Sistema (Global)
│
│  ⚙️ Funções:
│   • Controle total da plataforma
│   • Criação e gestão de empresas/clientes
│   • Gerenciamento de planos, licenças e acessos
│   • Monitoramento e auditoria global
│
└── 🏢 Administrador do Cliente (Empresa)
    │
    │  📋 Funções:
    │   • Gestão completa dentro da própria empresa
    │   • Cadastro de técnicos e clientes associados
    │   • Configuração de dados corporativos (logo, endereço, contratos)
    │   • Emissão de relatórios e certificados
    │
    ├── 🧰 Técnico do Cliente
    │    │
    │    │  🔧 Funções:
    │    │   • Execução dos serviços (ex.: calibrações, inspeções)
    │    │   • Registro de resultados, fotos e assinaturas
    │    │   • Envio para aprovação do administrador
    │    │
    │    └── 🔄 Fluxo:
    │          Técnicos → Administrador Cliente → Certificados Emitidos
    │
    └── 👥 Cliente do Cliente (Fornecedor / Contratante)
         │
         │  🔍 Funções:
         │   • Visualização de relatórios e certificados
         │   • Acompanhamento de status e histórico
         │   • Aprovação ou rejeição de orçamentos (se aplicável)
         │
         └── 🔒 Acesso restrito somente à empresa contratante
🧭 Visão hierárquica resumida
arduino
Copiar código
🧑‍💼 Administrador do Sistema
 └── 🏢 Administrador do Cliente
      ├── 🧰 Técnico do Cliente
      └── 👥 Cliente do Cliente


═══════════════════════════════════════════════════════════════════
                    SISTEMA DE GERENCIAMENTO DE PERMISSÕES
═══════════════════════════════════════════════════════════════════

📊 ESTRUTURA ATUAL DO BANCO DE DADOS

Total de Permissões no Sistema: 28

Organização por Módulo:
┌────────────────────┬──────────────────┐
│ Módulo             │ Permissões       │
├────────────────────┼──────────────────┤
│ 👥 usuarios        │ 4 permissões     │
│ 👤 clientes        │ 4 permissões     │
│ ⚙️  equipamentos    │ 4 permissões     │
│ 📜 certificados    │ 5 permissões     │
│ 🔬 afericoes       │ 4 permissões     │
│ 📊 relatorios      │ 3 permissões     │
│ 🔍 auditoria       │ 2 permissões     │
│ ⚙️  configuracoes   │ 2 permissões     │
└────────────────────┴──────────────────┘

Formato das Permissões: modulo:acao

Exemplos:
  • usuarios:visualizar
  • usuarios:criar
  • usuarios:editar
  • usuarios:excluir
  • clientes:visualizar
  • equipamentos:criar
  • certificados:emitir
  • auditoria:visualizar


═══════════════════════════════════════════════════════════════════
                    PROPOSTA DE INTERFACE DE GERENCIAMENTO
═══════════════════════════════════════════════════════════════════

1️⃣ MODAL DE GERENCIAMENTO DE PERMISSÕES

╔══════════════════════════════════════════════════════════════════╗
║ 🛡️  Gerenciar Permissões - Administrador                  [✕]   ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║ 📦 USUÁRIOS (4 permissões) ───────────────── [☑ Todos] [☐ Nenhum] ║
║ ├── ☑ usuarios:visualizar                                       ║
║ │   └─ Visualizar lista de usuários                            ║
║ ├── ☑ usuarios:criar                                            ║
║ │   └─ Criar novos usuários                                     ║
║ ├── ☑ usuarios:editar                                           ║
║ │   └─ Editar usuários existentes                              ║
║ └── ☑ usuarios:excluir                                          ║
║     └─ Excluir usuários                                         ║
║                                                                  ║
║ 📦 CLIENTES (4 permissões) ───────────────── [☑ Todos] [☐ Nenhum] ║
║ ├── ☑ clientes:visualizar                                       ║
║ ├── ☑ clientes:criar                                            ║
║ ├── ☑ clientes:editar                                           ║
║ └── ☑ clientes:excluir                                          ║
║                                                                  ║
║ 📦 EQUIPAMENTOS (4 permissões) ──────────── [☐ Todos] [☑ Nenhum] ║
║ ├── ☑ equipamentos:visualizar                                   ║
║ ├── ☐ equipamentos:criar                                        ║
║ ├── ☑ equipamentos:editar                                       ║
║ └── ☐ equipamentos:excluir                                      ║
║                                                                  ║
║ 📦 CERTIFICADOS (5 permissões) ──────────── [☑ Todos] [☐ Nenhum] ║
║ ├── ☑ certificados:visualizar                                   ║
║ ├── ☑ certificados:criar                                        ║
║ ├── ☑ certificados:editar                                       ║
║ ├── ☑ certificados:emitir                                       ║
║ └── ☑ certificados:excluir                                      ║
║                                                                  ║
║ 📦 AFERIÇÕES (4 permissões) ─────────────── [☐ Todos] [☑ Nenhum] ║
║ ├── ☑ afericoes:visualizar                                      ║
║ ├── ☐ afericoes:criar                                           ║
║ ├── ☐ afericoes:editar                                          ║
║ └── ☐ afericoes:excluir                                         ║
║                                                                  ║
║ 📦 RELATÓRIOS (3 permissões) ────────────── [☑ Todos] [☐ Nenhum] ║
║ ├── ☑ relatorios:visualizar                                     ║
║ ├── ☑ relatorios:gerar                                          ║
║ └── ☑ relatorios:exportar                                       ║
║                                                                  ║
║ 📦 AUDITORIA (2 permissões) ─────────────── [☑ Todos] [☐ Nenhum] ║
║ ├── ☑ auditoria:visualizar                                      ║
║ └── ☑ auditoria:exportar                                        ║
║                                                                  ║
║ 📦 CONFIGURAÇÕES (2 permissões) ─────────── [☑ Todos] [☐ Nenhum] ║
║ ├── ☑ configuracoes:visualizar                                  ║
║ └── ☑ configuracoes:editar                                      ║
║                                                                  ║
╠══════════════════════════════════════════════════════════════════╣
║ 📊 Total: 22/28 permissões selecionadas (78.6%)                 ║
╠══════════════════════════════════════════════════════════════════╣
║                               [Cancelar] [💾 Salvar Permissões] ║
╚══════════════════════════════════════════════════════════════════╝


2️⃣ INTEGRAÇÃO NA TABELA DE ROLES

Adicionar coluna "Permissões" com botão de gerenciamento:

╔═════╤═══════════════╤════════╤═══════════════════════╤══════════╗
║ ID  │ Nome          │ Status │ Permissões            │ Ações    ║
╠═════╪═══════════════╪════════╪═══════════════════════╪══════════╣
║ #1  │ Administrador │ Ativo  │ 🔑 28/28 (100%)       │ ✏️  🗑️   ║
║     │               │        │ [📋 Gerenciar]        │          ║
╠═════╪═══════════════╪════════╪═══════════════════════╪══════════╣
║ #2  │ Técnico       │ Ativo  │ 🔑 13/28 (46%)        │ ✏️  🗑️   ║
║     │               │        │ [📋 Gerenciar]        │          ║
╠═════╪═══════════════╪════════╪═══════════════════════╪══════════╣
║ #3  │ Cliente       │ Ativo  │ 🔑 2/28 (7%)          │ ✏️  🗑️   ║
║     │               │        │ [📋 Gerenciar]        │          ║
╠═════╪═══════════════╪════════╪═══════════════════════╪══════════╣
║ #4  │ Visualizador  │ Ativo  │ 🔑 8/28 (28%)         │ ✏️  🗑️   ║
║     │               │        │ [📋 Gerenciar]        │          ║
╠═════╪═══════════════╪════════╪═══════════════════════╪══════════╣
║ #5  │ Auditor       │ Ativo  │ 🔑 10/28 (35%)        │ ✏️  🗑️   ║
║     │               │        │ [📋 Gerenciar]        │          ║
╚═════╧═══════════════╧════════╧═══════════════════════╧══════════╝


═══════════════════════════════════════════════════════════════════
                    API REST - ENDPOINTS
═══════════════════════════════════════════════════════════════════

1. LISTAR TODAS AS PERMISSÕES
   GET /api/v1/permissoes/
   
   Response:
   {
     "permissoes": [
       {
         "id": 1,
         "nome": "usuarios:visualizar",
         "descricao": "Visualizar lista de usuários",
         "modulo": "usuarios",
         "acao": "visualizar",
         "ativo": true
       },
       ...
     ],
     "total": 28,
     "modulos": {
       "usuarios": 4,
       "clientes": 4,
       "equipamentos": 4,
       "certificados": 5,
       "afericoes": 4,
       "relatorios": 3,
       "auditoria": 2,
       "configuracoes": 2
     }
   }

2. OBTER PERMISSÕES DE UMA ROLE
   GET /api/v1/roles/{role_id}/permissoes
   
   Response:
   {
     "role_id": 1,
     "role_nome": "Administrador",
     "permissoes": [
       {
         "id": 1,
         "nome": "usuarios:visualizar",
         "modulo": "usuarios",
         "acao": "visualizar"
       },
       ...
     ],
     "total_permissoes": 28,
     "permissoes_ids": [1, 2, 3, 4, 5, ...]
   }

3. ATUALIZAR PERMISSÕES DE UMA ROLE
   PUT /api/v1/roles/{role_id}/permissoes
   
   Body:
   {
     "permissoes_ids": [1, 2, 3, 5, 7, 9, 10, 11]
   }
   
   Response:
   {
     "message": "Permissões atualizadas com sucesso",
     "role_id": 2,
     "role_nome": "Técnico",
     "total_permissoes": 8,
     "permissoes_atualizadas": 8
   }

4. LISTAR PERMISSÕES POR MÓDULO
   GET /api/v1/permissoes/modulo/{modulo}
   
   Response:
   {
     "modulo": "usuarios",
     "permissoes": [
       {
         "id": 1,
         "nome": "usuarios:visualizar",
         "descricao": "Visualizar lista de usuários",
         "acao": "visualizar"
       },
       ...
     ],
     "total": 4
   }


═══════════════════════════════════════════════════════════════════
                    PERFIS DE PERMISSÕES SUGERIDOS
═══════════════════════════════════════════════════════════════════

🧑‍💼 ADMINISTRADOR DO SISTEMA (28/28 permissões - 100%)
├── ✅ Todas as permissões de usuários
├── ✅ Todas as permissões de clientes
├── ✅ Todas as permissões de equipamentos
├── ✅ Todas as permissões de certificados
├── ✅ Todas as permissões de aferições
├── ✅ Todas as permissões de relatórios
├── ✅ Todas as permissões de auditoria
└── ✅ Todas as permissões de configurações


🔧 TÉCNICO (13/28 permissões - 46%)
├── ✅ clientes:visualizar
├── ✅ equipamentos:visualizar
├── ✅ equipamentos:editar (registrar dados)
├── ✅ certificados:visualizar
├── ✅ certificados:criar (rascunho)
├── ✅ afericoes:visualizar
├── ✅ afericoes:criar
├── ✅ afericoes:editar
├── ✅ relatorios:visualizar
└── ❌ Sem permissões de: excluir, configurações, auditoria


👤 CLIENTE (2/28 permissões - 7%)
├── ✅ certificados:visualizar (apenas seus certificados)
├── ✅ relatorios:visualizar (apenas seus relatórios)
└── ❌ Sem acesso a: usuários, equipamentos, aferições, configurações


👁️  VISUALIZADOR (8/28 permissões - 28%)
├── ✅ usuarios:visualizar
├── ✅ clientes:visualizar
├── ✅ equipamentos:visualizar
├── ✅ certificados:visualizar
├── ✅ afericoes:visualizar
├── ✅ relatorios:visualizar
├── ✅ relatorios:gerar
└── ❌ Sem permissões de: criar, editar, excluir


🔍 AUDITOR (10/28 permissões - 35%)
├── ✅ Todas as permissões de visualizar
├── ✅ auditoria:visualizar
├── ✅ auditoria:exportar
├── ✅ relatorios:visualizar
├── ✅ relatorios:gerar
├── ✅ relatorios:exportar
└── ❌ Sem permissões de: criar, editar, excluir


═══════════════════════════════════════════════════════════════════
                    FUNCIONALIDADES DO SISTEMA
═══════════════════════════════════════════════════════════════════

✅ Organização por Módulos
   • Permissões agrupadas por área funcional
   • Acordeão expansível/recolhível por módulo
   • Contador visual de permissões ativas por módulo

✅ Seleção em Massa
   • Botão "Selecionar Todas" por módulo
   • Botão "Desmarcar Todas" por módulo
   • Indicador visual de módulo totalmente selecionado

✅ Busca e Filtros
   • Busca por nome ou descrição da permissão
   • Filtro por módulo
   • Filtro por ação (visualizar, criar, editar, excluir)

✅ Indicadores Visuais
   • Badge com contador total (ex: 22/28)
   • Porcentagem de permissões ativas
   • Cor diferenciada por nível de acesso
     - Verde: 80-100% (Administrador)
     - Azul: 40-79% (Técnico, Auditor)
     - Amarelo: 10-39% (Visualizador)
     - Vermelho: 0-9% (Cliente)

✅ Proteções de Segurança
   • Apenas Administradores podem gerenciar permissões
   • Confirmação antes de remover permissões críticas
   • Log de auditoria de mudanças de permissões
   • Validação de permissões mínimas por role


═══════════════════════════════════════════════════════════════════
                    FLUXO DE USO
═══════════════════════════════════════════════════════════════════

1️⃣ Administrador acessa página de Roles
2️⃣ Clica no botão "Gerenciar Permissões" na linha da role desejada
3️⃣ Modal é aberto com permissões agrupadas por módulo
4️⃣ Administrador marca/desmarca as permissões desejadas
5️⃣ Sistema mostra contador em tempo real
6️⃣ Administrador clica em "Salvar Permissões"
7️⃣ Sistema valida e salva as alterações
8️⃣ Tabela de roles é atualizada com novo contador
9️⃣ Sistema registra a ação no log de auditoria


═══════════════════════════════════════════════════════════════════
                    ARQUIVOS A SEREM CRIADOS/MODIFICADOS
═══════════════════════════════════════════════════════════════════

NOVOS ARQUIVOS:
  📄 /app/api/v1/permissoes.py          - API de permissões
  📄 /app/schemas/permissao.py          - Schemas Pydantic
  📄 /app/static/js/permissoes-manager.js - Gerenciador JS

ARQUIVOS A MODIFICAR:
  📝 /app/templates/usuarios/index.html - Adicionar modal de permissões
  📝 /app/static/js/roles-manager.js    - Adicionar botão e lógica
  📝 /app/static/js/custom-modal.js     - Registrar novo modal
  📝 main.py                            - Registrar rotas


═══════════════════════════════════════════════════════════════════
                    PRÓXIMOS PASSOS
═══════════════════════════════════════════════════════════════════

✅ Fase 1: Backend
   1. Criar schemas Pydantic para permissões
   2. Criar API REST de permissões
   3. Adicionar endpoint de atualização em lote
   4. Registrar rotas no main.py

✅ Fase 2: Frontend - Estrutura
   1. Criar modal customizado HTML
   2. Adicionar CSS para acordeão de módulos
   3. Adicionar botão na tabela de roles

✅ Fase 3: Frontend - Lógica
   1. Criar permissoes-manager.js
   2. Implementar carregamento de permissões
   3. Implementar seleção/deseleção
   4. Implementar salvamento em lote

✅ Fase 4: Melhorias
   1. Adicionar busca/filtro de permissões
   2. Adicionar templates de permissões comuns
   3. Adicionar histórico de alterações
   4. Adicionar exportação de configuração