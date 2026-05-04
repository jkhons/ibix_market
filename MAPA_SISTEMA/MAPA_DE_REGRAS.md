# MAPA DE REGRAS - PDV Ibix

## Visão Geral

Este documento consolida todas as regras, diretrizes e políticas do PDV Ibix. É a **fonte única de verdade** sobre regras e padrões. Inclui as regras obrigatórias para uso do Cursor/IA. **Desenvolvedor do produto:** Automscale.

---

## 0. REGRAS OBRIGATÓRIAS PARA CURSOR/IA

**Fonte única de verdade:** Considere `MAPA_DO_SISTEMA.md` para arquitetura e estrutura; `MAPA_DE_REGRAS.md` (este arquivo) para regras e padrões.

**Regras obrigatórias:**
1. NÃO contradiga o que está definido nos mapas de MAPA_SISTEMA.
2. NÃO recrie soluções já descartadas ou proibidas nos mapas.
3. Se houver ambiguidade, assuma o que está documentado no mapa correspondente.
4. Se algo necessário NÃO estiver no mapa, solicite explicitamente que ele seja atualizado.
5. Mantenha as soluções alinhadas ao padrão arquitetural existente.
6. Seja objetivo, técnico e evite explicações desnecessárias.
7. Sempre priorize reutilização de código e padrões já existentes.
8. NÃO proponha mudanças estruturais sem justificar e sem indicar atualização do mapa.
9. **Sem fallback (obrigatório):** NÃO usar valores ou comportamentos de fallback que mascaram erros ou dados ausentes. Se um dado for obrigatório e não existir, **lançar erro explícito** (HTTP 4xx/5xx, exceção) e **NÃO** retornar valor alternativo (ex.: `None`, string vazia, 0, lista vazia como substituto). Preferir falhar de forma visível e rastreável a ocultar falhas com fallbacks. Exceção: apenas onde o mapa ou contrato da API documentar explicitamente valor padrão permitido.

10. **Validade jurídica — Nunca publicar informação sem fluxo real:** NÃO exibir confirmação de venda, compra ou pagamento sem que o fluxo real (gateway, webhook, reconciliação) tenha confirmado. Ex.: página "Compra finalizada" só quando `status_pagamento = "pago"`; em retorno de gateway, validar estado real antes de qualquer mensagem de sucesso. Confirmação indevida gera responsabilidade jurídica.

**Hierarquia de acesso (obrigatória):** O sistema e os dados seguem sempre: **Superadministrador** (gerencia todos administradores e todo o sistema) → **Administrador** (gerencia apenas clientes alocados a ele, tabela `administrador_clientes`) → **Cliente Administrador** (Cliente do sistema = Empresa Fiscal; gerencia Subclientes e técnicos em **Minha equipe** somente) → **Subcliente** (Cliente da Empresa Fiscal, gerenciado pelo Cliente Administrador). Detalhes em `MAPA_RBAC.md`. **Isolamento Subcliente:** Um cliente final (Subcliente) não pode ver dados de outro cliente final; o escopo é obrigatório por `cliente_id` (token ou `areas_cliente`). **Regra:** **Cliente Administrador não acessa** `/usuarios` nem `/configuracoes` (apenas Superadministrador e Administrador). O card "Funções (Roles) e Permissões", a rota `/roles`, as rotas `/usuarios` e `/configuracoes` (e API `/api/v1/configuracoes`) são acessíveis **apenas** para Superadministrador e Administrador. **Minha equipe:** técnico pertence a um único Cliente Administrador; vínculo por email; Cliente Administrador não vê técnicos de outras organizações. Ver `MAPA_RBAC.md` (Apêndice B — Acesso por Role) e `MAPA_DE_API.md` § 11b.

**Modelo de negócio — Empresa Fiscal obrigatória:** O **Cliente Administrador (CA)** é o **cliente do SaaS** (quem paga a assinatura). A **Empresa Fiscal** é a empresa do CA e é **obrigatória**: é cadastrada no ato da assinatura; não existe possibilidade de não ter Empresa Fiscal — faz parte do sistema. Cada CA é um **tenant** próprio; a Empresa Fiscal é separada dos outros tenants. Em operações fiscais (criação de rascunho de nota a partir de venda, emissão de NF-e), usar **exclusivamente** a Empresa Fiscal do usuário (CA), obtida por `get_empresa_fiscal_empresa` / `get_empresa_fiscal_cliente_id`. **Sem fallback:** não usar "primeira empresa do escopo", "primeira empresa do cliente da venda" nem qualquer outra empresa que não seja a do CA.

**Regra fiscal:** Na emissão de notas (NF-e, NFC-e, NFS-e), o **emissor** é a Empresa Fiscal (Cliente Administrador) e o **destinatário** é o Subcliente.

**Segurança — senha do certificado A1 (empresa fiscal):** A senha do certificado A1 (campo `senha_certificado` da empresa fiscal) deve ser **criptografada em repouso** (ex.: Fernet com chave de ambiente). Não logar nem expor em respostas de API. Implementação em `app/services/payments/credentials.py`; uso em `app/api/v1/empresa.py` e no carregador de certificado fiscal (`app/services/fiscal/certificado.py`).

**Fluxo esperado:** Leia o mapa relevante (use `MAPA_SISTEMA/INDICE.md` para escolher qual) → Execute a tarefa → Se houver impacto estrutural, proponha atualização objetiva do mapa.

**Quando consultar cada mapa (sempre antes de implementar):**
- **MAPA_DO_SISTEMA.md** — arquitetura, banco de dados, módulos, auditoria, impacto de mudanças, deploy (Ap. D), etapas de desenvolvimento (Ap. E).
- **MAPA_DE_API.md** — criar/modificar endpoints, schemas, autenticação.
- **MAPA_DE_REGRAS.md** — regras de desenvolvimento, modais, template, segurança.
- **MAPA_RBAC.md** — permissões, roles, controle de acesso; **criar/alterar rotas HTML:** consultar Ap. A (performance, um contexto, request.state); Ap. B (acesso por role).

**Estrutura de documentação (apenas estes 5 arquivos + INDICE):**
- `MAPA_DO_SISTEMA.md` — Sistema + Banco de Dados + Auditoria + Impactos + Deploy (Ap. D) + Etapas (Ap. E) + Performance rotas HTML (ref. MAPA_RBAC Ap. A)
- `MAPA_DE_API.md` — APIs REST
- `MAPA_DE_REGRAS.md` — Regras e padrões (este arquivo)
- `MAPA_RBAC.md` — Controle de acesso; Ap. A Performance Auth/RBAC e rotas HTML (referência para novas rotas); Ap. B Acesso por Role
- `MAPA_PAGAMENTO.md` — Pagamento e assinatura
- `INDICE.md` — Índice para pesquisa (Cursor)

**Extensões Cursor/VS Code recomendadas:** **Obrigatórias:** Python, Pylance, GitLens, Thunder Client, PostgreSQL (ou DBeaver), Jinja. **Recomendadas:** Black Formatter, Flake8, Error Lens, Auto Rename Tag, Path Intellisense.

---

## 1. REGRAS CRÍTICAS DE DESENVOLVIMENTO

### Sistema em Desenvolvimento
- **Porta obrigatória:** 8000
- **Análise:** Sempre fazer análise diretamente na programação/script, NÃO no PowerShell
- **Ambiente:** Sistema em desenvolvimento ativo

### Proibições Absolutas
- ❌ **NUNCA** criar dados fictícios ou de exemplo
- ❌ **NUNCA** inventar informações para demonstração
- ❌ **NUNCA** usar dados simulados em produção
- ❌ **NUNCA** exibir confirmação de venda/pagamento sem fluxo real confirmado (validade jurídica)
- ✅ **SEMPRE** usar dados reais ou estruturas vazias

### Dados Hardcoded no Frontend - PROIBIDO

> **⚠️ CRÍTICO - NUNCA REPETIR ERROS**: Esta regra é FUNDAMENTAL e não pode ser ignorada. 
> Dados hardcoded causam:
> - Duplicação de elementos (ex: sidebar, breadcrumbs)
> - Inconsistência entre páginas
> - Dificuldade de manutenção
> - Violação de padrões arquiteturais
> 
> **Exemplos de violações comuns:**
> - ❌ Adicionar breadcrumb manual quando base.html já fornece estrutura
> - ❌ Duplicar sidebar ou navbar em templates filhos
> - ❌ Valores numéricos fixos (ex: `default=24`) em vez de buscar do banco
> - ❌ Arrays de opções hardcoded em JavaScript quando deveriam vir de API
> - ❌ Fallbacks hardcoded (ex: `if config else 24`) em vez de buscar do banco ou lançar erro
- ❌ **Regra obrigatória:** Sem fallback (ver seção 0) — não mascarar erros com valores alternativos

