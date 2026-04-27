// PDV Ibix - Gerenciamento de Templates de E-mail

let templates = [];
let templateEmEdicao = null;

// Carregar templates
async function carregarTemplates() {
    try {
        const response = await fetch('/api/v1/configuracoes/email/templates/', {
            credentials: 'include'
        });
        
        if (response.ok) {
            templates = await response.json();
            renderizarListaTemplates();
        } else {
            mostrarAlerta('Erro ao carregar templates', 'danger');
        }
    } catch (error) {
        console.error('Erro ao carregar templates:', error);
        mostrarAlerta('Erro ao carregar templates', 'danger');
    }
}

// Renderizar lista de templates
function renderizarListaTemplates() {
    const lista = document.getElementById('listaTemplates');
    
    if (templates.length === 0) {
        lista.innerHTML = '<div class="list-group-item text-center text-muted">Nenhum template encontrado</div>';
        return;
    }
    
    lista.innerHTML = templates.map(template => `
        <a href="#" class="list-group-item list-group-item-action" onclick="selecionarTemplate('${template.nome}'); return false;">
            <div class="d-flex w-100 justify-content-between align-items-center">
                <div>
                    <h6 class="mb-1">${template.nome}</h6>
                    <small class="text-muted">${template.assunto || 'Sem assunto definido'}</small>
                </div>
                <i class="align-middle text-primary" data-feather="chevron-right"></i>
            </div>
        </a>
    `).join('');
    
    if (typeof feather !== 'undefined') {
        feather.replace();
    }
}

// Selecionar template para edição
async function selecionarTemplate(nome) {
    try {
        const response = await fetch(`/api/v1/configuracoes/email/templates/${nome}`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const template = await response.json();
            
            templateEmEdicao = nome;
            
            document.getElementById('tituloEditor').innerHTML = '<i class="align-middle me-2" data-feather="edit"></i>Editar Template: ' + nome;
            document.getElementById('templateOriginalNome').value = nome;
            document.getElementById('templateNome').value = template.nome;
            document.getElementById('templateAssunto').value = template.assunto || '';
            document.getElementById('templateVariaveis').value = template.variaveis || '';
            document.getElementById('templateHtml').value = template.html;
            
            document.getElementById('cardBoasVindas').style.display = 'none';
            document.getElementById('cardEditor').style.display = 'block';
            document.getElementById('btnExcluirTemplate').style.display = 'inline-block';
            
            if (typeof feather !== 'undefined') {
                feather.replace();
            }
        } else {
            mostrarAlerta('Erro ao carregar template', 'danger');
        }
    } catch (error) {
        console.error('Erro ao carregar template:', error);
        mostrarAlerta('Erro ao carregar template', 'danger');
    }
}

// Novo template
function novoTemplate() {
    templateEmEdicao = null;
    
    document.getElementById('tituloEditor').innerHTML = '<i class="align-middle me-2" data-feather="plus"></i>Criar Novo Template';
    document.getElementById('formTemplate').reset();
    document.getElementById('templateOriginalNome').value = '';
    
    document.getElementById('cardBoasVindas').style.display = 'none';
    document.getElementById('cardEditor').style.display = 'block';
    document.getElementById('btnExcluirTemplate').style.display = 'none';
    
    if (typeof feather !== 'undefined') {
        feather.replace();
    }
}

// Cancelar edição
function cancelarEdicao() {
    templateEmEdicao = null;
    document.getElementById('formTemplate').reset();
    document.getElementById('cardEditor').style.display = 'none';
    document.getElementById('cardBoasVindas').style.display = 'block';
}

// Salvar template
async function salvarTemplate(event) {
    event.preventDefault();
    
    const dados = {
        nome: document.getElementById('templateNome').value.trim(),
        assunto: document.getElementById('templateAssunto').value.trim(),
        variaveis: document.getElementById('templateVariaveis').value.trim(),
        html: document.getElementById('templateHtml').value
    };
    
    // Validar nome
    if (!/^[a-z0-9_]+$/.test(dados.nome)) {
        mostrarAlerta('Nome inválido! Use apenas letras minúsculas, números e underscore', 'danger');
        return;
    }
    
    mostrarAlerta('Salvando template...', 'info');
    
    try {
        const url = templateEmEdicao 
            ? `/api/v1/configuracoes/email/templates/${templateEmEdicao}`
            : '/api/v1/configuracoes/email/templates/';
        
        const response = await fetch(url, {
            method: templateEmEdicao ? 'PUT' : 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify(dados)
        });
        
        if (response.ok) {
            mostrarAlerta('Template salvo com sucesso!', 'success');
            carregarTemplates();
            cancelarEdicao();
        } else {
            const error = await response.json();
            mostrarAlerta('Erro ao salvar template: ' + (error.detail || 'Erro desconhecido'), 'danger');
        }
    } catch (error) {
        console.error('Erro ao salvar template:', error);
        mostrarAlerta('Erro ao salvar template', 'danger');
    }
}

// Excluir template
async function excluirTemplate() {
    if (!templateEmEdicao) return;
    
    if (!confirm(`Tem certeza que deseja excluir o template "${templateEmEdicao}"?\n\nEsta ação não pode ser desfeita!`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/v1/configuracoes/email/templates/${templateEmEdicao}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        if (response.ok) {
            mostrarAlerta('Template excluído com sucesso!', 'success');
            carregarTemplates();
            cancelarEdicao();
        } else {
            mostrarAlerta('Erro ao excluir template', 'danger');
        }
    } catch (error) {
        console.error('Erro ao excluir template:', error);
        mostrarAlerta('Erro ao excluir template', 'danger');
    }
}

// Função para mostrar alertas
function mostrarAlerta(mensagem, tipo = 'info') {
    const container = document.getElementById('alert-container');
    if (!container) return;
    
    const alerta = document.createElement('div');
    alerta.className = `alert alert-${tipo} alert-dismissible fade show`;
    alerta.role = 'alert';
    alerta.innerHTML = `
        ${mensagem}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    container.appendChild(alerta);
    
    setTimeout(() => {
        alerta.remove();
    }, 5000);
}

// Inicializar página
document.addEventListener('DOMContentLoaded', function() {
    // Carregar templates
    carregarTemplates();
    
    // Event listeners
    const btnNovoTemplate = document.getElementById('btnNovoTemplate');
    if (btnNovoTemplate) {
        btnNovoTemplate.addEventListener('click', novoTemplate);
    }
    
    const formTemplate = document.getElementById('formTemplate');
    if (formTemplate) {
        formTemplate.addEventListener('submit', salvarTemplate);
    }
    
    const btnCancelar = document.getElementById('btnCancelar');
    if (btnCancelar) {
        btnCancelar.addEventListener('click', cancelarEdicao);
    }
    
    const btnExcluir = document.getElementById('btnExcluirTemplate');
    if (btnExcluir) {
        btnExcluir.addEventListener('click', excluirTemplate);
    }
});

