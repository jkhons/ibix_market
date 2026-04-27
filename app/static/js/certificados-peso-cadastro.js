/**
 * PDV Ibix - JavaScript para Cadastro de Certificados de Peso
 * Gerencia o formulário de cadastro de certificados de peso
 */

// Variáveis globais
let certificadoId = null;
let arquivoAtual = null; // Armazena o nome do arquivo atual

// Inicialização quando o DOM estiver carregado
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Inicializando página de cadastro de certificados de peso...');
    
    // Configurar validações
    configurarValidacoes();
    
    // Configurar eventos
    configurarEventos();
    
    // Verificar se é edição
    verificarEdicao();
});

/**
 * Configura as validações do formulário
 */
function configurarValidacoes() {
    const form = document.getElementById('formCertificadoPeso');
    if (!form) return;
    
    // Validação de valor nominal (campo livre)
    const valorNominal = document.getElementById('valor_nominal');
    if (valorNominal) {
        valorNominal.addEventListener('input', function() {
            if (this.value.trim() === '') {
                this.setCustomValidity('Campo obrigatório');
            } else {
                this.setCustomValidity('');
            }
        });
    }
    
    // Validação de datas
    const dataCalibracao = document.getElementById('data_calibracao');
    const dataValidade = document.getElementById('data_validade');
    
    if (dataCalibracao && dataValidade) {
        dataCalibracao.addEventListener('change', validarDatas);
        dataValidade.addEventListener('change', validarDatas);
    }
    
    // Validação de arquivo
    const arquivoPdf = document.getElementById('arquivo_pdf');
    if (arquivoPdf) {
        arquivoPdf.addEventListener('change', validarArquivo);
    }
}

/**
 * Valida as datas de calibração e validade
 */
function validarDatas() {
    const dataCalibracao = document.getElementById('data_calibracao');
    const dataValidade = document.getElementById('data_validade');
    
    if (dataCalibracao.value && dataValidade.value) {
        const calibracao = new Date(dataCalibracao.value);
        const validade = new Date(dataValidade.value);
        
        if (validade <= calibracao) {
            dataValidade.setCustomValidity('Data de validade deve ser posterior à data de calibração');
        } else {
            dataValidade.setCustomValidity('');
        }
    }
}

/**
 * Valida o arquivo PDF
 */
function validarArquivo() {
    const arquivo = document.getElementById('arquivo_pdf');
    const file = arquivo.files[0];
    
    if (file) {
        // Verificar tipo
        if (file.type !== 'application/pdf') {
            arquivo.setCustomValidity('Apenas arquivos PDF são permitidos');
            return;
        }
        
        // Verificar tamanho (10MB)
        const maxSize = 10 * 1024 * 1024; // 10MB
        if (file.size > maxSize) {
            arquivo.setCustomValidity('Arquivo deve ter no máximo 10MB');
            return;
        }
        
        arquivo.setCustomValidity('');
    }
}

/**
 * Configura os eventos do formulário
 */
function configurarEventos() {
    const form = document.getElementById('formCertificadoPeso');
    if (!form) return;
    
    // Evento de submit
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        salvarCertificado();
    });
    
    // Evento de mudança no arquivo PDF
    const arquivoPdf = document.getElementById('arquivo_pdf');
    if (arquivoPdf) {
        arquivoPdf.addEventListener('change', function() {
            console.log('📁 Arquivo PDF selecionado:', this.files[0] ? this.files[0].name : 'Nenhum');
            console.log('📁 Tamanho do arquivo:', this.files[0] ? this.files[0].size : 0, 'bytes');
            
            // Se um novo arquivo foi selecionado, limpar o arquivo atual
            if (this.files.length > 0) {
                console.log('📁 Novo arquivo selecionado, limpando arquivo atual');
                limparArquivoAtual();
            }
        });
    }
}

/**
 * Verifica se é uma edição e carrega os dados
 */
function verificarEdicao() {
    const urlParams = new URLSearchParams(window.location.search);
    const id = urlParams.get('id');
    
    if (id) {
        console.log('📝 Modo edição detectado, ID:', id);
        certificadoId = parseInt(id);
        carregarCertificado(certificadoId);
    }
}

/**
 * Carrega um certificado para edição
 */