- ❌ **NUNCA** usar dados hardcoded (fixos) no código JavaScript/HTML do frontend
- ❌ **NUNCA** criar arrays, objetos ou listas de dados diretamente no código frontend
- ❌ **NUNCA** usar dados mockados ou estáticos no frontend para funcionalidades que requerem dados dinâmicos
- ✅ **SEMPRE** buscar dados do banco de dados através de APIs REST
- ✅ **SEMPRE** sugerir cadastro no banco de dados quando dados forem necessários
- ✅ **SEMPRE** aguardar aprovação antes de implementar soluções alternativas (ex: arquivos de configuração, cache, etc.)
- ✅ **SEMPRE** usar endpoints da API para obter dados dinâmicos
- **Exceções permitidas (apenas com aprovação explícita):**
  - Dados de configuração estática do sistema (ex: opções de enum, constantes de validação)
  - Mensagens de interface (textos, labels) - preferencialmente usar i18n
  - Dados temporários de sessão (não persistidos)
- **Fluxo obrigatório quando dados são necessários:**
  1. Identificar necessidade de dados
  2. Verificar se já existe tabela/entidade no banco de dados
  3. Se não existir, **SUGERIR** criação de tabela/entidade no banco
  4. **AGUARDAR APROVAÇÃO** antes de criar estrutura no banco
  5. Se aprovado, criar migração/script SQL e endpoint de API
  6. Implementar consumo da API no frontend
  7. Se não aprovado ou houver alternativa, **AGUARDAR APROVAÇÃO** para solução alternativa

### Notificação Obrigatória de Alterações
- **OBRIGATORIAMENTE** notificar ANTES de alterar qualquer arquivo de diretrizes
- **OBRIGATORIAMENTE** aguardar aprovação antes de implementar mudanças
- **OBRIGATORIAMENTE** atualizar TODOS os arquivos relacionados após aprovação
- **OBRIGATORIAMENTE** manter consistência entre todos os documentos
- **NUNCA** permitir informações conflitantes entre arquivos
- **SEMPRE** garantir que todas as diretrizes sigam o mesmo comportamento

### Consistência Entre Arquivos
- **TODOS os arquivos** devem seguir as mesmas regras e diretrizes
- **TODAS as informações** devem ser consistentes e não conflitantes
- **TODAS as alterações** devem ser refletidas em todos os arquivos relacionados
- **NUNCA** permitir divergências entre documentos de diretrizes
- **SEMPRE** verificar impacto em outros arquivos antes de alterar

### Testes e Verificações
- ❌ **NUNCA** criar scripts de teste sem permissão
- ✅ **SEMPRE** perguntar antes de implementar testes
- ✅ **Testes** são responsabilidade do usuário
- ❌ **NUNCA** executar verificações externas (banco, APIs, etc.)
- ✅ **SEMPRE** solicitar ao usuário para realizar verificações
- ✅ **Verificações** são responsabilidade do usuário

### Scripts
- ✅ **Apenas** em `Scripts_auxiliares/`
- ✅ **Nomenclatura:** snake_case com prefixos descritivos
- ✅ **Documentação:** Comentários obrigatórios

### Alteração de Arquivos
- **Alterar arquivos apenas se for necessário para a solicitação feita**
- **Em hipótese alguma alterar arquivos que não sejam os solicitados**

---

## 2. ESTRUTURA E TECNOLOGIAS OBRIGATÓRIAS

### Backend
- **Python 3.11+** com **FastAPI** obrigatório
- **PostgreSQL** (porta 5432)
- **SQLAlchemy 2.0** para ORM

### Banco de Dados
- **RBAC (Role-Based Access Control)** obrigatório para controle de acesso
- **Arquitetura SaaS Multi-Tenancy** obrigatória para escalabilidade
- **Isolamento de dados** por módulo obrigatório

### Frontend
- **HTML, CSS, JavaScript**
- **Bootstrap 5** para interface responsiva
- **Template PDV Ibix** baseado no AdminKit (OBRIGATÓRIO)
- **Jinja2** para templates
- **❌ PROIBIDO:** Dados hardcoded no frontend (ver seção "Dados Hardcoded no Frontend - PROIBIDO")
- **✅ OBRIGATÓRIO:** Todos os dados dinâmicos devem vir de APIs REST que consultam o banco de dados
- **✅ OBRIGATÓRIO:** Requisições REST no frontend devem usar `window.authenticatedFetch` para incluir cookie + `Authorization` e respeitar o `cliente_id` do token. A página Novo Processo (`novo_processo.html`) foi alinhada a esta regra: todas as chamadas à API usam `window.authenticatedFetch` (definido em `app/static/js/certipeso.js`).
- **Cookies de autenticação:** O backend (`main.py` add_user_to_request) e middleware (`app/core/middleware.py`) aceitam os cookies `pdv_solumatica_token` e `pdv_automscale_token` como alternativa ao Bearer para autenticação. Usado em rotas HTML (ex.: comprovante) e em fetch com `credentials: 'include'`.

### PWA dedicado do PDV (obrigatório para modo app)
- Escopo exclusivo do PDV: usar `manifest` e `service worker` apenas em `/negocio/venda/pdv`.
- Rotas oficiais: `GET /negocio/venda/pdv/manifest.webmanifest` e `GET /negocio/venda/pdv/sw.js`.
- Registro no frontend PDV deve ser feito por arquivo JS externo (`app/static/js/pdv-pwa.js`), sem JS inline.
- Estratégia de cache:
  - `cache-first` para estáticos do PDV (`/static/css/pdv.css`, scripts do PDV, ícones);
  - `network-first` para navegação HTML do PDV;
  - APIs (`/api/`) sempre em rede (sem fallback de dados para não mascarar erro de negócio).
- Meta tags para tela cheia em mobile/tablet são obrigatórias na página PDV (`theme-color`, `apple-mobile-web-app-capable`, `viewport-fit=cover`).

### Integrações multipropósito por tenant (Fase 5)
- Eventos de integração externa devem operar sempre no contexto do `tenant_id` (isolamento obrigatório).
- Configurações de webhook de integração não podem ser globais quando o evento for de negócio do tenant.
- Para evento `venda.fechada`, usar chaves segregadas por tenant e validação explícita de `tenant_id`.
- **Sem fallback obrigatório:** integração habilitada sem URL/token necessário deve falhar com erro explícito (HTTP 4xx), sem mascarar com valores padrão.
- Envio para sistemas externos deve ser assíncrono (worker) e com política de retentativa controlada.

### Formatação de datas no frontend (data-only, fuso horário)

> **Problema:** Em JavaScript, `new Date('YYYY-MM-DD')` interpreta a string como **meia-noite UTC**. Em fusos como Brasil (UTC-3), isso vira o dia anterior às 21h, e `toLocaleDateString('pt-BR')` exibe o dia errado (ex.: 28/01 vira 27/01).

- **✅ OBRIGATÓRIO** para campos **apenas data** (sem hora) vindos da API: usar **`formatarDataApenas(dataStr)`** (definida em `app/static/js/certipeso.js` e disponível como `window.formatarDataApenas`).
- **✅** A função formata `YYYY-MM-DD` em `dd/mm/yyyy` por split da string, **sem** usar `new Date(str)`, evitando deslocamento de dia.
- **❌ NUNCA** usar `new Date(campo_data).toLocaleDateString('pt-BR')` quando o valor é apenas data (ex.: `data_agendamento`, `data_inicio`, `data_fim`, `data_emissao`, `data_validade`).
- **Exceção:** Para strings **com hora** (datetime, ex.: `created_at`, `data_hora`), pode-se usar `new Date(str).toLocaleString('pt-BR')`. Se a string for só `YYYY-MM-DD`, usar `new Date(str + 'T12:00:00')` antes de formatar para evitar virada de dia.
- **Referência:** MAPA_DO_SISTEMA.md – seção "Formatação de datas no frontend"; arquivos já corrigidos: agendamento.js, dashboard.html, novo_processo.html, contratos, procedimentos, ordem_de_servico, vendas, notas_fiscais.js, certificados-peso/auxiliares, equipamentos.js, inspetores-aprovadores.js, etc.

### Padrão de Modais - OBRIGATÓRIO
**⚠️ PROBLEMA RECORRENTE:** Modais Bootstrap (`modal fade`, `data-bs-dismiss`, `bootstrap.Modal`) causam problemas de herança, dependências e não centralizam corretamente na tela.

**✅ PADRÃO OBRIGATÓRIO - Modais Independentes com CSS Inline:**

> **ATENÇÃO CRÍTICA**: Todos os modais DEVEM usar CSS inline diretamente nos elementos HTML. NÃO usar classes CSS externas, NÃO usar Bootstrap Modal API, NÃO herdar configurações de outros modais.

