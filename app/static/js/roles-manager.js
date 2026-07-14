/**
 * PDV Ibix - Gerenciador de Roles (RBAC)
 * Sistema para gerenciar roles - Apenas Administradores
 */

class RolesManager {
    constructor() {
        this.roles = [];
        this.roleEmEdicao = null;
        this.currentUserRole = null;
        this.totalPermissoesSistema = 28; // Será carregado do backend
        
        this.inicializar();
    }

    async inicializar() {
        const roleDoServidor = window.USER_ROLE || window.__USER_ROLE__ || null;
        if (roleDoServidor === 'Administrador' || roleDoServidor === 'Superadministrador') {
            this.currentUserRole = roleDoServidor;
        } else {
            await this.verificarPermissao();
        }

        const podeGerenciarRoles = this.currentUserRole === 'Administrador' || this.currentUserRole === 'Superadministrador';
        if (!podeGerenciarRoles) {
            return;
        }
        const cardContainer = document.getElementById('cardRolesContainer');
        if (cardContainer) {
            cardContainer.style.display = 'block';
        }
        const carregar = async () => {
            await this.carregarTotalPermissoesSistema();
            await this.carregarRoles();
            this.configurarEventos();
        };
        if (typeof requestIdleCallback === 'function') {
            requestIdleCallback(() => { carregar(); }, { timeout: 1500 });
        } else {
            setTimeout(() => { carregar(); }, 0);
        }
    }

    async verificarPermissao() {
        try {
            const response = await fetch('/api/v1/auth/me', { credentials: 'include' });
            if (response.ok) {
                const userData = await response.json();
                if (userData.role_nome) {
                    this.currentUserRole = userData.role_nome;
                }
            }
        } catch (error) {
            console.error('Erro ao verificar permissão:', error);
        }
    }

    async carregarTotalPermissoesSistema() {
        try {
            const response = await fetch('/api/v1/permissoes/agrupadas/modulos', { credentials: 'include' });
            if (response.ok) {
                const data = await response.json();
                this.totalPermissoesSistema = data.total_permissoes || 28;
            }
        } catch (error) {
            console.error('Erro ao carregar total de permissões:', error);
            // Manter fallback de 28 se houver erro
        }
    }

    configurarEventos() {
        // Botão Nova Role
        const btnNovaRole = document.getElementById('btnNovaRole');
        if (btnNovaRole) {
            btnNovaRole.addEventListener('click', () => {
                this.abrirModalNovaRole();
            });
        }
        
        // Botão Adicionar Permissões
        const btnAdicionarPermissoes = document.getElementById('btnAdicionarPermissoes');
        if (btnAdicionarPermissoes) {
            btnAdicionarPermissoes.addEventListener('click', () => {
                this.abrirModalAdicionarPermissoes();
            });
        }

        // Formulário e eventos do modal Adicionar Permissões (apenas uma vez)
        this.configurarEventosFormularioAdicionarPermissoes();

        // Formulário de Role
        const formRole = document.getElementById('formRole');
        if (formRole) {
            formRole.addEventListener('submit', (e) => {
                e.preventDefault();
                this.salvarRole();
            });
        }

        // Botões de cancelar
        const btnCancelarRole = document.getElementById('btnCancelarRole');
        if (btnCancelarRole) {
            btnCancelarRole.addEventListener('click', () => {
                if (typeof modalNovaRole !== 'undefined') {
                    modalNovaRole.close();
                }
            });
        }

        const btnCancelarExclusaoRole = document.getElementById('btnCancelarExclusaoRole');
        if (btnCancelarExclusaoRole) {
            btnCancelarExclusaoRole.addEventListener('click', () => {
                if (typeof modalConfirmarExclusaoRole !== 'undefined') {
                    modalConfirmarExclusaoRole.close();
                }
            });
        }

        // Event listener para limpar formulário ao fechar modal
        document.addEventListener('modalClosed', (e) => {
            if (e.detail.modalId === 'modalNovaRole') {
                this.limparFormularioRole();
            }
        });
    }