async function carregarCertificado(id) {
    try {
        console.log('📥 Carregando certificado ID:', id);
        
        const response = await fetch(`/api/v1/certificados-auxiliares/peso/${id}`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${getToken()}`
            }
        });
        
        if (response.ok) {
            const certificado = await response.json();
            console.log('✅ Certificado carregado:', certificado);
            preencherFormulario(certificado);
        } else {
            const error = await response.json();
            console.error('❌ Erro ao carregar certificado:', error);
            mostrarAlerta('Erro ao carregar certificado', 'error');
        }
    } catch (error) {
        console.error('❌ Erro ao carregar certificado:', error);
        mostrarAlerta('Erro ao carregar certificado', 'error');
    }
}

/**
 * Preenche o formulário com os dados do certificado
 */
function preencherFormulario(certificado) {
    console.log('🔧 Preenchendo formulário com dados:', certificado);
    
    // Campos básicos
    setFieldValue('identificacao', certificado.identificacao);
    setFieldValue('valor_nominal', certificado.valor_nominal);
    setFieldValue('unidade', certificado.unidade);
    setFieldValue('classe', certificado.classe);
    setFieldValue('certificado_numero', certificado.certificado_numero);
    
    // Datas
    if (certificado.data_calibracao) {
        setFieldValue('data_calibracao', formatarDataParaInput(certificado.data_calibracao));
    }
    if (certificado.data_validade) {
        setFieldValue('data_validade', formatarDataParaInput(certificado.data_validade));
    }
    
    // Status (checkbox)
    const ativoField = document.getElementById('ativo');
    if (ativoField) {
        ativoField.checked = certificado.ativo;
    }
    
    // Arquivo PDF
    console.log('📄 Verificando arquivo PDF no certificado:', certificado.arquivo_pdf);
    const arquivoPdfField = document.getElementById('arquivo_pdf');
    console.log('📄 Campo arquivo_pdf encontrado:', !!arquivoPdfField);
    
    if (certificado.arquivo_pdf) {
        arquivoAtual = certificado.arquivo_pdf;
        mostrarArquivoAtual(certificado.arquivo_pdf);
    } else {
        arquivoAtual = null;
        limparArquivoAtual();
    }
    
    // Atualizar título
    const titulo = document.querySelector('h1');
    if (titulo) {
        titulo.textContent = 'Editar Certificado de Peso';
    }
}

/**
 * Mostra o arquivo atual no formulário
 */
function mostrarArquivoAtual(nomeArquivo) {
    console.log('📄 Mostrando arquivo atual:', nomeArquivo);
    
    // Remover arquivo atual anterior se existir
    limparArquivoAtual();
    
    // Criar um elemento para mostrar o arquivo atual
    const div = document.createElement('div');
    div.id = 'arquivo_atual';
    div.className = 'mb-3';
            div.innerHTML = `
            <label class="form-label">Arquivo PDF Atual</label>
            <div class="alert alert-info">
                <i class="align-middle me-1" data-feather="file-text"></i>
                ${nomeArquivo}
                <a href="/api/v1/certificados-auxiliares/peso/${certificadoId}/download-pdf" 
                   target="_blank" class="btn btn-sm btn-outline-primary ms-2">
                    <i class="align-middle me-1" data-feather="eye"></i>
                    Visualizar
                </a>
                <button type="button" class="btn btn-sm btn-outline-danger ms-2" 
                        onclick="removerArquivoAtual()">
                    <i class="align-middle me-1" data-feather="trash-2"></i>
                    Remover
                </button>
            </div>
        `;
    
            const arquivoPdfField = document.getElementById('arquivo_pdf');
        if (arquivoPdfField) {
            arquivoPdfField.parentNode.insertBefore(div, arquivoPdfField);
        }
}

/**
 * Remove o arquivo atual
 */
function removerArquivoAtual() {
    console.log('🗑️ Removendo arquivo atual');
    arquivoAtual = null;
    limparArquivoAtual();
    
    // Limpar o campo de arquivo
    const arquivoPdfField = document.getElementById('arquivo_pdf');
    if (arquivoPdfField) {
        arquivoPdfField.value = '';
    }
}

/**
 * Limpa a exibição do arquivo atual
 */
function limparArquivoAtual() {
    const arquivoAtual = document.getElementById('arquivo_atual');
    if (arquivoAtual) {
        arquivoAtual.remove();
    }
}

/**
 * Define o valor de um campo
 */
function setFieldValue(fieldName, value) {
    const field = document.getElementById(fieldName);
    if (!field) {
        console.log(`⚠️ Campo ${fieldName} não encontrado`);
        return;
    }
    
    console.log(`🔧 Definindo campo ${fieldName} = ${value} (tipo: ${typeof value})`);
    
    if (field.type === 'checkbox') {
        field.checked = value;
    } else {
        field.value = value;
    }
}

/**
 * Formata data para input type="date"
 */
function formatarDataParaInput(dataString) {
    if (!dataString) return '';
    const data = new Date(dataString);
    return data.toISOString().split('T')[0];
}

/**
 * Salva o certificado
 */
async function salvarCertificado() {
    try {
        console.log('💾 Salvando certificado...');
        
        // Validar formulário
        const form = document.getElementById('formCertificadoPeso');
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }
        
        // Preparar dados
        const formData = new FormData(form);
        const dados = {
            identificacao: formData.get('identificacao'),
            valor_nominal: formData.get('valor_nominal'),
            unidade: formData.get('unidade'),
            classe: formData.get('classe') || null,
            certificado_numero: formData.get('certificado_numero') || null,
            data_calibracao: formData.get('data_calibracao') || null,
            data_validade: formData.get('data_validade') || null,
            ativo: formData.get('ativo') === 'on'
        };
        
        // URL e método
        const url = certificadoId 
            ? `/api/v1/certificados-auxiliares/peso/${certificadoId}`
            : '/api/v1/certificados-auxiliares/peso';
        const method = certificadoId ? 'PUT' : 'POST';
        
        console.log('📤 Enviando dados para:', url);
        console.log('📤 Dados:', dados);
        
        // Enviar dados
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getToken()}`
            },
            body: JSON.stringify(dados)
        });
        
        if (response.ok) {
            const resultado = await response.json();
            console.log('✅ Certificado salvo com sucesso:', resultado);
            
            // Upload do arquivo PDF se existir
            const arquivoPdfField = document.getElementById('arquivo_pdf');
            const arquivoPdf = arquivoPdfField ? arquivoPdfField.files[0] : null;
            console.log('📁 Verificando arquivo PDF:', arquivoPdf ? arquivoPdf.name : 'Nenhum arquivo');
            console.log('📁 Tamanho do arquivo:', arquivoPdf ? arquivoPdf.size : 0, 'bytes');
            console.log('📁 Tipo do arquivo:', arquivoPdf ? arquivoPdf.type : 'N/A');
            console.log('📁 Arquivo atual antes da edição:', arquivoAtual);
            
            if (arquivoPdf && arquivoPdf.size > 0) {
                console.log('📁 Enviando arquivo PDF...');
                const certificadoIdParaUpload = certificadoId || resultado.id;
                console.log('📁 ID para upload:', certificadoIdParaUpload);
                await uploadArquivoPdf(certificadoIdParaUpload, arquivoPdf);
            } else {
                console.log('📁 Nenhum arquivo PDF para enviar');
                console.log('📁 Verificando se há arquivo atual:', arquivoAtual);
            }
            
            mostrarAlerta(
                certificadoId ? 'Certificado atualizado com sucesso!' : 'Certificado criado com sucesso!',
                'success'
            );
            
            // Redirecionar após 2 segundos
            setTimeout(() => {
                window.location.href = '/certificados/peso';
            }, 2000);
        } else {
            const error = await response.json();
            console.error('❌ Erro ao salvar certificado:', error);
            mostrarAlerta(error.detail || 'Erro ao salvar certificado', 'error');
        }
    } catch (error) {
        console.error('❌ Erro ao salvar certificado:', error);
        mostrarAlerta('Erro ao salvar certificado', 'error');
    }
}

