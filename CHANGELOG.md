# Changelog - PDV Ibix

Todas as mudanças notáveis no PDV Ibix (sistema de vendas e gestão PDV, desenvolvido pela Automscale) serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [Não versionado] - 2026-02-06

### PostgreSQL

- **Configuração:** Banco PostgreSQL em `app/database/connection.py`. Porta 5432.
- **Dependência:** `psycopg2-binary` em `requirements.txt`.
- **Alembic:** `app/database/migrations/env.py` usa `get_database_url()`.
- **Variáveis:** `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` em `.env.example`.
- **Erros de unicidade:** Helper `app/core/db_errors.py` para PostgreSQL (23505).

## [Não versionado] - 2025-01-02

### 🐛 Correções - Pesos Padrão e Modal de Visualização

#### 🔧 Correção de Salvamento e Carregamento de Pesos Padrão
- **PROBLEMA CORRIGIDO:** Pesos padrão não eram salvos ao criar/editar certificados
- **PROBLEMA CORRIGIDO:** Pesos padrão não eram carregados ao editar certificados
- **SCHEMA ATUALIZADO:** Adicionado `PesoPadraoSimples` em `app/schemas/certificado.py`
- **RESPOSTA API:** Incluído `pesos_padrao: Optional[List[PesoPadraoSimples]]` em `CertificadoResponse`
- **PROCESSAMENTO API:** Criada função `_processar_pesos_padrao()` em `app/api/v1/certificados.py` para processar campos `peso_padrao_*`
- **CRIAÇÃO:** Endpoint `POST /api/v1/certificados/` agora processa e salva pesos padrão
- **ATUALIZAÇÃO:** Endpoint `PUT /api/v1/certificados/{id}` agora processa e atualiza pesos padrão (remove antigos, cria novos)
- **CARREGAMENTO:** Adicionado `joinedload(Certificado.pesos_padrao)` em todas as queries de certificados
- **FRONTEND:** Criada função `preencherPesosPadrao()` para carregar pesos padrão ao editar certificado
- **COLETA:** Atualizada função `coletarPesosPadrao()` para coletar dados diretamente dos campos do formulário

#### 🎨 Modal de Visualização - Pesos Padrão
- **NOVA SEÇÃO:** Adicionada seção "Pesos Padrão Utilizados" no modal de visualização
- **EXIBIÇÃO:** Tabela formatada mostrando Ordem, Identificação, Certificado e Validade
- **ORDENAÇÃO:** Pesos padrão ordenados por campo `ordem` e `id`
- **CONDIÇÃO:** Seção só aparece quando há pesos padrão associados ao certificado

#### 🎨 Modal de Visualização - Ensaios
- **NOVA SEÇÃO:** Adicionada seção "Ensaios de Excentricidade" no modal de visualização
- **NOVA SEÇÃO:** Adicionada seção "Resultados dos Ensaios" no modal de visualização
- **NOVA SEÇÃO:** Adicionada seção "Ensaios de Mobilidade" no modal de visualização
- **CARREGAMENTO:** Função `visualizarCertificado()` agora carrega ensaios em paralelo via API
- **ENSAIOS EXCENTRICIDADE:** Tabela com colunas Ponto, Carga, Leitura Antes, Erro Antes, Leitura Depois, Erro Depois (ordenados A-E)
- **RESULTADOS ENSAIOS:** Tabela com colunas Ponto, Carga, Leitura Antes, Erro Antes, Leitura Depois, Erro Depois, Incerteza (ordenados 1-5)
- **ENSAIOS MOBILIDADE:** Tabela com colunas Carga, Sobrecarga, Leitura Antes, Leitura Depois, Padrão Utilizado
- **CONDIÇÃO:** Seções só aparecem quando há dados correspondentes

#### 🛡️ Melhorias de Segurança e Tratamento de Erros
- **TRY-CATCH:** Função `preencherModalVisualizacao()` envolvida em try-catch para capturar erros
- **VERIFICAÇÕES:** Adicionada função auxiliar `setElementText()` que verifica existência de elementos antes de definir valores
- **VALIDAÇÕES:** Verificações de segurança para todos os elementos do DOM antes de acesso
- **FORMATAÇÃO:** Funções auxiliares para formatar valores, datas e tipos de forma segura

