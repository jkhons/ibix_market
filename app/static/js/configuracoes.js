// PDV Ibix - Configurações Manager

// ===== FUNÇÕES DE E-MAIL =====

// Carregar configurações de e-mail
async function carregarConfiguracoesEmail() {
    try {
        const response = await fetch('/api/v1/configuracoes/email/', {
            credentials: 'include'
        });
        
        if (response.ok) {
            const configs = await response.json();
            
            document.getElementById('emailHost').value = configs.email_host || '';
            document.getElementById('emailPort').value = configs.email_port || '';
            document.getElementById('emailUsername').value = configs.email_username || '';
            document.getElementById('emailPassword').value = configs.email_password || '';
            document.getElementById('emailFrom').value = configs.email_from || '';
            document.getElementById('emailFromName').value = configs.email_from_name || '';
            document.getElementById('emailUseTLS').checked = configs.email_use_tls === 'true';
            document.getElementById('emailUseSSL').checked = configs.email_use_ssl === 'true';
        }
    } catch (error) {
        console.error('Erro ao carregar configurações de e-mail:', error);
    }
}

// Salvar configurações de e-mail
async function salvarConfiguracoesEmail(event) {
    event.preventDefault();
    
    const configs = {
        email_host: document.getElementById('emailHost').value,
        email_port: document.getElementById('emailPort').value,
        email_username: document.getElementById('emailUsername').value,
        email_password: document.getElementById('emailPassword').value,
        email_from: document.getElementById('emailFrom').value,
        email_from_name: document.getElementById('emailFromName').value,
        email_use_tls: document.getElementById('emailUseTLS').checked ? 'true' : 'false',
        email_use_ssl: document.getElementById('emailUseSSL').checked ? 'true' : 'false'
    };
    
    mostrarAlerta('Salvando configurações...', 'info');
    
    try {
        const response = await fetch('/api/v1/configuracoes/email/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify(configs)
        });
        
        if (response.ok) {
            const result = await response.json();
            mostrarAlerta('Configurações de e-mail salvas com sucesso!', 'success');
        } else {
            const error = await response.json();
            mostrarAlerta('Erro ao salvar configurações: ' + (error.detail || 'Erro desconhecido'), 'danger');
        }
    } catch (error) {
        console.error('Erro ao salvar configurações:', error);
        mostrarAlerta('Erro ao salvar configurações: ' + error.message, 'danger');
    }
}

// Testar conexão com servidor SMTP
async function testarConexaoEmail() {
    mostrarAlerta('Testando conexão com servidor SMTP...', 'info');
    
    try {
        const response = await fetch('/api/v1/configuracoes/email/test-connection/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include'
        });
        
        if (!response.ok) {
            mostrarAlerta('Erro ao testar conexão: ' + response.statusText, 'danger');
            return;
        }
        
        const result = await response.json();
        
        if (result.success) {
            mostrarAlerta(result.message, 'success');
        } else {
            mostrarAlerta(result.message, 'danger');
        }
    } catch (error) {
        console.error('Erro ao testar conexão:', error);
        mostrarAlerta('Erro ao testar conexão: ' + error.message, 'danger');
    }
}

// ===== E-MAIL POR FUNÇÃO =====

