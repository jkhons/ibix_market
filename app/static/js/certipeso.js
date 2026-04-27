// PDV Ibix - Sistema de gestão de certificação, calibração e PDV
// JavaScript customizado para o dashboard

// ===== UTILITÁRIO DE AUTENTICAÇÃO =====
/**
 * Função helper para fazer fetch com autenticação automática
 * Garante que o token seja enviado em todas as requisições
 */
window.authenticatedFetch = async function(url, options = {}) {
    // Obter token (cookie ou sessionStorage após login)
    const token = getAuthToken();
    
    // Configurar headers padrão
    const defaultOptions = {
        credentials: 'include', // Sempre incluir cookies
        headers: {
            'Content-Type': 'application/json',
            ...(options.headers || {})
        }
    };
    
    // Se houver token, adicionar ao header Authorization
    if (token) {
        defaultOptions.headers['Authorization'] = `Bearer ${token}`;
    }
    
    // Mesclar opções
    const finalOptions = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...(options.headers || {})
        }
    };
    
    return fetch(url, finalOptions);
};

/**
 * Função helper para obter cookie por nome
 */
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) {
        return parts.pop().split(';').shift();
    }
    return null;
}

/**
 * Obtém token para API: cookie (pdv_solumatica_token, pdv_automscale_token) ou sessionStorage (fallback após login).
 * Garante que o dashboard envie Authorization mesmo se o cookie não for enviado.
 */
function getAuthToken() {
    try {
        return getCookie('pdv_solumatica_token') || getCookie('pdv_automscale_token')
            || sessionStorage.getItem('pdv_solumatica_token') || sessionStorage.getItem('pdv_automscale_token') || null;
    } catch (_) {
        return getCookie('pdv_solumatica_token') || getCookie('pdv_automscale_token') || null;
    }
}
window.getAuthToken = getAuthToken;

/**
 * Formata string YYYY-MM-DD (data sem timezone) para dd/mm/yyyy.
 * Evita new Date(str) que interpreta como UTC e desloca um dia em fusos como UTC-3.
 * Use para campos de data-only vindos da API (data_agendamento, data_inicio, data_fim, etc.).
 */
window.formatarDataApenas = function(dataStr) {
    if (!dataStr) return '-';
    const s = String(dataStr).trim();
    const match = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (match) return match[3] + '/' + match[2] + '/' + match[1];
    const d = new Date(s);
    if (!isNaN(d.getTime())) return d.toLocaleDateString('pt-BR');
    return s;
};

/**
 * Função para verificar se o usuário está autenticado
 */
window.checkAuth = function() {
    const token = getAuthToken();
    if (!token) {
        window.location.href = '/login';
        return false;
    }
    return true;
};

document.addEventListener('DOMContentLoaded', function() {
    // Inicializar componentes
    initializeDashboard();
    initializeCharts();
    initializeSidebar();
    initializeNotifications();
    initializeBootstrapComponents(); // Nova função para corrigir problemas do Bootstrap
    
    // Aguardar um pouco e reinicializar componentes se necessário
    setTimeout(function() {
        if (typeof window.DashboardUtils !== 'undefined') {
            window.DashboardUtils.initializeAllComponents();
        }
    }, 500);
    
    // Correção específica para dropdowns da navbar
    fixNavbarDropdowns();
});

