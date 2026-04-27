// PDV Ibix - Empresa Fiscal JavaScript
class EmpresaFiscalManager {
    constructor() {
        this.empresaEmEdicao = null;
        this.empresaNfceCscTokenConfigurado = false;
        this.certificadoArquivo = null;
        this.logoArquivo = null;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.setupMasks();
        this.carregarParametrosFiscal();
        this.carregarClientes();
        this.carregarEmpresas();
    }
    
    setupEventListeners() {
        const formEmpresa = document.getElementById('formEmpresa');
        const btnConfirmarExclusao = document.getElementById('btnConfirmarExclusao');
        const certificadoFile = document.getElementById('certificado_file');
        const modoReceb = document.getElementById('modo_recebimento');
        if (modoReceb) {
            modoReceb.addEventListener('change', () => {
                this._toggleTaxaFields();
                this._toggleGatewayPlataforma();
            });
            this._toggleTaxaFields();
            this._toggleGatewayPlataforma();
        }
        
        if (formEmpresa) {
            formEmpresa.addEventListener('submit', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const btn = document.getElementById('btnSalvarEmpresa');
                if (btn && btn.disabled) return;
                if (btn) {
                    btn.disabled = true;
                    btn.textContent = 'Salvando...';
                }
                this.salvarEmpresa().finally(() => {
                    if (btn) {
                        btn.disabled = false;
                        btn.textContent = 'Salvar';
                    }
                });
            });
        }
        
        if (btnConfirmarExclusao) {
            btnConfirmarExclusao.addEventListener('click', () => {
                this.confirmarExclusao();
            });
        }
        
        // Listener para upload de certificado
        if (certificadoFile) {
            certificadoFile.addEventListener('change', (e) => {
                this.processarCertificado(e.target.files[0]);
            });
        }
        
        // Listener para anexar logo (preview e envio em base64 ao salvar)
        const logoFile = document.getElementById('logo_file');
        if (logoFile) {
            logoFile.addEventListener('change', (e) => {
                const file = e.target.files[0];
                this.logoArquivo = file || null;
                if (file) {
                    const reader = new FileReader();
                    reader.onload = () => this.atualizarPreviewLogo(reader.result);
                    reader.readAsDataURL(file);
                } else {
                    this.atualizarPreviewLogo('');
                }
            });
        }

