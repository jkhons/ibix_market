/**
 * PDV Ibix - Gerenciamento de Usuários
 * Visibilidade e ações por permissão granular (usuarios:visualizar, usuarios:criar, etc.)
 */

const PERMS = Array.isArray(window.USER_PERMISSIONS) ? window.USER_PERMISSIONS : [];
const has = (p) => PERMS.includes(p);
const canView = has('usuarios:visualizar');
const canCreate = has('usuarios:criar');
const canEdit = has('usuarios:editar');
const canDelete = has('usuarios:excluir');

function getTokenUsuarios() {
    if (typeof window.getAuthToken === 'function') {
        return window.getAuthToken();
    }
    const m = document.cookie.match(/(?:^|;\s*)pdv_solumatica_token=([^;]*)/)
        || document.cookie.match(/(?:^|;\s*)pdv_automscale_token=([^;]*)/);
    return m ? decodeURIComponent(m[1]) : (
        sessionStorage.getItem('pdv_solumatica_token')
        || sessionStorage.getItem('pdv_automscale_token')
        || null
    );
}

function fetchUsuariosApi(url, options = {}) {
    const token = getTokenUsuarios();
    const headers = { ...(options.headers || {}) };
    if (token) headers['Authorization'] = 'Bearer ' + token;
    return fetch(url, { ...options, headers, credentials: 'include' });
}

class GerenciamentoUsuarios {
    constructor() {
        this.usuarios = [];
        this.paginaAtual = 1;
        this.limitePorPagina = 10;
        this.filtros = {
            nome: '',
            status: '',
            role: ''
        };
        this.usuarioEmEdicao = null;
        this.roles = [];
        this.listaClientes = [];
        
        this.inicializar();
    }

    inicializar() {
        if (!document.getElementById('tbodyUsuarios')) {
            this.configurarFeatherIcons();
            return;
        }
        this.configurarEventos();
        this.carregarUsuarios();
        this.carregarRepresentantes();
        this.carregarRoles();
        this.configurarFeatherIcons();
        const btnNovo = document.getElementById('btnNovoUsuario');
        if (btnNovo && !canCreate) btnNovo.remove();
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

        document.getElementById('filtroRole').addEventListener('change', (e) => {
            this.filtros.role = e.target.value;
            this.aplicarFiltros();
        });

        document.getElementById('role').addEventListener('change', (e) => {
            this.toggleSecaoClientesAdmin();
        });

        const cpfInput = document.getElementById('cpf');
        if (cpfInput) {
            cpfInput.addEventListener('input', (e) => {
                let v = e.target.value.replace(/\D/g, '');
                if (v.length > 11) v = v.slice(0, 11);
                if (v.length <= 3) e.target.value = v;
                else if (v.length <= 6) e.target.value = v.slice(0,3) + '.' + v.slice(3);
                else if (v.length <= 9) e.target.value = v.slice(0,3) + '.' + v.slice(3,6) + '.' + v.slice(6);
                else e.target.value = v.slice(0,3) + '.' + v.slice(3,6) + '.' + v.slice(6,9) + '-' + v.slice(9,11);
            });
        }

        document.getElementById('btnLimparFiltros').addEventListener('click', () => {
            this.limparFiltros();
        });

        // Formulário
        document.getElementById('formUsuario').addEventListener('submit', (e) => {
            e.preventDefault();
            this.salvarUsuario();
        });

        // Toggle senha
        document.getElementById('btnToggleSenha').addEventListener('click', () => {
            this.toggleVisibilidadeSenha();
        });
        
        // Limpar formulário ao fechar modal
        document.addEventListener('modalClosed', (e) => {
            if (e.detail.modalId === 'modalNovoUsuario') {
                this.limparFormulario();
            }
        });
        // Botão "Novo Representante": pré-selecionar função Administrador e exibir seção de clientes
        document.addEventListener('modalNovoAdministradorOpened', async () => {
            this.limparFormulario();
            if (!this.roles || this.roles.length === 0) {
                await this.carregarRoles();
            }
            const adminRole = this.roles.find(r => r.nome === 'Administrador');
            if (adminRole) {
                const selectRole = document.getElementById('role');
                if (selectRole) {
                    selectRole.value = String(adminRole.id);
                    this.toggleSecaoClientesAdmin();
                }
            }
            if (typeof feather !== 'undefined') feather.replace();
        });
    }