// Função específica para corrigir dropdowns da navbar
function fixNavbarDropdowns() {
    // Aguardar um pouco para garantir que o DOM está pronto
    setTimeout(function() {
        // Debug: verificar se os elementos existem
        const alertsDropdown = document.getElementById('alertsDropdown');
        const messagesDropdown = document.getElementById('messagesDropdown');
        
        // Corrigir dropdown de notificações
        if (alertsDropdown) {
            // Tentar inicializar com Bootstrap primeiro
            if (typeof bootstrap !== 'undefined') {
                try {
                    const dropdown = new bootstrap.Dropdown(alertsDropdown);
                } catch (error) {
                    // Erro silencioso
                }
            }
            
            // Fallback: event listener manual
            alertsDropdown.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                
                const dropdownMenu = document.querySelector('[aria-labelledby="alertsDropdown"]');
                if (dropdownMenu) {
                    const isVisible = dropdownMenu.classList.contains('show');
                    
                    // Fechar todos os outros dropdowns
                    document.querySelectorAll('.dropdown-menu.show').forEach(function(menu) {
                        menu.classList.remove('show');
                    });
                    
                    // Toggle do dropdown atual
                    if (!isVisible) {
                        dropdownMenu.classList.add('show');
                    } else {
                        dropdownMenu.classList.remove('show');
                    }
                }
            });
            
            // Fechar dropdown quando clicar fora
            document.addEventListener('click', function(e) {
                if (!alertsDropdown.contains(e.target)) {
                    const dropdownMenu = document.querySelector('[aria-labelledby="alertsDropdown"]');
                    if (dropdownMenu) {
                        dropdownMenu.classList.remove('show');
                    }
                }
            });
        }
        
        // Corrigir dropdown de mensagens
        if (messagesDropdown) {
            // Tentar inicializar com Bootstrap primeiro
            if (typeof bootstrap !== 'undefined') {
                try {
                    const dropdown = new bootstrap.Dropdown(messagesDropdown);
                } catch (error) {
                    // Erro silencioso
                }
            }
            
            // Fallback: event listener manual
            messagesDropdown.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                
                const dropdownMenu = document.querySelector('[aria-labelledby="messagesDropdown"]');
                if (dropdownMenu) {
                    const isVisible = dropdownMenu.classList.contains('show');
                    
                    // Fechar todos os outros dropdowns
                    document.querySelectorAll('.dropdown-menu.show').forEach(function(menu) {
                        menu.classList.remove('show');
                    });
                    
                    // Toggle do dropdown atual
                    if (!isVisible) {
                        dropdownMenu.classList.add('show');
                    } else {
                        dropdownMenu.classList.remove('show');
                    }
                }
            });
        }
        
        // Corrigir dropdown do perfil
        const profileDropdowns = document.querySelectorAll('.nav-link.dropdown-toggle, .nav-icon.dropdown-toggle');
        
        profileDropdowns.forEach(function(dropdown, index) {
            if (dropdown.getAttribute('data-bs-toggle') === 'dropdown') {
                // Tentar inicializar com Bootstrap primeiro
                if (typeof bootstrap !== 'undefined') {
                    try {
                        const bootstrapDropdown = new bootstrap.Dropdown(dropdown);
                    } catch (error) {
                        // Erro silencioso
                    }
                }
                
                // Fallback: event listener manual
                dropdown.addEventListener('click', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    
                    const dropdownMenu = dropdown.nextElementSibling;
                    if (dropdownMenu && dropdownMenu.classList.contains('dropdown-menu')) {
                        const isVisible = dropdownMenu.classList.contains('show');
                        
                        // Fechar todos os outros dropdowns
                        document.querySelectorAll('.dropdown-menu.show').forEach(function(menu) {
                            menu.classList.remove('show');
                        });
                        
                        // Toggle do dropdown atual
                        if (!isVisible) {
                            dropdownMenu.classList.add('show');
                        } else {
                            dropdownMenu.classList.remove('show');
                        }
                    }
                });
            }
        });
    }, 1000);
}

// Função para corrigir problemas do Bootstrap
function initializeBootstrapComponents() {
    // Corrigir dropdowns do Bootstrap
    initializeDropdowns();
    
    // Corrigir sidebar toggle
    initializeSidebarToggle();
    
    // Corrigir notificações
    initializeNotificationDropdown();
    
    // Corrigir botão de perfil
    initializeProfileDropdown();
    
    // Forçar reinicialização após um delay
    setTimeout(function() {
        forceReinitializeDropdowns();
    }, 200);
}

// Inicializar dropdowns do Bootstrap
function initializeDropdowns() {
    // Verificar se o Bootstrap está disponível
    if (typeof bootstrap === 'undefined') {
        console.warn('Bootstrap não está disponível');
        return;
    }
    
    // Inicializar todos os dropdowns
    const dropdownElements = document.querySelectorAll('[data-bs-toggle="dropdown"]');
    
    dropdownElements.forEach(function(element) {
        try {
            // Destruir instância existente se houver
            const existingDropdown = bootstrap.Dropdown.getInstance(element);
            if (existingDropdown) {
                existingDropdown.dispose();
            }
            
            // Criar nova instância
            new bootstrap.Dropdown(element);
        } catch (error) {
            // Erro silencioso
        }
    });
}

// Forçar reinicialização dos dropdowns
function forceReinitializeDropdowns() {
    if (typeof bootstrap === 'undefined') {
        return;
    }
    
    // Forçar reinicialização de dropdowns específicos
    const alertsDropdown = document.getElementById('alertsDropdown');
    if (alertsDropdown) {
        try {
            const existingDropdown = bootstrap.Dropdown.getInstance(alertsDropdown);
            if (existingDropdown) {
                existingDropdown.dispose();
            }
            new bootstrap.Dropdown(alertsDropdown);
        } catch (error) {
            // Erro silencioso
        }
    }
    
    // Reinicializar dropdowns do perfil
    const profileDropdowns = document.querySelectorAll('.nav-link.dropdown-toggle, .nav-icon.dropdown-toggle');
    profileDropdowns.forEach(function(dropdown) {
        try {
            const existingDropdown = bootstrap.Dropdown.getInstance(dropdown);
            if (existingDropdown) {
                existingDropdown.dispose();
            }
            new bootstrap.Dropdown(dropdown);
        } catch (error) {
            // Erro silencioso
        }
    });
}

