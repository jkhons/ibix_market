/**
 * PDV Ibix - Sistema de Breadcrumbs
 * Navegação hierárquica dinâmica
 */

class BreadcrumbSystem {
    constructor() {
        // Verificar se já existe uma instância
        if (window.breadcrumbSystem) {
            console.log('⚠️ Sistema de Breadcrumbs já existe, retornando instância existente');
            return window.breadcrumbSystem;
        }
        
        this.breadcrumbs = [];
        this.init();
    }

    init() {
        // Verificar se já foi inicializado
        if (this.initialized) {
            console.log('⚠️ BreadcrumbSystem já inicializado');
            return;
        }
        
        // Configurar breadcrumbs baseado na URL atual
        this.setupBreadcrumbs();
        
        // Atualizar breadcrumbs quando a URL mudar
        this.setupNavigationListener();
        
        this.initialized = true;
    }

    setupBreadcrumbs() {
        const currentPath = window.location.pathname;
        this.generateBreadcrumbs(currentPath);
        this.renderBreadcrumbs();
    }

    generateBreadcrumbs(path) {
        this.breadcrumbs = [];
        
        // Mapeamento de rotas para breadcrumbs
        const routeMap = {
            '/': { title: 'Dashboard', icon: 'home', url: '/' },
            '/dashboard': { title: 'Dashboard', icon: 'home', url: '/dashboard' },
            '/clientes': { title: 'Clientes', icon: 'users', url: '/clientes' },
            '/equipamentos': { title: 'Equipamentos', icon: 'settings', url: '/equipamentos' },
            '/certificados': { title: 'Certificados', icon: 'file-text', url: '/certificados' },
            '/relatorios': { title: 'Relatórios', icon: 'bar-chart-2', url: '/relatorios' },
            '/configuracoes': { title: 'Configurações', icon: 'settings', url: '/configuracoes' },
            '/profile': { title: 'Perfil', icon: 'user', url: '/profile' },
            '/login': { title: 'Login', icon: 'log-in', url: '/login' },
            '/register': { title: 'Registro', icon: 'user-plus', url: '/register' },
            '/change-password': { title: 'Alterar Senha', icon: 'lock', url: '/change-password' },
            '/ui/forms': { title: 'Formulários', icon: 'edit-3', url: '/ui/forms' },
            '/ui/buttons': { title: 'Botões', icon: 'square', url: '/ui/buttons' },
            '/ui/cards': { title: 'Cards', icon: 'credit-card', url: '/ui/cards' },
            '/ui/typography': { title: 'Tipografia', icon: 'type', url: '/ui/typography' },
            '/ui/icons': { title: 'Ícones', icon: 'image', url: '/ui/icons' },
            '/ui/charts': { title: 'Gráficos', url: '/ui/charts' },
            '/ui/maps': { title: 'Mapas', icon: 'map', url: '/ui/maps' }
        };

        // Adicionar breadcrumb inicial
        this.breadcrumbs.push({
            title: 'PDV Ibix',
            icon: 'home',
            url: '/',
            isHome: true
        });

        // Gerar breadcrumbs baseado na rota atual
        if (routeMap[path]) {
            const route = routeMap[path];
            this.breadcrumbs.push({
                title: route.title,
                icon: route.icon,
                url: route.url,
                isActive: true
            });
        } else {
            // Para rotas não mapeadas, usar o path como título
            const pathParts = path.split('/').filter(part => part);
            if (pathParts.length > 0) {
                const title = pathParts[pathParts.length - 1]
                    .replace(/-/g, ' ')
                    .replace(/\b\w/g, l => l.toUpperCase());
                
                this.breadcrumbs.push({
                    title: title,
                    icon: 'file',
                    url: path,
                    isActive: true
                });
            }
        }
    }

    renderBreadcrumbs() {
        // Buscar container de breadcrumbs
        let breadcrumbContainer = document.getElementById('breadcrumb-container');
        
        if (!breadcrumbContainer) {
            // Criar container se não existir
            breadcrumbContainer = document.createElement('div');
            breadcrumbContainer.id = 'breadcrumb-container';
            breadcrumbContainer.className = 'breadcrumb-container mb-3';
            
            // Inserir após o navbar
            const navbar = document.querySelector('.navbar');
            if (navbar) {
                navbar.parentNode.insertBefore(breadcrumbContainer, navbar.nextSibling);
            } else {
                // Fallback: inserir no início do main
                const main = document.querySelector('.main');
                if (main) {
                    main.insertBefore(breadcrumbContainer, main.firstChild);
                }
            }
        }

        // Limpar breadcrumbs existentes antes de renderizar
        breadcrumbContainer.innerHTML = '';
        
        // Gerar HTML dos breadcrumbs
        const breadcrumbHTML = this.generateBreadcrumbHTML();
        breadcrumbContainer.innerHTML = breadcrumbHTML;
    }

