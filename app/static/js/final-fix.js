// final-fix.js - Script final para garantir funcionamento dos botões
// Este script é executado após todos os outros para garantir que tudo funcione

(function() {
    'use strict';
    
    console.log('Final Fix - Inicializando correções finais...');
    
    // Aguardar que tudo esteja carregado
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeFinalFix);
    } else {
        initializeFinalFix();
    }
    
    function initializeFinalFix() {
        // Aguardar um pouco mais para garantir que o Bootstrap esteja totalmente carregado
        setTimeout(function() {
            console.log('Aplicando correções finais...');
            
            // 1. Forçar inicialização do Bootstrap
            forceBootstrapInit();
            
            // 2. Corrigir dropdowns específicos
            fixSpecificDropdowns();
            
            // 3. Corrigir sidebar toggle
            fixSidebarToggle();
            
            // 4. Adicionar event listeners manuais se necessário
            addManualEventListeners();
            
            console.log('Correções finais aplicadas com sucesso!');
        }, 500);
    }
    
    function forceBootstrapInit() {
        console.log('Forçando inicialização do Bootstrap...');
        
        // Verificar se o Bootstrap está disponível
        if (typeof window.bootstrap === 'undefined') {
            console.error('Bootstrap não está disponível!');
            return;
        }
        
        // Forçar inicialização de todos os dropdowns
        const dropdownElements = document.querySelectorAll('[data-bs-toggle="dropdown"]');
        dropdownElements.forEach(function(element) {
            try {
                // Destruir instância existente
                const existingInstance = window.bootstrap.Dropdown.getInstance(element);
                if (existingInstance) {
                    existingInstance.dispose();
                }
                
                // Criar nova instância
                new window.bootstrap.Dropdown(element);
                console.log('Dropdown inicializado:', element.id || element.className);
            } catch (error) {
                console.error('Erro ao inicializar dropdown:', error);
            }
        });
        
        // Forçar inicialização de tooltips
        const tooltipElements = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        tooltipElements.forEach(function(element) {
            try {
                const existingInstance = window.bootstrap.Tooltip.getInstance(element);
                if (existingInstance) {
                    existingInstance.dispose();
                }
                new window.bootstrap.Tooltip(element);
            } catch (error) {
                console.error('Erro ao inicializar tooltip:', error);
            }
        });
        
        // Forçar inicialização de popovers
        const popoverElements = document.querySelectorAll('[data-bs-toggle="popover"]');
        popoverElements.forEach(function(element) {
            try {
                const existingInstance = window.bootstrap.Popover.getInstance(element);
                if (existingInstance) {
                    existingInstance.dispose();
                }
                new window.bootstrap.Popover(element);
            } catch (error) {
                console.error('Erro ao inicializar popover:', error);
            }
        });
    }
    
    function fixSpecificDropdowns() {
        console.log('Corrigindo dropdowns específicos...');
        
        // Corrigir dropdown de notificações
        const alertsDropdown = document.getElementById('alertsDropdown');
        if (alertsDropdown) {
            console.log('Corrigindo dropdown de notificações...');
            alertsDropdown.addEventListener('click', function(e) {
                e.preventDefault();
                const dropdown = window.bootstrap.Dropdown.getInstance(this);
                if (dropdown) {
                    dropdown.toggle();
                }
            });
        }
        
        // Corrigir dropdown do perfil
        const profileDropdown = document.querySelector('.nav-item.dropdown .dropdown-toggle');
        if (profileDropdown) {
            console.log('Corrigindo dropdown do perfil...');
            profileDropdown.addEventListener('click', function(e) {
                e.preventDefault();
                const dropdown = window.bootstrap.Dropdown.getInstance(this);
                if (dropdown) {
                    dropdown.toggle();
                }
            });
        }
    }
    
    function fixSidebarToggle() {
        console.log('Corrigindo toggle da sidebar...');
        
        const sidebarToggle = document.querySelector('.js-sidebar-toggle');
        const sidebar = document.getElementById('sidebar');
        const main = document.querySelector('.main');
        
        if (sidebarToggle && sidebar && main) {
            sidebarToggle.addEventListener('click', function(e) {
                e.preventDefault();
                console.log('Toggle da sidebar clicado');
                
                // Toggle da classe collapsed
                sidebar.classList.toggle('collapsed');
                main.classList.toggle('sidebar-collapsed');
                this.classList.toggle('active');
                
                // Salvar estado no localStorage
                const isCollapsed = sidebar.classList.contains('collapsed');
                localStorage.setItem('sidebar-collapsed', isCollapsed);
            });
            
            // Restaurar estado salvo (sempre iniciar expandida)
            const isCollapsed = localStorage.getItem('sidebar-collapsed') === 'true';
            if (isCollapsed) {
                // Remover estado colapsado do localStorage para sempre iniciar expandida
                localStorage.removeItem('sidebar-collapsed');
                sidebar.classList.remove('collapsed');
                main.classList.remove('sidebar-collapsed');
                sidebarToggle.classList.remove('active');
            }
        }
    }
    
    function addManualEventListeners() {
        console.log('Adicionando event listeners manuais...');
        
        // Adicionar event listeners para todos os dropdowns
        document.addEventListener('click', function(e) {
            const dropdownToggle = e.target.closest('[data-bs-toggle="dropdown"]');
            if (dropdownToggle) {
                e.preventDefault();
                const dropdown = window.bootstrap.Dropdown.getInstance(dropdownToggle);
                if (dropdown) {
                    dropdown.toggle();
                }
            }
        });
        
        // Fechar dropdowns quando clicar fora
        document.addEventListener('click', function(e) {
            if (!e.target.closest('.dropdown')) {
                const openDropdowns = document.querySelectorAll('.dropdown-menu.show');
                openDropdowns.forEach(function(dropdown) {
                    const dropdownToggle = dropdown.previousElementSibling;
                    if (dropdownToggle) {
                        const dropdownInstance = window.bootstrap.Dropdown.getInstance(dropdownToggle);
                        if (dropdownInstance) {
                            dropdownInstance.hide();
                        }
                    }
                });
            }
        });
    }
    
    // Expor funções para debug
    window.CertipesoFix = {
        forceBootstrapInit: forceBootstrapInit,
        fixSpecificDropdowns: fixSpecificDropdowns,
        fixSidebarToggle: fixSidebarToggle,
        addManualEventListeners: addManualEventListeners
    };
    
})(); 