    async carregarRoles() {
        try {
            const response = await fetch('/api/v1/roles/', { credentials: 'include' });
            
            if (!response.ok) {
                throw new Error(`Erro HTTP: ${response.status}`);
            }

            const data = await response.json();
            this.roles = data.roles;
            
            this.renderizarRolesTabela();
            
        } catch (error) {
            console.error('Erro ao carregar roles:', error);
            this.mostrarErroCarregamento();
        }
    }

    renderizarRolesTabela() {
        const tbody = document.getElementById('tbodyRoles');
        if (!tbody) return;

        if (this.roles.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="text-center py-4">
                        <i class="align-middle text-muted" data-feather="shield"></i>
                        <p class="text-muted mt-2 mb-0">Nenhuma role encontrada</p>
                    </td>
                </tr>
            `;
            if (typeof feather !== 'undefined') {
                feather.replace();
            }
            return;
        }

        tbody.innerHTML = '';

        // Roles do sistema que não podem ser excluídas
        const rolesSistema = ['Administrador', 'Técnico', 'Subcliente', 'Visualizador', 'Auditor'];

        this.roles.forEach(role => {
            const tr = document.createElement('tr');
            const isRoleSistema = rolesSistema.includes(role.nome);
            
            // Badge de status
            const badgeStatus = role.ativo 
                ? '<span class="badge bg-success">Ativo</span>' 
                : '<span class="badge bg-secondary">Inativo</span>';
            
            // Badge de tipo
            const badgeTipo = isRoleSistema 
                ? '<span class="badge bg-info">Sistema</span>' 
                : '<span class="badge bg-primary">Customizada</span>';
            
            // Contador de usuários
            const totalUsuarios = role.total_usuarios || 0;
            
            // Calcular total de permissões (vem do backend)
            const totalPermissoes = role.total_permissoes || 0;
            const totalPermissoesSistema = this.totalPermissoesSistema || 28; // Fallback temporário
            const percentual = totalPermissoes > 0 ? Math.round((totalPermissoes / totalPermissoesSistema) * 100) : 0;
            
            let badgePercentual = '';
            if (percentual >= 80) {
                badgePercentual = 'bg-success';
            } else if (percentual >= 40) {
                badgePercentual = 'bg-primary';
            } else if (percentual >= 10) {
                badgePercentual = 'bg-warning';
            } else {
                badgePercentual = 'bg-danger';
            }
            
            tr.innerHTML = `
                <td><strong>#${role.id}</strong></td>
                <td>
                    <strong>${role.nome}</strong>
                </td>
                <td>
                    <small class="text-muted">${role.descricao || 'Sem descrição'}</small>
                </td>
                <td>${badgeStatus}</td>
                <td>${badgeTipo}</td>
                <td>
                    <span class="badge bg-light text-dark">
                        <i class="align-middle" data-feather="users"></i>
                        ${totalUsuarios}
                    </span>
                </td>
                <td>
                    <span class="badge ${badgePercentual}">
                        <i class="align-middle" data-feather="key"></i>
                        ${totalPermissoes}/${totalPermissoesSistema} (${percentual}%)
                    </span>
                </td>
                <td>
                    <div class="btn-group btn-group-sm" role="group">
                        <button type="button" class="btn btn-outline-info" 
                                onclick="rolesManager.gerenciarPermissoes(${role.id}, '${role.nome.replace(/'/g, "\\'")}')"
                                title="Gerenciar permissões">
                            <i class="align-middle" data-feather="key"></i>
                        </button>
                        <button type="button" class="btn btn-outline-primary" 
                                onclick="rolesManager.editarRole(${role.id})"
                                title="Editar role">
                            <i class="align-middle" data-feather="edit-2"></i>
                        </button>
                        ${!isRoleSistema ? `
                        <button type="button" class="btn btn-outline-danger" 
                                onclick="rolesManager.confirmarExclusaoRole(${role.id}, '${role.nome.replace(/'/g, "\\'")}')"
                                title="Excluir role">
                            <i class="align-middle" data-feather="trash-2"></i>
                        </button>
                        ` : `
                        <button type="button" class="btn btn-outline-secondary" 
                                disabled
                                title="Roles do sistema não podem ser excluídas">
                            <i class="align-middle" data-feather="lock"></i>
                        </button>
                        `}
                    </div>
                </td>
            `;
            
            tbody.appendChild(tr);
        });

        // Atualizar ícones Feather
        if (typeof feather !== 'undefined') {
            feather.replace();
        }
    }

    mostrarErroCarregamento() {
        const tbody = document.getElementById('tbodyRoles');
        if (!tbody) return;

        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center py-4">
                    <i class="align-middle text-danger" data-feather="alert-circle"></i>
                    <p class="text-danger mt-2 mb-0">Erro ao carregar roles. Tente novamente.</p>
                </td>
            </tr>
        `;
        
        if (typeof feather !== 'undefined') {
            feather.replace();
        }
    }

