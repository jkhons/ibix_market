/**
 * CertificadosAuxiliaresCadastroManager - Gerenciador de Cadastro/Edição Unificado
 * Gerencia formulário dinâmico baseado em categoria
 */

class CertificadosAuxiliaresCadastroManager {
    constructor() {
        this.cadastroId = null;
        this.categoriaAtual = null;
        this.responsaveis = [];
        this.categorias = [];
        this.manager = new CertificadosAuxiliaresUnificadoManager();
        
        this.init();
    }
    
    async init() {
        // Verificar se é edição
        const cadastroIdInput = document.getElementById('cadastro_id');
        if (cadastroIdInput && cadastroIdInput.value) {
            this.cadastroId = parseInt(cadastroIdInput.value);
        }
        
        // Configurar eventos
        this.configurarEventos();
        
        // Carregar dados iniciais
        await this.carregarCategorias();
        await this.carregarResponsaveis();
        
        // Se for edição, carregar dados
        if (this.cadastroId) {
            await this.carregarCadastro(this.cadastroId);
        }
    }
    
    configurarEventos() {
        // Mudança de categoria
        const categoriaSelect = document.getElementById('categoria_codigo');
        if (categoriaSelect) {
            categoriaSelect.addEventListener('change', () => this.onCategoriaChange());
        }
        
        // Botão para nova categoria
        const btnNovaCategoria = document.getElementById('btnNovaCategoria');
        if (btnNovaCategoria) {
            btnNovaCategoria.addEventListener('click', () => this.abrirModalNovaCategoria());
        }
        
        // Submit do formulário de categoria
        const formNovaCategoria = document.getElementById('formNovaCategoria');
        if (formNovaCategoria) {
            formNovaCategoria.addEventListener('submit', (e) => this.salvarCategoria(e));
        }
        
        // Submit do formulário principal
        const form = document.getElementById('formCertificadoAuxiliar');
        if (form) {
            form.addEventListener('submit', (e) => this.salvarCadastro(e));
        }
    }
    
    onCategoriaChange() {
        const categoriaSelect = document.getElementById('categoria_codigo');
        if (!categoriaSelect) return;
        
        const categoria = categoriaSelect.value;
        this.categoriaAtual = categoria;
        
        // Mostrar/ocultar campos específicos
        this.renderizarCamposCategoria(categoria);
    }
    
