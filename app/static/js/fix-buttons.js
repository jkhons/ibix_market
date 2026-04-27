// fix-buttons.js - Script para corrigir problemas dos botões do dashboard
// Este script garante que todos os componentes do Bootstrap funcionem corretamente

document.addEventListener('DOMContentLoaded', function() {
    console.log('Fix Buttons - Inicializando correções...');
    
    // Aguardar um pouco para garantir que o Bootstrap esteja carregado
    setTimeout(function() {
        fixAllButtons();
    }, 300);
});

function fixAllButtons() {
    console.log('Aplicando correções nos botões...');
    
    // 1. Corrigir dropdown de notificações (sino)
    fixNotificationDropdown();
    
    // 2. Corrigir dropdown do perfil
    fixProfileDropdown();
    
    // 3. Corrigir toggle da sidebar
    fixSidebarToggle();
    
    // 4. Forçar reinicialização de todos os dropdowns
    forceReinitializeAllDropdowns();
    
    console.log('Correções aplicadas com sucesso!');
}

function fixNotificationDropdown() {
    console.log('Corrigindo dropdown de notificações...');
    
    const alertsDropdown = document.getElementById('alertsDropdown');
    if (alertsDropdown) {
        // Remover event listeners existentes
        const newAlertsDropdown = alertsDropdown.cloneNode(true);
        alertsDropdown.parentNode.replaceChild(newAlertsDropdown, alertsDropdown);
        
        // Adicionar novo event listener
        newAlertsDropdown.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('Dropdown de notificações clicado');
            
            // Toggle manual do dropdown
            const dropdownMenu = document.querySelector('.dropdown-menu[aria-labelledby="alertsDropdown"]');
            if (dropdownMenu) {
                dropdownMenu.classList.toggle('show');
            }
        });
        
        console.log('Dropdown de notificações corrigido');
    } else {
        console.warn('Dropdown de notificações não encontrado');
    }
}

function fixProfileDropdown() {
    console.log('Corrigindo dropdown do perfil...');
    
    const profileDropdowns = document.querySelectorAll('.nav-link.dropdown-toggle, .nav-icon.dropdown-toggle');
    
    profileDropdowns.forEach(function(dropdown) {
        // Remover event listeners existentes
        const newDropdown = dropdown.cloneNode(true);
        dropdown.parentNode.replaceChild(newDropdown, dropdown);
        
        // Adicionar novo event listener
        newDropdown.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('Dropdown do perfil clicado');
            
            // Toggle manual do dropdown
            const dropdownMenu = this.nextElementSibling;
            if (dropdownMenu && dropdownMenu.classList.contains('dropdown-menu')) {
                dropdownMenu.classList.toggle('show');
            }
        });
    });
    
    console.log('Dropdowns do perfil corrigidos:', profileDropdowns.length);
}

function fixSidebarToggle() {
    console.log('Corrigindo toggle da sidebar...');
    
    const sidebarToggle = document.querySelector('.js-sidebar-toggle');
    const sidebar = document.querySelector('.js-sidebar');
    
    if (sidebarToggle && sidebar) {
        // Remover event listeners existentes
        const newSidebarToggle = sidebarToggle.cloneNode(true);
        sidebarToggle.parentNode.replaceChild(newSidebarToggle, sidebarToggle);
        
        // Adicionar novo event listener
        newSidebarToggle.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            if (typeof window.toggleSidebar === 'function') {
                window.toggleSidebar();
            } else {
                sidebar.classList.toggle('collapsed');
            }
            setTimeout(function() {
                window.dispatchEvent(new Event('resize'));
            }, 300);
        });
        
        console.log('Toggle da sidebar corrigido');
    } else {
        console.warn('Elementos da sidebar não encontrados');
    }
}

function forceReinitializeAllDropdowns() {
    console.log('Forçando reinicialização de todos os dropdowns...');
    
    // Verificar se o Bootstrap está disponível
    if (typeof bootstrap !== 'undefined') {
        // Destruir todas as instâncias existentes
        const dropdownElements = document.querySelectorAll('[data-bs-toggle="dropdown"]');
        
        dropdownElements.forEach(function(element) {
            try {
                const existingDropdown = bootstrap.Dropdown.getInstance(element);
                if (existingDropdown) {
                    existingDropdown.dispose();
                }
                
                // Criar nova instância
                new bootstrap.Dropdown(element);
                console.log('Dropdown reinicializado:', element.id || element.className);
            } catch (error) {
                console.error('Erro ao reinicializar dropdown:', error);
            }
        });
        
        console.log('Total de dropdowns reinicializados:', dropdownElements.length);
    } else {
        console.warn('Bootstrap não está disponível');
    }
}

// Adicionar event listener para fechar dropdowns quando clicar fora
document.addEventListener('click', function(e) {
    if (!e.target.closest('.dropdown')) {
        const openDropdowns = document.querySelectorAll('.dropdown-menu.show');
        openDropdowns.forEach(function(dropdown) {
            dropdown.classList.remove('show');
        });
    }
});

// Adicionar event listener para tecla Escape
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        const openDropdowns = document.querySelectorAll('.dropdown-menu.show');
        openDropdowns.forEach(function(dropdown) {
            dropdown.classList.remove('show');
        });
    }
});

console.log('Fix Buttons - Script carregado'); 