1. **Estrutura HTML com CSS Inline:**
   ```html
   <div id="modal{Nome}Custom" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5); z-index: 10000;">
       <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); background: white; border-radius: 8px; width: 95%; max-width: 900px; max-height: 95vh; overflow-y: auto; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3); display: flex; flex-direction: column;">
           <div style="background: linear-gradient(135deg, #3498db 0%, #2980b9 100%); color: white; padding: 20px 30px; border-radius: 8px 8px 0 0; display: flex; justify-content: space-between; align-items: center;">
               <h3 style="margin: 0; font-size: 1.5rem; font-weight: 700;">Título do Modal</h3>
               <button onclick="fecharModal{Nome}()" style="background: rgba(255, 255, 255, 0.25); border: none; color: white; font-size: 32px; line-height: 1; width: 44px; height: 44px; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center;">×</button>
           </div>
           <div style="padding: 30px; overflow-y: auto; flex: 1; background: #f8f9fa;">
               <!-- Conteúdo do modal -->
           </div>
           <div style="background: #f8f9fa; padding: 20px 30px; border-radius: 0 0 8px 8px; border-top: 2px solid #e9ecef; display: flex; justify-content: flex-end;">
               <button onclick="fecharModal{Nome}()" style="padding: 10px 24px; border: none; border-radius: 8px; font-weight: 600; font-size: 15px; cursor: pointer; background: #6c757d; color: white;">
                   Fechar
               </button>
           </div>
       </div>
   </div>
   ```

2. **JavaScript Obrigatório:**
   ```javascript
   function abrirModal{Nome}() {
       const modal = document.getElementById('modal{Nome}Custom');
       if (modal) {
           modal.style.display = 'block';
           document.body.style.overflow = 'hidden';
       }
   }
   
   function fecharModal{Nome}() {
       const modal = document.getElementById('modal{Nome}Custom');
       if (modal) {
           modal.style.display = 'none';
           document.body.style.overflow = '';
       }
   }
   ```
   - **Quando o script estiver dentro de uma IIFE** `(function() { ... })();`, os botões "×" e "Fechar" com `onclick="fecharModal{Nome}()"` avaliam no escopo global e não encontram a função. **Obrigatório:** expor as funções de fechar (e abrir, se usadas em onclick) no `window`, por exemplo: `window.fecharModalProduto = fecharModalProduto; window.fecharModalCustos = fecharModalCustos;`. Referência: `app/templates/meu_negocio/entrada_nfe/conciliar.html` (modais de conciliação NFe).

3. **Características Obrigatórias:**
   - ✅ **CSS Inline**: Todos os estilos devem estar inline (`style="..."`) diretamente nos elementos
   - ✅ **Centralização**: Usar `position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%)` para centralizar
   - ✅ **Overlay fixo**: `position: fixed` com `width: 100%; height: 100%` cobrindo toda a tela
   - ✅ **Z-index alto**: `z-index: 10000` para garantir que apareça acima de tudo
   - ✅ **Controle via display**: Usar `style.display = 'block'/'none'` ao invés de classes
   - ✅ **Bloqueio de scroll**: `document.body.style.overflow = 'hidden'` ao abrir

4. **Regras Críticas:**
   - ❌ **NUNCA** usar `modal fade`, `data-bs-dismiss`, `bootstrap.Modal.getOrCreateInstance()`
   - ❌ **NUNCA** usar classes CSS externas (`.modal-*-overlay`, etc.)
   - ❌ **NUNCA** usar `classList.add('active')` ou `classList.remove('active')`
   - ❌ **NUNCA** herdar configurações CSS de outros modais ou templates
   - ✅ **SEMPRE** usar CSS inline direto nos elementos (`style="..."`)
   - ✅ **SEMPRE** usar `style.display = 'block'` para abrir e `style.display = 'none'` para fechar
   - ✅ **SEMPRE** centralizar usando `transform: translate(-50%, -50%)`
   - ✅ **SEMPRE** bloquear scroll do body ao abrir (`overflow: hidden`)

5. **Vantagens do Padrão:**
   - ✅ **Independência do Bootstrap** - Não depende de `bootstrap.Modal`
   - ✅ **Performance** - Menos dependências JavaScript, código mais leve
   - ✅ **Customização** - Estilos inline facilitam customização
   - ✅ **Consistência** - Segue o padrão já estabelecido no sistema
   - ✅ **Manutenibilidade** - Código mais simples e direto

5.1. **Modal de aviso com duração fixa:** Para avisos que devem sumir sozinhos (ex.: erro 422 pesos vencidos), usar o mesmo padrão (CSS inline, id `modal{Nome}Custom`) e fechar automaticamente com `setTimeout(fecharModal{Nome}, 2000)`. Exemplo no sistema: **Modal "Pesos padrão vencidos"** (id: `modalPesosVencidosCustom`) – exibido por 2 segundos quando a API retorna 422 por pesos vencidos; título "Pesos padrão vencidos", body com mensagem da API; ver `app/templates/procedimentos/novo_processo.html` e `app/static/js/pesos_ensaios_mobile.js`.

6. **Exemplo Completo de Implementação:**
   ```html
   <!-- Modal Exemplo -->
   <div id="modalExemploCustom" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5); z-index: 10000;">
       <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); background: white; border-radius: 8px; width: 95%; max-width: 900px; max-height: 95vh; overflow-y: auto; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3); display: flex; flex-direction: column;">
           <!-- Header -->
           <div style="background: linear-gradient(135deg, #3498db 0%, #2980b9 100%); color: white; padding: 20px 30px; border-radius: 8px 8px 0 0; display: flex; justify-content: space-between; align-items: center;">
               <h3 style="margin: 0; font-size: 1.5rem; font-weight: 700;">Título do Modal</h3>
               <button onclick="fecharModalExemplo()" style="background: rgba(255, 255, 255, 0.25); border: none; color: white; font-size: 32px; line-height: 1; width: 44px; height: 44px; border-radius: 50%; cursor: pointer;">×</button>
           </div>
           <!-- Body -->
           <div style="padding: 30px; overflow-y: auto; flex: 1; background: #f8f9fa;">
               <!-- Conteúdo do modal -->
           </div>
           <!-- Footer -->
           <div style="background: #f8f9fa; padding: 20px 30px; border-radius: 0 0 8px 8px; border-top: 2px solid #e9ecef; display: flex; justify-content: flex-end;">
               <button onclick="fecharModalExemplo()" style="padding: 10px 24px; border: none; border-radius: 8px; font-weight: 600; font-size: 15px; cursor: pointer; background: #6c757d; color: white;">Fechar</button>
           </div>
       </div>
   </div>

   <script>
   function abrirModalExemplo() {
       const modal = document.getElementById('modalExemploCustom');
       if (modal) {
           modal.style.display = 'block';
           document.body.style.overflow = 'hidden';
       }
   }
   
   function fecharModalExemplo() {
       const modal = document.getElementById('modalExemploCustom');
       if (modal) {
           modal.style.display = 'none';
           document.body.style.overflow = '';
       }
   }
   
   // Fechar modal ao clicar fora dele
   document.addEventListener('DOMContentLoaded', function() {
       const modal = document.getElementById('modalExemploCustom');
       if (modal) {
           modal.addEventListener('click', function(e) {
               if (e.target === modal) {
                   fecharModalExemplo();
               }
           });
       }
   });
   </script>
   ```

**Referência:** Este padrão foi estabelecido após correção de modais de equipamentos. Ver histórico em: `Diretrizes/CORRECAO_MODAIS_EQUIPAMENTOS.md`

### Estrutura de Diretórios
- ✅ **Todos os arquivos** devem estar dentro de `app/`
- ✅ **Scripts auxiliares** apenas em `Scripts_auxiliares/`

---

## 3. TEMPLATE CERTIPESO - ESTRUTURA OBRIGATÓRIA

### Página Modelo Obrigatória
- ✅ **`/dashboard`** é a página modelo padrão para todo o sistema
- ✅ **TODAS as páginas** devem seguir rigorosamente o padrão visual do dashboard
- ✅ **Estrutura HTML, CSS e componentes** devem ser idênticos
- ✅ **Botões, forms, cards, icons, charts** devem seguir o mesmo padrão
- ✅ **Responsividade e UX/UI** devem ser uniformes em todo o sistema
- ✅ **Cores dos cabeçalhos:** Sempre usar gradiente do sidebar (`linear-gradient(180deg, #2c3e50, #34495e)`)
- ✅ **Alinhamento de botões:** Usar flexbox (`d-flex flex-column` + `mt-auto`) para garantir alinhamento consistente

### Implementação Obrigatória
- ✅ **Copiar EXATAMENTE** a estrutura do `dashboard.html` modelo
- ✅ **Manter consistência visual** em todos os módulos
- ✅ **Aplicar o mesmo padrão** para todas as páginas específicas
- ✅ **Componentes Bootstrap** devem ter o mesmo estilo e comportamento

### Template PDV Ibix - Estrutura obrigatória

### Template Base
- ✅ **TODAS as páginas** devem herdar de `app/templates/base.html`
- ✅ **Sidebar, Navbar, Footer** obrigatórios em todas as páginas
- ✅ **Branding "PDV Ibix"** em todo o sistema
- ✅ **Templates específicos** para cada sistema (certificacao/base.html, monitoramento/base.html)