/**
 * Salva como rascunho
 */
async function salvarRascunho() {
    try {
        console.log('📝 Salvando rascunho...');
        
        // Preparar dados (sem validações obrigatórias)
        const formData = new FormData(document.getElementById('formCertificadoPeso'));
        const dados = {
            identificacao: formData.get('identificacao') || 'Rascunho',
            valor_nominal: formData.get('valor_nominal') || '',
            unidade: formData.get('unidade') || 'kg',
            classe: formData.get('classe') || null,
            certificado_numero: formData.get('certificado_numero') || null,
            data_calibracao: formData.get('data_calibracao') || null,
            data_validade: formData.get('data_validade') || null,
            ativo: formData.get('ativo') === 'on'
        };
        
        // URL e método
        const url = certificadoId 
            ? `/api/v1/certificados-auxiliares/peso/${certificadoId}`
            : '/api/v1/certificados-auxiliares/peso';
        const method = certificadoId ? 'PUT' : 'POST';
        
        // Enviar dados
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getToken()}`
            },
            body: JSON.stringify(dados)
        });
        
        if (response.ok) {
            const resultado = await response.json();
            console.log('✅ Rascunho salvo com sucesso');
            
            // Upload do arquivo PDF se existir
            const arquivoPdfField = document.getElementById('arquivo_pdf');
            const arquivoPdf = arquivoPdfField ? arquivoPdfField.files[0] : null;
            if (arquivoPdf && arquivoPdf.size > 0) {
                const certificadoIdParaUpload = certificadoId || resultado.id;
                await uploadArquivoPdf(certificadoIdParaUpload, arquivoPdf);
            }
            
            mostrarAlerta('Rascunho salvo com sucesso!', 'success');
            
            // Redirecionar após 2 segundos
            setTimeout(() => {
                window.location.href = '/certificados/peso';
            }, 2000);
        } else {
            const error = await response.json();
            console.error('❌ Erro ao salvar rascunho:', error);
            mostrarAlerta(error.detail || 'Erro ao salvar rascunho', 'error');
        }
    } catch (error) {
        console.error('❌ Erro ao salvar rascunho:', error);
        mostrarAlerta('Erro ao salvar rascunho', 'error');
    }
}

/**
 * Upload do arquivo PDF
 */
async function uploadArquivoPdf(certificadoId, arquivo) {
    try {
        console.log('📁 Iniciando upload do arquivo:', arquivo.name);
        console.log('📁 Tamanho do arquivo:', arquivo.size, 'bytes');
        console.log('📁 Tipo do arquivo:', arquivo.type);
        console.log('📁 Certificado ID:', certificadoId);
        console.log('📁 É edição?', certificadoId ? 'Sim' : 'Não');
        
        const formData = new FormData();
        formData.append('file', arquivo);
        
        console.log('📁 FormData criado, enviando para:', `/api/v1/certificados-auxiliares/peso/${certificadoId}/upload-pdf`);
        
        const response = await fetch(`/api/v1/certificados-auxiliares/peso/${certificadoId}/upload-pdf`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${getToken()}`
            },
            body: formData
        });
        
        if (response.ok) {
            const resultado = await response.json();
            console.log('✅ Arquivo PDF enviado com sucesso:', resultado.filename);
            mostrarAlerta('Arquivo PDF enviado com sucesso!', 'success');
        } else {
            const error = await response.json();
            console.error('❌ Erro ao enviar arquivo PDF:', error);
            mostrarAlerta('Erro ao enviar arquivo PDF', 'error');
        }
    } catch (error) {
        console.error('❌ Erro ao enviar arquivo PDF:', error);
        mostrarAlerta('Erro ao enviar arquivo PDF', 'error');
    }
}

