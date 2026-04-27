/* 
  REFERÊNCIA DO CERTILOG - Form Builder Editor JavaScript
  Este arquivo é uma cópia de referência do sistema Certilog.
  Não deve ser usado diretamente no PDV Ibix.
  Adaptar conforme necessário para implementação futura.
*/

// Form Builder Editor - Editor Drag-and-Drop de Templates
// Gerencia construção visual de templates de formulários

// ============================================================================
// CONFIGURAÇÃO DE DEBUG
// ============================================================================
// Para desabilitar logs em produção, altere para false
const FORMBUILDER_DEBUG = true;

// Função auxiliar para logs condicionais
function formBuilderLog(...args) {
    if (FORMBUILDER_DEBUG) {
        console.log(...args);
    }
}

function formBuilderWarn(...args) {
    if (FORMBUILDER_DEBUG) {
        console.warn(...args);
    }
}

function formBuilderError(...args) {
    // Erros sempre são logados, mesmo em produção
    console.error(...args);
}

// ============================================================================

class FormBuilderEditor {
    constructor(containerId, templateId = null) {
        this.container = document.getElementById(containerId);
        this.templateId = templateId;
        this.templateNome = null; // Nome do template para uso no cabeçalho
        this.templateCriadoEm = null; // Data de criação do template (Data de Emissão)
        this.templateAtualizadoEm = null; // Data de atualização do template (Data de Revisão)
        this.templateVersao = null; // Versão atual do template (N° Revisão)
        this.schema = {
            layout: "column",
            secoes: [],
            campos: []
        };
        this.campoSelecionado = null;
        // Dados da unidade para preencher campos padrão
        this.unidadeNome = null;
        this.unidadeEndereco = null;
        this.unidadeCidade = null;
        this.unidadeEstado = null;
        
        if (templateId) {
            this.carregarTemplate(templateId);
        } else {
            // Se não há template, carregar dados da unidade para novos templates
            this.carregarDadosUnidade();
        }
    }
    
    async carregarDadosUnidade(unidadeId = null) {
        try {
            let unidade_id_para_buscar = unidadeId;
            
            // Se unidade_id não foi fornecido (null/undefined), buscar do usuário (fallback)
            if (unidade_id_para_buscar === null || unidade_id_para_buscar === undefined) {
                // Buscar dados do usuário atual para obter unidade_id
                const userResponse = await fetch('/api/v1/auth/me', {
                    credentials: 'include'
                });
                
                if (!userResponse.ok) {
                    formBuilderWarn('[FormBuilder] Erro ao buscar dados do usuário. Status:', userResponse.status);
                    this.unidadeNomeCompleto = null;
                    this.unidadeNome = null;
                    this.unidadeEndereco = null;
                    return;
                }
                
                const user = await userResponse.json();
                formBuilderLog('[FormBuilder] Dados do usuário carregados:', { 
                    unidade_id: user.unidade_id, 
                    user_id: user.id,
                    user_keys: Object.keys(user)
                });
                
                // Verificar se unidade_id existe (pode estar null ou undefined)
                if (!user.unidade_id && user.unidade_id !== 0) {
                    formBuilderWarn('[FormBuilder] Usuário não tem unidade_id configurado. user:', user);
                    this.unidadeNomeCompleto = null;
                    this.unidadeNome = null;
                    this.unidadeEndereco = null;
                    return;
                }
                
                unidade_id_para_buscar = user.unidade_id;
            } else {
                formBuilderLog('[FormBuilder] Usando unidade_id do template:', unidade_id_para_buscar);
            }
            
            // Buscar dados da unidade
            const unidadeResponse = await fetch(`/api/v1/configuracoes/unidades/${unidade_id_para_buscar}`, {
                credentials: 'include'
            });
            
            if (!unidadeResponse.ok) {
                formBuilderWarn('[FormBuilder] Erro ao buscar dados da unidade. Status:', unidadeResponse.status, 'unidade_id:', unidade_id_para_buscar);
                this.unidadeNomeCompleto = null;
                this.unidadeNome = null;
                this.unidadeEndereco = null;
                return;
            }
            
            const unidade = await unidadeResponse.json();
            this.unidadeNome = unidade.nome || null;
            this.unidadeEndereco = unidade.endereco || null;
            this.unidadeCidade = unidade.cidade || null;
            this.unidadeEstado = unidade.estado || null;
            
            // Construir nome completo da unidade se tiver cidade e estado
            if (this.unidadeNome && this.unidadeCidade && this.unidadeEstado) {
                this.unidadeNomeCompleto = `${this.unidadeNome} - ${this.unidadeCidade} - ${this.unidadeEstado}`;
            } else if (this.unidadeNome) {
                this.unidadeNomeCompleto = this.unidadeNome;
            } else {
                // Sem fallback - deixar null se não tiver nome
                this.unidadeNomeCompleto = null;
            }
            
            formBuilderLog('[FormBuilder] Dados da unidade carregados:', {
                nome: this.unidadeNome,
                endereco: this.unidadeEndereco,
                cidade: this.unidadeCidade,
                estado: this.unidadeEstado,
                nomeCompleto: this.unidadeNomeCompleto
            });
            
            // Se já tem schema renderizado, re-renderizar para atualizar com dados da unidade
            if (this.schema && (this.schema.secoes || this.schema.campos)) {
                this.renderizar();
            }
        } catch (error) {
            formBuilderWarn('[FormBuilder] Erro ao carregar dados da unidade:', error);
            // Deixar vazio se não conseguir carregar (sem fallback)
            this.unidadeNomeCompleto = null;
            this.unidadeNome = null;
            this.unidadeEndereco = null;
        }
    }
    
