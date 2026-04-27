/**
 * PDV Ibix - JavaScript para Inspetores/Aprovadores
 * Gerencia a listagem e operações de inspetores e aprovadores
 */

// Variáveis globais
let inspetores = [];
let paginaAtual = 1;
let totalPaginas = 1;
let inspetorSelecionado = null;

// Inicialização quando o DOM estiver carregado
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Inicializando página de inspetores/aprovadores...');
    
    // Carregar inspetores
    carregarInspetores();
    
    // Configurar eventos
    configurarEventos();
});

/**
 * Configura os eventos da página
 */
function configurarEventos() {
    // Busca ao pressionar Enter
    document.getElementById('filtroNome').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            buscarInspetores();
        }
    });
    
    document.getElementById('filtroCPF').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            buscarInspetores();
        }
    });
}

/**
 * Carrega a lista de inspetores/aprovadores
 */
async function carregarInspetores() {
    try {
        console.log('📋 Carregando inspetores/aprovadores...');
        
        const skip = (paginaAtual - 1) * 10;
        const url = `/api/v1/inspetores-aprovadores/?skip=${skip}&limit=10`;
        
        console.log('🔗 URL:', url);
        
        const response = await fetch(url, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('pdv_automscale_token')}`
            }
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            console.error('❌ Erro na API:', errorData);
            throw new Error(`Erro HTTP: ${response.status} - ${errorData.detail || 'Erro desconhecido'}`);
        }
        
        const data = await response.json();
        console.log('📦 Dados recebidos:', data);
        
        inspetores = data.inspetores || [];
        totalPaginas = Math.ceil((data.total || 0) / 10) || 1;
        
        renderizarTabela();
        renderizarPaginacao();
        
        console.log(`✅ ${inspetores.length} inspetores/aprovadores carregados`);
        
    } catch (error) {
        console.error('❌ Erro ao carregar inspetores:', error);
        mostrarAlerta('Erro ao carregar inspetores/aprovadores', 'danger');
    }
}

/**
 * Busca inspetores com filtros
 */
async function buscarInspetores() {
    try {
        console.log('🔍 Buscando inspetores...');
        
        const nome = document.getElementById('filtroNome').value.trim();
        const cpf = document.getElementById('filtroCPF').value.trim();
        const tipo = document.getElementById('filtroTipo').value;
        const ativo = document.getElementById('filtroStatus').value;
        
        const params = new URLSearchParams({
            skip: 0,
            limit: 100
        });
        
        if (nome) params.append('nome', nome);
        if (tipo) params.append('tipo', tipo);
        if (ativo) params.append('ativo', ativo);
        
        const response = await fetch(`/api/v1/inspetores-aprovadores?${params}`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('pdv_automscale_token')}`
            }
        });
        
        if (!response.ok) {
            throw new Error(`Erro HTTP: ${response.status}`);
        }
        
        const data = await response.json();
        inspetores = data.inspetores || [];
        totalPaginas = Math.ceil(data.total / 10) || 1;
        paginaAtual = 1;
        
        renderizarTabela();
        renderizarPaginacao();
        
        console.log(`✅ ${inspetores.length} inspetores encontrados`);
        
    } catch (error) {
        console.error('❌ Erro ao buscar inspetores:', error);
        mostrarAlerta('Erro ao buscar inspetores/aprovadores', 'danger');
    }
}

/**
 * Limpa os filtros
 */
function limparFiltros() {
    document.getElementById('filtroNome').value = '';
    document.getElementById('filtroCPF').value = '';
    document.getElementById('filtroTipo').value = '';
    document.getElementById('filtroStatus').value = '';
    
    paginaAtual = 1;
    carregarInspetores();
}

/**
 * Renderiza a tabela de inspetores
 */