#### 📋 Arquivos Modificados
- `app/schemas/certificado.py` - Adicionado schema `PesoPadraoSimples` e incluído em `CertificadoResponse`
- `app/api/v1/certificados.py` - Processamento de pesos padrão e carregamento com `joinedload`
- `app/static/js/certificados.js` - Função `preencherPesosPadrao()` e melhorias no modal de visualização
- `app/static/js/certificados/features/pesos-padrao.js` - Melhorias na coleta de dados
- `app/templates/certificados/listar.html` - Seções de pesos padrão e ensaios no modal

## [Não versionado] - 2025-01-XX

### ✨ NOVO: Sistema de Tipos de Equipamento

#### 🗄️ Banco de Dados
- **NOVA TABELA:** Criada tabela `tipo_equipamento` com as seguintes colunas:
  - `id` (INT, PK, AUTO_INCREMENT)
  - `tipo_equipamento` (VARCHAR(255), NOT NULL)
  - `inf_adicionais` (TEXT, NULL)
  - `created_at` (DATETIME, automático)
  - `updated_at` (DATETIME, automático)
- **RELACIONAMENTO:** Adicionada coluna `tipo_equipamento_id` (INT, FK, NULL) na tabela `equipamentos`
- **CONSTRAINT:** Criada foreign key `fk_equipamento_tipo_equipamento` ligando `equipamentos.tipo_equipamento_id` → `tipo_equipamento.id`
- **SCRIPT SQL:** Criado arquivo `app/database/migrations/create_tipo_equipamento.sql` para execução manual

#### 🏗️ Modelo SQLAlchemy
- **NOVO MODELO:** Criado `app/models/tipo_equipamento.py` com classe `TipoEquipamento` herdando de `BaseModel`
- **RELACIONAMENTO:** Adicionado relacionamento `equipamentos` em `TipoEquipamento` (one-to-many)
- **ATUALIZAÇÃO:** Modelo `Equipamento` atualizado com:
  - Coluna `tipo_equipamento_id` (Integer, ForeignKey, nullable=True)
  - Relacionamento `tipo_equipamento` (relationship com TipoEquipamento)
- **IMPORTS:** Adicionado `TipoEquipamento` no `__init__.py` dos models

#### 📋 Schemas Pydantic
- **NOVO SCHEMA:** Criado `app/schemas/tipo_equipamento.py` com:
  - `TipoEquipamentoBase`: campos base (tipo_equipamento, inf_adicionais)
  - `TipoEquipamentoCreate`: para criação
  - `TipoEquipamentoUpdate`: para atualização (todos campos opcionais)
  - `TipoEquipamentoResponse`: resposta completa com id, created_at, updated_at
- **SCHEMA SIMPLIFICADO:** Criado `TipoEquipamentoSimples` em `equipamento.py` para uso em respostas
- **ATUALIZAÇÃO:** Schema `EquipamentoBase` atualizado com campo `tipo_equipamento_id: Optional[int]`
- **ATUALIZAÇÃO:** Schema `EquipamentoUpdate` atualizado com campo `tipo_equipamento_id: Optional[int]`
- **ATUALIZAÇÃO:** Schema `EquipamentoResponse` atualizado com campo `tipo_equipamento: Optional[TipoEquipamentoSimples]`

#### 🔌 API REST
- **NOVA API:** Criada `/api/v1/tipo_equipamento/` para gerenciamento completo de tipos
- **ENDPOINTS DISPONÍVEIS:**
  - `POST /api/v1/tipo_equipamento/` - Criar novo tipo de equipamento
  - `GET /api/v1/tipo_equipamento/` - Listar todos os tipos
  - `GET /api/v1/tipo_equipamento/{id}` - Obter tipo por ID
  - `PUT /api/v1/tipo_equipamento/{id}` - Atualizar tipo existente
  - `DELETE /api/v1/tipo_equipamento/{id}` - Excluir tipo (com validação de equipamentos vinculados)
