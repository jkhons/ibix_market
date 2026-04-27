// ============================================================================
// ETAPA 3: RESPONSABILIDADES DO PROCESSO (Inspetor/Aprovador)
// Versão Simplificada - Responsáveis no nível do PROCESSO
// ============================================================================

// Variáveis globais para Etapa 3
let cadastrosInspetoresAprovadores = [];

/**
 * Obter cookie por nome (implementação local para evitar recursão com window.getCookie)
 */
function getCookieEtapa3(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) {
        return parts.pop().split(';').shift();
    }
    return null;
}

/**
 * Obter processoId de forma segura (global, URL ou null)
 */
function obterProcessoId() {
    // Tentar obter de window.processoId (variável global)
    if (window.processoId) {
        return window.processoId;
    }
    
    // Tentar obter da URL
    const urlParams = new URLSearchParams(window.location.search);
    const idFromUrl = urlParams.get('id');
    if (idFromUrl) {
        return parseInt(idFromUrl);
    }
    
    // Tentar obter de variável local (se disponível)
    if (typeof processoId !== 'undefined' && processoId !== null) {
        return processoId;
    }
    
    console.warn('⚠️ processoId não encontrado');
    return null;
}

// ============================================================================
// CARREGAMENTO INICIAL
// ============================================================================

/**
 * Carregar dados quando Etapa 3 for exibida
 */
async function carregarDadosEtapa3() {
    console.log('📋 Carregando dados da Etapa 3...');
    
    try {
        // Verificar se processoId está disponível
        const processoIdAtual = obterProcessoId();
        console.log('🔍 processoId obtido:', processoIdAtual);
        
        // Carregar lista de inspetores/aprovadores disponíveis
        await carregarCadastrosInspetoresAprovadores();
        
        // Carregar responsáveis já definidos no processo
        if (processoIdAtual) {
            await carregarResponsaveisExistentes();
        } else {
            console.warn('⚠️ processoId não disponível - pulando carregamento de responsáveis');
        }
        
        // Atualizar ícones do Feather (se disponível)
        if (typeof feather !== 'undefined' && typeof feather.replace === 'function') {
            feather.replace();
        }
        
        console.log('✅ Dados da Etapa 3 carregados com sucesso');
        
    } catch (error) {
        console.error('❌ Erro ao carregar dados da Etapa 3:', error);
        console.error('❌ Stack trace:', error.stack);
        alert('Erro ao carregar dados da Etapa 3: ' + (error.message || 'Erro desconhecido'));
    }
}

/**
 * Carregar cadastros de inspetores/aprovadores disponíveis
 */