        // Filtros com debounce
        let timeoutId;
        ['filtroRazaoSocial', 'filtroCNPJ'].forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.addEventListener('input', () => {
                    clearTimeout(timeoutId);
                    timeoutId = setTimeout(() => this.aplicarFiltros(), 500);
                });
            }
        });
        
        const filtroAtivo = document.getElementById('filtroAtivo');
        if (filtroAtivo) {
            filtroAtivo.addEventListener('change', () => {
                this.aplicarFiltros();
            });
        }
        const filtroCliente = document.getElementById('filtroCliente');
        if (filtroCliente) {
            filtroCliente.addEventListener('change', () => {
                this.aplicarFiltros();
            });
        }
        const filtroAmbiente = document.getElementById('filtroAmbiente');
        if (filtroAmbiente) {
            filtroAmbiente.addEventListener('change', () => {
                this.aplicarFiltros();
            });
        }
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
    
    async carregarParametrosFiscal() {
        try {
            const token = this.getToken();
            const headers = {};
            if (token) headers['Authorization'] = `Bearer ${token}`;
            const response = await fetch('/api/v1/fiscal/empresa/parametros', {
                headers,
                credentials: 'include'
            });
            if (!response.ok) return;
            const data = await response.json();
            const opcoes = data.opcoes_ambiente;
            if (!Array.isArray(opcoes)) return;
            const selectModal = document.getElementById('ambiente');
            const selectFiltro = document.getElementById('filtroAmbiente');
            if (selectModal && selectModal.tagName === 'SELECT') {
                selectModal.innerHTML = '';
                opcoes.forEach(o => {
                    const opt = document.createElement('option');
                    opt.value = o.value || o;
                    opt.textContent = (typeof o === 'object' && o.label) ? o.label : String(o.value || o);
                    selectModal.appendChild(opt);
                });
            }
            if (selectFiltro) {
                const firstOpt = selectFiltro.querySelector('option[value=""]');
                const todosOpt = firstOpt ? firstOpt.outerHTML : '<option value="">Todos ambientes</option>';
                selectFiltro.innerHTML = todosOpt;
                opcoes.forEach(o => {
                    const opt = document.createElement('option');
                    opt.value = o.value || o;
                    opt.textContent = (typeof o === 'object' && o.label) ? o.label : String(o.value || o);
                    selectFiltro.appendChild(opt);
                });
            }
        } catch (e) {}
    }

    async buscarCep(cep) {
        const cepLimpo = cep.replace(/\D/g, '');
        if (cepLimpo.length !== 8) return;
        
        try {
            const response = await fetch(`https://viacep.com.br/ws/${cepLimpo}/json/`, {
                method: 'GET',
                mode: 'cors',
                cache: 'default'
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (!data.erro) {
                const endereco = document.getElementById('endereco');
                const bairro = document.getElementById('bairro');
                const cidade = document.getElementById('cidade');
                const uf = document.getElementById('uf');
                
                if (endereco) endereco.value = data.logradouro || '';
                if (bairro) bairro.value = data.bairro || '';
                if (cidade) cidade.value = data.localidade || '';
                if (uf) uf.value = data.uf || '';
            } else {
                this.mostrarAlerta('CEP não encontrado', 'warning');
            }
        } catch (error) {
            // Não mostrar erro para o usuário (pode ser problema de CORS ou rede)
        }
    }
    
    async carregarClientes() {
        try {
            const token = this.getToken();
            const headers = {};
            if (token) headers['Authorization'] = `Bearer ${token}`;
            const response = await fetch('/api/v1/clientes/todos?para_empresa_fiscal=true', {
                headers,
                credentials: 'include'
            });
            if (!response.ok) return;
            const clientes = await response.json();
            if (!Array.isArray(clientes)) return;
            const selectModal = document.getElementById('cliente_id');
            const selectFiltro = document.getElementById('filtroCliente');
            if (selectModal && selectModal.tagName === 'SELECT') {
                const firstOpt = selectModal.querySelector('option');
                selectModal.innerHTML = firstOpt ? firstOpt.outerHTML : '<option value="">Selecione...</option>';
                clientes.forEach(c => {
                    const opt = document.createElement('option');
                    opt.value = c.id;
                    opt.textContent = c.nome || `Cliente #${c.id}`;
                    selectModal.appendChild(opt);
                });
            }
            if (selectFiltro) {
                const firstOpt = selectFiltro.querySelector('option');
                selectFiltro.innerHTML = firstOpt ? firstOpt.outerHTML : '<option value="">Selecione...</option>';
                clientes.forEach(c => {
                    const opt = document.createElement('option');
                    opt.value = c.id;
                    opt.textContent = c.nome || `Cliente #${c.id}`;
                    selectFiltro.appendChild(opt);
                });
            }
        } catch (e) {}
    }

    async definirClientePadraoSeNecessario() {
        if (typeof window.permiteVerClienteEmpresaFiscal !== 'undefined' && window.permiteVerClienteEmpresaFiscal === true) {
            return;
        }
        const clienteInput = document.getElementById('cliente_id');
        if (!clienteInput || clienteInput.tagName === 'SELECT') {
            return;
        }
        try {
            const token = this.getToken();
            const headers = {};
            if (token) headers['Authorization'] = `Bearer ${token}`;
            const response = await fetch('/api/v1/clientes/todos?para_empresa_fiscal=true', {
                headers,
                credentials: 'include'
            });
            if (!response.ok) return;
            const clientes = await response.json();
            if (Array.isArray(clientes) && clientes.length > 0) {
                clienteInput.value = clientes[0].id;
            }
        } catch (e) {}
    }

    async carregarEmpresas() {
        try {
            const params = new URLSearchParams();
            
            const razaoSocial = document.getElementById('filtroRazaoSocial')?.value.trim();
            const cnpj = document.getElementById('filtroCNPJ')?.value.trim();
            const ativo = document.getElementById('filtroAtivo')?.value;
            const clienteId = document.getElementById('filtroCliente')?.value;
            
            if (razaoSocial) params.append('razao_social', razaoSocial);
            if (cnpj) params.append('cnpj', cnpj);
            // "Todas" (valor vazio) → backend lista ativas+inativas; "Ativas"/"Inativas" → filtra por ativo
            if (ativo === '') {
                params.append('todas', 'true');
            } else if (ativo) {
                params.append('ativo', ativo);
            }
            if (clienteId) params.append('cliente_id', clienteId);
            
            const token = this.getToken();
            const headers = {};
            if (token) headers['Authorization'] = `Bearer ${token}`;
            const url = `/api/v1/fiscal/empresa${params.toString() ? '?' + params.toString() : ''}`;
            
            const response = await fetch(url, {
                headers,
                credentials: 'include'
            });
            
            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.detail || `Erro ao carregar empresas (${response.status})`);
            }
            
            let empresas = await response.json();
            
            // Garantir que empresas é um array
            let empresasArray = Array.isArray(empresas) ? empresas : [];
            // Filtro por ambiente (regra central: Homologação vs Produção)
            const filtroAmbiente = document.getElementById('filtroAmbiente')?.value;
            if (filtroAmbiente) {
                empresasArray = empresasArray.filter(e => (e.ambiente || 'homologacao') === filtroAmbiente);
            }
            this.renderizarTabela(empresasArray);
            
        } catch (error) {
            this.mostrarAlerta(error.message || 'Erro ao carregar empresas', 'danger');
            
            // Mostrar mensagem na tabela em caso de erro
            const tbody = document.getElementById('tabelaEmpresas');
            if (tbody) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="9" class="text-center text-danger">
                            Erro ao carregar empresas. Tente novamente.
                        </td>
                    </tr>
                `;
            }
        }
    }
    
    renderizarTabela(empresas) {
        const tbody = document.getElementById('tabelaEmpresas');
        
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        // Garantir que empresas é um array
        const permiteVerCliente = typeof window.permiteVerClienteEmpresaFiscal === 'undefined' || window.permiteVerClienteEmpresaFiscal === true;
        const colspan = permiteVerCliente ? 9 : 8;

        if (!Array.isArray(empresas)) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="${colspan}" class="text-center text-warning">
                        Formato de dados inválido
                    </td>
                </tr>
            `;
            return;
        }
        
        if (empresas.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="${colspan}" class="text-center text-muted">
                        Nenhuma empresa encontrada
                    </td>
                </tr>
            `;
            return;
        }
        
        const canDelete = typeof window.canDeleteEmpresa !== 'undefined' && window.canDeleteEmpresa;
        empresas.forEach(empresa => {
            const deleteBtnHtml = canDelete
                ? `<button type="button" class="btn btn-outline-danger" onclick="empresaFiscalManager.excluirEmpresa(${empresa.id})" title="Excluir"><i class="align-middle me-1" data-feather="trash-2"></i> Excluir</button>`
                : '';
            const row = document.createElement('tr');
            const celulaCliente = permiteVerCliente ? `<td>${empresa.cliente_nome || '-'}</td>` : '';
            row.innerHTML = `
                <td>${empresa.id}</td>
                ${celulaCliente}
                <td>${empresa.razao_social || ''}</td>
                <td>${empresa.nome_fantasia || '-'}</td>
                <td>${empresa.cnpj || ''}</td>
                <td>${empresa.cidade || ''}/${empresa.uf || ''}</td>
                <td>
                    <span class="badge ${empresa.ambiente === 'producao' ? 'bg-success' : 'bg-warning'}">
                        ${empresa.ambiente === 'producao' ? 'Produção' : 'Homologação'}
                    </span>
                </td>
                <td>
                    <span class="badge ${empresa.ativo ? 'bg-success' : 'bg-secondary'}">
                        ${empresa.ativo ? 'Ativa' : 'Inativa'}
                    </span>
                </td>
                <td>
                    <div class="btn-group btn-group-sm" role="group">
                        <button type="button" class="btn btn-outline-primary" 
                                onclick="empresaFiscalManager.editarEmpresa(${empresa.id})" title="Editar">
                            <i class="align-middle me-1" data-feather="edit-2"></i> Editar
                        </button>
                        ${deleteBtnHtml}
                    </div>
                </td>
            `;
            tbody.appendChild(row);
        });
        
        // Reinicializar ícones Feather
        setTimeout(() => {
            try {
                if (typeof feather !== 'undefined' && feather && typeof feather.replace === 'function') {
                    const featherElements = document.querySelectorAll('[data-feather]');
                    if (featherElements.length > 0) {
                        feather.replace();
                    }
                }
            } catch (error) {}
        }, 100);
    }
    
    aplicarFiltros() {
        this.carregarEmpresas();
    }
    
    processarCertificado(file) {
        if (!file) {
            return;
        }
        
        // Validar tipo de arquivo
        const extensoesPermitidas = ['.pfx', '.p12'];
        const nomeArquivo = file.name.toLowerCase();
        const extensaoValida = extensoesPermitidas.some(ext => nomeArquivo.endsWith(ext));
        
        if (!extensaoValida) {
            this.mostrarAlerta('Por favor, selecione um arquivo .pfx ou .p12', 'danger');
            const certificadoFile = document.getElementById('certificado_file');
            if (certificadoFile) {
                certificadoFile.value = '';
            }
            return;
        }
        
        // Validar tamanho (máximo 5MB)
        const tamanhoMaximo = 5 * 1024 * 1024; // 5MB
        if (file.size > tamanhoMaximo) {
            this.mostrarAlerta('O arquivo é muito grande. Tamanho máximo: 5MB', 'danger');
            const certificadoFile = document.getElementById('certificado_file');
            if (certificadoFile) {
                certificadoFile.value = '';
            }
            return;
        }
        
        // Mostrar nome do arquivo
        const nomeArquivoDiv = document.getElementById('certificado_nome_arquivo');
        const nomeArquivoTexto = document.getElementById('certificado_nome_texto');
        if (nomeArquivoDiv && nomeArquivoTexto) {
            nomeArquivoTexto.textContent = file.name;
            nomeArquivoDiv.style.display = 'block';
        }
        
        // Armazenar nome do arquivo no campo hidden
        const certificadoPath = document.getElementById('certificado_a1_path');
        if (certificadoPath) {
            certificadoPath.value = file.name;
        }
        
        // Armazenar arquivo para envio
        this.certificadoArquivo = file;
        
        // Reinicializar ícones Feather
        setTimeout(() => {
            try {
                if (typeof feather !== 'undefined' && feather && typeof feather.replace === 'function') {
                    feather.replace();
                }
            } catch (error) {}
        }, 100);
    }
    
    validarFormulario() {
        const erros = [];
        const razaoSocial = document.getElementById('razao_social')?.value.trim();
        const cnpj = document.getElementById('cnpj')?.value.replace(/\D/g, '');
        
        if (!razaoSocial) {
            erros.push('Razão Social é obrigatória');
        }
        
        if (!cnpj) {
            erros.push('CNPJ é obrigatório');
        } else if (cnpj.length !== 14) {
            erros.push('CNPJ deve conter 14 dígitos');
        } else if (!this.validarCNPJ(cnpj)) {
            erros.push('CNPJ inválido');
        }
        const nfceHabilitado = document.getElementById('nfce_habilitado')?.checked;
        if (nfceHabilitado) {
            const cscId = document.getElementById('nfce_csc_id')?.value?.trim();
            const cscToken = document.getElementById('nfce_csc_token')?.value?.trim();
            if (!cscId) erros.push('ID CSC obrigatório para NFC-e habilitado');
            // Na edição, token já configurado não precisa ser preenchido de novo (não é retornado pela API)
            const tokenJaConfigurado = this.empresaEmEdicao && this.empresaNfceCscTokenConfigurado;
            if (!tokenJaConfigurado && !cscToken) erros.push('Token CSC obrigatório para NFC-e habilitado');
        }
        return {
            valido: erros.length === 0,
            erros: erros
        };
    }
    
    validarCNPJ(cnpj) {
        // Remove caracteres não numéricos
        cnpj = cnpj.replace(/\D/g, '');
        
        if (cnpj.length !== 14) return false;
        
        // Verifica se todos os dígitos são iguais
        if (/^(\d)\1+$/.test(cnpj)) return false;
        
        // Validação dos dígitos verificadores
        let tamanho = cnpj.length - 2;
        let numeros = cnpj.substring(0, tamanho);
        let digitos = cnpj.substring(tamanho);
        let soma = 0;
        let pos = tamanho - 7;
        
        for (let i = tamanho; i >= 1; i--) {
            soma += numeros.charAt(tamanho - i) * pos--;
            if (pos < 2) pos = 9;
        }
        
        let resultado = soma % 11 < 2 ? 0 : 11 - soma % 11;
        if (resultado != digitos.charAt(0)) return false;
        
        tamanho = tamanho + 1;
        numeros = cnpj.substring(0, tamanho);
        soma = 0;
        pos = tamanho - 7;
        
        for (let i = tamanho; i >= 1; i--) {
            soma += numeros.charAt(tamanho - i) * pos--;
            if (pos < 2) pos = 9;
        }
        
        resultado = soma % 11 < 2 ? 0 : 11 - soma % 11;
        if (resultado != digitos.charAt(1)) return false;
        
        return true;
    }
    
    async salvarEmpresa() {
        // Validar formulário antes de enviar
        const validacao = this.validarFormulario();
        if (!validacao.valido) {
            this.mostrarAlerta(validacao.erros.join(', '), 'danger');
            return;
        }
        
        try {
            const formElement = document.getElementById('formEmpresa');
            if (!formElement) {
                throw new Error('Formulário não encontrado');
            }
            
            let formData = new FormData(formElement);
            let clienteIdVal = formData.get('cliente_id');
            if (!this.empresaEmEdicao && (!clienteIdVal || clienteIdVal === '') && (typeof window.permiteVerClienteEmpresaFiscal === 'undefined' || window.permiteVerClienteEmpresaFiscal === true)) {
                this.mostrarAlerta('Selecione o Cliente (cadastro na plataforma ao qual esta empresa fiscal pertence).', 'danger');
                return;
            }
            if (!this.empresaEmEdicao && (!clienteIdVal || clienteIdVal === '') && window.permiteVerClienteEmpresaFiscal === false) {
                await this.definirClientePadraoSeNecessario();
                formData = new FormData(formElement);
                clienteIdVal = formData.get('cliente_id');
            }
            if (!this.empresaEmEdicao && (!clienteIdVal || clienteIdVal === '')) {
                this.mostrarAlerta('Não foi possível vincular ao cliente. Tente novamente.', 'danger');
                return;
            }
            
            // Para nova empresa, converter certificado para base64 (PUT aceita); para edição, usar POST /certificado
            let certificadoBase64 = null;
            if (this.certificadoArquivo && !this.empresaEmEdicao) {
                certificadoBase64 = await this.converterArquivoParaBase64(this.certificadoArquivo);
            }

            // Se estiver editando e tiver arquivo .pfx + senha, usar endpoint dedicado POST /certificado (atualiza validade no backend)
            if (this.empresaEmEdicao && this.certificadoArquivo) {
                const senhaCert = formData.get('senha_certificado') || '';
                if (!senhaCert || !senhaCert.trim()) {
                    this.mostrarAlerta('Para enviar o certificado, informe a senha do arquivo .pfx/.p12', 'danger');
                    return;
                }
                const formCert = new FormData();
                formCert.append('arquivo', this.certificadoArquivo);
                formCert.append('senha', senhaCert);
                const token = this.getToken();
                const headersCert = {};
                if (token) headersCert['Authorization'] = `Bearer ${token}`;
                const resCert = await fetch(`/api/v1/fiscal/empresa/${this.empresaEmEdicao}/certificado`, {
                    method: 'POST',
                    headers: headersCert,
                    body: formCert,
                    credentials: 'include'
                });
                if (!resCert.ok) {
                    const errCert = await resCert.json().catch(() => ({}));
                    throw new Error(errCert.detail || 'Erro ao enviar certificado');
                }
                const empresaAtualizada = await resCert.json();
                if (empresaAtualizada.certificado_validade) {
                    const certVal = document.getElementById('certificado_validade');
                    if (certVal) certVal.value = typeof empresaAtualizada.certificado_validade === 'string'
                        ? empresaAtualizada.certificado_validade.split('T')[0] : empresaAtualizada.certificado_validade;
                }
            }

            // Processar logo anexado (base64 com data URL para o backend detectar o tipo)
            let logoEmissorBlob = null;
            if (this.logoArquivo) {
                logoEmissorBlob = await this.converterArquivoParaDataURL(this.logoArquivo);
            }
            const empresaData = {
                cliente_id: clienteIdVal ? parseInt(clienteIdVal, 10) : undefined,
                razao_social: formData.get('razao_social'),
                nome_fantasia: formData.get('nome_fantasia') || null,
                cnpj: formData.get('cnpj'),
                ie: formData.get('ie') || null,
                im: formData.get('im') || null,
                cnae: formData.get('cnae') || null,
                crt: formData.get('crt') ? parseInt(formData.get('crt')) : null,
                cep: formData.get('cep') || null,
                endereco: formData.get('endereco') || null,
                numero: formData.get('numero') || null,
                complemento: formData.get('complemento') || null,
                bairro: formData.get('bairro') || null,
                cidade: formData.get('cidade') || null,
                uf: formData.get('uf') || null,
                municipio_ibge: formData.get('municipio_ibge') ? parseInt(formData.get('municipio_ibge'), 10) : null,
                telefone: formData.get('telefone') || null,
                email: formData.get('email') || null,
                certificado_a1_path: formData.get('certificado_a1_path') || null,
                certificado_a1_blob: certificadoBase64,
                senha_certificado: this.empresaEmEdicao ? undefined : (formData.get('senha_certificado') || null),
                certificado_validade: formData.get('certificado_validade') || null,
                provedor_fiscal: formData.get('provedor_fiscal') || null,
                ambiente: formData.get('ambiente') || 'homologacao',
                uf_emissao: formData.get('uf_emissao') || null,
                cnae_servicos: formData.get('cnae_servicos') || null,
                codigo_servico_municipal: formData.get('codigo_servico_municipal') || null,
                aliquota_iss: formData.get('aliquota_iss') ? parseFloat(formData.get('aliquota_iss')) : null,
                codigo_ativacao_sat: formData.get('codigo_ativacao_sat') || null,
                numero_serie_sat: formData.get('numero_serie_sat') || null,
                tipo_equipamento_sat: formData.get('tipo_equipamento_sat') || null,
                logo_emissor_blob: logoEmissorBlob,
                nfce_habilitado: formData.get('nfce_habilitado') === 'true',
                nfce_csc_id: (formData.get('nfce_csc_id') || '').toString().trim() || null,
                nfce_csc_token: (formData.get('nfce_csc_token') || '').toString().trim() || null,
                ativo: formData.get('ativo') === 'true',
                modo_recebimento: formData.get('modo_recebimento') || undefined,
                taxa_plataforma_percentual: formData.get('taxa_plataforma_percentual') ? parseFloat(formData.get('taxa_plataforma_percentual')) : null,
                taxa_plataforma_valor_fixo: formData.get('taxa_plataforma_valor_fixo') ? parseFloat(formData.get('taxa_plataforma_valor_fixo')) : null,
            };
            const gwEl = document.getElementById('gateway_plataforma');
            if (gwEl) {
                empresaData.gateway_plataforma = formData.get('gateway_plataforma') || undefined;
            }
            
            if (this.empresaEmEdicao && empresaData.cliente_id === undefined) {
                delete empresaData.cliente_id;
            }
            // Na edição, não enviar token CSC vazio para não sobrescrever o já salvo no banco
            if (this.empresaEmEdicao && (!empresaData.nfce_csc_token || empresaData.nfce_csc_token === '')) {
                delete empresaData.nfce_csc_token;
            }
            // Remover campos vazios (exceto nfce_csc quando NFC-e habilitado - backend valida)
            const nfceHabilitado = empresaData.nfce_habilitado === true;
            Object.keys(empresaData).forEach(key => {
                if (empresaData[key] === '' || empresaData[key] === null || empresaData[key] === undefined) {
                    // Manter nfce_csc_id e nfce_csc_token quando NFC-e habilitado para o backend validar
                    if (nfceHabilitado && (key === 'nfce_csc_id' || key === 'nfce_csc_token')) return;
                    delete empresaData[key];
                }
            });
            
            const token = this.getToken();
            const url = this.empresaEmEdicao 
                ? `/api/v1/fiscal/empresa/${this.empresaEmEdicao}`
                : '/api/v1/fiscal/empresa';
            
            const method = this.empresaEmEdicao ? 'PUT' : 'POST';
            const headers = { 'Content-Type': 'application/json' };
            if (token) headers['Authorization'] = `Bearer ${token}`;
            const response = await fetch(url, {
                method: method,
                headers,
                body: JSON.stringify(empresaData),
                credentials: 'include'
            });
            
            if (!response.ok) {
                let msg = 'Erro ao salvar empresa';
                try {
                    const error = await response.json();
                    if (error.detail && Array.isArray(error.detail)) {
                        msg = error.detail.map(err => (err.msg || err.loc?.join('.'))).join('; ');
                    } else if (error.detail) {
                        msg = typeof error.detail === 'string' ? error.detail : JSON.stringify(error.detail);
                    }
                } catch (_) {
                    const text = await response.text();
                    if (text) msg = `Erro ${response.status}: ${text.substring(0, 200)}`;
                }
                throw new Error(msg);
            }
            
            try {
                await response.json();
            } catch (_) {
                // Resposta OK mas corpo não-JSON; considerar sucesso
            }
            
            this.mostrarAlerta(
                this.empresaEmEdicao ? 'Empresa atualizada com sucesso!' : 'Empresa criada com sucesso!',
                'success'
            );
            
            if (typeof fecharModalEmpresa === 'function') {
                fecharModalEmpresa();
            }
            
            this.empresaEmEdicao = null;
            this.carregarEmpresas();
            
        } catch (error) {
            this.mostrarAlerta(error.message || 'Erro ao salvar empresa', 'danger');
        }
    }
    
    async editarEmpresa(id) {
        try {
            if (!id) {
                throw new Error('ID da empresa não fornecido');
            }
            
            const token = this.getToken();
            const headers = {};
            if (token) headers['Authorization'] = `Bearer ${token}`;
            const response = await fetch(`/api/v1/fiscal/empresa/${id}`, {
                headers,
                credentials: 'include'
            });
            
            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.detail || 'Erro ao carregar empresa');
            }
            
            const empresa = await response.json();
            // Garantir que o select de clientes está populado antes de preencher o formulário
            await this.carregarClientes();
            this.preencherFormulario(empresa);
            this.empresaEmEdicao = id;
            
            const titulo = document.getElementById('modalEmpresaTitulo');
            const modal = document.getElementById('modalEmpresa');
            
            if (titulo) {
                titulo.textContent = 'Editar Empresa Fiscal';
            }
            if (modal) {
                modal.style.display = 'block';
            }
            
        } catch (error) {
            this.mostrarAlerta(error.message || 'Erro ao carregar empresa', 'danger');
        }
    }
    
    preencherFormulario(empresa) {
        if (!empresa) return;
        
        const setValue = (id, value) => {
            const element = document.getElementById(id);
            if (element) {
                const strVal = value === null || value === undefined ? '' : String(value);
                element.value = strVal;
            }
        };
        
        setValue('empresa_id', empresa.id);
        setValue('cliente_id', empresa.cliente_id);
        setValue('razao_social', empresa.razao_social);
        setValue('nome_fantasia', empresa.nome_fantasia);
        setValue('cnpj', empresa.cnpj);
        setValue('ie', empresa.ie);
        setValue('im', empresa.im);
        setValue('cnae', empresa.cnae);
        setValue('crt', empresa.crt != null ? String(empresa.crt) : '');
        setValue('cep', empresa.cep);
        setValue('endereco', empresa.endereco);
        setValue('numero', empresa.numero);
        setValue('complemento', empresa.complemento);
        setValue('bairro', empresa.bairro);
        setValue('cidade', empresa.cidade);
        setValue('uf', empresa.uf);
        setValue('municipio_ibge', empresa.municipio_ibge != null ? String(empresa.municipio_ibge) : '');
        setValue('telefone', empresa.telefone);
        setValue('email', empresa.email);
        setValue('certificado_a1_path', empresa.certificado_a1_path);
        setValue('senha_certificado', '');
        const certVal = empresa.certificado_validade;
        setValue('certificado_validade', certVal ? (typeof certVal === 'string' ? certVal.split('T')[0] : certVal) : '');
        
        const certificadoFile = document.getElementById('certificado_file');
        if (certificadoFile) {
            certificadoFile.value = '';
        }
        this.certificadoArquivo = null;
        const logoFile = document.getElementById('logo_file');
        if (logoFile) {
            logoFile.value = '';
        }
        this.logoArquivo = null;
        
        const nomeArquivoDiv = document.getElementById('certificado_nome_arquivo');
        const nomeArquivoTexto = document.getElementById('certificado_nome_texto');
        if (empresa.certificado_a1_path && nomeArquivoDiv && nomeArquivoTexto) {
            nomeArquivoTexto.textContent = empresa.certificado_a1_path;
            nomeArquivoDiv.style.display = 'block';
        } else if (nomeArquivoDiv) {
            nomeArquivoDiv.style.display = 'none';
        }
        this.atualizarPreviewLogo(empresa.logo_url || '');
        this.atualizarBotaoVisualizarLogo(empresa.logo_url || '');
        setValue('provedor_fiscal', empresa.provedor_fiscal || '');
        setValue('ambiente', empresa.ambiente || 'homologacao');
        setValue('uf_emissao', empresa.uf_emissao);
        setValue('cnae_servicos', empresa.cnae_servicos);
        setValue('codigo_servico_municipal', empresa.codigo_servico_municipal);
        setValue('aliquota_iss', empresa.aliquota_iss);
        setValue('codigo_ativacao_sat', empresa.codigo_ativacao_sat);
        setValue('numero_serie_sat', empresa.numero_serie_sat);
        setValue('tipo_equipamento_sat', empresa.tipo_equipamento_sat || '');
        const nfceHab = document.getElementById('nfce_habilitado');
        if (nfceHab) nfceHab.checked = empresa.nfce_habilitado === true || empresa.nfce_habilitado === 'true';
        setValue('nfce_csc_id', empresa.nfce_csc_id || '');
        setValue('nfce_csc_token', ''); // Nunca preencher token (segurança); backend mantém o salvo na edição
        this.empresaNfceCscTokenConfigurado = empresa.nfce_csc_token_configurado === true;
        setValue('ativo', empresa.ativo === true || empresa.ativo === 'true' ? 'true' : 'false');
        setValue('modo_recebimento', empresa.modo_recebimento || 'plataforma');
        setValue('gateway_plataforma', empresa.gateway_plataforma || 'mercadopago');
        setValue('taxa_plataforma_percentual', empresa.taxa_plataforma_percentual != null ? String(empresa.taxa_plataforma_percentual) : '');
        setValue('taxa_plataforma_valor_fixo', empresa.taxa_plataforma_valor_fixo != null ? String(empresa.taxa_plataforma_valor_fixo) : '');
        this._toggleTaxaFields();
        this._toggleGatewayPlataforma();
    }

    _toggleTaxaFields() {
        const modo = document.getElementById('modo_recebimento');
        const blocoP = document.getElementById('bloco_taxa_percentual');
        const blocoF = document.getElementById('bloco_taxa_fixa');
        if (!modo || !blocoP || !blocoF) return;
        const show = modo.value === 'plataforma';
        blocoP.style.display = show ? '' : 'none';
        blocoF.style.display = show ? '' : 'none';
    }

    _toggleGatewayPlataforma() {
        const modo = document.getElementById('modo_recebimento');
        const bloco = document.getElementById('bloco_gateway_plataforma');
        if (!modo || !bloco) return;
        bloco.style.display = modo.value === 'plataforma' ? '' : 'none';
    }
    
    atualizarPreviewLogo(url) {
        const container = document.getElementById('logo_preview_container');
        const img = document.getElementById('logo_preview');
        if (!container || !img) return;
        const u = (url || '').trim();
        if (!u) {
            img.src = '';
            container.style.display = 'none';
            return;
        }
        // Rejeitar valores que não são URLs de imagem (ex: email digitado por engano)
        const isEmail = u.includes('@') && !u.startsWith('http') && !u.startsWith('data:');
        const isValidUrl = u.startsWith('http://') || u.startsWith('https://') ||
            u.startsWith('/') || u.startsWith('data:') || u.startsWith('./');
        if (isEmail || !isValidUrl) {
            img.src = '';
            container.style.display = 'none';
            return;
        }
        container.style.display = 'none';
        img.onerror = () => { container.style.display = 'none'; };
        img.onload = () => { container.style.display = 'block'; };
        img.src = u;
    }

    /** Mostra ou esconde o botão "Visualizar logo" no modal e define o href (só para logo já salvo no servidor). */
    atualizarBotaoVisualizarLogo(logoUrl) {
        const wrap = document.getElementById('logo_visualizar_wrap');
        const btn = document.getElementById('btn_visualizar_logo');
        if (!wrap || !btn) return;
        const u = (logoUrl || '').trim();
        const isServerUrl = u && (u.startsWith('/') || u.startsWith('http://') || u.startsWith('https://'));
        if (isServerUrl) {
            wrap.style.display = 'block';
            btn.href = u.startsWith('http') ? u : (window.location.origin + (u.startsWith('/') ? u : '/' + u));
        } else {
            wrap.style.display = 'none';
            btn.href = '#';
        }
    }

    async converterArquivoParaBase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => {
                // Remover o prefixo "data:application/x-pkcs12;base64," ou similar
                const base64 = reader.result.split(',')[1] || reader.result;
                resolve(base64);
            };
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    }

    /** Retorna o arquivo como data URL (ex: data:image/png;base64,...) para o backend detectar o tipo da imagem. */
    async converterArquivoParaDataURL(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result);
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    }
    
    limparFormulario() {
        const form = document.getElementById('formEmpresa');
        if (form) {
            form.reset();
        }
        
        this.empresaEmEdicao = null;
        this.empresaNfceCscTokenConfigurado = false;
        this.certificadoArquivo = null;
        this.logoArquivo = null;
        
        const logoFile = document.getElementById('logo_file');
        if (logoFile) {
            logoFile.value = '';
        }
        
        const empresaId = document.getElementById('empresa_id');
        if (empresaId) {
            empresaId.value = '';
        }
        
        const certificadoFile = document.getElementById('certificado_file');
        if (certificadoFile) {
            certificadoFile.value = '';
        }
        
        const nomeArquivoDiv = document.getElementById('certificado_nome_arquivo');
        if (nomeArquivoDiv) {
            nomeArquivoDiv.style.display = 'none';
        }
        this.atualizarBotaoVisualizarLogo('');
        const titulo = document.getElementById('modalEmpresaTitulo');
        if (titulo) {
            titulo.textContent = 'Nova Empresa Fiscal';
        }
    }
    
    excluirEmpresa(id) {
        this.empresaEmEdicao = id;
        abrirModalConfirmacao();
    }
    
    async confirmarExclusao() {
        try {
            if (!this.empresaEmEdicao) {
                throw new Error('ID da empresa não fornecido para exclusão');
            }
            
            const token = this.getToken();
            const headers = {};
            if (token) headers['Authorization'] = `Bearer ${token}`;
            const response = await fetch(`/api/v1/fiscal/empresa/${this.empresaEmEdicao}`, {
                method: 'DELETE',
                headers,
                credentials: 'include'
            });
            
            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.detail || 'Erro ao excluir empresa');
            }
            
            this.mostrarAlerta('Empresa excluída com sucesso!', 'success');
            
            if (typeof fecharModalConfirmacao === 'function') {
                fecharModalConfirmacao();
            }
            
            this.empresaEmEdicao = null;
            this.carregarEmpresas();
            
        } catch (error) {
            this.mostrarAlerta(error.message || 'Erro ao excluir empresa', 'danger');
        }
    }
    
    getToken() {
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
        if (window.alertSystem) {
            window.alertSystem.show(mensagem, tipo);
        } else {
            const alertDiv = document.createElement('div');
            alertDiv.className = `alert alert-${tipo} alert-dismissible fade show`;
            alertDiv.innerHTML = `
                ${mensagem}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            
            let alertContainer = document.getElementById('alert-container');
            if (alertContainer) {
                alertContainer.appendChild(alertDiv);
            } else {
                document.body.appendChild(alertDiv);
            }
            
            setTimeout(() => {
                if (alertDiv.parentNode) {
                    alertDiv.remove();
                }
            }, 5000);
        }
    }
}

// Inicializar quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', function() {
    window.empresaFiscalManager = new EmpresaFiscalManager();
});

