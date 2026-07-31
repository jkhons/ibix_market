/**
 * PDV Ibix - Gerenciador de Permissões de Roles
 * Sistema completo para gerenciar permissões RBAC
 */

class PermissoesManager {
    constructor() {
        this.permissoes = {};  // Permissões agrupadas por módulo
        this.permissoesSelecionadas = new Set();  // IDs das permissões selecionadas
        this.roleAtual = null;
        this.totalPermissoes = 0;
        
        // Ícones por módulo
        this.modulosIcons = {
            'usuarios': '👥',
            'clientes': '👤',
            'equipamentos': '⚙️',
            'afericoes': '🔬',
            'relatorios': '📊',
            'configuracoes': '⚙️',
            'negocios': '💼',
            'negocios.estoque': '📦',
            'negocios.venda': '🛒',
            'negocios.financeiro': '💰',
            'negocios.ordem-servico': '📋',
            'negocios.lacres-selos': '🏷️',
            'lacres-selos': '🏷️',
            'lacres_selos': '🏷️',
            'estoque': '📦',
            'financeiro': '💰',
            'venda': '🛒',
            'agendamentos': '📅',
            'contratos': '📋',
            'marketplace': '🏪',
            'pdv': '🖥️',
            'fiscal': '📄'
        };
    }

    async abrirModal(roleId, roleNome) {
        console.log('🚀 Abrindo modal de permissões para:', roleId, roleNome);
        
        this.roleAtual = { id: roleId, nome: roleNome };
        this.permissoesSelecionadas.clear();
        
        // Atualizar título do modal
        const tituloElement = document.getElementById('rolePermissoesNome');
        if (tituloElement) {
            tituloElement.textContent = roleNome;
            console.log('✅ Título do modal atualizado');
        } else {
            console.error('❌ Elemento rolePermissoesNome não encontrado');
        }
        
        // Carregar permissões
        console.log('📥 Carregando permissões...');
        await this.carregarPermissoes();
        
        // Abrir modal
        if (typeof modalGerenciarPermissoes !== 'undefined') {
            console.log('🎭 Abrindo modal...');
            modalGerenciarPermissoes.open();
        } else {
            console.error('❌ Modal modalGerenciarPermissoes não está disponível');
        }
        
        // Configurar eventos
        this.configurarEventos();
        console.log('✅ Modal configurado e aberto');
    }

