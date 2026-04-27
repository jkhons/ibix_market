/**
 * PDV Ibix - JavaScript para Cadastro de Inspetores/Aprovadores
 * Gerencia o formulário de cadastro de inspetores e aprovadores
 */

// Variáveis globais
let inspetorId = null;
let modoEdicao = false;
let signaturePad = null;

// Inicialização quando o DOM estiver carregado
document.addEventListener('DOMContentLoaded', function() {
    configurarValidacoes();
    configurarEventos();
    verificarEdicao();
    configurarMascaras();
    configurarAssinatura();
});

/**
 * Configura as validações do formulário
 */
function configurarValidacoes() {
    const form = document.getElementById('formInspetor');
    
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        if (validarFormulario()) {
            await salvarInspetor();
        }
    });
}

/**
 * Configura os eventos da página
 */
function configurarEventos() {
    // Validação de CPF em tempo real
    document.getElementById('cpf').addEventListener('blur', function() {
        validarCPF(this.value);
    });
    
    // Validação de email em tempo real
    document.getElementById('email').addEventListener('blur', function() {
        validarEmail(this.value);
    });
    
    // Busca de CEP
    document.getElementById('cep').addEventListener('blur', function() {
        if (this.value.length === 9) {
            buscarCEP(this.value);
        }
    });
    
    // Validação de datas
    document.getElementById('dataValidadeCredenciamento').addEventListener('change', function() {
        validarDatasCredenciamento();
    });
}

/**
 * Configura as máscaras dos campos
 */
function configurarMascaras() {
    // Máscara para CPF
    const cpfInput = document.getElementById('cpf');
    cpfInput.addEventListener('input', function(e) {
        let value = e.target.value.replace(/\D/g, '');
        value = value.replace(/(\d{3})(\d)/, '$1.$2');
        value = value.replace(/(\d{3})(\d)/, '$1.$2');
        value = value.replace(/(\d{3})(\d{1,2})$/, '$1-$2');
        e.target.value = value;
    });
    
    // Máscara para telefone
    const telefoneInput = document.getElementById('telefone');
    telefoneInput.addEventListener('input', function(e) {
        let value = e.target.value.replace(/\D/g, '');
        value = value.replace(/(\d{2})(\d)/, '($1) $2');
        value = value.replace(/(\d{4})(\d)/, '$1-$2');
        e.target.value = value;
    });
    
    // Máscara para celular
    const celularInput = document.getElementById('celular');
    celularInput.addEventListener('input', function(e) {
        let value = e.target.value.replace(/\D/g, '');
        value = value.replace(/(\d{2})(\d)/, '($1) $2');
        value = value.replace(/(\d{5})(\d)/, '$1-$2');
        e.target.value = value;
    });
    
    // Máscara para CEP
    const cepInput = document.getElementById('cep');
    cepInput.addEventListener('input', function(e) {
        let value = e.target.value.replace(/\D/g, '');
        value = value.replace(/(\d{5})(\d)/, '$1-$2');
        e.target.value = value;
    });
}

/**
 * Verifica se está em modo de edição
 */
function verificarEdicao() {
    const path = window.location.pathname;
    const match = path.match(/\/certificados\/inspetores\/editar\/(\d+)/);
    
    if (match) {
        const id = match[1];
        modoEdicao = true;
        inspetorId = id;
        carregarInspetor(id);
        
        const titulo = document.querySelector('h1');
        if (titulo) {
            titulo.textContent = 'Editar Inspetor/Aprovador';
        }
    }
}

/**
 * Carrega dados do inspetor para edição
 */
