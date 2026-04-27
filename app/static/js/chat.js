// PDV Ibix - Chat no cabeçalho (painel slide-over + envio WhatsApp)
(function() {
    'use strict';

    function getToken() {
        var match = document.cookie.match(/pdv_automscale_token=([^;]+)/);
        return match ? match[1] : null;
    }

    function openChatPanel() {
        var panel = document.getElementById('chatPanel');
        var overlay = document.getElementById('chatPanelOverlay');
        if (panel) panel.classList.remove('d-none');
        if (overlay) overlay.classList.remove('d-none');
        if (typeof feather !== 'undefined' && feather.replace) feather.replace();
    }

    function closeChatPanel() {
        var panel = document.getElementById('chatPanel');
        var overlay = document.getElementById('chatPanelOverlay');
        if (panel) panel.classList.add('d-none');
        if (overlay) overlay.classList.add('d-none');
    }

    function toggleChatPanel() {
        var panel = document.getElementById('chatPanel');
        if (panel && panel.classList.contains('d-none')) openChatPanel();
        else closeChatPanel();
    }

    window.openChatPanel = openChatPanel;
    window.closeChatPanel = closeChatPanel;
    window.toggleChatPanel = toggleChatPanel;

    document.getElementById('chatPanelClose') && document.getElementById('chatPanelClose').addEventListener('click', closeChatPanel);

    var form = document.getElementById('chatWhatsAppForm');
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            var numero = (document.getElementById('chatNumeroDestino') && document.getElementById('chatNumeroDestino').value || '').trim();
            var texto = (document.getElementById('chatMensagem') && document.getElementById('chatMensagem').value || '').trim();
            var resultadoEl = document.getElementById('chatEnvioResultado');
            if (!numero || !texto) {
                if (resultadoEl) {
                    resultadoEl.classList.remove('d-none', 'alert-success', 'alert-danger');
                    resultadoEl.classList.add('alert', 'alert-warning');
                    resultadoEl.textContent = 'Preencha número e mensagem.';
                }
                return;
            }
            var token = getToken();
            var headers = { 'Content-Type': 'application/json' };
            if (token) headers['Authorization'] = 'Bearer ' + token;
            if (resultadoEl) {
                resultadoEl.classList.remove('alert-success', 'alert-danger', 'alert-warning');
                resultadoEl.classList.add('alert');
                resultadoEl.textContent = 'Enviando...';
                resultadoEl.classList.remove('d-none');
            }
            fetch('/api/v1/whatsapp/enviar', {
                method: 'POST',
                headers: headers,
                credentials: 'include',
                body: JSON.stringify({ numero_destino: numero, texto: texto, incluir_prefixo: true })
            }).then(function(res) {
                if (res.ok) {
                    if (resultadoEl) {
                        resultadoEl.textContent = 'Mensagem enviada.';
                        resultadoEl.classList.add('alert-success');
                    }
                    if (document.getElementById('chatMensagem')) document.getElementById('chatMensagem').value = '';
                } else {
                    return res.json().then(function(err) {
                        if (resultadoEl) {
                            resultadoEl.textContent = err.detail || 'Erro ao enviar.';
                            resultadoEl.classList.add('alert-danger');
                        }
                    }).catch(function() {
                        if (resultadoEl) {
                            resultadoEl.textContent = 'Erro ao enviar.';
                            resultadoEl.classList.add('alert-danger');
                        }
                    });
                }
            }).catch(function(err) {
                if (resultadoEl) {
                    resultadoEl.textContent = 'Erro: ' + (err.message || 'Falha na requisição.');
                    resultadoEl.classList.add('alert-danger');
                }
            });
        });
    }
})();