async function carregarCadastrosInspetoresAprovadores() {
    try {
        const token = getCookieEtapa3('pdv_automscale_token');
        if (!token) {
            throw new Error('Token de autenticação não encontrado');
        }
        
        const response = await fetch('/api/v1/aux-cadastros/inspetores-aprovadores', {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            credentials: 'include'
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('❌ Erro na resposta:', response.status, errorText);
            
            // Tratar erro 401 (não autenticado)
            if (response.status === 401) {
                alert('⚠️ Sessão expirada. Por favor, faça login novamente.');
                window.location.href = '/login';
                return;
            }
            
            throw new Error(`Erro ao carregar inspetores/aprovadores: ${response.status}`);
        }
        
        const dados = await response.json();
        
        // Verificar se a resposta é um array
        if (!Array.isArray(dados)) {
            console.warn('⚠️ Resposta não é um array:', dados);
            cadastrosInspetoresAprovadores = [];
        } else {
            cadastrosInspetoresAprovadores = dados;
        }
        
        console.log('✅ Cadastros carregados:', cadastrosInspetoresAprovadores.length);
        
        // Popular selects
        popularSelectInspetor();
        popularSelectAprovador();
        
    } catch (error) {
        console.error('❌ Erro ao carregar cadastros:', error);
        console.error('❌ Stack trace:', error.stack);
        
        // Mostrar mensagem de erro mais amigável
        if (error.message.includes('Token')) {
            alert('⚠️ Erro de autenticação. Por favor, faça login novamente.');
            window.location.href = '/login';
        } else {
            alert('⚠️ Erro ao carregar lista de inspetores/aprovadores. Tente recarregar a página.');
        }
        
        throw error;
    }
}

/**
 * Popular select de inspetores
 */
function popularSelectInspetor() {
    const select = document.getElementById('selectInspetor');
    if (!select) {
        console.warn('⚠️ Select de inspetor não encontrado');
        return;
    }
    
    select.innerHTML = '<option value="">Selecione um inspetor...</option>';
    
    if (!Array.isArray(cadastrosInspetoresAprovadores) || cadastrosInspetoresAprovadores.length === 0) {
        console.warn('⚠️ Nenhum cadastro de inspetor/aprovador disponível');
        return;
    }
    
    cadastrosInspetoresAprovadores.forEach(cadastro => {
        const option = document.createElement('option');
        option.value = cadastro.id;
        const nome = cadastro.nome || cadastro.nome_titulo || 'Sem nome';
        const cpf = cadastro.cpf || '';
        option.textContent = cpf ? `${nome} (CPF: ${cpf})` : nome;
        select.appendChild(option);
    });
    
    console.log(`✅ ${cadastrosInspetoresAprovadores.length} inspetores/aprovadores adicionados ao select`);
}

/**
 * Popular select de aprovadores
 */
function popularSelectAprovador() {
    const select = document.getElementById('selectAprovador');
    if (!select) {
        console.warn('⚠️ Select de aprovador não encontrado');
        return;
    }
    
    select.innerHTML = '<option value="">Selecione um aprovador...</option>';
    
    if (!Array.isArray(cadastrosInspetoresAprovadores) || cadastrosInspetoresAprovadores.length === 0) {
        console.warn('⚠️ Nenhum cadastro de inspetor/aprovador disponível');
        return;
    }
    
    cadastrosInspetoresAprovadores.forEach(cadastro => {
        const option = document.createElement('option');
        option.value = cadastro.id;
        const nome = cadastro.nome || cadastro.nome_titulo || 'Sem nome';
        const cpf = cadastro.cpf || '';
        option.textContent = cpf ? `${nome} (CPF: ${cpf})` : nome;
        select.appendChild(option);
    });
    
    console.log(`✅ ${cadastrosInspetoresAprovadores.length} inspetores/aprovadores adicionados ao select`);
}

// ============================================================================
// RESPONSÁVEIS DO PROCESSO
// ============================================================================

/**
 * Carregar responsáveis já definidos no processo
 */
async function carregarResponsaveisExistentes() {
    try {
        const processoIdAtual = obterProcessoId();
        if (!processoIdAtual) {
            console.warn('⚠️ processoId não disponível - não é possível carregar responsáveis');
            return;
        }
        
        const token = getCookieEtapa3('pdv_automscale_token');
        const response = await fetch(`/api/v1/processos/${processoIdAtual}`, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            console.warn('⚠️ Não foi possível carregar responsáveis do processo');
            return;
        }
        
        const processo = await response.json();
        
        // Preencher selects com valores atuais
        const selectInspetor = document.getElementById('selectInspetor');
        const selectAprovador = document.getElementById('selectAprovador');
        
        if (processo.inspetor_aux_cadastro_id && selectInspetor) {
            selectInspetor.value = processo.inspetor_aux_cadastro_id;
            console.log('✅ Inspetor pré-selecionado:', processo.inspetor_aux_cadastro_id);
        }
        
        if (processo.aprovador_aux_cadastro_id && selectAprovador) {
            selectAprovador.value = processo.aprovador_aux_cadastro_id;
            console.log('✅ Aprovador pré-selecionado:', processo.aprovador_aux_cadastro_id);
        }
        
    } catch (error) {
        console.error('❌ Erro ao carregar responsáveis:', error);
    }
}

/**
 * Salvar responsáveis do processo
 */
async function salvarResponsaveisEtapa3() {
    const processoIdAtual = obterProcessoId();
    if (!processoIdAtual) {
        alert('⚠️ Erro: ID do processo não encontrado. Recarregue a página.');
        return false;
    }
    
    const inspetorId = document.getElementById('selectInspetor')?.value;
    const aprovadorId = document.getElementById('selectAprovador')?.value;
    
    if (!inspetorId || !aprovadorId) {
        alert('⚠️ Selecione inspetor e aprovador');
        return false;
    }
    
    try {
        const token = getCookieEtapa3('pdv_automscale_token');
        const response = await fetch(
            `/api/v1/processos/${processoIdAtual}/responsaveis`,
            {
                method: 'PATCH',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    inspetor_aux_cadastro_id: parseInt(inspetorId),
                    aprovador_aux_cadastro_id: parseInt(aprovadorId)
                })
            }
        );
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('❌ Erro na resposta:', response.status, errorText);
            throw new Error(`Erro ao salvar responsáveis: ${response.status}`);
        }
        
        console.log('✅ Responsáveis salvos com sucesso');
        return true;
        
    } catch (error) {
        console.error('❌ Erro ao salvar responsáveis:', error);
        alert('Erro ao salvar responsáveis: ' + error.message);
        return false;
    }
}