    async carregarTemplate(templateId) {
        try {
            console.log('Carregando template:', templateId);
            const response = await fetch(`/api/v1/manutencao/templates/${templateId}`, {
                credentials: 'include'  // Incluir cookies de sessão
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const template = await response.json();
            console.log('Template carregado:', template);
            
            // Armazenar dados do template para uso no cabeçalho
            if (template.nome) {
                this.templateNome = template.nome;
            }
            if (template.criado_em) {
                this.templateCriadoEm = new Date(template.criado_em);
            }
            if (template.atualizado_em) {
                this.templateAtualizadoEm = new Date(template.atualizado_em);
            }
            // Versão vem da versao_atual
            if (template.versao_atual && template.versao_atual.versao) {
                this.templateVersao = template.versao_atual.versao;
            } else if (template.versao_atual && template.versao_atual.criado_em) {
                // Se não tiver versão mas tiver data de criação da versão, usar como data de revisão
                this.templateAtualizadoEm = new Date(template.versao_atual.criado_em);
            }
            
            // Carregar dados da unidade ANTES de renderizar para ter dados disponíveis
            // Prioridade: unidade_id do template > unidade_id do usuário (fallback)
            const template_unidade_id = template.unidade_id !== undefined && template.unidade_id !== null ? template.unidade_id : null;
            await this.carregarDadosUnidade(template_unidade_id);
            
            // A API retorna schema_json (alias), mas internamente é formulario_schema
            // O Pydantic serializa com o alias, então usamos schema_json
            if (template.versao_atual) {
                const schema = template.versao_atual.schema_json || template.versao_atual.formulario_schema;
                if (schema) {
                    this.schema = schema;
                    console.log('Schema carregado:', this.schema);
                    this.renderizar();
                } else {
                    console.warn('Template não possui schema');
                    // Inicializar schema vazio para novo template
                    this.schema = {
                        layout: "column",
                        secoes: [],
                        campos: []
                    };
                    this.renderizar();
                }
            } else {
                console.log('Template sem versão publicada, inicializando schema vazio');
                // Template sem versão - inicializar schema vazio
                this.schema = {
                    layout: "column",
                    secoes: [],
                    campos: []
                };
                this.renderizar();
            }
        } catch (error) {
            console.error('Erro ao carregar template:', error);
            // Tentar carregar dados da unidade mesmo em caso de erro
            await this.carregarDadosUnidade();
            // Inicializar schema vazio em caso de erro
            this.schema = {
                layout: "column",
                secoes: [],
                campos: []
            };
            this.renderizar();
        }
    }
    
    renderizar() {
        formBuilderLog('[FormBuilder] ========== renderizar() INICIADO ==========');
        // Renderizar estrutura do formulário com drag and drop
        if (!this.container) {
            formBuilderError('[FormBuilder] ❌ Container não encontrado para renderização');
            return;
        }
        
        formBuilderLog('[FormBuilder] Renderizando formulário com schema:', this.schema);
        formBuilderLog('[FormBuilder] Seções no schema:', this.schema.secoes?.length || 0);
        formBuilderLog('[FormBuilder] Campos no schema:', this.schema.campos?.length || 0);
        
        let html = '<div class="form-builder-secoes">';
        
        // Renderizar seções existentes
        const secoes = this.schema.secoes || [];
        const campos = this.schema.campos || [];
        const camposMap = {};
        
        // Criar mapa de campos
        campos.forEach(campo => {
            camposMap[campo.id] = campo;
        });
        
        // Se não há seções, criar uma padrão
        if (secoes.length === 0) {
            html += this.renderizarSecao({
                id: 'secao_1',
                titulo: '',
                ordem: 1,
                campos: []
            }, camposMap);
        } else {
            // Ordenar seções por ordem
            const secoesOrdenadas = [...secoes].sort((a, b) => (a.ordem || 0) - (b.ordem || 0));
            secoesOrdenadas.forEach(secao => {
                html += this.renderizarSecao(secao, camposMap);
            });
        }
        
        // Botão para adicionar nova seção
        html += `
            <div class="form-builder-add-secao">
                <button type="button" class="btn btn-sm btn-outline-primary" onclick="adicionarNovaSecao()">
                    <i data-feather="plus"></i> Adicionar Seção
                </button>
            </div>
        `;
        
        html += '</div>';
        this.container.innerHTML = html;
        formBuilderLog('[FormBuilder] HTML renderizado, tamanho:', html.length, 'caracteres');
        
        // Inicializar drag and drop
        formBuilderLog('[FormBuilder] Inicializando drag and drop após renderização...');
        this.inicializarDragAndDrop();
        
        // Atualizar ícones Feather
        if (typeof feather !== 'undefined') {
            feather.replace();
            formBuilderLog('[FormBuilder] Ícones Feather atualizados');
        }
        
        formBuilderLog('[FormBuilder] ========== renderizar() CONCLUÍDO ==========');
    }
    
    renderizarSecao(secao, camposMap) {
        const campoIds = secao.campos || [];
        let html = `
            <div class="form-builder-secao" data-secao-id="${secao.id}">
                <div class="form-builder-secao-header">
                    <h5>
                        <span class="secao-titulo" contenteditable="true" onblur="atualizarTituloSecao('${secao.id}', this.textContent)">
                            ${secao.titulo || ''}
                        </span>
                    </h5>
                    <div style="display: flex; gap: 4px;">
                        <button type="button" class="btn btn-sm btn-secondary" onclick="event.stopPropagation(); moverSecao('${secao.id}', 'cima')" title="Mover seção para cima">
                            <i data-feather="arrow-up"></i>
                        </button>
                        <button type="button" class="btn btn-sm btn-secondary" onclick="event.stopPropagation(); moverSecao('${secao.id}', 'baixo')" title="Mover seção para baixo">
                            <i data-feather="arrow-down"></i>
                        </button>
                        <button type="button" class="btn btn-sm btn-danger" onclick="removerSecao('${secao.id}')" title="Remover seção">
                            <i data-feather="trash-2"></i>
                        </button>
                    </div>
                </div>
                <div class="form-builder-secao-body" 
                     data-secao-id="${secao.id}">
        `;
        
        // Renderizar campos da seção
        campoIds.forEach(campoId => {
            if (camposMap[campoId]) {
                html += this.renderizarCampo(camposMap[campoId], secao.id);
            }
        });
        
        // Área de drop vazia
        html += `
                    <div class="form-builder-drop-zone" data-secao-id="${secao.id}">
                        <p class="text-muted small">Solte campos aqui</p>
                    </div>
                </div>
            </div>
        `;
        
        return html;
    }
    
    renderizarCampo(campo, secaoId) {
        const tiposIcones = {
            'text': 'type',
            'number': 'hash',
            'date': 'calendar',
            'hora': 'clock',
            'datetime': 'calendar',
            'select': 'list',
            'checkbox': 'check-square',
            'boolean': 'toggle-left',
            'checklist': 'check-square',
            'tabela': 'grid',
            'upload': 'upload',
            'apontamento_horas': 'clock',
            'materiais_pecas': 'package',
            'equipamentos': 'tool',
            'ativos': 'layers',
            'status_final': 'flag',
            'seguranca_operacional': 'shield',
            'qsa': 'check-circle',
            'solicitante': 'user',
            'descricao_solicitante': 'file-text',
            'descricao_tecnico': 'edit-3',
            'texto_informativo': 'info',
            'cabecalho_os': 'file-text'
        };
        
        const icone = tiposIcones[campo.tipo] || 'edit';
        
        // Renderização especial para cabeçalho da OS
        if (campo.tipo === 'cabecalho_os') {
            return this.renderizarPreviewCabecalhoOS(campo, secaoId);
        }
        
        // Renderização especial para solicitante
        if (campo.tipo === 'solicitante') {
            return this.renderizarPreviewSolicitante(campo, secaoId);
        }
        
        // Renderização especial para descrição do solicitante
        if (campo.tipo === 'descricao_solicitante') {
            return this.renderizarPreviewDescricaoSolicitante(campo, secaoId);
        }
        
        return `
            <div class="form-builder-campo" 
                 draggable="true"
                 data-campo-id="${campo.id}"
                 data-secao-id="${secaoId}"
                 ondragstart="handleDragStart(event, '${campo.id}')"
                 onclick="selecionarCampo('${campo.id}')">
                <div class="form-builder-campo-header">
                    <i data-feather="${icone}"></i>
                    <span class="campo-label" contenteditable="true" 
                          onblur="salvarLabelInline('${campo.id}', this.textContent)"
                          onkeydown="if(event.key==='Enter'){this.blur();event.preventDefault();}">
                        ${campo.label || campo.id}
                    </span>
                    ${campo.obrigatorio ? '<span class="badge bg-danger">Obrigatório</span>' : ''}
                    <div style="display: flex; gap: 4px;">
                        <button type="button" class="btn btn-sm btn-secondary" onclick="event.stopPropagation(); moverCampo('${campo.id}', 'cima')" title="Mover campo para cima">
                            <i data-feather="arrow-up"></i>
                        </button>
                        <button type="button" class="btn btn-sm btn-secondary" onclick="event.stopPropagation(); moverCampo('${campo.id}', 'baixo')" title="Mover campo para baixo">
                            <i data-feather="arrow-down"></i>
                        </button>
                        <button type="button" class="btn btn-sm btn-secondary" onclick="event.stopPropagation(); duplicarCampo('${campo.id}')" title="Duplicar bloco">
                            <i data-feather="copy"></i>
                        </button>
                        <button type="button" class="btn btn-sm btn-danger" onclick="event.stopPropagation(); removerCampo('${campo.id}')" title="Remover campo">
                            <i data-feather="x"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
    }
    
    renderizarPreviewCabecalhoOS(campo, secaoId) {
        const config = campo.config || {};
        const layout = campo.layout || {};
        
        const variant = layout.variant || 'print_like';
        const columns = layout.columns || 3;
        const showBorders = layout.showBorders !== undefined ? layout.showBorders : true;
        
        const borderClass = showBorders ? 'border' : '';
        const variantClass = variant === 'compact' ? 'cabecalho-os-compact' : 'cabecalho-os-print-like';
        const columnsClass = `cabecalho-os-cols-${columns}`;
        
        let previewHTML = `
            <div class="form-builder-campo form-builder-campo-cabecalho" 
                 draggable="true"
                 data-campo-id="${campo.id}"
                 data-secao-id="${secaoId}"
                 ondragstart="handleDragStart(event, '${campo.id}')"
                 onclick="selecionarCampo('${campo.id}')">
                <div class="form-builder-campo-header">
                    <i data-feather="file-text"></i>
                    <span class="campo-label" contenteditable="true" 
                          onblur="salvarLabelInline('${campo.id}', this.textContent)"
                          onkeydown="if(event.key==='Enter'){this.blur();event.preventDefault();}">
                        ${campo.label || 'Cabeçalho da Ordem de Serviço'}
                    </span>
                    <span class="badge bg-info ms-2">Read-only</span>
                    <div style="display: flex; gap: 4px;">
                        <button type="button" class="btn btn-sm btn-secondary" onclick="event.stopPropagation(); moverCampo('${campo.id}', 'cima')" title="Mover campo para cima">
                            <i data-feather="arrow-up"></i>
                        </button>
                        <button type="button" class="btn btn-sm btn-secondary" onclick="event.stopPropagation(); moverCampo('${campo.id}', 'baixo')" title="Mover campo para baixo">
                            <i data-feather="arrow-down"></i>
                        </button>
                        <button type="button" class="btn btn-sm btn-secondary" onclick="event.stopPropagation(); duplicarCampo('${campo.id}')" title="Duplicar bloco">
                            <i data-feather="copy"></i>
                        </button>
                        <button type="button" class="btn btn-sm btn-danger" onclick="event.stopPropagation(); removerCampo('${campo.id}')" title="Remover campo">
                            <i data-feather="x"></i>
                        </button>
                    </div>
                </div>
                <div class="cabecalho-os cabecalho-os-preview ${variantClass} ${columnsClass} ${borderClass} mt-2">
        `;
        
        // Renderizar preview baseado nas configurações
        if (variant === 'print_like') {
            previewHTML += this.renderizarPreviewPrintLike(config, columns, campo.id);
        } else {
            previewHTML += this.renderizarPreviewCompact(config, columns);
        }
        
        previewHTML += `
                </div>
            </div>
        `;
        
        return previewHTML;
    }
    
    renderizarPreviewPrintLike(config, columns, campoId) {
        let html = '<div class="os-hd-row os-hd-top">';
        
        // LEFT: LOGO
        html += '<div class="os-hd-cell os-hd-left">';
        if (config.showLogo !== false) {
            html += '<div class="os-hd-logo">';
            html += '<img class="os-hd-logo-img" src="/static/img/logo_frigol.png" alt="Logo Frigol">';
            html += '</div>';
        }
        html += '</div>';

        // CENTER: TITLES
        html += '<div class="os-hd-cell os-hd-center">';
        if (config.showProgramName !== false) {
            const programName = config.programName || 'Programa de Gestão de Manutenção';
            html += `<div class="os-hd-title-1" 
                         contenteditable="false" 
                         data-campo-id="${campoId}"
                         data-config-key="programName"
                         ondblclick="editarProgramName(this)"
                         onblur="salvarProgramName(this)"
                         onkeydown="if(event.key==='Enter'){this.blur();event.preventDefault();}"
                         style="cursor: pointer;"
                         title="Duplo clique para editar">${programName}</div>`;
        }
        if (config.showUnit !== false) {
            // Prioridade: valor editável no config > dados da unidade carregados (sem fallback)
            const unitName = config.unitName || this.unidadeNomeCompleto || '';
            html += `<div class="os-hd-title-2" 
                         contenteditable="false" 
                         data-campo-id="${campoId}"
                         data-config-key="unitName"
                         ondblclick="editarUnitName(this)"
                         onblur="salvarUnitName(this)"
                         onkeydown="if(event.key==='Enter'){this.blur();event.preventDefault();}"
                         style="cursor: pointer;"
                         title="Duplo clique para editar">${unitName || '[Unidade não configurada]'}</div>`;
        }
        if (config.showAddress === true) {
            // Prioridade: valor editável no config > endereço da unidade carregada (sem fallback)
            const address = config.address || this.unidadeEndereco || '';
            html += `<div class="os-hd-title-3" 
                         style="font-size: 0.85em; color: #666; margin-top: 4px; cursor: pointer;"
                         contenteditable="false" 
                         data-campo-id="${campoId}"
                         data-config-key="address"
                         ondblclick="editarAddress(this)"
                         onblur="salvarAddress(this)"
                         onkeydown="if(event.key==='Enter'){this.blur();event.preventDefault();}"
                         title="Duplo clique para editar">${address || '[Endereço não configurado]'}</div>`;
        }
        html += '</div>';

        // RIGHT: META TABLE
        html += '<div class="os-hd-cell os-hd-right">';
        html += '<div class="os-hd-meta">';
        
        // Sempre mostrar 5 linhas para manter altura fixa (como formulário oficial)
        if (config.showDocumentCode !== false) {
            html += '<div class="os-hd-meta-row">';
            html += '<div class="k">Código</div>';
            const codigoDocumento = config.codigoDocumento || 'RSGM078/SIF2960';
            html += `<div class="v" 
                         contenteditable="false" 
                         data-campo-id="${campoId}"
                         data-config-key="codigoDocumento"
                         ondblclick="editarCodigoDocumento(this)"
                         onblur="salvarCodigoDocumento(this)"
                         onkeydown="if(event.key==='Enter'){this.blur();event.preventDefault();}"
                         style="cursor: pointer; min-width: 120px;"
                         title="Duplo clique para editar">${codigoDocumento}</div>`;
            html += '</div>';
        } else {
            html += '<div class="os-hd-meta-row"><div class="k">—</div><div class="v">—</div></div>';
        }
        
        if (config.showIssueDate !== false) {
            html += '<div class="os-hd-meta-row">';
            html += '<div class="k">Data Emissão</div>';
            // Data de emissão = data que o formulário foi criado
            let dataEmissao = '—';
            if (this.templateCriadoEm) {
                const mes = String(this.templateCriadoEm.getMonth() + 1).padStart(2, '0');
                const ano = this.templateCriadoEm.getFullYear();
                dataEmissao = `${mes}/${ano}`;
            }
            html += `<div class="v">${dataEmissao}</div>`;
            html += '</div>';
        } else {
            html += '<div class="os-hd-meta-row"><div class="k">—</div><div class="v">—</div></div>';
        }
        
        if (config.showRevision !== false) {
            html += '<div class="os-hd-meta-row">';
            html += '<div class="k">Data Revisão</div>';
            // Data de revisão = quando foi modificado
            let dataRevisao = '—';
            if (this.templateAtualizadoEm) {
                try {
                    const dia = String(this.templateAtualizadoEm.getDate()).padStart(2, '0');
                    const mes = String(this.templateAtualizadoEm.getMonth() + 1).padStart(2, '0');
                    const ano = this.templateAtualizadoEm.getFullYear();
                    dataRevisao = `${dia}/${mes}/${ano}`;
                } catch (e) {
                    formBuilderWarn('[FormBuilder] Erro ao formatar data de revisão:', e);
                    dataRevisao = '—';
                }
            }
            html += `<div class="v">${dataRevisao}</div>`;
            html += '</div>';
            html += '<div class="os-hd-meta-row">';
            html += '<div class="k">N° Revisão</div>';
            // N° Revisão = versão atual (sequencial de edição)
            const numeroRevisao = this.templateVersao || '—';
            html += `<div class="v">${numeroRevisao}</div>`;
            html += '</div>';
        } else {
            html += '<div class="os-hd-meta-row"><div class="k">—</div><div class="v">—</div></div>';
            html += '<div class="os-hd-meta-row"><div class="k">—</div><div class="v">—</div></div>';
        }
        
        if (config.showPageCounter !== false) {
            html += '<div class="os-hd-meta-row">';
            html += '<div class="k">Página</div>';
            html += '<div class="v">1 de 1</div>';
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
        if (config.showOsType !== false || config.showOsNumber !== false) {
            let osTypeText = '';
            if (config.showOsType !== false) {
                // Prioridade: config.osType > templateNome (sem fallback)
                if (config.osType) {
                    osTypeText = config.osType;
                } else if (this.templateNome) {
                    osTypeText = this.templateNome;
                } else {
                    osTypeText = '[Tipo de OS não configurado]';
                }
            }
            html += `<span 
                         contenteditable="false" 
                         data-campo-id="${campoId}"
                         data-config-key="osType"
                         ondblclick="editarOsType(this)"
                         onblur="salvarOsType(this)"
                         onkeydown="if(event.key==='Enter'){this.blur();event.preventDefault();}"
                         style="cursor: pointer;"
                         title="Duplo clique para editar">${osTypeText}</span>`;
        }
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
     * @param {Array} campos - Array de objetos {nome, show, html}
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
    
    renderizarPreviewSolicitante(campo, secaoId) {
        const config = campo.config || {};
        const layout = campo.layout || { columns: 2, columnSizes: [6, 6], compact: false };
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
        if (showNumeroOS) campos.push({ nome: 'numeroOS', grupo: 'os', show: true, label: 'Número da OS', valor: '[000001]', bold: true });
        if (showDataCriacao) campos.push({ nome: 'dataCriacao', grupo: 'os', show: true, label: 'Data de Criação', valor: '[DD/MM/AAAA HH:mm]' });
        if (showAtivo) campos.push({ nome: 'ativo', grupo: 'os', show: true, label: 'Ativo', valor: '[Nome do Ativo]' });
        if (showPrioridade) campos.push({ nome: 'prioridade', grupo: 'os', show: true, label: 'Prioridade', valor: '<span class="badge bg-warning">[Média]</span>', html: true });
        if (showPrazoTermino) campos.push({ nome: 'prazoTermino', grupo: 'os', show: true, label: 'Prazo de Término', valor: '[DD/MM/AAAA HH:mm]' });
        if (showSetorOS) campos.push({ nome: 'setorOS', grupo: 'os', show: true, label: 'Setor', valor: '[Nome do Setor]' });
        
        // Grupo Solicitante
        if (showNome) campos.push({ nome: 'nome', grupo: 'solicitante', show: true, label: 'Nome', valor: '[Nome do Solicitante]', bold: true });
        if (showEmail) campos.push({ nome: 'email', grupo: 'solicitante', show: true, label: 'Email', valor: '[email@exemplo.com]' });
        if (showUnidade) campos.push({ nome: 'unidade', grupo: 'solicitante', show: true, label: 'Unidade', valor: '[Unidade do Solicitante]' });
        if (showSetor) campos.push({ nome: 'setor', grupo: 'solicitante', show: true, label: 'Setor', valor: '[Setor do Solicitante]' });
        if (showTelefone) campos.push({ nome: 'telefone', grupo: 'solicitante', show: true, label: 'Telefone', valor: '[(00) 00000-0000]' });
        
        // Distribuir campos nas colunas
        const distribuicao = this.distribuirCamposColunas(campos, numColunas, columnSizes);
        
        let previewHTML = `
            <div class="form-builder-campo form-builder-campo-solicitante" 
                 draggable="true"
                 data-campo-id="${campo.id}"
                 data-secao-id="${secaoId}"
                 ondragstart="handleDragStart(event, '${campo.id}')"
                 onclick="selecionarCampo('${campo.id}')">
                <div class="form-builder-campo-header">
                    <i data-feather="user"></i>
                    <span class="campo-label" contenteditable="true" 
                          onblur="salvarLabelInline('${campo.id}', this.textContent)"
                          onkeydown="if(event.key==='Enter'){this.blur();event.preventDefault();}">
                        ${campo.label || 'Solicitante'}
                    </span>
                    <span class="badge bg-info ms-2">Read-only</span>
                    <div style="display: flex; gap: 4px;">
                        <button type="button" class="btn btn-sm btn-secondary" onclick="event.stopPropagation(); moverCampo('${campo.id}', 'cima')" title="Mover campo para cima">
                            <i data-feather="arrow-up"></i>
                        </button>
                        <button type="button" class="btn btn-sm btn-secondary" onclick="event.stopPropagation(); moverCampo('${campo.id}', 'baixo')" title="Mover campo para baixo">
                            <i data-feather="arrow-down"></i>
                        </button>
                        <button type="button" class="btn btn-sm btn-secondary" onclick="event.stopPropagation(); duplicarCampo('${campo.id}')" title="Duplicar bloco">
                            <i data-feather="copy"></i>
                        </button>
                        <button type="button" class="btn btn-sm btn-danger" onclick="event.stopPropagation(); removerCampo('${campo.id}')" title="Remover campo">
                            <i data-feather="x"></i>
                        </button>
                    </div>
                </div>
                <div class="solicitante-preview mt-2 p-3 border rounded ${compact ? 'compact' : ''}" style="background-color: #f8f9fa;">
        `;
        
        previewHTML += '<div class="row g-2">';
        
        // Renderizar cada coluna
        distribuicao.forEach((camposColuna, colunaIndex) => {
            const colSize = columnSizes[colunaIndex] || 12;
            previewHTML += `<div class="col-md-${colSize}">`;
            
            camposColuna.forEach(campoItem => {
                const boldClass = campoItem.bold ? 'fw-bold' : '';
                const valorHTML = campoItem.html ? campoItem.valor : (campoItem.valor || '—');
                previewHTML += `
                    <div class="mb-2">
                        <label class="small text-muted mb-1">${campoItem.label}</label>
                        <div class="${boldClass}">${valorHTML}</div>
                    </div>
                `;
            });
            
            previewHTML += '</div>';
        });
        
        previewHTML += '</div>';
        previewHTML += '</div>'; // .solicitante-preview
        previewHTML += '</div>'; // .form-builder-campo
        
        return previewHTML;
    }
    
    renderizarPreviewDescricaoSolicitante(campo, secaoId) {
        const config = campo.config || {};
        const rows = config.rows || 4;
        const placeholder = config.placeholder || 'Descreva o problema encontrado...';
        const obrigatorio = campo.obrigatorio || campo.validation?.required || false;
        
        let previewHTML = `
            <div class="form-builder-campo form-builder-campo-descricao-solicitante" 
                 draggable="true"
                 data-campo-id="${campo.id}"
                 data-secao-id="${secaoId}"
                 ondragstart="handleDragStart(event, '${campo.id}')"
                 onclick="selecionarCampo('${campo.id}')">
                <div class="form-builder-campo-header">
                    <i data-feather="file-text"></i>
                    <span class="campo-label" contenteditable="true" 
                          onblur="salvarLabelInline('${campo.id}', this.textContent)"
                          onkeydown="if(event.key==='Enter'){this.blur();event.preventDefault();}">
                        ${campo.label || 'Descrição do Problema'}
                    </span>
                    ${obrigatorio ? '<span class="badge bg-danger">Obrigatório</span>' : ''}
                    <button type="button" class="btn btn-sm btn-secondary" onclick="event.stopPropagation(); duplicarCampo('${campo.id}')" title="Duplicar bloco">
                        <i data-feather="copy"></i>
                    </button>
                    <button type="button" class="btn btn-sm btn-danger" onclick="event.stopPropagation(); removerCampo('${campo.id}')">
                        <i data-feather="x"></i>
                    </button>
                </div>
                <div class="descricao-solicitante-preview mt-2">
                    <label class="form-label small mb-1">${campo.label || 'Descrição do Problema'}${obrigatorio ? ' *' : ''}</label>
                    <textarea class="form-control" 
                              rows="${rows}" 
                              placeholder="${placeholder}"
                              disabled
                              style="min-height: ${rows * 24}px; resize: vertical;">[Campo de texto para descrição do problema]</textarea>
                    <small class="text-muted">Este campo coletará a descrição do problema ao criar a OS</small>
                </div>
            </div>
        `;
        
        return previewHTML;
    }
    
    renderizarPreviewCompact(config, columns) {
        let html = '<div class="row g-2">';
        
        if (config.showLogo !== false) {
            html += '<div class="col-auto"><small class="text-muted">[Logo]</small></div>';
        }
        if (config.showProgramName !== false) {
            html += '<div class="col"><small><strong>[Programa]</strong></small></div>';
        }
        if (config.showDocumentCode !== false) {
            html += '<div class="col-auto"><span class="badge bg-secondary">RSGM-XXX</span></div>';
        }
        if (config.showOsNumber !== false) {
            html += '<div class="col-auto"><small><strong>OS:</strong> [000000]</small></div>';
        }
        
        html += '</div>';
        
        if (config.showUnit !== false || config.showOsType !== false || config.showIssueDate !== false) {
            html += '<div class="row g-2 mt-1">';
            if (config.showUnit !== false) {
                html += '<div class="col"><small class="text-muted">[Unidade]</small></div>';
            }
            if (config.showOsType !== false) {
                html += '<div class="col"><small class="text-muted">[Tipo OS]</small></div>';
            }
            if (config.showIssueDate !== false) {
                html += '<div class="col"><small class="text-muted">[Data]</small></div>';
            }
            html += '</div>';
        }
        
        return html;
    }
    
    inicializarDragAndDrop() {
        formBuilderLog('[FormBuilder] Inicializando drag and drop...');
        
        // Tornar blocos da lateral arrastáveis - incluir todos os containers de blocos
        const seletores = [
            '#lista-blocos-basicos .list-group-item[data-tipo]',
            '#lista-blocos-cmms .list-group-item[data-tipo]',
            '#lista-blocos-especiais .list-group-item[data-tipo]',
            '#catalogo-blocos .list-group-item'
        ];
        
        let totalBlocos = 0;
        seletores.forEach(seletor => {
            const blocos = document.querySelectorAll(seletor);
            formBuilderLog(`[FormBuilder] Seletor "${seletor}": ${blocos.length} elementos encontrados`);
            totalBlocos += blocos.length;
            
            blocos.forEach((bloco, index) => {
                // Remover listeners anteriores se existirem
                const novoBloco = bloco.cloneNode(true);
                bloco.parentNode.replaceChild(novoBloco, bloco);
                
                // Garantir que está arrastável
                novoBloco.setAttribute('draggable', 'true');
                
                novoBloco.addEventListener('dragstart', (e) => {
                    const tipo = novoBloco.dataset.tipo || this.obterTipoBloco(novoBloco);
                    const data = {
                        tipo: 'novo',
                        campo_tipo: tipo
                    };
                    formBuilderLog('[FormBuilder] DragStart - Bloco arrastado:', {
                        tipo: tipo,
                        elemento: novoBloco,
                        data: data
                    });
                    
                    e.dataTransfer.setData('text/plain', JSON.stringify(data));
                    e.dataTransfer.effectAllowed = 'copy';
                    novoBloco.style.opacity = '0.5';
                });
                
                novoBloco.addEventListener('dragend', (e) => {
                    formBuilderLog('[FormBuilder] DragEnd - Bloco solto');
                    novoBloco.style.opacity = '1';
                });
            });
        });
        
        formBuilderLog(`[FormBuilder] Total de blocos arrastáveis configurados: ${totalBlocos}`);
        
        // Adicionar eventos de drag over/leave nas áreas de drop
        const areasDrop = document.querySelectorAll('.form-builder-secao-body');
        formBuilderLog(`[FormBuilder] Áreas de drop encontradas: ${areasDrop.length}`);
        
        areasDrop.forEach((area, index) => {
            // Obter secaoId antes de clonar
            const secaoId = area.dataset.secaoId || area.closest('.form-builder-secao')?.dataset.secaoId;
            
            if (!secaoId) {
                formBuilderWarn('[FormBuilder] ⚠️ Área de drop sem secaoId:', area);
                return;
            }
            
            formBuilderLog(`[FormBuilder] Configurando área de drop ${index + 1} - secaoId: ${secaoId}`);
            
            // Remover listeners anteriores clonando o elemento
            const novaArea = area.cloneNode(true);
            // Preservar data-secao-id
            novaArea.setAttribute('data-secao-id', secaoId);
            area.parentNode.replaceChild(novaArea, area);
            
            // Adicionar listeners
            // Usar { passive: false } para garantir que preventDefault funcione
            novaArea.addEventListener('dragover', handleDragOver, { passive: false });
            novaArea.addEventListener('dragleave', handleDragLeave);
            
            // CRÍTICO: O evento drop precisa estar registrado e preventDefault deve ser chamado
            novaArea.addEventListener('drop', (e) => {
                formBuilderLog('[FormBuilder] 🎯 Drop detectado! Seção:', secaoId);
                handleDrop(e, secaoId);
            }, { passive: false });
            
            // Também adicionar na zona de drop vazia dentro da seção
            const dropZone = novaArea.querySelector('.form-builder-drop-zone');
            if (dropZone) {
                dropZone.addEventListener('dragover', handleDragOver, { passive: false });
                dropZone.addEventListener('drop', (e) => {
                    formBuilderLog('[FormBuilder] 🎯 Drop na zona vazia! Seção:', secaoId);
                    e.stopPropagation(); // Evitar que o evento suba para a seção
                    handleDrop(e, secaoId);
                }, { passive: false });
            }
        });
        
        formBuilderLog('[FormBuilder] ✅ Drag and drop inicializado com sucesso');
    }
    
    obterTipoBloco(elemento) {
        // Determinar tipo do bloco pelo atributo data-tipo ou texto
        if (elemento.dataset && elemento.dataset.tipo) {
            return elemento.dataset.tipo;
        }
        
        const texto = elemento.textContent.toLowerCase();
        if (texto.includes('texto')) return 'text';
        if (texto.includes('numérico') || texto.includes('numero')) return 'number';
        if (texto.includes('data')) return 'date';
        if (texto.includes('checklist')) return 'checklist';
        if (texto.includes('tabela')) return 'tabela';
        return 'text';
    }
    
    /**
     * Adiciona um novo campo/bloco ao formulário
     * 
     * ============================================================================
     * ETAPAS OBRIGATÓRIAS PARA TODOS OS BLOCOS CRIADOS
     * ============================================================================
     * 
     * IMPORTANTE: Ao criar um novo tipo de campo ou modificar este método,
     * as seguintes etapas são OBRIGATÓRIAS e devem ser seguidas SEMPRE:
     * 
     * 1. ESTRUTURA BÁSICA OBRIGATÓRIA (todos os campos devem ter):
     *    - id: Identificador único (gerado como `campo_${Date.now()}`)
     *    - tipo: Tipo do campo (text, number, date, cabecalho_os, etc.)
     *    - label: Rótulo visível no formulário
     *    - obrigatorio: Boolean indicando se campo é obrigatório
     * 
     * 2. ESTRUTURAS POR CATEGORIA:
     * 
     *    a) CAMPOS ESPECIAIS (cabecalho_os, solicitante, descricao_solicitante):
     *       - Devem ter objeto `config` com propriedades específicas do tipo
     *       - Podem ter objeto `layout` para configuração de exibição
     *       - Podem ter objeto `data` para bindings e valores padrão
     * 
     *    b) CAMPOS PADRÃO (text, number, date, checklist, tabela, etc.):
     *       - DEVEM ter TODAS estas estruturas obrigatórias:
     *         * layout: { width, columns, align }
     *         * data: { mode, binding, default }
     *         * render: { showWhen, format, placeholder, emptyState }
     *         * validation: { required, requiredWhen, rules }
     *         * permissions: { visibility, editable, editableWhen }
     *         * audit: { trackChanges, immutableAfter }
     *       - Campos de compatibilidade com schema legado também são obrigatórios:
     *         (obrigatorio, descricao, valor_padrao, visivel_por_perfil, editavel_por_perfil)
     * 
     * 3. ETAPAS APÓS CRIAR O OBJETO CAMPO (sempre executar nesta ordem):
     *    a) Adicionar campo ao array: this.schema.campos.push(campo)
     *    b) Se secaoId fornecido:
     *       - Buscar seção existente ou criar nova se não existir
     *       - Adicionar campoId ao array secao.campos
     *       - Se criar nova seção, usar estrutura: { id, titulo, ordem: length+1, campos: [] }
     *    c) Chamar this.renderizar() para atualizar o preview
     *    d) Chamar this.selecionarCampo(campoId) para selecionar o novo campo
     * 
     * 4. PADRÕES OBRIGATÓRIOS:
     *    - ID: Sempre usar `campo_${Date.now()}` para garantir unicidade
     *    - Ordem de seções: Usar `this.schema.secoes.length + 1` para nova seção
     *    - Merging de config: Sempre usar spread: `...(config.config || {})` e valores padrão DEPOIS
     *    - Logging: Sempre logar criação: `formBuilderLog('[FormBuilder] Campo criado:', campo)`
     * 
     * 5. NOTAS IMPORTANTES:
     *    - Valores padrão devem vir DEPOIS do spread para garantir precedência
     *    - Campos especiais podem ter estruturas diferentes, mas devem seguir padrão de ID, tipo, label
     *    - Todos os campos devem ser adicionados a this.schema.campos antes de renderizar
     * 
     * ============================================================================
     * 
     * @param {string} tipo - Tipo do campo (text, number, date, cabecalho_os, solicitante, etc.)
     * @param {object} config - Configurações do campo (label, obrigatorio, config, layout, data, etc.)
     * @param {string|null} secaoId - ID da seção onde adicionar o campo (null = sem seção)
     */
    adicionarCampo(tipo, config = {}, secaoId = null) {
        formBuilderLog('[FormBuilder] adicionarCampo chamado:', { tipo, config, secaoId });
        const campoId = `campo_${Date.now()}`;
        
        // Configuração especial para cabeçalho da OS
        if (tipo === 'cabecalho_os') {
            const campo = {
                id: campoId,
                tipo: tipo,
                label: config.label || 'Cabeçalho da Ordem de Serviço',
                obrigatorio: false, // Cabeçalho nunca é obrigatório (read-only)
                config: {
                    showLogo: true,
                    showProgramName: true,
                    programName: 'Programa de Gestão de Manutenção', // Nome do programa editável
                    showUnit: true,
                    // Prioridade: usar dados da unidade carregados (sem fallback)
                    unitName: this.unidadeNomeCompleto || '', // Nome da unidade editável
                    showAddress: false,
                    address: this.unidadeEndereco || '', // Endereço editável (da unidade ou vazio)
                    showDocumentCode: true,
                    codigoDocumento: 'RSGM078/SIF2960', // Código do documento editável
                    showRegulatory: true,
                    showRevision: true,
                    showPageCounter: true,
                    showOsNumber: true,
                    showOsType: true,
                    osType: '', // Tipo da OS editável (se vazio, usa templateNome ou fallback)
                    showIssueDate: true,
                    ...(config.config || {})
                },
                layout: {
                    variant: 'print_like',
                    columns: 3,
                    showBorders: true,
                    ...(config.layout || {})
                },
                ...config
            };
            
            formBuilderLog('[FormBuilder] Campo cabeçalho criado:', campo);
            this.schema.campos.push(campo);
        } else if (tipo === 'solicitante') {
            // Configuração especial para solicitante
            const campo = {
                id: campoId,
                tipo: tipo,
                label: config.label || 'Solicitante',
                obrigatorio: false, // Solicitante nunca é obrigatório (read-only)
                config: {
                    // Informações da Nova Ordem de Serviço
                    showNumeroOS: true,
                    showDataCriacao: true,
                    showAtivo: true,
                    showPrioridade: true,
                    showPrazoTermino: true,
                    showSetorOS: true,
                    // Informações do Solicitante
                    showNome: true,
                    showEmail: true,
                    showUnidade: true,
                    showSetor: false,
                    showTelefone: false,
                    ...(config.config || {})
                },
                layout: {
                    columns: config.layout?.columns || 2,
                    columnSizes: config.layout?.columnSizes || [6, 6],
                    compact: config.layout?.compact || false,
                    ...(config.layout || {})
                },
                ...config
            };
            
            formBuilderLog('[FormBuilder] Campo solicitante criado:', campo);
            this.schema.campos.push(campo);
        } else if (tipo === 'descricao_solicitante') {
            // Configuração especial para descrição do solicitante
            const campo = {
                id: campoId,
                tipo: tipo,
                label: config.label || 'Descrição do Problema',
                obrigatorio: config.obrigatorio !== undefined ? config.obrigatorio : true, // Padrão: obrigatório
                config: {
                    rows: config.config?.rows || 4, // Número de linhas do textarea
                    placeholder: config.config?.placeholder || 'Descreva o problema encontrado...',
                    maxLength: config.config?.maxLength || null, // Tamanho máximo (null = sem limite)
                    ...(config.config || {})
                },
                data: {
                    mode: 'input', // Campo editável pelo usuário
                    binding: 'os.descricao_problema', // Binding para os.descricao_problema
                    ...(config.data || {})
                },
                ...config
            };
            
            formBuilderLog('[FormBuilder] Campo descricao_solicitante criado:', campo);
            this.schema.campos.push(campo);
        } else if (tipo === 'descricao_tecnico') {
            // Configuração especial para descrição do técnico
            const campo = {
                id: campoId,
                tipo: tipo,
                label: config.label || 'Descrição das Ocorrências',
                obrigatorio: config.obrigatorio !== undefined ? config.obrigatorio : false, // Padrão: opcional
                config: {
                    permite_edicao_tecnico: config.config?.permite_edicao_tecnico !== undefined ? config.config.permite_edicao_tecnico : true,
                    permite_edicao_hierarquia_acima: config.config?.permite_edicao_hierarquia_acima !== undefined ? config.config.permite_edicao_hierarquia_acima : true,
                    rows: config.config?.rows || 6,
                    placeholder: config.config?.placeholder || 'Descreva as ocorrências encontradas durante o atendimento...',
                    maxLength: config.config?.maxLength || 5000,
                    ...(config.config || {})
                },
                data: {
                    mode: 'input', // Campo editável pelo técnico
                    ...(config.data || {})
                },
                validation: {
                    required: config.validation?.required !== undefined ? config.validation.required : false,
                    maxLength: config.validation?.maxLength || 5000,
                    ...(config.validation || {})
                },
                ...config
            };
            
            formBuilderLog('[FormBuilder] Campo descricao_tecnico criado:', campo);
            this.schema.campos.push(campo);
        } else {
            // Schema padrão completo conforme templates.md
            const campo = {
                id: campoId,
                tipo: tipo,
                label: config.label || `Campo ${tipo}`,
                help: config.help || config.descricao || '', // Compatibilidade com descricao
                
                // Layout
                layout: {
                    width: config.layout?.width || 'full',
                    columns: config.layout?.columns || 1,
                    align: config.layout?.align || 'left',
                    ...(config.layout || {})
                },
                
                // Data
                data: {
                    mode: config.data?.mode || 'input', // input | computed | readonly
                    binding: config.data?.binding || null,
                    default: config.data?.default || config.valor_padrao || null, // Compatibilidade
                    ...(config.data || {})
                },
                
                // Render
                render: {
                    showWhen: config.render?.showWhen || [{ if: 'always' }],
                    format: {
                        date: config.render?.format?.date || 'DD/MM/YYYY',
                        datetime: config.render?.format?.datetime || 'DD/MM/YYYY HH:mm',
                        numberDecimals: config.render?.format?.numberDecimals || null,
                        mask: config.render?.format?.mask || null,
                        ...(config.render?.format || {})
                    },
                    placeholder: config.render?.placeholder || '',
                    emptyState: config.render?.emptyState || '—',
                    ...(config.render || {})
                },
                
                // Validation
                validation: {
                    required: config.validation?.required || config.obrigatorio || false, // Compatibilidade
                    requiredWhen: config.validation?.requiredWhen || [],
                    rules: config.validation?.rules || [],
                    ...(config.validation || {})
                },
                
                // Permissions
                permissions: {
                    visibility: config.permissions?.visibility || ['ADMIN', 'PCM', 'SUPERVISOR', 'TECNICO', 'SOLICITANTE'],
                    editable: config.permissions?.editable || [],
                    editableWhen: config.permissions?.editableWhen || [],
                    ...(config.permissions || {})
                },
                
                // Audit
                audit: {
                    trackChanges: config.audit?.trackChanges !== undefined ? config.audit.trackChanges : true,
                    immutableAfter: config.audit?.immutableAfter || [],
                    ...(config.audit || {})
                },
                
                // Compatibilidade com schema legado
                obrigatorio: config.obrigatorio || false,
                descricao: config.descricao || '',
                valor_padrao: config.valor_padrao || null,
                visivel_por_perfil: config.visivel_por_perfil || [],
                editavel_por_perfil: config.editavel_por_perfil || [],
                
                // Outras propriedades específicas do tipo
                ...config
            };
            
            formBuilderLog('[FormBuilder] Campo criado com schema padrão:', campo);
            this.schema.campos.push(campo);
        }
        
        // Adicionar campo à seção
        if (secaoId) {
            let secao = this.schema.secoes.find(s => s.id === secaoId);
            if (!secao) {
                formBuilderLog('[FormBuilder] Criando nova seção:', secaoId);
                // Criar seção se não existir
                secao = {
                    id: secaoId,
                    titulo: '',
                    ordem: this.schema.secoes.length + 1,
                    campos: []
                };
                this.schema.secoes.push(secao);
            }
            if (!secao.campos) {
                secao.campos = [];
            }
            secao.campos.push(campoId);
            formBuilderLog('[FormBuilder] Campo adicionado à seção. Campos na seção:', secao.campos);
        }
        
        formBuilderLog('[FormBuilder] Renderizando após adicionar campo...');
        this.renderizar();
        this.selecionarCampo(campoId);
    }
    
    moverCampo(campoId, secaoOrigemId, secaoDestinoId) {
        // Remover da seção origem
        const secaoOrigem = this.schema.secoes.find(s => s.id === secaoOrigemId);
        if (secaoOrigem && secaoOrigem.campos) {
            secaoOrigem.campos = secaoOrigem.campos.filter(id => id !== campoId);
        }
        
        // Adicionar à seção destino
        let secaoDestino = this.schema.secoes.find(s => s.id === secaoDestinoId);
        if (!secaoDestino) {
            secaoDestino = {
                id: secaoDestinoId,
                titulo: '',
                ordem: this.schema.secoes.length + 1,
                campos: []
            };
            this.schema.secoes.push(secaoDestino);
        }
        if (!secaoDestino.campos) {
            secaoDestino.campos = [];
        }
        if (!secaoDestino.campos.includes(campoId)) {
            secaoDestino.campos.push(campoId);
        }
        
        this.renderizar();
    }
    
    selecionarCampo(campoId) {
        this.campoSelecionado = campoId;
        const campo = this.schema.campos.find(c => c.id === campoId);
        
        if (!campo) return;
        
        // Atualizar painel de propriedades
        const painel = document.getElementById('painel-propriedades');
        if (!painel) return;
        
        // Painel especial para cabeçalho da OS
        if (campo.tipo === 'cabecalho_os') {
            this.renderizarPropriedadesCabecalhoOS(campo, campoId);
            return;
        }
        
        // Painel especial para solicitante
        if (campo.tipo === 'solicitante') {
            this.renderizarPropriedadesSolicitante(campo, campoId);
            return;
        }
        
        // Painel especial para descrição do solicitante
        if (campo.tipo === 'descricao_solicitante') {
            this.renderizarPropriedadesDescricaoSolicitante(campo, campoId);
            return;
        }
        
        // Painel especial para descrição do técnico
        if (campo.tipo === 'descricao_tecnico') {
            this.renderizarPropriedadesDescricaoTecnico(campo, campoId);
            return;
        }
        
        // Inicializar propriedades padrão se não existirem
        if (!campo.layout) campo.layout = { width: 'full', columns: 1, align: 'left' };
        if (!campo.data) campo.data = { mode: 'input', binding: null, default: null };
        if (!campo.render) campo.render = { showWhen: [{ if: 'always' }], format: {}, placeholder: '', emptyState: '—' };
        if (!campo.validation) campo.validation = { required: false, requiredWhen: [], rules: [] };
        if (!campo.permissions) campo.permissions = { visibility: ['ADMIN', 'PCM', 'SUPERVISOR', 'TECNICO', 'SOLICITANTE'], editable: [], editableWhen: [] };
        if (!campo.audit) campo.audit = { trackChanges: true, immutableAfter: [] };
        if (!campo.permissao_escrita) campo.permissao_escrita = null;
        
        // Compatibilidade com schema legado
        const layout = campo.layout;
        const data = campo.data;
        const render = campo.render;
        const validation = campo.validation;
        const permissions = campo.permissions;
        const audit = campo.audit;
        
        // Valores para UI
        const help = campo.help || campo.descricao || '';
        const valorPadrao = data.default || campo.valor_padrao || '';
        const obrigatorio = validation.required || campo.obrigatorio || false;
        
        painel.innerHTML = `
            <h6>Propriedades do Campo</h6>
            <div class="mb-3">
                <label class="form-label">ID</label>
                <input type="text" class="form-control form-control-sm" value="${campo.id}" readonly>
            </div>
            <div class="mb-3">
                <label class="form-label">Label *</label>
                <input type="text" class="form-control form-control-sm" id="prop-label" value="${campo.label || ''}" 
                       onchange="atualizarPropriedadeCampo('${campoId}', 'label', this.value)">
            </div>
            <div class="mb-3">
                <label class="form-label">Tipo</label>
                <select class="form-select form-select-sm" id="prop-tipo" 
                        onchange="atualizarPropriedadeCampo('${campoId}', 'tipo', this.value)">
                    <optgroup label="Básicos">
                        <option value="text" ${campo.tipo === 'text' ? 'selected' : ''}>Texto</option>
                        <option value="number" ${campo.tipo === 'number' ? 'selected' : ''}>Número</option>
                        <option value="date" ${campo.tipo === 'date' ? 'selected' : ''}>Data</option>
                        <option value="hora" ${campo.tipo === 'hora' ? 'selected' : ''}>Hora</option>
                        <option value="datetime" ${campo.tipo === 'datetime' ? 'selected' : ''}>Data + Hora</option>
                        <option value="boolean" ${campo.tipo === 'boolean' ? 'selected' : ''}>Booleano (Sim/Não)</option>
                        <option value="select" ${campo.tipo === 'select' ? 'selected' : ''}>Select</option>
                        <option value="checkbox" ${campo.tipo === 'checkbox' ? 'selected' : ''}>Checkbox</option>
                    </optgroup>
                    <optgroup label="CMMS">
                        <option value="apontamento_horas" ${campo.tipo === 'apontamento_horas' ? 'selected' : ''}>Apontamento de Horas</option>
                        <option value="materiais_pecas" ${campo.tipo === 'materiais_pecas' ? 'selected' : ''}>Materiais/Peças</option>
                        <option value="equipamentos" ${campo.tipo === 'equipamentos' ? 'selected' : ''}>Equipamentos</option>
                        <option value="ativos" ${campo.tipo === 'ativos' ? 'selected' : ''}>Ativos</option>
                        <option value="status_final" ${campo.tipo === 'status_final' ? 'selected' : ''}>Status Final do Serviço</option>
                        <option value="seguranca_operacional" ${campo.tipo === 'seguranca_operacional' ? 'selected' : ''}>Segurança Operacional</option>
                        <option value="qsa" ${campo.tipo === 'qsa' ? 'selected' : ''}>QSA (C/NC)</option>
                        <option value="solicitante" ${campo.tipo === 'solicitante' ? 'selected' : ''}>Solicitante</option>
                        <option value="descricao_solicitante" ${campo.tipo === 'descricao_solicitante' ? 'selected' : ''}>Descrição do Solicitante</option>
                        <option value="descricao_tecnico" ${campo.tipo === 'descricao_tecnico' ? 'selected' : ''}>Descrição do Técnico</option>
                    </optgroup>
                    <optgroup label="Especiais">
                        <option value="checklist" ${campo.tipo === 'checklist' ? 'selected' : ''}>Checklist</option>
                        <option value="tabela" ${campo.tipo === 'tabela' ? 'selected' : ''}>Tabela Repetível</option>
                        <option value="upload" ${campo.tipo === 'upload' ? 'selected' : ''}>Upload</option>
                        <option value="texto_informativo" ${campo.tipo === 'texto_informativo' ? 'selected' : ''}>Texto Informativo (read-only)</option>
                        <option value="cabecalho_os" ${campo.tipo === 'cabecalho_os' ? 'selected' : ''}>Cabeçalho da OS</option>
                    </optgroup>
                </select>
            </div>
            <div class="mb-3">
                <label class="form-label">Descrição/Ajuda</label>
                <textarea class="form-control form-control-sm" id="prop-help" rows="2" 
                          placeholder="Texto de ajuda para o usuário"
                          onchange="atualizarPropriedadeCampo('${campoId}', 'help', this.value); atualizarPropriedadeCampo('${campoId}', 'descricao', this.value)">${help}</textarea>
            </div>
            
            <hr>
            <h6>Layout</h6>
            <div class="mb-3">
                <label class="form-label">Largura</label>
                <select class="form-select form-select-sm" id="prop-layout-width" 
                        onchange="atualizarLayoutCampo('${campoId}', 'width', this.value)">
                    <option value="full" ${layout.width === 'full' ? 'selected' : ''}>100% (Completo)</option>
                    <option value="half" ${layout.width === 'half' ? 'selected' : ''}>50% (Metade)</option>
                    <option value="third" ${layout.width === 'third' ? 'selected' : ''}>33% (Um Terço)</option>
                </select>
            </div>
            <div class="mb-3">
                <label class="form-label">Colunas</label>
                <input type="number" class="form-control form-control-sm" id="prop-layout-columns" 
                       value="${layout.columns || 1}" min="1" max="12"
                       onchange="atualizarLayoutCampo('${campoId}', 'columns', parseInt(this.value))">
            </div>
            <div class="mb-3">
                <label class="form-label">Alinhamento</label>
                <select class="form-select form-select-sm" id="prop-layout-align" 
                        onchange="atualizarLayoutCampo('${campoId}', 'align', this.value)">
                    <option value="left" ${layout.align === 'left' ? 'selected' : ''}>Esquerda</option>
                    <option value="center" ${layout.align === 'center' ? 'selected' : ''}>Centro</option>
                    <option value="right" ${layout.align === 'right' ? 'selected' : ''}>Direita</option>
                </select>
            </div>
            
            <hr>
            <h6>Dados</h6>
            <div class="mb-3">
                <label class="form-label">Modo</label>
                <select class="form-select form-select-sm" id="prop-data-mode" 
                        onchange="atualizarDataCampo('${campoId}', 'mode', this.value)">
                    <option value="input" ${data.mode === 'input' ? 'selected' : ''}>Input (usuário preenche)</option>
                    <option value="computed" ${data.mode === 'computed' ? 'selected' : ''}>Computed (calculado)</option>
                    <option value="readonly" ${data.mode === 'readonly' ? 'selected' : ''}>Readonly (somente leitura)</option>
                </select>
                <small class="text-muted">Input: salva no JSON. Computed: calculado em runtime. Readonly: não editável.</small>
            </div>
            <div class="mb-3">
                <label class="form-label">Binding Source</label>
                <input type="text" class="form-control form-control-sm" id="prop-data-binding" 
                       value="${data.binding?.source || ''}"
                       placeholder="Ex: os.number, user.name, company.logo_url"
                       onchange="atualizarDataCampo('${campoId}', 'binding', { source: this.value })">
                <small class="text-muted">Fonte de dados para campos computed/readonly</small>
            </div>
            <div class="mb-3">
                <label class="form-label">Valor Padrão</label>
                <input type="text" class="form-control form-control-sm" id="prop-data-default" 
                       value="${valorPadrao}"
                       placeholder="Valor inicial do campo"
                       onchange="atualizarDataCampo('${campoId}', 'default', this.value)">
            </div>
            
            <hr>
            <h6>Renderização</h6>
            <div class="mb-3">
                <label class="form-label">Placeholder</label>
                <input type="text" class="form-control form-control-sm" id="prop-render-placeholder" 
                       value="${render.placeholder || ''}"
                       placeholder="Texto de placeholder"
                       onchange="atualizarRenderCampo('${campoId}', 'placeholder', this.value)">
            </div>
            <div class="mb-3">
                <label class="form-label">Estado Vazio</label>
                <input type="text" class="form-control form-control-sm" id="prop-render-emptyState" 
                       value="${render.emptyState || '—'}"
                       placeholder="—"
                       onchange="atualizarRenderCampo('${campoId}', 'emptyState', this.value)">
                <small class="text-muted">Texto exibido quando campo está vazio</small>
            </div>
            <div class="mb-3">
                <label class="form-label">Formato Data</label>
                <input type="text" class="form-control form-control-sm" id="prop-render-format-date" 
                       value="${render.format?.date || 'DD/MM/YYYY'}"
                       placeholder="DD/MM/YYYY"
                       onchange="atualizarRenderCampo('${campoId}', 'format', { ...window.editor.schema.campos.find(c => c.id === '${campoId}')?.render?.format || {}, date: this.value })">
            </div>
            <div class="mb-3">
                <label class="form-label">Formato Data/Hora</label>
                <input type="text" class="form-control form-control-sm" id="prop-render-format-datetime" 
                       value="${render.format?.datetime || 'DD/MM/YYYY HH:mm'}"
                       placeholder="DD/MM/YYYY HH:mm"
                       onchange="atualizarRenderCampo('${campoId}', 'format', { ...window.editor.schema.campos.find(c => c.id === '${campoId}')?.render?.format || {}, datetime: this.value })">
            </div>
            <div class="mb-3">
                <label class="form-label">Decimais (Número)</label>
                <input type="number" class="form-control form-control-sm" id="prop-render-format-numberDecimals" 
                       value="${render.format?.numberDecimals || ''}"
                       placeholder="Ex: 2"
                       min="0" max="10"
                       onchange="atualizarRenderCampo('${campoId}', 'format', { ...window.editor.schema.campos.find(c => c.id === '${campoId}')?.render?.format || {}, numberDecimals: this.value ? parseInt(this.value) : null })">
            </div>
            <div class="mb-3">
                <label class="form-label">Máscara de Input</label>
                <select class="form-select form-select-sm" id="prop-render-format-mask" 
                        onchange="atualizarMascaraCampo('${campoId}', this.value)">
                    <option value="">Sem máscara</option>
                    <option value="cpf" ${render.format?.mask === 'cpf' || render.format?.mask === '000.000.000-00' ? 'selected' : ''}>CPF (000.000.000-00)</option>
                    <option value="cnpj" ${render.format?.mask === 'cnpj' || render.format?.mask === '00.000.000/0000-00' ? 'selected' : ''}>CNPJ (00.000.000/0000-00)</option>
                    <option value="telefone" ${render.format?.mask === 'telefone' || render.format?.mask === '(00) 00000-0000' ? 'selected' : ''}>Telefone ((00) 00000-0000)</option>
                    <option value="cep" ${render.format?.mask === 'cep' || render.format?.mask === '00000-000' ? 'selected' : ''}>CEP (00000-000)</option>
                    <option value="data" ${render.format?.mask === 'data' || render.format?.mask === 'DD/MM/YYYY' ? 'selected' : ''}>Data (DD/MM/YYYY)</option>
                    <option value="custom" ${render.format?.mask && !['cpf', 'cnpj', 'telefone', 'cep', 'data'].includes(render.format.mask) ? 'selected' : ''}>Customizada</option>
                </select>
            </div>
            <div class="mb-3" id="prop-render-format-mask-custom" style="display: ${render.format?.mask && !['cpf', 'cnpj', 'telefone', 'cep', 'data'].includes(render.format.mask) ? 'block' : 'none'};">
                <label class="form-label">Máscara Customizada</label>
                <input type="text" class="form-control form-control-sm" id="prop-render-format-mask-custom-value" 
                       value="${render.format?.mask && !['cpf', 'cnpj', 'telefone', 'cep', 'data'].includes(render.format.mask) ? render.format.mask : ''}"
                       placeholder="Ex: 000-000 (0 = dígito, outros = literais)"
                       onchange="atualizarMascaraCustomizada('${campoId}', this.value)">
                <small class="text-muted">Use 0 para dígitos, outros caracteres são literais. Ex: 000-000, (00) 00000-0000</small>
            </div>
            <div class="mb-3">
                <label class="form-label">Condições de Visibilidade (showWhen)</label>
                <div id="prop-render-showWhen-list" class="mb-2">
                    ${this.renderizarListaCondicoes(render.showWhen || [], campoId, 'showWhen')}
                </div>
                <button type="button" class="btn btn-sm btn-outline-primary" onclick="adicionarCondicaoShowWhen('${campoId}')">
                    <i data-feather="plus"></i> Adicionar Condição
                </button>
            </div>
            
            <hr>
            <h6>Validação</h6>
            <div class="mb-3">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="prop-validation-required" 
                           ${obrigatorio ? 'checked' : ''}
                           onchange="atualizarValidationCampo('${campoId}', 'required', this.checked); atualizarPropriedadeCampo('${campoId}', 'obrigatorio', this.checked)">
                    <label class="form-check-label" for="prop-validation-required">
                        Campo Obrigatório
                    </label>
                </div>
            </div>
            <div class="mb-3">
                <label class="form-label">Obrigatório Quando (requiredWhen)</label>
                <div id="prop-validation-requiredWhen-list" class="mb-2">
                    ${this.renderizarListaCondicoes(validation.requiredWhen || [], campoId, 'requiredWhen')}
                </div>
                <button type="button" class="btn btn-sm btn-outline-primary" onclick="adicionarCondicaoRequiredWhen('${campoId}')">
                    <i data-feather="plus"></i> Adicionar Condição
                </button>
            </div>
            
            <hr>
            <h6>Permissões</h6>
            <div class="mb-3">
                <label class="form-label">Visibilidade (roles)</label>
                <input type="text" class="form-control form-control-sm" id="prop-permissions-visibility" 
                       value="${(permissions.visibility || []).join(', ')}"
                       placeholder="ADMIN, PCM, SUPERVISOR, TECNICO, SOLICITANTE"
                       onchange="atualizarPermissionsCampo('${campoId}', 'visibility', this.value.split(',').map(s => s.trim()).filter(s => s))">
                <small class="text-muted">Roles separados por vírgula</small>
            </div>
            <div class="mb-3">
                <label class="form-label">Editável (roles)</label>
                <input type="text" class="form-control form-control-sm" id="prop-permissions-editable" 
                       value="${(permissions.editable || []).join(', ')}"
                       placeholder="ADMIN, PCM"
                       onchange="atualizarPermissionsCampo('${campoId}', 'editable', this.value.split(',').map(s => s.trim()).filter(s => s))">
                <small class="text-muted">Roles que podem editar (separados por vírgula)</small>
            </div>
            <div class="mb-3">
                <label class="form-label">Editável Quando (editableWhen)</label>
                <div id="prop-permissions-editableWhen-list" class="mb-2">
                    ${this.renderizarListaCondicoes(permissions.editableWhen || [], campoId, 'editableWhen')}
                </div>
                <button type="button" class="btn btn-sm btn-outline-primary" onclick="adicionarCondicaoEditableWhen('${campoId}')">
                    <i data-feather="plus"></i> Adicionar Condição
                </button>
            </div>
            
            <hr>
            <h6>Permissões de Escrita RBAC</h6>
            <div class="alert alert-info alert-sm py-2 px-3 mb-3">
                <small><i data-feather="info"></i> Configure permissões específicas para este campo. Se não configurado, o campo herda a permissão do bloco ao qual pertence.</small>
            </div>
            <div class="mb-3">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="prop-permissao-escrita-enabled" 
                           ${campo.permissao_escrita !== null && campo.permissao_escrita !== undefined ? 'checked' : ''}
                           onchange="togglePermissaoEscritaRBAC('${campoId}', this.checked)">
                    <label class="form-check-label" for="prop-permissao-escrita-enabled">
                        Configurar permissão específica (sobrescreve permissão do bloco)
                    </label>
                </div>
            </div>
            <div id="prop-permissao-escrita-config" style="display: ${campo.permissao_escrita !== null && campo.permissao_escrita !== undefined ? 'block' : 'none'};">
                <div class="mb-3">
                    <label class="form-label">Permissão RBAC</label>
                    <input type="text" class="form-control form-control-sm" id="prop-permissao-escrita-rbac" 
                           value="${campo.permissao_escrita?.permissao_necessaria || ''}"
                           placeholder="Ex: manutencao:os:editar_custo"
                           onchange="atualizarPermissaoEscritaRBAC('${campoId}', 'permissao_necessaria', this.value)">
                    <small class="text-muted">Permissão no formato 'modulo:recurso:acao'. Deixe vazio para não verificar permissão RBAC específica.</small>
                </div>
                <div class="mb-3">
                    <label class="form-label">Roles Permitidas</label>
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" id="prop-permissao-escrita-role-solicitante" 
                               ${(campo.permissao_escrita?.roles_permitidas || []).includes('SOLICITANTE') ? 'checked' : ''}
                               onchange="atualizarPermissaoEscritaRoles('${campoId}', 'SOLICITANTE', this.checked)">
                        <label class="form-check-label" for="prop-permissao-escrita-role-solicitante">SOLICITANTE</label>
                    </div>
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" id="prop-permissao-escrita-role-tecnico" 
                               ${(campo.permissao_escrita?.roles_permitidas || []).includes('TECNICO') ? 'checked' : ''}
                               onchange="atualizarPermissaoEscritaRoles('${campoId}', 'TECNICO', this.checked)">
                        <label class="form-check-label" for="prop-permissao-escrita-role-tecnico">TECNICO</label>
                    </div>
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" id="prop-permissao-escrita-role-pcm" 
                               ${(campo.permissao_escrita?.roles_permitidas || []).includes('PCM') ? 'checked' : ''}
                               onchange="atualizarPermissaoEscritaRoles('${campoId}', 'PCM', this.checked)">
                        <label class="form-check-label" for="prop-permissao-escrita-role-pcm">PCM</label>
                    </div>
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" id="prop-permissao-escrita-role-gestor" 
                               ${(campo.permissao_escrita?.roles_permitidas || []).includes('GESTOR') ? 'checked' : ''}
                               onchange="atualizarPermissaoEscritaRoles('${campoId}', 'GESTOR', this.checked)">
                        <label class="form-check-label" for="prop-permissao-escrita-role-gestor">GESTOR</label>
                    </div>
                    <small class="text-muted">Selecione as roles que podem editar este campo. Deixe vazio para permitir todas as roles (apenas verifica permissão RBAC).</small>
                </div>
            </div>
            
            <hr>
            <h6>Auditoria</h6>
            <div class="mb-3">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="prop-audit-trackChanges" 
                           ${audit.trackChanges !== false ? 'checked' : ''}
                           onchange="atualizarAuditCampo('${campoId}', 'trackChanges', this.checked)">
                    <label class="form-check-label" for="prop-audit-trackChanges">
                        Rastrear Alterações
                    </label>
                </div>
                <small class="text-muted">Registrar histórico de alterações do campo</small>
            </div>
            <div class="mb-3">
                <label class="form-label">Imutável Após Status</label>
                <input type="text" class="form-control form-control-sm" id="prop-audit-immutableAfter" 
                       value="${(audit.immutableAfter || []).join(', ')}"
                       placeholder="ENCERRADA, ARQUIVADA"
                       onchange="atualizarAuditCampo('${campoId}', 'immutableAfter', this.value.split(',').map(s => s.trim()).filter(s => s))">
                <small class="text-muted">Status após os quais o campo não pode ser editado (separados por vírgula)</small>
            </div>
        `;
        
        // Remover seleção anterior
        document.querySelectorAll('.form-builder-campo-selecionado').forEach(el => {
            el.classList.remove('form-builder-campo-selecionado');
        });
        
        // Adicionar seleção atual
        const campoElement = document.querySelector(`[data-campo-id="${campoId}"]`);
        if (campoElement) {
            campoElement.classList.add('form-builder-campo-selecionado');
        }
    }
    
    renderizarListaCondicoes(condicoes, campoId, tipo) {
        if (!condicoes || condicoes.length === 0) {
            return '<p class="text-muted small mb-0">Nenhuma condição configurada</p>';
        }
        
        return condicoes.map((cond, index) => `
            <div class="card mb-2" id="cond-${tipo}-${campoId}-${index}">
                <div class="card-body p-2">
                    <div class="mb-2">
                        <label class="form-label small">Condição (if)</label>
                        <input type="text" class="form-control form-control-sm" 
                               value="${cond.if || ''}"
                               placeholder="Ex: os.status in ['EM_EXECUCAO']"
                               onchange="atualizarCondicao('${campoId}', '${tipo}', ${index}, 'if', this.value)">
                    </div>
                    ${tipo === 'requiredWhen' ? `
                        <div class="mb-2">
                            <label class="form-label small">Mensagem</label>
                            <input type="text" class="form-control form-control-sm" 
                                   value="${cond.message || ''}"
                                   placeholder="Este campo é obrigatório"
                                   onchange="atualizarCondicao('${campoId}', '${tipo}', ${index}, 'message', this.value)">
                        </div>
                    ` : ''}
                    ${tipo === 'editableWhen' ? `
                        <div class="mb-2">
                            <label class="form-label small">Roles</label>
                            <input type="text" class="form-control form-control-sm" 
                                   value="${(cond.roles || []).join(', ')}"
                                   placeholder="PCM, SUPERVISOR"
                                   onchange="atualizarCondicao('${campoId}', '${tipo}', ${index}, 'roles', this.value.split(',').map(s => s.trim()).filter(s => s))">
                        </div>
                    ` : ''}
                    <button type="button" class="btn btn-sm btn-danger" onclick="removerCondicao('${campoId}', '${tipo}', ${index})">
                        <i data-feather="trash-2"></i> Remover
                    </button>
                </div>
            </div>
        `).join('');
    }
    
    renderizarPropriedadesCabecalhoOS(campo, campoId) {
        const painel = document.getElementById('painel-propriedades');
        if (!painel) return;
        
        // Inicializar config e layout se não existirem
        if (!campo.config) campo.config = {};
        if (!campo.layout) campo.layout = {};
        
        const config = campo.config;
        const layout = campo.layout;
        
        // Valores padrão
        const showLogo = config.showLogo !== undefined ? config.showLogo : true;
        const showProgramName = config.showProgramName !== undefined ? config.showProgramName : true;
        const showUnit = config.showUnit !== undefined ? config.showUnit : true;
        const showAddress = config.showAddress !== undefined ? config.showAddress : false;
        const showDocumentCode = config.showDocumentCode !== undefined ? config.showDocumentCode : true;
        const codigoDocumento = config.codigoDocumento || 'RSGM078/SIF2960';
        const showRegulatory = config.showRegulatory !== undefined ? config.showRegulatory : true;
        const showRevision = config.showRevision !== undefined ? config.showRevision : true;
        const showPageCounter = config.showPageCounter !== undefined ? config.showPageCounter : true;
        const showOsNumber = config.showOsNumber !== undefined ? config.showOsNumber : true;
        const showOsType = config.showOsType !== undefined ? config.showOsType : true;
        const showIssueDate = config.showIssueDate !== undefined ? config.showIssueDate : true;
        
        const variant = layout.variant || 'print_like';
        const columns = layout.columns || 3;
        const showBorders = layout.showBorders !== undefined ? layout.showBorders : true;
        
        painel.innerHTML = `
            <h6>Propriedades do Cabeçalho</h6>
            <div class="mb-3">
                <label class="form-label">ID</label>
                <input type="text" class="form-control form-control-sm" value="${campo.id}" readonly>
            </div>
            <div class="mb-3">
                <label class="form-label">Label *</label>
                <input type="text" class="form-control form-control-sm" id="prop-label" value="${campo.label || 'Cabeçalho da Ordem de Serviço'}" 
                       onchange="atualizarPropriedadeCampo('${campoId}', 'label', this.value)">
            </div>
            <small class="text-muted d-block mb-3">Bloco institucional/documental (logo, unidade, códigos, revisão, OS). Preenchimento automático.</small>
            
            <hr>
            <h6>Exibir/Ocultar Elementos</h6>
            
            <div class="mb-2">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="prop-show-logo" 
                           ${showLogo ? 'checked' : ''}
                           onchange="atualizarConfigCabecalho('${campoId}', 'showLogo', this.checked)">
                    <label class="form-check-label" for="prop-show-logo">Logo</label>
                </div>
            </div>
            
            <div class="mb-2">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="prop-show-program-name" 
                           ${showProgramName ? 'checked' : ''}
                           onchange="atualizarConfigCabecalho('${campoId}', 'showProgramName', this.checked)">
                    <label class="form-check-label" for="prop-show-program-name">Nome do Programa</label>
                </div>
            </div>
            
            <div class="mb-2">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="prop-show-unit" 
                           ${showUnit ? 'checked' : ''}
                           onchange="atualizarConfigCabecalho('${campoId}', 'showUnit', this.checked)">
                    <label class="form-check-label" for="prop-show-unit">Unidade/Planta</label>
                </div>
            </div>
            
            <div class="mb-2">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="prop-show-address" 
                           ${showAddress ? 'checked' : ''}
                           onchange="atualizarConfigCabecalho('${campoId}', 'showAddress', this.checked)">
                    <label class="form-check-label" for="prop-show-address">Endereço</label>
                </div>
            </div>
            
            <div class="mb-3">
                <label class="form-label">Endereço</label>
                <input type="text" class="form-control form-control-sm" id="prop-address" 
                       value="${config.address || ''}"
                       placeholder="Ex: Rua Exemplo, 123 - Bairro - Cidade/UF"
                       onchange="atualizarConfigCabecalho('${campoId}', 'address', this.value)">
                <small class="text-muted">Duplo clique no endereço no cabeçalho para editar rapidamente</small>
            </div>
            
            <div class="mb-2">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="prop-show-document-code" 
                           ${showDocumentCode ? 'checked' : ''}
                           onchange="atualizarConfigCabecalho('${campoId}', 'showDocumentCode', this.checked)">
                    <label class="form-check-label" for="prop-show-document-code">Código do Documento</label>
                </div>
            </div>
            
            <div class="mb-3">
                <label class="form-label">Código do Documento</label>
                <input type="text" class="form-control form-control-sm" id="prop-codigo-documento" 
                       value="${codigoDocumento}"
                       placeholder="Ex: RSGM078/SIF2960"
                       onchange="atualizarConfigCabecalho('${campoId}', 'codigoDocumento', this.value)">
                <small class="text-muted">Duplo clique no código no cabeçalho para editar rapidamente</small>
            </div>
            
            <div class="mb-2">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="prop-show-regulatory" 
                           ${showRegulatory ? 'checked' : ''}
                           onchange="atualizarConfigCabecalho('${campoId}', 'showRegulatory', this.checked)">
                    <label class="form-check-label" for="prop-show-regulatory">Órgão Fiscalizador</label>
                </div>
            </div>
            
            <div class="mb-2">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="prop-show-revision" 
                           ${showRevision ? 'checked' : ''}
                           onchange="atualizarConfigCabecalho('${campoId}', 'showRevision', this.checked)">
                    <label class="form-check-label" for="prop-show-revision">Revisão (número e data)</label>
                </div>
            </div>
            
            <div class="mb-2">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="prop-show-page-counter" 
                           ${showPageCounter ? 'checked' : ''}
                           onchange="atualizarConfigCabecalho('${campoId}', 'showPageCounter', this.checked)">
                    <label class="form-check-label" for="prop-show-page-counter">Contador de Página (X de Y)</label>
                </div>
            </div>
            
            <div class="mb-2">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="prop-show-os-number" 
                           ${showOsNumber ? 'checked' : ''}
                           onchange="atualizarConfigCabecalho('${campoId}', 'showOsNumber', this.checked)">
                    <label class="form-check-label" for="prop-show-os-number">Número da OS</label>
                </div>
            </div>
            
            <div class="mb-2">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="prop-show-os-type" 
                           ${showOsType ? 'checked' : ''}
                           onchange="atualizarConfigCabecalho('${campoId}', 'showOsType', this.checked)">
                    <label class="form-check-label" for="prop-show-os-type">Tipo da OS</label>
                </div>
            </div>
            
            <div class="mb-3">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="prop-show-issue-date" 
                           ${showIssueDate ? 'checked' : ''}
                           onchange="atualizarConfigCabecalho('${campoId}', 'showIssueDate', this.checked)">
                    <label class="form-check-label" for="prop-show-issue-date">Data de Emissão da OS</label>
                </div>
            </div>
            
            <hr>
            <h6>Layout</h6>
            
            <div class="mb-3">
                <label class="form-label">Variante</label>
                <select class="form-select form-select-sm" id="prop-layout-variant" 
                        onchange="atualizarLayoutCabecalho('${campoId}', 'variant', this.value)">
                    <option value="print_like" ${variant === 'print_like' ? 'selected' : ''}>Print-like (impresso)</option>
                    <option value="compact" ${variant === 'compact' ? 'selected' : ''}>Compacto</option>
                </select>
                <small class="text-muted">Estilo visual do cabeçalho</small>
            </div>
            
            <div class="mb-3">
                <label class="form-label">Colunas</label>
                <select class="form-select form-select-sm" id="prop-layout-columns" 
                        onchange="atualizarLayoutCabecalho('${campoId}', 'columns', parseInt(this.value))">
                    <option value="2" ${columns === 2 ? 'selected' : ''}>2 Colunas</option>
                    <option value="3" ${columns === 3 ? 'selected' : ''}>3 Colunas</option>
                </select>
                <small class="text-muted">Número de colunas no layout</small>
            </div>
            
            <div class="mb-3">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="prop-layout-borders" 
                           ${showBorders ? 'checked' : ''}
                           onchange="atualizarLayoutCabecalho('${campoId}', 'showBorders', this.checked)">
                    <label class="form-check-label" for="prop-layout-borders">Mostrar Bordas</label>
                </div>
            </div>
            
            <hr>
            <h6>Data Bindings</h6>
            <div class="alert alert-info small mb-0">
                <strong>Informação:</strong> Os dados do cabeçalho são preenchidos automaticamente pelo sistema a partir de:
                <ul class="mb-0 mt-2 small">
                    <li><strong>Empresa:</strong> Logo, nome</li>
                    <li><strong>Unidade:</strong> Nome, endereço</li>
                    <li><strong>Programa:</strong> Código, órgão fiscalizador, revisão</li>
                    <li><strong>OS:</strong> Número, tipo, data de emissão</li>
                </ul>
                <small class="d-block mt-2">Os bindings são resolvidos no backend durante a renderização.</small>
            </div>
        `;
        
        // Remover seleção anterior
        document.querySelectorAll('.form-builder-campo-selecionado').forEach(el => {
            el.classList.remove('form-builder-campo-selecionado');
        });
        
        // Adicionar seleção atual
        const campoElement = document.querySelector(`[data-campo-id="${campoId}"]`);
        if (campoElement) {
            campoElement.classList.add('form-builder-campo-selecionado');
        }
    }
    
    renderizarPropriedadesSolicitante(campo, campoId) {
        const painel = document.getElementById('painel-propriedades');
        if (!painel) return;
        
        // Inicializar config e layout se não existirem
        if (!campo.config) campo.config = {};
        if (!campo.layout) campo.layout = { columns: 2, columnSizes: [6, 6], compact: false };
        
        const config = campo.config;
        const layout = campo.layout;
        
        // Valores de layout
        const numColunas = Math.max(1, Math.min(4, layout.columns || 2));
        const columnSizes = layout.columnSizes && layout.columnSizes.length === numColunas ? 
            layout.columnSizes : this.calcularTamanhosPadrao(numColunas);
        const compact = layout.compact || false;
        
        // Valores padrão
        const showNome = config.showNome !== undefined ? config.showNome : true;
        const showEmail = config.showEmail !== undefined ? config.showEmail : true;
        const showUnidade = config.showUnidade !== undefined ? config.showUnidade : true;
        const showSetor = config.showSetor !== undefined ? config.showSetor : false;
        const showTelefone = config.showTelefone !== undefined ? config.showTelefone : false;
        const showDataCriacao = config.showDataCriacao !== undefined ? config.showDataCriacao : true;
        const showNumeroOS = config.showNumeroOS !== undefined ? config.showNumeroOS : true;
        const showAtivo = config.showAtivo !== undefined ? config.showAtivo : true;
        const showPrioridade = config.showPrioridade !== undefined ? config.showPrioridade : true;
        const showPrazoTermino = config.showPrazoTermino !== undefined ? config.showPrazoTermino : true;
        const showSetorOS = config.showSetorOS !== undefined ? config.showSetorOS : true;
        
        painel.innerHTML = `
            <h6>Propriedades do Solicitante</h6>
            <div class="mb-3">
                <label class="form-label">ID</label>
                <input type="text" class="form-control form-control-sm" value="${campo.id}" readonly>
            </div>
            <div class="mb-3">
                <label class="form-label">Label *</label>
                <input type="text" class="form-control form-control-sm" id="prop-label" value="${campo.label || 'Solicitante'}" 
                       onchange="atualizarPropriedadeCampo('${campoId}', 'label', this.value)">
            </div>
            <small class="text-muted d-block mb-3">Bloco informativo que exibe dados do solicitante e informações da nova ordem de serviço. Preenchimento automático a partir da OS.</small>
            
            <hr>
            <h6>Informações da Nova Ordem de Serviço</h6>
            
            <div class="mb-2">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="prop-show-numero-os" 
                           ${showNumeroOS ? 'checked' : ''}
                           onchange="atualizarConfigSolicitante('${campoId}', 'showNumeroOS', this.checked)">
                    <label class="form-check-label" for="prop-show-numero-os">Número da OS</label>
                </div>
            </div>
            
            <div class="mb-2">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="prop-show-data-criacao" 
                           ${showDataCriacao ? 'checked' : ''}
                           onchange="atualizarConfigSolicitante('${campoId}', 'showDataCriacao', this.checked)">
                    <label class="form-check-label" for="prop-show-data-criacao">Data de Criação do Chamado</label>
                </div>
            </div>
            
            <div class="mb-2">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="prop-show-ativo" 
                           ${showAtivo ? 'checked' : ''}
                           onchange="atualizarConfigSolicitante('${campoId}', 'showAtivo', this.checked)">
                    <label class="form-check-label" for="prop-show-ativo">Ativo</label>
                </div>
            </div>
            
            <div class="mb-2">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="prop-show-prioridade" 
                           ${showPrioridade ? 'checked' : ''}
                           onchange="atualizarConfigSolicitante('${campoId}', 'showPrioridade', this.checked)">
                    <label class="form-check-label" for="prop-show-prioridade">Prioridade</label>
                </div>
            </div>
            
            <div class="mb-2">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="prop-show-prazo-termino" 
                           ${showPrazoTermino ? 'checked' : ''}
                           onchange="atualizarConfigSolicitante('${campoId}', 'showPrazoTermino', this.checked)">
                    <label class="form-check-label" for="prop-show-prazo-termino">Prazo de Término</label>
                </div>
            </div>
            
            <div class="mb-3">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="prop-show-setor-os" 
                           ${showSetorOS ? 'checked' : ''}
                           onchange="atualizarConfigSolicitante('${campoId}', 'showSetorOS', this.checked)">
                    <label class="form-check-label" for="prop-show-setor-os">Setor</label>
                </div>
            </div>
            
            <hr>
            <h6>Informações do Solicitante</h6>
            
            <div class="mb-2">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="prop-show-nome" 
                           ${showNome ? 'checked' : ''}
                           onchange="atualizarConfigSolicitante('${campoId}', 'showNome', this.checked)">
                    <label class="form-check-label" for="prop-show-nome">Nome</label>
                </div>
            </div>
            
            <div class="mb-2">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="prop-show-email" 
                           ${showEmail ? 'checked' : ''}
                           onchange="atualizarConfigSolicitante('${campoId}', 'showEmail', this.checked)">
                    <label class="form-check-label" for="prop-show-email">Email</label>
                </div>
            </div>
            
            <div class="mb-2">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="prop-show-unidade" 
                           ${showUnidade ? 'checked' : ''}
                           onchange="atualizarConfigSolicitante('${campoId}', 'showUnidade', this.checked)">
                    <label class="form-check-label" for="prop-show-unidade">Unidade</label>
                </div>
            </div>
            
            <div class="mb-2">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="prop-show-setor" 
                           ${showSetor ? 'checked' : ''}
                           onchange="atualizarConfigSolicitante('${campoId}', 'showSetor', this.checked)">
                    <label class="form-check-label" for="prop-show-setor">Setor</label>
                </div>
            </div>
            
            <div class="mb-3">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="prop-show-telefone" 
                           ${showTelefone ? 'checked' : ''}
                           onchange="atualizarConfigSolicitante('${campoId}', 'showTelefone', this.checked)">
                    <label class="form-check-label" for="prop-show-telefone">Telefone</label>
                </div>
            </div>
            
            <hr>
            <h6>Layout e Colunas</h6>
            
            <div class="mb-3">
                <label class="form-label">Número de Colunas</label>
                <select class="form-select form-select-sm" id="prop-layout-columns" 
                        onchange="atualizarLayoutSolicitante('${campoId}', 'columns', parseInt(this.value))">
                    <option value="1" ${numColunas === 1 ? 'selected' : ''}>1 coluna</option>
                    <option value="2" ${numColunas === 2 ? 'selected' : ''}>2 colunas</option>
                    <option value="3" ${numColunas === 3 ? 'selected' : ''}>3 colunas</option>
                    <option value="4" ${numColunas === 4 ? 'selected' : ''}>4 colunas</option>
                </select>
                <small class="text-muted">Selecione quantas colunas deseja exibir os campos</small>
            </div>
            
            <div class="mb-3" id="prop-column-sizes-container">
                <label class="form-label">Tamanho das Colunas (Bootstrap)</label>
                ${columnSizes.map((size, index) => `
                    <div class="input-group input-group-sm mb-2">
                        <span class="input-group-text">Coluna ${index + 1}</span>
                        <input type="number" class="form-control" min="1" max="12" 
                               value="${size}" id="prop-column-size-${index}"
                               onchange="atualizarTamanhoColunaSolicitante('${campoId}', ${index}, parseInt(this.value))">
                        <span class="input-group-text">/ 12</span>
                    </div>
                `).join('')}
                <small class="text-muted">Ajuste o tamanho de cada coluna (a soma deve ser 12)</small>
                <div class="alert alert-warning small mt-2 mb-0" id="prop-column-sum-warning" style="display: none;">
                    <strong>Atenção:</strong> A soma dos tamanhos deve ser igual a 12!
                </div>
            </div>
            
            <div class="mb-3">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="prop-layout-compact" 
                           ${compact ? 'checked' : ''}
                           onchange="atualizarLayoutSolicitante('${campoId}', 'compact', this.checked)">
                    <label class="form-check-label" for="prop-layout-compact">Modo Compacto</label>
                </div>
                <small class="text-muted">Reduz padding e margens para ocupar menos espaço</small>
            </div>
            
            <hr>
            <h6>Data Bindings</h6>
            <div class="alert alert-info small mb-0">
                <strong>Informação:</strong> Os dados são preenchidos automaticamente pelo sistema a partir da OS:
                <ul class="mb-0 mt-2 small">
                    <li><strong>Nova Ordem de Serviço:</strong> os.numero_os, os.data_solicitacao, os.ativo_rel.nome, os.prioridade, os.data_fim, os.setor.nome</li>
                    <li><strong>Solicitante:</strong> os.solicitante.nome, os.solicitante.email, os.solicitante.unidade, etc.</li>
                </ul>
                <small class="d-block mt-2">Os bindings são resolvidos no backend durante a renderização.</small>
            </div>
        `;
        
        // Remover seleção anterior
        document.querySelectorAll('.form-builder-campo-selecionado').forEach(el => {
            el.classList.remove('form-builder-campo-selecionado');
        });
        
        // Adicionar seleção atual
        const campoElement = document.querySelector(`[data-campo-id="${campoId}"]`);
        if (campoElement) {
            campoElement.classList.add('form-builder-campo-selecionado');
        }
    }
    
    renderizarPropriedadesDescricaoSolicitante(campo, campoId) {
        const painel = document.getElementById('painel-propriedades');
        if (!painel) return;
        
        // Inicializar config e validation se não existirem
        if (!campo.config) campo.config = {};
        if (!campo.validation) campo.validation = {};
        
        const config = campo.config;
        const validation = campo.validation;
        
        // Valores padrão
        const rows = config.rows || 4;
        const placeholder = config.placeholder || 'Descreva o problema encontrado...';
        const maxLength = config.maxLength || null;
        const obrigatorio = campo.obrigatorio || validation.required || true; // Padrão: obrigatório
        
        painel.innerHTML = `
            <h6>Propriedades da Descrição do Solicitante</h6>
            <div class="mb-3">
                <label class="form-label">ID</label>
                <input type="text" class="form-control form-control-sm" value="${campo.id}" readonly>
            </div>
            <div class="mb-3">
                <label class="form-label">Label *</label>
                <input type="text" class="form-control form-control-sm" id="prop-label" value="${campo.label || 'Descrição do Problema'}" 
                       onchange="atualizarPropriedadeCampo('${campoId}', 'label', this.value)">
            </div>
            <small class="text-muted d-block mb-3">Campo de texto (textarea) para coletar a descrição do problema ao criar a ordem de serviço. Os dados são salvos em os.descricao_problema.</small>
            
            <hr>
            <h6>Configurações do Campo</h6>
            
            <div class="mb-3">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="prop-validation-required" 
                           ${obrigatorio ? 'checked' : ''}
                           onchange="atualizarValidationCampo('${campoId}', 'required', this.checked); atualizarPropriedadeCampo('${campoId}', 'obrigatorio', this.checked)">
                    <label class="form-check-label" for="prop-validation-required">
                        Campo Obrigatório
                    </label>
                </div>
                <small class="text-muted">Se marcado, o solicitante deve preencher este campo ao criar a OS</small>
            </div>
            
            <div class="mb-3">
                <label class="form-label">Número de Linhas</label>
                <input type="number" class="form-control form-control-sm" id="prop-rows" 
                       value="${rows}" min="2" max="20"
                       onchange="atualizarConfigDescricaoSolicitante('${campoId}', 'rows', parseInt(this.value))">
                <small class="text-muted">Altura inicial do campo de texto (2-20 linhas)</small>
            </div>
            
            <div class="mb-3">
                <label class="form-label">Placeholder</label>
                <input type="text" class="form-control form-control-sm" id="prop-placeholder" 
                       value="${placeholder}"
                       placeholder="Ex: Descreva o problema encontrado..."
                       onchange="atualizarConfigDescricaoSolicitante('${campoId}', 'placeholder', this.value)">
                <small class="text-muted">Texto de exemplo exibido quando o campo está vazio</small>
            </div>
            
            <div class="mb-3">
                <label class="form-label">Tamanho Máximo (caracteres)</label>
                <input type="number" class="form-control form-control-sm" id="prop-maxLength" 
                       value="${maxLength || ''}"
                       placeholder="Ex: 1000 (deixe vazio para sem limite)"
                       min="1"
                       onchange="atualizarConfigDescricaoSolicitante('${campoId}', 'maxLength', this.value ? parseInt(this.value) : null)">
                <small class="text-muted">Limite de caracteres (deixe vazio para sem limite)</small>
            </div>
            
            <hr>
            <h6>Data Binding</h6>
            <div class="alert alert-info small mb-0">
                <strong>Informação:</strong> Este campo está vinculado ao campo <code>descricao_problema</code> da OS:
                <ul class="mb-0 mt-2 small">
                    <li><strong>Binding:</strong> os.descricao_problema</li>
                    <li><strong>Modo:</strong> Input (editável pelo usuário)</li>
                    <li><strong>Uso:</strong> Coleta a descrição do problema ao criar a OS</li>
                </ul>
                <small class="d-block mt-2">O valor preenchido será salvo automaticamente na OS.</small>
            </div>
        `;
        
        // Remover seleção anterior
        document.querySelectorAll('.form-builder-campo-selecionado').forEach(el => {
            el.classList.remove('form-builder-campo-selecionado');
        });
        
        // Adicionar seleção atual
        const campoElement = document.querySelector(`[data-campo-id="${campoId}"]`);
        if (campoElement) {
            campoElement.classList.add('form-builder-campo-selecionado');
        }
    }
    
    renderizarPropriedadesDescricaoTecnico(campo, campoId) {
        const painel = document.getElementById('painel-propriedades');
        if (!painel) return;
        
        // Inicializar config e validation se não existirem
        if (!campo.config) campo.config = {};
        if (!campo.validation) campo.validation = {};
        
        const config = campo.config;
        const validation = campo.validation;
        
        // Valores padrão
        const rows = config.rows || 6;
        const placeholder = config.placeholder || 'Descreva as ocorrências encontradas durante o atendimento...';
        const maxLength = config.maxLength || 5000;
        const obrigatorio = campo.obrigatorio || validation.required || false; // Padrão: opcional
        const permiteEdicaoTecnico = config.permite_edicao_tecnico !== undefined ? config.permite_edicao_tecnico : true;
        const permiteEdicaoHierarquia = config.permite_edicao_hierarquia_acima !== undefined ? config.permite_edicao_hierarquia_acima : true;
        
        painel.innerHTML = `
            <h6>Propriedades da Descrição do Técnico</h6>
            <div class="mb-3">
                <label class="form-label">ID</label>
                <input type="text" class="form-control form-control-sm" value="${campo.id}" readonly>
            </div>
            <div class="mb-3">
                <label class="form-label">Label *</label>
                <input type="text" class="form-control form-control-sm" id="prop-label" value="${campo.label || 'Descrição das Ocorrências'}" 
                       onchange="atualizarPropriedadeCampo('${campoId}', 'label', this.value)">
            </div>
            <small class="text-muted d-block mb-3">Campo de texto (textarea) para o técnico descrever ocorrências durante o atendimento. Apenas técnico atribuído e hierarquia acima podem editar.</small>
            
            <hr>
            <h6>Configurações do Campo</h6>
            
            <div class="mb-3">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="prop-validation-required" 
                           ${obrigatorio ? 'checked' : ''}
                           onchange="atualizarValidationCampo('${campoId}', 'required', this.checked); atualizarPropriedadeCampo('${campoId}', 'obrigatorio', this.checked)">
                    <label class="form-check-label" for="prop-validation-required">
                        Campo Obrigatório
                    </label>
                </div>
                <small class="text-muted">Se marcado, o técnico deve preencher este campo ao atender a OS</small>
            </div>
            
            <div class="mb-3">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="prop-permite-edicao-tecnico" 
                           ${permiteEdicaoTecnico ? 'checked' : ''}
                           onchange="atualizarConfigDescricaoTecnico('${campoId}', 'permite_edicao_tecnico', this.checked)">
                    <label class="form-check-label" for="prop-permite-edicao-tecnico">
                        Permite Edição por Técnico
                    </label>
                </div>
                <small class="text-muted">Se marcado, o técnico atribuído à OS pode editar este campo</small>
            </div>
            
            <div class="mb-3">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="prop-permite-edicao-hierarquia" 
                           ${permiteEdicaoHierarquia ? 'checked' : ''}
                           onchange="atualizarConfigDescricaoTecnico('${campoId}', 'permite_edicao_hierarquia_acima', this.checked)">
                    <label class="form-check-label" for="prop-permite-edicao-hierarquia">
                        Permite Edição por Hierarquia Acima
                    </label>
                </div>
                <small class="text-muted">Se marcado, gestores, supervisores e líderes podem editar este campo</small>
            </div>
            
            <div class="mb-3">
                <label class="form-label">Número de Linhas</label>
                <input type="number" class="form-control form-control-sm" id="prop-rows" 
                       value="${rows}" min="2" max="20"
                       onchange="atualizarConfigDescricaoTecnico('${campoId}', 'rows', parseInt(this.value))">
                <small class="text-muted">Altura inicial do campo de texto (2-20 linhas)</small>
            </div>
            
            <div class="mb-3">
                <label class="form-label">Placeholder</label>
                <input type="text" class="form-control form-control-sm" id="prop-placeholder" 
                       value="${placeholder}"
                       placeholder="Ex: Descreva as ocorrências encontradas..."
                       onchange="atualizarConfigDescricaoTecnico('${campoId}', 'placeholder', this.value)">
                <small class="text-muted">Texto de exemplo exibido quando o campo está vazio</small>
            </div>
            
            <div class="mb-3">
                <label class="form-label">Tamanho Máximo (caracteres)</label>
                <input type="number" class="form-control form-control-sm" id="prop-maxLength" 
                       value="${maxLength || ''}"
                       placeholder="Ex: 5000"
                       min="1"
                       onchange="atualizarConfigDescricaoTecnico('${campoId}', 'maxLength', this.value ? parseInt(this.value) : null)">
                <small class="text-muted">Limite de caracteres (padrão: 5000)</small>
            </div>
            
            <hr>
            <h6>Histórico de Alterações</h6>
            <div class="alert alert-info small mb-0">
                <strong>Informação:</strong> Este campo registra automaticamente todas as alterações:
                <ul class="mb-0 mt-2 small">
                    <li><strong>Rastreamento:</strong> Cada alteração é registrada com data/hora completa</li>
                    <li><strong>Usuário:</strong> Registra quem fez a alteração</li>
                    <li><strong>Visualização:</strong> Ícone de histórico ao lado do campo mostra datas de alterações</li>
                </ul>
                <small class="d-block mt-2">O histórico é armazenado na tabela manutencao_historico_formulario.</small>
            </div>
        `;
        
        // Remover seleção anterior
        document.querySelectorAll('.form-builder-campo-selecionado').forEach(el => {
            el.classList.remove('form-builder-campo-selecionado');
        });
        
        // Adicionar seleção atual
        const campoElement = document.querySelector(`[data-campo-id="${campoId}"]`);
        if (campoElement) {
            campoElement.classList.add('form-builder-campo-selecionado');
        }
    }
    
    adicionarSecao() {
        const secaoId = `secao_${Date.now()}`;
        const novaSecao = {
            id: secaoId,
            titulo: '',
            ordem: (this.schema.secoes.length + 1),
            campos: []
        };
        
        this.schema.secoes.push(novaSecao);
        this.renderizar();
    }
    
    removerSecao(secaoId) {
        const secao = this.schema.secoes.find(s => s.id === secaoId);
        if (secao && secao.campos) {
            // Remover campos da seção
            secao.campos.forEach(campoId => {
                this.removerCampo(campoId);
            });
        }
        
        this.schema.secoes = this.schema.secoes.filter(s => s.id !== secaoId);
        this.renderizar();
    }
    
    atualizarTituloSecao(secaoId, novoTitulo) {
        const secao = this.schema.secoes.find(s => s.id === secaoId);
        if (secao) {
            secao.titulo = novoTitulo;
        }
    }
    
    removerCampo(campoId) {
        this.schema.campos = this.schema.campos.filter(c => c.id !== campoId);
        this.renderizar();
    }
    
    moverCampo(campoId, direcao) {
        // Encontrar a seção que contém o campo
        let secaoEncontrada = null;
        let indiceCampo = -1;
        
        for (const secao of this.schema.secoes) {
            if (secao.campos && secao.campos.includes(campoId)) {
                secaoEncontrada = secao;
                indiceCampo = secao.campos.indexOf(campoId);
                break;
            }
        }
        
        if (!secaoEncontrada || indiceCampo === -1) {
            formBuilderWarn('[FormBuilder] Campo não encontrado em nenhuma seção:', campoId);
            return;
        }
        
        // Calcular novo índice
        const novoIndice = direcao === 'cima' ? indiceCampo - 1 : indiceCampo + 1;
        
        // Verificar limites
        if (novoIndice < 0 || novoIndice >= secaoEncontrada.campos.length) {
            formBuilderLog('[FormBuilder] Movimento inválido:', direcao, 'índice atual:', indiceCampo, 'novo índice:', novoIndice);
            return;
        }
        
        // Mover campo no array
        const campos = secaoEncontrada.campos;
        [campos[indiceCampo], campos[novoIndice]] = [campos[novoIndice], campos[indiceCampo]];
        
        formBuilderLog('[FormBuilder] Campo movido:', campoId, direcao, 'de', indiceCampo, 'para', novoIndice);
        this.renderizar();
        
        // Manter seleção no campo após renderização
        setTimeout(() => {
            this.selecionarCampo(campoId);
        }, 50);
    }
    
    moverSecao(secaoId, direcao) {
        const indiceSecao = this.schema.secoes.findIndex(s => s.id === secaoId);
        
        if (indiceSecao === -1) {
            formBuilderWarn('[FormBuilder] Seção não encontrada:', secaoId);
            return;
        }
        
        // Calcular novo índice
        const novoIndice = direcao === 'cima' ? indiceSecao - 1 : indiceSecao + 1;
        
        // Verificar limites
        if (novoIndice < 0 || novoIndice >= this.schema.secoes.length) {
            formBuilderLog('[FormBuilder] Movimento de seção inválido:', direcao, 'índice atual:', indiceSecao, 'novo índice:', novoIndice);
            return;
        }
        
        // Atualizar ordem nas seções
        const secoes = this.schema.secoes;
        [secoes[indiceSecao], secoes[novoIndice]] = [secoes[novoIndice], secoes[indiceSecao]];
        
        // Atualizar campo ordem para manter consistência
        secoes[indiceSecao].ordem = indiceSecao + 1;
        secoes[novoIndice].ordem = novoIndice + 1;
        
        formBuilderLog('[FormBuilder] Seção movida:', secaoId, direcao, 'de', indiceSecao, 'para', novoIndice);
        this.renderizar();
    }
    
    duplicarCampo(campoId) {
        formBuilderLog('[FormBuilder] duplicarCampo chamado:', campoId);
        
        // Buscar o campo original
        const campoOriginal = this.schema.campos.find(c => c.id === campoId);
        if (!campoOriginal) {
            formBuilderError('[FormBuilder] Campo não encontrado:', campoId);
            return;
        }
        
        // Criar cópia profunda do campo
        const campoDuplicado = JSON.parse(JSON.stringify(campoOriginal));
        
        // Gerar novo ID único
        const novoCampoId = `campo_${Date.now()}_${Math.floor(Math.random() * 10000)}`;
        campoDuplicado.id = novoCampoId;
        
        // Adicionar sufixo ao label
        if (campoDuplicado.label) {
            campoDuplicado.label = campoDuplicado.label + ' (cópia)';
        }
        
        // Encontrar a seção onde o campo está
        let secaoEncontrada = null;
        let indiceOriginal = -1;
        
        for (const secao of this.schema.secoes) {
            if (secao.campos && secao.campos.includes(campoId)) {
                secaoEncontrada = secao;
                indiceOriginal = secao.campos.indexOf(campoId);
                break;
            }
        }
        
        // Adicionar campo duplicado ao array de campos
        this.schema.campos.push(campoDuplicado);
        
        // Inserir na seção logo após o campo original
        if (secaoEncontrada && indiceOriginal >= 0) {
            secaoEncontrada.campos.splice(indiceOriginal + 1, 0, novoCampoId);
            formBuilderLog('[FormBuilder] Campo duplicado inserido na seção:', secaoEncontrada.id, 'no índice:', indiceOriginal + 1);
        } else {
            // Se não encontrou a seção, adicionar à primeira seção
            if (this.schema.secoes.length > 0) {
                const primeiraSecao = this.schema.secoes[0];
                if (!primeiraSecao.campos) {
                    primeiraSecao.campos = [];
                }
                primeiraSecao.campos.push(novoCampoId);
                formBuilderLog('[FormBuilder] Campo duplicado adicionado à primeira seção');
            }
        }
        
        // Renderizar e selecionar o novo campo
        this.renderizar();
        this.selecionarCampo(novoCampoId);
        formBuilderLog('[FormBuilder] Campo duplicado criado com sucesso:', novoCampoId);
    }
    
    validarSchema() {
        const erros = [];
        
        if (!this.schema.layout) {
            erros.push('Layout não definido');
        }
        
        if (!this.schema.campos || this.schema.campos.length === 0) {
            erros.push('Nenhum campo definido');
        }
        
        return erros;
    }
    
    async salvarRascunho() {
        if (!this.templateId) {
            alert('Template deve ser criado primeiro. Use o botão "Novo Template" na listagem.');
            return;
        }
        
        const erros = this.validarSchema();
        if (erros.length > 0) {
            alert('Erros no schema: ' + erros.join(', '));
            return;
        }
        
        try {
            // Atualizar template com schema atual (mas não publica)
            const response = await fetch(`/api/v1/manutencao/templates/${this.templateId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({
                    // Apenas atualizar metadados, schema será salvo na publicação
                    // Por enquanto, apenas validação
                })
            });
            
            if (response.ok) {
                alert('Rascunho salvo! (Schema será salvo ao publicar)');
            } else {
                const error = await response.json();
                alert('Erro ao salvar rascunho: ' + (error.detail || 'Erro desconhecido'));
            }
        } catch (error) {
            console.error('Erro ao salvar rascunho:', error);
            alert('Erro ao salvar rascunho: ' + error.message);
        }
    }
    