function renderizarTabela() {
    const tbody = document.getElementById('tbodyInspetores');
    
    if (inspetores.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="10" class="text-center text-muted py-4">
                    <i class="align-middle me-2" data-feather="inbox"></i>
                    Nenhum inspetor/aprovador encontrado
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = inspetores.map(inspetor => `
        <tr>
            <td>${inspetor.id}</td>
            <td>${inspetor.nome}</td>
            <td>${inspetor.cpf}</td>
            <td>${inspetor.email}</td>
            <td>${inspetor.cargo}</td>
            <td>
                <span class="badge bg-${getBadgeColor(inspetor.tipo)}">
                    ${formatTipo(inspetor.tipo)}
                </span>
            </td>
            <td>${inspetor.registro_profissional || '-'}</td>
            <td>${inspetor.data_validade_credenciamento ? formatarData(inspetor.data_validade_credenciamento) : '-'}</td>
            <td>
                <span class="badge bg-${inspetor.ativo ? 'success' : 'secondary'}">
                    ${inspetor.ativo ? 'Ativo' : 'Inativo'}
                </span>
            </td>
            <td>
                <div class="btn-group" role="group">
                    <button type="button" class="btn btn-sm btn-outline-primary" onclick="verDetalhes(${inspetor.id})">
                        <i class="align-middle" data-feather="eye"></i>
                    </button>
                    <button type="button" class="btn btn-sm btn-outline-warning" onclick="editarInspetor(${inspetor.id})">
                        <i class="align-middle" data-feather="edit"></i>
                    </button>
                    <button type="button" class="btn btn-sm btn-outline-${inspetor.ativo ? 'danger' : 'success'}" 
                            onclick="toggleStatus(${inspetor.id}, ${inspetor.ativo})">
                        <i class="align-middle" data-feather="${inspetor.ativo ? 'pause' : 'play'}"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
    
    // Reinicializar ícones Feather
    if (typeof feather !== 'undefined') {
        feather.replace();
    }
}

/**
 * Renderiza a paginação
 */
function renderizarPaginacao() {
    const paginacao = document.getElementById('paginacao');
    
    if (totalPaginas <= 1) {
        paginacao.innerHTML = '';
        return;
    }
    
    let paginas = '';
    
    // Botão anterior
    paginas += `
        <li class="page-item ${paginaAtual === 1 ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="mudarPagina(${paginaAtual - 1})">Anterior</a>
        </li>
    `;
    
    // Páginas
    for (let i = 1; i <= totalPaginas; i++) {
        if (i === 1 || i === totalPaginas || (i >= paginaAtual - 2 && i <= paginaAtual + 2)) {
            paginas += `
                <li class="page-item ${i === paginaAtual ? 'active' : ''}">
                    <a class="page-link" href="#" onclick="mudarPagina(${i})">${i}</a>
                </li>
            `;
        } else if (i === paginaAtual - 3 || i === paginaAtual + 3) {
            paginas += '<li class="page-item disabled"><span class="page-link">...</span></li>';
        }
    }
    
    // Botão próximo
    paginas += `
        <li class="page-item ${paginaAtual === totalPaginas ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="mudarPagina(${paginaAtual + 1})">Próximo</a>
        </li>
    `;
    
    paginacao.innerHTML = paginas;
}

/**
 * Muda a página
 */
function mudarPagina(pagina) {
    if (pagina < 1 || pagina > totalPaginas) return;
    
    paginaAtual = pagina;
    carregarInspetores();
}

/**
 * Ver detalhes do inspetor
 */
async function verDetalhes(id) {
    try {
        console.log(`👁️ Verificando detalhes do inspetor ${id}...`);
        
        const response = await fetch(`/api/v1/inspetores-aprovadores/${id}`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('pdv_automscale_token')}`
            }
        });
        
        if (!response.ok) {
            throw new Error(`Erro HTTP: ${response.status}`);
        }
        
        const inspetor = await response.json();
        inspetorSelecionado = inspetor;
        
        const modalBody = document.getElementById('modalDetalhesBody');
        modalBody.innerHTML = `
            <div class="row">
                <div class="col-md-6">
                    <h6 class="text-primary">Dados Pessoais</h6>
                    <p><strong>Nome:</strong> ${inspetor.nome}</p>
                    <p><strong>CPF:</strong> ${inspetor.cpf}</p>
                    <p><strong>RG:</strong> ${inspetor.rg || '-'}</p>
                    <p><strong>Data de Nascimento:</strong> ${inspetor.data_nascimento ? formatarData(inspetor.data_nascimento) : '-'}</p>
                    <p><strong>Sexo:</strong> ${formatSexo(inspetor.sexo)}</p>
                </div>
                <div class="col-md-6">
                    <h6 class="text-primary">Contato</h6>
                    <p><strong>Email:</strong> ${inspetor.email}</p>
                    <p><strong>Telefone:</strong> ${inspetor.telefone || '-'}</p>
                    <p><strong>Celular:</strong> ${inspetor.celular || '-'}</p>
                </div>
            </div>
            <div class="row mt-3">
                <div class="col-md-6">
                    <h6 class="text-primary">Dados Profissionais</h6>
                    <p><strong>Cargo:</strong> ${inspetor.cargo}</p>
                    <p><strong>Tipo:</strong> ${formatTipo(inspetor.tipo)}</p>
                    <p><strong>Registro:</strong> ${inspetor.registro_profissional || '-'}</p>
                    <p><strong>Órgão:</strong> ${inspetor.orgao_registro || '-'}</p>
                </div>
                <div class="col-md-6">
                    <h6 class="text-primary">Credenciamento</h6>
                    <p><strong>Data de Credenciamento:</strong> ${inspetor.data_credenciamento ? formatarData(inspetor.data_credenciamento) : '-'}</p>
                    <p><strong>Validade:</strong> ${inspetor.data_validade_credenciamento ? formatarData(inspetor.data_validade_credenciamento) : '-'}</p>
                    <p><strong>Status:</strong> <span class="badge bg-${inspetor.ativo ? 'success' : 'secondary'}">${inspetor.ativo ? 'Ativo' : 'Inativo'}</span></p>
                </div>
            </div>
            ${inspetor.especialidades || inspetor.areas_atuacao ? `
            <div class="row mt-3">
                <div class="col-12">
                    <h6 class="text-primary">Especializações</h6>
                    ${inspetor.especialidades ? `<p><strong>Especialidades:</strong> ${inspetor.especialidades}</p>` : ''}
                    ${inspetor.areas_atuacao ? `<p><strong>Áreas de Atuação:</strong> ${inspetor.areas_atuacao}</p>` : ''}
                </div>
            </div>
            ` : ''}
        `;
        
        const modal = new bootstrap.Modal(document.getElementById('modalDetalhes'));
        modal.show();
        
    } catch (error) {
        console.error('❌ Erro ao carregar detalhes:', error);
        mostrarAlerta('Erro ao carregar detalhes do inspetor', 'danger');
    }
}