### Componentes Obrigatórios do Template

**✅ SIDEBAR (Menu Lateral):**
- Logo/Brand: "PDV Ibix" (obrigatório)
- Navegação: Links para todos os módulos
- Seções: Pages, Tools & Components, Plugins & Addons
- Responsivo: Colapsa em telas menores
- Toggle: Botão hamburger funcional

**✅ NAVBAR SUPERIOR:**
- Botão Hamburger: Toggle da sidebar (obrigatório)
- Notificações: Dropdown com alertas do sistema
- Mensagens: Dropdown com mensagens
- Perfil: Dropdown do usuário logado

**✅ CONTEÚDO PRINCIPAL:**
- Breadcrumbs: Navegação hierárquica
- Cards: Containers para conteúdo
- Tabelas: Listagens de dados
- Formulários: Entrada de dados

**✅ FOOTER:**
- Copyright: "PDV Ibix - Sistema de gerenciamento de Certificados e processos @ 2023"
- Links: Suporte, Central de Ajuda, Privacidade, Termos

### Arquivos CSS e JavaScript Obrigatórios

**CSS:**
```html
<link href="/static/css/dashboard.css" rel="stylesheet">
<link href="/static/css/certipeso.css" rel="stylesheet">
```

**JavaScript:**
```html
<script src="/static/js/app.js"></script>
<script src="/static/js/dashboard.js"></script>
<script src="/static/js/certipeso.js"></script>
```

**Nota:** O `dashboard.css` e `app.js` são baseados no AdminKit, mas o `certipeso.css` e `certipeso.js` contêm todas as customizações específicas do PDV Ibix.

**Página Novo Processo (`/procedimentos/novo-processo`):** Além dos CSS obrigatórios, a página usa `novo-processo-mobile.css`, `novo-processo-stepper.css` e `novo-processo-form.css` para stepper, etapas e formulário (pesos/ensaios, accordion). O CSS dos modais desta página permanece no próprio template (inline ou bloco `<style>`), em conformidade com o Padrão de Modais obrigatório.

---

### Arquivos CSS Obrigatórios
```html
<link href="/static/css/dashboard.css" rel="stylesheet">
<link href="/static/css/certipeso.css" rel="stylesheet">
```

### Arquivos JavaScript Obrigatórios
```html
<script src="/static/js/app.js"></script>
<script src="/static/js/dashboard.js"></script>
<script src="/static/js/certipeso.js"></script>
```

---

## 3.B MARKETPLACE — IDENTIDADE VISUAL ÚNICA (Vitrine Web + App Mobile)

> O **Marketplace** (vitrine pública + app mobile consumidor final) tem identidade visual SEPARADA do painel admin/PDV. As duas identidades coexistem por design e NÃO se misturam.

### 3.B.1 Painel admin (PDV) vs. Marketplace (consumidor final)

| Sistema | Identidade | Quem usa | Fonte canônica |
|---|---|---|---|
| **Painel admin / PDV** | Azul institucional (`#2c3e50`/`#34495e` em gradient) | Lojistas, operadores | `app/templates/base.html`, `app/static/css/dashboard.css` |
| **Marketplace (Vitrine + App)** | Off-white / azul-ardósia / verde-musgo / terracota / dourado (paleta artesanal premium) | Consumidor final | `app/static/css/loja.css` (tokens `--ibix-*`) |

NUNCA aplique tokens do PDV no Marketplace ou vice-versa. Eles são produtos diferentes para públicos diferentes.

### 3.B.2 Vitrine web é a fonte canônica

**`app/static/css/loja.css` (tokens `--ibix-*`) é a ÚNICA fonte de verdade visual do Marketplace.** O app mobile (`mobile_marketplace/`) **espelha** esses tokens em `theme/colors.ts`, `theme/typography.ts`, `theme/spacing.ts` e `theme/shadows.ts`.

**Mudanças visuais começam pela vitrine.** Se uma cor, fonte, radius ou sombra precisa mudar, o time muda primeiro em `loja.css`/`base_loja.html`, e o app espelha em seguida no mesmo PR.

### 3.B.3 Brand assets (logo Ibix Market)

**Fonte canônica do logo:**
- `app/static/img/ibix/cab.png` — logo do header da vitrine
- `app/static/img/ibix/rodape.png` — variante para fundos escuros
- `app/static/img/landing/logoSfundo.png` — logo institucional (Open Graph, JSON-LD, ícone do app)

**No app mobile** os logos vivem em `mobile_marketplace/assets/brand/` como **cópia bit-a-bit** dos arquivos da vitrine. **NUNCA recriar o logo no Figma/Photoshop local.** Quando a vitrine atualizar `cab.png`, copie para o app no mesmo PR.

**Renderização:** o componente `<BrandLogo>` (`mobile_marketplace/components/common/BrandLogo.tsx`) é o ÚNICO ponto de exibição do logo no app. Onde antes havia "Ibix Market" como texto, agora aparece o logo gráfico.

### 3.B.4 Naming nas lojas (App Store / Play Store)

| Item | Valor |
|---|---|
| **Display name nas lojas e no springboard** | **`Ibix`** (curto, marca-mãe) |
| **Brand visível dentro do app e na vitrine pública** | **`Ibix Market`** (logo `cab.png`) |
| `expo.name` (`mobile_marketplace/app.json`) | `Ibix` |
| `slug` Expo | `ibix-market` (interno, não muda) |
| `bundleIdentifier` iOS | `com.ibix.market` (já publicado, não muda) |
| `package` Android | `com.ibix.market` |
| `scheme` deep link | `ibixmarket://` |
| ASO Apple App Name | `Ibix` |
| ASO Google Play App Name | `Ibix` |

**Os dois nomes coexistem por design** — não tente unificar. Justificativa: nas lojas o "Ibix" curto reforça a marca-mãe; dentro do app o "Ibix Market" mantém paridade com o `<title>` da vitrine (`{block} | Ibix`) e com o domínio `ibix.com.br`.

### 3.B.5 Tokens críticos (resumo)

| Token | Hex | Origem |
|---|---|---|
| `bg` | `#FEF7F1` | `--ibix-bg` |
| `text` | `#4A627A` | `--ibix-text` |
| `textStrong` | `#2F3A44` | `--ibix-text-strong` |
| `action` | `#5C6E4A` | `--ibix-action` (verde-musgo, CTA) |
| `accent` | `#C47A44` | `--ibix-hover` (terracota, focus, destaque) |
| `premium` | `#D9B48B` | `--ibix-premium` (dourado) |
| **Tipografia** | Poppins | `loja.css:1394` |
| **Radii** | 8 / 10 / 14 | `btn-primary` / `loja-search-form` / `loja-section-block` |
| **Focus-ring** | 2px sólido `#C47A44`, offset 2 | `loja-header *:focus-visible` |

### 3.B.6 Documentação relacionada

- `app/static/css/loja.css` — fonte canônica de tokens
- `mobile_marketplace/AGENTS.md` § 6 e § 8.1 — regras detalhadas para o app
- `MAPA_SISTEMA/PLANO_APP_MOBILE_MARKETPLACE.md` — Fase 1.3 (Design System) e Fase 7.2 (ASO)

---

## 4. SEGURANÇA HTML - REGRAS OBRIGATÓRIAS

### Proteção Contra XSS (Cross-Site Scripting)

**✅ Escape de Conteúdo Dinâmico:**
```html
<!-- ✅ CORRETO -->
<p>{{ variavel | e }}</p>
<div>{{ conteudo_usuario | e }}</div>

<!-- ❌ INCORRETO -->
<p>{{ variavel }}</p>
<div>{{ conteudo_usuario }}</div>
```

**✅ Proteção em Scripts:**
```html
<!-- ✅ CORRETO -->
<script>
    var dados = {{ dados_json | tojson | safe }};
</script>

<!-- ❌ INCORRETO -->
<script>
    var dados = "{{ dados_dinamicos }}";
</script>
```

**Regras Obrigatórias:**
- **SEMPRE** usar `{{ variavel | e }}` para conteúdo dinâmico
- **NUNCA** inserir dados não sanitizados em scripts
- Usar `| tojson | safe` para dados JSON em JavaScript
- Validar e sanitizar todos os inputs do usuário

**Conteúdo dinâmico gerado em JavaScript (HTML injetado):**
- **NUNCA** injetar JSON ou objetos em atributos HTML (ex.: `onclick="funcao(${JSON.stringify(obj)})"`) — risco de XSS.
- **SEMPRE** usar identificador seguro (ex.: `data-equipamento-id="${id}"`) no HTML e **event delegation** no container; no handler, obter o objeto em memória (ex.: `todosEquipamentos.find(e => e.id === id)`) e chamar a função com o objeto.
- Referência de implementação: `app/templates/procedimentos/novo_processo.html` (botão "Configurar" nos cards mobile de equipamentos: `data-action="configurar-equipamento"` + `data-equipamento-id` + listener delegado em `#equipamentosCardsMobile`).