    renderizarCamposCategoria(categoria) {
        // Ocultar todos os campos específicos
        document.getElementById('camposEquipamento')?.classList.remove('active');
        document.getElementById('camposPeso')?.classList.remove('active');
        document.getElementById('camposPesoPadrao')?.classList.remove('active');
        document.getElementById('camposInspetor')?.classList.remove('active');
        document.getElementById('uploadPdf')?.classList.remove('active');
        document.getElementById('uploadAssinatura')?.classList.remove('active');
        document.getElementById('uploadCertDigital')?.classList.remove('active');
        
        // Mostrar campos conforme categoria
        // PESO: apenas valor nominal, unidade, classe (sem carga/sobrecarga)
        if (categoria === 'PESO') {
            document.getElementById('camposEquipamento')?.classList.add('active');
            document.getElementById('camposRastreabilidade')?.classList.remove('oculto');
            document.getElementById('camposPeso')?.classList.add('active');
            document.getElementById('uploadPdf')?.classList.add('active');
            const valorNominal = document.getElementById('valor_nominal');
            const unidade = document.getElementById('unidade');
            if (valorNominal) valorNominal.required = true;
            if (unidade) unidade.required = true;
        }
        // PESOPADRAO: valor nominal, unidade, classe + carga e sobrecarga
        else if (categoria === 'PESOPADRAO') {
            document.getElementById('camposEquipamento')?.classList.add('active');
            document.getElementById('camposRastreabilidade')?.classList.remove('oculto');
            document.getElementById('camposPeso')?.classList.add('active');
            document.getElementById('camposPesoPadrao')?.classList.add('active');
            document.getElementById('uploadPdf')?.classList.add('active');
            const valorNominal = document.getElementById('valor_nominal');
            const unidade = document.getElementById('unidade');
            if (valorNominal) valorNominal.required = true;
            if (unidade) unidade.required = true;
        } else if (categoria === 'INSPETOR_APROVADOR') {
            document.getElementById('camposRastreabilidade')?.classList.add('oculto');
            document.getElementById('camposInspetor')?.classList.add('active');
            document.getElementById('uploadAssinatura')?.classList.add('active');
            document.getElementById('uploadCertDigital')?.classList.add('active');
            
            // Tornar campos obrigatórios
            const cpf = document.getElementById('cpf');
            const email = document.getElementById('email');
            const cargo = document.getElementById('cargo');
            const tipo = document.getElementById('tipo');
            if (cpf) cpf.required = true;
            if (email) email.required = true;
            if (cargo) cargo.required = true;
            if (tipo) tipo.required = true;
            
            // Ocultar certificado_numero (não aplica para INSPETOR)
            const certificadoNumero = document.getElementById('certificado_numero');
            if (certificadoNumero) {
                certificadoNumero.disabled = true;
                certificadoNumero.value = '';
            }
            
        } else if (categoria === 'TERMOBAROHIGROMETRO') {
            document.getElementById('camposEquipamento')?.classList.add('active');
            document.getElementById('camposRastreabilidade')?.classList.remove('oculto');
            document.getElementById('uploadPdf')?.classList.add('active');
            
            // Remover required dos campos de outras categorias
            const valorNominal = document.getElementById('valor_nominal');
            const unidade = document.getElementById('unidade');
            const cpf = document.getElementById('cpf');
            const email = document.getElementById('email');
            const cargo = document.getElementById('cargo');
            const tipo = document.getElementById('tipo');
            if (valorNominal) valorNominal.required = false;
            if (unidade) unidade.required = false;
            if (cpf) cpf.required = false;
            if (email) email.required = false;
            if (cargo) cargo.required = false;
            if (tipo) tipo.required = false;
            
            // Habilitar certificado_numero
            const certificadoNumero = document.getElementById('certificado_numero');
            if (certificadoNumero) certificadoNumero.disabled = false;
        }
        
        // Reinicializar feather icons
        if (typeof feather !== 'undefined') {
            feather.replace();
        }
    }
    