    async carregarUsuarios() {
        try {
            this.mostrarLoading();
            
            const params = new URLSearchParams({
                skip: (this.paginaAtual - 1) * this.limitePorPagina,
                limit: this.limitePorPagina
            });
            if (this.filtros.status !== '') params.append('ativo', this.filtros.status);
            if (this.filtros.nome) params.append('nome', this.filtros.nome);
            if (this.filtros.role) params.append('role_id', this.filtros.role);

            const response = await fetchUsuariosApi(`/api/v1/usuarios/?${params}`);
            
            if (!response.ok) {
                throw new Error(`Erro HTTP: ${response.status}`);
            }

            const data = await response.json();
            this.usuarios = data.usuarios;
            
            this.renderizarTabela();
            this.renderizarPaginacao(data.total);
            this.atualizarInfoPagina(data.total);
            
        } catch (error) {
            console.error('Erro ao carregar usuários:', error);
            this.mostrarErro('Erro ao carregar usuários. Tente novamente.');
        } finally {
            this.ocultarLoading();
        }
    }

    async carregarRoles() {
        try {
            const response = await fetch('/api/v1/auth/roles', { credentials: 'include' });
            if (response.ok) {
                this.roles = await response.json();
                this.preencherSelectRoles(this.roles);
                this.preencherFiltroRoles(this.roles);
            }
        } catch (error) {
            console.error('Erro ao carregar roles:', error);
        }
    }

    async carregarRepresentantes() {
        const tbody = document.getElementById('tbodyRepresentantes');
        const totalEl = document.getElementById('totalRepresentantes');
        if (!tbody) return;
        const colSpan = canEdit ? 4 : 3;
        try {
            const response = await fetchUsuariosApi('/api/v1/usuarios/representantes');
            if (!response.ok) {
                tbody.innerHTML = `<tr><td colspan="${colSpan}" class="text-center text-danger">Erro ao carregar representantes.</td></tr>`;
                if (totalEl) totalEl.textContent = '0';
                return;
            }
            const data = await response.json();
            const lista = data.representantes || [];
            if (totalEl) totalEl.textContent = lista.length;
            if (lista.length === 0) {
                tbody.innerHTML = `<tr><td colspan="${colSpan}" class="text-center text-muted">Nenhum representante cadastrado.</td></tr>`;
                return;
            }
            tbody.innerHTML = lista.map(u => {
                const statusBadge = u.ativo ? '<span class="badge bg-success">Ativo</span>' : '<span class="badge bg-secondary">Inativo</span>';
                const acaoBtn = canEdit ? `<td class="text-end"><button type="button" class="btn btn-sm btn-outline-primary btn-editar-representante" data-usuario-id="${u.id}" title="Editar">Editar</button></td>` : '';
                return `<tr>
                    <td>${u.nome || '-'}</td>
                    <td>${u.email || '-'}</td>
                    <td>${statusBadge}</td>
                    ${acaoBtn}
                </tr>`;
            }).join('');
            tbody.querySelectorAll('.btn-editar-representante').forEach(btn => {
                btn.addEventListener('click', () => {
                    const id = parseInt(btn.getAttribute('data-usuario-id'), 10);
                    if (id) this.editarUsuario(id);
                });
            });
            if (typeof feather !== 'undefined') feather.replace();
        } catch (error) {
            console.error('Erro ao carregar representantes:', error);
            tbody.innerHTML = `<tr><td colspan="${colSpan}" class="text-center text-danger">Erro ao carregar representantes.</td></tr>`;
            if (totalEl) totalEl.textContent = '0';
        }
    }