    abrirModalNovaRole() {
        this.roleEmEdicao = null;
        this.limparFormularioRole();
        
        // Atualizar título
        document.getElementById('modalNovaRoleLabel').innerHTML = `
            <i class="align-middle" data-feather="shield"></i>
            Nova Role
        `;
        
        // Atualizar botão
        const btnSalvar = document.getElementById('btnSalvarRole');
        if (btnSalvar) {
            btnSalvar.innerHTML = '<i class="align-middle me-1" data-feather="save"></i> Salvar Role';
        }
        
        // Abrir modal
        if (typeof modalNovaRole !== 'undefined') {
            modalNovaRole.open();
        }
    }

    abrirModalAdicionarPermissoes() {
        if (typeof modalAdicionarPermissoes !== 'undefined' && modalAdicionarPermissoes.modal) {
            modalAdicionarPermissoes.open();
        }
        this.limparFormularioAdicionarPermissoes();
        this.carregarModulosDoBanco();
    }

    async carregarModulosDoBanco() {
        const select = document.getElementById('novoModulo');
        if (!select) return;
        try {
            const response = await fetch('/api/v1/permissoes/agrupadas/modulos', {
                credentials: 'include'
            });
            if (!response.ok) return;
            const data = await response.json();
            const modulos = data.modulos ? Object.keys(data.modulos).sort() : [];
            const optsAtuais = Array.from(select.options).map(o => o.value);
            const valorOutro = 'outro';
            const valorVazio = '';
            if (modulos.length === 0) return;
            select.innerHTML = '';
            const opt0 = document.createElement('option');
            opt0.value = '';
            opt0.textContent = 'Selecione um módulo...';
            select.appendChild(opt0);
            modulos.forEach(mod => {
                const opt = document.createElement('option');
                opt.value = mod;
                opt.textContent = mod.charAt(0).toUpperCase() + mod.slice(1).replace(/_/g, ' ');
                select.appendChild(opt);
            });
            const optOutro = document.createElement('option');
            optOutro.value = 'outro';
            optOutro.textContent = 'Outro (novo módulo)';
            select.appendChild(optOutro);
        } catch (err) {
            console.error('Erro ao carregar módulos:', err);
        }
    }
    
    limparFormularioAdicionarPermissoes() {
        // Limpar formulário com verificações de segurança
        const novoModulo = document.getElementById('novoModulo');
        if (novoModulo) novoModulo.value = '';
        
        const novoModuloNome = document.getElementById('novoModuloNome');
        if (novoModuloNome) novoModuloNome.value = '';
        
        const grupoNovoModulo = document.getElementById('grupoNovoModulo');
        if (grupoNovoModulo) grupoNovoModulo.style.display = 'none';
        
        this.limparPermissoesExistentes();
        
        const previewPermissoes = document.getElementById('previewPermissoes');
        if (previewPermissoes) previewPermissoes.innerHTML = '<span class="text-muted">Nenhuma permissão selecionada</span>';
    }