    async carregarPermissoes() {
        try {
            console.log('🔍 Carregando permissões para role:', this.roleAtual);
            
            const container = document.getElementById('containerModulos');
            container.innerHTML = `
                <div class="text-center py-4">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Carregando...</span>
                    </div>
                    <p class="mt-2 text-muted">Carregando permissões...</p>
                </div>
            `;

            const url = `/api/v1/permissoes/agrupadas/modulos?role_id=${this.roleAtual.id}`;
            console.log('📡 Fazendo requisição para:', url);
            
            const response = await fetch(url);
            console.log('📡 Resposta recebida:', response.status, response.statusText);
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error('❌ Erro na resposta:', errorText);
                throw new Error(`Erro HTTP: ${response.status} - ${errorText}`);
            }

            const data = await response.json();
            console.log('📊 Dados recebidos:', data);
            
            this.permissoes = data.modulos;
            this.totalPermissoes = data.total_permissoes;
            
            // Inicializar permissões selecionadas
            for (const modulo in this.permissoes) {
                for (const perm of this.permissoes[modulo]) {
                    if (perm.selecionada) {
                        this.permissoesSelecionadas.add(perm.id);
                    }
                }
            }
            
            console.log('🎨 Renderizando módulos...');
            this.renderizarModulos();
            this.atualizarContador();
            console.log('✅ Permissões carregadas com sucesso!');
            
        } catch (error) {
            console.error('❌ Erro ao carregar permissões:', error);
            this.mostrarErroCarregamento();
        }
    }

    renderizarModulos() {
        console.log('🎨 Iniciando renderização de módulos...');
        const container = document.getElementById('containerModulos');
        container.innerHTML = '';

        const modulosOrdenados = Object.keys(this.permissoes).sort();
        console.log('📦 Módulos para renderizar:', modulosOrdenados);

        modulosOrdenados.forEach(modulo => {
            const permissoes = this.permissoes[modulo];
            const totalSelecionadas = permissoes.filter(p => this.permissoesSelecionadas.has(p.id)).length;
            
            const moduloDiv = document.createElement('div');
            moduloDiv.className = 'modulo-permissoes';
            moduloDiv.dataset.modulo = modulo;
            
            const icon = this.modulosIcons[modulo] || this.modulosIcons[modulo.replace('-', '_')] || '📦';
            
            // Mapear nomes de módulos para exibição mais amigável
            const nomesModulos = {
                'negocios': 'Negócios',
                'negocios.estoque': 'Negócios > Estoque',
                'negocios.venda': 'Negócios > Venda',
                'negocios.financeiro': 'Negócios > Financeiro',
                'negocios.ordem-servico': 'Negócios > Ordem de Serviço',
                'negocios.ordem-servico-tipos': 'Negócios > Ordem de Serviço > Tipos',
                'negocios.lacres-selos': 'Negócios > Lacres e Selos',
                'lacres-selos': 'Lacres e Selos',
                'lacres_selos': 'Lacres e Selos',
                'usuarios': 'Usuários',
                'clientes': 'Clientes',
                'equipamentos': 'Equipamentos',
                'afericoes': 'Aferições',
                'agendamentos': 'Agendamentos',
                'contratos': 'Contratos',
                'relatorios': 'Relatórios',
                'configuracoes': 'Configurações',
                'marketplace': 'Marketplace',
                'pdv': 'PDV',
                'fiscal': 'Fiscal',
                'estoque': 'Estoque',
                'financeiro': 'Financeiro',
                'venda': 'Venda'
            };
            
            // Se o módulo começa com 'negocios.', usar nome mais amigável
            let nomeExibicao = nomesModulos[modulo];
            if (!nomeExibicao) {
                // Tentar extrair nome do sub-módulo
                if (modulo.startsWith('negocios.')) {
                    const subModulo = modulo.replace('negocios.', '');
                    nomeExibicao = `Negócios > ${this.capitalize(subModulo.replace('-', ' ').replace('_', ' '))}`;
                } else {
                    nomeExibicao = this.capitalize(modulo.replace('-', ' ').replace('_', ' '));
                }
            }
            
            moduloDiv.innerHTML = `
                <div class="modulo-header" onclick="permissoesManager.toggleModulo('${modulo}')">
                    <div class="modulo-header-content">
                        <span class="modulo-icon">${icon}</span>
                        <h6 class="modulo-titulo">
                            ${nomeExibicao}
                            <span class="modulo-contador">(${totalSelecionadas}/${permissoes.length})</span>
                        </h6>
                    </div>
                    <div class="modulo-actions" onclick="event.stopPropagation()">
                        <button class="btn-selecionar-todas" 
                                onclick="permissoesManager.selecionarTodasModulo('${modulo}')">
                            ☑ Todas
                        </button>
                        <button class="btn-desmarcar-todas" 
                                onclick="permissoesManager.desmarcarTodasModulo('${modulo}')">
                            ☐ Nenhum
                        </button>
                        <span class="modulo-toggle">▼</span>
                    </div>
                </div>
                <div class="modulo-body" id="modulo-body-${modulo}">
                    ${this.renderizarPermissoesModulo(modulo, permissoes)}
                </div>
            `;
            
            container.appendChild(moduloDiv);
        });

        // Atualizar ícones Feather
        if (typeof feather !== 'undefined') {
            feather.replace();
        }
    }

    renderizarPermissoesModulo(modulo, permissoes) {
        return permissoes.map(perm => {
            const checked = this.permissoesSelecionadas.has(perm.id) ? 'checked' : '';
            const badgeClass = `permissao-badge-${perm.acao}`;
            
            return `
                <div class="permissao-item" data-permissao-id="${perm.id}">
                    <input type="checkbox" 
                           class="permissao-checkbox" 
                           id="perm-${perm.id}" 
                           data-id="${perm.id}"
                           data-modulo="${modulo}"
                           ${checked}
                           onchange="permissoesManager.togglePermissao(${perm.id})">
                    <div class="permissao-info">
                        <div class="permissao-nome">
                            <label for="perm-${perm.id}" style="cursor: pointer; margin: 0;">
                                ${perm.nome}
                            </label>
                        </div>
                        ${perm.descricao ? `<p class="permissao-descricao">${perm.descricao}</p>` : ''}
                    </div>
                    <span class="permissao-badge ${badgeClass}">${perm.acao}</span>
                </div>
            `;
        }).join('');
    }

    toggleModulo(modulo) {
        const body = document.getElementById(`modulo-body-${modulo}`);
        const header = body.previousElementSibling;
        const toggle = header.querySelector('.modulo-toggle');
        
        if (body.classList.contains('expandido')) {
            body.classList.remove('expandido');
            toggle.classList.remove('expandido');
        } else {
            body.classList.add('expandido');
            toggle.classList.add('expandido');
        }
    }

    togglePermissao(permissaoId) {
        if (this.permissoesSelecionadas.has(permissaoId)) {
            this.permissoesSelecionadas.delete(permissaoId);
        } else {
            this.permissoesSelecionadas.add(permissaoId);
        }
        
        this.atualizarContador();
        this.atualizarContadorModulo(permissaoId);
    }

    selecionarTodasModulo(modulo) {
        const permissoes = this.permissoes[modulo];
        permissoes.forEach(perm => {
            this.permissoesSelecionadas.add(perm.id);
            const checkbox = document.getElementById(`perm-${perm.id}`);
            if (checkbox) checkbox.checked = true;
        });
        
        this.atualizarContador();
        this.atualizarContadorModuloNome(modulo);
    }

    desmarcarTodasModulo(modulo) {
        const permissoes = this.permissoes[modulo];
        permissoes.forEach(perm => {
            this.permissoesSelecionadas.delete(perm.id);
            const checkbox = document.getElementById(`perm-${perm.id}`);
            if (checkbox) checkbox.checked = false;
        });
        
        this.atualizarContador();
        this.atualizarContadorModuloNome(modulo);
    }

    atualizarContadorModulo(permissaoId) {
        // Encontrar o módulo da permissão
        for (const modulo in this.permissoes) {
            const permissoes = this.permissoes[modulo];
            if (permissoes.some(p => p.id === permissaoId)) {
                this.atualizarContadorModuloNome(modulo);
                break;
            }
        }
    }

    atualizarContadorModuloNome(modulo) {
        const permissoes = this.permissoes[modulo];
        const totalSelecionadas = permissoes.filter(p => this.permissoesSelecionadas.has(p.id)).length;
        
        const moduloDiv = document.querySelector(`[data-modulo="${modulo}"]`);
        if (moduloDiv) {
            const contador = moduloDiv.querySelector('.modulo-contador');
            if (contador) {
                contador.textContent = `(${totalSelecionadas}/${permissoes.length})`;
            }
        }
    }

    atualizarContador() {
        const total = this.permissoesSelecionadas.size;
        const percentual = Math.round((total / this.totalPermissoes) * 100);
        
        document.getElementById('contadorPermissoes').textContent = `${total}/${this.totalPermissoes}`;
        document.getElementById('percentualPermissoes').textContent = `${percentual}%`;
        
        // Mudar cor do badge baseado na porcentagem
        const badge = document.getElementById('percentualPermissoes');
        badge.className = 'badge';
        
        if (percentual >= 80) {
            badge.classList.add('bg-success');
        } else if (percentual >= 40) {
            badge.classList.add('bg-primary');
        } else if (percentual >= 10) {
            badge.classList.add('bg-warning');
        } else {
            badge.classList.add('bg-danger');
        }
    }

    configurarEventos() {
        // Busca de permissões
        const campoBusca = document.getElementById('buscaPermissoes');
        if (campoBusca) {
            // Remover listeners anteriores
            campoBusca.replaceWith(campoBusca.cloneNode(true));
            const novoCampo = document.getElementById('buscaPermissoes');
            
            novoCampo.addEventListener('input', (e) => {
                this.filtrarPermissoes(e.target.value);
            });
        }

        // Botão Salvar
        const btnSalvar = document.getElementById('btnSalvarPermissoes');
        if (btnSalvar) {
            btnSalvar.replaceWith(btnSalvar.cloneNode(true));
            const novoBtnSalvar = document.getElementById('btnSalvarPermissoes');
            
            novoBtnSalvar.addEventListener('click', () => {
                this.salvarPermissoes();
            });
        }
    }

    filtrarPermissoes(termo) {
        termo = termo.toLowerCase().trim();
        
        if (!termo) {
            // Mostrar todos os módulos
            document.querySelectorAll('.modulo-permissoes').forEach(modulo => {
                modulo.classList.remove('oculto');
            });
            document.querySelectorAll('.permissao-item').forEach(item => {
                item.style.display = 'flex';
            });
            return;
        }

        // Filtrar permissões
        const modulosVisiveis = new Set();
        
        document.querySelectorAll('.permissao-item').forEach(item => {
            const checkbox = item.querySelector('.permissao-checkbox');
            const modulo = checkbox.dataset.modulo;
            const nome = item.querySelector('.permissao-nome label').textContent.toLowerCase();
            const descricao = item.querySelector('.permissao-descricao')?.textContent.toLowerCase() || '';
            
            if (nome.includes(termo) || descricao.includes(termo)) {
                item.style.display = 'flex';
                modulosVisiveis.add(modulo);
            } else {
                item.style.display = 'none';
            }
        });

        // Mostrar/ocultar módulos
        document.querySelectorAll('.modulo-permissoes').forEach(modulo => {
            const moduloNome = modulo.dataset.modulo;
            if (modulosVisiveis.has(moduloNome)) {
                modulo.classList.remove('oculto');
                // Expandir automaticamente
                const body = modulo.querySelector('.modulo-body');
                const toggle = modulo.querySelector('.modulo-toggle');
                if (body && toggle) {
                    body.classList.add('expandido');
                    toggle.classList.add('expandido');
                }
            } else {
                modulo.classList.add('oculto');
            }
        });
    }

    async salvarPermissoes() {
        try {
            const btnSalvar = document.getElementById('btnSalvarPermissoes');
            const textoOriginal = btnSalvar.innerHTML;
            
            // Desabilitar botão
            btnSalvar.disabled = true;
            btnSalvar.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Salvando...';

            const permissoesIds = Array.from(this.permissoesSelecionadas);

            const response = await fetch(`/api/v1/permissoes/role/${this.roleAtual.id}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ permissoes_ids: permissoesIds })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Erro ao salvar permissões');
            }

            const data = await response.json();

            // Mostrar notificação de sucesso
            if (typeof mostrarNotificacao === 'function') {
                mostrarNotificacao(data.message || 'Permissões atualizadas com sucesso!', 'success');
            } else {
                alert('Permissões atualizadas com sucesso!');
            }

            // Fechar modal
            if (typeof modalGerenciarPermissoes !== 'undefined') {
                modalGerenciarPermissoes.close();
            }

            // Atualizar tabela de roles
            if (typeof rolesManager !== 'undefined' && rolesManager.carregarRoles) {
                await rolesManager.carregarRoles();
            }

        } catch (error) {
            console.error('Erro ao salvar permissões:', error);
            
            if (typeof mostrarNotificacao === 'function') {
                mostrarNotificacao(error.message || 'Erro ao salvar permissões', 'error');
            } else {
                alert('Erro: ' + (error.message || 'Erro ao salvar permissões'));
            }
        } finally {
            // Reabilitar botão
            const btnSalvar = document.getElementById('btnSalvarPermissoes');
            if (btnSalvar) {
                btnSalvar.disabled = false;
                btnSalvar.innerHTML = '<i class="align-middle me-1" data-feather="save"></i> Salvar Permissões';
                
                if (typeof feather !== 'undefined') {
                    feather.replace();
                }
            }
        }
    }

    mostrarErroCarregamento() {
        const container = document.getElementById('containerModulos');
        container.innerHTML = `
            <div class="text-center py-4">
                <i class="align-middle text-danger" data-feather="alert-circle"></i>
                <p class="text-danger mt-2">Erro ao carregar permissões. Tente novamente.</p>
            </div>
        `;
        
        if (typeof feather !== 'undefined') {
            feather.replace();
        }
    }

    capitalize(str) {
        return str.charAt(0).toUpperCase() + str.slice(1);
    }
}

// Instância global
let permissoesManager;

// Inicializar quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Inicializando PermissoesManager...');
    permissoesManager = new PermissoesManager();
    console.log('✅ PermissoesManager inicializado:', permissoesManager);
});