### Proteção contra clickjacking (embed em iframe)
- **base.html** deve incluir no `<head>`: `<meta http-equiv="Content-Security-Policy" content="frame-ancestors 'self';">` para restringir que a página seja embutida em iframes de outros origens.
- Alternativa: configurar header HTTP `X-Frame-Options: SAMEORIGIN` ou CSP `frame-ancestors 'self'` no servidor (Nginx/Gunicorn).

### Proteção Contra CSRF (Cross-Site Request Forgery)

**✅ Token CSRF em Todos os Formulários:**
```html
<form method="POST" action="/endpoint">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
    <!-- outros campos do formulário -->
</form>
```

**Implementação no FastAPI:**
```python
from fastapi_csrf_protect import CsrfProtect

@app.post("/endpoint")
async def endpoint(request: Request, csrf_protect: CsrfProtect = Depends()):
    csrf_protect.validate_csrf(request)
    # processar formulário
```

### Controle de Permissões no Frontend

**✅ Controle de Permissões por Botão:**
```html
<!-- ✅ Exemplo: Botão de Edição -->
{% if current_user.role == 'Administrador' %}
    <a href="/usuarios/editar/{{ usuario.id }}" class="btn btn-warning">
        <i class="fas fa-edit"></i> Editar
    </a>
{% endif %}

<!-- ✅ Exemplo: Botão de Exclusão -->
{% if current_user.role in ['Administrador', 'Operador'] %}
    <button class="btn btn-danger" onclick="confirmarExclusao({{ item.id }})">
        <i class="fas fa-trash"></i> Excluir
    </button>
{% endif %}
```

**✅ Controle de Menus:**
```html
<!-- ✅ Menu Administrativo -->
{% if current_user.role == 'Administrador' %}
    <li class="sidebar-item">
        <a href="/admin/usuarios" class="sidebar-link">
            <i class="fas fa-users"></i> Gerenciar Usuários
        </a>
    </li>
{% endif %}
```

### Sidebar Dinâmica por Perfil

**✅ Estrutura da Sidebar:**
- Dashboard - Todos os usuários
- Módulos Administrativos - Apenas Administrador
- Módulos Operacionais - Administrador e Operador
- Área do Cliente - Apenas Cliente