    limparPermissoesExistentes() {
        const grupo = document.getElementById('grupoPermissoesExistentes');
        const lista = document.getElementById('listaPermissoesExistentes');
        if (grupo) grupo.style.display = 'none';
        if (lista) lista.innerHTML = '';
        const acoes = ['permVisualizar', 'permCriar', 'permEditar', 'permExcluir'];
        const valores = { permVisualizar: 'visualizar', permCriar: 'criar', permEditar: 'editar', permExcluir: 'excluir' };
        acoes.forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.checked = false;
                el.disabled = false;
            }
        });
    }

    async carregarPermissoesDoModulo(modulo) {
        const grupo = document.getElementById('grupoPermissoesExistentes');
        const lista = document.getElementById('listaPermissoesExistentes');
        const permVisualizar = document.getElementById('permVisualizar');
        const permCriar = document.getElementById('permCriar');
        const permEditar = document.getElementById('permEditar');
        const permExcluir = document.getElementById('permExcluir');
        const checkboxes = [
            { el: permVisualizar, acao: 'visualizar' },
            { el: permCriar, acao: 'criar' },
            { el: permEditar, acao: 'editar' },
            { el: permExcluir, acao: 'excluir' }
        ];
        checkboxes.forEach(({ el }) => {
            if (el) {
                el.checked = false;
                el.disabled = false;
            }
        });
        try {
            const response = await fetch(`/api/v1/permissoes/modulo/${encodeURIComponent(modulo)}`, {
                credentials: 'include'
            });
            if (response.status === 404) {
                if (grupo) grupo.style.display = 'none';
                if (lista) lista.innerHTML = '';
                return;
            }
            if (!response.ok) {
                throw new Error(`Erro HTTP: ${response.status}`);
            }
            const data = await response.json();
            const permissoes = data.permissoes || [];
            if (permissoes.length === 0) {
                if (grupo) grupo.style.display = 'none';
                if (lista) lista.innerHTML = '';
                return;
            }
            if (grupo) grupo.style.display = 'block';
            if (lista) {
                lista.innerHTML = permissoes.map(p => {
                    const nome = p.nome || `${p.modulo || modulo}:${p.acao || ''}`;
                    return `<span class="badge bg-secondary me-1 mb-1">${nome}</span>`;
                }).join('');
            }
            const acoesExistentes = new Set(permissoes.map(p => (p.acao || '').toLowerCase()));
            checkboxes.forEach(({ el, acao }) => {
                if (!el) return;
                if (acoesExistentes.has(acao)) {
                    el.checked = true;
                    el.disabled = true;
                }
            });
        } catch (err) {
            console.error('Erro ao carregar permissões do módulo:', err);
            if (grupo) grupo.style.display = 'none';
            if (lista) lista.innerHTML = '';
        }
    }

    configurarEventosFormularioAdicionarPermissoes() {
        if (!document.getElementById('formAdicionarPermissoes')) return;
        // Preview das permissões em tempo real
        const novoModulo = document.getElementById('novoModulo');
        const novoModuloNome = document.getElementById('novoModuloNome');
        const grupoNovoModulo = document.getElementById('grupoNovoModulo');
        const previewPermissoes = document.getElementById('previewPermissoes');
        const checkboxes = [
            document.getElementById('permVisualizar'),
            document.getElementById('permCriar'),
            document.getElementById('permEditar'),
            document.getElementById('permExcluir')
        ];
        
        // Função para obter o valor do módulo (do select ou do campo de novo módulo)
        const obterModulo = () => {
            const moduloSelecionado = novoModulo ? novoModulo.value : '';
            if (moduloSelecionado === 'outro') {
                return novoModuloNome ? novoModuloNome.value.trim() : '';
            }
            return moduloSelecionado;
        };
        
        // Mostrar/ocultar campo de novo módulo
        const toggleCampoNovoModulo = () => {
            if (novoModulo && grupoNovoModulo) {
                if (novoModulo.value === 'outro') {
                    grupoNovoModulo.style.display = 'block';
                    if (novoModuloNome) {
                        novoModuloNome.required = true;
                        novoModuloNome.focus();
                    }
                } else {
                    grupoNovoModulo.style.display = 'none';
                    if (novoModuloNome) {
                        novoModuloNome.required = false;
                        novoModuloNome.value = '';
                    }
                }
            }
        };
        
        const atualizarPreview = () => {
            if (!previewPermissoes) return;
            const modulo = obterModulo();
            const permissoesSelecionadas = checkboxes.filter(cb => cb && cb.checked).map(cb => cb.value);
            
            if (!modulo) {
                previewPermissoes.innerHTML = '<span class="text-muted">Selecione um módulo</span>';
                return;
            }
            
            if (permissoesSelecionadas.length === 0) {
                previewPermissoes.innerHTML = '<span class="text-muted">Nenhuma permissão selecionada</span>';
                return;
            }
            
            const preview = permissoesSelecionadas.map(acao => {
                const descricao = this.getDescricaoPermissao(modulo, acao);
                return `<div class="badge bg-primary me-1 mb-1">${modulo}:${acao}</div><br><small class="text-muted">${descricao}</small>`;
            }).join('<br>');
            
            previewPermissoes.innerHTML = preview;
        };
        
        // Ao mudar o módulo: buscar permissões do banco e preencher/desabilitar checkboxes
        if (novoModulo) {
            novoModulo.addEventListener('change', () => {
                toggleCampoNovoModulo();
                const mod = (novoModulo.value || '').trim();
                if (mod && mod !== 'outro') {
                    this.carregarPermissoesDoModulo(mod);
                } else {
                    this.limparPermissoesExistentes();
                }
                atualizarPreview();
            });
        }
        
        if (novoModuloNome) {
            novoModuloNome.addEventListener('input', () => {
                // Validar formato (apenas letras minúsculas, números, hífens e underscores)
                const valor = novoModuloNome.value.trim();
                const regex = /^[a-z0-9_-]+$/;
                if (valor && !regex.test(valor)) {
                    novoModuloNome.setCustomValidity('Apenas letras minúsculas, números, hífens e underscores são permitidos');
                } else {
                    novoModuloNome.setCustomValidity('');
                }
                atualizarPreview();
            });
        }
        
        checkboxes.forEach(checkbox => {
            if (checkbox) {
                checkbox.addEventListener('change', atualizarPreview);
            }
        });
        
        // Botão salvar
        const btnSalvar = document.getElementById('btnSalvarAdicionarPermissoes');
        if (btnSalvar) {
            btnSalvar.onclick = () => this.salvarNovaPermissao();
        }
        
        // Botão cancelar
        const btnCancelar = document.getElementById('btnCancelarAdicionarPermissoes');
        if (btnCancelar) {
            btnCancelar.onclick = () => {
                if (typeof modalAdicionarPermissoes !== 'undefined') {
                    modalAdicionarPermissoes.close();
                }
            };
        }
        
        // Botão fechar modal
        const btnFechar = document.getElementById('btnCloseModalAdicionarPermissoes');
        if (btnFechar) {
            btnFechar.onclick = () => {
                if (typeof modalAdicionarPermissoes !== 'undefined') {
                    modalAdicionarPermissoes.close();
                }
            };
        }
    }

    getDescricaoPermissao(modulo, acao) {
        const descricoes = {
            'visualizar': `Visualizar lista de ${modulo}`,
            'criar': `Criar novos ${modulo}`,
            'editar': `Editar ${modulo} existentes`,
            'excluir': `Excluir ${modulo}`
        };
        return descricoes[acao] || `${acao} ${modulo}`;
    }

    async salvarNovaPermissao() {
        const moduloElement = document.getElementById('novoModulo');
        if (!moduloElement) {
            alert('Erro: Campo de módulo não encontrado');
            return;
        }
        
        // Obter o valor do módulo (do select ou do campo de novo módulo)
        let modulo = moduloElement.value.trim();
        
        if (modulo === 'outro') {
            const novoModuloNome = document.getElementById('novoModuloNome');
            if (!novoModuloNome) {
                alert('Erro: Campo de nome do novo módulo não encontrado');
                return;
            }
            
            modulo = novoModuloNome.value.trim();
            
            if (!modulo) {
                alert('Por favor, digite o nome do novo módulo');
                if (novoModuloNome) novoModuloNome.focus();
                return;
            }
            
            // Validar formato (apenas letras minúsculas, números, hífens e underscores)
            const regex = /^[a-z0-9_-]+$/;
            if (!regex.test(modulo)) {
                alert('O nome do módulo deve conter apenas letras minúsculas, números, hífens e underscores');
                if (novoModuloNome) novoModuloNome.focus();
                return;
            }
        }
        
        if (!modulo) {
            alert('Por favor, selecione um módulo');
            return;
        }
        
        const checkboxes = [
            { id: 'permVisualizar', value: 'visualizar' },
            { id: 'permCriar', value: 'criar' },
            { id: 'permEditar', value: 'editar' },
            { id: 'permExcluir', value: 'excluir' }
        ];
        
        const permissoesSelecionadas = checkboxes.filter(cb => {
            const element = document.getElementById(cb.id);
            return element && element.checked;
        });
        
        if (permissoesSelecionadas.length === 0) {
            alert('Por favor, selecione pelo menos uma permissão');
            return;
        }
        
        try {
            // Criar todas as permissões selecionadas
            const promises = permissoesSelecionadas.map(async (perm) => {
                const nomePermissao = `${modulo}:${perm.value}`;
                const descricao = this.getDescricaoPermissao(modulo, perm.value);
                
                const response = await fetch('/api/v1/permissoes', {
                    method: 'POST',
                    credentials: 'include',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        nome: nomePermissao,
                        descricao: descricao,
                        modulo: modulo,
                        acao: perm.value,
                        ativo: true
                    })
                });
                
                if (!response.ok) {
                    const errorData = await response.json();
                    if (errorData.detail && errorData.detail.includes('já existe')) {
                        return { nome: nomePermissao, status: 'existe' };
                    } else {
                        throw new Error(`Erro ao criar ${nomePermissao}: ${errorData.detail || 'Erro desconhecido'}`);
                    }
                }
                
                return { nome: nomePermissao, status: 'criada' };
            });
            
            const resultados = await Promise.all(promises);
            
            // Separar permissões criadas das que já existiam
            const criadas = resultados.filter(r => r.status === 'criada');
            const existentes = resultados.filter(r => r.status === 'existe');
            
            // Criar mensagem detalhada
            let mensagem = '';
            if (criadas.length > 0) {
                mensagem += `✅ ${criadas.length} permissão(ões) criada(s) com sucesso:\n`;
                mensagem += criadas.map(p => `   • ${p.nome}`).join('\n');
            }
            if (existentes.length > 0) {
                if (mensagem) mensagem += '\n\n';
                mensagem += `⚠️ ${existentes.length} permissão(ões) já existiam:\n`;
                mensagem += existentes.map(p => `   • ${p.nome}`).join('\n');
            }
            
            alert(mensagem);
            
            if (typeof modalAdicionarPermissoes !== 'undefined') {
                modalAdicionarPermissoes.close();
            }
            
            // Recarregar roles para mostrar as novas permissões
            await this.carregarRoles();
            
        } catch (error) {
            console.error('Erro ao salvar permissões:', error);
            alert(`Erro ao criar permissões: ${error.message}`);
        }
    }

    async editarRole(roleId) {
        try {
            const response = await fetch(`/api/v1/roles/${roleId}`);
            if (!response.ok) {
                throw new Error(`Erro HTTP: ${response.status}`);
            }

            const role = await response.json();
            this.roleEmEdicao = role;
            
            // Preencher formulário
            document.getElementById('roleId').value = role.id;
            document.getElementById('roleNome').value = role.nome;
            document.getElementById('roleDescricao').value = role.descricao || '';
            document.getElementById('roleAtivo').checked = role.ativo;
            
            // Atualizar título
            document.getElementById('modalNovaRoleLabel').innerHTML = `
                <i class="align-middle" data-feather="edit-2"></i>
                Editar Role
            `;
            
            // Atualizar botão
            const btnSalvar = document.getElementById('btnSalvarRole');
            if (btnSalvar) {
                btnSalvar.innerHTML = '<i class="align-middle me-1" data-feather="save"></i> Atualizar Role';
            }
            
            // Abrir modal
            if (typeof modalNovaRole !== 'undefined') {
                modalNovaRole.open();
            }
            
        } catch (error) {
            console.error('Erro ao carregar role:', error);
            if (typeof mostrarNotificacao === 'function') {
                mostrarNotificacao('Erro ao carregar dados da role', 'error');
            } else {
                alert('Erro ao carregar dados da role');
            }
        }
    }

    limparFormularioRole() {
        document.getElementById('formRole').reset();
        document.getElementById('roleId').value = '';
        this.roleEmEdicao = null;
    }

    async salvarRole() {
        try {
            const dados = {
                nome: document.getElementById('roleNome').value.trim(),
                descricao: document.getElementById('roleDescricao').value.trim() || null,
                ativo: document.getElementById('roleAtivo').checked
            };

            if (!dados.nome) {
                if (typeof mostrarNotificacao === 'function') {
                    mostrarNotificacao('Nome da role é obrigatório', 'error');
                } else {
                    alert('Nome da role é obrigatório');
                }
                return;
            }

            const url = this.roleEmEdicao 
                ? `/api/v1/roles/${this.roleEmEdicao.id}`
                : '/api/v1/roles/';
            
            const method = this.roleEmEdicao ? 'PUT' : 'POST';

            const response = await fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(dados)
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Erro ao salvar role');
            }

            const mensagem = this.roleEmEdicao 
                ? 'Role atualizada com sucesso!' 
                : 'Role criada com sucesso!';
            
            if (typeof mostrarNotificacao === 'function') {
                mostrarNotificacao(mensagem, 'success');
            } else {
                alert(mensagem);
            }

            // Fechar modal
            if (typeof modalNovaRole !== 'undefined') {
                modalNovaRole.close();
            }
            
            // Recarregar roles
            await this.carregarRoles();
            
            // Atualizar select de roles no formulário de usuário
            if (typeof gerenciamentoUsuarios !== 'undefined') {
                await gerenciamentoUsuarios.carregarRoles();
            }
            
        } catch (error) {
            console.error('Erro ao salvar role:', error);
            if (typeof mostrarNotificacao === 'function') {
                mostrarNotificacao(error.message || 'Erro ao salvar role', 'error');
            } else {
                alert('Erro: ' + (error.message || 'Erro ao salvar role'));
            }
        }
    }

    gerenciarPermissoes(roleId, roleNome) {
        // Abrir modal de gerenciamento de permissões
        if (typeof permissoesManager !== 'undefined') {
            permissoesManager.abrirModal(roleId, roleNome);
        } else {
            console.error('PermissoesManager não está disponível');
            alert('Erro: Sistema de gerenciamento de permissões não está carregado');
        }
    }

    confirmarExclusaoRole(roleId, roleNome) {
        document.getElementById('nomeRoleExclusao').textContent = roleNome;
        
        // Abrir modal de confirmação
        if (typeof modalConfirmarExclusaoRole !== 'undefined') {
            modalConfirmarExclusaoRole.open();
        }
        
        // Configurar botão de confirmação
        document.getElementById('btnConfirmarExclusaoRole').onclick = () => {
            this.excluirRole(roleId);
        };
    }

    async excluirRole(roleId) {
        try {
            const response = await fetch(`/api/v1/roles/${roleId}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Erro ao excluir role');
            }

            if (typeof mostrarNotificacao === 'function') {
                mostrarNotificacao('Role excluída com sucesso!', 'success');
            } else {
                alert('Role excluída com sucesso!');
            }
            
            // Fechar modal
            if (typeof modalConfirmarExclusaoRole !== 'undefined') {
                modalConfirmarExclusaoRole.close();
            }
            
            // Recarregar roles
            await this.carregarRoles();
            
            // Atualizar select de roles no formulário de usuário
            if (typeof gerenciamentoUsuarios !== 'undefined') {
                await gerenciamentoUsuarios.carregarRoles();
            }
            
        } catch (error) {
            console.error('Erro ao excluir role:', error);
            if (typeof mostrarNotificacao === 'function') {
                mostrarNotificacao(error.message || 'Erro ao excluir role', 'error');
            } else {
                alert('Erro: ' + (error.message || 'Erro ao excluir role'));
            }
        }
    }
}

// Instância global do gerenciador de roles
let rolesManager;

// Inicializar quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Inicializando RolesManager...');
    rolesManager = new RolesManager();
    console.log('✅ RolesManager inicializado:', rolesManager);
});

