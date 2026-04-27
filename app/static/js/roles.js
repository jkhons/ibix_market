/**
 * PDV Ibix - Gerenciamento de Roles RBAC
 * JavaScript para funcionalidades da página de roles
 */

class GerenciamentoRoles {
    constructor() {
        this.roles = [];
        this.paginaAtual = 1;
        this.limitePorPagina = 10;
        this.filtros = {
            nome: '',
            status: ''
        };
        this.roleEmEdicao = null;
        this.rolesSistema = ['Administrador', 'Técnico', 'Subcliente', 'Visualizador', 'Auditor'];
        
        this.inicializar();
    }

    inicializar() {
        this.configurarEventos();
        this.carregarRoles();
        this.configurarFeatherIcons();
    }

    configurarEventos() {
        // Filtros
        document.getElementById('filtroNome').addEventListener('input', (e) => {
            this.filtros.nome = e.target.value;
            this.aplicarFiltros();
        });

        document.getElementById('filtroStatus').addEventListener('change', (e) => {
            this.filtros.status = e.target.value;
            this.aplicarFiltros();
        });

        document.getElementById('btnLimparFiltros').addEventListener('click', () => {
            this.limparFiltros();
        });

        // Formulário
        document.getElementById('formRole').addEventListener('submit', (e) => {
            e.preventDefault();
            this.salvarRole();
        });
        
        // Limpar formulário ao fechar modal
        document.addEventListener('modalClosed', (e) => {
            if (e.detail.modalId === 'modalNovaRole') {
                this.limparFormulario();
            }
        });
    }

    async carregarRoles() {
        try {
            this.mostrarLoading();
            
            const params = new URLSearchParams({
                skip: (this.paginaAtual - 1) * this.limitePorPagina,
                limit: this.limitePorPagina
            });

            if (this.filtros.status !== '') {
                params.append('ativo', this.filtros.status);
            }

            const response = await fetch(`/api/v1/roles/?${params}`);
            
            if (!response.ok) {
                if (response.status === 403) {
                    this.mostrarErro('Acesso negado. Apenas administradores podem gerenciar roles.');
                    return;
                }
                throw new Error(`Erro HTTP: ${response.status}`);
            }

            const data = await response.json();
            this.roles = data.roles;
            
            this.renderizarTabela();
            this.renderizarPaginacao(data.total);
            this.atualizarInfoPagina(data.total);
            
        } catch (error) {
            console.error('Erro ao carregar roles:', error);
            this.mostrarErro('Erro ao carregar roles. Tente novamente.');
        } finally {
            this.ocultarLoading();
        }
    }

    aplicarFiltros() {
        this.paginaAtual = 1;
        
        // Aplicar filtros no frontend
        if (this.filtros.nome) {
            this.aplicarFiltrosFrontend();
        } else {
            this.carregarRoles();
        }
    }

    aplicarFiltrosFrontend() {
        const rolesFiltradas = this.roles.filter(role => {
            const nomeMatch = !this.filtros.nome || 
                role.nome.toLowerCase().includes(this.filtros.nome.toLowerCase());
            
            const statusMatch = !this.filtros.status || 
                role.ativo.toString() === this.filtros.status;
            
            return nomeMatch && statusMatch;
        });
        
        this.renderizarTabela(rolesFiltradas);
        this.renderizarPaginacao(rolesFiltradas.length);
        this.atualizarInfoPagina(rolesFiltradas.length);
    }

    limparFiltros() {
        document.getElementById('filtroNome').value = '';
        document.getElementById('filtroStatus').value = '';
        
        this.filtros = {
            nome: '',
            status: ''
        };
        
        this.aplicarFiltros();
    }

    renderizarTabela(roles = null) {
        const tbody = document.getElementById('tbodyRoles');
        tbody.innerHTML = '';
        
        const rolesParaRenderizar = roles || this.roles;

        if (rolesParaRenderizar.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="text-center text-muted py-4">
                        <i class="align-middle me-2" data-feather="shield"></i>
                        Nenhuma role encontrada
                    </td>
                </tr>
            `;
            this.configurarFeatherIcons();
            return;
        }

        rolesParaRenderizar.forEach(role => {
            const tr = document.createElement('tr');
            const isRoleSistema = this.rolesSistema.includes(role.nome);
            
            // Badge de status
            const badgeStatus = role.ativo 
                ? '<span class="badge bg-success">Ativo</span>' 
                : '<span class="badge bg-secondary">Inativo</span>';
            
            // Badge de tipo
            const badgeTipo = isRoleSistema 
                ? '<span class="badge bg-info">Sistema</span>' 
                : '<span class="badge bg-primary">Customizada</span>';
            
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
                    <button class="btn btn-sm btn-outline-info" onclick="gerenciamentoRoles.verUsuariosRole(${role.id})">
                        <i class="align-middle" data-feather="users"></i>
                        Ver Usuários
                    </button>
                </td>
                <td>
                    <small class="text-muted">
                        ${this.formatarData(role.created_at)}
                    </small>
                </td>
                <td>
                    <div class="btn-group btn-group-sm" role="group">
                        <button type="button" class="btn btn-outline-primary" 
                                onclick="gerenciamentoRoles.editarRole(${role.id})"
                                title="Editar role">
                            <i class="align-middle" data-feather="edit-2"></i>
                        </button>
                        ${!isRoleSistema ? `
                        <button type="button" class="btn btn-outline-danger" 
                                onclick="gerenciamentoRoles.confirmarExclusao(${role.id}, '${role.nome.replace(/'/g, "\\'")}')"
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

        this.configurarFeatherIcons();
    }