// Carregar configurações de e-mail por função
async function carregarConfiguracoesEmailFuncoes() {
    const container = document.getElementById('email-funcoes-container');
    if (!container) return;

    try {
        const response = await fetch('/api/v1/configuracoes/email/funcoes/', { credentials: 'include' });
        if (!response.ok) {
            container.innerHTML = '<div class="alert alert-danger">Erro ao carregar configurações.</div>';
            return;
        }
        const data = await response.json();
        const funcoes = data.funcoes || [];

        let html = '<div class="table-responsive"><table class="table table-sm table-bordered">';
        html += '<thead><tr><th>Função</th><th>E-mail remetente</th><th>Nome remetente</th></tr></thead><tbody>';
        funcoes.forEach(function (f) {
            const idFrom = 'emailFuncaoFrom_' + f.codigo;
            const idName = 'emailFuncaoName_' + f.codigo;
            const desc = f.descricao ? ' title="' + (f.descricao || '').replace(/"/g, '&quot;') + '"' : '';
            html += '<tr' + desc + '>';
            html += '<td class="align-middle"><strong>' + (f.label || f.codigo) + '</strong></td>';
            html += '<td><input type="email" class="form-control form-control-sm" id="' + idFrom + '" data-codigo="' + f.codigo + '" placeholder="Deixe vazio para usar o geral" value="' + (f.from_email || '').replace(/"/g, '&quot;') + '"></td>';
            html += '<td><input type="text" class="form-control form-control-sm" id="' + idName + '" data-codigo="' + f.codigo + '" placeholder="Nome" value="' + (f.from_name || '').replace(/"/g, '&quot;') + '"></td>';
            html += '</tr>';
        });
        html += '</tbody></table></div>';
        container.innerHTML = html;

        if (typeof feather !== 'undefined') feather.replace();
    } catch (error) {
        console.error('Erro ao carregar e-mail por função:', error);
        container.innerHTML = '<div class="alert alert-danger">Erro ao carregar configurações.</div>';
    }
}

// ===== E-MAIL SEPARADO POR CLIENTE (Super Admin) =====

async function carregarEmailSeparadoPorCliente() {
    const checkbox = document.getElementById('emailSeparadoPorClienteAtivo');
    if (!checkbox) return;
    try {
        const response = await fetch('/api/v1/configuracoes/email/separado-por-cliente/', { credentials: 'include' });
        if (response.ok) {
            const data = await response.json();
            checkbox.checked = data.ativo === true;
        }
    } catch (error) {
        console.error('Erro ao carregar flag e-mail separado por cliente:', error);
    }
}

async function salvarEmailSeparadoPorCliente() {
    const checkbox = document.getElementById('emailSeparadoPorClienteAtivo');
    if (!checkbox) return;
    mostrarAlerta('Salvando...', 'info');
    try {
        const response = await fetch('/api/v1/configuracoes/email/separado-por-cliente/', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ ativo: checkbox.checked })
        });
        if (response.ok) {
            mostrarAlerta('Configuração salva com sucesso.', 'success');
        } else {
            const err = await response.json();
            mostrarAlerta('Erro: ' + (err.detail || response.statusText), 'danger');
        }
    } catch (error) {
        console.error('Erro ao salvar:', error);
        mostrarAlerta('Erro ao salvar: ' + error.message, 'danger');
    }
}

// Salvar configurações de e-mail por função
async function salvarConfiguracoesEmailFuncoes() {
    const container = document.getElementById('email-funcoes-container');
    if (!container) return;

    const inputsFrom = container.querySelectorAll('input[data-codigo][type="email"]');
    const codigos = Array.from(inputsFrom).map(function (el) { return el.getAttribute('data-codigo'); });
    const funcoes = codigos.map(function (codigo) {
        const fromEl = document.getElementById('emailFuncaoFrom_' + codigo);
        const nameEl = document.getElementById('emailFuncaoName_' + codigo);
        return {
            codigo: codigo,
            from_email: fromEl ? fromEl.value.trim() : '',
            from_name: nameEl ? nameEl.value.trim() : ''
        };
    });

    mostrarAlerta('Salvando e-mail por função...', 'info');

    try {
        const response = await fetch('/api/v1/configuracoes/email/funcoes/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ funcoes: funcoes })
        });

        if (response.ok) {
            mostrarAlerta('Configurações de e-mail por função salvas com sucesso!', 'success');
            carregarConfiguracoesEmailFuncoes();
        } else {
            const err = await response.json();
            mostrarAlerta('Erro ao salvar: ' + (err.detail || 'Erro desconhecido'), 'danger');
        }
    } catch (error) {
        console.error('Erro ao salvar e-mail por função:', error);
        mostrarAlerta('Erro ao salvar: ' + error.message, 'danger');
    }
}