    async publicar() {
        const erros = this.validarSchema();
        if (erros.length > 0) {
            alert('Erros no schema: ' + erros.join(', '));
            return;
        }
        
        // Solicitar versão
        const versao = prompt('Digite a versão (ex: 1.0, 1.1, 2.0):');
        if (!versao) {
            return;
        }
        
        try {
            const response = await fetch(`/api/v1/manutencao/templates/${this.templateId}/publicar`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',  // Incluir cookies de sessão
                body: JSON.stringify({
                    versao: versao,
                    schema_json: this.schema  // API espera schema_json (alias)
                })
            });
            
            if (response.ok) {
                alert('Template publicado com sucesso!');
                window.location.href = '/manutencao/templates';
            } else {
                const error = await response.json();
                alert('Erro ao publicar: ' + error.detail);
            }
        } catch (error) {
            console.error('Erro ao publicar template:', error);
            alert('Erro ao publicar template');
        }
    }
}

// Funções auxiliares globais
function adicionarCampoTexto() {
    if (window.editor) {
        const primeiraSecao = window.editor.schema.secoes[0];
        const secaoId = primeiraSecao ? primeiraSecao.id : null;
        window.editor.adicionarCampo('text', { label: 'Campo de Texto' }, secaoId);
    }
}

function adicionarCampoNumero() {
    if (window.editor) {
        const primeiraSecao = window.editor.schema.secoes[0];
        const secaoId = primeiraSecao ? primeiraSecao.id : null;
        window.editor.adicionarCampo('number', { label: 'Campo Numérico' }, secaoId);
    }
}

