// PDV Ibix - Clientes JavaScript
class ClientesManager {
    constructor() {
        this.currentPage = 1;
        this.itemsPerPage = 10;
        this.currentFilters = {};
        this.clienteEmEdicao = null;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.setupMasks();
        this.carregarClientes();
        this.carregarPdvClientePadrao();
    }
    
    setupEventListeners() {
        // Verificar se elementos existem
        const formCliente = document.getElementById('formCliente');
        const btnConfirmarExclusao = document.getElementById('btnConfirmarExclusao');
        const modalCliente = document.getElementById('modalCliente');
        
        // Form de cliente
        if (formCliente) {
            formCliente.addEventListener('submit', (e) => {
                e.preventDefault();
                this.salvarCliente();
            });
            this.configurarValidacaoVisualFormulario();
        }
        
        // Modal de confirmação
        if (btnConfirmarExclusao) {
            btnConfirmarExclusao.addEventListener('click', () => {
            this.confirmarExclusao();
        });
        }
        
        // Filtros com debounce
        let timeoutId;
        ['filtroNome', 'filtroCNPJ', 'filtroCidade'].forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.addEventListener('input', () => {
                clearTimeout(timeoutId);
                timeoutId = setTimeout(() => this.aplicarFiltros(), 500);
            });
            }
        });
        
        const filtroUF = document.getElementById('filtroUF');
        if (filtroUF) {
            filtroUF.addEventListener('change', () => {
            this.aplicarFiltros();
        });
        }

        const filtroTipoCliente = document.getElementById('filtroTipoCliente');
        if (filtroTipoCliente) {
            filtroTipoCliente.addEventListener('change', () => this.aplicarFiltros());
        }

        const btnSalvarPdvClientePadrao = document.getElementById('btnSalvarPdvClientePadrao');
        if (btnSalvarPdvClientePadrao) {
            btnSalvarPdvClientePadrao.addEventListener('click', () => this.salvarPdvClientePadrao());
        }
        
        // Modal de cliente é overlay custom (display block/none); limpeza ao fechar em fecharModalCliente() no template
    }
    
    setupMasks() {
        // Máscara para CNPJ
        const cnpjInput = document.getElementById('cnpj');
        if (cnpjInput) {
            cnpjInput.addEventListener('input', (e) => {
                let value = e.target.value.replace(/\D/g, '');
                if (value.length <= 14) {
                    value = value.replace(/^(\d{2})(\d)/, '$1.$2');
                    value = value.replace(/^(\d{2})\.(\d{3})(\d)/, '$1.$2.$3');
                    value = value.replace(/\.(\d{3})(\d)/, '.$1/$2');
                    value = value.replace(/(\d{4})(\d)/, '$1-$2');
                    e.target.value = value;
                }
            });
        }
        // Máscara para CPF
        const cpfInput = document.getElementById('cpf');
        if (cpfInput) {
            cpfInput.addEventListener('input', (e) => {
                let value = e.target.value.replace(/\D/g, '');
                if (value.length <= 11) {
                    value = value.replace(/^(\d{3})(\d)/, '$1.$2');
                    value = value.replace(/^(\d{3})\.(\d{3})(\d)/, '$1.$2.$3');
                    value = value.replace(/\.(\d{3})(\d)/, '.$1-$2');
                    e.target.value = value;
                }
            });
        }
        // Abas PJ / PF (também expostas em window para onclick no template)
        const tabPJ = document.getElementById('tabPJ');
        const tabPF = document.getElementById('tabPF');
        const blocoCnpj = document.getElementById('blocoCnpj');
        const blocoCpf = document.getElementById('blocoCpf');
        const switchToPJ = () => {
            if (!tabPJ || !tabPF || !blocoCnpj || !blocoCpf) return;
            tabPJ.setAttribute('aria-selected', 'true');
            tabPF.setAttribute('aria-selected', 'false');
            tabPJ.style.borderBottomColor = '#0d6efd';
            tabPJ.style.fontWeight = '600';
            tabPJ.style.color = '#0d6efd';
            tabPF.style.borderBottomColor = 'transparent';
            tabPF.style.color = '#6c757d';
            tabPF.style.fontWeight = 'normal';
            blocoCnpj.style.display = 'block';
            blocoCpf.style.display = 'none';
            const cpfEl = document.getElementById('cpf');
            const cnpjEl = document.getElementById('cnpj');
            if (cpfEl) { cpfEl.value = ''; cpfEl.removeAttribute('required'); }
            if (cnpjEl) { cnpjEl.setAttribute('required', 'required'); }
        };
        const switchToPF = () => {
            if (!tabPJ || !tabPF || !blocoCnpj || !blocoCpf) return;
            tabPF.setAttribute('aria-selected', 'true');
            tabPJ.setAttribute('aria-selected', 'false');
            tabPF.style.borderBottomColor = '#0d6efd';
            tabPF.style.fontWeight = '600';
            tabPF.style.color = '#0d6efd';
            tabPJ.style.borderBottomColor = 'transparent';
            tabPJ.style.color = '#6c757d';
            tabPJ.style.fontWeight = 'normal';
            blocoCpf.style.display = 'block';
            blocoCnpj.style.display = 'none';
            const cnpjEl = document.getElementById('cnpj');
            const cpfEl = document.getElementById('cpf');
            if (cnpjEl) { cnpjEl.value = ''; cnpjEl.removeAttribute('required'); }
            if (cpfEl) { cpfEl.setAttribute('required', 'required'); }
        };
        if (tabPJ && tabPF && blocoCnpj && blocoCpf) {
            tabPJ.addEventListener('click', switchToPJ);
            tabPF.addEventListener('click', switchToPF);
            window.tabClientePJ = switchToPJ;
            window.tabClientePF = switchToPF;
        }
        
        // Máscara para telefone
        const telefoneInput = document.getElementById('telefone');
        if (telefoneInput) {
        telefoneInput.addEventListener('input', (e) => {
            let value = e.target.value.replace(/\D/g, '');
            if (value.length <= 11) {
                if (value.length === 11) {
                    value = value.replace(/^(\d{2})(\d{5})(\d{4})/, '($1) $2-$3');
                } else if (value.length === 10) {
                    value = value.replace(/^(\d{2})(\d{4})(\d{4})/, '($1) $2-$3');
                }
                e.target.value = value;
            }
        });
        }
        
        // Máscara para CEP
        const cepInput = document.getElementById('cep');
        if (cepInput) {
        cepInput.addEventListener('input', (e) => {
            let value = e.target.value.replace(/\D/g, '');
            if (value.length <= 8) {
                value = value.replace(/^(\d{5})(\d)/, '$1-$2');
                e.target.value = value;
            }
        });
        
        // Busca CEP
        cepInput.addEventListener('blur', () => {
            this.buscarCep(cepInput.value);
        });
        }
    }
    
    async buscarCep(cep) {
        const cepLimpo = cep.replace(/\D/g, '');
        if (cepLimpo.length !== 8) return;
        
        try {
            // ViaCEP não aceita credenciais/cookies de origem externa; usar omit evita erro de CORS
            const response = await fetch(`https://viacep.com.br/ws/${cepLimpo}/json/`, {
                credentials: 'omit'
            });
            if (!response.ok) {
                throw new Error(`Falha ao consultar CEP (${response.status})`);
            }
            const data = await response.json();
            
            if (!data.erro) {
                document.getElementById('endereco').value = data.logradouro;
                document.getElementById('cidade').value = data.localidade;
                document.getElementById('uf').value = data.uf;
            } else {
                this.mostrarAlerta('CEP não encontrado. Confira o número informado.', 'warning');
            }
        } catch (error) {
            this.mostrarAlerta('Não foi possível consultar o CEP agora. Você pode preencher endereço/cidade/UF manualmente.', 'warning');
        }
    }
    
    async carregarClientes() {
        try {
            const params = new URLSearchParams({
                pagina: this.currentPage,
                por_pagina: this.itemsPerPage,
                ...this.currentFilters
            });
            
            const token = this.getToken();
            
            const headers = { 'Content-Type': 'application/json' };
            if (token) headers['Authorization'] = `Bearer ${token}`;
            
            const response = await fetch(`/api/v1/clientes/?${params}`, {
                headers,
                credentials: 'include'
            });
            
            if (!response.ok) {
                await response.text();
                throw new Error('Erro ao carregar clientes');
            }
            
            const data = await response.json();
            
            this.renderizarTabela(data.clientes);
            this.renderizarPaginacao(data);
            this.atualizarInfoPagina(data);
            
        } catch (error) {
            this.mostrarAlerta('Erro ao carregar clientes', 'danger');
        }
    }
    
    renderizarTabela(clientes) {
        const tbody = document.getElementById('tabelaClientes');
        
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        if (clientes.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="text-center text-muted">
                        Nenhum cliente encontrado
                    </td>
                </tr>
            `;
            return;
        }
        
        clientes.forEach(cliente => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${cliente.id}</td>
                <td>${cliente.nome}</td>
                <td>${cliente.cnpj || cliente.cpf || ''}</td>
                <td>${cliente.cidade}/${cliente.uf}</td>
                <td>${cliente.contato}</td>
                <td>${cliente.telefone}</td>
                <td>${cliente.email}</td>
                <td>
                    <div class="btn-group" role="group">
                        <button type="button" class="btn btn-sm btn-outline-success" 
                                onclick="abrirModalUsuarioCliente(${cliente.id}, '${cliente.nome.replace(/'/g, "\\'")}')"
                                title="Criar Usuário">
                            <i class="align-middle" data-feather="user-plus"></i>
                        </button>
                        <button type="button" class="btn btn-sm btn-outline-primary" 
                                onclick="clientesManager.editarCliente(${cliente.id})">
                            <i class="align-middle" data-feather="edit-2"></i>
                        </button>
                        <button type="button" class="btn btn-sm btn-outline-danger" 
                                onclick="clientesManager.excluirCliente(${cliente.id})">
                            <i class="align-middle" data-feather="trash-2"></i>
                        </button>
                    </div>
                </td>
            `;
            tbody.appendChild(row);
        });
        
        // Reinicializar ícones Feather
        if (window.feather) {
            feather.replace();
        }
    }
    
    renderizarPaginacao(data) {
        const paginacao = document.getElementById('paginacao');
        paginacao.innerHTML = '';
        
        if (data.total_paginas <= 1) return;
        
        // Botão anterior
        const prevLi = document.createElement('li');
        prevLi.className = `page-item ${data.pagina === 1 ? 'disabled' : ''}`;
        prevLi.innerHTML = `
            <button type="button" class="page-link" onclick="clientesManager.irParaPagina(${data.pagina - 1})" ${data.pagina === 1 ? 'disabled' : ''}>
                <i class="align-middle" data-feather="chevron-left"></i>
                Anterior
            </button>
        `;
        paginacao.appendChild(prevLi);
        
        // Páginas
        const inicio = Math.max(1, data.pagina - 2);
        const fim = Math.min(data.total_paginas, data.pagina + 2);
        
        // Adicionar primeira página se não estiver no range
        if (inicio > 1) {
            const firstLi = document.createElement('li');
            firstLi.className = 'page-item';
            firstLi.innerHTML = `
                <button type="button" class="page-link" onclick="clientesManager.irParaPagina(1)">
                    1
                </button>
            `;
            paginacao.appendChild(firstLi);
            
            // Adicionar ellipsis se necessário
            if (inicio > 2) {
                const ellipsisLi = document.createElement('li');
                ellipsisLi.className = 'page-item disabled';
                ellipsisLi.innerHTML = `
                    <span class="page-link">...</span>
                `;
                paginacao.appendChild(ellipsisLi);
            }
        }
        
        for (let i = inicio; i <= fim; i++) {
            const li = document.createElement('li');
            li.className = `page-item ${i === data.pagina ? 'active' : ''}`;
            li.innerHTML = `
                <button type="button" class="page-link" onclick="clientesManager.irParaPagina(${i})">
                    ${i}
                </button>
            `;
            paginacao.appendChild(li);
        }
        
        // Adicionar última página se não estiver no range
        if (fim < data.total_paginas) {
            // Adicionar ellipsis se necessário
            if (fim < data.total_paginas - 1) {
                const ellipsisLi = document.createElement('li');
                ellipsisLi.className = 'page-item disabled';
                ellipsisLi.innerHTML = `
                    <span class="page-link">...</span>
                `;
                paginacao.appendChild(ellipsisLi);
            }
            
            const lastLi = document.createElement('li');
            lastLi.className = 'page-item';
            lastLi.innerHTML = `
                <button type="button" class="page-link" onclick="clientesManager.irParaPagina(${data.total_paginas})">
                    ${data.total_paginas}
                </button>
            `;
            paginacao.appendChild(lastLi);
        }
        
        // Botão próximo
        const nextLi = document.createElement('li');
        nextLi.className = `page-item ${data.pagina === data.total_paginas ? 'disabled' : ''}`;
        nextLi.innerHTML = `
            <button type="button" class="page-link" onclick="clientesManager.irParaPagina(${data.pagina + 1})" ${data.pagina === data.total_paginas ? 'disabled' : ''}>
                Próximo
                <i class="align-middle" data-feather="chevron-right"></i>
            </button>
        `;
        paginacao.appendChild(nextLi);
        
        // Reinicializar ícones Feather
        if (window.feather) {
            feather.replace();
        }
    }
    
    atualizarInfoPagina(data) {
        const info = document.getElementById('infoPagina');
        const inicio = (data.pagina - 1) * data.por_pagina + 1;
        const fim = Math.min(data.pagina * data.por_pagina, data.total);
        
        info.textContent = `Mostrando ${inicio} a ${fim} de ${data.total} clientes`;
    }
    
    irParaPagina(pagina) {
        if (pagina < 1) return;
        
        this.currentPage = pagina;
        this.carregarClientes();
    }
    
    aplicarFiltros() {
        this.currentFilters = {};
        
        const nome = document.getElementById('filtroNome').value.trim();
        const cnpj = document.getElementById('filtroCNPJ').value.trim();
        const cidade = document.getElementById('filtroCidade').value.trim();
        const uf = document.getElementById('filtroUF').value;
        const filtroTipo = document.getElementById('filtroTipoCliente');
        const empresaFiscal = filtroTipo ? filtroTipo.value : '';
        
        if (nome) this.currentFilters.nome = nome;
        if (cnpj) this.currentFilters.cnpj = cnpj;
        if (cidade) this.currentFilters.cidade = cidade;
        if (uf) this.currentFilters.uf = uf;
        if (empresaFiscal === 'true' || empresaFiscal === 'false') this.currentFilters.empresa_fiscal = empresaFiscal;
        
        this.currentPage = 1;
        this.carregarClientes();
    }

    configurarValidacaoVisualFormulario() {
        const campos = ['nome', 'cnpj', 'cpf', 'cep', 'endereco', 'cidade', 'uf', 'contato', 'telefone', 'email'];
        campos.forEach((id) => {
            const input = document.getElementById(id);
            if (!input || input.dataset.validationBound === 'true') return;
            const limparVisual = () => {
                input.classList.remove('is-invalid');
                input.style.borderColor = '';
                input.style.boxShadow = '';
            };
            input.addEventListener('input', limparVisual);
            input.addEventListener('change', limparVisual);
            input.dataset.validationBound = 'true';
        });
    }

    limparCamposInvalidos() {
        const campos = ['nome', 'cnpj', 'cpf', 'cep', 'endereco', 'cidade', 'uf', 'contato', 'telefone', 'email'];
        campos.forEach((id) => {
            const input = document.getElementById(id);
            if (!input) return;
            input.classList.remove('is-invalid');
            input.style.borderColor = '';
            input.style.boxShadow = '';
        });
    }

    marcarCamposInvalidos(campos = []) {
        this.limparCamposInvalidos();
        campos.forEach((id) => {
            const input = document.getElementById(id);
            if (!input) return;
            input.classList.add('is-invalid');
            input.style.borderColor = '#dc3545';
            input.style.boxShadow = '0 0 0 0.2rem rgba(220, 53, 69, 0.15)';
        });
    }
    
    getTabAtivo() {
        const blocoCpf = document.getElementById('blocoCpf');
        return blocoCpf && blocoCpf.style.display !== 'none' ? 'pf' : 'pj';
    }

    validarCpfDigitos(cpf) {
        if (!cpf || cpf.length !== 11) return false;
        if (/^(\d)\1+$/.test(cpf)) return false;
        const calc = (base) => {
            const pesos = base.length === 9 ? [10,9,8,7,6,5,4,3,2] : [11,10,9,8,7,6,5,4,3,2];
            const soma = base.split('').reduce((acc, d, i) => acc + parseInt(d,10) * pesos[i], 0);
            const r = soma % 11;
            return r < 2 ? 0 : 11 - r;
        };
        return Number(cpf[9]) === calc(cpf.slice(0,9)) && Number(cpf[10]) === calc(cpf.slice(0,10));
    }

    async salvarCliente() {
        try {
            this.limparCamposInvalidos();
            const formData = new FormData(document.getElementById('formCliente'));
            const cepValue = formData.get('cep');
            const cnpjValue = formData.get('cnpj');
            const cpfValue = formData.get('cpf');
            const telefoneValue = formData.get('telefone');
            const emailValue = formData.get('email');

            const somenteDigitos = (valor) => (valor || '').toString().replace(/\D/g, '');
            const emailValido = (valor) => /.+@.+\..+/.test(valor || '');
            const validarCnpjDigitos = (cnpj) => {
                if (!cnpj || cnpj.length !== 14) return false;
                if (/^(\d)\1+$/.test(cnpj)) return false;
                const calcularDigito = (base, pesos) => {
                    const soma = base.split('').reduce((acc, digito, idx) => acc + (parseInt(digito, 10) * pesos[idx]), 0);
                    const resto = soma % 11;
                    return resto < 2 ? 0 : 11 - resto;
                };
                const digito1 = calcularDigito(cnpj.slice(0, 12), [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]);
                const digito2 = calcularDigito(cnpj.slice(0, 12) + String(digito1), [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]);
                return Number(cnpj[12]) === digito1 && Number(cnpj[13]) === digito2;
            };
            const erroValidacao = (mensagem, campos = []) => {
                this.marcarCamposInvalidos(campos);
                throw new Error(mensagem);
            };

            const tabAtivo = this.getTabAtivo();
            const cnpjLimpo = somenteDigitos(cnpjValue);
            const cpfLimpo = somenteDigitos(cpfValue);
            const cepLimpo = somenteDigitos(cepValue);
            const telefoneLimpo = somenteDigitos(telefoneValue);
            const nome = (formData.get('nome') || '').toString().trim();
            const endereco = (formData.get('endereco') || '').toString().trim();
            const cidade = (formData.get('cidade') || '').toString().trim();
            const uf = (formData.get('uf') || '').toString().trim();
            const contato = (formData.get('contato') || '').toString().trim();
            const email = (emailValue || '').toString().trim();

            if (!nome) erroValidacao('Preencha o campo Nome/Razão Social', ['nome']);
            if (!endereco) erroValidacao('Preencha o campo Endereço', ['endereco']);
            if (!cidade) erroValidacao('Preencha o campo Cidade', ['cidade']);
            if (!uf) erroValidacao('Selecione uma UF válida', ['uf']);
            if (!contato) erroValidacao('Preencha o campo Contato', ['contato']);

            if (tabAtivo === 'pj') {
                if (!cnpjLimpo || cnpjLimpo.length !== 14) erroValidacao('CNPJ deve ter 14 dígitos', ['cnpj']);
                if (!validarCnpjDigitos(cnpjLimpo)) erroValidacao('CNPJ inválido (dígitos verificadores incorretos)', ['cnpj']);
            } else {
                if (!cpfLimpo || cpfLimpo.length !== 11) erroValidacao('CPF deve ter 11 dígitos', ['cpf']);
                if (!this.validarCpfDigitos(cpfLimpo)) erroValidacao('CPF inválido (dígitos verificadores incorretos)', ['cpf']);
            }
            if (cepLimpo && cepLimpo.length !== 8) erroValidacao('CEP deve ter 8 dígitos', ['cep']);
            if (!telefoneLimpo || (telefoneLimpo.length !== 10 && telefoneLimpo.length !== 11)) {
                erroValidacao('Telefone deve ter 10 ou 11 dígitos', ['telefone']);
            }
            if (!emailValido(emailValue)) erroValidacao('Email inválido', ['email']);

            const clienteData = {
                nome,
                cep: cepLimpo || null,
                endereco,
                cidade,
                uf,
                contato,
                telefone: telefoneLimpo,
                email
            };
            if (tabAtivo === 'pj') {
                clienteData.cnpj = cnpjLimpo;
                clienteData.cpf = null;
            } else {
                clienteData.cnpj = null;
                clienteData.cpf = cpfLimpo;
            }
            
            const token = this.getToken();
            const url = this.clienteEmEdicao 
                ? `/api/v1/clientes/${this.clienteEmEdicao}`
                : '/api/v1/clientes/';
            
            const method = this.clienteEmEdicao ? 'PUT' : 'POST';
            
            const headers = { 'Content-Type': 'application/json' };
            if (token) headers['Authorization'] = `Bearer ${token}`;
            const response = await fetch(url, {
                method: method,
                headers,
                body: JSON.stringify(clienteData),
                credentials: 'include'
            });
            
            if (!response.ok) {
                const error = await response.json();
                // Tratar erros de validação
                if (error.detail && Array.isArray(error.detail)) {
                    const camposComErro = [];
                    const errorMessages = error.detail.map(err => {
                        const campo = Array.isArray(err.loc) ? err.loc[err.loc.length - 1] : '';
                        if (campo && rotuloCampo[campo]) camposComErro.push(campo);
                        const nomeCampo = rotuloCampo[campo] || campo || 'campo';
                        return `${nomeCampo}: ${err.msg}`;
                    }).join(' | ');
                    if (camposComErro.length) this.marcarCamposInvalidos(camposComErro);
                    throw new Error(`Erro de validação: ${errorMessages}`);
                } else if (error.detail) {
                    throw new Error(error.detail);
                } else {
                    throw new Error('Erro ao salvar cliente');
                }
            }
            
            await response.json();
            
            this.mostrarAlerta(
                this.clienteEmEdicao ? 'Cliente atualizado com sucesso!' : 'Cliente criado com sucesso!',
                'success'
            );
            
            const elModal = document.getElementById('modalCliente');
            if (elModal) elModal.style.display = 'none';
            this.carregarClientes();
            
        } catch (error) {
            this.mostrarAlerta(error.message, 'danger');
        }
    }
    
    async editarCliente(id) {
        try {
            const token = this.getToken();
            const headers = {};
            if (token) headers['Authorization'] = `Bearer ${token}`;
            const response = await fetch(`/api/v1/clientes/${id}`, {
                headers,
                credentials: 'include'
            });
            
            if (!response.ok) {
                throw new Error('Erro ao carregar cliente');
            }
            
            const cliente = await response.json();
            this.preencherFormulario(cliente);
            this.clienteEmEdicao = id;
            
            const modalLabel = document.getElementById('modalClienteLabel');
            if (modalLabel) modalLabel.textContent = 'Editar Cliente';

            const elModal = document.getElementById('modalCliente');
            if (elModal) elModal.style.display = 'block';
            
        } catch (error) {
            this.mostrarAlerta('Erro ao carregar cliente', 'danger');
        }
    }
    
    preencherFormulario(cliente) {
        this.limparCamposInvalidos();
        document.getElementById('nome').value = cliente.nome || '';
        document.getElementById('cep').value = cliente.cep || '';
        document.getElementById('endereco').value = cliente.endereco || '';
        document.getElementById('cidade').value = cliente.cidade || '';
        document.getElementById('uf').value = cliente.uf || '';
        document.getElementById('contato').value = cliente.contato || '';
        document.getElementById('telefone').value = cliente.telefone || '';
        document.getElementById('email').value = cliente.email || '';
        const tabPJ = document.getElementById('tabPJ');
        const tabPF = document.getElementById('tabPF');
        const blocoCnpj = document.getElementById('blocoCnpj');
        const blocoCpf = document.getElementById('blocoCpf');
        if (cliente.cnpj) {
            document.getElementById('cnpj').value = cliente.cnpj;
            document.getElementById('cpf').value = '';
            if (tabPJ && tabPF && blocoCnpj && blocoCpf) {
                tabPJ.click();
            }
        } else {
            document.getElementById('cpf').value = cliente.cpf || '';
            document.getElementById('cnpj').value = '';
            if (tabPF && tabPJ && blocoCpf && blocoCnpj) {
                tabPF.click();
            }
        }
    }

    limparFormulario() {
        document.getElementById('formCliente').reset();
        this.limparCamposInvalidos();
        this.clienteEmEdicao = null;
        const modalLabel = document.getElementById('modalClienteLabel');
        if (modalLabel) modalLabel.textContent = 'Novo Cliente';
        const tabPJ = document.getElementById('tabPJ');
        const blocoCnpj = document.getElementById('blocoCnpj');
        const blocoCpf = document.getElementById('blocoCpf');
        if (tabPJ && blocoCnpj && blocoCpf) {
            tabPJ.click();
        }
    }
    
    excluirCliente(id) {
        this.clienteEmEdicao = id;
        const el = document.getElementById('modalConfirmacao');
        if (el) el.style.display = 'block';
    }
    
    async confirmarExclusao() {
        try {
            const token = this.getToken();
            const headers = {};
            if (token) headers['Authorization'] = `Bearer ${token}`;
            const response = await fetch(`/api/v1/clientes/${this.clienteEmEdicao}`, {
                method: 'DELETE',
                headers,
                credentials: 'include'
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Erro ao excluir cliente');
            }
            
            this.mostrarAlerta('Cliente excluído com sucesso!', 'success');
            
            const elConfirm = document.getElementById('modalConfirmacao');
            if (elConfirm) elConfirm.style.display = 'none';
            this.carregarClientes();
            
        } catch (error) {
            this.mostrarAlerta(error.message, 'danger');
            const elConfirm = document.getElementById('modalConfirmacao');
            if (elConfirm) elConfirm.style.display = 'none';
        }
    }
    
    async carregarPdvClientePadrao() {
        const sel = document.getElementById('pdvClientePadraoId');
        if (!sel) return;
        const token = this.getToken();
        const headers = { 'Content-Type': 'application/json' };
        if (token) headers['Authorization'] = `Bearer ${token}`;
        try {
            const params = new URLSearchParams({
                pagina: 1,
                por_pagina: 5000,
                ...this.currentFilters
            });
            const [rLista, rPadrao] = await Promise.all([
                fetch(`/api/v1/clientes/?${params}`, { headers, credentials: 'include' }),
                fetch('/api/v1/clientes/pdv-cliente-padrao/', { headers, credentials: 'include' })
            ]);
            let list = [];
            if (rLista.ok) {
                const data = await rLista.json();
                if (Array.isArray(data)) {
                    list = data;
                } else if (data && Array.isArray(data.clientes)) {
                    list = data.clientes;
                } else if (data && Array.isArray(data.items)) {
                    list = data.items;
                } else if (data && Array.isArray(data.data)) {
                    list = data.data;
                }
            }
            sel.innerHTML = '<option value="">Nenhum (selecionar na hora da venda)</option>';
            list.forEach(c => {
                const opt = document.createElement('option');
                opt.value = c.id;
                opt.textContent = (c.nome || '').trim() || `Cliente #${c.id}`;
                sel.appendChild(opt);
            });
            let clienteIdPadrao = null;
            if (rPadrao.ok) {
                const data = await rPadrao.json();
                if (data && data.cliente_id != null) clienteIdPadrao = data.cliente_id;
            }
            sel.value = clienteIdPadrao !== null ? String(clienteIdPadrao) : '';
        } catch (e) {}
    }

    async salvarPdvClientePadrao() {
        const sel = document.getElementById('pdvClientePadraoId');
        if (!sel) return;
        const token = this.getToken();
        if (!token) {
            this.mostrarAlerta('Você precisa estar autenticado.', 'danger');
            return;
        }
        const valor = sel.value;
        const clienteId = valor === '' ? null : parseInt(valor, 10);
        const headers = { 'Content-Type': 'application/json' };
        headers['Authorization'] = `Bearer ${token}`;
        try {
            const response = await fetch('/api/v1/clientes/pdv-cliente-padrao/', {
                method: 'PUT',
                headers,
                body: JSON.stringify({ cliente_id: clienteId }),
                credentials: 'include'
            });
            const data = await response.json().catch(() => ({}));
            if (response.ok) {
                this.mostrarAlerta('Cliente padrão do PDV salvo.', 'success');
            } else {
                this.mostrarAlerta(data.detail || 'Não foi possível salvar. Apenas no contexto de Cliente Administrador.', 'danger');
            }
        } catch (e) {
            this.mostrarAlerta('Erro ao salvar. Tente novamente.', 'danger');
        }
    }

    getToken() {
        // Usar getAuthToken global (certipeso) se disponível; senão cookie (JWT pode ter = no valor)
        if (typeof window.getAuthToken === 'function') return window.getAuthToken();
        const nameEq = 'pdv_automscale_token=';
        const ca = document.cookie.split(';');
        for (let i = 0; i < ca.length; i++) {
            let c = ca[i];
            while (c.charAt(0) === ' ') c = c.substring(1);
            if (c.indexOf(nameEq) === 0) return c.substring(nameEq.length);
        }
        return sessionStorage.getItem('pdv_automscale_token') || null;
    }
    
    mostrarAlerta(mensagem, tipo) {
        const duracao = tipo === 'danger' ? 2000 : 5000;
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${tipo} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${mensagem}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        const modalCliente = document.getElementById('modalCliente');
        const modalUsuario = document.getElementById('modalUsuarioCliente');
        const modalClienteVisivel = modalCliente && modalCliente.style.display === 'block';
        const modalUsuarioVisivel = modalUsuario && modalUsuario.style.display === 'block';

        let alertContainer = null;
        if (modalClienteVisivel) {
            alertContainer = document.getElementById('modalClienteAlertContainer');
        } else if (modalUsuarioVisivel) {
            alertContainer = document.getElementById('modalUsuarioClienteAlertContainer');
        }
        if (alertContainer) {
            alertContainer.innerHTML = '';
            alertContainer.appendChild(alertDiv);
            alertContainer.style.display = 'block';
            alertDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            setTimeout(() => {
                if (alertDiv.parentNode) {
                    alertDiv.remove();
                }
                if (alertContainer && !alertContainer.children.length) {
                    alertContainer.style.display = 'none';
                }
            }, duracao);
            return;
        }

        const renderFallback = () => {
            let container = document.getElementById('alert-container');
            if (container) {
                container.appendChild(alertDiv);
            } else {
                document.body.appendChild(alertDiv);
            }
            setTimeout(() => {
                if (alertDiv.parentNode) {
                    alertDiv.remove();
                }
            }, duracao);
        };

        try {
            if (window.alertSystem && typeof window.alertSystem.show === 'function') {
                window.alertSystem.clearAll();
                const dur = tipo === 'danger' ? 2000 : undefined;
                window.alertSystem.show(mensagem, tipo, dur);
                return;
            }
            renderFallback();
        } catch (e) {
            renderFallback();
        }
    }
    
    async criarUsuarioCliente(clienteId, dadosUsuario) {
        try {
            // Validar senhas
            if (dadosUsuario.senha !== dadosUsuario.confirmar_senha) {
                this.mostrarAlerta('As senhas não coincidem', 'danger');
                return;
            }
            
            if (dadosUsuario.senha.length < 6) {
                this.mostrarAlerta('A senha deve ter pelo menos 6 caracteres', 'danger');
                return;
            }
            
            const token = this.getToken();
            if (!token) {
                this.mostrarAlerta('Você precisa estar autenticado para criar usuários', 'danger');
                return;
            }
            
            const headers = { 'Content-Type': 'application/json' };
            if (token) headers['Authorization'] = `Bearer ${token}`;
            const response = await fetch(`/api/v1/clientes/${clienteId}/usuarios`, {
                method: 'POST',
                headers,
                body: JSON.stringify({
                    nome: dadosUsuario.nome,
                    email: dadosUsuario.email,
                    senha: dadosUsuario.senha,
                    cliente_id: clienteId,
                    ativo: true
                }),
                credentials: 'include'
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.mostrarAlerta('Usuário criado com sucesso!', 'success');
                fecharModalUsuarioCliente();
            } else {
                const mensagemErro = data.detail || 'Erro ao criar usuário';
                this.mostrarAlerta(mensagemErro, 'danger');
            }
        } catch (error) {
            this.mostrarAlerta('Erro ao criar usuário. Tente novamente.', 'danger');
        }
    }
}

// Funções globais para compatibilidade
window.aplicarFiltros = function() {
    clientesManager.aplicarFiltros();
};

// Função global para criar usuário (chamada pelo botão)
window.criarUsuarioClienteSubmit = function(e) {
    if (e) {
        e.preventDefault();
    }
    
    // Verificar se todos os elementos existem
    const clienteIdElement = document.getElementById('cliente_id_usuario');
    const usuarioNomeElement = document.getElementById('usuario_nome');
    const usuarioEmailElement = document.getElementById('usuario_email');
    const usuarioSenhaElement = document.getElementById('usuario_senha');
    const usuarioConfirmarSenhaElement = document.getElementById('usuario_confirmar_senha');
    
    if (!clienteIdElement) {
        alert('Erro: Cliente não identificado. Tente novamente.');
        return;
    }
    
    if (!usuarioNomeElement) {
        alert('Erro: Campo nome não encontrado. Tente novamente.');
        return;
    }
    
    if (!usuarioEmailElement) {
        alert('Erro: Campo email não encontrado. Tente novamente.');
        return;
    }
    
    if (!usuarioSenhaElement) {
        alert('Erro: Campo senha não encontrado. Tente novamente.');
        return;
    }
    
    if (!usuarioConfirmarSenhaElement) {
        alert('Erro: Campo confirmar senha não encontrado. Tente novamente.');
        return;
    }
    
    const clienteId = clienteIdElement.value;
    
    if (!clienteId) {
        alert('Erro: Cliente não identificado. Feche o modal e tente novamente.');
        return;
    }
    
    const dadosUsuario = {
        nome: usuarioNomeElement.value.trim(),
        email: usuarioEmailElement.value.trim(),
        senha: usuarioSenhaElement.value,
        confirmar_senha: usuarioConfirmarSenhaElement.value
    };
    
    // Validar campos obrigatórios
    if (!dadosUsuario.nome || !dadosUsuario.email || !dadosUsuario.senha || !dadosUsuario.confirmar_senha) {
        alert('Por favor, preencha todos os campos obrigatórios.');
        return;
    }
    
    if (window.clientesManager) {
        window.clientesManager.criarUsuarioCliente(clienteId, dadosUsuario);
    } else {
        alert('Erro: Sistema não inicializado. Recarregue a página e tente novamente.');
    }
};

// Inicializar quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', function() {
    window.clientesManager = new ClientesManager();
}); 