// Enviar e-mail de teste
async function enviarEmailTeste() {
    const emailDestino = prompt('Digite o e-mail de destino para o teste:');
    
    if (!emailDestino) {
        return;
    }
    
    // Validar e-mail
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(emailDestino)) {
        mostrarAlerta('E-mail inválido!', 'danger');
        return;
    }
    
    mostrarAlerta('Enviando e-mail de teste...', 'info');
    
    try {
        const response = await fetch('/api/v1/configuracoes/email/send-test/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({ to: emailDestino })
        });
        
        if (!response.ok) {
            mostrarAlerta('Erro ao enviar e-mail: ' + response.statusText, 'danger');
            return;
        }
        
        const result = await response.json();
        
        if (result.success) {
            mostrarAlerta('E-mail de teste enviado com sucesso para ' + emailDestino, 'success');
        } else {
            mostrarAlerta('Erro ao enviar e-mail: ' + result.message, 'danger');
        }
    } catch (error) {
        console.error('Erro ao enviar e-mail:', error);
        mostrarAlerta('Erro ao enviar e-mail: ' + error.message, 'danger');
    }
}

// Função para mostrar alertas
function mostrarAlerta(mensagem, tipo = 'info') {
    const container = document.getElementById('alert-container');
    if (!container) return;
    
    const alerta = document.createElement('div');
    alerta.className = `alert alert-${tipo} alert-dismissible fade show mt-3`;
    alerta.role = 'alert';
    alerta.innerHTML = `
        ${mensagem}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    container.appendChild(alerta);
    
    // Remover após 5 segundos
    setTimeout(() => {
        alerta.remove();
    }, 5000);
}

// Configurar event listeners quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', function() {
    // ===== CONFIGURAÇÕES DE E-MAIL =====
    
    // Configurar formulário de e-mail
    const formEmail = document.getElementById('formConfigEmail');
    if (formEmail) {
        formEmail.addEventListener('submit', salvarConfiguracoesEmail);
    }
    
    // Carregar configurações de e-mail
    carregarConfiguracoesEmail();
    carregarConfiguracoesEmailFuncoes();
    carregarEmailSeparadoPorCliente();

    // Botão salvar e-mail separado por cliente (Super Admin)
    const btnSalvarEmailSeparadoPorCliente = document.getElementById('btnSalvarEmailSeparadoPorCliente');
    if (btnSalvarEmailSeparadoPorCliente) {
        btnSalvarEmailSeparadoPorCliente.addEventListener('click', salvarEmailSeparadoPorCliente);
    }

    // Botão salvar e-mail por função
    const btnSalvarEmailFuncoes = document.getElementById('btnSalvarEmailFuncoes');
    if (btnSalvarEmailFuncoes) {
        btnSalvarEmailFuncoes.addEventListener('click', salvarConfiguracoesEmailFuncoes);
    }
    
    // Botão toggle senha
    const togglePassword = document.getElementById('toggleEmailPassword');
    if (togglePassword) {
        togglePassword.addEventListener('click', function() {
            const passwordInput = document.getElementById('emailPassword');
            const icon = this.querySelector('i');
            
            if (passwordInput.type === 'password') {
                passwordInput.type = 'text';
                icon.setAttribute('data-feather', 'eye-off');
            } else {
                passwordInput.type = 'password';
                icon.setAttribute('data-feather', 'eye');
            }
            
            if (typeof feather !== 'undefined') {
                feather.replace();
            }
        });
    }
    
    // Botão testar conexão
    const btnTestarConexao = document.getElementById('btnTestarConexaoEmail');
    if (btnTestarConexao) {
        btnTestarConexao.addEventListener('click', testarConexaoEmail);
    }
    
    // Botão enviar e-mail de teste
    const btnEnviarTeste = document.getElementById('btnEnviarEmailTeste');
    if (btnEnviarTeste) {
        btnEnviarTeste.addEventListener('click', enviarEmailTeste);
    }
    
    // Carregar configurações de alertas
    carregarConfiguracoesAlertas();
});

// ===== FUNÇÕES DE ALERTAS E NOTIFICAÇÕES =====

// Carregar configurações de alertas
async function carregarConfiguracoesAlertas() {
    try {
        const response = await fetch('/api/v1/configuracoes/alertas/', {
            credentials: 'include'
        });
        
        if (response.ok) {
            const configs = await response.json();
            
            // Preencher campos de prazos de certificados
            if (document.getElementById('prazoCertAlerta')) {
                document.getElementById('prazoCertAlerta').value = configs.prazo_cert_alerta;
            }
            if (document.getElementById('prazoCertCritico')) {
                document.getElementById('prazoCertCritico').value = configs.prazo_cert_critico;
            }
            
            // Preencher campos de prazos de contratos
            if (document.getElementById('prazoContratoAlerta')) {
                document.getElementById('prazoContratoAlerta').value = configs.prazo_contrato_alerta;
            }
            if (document.getElementById('prazoContratoCritico')) {
                document.getElementById('prazoContratoCritico').value = configs.prazo_contrato_critico;
            }
            
            // Preencher campos de janelas temporais
            if (document.getElementById('janelaNovosAgendamentos')) {
                document.getElementById('janelaNovosAgendamentos').value = configs.janela_novos_agendamentos;
            }
            if (document.getElementById('intervaloAtualizacao')) {
                document.getElementById('intervaloAtualizacao').value = configs.intervalo_atualizacao;
            }
            
            // Preencher switches de notificações
            if (document.getElementById('notifAgendamentoHoje')) {
                document.getElementById('notifAgendamentoHoje').checked = configs.notif_agendamento_hoje;
            }
            if (document.getElementById('notifNovoAgendamento')) {
                document.getElementById('notifNovoAgendamento').checked = configs.notif_novo_agendamento;
            }
            if (document.getElementById('notifCertificadoVencendo')) {
                document.getElementById('notifCertificadoVencendo').checked = configs.notif_certificado_vencendo;
            }
            if (document.getElementById('notifContratoVencendo')) {
                document.getElementById('notifContratoVencendo').checked = configs.notif_contrato_vencendo;
            }
            
            console.log('✅ Configurações de alertas carregadas:', configs);
        }
    } catch (error) {
        console.error('Erro ao carregar configurações de alertas:', error);
    }
}

// Salvar configurações de alertas
async function salvarConfiguracoesAlertasAPI() {
    const configs = {
        prazo_cert_alerta: parseInt(document.getElementById('prazoCertAlerta').value),
        prazo_cert_critico: parseInt(document.getElementById('prazoCertCritico').value),
        prazo_contrato_alerta: parseInt(document.getElementById('prazoContratoAlerta').value),
        prazo_contrato_critico: parseInt(document.getElementById('prazoContratoCritico').value),
        janela_novos_agendamentos: parseInt(document.getElementById('janelaNovosAgendamentos').value),
        intervalo_atualizacao: parseInt(document.getElementById('intervaloAtualizacao').value),
        notif_agendamento_hoje: document.getElementById('notifAgendamentoHoje').checked,
        notif_novo_agendamento: document.getElementById('notifNovoAgendamento').checked,
        notif_certificado_vencendo: document.getElementById('notifCertificadoVencendo').checked,
        notif_contrato_vencendo: document.getElementById('notifContratoVencendo').checked
    };
    
    mostrarAlerta('Salvando configurações de alertas...', 'info');
    
    try {
        const response = await fetch('/api/v1/configuracoes/alertas/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify(configs)
        });
        
        if (response.ok) {
            const result = await response.json();
            mostrarAlerta('✅ Configurações de alertas salvas com sucesso!', 'success');
            
            // Recarregar configurações para garantir sincronização
            setTimeout(() => carregarConfiguracoesAlertas(), 500);
        } else {
            const error = await response.json();
            mostrarAlerta('❌ Erro ao salvar: ' + (error.detail || 'Erro desconhecido'), 'danger');
        }
    } catch (error) {
        console.error('Erro ao salvar configurações:', error);
        mostrarAlerta('❌ Erro ao salvar: ' + error.message, 'danger');
    }
}

// Disponibilizar função globalmente para o botão HTML
window.salvarConfiguracoesAlertas = salvarConfiguracoesAlertasAPI;

// ===== CONFIGURAÇÕES WHATSAPP (apenas Superadministrador) =====
async function carregarConfiguracoesWhatsApp() {
    const elAtivo = document.getElementById('whatsappAtivo');
    if (!elAtivo) return;
    try {
        const response = await fetch('/api/v1/configuracoes/whatsapp/', { credentials: 'include' });
        if (response.status === 403) return;
        if (!response.ok) return;
        const data = await response.json();
        elAtivo.checked = data.ativo === true;
        const elPhone = document.getElementById('whatsappPhoneNumberId');
        if (elPhone) elPhone.value = data.phone_number_id || '';
        const elVerify = document.getElementById('whatsappVerifyToken');
        if (elVerify) elVerify.value = data.verify_token === '••••••••' ? '' : (data.verify_token || '');
        const elBusiness = document.getElementById('whatsappBusinessAccountId');
        if (elBusiness) elBusiness.value = data.business_account_id || '';
        const elToken = document.getElementById('whatsappToken');
        if (elToken) elToken.placeholder = data.token_preenchido ? '•••••••• (deixe em branco para não alterar)' : '••••••••';
    } catch (e) {
        console.error('Erro ao carregar configurações WhatsApp:', e);
    }
}

async function salvarConfiguracoesWhatsApp(event) {
    if (event) event.preventDefault();
    const elAtivo = document.getElementById('whatsappAtivo');
    if (!elAtivo) return;
    const body = {
        ativo: elAtivo.checked,
        phone_number_id: document.getElementById('whatsappPhoneNumberId')?.value?.trim() || null,
        verify_token: document.getElementById('whatsappVerifyToken')?.value?.trim() || null,
        business_account_id: document.getElementById('whatsappBusinessAccountId')?.value?.trim() || null
    };
    const tokenEl = document.getElementById('whatsappToken');
    if (tokenEl && tokenEl.value) body.token = tokenEl.value;
    try {
        const response = await fetch('/api/v1/configuracoes/whatsapp/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(body)
        });
        if (response.ok) {
            if (typeof mostrarAlerta === 'function') mostrarAlerta('Configurações WhatsApp salvas.', 'success');
            carregarConfiguracoesWhatsApp();
            if (tokenEl) tokenEl.value = '';
        } else {
            const err = await response.json();
            if (typeof mostrarAlerta === 'function') mostrarAlerta('Erro: ' + (err.detail || 'Erro ao salvar'), 'danger');
        }
    } catch (e) {
        console.error('Erro ao salvar WhatsApp:', e);
        if (typeof mostrarAlerta === 'function') mostrarAlerta('Erro ao salvar: ' + e.message, 'danger');
    }
}

// ===== PROVEDOR FISCAL (único para o sistema; apenas Superadministrador) =====
async function carregarConfiguracoesFiscalProvedor() {
    const form = document.getElementById('formFiscalProvedor');
    if (!form) return;
    try {
        const response = await fetch('/api/v1/configuracoes/fiscal-provedor/', { credentials: 'include' });
        if (response.status === 403) return;
        if (!response.ok) return;
        const data = await response.json();
        const elProvedor = document.getElementById('fiscalProvedor');
        if (elProvedor) elProvedor.value = data.provedor || '';
        const elNfe = document.getElementById('fiscalSerieNfe');
        if (elNfe) elNfe.value = data.serie_padrao_nfe || '';
        const elNfce = document.getElementById('fiscalSerieNfce');
        if (elNfce) elNfce.value = data.serie_padrao_nfce || '';
        // API key/secret não são retornados por segurança
    } catch (e) {
        console.error('Erro ao carregar provedor fiscal:', e);
    }
}

async function salvarConfiguracoesFiscalProvedor(event) {
    if (event) event.preventDefault();
    const form = document.getElementById('formFiscalProvedor');
    if (!form) return;
    const body = {
        provedor: document.getElementById('fiscalProvedor')?.value?.trim() || null,
        serie_padrao_nfe: document.getElementById('fiscalSerieNfe')?.value?.trim() || null,
        serie_padrao_nfce: document.getElementById('fiscalSerieNfce')?.value?.trim() || null
    };
    const apiKey = document.getElementById('fiscalProvedorApiKey')?.value?.trim();
    const apiSecret = document.getElementById('fiscalProvedorApiSecret')?.value?.trim();
    if (apiKey) body.provedor_api_key = apiKey;
    if (apiSecret) body.provedor_api_secret = apiSecret;
    try {
        const response = await fetch('/api/v1/configuracoes/fiscal-provedor/', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(body)
        });
        if (response.ok) {
            if (typeof mostrarAlerta === 'function') mostrarAlerta('Provedor fiscal salvo.', 'success');
            carregarConfiguracoesFiscalProvedor();
            const elSecret = document.getElementById('fiscalProvedorApiSecret');
            if (elSecret) elSecret.value = '';
        } else {
            const err = await response.json();
            if (typeof mostrarAlerta === 'function') mostrarAlerta('Erro: ' + (err.detail || 'Erro ao salvar'), 'danger');
        }
    } catch (e) {
        console.error('Erro ao salvar provedor fiscal:', e);
        if (typeof mostrarAlerta === 'function') mostrarAlerta('Erro ao salvar: ' + e.message, 'danger');
    }
}

// Atualizar se DOM já estiver pronto
if (document.readyState !== 'loading') {
    carregarConfiguracoesAlertas();
    carregarConfiguracoesWhatsApp();
    carregarConfiguracoesFiscalProvedor();
}

async function carregarMarketplaceNap() {
    const form = document.getElementById('formMarketplaceNap');
    if (!form) return;
    try {
        const response = await window.authenticatedFetch('/api/v1/configuracoes/marketplace-nap/');
        if (!response.ok) return;
        const data = await response.json();
        const fields = ['marketplace_nome', 'marketplace_endereco', 'marketplace_cidade', 'marketplace_uf', 'marketplace_cep', 'marketplace_telefone'];
        const ids = ['napNome', 'napEndereco', 'napCidade', 'napUf', 'napCep', 'napTelefone'];
        for (let i = 0; i < fields.length; i++) {
            const el = document.getElementById(ids[i]);
            if (el) el.value = data[fields[i]] || '';
        }
    } catch (e) {
        console.error('Erro ao carregar NAP:', e);
    }
}

async function salvarMarketplaceNap(e) {
    e.preventDefault();
    try {
        const body = {
            marketplace_nome: document.getElementById('napNome')?.value?.trim() || '',
            marketplace_endereco: document.getElementById('napEndereco')?.value?.trim() || '',
            marketplace_cidade: document.getElementById('napCidade')?.value?.trim() || '',
            marketplace_uf: (document.getElementById('napUf')?.value?.trim() || '').toUpperCase(),
            marketplace_cep: document.getElementById('napCep')?.value?.trim() || '',
            marketplace_telefone: document.getElementById('napTelefone')?.value?.trim() || '',
        };
        const response = await window.authenticatedFetch('/api/v1/configuracoes/marketplace-nap/', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        const status = document.getElementById('napSaveStatus');
        if (response.ok) {
            if (status) { status.style.display = 'inline'; setTimeout(function() { status.style.display = 'none'; }, 3000); }
            if (typeof mostrarAlerta === 'function') mostrarAlerta('Dados NAP salvos com sucesso.', 'success');
        } else {
            const err = await response.json();
            if (typeof mostrarAlerta === 'function') mostrarAlerta('Erro: ' + (err.detail || 'Erro ao salvar'), 'danger');
        }
    } catch (e) {
        console.error('Erro ao salvar NAP:', e);
        if (typeof mostrarAlerta === 'function') mostrarAlerta('Erro ao salvar: ' + e.message, 'danger');
    }
}

document.addEventListener('DOMContentLoaded', function() {
    const formWhatsApp = document.getElementById('formConfigWhatsApp');
    if (formWhatsApp) formWhatsApp.addEventListener('submit', salvarConfiguracoesWhatsApp);
    const formFiscalProvedor = document.getElementById('formFiscalProvedor');
    if (formFiscalProvedor) {
        formFiscalProvedor.addEventListener('submit', salvarConfiguracoesFiscalProvedor);
        carregarConfiguracoesFiscalProvedor();
    }
    const formNap = document.getElementById('formMarketplaceNap');
    if (formNap) {
        formNap.addEventListener('submit', salvarMarketplaceNap);
        carregarMarketplaceNap();
    }
}); 