function adicionarCampoData() {
    if (window.editor) {
        const primeiraSecao = window.editor.schema.secoes[0];
        const secaoId = primeiraSecao ? primeiraSecao.id : null;
        window.editor.adicionarCampo('date', { label: 'Campo de Data' }, secaoId);
    }
}

function adicionarChecklist() {
    if (window.editor) {
        const primeiraSecao = window.editor.schema.secoes[0];
        const secaoId = primeiraSecao ? primeiraSecao.id : null;
        window.editor.adicionarCampo('checklist', { label: 'Checklist' }, secaoId);
    }
}

function adicionarTabela() {
    if (window.editor) {
        const primeiraSecao = window.editor.schema.secoes[0];
        const secaoId = primeiraSecao ? primeiraSecao.id : null;
        window.editor.adicionarCampo('tabela', { label: 'Tabela Repetível' }, secaoId);
    }
}

function atualizarPropriedadeCampo(campoId, propriedade, valor) {
    if (window.editor) {
        const campo = window.editor.schema.campos.find(c => c.id === campoId);
        if (campo) {
            campo[propriedade] = valor;
            window.editor.renderizar();
            window.editor.selecionarCampo(campoId);
        }
    }
}

function atualizarConfigCabecalho(campoId, chave, valor) {
    if (window.editor) {
        const campo = window.editor.schema.campos.find(c => c.id === campoId);
        if (campo && campo.tipo === 'cabecalho_os') {
            if (!campo.config) campo.config = {};
            campo.config[chave] = valor;
            formBuilderLog('[FormBuilder] Config cabeçalho atualizado:', campo.config);
            window.editor.renderizar();
            window.editor.selecionarCampo(campoId);
        }
    }
}

