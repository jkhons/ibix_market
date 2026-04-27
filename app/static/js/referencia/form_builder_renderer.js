/* 
  REFERÊNCIA DO CERTILOG - Form Builder Renderer JavaScript
  Este arquivo é uma cópia de referência do sistema Certilog.
  Não deve ser usado diretamente no PDV Ibix.
  Adaptar conforme necessário para implementação futura.
*/

// Form Builder Renderer - Renderizador de Formulários Dinâmicos
// Renderiza formulários a partir de schemas de templates

/**
 * RuleEngine - Engine para avaliar condições e resolver bindings
 */
class RuleEngine {
    constructor(contexto = {}) {
        this.contexto = contexto;
        this.cache = {}; // Cache para avaliações
    }
    
    /**
     * Avaliar uma condição (ex: "os.status in ['EM_EXECUCAO']")
     */
    avaliarCondicao(condicao, contexto = null) {
        const ctx = contexto || this.contexto;
        const cacheKey = `cond_${JSON.stringify(condicao)}_${JSON.stringify(ctx)}`;
        
        if (this.cache[cacheKey] !== undefined) {
            return this.cache[cacheKey];
        }
        
        try {
            let resultado = false;
            
            if (!condicao || !condicao.if) {
                return true; // Sem condição = sempre verdadeiro
            }
            
            const expressao = condicao.if.trim();
            
            // Condições especiais
            if (expressao === 'always') {
                resultado = true;
            } else if (expressao === 'never') {
                resultado = false;
            } else {
                // Avaliar expressão JavaScript segura
                resultado = this.avaliarExpressao(expressao, ctx);
            }
            
            this.cache[cacheKey] = resultado;
            return resultado;
        } catch (error) {
            console.error('Erro ao avaliar condição:', condicao, error);
            return false; // Em caso de erro, retornar false (mais seguro)
        }
    }
    