    formatarData(dataString) {
        if (!dataString) return '-';
        const s = String(dataString).trim();
        const d = /^\d{4}-\d{2}-\d{2}$/.test(s) ? new Date(s + 'T12:00:00') : new Date(dataString);
        if (isNaN(d.getTime())) return '-';
        return d.toLocaleDateString('pt-BR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric'
        });
    }

    renderizarPaginacao(total) {
        const paginacao = document.getElementById('paginacao');
        const totalPaginas = Math.ceil(total / this.limitePorPagina);
        
        if (totalPaginas <= 1) {
            paginacao.innerHTML = '';
            return;
        }

        let html = '';

        // Botão anterior
        html += `
            <li class="page-item ${this.paginaAtual === 1 ? 'disabled' : ''}">
                <a class="page-link" href="#" onclick="gerenciamentoRoles.irParaPagina(${this.paginaAtual - 1})">
                    <i class="align-middle" data-feather="chevron-left"></i>
                </a>
            </li>
        `;

        // Páginas numeradas
        for (let i = 1; i <= totalPaginas; i++) {
            if (i === 1 || i === totalPaginas || (i >= this.paginaAtual - 2 && i <= this.paginaAtual + 2)) {
                html += `
                    <li class="page-item ${i === this.paginaAtual ? 'active' : ''}">
                        <a class="page-link" href="#" onclick="gerenciamentoRoles.irParaPagina(${i})">${i}</a>
                    </li>
                `;
            } else if (i === this.paginaAtual - 3 || i === this.paginaAtual + 3) {
                html += '<li class="page-item disabled"><span class="page-link">...</span></li>';
            }
        }

        // Botão próximo
        html += `
            <li class="page-item ${this.paginaAtual === totalPaginas ? 'disabled' : ''}">
                <a class="page-link" href="#" onclick="gerenciamentoRoles.irParaPagina(${this.paginaAtual + 1})">
                    <i class="align-middle" data-feather="chevron-right"></i>
                </a>
            </li>
        `;

        paginacao.innerHTML = html;
        this.configurarFeatherIcons();
    }

    irParaPagina(pagina) {
        if (pagina < 1) return;
        this.paginaAtual = pagina;
        this.carregarRoles();
    }

    atualizarInfoPagina(total) {
        const inicio = (this.paginaAtual - 1) * this.limitePorPagina + 1;
        const fim = Math.min(this.paginaAtual * this.limitePorPagina, total);
        
        document.getElementById('infoPagina').textContent = `${inicio}-${fim}`;
        document.getElementById('totalRoles').textContent = total;
    }

    async editarRole(id) {
        try {
            const response = await fetch(`/api/v1/roles/${id}`);
            if (!response.ok) {
                throw new Error(`Erro HTTP: ${response.status}`);
            }

            const role = await response.json();
            this.roleEmEdicao = role;
            this.preencherFormulario(role);
            
            // Alterar título do modal
            document.getElementById('modalNovaRoleLabel').innerHTML = `
                <i class="align-middle me-2" data-feather="edit-2"></i>
                Editar Role
            `;
            
            // Alterar texto do botão
            const btnSalvar = document.getElementById('btnSalvarRole');
            btnSalvar.innerHTML = '<i class="align-middle me-1" data-feather="save"></i> Atualizar Role';
            
            // Mostrar modal customizado
            if (typeof modalNovaRole !== 'undefined') {
                modalNovaRole.open();
            }
            
        } catch (error) {
            console.error('Erro ao carregar role:', error);
            this.mostrarErro('Erro ao carregar dados da role.');
        }
    }

    preencherFormulario(role) {
        document.getElementById('roleId').value = role.id;
        document.getElementById('nome').value = role.nome;
        document.getElementById('descricao').value = role.descricao || '';
        document.getElementById('ativo').checked = role.ativo;
    }

    limparFormulario() {
        document.getElementById('formRole').reset();
        document.getElementById('roleId').value = '';
        this.roleEmEdicao = null;
        
        // Restaurar título e botão
        document.getElementById('modalNovaRoleLabel').innerHTML = `
            <i class="align-middle me-2" data-feather="plus-circle"></i>
            Nova Role
        `;
        
        const btnSalvar = document.getElementById('btnSalvarRole');
        if (btnSalvar) {
            btnSalvar.innerHTML = '<i class="align-middle me-1" data-feather="save"></i> Salvar Role';
        }
    }

    async salvarRole() {
        try {
            // Coletar dados do formulário
            const dados = {
                nome: document.getElementById('nome').value.trim(),
                descricao: document.getElementById('descricao').value.trim() || null,
                ativo: document.getElementById('ativo').checked
            };
            
            // Validar nome
            if (!dados.nome || dados.nome.length < 2) {
                this.mostrarErro('Nome da role é obrigatório (mínimo 2 caracteres)');
                return;
            }

            const url = this.roleEmEdicao 
                ? `/api/v1/roles/${this.roleEmEdicao.id}`
                : '/api/v1/roles/';
            
            const method = this.roleEmEdicao ? 'PUT' : 'POST';

            console.log('Enviando dados:', dados);

            const response = await fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(dados)
            });

            if (!response.ok) {
                const errorData = await response.json();
                console.error('Erro do servidor:', errorData);
                throw new Error(errorData.detail || 'Erro ao salvar role');
            }

            this.mostrarSucesso(
                this.roleEmEdicao 
                    ? 'Role atualizada com sucesso!' 
                    : 'Role criada com sucesso!'
            );

            // Fechar modal customizado e recarregar dados
            if (typeof modalNovaRole !== 'undefined') {
                modalNovaRole.close();
            }
            
            this.carregarRoles();
            
        } catch (error) {
            console.error('Erro ao salvar role:', error);
            this.mostrarErro(error.message || 'Erro ao salvar role. Tente novamente.');
        }
    }

    confirmarExclusao(id, nome) {
        document.getElementById('nomeRoleExclusao').textContent = nome;
        
        // Abrir modal customizado
        if (typeof modalConfirmacaoRole !== 'undefined') {
            modalConfirmacaoRole.open();
        }
        
        // Configurar botão de confirmação
        document.getElementById('btnConfirmarExclusao').onclick = () => {
            this.excluirRole(id);
        };
    }

    async excluirRole(id) {
        try {
            const response = await fetch(`/api/v1/roles/${id}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `Erro HTTP: ${response.status}`);
            }

            this.mostrarSucesso('Role excluída com sucesso!');
            
            // Fechar modal customizado e recarregar dados
            if (typeof modalConfirmacaoRole !== 'undefined') {
                modalConfirmacaoRole.close();
            }
            
            this.carregarRoles();
            
        } catch (error) {
            console.error('Erro ao excluir role:', error);
            this.mostrarErro(error.message || 'Erro ao excluir role. Tente novamente.');
        }
    }

    async verUsuariosRole(roleId) {
        try {
            const response = await fetch(`/api/v1/roles/${roleId}/usuarios`);
            
            if (!response.ok) {
                throw new Error(`Erro HTTP: ${response.status}`);
            }

            const data = await response.json();
            
            // Criar mensagem
            let mensagem = `<div style="text-align: left;">`;
            mensagem += `<p><strong>Role:</strong> ${data.role_nome}</p>`;
            mensagem += `<p><strong>Total de usuários:</strong> ${data.total_usuarios}</p>`;
            
            if (data.total_usuarios > 0) {
                mensagem += `<hr><p><strong>Usuários:</strong></p><ul>`;
                data.usuarios.forEach(u => {
                    mensagem += `<li>${u.nome} (${u.email}) - ${u.ativo ? 'Ativo' : 'Inativo'}</li>`;
                });
                mensagem += `</ul>`;
            }
            mensagem += `</div>`;
            
            // Mostrar em alert (pode ser melhorado com um modal customizado)
            this.mostrarInfo(mensagem);
            
        } catch (error) {
            console.error('Erro ao carregar usuários:', error);
            this.mostrarErro('Erro ao carregar usuários da role.');
        }
    }

    mostrarLoading() {
        // Implementar indicador de carregamento se necessário
    }

    ocultarLoading() {
        // Implementar ocultação de carregamento se necessário
    }

    mostrarSucesso(mensagem) {
        if (typeof mostrarNotificacao === 'function') {
            mostrarNotificacao(mensagem, 'success');
        } else if (typeof showAlert === 'function') {
            showAlert(mensagem, 'success');
        } else {
            alert(mensagem);
        }
    }

    mostrarErro(mensagem) {
        if (typeof mostrarNotificacao === 'function') {
            mostrarNotificacao(mensagem, 'error');
        } else if (typeof showAlert === 'function') {
            showAlert(mensagem, 'danger');
        } else {
            alert('Erro: ' + mensagem);
        }
    }

    mostrarInfo(mensagem) {
        if (typeof mostrarNotificacao === 'function') {
            mostrarNotificacao(mensagem, 'info');
        } else {
            alert(mensagem);
        }
    }

    configurarFeatherIcons() {
        if (typeof feather !== 'undefined') {
            feather.replace();
        }
    }
}

// Inicializar quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', () => {
    window.gerenciamentoRoles = new GerenciamentoRoles();
});