// Corrigir sidebar toggle
function initializeSidebarToggle() {
    const sidebarElement = document.querySelector('.js-sidebar');
    const sidebarToggleElement = document.querySelector('.js-sidebar-toggle');
    
    if (sidebarElement && sidebarToggleElement) {
        // Remover event listeners existentes para evitar duplicação
        sidebarToggleElement.removeEventListener('click', handleSidebarToggle);
        
        // Adicionar novo event listener
        sidebarToggleElement.addEventListener('click', handleSidebarToggle);
    }
}

// Função separada para o handler do sidebar toggle (desktop: .collapsed; mobile: .show + overlay)
function handleSidebarToggle(e) {
    e.preventDefault();
    e.stopPropagation();
    if (typeof window.toggleSidebar === 'function') {
        window.toggleSidebar();
    } else {
        const sidebarElement = document.querySelector('.js-sidebar');
        if (sidebarElement) sidebarElement.classList.toggle('collapsed');
    }
    setTimeout(function() {
        window.dispatchEvent(new Event('resize'));
    }, 100);
}

// Corrigir dropdown de notificações
function initializeNotificationDropdown() {
    const notificationDropdown = document.getElementById('alertsDropdown');
    
    if (notificationDropdown) {
        // Garantir que o dropdown funcione
        notificationDropdown.addEventListener('click', function(e) {
            e.preventDefault();
        });
    }
}

// Corrigir dropdown do perfil
function initializeProfileDropdown() {
    const profileDropdowns = document.querySelectorAll('.nav-link.dropdown-toggle');
    
    profileDropdowns.forEach(function(dropdown) {
        dropdown.addEventListener('click', function(e) {
            e.preventDefault();
        });
    });
}

// Função principal do dashboard
function initializeDashboard() {
    // ⚡ OTIMIZADO: Só atualizar stats se estiver na página do dashboard
    if (window.location.pathname === '/dashboard' || window.location.pathname === '/') {
        // Atualizar estatísticas em tempo real
        updateDashboardStats();
        
        // Configurar atualizações automáticas (só no dashboard)
        setInterval(updateDashboardStats, 60000); // ⚡ Aumentado para 1 minuto
    }
}

// Atualizar estatísticas do dashboard
function updateDashboardStats() {
    // Aqui você pode fazer chamadas AJAX para buscar dados atualizados
    
    // Exemplo de atualização de estatísticas
    updateStatCard('total-clientes', '1,234');
    updateStatCard('total-equipamentos', '5,678');
    updateStatCard('certificados-ativos', '3,456');
    updateStatCard('certificados-vencendo', '89');
}

// Atualizar card de estatística
function updateStatCard(cardId, value) {
    const card = document.getElementById(cardId);
    if (card) {
        const numberElement = card.querySelector('.certlog-stat-number');
        if (numberElement) {
            numberElement.textContent = value;
        }
    }
}

// Inicializar gráficos
function initializeCharts() {
    // Configuração dos gráficos do dashboard
    
    // Verificar se o Chart.js está disponível
    if (typeof Chart === 'undefined') {
        return;
    }
    
    // Gráfico de linha - DESABILITADO
    // Cada página agora controla seu próprio gráfico com dados reais
    // O dashboard.html possui sua própria lógica de gráficos dinâmicos
    const lineChartCtx = document.getElementById('chartjs-dashboard-line');
    if (lineChartCtx) {
        // Não inicializar gráfico mockado aqui - cada página controla seu próprio gráfico
    }
    
    // Gráfico de pizza - Status dos Certificados
    const pieChartCtx = document.getElementById('chartjs-dashboard-pie');
    if (pieChartCtx) {
        // Destruir gráfico existente se houver
        if (window.certilogPieChart) {
            window.certilogPieChart.destroy();
        }
        
        window.certilogPieChart = new Chart(pieChartCtx, {
            type: 'doughnut',
            data: {
                labels: ['Ativos', 'Vencendo', 'Vencidos', 'Suspensos'],
                datasets: [{
                    data: [70, 15, 10, 5],
                    backgroundColor: [
                        '#27ae60',
                        '#f39c12',
                        '#e74c3c',
                        '#95a5a6'
                    ],
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'bottom',
                    },
                    title: {
                        display: true,
                        text: 'Status dos Certificados'
                    }
                },
                cutout: '65%'
            }
        });
    }
}