function atualizarLayoutCabecalho(campoId, chave, valor) {
    if (window.editor) {
        const campo = window.editor.schema.campos.find(c => c.id === campoId);
        if (campo && campo.tipo === 'cabecalho_os') {
            if (!campo.layout) campo.layout = {};
            campo.layout[chave] = valor;
            formBuilderLog('[FormBuilder] Layout cabeçalho atualizado:', campo.layout);
            window.editor.renderizar();
            window.editor.selecionarCampo(campoId);
        }
    }
}

function atualizarConfigSolicitante(campoId, chave, valor) {
    if (window.editor) {
        const campo = window.editor.schema.campos.find(c => c.id === campoId);
        if (campo && campo.tipo === 'solicitante') {
            if (!campo.config) campo.config = {};
            campo.config[chave] = valor;
            formBuilderLog('[FormBuilder] Config solicitante atualizado:', campo.config);
            window.editor.renderizar();
            window.editor.selecionarCampo(campoId);
        }
    }
}

function atualizarLayoutSolicitante(campoId, chave, valor) {
    if (window.editor) {
        const campo = window.editor.schema.campos.find(c => c.id === campoId);
        if (campo && campo.tipo === 'solicitante') {
            if (!campo.layout) campo.layout = { columns: 2, columnSizes: [6, 6], compact: false };
            
            if (chave === 'columns') {
                // Atualizar número de colunas e recalcular tamanhos
                const numColunas = Math.max(1, Math.min(4, parseInt(valor) || 2));
                campo.layout.columns = numColunas;
                campo.layout.columnSizes = window.editor.calcularTamanhosPadrao(numColunas);
            } else {
                campo.layout[chave] = valor;
            }
            
            formBuilderLog('[FormBuilder] Layout solicitante atualizado:', campo.layout);
            window.editor.renderizar();
            window.editor.selecionarCampo(campoId);
        }
    }
}

