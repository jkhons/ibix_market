/**
 * PDV Ibix - User Dropdown Functionality
 * Melhora a funcionalidade do dropdown do usuário
 */

// Variável global para controlar se os dados já foram carregados
window.userDataLoaded = false;

// Proteção contra múltiplas execuções
let initializationComplete = false;

document.addEventListener('DOMContentLoaded', function() {
    // PRIMEIRO: Verificar e aplicar nome do usuário imediatamente
    checkAndApplyUserNameImmediately();
    
    // Aguardar um pouco para garantir que outros scripts não interfiram
    setTimeout(function() {
        if (!initializationComplete) {
            initializeUserDropdown();
        }
    }, 1000);
});

// Função para verificar e aplicar nome do usuário imediatamente
function checkAndApplyUserNameImmediately() {
    const userNameElement = document.getElementById('userName');
    if (!userNameElement) {
        return;
    }
    
    // Se o nome é "Usuário" ou "Usuario", tentar aplicar o nome correto
    if (userNameElement.textContent === 'Usuário' || userNameElement.textContent === 'Usuario') {
        // Tentar carregar do localStorage primeiro
        const storedData = loadUserDataFromStorage();
        if (storedData && storedData.nome) {
            userNameElement.textContent = storedData.nome;
            window.userDataLoaded = true;
            return;
        }
        
        // Se não há dados no localStorage, carregar da API
        loadUserNameFromAPI();
    } else {
        window.userDataLoaded = true;
    }
}

// Função para carregar nome do usuário da API
async function loadUserNameFromAPI() {
    try {
        
        const token = getToken();
        if (!token) {
            return;
        }
        
        const response = await fetch('/api/v1/auth/me', {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            const userData = await response.json();
            
            // Aplicar nome imediatamente
            const userNameElement = document.getElementById('userName');
            if (userNameElement && userData.nome) {
                userNameElement.textContent = userData.nome;
            }
            
            // Salvar dados no localStorage
            saveUserData(userData);
            window.userDataLoaded = true;
        } else {
            console.warn('⚠️ Erro na resposta da API:', response.status);
        }
    } catch (error) {
        console.error('❌ Erro ao carregar nome do usuário:', error);
    }
}

// Proteção adicional contra interferência
window.addEventListener('load', function() {
    
    // Verificar se os dados foram aplicados corretamente
    setTimeout(function() {
        ensureUserDataApplied();
    }, 2000);
});

function ensureUserDataApplied() {
    const userNameElement = document.getElementById('userName');
    const userAvatarElement = document.getElementById('userAvatar');
    
    if (userNameElement && userNameElement.textContent === 'Usuário') {
        console.log('⚠️ User Dropdown - Nome ainda é "Usuário", aplicando dados...');
        forceApplyUserData();
    }
}

function initializeUserDropdown() {
    if (initializationComplete) {
        return;
    }
    
    
    // Marcar como inicializado
    initializationComplete = true;
    
    // Inicializar dropdowns do Bootstrap
    const dropdownElementList = [].slice.call(document.querySelectorAll('.dropdown-toggle'));
    const dropdownList = dropdownElementList.map(function (dropdownToggleEl) {
        return new bootstrap.Dropdown(dropdownToggleEl);
    });

    // Funcionalidade de logout
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Confirmar logout
            if (confirm('Tem certeza que deseja sair do sistema?')) {
                performLogout();
            }
        });
    }

    // Melhorar comportamento do dropdown em dispositivos móveis
    const dropdownToggles = document.querySelectorAll('.dropdown-toggle');
    dropdownToggles.forEach(toggle => {
        toggle.addEventListener('click', function(e) {
            // Em dispositivos móveis, fechar outros dropdowns abertos
            if (window.innerWidth < 768) {
                const openDropdowns = document.querySelectorAll('.dropdown-menu.show');
                openDropdowns.forEach(dropdown => {
                    if (dropdown !== this.nextElementSibling) {
                        dropdown.classList.remove('show');
                    }
                });
            }
        });
    });

    // Fechar dropdown ao clicar fora
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.dropdown')) {
            const openDropdowns = document.querySelectorAll('.dropdown-menu.show');
            openDropdowns.forEach(dropdown => {
                dropdown.classList.remove('show');
            });
        }
    });

    // Adicionar animação suave ao dropdown
    const dropdownMenus = document.querySelectorAll('.dropdown-menu');
    dropdownMenus.forEach(menu => {
        menu.style.transition = 'opacity 0.2s ease-in-out, transform 0.2s ease-in-out';
    });

    // Verificar se o usuário está autenticado
    function checkAuthStatus() {
        const token = getToken();
        if (!token) {
            // Se não há token, redirecionar para login
            if (window.location.pathname !== '/login' && window.location.pathname !== '/register') {
                window.location.href = '/login';
            }
        }
    }

    // Verificar autenticação a cada 5 minutos
    setInterval(checkAuthStatus, 300000);

    // Verificar na inicialização (pequeno delay para cookie estar disponível após redirect do login)
    setTimeout(checkAuthStatus, 100);
    
    // Carregar dados do usuário apenas se ainda não foram carregados
    if (!window.userDataLoaded) {
        loadUserData();
    }
}

// Função para forçar aplicação dos dados
function forceApplyUserData() {
    
    const storedData = localStorage.getItem('pdv_automscale_user_data');
    if (storedData) {
        try {
            const userData = JSON.parse(storedData);
            applyUserData(userData);
        } catch (error) {
            console.error('❌ Erro ao forçar aplicação:', error);
        }
    }
}

