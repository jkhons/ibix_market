# 📁 Estrutura da Aplicação PDV Ibix

## 🏗️ Visão Geral

Esta é a estrutura principal da aplicação PDV Ibix, organizada conforme as especificações do `ESTRUTURA_DIRETORIOS.md`.

## 📂 Estrutura de Diretórios

```
app/
├── 📁 api/                    # APIs REST do FastAPI
│   └── 📁 v1/                # Versão 1 das APIs
│       └── 📄 __init__.py
│   └── 📄 __init__.py
├── 📁 core/                   # Configurações centrais
├── 📁 database/               # Camada de banco de dados
│   └── 📁 migrations/        # Scripts de migração
├── 📁 models/                 # Modelos SQLAlchemy
├── 📁 schemas/                # Schemas Pydantic
├── 📁 services/               # Lógica de negócio
├── 📁 static/                 # Arquivos estáticos customizados
│   ├── 📁 css/               # CSS customizado
│   │   ├── 📄 certlog.css    # Estilos específicos do PDV Ibix
│   │   └── 📄 dashboard.css  # Estilos do dashboard
│   ├── 📁 js/                # JavaScript customizado
│   │   ├── 📄 certlog.js     # Funções principais do PDV Ibix
│   │   └── 📄 dashboard.js   # JavaScript do dashboard
│   ├── 📁 img/               # Imagens customizadas
│   ├── 📁 fonts/             # Fontes customizadas
│   └── 📁 docs/              # Documentos gerados
│       ├── 📁 pdfs/          # PDFs gerados
│       ├── 📁 certificados/  # PDFs (quando utilizado)
│       ├── 📁 comprovantes/  # Comprovantes em PDF
│       └── 📁 relatorios/    # Relatórios em PDF
├── 📁 templates/              # Templates Jinja2
│   └── 📄 dashboard.html     # Dashboard principal customizado
├── 📄 __init__.py            # Módulo principal
└── 📄 README.md              # Esta documentação
```

## 🎯 Dashboard Customizado

### **Arquivos Principais:**
- **Template:** `templates/dashboard.html` - Dashboard principal customizado
- **CSS:** `static/css/certlog.css` - Estilos específicos do PDV Ibix
- **JavaScript:** `static/js/certlog.js` - Funcionalidades customizadas do PDV Ibix

### **Características:**
- ✅ Design responsivo com Bootstrap 5
- ✅ Gráficos interativos com Chart.js
- ✅ Sistema de notificações
- ✅ Atualizações em tempo real
- ✅ Sidebar customizada
- ✅ Cores e branding do PDV Ibix

### **Funcionalidades Implementadas:**
1. **Estatísticas em Tempo Real**
   - Total de clientes
   - Resumo de vendas e pedidos
   - Indicadores de caixa e estoque
   - Alertas e pendências

2. **Gráficos Interativos**
   - Gráfico de linha: evolução por período
   - Gráfico de pizza: status e distribuição

3. **Sistema de Notificações**
   - Alertas de vencimentos e pendências
   - Notificações de pedidos e atualizações

4. **Interface Customizada**
   - Cores e branding do PDV Ibix
   - Sidebar personalizada
   - Cards de estatísticas animados

## Banco de dados

O banco em uso é **PostgreSQL**.

- **Variáveis:** `DB_HOST`, `DB_PORT=5432`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`. Ver `.env.example` na raiz do projeto.
- **Conexão:** Configurada em `database/connection.py`.
- **Schema:** Criado por `scripts/create_all_pg.py`. Para alterações, use Alembic (`alembic revision`, `alembic upgrade head`).
- **Documentação:** Ver `MAPA_SISTEMA/INDICE.md` e `MAPA_SISTEMA/MAPA_DO_SISTEMA.md`.

## Próximos passos

1. **Implementar APIs REST** em `api/v1/`
2. **Criar modelos de dados** em `models/`
3. **Desenvolver serviços** em `services/`
4. **Configurar banco de dados** em `database/`
5. **Implementar autenticação** em `core/`

## Notas de desenvolvimento

- Todos os arquivos estão organizados dentro do diretório `app/`
- O template AdminKit original permanece em `static/` como referência
- Os arquivos customizados estão em `app/static/` e `app/templates/`
- A estrutura segue as melhores práticas do FastAPI
- Em produção, defina `SECRET_KEY` forte e única via variáveis de ambiente

---

**Versão:** 1.0.0  
**Data:** 24/07/2024  
**Status:** Estrutura base implementada 