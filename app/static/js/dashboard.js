// Dashboard.js - Script específico para o dashboard do PDV Ibix
// Garante que todos os componentes do Bootstrap funcionem corretamente

document.addEventListener('DOMContentLoaded', function() {
    // Aguardar um pouco para garantir que o Bootstrap esteja carregado
    setTimeout(function() {
        initializeAllComponents();
    }, 100);
});

function initializeAllComponents() {
    // 1. Inicializar todos os dropdowns
    initializeAllDropdowns();
    
    // 2. Inicializar sidebar toggle
    initializeSidebarToggle();
    
    // 3. Inicializar tooltips
    initializeTooltips();
    
    // 4. Inicializar popovers
    initializePopovers();
    
    // 5. Verificar se o Bootstrap está disponível
    checkBootstrapAvailability();
}

function checkBootstrapAvailability() {
    if (typeof bootstrap === 'undefined') {
        return false;
    }
    return true;
}

function initializeAllDropdowns() {
    if (!checkBootstrapAvailability()) return;
    
    // Inicializar todos os dropdowns manualmente
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

function initializeSidebarToggle() {
    try {
        const sidebarElement = document.querySelector('.js-sidebar');
        const sidebarToggleElement = document.querySelector('.js-sidebar-toggle');
        
        if (sidebarElement && sidebarToggleElement) {
            const clone = sidebarToggleElement.cloneNode(true);
            clone.removeAttribute('onclick');
            sidebarToggleElement.replaceWith(clone);
            const newToggleElement = document.querySelector('.js-sidebar-toggle');
            
            newToggleElement.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                // Usar a função global para desktop e mobile (mobile: .show + overlay)
                if (typeof window.toggleSidebar === 'function') {
                    window.toggleSidebar();
                } else {
                    sidebarElement.classList.toggle('collapsed');
                    localStorage.setItem('sidebar-collapsed', sidebarElement.classList.contains('collapsed'));
                }
                setTimeout(function() {
                    window.dispatchEvent(new Event('resize'));
                }, 300);
            });
            
            // Restaurar estado salvo em desktop (sempre iniciar expandida); em mobile não aplicar collapsed
            const savedState = localStorage.getItem('sidebar-collapsed');
            if (savedState === 'true') {
                const isMobile = window.matchMedia && window.matchMedia('(max-width: 768px)').matches;
                if (!isMobile) {
                    localStorage.removeItem('sidebar-collapsed');
                    sidebarElement.classList.remove('collapsed');
                }
            }
        }
    } catch (error) {
        // Erro silencioso
    }
}

function initializeTooltips() {
    if (!checkBootstrapAvailability()) return;
    
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

function initializePopovers() {
    if (!checkBootstrapAvailability()) return;
    
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
}

// Função para forçar a reinicialização de todos os componentes
function reinitializeComponents() {
    initializeAllComponents();
}

// Exportar funções para uso global
window.DashboardUtils = {
    initializeAllComponents,
    reinitializeComponents,
    initializeSidebarToggle
}; 