// ============================================================================
// VALIDAÇÕES
// ============================================================================

/**
 * Validar Etapa 3 antes de finalizar
 */
function validarEtapa3() {
    const inspetorId = document.getElementById('selectInspetor')?.value;
    const aprovadorId = document.getElementById('selectAprovador')?.value;
    
    if (!inspetorId) {
        alert('⚠️ Selecione um inspetor');
        return false;
    }
    
    if (!aprovadorId) {
        alert('⚠️ Selecione um aprovador');
        return false;
    }
    
    console.log('✅ Etapa 3 validada com sucesso');
    return true;
}

// ============================================================================
// INTEGRAÇÃO COM WIZARD
// ============================================================================

// Observer para detectar quando Etapa 3 é exibida
if (typeof MutationObserver !== 'undefined') {
    let etapa3Carregada = false; // Flag para evitar carregamento múltiplo
    
    const etapa3Observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
                const etapa3 = document.getElementById('etapa3');
                if (etapa3 && !etapa3.classList.contains('d-none') && !etapa3Carregada) {
                    // Etapa 3 foi exibida
                    console.log('👁️ Etapa 3 exibida - carregando dados');
                    etapa3Carregada = true;
                    carregarDadosEtapa3();
                } else if (etapa3 && etapa3.classList.contains('d-none')) {
                    // Etapa 3 foi ocultada - resetar flag
                    etapa3Carregada = false;
                }
            }
        });
    });
    
    // Observar mudanças na classe da Etapa 3
    function inicializarObserver() {
        const etapa3 = document.getElementById('etapa3');
        if (etapa3) {
            etapa3Observer.observe(etapa3, {
                attributes: true,
                attributeFilter: ['class']
            });
            console.log('✅ Observer da Etapa 3 inicializado');
            
            // Verificar se a etapa 3 já está visível ao carregar
            if (!etapa3.classList.contains('d-none') && !etapa3Carregada) {
                console.log('👁️ Etapa 3 já visível ao carregar - carregando dados');
                etapa3Carregada = true;
                carregarDadosEtapa3();
            }
        } else {
            console.warn('⚠️ Elemento #etapa3 não encontrado');
        }
    }
    
    // Inicializar quando o DOM estiver pronto
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', inicializarObserver);
    } else {
        // DOM já está pronto
        inicializarObserver();
    }
} else {
    console.warn('⚠️ MutationObserver não disponível - funcionalidade da Etapa 3 pode não funcionar corretamente');
}

console.log('✅ Script etapa3_certificado.js carregado (v2 simplificado)');