async function carregarInspetor(id) {
    try {
        const response = await fetch(`/api/v1/inspetores-aprovadores/${id}`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('pdv_automscale_token')}`
            }
        });
        
        if (!response.ok) {
            throw new Error(`Erro HTTP: ${response.status}`);
        }
        
        const inspetor = await response.json();
        preencherFormulario(inspetor);
        
    } catch (error) {
        console.error('Erro ao carregar inspetor:', error);
        mostrarAlerta('Erro ao carregar dados do inspetor', 'danger');
    }
}

/**
 * Preenche o formulário com os dados do inspetor
 */
function preencherFormulario(inspetor) {
    // Dados pessoais
    document.getElementById('nome').value = inspetor.nome || '';
    document.getElementById('cpf').value = inspetor.cpf || '';
    document.getElementById('rg').value = inspetor.rg || '';
    document.getElementById('dataNascimento').value = inspetor.data_nascimento || '';
    document.getElementById('sexo').value = inspetor.sexo || '';
    
    // Contato
    document.getElementById('email').value = inspetor.email || '';
    document.getElementById('telefone').value = inspetor.telefone || '';
    document.getElementById('celular').value = inspetor.celular || '';
    
    // Endereço
    document.getElementById('cep').value = inspetor.cep || '';
    document.getElementById('endereco').value = inspetor.endereco || '';
    document.getElementById('numero').value = inspetor.numero || '';
    document.getElementById('complemento').value = inspetor.complemento || '';
    document.getElementById('bairro').value = inspetor.bairro || '';
    document.getElementById('cidade').value = inspetor.cidade || '';
    document.getElementById('uf').value = inspetor.uf || '';
    
    // Dados profissionais
    document.getElementById('cargo').value = inspetor.cargo || '';
    document.getElementById('tipo').value = inspetor.tipo || '';
    document.getElementById('registroProfissional').value = inspetor.registro_profissional || '';
    document.getElementById('orgaoRegistro').value = inspetor.orgao_registro || '';
    document.getElementById('dataCredenciamento').value = inspetor.data_credenciamento || '';
    document.getElementById('dataValidadeCredenciamento').value = inspetor.data_validade_credenciamento || '';
    document.getElementById('especialidades').value = inspetor.especialidades || '';
    document.getElementById('areasAtuacao').value = inspetor.areas_atuacao || '';
    
    // Assinatura
    document.getElementById('chavePublica').value = inspetor.chave_publica || '';
    
    // Status
    document.getElementById('ativo').checked = inspetor.ativo !== false;
    
    // Carregar assinatura digital se existir
    if (inspetor.assinatura_digital) {
        const imgPath = `/static/docs/assinaturas/${inspetor.assinatura_digital}`;
        
        // Mostrar preview da assinatura
        document.getElementById('imgAssinatura').src = imgPath;
        document.getElementById('previewAssinatura').style.display = 'block';
        
        // Atualizar status
        document.getElementById('statusAssinatura').textContent = 'Assinatura cadastrada ✓';
        document.getElementById('statusAssinatura').className = 'ms-2 text-success';
    }
}

/**
 * Valida o formulário
 */
function validarFormulario() {
    let valido = true;
    
    // Campos obrigatórios
    const camposObrigatorios = ['nome', 'cpf', 'email', 'cargo', 'tipo'];
    
    camposObrigatorios.forEach(campo => {
        const elemento = document.getElementById(campo);
        if (!elemento.value.trim()) {
            mostrarErroCampo(elemento, 'Este campo é obrigatório');
            valido = false;
        } else {
            limparErroCampo(elemento);
        }
    });
    
    // Validações específicas
    if (!validarCPF(document.getElementById('cpf').value)) {
        valido = false;
    }
    
    if (!validarEmail(document.getElementById('email').value)) {
        valido = false;
    }
    
    if (!validarDatasCredenciamento()) {
        valido = false;
    }
    
    return valido;
}

/**
 * Valida CPF
 */
function validarCPF(cpf) {
    const cpfLimpo = cpf.replace(/\D/g, '');
    
    if (cpfLimpo.length !== 11) {
        mostrarErroCampo(document.getElementById('cpf'), 'CPF deve ter 11 dígitos');
        return false;
    }
    
    // Verifica se todos os dígitos são iguais
    if (cpfLimpo === cpfLimpo[0].repeat(11)) {
        mostrarErroCampo(document.getElementById('cpf'), 'CPF inválido');
        return false;
    }
    
    // Validação dos dígitos verificadores
    let soma = 0;
    for (let i = 0; i < 9; i++) {
        soma += parseInt(cpfLimpo[i]) * (10 - i);
    }
    let resto = soma % 11;
    let digito1 = resto < 2 ? 0 : 11 - resto;
    
    soma = 0;
    for (let i = 0; i < 10; i++) {
        soma += parseInt(cpfLimpo[i]) * (11 - i);
    }
    resto = soma % 11;
    let digito2 = resto < 2 ? 0 : 11 - resto;
    
    if (cpfLimpo.slice(-2) !== `${digito1}${digito2}`) {
        mostrarErroCampo(document.getElementById('cpf'), 'CPF inválido');
        return false;
    }
    
    limparErroCampo(document.getElementById('cpf'));
    return true;
}

/**
 * Valida email
 */
function validarEmail(email) {
    const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    
    if (!regex.test(email)) {
        mostrarErroCampo(document.getElementById('email'), 'Email inválido');
        return false;
    }
    
    limparErroCampo(document.getElementById('email'));
    return true;
}

/**
 * Valida datas de credenciamento
 */
function validarDatasCredenciamento() {
    const dataCredenciamento = document.getElementById('dataCredenciamento').value;
    const dataValidade = document.getElementById('dataValidadeCredenciamento').value;
    
    if (dataCredenciamento && dataValidade) {
        if (new Date(dataValidade) <= new Date(dataCredenciamento)) {
            mostrarErroCampo(document.getElementById('dataValidadeCredenciamento'), 'Data de validade deve ser posterior à data de credenciamento');
            return false;
        }
    }
    
    limparErroCampo(document.getElementById('dataValidadeCredenciamento'));
    return true;
}

/**
 * Busca CEP
 */
async function buscarCEP(cep) {
    try {
        const cepLimpo = cep.replace(/\D/g, '');
        const response = await fetch(`https://viacep.com.br/ws/${cepLimpo}/json/`);
        
        if (!response.ok) {
            throw new Error(`Erro HTTP: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.erro) {
            mostrarAlerta('CEP não encontrado', 'warning');
            return;
        }
        
        document.getElementById('endereco').value = data.logradouro || '';
        document.getElementById('bairro').value = data.bairro || '';
        document.getElementById('cidade').value = data.localidade || '';
        document.getElementById('uf').value = data.uf || '';
        
    } catch (error) {
        console.error('Erro ao buscar CEP:', error);
        mostrarAlerta('Erro ao buscar CEP', 'warning');
    }
}

/**
 * Salva o inspetor
 */
async function salvarInspetor() {
    try {
        const formData = new FormData(document.getElementById('formInspetor'));
        const dados = {};
        
        for (let [key, value] of formData.entries()) {
            if (key === 'assinatura_digital' || key === 'certificado_digital' || key === 'assinatura_base64') continue;
            dados[key] = value.trim() === '' ? null : value.trim();
        }
        
        dados.ativo = document.getElementById('ativo').checked;
        dados.nome = document.getElementById('nome').value.trim();
        dados.cpf = document.getElementById('cpf').value.trim();
        dados.email = document.getElementById('email').value.trim();
        dados.cargo = document.getElementById('cargo').value.trim();
        dados.tipo = document.getElementById('tipo').value;
        
        const url = modoEdicao 
            ? `/api/v1/inspetores-aprovadores/${inspetorId}`
            : '/api/v1/inspetores-aprovadores';
        
        const method = modoEdicao ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method: method,
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('pdv_automscale_token')}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(dados)
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            
            let errorMessage = 'Erro ao salvar';
            if (typeof errorData.detail === 'string') {
                errorMessage = errorData.detail;
            } else if (Array.isArray(errorData.detail)) {
                errorMessage = errorData.detail.map(e => `${e.loc?.join('.')}: ${e.msg}`).join('; ');
            } else if (errorData.detail) {
                errorMessage = JSON.stringify(errorData.detail);
            }
            
            throw new Error(errorMessage);
        }
        
        const inspetor = await response.json();
        const inspetorIdSalvo = inspetor.id || inspetorId;
        
        // Se tem assinatura capturada, enviar separadamente
        const assinaturaBase64 = document.getElementById('assinaturaBase64').value;
        if (assinaturaBase64 && inspetorIdSalvo) {
            await salvarAssinaturaDigital(inspetorIdSalvo, assinaturaBase64);
        }
        
        mostrarAlerta(`Inspetor ${modoEdicao ? 'atualizado' : 'cadastrado'} com sucesso!`, 'success');
        
        setTimeout(() => {
            window.location.href = '/certificados/inspetores';
        }, 1500);
        
    } catch (error) {
        console.error('Erro ao salvar inspetor:', error);
        mostrarAlerta(`Erro ao ${modoEdicao ? 'atualizar' : 'cadastrar'} inspetor: ${error.message}`, 'danger');
    }
}

/**
 * Salva assinatura digital do inspetor
 */
async function salvarAssinaturaDigital(inspetorId, dataURL) {
    try {
        const response = await fetch(`/api/v1/inspetores-aprovadores/${inspetorId}/salvar-assinatura`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('pdv_automscale_token')}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                assinatura_base64: dataURL
            })
        });
        
        if (!response.ok) {
            throw new Error('Erro ao salvar assinatura');
        }
        
        return true;
    } catch (error) {
        console.error('Erro ao salvar assinatura:', error);
        return false;
    }
}

/**
 * Funções auxiliares para validação
 */
function mostrarErroCampo(elemento, mensagem) {
    limparErroCampo(elemento);
    
    elemento.classList.add('is-invalid');
    
    const feedback = document.createElement('div');
    feedback.className = 'invalid-feedback';
    feedback.textContent = mensagem;
    
    elemento.parentNode.appendChild(feedback);
}

function limparErroCampo(elemento) {
    elemento.classList.remove('is-invalid');
    
    const feedback = elemento.parentNode.querySelector('.invalid-feedback');
    if (feedback) {
        feedback.remove();
    }
}

function mostrarAlerta(mensagem, tipo) {
    alert(mensagem);
}

// ===== GERENCIAMENTO DE ASSINATURA DIGITAL (ISOLADO) =====

function configurarAssinatura() {
    // Não usa Bootstrap Modal - totalmente isolado
}

function abrirModalAssinatura() {
    const modal = document.getElementById('modalAssinaturaCustom');
    const canvas = document.getElementById('canvasAssinaturaCustom');
    
    // Mostrar modal
    modal.classList.add('show');
    
    // Configurar canvas
    canvas.width = 560;
    canvas.height = 200;
    
    // Criar Signature Pad
    signaturePad = new SignaturePad(canvas, {
        backgroundColor: 'rgb(255, 255, 255)',
        penColor: 'rgb(0, 0, 139)',
        minWidth: 1,
        maxWidth: 2.5
    });
    
    // Atualizar ícones
    if (typeof feather !== 'undefined') {
        feather.replace();
    }
}

function fecharModalAssinatura() {
    const modal = document.getElementById('modalAssinaturaCustom');
    modal.classList.remove('show');
    
    if (signaturePad) {
        signaturePad.clear();
        signaturePad = null;
    }
}

function limparAssinaturaCustom() {
    if (signaturePad) {
        signaturePad.clear();
    }
}

function confirmarAssinaturaCustom() {
    if (!signaturePad || signaturePad.isEmpty()) {
        alert('Por favor, assine antes de confirmar');
        return;
    }
    
    // Converter para PNG base64
    const dataURL = signaturePad.toDataURL('image/png');
    
    // Salvar no campo hidden
    document.getElementById('assinaturaBase64').value = dataURL;
    
    // Atualizar status
    document.getElementById('statusAssinatura').textContent = 'Assinatura capturada ✓';
    document.getElementById('statusAssinatura').className = 'ms-2 text-success';
    
    // Mostrar preview
    document.getElementById('imgAssinatura').src = dataURL;
    document.getElementById('previewAssinatura').style.display = 'block';
    
    // Fechar modal
    fecharModalAssinatura();
} 