/**
 * Obtém o token de autenticação
 */
function getToken() {
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === 'pdv_automscale_token') {
            return value;
        }
    }
    return null;
}

/**
 * Mostra um alerta
 */
function mostrarAlerta(mensagem, tipo = 'info') {
    const container = document.getElementById('alert-container');
    if (!container) return;
    
    const alertClass = {
        'success': 'alert-success',
        'error': 'alert-danger',
        'warning': 'alert-warning',
        'info': 'alert-info'
    }[tipo] || 'alert-info';
    
    const alert = document.createElement('div');
    alert.className = `alert ${alertClass} alert-dismissible fade show`;
    alert.innerHTML = `
        ${mensagem}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    container.appendChild(alert);
    
    // Auto-remover após 5 segundos
    setTimeout(() => {
        if (alert.parentNode) {
            alert.remove();
        }
    }, 5000);
}

/**
 * Limpa o formulário
 */
function limparFormulario() {
    document.getElementById('formCertificadoPeso').reset();
    certificadoId = null;
    arquivoAtual = null;
    
    // Limpar arquivo atual se existir
    limparArquivoAtual();
    
    // Limpar título
    const titulo = document.querySelector('h1');
    if (titulo) {
        titulo.textContent = 'Cadastro de Certificado de Peso';
    }
} 