    /**
     * Avaliar expressão JavaScript de forma segura
     */
    avaliarExpressao(expressao, contexto) {
        // Criar função segura para avaliar expressões
        // Suporta: ==, !=, in, &&, ||, comparações
        try {
            // Substituir referências do contexto
            let expr = expressao;
            
            // Substituir acessos a objetos (ex: os.status -> ctx.os.status)
            expr = expr.replace(/\b(os|user|status|refs)\.(\w+)/g, (match, obj, prop) => {
                if (obj === 'status') {
                    return `ctx.os?.status || ctx.status || ''`;
                }
                return `ctx.${obj}?.${prop} || ''`;
            });
            
            // Substituir 'in' por verificação de array
            expr = expr.replace(/(\w+)\s+in\s+\[([^\]]+)\]/g, (match, varName, arrayContent) => {
                const arrayValues = arrayContent.split(',').map(v => v.trim().replace(/['"]/g, ''));
                return `['${arrayValues.join("','")}'].includes(${varName})`;
            });
            
            // Criar função de avaliação
            const func = new Function('ctx', `
                try {
                    const os = ctx.os || {};
                    const user = ctx.user || {};
                    const status = ctx.os?.status || ctx.status || '';
                    const refs = ctx.refs || {};
                    return ${expr};
                } catch (e) {
                    return false;
                }
            `);
            
            return func(contexto);
        } catch (error) {
            console.error('Erro ao avaliar expressão:', expressao, error);
            return false;
        }
    }
    
    /**
     * Resolver binding (ex: "os.number" -> valor real)
     */
    resolverBinding(binding, contexto = null) {
        const ctx = contexto || this.contexto;
        
        if (!binding || !binding.source) {
            return null;
        }
        
        try {
            const source = binding.source;
            const parts = source.split('.');
            
            let valor = ctx;
            for (const part of parts) {
                if (valor && typeof valor === 'object') {
                    valor = valor[part];
                } else {
                    return null;
                }
            }
            
            return valor !== undefined ? valor : null;
        } catch (error) {
            console.error('Erro ao resolver binding:', binding, error);
            return null;
        }
    }
    
    /**
     * Resolve o bloco de um campo (agnóstico de UI)
     * 
     * Ordem de resolução:
     * 1. campo.bloco (explícito no schema - preferencial)
     * 2. Inferência do tipo (fallback - transitório)
     * 
     * Referência: PLANO_PCM/plano_1.md - Etapa 4
     */
    resolverBlocoCampo(campo) {
        // Opção 1: Bloco explícito no schema (recomendado)
        if (campo.bloco) {
            return campo.bloco;
        }
        
        // Opção 2: Inferência do tipo (fallback transitório)
        // Mapeamento interno agnóstico de UI/DOM
        const mapeamento = {
            'descricao_solicitante': 'descricao_solicitante',
            'descricao_tecnico': 'descricao_tecnico',
            'materiais_pecas': 'materiais',
            'apontamento_horas': 'apontamento_horas',
            'checklist': 'checklist',
            'qsa': 'qsa',
            'assinatura': 'assinaturas',
            'aprovacao': 'aprovacoes',
            'cabecalho_os': 'cabecalho_os'
        };
        
        return mapeamento[campo.tipo] || null;
    }
    
    /**
     * Obtém permissões de um bloco do contexto
     * Retorna null se não existir (comportamento legado)
     */
    getBlocoPermissao(blocoId, contexto = null) {
        const ctx = contexto || this.contexto;
        const b = ctx?.permissoes?.blocos?.[blocoId];
        if (!b) return null; // legado: não bloqueia
        return { read: !!b.read, write: !!b.write };
    }
    
    /**
     * Verifica se bloco pode ser visto (read permission)
     * Se não existir permissão, retorna true (comportamento legado)
     */
    blocoPodeSerVisto(blocoId, contexto = null) {
        const p = this.getBlocoPermissao(blocoId, contexto);
        if (!p) return true;         // legado: não bloqueia
        return p.read === true;      // se existe, aplica
    }
    
    /**
     * Verifica se bloco pode ser editado (write permission)
     * Se não existir permissão, retorna true (comportamento legado)
     * 
     * REGRA OBRIGATÓRIA: write_final = contexto.pode_editar && permissoes.blocos[bloco].write
     * pode_editar é um gate macro (habilita edição geral), mas cada bloco decide o write final
     * Se pode_editar for False, TODOS os blocos terão write=False, independente do cálculo do bloco
     */
    blocoPodeSerEditado(blocoId, contexto = null) {
        const ctx = contexto || this.contexto;
        const p = this.getBlocoPermissao(blocoId, ctx);
        if (!p) return true; // legado
        
        // Aplicar regra obrigatória: write_final = pode_editar && permissao_bloco.write
        const pode_editar = ctx?.pode_editar === true;
        const write_final = pode_editar && p.write === true;
        
        return write_final;
    }
    
    /**
     * Verificar se campo deve ser visível
     * 
     * Referência: PLANO_PCM/plano_1.md - Etapa 4
     * 
     * Ordem de verificação:
     * 1. Gate de bloco (permissoes.blocos[bloco].read) - ETAPA 04
     * 2. showWhen (regra existente)
     * 3. Sem regra = sempre visível (compatibilidade)
     * 
     * RuleEngine decide SE é visível (agnóstico de UI)
     * FormBuilderRenderer decide COMO renderizar
     */
    verificarVisibilidade(campo, contexto = null) {
        const ctx = contexto || this.contexto;
        
        // ETAPA 04: Gate de bloco (verifica permissoes.blocos[bloco].read)
        // Resolver bloco de forma agnóstica (sem depender do renderer)
        const blocoId = this.resolverBlocoCampo(campo);
        if (blocoId) {
            const podeVerBloco = this.blocoPodeSerVisto(blocoId, ctx);
            if (!podeVerBloco) {
                return false; // Bloco não pode ser visto
            }
        }
        
        // Verificar showWhen (regra existente)
        if (!campo.render || !campo.render.showWhen) {
            return true; // Sem regra = sempre visível
        }
        
        const showWhen = Array.isArray(campo.render.showWhen) 
            ? campo.render.showWhen 
            : [campo.render.showWhen];
        
        // Se qualquer condição for verdadeira, campo é visível
        for (const condicao of showWhen) {
            if (this.avaliarCondicao(condicao, ctx)) {
                return true;
            }
        }
        
        return false;
    }
    
    /**
     * Verificar se campo é editável
     * 
     * Referência: PLANO_PCM/plano_1.md - Etapa 4
     * 
     * Ordem de verificação:
     * 1. Campos computed/readonly nunca são editáveis
     * 2. Permissão específica do campo (permissoes.campos[campoId].write) - PRIORIDADE sobre bloco
     * 3. Gate de bloco (permissoes.blocos[bloco].write) - ETAPA 04
     * 4. immutableAfter (auditoria)
     * 5. permissions.editable (regra existente)
     * 6. editableWhen (regra existente)
     * 7. pode_editar global (legado - mantido para compatibilidade)
     */
    verificarEditabilidade(campo, contexto = null) {
        const ctx = contexto || this.contexto;
        
        // Campos computed nunca são editáveis
        if (campo.data && campo.data.mode === 'computed') {
            return false;
        }
        
        // Campos readonly não são editáveis
        if (campo.data && campo.data.mode === 'readonly') {
            return false;
        }
        
        // NOVO: Verificar permissão específica do campo (prioridade sobre bloco)
        // Se campo tem permissão específica configurada, usa essa permissão
        const campoId = campo.id;
        const permCampo = ctx?.permissoes?.campos?.[campoId];
        if (permCampo !== undefined) {
            // Campo tem permissão específica - usar ela
            if (!permCampo.write) {
                return false; // Campo tem permissão específica e não pode editar
            }
            // Se campo pode editar pela permissão específica, continua verificação
            // (outras regras como immutableAfter ainda podem bloquear)
        }
        
        // ETAPA 04: Gate de bloco (verifica permissoes.blocos[bloco].write)
        // Aplicado apenas se campo não tem permissão específica
        // Se campo tem permissão específica e passou, bloco não bloqueia (mas outras regras podem)
        if (permCampo === undefined) {
            // Resolver bloco de forma agnóstica (sem depender do renderer)
            const blocoId = this.resolverBlocoCampo(campo);
            if (blocoId) {
                const podeEditarBloco = this.blocoPodeSerEditado(blocoId, ctx);
                if (!podeEditarBloco) {
                    return false; // Bloco não pode ser editado
                }
            }
        }
        
        // Verificar immutableAfter
        if (campo.audit && campo.audit.immutableAfter) {
            const statusAtual = ctx.os?.status || ctx.status || '';
            if (campo.audit.immutableAfter.includes(statusAtual)) {
                return false;
            }
        }
        
        // Verificar permissions.editable
        if (campo.permissions && campo.permissions.editable) {
            const userRole = ctx.user?.role || ctx.user?.papel_organizacional || '';
            if (campo.permissions.editable.includes(userRole)) {
                return true;
            }
        }
        
        // Verificar editableWhen
        if (campo.permissions && campo.permissions.editableWhen) {
            const editableWhen = Array.isArray(campo.permissions.editableWhen)
                ? campo.permissions.editableWhen
                : [campo.permissions.editableWhen];
            
            for (const condicao of editableWhen) {
                if (this.avaliarCondicao(condicao, ctx)) {
                    const userRole = ctx.user?.role || ctx.user?.papel_organizacional || '';
                    const rolesPermitidos = condicao.roles || [];
                    if (rolesPermitidos.includes(userRole)) {
                        return true;
                    }
                }
            }
        }
        
        // Verificar pode_editar global (legado - mantido para compatibilidade)
        const podeEditarGlobal = ctx.pode_editar !== undefined ? ctx.pode_editar : null;
        if (podeEditarGlobal !== null) {
            return podeEditarGlobal;
        }
        
        // Por padrão, campos input são editáveis se não houver restrições
        return campo.data && campo.data.mode === 'input';
    }
    
    /**
     * Verificar se campo é obrigatório
     */
    verificarObrigatoriedade(campo, contexto = null) {
        const ctx = contexto || this.contexto;
        
        // Verificar required básico
        if (campo.validation && campo.validation.required === true) {
            return true;
        }
        
        // Verificar requiredWhen
        if (campo.validation && campo.validation.requiredWhen) {
            const requiredWhen = Array.isArray(campo.validation.requiredWhen)
                ? campo.validation.requiredWhen
                : [campo.validation.requiredWhen];
            
            for (const condicao of requiredWhen) {
                if (this.avaliarCondicao(condicao, ctx)) {
                    return true;
                }
            }
        }
        
        // Compatibilidade com schema legado
        if (campo.obrigatorio === true) {
            return true;
        }
        
        return false;
    }
    
    /**
     * Obter mensagem de validação
     */
    obterMensagemValidacao(campo, contexto = null) {
        const ctx = contexto || this.contexto;
        
        if (campo.validation && campo.validation.requiredWhen) {
            const requiredWhen = Array.isArray(campo.validation.requiredWhen)
                ? campo.validation.requiredWhen
                : [campo.validation.requiredWhen];
            
            for (const condicao of requiredWhen) {
                if (this.avaliarCondicao(condicao, ctx)) {
                    return condicao.message || 'Este campo é obrigatório';
                }
            }
        }
        
        if (this.verificarObrigatoriedade(campo, ctx)) {
            return 'Este campo é obrigatório';
        }
        
        return null;
    }
}

class FormBuilderRenderer {
    constructor(containerId = null, schema = null, dados = {}, osId = null, contexto = {}) {
        this.container = containerId ? document.getElementById(containerId) : null;
        this.schema = schema;
        this.dados = dados;
        this.osId = osId;  // ID da OS para carregar eventos
        this.contexto = contexto; // Contexto completo (os, user, status, refs, permissoes)
        this.assinaturas = []; // Assinaturas recebidas explicitamente
        this.ruleEngine = new RuleEngine(contexto);
    }
    
    /**
     * Mapeia tipo de campo para ID do bloco oficial
     * Referência: PLANO_PCM/plano_1.md - Mapeamento Tipo de Campo → Bloco
     * Etapa 04: Preparação para consumo de permissoes.blocos
     */
    mapearTipoParaBloco(tipoCampo) {
        const mapeamento = {
            'descricao_solicitante': 'descricao_solicitante',
            'descricao_tecnico': 'descricao_tecnico',
            'materiais_pecas': 'materiais',
            'apontamento_horas': 'apontamento_horas',
            'checklist': 'checklist',
            'qsa': 'qsa',
            'assinatura': 'assinaturas',
            'aprovacao': 'aprovacoes',
            'cabecalho_os': 'cabecalho_os'
        };
        return mapeamento[tipoCampo] || null;
    }
    
    /**
     * Obtém permissões de um bloco do contexto
     * Retorna null se não existir (comportamento legado)
     * Referência: PLANO_PCM/plano_1.md - Etapa 4
     */
    getBlocoPermissao(blocoId) {
        const b = this.contexto?.permissoes?.blocos?.[blocoId];
        if (!b) return null; // legado: não bloqueia
        return { read: !!b.read, write: !!b.write };
    }
    
    /**
     * Verifica se bloco pode ser visto (read permission)
     * Se não existir permissão, retorna true (comportamento legado)
     * Referência: PLANO_PCM/plano_1.md - Etapa 4
     */
    blocoPodeSerVisto(blocoId) {
        const p = this.getBlocoPermissao(blocoId);
        if (!p) return true;         // legado: não bloqueia
        return p.read === true;      // se existe, aplica
    }
    
    /**
     * Verifica se bloco pode ser editado (write permission)
     * Se não existir permissão, retorna true (comportamento legado)
     * 
     * REGRA OBRIGATÓRIA: write_final = contexto.pode_editar && permissoes.blocos[bloco].write
     * pode_editar é um gate macro (habilita edição geral), mas cada bloco decide o write final
     * Se pode_editar for False, TODOS os blocos terão write=False, independente do cálculo do bloco
     * 
     * Referência: PLANO_PCM/plano_1.md - Etapa 4
     * MAPA_RBAC.md - Seção 17.3 (Alinhamento de Permissões)
     */
    blocoPodeSerEditado(blocoId) {
        const p = this.getBlocoPermissao(blocoId);
        if (!p) return true; // legado
        
        // Aplicar regra obrigatória: write_final = pode_editar && permissao_bloco.write
        const pode_editar = this.contexto?.pode_editar === true;
        const write_final = pode_editar && p.write === true;
        
        return write_final;
    }
    
    /**
     * Obtém valor de objeto por path (ex: "os.numero" -> contexto.os.numero)
     * Seguro para paths aninhados
     * Referência: PLANO_PCM/plano_1.md - Etapa 4 (Ordem Determinística de Resolução)
     */
    getByPath(obj, path) {
        if (!obj || !path) return undefined;
        const parts = path.split('.');
        let cur = obj;
        for (const p of parts) {
            if (cur == null) return undefined;
            cur = cur[p];
        }
        return cur;
    }
    
    /**
     * Método render() para uso direto (sem containerId no construtor)
     * Recebe assinaturas explicitamente para evitar dependência de variável global
     */
    render(schema, valores, contexto, assinaturas = []) {
        // Se container não foi definido, usar 'formulario-os' como padrão
        if (!this.container) {
            this.container = document.getElementById('formulario-os');
        }
        
        if (!this.container) {
            console.error('Container não encontrado. Use containerId no construtor ou defina elemento com id="formulario-os"');
            return;
        }
        
        this.schema = schema;
        this.dados = valores;
        this.contexto = contexto;
        this.assinaturas = assinaturas; // Recebido explicitamente
        this.osId = contexto.os?.id || null;
        this.ruleEngine = new RuleEngine(contexto);
        
        // Armazenar renderer globalmente para acesso em funções de materiais
        window.formBuilderRenderer = this;
        window.renderer = this;
        
        // Renderizar formulário
        this.renderizar();
        
        // Aplicar regras de edição após renderização completa
        // Usar setTimeout para garantir que DOM está pronto
        setTimeout(() => {
            this.aplicarEditableWhen();
        }, 50);
    }
    
    renderizar() {
        if (!this.container) {
            console.error('Container não encontrado');
            return;
        }
        
        // Armazenar instância globalmente para acesso de funções globais
        window.formBuilderRenderer = this;
        
        let html = '<div class="form-builder-renderizado">';
        
        // Renderizar seções
        const secoes = this.schema.secoes || [];
        const campos = this.schema.campos || [];
        const camposMap = {};
        
        // Criar mapa de campos
        campos.forEach(campo => {
            camposMap[campo.id] = campo;
        });
        
        // Ordenar seções pela propriedade 'ordem' (se existir)
        // IMPORTANTE: Manter a ordem original se não houver campo 'ordem'
        const secoesOrdenadas = [...secoes].sort((a, b) => {
            // Se ambas têm ordem definida, ordenar por ordem
            if (a.ordem !== undefined && a.ordem !== null && b.ordem !== undefined && b.ordem !== null) {
                return a.ordem - b.ordem;
            }
            // Se apenas uma tem ordem, ela vem primeiro
            if (a.ordem !== undefined && a.ordem !== null) {
                return -1;
            }
            if (b.ordem !== undefined && b.ordem !== null) {
                return 1;
            }
            // Se nenhuma tem ordem, manter ordem original (índice no array)
            return 0;
        });
        
        // Debug: log da ordem das seções
        console.log('Seções ordenadas:', secoesOrdenadas.map((s, idx) => ({ 
            indice: idx, 
            id: s.id, 
            ordem: s.ordem, 
            titulo: s.titulo,
            numCampos: (s.campos || []).length 
        })));
        
        secoesOrdenadas.forEach((secao, secaoIndex) => {
            html += `<div class="form-builder-secao" style="display: block; width: 100%; position: relative; clear: both;" data-secao-index="${secaoIndex}" data-secao-ordem="${secao.ordem || 'null'}">`;
            
            // Renderizar título da seção se existir
            if (secao.titulo) {
                html += `<div class="form-builder-secao-header">`;
                html += `<h5 class="secao-titulo">${secao.titulo}</h5>`;
                html += `</div>`;
            }
            
            // Renderizar campos da seção na ordem especificada (manter ordem do array)
            const campoIds = secao.campos || [];
            campoIds.forEach((campoId, campoIndex) => {
                if (camposMap[campoId]) {
                    const campo = camposMap[campoId];
                    // Verificar se o campo tem tipo definido
                    if (!campo.tipo) {
                        console.warn(`Campo sem tipo definido: ${campoId}`, campo);
                        // Se não tiver tipo, não renderizar (evitar mostrar IDs ou valores soltos)
                        return;
                    }
                    html += this.renderizarCampo(campo);
                } else {
                    console.warn(`Campo não encontrado no mapa: ${campoId} (seção: ${secao.titulo || secao.id})`);
                }
            });
            
            html += `</div>`;
        });
        
        // NÃO renderizar eventos dentro do formulário do template
        // Os eventos devem ser renderizados em uma seção separada na página, não dentro do formulário
        
        html += '</div>';
        this.container.innerHTML = html;
        
        // Aplicar máscaras após inserção no DOM
        this.aplicarMascaras();
        
        // Carregar eventos via API após renderização
        if (this.osId) {
            setTimeout(() => {
                this.carregarEventos();
            }, 100);
        }
    }
    
    /**
     * Aplicar regras de editableWhen baseado em contexto (status + role)
     * Desabilita campos quando status não permite edição ou técnico já assinou
     * 
     * ⚠️ IMPORTANTE: Backend é fonte da verdade para pode_editar.
     * Este método apenas aplica regras visuais baseado em editableWhen de cada campo.
     * 
     * ⚠️ REGRA: Se pode_editar=false, desabilita todos e impede submit.
     */
    aplicarEditableWhen() {
        if (!this.container) {
            return;
        }
        
        // ⚠️ Backend é fonte da verdade - verificar se pode_editar foi passado
        // Se não foi passado, usar lógica de fallback (não recomendado)
        const podeEditarGlobal = this.contexto.pode_editar !== undefined 
            ? this.contexto.pode_editar 
            : null;
        
        const status = (this.contexto.status || this.contexto.os?.status || '').toLowerCase();
        const userId = this.contexto.user?.id || window.currentUserId || null;
        
        // Verificar se status permite edição (regra explícita - backend é fonte da verdade)
        const STATUS_EDITAVEIS = ['em_execucao', 'pausada', 'aguardando_material'];
        const statusPermiteEdicao = STATUS_EDITAVEIS.includes(status);
        
        // Verificar se técnico já assinou
        const tecnicoAssinou = this.assinaturas?.some(a => 
            a.tipo === 'tecnico' && a.usuario_id === userId
        ) || false;
        
        // Se pode_editar foi passado pelo backend, usar esse valor
        // Caso contrário, usar lógica de fallback (não recomendado em produção)
        const podeEditar = podeEditarGlobal !== null 
            ? podeEditarGlobal 
            : (statusPermiteEdicao && !tecnicoAssinou);
        
        // Se não pode editar, desabilitar todos os campos e impedir submit
        if (!podeEditar) {
            this.desabilitarTodosCampos();
            // Exibir aviso "Formulário bloqueado..." (será feito pela página)
            return;
        }
        
        // Aplicar editableWhen de cada campo (só se pode_editar=true)
        const campos = this.schema?.campos || [];
        campos.forEach(campo => {
            // ⚠️ REGRA: Campo invisível (showWhen=false) não é validado/editado
            if (!this.ruleEngine.verificarVisibilidade(campo, this.contexto)) {
                return; // Campo não visível, pular
            }
            
            // Tentar encontrar campo por id ou campo_${id}
            let campoElement = document.getElementById(campo.id);
            if (!campoElement) {
                campoElement = document.getElementById(`campo_${campo.id}`);
            }
            if (!campoElement) {
                // Tentar encontrar por name
                campoElement = this.container.querySelector(`[name="${campo.id}"]`);
            }
            
            if (!campoElement) {
                return;
            }
            
            // ETAPA 04: Verificar editabilidade via RuleEngine (já inclui gate de bloco e editableWhen)
            const editavel = this.ruleEngine.verificarEditabilidade(campo, this.contexto);
            
            // Aplicar editabilidade
            if (campoElement.tagName === 'INPUT' || campoElement.tagName === 'TEXTAREA' || campoElement.tagName === 'SELECT') {
                campoElement.disabled = !editavel;
                campoElement.readOnly = !editavel;
                if (!editavel) {
                    campoElement.classList.add('bg-light');
                } else {
                    campoElement.classList.remove('bg-light');
                }
            }
        });
    }
    
    /**
     * Desabilitar todos os campos do formulário
     */
    desabilitarTodosCampos() {
        if (!this.container) {
            return;
        }
        
        this.container.querySelectorAll('input, textarea, select').forEach(campo => {
            campo.disabled = true;
            campo.readOnly = true;
            campo.classList.add('bg-light');
        });
    }
    
    /**
     * Coletar dados do formulário renderizado
     * Retorna objeto com campo_id: valor
     * Suporta: text, number, select, textarea, date, time, boolean, checklist, tabela
     */
    coletarDadosFormulario() {
        const dados = {};
        
        if (!this.container) {
            return dados;
        }
        
        const campos = this.schema?.campos || [];
        
        campos.forEach(campo => {
            const campoId = campo.id;
            if (!campoId) {
                return;
            }
            
            // Coletar baseado no tipo do campo
            if (campo.tipo === 'checklist') {
                // Coletar checklist
                const itens = campo.config?.itens || [];
                const checklistData = {
                    itens: []
                };
                
                itens.forEach((item, index) => {
                    const itemId = item.id || `item_${index}`;
                    // Buscar radio buttons
                    const radioChecked = this.container.querySelector(`input[name="${campoId}_${itemId}"]:checked`);
                    const resposta = radioChecked ? radioChecked.value : null;
                    
                    if (resposta) {
                        const itemData = {
                            id: itemId,
                            resposta: resposta
                        };
                        
                        // Se NC, buscar observação
                        if (resposta === 'NC') {
                            const obsElement = this.container.querySelector(`textarea[name="${campoId}_${itemId}_obs"]`);
                            if (obsElement) {
                                itemData.observacao = obsElement.value || '';
                            }
                        }
                        
                        checklistData.itens.push(itemData);
                    }
                });
                
                if (checklistData.itens.length > 0) {
                    dados[campoId] = checklistData;
                }
            } else if (campo.tipo === 'tabela') {
                // Coletar tabela (estrutura complexa - manter valor existente se não editável)
                // Por enquanto, manter valor do dados existente
                if (this.dados[campoId]) {
                    dados[campoId] = this.dados[campoId];
                }
            } else if (campo.tipo === 'boolean') {
                // Coletar boolean (radio buttons)
                const radioChecked = this.container.querySelector(`input[name="${campoId}"]:checked`);
                if (radioChecked) {
                    dados[campoId] = radioChecked.value === 'true';
                }
            } else {
                // Campos simples (text, number, select, textarea, date, time, etc.)
                let campoElement = document.getElementById(campoId);
                if (!campoElement) {
                    campoElement = this.container.querySelector(`[name="${campoId}"]`);
                }
                
                if (!campoElement) {
                    return;
                }
                
                let valor = null;
                
                // Coletar valor baseado no tipo
                if (campoElement.tagName === 'INPUT') {
                    if (campoElement.type === 'checkbox') {
                        valor = campoElement.checked;
                    } else if (campoElement.type === 'number') {
                        valor = campoElement.value ? parseFloat(campoElement.value) : null;
                    } else if (campoElement.type === 'date' || campoElement.type === 'time' || campoElement.type === 'datetime-local') {
                        valor = campoElement.value || null;
                    } else {
                        valor = campoElement.value || '';
                    }
                } else if (campoElement.tagName === 'TEXTAREA') {
                    valor = campoElement.value || '';
                } else if (campoElement.tagName === 'SELECT') {
                    valor = campoElement.value || null;
                }
                
                // Só adicionar se valor não for null/undefined (exceto string vazia que é válida)
                if (valor !== null && valor !== undefined) {
                    dados[campoId] = valor;
                }
            }
        });
        
        return dados;
    }
    
    /**
     * Aplicar máscaras em todos os inputs que têm data-mask
     */
    aplicarMascaras() {
        const inputsComMascara = this.container.querySelectorAll('input[data-mask]');
        inputsComMascara.forEach(input => {
            const mask = input.getAttribute('data-mask');
            if (mask) {
                this.aplicarMascaraInput(input, mask);
            }
        });
    }
    
    /**
     * Aplicar máscara em um input específico
     */
    aplicarMascaraInput(input, mask) {
        // Remover listeners anteriores se existirem
        const novoInput = input.cloneNode(true);
        input.parentNode.replaceChild(novoInput, input);
        
        // Aplicar máscara baseada no tipo
        if (mask === 'cpf' || mask === '000.000.000-00') {
            this.aplicarMascaraCPF(novoInput);
        } else if (mask === 'cnpj' || mask === '00.000.000/0000-00') {
            this.aplicarMascaraCNPJ(novoInput);
        } else if (mask === 'telefone' || mask === '(00) 00000-0000' || mask === '(00) 0000-0000') {
            this.aplicarMascaraTelefone(novoInput);
        } else if (mask === 'cep' || mask === '00000-000') {
            this.aplicarMascaraCEP(novoInput);
        } else if (mask === 'data' || mask === 'DD/MM/YYYY') {
            this.aplicarMascaraData(novoInput);
        } else if (mask === 'hora' || mask === 'HH:mm') {
            // Hora já tem input type="time", não precisa de máscara
        } else {
            // Máscara customizada
            this.aplicarMascaraCustomizada(novoInput, mask);
        }
    }
    
    /**
     * Aplicar máscara de CPF
     */
    aplicarMascaraCPF(input) {
        input.addEventListener('input', function(e) {
            let valor = e.target.value.replace(/\D/g, '');
            if (valor.length <= 11) {
                valor = valor.replace(/(\d{3})(\d)/, '$1.$2');
                valor = valor.replace(/(\d{3})(\d)/, '$1.$2');
                valor = valor.replace(/(\d{3})(\d{1,2})$/, '$1-$2');
                e.target.value = valor;
            }
        });
    }
    
    /**
     * Aplicar máscara de CNPJ
     */
    aplicarMascaraCNPJ(input) {
        input.addEventListener('input', function(e) {
            let valor = e.target.value.replace(/\D/g, '');
            if (valor.length <= 14) {
                valor = valor.replace(/^(\d{2})(\d)/, '$1.$2');
                valor = valor.replace(/^(\d{2})\.(\d{3})(\d)/, '$1.$2.$3');
                valor = valor.replace(/\.(\d{3})(\d)/, '.$1/$2');
                valor = valor.replace(/(\d{4})(\d)/, '$1-$2');
                e.target.value = valor;
            }
        });
    }
    
    /**
     * Aplicar máscara de telefone
     */
    aplicarMascaraTelefone(input) {
        input.addEventListener('input', function(e) {
            let valor = e.target.value.replace(/\D/g, '');
            if (valor.length <= 11) {
                if (valor.length <= 10) {
                    valor = valor.replace(/^(\d{2})(\d{4})(\d)/, '($1) $2-$3');
                } else {
                    valor = valor.replace(/^(\d{2})(\d{5})(\d)/, '($1) $2-$3');
                }
                e.target.value = valor;
            }
        });
    }
    
    /**
     * Aplicar máscara de CEP
     */
    aplicarMascaraCEP(input) {
        input.addEventListener('input', function(e) {
            let valor = e.target.value.replace(/\D/g, '');
            if (valor.length <= 8) {
                valor = valor.replace(/^(\d{5})(\d)/, '$1-$2');
                e.target.value = valor;
            }
        });
    }
    
    /**
     * Aplicar máscara de data
     */
    aplicarMascaraData(input) {
        input.addEventListener('input', function(e) {
            let valor = e.target.value.replace(/\D/g, '');
            if (valor.length <= 8) {
                valor = valor.replace(/^(\d{2})(\d)/, '$1/$2');
                valor = valor.replace(/(\d{2})\/(\d{2})(\d)/, '$1/$2/$3');
                e.target.value = valor;
            }
        });
    }
    
    /**
     * Aplicar máscara customizada
     */
    aplicarMascaraCustomizada(input, mask) {
        // Converter máscara para regex
        // 0 = dígito, outros caracteres são literais
        const pattern = mask.replace(/0/g, '\\d');
        
        input.addEventListener('input', function(e) {
            let valor = e.target.value.replace(/\D/g, '');
            let resultado = '';
            let valorIndex = 0;
            
            for (let i = 0; i < mask.length && valorIndex < valor.length; i++) {
                if (mask[i] === '0') {
                    resultado += valor[valorIndex];
                    valorIndex++;
                } else {
                    resultado += mask[i];
                }
            }
            
            e.target.value = resultado;
        });
    }
    
    renderizarEventos() {
        // Renderizar seção de eventos (assinaturas e aprovações)
        let html = `<div class="form-builder-secao eventos-os">`;
        html += `<h4>Eventos da OS</h4>`;
        html += `<div id="eventos-assinaturas" class="mb-3">`;
        html += `<h6>Assinaturas</h6>`;
        html += `<div id="lista-assinaturas" class="list-group">`;
        html += `<p class="text-muted small">Carregando assinaturas...</p>`;
        html += `</div>`;
        html += `</div>`;
        html += `<div id="eventos-aprovacoes" class="mb-3">`;
        html += `<h6>Aprovações</h6>`;
        html += `<div id="lista-aprovacoes" class="list-group">`;
        html += `<p class="text-muted small">Carregando aprovações...</p>`;
        html += `</div>`;
        html += `</div>`;
        html += `<div id="eventos-sla" class="mb-3">`;
        html += `<h6>SLA</h6>`;
        html += `<div id="marcador-sla" class="alert alert-info mb-0">`;
        html += `<i data-feather="clock"></i> <span id="status-sla">Carregando status do SLA...</span>`;
        html += `</div>`;
        html += `</div>`;
        html += `</div>`;
        return html;
    }
    
    async carregarEventos() {
        if (!this.osId) return;
        
        try {
            // Carregar assinaturas
            const responseAssinaturas = await fetch(`/api/v1/manutencao/eventos/assinaturas/os/${this.osId}`, {
                credentials: 'include'
            });
            
            if (responseAssinaturas.ok) {
                const assinaturas = await responseAssinaturas.json();
                const container = document.getElementById('lista-assinaturas');
                if (container) {
                    if (assinaturas.length === 0) {
                        container.innerHTML = '<p class="text-muted small">Nenhuma assinatura registrada</p>';
                    } else {
                        container.innerHTML = assinaturas.map(ass => `
                            <div class="list-group-item">
                                <div class="d-flex justify-content-between">
                                    <div>
                                        <strong>${ass.tipo}</strong> - ${ass.usuario_nome}
                                        <br><small class="text-muted">${ass.acao} - ${new Date(ass.data_hora).toLocaleString('pt-BR')}</small>
                                    </div>
                                    <span class="badge bg-success">Assinado</span>
                                </div>
                            </div>
                        `).join('');
                    }
                }
            }
            
            // Carregar aprovações
            const responseAprovacoes = await fetch(`/api/v1/manutencao/eventos/aprovacoes/os/${this.osId}`, {
                credentials: 'include'
            });
            
            if (responseAprovacoes.ok) {
                const aprovacoes = await responseAprovacoes.json();
                const container = document.getElementById('lista-aprovacoes');
                if (container) {
                    if (aprovacoes.length === 0) {
                        container.innerHTML = '<p class="text-muted small">Nenhuma aprovação registrada</p>';
                    } else {
                        container.innerHTML = aprovacoes.map(apr => `
                            <div class="list-group-item">
                                <div class="d-flex justify-content-between">
                                    <div>
                                        <strong>${apr.tipo}</strong> - ${apr.usuario_nome}
                                        <br><small class="text-muted">${new Date(apr.data_hora).toLocaleString('pt-BR')}</small>
                                    </div>
                                    <span class="badge ${apr.aprovado ? 'bg-success' : 'bg-danger'}">${apr.aprovado ? 'Aprovado' : 'Reprovado'}</span>
                                </div>
                            </div>
                        `).join('');
                    }
                }
            }
            
            // Carregar status do SLA
            const responseSLA = await fetch(`/api/v1/manutencao/sla/calcular/${this.osId}`, {
                credentials: 'include'
            });
            
            if (responseSLA.ok) {
                const sla = await responseSLA.json();
                const container = document.getElementById('status-sla');
                if (container) {
                    const statusBadge = sla.sla_status === 'dentro' ? 'success' : 
                                       sla.sla_status === 'fora' ? 'danger' : 'warning';
                    container.innerHTML = `
                        <span class="badge bg-${statusBadge}">${sla.sla_status?.toUpperCase() || 'N/A'}</span>
                        <small class="ms-2">Tempo efetivo: ${Math.round(sla.tempo_efetivo_minutos / 60)}h ${sla.tempo_efetivo_minutos % 60}min</small>
                    `;
                }
            }
            
        } catch (error) {
            console.error('Erro ao carregar eventos:', error);
        }
    }
    
    renderizarCampo(campo) {
        // ETAPA 04: Gate de bloco (mais restritivo - vem antes de showWhen)
        // Referência: PLANO_PCM/plano_1.md - Etapa 4
        // Se bloco não pode ser visto (read=false), campo não é renderizado
        // Verificação de bloco movida para verificarVisibilidade no RuleEngine
        // Manter aqui apenas como fallback adicional se necessário
        // const blocoId = this.mapearTipoParaBloco(campo.tipo);
        // if (blocoId && !this.blocoPodeSerVisto(blocoId)) {
        //     return ''; // Bloco não visível - não renderizar
        // }
        
        // ⚠️ REGRA: Campo invisível (showWhen=false) não aparece no DOM e não é validado
        if (!this.ruleEngine.verificarVisibilidade(campo, this.contexto)) {
            return ''; // Campo não visível - não renderizar
        }
        
        // Resolver valor baseado em data.mode
        const valor = this.resolverValorCampo(campo);
        const editavel = this.ruleEngine.verificarEditabilidade(campo, this.contexto);
        const obrigatorio = this.ruleEngine.verificarObrigatoriedade(campo, this.contexto);
        const visivel = this.ruleEngine.verificarVisibilidade(campo, this.contexto);
        const mensagemValidacao = this.ruleEngine.obterMensagemValidacao(campo, this.contexto);
        
        const help = campo.help || campo.descricao || '';
        const layout = campo.layout || { width: 'full', columns: 1, align: 'left' };
        
        // Aplicar classes de layout
        const layoutClasses = this.aplicarLayoutClasses(layout);
        
        let html = `<div class="form-builder-campo-renderizado mb-3 ${layoutClasses}" data-campo-id="${campo.id}">`;
        
        // Blocos especiais não mostram label (cabeçalho, solicitante, descricao_solicitante)
        const blocosEspeciais = ['cabecalho_os', 'solicitante', 'descricao_solicitante'];
        if (!blocosEspeciais.includes(campo.tipo)) {
            html += `<label class="form-label">${campo.label || campo.id}`;
            if (obrigatorio) {
                html += ` <span class="text-danger">*</span>`;
            }
            html += `</label>`;
            if (help) {
                html += `<small class="form-text text-muted d-block mb-2">${help}</small>`;
            }
        }
        
        // Aplicar formatação ao valor
        const valorFormatado = this.formatarValor(valor, campo.render?.format || {}, campo.tipo);
        const placeholder = campo.render?.placeholder || '';
        const emptyState = campo.render?.emptyState || '—';
        
        // Renderizar input com validação
        const classeValidacao = obrigatorio ? 'is-invalid' : '';
        const readonlyAttr = !editavel ? 'readonly' : '';
        const disabledAttr = !editavel ? 'disabled' : '';
        
        switch (campo.tipo) {
            case 'text':
            case 'number':
                const mask = campo.render?.format?.mask;
                const maskAttr = mask ? `data-mask="${mask}"` : '';
                html += `<input type="${campo.tipo}" class="form-control ${classeValidacao}" 
                         value="${valorFormatado || ''}" 
                         name="${campo.id}" 
                         id="${campo.id}"
                         placeholder="${placeholder}"
                         ${maskAttr}
                         ${readonlyAttr}
                         ${disabledAttr}>`;
                if (mensagemValidacao) {
                    html += `<div class="invalid-feedback">${mensagemValidacao}</div>`;
                }
                // Máscara será aplicada via event listener após inserção no DOM
                break;
            case 'date':
                html += `<input type="date" class="form-control" value="${valor}" name="${campo.id}" id="${campo.id}" ${readonlyAttr} ${disabledAttr}>`;
                break;
            case 'hora':
                html += `<input type="time" class="form-control" value="${valor}" name="${campo.id}" id="${campo.id}" ${readonlyAttr} ${disabledAttr}>`;
                break;
            case 'datetime':
                html += `<input type="datetime-local" class="form-control" value="${valor}" name="${campo.id}" id="${campo.id}" ${readonlyAttr} ${disabledAttr}>`;
                break;
            case 'boolean':
                html += `<div class="form-check form-check-inline">`;
                html += `<input class="form-check-input" type="radio" name="${campo.id}" id="${campo.id}_sim" value="true" ${valor === true || valor === 'true' ? 'checked' : ''} ${disabledAttr}>`;
                html += `<label class="form-check-label" for="${campo.id}_sim">Sim</label>`;
                html += `</div>`;
                html += `<div class="form-check form-check-inline">`;
                html += `<input class="form-check-input" type="radio" name="${campo.id}" id="${campo.id}_nao" value="false" ${valor === false || valor === 'false' ? 'checked' : ''} ${disabledAttr}>`;
                html += `<label class="form-check-label" for="${campo.id}_nao">Não</label>`;
                html += `</div>`;
                break;
            case 'select':
                html += `<select class="form-select" name="${campo.id}" id="${campo.id}" ${disabledAttr}>`;
                html += `<option value="">Selecione...</option>`;
                (campo.opcoes || []).forEach(opcao => {
                    html += `<option value="${opcao.value}" ${opcao.value === valor ? 'selected' : ''}>${opcao.label}</option>`;
                });
                html += `</select>`;
                break;
            case 'checklist':
                html += this.renderizarChecklist(campo, valor, { editavel, visivel, obrigatorio });
                break;
            case 'apontamento_horas':
                html += this.renderizarApontamentoHoras(campo, valor, { editavel, visivel, obrigatorio });
                break;
            case 'materiais_pecas':
                html += this.renderizarMateriaisPecas(campo, valor, { editavel, visivel, obrigatorio });
                break;
            case 'equipamentos':
                html += this.renderizarEquipamentos(campo, valor);
                break;
            case 'ativos':
                html += this.renderizarAtivos(campo, valor);
                break;
            case 'status_final':
                html += this.renderizarStatusFinal(campo, valor);
                break;
            case 'seguranca_operacional':
                html += this.renderizarSegurancaOperacional(campo, valor);
                break;
            case 'qsa':
                html += this.renderizarQSA(campo, valor, { editavel, visivel, obrigatorio });
                break;
            case 'texto_informativo':
                const textoInformativo = valor || campo.valor_padrao || '';
                if (textoInformativo) {
                    html += `<div class="alert alert-info mb-0">${textoInformativo}</div>`;
                }
                break;
            case 'cabecalho_os':
                // Resolver valores do cabeçalho a partir do contexto
                const valorCabecalho = this.resolverValoresCabecalho(campo);
                html += this.renderizarCabecalhoOS(campo, valorCabecalho);
                break;
            case 'solicitante':
                html += this.renderizarSolicitante(campo, valor);
                break;
            case 'descricao_solicitante':
                html += this.renderizarDescricaoSolicitante(campo, valor, { editavel, visivel, obrigatorio });
                break;
            case 'descricao_tecnico':
                html += this.renderizarDescricaoTecnico(campo, valor, { editavel, visivel, obrigatorio });
                break;
            case 'tabela':
                html += this.renderizarTabela(campo, valor);
                break;
            case 'upload':
                html += `<input type="file" class="form-control" name="${campo.id}" id="${campo.id}" multiple ${disabledAttr}>`;
                break;
            default:
                // Se for um tipo desconhecido mas tiver um tipo similar, tentar renderizar
                console.warn(`Tipo de campo desconhecido: ${campo.tipo}`, campo);
                // Fallback: renderizar como texto simples (sem mostrar o ID do campo)
                const valorExibido = valor || campo.label || campo.valor_padrao || '';
                if (valorExibido) {
                    html += `<p class="text-muted">${valorExibido}</p>`;
                } else {
                    // Se não houver valor, não renderizar nada (evitar mostrar IDs ou valores vazios)
                    html += '';
                }
        }
        
        html += `</div>`;
        return html;
    }
    
    renderizarDescricaoTecnico(campo, valor, { editavel = true, visivel = true, obrigatorio = false } = {}) {
        const config = campo.config || {};
        const rows = config.rows || 6;
        const placeholder = config.placeholder || 'Descreva as ocorrências encontradas durante o atendimento...';
        const maxLength = config.maxLength || 5000;
        const obrigatorioCampo = obrigatorio || campo.obrigatorio || campo.validation?.required || false;
        
        // Resolver valor
        let valorCampo = '';
        if (valor !== null && valor !== undefined) {
            valorCampo = String(valor);
        }
        
        const maxLengthAttr = maxLength ? `maxlength="${maxLength}"` : '';
        // Verificar permissões: técnico atribuído ou hierarquia acima
        const podeEditar = this.verificarPermissaoDescricaoTecnico(campo, editavel);
        const readonlyAttr = (!podeEditar || campo.data?.mode === 'readonly') ? 'readonly' : '';
        const disabledAttr = (!podeEditar || campo.data?.mode === 'readonly') ? 'disabled' : '';
        const classeValidacao = obrigatorioCampo ? 'is-invalid' : '';
        
        let html = `<div class="descricao-tecnico-renderizado">`;
        
        // Label com ícone de histórico (será preenchido via JS após renderização)
        html += `<div class="d-flex align-items-center mb-2">`;
        html += `<label class="form-label mb-0 me-2">${this.escapeHtml(campo.label || 'Descrição das Ocorrências')}</label>`;
        html += `<span id="historico-icon-${campo.id}" class="historico-icon-container"></span>`;
        html += `</div>`;
        
        html += `<textarea class="form-control ${classeValidacao}" 
                  name="${campo.id}" 
                  id="${campo.id}"
                  rows="${rows}" 
                  placeholder="${placeholder}"
                  ${maxLengthAttr}
                  ${readonlyAttr}
                  ${disabledAttr}>${this.escapeHtml(valorCampo || '')}</textarea>`;
        html += `</div>`;
        
        // Buscar histórico de forma assíncrona após renderização
        this.carregarHistoricoDescricaoTecnico(campo.id);
        
        return html;
    }
    
    async carregarHistoricoDescricaoTecnico(campoId) {
        try {
            const historico = await this.buscarHistoricoDescricaoTecnico(campoId);
            const tooltipHistorico = this.formatarTooltipHistorico(historico);
            const iconContainer = document.getElementById(`historico-icon-${campoId}`);
            
            if (iconContainer && historico && historico.length > 0) {
                iconContainer.innerHTML = `<i data-feather="clock" class="historico-icon" style="cursor: help; color: #6c757d; width: 16px; height: 16px;" 
                      title="${this.escapeHtml(tooltipHistorico)}" 
                      data-bs-toggle="tooltip" 
                      data-bs-placement="top"></i>`;
                
                // Inicializar tooltip do Bootstrap se disponível
                if (window.bootstrap && window.bootstrap.Tooltip) {
                    const tooltipElement = iconContainer.querySelector('[data-bs-toggle="tooltip"]');
                    if (tooltipElement) {
                        new window.bootstrap.Tooltip(tooltipElement);
                    }
                }
                
                // Inicializar feather icons
                if (window.feather) {
                    window.feather.replace();
                }
            }
        } catch (error) {
            console.warn('Erro ao carregar histórico:', error);
        }
    }
    
    verificarPermissaoDescricaoTecnico(campo, editavelPadrao) {
        // Se não pode editar por padrão, não pode editar
        if (!editavelPadrao) {
            return false;
        }
        
        const config = campo.config || {};
        const permiteEdicaoTecnico = config.permite_edicao_tecnico !== undefined ? config.permite_edicao_tecnico : true;
        const permiteEdicaoHierarquia = config.permite_edicao_hierarquia_acima !== undefined ? config.permite_edicao_hierarquia_acima : true;
        
        // Verificar se usuário é técnico atribuído
        const contexto = this.contexto || {};
        const os = contexto.os || {};
        const user = contexto.user || {};
        
        // Se é técnico atribuído e permite edição por técnico
        if (permiteEdicaoTecnico && os.tecnico_id && user.id && os.tecnico_id === user.id) {
            return true;
        }
        
        // Se é hierarquia acima e permite edição por hierarquia
        if (permiteEdicaoHierarquia && user.papel_organizacional) {
            const hierarquiaAcima = ['GESTOR', 'SUPERVISOR', 'LIDER'];
            if (hierarquiaAcima.includes(user.papel_organizacional)) {
                return true;
            }
        }
        
        return false;
    }
    
    async buscarHistoricoDescricaoTecnico(campoId) {
        try {
            const contexto = this.contexto || {};
            const os = contexto.os || {};
            
            if (!os.id) {
                return [];
            }
            
            // Buscar histórico via API (endpoint correto: /execucao/{os_id}/historico-formulario)
            const response = await fetch(`/api/v1/manutencao/execucao/${os.id}/historico-formulario?campo_id=${encodeURIComponent(campoId)}`, {
                credentials: 'include',
                headers: {
                    'Accept': 'application/json'
                }
            });
            
            if (!response.ok) {
                console.warn('Erro ao buscar histórico:', response.status);
                return [];
            }
            
            const historico = await response.json();
            return historico || [];
        } catch (error) {
            console.warn('Erro ao buscar histórico de descrição técnico:', error);
            return [];
        }
    }
    
    formatarTooltipHistorico(historico) {
        if (!historico || historico.length === 0) {
            return 'Nenhuma alteração registrada';
        }
        
        // Ordenar do mais recente para o mais antigo
        const historicoOrdenado = [...historico].sort((a, b) => {
            const dataA = new Date(a.data_hora);
            const dataB = new Date(b.data_hora);
            return dataB - dataA;
        });
        
        // Formatar datas
        const datasFormatadas = historicoOrdenado.map(item => {
            const data = new Date(item.data_hora);
            const dia = String(data.getDate()).padStart(2, '0');
            const mes = String(data.getMonth() + 1).padStart(2, '0');
            const ano = data.getFullYear();
            const hora = String(data.getHours()).padStart(2, '0');
            const minuto = String(data.getMinutes()).padStart(2, '0');
            return `${dia}/${mes}/${ano} ${hora}:${minuto}`;
        });
        
        return 'Histórico de alterações:\n' + datasFormatadas.map(d => `• ${d}`).join('\n');
    }
    
    /**
     * Resolver valor do campo baseado em data.mode
     */
    /**
     * Resolver valor do campo com ordem determinística
     * 
     * Referência: PLANO_PCM/plano_1.md - Etapa 4 (Ordem Determinística de Resolução)
     * 
     * Ordem de resolução:
     * 1. binding explícito (computed)
     * 2. dados[campo.id] (resposta salva)
     * 3. contexto.os.* (se binding existe)
     * 4. contexto.header.* (se binding existe)
     * 5. contexto.* (fallback geral)
     * 6. default/valor_padrao
     * 
     * IMPORTANTE: Não usa heurística por nome de campo. Resolve apenas por binding/path explícito.
     */
    /**
     * Resolver valor do campo seguindo ordem estrita conforme Etapa 04:
     * 1. binding explícito
     * 2. dados[campo.id]
     * 3. contexto.os.*
     * 4. contexto.header.*
     * 5. contexto.*
     * 
     * Referência: PLANO_PCM/plano_1.md - Etapa 4
     */
    resolverValorCampo(campo) {
        const data = campo.data || {};
        const ctx = this.contexto || {};
        const dados = this.dados || {};
        
        // 1. Binding explícito (independente do mode)
        if (data.binding) {
            // Tentar resolver via ruleEngine primeiro
            const valorBinding = this.ruleEngine.resolverBinding(data.binding, ctx);
            if (valorBinding !== null && valorBinding !== undefined && valorBinding !== '') {
                return valorBinding;
            }
            
            // Fallback: resolver por path literal se binding é string simples
            if (typeof data.binding === 'string' || (data.binding && typeof data.binding.source === 'string')) {
                const bindingPath = typeof data.binding === 'string' ? data.binding : data.binding.source;
                if (bindingPath) {
                    const v = this.getByPath(ctx, bindingPath);
                    if (v !== null && v !== undefined && v !== '') {
                        return v;
                    }
                }
            }
        }
        
        // 2. dados[campo.id]
        if (Object.prototype.hasOwnProperty.call(dados, campo.id)) {
            const v = dados[campo.id];
            if (v !== null && v !== undefined) {
                return v;
            }
        }
        
        // 3. contexto.os.*
        if (ctx.os) {
            // Se tem binding explícito para os.*, já foi resolvido no passo 1
            // Aqui tentamos mapeamentos comuns sem binding explícito
            const campoIdLower = campo.id.toLowerCase();
            
            // Mapeamentos comuns de campos para contexto.os.*
            if (campoIdLower === 'numero_os' || campoIdLower === 'numeroos') {
                if (ctx.os.number) return ctx.os.number;
                if (ctx.os.numero_os) return ctx.os.numero_os;
            }
            if (campoIdLower === 'status' || campoIdLower === 'status_os') {
                if (ctx.os.status) return ctx.os.status;
            }
            if (campoIdLower.includes('descricao') && ctx.os.descricao_problema) {
                return ctx.os.descricao_problema;
            }
            if (campoIdLower.includes('prioridade') && ctx.os.prioridade) {
                return ctx.os.prioridade;
            }
            // Tentar resolver via getByPath para outros campos de contexto.os.*
            const osPath = `os.${campo.id}`;
            const v = this.getByPath(ctx, osPath);
            if (v !== null && v !== undefined && v !== '') {
                return v;
            }
        }
        
        // 4. contexto.header.*
        if (ctx.header) {
            const campoIdLower = campo.id.toLowerCase();
            
            // Mapeamentos comuns de campos para contexto.header.*
            if (campoIdLower.includes('documento') || campoIdLower.includes('document')) {
                const headerDoc = ctx.header.documento || {};
                if (campoIdLower.includes('numero') && headerDoc.numero) {
                    return headerDoc.numero;
                }
                if (campoIdLower.includes('codigo') && headerDoc.codigo) {
                    return headerDoc.codigo;
                }
                if (campoIdLower.includes('revisao') && headerDoc.revisao) {
                    return headerDoc.revisao;
                }
                if ((campoIdLower.includes('data_emissao') || campoIdLower.includes('dataemissao')) && headerDoc.data_emissao) {
                    return headerDoc.data_emissao;
                }
            }
            // Campos relacionados a unidade do header
            if (campoIdLower.includes('unidade') || campoIdLower.includes('unit')) {
                const headerUnit = ctx.header.unidade || {};
                if (headerUnit.nome) {
                    return headerUnit.nome;
                }
                if (headerUnit.name) {
                    return headerUnit.name;
                }
            }
            // Tentar resolver via getByPath para outros campos de contexto.header.*
            const headerPath = `header.${campo.id}`;
            const v = this.getByPath(ctx, headerPath);
            if (v !== null && v !== undefined && v !== '') {
                return v;
            }
        }
        
        // 5. contexto.* (outros campos do contexto sem prefixo específico)
        if (data.binding) {
            const bindingPath = typeof data.binding === 'string' ? data.binding : (data.binding.source || '');
            // Só tentar se não for os.* ou header.* (já tentamos acima)
            if (bindingPath && !bindingPath.startsWith('os.') && !bindingPath.startsWith('header.')) {
                const v = this.getByPath(ctx, bindingPath);
                if (v !== null && v !== undefined && v !== '') {
                    return v;
                }
            }
        }
        
        // Fallback: default / valor_padrao
        if (data.default !== undefined) {
            return data.default;
        }
        if (campo.valor_padrao !== undefined) {
            return campo.valor_padrao;
        }
        
        // Fallback final: string vazia
        return '';
    }
    
    /**
     * Formatar valor conforme render.format
     */
    formatarValor(valor, format, tipo) {
        if (!valor && valor !== 0) {
            return '';
        }
        
        // Formatação de data
        if (tipo === 'date' && format.date) {
            if (valor instanceof Date) {
                return this.formatarData(valor, format.date);
            } else if (typeof valor === 'string') {
                const data = new Date(valor);
                if (!isNaN(data.getTime())) {
                    return this.formatarData(data, format.date);
                }
            }
        }
        
        // Formatação de datetime
        if (tipo === 'datetime' && format.datetime) {
            if (valor instanceof Date) {
                return this.formatarDataHora(valor, format.datetime);
            } else if (typeof valor === 'string') {
                const data = new Date(valor);
                if (!isNaN(data.getTime())) {
                    return this.formatarDataHora(data, format.datetime);
                }
            }
        }
        
        // Formatação de número com decimais
        if (tipo === 'number' && format.numberDecimals !== null && format.numberDecimals !== undefined) {
            const num = parseFloat(valor);
            if (!isNaN(num)) {
                return num.toFixed(format.numberDecimals);
            }
        }
        
        // Máscara será aplicada no input, não na formatação do valor
        // (mantemos valor limpo para processamento)
        
        return valor;
    }
    
    /**
     * Formatar data conforme formato especificado
     */
    formatarData(data, formato) {
        const dia = String(data.getDate()).padStart(2, '0');
        const mes = String(data.getMonth() + 1).padStart(2, '0');
        const ano = data.getFullYear();
        
        return formato
            .replace('DD', dia)
            .replace('MM', mes)
            .replace('YYYY', ano);
    }
    
    /**
     * Formatar data/hora conforme formato especificado
     */
    formatarDataHora(data, formato) {
        const dia = String(data.getDate()).padStart(2, '0');
        const mes = String(data.getMonth() + 1).padStart(2, '0');
        const ano = data.getFullYear();
        const hora = String(data.getHours()).padStart(2, '0');
        const minuto = String(data.getMinutes()).padStart(2, '0');
        
        return formato
            .replace('DD', dia)
            .replace('MM', mes)
            .replace('YYYY', ano)
            .replace('HH', hora)
            .replace('mm', minuto);
    }
    
    /**
     * Aplicar classes CSS conforme layout
     */
    aplicarLayoutClasses(layout) {
        const classes = [];
        
        if (layout.width === 'half') {
            classes.push('form-builder-field-width-half');
        } else if (layout.width === 'third') {
            classes.push('form-builder-field-width-third');
        } else {
            classes.push('form-builder-field-width-full');
        }
        
        if (layout.align === 'center') {
            classes.push('form-builder-field-align-center');
        } else if (layout.align === 'right') {
            classes.push('form-builder-field-align-right');
        } else {
            classes.push('form-builder-field-align-left');
        }
        
        return classes.join(' ');
    }
    
    renderizarChecklist(campo, valor, { editavel = true, visivel = true, obrigatorio = false } = {}) {
        // ETAPA 5: Modo do bloco (read/write)
        // Referência: PLANO_PCM/ETAPA_5_IMPLEMENTACAO.md
        const readonlyClass = !editavel ? 'fb-readonly' : '';
        const disabledAttr = !editavel ? 'disabled' : '';
        
        let html = `<div class="checklist-renderizado ${readonlyClass}" data-editavel="${editavel}">`;
        const itens = campo.config?.itens || valor?.itens || [];
        itens.forEach((item, index) => {
            const itemId = item.id || `item_${index}`;
            const respostaAtual = valor?.itens?.find(i => i.id === itemId)?.resposta || '';
            html += `<div class="form-check mb-2">`;
            html += `<input class="form-check-input" type="radio" name="${campo.id}_${itemId}" id="${campo.id}_${itemId}_c" value="C" ${respostaAtual === 'C' ? 'checked' : ''} ${disabledAttr}>`;
            html += `<label class="form-check-label" for="${campo.id}_${itemId}_c">C - Conforme</label>`;
            html += `</div>`;
            html += `<div class="form-check mb-2">`;
            html += `<input class="form-check-input" type="radio" name="${campo.id}_${itemId}" id="${campo.id}_${itemId}_nc" value="NC" ${respostaAtual === 'NC' ? 'checked' : ''} ${disabledAttr}>`;
            html += `<label class="form-check-label" for="${campo.id}_${itemId}_nc">NC - Não Conforme</label>`;
            html += `</div>`;
            html += `<div class="form-check mb-2">`;
            html += `<input class="form-check-input" type="radio" name="${campo.id}_${itemId}" id="${campo.id}_${itemId}_na" value="NA" ${respostaAtual === 'NA' ? 'checked' : ''} ${disabledAttr}>`;
            html += `<label class="form-check-label" for="${campo.id}_${itemId}_na">NA - Não Aplicável</label>`;
            html += `</div>`;
            if (respostaAtual === 'NC') {
                html += `<div class="mb-3">`;
                html += `<label class="form-label">Observação (obrigatória para NC)</label>`;
                html += `<textarea class="form-control" name="${campo.id}_${itemId}_obs" rows="2" required ${disabledAttr}>${valor?.itens?.find(i => i.id === itemId)?.observacao || ''}</textarea>`;
                html += `</div>`;
            }
        });
        html += `</div>`;
        return html;
    }
    
    renderizarApontamentoHoras(campo, valor, { editavel = true, visivel = true, obrigatorio = false } = {}) {
        // ETAPA 5: Modo do bloco (read/write)
        // Referência: PLANO_PCM/ETAPA_5_IMPLEMENTACAO.md
        const readonlyClass = !editavel ? 'fb-readonly' : '';
        
        let html = `<div class="apontamento-horas-renderizado ${readonlyClass}" data-editavel="${editavel}">`;
        html += `<table class="table table-sm table-bordered" id="tabela_apontamentos_${campo.id}">`;
        html += `<thead><tr><th>Técnico</th><th>Início</th><th>Fim</th><th>Pausa</th><th>Retomada</th><th>Total</th>${editavel ? '<th>Ações</th>' : ''}</tr></thead>`;
        html += `<tbody id="tbody_apontamentos_${campo.id}">`;
        const apontamentos = valor?.apontamentos || [];
        if (apontamentos.length === 0) {
            html += `<tr><td colspan="${editavel ? '7' : '6'}" class="text-center text-muted">Nenhum apontamento registrado</td></tr>`;
        } else {
            apontamentos.forEach((ap, index) => {
                html += `<tr data-apontamento-index="${index}">`;
                html += `<td>${ap.tecnico_nome || 'N/A'}</td>`;
                html += `<td>${ap.inicio || '-'}</td>`;
                html += `<td>${ap.fim || '-'}</td>`;
                html += `<td>${ap.pausa || '-'}</td>`;
                html += `<td>${ap.retomada || '-'}</td>`;
                html += `<td>${ap.total_horas || '0h'}</td>`;
                if (editavel) {
                    html += `<td><button type="button" class="btn btn-sm btn-danger" onclick="removerApontamento('${campo.id}', ${index})">Remover</button></td>`;
                }
                html += `</tr>`;
            });
        }
        html += `</tbody></table>`;
        // Botão "Adicionar Apontamento" só aparece se editável
        if (editavel) {
            html += `<button type="button" class="btn btn-sm btn-primary" onclick="adicionarApontamento('${campo.id}')">Adicionar Apontamento</button>`;
        }
        html += `</div>`;
        
        // Carregar técnicos via API
        setTimeout(() => {
            this.carregarTecnicos(campo.id, campo.config?.equipe_id);
        }, 100);
        
        return html;
    }
    
    renderizarMateriaisPecas(campo, valor, { editavel = true, visivel = true, obrigatorio = false } = {}) {
        // ETAPA 5: Modo do bloco (read/write)
        // Referência: PLANO_PCM/ETAPA_5_IMPLEMENTACAO.md
        const readonlyClass = !editavel ? 'fb-readonly' : '';
        // Garantir que editavel seja sempre string "true" ou "false" explícita
        const editavelStr = editavel ? 'true' : 'false';
        
        let html = `<div class="materiais-pecas-renderizado ${readonlyClass}" data-editavel="${editavelStr}">`;
        html += `<table class="table table-sm table-bordered" id="tabela_materiais_${campo.id}">`;
        html += `<thead><tr><th>Material</th><th>Código</th><th>Quantidade</th><th>Unidade</th><th>Valor Unit.</th><th>Local Aplicado</th><th>Técnico</th>${editavel ? '<th>Ações</th>' : ''}</tr></thead>`;
        html += `<tbody id="tbody_materiais_${campo.id}">`;
        html += `<tr><td colspan="${editavel ? '8' : '7'}" class="text-center text-muted">Carregando materiais...</td></tr>`;
        html += `</tbody></table>`;
        // Botão "Adicionar Material" só aparece se editável
        if (editavel) {
            html += `<button type="button" class="btn btn-sm btn-primary" onclick="adicionarMaterial('${campo.id}')">Adicionar Material</button>`;
        }
        html += `</div>`;
        
        // Carregar materiais via API da OS
        setTimeout(() => {
            this.carregarMateriaisOS(campo.id);
        }, 100);
        
        return html;
    }
    
    renderizarEquipamentos(campo, valor) {
        let html = `<div class="equipamentos-renderizado">`;
        html += `<select class="form-select" name="${campo.id}" id="${campo.id}" data-tipo="equipamentos" onchange="carregarEquipamento('${campo.id}', this.value)">`;
        html += `<option value="">Carregando equipamentos...</option>`;
        html += `</select>`;
        html += `<small class="text-muted">Equipamentos carregados do cadastro</small>`;
        html += `</div>`;
        
        // Carregar equipamentos via API após renderização
        setTimeout(() => {
            this.carregarEquipamentos(campo.id, campo.config?.setor_id);
        }, 100);
        
        return html;
    }
    
    async carregarEquipamentos(campoId, setorId = null) {
        try {
            let url = `/api/v1/manutencao/form-builder/equipamentos?limit=200`;
            if (setorId) {
                url += `&setor_id=${setorId}`;
            }
            
            const response = await fetch(url, {
                credentials: 'include'
            });
            
            if (response.ok) {
                const equipamentos = await response.json();
                const select = document.getElementById(campoId);
                if (select) {
                    select.innerHTML = '<option value="">Selecione um equipamento...</option>';
                    equipamentos.forEach(eq => {
                        const option = document.createElement('option');
                        option.value = eq.id;
                        option.textContent = eq.label;
                        select.appendChild(option);
                    });
                }
            }
        } catch (error) {
            console.error('Erro ao carregar equipamentos:', error);
        }
    }
    
    renderizarAtivos(campo, valor) {
        let html = `<div class="ativos-renderizado">`;
        html += `<select class="form-select" name="${campo.id}" id="${campo.id}" data-tipo="ativos" onchange="carregarAtivoSelecionado('${campo.id}', this.value)">`;
        html += `<option value="">Carregando ativos...</option>`;
        html += `</select>`;
        html += `<small class="text-muted">Ativos da unidade carregados do cadastro</small>`;
        html += `</div>`;
        
        // Carregar ativos via API após renderização (filtra automaticamente por unidade do usuário)
        setTimeout(() => {
            this.carregarAtivos(campo.id, campo.config?.unidade_id, campo.config?.setor_id);
        }, 100);
        
        return html;
    }
    
    async carregarAtivos(campoId, unidadeId = null, setorId = null) {
        try {
            let url = `/api/v1/manutencao/form-builder/ativos?limit=200`;
            if (unidadeId) {
                url += `&unidade_id=${unidadeId}`;
            }
            if (setorId) {
                url += `&setor_id=${setorId}`;
            }
            
            const response = await fetch(url, {
                credentials: 'include'
            });
            
            if (response.ok) {
                const ativos = await response.json();
                const select = document.getElementById(campoId);
                if (select) {
                    select.innerHTML = '<option value="">Selecione um ativo...</option>';
                    ativos.forEach(ativo => {
                        const option = document.createElement('option');
                        option.value = ativo.id;
                        option.textContent = ativo.label;
                        select.appendChild(option);
                    });
                }
            } else {
                const select = document.getElementById(campoId);
                if (select) {
                    select.innerHTML = '<option value="">Erro ao carregar ativos</option>';
                }
            }
        } catch (error) {
            console.error('Erro ao carregar ativos:', error);
            const select = document.getElementById(campoId);
            if (select) {
                select.innerHTML = '<option value="">Erro ao carregar ativos</option>';
            }
        }
    }
    
    async carregarMateriais(campoId) {
        try {
            const response = await fetch(`/api/v1/manutencao/form-builder/materiais?limit=200`, {
                credentials: 'include'
            });
            
            if (response.ok) {
                const materiais = await response.json();
                // Armazenar materiais para uso no modal de adicionar material
                window.materiaisDisponiveis = materiais;
            }
        } catch (error) {
            console.error('Erro ao carregar materiais:', error);
        }
    }
    
    /**
     * Carregar materiais já salvos da OS
     */
    async carregarMateriaisOS(campoId) {
        if (!this.osId) {
            console.warn('os_id não disponível para carregar materiais');
            const tbody = document.getElementById(`tbody_materiais_${campoId}`);
            if (tbody) {
                tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">Nenhum material registrado</td></tr>';
            }
            return;
        }
        
        try {
            const response = await fetch(`/api/v1/manutencao/materiais/os/${this.osId}`, {
                credentials: 'include'
            });
            
            if (response.ok) {
                const materiais = await response.json();
                this.atualizarTabelaMateriais(campoId, materiais);
            } else {
                console.error('Erro ao carregar materiais da OS:', response.statusText);
                const tbody = document.getElementById(`tbody_materiais_${campoId}`);
                if (tbody) {
                    tbody.innerHTML = '<tr><td colspan="8" class="text-center text-danger">Erro ao carregar materiais</td></tr>';
                }
            }
        } catch (error) {
            console.error('Erro ao carregar materiais da OS:', error);
            const tbody = document.getElementById(`tbody_materiais_${campoId}`);
            if (tbody) {
                tbody.innerHTML = '<tr><td colspan="8" class="text-center text-danger">Erro ao carregar materiais</td></tr>';
            }
        }
    }
    
    /**
     * Atualizar tabela de materiais com dados do banco
     * ETAPA 5: Respeita modo read/write do bloco
     */
    atualizarTabelaMateriais(campoId, materiais) {
        const tbody = document.getElementById(`tbody_materiais_${campoId}`);
        if (!tbody) return;
        
        // Verificar estado editavel do bloco (ETAPA 5)
        const container = tbody.closest('.materiais-pecas-renderizado');
        const editavel = container?.dataset.editavel === 'true';
        const colSpan = editavel ? '8' : '7';
        
        if (materiais.length === 0) {
            tbody.innerHTML = `<tr><td colspan="${colSpan}" class="text-center text-muted">Nenhum material registrado</td></tr>`;
            return;
        }
        
        let html = '';
        materiais.forEach((mat, index) => {
            const nomeMaterial = mat.nome_material || mat.item?.nome || 'N/A';
            const codigoMaterial = mat.codigo_material || mat.item?.codigo_interno || '-';
            const unidadeMedida = mat.unidade_medida || mat.uom?.simbolo || mat.uom?.codigo || '-';
            const valorUnitario = mat.valor_unitario ? parseFloat(mat.valor_unitario).toFixed(2) : '0.00';
            const tecnicoNome = mat.tecnico_nome || '-';
            
            html += `<tr data-material-id="${mat.id}" data-material-index="${index}">`;
            html += `<td>${nomeMaterial}</td>`;
            html += `<td>${codigoMaterial}</td>`;
            html += `<td>${mat.quantidade || '0'}</td>`;
            html += `<td>${unidadeMedida}</td>`;
            html += `<td>R$ ${valorUnitario}</td>`;
            html += `<td>${mat.local_aplicado || '-'}</td>`;
            html += `<td>${tecnicoNome}</td>`;
            // Botão "Remover" só aparece se editável
            if (editavel) {
                html += `<td><button type="button" class="btn btn-sm btn-danger" onclick="removerMaterial('${campoId}', ${mat.id})">Remover</button></td>`;
            }
            html += `</tr>`;
        });
        
        tbody.innerHTML = html;
    }
    
    /**
     * Buscar itens do catálogo para autocomplete
     */
    async buscarItensCatalogo(busca = '') {
        try {
            let url = `/api/v1/comum/itens?limit=50&ativo=true`;
            if (busca) {
                url += `&busca=${encodeURIComponent(busca)}`;
            }
            
            const response = await fetch(url, {
                credentials: 'include'
            });
            
            if (response.ok) {
                const itens = await response.json();
                // Mapear itens para formato esperado pelo frontend
                // A API retorna uom como objeto aninhado, precisamos extrair para campos planos
                return itens.map(item => ({
                    id: item.id,
                    codigo_interno: item.codigo_interno,
                    nome: item.nome,
                    tipo_item: item.tipo_item,
                    uom_id: item.uom_id,
                    // Extrair campos do objeto uom aninhado
                    uom_codigo: item.uom?.codigo || null,
                    uom_nome: item.uom?.nome || null,
                    uom_simbolo: item.uom?.simbolo || item.uom?.codigo || 'un',
                    // Compatibilidade: manter campos antigos
                    unidade_medida: item.uom?.simbolo || item.uom?.codigo || 'un',
                    label: item.codigo_interno ? `${item.codigo_interno} - ${item.nome}` : item.nome
                }));
            }
            return [];
        } catch (error) {
            console.error('Erro ao buscar itens do catálogo:', error);
            return [];
        }
    }
    
    async carregarTecnicos(campoId, equipeId = null) {
        try {
            let url = `/api/v1/manutencao/form-builder/tecnicos?limit=200`;
            if (equipeId) {
                url += `&equipe_id=${equipeId}`;
            }
            
            const response = await fetch(url, {
                credentials: 'include'
            });
            
            if (response.ok) {
                const tecnicos = await response.json();
                // Armazenar técnicos para uso no bloco de apontamento
                window.tecnicosDisponiveis = tecnicos;
            }
        } catch (error) {
            console.error('Erro ao carregar técnicos:', error);
        }
    }
    
    renderizarStatusFinal(campo, valor) {
        const config = campo.config || {};
        const opcoes = config.opcoes || [
            {value: "concluido", label: "Concluído"},
            {value: "andamento", label: "Em Andamento"},
            {value: "paliativo", label: "Medida Paliativa"}
        ];
        let html = `<div class="status-final-renderizado">`;
        html += `<select class="form-select" name="${campo.id}" id="${campo.id}" onchange="validarStatusFinal('${campo.id}', this.value)">`;
        html += `<option value="">Selecione...</option>`;
        opcoes.forEach(opcao => {
            html += `<option value="${opcao.value}" ${valor === opcao.value ? 'selected' : ''}>${opcao.label}</option>`;
        });
        html += `</select>`;
        if (config.exige_justificativa_se === "paliativo" && valor === "paliativo") {
            const justificativaId = config.campo_justificativa_id || `${campo.id}_justificativa`;
            html += `<div class="mt-2">`;
            html += `<label class="form-label">Justificativa (obrigatória para medida paliativa)</label>`;
            html += `<textarea class="form-control" name="${justificativaId}" id="${justificativaId}" rows="3" required></textarea>`;
            html += `</div>`;
        }
        html += `</div>`;
        return html;
    }
    
    renderizarSegurancaOperacional(campo, valor) {
        let html = `<div class="seguranca-operacional-renderizado">`;
        html += `<div class="form-check form-check-inline">`;
        html += `<input class="form-check-input" type="radio" name="${campo.id}" id="${campo.id}_sim" value="true" ${valor === true || valor === 'true' ? 'checked' : ''} required>`;
        html += `<label class="form-check-label" for="${campo.id}_sim">Sim - Equipamento seguro para operação</label>`;
        html += `</div>`;
        html += `<div class="form-check form-check-inline">`;
        html += `<input class="form-check-input" type="radio" name="${campo.id}" id="${campo.id}_nao" value="false" ${valor === false || valor === 'false' ? 'checked' : ''} required>`;
        html += `<label class="form-check-label" for="${campo.id}_nao">Não - Equipamento NÃO seguro</label>`;
        html += `</div>`;
        html += `</div>`;
        return html;
    }
    
    renderizarQSA(campo, valor, { editavel = true, visivel = true, obrigatorio = false } = {}) {
        // ETAPA 5: Modo do bloco (read/write)
        // Referência: PLANO_PCM/ETAPA_5_IMPLEMENTACAO.md
        const readonlyClass = !editavel ? 'fb-readonly' : '';
        const disabledAttr = !editavel ? 'disabled' : '';
        
        let html = `<div class="qsa-renderizado ${readonlyClass}" data-editavel="${editavel}">`;
        html += `<div class="form-check form-check-inline">`;
        html += `<input class="form-check-input" type="radio" name="${campo.id}" id="${campo.id}_c" value="C" ${valor === 'C' ? 'checked' : ''} required ${disabledAttr}>`;
        html += `<label class="form-check-label" for="${campo.id}_c">C - Conforme</label>`;
        html += `</div>`;
        html += `<div class="form-check form-check-inline">`;
        html += `<input class="form-check-input" type="radio" name="${campo.id}" id="${campo.id}_nc" value="NC" ${valor === 'NC' ? 'checked' : ''} required ${disabledAttr} onchange="validarQSA('${campo.id}', this.value)">`;
        html += `<label class="form-check-label" for="${campo.id}_nc">NC - Não Conforme</label>`;
        html += `</div>`;
        if (valor === 'NC') {
            html += `<div class="mt-2">`;
            html += `<label class="form-label">Observação (obrigatória para NC)</label>`;
            html += `<textarea class="form-control" name="${campo.id}_obs" id="${campo.id}_obs" rows="3" required ${disabledAttr}>${valor?.observacao || ''}</textarea>`;
            html += `</div>`;
        }
        html += `</div>`;
        return html;
    }
    
    /**
     * Resolver valores do cabeçalho a partir do contexto
     */
    resolverValoresCabecalho(campo) {
        const config = campo.config || {};
        const contexto = this.contexto || {};
        const os = contexto.os || {};
        const refs = contexto.refs || {};
        const unit = refs.unit || {};
        const company = refs.company || {};
        const program = refs.program || {};
        const template = contexto.template || {};
        const header = contexto.header || {};
        const headerUnidade = header.unidade || {};
        
        // Obter código do documento do config ou do programa
        const codigoDocumento = config.codigoDocumento || program.code || 'RSGM078/SIF2960';
        
        // Data de emissão: data de criação do template ou data atual
        let issueDate = '—';
        if (template.criado_em) {
            try {
                const data = new Date(template.criado_em);
                const mes = String(data.getMonth() + 1).padStart(2, '0');
                const ano = data.getFullYear();
                issueDate = `${mes}/${ano}`;
            } catch (e) {
                console.warn('Erro ao formatar data de criação do template:', e);
            }
        } else if (os.created_at || os.criado_em) {
            try {
                const data = new Date(os.created_at || os.criado_em);
                const mes = String(data.getMonth() + 1).padStart(2, '0');
                const ano = data.getFullYear();
                issueDate = `${mes}/${ano}`;
            } catch (e) {
                console.warn('Erro ao formatar data de criação da OS:', e);
            }
        }
        
        // Data de revisão: usar template_atualizado_em do contexto (prioridade) ou fallback
        let revisionDate = '—';
        if (contexto.template_atualizado_em) {
            try {
                const data = new Date(contexto.template_atualizado_em);
                const dia = String(data.getDate()).padStart(2, '0');
                const mes = String(data.getMonth() + 1).padStart(2, '0');
                const ano = data.getFullYear();
                revisionDate = `${dia}/${mes}/${ano}`;
            } catch (e) {
                console.warn('Erro ao formatar data de atualização do template:', e);
            }
        } else if (template.atualizado_em) {
            try {
                const data = new Date(template.atualizado_em);
                const dia = String(data.getDate()).padStart(2, '0');
                const mes = String(data.getMonth() + 1).padStart(2, '0');
                const ano = data.getFullYear();
                revisionDate = `${dia}/${mes}/${ano}`;
            } catch (e) {
                console.warn('Erro ao formatar data de atualização do template:', e);
            }
        } else if (program.revision_date) {
            try {
                const data = new Date(program.revision_date);
                const dia = String(data.getDate()).padStart(2, '0');
                const mes = String(data.getMonth() + 1).padStart(2, '0');
                const ano = data.getFullYear();
                revisionDate = `${dia}/${mes}/${ano}`;
            } catch (e) {
                console.warn('Erro ao formatar data de revisão do programa:', e);
            }
        }
        
        // Número de revisão: usar template_versao do contexto (prioridade) ou fallback
        const revisionNumber = contexto.template_versao || template.versao || program.revision_number || '00';
        
        // Nome do template para tipo de OS: usar template_nome do contexto (prioridade) ou fallback
        const osType = contexto.template_nome || template.nome || 'Ordem de Serviço';
        
        // Resolver valores dinâmicos da OS
        // Número da OS
        const numeroOS = os.numero_os || os.number || '[000000]';
        
        // Data de Criação
        let dataCriacao = '—';
        if (os.data_solicitacao || os.created_at || os.criado_em) {
            try {
                const data = new Date(os.data_solicitacao || os.created_at || os.criado_em);
                dataCriacao = this.formatarDataHora(os.data_solicitacao || os.created_at || os.criado_em);
            } catch (e) {
                console.warn('Erro ao formatar data de criação:', e);
            }
        }
        
        // Ativo - buscar do contexto ou refs
        const ativo = (() => {
            if (refs.asset && refs.asset.name) return refs.asset.name;
            if (os.ativo_nome) return os.ativo_nome;
            return '—';
        })();
        
        // Prioridade
        const prioridade = os.prioridade || '—';
        
        // Prazo de Término
        let prazoTermino = '—';
        if (os.data_fim) {
            try {
                prazoTermino = this.formatarDataHora(os.data_fim);
            } catch (e) {
                console.warn('Erro ao formatar prazo de término:', e);
            }
        }
        
        // Setor - buscar do contexto ou refs
        const setor = (() => {
            if (refs.setor && refs.setor.name) return refs.setor.name;
            if (os.setor_nome) return os.setor_nome;
            return '—';
        })();
        
        // Nome do Solicitante - buscar do contexto
        const nome = (() => {
            if (contexto.user && contexto.user.nome) return contexto.user.nome;
            if (os.solicitante_nome) return os.solicitante_nome;
            return '—';
        })();
        
        // Email do Solicitante - buscar do contexto
        const email = (() => {
            if (contexto.user && contexto.user.email) return contexto.user.email;
            if (os.solicitante_email) return os.solicitante_email;
            return '—';
        })();
        
        return {
            logoUrl: company.logo_url || '/static/img/logo_frigol.png',
            programName: program.name || 'Programa de Gestão de Manutenção',
            // Formatar nome da unidade: se tiver address_full, usar; senão, usar nome; senão, fallback
            unitName: (() => {
                if (headerUnidade.nome) {
                    return headerUnidade.nome;
                }
                if (unit.address_full) {
                    return unit.address_full;
                }
                if (unit.name) {
                    // Se o nome da unidade não tiver cidade/estado, tentar construir
                    const parts = [];
                    if (unit.name) parts.push(unit.name);
                    if (unit.cidade) parts.push(unit.cidade);
                    if (unit.estado) parts.push(unit.estado);
                    if (parts.length > 1) {
                        return parts.join(' - ');
                    }
                    return unit.name;
                }
                return 'Matriz - Lençóis Paulista - SP';
            })(),
            documentCode: codigoDocumento,
            issueDate: issueDate,
            revisionDate: revisionDate,
            revisionNumber: revisionNumber,
            pageCounter: '1 de 1', // TODO: Implementar contador de páginas
            osType: osType,
            osNumber: numeroOS,
            osCreatedAt: os.created_at || os.criado_em || null,
            // Campos dinâmicos
            numeroOS: numeroOS,
            dataCriacao: dataCriacao,
            ativo: ativo,
            prioridade: prioridade,
            prazoTermino: prazoTermino,
            setor: setor,
            nome: nome,
            email: email
        };
    }
    
    renderizarCabecalhoOS(campo, valor) {
        const config = campo.config || {};
        const layout = campo.layout || {};
        
        // Valores padrão
        const variant = layout.variant || 'print_like';
        const columns = layout.columns || 3;
        const showBorders = layout.showBorders !== undefined ? layout.showBorders : true;
        
        // Classes CSS
        const borderClass = showBorders ? 'border' : '';
        const variantClass = variant === 'compact' ? 'cabecalho-os-compact' : 'cabecalho-os-print-like';
        const columnsClass = `cabecalho-os-cols-${columns}`;
        
        let html = `<div class="cabecalho-os cabecalho-os-renderizado ${variantClass} ${columnsClass} ${borderClass} mb-3">`;
        
        // Renderizar conforme variant
        if (variant === 'print_like') {
            html += this.renderizarCabecalhoPrintLike(config, columns, valor);
        } else {
            html += this.renderizarCabecalhoCompact(config, columns, valor);
        }
        
        html += `</div>`;
        return html;
    }
    
    renderizarCabecalhoPrintLike(config, columns, valor) {
        let html = '';
        
        // ROW TOP
        html += '<div class="os-hd-row os-hd-top">';
        
        // LEFT: LOGO
        html += '<div class="os-hd-cell os-hd-left">';
        if (config.showLogo !== false) {
            html += '<div class="os-hd-logo">';
            // Prioridade: logoUrl do contexto > logo padrão
            const logoUrl = valor?.logoUrl || '/static/img/logo_frigol.png';
            html += `<img class="os-hd-logo-img" src="${logoUrl}" alt="Logo Frigol">`;
            html += '</div>';
        }
        html += '</div>';

        // CENTER: TITLES
        html += '<div class="os-hd-cell os-hd-center">';
        if (config.showProgramName !== false) {
            // Prioridade: valor editável no config > valor do contexto > fallback
            const programName = config.programName || valor?.programName || 'Programa de Gestão de Manutenção';
            html += '<div class="os-hd-title-1">' + programName + '</div>';
        }
        if (config.showUnit !== false) {
            // Prioridade: valor editável no config > valor do contexto > fallback
            const unitName = config.unitName || valor?.unitName || 'Matriz - Lençóis Paulista - SP';
            html += '<div class="os-hd-title-2">' + unitName + '</div>';
        }
        if (config.showAddress === true) {
            // Prioridade: valor editável no config > valor do contexto > fallback
            const address = config.address || valor?.unitAddress || '';
            html += '<div class="os-hd-title-3" style="font-size: 0.85em; color: #666; margin-top: 4px;">' + (address || '—') + '</div>';
        }
        html += '</div>';

        // RIGHT: META TABLE
        html += '<div class="os-hd-cell os-hd-right">';
        html += '<div class="os-hd-meta">';
        
        // Sempre mostrar 5 linhas para manter altura fixa (como formulário oficial)
        if (config.showDocumentCode !== false) {
            // Prioridade: valor editável no config > valor do contexto > fallback
            const docCode = config.codigoDocumento || valor?.documentCode || 'RSGM078/SIF2960';
            html += '<div class="os-hd-meta-row">';
            html += '<div class="k">Código</div>';
            html += '<div class="v">' + docCode + '</div>';
            html += '</div>';
        } else {
            html += '<div class="os-hd-meta-row"><div class="k">—</div><div class="v">—</div></div>';
        }
        
        if (config.showIssueDate !== false) {
            const issueDate = valor?.issueDate || '—';
            html += '<div class="os-hd-meta-row">';
            html += '<div class="k">Data Emissão</div>';
            html += '<div class="v">' + issueDate + '</div>';
            html += '</div>';
        } else {
            html += '<div class="os-hd-meta-row"><div class="k">—</div><div class="v">—</div></div>';
        }
        
        if (config.showRevision !== false) {
            const revisionDate = valor?.revisionDate || '—';
            const revisionNumber = valor?.revisionNumber || '—';
            html += '<div class="os-hd-meta-row">';
            html += '<div class="k">Data Revisão</div>';
            html += '<div class="v">' + revisionDate + '</div>';
            html += '</div>';
            html += '<div class="os-hd-meta-row">';
            html += '<div class="k">N° Revisão</div>';
            html += '<div class="v">' + revisionNumber + '</div>';
            html += '</div>';
        } else {
            html += '<div class="os-hd-meta-row"><div class="k">—</div><div class="v">—</div></div>';
            html += '<div class="os-hd-meta-row"><div class="k">—</div><div class="v">—</div></div>';
        }
        
        if (config.showPageCounter !== false) {
            const pageCounter = valor?.pageCounter || '1 de 1';
            html += '<div class="os-hd-meta-row">';
            html += '<div class="k">Página</div>';
            html += '<div class="v">' + pageCounter + '</div>';
            html += '</div>';
        } else {
            html += '<div class="os-hd-meta-row"><div class="k">—</div><div class="v">—</div></div>';
        }
        
        html += '</div>'; // .os-hd-meta
        html += '</div>'; // .os-hd-right
        html += '</div>'; // .os-hd-top

        // ROW BOTTOM (STRIP)
        html += '<div class="os-hd-row os-hd-bottom">';
        html += '<div class="os-hd-cell os-hd-bottom-left">';
        html += 'Registro do Sistema de Gestão de Manutenção';
        html += '</div>';
        html += '<div class="os-hd-cell os-hd-bottom-center">';
        let osTypeText = 'Ordem de Serviço';
        if (config.showOsType !== false) {
            // Prioridade: valor editável no config > valor do contexto > template_nome > fallback
            let tipoOS = config.osType || valor?.osType || this.contexto?.template_nome || 'Ordem de Serviço';
            // Se o nome do template já começar com "Ordem de Serviço", usar apenas o resto
            const tipoOSTexto = tipoOS.startsWith('Ordem de Serviço') ? tipoOS.replace(/^Ordem de Serviço\s*-?\s*/i, '').trim() : tipoOS;
            if (tipoOSTexto && tipoOSTexto !== 'Ordem de Serviço') {
                osTypeText = tipoOS; // Usar nome completo do template
            } else if (config.osType) {
                // Se há valor editável no config, usar diretamente
                osTypeText = config.osType;
            }
        }
        html += osTypeText;
        html += '</div>';
        html += '</div>'; // .os-hd-bottom
        
        return html;
    }
    
    /**
     * Calcula tamanhos padrão de colunas Bootstrap baseado no número de colunas
     * @param {number} numColunas - Número de colunas (1-4)
     * @returns {Array<number>} Array de tamanhos Bootstrap (soma = 12)
     */
    calcularTamanhosPadrao(numColunas) {
        const total = 12;
        const tamanhoBase = Math.floor(total / numColunas);
        const resto = total % numColunas;
        
        const tamanhos = Array(numColunas).fill(tamanhoBase);
        // Distribuir resto nas primeiras colunas
        for (let i = 0; i < resto; i++) {
            tamanhos[i]++;
        }
        return tamanhos;
    }
    
    /**
     * Distribui campos em colunas conforme configuração de layout
     * @param {Array} campos - Array de objetos {nome, grupo, show, html, valor, label, bold}
     * @param {number} numColunas - Número de colunas
     * @param {Array<number>} columnSizes - Tamanhos Bootstrap das colunas
     * @returns {Array<Array>} Array de arrays, onde cada sub-array contém os campos da coluna
     */
    distribuirCamposColunas(campos, numColunas, columnSizes) {
        if (!campos || campos.length === 0) return [];
        
        // Filtrar apenas campos visíveis
        const camposVisiveis = campos.filter(c => c.show !== false);
        
        if (numColunas === 1) {
            // Todas as colunas em uma única coluna
            return [camposVisiveis];
        } else if (numColunas === 2) {
            // Dividir em dois grupos: OS e Solicitante
            const grupoOS = camposVisiveis.filter(c => c.grupo === 'os');
            const grupoSolicitante = camposVisiveis.filter(c => c.grupo === 'solicitante');
            return [grupoOS, grupoSolicitante];
        } else {
            // Distribuir uniformemente entre as colunas
            const distribuicao = Array(numColunas).fill(null).map(() => []);
            camposVisiveis.forEach((campo, index) => {
                const colunaIndex = index % numColunas;
                distribuicao[colunaIndex].push(campo);
            });
            return distribuicao;
        }
    }
    
    /**
     * Resolver valores do solicitante a partir do contexto
     * IMPORTANTE: Usar campos do payload unificado (Plano 1.2 - Etapa 7)
     * NÃO usar valores hardcoded - tudo deve vir do contexto.os
     */
    resolverValoresSolicitante(campo) {
        const contexto = this.contexto || {};
        const os = contexto.os || {};
        const user = contexto.user || {};
        const refs = contexto.refs || {};
        const unit = refs.unit || {};
        const asset = refs.asset || {};
        const setor = refs.setor || {};
        
        // Se há OS, usar dados da OS do payload unificado
        if (os.id) {
            // Resolver unidade do solicitante: prioridade para solicitante_unidade_nome > unit.name > header.unidade
            const headerUnidade = (contexto.header || {}).unidade || {};
            const unidadeSolicitante = os.solicitante_unidade_nome || unit.name || headerUnidade.nome || '—';
            
            // Usar campos do payload unificado: numero_os, data_solicitacao, ativo_nome, setor_nome, solicitante_nome, solicitante_email
            return {
                numeroOS: os.numero_os || os.number || '[000000]',
                dataCriacao: (os.data_solicitacao || os.criado_em || os.created_at) ? 
                    this.formatarDataHora(os.data_solicitacao || os.criado_em || os.created_at) : '—',
                ativo: os.ativo_nome || asset.name || '—',
                prioridade: os.prioridade || '—',
                prazoTermino: os.data_fim ? this.formatarDataHora(os.data_fim) : '—',
                setor: os.setor_nome || setor.name || '—',
                nome: os.solicitante_nome || user.name || '—',
                email: os.solicitante_email || user.email || '—',
                unidade: unidadeSolicitante,
                telefone: user.telefone || '—'
            };
        }
        
        // Fallback: usar dados do usuário atual
        const headerUnidadeFallback = (contexto.header || {}).unidade || {};
        const unidadeFallback = unit.name || headerUnidadeFallback.nome || '—';
        
        return {
            numeroOS: '[000000]',
            dataCriacao: '—',
            ativo: '—',
            prioridade: '—',
            prazoTermino: '—',
            setor: '—',
            nome: user.name || '—',
            email: user.email || '—',
            unidade: unidadeFallback,
            telefone: user.telefone || '—'
        };
    }
    
    formatarDataHora(dataISO) {
        if (!dataISO) return '—';
        try {
            const data = new Date(dataISO);
            const dia = String(data.getDate()).padStart(2, '0');
            const mes = String(data.getMonth() + 1).padStart(2, '0');
            const ano = data.getFullYear();
            const hora = String(data.getHours()).padStart(2, '0');
            const minuto = String(data.getMinutes()).padStart(2, '0');
            return `${dia}/${mes}/${ano} ${hora}:${minuto}`;
        } catch (e) {
            return '—';
        }
    }
    
    renderizarSolicitante(campo, valor) {
        const config = campo.config || {};
        const layout = campo.layout || { columns: 2, columnSizes: [6, 6], compact: false };
        const valores = this.resolverValoresSolicitante(campo);
        
        // Configuração de layout com fallback
        const numColunas = Math.max(1, Math.min(4, layout.columns || 2));
        const columnSizes = layout.columnSizes && layout.columnSizes.length === numColunas ? 
            layout.columnSizes : this.calcularTamanhosPadrao(numColunas);
        const compact = layout.compact || false;
        
        const showNome = config.showNome !== undefined ? config.showNome : true;
        const showEmail = config.showEmail !== undefined ? config.showEmail : true;
        const showUnidade = config.showUnidade !== undefined ? config.showUnidade : true;
        const showTelefone = config.showTelefone !== undefined ? config.showTelefone : false;
        const showSetor = config.showSetor !== undefined ? config.showSetor : false;
        const showDataCriacao = config.showDataCriacao !== undefined ? config.showDataCriacao : true;
        const showNumeroOS = config.showNumeroOS !== undefined ? config.showNumeroOS : true;
        const showAtivo = config.showAtivo !== undefined ? config.showAtivo : true;
        const showPrioridade = config.showPrioridade !== undefined ? config.showPrioridade : true;
        const showPrazoTermino = config.showPrazoTermino !== undefined ? config.showPrazoTermino : true;
        const showSetorOS = config.showSetorOS !== undefined ? config.showSetorOS : true;
        
        // Coletar campos em grupos
        const campos = [];
        
        // Grupo OS
        if (showNumeroOS) campos.push({ 
            nome: 'numeroOS', grupo: 'os', show: true, 
            label: 'Número da OS', valor: valores.numeroOS, bold: true 
        });
        if (showDataCriacao) campos.push({ 
            nome: 'dataCriacao', grupo: 'os', show: true, 
            label: 'Data de Criação', valor: valores.dataCriacao 
        });
        if (showAtivo) campos.push({ 
            nome: 'ativo', grupo: 'os', show: true, 
            label: 'Ativo', valor: valores.ativo 
        });
        if (showPrioridade) {
            const prioridadeBadge = {
                'critica': 'danger',
                'alta': 'warning',
                'media': 'info',
                'baixa': 'secondary'
            }[valores.prioridade] || 'secondary';
            campos.push({ 
                nome: 'prioridade', grupo: 'os', show: true, 
                label: 'Prioridade', 
                valor: `<span class="badge bg-${prioridadeBadge}">${valores.prioridade || '—'}</span>`, 
                html: true 
            });
        }
        if (showPrazoTermino) campos.push({ 
            nome: 'prazoTermino', grupo: 'os', show: true, 
            label: 'Prazo de Término', valor: valores.prazoTermino 
        });
        if (showSetorOS) campos.push({ 
            nome: 'setorOS', grupo: 'os', show: true, 
            label: 'Setor', valor: valores.setor 
        });
        
        // Grupo Solicitante
        if (showNome) campos.push({ 
            nome: 'nome', grupo: 'solicitante', show: true, 
            label: 'Nome', valor: valores.nome, bold: true 
        });
        if (showEmail) campos.push({ 
            nome: 'email', grupo: 'solicitante', show: true, 
            label: 'Email', valor: valores.email 
        });
        if (showUnidade) campos.push({ 
            nome: 'unidade', grupo: 'solicitante', show: true, 
            label: 'Unidade', valor: valores.unidade 
        });
        if (showSetor) campos.push({ 
            nome: 'setor', grupo: 'solicitante', show: true, 
            label: 'Setor', valor: valores.setor 
        });
        if (showTelefone) campos.push({ 
            nome: 'telefone', grupo: 'solicitante', show: true, 
            label: 'Telefone', valor: valores.telefone 
        });
        
        // Distribuir campos nas colunas
        const distribuicao = this.distribuirCamposColunas(campos, numColunas, columnSizes);
        
        const compactClass = compact ? 'compact' : '';
        let html = `<div class="solicitante-renderizado p-3 border rounded mb-3 ${compactClass}" style="background-color: #f8f9fa;">`;
        html += '<div class="row g-2">';
        
        // Renderizar cada coluna
        distribuicao.forEach((camposColuna, colunaIndex) => {
            const colSize = columnSizes[colunaIndex] || 12;
            html += `<div class="col-md-${colSize}">`;
            
            camposColuna.forEach(campoItem => {
                const boldClass = campoItem.bold ? 'fw-bold' : '';
                const valorHTML = campoItem.html ? campoItem.valor : this.escapeHtml(campoItem.valor || '—');
                html += `
                    <div class="mb-2">
                        <label class="small text-muted mb-1">${campoItem.label}</label>
                        <div class="${boldClass}">${valorHTML}</div>
                    </div>
                `;
            });
            
            html += '</div>';
        });
        
        html += '</div>';
        html += '</div>';
        return html;
    }
    
    renderizarDescricaoSolicitante(campo, valor, { editavel = true, visivel = true, obrigatorio = false } = {}) {
        const config = campo.config || {};
        const rows = config.rows || 4;
        const placeholder = config.placeholder || 'Descreva o problema encontrado...';
        const maxLength = config.maxLength || null;
        const obrigatorioCampo = obrigatorio || campo.obrigatorio || campo.validation?.required || false;
        
        // Resolver valor: prioridade para binding > dados_formulario_json > contexto OS
        let valorCampo = '';
        const data = campo.data || {};
        const mode = data.mode || 'input';
        
        // Se o campo tem binding e mode é 'computed', resolver via binding
        if (mode === 'computed' && data.binding) {
            const valorBinding = this.ruleEngine.resolverBinding(data.binding, this.contexto);
            if (valorBinding) {
                valorCampo = valorBinding;
            }
        }
        
        // Se não resolveu via binding, usar valor passado (pode ser de dados_formulario_json)
        // Não validar se é número - o usuário pode ter digitado apenas números na descrição
        if (!valorCampo && valor !== null && valor !== undefined) {
            valorCampo = String(valor);
        }
        
        // Fallback: usar descricao_problema do contexto da OS
        if (!valorCampo && this.contexto?.os?.descricao_problema) {
            valorCampo = this.contexto.os.descricao_problema;
        }
        
        const maxLengthAttr = maxLength ? `maxlength="${maxLength}"` : '';
        // Usar editavel do contexto (permissões do backend) OU modo readonly do campo
        const readonlyAttr = (!editavel || campo.data?.mode === 'readonly') ? 'readonly' : '';
        const disabledAttr = (!editavel || campo.data?.mode === 'readonly') ? 'disabled' : '';
        const classeValidacao = obrigatorioCampo ? 'is-invalid' : '';
        
        let html = `<div class="descricao-solicitante-renderizado">`;
        html += `<textarea class="form-control ${classeValidacao}" 
                  name="${campo.id}" 
                  id="${campo.id}"
                  rows="${rows}" 
                  placeholder="${placeholder}"
                  ${maxLengthAttr}
                  ${readonlyAttr}
                  ${disabledAttr}>${this.escapeHtml(valorCampo || '')}</textarea>`;
        html += `</div>`;
        return html;
    }
    
    /**
     * Escapar HTML para evitar XSS
     */
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    renderizarCabecalhoCompact(config, columns, valor) {
        let html = '';
        
        // Primeira linha: Logo, Programa, Códigos, OS
        html += '<div class="row g-2 align-items-center">';
        
        if (config.showLogo !== false) {
            if (valor?.logoUrl) {
                html += `<div class="col-auto"><img src="${valor.logoUrl}" alt="Logo" style="max-height: 40px;"></div>`;
            } else {
                html += '<div class="col-auto"><small class="text-muted">[Logo]</small></div>';
            }
        }
        
        if (config.showProgramName !== false) {
            // Prioridade: valor editável no config > valor do contexto > fallback
            const programName = config.programName || valor?.programName || '[Programa]';
            html += `<div class="col"><small><strong>${programName}</strong></small></div>`;
        }
        
        if (config.showDocumentCode !== false) {
            // Prioridade: valor editável no config > valor do contexto > fallback
            const docCode = config.codigoDocumento || valor?.documentCode || 'RSGM-XXX';
            html += `<div class="col-auto"><span class="badge bg-secondary">${docCode}</span></div>`;
        }
        
        if (config.showOsNumber !== false) {
            const osNumber = valor?.osNumber || '[000000]';
            html += `<div class="col-auto"><small><strong>OS:</strong> ${osNumber}</small></div>`;
        }
        
        html += '</div>';
        
        // Segunda linha: Unidade, Tipo, Data
        if (config.showUnit !== false || config.showOsType !== false || config.showIssueDate !== false) {
            html += '<div class="row g-2 mt-1">';
            
            if (config.showUnit !== false) {
                // Prioridade: valor editável no config > valor do contexto > fallback
                const unitName = config.unitName || valor?.unitName || '[Unidade]';
                html += `<div class="col"><small class="text-muted">${unitName}</small></div>`;
            }
            
            if (config.showOsType !== false) {
                // Prioridade: valor editável no config > valor do contexto > fallback
                const osType = config.osType || valor?.osType || '[Tipo OS]';
                html += `<div class="col"><small class="text-muted">${osType}</small></div>`;
            }
            
            if (config.showIssueDate !== false) {
                const issueDate = valor?.issueDate || '[Data]';
                html += `<div class="col"><small class="text-muted">${issueDate}</small></div>`;
            }
            
            html += '</div>';
        }
        
        // Terceira linha: Informações adicionais (se houver espaço)
        if (config.showAddress !== false && config.showAddress) {
            // Prioridade: valor editável no config > valor do contexto > fallback
            const address = config.address || valor?.unitAddress || '[Endereço]';
            html += `<div class="row mt-1"><div class="col-12"><small class="text-muted">${address}</small></div></div>`;
        }
        
        if (config.showRevision !== false) {
            const revision = valor?.revisionNumber || 'Rev. 00';
            const revisionDate = valor?.revisionDate || '00/00/0000';
            html += `<div class="row mt-1"><div class="col-12"><small class="text-muted">${revision} - ${revisionDate}</small></div></div>`;
        }
        
        return html;
    }
    
    renderizarTabela(campo, valor) {
        let html = `<div class="tabela-renderizado">`;
        html += `<table class="table table-sm table-bordered">`;
        const linhas = valor?.linhas || [];
        const colunas = campo.config?.colunas || (linhas.length > 0 ? Object.keys(linhas[0] || {}) : []);
        
        // Sempre renderizar cabeçalho se houver colunas definidas
        if (colunas.length > 0) {
            html += `<thead><tr>`;
            colunas.forEach(col => {
                html += `<th>${col}</th>`;
            });
            html += `</tr></thead>`;
        }
        
        html += `<tbody>`;
        if (linhas.length > 0) {
            linhas.forEach(linha => {
                html += `<tr>`;
                colunas.forEach(col => {
                    html += `<td>${linha[col] || '-'}</td>`;
                });
                html += `</tr>`;
            });
        }
        html += `</tbody>`;
        html += `</table>`;
        html += `<button type="button" class="btn btn-sm btn-primary" onclick="adicionarLinhaTabela('${campo.id}')">Adicionar Linha</button>`;
        html += `</div>`;
        return html;
    }
    
    aplicarRegrasPorStatus(status) {
        // Aplicar regras por status (visibilidade, editabilidade)
        const regrasPorStatus = this.schema.regras_por_status || {};
        const regrasStatus = regrasPorStatus[status] || {};
        const camposVisiveis = regrasStatus.campos_visiveis || [];
        const camposEditaveis = regrasStatus.campos_editaveis || [];
        const camposReadonly = regrasStatus.campos_readonly || [];
        
        // Aplicar visibilidade
        if (camposVisiveis.length > 0) {
            document.querySelectorAll('.form-builder-campo-renderizado').forEach(el => {
                const campoId = el.dataset.campoId;
                if (!camposVisiveis.includes(campoId)) {
                    el.style.display = 'none';
                } else {
                    el.style.display = 'block';
                }
            });
        }
        
        // Aplicar editabilidade
        document.querySelectorAll('.form-builder-campo-renderizado input, .form-builder-campo-renderizado select, .form-builder-campo-renderizado textarea').forEach(input => {
            const campoId = input.closest('.form-builder-campo-renderizado')?.dataset.campoId;
            if (campoId) {
                if (camposReadonly.includes(campoId)) {
                    input.disabled = true;
                    input.readOnly = true;
                } else if (camposEditaveis.length > 0 && !camposEditaveis.includes(campoId)) {
                    input.disabled = true;
                    input.readOnly = true;
                } else {
                    input.disabled = false;
                    input.readOnly = false;
                }
            }
        });
    }
    
    aplicarRegrasCondicionais() {
        // Aplicar regras condicionais de visibilidade baseadas em valores de outros campos
        const campos = this.schema.campos || [];
        campos.forEach(campo => {
            const regrasCondicionais = campo.regras_condicionais || [];
            if (regrasCondicionais.length > 0) {
                const campoEl = document.querySelector(`[data-campo-id="${campo.id}"]`);
                if (campoEl) {
                    let deveAparecer = true;
                    regrasCondicionais.forEach(regra => {
                        const campoRef = regra.campo;
                        const operador = regra.operador || 'equals';
                        const valorEsperado = regra.valor;
                        
                        if (campoRef) {
                            const inputRef = document.getElementById(campoRef);
                            if (inputRef) {
                                const valorRef = inputRef.value;
                                if (operador === 'equals' && valorRef !== valorEsperado) {
                                    deveAparecer = false;
                                } else if (operador === 'not_equals' && valorRef === valorEsperado) {
                                    deveAparecer = false;
                                } else if (operador === 'in' && !valorEsperado.includes(valorRef)) {
                                    deveAparecer = false;
                                }
                            }
                        }
                    });
                    campoEl.style.display = deveAparecer ? 'block' : 'none';
                }
            }
        });
    }
    
    aplicarPermissoesRBAC(perfilUsuario) {
        // Filtrar campos por permissões RBAC
        const campos = this.schema.campos || [];
        campos.forEach(campo => {
            const visivelPorPerfil = campo.visivel_por_perfil || [];
            const editavelPorPerfil = campo.editavel_por_perfil || [];
            const campoEl = document.querySelector(`[data-campo-id="${campo.id}"]`);
            
            if (campoEl && visivelPorPerfil.length > 0) {
                if (!visivelPorPerfil.includes(perfilUsuario)) {
                    campoEl.style.display = 'none';
                    return;
                }
            }
            
            if (campoEl && editavelPorPerfil.length > 0) {
                const inputs = campoEl.querySelectorAll('input, select, textarea');
                inputs.forEach(input => {
                    if (!editavelPorPerfil.includes(perfilUsuario)) {
                        input.disabled = true;
                        input.readOnly = true;
                    }
                });
            }
        });
    }
    
    validarCampos() {
        const erros = [];
        const campos = this.schema.campos || [];
        
        campos.forEach(campo => {
            if (campo.obrigatorio && !this.dados[campo.id]) {
                erros.push(`Campo ${campo.label || campo.id} é obrigatório`);
            }
        });
        
        return erros;
    }
    
    obterDados() {
        // Obter dados do formulário renderizado
        const dados = {};
        const campos = this.schema.campos || [];
        
        campos.forEach(campo => {
            const input = document.getElementById(campo.id);
            if (input) {
                if (input.type === 'checkbox' || input.type === 'radio') {
                    const checked = document.querySelector(`input[name="${campo.id}"]:checked`);
                    dados[campo.id] = checked ? checked.value : null;
                } else {
                    dados[campo.id] = input.value;
                }
            }
        });
        
        return dados;
    }
}

// Funções auxiliares globais para blocos CMMS
// ETAPA 5: Proteção defensiva nos handlers
async function adicionarApontamento(campoId) {
    // ETAPA 5: Proteção defensiva - verificar editavel antes de permitir ação
    const container = document.querySelector(`[data-campo-id*="${campoId}"], .apontamento-horas-renderizado[data-editavel]`);
    const editavel = container?.dataset.editavel === 'true' || container?.closest('.apontamento-horas-renderizado')?.dataset.editavel === 'true';
    if (!editavel) {
        console.warn('Tentativa de adicionar apontamento em modo read-only');
        return;
    }
    
    // Abrir modal para adicionar apontamento
    // Implementação será feita com modal customizado conforme MAPA_SISTEMA
    alert('Funcionalidade de adicionar apontamento será implementada com modal customizado');
}

async function removerApontamento(campoId, index) {
    // ETAPA 5: Proteção defensiva - verificar editavel antes de permitir ação
    const container = document.querySelector(`[data-campo-id*="${campoId}"], .apontamento-horas-renderizado[data-editavel]`);
    const editavel = container?.dataset.editavel === 'true' || container?.closest('.apontamento-horas-renderizado')?.dataset.editavel === 'true';
    if (!editavel) {
        console.warn('Tentativa de remover apontamento em modo read-only');
        return;
    }
    
    if (confirm('Deseja remover este apontamento?')) {
        const tbody = document.getElementById(`tbody_apontamentos_${campoId}`);
        const row = tbody.querySelector(`tr[data-apontamento-index="${index}"]`);
        if (row) {
            row.remove();
        }
    }
}

async function adicionarMaterial(campoId) {
    // ETAPA 5: Proteção defensiva - verificar editavel antes de permitir ação
    // Buscar container do bloco de materiais
    const container = document.querySelector(`.materiais-pecas-renderizado[data-campo-id*="${campoId}"], [data-campo-id="${campoId}"] .materiais-pecas-renderizado, .materiais-pecas-renderizado`);
    
    if (!container) {
        console.warn('[DEBUG] adicionarMaterial - Container de materiais não encontrado para campoId:', campoId);
        return;
    }
    
    // Verificar editavel do data-attribute
    const editavelAttr = container.dataset.editavel;
    const editavel = editavelAttr === 'true' || editavelAttr === true;
    
    // Verificação adicional: verificar permissões no contexto do renderer
    const renderer = window.formBuilderRenderer || window.renderer;
    if (renderer && renderer.contexto) {
        const blocoPermissao = renderer.contexto.permissoes?.blocos?.materiais;
        if (blocoPermissao && !blocoPermissao.write) {
            console.warn('[DEBUG] adicionarMaterial - Tentativa sem permissão de escrita no contexto');
            alert('Você não tem permissão para adicionar materiais nesta OS.');
            return;
        }
    }
    
    if (!editavel) {
        console.warn('[DEBUG] adicionarMaterial - Tentativa em modo read-only. campoId:', campoId, 'editavelAttr:', editavelAttr);
        alert('Este campo está em modo somente leitura.');
        return;
    }
    
    // Verificar se renderer e osId estão disponíveis
    if (!renderer || !renderer.osId) {
        alert('Erro: ID da OS não disponível. Não é possível adicionar material.');
        return;
    }
    
    // Verificar role do usuário (campo Fornecedor foi removido para todos)
    const isTecnico = renderer?.contexto?.role === "TECNICO";
    
    // Criar modal para adicionar material (CSS inline conforme padrão)
    const modalId = `modalMaterial_${campoId}`;
    
    // Verificar se modal já existe
    let modal = document.getElementById(modalId);
    if (!modal) {
        // Criar modal
        modal = document.createElement('div');
        modal.id = modalId;
        modal.style.cssText = 'display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5); z-index: 10000;';
        modal.innerHTML = `
            <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); background: white; border-radius: 8px; width: 95%; max-width: 600px; max-height: 95vh; overflow-y: auto; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3); display: flex; flex-direction: column;">
                <div style="background: linear-gradient(135deg, #3498db 0%, #2980b9 100%); color: white; padding: 20px 30px; border-radius: 8px 8px 0 0; display: flex; justify-content: space-between; align-items: center;">
                    <h3 style="margin: 0; font-size: 1.5rem; font-weight: 700;">Adicionar Material</h3>
                    <button onclick="fecharModalMaterial('${campoId}')" style="background: rgba(255, 255, 255, 0.25); border: none; color: white; font-size: 32px; line-height: 1; width: 44px; height: 44px; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center;">×</button>
                </div>
                <div style="padding: 30px; overflow-y: auto; flex: 1;">
                    <div class="mb-3">
                        <label class="form-label">Buscar Item do Catálogo</label>
                        <input type="text" class="form-control" id="busca_item_${campoId}" placeholder="Digite código ou nome do item..." onkeyup="buscarItensAutocomplete('${campoId}', this.value)">
                        <div id="lista_itens_${campoId}" style="max-height: 200px; overflow-y: auto; border: 1px solid #ddd; border-radius: 4px; margin-top: 5px; display: none;"></div>
                    </div>
                    <div class="mb-3">
                        <button type="button" class="btn btn-outline-secondary" id="btn_item_livre_${campoId}" onclick="toggleItemLivre('${campoId}')">
                            Item não cadastrado
                        </button>
                    </div>
                    <div id="campos_item_catalogo_${campoId}">
                        <input type="hidden" id="item_id_${campoId}">
                        <div class="mb-3" style="display: none;">
                            <label class="form-label">Código</label>
                            <input type="text" class="form-control" id="codigo_material_${campoId}" readonly>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Nome</label>
                            <input type="text" class="form-control" id="nome_material_${campoId}" readonly>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Unidade de Medida</label>
                            <input type="text" class="form-control" id="unidade_medida_${campoId}" readonly>
                        </div>
                    </div>
                    <div id="campos_item_livre_${campoId}" style="display: none;">
                        <div class="mb-3" id="campo_codigo_livre_${campoId}" style="display: none;">
                            <label class="form-label">Código *</label>
                            <input type="text" class="form-control" id="codigo_livre_${campoId}">
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Nome *</label>
                            <input type="text" class="form-control" id="nome_livre_${campoId}">
                        </div>
                        <div class="mb-3" id="campo_unidade_livre_${campoId}" style="display: none;">
                            <label class="form-label">Unidade de Medida *</label>
                            <input type="text" class="form-control" id="unidade_livre_${campoId}">
                        </div>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Quantidade *</label>
                        <input type="number" class="form-control" id="quantidade_${campoId}" step="0.01" min="0" value="1">
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Local Aplicado</label>
                        <textarea class="form-control" id="local_aplicado_${campoId}" rows="2"></textarea>
                    </div>
                </div>
                <div style="padding: 20px 30px; border-top: 1px solid #ddd; display: flex; justify-content: flex-end; gap: 10px;">
                    <button type="button" class="btn btn-secondary" onclick="fecharModalMaterial('${campoId}')">Cancelar</button>
                    <button type="button" class="btn btn-primary" onclick="salvarMaterial('${campoId}')">Adicionar</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }
    
    // Abrir modal
    modal.style.display = 'block';
    document.body.style.overflow = 'hidden';
    
    // Limpar campos
    document.getElementById(`busca_item_${campoId}`).value = '';
    document.getElementById(`item_id_${campoId}`).value = '';
    document.getElementById(`codigo_material_${campoId}`).value = '';
    document.getElementById(`nome_material_${campoId}`).value = '';
    document.getElementById(`unidade_medida_${campoId}`).value = '';
    
    // Resetar botão item livre
    const btnItemLivre = document.getElementById(`btn_item_livre_${campoId}`);
    if (btnItemLivre) {
        btnItemLivre.textContent = 'Item não cadastrado';
        btnItemLivre.classList.remove('btn-outline-primary');
        btnItemLivre.classList.add('btn-outline-secondary');
    }
    
    document.getElementById(`campos_item_livre_${campoId}`).style.display = 'none';
    document.getElementById(`campos_item_catalogo_${campoId}`).style.display = 'block';
    const buscaItem = document.getElementById(`busca_item_${campoId}`);
    if (buscaItem) {
        buscaItem.disabled = false;
        buscaItem.style.opacity = '1';
    }
    
    document.getElementById(`quantidade_${campoId}`).value = '1';
    
    // Preencher Local Aplicado com setor da OS
    const setorNome = renderer?.contexto?.os?.setor_nome;
    const localAplicadoField = document.getElementById(`local_aplicado_${campoId}`);
    if (localAplicadoField) {
        localAplicadoField.value = setorNome || '';
    }
}

function fecharModalMaterial(campoId) {
    const modal = document.getElementById(`modalMaterial_${campoId}`);
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = '';
    }
}

async function buscarItensAutocomplete(campoId, busca) {
    const listaItens = document.getElementById(`lista_itens_${campoId}`);
    if (!busca || busca.length < 2) {
        listaItens.style.display = 'none';
        return;
    }
    
    try {
        const renderer = window.formBuilderRenderer;
        if (!renderer || !renderer.buscarItensCatalogo) {
            console.error('Renderer não encontrado ou método buscarItensCatalogo não disponível');
            return;
        }
        
        const itens = await renderer.buscarItensCatalogo(busca);
        
        if (itens.length === 0) {
            listaItens.innerHTML = '<div style="padding: 10px; color: #666;">Nenhum item encontrado</div>';
            listaItens.style.display = 'block';
            return;
        }
        
        let html = '';
        itens.forEach(item => {
            // Tratar valores null/undefined e escapar caracteres especiais
            const itemId = item.id || '';
            const codigo = (item.codigo_interno || '').replace(/'/g, "\\'").replace(/"/g, '&quot;');
            const nome = (item.nome || '').replace(/'/g, "\\'").replace(/"/g, '&quot;');
            const unidade = (item.uom_simbolo || item.uom_codigo || 'un').replace(/'/g, "\\'").replace(/"/g, '&quot;');
            const codigoDisplay = item.codigo_interno || 'Sem código';
            const nomeDisplay = item.nome || 'Sem nome';
            const unidadeDisplay = item.uom_simbolo || item.uom_codigo || 'un';
            
            html += `
                <div style="padding: 10px; border-bottom: 1px solid #eee; cursor: pointer;" 
                     onmouseover="this.style.background='#f0f0f0'" 
                     onmouseout="this.style.background='white'"
                     onclick="selecionarItemCatalogo('${campoId}', ${itemId}, '${codigo}', '${nome}', '${unidade}')">
                    <strong>${codigoDisplay}</strong> - ${nomeDisplay}
                    <small class="text-muted d-block">${unidadeDisplay}</small>
                </div>
            `;
        });
        listaItens.innerHTML = html;
        listaItens.style.display = 'block';
    } catch (error) {
        console.error('Erro ao buscar itens:', error);
    }
}

function selecionarItemCatalogo(campoId, itemId, codigo, nome, unidade) {
    // Tratar valores null/undefined
    const itemIdValue = itemId || '';
    const codigoValue = codigo || '';
    const nomeValue = nome || '';
    const unidadeValue = unidade || 'un';
    
    // Preencher campos do formulário
    const itemIdField = document.getElementById(`item_id_${campoId}`);
    const codigoField = document.getElementById(`codigo_material_${campoId}`);
    const nomeField = document.getElementById(`nome_material_${campoId}`);
    const unidadeField = document.getElementById(`unidade_medida_${campoId}`);
    const buscaField = document.getElementById(`busca_item_${campoId}`);
    const listaItens = document.getElementById(`lista_itens_${campoId}`);
    const itemLivreCheckbox = document.getElementById(`item_livre_${campoId}`);
    const camposItemLivre = document.getElementById(`campos_item_livre_${campoId}`);
    const camposItemCatalogo = document.getElementById(`campos_item_catalogo_${campoId}`);
    
    if (itemIdField) itemIdField.value = itemIdValue;
    if (codigoField) codigoField.value = codigoValue;
    if (nomeField) nomeField.value = nomeValue;
    if (unidadeField) unidadeField.value = unidadeValue;
    if (buscaField) buscaField.value = codigoValue ? `${codigoValue} - ${nomeValue}` : nomeValue;
    if (listaItens) listaItens.style.display = 'none';
    if (itemLivreCheckbox) itemLivreCheckbox.checked = false;
    if (camposItemLivre) camposItemLivre.style.display = 'none';
    if (camposItemCatalogo) camposItemCatalogo.style.display = 'block';
}

function toggleItemLivre(campoId) {
    const btnItemLivre = document.getElementById(`btn_item_livre_${campoId}`);
    const camposItemCatalogo = document.getElementById(`campos_item_catalogo_${campoId}`);
    const camposItemLivre = document.getElementById(`campos_item_livre_${campoId}`);
    const buscaItem = document.getElementById(`busca_item_${campoId}`);
    
    // Campos a ocultar quando item livre estiver ativo
    const campoCodigoLivre = document.getElementById(`campo_codigo_livre_${campoId}`);
    const campoUnidadeLivre = document.getElementById(`campo_unidade_livre_${campoId}`);
    
    // Verificar estado atual (se campos_item_livre está visível)
    const isItemLivreAtivo = camposItemLivre && camposItemLivre.style.display !== 'none';
    
    if (!isItemLivreAtivo) {
        // Ativar item livre
        if (camposItemCatalogo) camposItemCatalogo.style.display = 'none';
        if (camposItemLivre) camposItemLivre.style.display = 'block';
        if (buscaItem) {
            buscaItem.disabled = true;
            buscaItem.style.opacity = '0.5';
        }
        if (btnItemLivre) {
            btnItemLivre.textContent = 'Usar Item do Catálogo';
            btnItemLivre.classList.remove('btn-outline-secondary');
            btnItemLivre.classList.add('btn-outline-primary');
        }
        
        // Ocultar campos: Código e Unidade de Medida
        if (campoCodigoLivre) campoCodigoLivre.style.display = 'none';
        if (campoUnidadeLivre) campoUnidadeLivre.style.display = 'none';
        
        // Limpar campos do catálogo
        const itemIdField = document.getElementById(`item_id_${campoId}`);
        if (itemIdField) itemIdField.value = '';
        if (buscaItem) buscaItem.value = '';
    } else {
        // Desativar item livre (voltar para catálogo)
        if (camposItemCatalogo) camposItemCatalogo.style.display = 'block';
        if (camposItemLivre) camposItemLivre.style.display = 'none';
        if (buscaItem) {
            buscaItem.disabled = false;
            buscaItem.style.opacity = '1';
        }
        if (btnItemLivre) {
            btnItemLivre.textContent = 'Item não cadastrado';
            btnItemLivre.classList.remove('btn-outline-primary');
            btnItemLivre.classList.add('btn-outline-secondary');
        }
        
        // Mostrar campos: Código e Unidade de Medida novamente (se necessário)
        // Nota: Código do catálogo sempre oculto, apenas código livre seria mostrado se necessário
        if (campoCodigoLivre) campoCodigoLivre.style.display = 'none'; // Sempre oculto
        if (campoUnidadeLivre) campoUnidadeLivre.style.display = 'none'; // Sempre oculto quando item livre inativo
        
        // Limpar campos de item livre
        const codigoLivre = document.getElementById(`codigo_livre_${campoId}`);
        const nomeLivre = document.getElementById(`nome_livre_${campoId}`);
        const unidadeLivre = document.getElementById(`unidade_livre_${campoId}`);
        if (codigoLivre) codigoLivre.value = '';
        if (nomeLivre) nomeLivre.value = '';
        if (unidadeLivre) unidadeLivre.value = '';
    }
}

async function salvarMaterial(campoId) {
    // Obter renderer (pode estar em window.formBuilderRenderer ou variável local)
    const renderer = window.formBuilderRenderer || window.renderer;
    if (!renderer) {
        alert('Erro: Renderer não encontrado');
        return;
    }
    
    // Verificar se os_id está disponível
    if (!renderer.osId) {
        alert('Erro: ID da OS não disponível. Não é possível salvar material.');
        return;
    }
    
    // Verificar role antes de incluir fornecedor
    const isTecnico = renderer?.contexto?.role === "TECNICO";
    
    // Verificar se item livre está ativo (verificar se campos_item_livre está visível)
    const camposItemLivre = document.getElementById(`campos_item_livre_${campoId}`);
    const itemLivre = camposItemLivre && camposItemLivre.style.display !== 'none';
    
    const quantidade = parseFloat(document.getElementById(`quantidade_${campoId}`).value) || 1;
    // Valor unitário sempre 0 já que campo foi removido
    const valorUnitario = 0;
    
    let materialData;
    if (itemLivre) {
        // Campos Código e Unidade de Medida estão ocultos quando item livre está ativo
        // Apenas Nome é obrigatório
        const nome = document.getElementById(`nome_livre_${campoId}`).value.trim();
        
        if (!nome) {
            alert('Preencha o campo Nome (obrigatório)');
            return;
        }
        
        // Código e Unidade de Medida podem estar vazios (campos ocultos)
        const codigo = document.getElementById(`codigo_livre_${campoId}`)?.value.trim() || null;
        const unidade = document.getElementById(`unidade_livre_${campoId}`)?.value.trim() || null;
        
        // Campo Fornecedor foi removido para todos
        const fornecedor = null;
        
        materialData = {
            os_id: renderer.osId,
            item_id: null,
            codigo_material: codigo,
            nome_material: nome,
            unidade_medida: unidade,
            quantidade: quantidade,
            valor_unitario: valorUnitario,
            fornecedor: fornecedor,
            local_aplicado: document.getElementById(`local_aplicado_${campoId}`).value.trim() || null,
            tecnico_id: renderer.contexto?.user?.id || null
        };
    } else {
        const itemId = document.getElementById(`item_id_${campoId}`).value;
        if (!itemId) {
            alert('Selecione um item do catálogo ou use "item livre"');
            return;
        }
        
        // Campo Fornecedor foi removido para todos
        const fornecedor = null;
        
        materialData = {
            os_id: renderer.osId,
            item_id: parseInt(itemId),
            quantidade: quantidade,
            valor_unitario: valorUnitario,
            fornecedor: fornecedor,
            local_aplicado: document.getElementById(`local_aplicado_${campoId}`).value.trim() || null,
            tecnico_id: renderer.contexto?.user?.id || null
        };
    }
    
    try {
        // Salvar material via API
        const response = await fetch('/api/v1/manutencao/materiais/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify(materialData)
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Erro desconhecido' }));
            let errorMessage = 'Erro ao salvar material';
            if (errorData.detail) {
                if (typeof errorData.detail === 'string') {
                    errorMessage = errorData.detail;
                } else if (Array.isArray(errorData.detail)) {
                    errorMessage = errorData.detail.map(e => e.msg || e).join(', ');
                } else if (typeof errorData.detail === 'object') {
                    errorMessage = JSON.stringify(errorData.detail);
                }
            } else {
                errorMessage = response.statusText || 'Erro desconhecido';
            }
            alert(`Erro ao salvar material: ${errorMessage}`);
            return;
        }
        
        // Material salvo com sucesso, recarregar lista
        fecharModalMaterial(campoId);
        
        // Recarregar materiais da OS
        await renderer.carregarMateriaisOS(campoId);
        
        // Recarregar formulário completo para atualizar descricao_tecnico
        if (typeof window.carregarOS === 'function') {
            await window.carregarOS();
        } else if (typeof carregarOS === 'function') {
            await carregarOS();
        }
        
        // Mostrar mensagem de sucesso
        const toast = document.createElement('div');
        toast.className = 'alert alert-success alert-dismissible fade show position-fixed top-0 end-0 m-3';
        toast.style.zIndex = '9999';
        toast.innerHTML = `
            <strong>Sucesso!</strong> Material adicionado com sucesso.
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
        
    } catch (error) {
        console.error('Erro ao salvar material:', error);
        alert('Erro ao salvar material: ' + error.message);
    }
}

async function removerMaterial(campoId, materialId) {
    // ETAPA 5: Proteção defensiva - verificar editavel antes de permitir ação
    const container = document.querySelector(`[data-campo-id*="${campoId}"], .materiais-pecas-renderizado[data-editavel]`);
    const editavel = container?.dataset.editavel === 'true' || container?.closest('.materiais-pecas-renderizado')?.dataset.editavel === 'true';
    if (!editavel) {
        console.warn('Tentativa de remover material em modo read-only');
        return;
    }
    
    if (!confirm('Deseja remover este material?')) {
        return;
    }
    
    // Obter renderer (pode estar em window.formBuilderRenderer ou variável local)
    const renderer = window.formBuilderRenderer || window.renderer;
    if (!renderer) {
        alert('Erro: Renderer não encontrado');
        return;
    }
    
    try {
        // Deletar material via API
        const response = await fetch(`/api/v1/manutencao/materiais/${materialId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Erro desconhecido' }));
            alert(`Erro ao remover material: ${errorData.detail || response.statusText}`);
            return;
        }
        
        // Material removido com sucesso, recarregar lista
        await renderer.carregarMateriaisOS(campoId);
        
        // Mostrar mensagem de sucesso
        const toast = document.createElement('div');
        toast.className = 'alert alert-success alert-dismissible fade show position-fixed top-0 end-0 m-3';
        toast.style.zIndex = '9999';
        toast.innerHTML = `
            <strong>Sucesso!</strong> Material removido com sucesso.
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
        
    } catch (error) {
        console.error('Erro ao remover material:', error);
        alert('Erro ao remover material: ' + error.message);
    }
}

function validarStatusFinal(campoId, valor) {
    // Validar se medida paliativa exige justificativa
    const campo = document.getElementById(campoId);
    const config = campo.dataset.config ? JSON.parse(campo.dataset.config) : {};
    
    if (valor === 'paliativo' && config.exige_justificativa_se === 'paliativo') {
        const justificativaId = config.campo_justificativa_id || `${campoId}_justificativa`;
        const justificativa = document.getElementById(justificativaId);
        if (justificativa) {
            justificativa.style.display = 'block';
            justificativa.required = true;
        }
    } else {
        const justificativaId = config.campo_justificativa_id || `${campoId}_justificativa`;
        const justificativa = document.getElementById(justificativaId);
        if (justificativa) {
            justificativa.style.display = 'none';
            justificativa.required = false;
        }
    }
}

function validarQSA(campoId, valor) {
    // Validar se NC exige observação
    if (valor === 'NC') {
        const obsId = `${campoId}_obs`;
        const obs = document.getElementById(obsId);
        if (obs) {
            obs.style.display = 'block';
            obs.required = true;
        }
    } else {
        const obsId = `${campoId}_obs`;
        const obs = document.getElementById(obsId);
        if (obs) {
            obs.style.display = 'none';
            obs.required = false;
        }
    }
}

function adicionarLinhaTabela(campoId) {
    // Adicionar linha à tabela repetível
    const renderer = window.formBuilderRenderer;
    if (!renderer) {
        console.error('Renderer não encontrado. Certifique-se de que o formulário foi renderizado.');
        alert('Erro: Renderer não encontrado');
        return;
    }
    
    // Buscar campo no schema
    const campo = renderer.schema.campos?.find(c => c.id === campoId);
    if (!campo) {
        console.error('Campo não encontrado:', campoId);
        alert('Erro: Campo não encontrado');
        return;
    }
    
    // Obter colunas da configuração
    const colunas = campo.config?.colunas || [];
    if (colunas.length === 0) {
        console.warn('Campo de tabela não possui colunas configuradas');
        alert('Erro: Tabela não possui colunas configuradas');
        return;
    }
    
    // Inicializar estrutura de dados se não existir
    if (!renderer.dados[campoId]) {
        renderer.dados[campoId] = { linhas: [] };
    }
    
    // Garantir que linhas seja um array
    if (!Array.isArray(renderer.dados[campoId].linhas)) {
        renderer.dados[campoId].linhas = [];
    }
    
    // Criar nova linha vazia com todas as colunas
    const novaLinha = {};
    colunas.forEach(col => {
        novaLinha[col] = '';
    });
    
    // Adicionar linha ao array
    renderer.dados[campoId].linhas.push(novaLinha);
    
    // Re-renderizar o formulário
    renderer.renderizar();
}

async function carregarEquipamento(campoId, equipamentoId) {
    // Carregar detalhes do equipamento selecionado
    if (equipamentoId) {
        try {
            const response = await fetch(`/api/v1/manutencao/ativos/${equipamentoId}`, {
                credentials: 'include'
            });
            if (response.ok) {
                const equipamento = await response.json();
                // Armazenar dados do equipamento para uso no formulário
                window.equipamentoSelecionado = equipamento;
            }
        } catch (error) {
            console.error('Erro ao carregar equipamento:', error);
        }
    }
}

async function carregarAtivoSelecionado(campoId, ativoId) {
    // Carregar detalhes do ativo selecionado
    if (ativoId) {
        try {
            const response = await fetch(`/api/v1/manutencao/ativos/${ativoId}`, {
                credentials: 'include'
            });
            if (response.ok) {
                const ativo = await response.json();
                // Armazenar dados do ativo para uso no formulário
                window.ativoSelecionado = ativo;
            }
        } catch (error) {
            console.error('Erro ao carregar ativo:', error);
        }
    }
}

/**
 * Renderizar campos usando FormBuilderRenderer com schema completo
 * 
 * ETAPA 04: Removida filtragem estrutural - schema completo é passado ao renderer
 * Referência: PLANO_PCM/plano_1.md - Etapa 4 (Ajustar Renderer Único)
 * 
 * Visibilidade/editabilidade controlada via contexto.permissoes.blocos
 * 
 * @param {Object} schema - Schema completo do template (sem filtragem)
 * @param {HTMLElement|string} container - Container onde renderizar os campos (elemento ou ID)
 * @param {Object} dadosIniciais - Dados iniciais para preencher os campos (opcional)
 */
function renderizarCamposSolicitante(schema, container, dadosIniciais = {}) {
    if (!schema || !container) {
        console.error('Schema ou container não fornecido');
        return;
    }
    
    // Obter elemento do container (pode ser elemento ou ID string)
    let containerElement = container;
    let containerId = null;
    
    if (typeof container === 'string') {
        containerId = container;
        containerElement = document.getElementById(container);
    } else if (container.id) {
        containerId = container.id;
        containerElement = container;
    } else {
        console.error('Container deve ser um elemento com ID ou uma string com ID');
        return;
    }
    
    if (!containerElement) {
        console.error(`Container não encontrado: ${containerId}`);
        return;
    }
    
    // ETAPA 04: Usar schema completo (sem filtragem estrutural)
    // Renderer aplicará gates de visibilidade/editabilidade por bloco
    
    // Contexto para renderização (OS sendo criada, status 'aberta')
    const contexto = {
        status: 'aberta',
        role: 'SOLICITANTE', // Role será normalizada pelo backend
        user: {
            role: window.CURRENT_USER_PAPEL_ORGANIZACIONAL || 'solicitante'
        },
        // permissoes.blocos será fornecido pelo backend via endpoint /formulario
        permissoes: {
            blocos: {} // Fallback: renderer aplicará comportamento legado se não existir
        }
    };
    
    // Limpar container
    containerElement.innerHTML = '';
    
    // Criar e renderizar formulário usando FormBuilderRenderer com schema completo
    const renderer = new FormBuilderRenderer(
        containerId,
        schema, // Schema completo (sem filtragem)
        dadosIniciais,
        null, // sem callback de mudança
        contexto
    );
    
    renderer.renderizar();
    
    // Armazenar renderer globalmente para acesso posterior
    window.formBuilderRenderer = renderer;
    
    console.log('Schema completo renderizado - visibilidade/editabilidade controlada por permissoes.blocos');
}