- **VALIDAÇÕES:** Endpoint DELETE verifica se existem equipamentos usando o tipo antes de permitir exclusão
- **EAGER LOADING:** Adicionado `joinedload` para carregar relacionamento `tipo_equipamento` nas queries de equipamentos
- **REGISTRO:** Rota registrada no `main.py` com prefixo `/api/v1`

#### 🎨 Interface - Modal de Tipos de Equipamento
- **NOVO MODAL:** Criado modal independente (sem Bootstrap) para gerenciar tipos de equipamento
- **LOCALIZAÇÃO:** Modal adicionado em `app/templates/equipamentos/listar.html`
- **ESTRUTURA:**
  - Formulário para cadastrar/editar tipo de equipamento
  - Tabela listando todos os tipos cadastrados
  - Botões de ação (editar/excluir) para cada tipo
- **CAMPOS DO FORMULÁRIO:**
  - Tipo de Equipamento (obrigatório)
  - Informações Adicionais (opcional)
- **BOTÃO:** Adicionado botão "Gerenciar Tipos de Equipamento" no header da página de equipamentos

#### 🎨 Interface - Formulário de Equipamento
- **MODAL ATUALIZADO:** Modal de equipamento convertido para formato independente (sem Bootstrap)
- **NOVO CAMPO:** Adicionado campo select "Tipo de Equipamento" no formulário de equipamento
- **POSICIONAMENTO:** Campo posicionado ao lado do campo "Cliente" na seção "Cliente e Tipo"
- **CARREGAMENTO:** Select preenchido automaticamente com tipos disponíveis via API
- **INTEGRAÇÃO:** Campo incluído no envio do formulário (criação e atualização)

#### 📊 Tabela de Equipamentos
- **NOVA COLUNA:** Adicionada coluna "Tipo de Equipamento" na tabela de listagem
- **POSICIONAMENTO:** Coluna inserida entre "Capacidade" e "Inmetro/Reparo"
- **EXIBIÇÃO:** Mostra o nome do tipo de equipamento ou "-" se não houver tipo associado
- **COLSPAN:** Atualizado colspan de 9 para 10 na mensagem de "nenhum equipamento encontrado"

#### 💻 JavaScript
- **NOVAS FUNÇÕES:**
  - `abrirModalTipoEquipamento()`: Abre modal e carrega lista de tipos
  - `fecharModalTipoEquipamento()`: Fecha modal e limpa formulário
  - `carregarTiposEquipamento()`: Busca todos os tipos via API
  - `preencherSelectTiposEquipamento()`: Preenche select com tipos disponíveis
  - `salvarTipoEquipamento()`: Cria ou atualiza tipo via API
  - `editarTipoEquipamento(id)`: Preenche formulário para edição
  - `excluirTipoEquipamento(id)`: Exclui tipo com confirmação
  - `limparFormularioTipoEquipamento()`: Reseta formulário
  - `abrirModalEquipamento()`: Abre modal de equipamento (atualizado)
  - `fecharModalEquipamento()`: Fecha modal de equipamento (atualizado)
- **ATUALIZAÇÕES:**
  - `carregarEquipamentos()`: Inclui chamada para carregar tipos
  - `salvarEquipamento()`: Inclui `tipo_equipamento_id` nos dados enviados
  - `preencherFormulario()`: Preenche campo `tipoEquipamentoId` ao editar
  - `renderizarTabela()`: Adiciona coluna com tipo de equipamento
  - `editarEquipamento()`: Garante carregamento de tipos antes de preencher formulário
- **LOGS DE DEBUG:** Adicionados logs para diagnosticar problemas com tipo_equipamento_id

#### 🔧 Melhorias Técnicas
- **EAGER LOADING:** Implementado eager loading de relacionamentos para melhor performance
- **VALIDAÇÃO:** Validação de exclusão de tipo quando há equipamentos vinculados
- **TRATAMENTO DE ERROS:** Tratamento adequado de valores null/undefined
- **TIMING:** Garantia de carregamento de dados antes de preencher formulários

### 📝 Notas
- O script SQL deve ser executado manualmente no banco de dados antes de usar a funcionalidade
- A FK em equipamentos é opcional (nullable=True) para não quebrar dados existentes
- Todos os modais foram convertidos para formato independente (sem Bootstrap) seguindo padrão do modal de clientes