    async carregarResponsaveis() {
        try {
            const token = this.manager.getToken();
            if (!token) return;
            
            const response = await fetch('/api/v1/usuarios?ativo=true&limit=100', {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                this.responsaveis = data.usuarios || data.items || [];
                this.renderizarResponsaveis();
            }
        } catch (error) {
            console.error('Erro ao carregar responsáveis:', error);
        }
    }
    
    renderizarResponsaveis() {
        const select = document.getElementById('responsavel_id');
        if (!select) return;
        
        let html = '<option value="">Selecione...</option>';
        this.responsaveis.forEach(usuario => {
            html += `<option value="${usuario.id}">${usuario.nome || usuario.email}</option>`;
        });
        select.innerHTML = html;
    }
    
    async carregarCategorias() {
        try {
            const token = this.manager.getToken();
            if (!token) {
                console.error('Token não encontrado');
                return;
            }
            
            const response = await fetch('/api/v1/aux-cadastros/categorias?ativo=true', {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                this.categorias = data || [];
                this.renderizarCategorias();
            } else {
                console.error('Erro ao carregar categorias:', response.statusText);
                this.renderizarCategorias(); // Renderizar mesmo se falhar (vazio)
            }
        } catch (error) {
            console.error('Erro ao carregar categorias:', error);
            this.renderizarCategorias(); // Renderizar mesmo se falhar (vazio)
        }
    }
    
    renderizarCategorias() {
        const select = document.getElementById('categoria_codigo');
        if (!select) return;
        
        let html = '<option value="">Selecione a categoria...</option>';
        
        if (this.categorias.length === 0) {
            html = '<option value="">Nenhuma categoria disponível</option>';
        } else {
            this.categorias.forEach(categoria => {
                html += `<option value="${categoria.codigo}">${categoria.nome}</option>`;
            });
        }
        
        select.innerHTML = html;
        
        // Se já havia uma categoria selecionada (em edição), restaurar
        if (this.categoriaAtual) {
            select.value = this.categoriaAtual;
        }
    }
    
    abrirModalNovaCategoria() {
        const modal = new bootstrap.Modal(document.getElementById('modalNovaCategoria'));
        
        // Limpar formulário
        document.getElementById('formNovaCategoria').reset();
        const ativoCheckbox = document.getElementById('categoriaAtivo');
        if (ativoCheckbox) {
            ativoCheckbox.checked = true;
        }
        
        // Converter código para maiúsculas automaticamente
        const codigoInput = document.getElementById('categoriaCodigo');
        if (codigoInput) {
            codigoInput.addEventListener('input', function() {
                this.value = this.value.toUpperCase().replace(/[^A-Z0-9_]/g, '');
            });
        }
        
        modal.show();
        
        // Reinicializar feather icons
        if (typeof feather !== 'undefined') {
            feather.replace();
        }
    }
    
    async salvarCategoria(e) {
        e.preventDefault();
        
        try {
            const token = this.manager.getToken();
            if (!token) {
                throw new Error('Token não encontrado');
            }
            
            const dados = {
                codigo: document.getElementById('categoriaCodigo').value.toUpperCase().trim(),
                nome: document.getElementById('categoriaNome').value.trim(),
                ativo: document.getElementById('categoriaAtivo').checked
            };
            
            if (!dados.codigo || !dados.nome) {
                throw new Error('Preencha código e nome da categoria');
            }
            
            const response = await fetch('/api/v1/aux-cadastros/categorias', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(dados)
            });
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: response.statusText }));
                throw new Error(errorData.detail || `HTTP ${response.status}`);
            }
            
            const novaCategoria = await response.json();
            
            // Adicionar à lista local
            this.categorias.push(novaCategoria);
            
            // Atualizar select
            this.renderizarCategorias();
            
            // Selecionar a nova categoria
            const select = document.getElementById('categoria_codigo');
            if (select) {
                select.value = novaCategoria.codigo;
                this.onCategoriaChange();
            }
            
            // Fechar modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('modalNovaCategoria'));
            modal.hide();
            
            alert('✅ Categoria cadastrada com sucesso!');
            
        } catch (error) {
            let mensagem = 'Erro ao salvar categoria: ' + error.message;
            
            if (error.message.includes('409') || error.message.includes('Conflict') || error.message.includes('já existe')) {
                mensagem = '❌ Categoria com este código já existe. Escolha outro código.';
            }
            
            alert(mensagem);
            console.error('Erro ao salvar categoria:', error);
        }
    }
    
    async carregarCadastro(id) {
        try {
            const cadastro = await this.manager.obterCadastro(id);
            this.preencherFormulario(cadastro);
        } catch (error) {
            alert('Erro ao carregar cadastro: ' + error.message);
            window.location.href = '/certificados-auxiliares';
        }
    }
    
    preencherFormulario(cadastro) {
        // Categoria (desabilitada em edição)
        const categoriaSelect = document.getElementById('categoria_codigo');
        if (categoriaSelect && cadastro.categoria) {
            categoriaSelect.value = cadastro.categoria.codigo;
            this.categoriaAtual = cadastro.categoria.codigo;
            this.onCategoriaChange();
        }
        
        // Campos comuns
        if (document.getElementById('nome_titulo')) document.getElementById('nome_titulo').value = cadastro.nome_titulo || '';
        if (document.getElementById('identificador')) document.getElementById('identificador').value = cadastro.identificador || '';
        if (document.getElementById('fabricante')) document.getElementById('fabricante').value = cadastro.fabricante || '';
        if (document.getElementById('modelo')) document.getElementById('modelo').value = cadastro.modelo || '';
        if (document.getElementById('numero_serie')) document.getElementById('numero_serie').value = cadastro.numero_serie || '';
        if (document.getElementById('certificado_numero')) document.getElementById('certificado_numero').value = cadastro.certificado_numero || '';
        if (document.getElementById('laboratorio_calibrador')) document.getElementById('laboratorio_calibrador').value = cadastro.laboratorio_calibrador || '';
        if (document.getElementById('acreditado_por')) document.getElementById('acreditado_por').value = cadastro.acreditado_por || '';
        if (document.getElementById('data_calibracao')) document.getElementById('data_calibracao').value = cadastro.data_calibracao || '';
        if (document.getElementById('data_validade')) document.getElementById('data_validade').value = cadastro.data_validade || '';
        if (document.getElementById('status_equipamento')) document.getElementById('status_equipamento').value = cadastro.status_equipamento || '';
        if (document.getElementById('proxima_calibracao')) document.getElementById('proxima_calibracao').value = cadastro.proxima_calibracao || '';
        if (document.getElementById('responsavel_id')) document.getElementById('responsavel_id').value = cadastro.responsavel_id || '';
        if (document.getElementById('ativo')) document.getElementById('ativo').value = cadastro.ativo ? 'true' : 'false';
        
        // Campos específicos por categoria
        const atributos = cadastro.atributos_json || {};
        
        if (cadastro.categoria?.codigo === 'PESO') {
            if (document.getElementById('valor_nominal')) document.getElementById('valor_nominal').value = atributos.valor_nominal || '';
            if (document.getElementById('unidade')) document.getElementById('unidade').value = atributos.unidade || '';
            if (document.getElementById('classe')) document.getElementById('classe').value = atributos.classe || '';
        } else if (cadastro.categoria?.codigo === 'PESOPADRAO') {
            if (document.getElementById('valor_nominal')) document.getElementById('valor_nominal').value = atributos.valor_nominal ?? '';
            if (document.getElementById('unidade')) document.getElementById('unidade').value = atributos.unidade || '';
            if (document.getElementById('classe')) document.getElementById('classe').value = atributos.classe || '';
            if (document.getElementById('carga_kg')) document.getElementById('carga_kg').value = atributos.carga_kg ?? '';
            if (document.getElementById('sobrecarga_kg')) document.getElementById('sobrecarga_kg').value = atributos.sobrecarga_kg ?? '';
        } else if (cadastro.categoria?.codigo === 'INSPETOR_APROVADOR') {
            if (document.getElementById('cpf')) document.getElementById('cpf').value = atributos.cpf || '';
            if (document.getElementById('email')) document.getElementById('email').value = atributos.email || '';
            if (document.getElementById('cargo')) document.getElementById('cargo').value = atributos.cargo || '';
            if (document.getElementById('tipo')) document.getElementById('tipo').value = atributos.tipo || '';
            if (document.getElementById('registro_profissional')) document.getElementById('registro_profissional').value = atributos.registro_profissional || '';
            if (document.getElementById('orgao_registro')) document.getElementById('orgao_registro').value = atributos.orgao_registro || '';
            if (document.getElementById('data_credenciamento')) document.getElementById('data_credenciamento').value = atributos.data_credenciamento || '';
            if (document.getElementById('data_validade_credenciamento')) document.getElementById('data_validade_credenciamento').value = atributos.data_validade_credenciamento || '';
        }
    }
    
    async salvarCadastro(e) {
        e.preventDefault();
        
        try {
            const formData = await this.coletarDadosFormulario();
            
            // Validar dados
            this.validarFormulario(formData);
            
            // Salvar cadastro
            let cadastro;
            if (this.cadastroId) {
                cadastro = await this.manager.atualizarCadastro(this.cadastroId, formData);
            } else {
                cadastro = await this.manager.criarCadastro(formData);
                this.cadastroId = cadastro.id;
            }
            
            // Upload de arquivos
            try {
                await this.uploadArquivos(cadastro.id);
            } catch (uploadError) {
                console.warn('Aviso ao fazer upload de arquivos:', uploadError);
                // Continuar mesmo se upload falhar (arquivos podem ser adicionados depois)
            }
            
            alert('✅ Certificado salvo com sucesso!');
            window.location.href = '/certificados-auxiliares';
            
        } catch (error) {
            // Tratar erros específicos de unicidade
            let mensagem = 'Erro ao salvar: ' + error.message;
            
            if (error.message.includes('409') || error.message.includes('Conflict') || error.message.includes('já existe')) {
                mensagem = '❌ Este certificado já existe no sistema. Verifique o identificador ou número do certificado.';
            } else if (error.message.includes('CPF') || error.message.includes('email')) {
                mensagem = '❌ CPF ou email já cadastrado para outro inspetor/aprovador.';
            } else if (error.message.includes('identificador')) {
                mensagem = '❌ Este identificador já está em uso nesta categoria.';
            }
            
            alert(mensagem);
            console.error('Erro ao salvar:', error);
        }
    }
    
    async coletarDadosFormulario() {
        const categoriaCodigo = document.getElementById('categoria_codigo').value;
        if (!categoriaCodigo) {
            throw new Error('Selecione uma categoria');
        }
        
        // Buscar categoria_id a partir do código
        const categoriaId = await this.obterCategoriaId(categoriaCodigo);
        if (!categoriaId) {
            throw new Error('Categoria não encontrada');
        }
        
        const dados = {
            categoria_id: categoriaId,
            categoria_codigo: categoriaCodigo,
            nome_titulo: document.getElementById('nome_titulo').value,
            identificador: document.getElementById('identificador').value,
            fabricante: document.getElementById('fabricante').value || null,
            modelo: document.getElementById('modelo').value || null,
            numero_serie: document.getElementById('numero_serie').value || null,
            certificado_numero: document.getElementById('certificado_numero').value || null,
            laboratorio_calibrador: document.getElementById('laboratorio_calibrador')?.value || null,
            acreditado_por: document.getElementById('acreditado_por')?.value || null,
            data_calibracao: document.getElementById('data_calibracao').value || null,
            data_validade: document.getElementById('data_validade').value || null,
            status_equipamento: document.getElementById('status_equipamento')?.value || null,
            proxima_calibracao: document.getElementById('proxima_calibracao')?.value || null,
            responsavel_id: document.getElementById('responsavel_id').value ? parseInt(document.getElementById('responsavel_id').value) : null,
            ativo: document.getElementById('ativo').value === 'true',
            atributos_json: {}
        };
        
        // Campos específicos por categoria
        if (categoriaCodigo === 'PESO') {
            dados.atributos_json = {
                valor_nominal: document.getElementById('valor_nominal').value || null,
                unidade: document.getElementById('unidade').value || null,
                classe: document.getElementById('classe').value || null
            };
        } else if (categoriaCodigo === 'PESOPADRAO') {
            const valorNominalInput = document.getElementById('valor_nominal').value;
            const valorNominal = valorNominalInput ? parseFloat(valorNominalInput) : null;
            const cargaKgInput = document.getElementById('carga_kg')?.value;
            const sobrecargaKgInput = document.getElementById('sobrecarga_kg')?.value;
            const cargaKg = cargaKgInput ? parseFloat(cargaKgInput) : null;
            const sobrecargaKg = sobrecargaKgInput ? parseFloat(sobrecargaKgInput) : null;
            dados.atributos_json = {
                valor_nominal: valorNominal,
                unidade: document.getElementById('unidade').value || null,
                classe: document.getElementById('classe').value || null,
                carga_kg: cargaKg,
                sobrecarga_kg: sobrecargaKg
            };
        } else if (categoriaCodigo === 'INSPETOR_APROVADOR') {
            dados.atributos_json = {
                cpf: document.getElementById('cpf').value || null,
                email: document.getElementById('email').value || null,
                cargo: document.getElementById('cargo').value || null,
                tipo: document.getElementById('tipo').value || null,
                registro_profissional: document.getElementById('registro_profissional').value || null,
                orgao_registro: document.getElementById('orgao_registro').value || null,
                data_credenciamento: document.getElementById('data_credenciamento').value || null,
                data_validade_credenciamento: document.getElementById('data_validade_credenciamento').value || null
            };
        }
        
        return dados;
    }
    
    validarFormulario(dados) {
        if (!dados.categoria_codigo) {
            throw new Error('Selecione uma categoria');
        }
        
        if (!dados.nome_titulo || !dados.identificador) {
            throw new Error('Preencha nome/título e identificador');
        }
        
        // Validações específicas por categoria
        if (dados.categoria_codigo === 'PESO') {
            if (!dados.atributos_json.valor_nominal || !dados.atributos_json.unidade) {
                throw new Error('Preencha valor nominal e unidade para peso');
            }
        } else if (dados.categoria_codigo === 'PESOPADRAO') {
            if (!dados.atributos_json.valor_nominal || !dados.atributos_json.unidade) {
                throw new Error('Preencha valor nominal e unidade para peso padrão');
            }
        } else if (dados.categoria_codigo === 'INSPETOR_APROVADOR') {
            if (!dados.atributos_json.cpf || !dados.atributos_json.email || !dados.atributos_json.cargo || !dados.atributos_json.tipo) {
                throw new Error('Preencha CPF, email, cargo e tipo para inspetor/aprovador');
            }
        }
    }
    
    async uploadArquivos(cadastroId) {
        const categoriaCodigo = this.categoriaAtual || document.getElementById('categoria_codigo').value;
        
        // Upload PDF (TERMOBAROHIGROMETRO, PESO, PESOPADRAO)
        if (categoriaCodigo === 'TERMOBAROHIGROMETRO' || categoriaCodigo === 'PESO' || categoriaCodigo === 'PESOPADRAO') {
            const arquivoPdf = document.getElementById('arquivo_pdf');
            if (arquivoPdf && arquivoPdf.files.length > 0) {
                await this.uploadArquivo(cadastroId, arquivoPdf.files[0], 'pdf_certificado', true);
            }
        }
        
        // Upload Assinatura (INSPETOR)
        if (categoriaCodigo === 'INSPETOR_APROVADOR') {
            const arquivoAssinatura = document.getElementById('arquivo_assinatura');
            if (arquivoAssinatura && arquivoAssinatura.files.length > 0) {
                await this.uploadArquivo(cadastroId, arquivoAssinatura.files[0], 'assinatura', true);
            }
            
            const arquivoCertDigital = document.getElementById('arquivo_cert_digital');
            if (arquivoCertDigital && arquivoCertDigital.files.length > 0) {
                await this.uploadArquivo(cadastroId, arquivoCertDigital.files[0], 'cert_digital', true);
            }
        }
    }
    
    async obterCategoriaId(codigo) {
        try {
            // Primeiro, tentar buscar da lista local já carregada
            const categoriaLocal = this.categorias.find(cat => cat.codigo === codigo);
            if (categoriaLocal) {
                return categoriaLocal.id;
            }
            
            const token = this.manager.getToken();
            if (!token) {
                throw new Error('Token não encontrado');
            }
            
            // Buscar categoria via endpoint
            const response = await fetch(`/api/v1/aux-cadastros/categorias/${codigo}`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                // Adicionar à lista local para cache
                if (!this.categorias.find(cat => cat.id === data.id)) {
                    this.categorias.push(data);
                }
                return data.id;
            }
            
            throw new Error(`Categoria '${codigo}' não encontrada`);
            
        } catch (error) {
            console.error('Erro ao obter categoria_id:', error);
            throw new Error(`Não foi possível obter ID da categoria '${codigo}': ${error.message}`);
        }
    }
    
    async uploadArquivo(cadastroId, arquivo, tipoArquivo, principal = false) {
        try {
            const token = this.manager.getToken();
            if (!token) {
                throw new Error('Token não encontrado');
            }
            
            const formData = new FormData();
            formData.append('file', arquivo);
            
            // tipo_arquivo e principal são query params
            const params = new URLSearchParams();
            params.append('tipo_arquivo', tipoArquivo);
            params.append('principal', principal.toString());
            
            const response = await fetch(`/api/v1/aux-cadastros/${cadastroId}/arquivos?${params.toString()}`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`
                },
                body: formData
            });
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: response.statusText }));
                throw new Error(errorData.detail || `HTTP ${response.status}`);
            }
            
            return await response.json();
            
        } catch (error) {
            console.error('Erro ao fazer upload:', error);
            throw error;
        }
    }
}

// Exportar para uso global
window.CertificadosAuxiliaresCadastroManager = CertificadosAuxiliaresCadastroManager;