/**
 * Editar inspetor
 */
function editarInspetor(id) {
    if (id) {
        window.location.href = `/certificados/inspetores/editar/${id}`;
    } else if (inspetorSelecionado) {
        window.location.href = `/certificados/inspetores/editar/${inspetorSelecionado.id}`;
    }
}

/**
 * Toggle status do inspetor
 */
async function toggleStatus(id, ativoAtual) {
    try {
        const acao = ativoAtual ? 'desativar' : 'ativar';
        const confirmacao = confirm(`Tem certeza que deseja ${acao} este inspetor/aprovador?`);
        
        if (!confirmacao) return;
        
        console.log(`${ativoAtual ? '⏸️' : '▶️'} ${acao.charAt(0).toUpperCase() + acao.slice(1)} inspetor ${id}...`);
        
        const response = await fetch(`/api/v1/inspetores-aprovadores/${id}/toggle-status`, {
            method: 'PATCH',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('pdv_automscale_token')}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`Erro HTTP: ${response.status}`);
        }
        
        mostrarAlerta(`Inspetor ${acao}do com sucesso!`, 'success');
        carregarInspetores();
        
    } catch (error) {
        console.error('❌ Erro ao alterar status:', error);
        mostrarAlerta('Erro ao alterar status do inspetor', 'danger');
    }
}

/**
 * Funções auxiliares
 */
function getBadgeColor(tipo) {
    switch (tipo) {
        case 'inspetor': return 'info';
        case 'aprovador': return 'warning';
        case 'ambos': return 'primary';
        default: return 'secondary';
    }
}

function formatTipo(tipo) {
    switch (tipo) {
        case 'inspetor': return 'Inspetor';
        case 'aprovador': return 'Aprovador';
        case 'ambos': return 'Ambos';
        default: return tipo;
    }
}

function formatSexo(sexo) {
    switch (sexo) {
        case 'M': return 'Masculino';
        case 'F': return 'Feminino';
        case 'O': return 'Outro';
        default: return '-';
    }
}

function formatarData(data) {
    if (!data) return '-';
    if (typeof window.formatarDataApenas === 'function') return window.formatarDataApenas(data);
    const s = String(data).trim();
    const m = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (m) return m[3] + '/' + m[2] + '/' + m[1];
    const d = new Date(data);
    return isNaN(d.getTime()) ? '-' : d.toLocaleDateString('pt-BR');
}

function mostrarAlerta(mensagem, tipo) {
    // Implementar sistema de alertas
    console.log(`${tipo.toUpperCase()}: ${mensagem}`);
} 