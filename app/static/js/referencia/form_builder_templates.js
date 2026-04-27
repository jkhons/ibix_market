/* 
  REFERÊNCIA DO CERTILOG - Form Builder Templates JavaScript
  Este arquivo é uma cópia de referência do sistema Certilog.
  Não deve ser usado diretamente no PDV Ibix.
  Adaptar conforme necessário para implementação futura.
*/

// Form Builder - Templates de OS
// Gerencia listagem, criação e edição de templates

const API_BASE = '/api/v1/manutencao/templates';

let templatesData = [];
let unidadesData = [];
let isUserSuperAdmin = false; // Será definido ao carregar a página

// Carregar templates
async function carregarTemplates() {
    try {
        const response = await fetch(API_BASE, {
            credentials: 'include'  // Incluir cookies de sessão
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Erro HTTP:', response.status, errorText);
            throw new Error(`Erro ao carregar templates: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Templates carregados:', data);
        
        if (!Array.isArray(data)) {
            console.error('Resposta não é um array:', data);
            throw new Error('Resposta da API não é um array');
        }
        
        templatesData = data;
        renderizarTemplates();
    } catch (error) {
        console.error('Erro ao carregar templates:', error);
        const tbody = document.getElementById('tbody-templates');
        if (tbody) {
            tbody.innerHTML = 
                '<tr><td colspan="7" class="text-center text-danger">Erro ao carregar templates: ' + error.message + '</td></tr>';
        }
    }
}

// Renderizar templates na tabela
function renderizarTemplates() {
    const tbody = document.getElementById('tbody-templates');
    
    if (!tbody) {
        console.error('Elemento tbody-templates não encontrado');
        return;
    }
    
    if (!Array.isArray(templatesData)) {
        console.error('templatesData não é um array:', templatesData);
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-danger">Erro: dados inválidos</td></tr>';
        return;
    }
    
    if (templatesData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">Nenhum template encontrado</td></tr>';
        return;
    }
    
    try {
        tbody.innerHTML = templatesData.map(template => {
            // Validar campos obrigatórios
            if (!template.id || !template.nome) {
                console.warn('Template inválido:', template);
                return '';
            }
            
            const escopo = template.unidade_id ? `Unidade ${template.unidade_id}` : 'Corporativo';
            const versao = (template.versao_atual && template.versao_atual.versao) ? template.versao_atual.versao : '-';
            const statusBadge = getStatusBadge(template.status || 'rascunho');
            const dataCriacao = template.criado_em ? (typeof window.formatarDataApenas === 'function' ? window.formatarDataApenas(template.criado_em) : template.criado_em) : '-';
            
            // Botão de arquivar (apenas para templates não arquivados)
            const botaoArquivar = (template.status !== 'arquivado') ? 
                `<button class="btn btn-sm btn-warning" onclick="arquivarTemplate(${template.id}, '${escapeHtml(template.nome)}')" title="Arquivar Template">
                    <i data-feather="archive"></i>
                </button>` : '';
            
            // Botão de deletar apenas para SUPER_ADMIN
            const botaoDeletar = isUserSuperAdmin ? 
                `<button class="btn btn-sm btn-danger" onclick="apagarTemplate(${template.id}, '${escapeHtml(template.nome)}')" title="Apagar Permanentemente (SUPER_ADMIN)">
                    <i data-feather="trash-2"></i>
                </button>` : '';
            
            // Indicador de template padrão
            const templatePadrao = template.tipo_os_id ? 
                `<span class="badge bg-success" title="Template padrão para tipo de OS ID: ${template.tipo_os_id}">
                    <i data-feather="star" style="width: 12px; height: 12px;"></i> Padrão
                </span>` : '';
            
            return `
                <tr>
                    <td>${escapeHtml(template.nome)} ${templatePadrao}</td>
                    <td>${escapeHtml(template.tipo_os || '-')}</td>
                    <td>${escopo}</td>
                    <td>${statusBadge}</td>
                    <td>${versao}</td>
                    <td>${dataCriacao}</td>
                    <td>
                        <button class="btn btn-sm btn-primary" onclick="abrirEditorTemplate(${template.id})" title="Editar/Publicar">
                            <i data-feather="edit"></i> Editor
                        </button>
                        <button class="btn btn-sm btn-info" onclick="visualizarTemplate(${template.id})" title="Visualizar">
                            <i data-feather="eye"></i>
                        </button>
                        <button class="btn btn-sm btn-success" onclick="duplicarTemplate(${template.id}, '${escapeHtml(template.nome)}')" title="Duplicar Template">
                            <i data-feather="copy"></i>
                        </button>
                        ${template.status !== 'arquivado' ? 
                            `<button class="btn btn-sm btn-secondary" onclick="editarTemplate(${template.id})" title="Editar Metadados${template.status === 'publicado' ? ' (volta para rascunho)' : ''}">
                                <i data-feather="settings"></i>
                            </button>` : ''}
                        ${botaoArquivar}
                        ${botaoDeletar}
                    </td>
                </tr>
            `;
        }).filter(html => html !== '').join('');
        
        // Reinicializar ícones Feather
        if (typeof feather !== 'undefined') {
            feather.replace();
        }
    } catch (error) {
        console.error('Erro ao renderizar templates:', error);
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-danger">Erro ao renderizar templates</td></tr>';
    }
}

// Função auxiliar para escapar HTML
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Badge de status
function getStatusBadge(status) {
    const badges = {
        'rascunho': '<span class="badge bg-secondary">Rascunho</span>',
        'publicado': '<span class="badge bg-success">Publicado</span>',
        'arquivado': '<span class="badge bg-dark">Arquivado</span>'
    };
    return badges[status] || status;
}

// Carregar unidades para dropdown
async function carregarUnidades() {
    try {
        const response = await fetch('/api/v1/configuracoes/unidades', {
            credentials: 'include'  // Incluir cookies de sessão
        });
        
        if (response.ok) {
            unidadesData = await response.json();
            const select = document.getElementById('templateUnidadeId');
            if (select) {
                select.innerHTML = '<option value="">Corporativo (todas unidades)</option>' +
                    unidadesData.map(u => `<option value="${u.id}">${u.nome}</option>`).join('');
            }
            // Preencher também o select do modal de duplicação
            const selectDuplicar = document.getElementById('duplicarTemplateUnidadeId');
            if (selectDuplicar) {
                selectDuplicar.innerHTML = '<option value="">Corporativo (todas unidades)</option>' +
                    unidadesData.map(u => `<option value="${u.id}">${u.nome}</option>`).join('');
            }
        }
    } catch (error) {
        console.error('Erro ao carregar unidades:', error);
    }
}

// Carregar tipos de OS do banco de dados
async function carregarTiposOS() {
    try {
        const response = await fetch('/api/v1/manutencao/tipos-os/?ativo=true', {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error(`Erro ao carregar tipos de OS: ${response.status}`);
        }
        
        const tipos = await response.json();
        console.log('Tipos de OS carregados:', tipos);
        
        // Preencher select do modal (tipo_os - enum)
        const selectModal = document.getElementById('templateTipoOS');
        if (selectModal) {
            selectModal.innerHTML = '<option value="">Selecione...</option>' +
                tipos.map(t => {
                    const valor = t.tipo_os_template || t.codigo.toLowerCase();
                    return `<option value="${valor}">${t.nome}</option>`;
                }).join('');
        }
        
        // Preencher select de tipo OS padrão (tipo_os_id - ID do tipo)
        const selectTipoOSPadrao = document.getElementById('templateTipoOSPadrao');
        if (selectTipoOSPadrao) {
            selectTipoOSPadrao.innerHTML = '<option value="">Selecione para tornar este template padrão para um tipo específico...</option>' +
                tipos.map(t => {
                    return `<option value="${t.id}">${t.nome}</option>`;
                }).join('');
        }
        
        // Preencher select do filtro
        const selectFiltro = document.getElementById('filtro-tipo-os');
        if (selectFiltro) {
            // Manter opção "Todos" e adicionar tipos
            const opcoesExistentes = Array.from(selectFiltro.options).filter(opt => opt.value === '').map(opt => opt.outerHTML);
            selectFiltro.innerHTML = opcoesExistentes.join('') +
                tipos.map(t => {
                    const valor = t.tipo_os_template || t.codigo.toLowerCase();
                    return `<option value="${valor}">${t.nome}</option>`;
                }).join('');
        }
    } catch (error) {
        console.error('Erro ao carregar tipos de OS:', error);
        // Em caso de erro, manter valores padrão como fallback
        const selectModal = document.getElementById('templateTipoOS');
        if (selectModal) {
            selectModal.innerHTML = `
                <option value="">Erro ao carregar tipos</option>
                <option value="rota">Rota</option>
                <option value="preventiva">Preventiva</option>
                <option value="corretiva">Corretiva</option>
                <option value="inspecao">Inspeção</option>
                <option value="informativo">Informativo</option>
            `;
        }
    }
}

// Abrir modal de novo template
async function abrirModalNovoTemplate() {
    document.getElementById('formTemplate').reset();
    document.getElementById('templateId').value = '';
    document.getElementById('modalTemplateLabel').textContent = 'Novo Template';
    // Garantir que tipos de OS estejam carregados
    const selectTipoOS = document.getElementById('templateTipoOS');
    if (selectTipoOS && selectTipoOS.options.length <= 1) {
        await carregarTiposOS();
    }
    document.getElementById('modalTemplateCustom').classList.add('active');
    document.body.style.overflow = 'hidden';
}

// Fechar modal
function fecharModalTemplate() {
    document.getElementById('modalTemplateCustom').classList.remove('active');
    document.body.style.overflow = '';
}

// Salvar template
async function salvarTemplate() {
    const form = document.getElementById('formTemplate');
    const formData = new FormData(form);
    
    const dados = {
        nome: formData.get('nome'),
        tipo_os: formData.get('tipo_os'),
        tipo_os_id: formData.get('tipo_os_id') ? parseInt(formData.get('tipo_os_id')) : null,
        descricao: formData.get('descricao') || null,
        unidade_id: formData.get('unidade_id') ? parseInt(formData.get('unidade_id')) : null
    };
    
    const templateId = formData.get('id');
    const url = templateId ? `${API_BASE}/${templateId}` : API_BASE;
    const method = templateId ? 'PUT' : 'POST';
    
    try {
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',  // Incluir cookies de sessão
            body: JSON.stringify(dados)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Erro ao salvar template');
        }
        
        const result = await response.json();
        console.log('Template salvo:', result);
        
        fecharModalTemplate();
        
        // Recarregar listagem
        await carregarTemplates();
        
        // Se foi criação (não edição), redirecionar para editor
        if (!templateId && result.id) {
            alert('Template criado com sucesso! Redirecionando para o editor...');
            setTimeout(() => {
                abrirEditorTemplate(result.id);
            }, 500);
        } else {
            alert('Template salvo com sucesso!');
        }
    } catch (error) {
        console.error('Erro ao salvar template:', error);
        alert('Erro ao salvar template: ' + error.message);
    }
}

// Editar template
async function editarTemplate(templateId) {
    const template = templatesData.find(t => t.id === templateId);
    if (!template) {
        alert('Template não encontrado');
        return;
    }
    
    if (template.status === 'arquivado') {
        alert('Templates arquivados não podem ser editados');
        return;
    }
    
    // Templates publicados podem ser editados (voltam para rascunho automaticamente)
    if (template.status === 'publicado') {
        if (!confirm('Este template está publicado. Ao editar, ele voltará para rascunho. Deseja continuar?')) {
            return;
        }
    }
    
    // Garantir que tipos de OS estejam carregados antes de editar
    const selectTipoOS = document.getElementById('templateTipoOS');
    if (selectTipoOS && selectTipoOS.options.length <= 1) {
        await carregarTiposOS();
    }
    
    document.getElementById('templateId').value = template.id;
    document.getElementById('templateNome').value = template.nome;
    document.getElementById('templateTipoOS').value = template.tipo_os || '';
    document.getElementById('templateTipoOSPadrao').value = template.tipo_os_id || '';
    document.getElementById('templateUnidadeId').value = template.unidade_id || '';
    document.getElementById('templateDescricao').value = template.descricao || '';
    document.getElementById('modalTemplateLabel').textContent = 'Editar Template';
    
    document.getElementById('modalTemplateCustom').classList.add('active');
    document.body.style.overflow = 'hidden';
}

// Publicar template
async function publicarTemplate(templateId) {
    // Redirecionar para editor para definir schema antes de publicar
    window.location.href = `/manutencao/templates/${templateId}/editor`;
}

// Visualizar template
function visualizarTemplate(templateId) {
    window.location.href = `/manutencao/templates/${templateId}/visualizar`;
}

// Abrir editor de template
function abrirEditorTemplate(templateId) {
    window.location.href = `/manutencao/templates/${templateId}/editor`;
}

// Filtrar templates
function filtrarTemplates() {
    const tipoOS = document.getElementById('filtro-tipo-os').value;
    const status = document.getElementById('filtro-status').value;
    const escopo = document.getElementById('filtro-escopo').value;
    
    // Recarregar com filtros
    let url = API_BASE + '?';
    if (tipoOS) url += `tipo_os=${tipoOS}&`;
    if (status) url += `status_filter=${status}&`;
    if (escopo) url += `escopo=${escopo}&`;
    
    fetch(url, {
        credentials: 'include'  // Incluir cookies de sessão
    })
    .then(res => res.json())
    .then(data => {
        templatesData = data;
        renderizarTemplates();
    })
    .catch(error => {
        console.error('Erro ao filtrar templates:', error);
    });
}

// Verificar se usuário é SUPER_ADMIN
async function verificarSuperAdmin() {
    try {
        // Tentar acessar endpoint que requer SUPER_ADMIN para verificar
        // Usar endpoint de templates com método que falha se não for SUPER_ADMIN
        // Ou criar endpoint específico de verificação
        // Por enquanto, vamos tentar deletar um template inexistente para verificar permissão
        // Mas melhor: verificar via API de usuário atual
        
        // Alternativa: verificar via endpoint de configurações de usuários
        const response = await fetch('/api/v1/configuracoes/usuarios/me', {
            credentials: 'include'
        });
        
        if (response.ok) {
            const userData = await response.json();
            // Verificar se tem informação de SUPER_ADMIN no retorno
            // Se não tiver, tentar outra abordagem
            // Por enquanto, vamos usar uma verificação mais direta
        }
        
        // Verificar tentando acessar endpoint de deletar (mas não deletar de fato)
        // Ou melhor: adicionar flag no template response ou criar endpoint específico
        // Por enquanto, vamos usar uma verificação via tentativa de acesso ao endpoint
        // Mas isso não é ideal. Vamos adicionar verificação no backend que retorna isso
        
    } catch (error) {
        console.error('Erro ao verificar SUPER_ADMIN:', error);
        isUserSuperAdmin = false;
    }
}

// Arquivar template (soft delete)
async function arquivarTemplate(templateId, templateNome) {
    const confirmacao = confirm(
        `Deseja arquivar o template "${templateNome}"?\n\n` +
        `O template será arquivado e não aparecerá mais nas listagens padrão.\n\n` +
        `Templates arquivados podem ser visualizados através do filtro de status.`
    );
    
    if (!confirmacao) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/${templateId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        if (!response.ok) {
            // Tratar diferentes tipos de erro
            if (response.status === 403) {
                throw new Error('Você não tem permissão para arquivar templates. Entre em contato com o administrador.');
            } else if (response.status === 404) {
                throw new Error('Template não encontrado.');
            } else {
                const error = await response.json().catch(() => ({ detail: 'Erro desconhecido' }));
                throw new Error(error.detail || `Erro ${response.status}: ${response.statusText}`);
            }
        }
        
        // Sucesso (204 No Content)
        alert('Template arquivado com sucesso!');
        
        // Recarregar listagem
        await carregarTemplates();
        
    } catch (error) {
        console.error('Erro ao arquivar template:', error);
        alert('Erro ao arquivar template: ' + error.message);
    }
}

// Apagar template permanentemente (apenas SUPER_ADMIN)
async function apagarTemplate(templateId, templateNome) {
    // Confirmação dupla para operação destrutiva
    const confirmacao1 = confirm(
        `ATENÇÃO: Você está prestes a APAGAR PERMANENTEMENTE o template "${templateNome}".\n\n` +
        `Esta ação NÃO PODE ser desfeita!\n\n` +
        `Todas as versões do template serão apagadas permanentemente.\n\n` +
        `Deseja continuar?`
    );
    
    if (!confirmacao1) {
        return;
    }
    
    const confirmacao2 = confirm(
        `CONFIRMAÇÃO FINAL:\n\n` +
        `Tem certeza absoluta que deseja apagar permanentemente o template "${templateNome}"?\n\n` +
        `Esta ação é IRREVERSÍVEL!`
    );
    
    if (!confirmacao2) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/${templateId}/apagar`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Erro desconhecido' }));
            throw new Error(error.detail || `Erro ${response.status}: ${response.statusText}`);
        }
        
        // Sucesso
        alert('Template apagado permanentemente com sucesso!');
        
        // Recarregar listagem
        await carregarTemplates();
        
    } catch (error) {
        console.error('Erro ao apagar template:', error);
        alert('Erro ao apagar template: ' + error.message);
    }
}

// Duplicar template
async function duplicarTemplate(templateId, templateNome) {
    const template = templatesData.find(t => t.id === templateId);
    if (!template) {
        alert('Template não encontrado');
        return;
    }
    
    // Garantir que unidades estejam carregadas
    if (unidadesData.length === 0) {
        await carregarUnidades();
    }
    
    // Preencher modal com dados do template original
    document.getElementById('duplicarTemplateId').value = templateId;
    document.getElementById('duplicarTemplateNome').value = templateNome + ' (Cópia)';
    document.getElementById('duplicarTemplateUnidadeId').value = template.unidade_id || '';
    
    // Abrir modal
    document.getElementById('modalDuplicarTemplateCustom').classList.add('active');
    document.body.style.overflow = 'hidden';
}

// Fechar modal de duplicação
function fecharModalDuplicarTemplate() {
    document.getElementById('modalDuplicarTemplateCustom').classList.remove('active');
    document.body.style.overflow = '';
    document.getElementById('formDuplicarTemplate').reset();
}

// Confirmar duplicação
async function confirmarDuplicacao() {
    const form = document.getElementById('formDuplicarTemplate');
    const formData = new FormData(form);
    
    const templateId = formData.get('template_id');
    const nome = formData.get('nome');
    
    // Capturar unidade_id do select diretamente
    const selectUnidade = document.getElementById('duplicarTemplateUnidadeId');
    const unidadeIdValue = selectUnidade ? selectUnidade.value : null;
    
    // Normalizar unidade_id: string vazia ou "null" vira null, senão converte para int
    let unidade_id = null;
    if (unidadeIdValue && unidadeIdValue !== '' && unidadeIdValue !== 'null') {
        const parsed = parseInt(unidadeIdValue, 10);
        if (!isNaN(parsed)) {
            unidade_id = parsed;
        }
    }
    
    // Log para debug
    console.log('🔍 Duplicação - Valores capturados:', {
        templateId: templateId,
        nome: nome,
        unidadeIdValue: unidadeIdValue,
        unidade_id: unidade_id,
        tipo: typeof unidade_id
    });
    
    const dados = {
        nome: nome,
        unidade_id: unidade_id
    };
    
    if (!dados.nome || dados.nome.trim() === '') {
        alert('Por favor, informe o nome do template duplicado');
        return;
    }
    
    // Log dos dados que serão enviados
    console.log('📤 Dados que serão enviados:', dados);
    
    try {
        const response = await fetch(`${API_BASE}/${templateId}/duplicar`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify(dados)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Erro ao duplicar template');
        }
        
        const result = await response.json();
        console.log('Template duplicado:', result);
        
        fecharModalDuplicarTemplate();
        
        // Recarregar listagem
        await carregarTemplates();
        
        alert('Template duplicado com sucesso!');
        
        // Opcional: redirecionar para o editor do template duplicado
        if (result.id) {
            if (confirm('Template duplicado com sucesso! Deseja abrir o editor do template duplicado?')) {
                abrirEditorTemplate(result.id);
            }
        }
    } catch (error) {
        console.error('Erro ao duplicar template:', error);
        alert('Erro ao duplicar template: ' + error.message);
    }
}