**Ver detalhes completos em:** [MAPA_RBAC.md - Permissões por Nível](MAPA_RBAC.md#permissões-por-nível)

### Verificação de Autenticação

**✅ Controle de Sessão Obrigatório:**
```html
{% if not current_user.is_authenticated %}
    <script>window.location.href = '/login';</script>
{% endif %}
```

**Proteção de Rotas:**
- Verificar se o usuário está autenticado antes de renderizar qualquer página
- Caso contrário, redirecionar automaticamente para `/login`
- Implementar middleware de autenticação no FastAPI

### Validações Obrigatórias

**✅ Checklist de Segurança para Cada Página:**
- [ ] Herda de `base.html`
- [ ] Verifica autenticação do usuário
- [ ] Escapa conteúdo dinâmico com `| e`
- [ ] Usa tokens CSRF em formulários
- [ ] Controla permissões por botão/menu
- [ ] Registra logs de acesso

**✅ Checklist para Cada Endpoint:**
- [ ] Valida token JWT
- [ ] Verifica permissões do usuário
- [ ] Sanitiza inputs
- [ ] Registra logs de auditoria
- [ ] Retorna códigos HTTP apropriados

**✅ Checklist para Cada Formulário:**
- [ ] Inclui token CSRF
- [ ] Valida dados no frontend
- [ ] Valida dados no backend
- [ ] Registra alterações

### ⚠️ AVISOS IMPORTANTES

**🚨 NUNCA FAZER:**
- ❌ Renderizar conteúdo não escapado
- ❌ Confiar apenas na validação do frontend
- ❌ Expor tokens ou chaves secretas no HTML
- ❌ Expor token JWT em access log / syslog (URLs com `?token=eyJ...` devem ser redigidas)
- ❌ Permitir acesso sem verificar permissões
- ❌ Esquecer de registrar logs de auditoria

**✅ SEMPRE FAÇA:**
- ✅ Validar dados no backend
- ✅ Escapar conteúdo dinâmico
- ✅ Verificar permissões em cada endpoint
- ✅ Usar HTTPS em produção
- ✅ Manter logs de auditoria
- ✅ Redigir parâmetro token em logs (uso de `RedactTokenFilter` em uvicorn/gunicorn access log)
- ✅ Implementar timeout de sessão

---

## 5. SISTEMA DUAL OBRIGATÓRIO

### Visão Geral
Sistema de acesso separado com dois módulos independentes e permissões completamente isoladas:
- **PDV Ibix Certificação** - Sistema de certificação de balanças
- **PDV Ibix Monitoramento Térmico** - Sistema de monitoramento de temperatura e umidade

### Arquitetura de Banco Obrigatória
- **RBAC (Role-Based Access Control)** implementado conforme especificações
- **Multi-Tenancy SaaS** para isolamento e escalabilidade
- **Separação de dados** por módulo e tenant obrigatória

### Página Inicial Obrigatória
- **index.html** deve apresentar dois cards de seleção
- **Card Certificação** - Link para `/certificacao/dashboard`
- **Card Monitoramento Térmico** - Link para `/monitoramento/dashboard`
- **Interface responsiva** com Bootstrap 5
- **Branding PDV Ibix** em ambos os sistemas

### Permissões Completamente Isoladas
- **Usuários separados** por sistema (não compartilhados)
- **Roles independentes** para cada módulo
- **Sessões isoladas** com cookies diferentes
- **Middleware de autenticação** separado por sistema
- **Dados nunca compartilhados** entre os sistemas
- **RBAC implementado** conforme especificações
- **Multi-tenancy** para isolamento por cliente/empresa

### Estrutura de URLs Obrigatória
- **Certificação:** `/certificacao/*` (todas as rotas)
- **Monitoramento Térmico:** `/monitoramento/*` (todas as rotas)
- **Prefixo obrigatório** em todas as APIs e templates
- **Redirecionamento automático** para sistema correto

---

## 6. SISTEMA RBAC E NÍVEIS ADMINISTRATIVOS

### Hierarquia de Níveis Obrigatória
1. **SUPER_ADMIN** (Nível 1) - Administrador do Sistema
   - Acesso total ao sistema
   - Gerenciamento de todos os tenants
   - Configurações globais
   - Auditoria completa

2. **TENANT_ADMIN** (Nível 2) - Administrador Cliente
   - Gerenciamento do próprio tenant
   - Usuários e permissões do tenant
   - Configurações do tenant
   - Relatórios e analytics

3. **TENANT_MANAGER** (Nível 3) - Gerente Cliente
   - Gerenciamento de processos
   - Configurações operacionais
   - Relatórios de equipe
   - Aprovações de operações

4. **TENANT_OPERATOR** (Nível 4) - Operador Cliente
   - Operações diárias
   - Criação de certificados e aferições
   - Visualização de dados
   - Relatórios básicos

5. **TENANT_VIEWER** (Nível 5) - Visualizador Cliente
   - Apenas visualização
   - Relatórios de leitura
   - Sem modificações
   - Acesso restrito

### Permissões por Nível

#### SUPER_ADMIN
- tenant: [create, read, update, delete, manage]
- user: [create, read, update, delete, manage]
- system: [configure, monitor, backup, restore]
- audit: [full_access, export, analyze]

#### TENANT_ADMIN
- tenant: [read, update, configure]
- user: [create, read, update, delete, manage]
- certificacao: [full_access, export, backup]
- reports: [full_access, schedule, share]

#### TENANT_MANAGER
- certificacao: [approve, monitor, report]
- processos: [create, read, update, manage]
- afericoes: [read, export, limited_update] *(API afericoes removida; usar contratos/agendamentos)*
- reports: [read, create, schedule]

#### TENANT_OPERATOR
- certificacao: [create, read, update]
- afericoes: [create, read, update] *(API removida; usar contratos/agendamentos)*
- equipamentos: [read, create, limited_update]
- clientes: [read, create, limited_update]

#### TENANT_VIEWER
- certificacao: [read_only]
- afericoes: [read_only] *(API removida; usar contratos/agendamentos)*
- equipamentos: [read_only]
- clientes: [read_only]
- dashboard: [view_only]

---

## 7. REGRAS DE SEGURANÇA E CHECKLIST CRÍTICO

### Checklist de Segurança Crítico - Ação Imediata (ANTES DE PRODUÇÃO)

**🔴 CRÍTICO - Ação Imediata:**

- [ ] **1. Criar arquivo .env com SECRET_KEY segura**
  ```bash
  # Rodar o script:
  python Scripts_auxiliares/gerar_secret_key.py
  
  # OU gerar manualmente:
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```

- [ ] **2. Adicionar .env ao .gitignore**
  ```bash
  echo ".env" >> .gitignore
  echo "*.env" >> .gitignore
  echo ".env.*" >> .gitignore
  ```

- [ ] **3. Configurar cookies seguros para produção**
  ```python
  # Editar: app/api/v1/auth.py linha 70
  secure=True,          # Mudar de False para True
  samesite="strict",    # Mudar de "lax" para "strict"
  httponly=True,        # Já está correto
  ```

- [ ] **4. Configurar DATABASE_URL no .env**
  ```env
  DATABASE_URL=postgresql://usuario:senha@host:5432/pdv_solumatica
  ```

**🟡 IMPORTANTE - Esta Semana:**

- [ ] **5. Implementar Rate Limiting**
  ```bash
  pip install slowapi
  ```
  - Limitar login: 5 tentativas/minuto
  - Limitar APIs: 60 requisições/minuto

- [ ] **6. Implementar Refresh Token**
  - Criar tabela `refresh_tokens`
  - Endpoint `/auth/refresh`
  - Validade: 7 dias

- [ ] **7. Adicionar Auditoria Básica**
  - Criar tabela `audit_logs`
  - Registrar: login, logout, mudanças críticas
  - Armazenar: user_id, action, timestamp, ip

**🟢 RECOMENDADO - Este Mês:**

- [ ] **8. Aplicar permissões granulares**
  - Mapear todas as rotas
  - Usar `require_permission("modulo.acao")`
  - Testar todos os cenários

- [ ] **9. Password Policy**
  - Mínimo 8 caracteres
  - Letras + números + especiais
  - Validação frontend + backend

- [ ] **10. Two-Factor Authentication (2FA)**
  - TOTP (Google Authenticator)
  - Obrigatório para administradores

### Proteção Swagger - Documentação da API

**Status:** ✅ IMPLEMENTADO

A documentação da API está **PROTEGIDA** e requer autenticação com role **Administrador**.

**Antes (INSEGURO):**
```
❌ /docs             → Aberto para qualquer um
❌ /redoc            → Aberto para qualquer um
❌ /openapi.json     → Aberto para qualquer um
```

**Depois (SEGURO):**
```
✅ /docs             → Requer autenticação + Role Administrador
✅ /redoc            → Requer autenticação + Role Administrador
✅ /openapi.json     → Requer autenticação + Role Administrador
```

### Como Acessar a Documentação

#### 1. Fazer Login como Administrador

```bash
POST /api/v1/auth/token
Content-Type: application/x-www-form-urlencoded

username=admin@ibix.com.br
password=sua_senha
```

**Resposta:**
```json
{
  "success": true,
  "token": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "token_type": "bearer"
  },
  "user": {
    "role_nome": "Administrador"
  }
}
```

#### 2. Acessar Swagger com Token

**Via Postman/Insomnia:**
```http
GET https://pdv.ibix.com.br/docs
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

**Via CURL:**
```bash
curl -H "Authorization: Bearer SEU_TOKEN_AQUI" \
     https://pdv.ibix.com.br/docs
```

### Roles que Têm Acesso

| Role | `/docs` | `/redoc` | `/openapi.json` |
|------|---------|----------|-----------------|
| **Administrador Master** | ✅ | ✅ | ✅ |
| Administrador Cliente | ❌ | ❌ | ❌ |
| Técnico | ❌ | ❌ | ❌ |
| Cliente | ❌ | ❌ | ❌ |
| Sem login | ❌ | ❌ | ❌ |

### Para Desenvolvedor Terceirizado (Mobile)

**❌ NÃO forneça acesso ao Swagger em produção**

Em vez disso, forneça:

1. **URL base da API:**
   ```
   https://pdv.ibix.com.br/api/v1
   ```

2. **Documentação estática** (Postman Collection, PDF ou Markdown)

3. **Credenciais de teste** para ambiente de HOMOLOGAÇÃO:
   ```
   Homolog: https://homolog.ibix.com.br/docs
   Email: admin@ibix.com.br
   Senha: [fornecer senha de homolog]
   ```

4. **Instruções claras sobre endpoints** (ver GUIA_DESENVOLVEDOR_MOBILE.md)

### Configuração de Ambiente

**Variáveis de Ambiente Necessárias:**
```bash
# .env
SECRET_KEY=sua_chave_super_secreta_aqui
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
DATABASE_URL=postgresql://user:pass@localhost:5432/pdv_solumatica
ENVIRONMENT=production  # ou development
```

**Arquivos de Configuração:**
- 📄 `Scripts_auxiliares/ENV_TEMPLATE.env` - Template completo com todas as variáveis
- 🔧 `Scripts_auxiliares/gerar_secret_key.py` - Gera SECRET_KEY segura e cria .env

**Como Configurar:**

**Opção 1: Usar Script Automático**
```bash
python Scripts_auxiliares/gerar_secret_key.py
```

**Opção 2: Manual**
```bash
# 1. Copiar template
cp Scripts_auxiliares/ENV_TEMPLATE.env .env

# 2. Gerar SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 3. Editar .env com suas configurações
nano .env
```

**Validação do .env:**
```bash
# Verificar se .env existe
test -f .env && echo "✅ .env existe" || echo "❌ .env não encontrado"

# Verificar se está no .gitignore
grep -q "\.env" .gitignore && echo "✅ .env no .gitignore" || echo "❌ Adicionar .env ao .gitignore"

# Verificar SECRET_KEY
grep "SECRET_KEY" .env | grep -qv "change_in_production" && echo "✅ SECRET_KEY personalizada" || echo "⚠️ SECRET_KEY padrão (trocar!)"
```

### Regras de Segurança Mobile

**Storage de Dados:**
- Token → Secure Storage (criptografado)
- Dados do usuário → SharedPreferences (JSON)

**Timeout:**
- Timeout de requisições: 30 segundos
- Configurar timeout em todas as requisições HTTP

**Tratamento de Erros:**
- 401 → Redirecionar para login
- 403 → Mostrar mensagem de permissão negada
- 500 → Mostrar mensagem de erro de conexão

**Validações:**
- Validação client-side obrigatória
- Validação backend obrigatória (nunca confiar apenas no frontend)

**Referência:** Ver `Scripts_auxiliares/SEGURANCA_COMPLETA.md` para documentação completa de segurança

---

## 7. REGRAS DE SEGURANÇA (LEGADO)

### Autenticação JWT (PRIORIDADE MÁXIMA)
- Middleware de autenticação obrigatório
- Validação de tokens JWT
- Sistema de refresh tokens
- Controle de expiração de sessões
- Logs de auditoria de login/logout

### Proteção de APIs
- **Todas as rotas** devem estar protegidas (exceto login, refresh, status)
- **Middleware de autenticação** em todas as rotas
- **Validação de tokens JWT** obrigatória
- **Controle de permissões** ou roles
- **Logs de auditoria** de acesso

### Middleware de Segurança
- **CORS** configurado adequadamente
- **Rate limiting** para prevenir ataques
- **Validação de headers** de segurança
- **Logs de auditoria** de ações
- **Isolamento** entre tenants

### Validação de Permissões
Sempre verificar:
1. Nível administrativo do usuário
2. Permissões específicas atribuídas
3. Escopo (global/tenant/user)
4. Se está ativo e não expirou
5. Se tem restrições específicas
6. Se está no tenant correto

### Auditoria Obrigatória
Logar sempre:
- Quem alterou o quê
- Quando foi alterado
- De onde foi alterado (IP, User-Agent)
- Motivo da alteração
- Aprovação (se necessário)

---

## 8. POLÍTICAS DE SENHAS E AUTENTICAÇÃO

### Senhas
- **Mínimo:** 12 caracteres
- **Complexidade:** Maiúsculas, minúsculas, números, símbolos
- **Expiração:** 90 dias
- **Histórico:** Últimas 5 senhas não podem ser reutilizadas

### 2FA/MFA
- **Obrigatório:** Níveis 1-3 (SUPER_ADMIN, TENANT_ADMIN, TENANT_MANAGER)
- **Recomendado:** Nível 4 (TENANT_OPERATOR)
- **Opcional:** Nível 5 (TENANT_VIEWER)

### Bloqueio
- **Tentativas:** 5 falhas = bloqueio automático
- **Duração:** 30 minutos
- **Desbloqueio:** Automático ou manual por administrador

---

## 9. REGRAS DE BANCO DE DADOS

### Estrutura Obrigatória
- **Estrutura de tabelas** conforme definido no documento
- **RBAC e SaaS** implementados conforme especificações
- **Isolamento de dados** por módulo obrigatório

### Estrutura de Tabelas
- **Tabelas normalizadas** com relacionamentos corretos
- **Índices obrigatórios** para performance
- **Constraints** para integridade de dados
- **Campos de auditoria** obrigatórios (criado_por, criado_em, atualizado_por, atualizado_em)

### Multi-Tenancy
- **Isolamento completo** de dados por tenant
- **Middleware de tenant detection** obrigatório
- **Limites por plano** (usuários, equipamentos, certificados, armazenamento)
- **Escalabilidade automática**
- **Backup isolado** por tenant

---

## 10. REGRAS DE DESENVOLVIMENTO

### Módulos
- **Estrutura modular** obrigatória para isolamento
- **APIs:** Prefixos obrigatórios para separação de sistemas
- **Templates:** Base separada para cada sistema
- **Padronização Visual:** `/dashboard` é modelo OBRIGATÓRIO para todo o sistema

### APIs
- **Prefixos obrigatórios** para separação de sistemas
- **Versionamento:** `/api/v1/`
- **Documentação:** Swagger/OpenAPI em `/api/docs`
- **Validação:** Pydantic schemas obrigatórios

### CRUD
- **Validação de dados** com Pydantic
- **Tratamento de erros** específicos (400, 404, 409, 422)
- **Mensagens de erro** amigáveis
- **Logs detalhados** de operações
- **Rollback automático** em falhas

### Filtros e Busca
- **Busca por texto** (LIKE, full-text search)
- **Filtros por múltiplos campos**
- **Ordenação dinâmica** (ASC/DESC)
- **Paginação com metadata** (total, páginas, etc.)
- **Cache Redis** para consultas frequentes

### Paginação e Performance
- **Paginação eficiente** (LIMIT/OFFSET ou cursor)
- **Índices otimizados** no banco
- **Lazy loading** de relacionamentos
- **Cache de consultas** frequentes
- **Monitoramento de performance**

---

## 11. REGRAS ESPECÍFICAS DO CERTIPESO

### Validação de CNPJ
- **Obrigatória** no cadastro de clientes
- **Validador:** `app/utils/cnpj_validator.py`
- **Formato:** XX.XXX.XXX/XXXX-XX
- **Validação de dígitos verificadores** obrigatória

### Busca de CEP
- **Busca automática** de endereço por CEP
- **Integração:** API externa (ViaCEP ou similar)
- **Preenchimento automático** de campos de endereço
- **Validação** de CEP válido

### Regra de numeração: formato + escopo da sequência

Toda numeração sequencial do sistema segue **formato** + **escopo da sequência**. O escopo define onde a sequência é única (global, por unidade ou por tipo).

#### Formato

Padrão por entidade:

| Entidade | Formato | Exemplo | Chave de configuração |
|----------|---------|---------|------------------------|
| **Certificado** | `YYYY-XXXX` (ano + 4 dígitos) | `2026-0001` | `certificados.proximo_numero` |
| **Processo** | `PROC-YYYY-NNNNN` (ano + 5 dígitos) | `PROC-2026-00001` | `processos.proximo_numero` |
| **Ordem de serviço** | `OS-YYYY-NNNNN` | `OS-2026-00001` | `ordem_servico.proximo_numero` |
| **Venda** | `VENDA-YYYY-NNNNNN` (ano + 6 dígitos) | `VENDA-2026-000001` | *(derivado do último por ano)* |

- **YYYY:** ano civil da criação.
- **XXXX / NNNNN:** sequencial numérico, preenchido com zeros à esquerda.
- Sequência armazenada na tabela `configuracoes` (chave/valor), exceto vendas (calculada a partir do último `numero_venda` do ano).

#### Escopo da sequência (lista fechada)

- **global:** Uma única sequência para todo o sistema (ou por ano, quando o formato inclui ano). Último número e próximo são únicos.
- **unidade:** Sequência **por unidade organizacional** (filial, unidade). Cada unidade tem sua própria sequência (ex.: `2026-0001` na unidade A e `2026-0001` na unidade B). Relevante em multi-unidade/multi-tenant.
- **tipo:** Sequência **por tipo** da entidade (ex.: tipo de certificado `calibracao` vs `afericao`, tipo de processo, tipo de equipamento). Cada tipo possui sequência independente.

#### Escopo atual por entidade

| Entidade | Escopo atual | Observação |
|----------|--------------|------------|
| Certificado | **global** | Sequência única por ano. Chave `certificados.proximo_numero`. |
| Processo | **global** | Sequência única. Chave `processos.proximo_numero`. |
| Ordem de serviço | **global** | Sequência única. Chave `ordem_servico.proximo_numero`. |
| Venda | **global** | Sequência única por ano, obtida do último `numero_venda` do ano. |

Implementação futura de **unidade** ou **tipo** exigirá chaves (ou estruturas) por escopo, por exemplo: `certificados.proximo_numero.{unidade_id}` ou `certificados.proximo_numero.{tipo}`.

#### Regras obrigatórias

- **Validação de unicidade** do número gerado (por entidade e, se aplicável, por escopo).
- **Incremento atômico** da sequência ao gerar (uso de `configuracoes` com lock ou equivalente).
- **Nunca** reutilizar números já utilizados; **nunca** alterar número após emissão/uso.
- Formato e escopo são definidos neste mapa; alterações devem ser documentadas e refletidas no código e em migrações.

### Controle de Validade
- **Data de validade** obrigatória em certificados
- **Alertas automáticos** de vencimento (30 dias antes)
- **Cálculo automático** de dias restantes
- **Renovação simplificada** com histórico

### Renovação de Certificados
- **Verificação automática** de validade
- **Nova aferição** obrigatória para renovação
- **Histórico completo** de renovações
- **Vinculação** entre certificado antigo e novo

### Validação de Dados Técnicos
- **Campos obrigatórios** por tipo de equipamento
- **Validação de faixas** (capacidade, resolução)
- **Validação de formatos** (número de série, patrimônio)
- **Validação de relacionamentos** (equipamento-cliente)

### Assinaturas Digitais
- **Inspetor** obrigatório em todos os certificados
- **Aprovador** obrigatório em certificados aprovados
- **Registro completo** de assinaturas (data, hora, método)
- **Validação de permissões** para assinar

### Geração de PDF
- **Template padronizado** obrigatório
- **Dados dinâmicos** do banco de dados
- **Logo e branding** do sistema
- **QR Code** para validação (opcional)
- **Assinaturas digitais** incluídas no PDF

#### Implementação Atual
- **Serviço:** `app/services/pdf_certificado_job.py`
- **Endpoint de geração:** `POST /api/v1/certificados/{id}/pdf` (enfileira job assíncrono)
- **Endpoint de download:** `GET /api/v1/certificados/{id}/pdf` (retorna PDF quando pronto)
- **Status do PDF:** `pendente` → `gerando` → `pronto` | `erro`
- **Storage:** Interface `IStorage` com implementação `FilesystemStorage`
- **Estrutura de arquivos:** `{ano}/{certificado_id}.pdf`
- **Integridade:** Hash SHA256 armazenado em `certificado_pdf_hash`

#### Regras de Negócio
- PDF só pode ser gerado para certificados não cancelados
- Um PDF por certificado (regeneração substitui o anterior)
- Job assíncrono via `BackgroundTasks` do FastAPI
- Erros na geração são registrados em `certificado_pdf_erro` (máximo 4000 caracteres)
- Validação de existência antes de gerar novo PDF

---

## 12. REGRAS DE VERSIONAMENTO

### Formato: X.Y.Z.W
- **W:** 1-99 (patch)
- **Y:** Minor (funcionalidades)
- **Z:** Major (mudanças)
- **X:** Build

### Changelog
- **Arquivo:** `CHANGELOG.md` na raiz
- **Atualização obrigatória** a cada release
- **Histórico completo** de versões e funcionalidades

---

## 13. LEMBRETES CRÍTICOS

### Segurança em Produção
- ❌ NUNCA usar senhas padrão em produção
- ❌ NUNCA compartilhar credenciais
- ❌ NUNCA armazenar senhas em texto plano
- ❌ NUNCA usar a mesma senha em múltiplos sistemas
- ❌ NUNCA fazer login em dispositivos não confiáveis

### Boas Práticas
- ✅ Sempre usar 2FA/MFA
- ✅ Sempre usar senhas únicas e complexas
- ✅ Sempre fazer logout em dispositivos compartilhados
- ✅ Sempre reportar atividades suspeitas
- ✅ Sempre manter software atualizado
- ✅ Sempre fazer backup de configurações

---

## 14. MÓDULO DE PAGAMENTOS (Fase 3.3 – Plano Hierarquia)

Regras do módulo multiprovedor (payment_provider_configs, payment_transactions, transaction_splits, split_rules, payment_logs). Referência: plano de implantação PDV e hierarquia; MAPA_DO_SISTEMA e MAPA_DE_API.

### Roteamento e provedores
- Configuração de provedores é **por estabelecimento** (cliente_id). Apenas estabelecimentos no escopo do usuário (ClienteScope) podem ter configs listadas/criadas.
- **Gateway restrito por tenant do CA:** Configuração e processamento de gateway são restritos ao escopo do CA (`allowed_ids`); cada CA pode configurar seu próprio gateway (credenciais por estabelecimento) **se quiser** — a configuração é opcional; sem config ativa para um estabelecimento, pagamentos eletrônicos via gateway não estão disponíveis para esse estabelecimento.
- Roteamento (qual provedor usar por método/custo) será implementado no **PaymentOrchestrator** (3.3.1); hoje a API `/payments/process` é stub e persiste transação em status "pending".
- Provedores plugáveis (PagBank, Cielo, Stone, Efí, Mercado Pago) implementarão interface única (charge, refund, getStatus, supportsMethod); sem hardcode de credenciais no código.

### Gateways operacionais (pagamento real)
- Gateways permitidos: **`mercadopago`**, **`pagbank`** e **`pagarme`** (`/payments/configs` rejeita outros providers).
- **Mercado Pago:** CA informa Access Token (JSON: `{"access_token": "APP_USR-xxx"}`).
- **PagBank:** CA conecta via **OAuth Connect** (botão "Conectar conta PagBank" em Recebíveis → redirect → callback salva tokens automaticamente). Variáveis da aplicação: `PAGBANK_CONNECT_CLIENT_ID`, `PAGBANK_CONNECT_CLIENT_SECRET`, `PAGBANK_CONNECT_SANDBOX`.
- **Pagar.me:** CA informa **Secret Key** (campo dedicado em Recebíveis). Auth: HTTP Basic Auth (sk como usuário, senha vazia).
- Fluxo obrigatório: finalizar venda → criar venda → processar gateway em `/api/v1/payments/process`.
- Se o gateway não aprovar imediatamente, registrar como pendente/falha com retentativa explícita (`/api/v1/payments/retry/{transaction_uuid}`).
- Sem fallback para provider `stub` em produção quando pagamento real for exigido.
- Frontend deve manter alinhamento de contrato com backend (status, message, retry_allowed, payment_details) em PDV, Nova Venda e `/negocio/pagamentos`.

### Modo de Recebimento (empresa.modo_recebimento)
- Campo `modo_recebimento` na tabela `empresa`, definido pelo **SuperAdmin** em Fiscal > Empresa.
- **`direto`**: valor da venda vai para a conta do CA (via gateway configurado em Recebíveis). Sem split.
- **`plataforma`** (default): plataforma recebe o valor total na conta billing MP. SuperAdmin cria repasses manuais em Negócios > Financeiro.
- **Roteamento no Orchestrator**: se `modo=plataforma`, usa credenciais billing da plataforma (`billing_config.get_mp_access_token`); se `modo=direto`, usa `PaymentProviderConfig` do CA.
- Quando `modo=plataforma`, tela Recebíveis exibe alerta e oculta botão "Nova configuração".
- Somente SuperAdmin pode alterar `modo_recebimento`, `taxa_plataforma_percentual` e `taxa_plataforma_valor_fixo` (API ignora silenciosamente se outro role tentar).
- Cada `PaymentTransaction` grava o `modo_recebimento` usado no momento da cobrança.

### Repasses financeiros (tabela `repasses`)
- Modelo `Repasse`: transferência manual da plataforma para o CA (quando `modo=plataforma`).
- Status: `pendente` → `repassado` (com `data_repasse` automática) ou `cancelado`.
- API em `/api/v1/negocio/financeiro/repasses/` (SuperAdmin only, `require_superadmin()`).
- Endpoints: resumo por CA, extrato com filtros, criar repasse, atualizar status, listar taxas.
- Painel visual em `/negocio/financeiro` (SuperAdmin): cards de totais, tabela de repasses, ações marcar repassado/cancelar.

### Conciliação automática (webhooks)
- Webhook por provedor em **POST** `/api/v1/payments/webhook/{provider_code}` (aceita `mercadopago`, `pagbank`, `pagarme`).
- Webhook Mercado Pago legado (`/api/webhooks/mercadopago`) continua ativo para billing.
- Atualização obrigatória dos campos de transação: `status`, `provider_transaction_id`, `paid_at`, `reconciliation_status`, `reconciliation_date`.
- Sincronizar `venda_pagamentos` da venda vinculada com resultado da conciliação (`confirmado`/`pendente`).
- Manter fallback para fluxo de billing quando evento não estiver relacionado a venda.

### Fase 3 operacional (painel de pendências)
- O módulo `/negocio/pagamentos` deve exibir transações `pending` e `failed` por estabelecimento (escopo CA).
- Ação de retentativa deve usar endpoint dedicado (`/api/v1/payments/retry/{transaction_uuid}`).
- Após retentativa, frontend deve atualizar lista de pendências e refletir status retornado.

### Fase 4 operacional (hardening de operação)
- Painel de pendências deve suportar filtros de status e período (data inicial/final).
- Listagem operacional deve usar paginação (`skip/limit`) para não sobrecarregar a tela.
- Retentativa deve possuir trava anti-disparo concorrente no frontend para evitar múltiplas chamadas simultâneas da mesma transação.

### Split (repasses por nível)
- Regras em `split_rules` por estabelecimento: recipient_type (super_admin, admin, cliente_admin, estabelecimento), percentage ou fixed_amount, applies_to (JSON), priority.
- **SplitEngine** (3.3.3) calculará repasses antes de enviar ao provedor; valores líquidos registrados em `transaction_splits`. Restante líquido fica com o estabelecimento.

### Estorno
- Estorno via interface do provedor (refund) e atualização de status da transação (refunded_at); conciliação deve refletir estorno. API de estorno será exposta quando o Orquestrador e provedores estiverem implementados.

### Conciliação
- Transações possuem `reconciliation_status` (pending, matched, divergence). Conciliação = matching com extratos do provedor; relatórios de conferência (vendas x liquidação) conforme 3.3.3.
- Dados de transação (uuid, amount, status, provider_transaction_id, paid_at, etc.) devem ser mantidos para auditoria e conciliação.

### Retenção e segurança
- Credenciais de provedores devem ser **criptografadas em repouso** (ex.: AES-256-GCM); chave mestre em variável de ambiente (3.3.2+). Logs de request/response não devem gravar dados sensíveis de cartão; alinhamento a boas práticas PCI onde aplicável.
- **Sangria/suprimento (caixa):** registro em `movimentos_caixa` com permissão `pdv:sangria_suprimento`. Validação de **senha mestra** por estabelecimento: tabela `senha_mestra_estabelecimento`, API `POST /api/v1/senha-mestra/definir` e `POST /api/v1/senha-mestra/validar` (Fase 5.2).

### Senha mestra (Fase 5.2 – política obrigatória no plano)
- **Por estabelecimento:** uma senha mestra por `cliente_id` (estabelecimento), não global; reduz impacto em caso de vazamento.
- **Validade temporária:** campo `expira_em` em `senha_mestra_estabelecimento`; opcional ao definir (ex.: expira em 24h ou por sessão).
- **Armazenamento:** tabela `senha_mestra_estabelecimento` (cliente_id, senha_hash, expira_em); hash bcrypt; nunca hardcoded ou em texto plano.
- **Definir:** `POST /api/v1/senha-mestra/definir` (Super Admin, Admin ou CA no escopo); body: cliente_id, senha, expira_em_horas (opcional).
- **Validar:** `POST /api/v1/senha-mestra/validar` (uso em sangria/suprimento, desconto acima do limite, cancelamento de venda); retorna `{ "valido": true|false }`.
- **2FA e log:** autenticação de dois fatores para ações críticas e log detalhado de uso da senha mestra ficam para evolução (notificação ao administrador do estabelecimento). Biometria como alternativa onde houver hardware.

### Disaster Recovery (Fase 6.1 – obrigatório no plano)
- **Backup diário:** script `scripts/backup_pdv-solumatica.sh` (diretório + banco); agendar com cron. Opcional: backup em nuvem criptografado (`BACKUP_ENCRYPT=1`, `BACKUP_ENCRYPT_PASSPHRASE`, `BACKUP_UPLOAD_CMD`).
- **Backup das configurações dos PDVs:** o script exporta `pdvs_configuracoes.json` em cada execução; API `GET /api/v1/pdvs/export-configuracoes` permite export por escopo para rotinas externas.
- **Procedimento de restauração:** documentado em MAPA_DO_SISTEMA (Backup e Restauração; Disaster Recovery); deve ser testado em ambiente de homologação.
- **Teste de restauração trimestral:** obrigatório pelo menos a cada trimestre; documentar data, responsável e resultado.
- **Retenção legal:** 5 (cinco) anos de documentos fiscais e dados de vendas; políticas de retenção de backups devem ser definidas pela operação (ex.: manter backups anuais por 5 anos).

---

**Última Atualização:** 2026-03-03 — Padrão de Modais: regra obrigatória para scripts em IIFE — expor funções de fechar/abrir modal em `window` quando usadas por `onclick` no HTML (ex.: conciliar NFe).  
**Versão:** 1.5  
**Status:** Ativo e Essencial