function atualizarTamanhoColunaSolicitante(campoId, colunaIndex, tamanho) {
    if (window.editor) {
        const campo = window.editor.schema.campos.find(c => c.id === campoId);
        if (campo && campo.tipo === 'solicitante') {
            if (!campo.layout) campo.layout = { columns: 2, columnSizes: [6, 6], compact: false };
            if (!campo.layout.columnSizes) {
                campo.layout.columnSizes = window.editor.calcularTamanhosPadrao(campo.layout.columns || 2);
            }
            
            const tamanhoValido = Math.max(1, Math.min(12, parseInt(tamanho) || 1));
            campo.layout.columnSizes[colunaIndex] = tamanhoValido;
            
            // Validar soma
            const soma = campo.layout.columnSizes.reduce((a, b) => a + b, 0);
            const warningEl = document.getElementById('prop-column-sum-warning');
            if (warningEl) {
                if (soma !== 12) {
                    warningEl.style.display = 'block';
                } else {
                    warningEl.style.display = 'none';
                }
            }
            
            formBuilderLog('[FormBuilder] Tamanho coluna solicitante atualizado:', campo.layout.columnSizes);
            window.editor.renderizar();
            window.editor.selecionarCampo(campoId);
        }
    }
}

function atualizarConfigDescricaoSolicitante(campoId, chave, valor) {
    if (window.editor) {
        const campo = window.editor.schema.campos.find(c => c.id === campoId);
        if (campo && campo.tipo === 'descricao_solicitante') {
            if (!campo.config) campo.config = {};
            campo.config[chave] = valor;
            formBuilderLog('[FormBuilder] Config descrição solicitante atualizado:', campo.config);
            window.editor.renderizar();
            window.editor.selecionarCampo(campoId);
        }
    }
}