    preencherSelectRoles(roles) {
        const selectRole = document.getElementById('role');
        selectRole.innerHTML = '<option value="">Selecione uma função</option>';
        
        roles.forEach(role => {
            const option = document.createElement('option');
            option.value = role.id;
            option.textContent = role.nome;
            selectRole.appendChild(option);
        });
    }

    preencherFiltroRoles(roles) {
        const filtroRole = document.getElementById('filtroRole');
        filtroRole.innerHTML = '<option value="">Todas as funções</option>';
        
        roles.forEach(role => {
            const option = document.createElement('option');
            option.value = role.id;
            option.textContent = role.nome;
            filtroRole.appendChild(option);
        });
    }

    aplicarFiltros() {
        this.paginaAtual = 1;
        this.carregarUsuarios();
    }

    limparFiltros() {
        document.getElementById('filtroNome').value = '';
        document.getElementById('filtroStatus').value = '';
        document.getElementById('filtroRole').value = '';
        this.filtros = { nome: '', status: '', role: '' };
        this.aplicarFiltros();
    }

    renderizarTabela(usuarios = null) {
        const tbody = document.getElementById('tbodyUsuarios');
        if (!tbody) return;
        tbody.innerHTML = '';

        const usuariosParaRenderizar = usuarios || this.usuarios;
        const showActions = canEdit || canDelete;
        const colCount = showActions ? 7 : 6;

        if (usuariosParaRenderizar.length === 0) {
            const brandNome = document.body.getAttribute('data-brand-nome') || 'esta marca';
            const scopeLocked = document.body.getAttribute('data-brand-scope-locked') === 'true';
            const emptyMsg = scopeLocked
                ? `Nenhum usuário para ${brandNome}. Cadastros neste domínio aparecerão aqui.`
                : 'Nenhum usuário encontrado';
            tbody.innerHTML = `
                <tr>
                    <td colspan="${colCount}" class="text-center text-muted py-4">
                        <i class="align-middle me-2" data-feather="users"></i>
                        ${emptyMsg}
                    </td>
                </tr>
            `;
            this.configurarFeatherIcons();
            return;
        }

        usuariosParaRenderizar.forEach(usuario => {
            const actionsHtml = this.renderActions(usuario);
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${usuario.id}</td>
                <td>
                    <div class="d-flex align-items-center">
                        <div class="avatar avatar-sm me-2">
                            <span class="avatar-text">${usuario.nome.charAt(0).toUpperCase()}</span>
                        </div>
                        <div>
                            <div class="fw-bold">${usuario.nome}</div>
                        </div>
                    </div>
                </td>
                <td>${usuario.email}</td>
                <td>
                    ${this.renderizarRole(usuario.role)}
                </td>
                <td>
                    ${this.renderizarStatus(usuario.ativo)}
                </td>
                <td>
                    <small class="text-muted">
                        ${this.formatarData(usuario.created_at)}
                    </small>
                </td>
                ${showActions ? `<td>${actionsHtml}</td>` : ''}
            `;
            tbody.appendChild(tr);
        });

        this.configurarFeatherIcons();
    }

    renderActions(usuario) {
        if (!canEdit && !canDelete) return '';
        const nomeEsc = (usuario.nome || '').replace(/'/g, "\\'");
        let html = '<div class="btn-group btn-group-sm" role="group">';
        if (canEdit) {
            html += `<button type="button" class="btn btn-outline-primary" onclick="gerenciamentoUsuarios.editarUsuario(${usuario.id})" title="Editar usuário"><i class="align-middle" data-feather="edit-2"></i></button>`;
        }
        if (canDelete) {
            html += `<button type="button" class="btn btn-outline-danger" onclick="gerenciamentoUsuarios.confirmarExclusao(${usuario.id}, '${nomeEsc}')" title="Excluir usuário"><i class="align-middle" data-feather="trash-2"></i></button>`;
        }
        html += '</div>';
        return html;
    }

    renderizarStatus(ativo) {
        if (ativo) {
            return '<span class="badge bg-success">Ativo</span>';
        } else {
            return '<span class="badge bg-danger">Inativo</span>';
        }
    }

    renderizarRole(role) {
        if (!role) {
            return '<span class="text-muted">Sem função</span>';
        }
        
        const roleColors = {
            'Superadministrador': 'bg-dark',
            'Administrador': 'bg-danger',
            'Cliente Administrador': 'bg-warning text-dark',
            'Técnico': 'bg-primary',
            'Subcliente': 'bg-info',
            'Visualizador': 'bg-secondary',
            'Auditor': 'bg-warning'
        };
        
        const color = roleColors[role.nome] || 'bg-secondary';
        return `<span class="badge ${color}">${role.nome}</span>`;
    }

    renderizarPermissoes(role) {
        if (!role) {
            return '<span class="text-muted">-</span>';
        }
        
        // Mapear roles para permissões principais
        const permissoesPrincipais = {
            'Administrador': 'Todas as permissões',
            'Cliente Administrador': 'Cliente (Empresa Fiscal) — emite nota fiscal',
            'Técnico': 'Operações técnicas, certificados, clientes',
            'Subcliente': 'Cliente do Cliente — quem receberá a nota fiscal (gerenciado pelo Cliente Administrador)',
            'Visualizador': 'Apenas visualização',
            'Auditor': 'Visualização e auditoria'
        };
        
        const permissao = permissoesPrincipais[role.nome] || 'Permissões básicas';
        return `<small class="text-muted">${permissao}</small>`;
    }

    formatarData(dataString) {
        if (!dataString) return '-';
        const s = String(dataString).trim();
        const d = /^\d{4}-\d{2}-\d{2}$/.test(s) ? new Date(s + 'T12:00:00') : new Date(dataString);
        if (isNaN(d.getTime())) return '-';
        return d.toLocaleDateString('pt-BR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
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
                <a class="page-link" href="#" onclick="gerenciamentoUsuarios.irParaPagina(${this.paginaAtual - 1})">
                    <i class="align-middle" data-feather="chevron-left"></i>
                </a>
            </li>
        `;

        // Páginas numeradas
        for (let i = 1; i <= totalPaginas; i++) {
            if (i === 1 || i === totalPaginas || (i >= this.paginaAtual - 2 && i <= this.paginaAtual + 2)) {
                html += `
                    <li class="page-item ${i === this.paginaAtual ? 'active' : ''}">
                        <a class="page-link" href="#" onclick="gerenciamentoUsuarios.irParaPagina(${i})">${i}</a>
                    </li>
                `;
            } else if (i === this.paginaAtual - 3 || i === this.paginaAtual + 3) {
                html += '<li class="page-item disabled"><span class="page-link">...</span></li>';
            }
        }

        // Botão próximo
        html += `
            <li class="page-item ${this.paginaAtual === totalPaginas ? 'disabled' : ''}">
                <a class="page-link" href="#" onclick="gerenciamentoUsuarios.irParaPagina(${this.paginaAtual + 1})">
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
        this.carregarUsuarios();
    }

    atualizarInfoPagina(total) {
        const inicio = (this.paginaAtual - 1) * this.limitePorPagina + 1;
        const fim = Math.min(this.paginaAtual * this.limitePorPagina, total);
        
        document.getElementById('infoPagina').textContent = `${inicio}-${fim}`;
        document.getElementById('totalUsuarios').textContent = total;
    }

    async editarUsuario(id) {
        try {
            const response = await fetchUsuariosApi(`/api/v1/usuarios/${id}`);
            if (!response.ok) {
                throw new Error(`Erro HTTP: ${response.status}`);
            }

            const usuario = await response.json();
            this.usuarioEmEdicao = usuario;
            this.preencherFormulario(usuario);
            
            // Alterar título do modal
            document.getElementById('modalNovoUsuarioLabel').innerHTML = `
                <i class="align-middle me-2" data-feather="edit-2"></i>
                Editar Usuário
            `;
            
            // Alterar texto do botão
            const btnSalvar = document.getElementById('btnSalvarUsuario');
            btnSalvar.innerHTML = '<i class="align-middle me-1" data-feather="save"></i> Atualizar Usuário';
            
            // Mostrar modal customizado
            if (typeof modalNovoUsuario !== 'undefined') {
                modalNovoUsuario.open();
            }
            
        } catch (error) {
            console.error('Erro ao carregar usuário:', error);
            this.mostrarErro('Erro ao carregar dados do usuário.');
        }
    }

    preencherFormulario(usuario) {
        document.getElementById('usuarioId').value = usuario.id;
        document.getElementById('nome').value = usuario.nome || '';
        document.getElementById('email').value = usuario.email || '';
        document.getElementById('role').value = usuario.role_id || '';
        document.getElementById('ativo').checked = usuario.ativo;
        const cpfEl = document.getElementById('cpf');
        const rgEl = document.getElementById('rg');
        const docEl = document.getElementById('documentoPath');
        const cpfVal = (usuario && (usuario.cpf != null && usuario.cpf !== undefined)) ? String(usuario.cpf).trim() : '';
        const rgVal = (usuario && (usuario.rg != null && usuario.rg !== undefined)) ? String(usuario.rg).trim() : '';
        const docVal = (usuario && (usuario.documento_path != null && usuario.documento_path !== undefined)) ? String(usuario.documento_path).trim() : '';
        if (cpfEl) cpfEl.value = cpfVal;
        if (rgEl) rgEl.value = rgVal;
        if (docEl) docEl.value = docVal;
        
        // Para edição, senha não é obrigatória
        document.getElementById('senha').required = false;
        document.getElementById('confirmarSenha').required = false;
        
        // Adicionar indicador visual
        document.getElementById('senha').placeholder = 'Deixe em branco para manter a senha atual';
        document.getElementById('confirmarSenha').placeholder = 'Deixe em branco para manter a senha atual';
        
        // Função RBAC sempre obrigatória
        document.getElementById('role').required = true;

        this.toggleSecaoClientesAdmin();
        if (usuario.role && usuario.role.nome === 'Administrador' && usuario.id) {
            this.carregarClientesVinculados(usuario.id);
        }
    }

    toggleSecaoClientesAdmin() {
        const roleSelect = document.getElementById('role');
        const secao = document.getElementById('secaoClientesAdmin');
        const option = roleSelect.options[roleSelect.selectedIndex];
        const roleNome = option ? option.text.trim() : '';
        if (roleNome === 'Administrador') {
            secao.style.display = 'flex';
            this.carregarListaClientesParaSelect();
        } else {
            secao.style.display = 'none';
        }
    }

    async carregarListaClientesParaSelect() {
        const sel = document.getElementById('clientesVinculados');
        if (!sel || this.listaClientes.length > 0) {
            if (sel && this.listaClientes.length > 0) {
                sel.innerHTML = this.listaClientes.map(c => `<option value="${c.id}">${c.nome} (${c.cnpj || ''})</option>`).join('');
            }
            return;
        }
        try {
            const token = getTokenUsuarios();
            const headers = { 'Content-Type': 'application/json' };
            if (token) headers['Authorization'] = 'Bearer ' + token;
            const response = await fetch('/api/v1/clientes/todos', { headers });
            if (!response.ok) return;
            this.listaClientes = await response.json();
            sel.innerHTML = this.listaClientes.map(c => `<option value="${c.id}">${c.nome} (${c.cnpj || ''})</option>`).join('');
        } catch (e) {
            console.error('Erro ao carregar clientes', e);
            sel.innerHTML = '<option value="">Erro ao carregar</option>';
        }
    }

    async carregarClientesVinculados(usuarioId) {
        await this.carregarListaClientesParaSelect();
        const sel = document.getElementById('clientesVinculados');
        if (!sel) return;
        try {
            const response = await fetchUsuariosApi(`/api/v1/usuarios/${usuarioId}/clientes-vinculados`);
            if (!response.ok) return;
            const data = await response.json();
            const ids = (data.cliente_ids || []).map(String);
            for (let i = 0; i < sel.options.length; i++) {
                sel.options[i].selected = ids.indexOf(sel.options[i].value) !== -1;
            }
        } catch (e) {
            console.error('Erro ao carregar clientes vinculados', e);
        }
    }

    limparFormulario() {
        document.getElementById('formUsuario').reset();
        document.getElementById('usuarioId').value = '';
        this.usuarioEmEdicao = null;
        document.getElementById('secaoClientesAdmin').style.display = 'none';
        
        // Restaurar título e botão
        document.getElementById('modalNovoUsuarioLabel').innerHTML = `
            <i class="align-middle me-2" data-feather="user-plus"></i>
            Novo Usuário
        `;
        
        const btnSalvar = document.getElementById('btnSalvarUsuario');
        if (btnSalvar) {
            btnSalvar.innerHTML = '<i class="align-middle me-1" data-feather="save"></i> Salvar Usuário';
        }
        
        // Restaurar obrigatoriedade da senha
        document.getElementById('senha').required = true;
        document.getElementById('confirmarSenha').required = true;
        document.getElementById('senha').placeholder = '';
        document.getElementById('confirmarSenha').placeholder = '';
        
        // Restaurar obrigatoriedade da função RBAC
        document.getElementById('role').required = true;
    }

    async salvarUsuario() {
        if (!this.validarFormulario()) {
            return;
        }

        try {
            // Coletar dados do formulário manualmente
            const roleId = parseInt(document.getElementById('role').value);
            const roleSelect = document.getElementById('role');
            const roleNome = roleSelect.options[roleSelect.selectedIndex].text;
            
            const cpfRaw = document.getElementById('cpf') ? document.getElementById('cpf').value.trim() : '';
            const rgRaw = document.getElementById('rg') ? document.getElementById('rg').value.trim() : '';
            const docRaw = document.getElementById('documentoPath') ? document.getElementById('documentoPath').value.trim() : '';
            const dados = {
                nome: document.getElementById('nome').value.trim(),
                email: document.getElementById('email').value.trim(),
                cargo: roleNome, // Usar nome da role como cargo temporariamente
                role_id: roleId,
                ativo: document.getElementById('ativo').checked
            };
            dados.cpf = cpfRaw || null;
            dados.rg = rgRaw || null;
            dados.documento_path = docRaw || null;
            
            // Adicionar senha apenas se preenchida
            const senha = document.getElementById('senha').value;
            if (senha) {
                dados.senha = senha;
            }
            
            // Validar role_id
            if (!dados.role_id || isNaN(dados.role_id)) {
                this.mostrarErro('Selecione uma função RBAC válida');
                return;
            }

            const url = this.usuarioEmEdicao 
                ? `/api/v1/usuarios/${this.usuarioEmEdicao.id}`
                : '/api/v1/usuarios/';
            
            const method = this.usuarioEmEdicao ? 'PUT' : 'POST';

            console.log('Enviando dados:', dados);

            const response = await fetchUsuariosApi(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(dados)
            });

            if (!response.ok) {
                const errorData = await response.json();
                console.error('Erro do servidor:', errorData);
                throw new Error(errorData.detail || 'Erro ao salvar usuário');
            }

            let savedUserId = this.usuarioEmEdicao ? this.usuarioEmEdicao.id : null;
            if (!savedUserId) {
                const savedUser = await response.json();
                savedUserId = savedUser && savedUser.id ? savedUser.id : null;
            }
            if (roleNome === 'Administrador' && savedUserId) {
                const sel = document.getElementById('clientesVinculados');
                const clienteIds = sel ? Array.from(sel.selectedOptions).map(o => parseInt(o.value, 10)).filter(id => !isNaN(id)) : [];
                await fetchUsuariosApi(`/api/v1/usuarios/${savedUserId}/clientes-vinculados`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ cliente_ids: clienteIds })
                });
            }

            this.mostrarSucesso(
                this.usuarioEmEdicao 
                    ? 'Usuário atualizado com sucesso!' 
                    : 'Usuário criado com sucesso!'
            );

            // Fechar modal customizado e recarregar dados
            if (typeof modalNovoUsuario !== 'undefined') {
                modalNovoUsuario.close();
            }
            
            this.carregarUsuarios();
            this.carregarRepresentantes();
            
        } catch (error) {
            console.error('Erro ao salvar usuário:', error);
            this.mostrarErro(error.message || 'Erro ao salvar usuário. Tente novamente.');
        }
    }

    validarFormulario() {
        const form = document.getElementById('formUsuario');
        const senha = document.getElementById('senha').value;
        const confirmarSenha = document.getElementById('confirmarSenha').value;
        const role = document.getElementById('role').value;
        
        // Validação básica do HTML5
        if (!form.checkValidity()) {
            form.classList.add('was-validated');
            return false;
        }
        
        // Validação de função RBAC
        if (!role) {
            this.mostrarErro('Função RBAC é obrigatória.');
            return false;
        }
        
        // Validação de senha
        if (this.usuarioEmEdicao) {
            // Para edição, senha é opcional
            if (senha && senha !== confirmarSenha) {
                this.mostrarErro('As senhas não coincidem.');
                return false;
            }
        } else {
            // Para criação, senha é obrigatória
            if (senha !== confirmarSenha) {
                this.mostrarErro('As senhas não coincidem.');
                return false;
            }
        }
        
        return true;
    }

    confirmarExclusao(id, nome) {
        document.getElementById('nomeUsuarioExclusao').textContent = nome;
        
        // Abrir modal customizado
        if (typeof modalConfirmacao !== 'undefined') {
            modalConfirmacao.open();
        }
        
        // Configurar botão de confirmação
        document.getElementById('btnConfirmarExclusao').onclick = () => {
            this.excluirUsuario(id);
        };
    }

    async excluirUsuario(id) {
        try {
            const response = await window.authenticatedFetch(`/api/v1/usuarios/${id}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                let detalhe = '';
                try {
                    const errorData = await response.json();
                    detalhe = errorData && errorData.detail ? String(errorData.detail) : '';
                } catch (_) {}
                throw new Error(detalhe || `Erro HTTP: ${response.status}`);
            }

            this.mostrarSucesso('Usuário excluído com sucesso!');
            
            // Fechar modal customizado e recarregar dados
            if (typeof modalConfirmacao !== 'undefined') {
                modalConfirmacao.close();
            }
            
            this.carregarUsuarios();
            this.carregarRepresentantes();
            
        } catch (error) {
            console.error('Erro ao excluir usuário:', error);
            this.mostrarErro(error.message || 'Erro ao excluir usuário. Tente novamente.');
        }
    }

    toggleVisibilidadeSenha() {
        const senha = document.getElementById('senha');
        const btnToggle = document.getElementById('btnToggleSenha');
        const icon = btnToggle.querySelector('i');
        
        if (senha.type === 'password') {
            senha.type = 'text';
            icon.setAttribute('data-feather', 'eye-off');
        } else {
            senha.type = 'password';
            icon.setAttribute('data-feather', 'eye');
        }
        
        feather.replace();
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

    configurarFeatherIcons() {
        if (typeof feather !== 'undefined') {
            feather.replace();
        }
    }
}

// Inicializar quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', () => {
    window.gerenciamentoUsuarios = new GerenciamentoUsuarios();
});