// Inicializar sidebar
function initializeSidebar() {
    // Adicionar classe customizada à sidebar
    const sidebar = document.getElementById('sidebar');
    if (sidebar) {
        sidebar.classList.add('certlog-sidebar');
        // Scroll do mouse só rola a sidebar quando o cursor está sobre ela (não propaga para a página)
        setupSidebarWheelScroll(sidebar);
    }
    
    // Marcar item ativo no menu
    const currentPage = window.location.pathname;
    const menuItems = document.querySelectorAll('.sidebar-nav .sidebar-item');
    
    menuItems.forEach(item => {
        const link = item.querySelector('.sidebar-link');
        if (link && link.getAttribute('href') === currentPage) {
            item.classList.add('active');
        }
    });
}

/**
 * Quando o cursor está sobre a sidebar, o scroll do mouse rola apenas o menu da sidebar,
 * sem barra visível e sem rolar a página.
 */
function setupSidebarWheelScroll(sidebar) {
    var scrollable = sidebar.querySelector('.sidebar-content');
    if (!scrollable) return;
    sidebar.addEventListener('wheel', function (e) {
        if (!sidebar.contains(e.target)) return;
        var maxScroll = scrollable.scrollHeight - scrollable.clientHeight;
        if (maxScroll <= 0) return;
        e.preventDefault();
        e.stopPropagation();
        var next = scrollable.scrollTop + e.deltaY;
        scrollable.scrollTop = Math.max(0, Math.min(next, maxScroll));
    }, { passive: false, capture: true });
}

// Inicializar notificações
function initializeNotifications() {
    // Sistema de notificações para alertas
    
    // Verificar notificações pendentes
    checkPendingNotifications();
}

// Verificar notificações pendentes
function checkPendingNotifications() {
    // Aqui você pode fazer uma chamada AJAX para verificar notificações
    // Por enquanto, vamos simular algumas notificações
    
    const notifications = [
        { type: 'warning', message: '5 certificados vencem em 30 dias' },
        { type: 'info', message: 'Nova aferição programada para amanhã' }
    ];
    
    notifications.forEach(notification => {
        showNotification(notification.type, notification.message);
    });
}

// Mostrar notificação
function showNotification(type, message) {
    // Criar elemento de notificação
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show`;
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Adicionar ao container de notificações
    const container = document.getElementById('notifications-container');
    if (container) {
        container.appendChild(notification);
    }
}

// Funções utilitárias
function formatCurrency(value) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(value);
}

function formatDate(date) {
    return new Intl.DateTimeFormat('pt-BR').format(new Date(date));
}

// Exportar funções para uso global
window.Certilog = {
    updateDashboardStats,
    showNotification,
    formatCurrency,
    formatDate,
    initializeBootstrapComponents,
    initializeCharts
};

// Inicializar gráficos quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', function() {
    // Aguardar um pouco para garantir que o Chart.js esteja carregado
    setTimeout(function() {
        initializeCharts();
    }, 300);
}); 

// PDV Ibix - Script Global
// Interceptor para adicionar token de autenticação automaticamente

(function() {
    'use strict';
    
    // Função para adicionar token ao header Authorization e tratar 401
    function addAuthHeader() {
        const originalFetch = window.fetch;
        window.fetch = async function(url, options = {}) {
            const opts = {
                ...options,
                headers: {
                    ...(options.headers || {})
                }
            };

            // Não sobrescrever Authorization se já foi definido (case-insensitive)
            const hasAuthHeader = Object.keys(opts.headers).some(function(key) {
                return key.toLowerCase() === 'authorization';
            });

            if (!hasAuthHeader) {
                const token = (typeof getAuthToken === 'function') ? getAuthToken() : null;
                if (token) {
                    opts.headers['Authorization'] = `Bearer ${token}`;
                }
            }

            // Garantir envio de cookies
            if (!opts.credentials) {
                opts.credentials = 'include';
            }

            const response = await originalFetch(url, opts);

            // Tratamento centralizado para token inválido/expirado
            if (response && response.status === 401) {
                try {
                    sessionStorage.removeItem('pdv_automscale_token');
                    localStorage.removeItem('pdv_automscale_token');
                    localStorage.removeItem('certilog_user');
                } finally {
                    window.location.href = '/login';
                }
            }

            return response;
        };
    }
    
    // Aplicar patch do fetch imediatamente para que todas as requisições (incl. dashboard) já enviem o token
    addAuthHeader();
    
    // Função para fazer logout
    window.certilogLogout = function() {
        try { sessionStorage.removeItem('pdv_automscale_token'); } catch (_) {}
        localStorage.removeItem('pdv_automscale_token');
        localStorage.removeItem('certilog_user');
        window.location.href = '/login';
    };
})(); 