function atualizarConfigDescricaoTecnico(campoId, chave, valor) {
    if (window.editor) {
        const campo = window.editor.schema.campos.find(c => c.id === campoId);
        if (campo && campo.tipo === 'descricao_tecnico') {
            if (!campo.config) campo.config = {};
            campo.config[chave] = valor;
            formBuilderLog('[FormBuilder] Config descrição técnico atualizado:', campo.config);
            window.editor.renderizar();
            window.editor.selecionarCampo(campoId);
        }
    }
}

function editarCodigoDocumento(elemento) {
    // Tornar o elemento editável ao dar duplo clique
    elemento.contentEditable = 'true';
    elemento.style.backgroundColor = '#fff3cd';
    elemento.style.border = '1px solid #ffc107';
    elemento.style.padding = '2px 4px';
    elemento.style.borderRadius = '3px';
    elemento.focus();
    
    // Selecionar todo o texto
    if (window.getSelection && document.createRange) {
        const range = document.createRange();
        range.selectNodeContents(elemento);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
    }
}

function salvarCodigoDocumento(elemento) {
    // Restaurar estilo quando perder foco
    elemento.contentEditable = 'false';
    elemento.style.backgroundColor = '';
    elemento.style.border = '';
    elemento.style.padding = '';
    elemento.style.borderRadius = '';
    
    // Obter o novo valor
    const novoValor = elemento.textContent.trim();
    const campoId = elemento.dataset.campoId;
    const configKey = elemento.dataset.configKey;
    
    if (campoId && configKey && window.editor) {
        // Atualizar o valor no schema
        const campo = window.editor.schema.campos.find(c => c.id === campoId);
        if (campo && campo.tipo === 'cabecalho_os') {
            if (!campo.config) campo.config = {};
            campo.config[configKey] = novoValor;
            formBuilderLog('[FormBuilder] Código documento atualizado:', novoValor);
            
            // Atualizar também o campo no painel de propriedades se existir
            const propInput = document.getElementById('prop-codigo-documento');
            if (propInput) {
                propInput.value = novoValor;
            }
        }
    }
}

function editarProgramName(elemento) {
    // Tornar o elemento editável ao dar duplo clique
    elemento.contentEditable = 'true';
    elemento.style.backgroundColor = '#fff3cd';
    elemento.style.border = '1px solid #ffc107';
    elemento.style.padding = '2px 4px';
    elemento.style.borderRadius = '3px';
    elemento.focus();
    
    // Selecionar todo o texto
    if (window.getSelection && document.createRange) {
        const range = document.createRange();
        range.selectNodeContents(elemento);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
    }
}

function salvarProgramName(elemento) {
    // Restaurar estilo quando perder foco
    elemento.contentEditable = 'false';
    elemento.style.backgroundColor = '';
    elemento.style.border = '';
    elemento.style.padding = '';
    elemento.style.borderRadius = '';
    
    // Obter o novo valor
    const novoValor = elemento.textContent.trim();
    const campoId = elemento.dataset.campoId;
    const configKey = elemento.dataset.configKey;
    
    if (campoId && configKey && window.editor) {
        // Atualizar o valor no schema
        const campo = window.editor.schema.campos.find(c => c.id === campoId);
        if (campo && campo.tipo === 'cabecalho_os') {
            if (!campo.config) campo.config = {};
            campo.config[configKey] = novoValor;
            formBuilderLog('[FormBuilder] Nome do programa atualizado:', novoValor);
        }
    }
}

function editarUnitName(elemento) {
    // Tornar o elemento editável ao dar duplo clique
    elemento.contentEditable = 'true';
    elemento.style.backgroundColor = '#fff3cd';
    elemento.style.border = '1px solid #ffc107';
    elemento.style.padding = '2px 4px';
    elemento.style.borderRadius = '3px';
    elemento.focus();
    
    // Selecionar todo o texto
    if (window.getSelection && document.createRange) {
        const range = document.createRange();
        range.selectNodeContents(elemento);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
    }
}

function salvarUnitName(elemento) {
    // Restaurar estilo quando perder foco
    elemento.contentEditable = 'false';
    elemento.style.backgroundColor = '';
    elemento.style.border = '';
    elemento.style.padding = '';
    elemento.style.borderRadius = '';
    
    // Obter o novo valor
    const novoValor = elemento.textContent.trim();
    const campoId = elemento.dataset.campoId;
    const configKey = elemento.dataset.configKey;
    
    if (campoId && configKey && window.editor) {
        // Atualizar o valor no schema
        const campo = window.editor.schema.campos.find(c => c.id === campoId);
        if (campo && campo.tipo === 'cabecalho_os') {
            if (!campo.config) campo.config = {};
            campo.config[configKey] = novoValor;
            formBuilderLog('[FormBuilder] Nome da unidade atualizado:', novoValor);
        }
    }
}

function editarAddress(elemento) {
    // Tornar o elemento editável ao dar duplo clique
    elemento.contentEditable = 'true';
    elemento.style.backgroundColor = '#fff3cd';
    elemento.style.border = '1px solid #ffc107';
    elemento.style.padding = '2px 4px';
    elemento.style.borderRadius = '3px';
    elemento.focus();
    
    // Selecionar todo o texto
    if (window.getSelection && document.createRange) {
        const range = document.createRange();
        range.selectNodeContents(elemento);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
    }
}

function salvarAddress(elemento) {
    // Restaurar estilo quando perder foco
    elemento.contentEditable = 'false';
    elemento.style.backgroundColor = '';
    elemento.style.border = '';
    elemento.style.padding = '';
    elemento.style.borderRadius = '';
    
    // Obter o novo valor
    const novoValor = elemento.textContent.trim();
    const campoId = elemento.dataset.campoId;
    const configKey = elemento.dataset.configKey;
    
    if (campoId && configKey && window.editor) {
        // Atualizar o valor no schema
        const campo = window.editor.schema.campos.find(c => c.id === campoId);
        if (campo && campo.tipo === 'cabecalho_os') {
            if (!campo.config) campo.config = {};
            campo.config[configKey] = novoValor;
            formBuilderLog('[FormBuilder] Endereço atualizado:', novoValor);
            
            // Atualizar também o campo no painel de propriedades se existir
            const propInput = document.getElementById('prop-address');
            if (propInput) {
                propInput.value = novoValor;
            }
        }
    }
}

function editarOsType(elemento) {
    // Tornar o elemento editável ao dar duplo clique
    elemento.contentEditable = 'true';
    elemento.style.backgroundColor = '#fff3cd';
    elemento.style.border = '1px solid #ffc107';
    elemento.style.padding = '2px 4px';
    elemento.style.borderRadius = '3px';
    elemento.focus();
    
    // Selecionar todo o texto
    if (window.getSelection && document.createRange) {
        const range = document.createRange();
        range.selectNodeContents(elemento);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
    }
}

function salvarOsType(elemento) {
    // Restaurar estilo quando perder foco
    elemento.contentEditable = 'false';
    elemento.style.backgroundColor = '';
    elemento.style.border = '';
    elemento.style.padding = '';
    elemento.style.borderRadius = '';
    
    // Obter o novo valor
    const novoValor = elemento.textContent.trim();
    const campoId = elemento.dataset.campoId;
    const configKey = elemento.dataset.configKey;
    
    if (campoId && configKey && window.editor) {
        // Atualizar o valor no schema
        const campo = window.editor.schema.campos.find(c => c.id === campoId);
        if (campo && campo.tipo === 'cabecalho_os') {
            if (!campo.config) campo.config = {};
            campo.config[configKey] = novoValor;
            formBuilderLog('[FormBuilder] Tipo da OS atualizado:', novoValor);
        }
    }
}

// Funções para atualizar propriedades do schema padrão
function atualizarLayoutCampo(campoId, chave, valor) {
    if (window.editor) {
        const campo = window.editor.schema.campos.find(c => c.id === campoId);
        if (campo) {
            if (!campo.layout) campo.layout = {};
            campo.layout[chave] = valor;
            formBuilderLog('[FormBuilder] Layout atualizado:', campo.layout);
            window.editor.renderizar();
            window.editor.selecionarCampo(campoId);
        }
    }
}

function atualizarDataCampo(campoId, chave, valor) {
    if (window.editor) {
        const campo = window.editor.schema.campos.find(c => c.id === campoId);
        if (campo) {
            if (!campo.data) campo.data = {};
            if (chave === 'binding') {
                campo.data.binding = valor;
            } else {
                campo.data[chave] = valor;
            }
            // Compatibilidade
            if (chave === 'default') {
                campo.valor_padrao = valor;
            }
            formBuilderLog('[FormBuilder] Data atualizado:', campo.data);
            window.editor.renderizar();
            window.editor.selecionarCampo(campoId);
        }
    }
}

function atualizarRenderCampo(campoId, chave, valor) {
    if (window.editor) {
        const campo = window.editor.schema.campos.find(c => c.id === campoId);
        if (campo) {
            if (!campo.render) campo.render = {};
            if (chave === 'format') {
                if (!campo.render.format) campo.render.format = {};
                campo.render.format = { ...campo.render.format, ...valor };
            } else {
                campo.render[chave] = valor;
            }
            formBuilderLog('[FormBuilder] Render atualizado:', campo.render);
            window.editor.renderizar();
            window.editor.selecionarCampo(campoId);
        }
    }
}

function atualizarValidationCampo(campoId, chave, valor) {
    if (window.editor) {
        const campo = window.editor.schema.campos.find(c => c.id === campoId);
        if (campo) {
            if (!campo.validation) campo.validation = {};
            campo.validation[chave] = valor;
            // Compatibilidade
            if (chave === 'required') {
                campo.obrigatorio = valor;
            }
            formBuilderLog('[FormBuilder] Validation atualizado:', campo.validation);
            window.editor.renderizar();
            window.editor.selecionarCampo(campoId);
        }
    }
}

function atualizarPermissionsCampo(campoId, chave, valor) {
    if (window.editor) {
        const campo = window.editor.schema.campos.find(c => c.id === campoId);
        if (campo) {
            if (!campo.permissions) campo.permissions = {};
            campo.permissions[chave] = valor;
            // Compatibilidade
            if (chave === 'visibility') {
                campo.visivel_por_perfil = valor;
            } else if (chave === 'editable') {
                campo.editavel_por_perfil = valor;
            }
            formBuilderLog('[FormBuilder] Permissions atualizado:', campo.permissions);
            window.editor.renderizar();
            window.editor.selecionarCampo(campoId);
        }
    }
}

function atualizarAuditCampo(campoId, chave, valor) {
    if (window.editor) {
        const campo = window.editor.schema.campos.find(c => c.id === campoId);
        if (campo) {
            if (!campo.audit) campo.audit = {};
            campo.audit[chave] = valor;
            formBuilderLog('[FormBuilder] Audit atualizado:', campo.audit);
            window.editor.renderizar();
            window.editor.selecionarCampo(campoId);
        }
    }
}

function togglePermissaoEscritaRBAC(campoId, enabled) {
    if (window.editor) {
        const campo = window.editor.schema.campos.find(c => c.id === campoId);
        if (campo) {
            if (enabled) {
                // Inicializar permissao_escrita se não existir
                if (!campo.permissao_escrita) {
                    campo.permissao_escrita = {
                        permissao_necessaria: null,
                        roles_permitidas: []
                    };
                }
            } else {
                // Remover permissão específica (herda do bloco)
                campo.permissao_escrita = null;
            }
            
            // Mostrar/ocultar painel de configuração
            const configPanel = document.getElementById('prop-permissao-escrita-config');
            if (configPanel) {
                configPanel.style.display = enabled ? 'block' : 'none';
            }
            
            formBuilderLog('[FormBuilder] Permissão escrita RBAC toggled:', campo.permissao_escrita);
            window.editor.renderizar();
            window.editor.selecionarCampo(campoId);
        }
    }
}

function atualizarPermissaoEscritaRBAC(campoId, chave, valor) {
    if (window.editor) {
        const campo = window.editor.schema.campos.find(c => c.id === campoId);
        if (campo) {
            if (!campo.permissao_escrita) {
                campo.permissao_escrita = {
                    permissao_necessaria: null,
                    roles_permitidas: []
                };
            }
            
            // Atualizar chave específica
            if (chave === 'permissao_necessaria') {
                campo.permissao_escrita.permissao_necessaria = valor || null;
            }
            
            formBuilderLog('[FormBuilder] Permissão escrita RBAC atualizada:', campo.permissao_escrita);
            window.editor.renderizar();
            window.editor.selecionarCampo(campoId);
        }
    }
}

function atualizarPermissaoEscritaRoles(campoId, role, enabled) {
    if (window.editor) {
        const campo = window.editor.schema.campos.find(c => c.id === campoId);
        if (campo) {
            if (!campo.permissao_escrita) {
                campo.permissao_escrita = {
                    permissao_necessaria: null,
                    roles_permitidas: []
                };
            }
            
            if (!campo.permissao_escrita.roles_permitidas) {
                campo.permissao_escrita.roles_permitidas = [];
            }
            
            // Adicionar ou remover role
            const roles = campo.permissao_escrita.roles_permitidas;
            if (enabled) {
                if (!roles.includes(role)) {
                    roles.push(role);
                }
            } else {
                const index = roles.indexOf(role);
                if (index > -1) {
                    roles.splice(index, 1);
                }
            }
            
            formBuilderLog('[FormBuilder] Permissão escrita roles atualizada:', campo.permissao_escrita);
            window.editor.renderizar();
            window.editor.selecionarCampo(campoId);
        }
    }
}

// Funções para gerenciar condições
function adicionarCondicaoShowWhen(campoId) {
    if (window.editor) {
        const campo = window.editor.schema.campos.find(c => c.id === campoId);
        if (campo) {
            if (!campo.render) campo.render = {};
            if (!campo.render.showWhen) campo.render.showWhen = [];
            campo.render.showWhen.push({ if: 'always' });
            window.editor.renderizar();
            window.editor.selecionarCampo(campoId);
        }
    }
}

function adicionarCondicaoRequiredWhen(campoId) {
    if (window.editor) {
        const campo = window.editor.schema.campos.find(c => c.id === campoId);
        if (campo) {
            if (!campo.validation) campo.validation = {};
            if (!campo.validation.requiredWhen) campo.validation.requiredWhen = [];
            campo.validation.requiredWhen.push({ if: 'os.status in [\'EM_EXECUCAO\']', message: 'Este campo é obrigatório' });
            window.editor.renderizar();
            window.editor.selecionarCampo(campoId);
        }
    }
}

