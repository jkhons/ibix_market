// Sistema de Notificações - PDV Ibix
// Segurança: logs desabilitados em produção (nunca expor token ou dados sensíveis)

(function() {
    'use strict';

    // ⚡ LOCK para evitar múltiplas requisições simultâneas
    let isLoadingNotifications = false;
    let lastLoadTime = 0;
    const MIN_INTERVAL = 5000; // 5 segundos mínimo entre requisições

    // ⚡ Helper para pegar cookie (robusto: cookie primeiro, vários cookies, etc.)
    function getCookie(name) {
        const nameEq = name + '=';
        const ca = document.cookie.split(';');
        for (let i = 0; i < ca.length; i++) {
            let c = ca[i];
            while (c.charAt(0) === ' ') c = c.substring(1);
            if (c.indexOf(nameEq) === 0) return c.substring(nameEq.length);
        }
        return null;
    }

    // Marcar notificação como lida no banco de dados
    async function marcarComoLida(notificacaoId) {
        try {
            const token = getCookie('pdv_automscale_token');
            const response = await fetch(`/api/v1/notificacoes/${notificacaoId}/marcar-lido`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (response.ok) return true;
            return false;
        } catch (error) {
            return false;
        }
    }

    // Carregar notificações da API
    async function carregarNotificacoes() {
        // ⚡ LOCK: Verificar se já está carregando
        const now = Date.now();
        if (isLoadingNotifications) return;
        
        // ⚡ Verificar intervalo mínimo entre requisições
        const timeSinceLastLoad = now - lastLoadTime;
        if (timeSinceLastLoad < MIN_INTERVAL) return;
        
        try {
            isLoadingNotifications = true;
            lastLoadTime = now;
            
            // ⚡ Esperar um pouco para garantir que o cookie está disponível
            await new Promise(resolve => setTimeout(resolve, 100));
            
            const token = (typeof window.getAuthToken === 'function') ? window.getAuthToken() : getCookie('pdv_automscale_token');
            
            if (!token) {
                isLoadingNotifications = false;
                return;
            }
            
            // ⚡ Usar authenticatedFetch se disponível, senão usar fetch normal
            const fetchFunc = window.authenticatedFetch || fetch;
            const response = await fetchFunc('/api/v1/notificacoes', {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                credentials: 'include'
            });

            if (!response.ok) {
                if (response.status === 401) {
                    // Limpar contador se não autenticado
                    const countElement = document.getElementById('notificacoesCount');
                    if (countElement) countElement.textContent = '0';
                }
                // ⚡ Liberar lock antes de retornar
                isLoadingNotifications = false;
                return;
            }

            const data = await response.json();
            exibirNotificacoes(data.notificacoes);
        } catch (error) {
            const headerElement = document.getElementById('notificacoesHeader');
            if (headerElement) {
                headerElement.textContent = 'Erro ao carregar';
            }
            const listElement = document.getElementById('notificacoesList');
            if (listElement) {
                listElement.innerHTML = `
                    <div class="list-group-item text-center text-muted py-3">
                        <i data-feather="alert-circle"></i>
                        <p class="mb-0 mt-2">Erro ao carregar notificações</p>
                    </div>
                `;
                if (typeof feather !== 'undefined' && feather.icons) {
                    const featherElement = listElement.querySelector('[data-feather]');
                    if (featherElement) {
                        try {
                            const iconName = featherElement.getAttribute('data-feather');
                            if (iconName && feather.icons[iconName] && typeof feather.icons[iconName].toSvg === 'function') {
                                featherElement.innerHTML = feather.icons[iconName].toSvg();
                            } else if (feather.icons.bell && typeof feather.icons.bell.toSvg === 'function') {
                                featherElement.innerHTML = feather.icons.bell.toSvg();
                            } else {
                                featherElement.removeAttribute('data-feather');
                            }
                        } catch (error) {
                            featherElement.removeAttribute('data-feather');
                        }
                    }
                }
            }
        } finally {
            isLoadingNotifications = false;
        }
    }

    // Exibir notificações na interface
    function exibirNotificacoes(notificacoes) {
        const naoLidas = notificacoes.filter(n => !n.lido);
        
        // Atualizar contador
        const countElement = document.getElementById('notificacoesCount');
        if (countElement) {
            countElement.textContent = naoLidas.length;
            if (naoLidas.length === 0) {
                countElement.style.display = 'none';
            } else {
                countElement.style.display = '';
            }
        }

        // Atualizar header
        const headerElement = document.getElementById('notificacoesHeader');
        if (headerElement) {
            headerElement.textContent = `${naoLidas.length} Notificação${naoLidas.length !== 1 ? 'ões' : ''} não lida${naoLidas.length !== 1 ? 's' : ''}`;
        }

        // Atualizar lista
        const listElement = document.getElementById('notificacoesList');
        if (!listElement) return;

        if (notificacoes.length === 0) {
            listElement.innerHTML = `
                <div class="list-group-item text-center text-muted py-3">
                    <i data-feather="check-circle"></i>
                    <p class="mb-0 mt-2">Nenhuma notificação</p>
                </div>
            `;
            if (typeof feather !== 'undefined' && feather.icons) {
                const featherElement = listElement.querySelector('[data-feather]');
                if (featherElement) {
                    try {
                        const iconName = featherElement.getAttribute('data-feather');
                        if (iconName && feather.icons[iconName] && typeof feather.icons[iconName].toSvg === 'function') {
                            featherElement.innerHTML = feather.icons[iconName].toSvg();
                        } else if (feather.icons.bell && typeof feather.icons.bell.toSvg === 'function') {
                            featherElement.innerHTML = feather.icons.bell.toSvg();
                        } else {
                            featherElement.removeAttribute('data-feather');
                        }
                    } catch (error) {
                        featherElement.removeAttribute('data-feather');
                    }
                }
            }
            return;
        }

        // Lista de ícones válidos do Feather Icons (comuns)
        const iconesValidos = ['bell', 'alert-circle', 'check-circle', 'info', 'alert-triangle', 
            'x-circle', 'check', 'x', 'mail', 'user', 'settings', 'home', 'file', 'folder', 
            'download', 'upload', 'trash', 'edit', 'eye', 'eye-off', 'lock', 'unlock', 
            'calendar', 'clock', 'star', 'heart', 'message-circle', 'send', 'search', 
            'filter', 'chevron-right', 'chevron-left', 'chevron-up', 'chevron-down',
            'arrow-right', 'arrow-left', 'arrow-up', 'arrow-down', 'plus', 'minus',
            'more-vertical', 'more-horizontal', 'menu', 'x', 'check', 'alert-octagon'];

        // Função auxiliar para validar e obter ícone válido
        function obterIconeValido(icone) {
            if (!icone || typeof icone !== 'string' || icone.trim() === '') {
                return 'bell';
            }
            const iconeLimpo = icone.trim().toLowerCase();
            
            // Primeiro verificar se está na lista de ícones válidos conhecidos
            if (iconesValidos.includes(iconeLimpo)) {
                return iconeLimpo;
            }
            
            // Se a biblioteca Feather estiver disponível, verificar se o ícone existe
            if (typeof feather !== 'undefined' && feather.icons && feather.icons[iconeLimpo]) {
                return iconeLimpo;
            }
            
            // Fallback para ícone padrão
            return 'bell';
        }

        listElement.innerHTML = notificacoes.map(notif => {
            const corIcone = {
                'danger': 'text-danger',
                'warning': 'text-warning',
                'info': 'text-info',
                'success': 'text-success'
            }[notif.cor] || 'text-primary';

            // Validar e usar ícone válido
            const iconeValido = obterIconeValido(notif.icone);

            return `
                <a href="${notif.link}" class="list-group-item ${notif.lido ? 'read' : ''}" onclick="marcarNotificacaoLida('${notif.id}')">
                    <div class="row g-0 align-items-center">
                        <div class="col-2">
                            <i class="${corIcone}" data-feather="${iconeValido}"></i>
                        </div>
                        <div class="col-9">
                            <div class="text-dark">${notif.titulo}</div>
                            <div class="text-muted small mt-1">${notif.mensagem}</div>
                        </div>
                        <div class="col-1 text-end">
                            ${!notif.lido ? '<span class="badge bg-primary rounded-pill">!</span>' : ''}
                        </div>
                    </div>
                </a>
            `;
        }).join('');

        // Processar ícones Feather individualmente com validação rigorosa
        if (typeof feather !== 'undefined' && feather.icons) {
            const featherElements = listElement.querySelectorAll('[data-feather]');
            featherElements.forEach(el => {
                try {
                    const iconName = el.getAttribute('data-feather');
                    
                    // Validar se o ícone existe e tem o método toSvg
                    if (iconName && feather.icons[iconName] && typeof feather.icons[iconName].toSvg === 'function') {
                        el.innerHTML = feather.icons[iconName].toSvg();
                    } else {
                        // Se o ícone não existe, usar o ícone padrão
                        if (iconName && iconName !== 'bell') {}
                        // Garantir que o ícone padrão existe antes de usar
                        if (feather.icons.bell && typeof feather.icons.bell.toSvg === 'function') {
                            el.innerHTML = feather.icons.bell.toSvg();
                        } else {
                            el.removeAttribute('data-feather');
                        }
                    }
                } catch (e) {
                    // Usar ícone padrão como fallback em caso de erro
                    try {
                        if (feather.icons && feather.icons.bell && typeof feather.icons.bell.toSvg === 'function') {
                            el.innerHTML = feather.icons.bell.toSvg();
                        } else {
                            el.removeAttribute('data-feather');
                        }
                    } catch (fallbackError) {
                        el.removeAttribute('data-feather');
                    }
                }
            });
        } else {
            // Se Feather não estiver disponível, remover atributos data-feather para evitar erros
            const featherElements = listElement.querySelectorAll('[data-feather]');
            featherElements.forEach(el => {
                el.removeAttribute('data-feather');
            });
        }
    }

    // Marcar notificação como lida
    window.marcarNotificacaoLida = async function(notificacaoId) {
        const sucesso = await marcarComoLida(notificacaoId);
        if (sucesso) {
            // Recarregar notificações após marcar
            setTimeout(() => carregarNotificacoes(), 500);
        }
    };

    // Marcar todas como lidas
    window.marcarTodasLidas = async function() {
        event.preventDefault();
        const notifs = document.querySelectorAll('#notificacoesList .list-group-item');
        
        for (const item of notifs) {
            const link = item.getAttribute('onclick');
            if (link) {
                const match = link.match(/marcarNotificacaoLida\('([^']+)'\)/);
                if (match) {
                    await marcarComoLida(match[1]);
                }
            }
        }
        
        await carregarNotificacoes();
    };

    // ⚡ OTIMIZADO: Recarregar notificações com intervalo maior e apenas se aba está ativa
    function iniciarAtualizacaoAutomatica() {
        setInterval(() => {
            if (document.visibilityState === 'visible') carregarNotificacoes();
        }, 120000);
    }

    document.addEventListener('DOMContentLoaded', function() {
        carregarNotificacoes();
        iniciarAtualizacaoAutomatica();
        document.addEventListener('visibilitychange', function() {
            if (document.visibilityState === 'visible') carregarNotificacoes();
        });
    });
})();