    generateBreadcrumbHTML() {
        if (this.breadcrumbs.length === 0) {
            return '';
        }

        const breadcrumbItems = this.breadcrumbs.map((crumb, index) => {
            const isLast = index === this.breadcrumbs.length - 1;
            const isActive = crumb.isActive;
            
            let itemClass = 'breadcrumb-item';
            if (isActive) {
                itemClass += ' active';
            }

            let iconHTML = '';
            if (crumb.icon) {
                iconHTML = `<i class="align-middle me-1" data-feather="${crumb.icon}"></i>`;
            }

            if (isLast || isActive) {
                return `<li class="${itemClass}" aria-current="page">
                    ${iconHTML}${crumb.title}
                </li>`;
            } else {
                return `<li class="${itemClass}">
                    <a href="${crumb.url}" class="text-decoration-none">
                        ${iconHTML}${crumb.title}
                    </a>
                </li>`;
            }
        });

        return `
            <nav aria-label="breadcrumb">
                <ol class="breadcrumb">
                    ${breadcrumbItems.join('')}
                </ol>
            </nav>
        `;
    }

    setupNavigationListener() {
        // ⚡ OTIMIZADO: Usar eventos nativos em vez de polling
        
        // 1. Detectar navegação back/forward do navegador
        window.addEventListener('popstate', () => {
            console.log('🔄 Breadcrumbs: Navegação detectada (popstate)');
            this.setupBreadcrumbs();
        });

        // 2. Detectar mudanças de hash na URL
        window.addEventListener('hashchange', () => {
            console.log('🔄 Breadcrumbs: Hash mudou');
            this.setupBreadcrumbs();
        });

        // 3. Interceptar cliques em links internos
        document.addEventListener('click', (e) => {
            const link = e.target.closest('a');
            if (link && link.href && link.href.startsWith(window.location.origin)) {
                const url = new URL(link.href);
                if (url.pathname !== window.location.pathname) {
                    // ⚡ Usar requestAnimationFrame em vez de setTimeout
                    requestAnimationFrame(() => {
                        requestAnimationFrame(() => {
                            this.setupBreadcrumbs();
                        });
                    });
                }
            }
        });
        
        console.log('✅ Breadcrumbs: Listeners de navegação configurados (sem polling)');
    }

    // Método para atualizar breadcrumbs manualmente
    updateBreadcrumbs(customBreadcrumbs) {
        this.breadcrumbs = customBreadcrumbs;
        this.renderBreadcrumbs();
    }

    // Método para adicionar breadcrumb dinamicamente
    addBreadcrumb(title, icon = null, url = null) {
        this.breadcrumbs.push({
            title: title,
            icon: icon,
            url: url,
            isActive: true
        });
        this.renderBreadcrumbs();
    }
}

document.addEventListener('DOMContentLoaded', function() {
    // DESABILITADO TEMPORARIAMENTE PARA CORRIGIR DUPLICAÇÃO
    
    // Verificar se já existe uma instância para evitar duplicação
    // if (!window.breadcrumbSystem) {
    //     window.breadcrumbSystem = new BreadcrumbSystem();
    //     console.log('🚀 Sistema de Breadcrumbs - Inicializado');
    // } else {
    //     console.log('⚠️ Sistema de Breadcrumbs já inicializado');
    // }
});

// Função global para atualizar breadcrumbs
window.updateBreadcrumbs = function(customBreadcrumbs) {
    if (window.breadcrumbSystem) {
        window.breadcrumbSystem.updateBreadcrumbs(customBreadcrumbs);
    }
};

// Função global para adicionar breadcrumb
window.addBreadcrumb = function(title, icon, url) {
    if (window.breadcrumbSystem) {
        window.breadcrumbSystem.addBreadcrumb(title, icon, url);
    }
}; 