function adicionarCondicaoEditableWhen(campoId) {
    if (window.editor) {
        const campo = window.editor.schema.campos.find(c => c.id === campoId);
        if (campo) {
            if (!campo.permissions) campo.permissions = {};
            if (!campo.permissions.editableWhen) campo.permissions.editableWhen = [];
            campo.permissions.editableWhen.push({ if: 'os.status in [\'ABERTA\']', roles: ['PCM', 'SUPERVISOR'] });
            window.editor.renderizar();
            window.editor.selecionarCampo(campoId);
        }
    }
}

function atualizarCondicao(campoId, tipo, index, chave, valor) {
    if (window.editor) {
        const campo = window.editor.schema.campos.find(c => c.id === campoId);
        if (campo) {
            let array;
            if (tipo === 'showWhen') {
                if (!campo.render) campo.render = {};
                if (!campo.render.showWhen) campo.render.showWhen = [];
                array = campo.render.showWhen;
            } else if (tipo === 'requiredWhen') {
                if (!campo.validation) campo.validation = {};
                if (!campo.validation.requiredWhen) campo.validation.requiredWhen = [];
                array = campo.validation.requiredWhen;
            } else if (tipo === 'editableWhen') {
                if (!campo.permissions) campo.permissions = {};
                if (!campo.permissions.editableWhen) campo.permissions.editableWhen = [];
                array = campo.permissions.editableWhen;
            }
            
            if (array && array[index]) {
                array[index][chave] = valor;
                window.editor.renderizar();
                window.editor.selecionarCampo(campoId);
            }
        }
    }
}

function removerCondicao(campoId, tipo, index) {
    if (window.editor) {
        const campo = window.editor.schema.campos.find(c => c.id === campoId);
        if (campo) {
            let array;
            if (tipo === 'showWhen') {
                array = campo.render?.showWhen;
            } else if (tipo === 'requiredWhen') {
                array = campo.validation?.requiredWhen;
            } else if (tipo === 'editableWhen') {
                array = campo.permissions?.editableWhen;
            }
            
            if (array && array[index]) {
                array.splice(index, 1);
                window.editor.renderizar();
                window.editor.selecionarCampo(campoId);
            }
        }
    }
}

function atualizarMascaraCampo(campoId, tipoMascara) {
    if (window.editor) {
        const campo = window.editor.schema.campos.find(c => c.id === campoId);
        if (campo) {
            if (!campo.render) campo.render = {};
            if (!campo.render.format) campo.render.format = {};
            
            // Mapear tipos para máscaras
            const mascaras = {
                'cpf': '000.000.000-00',
                'cnpj': '00.000.000/0000-00',
                'telefone': '(00) 00000-0000',
                'cep': '00000-000',
                'data': 'DD/MM/YYYY'
            };
            
            if (tipoMascara === 'custom') {
                // Mostrar campo de máscara customizada
                const customDiv = document.getElementById('prop-render-format-mask-custom');
                if (customDiv) {
                    customDiv.style.display = 'block';
                }
                // Manter máscara atual se existir
            } else if (tipoMascara && mascaras[tipoMascara]) {
                campo.render.format.mask = mascaras[tipoMascara];
                // Ocultar campo customizado
                const customDiv = document.getElementById('prop-render-format-mask-custom');
                if (customDiv) {
                    customDiv.style.display = 'none';
                }
                window.editor.renderizar();
                window.editor.selecionarCampo(campoId);
            } else {
                // Sem máscara
                campo.render.format.mask = null;
                const customDiv = document.getElementById('prop-render-format-mask-custom');
                if (customDiv) {
                    customDiv.style.display = 'none';
                }
                window.editor.renderizar();
                window.editor.selecionarCampo(campoId);
            }
        }
    }
}

function atualizarMascaraCustomizada(campoId, mascara) {
    if (window.editor) {
        const campo = window.editor.schema.campos.find(c => c.id === campoId);
        if (campo) {
            if (!campo.render) campo.render = {};
            if (!campo.render.format) campo.render.format = {};
            campo.render.format.mask = mascara || null;
            formBuilderLog('[FormBuilder] Máscara customizada atualizada:', mascara);
            window.editor.renderizar();
            window.editor.selecionarCampo(campoId);
        }
    }
}

function abrirConfigRegrasStatus() {
    // Abrir modal para configurar regras por status
    // Implementação será feita com modal customizado conforme MAPA_SISTEMA
    alert('Configuração de regras por status será implementada com modal customizado');
    
    // Por enquanto, mostrar estrutura básica
    const regrasPorStatus = window.editor?.schema?.regras_por_status || {};
    console.log('Regras por status atuais:', regrasPorStatus);
}

// ============================================================================
// INICIALIZAÇÃO
// ============================================================================

// Inicializar editor quando DOM estiver pronto
document.addEventListener('DOMContentLoaded', function() {
    // Extrair template_id da URL: /manutencao/templates/{template_id}/editor
    let templateId = null;
    const pathParts = window.location.pathname.split('/');
    const templatesIndex = pathParts.indexOf('templates');
    
    if (templatesIndex !== -1 && pathParts.length > templatesIndex + 1) {
        const idPart = pathParts[templatesIndex + 1];
        // Verificar se é um número válido
        const parsedId = parseInt(idPart, 10);
        if (!isNaN(parsedId) && parsedId > 0) {
            templateId = parsedId;
        }
    }
    
    console.log('Inicializando editor com template_id:', templateId);
    
    // Verificar se o container existe
    const container = document.getElementById('editor-formulario');
    if (!container) {
        console.error('Container editor-formulario não encontrado');
        return;
    }
    
    try {
        // Inicializar editor
        window.editor = new FormBuilderEditor('editor-formulario', templateId);
        
        // Carregar informações do template se tiver ID
        if (templateId) {
            // Carregar nome e status do template para exibir no cabeçalho
            fetch(`/api/v1/manutencao/templates/${templateId}`, {
                credentials: 'include'
            })
            .then(res => res.json())
            .then(template => {
                if (window.editor) {
                    if (template.nome) {
                        window.editor.templateNome = template.nome;
                    }
                    if (template.criado_em) {
                        window.editor.templateCriadoEm = new Date(template.criado_em);
                    }
                    if (template.atualizado_em) {
                        window.editor.templateAtualizadoEm = new Date(template.atualizado_em);
                    }
                    // Versão vem da versao_atual
                    if (template.versao_atual && template.versao_atual.versao) {
                        window.editor.templateVersao = template.versao_atual.versao;
                    } else if (template.versao_atual && template.versao_atual.criado_em) {
                        // Se não tiver versão mas tiver data de criação da versão, usar como data de revisão
                        window.editor.templateAtualizadoEm = new Date(template.versao_atual.criado_em);
                    }
                    // Re-renderizar se houver campos de cabeçalho já criados
                    window.editor.renderizar();
                }
                if (template.nome) {
                    const tituloEl = document.getElementById('templateNomeTitulo');
                    if (tituloEl) tituloEl.textContent = template.nome;
                }
                if (template.status) {
                    const statusEl = document.getElementById('templateStatusBadge');
                    if (statusEl) {
                        statusEl.textContent = template.status.charAt(0).toUpperCase() + template.status.slice(1);
                        statusEl.className = `badge ${template.status === 'publicado' ? 'bg-success' : 'bg-secondary'} ms-2`;
                    }
                }
            })
            .catch(err => console.error('Erro ao carregar dados do template:', err));
        }
        
        // Carregar catálogo de blocos
        carregarCatalogoBlocos();
        
        // Aguardar um pouco para garantir que tudo foi renderizado
        setTimeout(() => {
            if (typeof feather !== 'undefined') {
                feather.replace();
            }
            // Reinicializar drag and drop após renderização
            // Isso garante que tanto os blocos da lateral quanto as áreas de drop estejam prontos
            if (window.editor) {
                window.editor.inicializarDragAndDrop();
            }
        }, 300);
        
        // Listener global de drop como fallback (caso os listeners específicos não funcionem)
        document.addEventListener('drop', (e) => {
            // Verificar se é um drop dentro de uma área de drop do form builder
            const dropZone = e.target.closest('.form-builder-secao-body, .form-builder-drop-zone');
            if (dropZone) {
                formBuilderLog('[FormBuilder] 🎯 Drop global capturado!');
                const secaoId = dropZone.dataset.secaoId || dropZone.closest('[data-secao-id]')?.dataset.secaoId;
                if (secaoId) {
                    e.preventDefault();
                    e.stopPropagation();
                    formBuilderLog('[FormBuilder] Processando drop global na seção:', secaoId);
                    handleDrop(e, secaoId);
                }
            }
        }, { passive: false });
        
        // Listener global de dragover como fallback
        document.addEventListener('dragover', (e) => {
            const dropZone = e.target.closest('.form-builder-secao-body, .form-builder-drop-zone');
            if (dropZone) {
                e.preventDefault();
                e.stopPropagation();
            }
        }, { passive: false });
    } catch (error) {
        console.error('Erro ao inicializar editor:', error);
        if (container) {
            container.innerHTML = '<p class="text-danger">Erro ao inicializar editor. Verifique o console.</p>';
        }
    }
});

function salvarRascunho() {
    if (window.editor) {
        window.editor.salvarRascunho();
    }
}

function publicarTemplate() {
    if (window.editor) {
        window.editor.publicar();
    }
}

async function carregarCatalogoBlocos() {
    try {
        const response = await fetch('/api/v1/manutencao/catalogo/blocos', {
            credentials: 'include'  // Incluir cookies de sessão
        });
        
        if (response.ok) {
            const blocos = await response.json();
            const container = document.getElementById('catalogo-blocos');
            
            if (blocos.length === 0) {
                container.innerHTML = '<p class="text-muted small">Nenhum bloco no catálogo</p>';
                return;
            }
            
            container.innerHTML = blocos.map(bloco => `
                <div class="list-group-item">
                    <strong>${bloco.nome}</strong>
                    <small class="d-block text-muted">${bloco.tipo_bloco}</small>
                    <button class="btn btn-sm btn-primary mt-2" onclick="inserirBlocoCatalogo(${bloco.id})">
                        Inserir
                    </button>
                </div>
            `).join('');
        }
    } catch (error) {
        console.error('Erro ao carregar catálogo:', error);
    }
}

function inserirBlocoCatalogo(blocoId) {
    // Implementar inserção de bloco do catálogo
    alert('Inserir bloco do catálogo (implementação pendente)');
}

// ============================================================================
// FUNÇÕES DE DRAG AND DROP
// ============================================================================

let campoArrastado = null;
let secaoOrigem = null;

function handleDragStart(event, campoId) {
    formBuilderLog('[FormBuilder] handleDragStart - Campo:', campoId);
    campoArrastado = campoId;
    const campoElement = event.target.closest('.form-builder-campo');
    if (campoElement) {
        secaoOrigem = campoElement.dataset.secaoId;
        formBuilderLog('[FormBuilder] handleDragStart - Seção origem:', secaoOrigem);
    } else {
        formBuilderWarn('[FormBuilder] ⚠️ handleDragStart - Campo element não encontrado');
    }
    event.dataTransfer.effectAllowed = 'move';
    const data = {
        tipo: 'mover',
        campo_id: campoId
    };
    event.dataTransfer.setData('text/plain', JSON.stringify(data));
    formBuilderLog('[FormBuilder] handleDragStart - Data transfer:', data);
    
    const campo = event.target.closest('.form-builder-campo');
    if (campo) {
        campo.style.opacity = '0.5';
    }
}

function handleDragOver(event) {
    // CRÍTICO: preventDefault() é necessário para permitir o drop
    event.preventDefault();
    event.stopPropagation();
    
    // Definir dropEffect - usar 'copy' para novos blocos, 'move' para campos existentes
    // Não podemos ler getData() durante dragover, então usamos effectAllowed como referência
    if (event.dataTransfer.effectAllowed === 'copy') {
        event.dataTransfer.dropEffect = 'copy';
    } else if (event.dataTransfer.effectAllowed === 'move') {
        event.dataTransfer.dropEffect = 'move';
    } else {
        event.dataTransfer.dropEffect = 'copy';
    }
    
    // Destacar área de drop
    const dropZone = event.currentTarget;
    const secaoId = dropZone.dataset.secaoId || dropZone.closest('[data-secao-id]')?.dataset.secaoId;
    
    // Evitar logs excessivos - apenas logar quando entrar na área pela primeira vez
    if (!dropZone.classList.contains('drag-over')) {
        formBuilderLog('[FormBuilder] handleDragOver - Entrando na área:', secaoId);
    }
    
    dropZone.classList.add('drag-over');
}

function handleDragLeave(event) {
    // Verificar se realmente saiu da área (não apenas passou por um elemento filho)
    const dropZone = event.currentTarget;
    const relatedTarget = event.relatedTarget;
    
    // Se o relatedTarget ainda está dentro da área de drop, não remover a classe
    if (relatedTarget && dropZone.contains(relatedTarget)) {
        return;
    }
    
    formBuilderLog('[FormBuilder] handleDragLeave - Saindo da área');
    dropZone.classList.remove('drag-over');
}

function handleDrop(event, secaoId) {
    formBuilderLog('[FormBuilder] ========== handleDrop INICIADO ==========');
    formBuilderLog('[FormBuilder] Seção destino:', secaoId);
    formBuilderLog('[FormBuilder] Seção origem:', secaoOrigem);
    
    event.preventDefault();
    event.stopPropagation();
    
    const dropZone = event.currentTarget;
    dropZone.classList.remove('drag-over');
    
    try {
        const dataString = event.dataTransfer.getData('text/plain');
        formBuilderLog('[FormBuilder] Data recebida (string):', dataString);
        
        if (!dataString) {
            formBuilderError('[FormBuilder] ❌ ERRO: Nenhum dado recebido no drop');
            return;
        }
        
        const data = JSON.parse(dataString);
        formBuilderLog('[FormBuilder] Data parseada:', data);
        
        if (!window.editor) {
            formBuilderError('[FormBuilder] ❌ ERRO: window.editor não está disponível');
            return;
        }
        
        if (data.tipo === 'novo') {
            formBuilderLog('[FormBuilder] Criando novo campo do tipo:', data.campo_tipo);
            // Criar novo campo
            let secao = window.editor.schema.secoes.find(s => s.id === secaoId);
            if (!secao) {
                formBuilderLog('[FormBuilder] Seção não existe, criando nova seção:', secaoId);
                // Criar nova seção se não existir
                secao = {
                    id: secaoId,
                    titulo: '',
                    ordem: window.editor.schema.secoes.length + 1,
                    campos: []
                };
                window.editor.schema.secoes.push(secao);
            } else {
                formBuilderLog('[FormBuilder] Seção encontrada:', secao);
            }
            
            // Mapeamento de labels padrão por tipo de campo
            const labelsPadrao = {
                'text': 'Campo de Texto',
                'number': 'Campo Numérico',
                'date': 'Data',
                'hora': 'Hora',
                'datetime': 'Data e Hora',
                'boolean': 'Booleano',
                'select': 'Seleção',
                'checkbox': 'Checkbox',
                'checklist': 'Checklist',
                'tabela': 'Tabela',
                'upload': 'Upload de Arquivo',
                'apontamento_horas': 'Apontamento de Horas',
                'materiais_pecas': 'Materiais/Peças',
                'equipamentos': 'Equipamentos',
                'ativos': 'Ativos',
                'status_final': 'Status Final',
                'seguranca_operacional': 'Segurança Operacional',
                'qsa': 'QSA',
                'solicitante': 'Solicitante',
                'descricao_solicitante': 'Descrição do Solicitante',
                'descricao_tecnico': 'Descrição do Técnico',
                'texto_informativo': 'Texto Informativo',
                'cabecalho_os': 'Cabeçalho da OS'
            };
            
            const labelPadrao = labelsPadrao[data.campo_tipo] || `Novo ${data.campo_tipo}`;
            
            window.editor.adicionarCampo(data.campo_tipo, {
                label: labelPadrao
            }, secaoId);
            formBuilderLog('[FormBuilder] ✅ Campo adicionado com sucesso');
            
        } else if (data.tipo === 'mover') {
            formBuilderLog('[FormBuilder] Movendo campo existente:', data.campo_id);
            // Mover campo existente
            if (data.campo_id && secaoOrigem) {
                formBuilderLog('[FormBuilder] Movendo de', secaoOrigem, 'para', secaoId);
                window.editor.moverCampo(data.campo_id, secaoOrigem, secaoId);
                formBuilderLog('[FormBuilder] ✅ Campo movido com sucesso');
            } else {
                formBuilderWarn('[FormBuilder] ⚠️ Não foi possível mover: campo_id ou secaoOrigem ausente', {
                    campo_id: data.campo_id,
                    secaoOrigem: secaoOrigem
                });
            }
        } else {
            formBuilderWarn('[FormBuilder] ⚠️ Tipo de operação desconhecido:', data.tipo);
        }
        
        // Restaurar opacidade do campo arrastado (apenas se for movimento)
        if (data.tipo === 'mover' && data.campo_id) {
            const campoElement = document.querySelector(`[data-campo-id="${data.campo_id}"]`);
            if (campoElement) {
                campoElement.style.opacity = '1';
            }
        }
        
        formBuilderLog('[FormBuilder] ========== handleDrop CONCLUÍDO ==========');
    } catch (error) {
        formBuilderError('[FormBuilder] ❌ ERRO ao processar drop:', error);
        formBuilderError('[FormBuilder] Stack trace:', error.stack);
    }
}

function selecionarCampo(campoId) {
    if (window.editor) {
        window.editor.selecionarCampo(campoId);
    }
}

function removerCampo(campoId) {
    if (window.editor) {
        if (confirm('Deseja remover este campo?')) {
            window.editor.removerCampo(campoId);
        }
    }
}

function duplicarCampo(campoId) {
    if (window.editor) {
        window.editor.duplicarCampo(campoId);
    }
}

function salvarLabelInline(campoId, novoLabel) {
    if (window.editor) {
        atualizarPropriedadeCampo(campoId, 'label', novoLabel.trim());
    }
}

function adicionarNovaSecao() {
    if (window.editor) {
        window.editor.adicionarSecao();
    }
}

function removerSecao(secaoId) {
    if (window.editor) {
        if (confirm('Deseja remover esta seção? Todos os campos serão removidos.')) {
            window.editor.removerSecao(secaoId);
        }
    }
}

function atualizarTituloSecao(secaoId, novoTitulo) {
    if (window.editor) {
        window.editor.atualizarTituloSecao(secaoId, novoTitulo);
    }
}

function moverCampo(campoId, direcao) {
    if (window.editor) {
        window.editor.moverCampo(campoId, direcao);
    }
}

function moverSecao(secaoId, direcao) {
    if (window.editor) {
        window.editor.moverSecao(secaoId, direcao);
    }
}