// Função para salvar dados do usuário no localStorage
function saveUserData(userData) {
    try {
        localStorage.setItem('pdv_automscale_user_data', JSON.stringify(userData));
        localStorage.setItem('pdv_automscale_user_data_timestamp', Date.now().toString());
    } catch (error) {
        console.error('❌ Erro ao salvar dados do usuário:', error);
    }
}

// Função para carregar dados do usuário do localStorage
function loadUserDataFromStorage() {
    try {
        const userData = localStorage.getItem('pdv_automscale_user_data');
        const timestamp = localStorage.getItem('pdv_automscale_user_data_timestamp');
        
        if (userData && timestamp) {
            const dataAge = Date.now() - parseInt(timestamp);
            // Considerar dados válidos por 1 hora
            if (dataAge < 3600000) {
                return JSON.parse(userData);
            } else {
                // Dados expirados, remover
                localStorage.removeItem('pdv_automscale_user_data');
                localStorage.removeItem('pdv_automscale_user_data_timestamp');
            }
        }
    } catch (error) {
        console.error('❌ Erro ao carregar dados do usuário do localStorage:', error);
    }
    return null;
}

// Função para aplicar dados do usuário na interface
function applyUserData(userData) {
    if (!userData) return;
    
    const userNameElement = document.getElementById('userName');
    const userAvatarElement = document.getElementById('userAvatar');
    
    if (userNameElement && userData.nome && userData.nome.trim() !== '') {
        // Verificar se o nome atual é diferente do que queremos aplicar
        if (userNameElement.textContent !== userData.nome) {
            userNameElement.textContent = userData.nome;
        }
        // Remover log desnecessário quando nome já está correto
    }
    
    if (userAvatarElement && userData.avatar) {
        // Verificar se o avatar atual é diferente do que queremos aplicar
        if (userAvatarElement.src !== userData.avatar) {
            userAvatarElement.src = userData.avatar;
            userAvatarElement.alt = userData.nome || 'Usuário';
        }
    }
    
    // Marcar como carregado
    window.userDataLoaded = true;
}

// Função para carregar dados do usuário
async function loadUserData() {
    try {
        
        // Se os dados já foram carregados, não executar novamente
        if (window.userDataLoaded) {
            return;
        }
        
        const token = getToken();
        if (!token) {
            return;
        }
        
        // Verificar se o nome já está correto no template (não é "Usuário" ou "Usuario")
        const userNameElement = document.getElementById('userName');
        if (userNameElement) {
            console.log('🔍 Nome atual no template:', userNameElement.textContent);
            if (userNameElement.textContent && 
                userNameElement.textContent !== 'Usuário' && 
                userNameElement.textContent !== 'Usuario' &&
                userNameElement.textContent.trim() !== '') {
                // Marcar como carregado para evitar requisições desnecessárias
                window.userDataLoaded = true;
                return;
            }
        }
        
        // Primeiro, tentar carregar dados do localStorage (apenas se nome não estiver correto)
        const storedUserData = loadUserDataFromStorage();
        if (storedUserData) {
            console.log('🔄 Aplicando dados do localStorage:', storedUserData.nome);
            applyUserData(storedUserData);
            return;
        }
        
        // Se não há dados no localStorage, carregar da API
        console.log('🔄 Carregando dados do usuário da API...');
        
        const response = await fetch('/api/v1/auth/me', {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            const userData = await response.json();
            
            // Salvar dados no localStorage
            saveUserData(userData);
            
            // Aplicar dados na interface
            applyUserData(userData);
        } else {
            console.warn('⚠️ Erro na resposta da API:', response.status, response.statusText);
        }
    } catch (error) {
        console.error('❌ Erro ao carregar dados do usuário:', error);
    }
}

// Função para realizar logout
async function performLogout() {
    try {
        const token = getToken();
        
        if (token) {
            // Chamar API de logout
            const response = await fetch('/api/v1/auth/logout', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });
        }
        
        // Limpar token do cookie
        document.cookie = 'pdv_automscale_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
        
        // Limpar sessionStorage e localStorage
        try { sessionStorage.removeItem('pdv_automscale_token'); } catch (_) {}
        localStorage.removeItem('pdv_automscale_token');
        localStorage.removeItem('pdv_automscale_user_data');
        localStorage.removeItem('pdv_automscale_user_data_timestamp');
        
        // Resetar flags
        window.userDataLoaded = false;
        initializationComplete = false;
        
        // Redirecionar para login
        window.location.href = '/login';
        
    } catch (error) {
        console.error('❌ Erro no logout:', error);
        // Mesmo com erro, limpar dados e redirecionar
        document.cookie = 'pdv_automscale_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
        try { sessionStorage.removeItem('pdv_automscale_token'); } catch (_) {}
        localStorage.removeItem('pdv_automscale_token');
        localStorage.removeItem('pdv_automscale_user_data');
        localStorage.removeItem('pdv_automscale_user_data_timestamp');
        window.userDataLoaded = false;
        initializationComplete = false;
        window.location.href = '/login';
    }
}

// Função para obter token (compatível com JWT que pode ter = no valor/base64)
function getToken() {
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        const s = cookie.trim();
        const eq = s.indexOf('=');
        if (eq === -1) continue;
        const name = s.substring(0, eq);
        const value = s.substring(eq + 1);
        if (name === 'pdv_automscale_token' && value) {
            return value;
        }
    }
    try {
        return sessionStorage.getItem('pdv_automscale_token') || localStorage.getItem('pdv_automscale_token');
    } catch (_) {
        return localStorage.getItem('pdv_automscale_token');
    }
} 