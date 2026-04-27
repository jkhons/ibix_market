// PDV Ibix - Certificados JavaScript (Modularizado)
// Importar módulos
import { Logger } from './certificados/core/logger.js';
import { requestCache } from './certificados/core/cache.js';
import { formatarData, calcularStatus, calcularDataValidade, getToken, mostrarAlerta, getCookie, getTokenFromCookieForTermo } from './certificados/utils/helpers.js';
import { setupGlobalFunctions } from './certificados/utils/globals.js';
import { carregarClientes as apiCarregarClientes, preencherSelectClientes as apiPreencherSelectClientes, criarAutocompleteCliente as apiCriarAutocompleteCliente } from './certificados/api/clientes.js';
import { carregarEquipamentos as apiCarregarEquipamentos, preencherSelectEquipamentos as apiPreencherSelectEquipamentos, carregarDadosEquipamento as apiCarregarDadosEquipamento } from './certificados/api/equipamentos.js';
import { carregarEstatisticas as apiCarregarEstatisticas, atualizarEstatisticas as apiAtualizarEstatisticas } from './certificados/api/estatisticas.js';
import { renderizarTabela as uiRenderizarTabela } from './certificados/ui/tabela.js';
import { gerarPaginacao as uiGerarPaginacao, atualizarInfoPagina as uiAtualizarInfoPagina } from './certificados/ui/paginacao.js';
import { aplicarFiltros as uiAplicarFiltros, limparFiltros as uiLimparFiltros } from './certificados/ui/filtros.js';
import { carregarPesosPadrao as featCarregarPesosPadrao, adicionarPesoPadrao as featAdicionarPesoPadrao, selecionarPesoPadrao as featSelecionarPesoPadrao, removerPesoPadrao as featRemoverPesoPadrao, coletarPesosPadrao as featColetarPesosPadrao, limparPesosPadrao as featLimparPesosPadrao } from './certificados/features/pesos-padrao.js';
import { carregarTermobarohigrometros as featCarregarTermobarohigrometros, preencherDadosTermobarohigrometro as featPreencherDadosTermobarohigrometro } from './certificados/features/termobarohigrometros.js';
import { carregarInspetoresAprovadores as featCarregarInspetoresAprovadores, preencherDadosInspetor as featPreencherDadosInspetor } from './certificados/features/inspetores.js';
import { carregarEnsaiosExcentricidade as featCarregarEnsaiosExcentricidade, coletarEnsaiosExcentricidade as featColetarEnsaiosExcentricidade, salvarEnsaiosExcentricidade as featSalvarEnsaiosExcentricidade, adicionarLinhaExcentricidade as featAdicionarLinhaExcentricidade, removerLinhaExcentricidade as featRemoverLinhaExcentricidade } from './certificados/features/ensaios-excentricidade.js';
import { carregarResultadosEnsaios as featCarregarResultadosEnsaios, coletarResultadosEnsaios as featColetarResultadosEnsaios, salvarResultadosEnsaios as featSalvarResultadosEnsaios, adicionarLinhaResultado as featAdicionarLinhaResultado, removerLinhaResultado as featRemoverLinhaResultado } from './certificados/features/ensaios-resultados.js';
import { carregarEnsaiosMobilidade as featCarregarEnsaiosMobilidade, coletarEnsaiosMobilidade as featColetarEnsaiosMobilidade, salvarEnsaiosMobilidade as featSalvarEnsaiosMobilidade } from './certificados/features/ensaios-mobilidade.js';

class CertificadosManager {
    constructor() {
        // Inicializar logger
        this.logger = new Logger();
        this.debugMode = this.logger.debugMode;
        this.logLevel = this.logger.logLevel;
        
        this.currentPage = 1;
        this.itemsPerPage = 10;
        this.currentFilters = {};
        this.certificadoEmEdicao = null;
        this.pesosPadrao = []; // Array para armazenar os pesos padrão disponíveis
        this.pesosSelecionados = []; // Array para armazenar os pesos selecionados no certificado
        this.proximoIdPeso = 1; // Contador para IDs únicos dos pesos
        this.certificadoParaExcluir = null;
        
        this.init();
    }
    
    // Delegar métodos de logging para o logger
    initLogging() {
        // Já inicializado no construtor via Logger
    }
    
    getCookie(name) {
        return getCookie(name);
    }
    
    log(level, message, data = null) {
        return this.logger.log(level, message, data);
    }
    
    logApiCall(endpoint, status, responseTime = null) {
        return this.logger.logApiCall(endpoint, status, responseTime);
    }
    
    sanitizeData(data) {
        return this.logger.sanitizeData(data);
    }
    
    async withTiming(operation, description) {
        return this.logger.withTiming(operation, description);
    }
    
    init() {
        this.setupEventListeners();
        
        // Detectar se está na página de edição ou listagem
        const isEdicaoPage = window.location.pathname.includes('/editar/');
        const isListagemPage = window.location.pathname === '/certificados';
        
        // Aguardar um pouco para garantir que a página carregue
        setTimeout(() => {
            // Carregar apenas na página de listagem
            if (isListagemPage) {
                const urlParams = new URLSearchParams(window.location.search);
                if (urlParams.get('origem_calibracao') === '1' || urlParams.get('origem_calibracao') === 'true') {
                    const filtroOrigem = document.getElementById('filtroOrigem');
                    if (filtroOrigem) filtroOrigem.value = 'calibracao';
                    this.currentFilters.origem_calibracao = true;
                }
                if (urlParams.get('processo_id')) {
                    this.currentFilters.processo_id = urlParams.get('processo_id');
                }
                if (!window.USER_IS_CLIENTE) {
                    this.carregarClientes();
                }
                this.carregarEquipamentos();
                this.carregarCertificados();
                this.carregarEstatisticas();
            this.carregarPesosPadrao();
                // Autocomplete já é inicializado no setupEventListeners
            } else if (!isEdicaoPage) {
                // Página de novo certificado - carregar dados necessários
                this.carregarClientes();
                this.carregarEquipamentos();
                this.carregarPesosPadrao();
            } else if (isEdicaoPage) {
                // Página de edição - carregar pesos padrão antecipadamente para que o select funcione
                this.carregarPesosPadrao();
            }
            // Na página de edição, os dados do certificado serão carregados por carregarCertificadoParaEdicao
        }, 100);
    }
    
    setupEventListeners() {
        
        // Formulário de certificado
        const formCertificado = document.getElementById('formCertificado');
        if (formCertificado) {
            formCertificado.addEventListener('submit', (e) => {
                e.preventDefault();
                this.salvarCertificado();
            });
        }
        
        // Modal de confirmação
        const btnConfirmarExclusao = document.getElementById('btnConfirmarExclusao');
        if (btnConfirmarExclusao) {
            btnConfirmarExclusao.addEventListener('click', () => {
                this.confirmarExclusao();
            });
        }
        
        // Evento para restaurar scroll quando modal de confirmação for fechado
        const modalConfirmacao = document.getElementById('modalConfirmacao');
        if (modalConfirmacao) {
            modalConfirmacao.addEventListener('hidden.bs.modal', () => {
                // Limpar referência
                this.certificadoParaExcluir = null;
            });
        }
        
        // Evento para limpar formulário quando o modal de certificado for aberto
        const modalCertificado = document.getElementById('modalCertificado');
        if (modalCertificado) {
            modalCertificado.addEventListener('show.bs.modal', () => {
                // Só limpar se não estiver editando um certificado existente
                if (!this.certificadoEmEdicao) {
                    this.limparFormulario();
                }
                // Inicializar autocomplete de clientes no modal
                this.inicializarAutocompleteCliente();
                // Carregar termobarohigrometros e inspetores quando modal abrir
                carregarTermobarohigrometros();
                carregarInspetores();
                // Resetar contadores de linhas dinâmicas
                proximoPontoExcentricidade = 1;
                proximoPontoResultado = 2;
            });
            
            // Evento para limpar formulário quando o modal for fechado
            modalCertificado.addEventListener('hidden.bs.modal', () => {
                // Sempre limpar quando o modal for fechado
                this.limparFormulario();
                this.certificadoEmEdicao = null;
                // Resetar contadores
                proximoPontoExcentricidade = 1;
                proximoPontoResultado = 2;
            });
        }
        
        // Filtros
        const filtros = ['filtroNumero', 'filtroNumeroSerie'];
        filtros.forEach(filtroId => {
            const elemento = document.getElementById(filtroId);
            if (elemento) {
                elemento.addEventListener('keypress', (e) => {
                    if (e.key === 'Enter') {
                        this.aplicarFiltros();
                    }
                });
            }
        });
        
        // Evento para select de status
        const filtroStatus = document.getElementById('filtroStatus');
        if (filtroStatus) {
            filtroStatus.addEventListener('change', () => {
                this.aplicarFiltros();
            });
        }
        
        // Inicializar autocomplete para filtro de cliente
        this.inicializarAutocompleteFiltroCliente();
        
        // Datas (data_emissao, data_ajuste, data_validade) vêm somente do backend na emissão/GET certificado; sem inputs no front.
        
        // Evento para botão Cancelar do modal
        const btnCancelar = document.querySelector('#modalCertificado .btn-secondary');
        if (btnCancelar) {
            btnCancelar.addEventListener('click', () => {
                this.limparFormulario();
                this.certificadoEmEdicao = null;
            });
        }
        
        // Evento para botão X (fechar) do modal
        const btnFechar = document.querySelector('#modalCertificado .btn-close');
        if (btnFechar) {
            btnFechar.addEventListener('click', () => {
                this.limparFormulario();
                this.certificadoEmEdicao = null;
            });
        }
    }
    
    async carregarClientes() {
        // Não precisa mais carregar todos os clientes, o autocomplete faz busca incremental
        // Apenas inicializar o autocomplete
        this.inicializarAutocompleteCliente();
    }
    
    inicializarAutocompleteCliente() {
        apiCriarAutocompleteCliente(this.logger);
    }
    
    inicializarAutocompleteFiltroCliente() {
        if (window.USER_IS_CLIENTE) {
            return;
        }
        const inputBusca = document.getElementById('filtroClienteInput');
        const inputHidden = document.getElementById('filtroCliente');
        const dropdown = document.getElementById('filtroClienteAutocompleteDropdown');
        
        if (!inputBusca || !inputHidden || !dropdown) {
            return;
        }
        
        let timeoutId = null;
        let clientesCarregados = [];
        let indiceSelecionado = -1;
        const self = this; // Capturar contexto
        
        // Função para buscar clientes
        const buscarClientes = async (termo) => {
            if (!termo || termo.trim().length < 2) {
                return [];
            }
            
            try {
                const token = self.getToken();
                const params = new URLSearchParams({
                    nome: termo.trim(),
                    por_pagina: 50
                });
                
                const response = await fetch(`/api/v1/clientes/?${params}`, {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });
            
            if (response.ok) {
                const data = await response.json();
                    const clientes = data.clientes || [];
                    return Array.isArray(clientes) ? clientes : [];
                }
                return [];
        } catch (error) {
                self.log('error', 'Erro ao buscar clientes', error);
                return [];
            }
        };
        
        // Função para exibir sugestões
        const exibirSugestoes = (clientes) => {
            clientesCarregados = clientes;
            dropdown.innerHTML = '';
            
            if (clientes.length === 0) {
                const item = document.createElement('div');
                item.className = 'cliente-autocomplete-item';
                item.textContent = 'Nenhum cliente encontrado';
                item.style.padding = '10px';
                item.style.color = '#6c757d';
                dropdown.appendChild(item);
            } else {
                clientes.forEach((cliente, index) => {
                    const item = document.createElement('div');
                    item.className = 'cliente-autocomplete-item';
                    item.dataset.index = index;
                    item.innerHTML = `
                        <strong>${cliente.nome}</strong>
                        ${cliente.cnpj ? `<br><small class="text-muted">CNPJ: ${cliente.cnpj}</small>` : ''}
                    `;
                    
                    item.addEventListener('click', () => selecionarCliente(cliente));
                    item.addEventListener('mouseenter', () => {
                        dropdown.querySelectorAll('.cliente-autocomplete-item').forEach(i => {
                            i.classList.remove('active');
                        });
                        item.classList.add('active');
                        indiceSelecionado = index;
                    });
                    
                    dropdown.appendChild(item);
                });
            }
            
            dropdown.style.display = 'block';
            indiceSelecionado = -1;
        };
        
        // Função para selecionar cliente
        const selecionarCliente = (cliente) => {
            inputBusca.value = cliente.nome;
            inputHidden.value = cliente.id;
            dropdown.style.display = 'none';
            self.log('info', `Cliente selecionado no filtro: ${cliente.nome}`);
            // Aplicar filtros automaticamente
            self.aplicarFiltros();
        };
        
        // Função de busca com debounce
        const buscarClientesDebounce = async (termo) => {
            if (termo.length < 2) {
                dropdown.style.display = 'none';
                inputHidden.value = '';
            return;
        }
        
            dropdown.innerHTML = '<div class="cliente-autocomplete-item" style="padding: 10px; color: #6c757d;">Buscando...</div>';
            dropdown.style.display = 'block';
            
            try {
                const clientes = await buscarClientes(termo);
                exibirSugestoes(clientes);
            } catch (error) {
                self.log('error', 'Erro na busca de clientes', error);
                dropdown.innerHTML = '<div class="cliente-autocomplete-item" style="padding: 10px; color: #dc3545;">Erro ao buscar clientes</div>';
            }
        };
        
        // Event listeners
        inputBusca.addEventListener('input', (e) => {
            const termo = e.target.value;
            
            if (termo.length === 0) {
                inputHidden.value = '';
                dropdown.style.display = 'none';
                // Aplicar filtros quando limpar
                self.aplicarFiltros();
                return;
            }
            
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => {
                buscarClientesDebounce(termo);
            }, 300);
        });
        
        inputBusca.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                if (indiceSelecionado < clientesCarregados.length - 1) {
                    indiceSelecionado++;
                    const items = dropdown.querySelectorAll('.cliente-autocomplete-item');
                    items.forEach((item, idx) => {
                        item.classList.toggle('active', idx === indiceSelecionado);
                    });
                }
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                if (indiceSelecionado > 0) {
                    indiceSelecionado--;
                    const items = dropdown.querySelectorAll('.cliente-autocomplete-item');
                    items.forEach((item, idx) => {
                        item.classList.toggle('active', idx === indiceSelecionado);
                    });
                }
            } else if (e.key === 'Enter') {
                e.preventDefault();
                if (indiceSelecionado >= 0 && clientesCarregados[indiceSelecionado]) {
                    selecionarCliente(clientesCarregados[indiceSelecionado]);
                } else {
                    // Se não houver seleção, aplicar filtros com o texto digitado
                    self.aplicarFiltros();
                }
            } else if (e.key === 'Escape') {
                dropdown.style.display = 'none';
                indiceSelecionado = -1;
            }
        });
        
        // Fechar dropdown ao clicar fora
        document.addEventListener('click', (e) => {
            const wrapper = inputBusca.parentElement;
            if (!wrapper.contains(e.target)) {
                dropdown.style.display = 'none';
            }
        });
        
    }
    
    preencherSelectClientes(clientes) {
        // Mantido para compatibilidade, mas não é mais usado
        apiPreencherSelectClientes(clientes, this.logger);
    }
    
    async carregarEquipamentos() {
        const equipamentos = await apiCarregarEquipamentos(this.logger, this.mostrarAlerta.bind(this));
        if (equipamentos.length > 0) {
            this.preencherSelectEquipamentos(equipamentos);
        }
    }
    
    preencherSelectEquipamentos(equipamentos, clienteId = null) {
        apiPreencherSelectEquipamentos(equipamentos, clienteId, this.logger);
    }
    

    
    async carregarCertificados() {
        try {
            const startTime = performance.now();
            const params = new URLSearchParams();
            params.append('skip', (this.currentPage - 1) * this.itemsPerPage);
            params.append('limit', this.itemsPerPage);
            
            // Adicionar filtros
            if (this.currentFilters.numero) {
                params.append('numero', this.currentFilters.numero);
            }
            if (this.currentFilters.cliente_id) {
                params.append('cliente_id', this.currentFilters.cliente_id);
            }
            if (this.currentFilters.numero_serie) {
                params.append('numero_serie', this.currentFilters.numero_serie);
            }
            if (this.currentFilters.status) {
                params.append('status', this.currentFilters.status);
            }
            if (this.currentFilters.origem_calibracao) {
                params.append('origem_calibracao', 'true');
            }
            if (this.currentFilters.processo_id) {
                params.append('processo_id', this.currentFilters.processo_id);
            }
            
            const url = `/api/v1/certificados/?${params}`;
            const token = this.getToken();
            
            if (!token) {
                this.mostrarAlerta('Erro de autenticação. Por favor, faça login novamente.', 'error');
                return;
            }
            
            const response = await fetch(url, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            const responseTime = performance.now() - startTime;
            
            if (response.ok) {
                let certificados;
                try {
                    certificados = await response.json();
                } catch (jsonError) {
                    try {
                        await response.text();
                    } catch (textError) {
                        // Ignorar erro ao ler texto
                    }
                    this.mostrarAlerta('Erro ao processar resposta da API', 'error');
                    return;
                }
                
                // Verificar se certificados é um array
                if (!Array.isArray(certificados)) {
                    this.mostrarAlerta('Formato de resposta inválido da API', 'error');
                    return;
                }
                
                try {
                    this.renderizarTabela(certificados);
                } catch (renderError) {
                    throw renderError;
                }
                
                try {
                    // Calcular total de páginas e gerar paginação
                    // Obter o total real de certificados para paginação correta
                    const totalCertificados = await this.obterTotalCertificados();
                    const totalPaginas = Math.ceil(totalCertificados / this.itemsPerPage);
                    this.gerarPaginacao(totalPaginas);
                    
                    // Atualizar informações da página com o total real
                    this.atualizarInfoPagina({
                        total: totalCertificados,
                        page: this.currentPage,
                        per_page: this.itemsPerPage
                    });
                } catch (paginacaoError) {
                    throw paginacaoError;
                }
            } else {
                this.logApiCall('/api/v1/certificados/', response.status, responseTime);
                
                // Tentar obter detalhes do erro
                let errorMessage = `Erro ${response.status}: ${response.statusText}`;
                try {
                    const errorText = await response.text();
                    if (errorText) {
                        try {
                            const errorJson = JSON.parse(errorText);
                            errorMessage = errorJson.detail || errorMessage;
                        } catch {
                            errorMessage = errorText.substring(0, 200);
                        }
                    }
                } catch (textError) {
                    // Ignorar erro ao ler texto
                }
                
                this.mostrarAlerta(`Erro ao carregar certificados: ${errorMessage}`, 'error');
            }
        } catch (error) {
            this.mostrarAlerta(`Erro ao carregar certificados: ${error.message || 'Erro desconhecido'}`, 'error');
        }
    }
    
    renderizarTabela(certificados) {
        uiRenderizarTabela(certificados, this.currentPage, this.itemsPerPage);
        // Atualizar informações da página (será atualizado quando obtivermos o total real)
        this.atualizarInfoPagina({
            total: 0, // Será atualizado pelo total real
            page: this.currentPage,
            per_page: this.itemsPerPage
        });
    }
    
    calcularStatus(dataValidade) {
        return calcularStatus(dataValidade);
    }
    
    formatarData(data) {
        return formatarData(data);
    }
    
    atualizarInfoPagina(data) {
        uiAtualizarInfoPagina(data, this.currentPage, this.itemsPerPage);
    }

    gerarPaginacao(totalPaginas) {
        uiGerarPaginacao(totalPaginas, this.currentPage, this.irParaPagina.bind(this));
    }

    irParaPagina(pagina) {
        if (pagina < 1) return;
        
        this.currentPage = pagina;
        this.carregarCertificados();
    }

    alterarItensPorPagina(novoValor) {
        this.itemsPerPage = parseInt(novoValor);
        this.currentPage = 1; // Volta para primeira página
        this.carregarCertificados();
    }

    async obterTotalCertificados() {
        return 0;
    }
    
    aplicarFiltros() {
        this.currentFilters = uiAplicarFiltros();
        this.currentPage = 1;
        this.carregarCertificados();
    }
    
    limparFiltros() {
        uiLimparFiltros();
        this.currentFilters = {};
        this.currentPage = 1;
        this.carregarCertificados();
    }
    
    async gerarNumero() {
        try {
            const response = await fetch('/api/v1/certificados/gerar-numero/', {
                headers: {
                    'Authorization': `Bearer ${this.getToken()}`
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                document.getElementById('numero').value = data.numero;
            } else {
                this.logApiCall('/api/v1/certificados/gerar-numero/', response.status);
                this.mostrarAlerta('Erro ao gerar número', 'error');
            }
        } catch (error) {
            this.mostrarAlerta('Erro ao gerar número', 'error');
        }
    }
    
    calcularDataValidade() {
        return calcularDataValidade();
    }
    
    async salvarCertificado() {
        try {
            const startTime = performance.now();
            const formData = new FormData(document.getElementById('formCertificado'));
            const dados = Object.fromEntries(formData.entries());
            
            // Converter strings vazias para null
            Object.keys(dados).forEach(key => {
                if (dados[key] === '') {
                    dados[key] = null;
                }
            });
            
            // Processar dados do cliente
            // Verificar se é autocomplete (input) ou select antigo
            const inputClienteId = document.getElementById('clienteId');
            const selectCliente = document.getElementById('clienteNome');
            
            if (inputClienteId && inputClienteId.value) {
                // Autocomplete - usar campo hidden
                dados.cliente_id = parseInt(inputClienteId.value);
            } else if (selectCliente && selectCliente.value) {
                // Select antigo (fallback)
                dados.cliente_id = parseInt(selectCliente.value);
            } else {
                dados.cliente_id = null;
            }
            
            // Converter IDs para números
            if (dados.equipamento_id) {
                dados.equipamento_id = parseInt(dados.equipamento_id);
            }
            
            // Remover campos que não pertencem ao certificado (se ainda existirem)
            const camposParaRemover = [
                'fabricante', 'modelo', 'numero_serie', 'patrimonio',
                'resolucao', 'capacidade', 'cliente_nome', 'cliente_cnpj',
                'cliente_endereco', 'cliente_cidade', 'cliente_uf', 'cliente_contato'
            ];
            
            camposParaRemover.forEach(campo => {
                if (dados[campo] !== undefined) {
                    delete dados[campo];
                }
            });
            
            // Coletar ID do inspetor/aprovador selecionado
            // Primeiro verificar se já veio do FormData (com name attribute)
            let inspetorId = dados.inspetor_aprovador_id;
            
            // Se não veio do FormData, buscar diretamente do select
            if (!inspetorId || inspetorId === '') {
                const selectInspetor = document.getElementById('selectInspetor');
                
                if (selectInspetor && selectInspetor.value) {
                    const valor = selectInspetor.value.trim();
                    if (valor && valor !== '') {
                        inspetorId = parseInt(valor);
                    } else {
                        inspetorId = null;
                    }
                } else {
                    inspetorId = null;
                }
            } else {
                // Converter string para int se necessário
                if (typeof inspetorId === 'string') {
                    inspetorId = inspetorId.trim() === '' ? null : parseInt(inspetorId);
                }
            }
            
            // Atualizar dados com o valor final
            dados.inspetor_aprovador_id = inspetorId;
            
            // Remover campos de assinatura antigos se existirem (não são mais necessários)
            if (dados.assinatura_nome !== undefined) delete dados.assinatura_nome;
            if (dados.assinatura_cargo !== undefined) delete dados.assinatura_cargo;
            if (dados.assinatura_registro !== undefined) delete dados.assinatura_registro;
            

            
            // Adicionar dados dos pesos padrão
            const pesosPadrao = this.coletarPesosPadrao();
            Object.assign(dados, pesosPadrao);
            

            

            
            // Verificação completa do FormData para encontrar campos problemáticos
            const formDataCheck = new FormData(document.getElementById('formCertificado'));
            const camposProblematicos = [];
            
            // Listar TODOS os campos do FormData
            for (let [key, value] of formDataCheck.entries()) {
                if (['fabricante', 'modelo', 'numero_serie', 'patrimonio', 'resolucao', 'capacidade', 'cliente_nome', 'cliente_cnpj', 'cliente_endereco', 'cliente_cidade', 'cliente_uf', 'cliente_contato'].includes(key)) {
                    camposProblematicos.push(key);
                }
            }
            
            if (camposProblematicos.length > 0) {
                // Campos problemáticos removidos silenciosamente
            }
            
            const url = this.certificadoEmEdicao 
                ? `/api/v1/certificados/${this.certificadoEmEdicao}`
                : '/api/v1/certificados/';
            
            const method = this.certificadoEmEdicao ? 'PUT' : 'POST';
            
            const response = await fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.getToken()}`
                },
                body: JSON.stringify(dados)
            });
            
            const responseTime = performance.now() - startTime;
            
            if (response.ok) {
                const certificado = await response.json();
                
                // Salvar ensaios de excentricidade
                await this.salvarEnsaiosExcentricidade(certificado.id);
                
                // Salvar resultados dos ensaios
                await this.salvarResultadosEnsaios(certificado.id);
                
                // Salvar ensaios de mobilidade
                await this.salvarEnsaiosMobilidade(certificado.id);
                
                this.logApiCall(url, response.status, responseTime);
                
                this.mostrarAlerta(
                    this.certificadoEmEdicao ? 'Certificado atualizado com sucesso!' : 'Certificado criado com sucesso!',
                    'success'
                );
                
                // Fechar modal se existir (só existe no listar.html)
                const modalElement = document.getElementById('modalCertificado');
                if (modalElement) {
                    const modal = bootstrap.Modal.getInstance(modalElement);
                    if (modal) {
                modal.hide();
                    }
                }
                
                this.certificadoEmEdicao = null;
                
                // Limpar formulário apenas se não estiver em página de edição/novo
                if (!window.location.pathname.includes('/editar/') && !window.location.pathname.includes('/novo')) {
                this.limparFormulario();
                }
                
                // Se estiver em modo de edição (URL com /editar/), redirecionar para lista
                if (window.location.pathname.includes('/editar/')) {
                    setTimeout(() => {
                    window.location.href = '/certificados';
                    }, 1000);
                } else if (window.location.pathname.includes('/novo')) {
                    // Se estiver em /novo, redirecionar para lista após salvar
                    setTimeout(() => {
                        window.location.href = '/certificados';
                    }, 1000);
                } else {
                    // Se estiver no listar.html, recarregar lista
                    if (this.carregarCertificados) {
                    this.carregarCertificados();
                    }
                    if (this.carregarEstatisticas) {
                    this.carregarEstatisticas();
                    }
                }
                
            } else {
                this.logApiCall(url, response.status, responseTime);
                
                // Tentar obter detalhes do erro
                let errorMessage = 'Erro ao salvar certificado';
                try {
                    const errorText = await response.text();
                    
                    
                    // Tentar fazer parse do JSON se possível
                    try {
                        const error = JSON.parse(errorText);
                        if (error.detail) {
                            if (Array.isArray(error.detail)) {
                                errorMessage = error.detail.map(e => e.msg || e.message || e).join(', ');
                            } else {
                                errorMessage = error.detail;
                            }
                        }
                    } catch (parseError) {
                        // Se não for JSON, usar o texto como está
                        errorMessage = errorText || `Erro ${response.status}: ${response.statusText}`;
                    }
                } catch (textError) {
                    errorMessage = `Erro ${response.status}: ${response.statusText}`;
                }
                
                this.mostrarAlerta(errorMessage, 'error');
            }
        } catch (error) {
            this.mostrarAlerta('Erro ao salvar certificado', 'error');
        }
    }
    
    async editarCertificado(id) {
        try {
            const response = await fetch(`/api/v1/certificados/${id}`, {
                headers: {
                    'Authorization': `Bearer ${this.getToken()}`
                }
            });
            
            if (response.ok) {
                const certificado = await response.json();
                
                this.certificadoEmEdicao = id;
                await this.preencherFormulario(certificado);
                
                // Carregar ensaios de excentricidade
                await this.carregarEnsaiosExcentricidade(id);
                
                // Carregar resultados dos ensaios
                await this.carregarResultadosEnsaios(id);
                
                // Carregar ensaios de mobilidade
                await this.carregarEnsaiosMobilidade(id);
                
                // Abrir modal
                const modal = new bootstrap.Modal(document.getElementById('modalCertificado'));
                modal.show();
                
                // Atualizar título do modal
                document.getElementById('modalCertificadoLabel').textContent = 'Editar Certificado';
                
            } else {
                this.logApiCall(`/api/v1/certificados/${id}`, response.status);
                this.mostrarAlerta('Erro ao carregar certificado', 'error');
            }
        } catch (error) {
            this.mostrarAlerta('Erro ao editar certificado', 'error');
        }
    }
    
    async carregarCertificadoParaEdicao(id) {
        // Função para carregar certificado na página dedicada de edição (sem modal)
        try {
            const response = await fetch(`/api/v1/certificados/${id}`, {
                headers: {
                    'Authorization': `Bearer ${this.getToken()}`
                }
            });
            
            if (response.ok) {
                const certificado = await response.json();
                
                this.certificadoEmEdicao = id;
                
                // Carregar termobarohigrometros, inspetores e pesos padrão em paralelo para melhor performance
                const promises = [];
                
                if (window.carregarTermobarohigrometros && typeof window.carregarTermobarohigrometros === 'function') {
                    promises.push(window.carregarTermobarohigrometros());
                }
                
                if (window.carregarInspetoresAprovadores && typeof window.carregarInspetoresAprovadores === 'function') {
                    promises.push(window.carregarInspetoresAprovadores());
                }
                
                // Carregar pesos padrão (necessário para o select funcionar ao adicionar pesos)
                promises.push(this.carregarPesosPadrao());
                
                // Aguardar todas as requisições em paralelo
                await Promise.all(promises);
                
                await this.preencherFormulario(certificado);
                
                // Carregar todos os ensaios em paralelo para melhor performance
                await Promise.all([
                    this.carregarEnsaiosExcentricidade(id),
                    this.carregarResultadosEnsaios(id),
                    this.carregarEnsaiosMobilidade(id)
                ]);
                
            } else {
                this.logApiCall(`/api/v1/certificados/${id}`, response.status);
                this.mostrarAlerta('Erro ao carregar certificado', 'error');
            }
        } catch (error) {
            this.mostrarAlerta('Erro ao carregar certificado', 'error');
        }
    }
    
    async preencherFormulario(certificado) {
        
        document.getElementById('numero').value = certificado.numero;
        const elDataEmissao = document.getElementById('dataEmissao');
        const elDataAjuste = document.getElementById('dataAjuste');
        const elDataValidade = document.getElementById('dataValidade');
        if (elDataEmissao) elDataEmissao.value = certificado.data_emissao || '';
        if (elDataAjuste) elDataAjuste.value = certificado.data_ajuste || '';
        if (elDataValidade) elDataValidade.value = certificado.data_validade || '';
        document.getElementById('regulamentacao').value = certificado.regulamentacao || '';
        document.getElementById('conclusao').value = certificado.conclusao || '';
        
        // Inicializar autocomplete de clientes se ainda não foi inicializado
        const inputCliente = document.getElementById('clienteNomeInput');
        const selectCliente = document.getElementById('clienteNome');
        
        if (!inputCliente && selectCliente) {
            this.inicializarAutocompleteCliente();
        }
        
        // Campo do cliente - preencher com dados do certificado
        if (certificado.cliente_id && certificado.cliente) {
            // Preencher dados do cliente primeiro
                document.getElementById('clienteCnpj').value = certificado.cliente.cnpj || '';
                document.getElementById('clienteEndereco').value = certificado.cliente.endereco || '';
                document.getElementById('clienteCidade').value = certificado.cliente.cidade || '';
                document.getElementById('clienteUf').value = certificado.cliente.uf || '';
                document.getElementById('clienteContato').value = certificado.cliente.contato || '';
            
            // Usar função global para definir cliente no autocomplete
            if (typeof window.definirClienteAutocomplete === 'function') {
                window.definirClienteAutocomplete(certificado.cliente);
                // Aguardar um pouco para garantir que o campo hidden foi preenchido
                await new Promise(resolve => setTimeout(resolve, 50));
            } else {
                // Se autocomplete ainda não foi inicializado, aguardar um pouco
                await new Promise(resolve => setTimeout(resolve, 100));
                if (typeof window.definirClienteAutocomplete === 'function') {
                    window.definirClienteAutocomplete(certificado.cliente);
                    await new Promise(resolve => setTimeout(resolve, 50));
                }
            }
            
            // Carregar equipamentos do cliente para o select
            await this.carregarEquipamentosCliente();
            
            // Selecionar o equipamento correto no select
            if (certificado.equipamento_id) {
                const selectEquipamento = document.getElementById('equipamentoId');
                if (selectEquipamento) {
                    selectEquipamento.value = certificado.equipamento_id;
                    
                    // Carregar os dados do equipamento
                    await this.carregarDadosEquipamento();
                }
            }
        } else {
            // Limpar campos se não há cliente
            document.getElementById('clienteCnpj').value = '';
            document.getElementById('clienteEndereco').value = '';
            document.getElementById('clienteCidade').value = '';
            document.getElementById('clienteUf').value = '';
            document.getElementById('clienteContato').value = '';
        }
        
        // Preencher dados do equipamento se disponível (assim como o cliente)
        if (certificado.equipamento) {
            this.preencherCamposEquipamento(certificado.equipamento);
        } else if (!certificado.equipamento_id) {
            // Só limpar se não há equipamento e não há equipamento_id (para não sobrescrever dados carregados)
            this.limparCamposEquipamento();
        }
        
        // Campos técnicos adicionais (sem valores padrão)
        this.preencherCampo('localCalibracaoCertificado', certificado.local_calibracao || '');
        this.preencherCampo('etiquetaVerificado', certificado.etiqueta_verificado);
        
        // Condições ambientais
        this.preencherCampo('temperaturaInicial', certificado.temperatura_inicial);
        this.preencherCampo('temperaturaFinal', certificado.temperatura_final);
        this.preencherCampo('umidadeInicial', certificado.umidade_inicial);
        this.preencherCampo('umidadeFinal', certificado.umidade_final);
        this.preencherCampo('pressaoInicial', certificado.pressao_inicial);
        this.preencherCampo('pressaoFinal', certificado.pressao_final);
        this.preencherCampo('massaArInicial', certificado.massa_ar_inicial);
        this.preencherCampo('massaArFinal', certificado.massa_ar_final);
        
        // Equipamento auxiliar
        this.preencherCampo('equipamentoAuxiliar', certificado.equipamento_auxiliar);
        this.preencherCampo('identificacaoAuxiliar', certificado.identificacao_auxiliar);
        this.preencherCampo('certificadoAuxiliar', certificado.certificado_auxiliar);
        this.preencherCampo('validadeAuxiliar', certificado.validade_auxiliar);
        
        // Selecionar termobarohigrometro no select se houver dados salvos
        await this.selecionarTermobarohigrometroSalvo(certificado);
        
        // Preencher campos de assinatura
        await this.preencherCamposAssinatura(certificado);
        
        // Preencher pesos padrão
        await this.preencherPesosPadrao(certificado);
    }
    
    async preencherCamposAssinatura(certificado) {
        // Verificar se há inspetor_aprovador_id ou objeto inspetor_aprovador
        const inspetorAprovadorId = certificado.inspetor_aprovador_id;
        const inspetorAprovador = certificado.inspetor_aprovador;
        
        if (!inspetorAprovadorId && !inspetorAprovador) {
            return;
        }
        
        // Se temos o objeto inspetor_aprovador, preencher os campos diretamente
        if (inspetorAprovador) {
            const nome = inspetorAprovador.nome || '';
            const cargo = inspetorAprovador.cargo || '';
            const registroCompleto = inspetorAprovador.registro_profissional 
                ? (inspetorAprovador.orgao_registro ? `${inspetorAprovador.orgao_registro}-${inspetorAprovador.registro_profissional}` : inspetorAprovador.registro_profissional)
                : '';
            
            // Preencher campos diretamente
            this.preencherCampo('assinaturaNome', nome);
            this.preencherCampo('assinaturaCargo', cargo);
            this.preencherCampo('assinaturaRegistro', registroCompleto);
        }
        
        // Selecionar o inspetor/aprovador no select
        await this.selecionarInspetorAprovadorPorId(inspetorAprovadorId || (inspetorAprovador && inspetorAprovador.id));
    }
    
    async selecionarInspetorAprovadorPorId(inspetorId) {
        if (!inspetorId) {
            return;
        }
        
        // Aguardar que os inspetores sejam carregados
        const select = document.getElementById('selectInspetor');
        if (!select) {
            return;
        }
        
        // Aguardar até que o select tenha opções (além da opção padrão)
        let tentativas = 0;
        while (select.options.length <= 1 && tentativas < 20) {
            await new Promise(resolve => setTimeout(resolve, 200));
            tentativas++;
        }
        
        if (select.options.length <= 1) {
            return;
        }
        
        // Procurar o inspetor pelo ID
        for (let i = 0; i < select.options.length; i++) {
            const option = select.options[i];
            if (option.value && parseInt(option.value) === inspetorId) {
                select.value = option.value;
                return;
            }
        }
    }
    
    async preencherPesosPadrao(certificado) {
        // Verificar se há pesos padrão no certificado
        if (!certificado.pesos_padrao || !Array.isArray(certificado.pesos_padrao) || certificado.pesos_padrao.length === 0) {
            return;
        }
        
        // Limpar pesos padrão existentes
        this.limparPesosPadrao();
        
        // Ordenar pesos padrão por ordem
        const pesosOrdenados = [...certificado.pesos_padrao].sort((a, b) => {
            if (a.ordem !== b.ordem) {
                return a.ordem - b.ordem;
            }
            return a.id - b.id;
        });
        
        // Aguardar que os pesos padrão disponíveis sejam carregados
        let tentativas = 0;
        while ((!this.pesosPadrao || this.pesosPadrao.length === 0) && tentativas < 20) {
            await new Promise(resolve => setTimeout(resolve, 100));
            tentativas++;
        }
        
        if (!this.pesosPadrao || this.pesosPadrao.length === 0) {
            // Tentar carregar novamente
            await this.carregarPesosPadrao();
        }
        
        // Para cada peso padrão, criar linha e preencher
        for (const pesoPadrao of pesosOrdenados) {
            // Adicionar linha de peso padrão
            await this.adicionarPesoPadrao();
            
            // Obter o último peso adicionado
            const ultimoPeso = this.pesosSelecionados[this.pesosSelecionados.length - 1];
            if (!ultimoPeso) continue;
            
            const pesoId = ultimoPeso.id;
            
            // Buscar o CertificadoPeso correspondente pela identificacao
            const certificadoPeso = this.pesosPadrao.find(p => p.identificacao === pesoPadrao.identificacao);
            
            if (certificadoPeso) {
                // Selecionar o peso padrão no select
                const select = document.getElementById(`pesoPadrao${pesoId}`);
                if (select) {
                    select.value = certificadoPeso.id;
                    
                    // Disparar evento change para preencher campos automaticamente
                    const event = new Event('change', { bubbles: true });
                    select.dispatchEvent(event);
                }
            }
            
            // Preencher campos diretamente (caso o evento não tenha funcionado)
            const certInput = document.getElementById(`pesoPadrao${pesoId}Cert`);
            const valInput = document.getElementById(`pesoPadrao${pesoId}Val`);
            const ordInput = document.getElementById(`pesoPadrao${pesoId}Ord`);
            
            if (certInput) certInput.value = pesoPadrao.certificado || '';
            if (valInput) {
                // Converter data para formato YYYY-MM-DD
                if (pesoPadrao.validade) {
                    const data = new Date(pesoPadrao.validade);
                    if (!isNaN(data.getTime())) {
                        valInput.value = data.toISOString().split('T')[0];
                    }
                }
            }
            if (ordInput) ordInput.value = pesoPadrao.ordem || ultimoPeso.ordem;
            
            // Atualizar array de pesos selecionados
            const index = this.pesosSelecionados.findIndex(p => p.id === pesoId);
            if (index !== -1) {
                this.pesosSelecionados[index] = {
                    ...this.pesosSelecionados[index],
                    peso_padrao_id: certificadoPeso ? certificadoPeso.id : '',
                    certificado: pesoPadrao.certificado || '',
                    validade: pesoPadrao.validade || '',
                    ordem: pesoPadrao.ordem || ultimoPeso.ordem
                };
            }
            
            // Pequeno delay para garantir que o DOM foi atualizado
            await new Promise(resolve => setTimeout(resolve, 50));
        }
    }
    
    async selecionarInspetorAprovadorSalvo(nome, cargo, registro) {
        // Aguardar que os inspetores sejam carregados
        const select = document.getElementById('selectInspetor');
        if (!select) {
            return;
        }
        
        // Aguardar até que o select tenha opções (além da opção padrão)
        let tentativas = 0;
        while (select.options.length <= 1 && tentativas < 20) {
            await new Promise(resolve => setTimeout(resolve, 200));
            tentativas++;
        }
        
        if (select.options.length <= 1) {
            return;
        }
        
        // Procurar o inspetor que corresponde aos dados salvos
        const nomeSalvo = (nome || '').trim().toUpperCase();
        const cargoSalvo = (cargo || '').trim().toUpperCase();
        const registroSalvo = (registro || '').trim().toUpperCase();
        
        let inspetorEncontrado = false;
        
        // Percorrer todas as opções do select
        for (let i = 0; i < select.options.length; i++) {
            const option = select.options[i];
            if (!option.value) continue; // Pular opção padrão
            
            try {
                const inspetor = JSON.parse(option.dataset.inspetor || '{}');
                const nomeInspetor = (inspetor.nome || '').trim().toUpperCase();
                const cargoInspetor = (inspetor.cargo || '').trim().toUpperCase();
                
                // Montar registro completo do inspetor
                let registroInspetor = '';
                if (inspetor.registro_profissional) {
                    if (inspetor.orgao_registro) {
                        registroInspetor = `${inspetor.orgao_registro}-${inspetor.registro_profissional}`.trim().toUpperCase();
                    } else {
                        registroInspetor = inspetor.registro_profissional.trim().toUpperCase();
                    }
                }
                
                // Comparar por nome (mais confiável)
                if (nomeSalvo && nomeInspetor && nomeInspetor === nomeSalvo) {
                    select.value = option.value;
                    inspetorEncontrado = true;
                    break;
                }
                
                // Comparar por registro se não encontrou por nome
                if (!inspetorEncontrado && registroSalvo && registroInspetor && registroInspetor === registroSalvo) {
                    select.value = option.value;
                    inspetorEncontrado = true;
                    break;
                }
            } catch (e) {
                // Ignorar erro ao processar opção
            }
        }
    }
    
    async selecionarTermobarohigrometroSalvo(certificado) {
        // Verificar se há dados de equipamento auxiliar salvos
        if (!certificado.identificacao_auxiliar && !certificado.equipamento_auxiliar) {
            return; // Não há dados para comparar
        }
        
        // Aguardar que os termobarohigrometros sejam carregados
        const select = document.getElementById('selectTermobarohigrometro');
        if (!select) {
            return;
        }
        
        // Aguardar até que o select tenha opções (além da opção padrão)
        let tentativas = 0;
        while (select.options.length <= 1 && tentativas < 20) {
            await new Promise(resolve => setTimeout(resolve, 200));
            tentativas++;
        }
        
        if (select.options.length <= 1) {
            return;
        }
        
        // Procurar o termobarohigrometro que corresponde aos dados salvos
        // Comparar por número de série (identificacao_auxiliar) ou nome (equipamento_auxiliar)
        const identificacaoSalva = (certificado.identificacao_auxiliar || '').trim().toUpperCase();
        const nomeSalvo = (certificado.equipamento_auxiliar || '').trim().toUpperCase();
        
        
        let termobarohigrometroEncontrado = false;
        
        // Percorrer todas as opções do select
        for (let i = 0; i < select.options.length; i++) {
            const option = select.options[i];
            if (!option.value) continue; // Pular opção padrão
            
            try {
                const equipamento = JSON.parse(option.dataset.equipamento || '{}');
                const numeroSerie = (equipamento.numero_serie || '').trim().toUpperCase();
                const nome = (equipamento.nome || '').trim().toUpperCase();
                
                // Comparar por número de série (mais confiável)
                if (identificacaoSalva && numeroSerie && numeroSerie === identificacaoSalva) {
                    select.value = option.value;
                    termobarohigrometroEncontrado = true;
                    // Não preencher campos aqui pois já foram preenchidos pelo preencherFormulario
                    break;
                }
                
                // Comparar por nome se não encontrou por número de série
                if (!termobarohigrometroEncontrado && nomeSalvo && nome && nome.includes(nomeSalvo)) {
                    select.value = option.value;
                    termobarohigrometroEncontrado = true;
                    // Não preencher campos aqui pois já foram preenchidos pelo preencherFormulario
                    break;
                }
            } catch (e) {
            }
        }
        
        if (!termobarohigrometroEncontrado) {
        }
    }

    preencherCampo(campoId, valor) {
        const elemento = document.getElementById(campoId);
        if (!elemento) {
            return;
        }
        const valorNormalizado = (valor === undefined || valor === null) ? '' : valor;
        elemento.value = valorNormalizado;
    }
    
    async carregarEquipamentosCliente() {
        // Verificar se é autocomplete (input) ou select antigo
        const inputClienteId = document.getElementById('clienteId');
        const selectCliente = document.getElementById('clienteNome');
        
        let clienteId = null;
        if (inputClienteId && inputClienteId.value) {
            // Autocomplete - usar campo hidden
            clienteId = inputClienteId.value;
        } else if (selectCliente && selectCliente.value) {
            // Select antigo (fallback)
            clienteId = selectCliente.value;
        }
        
        if (!clienteId) {
            // Limpar o select de equipamentos quando não há cliente selecionado
            const selectEquipamento = document.getElementById('equipamentoId');
            if (selectEquipamento) {
                selectEquipamento.innerHTML = '<option value="">Selecione um cliente primeiro...</option>';
            }
            return;
        }
        
        try {
            const url = `/api/v1/equipamentos/?cliente_id=${clienteId}&limit=500`;
            let response = await fetch(url);
            
            if (!response.ok) {
                const token = this.getToken();
                if (token) {
                    response = await fetch(`/api/v1/equipamentos/?cliente_id=${clienteId}&limit=500`, {
                        headers: { 'Authorization': `Bearer ${token}` }
                    });
                }
            }
            
            if (response.ok) {
                const data = await response.json();
                
                // A nova API retorna uma estrutura paginada
                const equipamentos = data.equipamentos || data;
                
                this.preencherSelectEquipamentos(equipamentos, clienteId);
                
                // Preencher automaticamente os dados do cliente apenas se for select antigo
                // (com autocomplete, os campos já são preenchidos pela função selecionarCliente)
                if (selectCliente && selectCliente.tagName === 'SELECT' && selectCliente.options) {
                const option = selectCliente.options[selectCliente.selectedIndex];
                if (option) {
                    document.getElementById('clienteCnpj').value = option.getAttribute('data-cnpj') || '';
                    document.getElementById('clienteEndereco').value = option.getAttribute('data-endereco') || '';
                    document.getElementById('clienteCidade').value = option.getAttribute('data-cidade') || '';
                    document.getElementById('clienteUf').value = option.getAttribute('data-uf') || '';
                    document.getElementById('clienteContato').value = option.getAttribute('data-contato') || '';
                    }
                }
            } else {
                this.logApiCall(`/api/v1/equipamentos/?cliente_id=${clienteId}`, response.status);
                this.mostrarAlerta('Erro ao carregar equipamentos do cliente', 'error');
            }
        } catch (error) {
            this.mostrarAlerta('Erro ao carregar equipamentos do cliente', 'error');
        }
    }
    
    async carregarDadosEquipamento() {
        const selectEquipamento = document.getElementById('equipamentoId');
        const equipamentoId = selectEquipamento?.value;
        
        if (!equipamentoId) {
            this.limparCamposEquipamento();
            return;
        }
        
        // Verificar se o equipamento existe no select
        const optionExists = Array.from(selectEquipamento.options).some(option => option.value === equipamentoId);
        if (!optionExists) {
            // Aguardar um pouco mais e tentar novamente
            await new Promise(resolve => setTimeout(resolve, 300));
            const equipamentoIdRetry = selectEquipamento.value;
            if (!equipamentoIdRetry) {
                this.limparCamposEquipamento();
                return;
            }
        }
        
        const equipamento = await apiCarregarDadosEquipamento(equipamentoId, this.logger, this.mostrarAlerta.bind(this));
        if (equipamento) {
                this.preencherCamposEquipamento(equipamento);
        }
    }
    
    async carregarDadosEquipamentoDireto(equipamentoId) {
        if (!equipamentoId) {
            return;
        }
        
        try {
            // Tentar primeiro sem token
            let response = await fetch(`/api/v1/equipamentos/${equipamentoId}`);
            
            // Se falhar, tentar com token
            if (!response.ok) {
                const token = this.getToken();
                
                response = await fetch(`/api/v1/equipamentos/${equipamentoId}`, {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });
            }
            
            if (response.ok) {
                const equipamento = await response.json();
                this.preencherCamposEquipamento(equipamento);
            } else {
                this.logApiCall(`/api/v1/equipamentos/${equipamentoId}`, response.status);
                this.mostrarAlerta(`Erro ao carregar dados do equipamento: ${response.status}`, 'error');
            }
        } catch (error) {
            this.mostrarAlerta('Erro ao carregar dados do equipamento', 'error');
        }
    }
    
    preencherCamposEquipamento(equipamento) {
        
        // Preencher campos com dados do equipamento
        document.getElementById('fabricante').value = equipamento.fabricante || '';
        document.getElementById('modelo').value = equipamento.modelo || '';
        document.getElementById('numeroSerie').value = equipamento.numero_serie || '';
        document.getElementById('patrimonio').value = equipamento.patrimonio || '';
        document.getElementById('resolucao').value = equipamento.resolucao || '';
        document.getElementById('inventario').value = equipamento.inventario || '';
        document.getElementById('capacidade').value = equipamento.capacidade || '';
        document.getElementById('unidade').value = equipamento.unidade || '';

        
        // Preencher também o campo de local de calibração do certificado somente com dado real
        const localCalibracaoCertificado = document.getElementById('localCalibracaoCertificado');
        if (localCalibracaoCertificado) {
            localCalibracaoCertificado.value = equipamento.local_calibracao || '';
        }

        // Não definir valores padrão nos campos de equipamento auxiliar
        document.getElementById('equipamentoAuxiliar').value = equipamento.equipamento_auxiliar || '';
        document.getElementById('identificacaoAuxiliar').value = equipamento.identificacao_auxiliar || '';
        document.getElementById('certificadoAuxiliar').value = equipamento.certificado_auxiliar || '';
        document.getElementById('validadeAuxiliar').value = equipamento.validade_auxiliar || '';
    }
    
    limparCamposEquipamento() {
        
        // Limpar todos os campos do equipamento
        document.getElementById('fabricante').value = '';
        document.getElementById('modelo').value = '';
        document.getElementById('numeroSerie').value = '';
        document.getElementById('patrimonio').value = '';
        document.getElementById('resolucao').value = '';
        document.getElementById('inventario').value = '';
        document.getElementById('capacidade').value = '';
        document.getElementById('unidade').value = '';

        
        // Limpar campo de local de calibração do certificado
        const localCalibracaoCertificado = document.getElementById('localCalibracaoCertificado');
        if (localCalibracaoCertificado) {
            localCalibracaoCertificado.value = '';
        }
        

        
        // Limpar campos do equipamento auxiliar
        document.getElementById('equipamentoAuxiliar').value = '';
        document.getElementById('identificacaoAuxiliar').value = '';
        document.getElementById('certificadoAuxiliar').value = '';
        document.getElementById('validadeAuxiliar').value = '';
    }
    
    limparCamposEnsaios() {
        // Limpar campos de ensaios de excentricidade (pontos A-E)
        const pontos = ['A', 'B', 'C', 'D', 'E'];
        pontos.forEach(ponto => {
            document.getElementById(`excentricidade${ponto}`).value = '';
            document.getElementById(`excentricidade${ponto}Leitura`).value = '';
            document.getElementById(`excentricidade${ponto}Erro`).value = '';
            document.getElementById(`excentricidade${ponto}LeituraDepois`).value = '';
            document.getElementById(`excentricidade${ponto}ErroDepois`).value = '';
        });
        
        // Limpar campos de resultados de ensaios (pontos 1-5)
        for (let i = 1; i <= 5; i++) {
            const campos = [
                `resultado${i}Carga`,
                `resultado${i}LeituraAntes`,
                `resultado${i}ErroAntes`,
                `resultado${i}LeituraDepois`,
                `resultado${i}ErroDepois`,
                `resultado${i}Incerteza`
            ];
            campos.forEach(campo => {
                const elemento = document.getElementById(campo);
                if (elemento) elemento.value = '';
            });
        }
        
        // Limpar campos de ensaios de mobilidade
        const camposMobilidade = [
            'mobilidadeCarga',
            'mobilidadeSobrecarga',
            'mobilidadeLeituraAntes',
            'mobilidadePadrao'
        ];
        camposMobilidade.forEach(campo => {
            const elemento = document.getElementById(campo);
            if (elemento) elemento.value = '';
        });
    }

    coletarEnsaiosExcentricidade() {
        return featColetarEnsaiosExcentricidade();
    }

    async salvarEnsaiosExcentricidade(certificadoId) {
        return await featSalvarEnsaiosExcentricidade(certificadoId, this.getToken.bind(this), this.logger, featColetarEnsaiosExcentricidade);
    }

    coletarResultadosEnsaios() {
        return featColetarResultadosEnsaios();
    }

    async salvarResultadosEnsaios(certificadoId) {
        return await featSalvarResultadosEnsaios(certificadoId, this.getToken.bind(this), this.logger, featColetarResultadosEnsaios);
    }

    coletarEnsaiosMobilidade() {
        return featColetarEnsaiosMobilidade();
    }

    async salvarEnsaiosMobilidade(certificadoId) {
        return await featSalvarEnsaiosMobilidade(certificadoId, this.getToken.bind(this), this.logger, featColetarEnsaiosMobilidade);
    }

    async carregarEnsaiosExcentricidade(certificadoId) {
        await featCarregarEnsaiosExcentricidade(certificadoId, this.getToken.bind(this), this.logger, this.mostrarAlerta.bind(this));
    }

    // preencherEnsaiosExcentricidade agora está no módulo features/ensaios-excentricidade.js

    async carregarResultadosEnsaios(certificadoId) {
        await featCarregarResultadosEnsaios(certificadoId, this.getToken.bind(this), this.logger);
    }

    // preencherResultadosEnsaios agora está no módulo features/ensaios-resultados.js

    async carregarEnsaiosMobilidade(certificadoId) {
        await featCarregarEnsaiosMobilidade(certificadoId, this.getToken.bind(this), this.logger);
    }

    // preencherEnsaiosMobilidade agora está no módulo features/ensaios-mobilidade.js
    
    limparFormulario() {
        
        // Resetar o formulário
        document.getElementById('formCertificado').reset();
        
        // Limpar variável de edição
        this.certificadoEmEdicao = null;
        
        // Atualizar título do modal (se existir - só existe no listar.html)
        const modalLabel = document.getElementById('modalCertificadoLabel');
        if (modalLabel) {
            modalLabel.textContent = 'Novo Certificado';
        }
        
        // Limpar campos específicos que podem não ser resetados pelo .reset()
        const camposParaLimpar = [
            'clienteCnpj', 'clienteEndereco', 'clienteCidade', 'clienteUf', 'clienteContato',
            'fabricante', 'modelo', 'numeroSerie', 'patrimonio', 'resolucao', 'capacidade',
            'inventario', 'unidade'
        ];
        
        camposParaLimpar.forEach(campoId => {
            const elemento = document.getElementById(campoId);
            if (elemento) {
                elemento.value = '';
            }
        });
        
        // Limpar selects
        const selectCliente = document.getElementById('clienteNome');
        if (selectCliente) selectCliente.value = '';
        
        const selectEquipamento = document.getElementById('equipamentoId');
        if (selectEquipamento) selectEquipamento.value = '';
        
        // Não preencher campos com valores padrão; manter vazio até dados reais
        const camposOpcionais = ['regulamentacao', 'conclusao', 'localCalibracaoCertificado', 'etiquetaVerificado'];
        camposOpcionais.forEach(campoId => {
            const elemento = document.getElementById(campoId);
            if (elemento) {
                elemento.value = '';
            }
        });
        
        // Limpar campos do equipamento
        this.limparCamposEquipamento();
        
        // Limpar campos de ensaios
        this.limparCamposEnsaios();
        
        // Limpar pesos padrão
        this.limparPesosPadrao();
        
        // Gerar novo número automaticamente
        this.gerarNumero();
    }
    
    excluirCertificado(id) {
        // Armazenar ID para confirmação
        this.certificadoParaExcluir = id;
        
        // Abrir modal de confirmação de forma simples
        const modal = new bootstrap.Modal(document.getElementById('modalConfirmacao'));
        modal.show();
    }

    async visualizarCertificado(id) {
        try {
            const response = await fetch(`/api/v1/certificados/${id}`, {
                headers: {
                    'Authorization': `Bearer ${this.getToken()}`
                }
            });
            
            if (!response.ok) {
                if (response.status === 404) {
                    this.mostrarAlerta('Certificado não encontrado', 'error');
            } else {
                    this.mostrarAlerta('Erro ao carregar certificado', 'error');
                }
                return;
            }
            
            const certificado = await response.json();
            
            // Carregar ensaios em paralelo
            const [ensaiosExcentricidade, resultadosEnsaios, ensaiosMobilidade] = await Promise.all([
                this.carregarEnsaiosExcentricidadeParaVisualizacao(id),
                this.carregarResultadosEnsaiosParaVisualizacao(id),
                this.carregarEnsaiosMobilidadeParaVisualizacao(id)
            ]);
            
            // Adicionar ensaios ao objeto certificado
            certificado.ensaios_excentricidade = ensaiosExcentricidade;
            certificado.resultados_ensaios = resultadosEnsaios;
            certificado.ensaios_mobilidade = ensaiosMobilidade;
            
            this.preencherModalVisualizacao(certificado);
            this.abrirModalVisualizacao();
            
        } catch (error) {
            this.mostrarAlerta('Erro ao visualizar certificado', 'error');
        }
    }

    async carregarEnsaiosExcentricidadeParaVisualizacao(certificadoId) {
        try {
            const response = await fetch(`/api/v1/ensaios/${certificadoId}/excentricidade`, {
                headers: {
                    'Authorization': `Bearer ${this.getToken()}`
                }
            });
            
            if (response.ok) {
                return await response.json();
            }
            return [];
        } catch (error) {
            return [];
        }
    }
    
    async carregarResultadosEnsaiosParaVisualizacao(certificadoId) {
        try {
            const response = await fetch(`/api/v1/ensaios/${certificadoId}/resultados`, {
                headers: {
                    'Authorization': `Bearer ${this.getToken()}`
                }
            });
            
            if (response.ok) {
                return await response.json();
            }
            return [];
        } catch (error) {
            return [];
        }
    }
    
    async carregarEnsaiosMobilidadeParaVisualizacao(certificadoId) {
        try {
            const response = await fetch(`/api/v1/ensaios/${certificadoId}/mobilidade`, {
                headers: {
                    'Authorization': `Bearer ${this.getToken()}`
                }
            });
            
            if (response.ok) {
                return await response.json();
            }
            return [];
        } catch (error) {
            return [];
        }
    }
    
    preencherModalVisualizacao(certificado) {
        try {
            // Função auxiliar para formatar valores
            const formatarValor = (valor) => {
                if (valor === null || valor === undefined || valor === '') {
                    return '-';
                }
                return valor;
            };
            
            const formatarData = (data) => {
                if (!data) return '-';
                if (typeof window.formatarDataApenas === 'function') return window.formatarDataApenas(data);
                try {
                    const s = String(data).trim();
                    const m = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
                    if (m) return m[3] + '/' + m[2] + '/' + m[1];
                    const date = new Date(data);
                    return isNaN(date.getTime()) ? data : date.toLocaleDateString('pt-BR');
                } catch (e) {
                    return data;
                }
            };
            
            const formatarTipo = (tipo) => {
                if (tipo === 'calibracao') return 'Calibração';
                if (tipo === 'afericao') return 'Aferição';
                return tipo;
            };
            
            // Função auxiliar para definir valor de elemento de forma segura
            const setElementText = (id, value) => {
                const element = document.getElementById(id);
                if (element) {
                    element.textContent = value;
                }
            };
            
            // Informações Básicas
            setElementText('viewNumero', formatarValor(certificado.numero));
            setElementText('viewTipo', formatarTipo(certificado.tipo));
            setElementText('viewDataEmissao', formatarData(certificado.data_emissao));
            setElementText('viewDataAjuste', formatarData(certificado.data_ajuste));
            setElementText('viewDataValidade', formatarData(certificado.data_validade));
            setElementText('viewRegulamentacao', formatarValor(certificado.regulamentacao));
            setElementText('viewConclusao', formatarValor(certificado.conclusao));
            setElementText('viewLocalCalibracao', formatarValor(certificado.local_calibracao));
            setElementText('viewEtiquetaVerificado', formatarValor(certificado.etiqueta_verificado));
        
            // Dados do Equipamento
            if (certificado.equipamento) {
                setElementText('viewFabricante', formatarValor(certificado.equipamento.fabricante));
                setElementText('viewModelo', formatarValor(certificado.equipamento.modelo));
                setElementText('viewNumeroSerie', formatarValor(certificado.equipamento.numero_serie));
                setElementText('viewPatrimonio', formatarValor(certificado.equipamento.patrimonio));
                setElementText('viewResolucao', formatarValor(certificado.equipamento.resolucao));
                setElementText('viewCapacidade', formatarValor(certificado.equipamento.capacidade));
            }
            
            setElementText('viewUnidade', formatarValor(certificado.unidade));
            setElementText('viewInventario', formatarValor(certificado.inventario));
            
            if (certificado.tipo_equipamento) {
                setElementText('viewTipoEquipamento', formatarValor(certificado.tipo_equipamento.tipo_equipamento));
            } else {
                setElementText('viewTipoEquipamento', '-');
            }
            
            // Dados do Cliente
            const sectionCliente = document.getElementById('sectionCliente');
            if (certificado.cliente && sectionCliente) {
                sectionCliente.style.display = 'block';
                setElementText('viewClienteNome', formatarValor(certificado.cliente.nome));
                setElementText('viewClienteCnpj', formatarValor(certificado.cliente.cnpj));
                setElementText('viewClienteEndereco', formatarValor(certificado.cliente.endereco));
                setElementText('viewClienteCidade', formatarValor(certificado.cliente.cidade));
                setElementText('viewClienteUf', formatarValor(certificado.cliente.uf));
                setElementText('viewClienteContato', formatarValor(certificado.cliente.contato));
            } else if (sectionCliente) {
                sectionCliente.style.display = 'none';
            }
            
            // Condições Ambientais
            const temCondicoes = certificado.temperatura_inicial || certificado.temperatura_final || 
                                certificado.umidade_inicial || certificado.umidade_final ||
                                certificado.pressao_inicial || certificado.pressao_final ||
                                certificado.massa_ar_inicial || certificado.massa_ar_final;
            
            const sectionCondicoes = document.getElementById('sectionCondicoesAmbientais');
            if (temCondicoes && sectionCondicoes) {
                sectionCondicoes.style.display = 'block';
                setElementText('viewTemperaturaInicial', formatarValor(certificado.temperatura_inicial));
                setElementText('viewTemperaturaFinal', formatarValor(certificado.temperatura_final));
                setElementText('viewUmidadeInicial', formatarValor(certificado.umidade_inicial));
                setElementText('viewUmidadeFinal', formatarValor(certificado.umidade_final));
                setElementText('viewPressaoInicial', formatarValor(certificado.pressao_inicial));
                setElementText('viewPressaoFinal', formatarValor(certificado.pressao_final));
                setElementText('viewMassaArInicial', formatarValor(certificado.massa_ar_inicial));
                setElementText('viewMassaArFinal', formatarValor(certificado.massa_ar_final));
            } else if (sectionCondicoes) {
                sectionCondicoes.style.display = 'none';
            }
            
            // Equipamento Auxiliar
            const temEquipamentoAuxiliar = certificado.equipamento_auxiliar || certificado.identificacao_auxiliar ||
                                           certificado.certificado_auxiliar || certificado.validade_auxiliar;
            
            const sectionEquipamentoAuxiliar = document.getElementById('sectionEquipamentoAuxiliar');
            if (temEquipamentoAuxiliar && sectionEquipamentoAuxiliar) {
                sectionEquipamentoAuxiliar.style.display = 'block';
                setElementText('viewEquipamentoAuxiliar', formatarValor(certificado.equipamento_auxiliar));
                setElementText('viewIdentificacaoAuxiliar', formatarValor(certificado.identificacao_auxiliar));
                setElementText('viewCertificadoAuxiliar', formatarValor(certificado.certificado_auxiliar));
                setElementText('viewValidadeAuxiliar', formatarData(certificado.validade_auxiliar));
            } else if (sectionEquipamentoAuxiliar) {
                sectionEquipamentoAuxiliar.style.display = 'none';
            }
        
            // Pesos Padrão Utilizados
            const containerPesosPadrao = document.getElementById('viewPesosPadraoContainer');
            const sectionPesosPadrao = document.getElementById('sectionPesosPadrao');
            
            if (containerPesosPadrao && sectionPesosPadrao) {
                if (certificado.pesos_padrao && Array.isArray(certificado.pesos_padrao) && certificado.pesos_padrao.length > 0) {
                    sectionPesosPadrao.style.display = 'block';
                    containerPesosPadrao.innerHTML = '';
                    
                    // Ordenar pesos padrão por ordem
                    const pesosOrdenados = [...certificado.pesos_padrao].sort((a, b) => {
                        if (a.ordem !== b.ordem) {
                            return a.ordem - b.ordem;
                        }
                        return a.id - b.id;
                    });
                    
                    // Criar tabela para exibir os pesos padrão
                    const table = document.createElement('table');
                    table.className = 'table table-sm table-bordered';
                    table.innerHTML = `
                        <thead class="table-light">
                            <tr>
                                <th style="width: 5%;">Ordem</th>
                                <th style="width: 25%;">Identificação</th>
                                <th style="width: 30%;">Certificado</th>
                                <th style="width: 20%;">Validade</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${pesosOrdenados.map(peso => `
                                <tr>
                                    <td>${formatarValor(peso.ordem)}</td>
                                    <td>${formatarValor(peso.identificacao)}</td>
                                    <td>${formatarValor(peso.certificado)}</td>
                                    <td>${formatarData(peso.validade)}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    `;
                    containerPesosPadrao.appendChild(table);
                } else {
                    sectionPesosPadrao.style.display = 'none';
                    containerPesosPadrao.innerHTML = '';
                }
            }
            
            // Ensaios de Excentricidade
            const containerExcentricidade = document.getElementById('viewEnsaiosExcentricidadeContainer');
            const sectionExcentricidade = document.getElementById('sectionEnsaiosExcentricidade');
            
            if (containerExcentricidade && sectionExcentricidade) {
                if (certificado.ensaios_excentricidade && Array.isArray(certificado.ensaios_excentricidade) && certificado.ensaios_excentricidade.length > 0) {
                    sectionExcentricidade.style.display = 'block';
                    containerExcentricidade.innerHTML = '';
                    
                    // Ordenar por ponto (A, B, C, D, E)
                    const ensaiosOrdenados = [...certificado.ensaios_excentricidade].sort((a, b) => {
                        const ordem = ['A', 'B', 'C', 'D', 'E'];
                        return ordem.indexOf(a.ponto) - ordem.indexOf(b.ponto);
                    });
                    
                    const table = document.createElement('table');
                    table.className = 'table table-sm table-bordered';
                    table.innerHTML = `
                        <thead class="table-light">
                            <tr>
                                <th>Ponto</th>
                                <th>Carga</th>
                                <th>Leitura Antes</th>
                                <th>Erro Antes</th>
                                <th>Leitura Depois</th>
                                <th>Erro Depois</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${ensaiosOrdenados.map(ensaio => `
                                <tr>
                                    <td>${formatarValor(ensaio.ponto)}</td>
                                    <td>${formatarValor(ensaio.carga)}</td>
                                    <td>${formatarValor(ensaio.leitura_antes)}</td>
                                    <td>${formatarValor(ensaio.erro_antes)}</td>
                                    <td>${formatarValor(ensaio.leitura_depois)}</td>
                                    <td>${formatarValor(ensaio.erro_depois)}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    `;
                    containerExcentricidade.appendChild(table);
                } else {
                    sectionExcentricidade.style.display = 'none';
                    containerExcentricidade.innerHTML = '';
                }
            }
            
            // Resultados dos Ensaios
            const containerResultados = document.getElementById('viewResultadosEnsaiosContainer');
            const sectionResultados = document.getElementById('sectionResultadosEnsaios');
            
            if (containerResultados && sectionResultados) {
                if (certificado.resultados_ensaios && Array.isArray(certificado.resultados_ensaios) && certificado.resultados_ensaios.length > 0) {
                    sectionResultados.style.display = 'block';
                    containerResultados.innerHTML = '';
                    
                    // Ordenar por ponto (1, 2, 3, 4, 5)
                    const resultadosOrdenados = [...certificado.resultados_ensaios].sort((a, b) => {
                        return (a.ponto || 0) - (b.ponto || 0);
                    });
                    
                    const table = document.createElement('table');
                    table.className = 'table table-sm table-bordered';
                    table.innerHTML = `
                        <thead class="table-light">
                            <tr>
                                <th>Ponto</th>
                                <th>Carga</th>
                                <th>Leitura Antes</th>
                                <th>Erro Antes</th>
                                <th>Leitura Depois</th>
                                <th>Erro Depois</th>
                                <th>Incerteza</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${resultadosOrdenados.map(resultado => `
                                <tr>
                                    <td>${formatarValor(resultado.ponto)}</td>
                                    <td>${formatarValor(resultado.carga)}</td>
                                    <td>${formatarValor(resultado.leitura_antes)}</td>
                                    <td>${formatarValor(resultado.erro_antes)}</td>
                                    <td>${formatarValor(resultado.leitura_depois)}</td>
                                    <td>${formatarValor(resultado.erro_depois)}</td>
                                    <td>${formatarValor(resultado.incerteza)}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    `;
                    containerResultados.appendChild(table);
                } else {
                    sectionResultados.style.display = 'none';
                    containerResultados.innerHTML = '';
                }
            }
            
            // Ensaios de Mobilidade
            const containerMobilidade = document.getElementById('viewEnsaiosMobilidadeContainer');
            const sectionMobilidade = document.getElementById('sectionEnsaiosMobilidade');
            
            if (containerMobilidade && sectionMobilidade) {
                if (certificado.ensaios_mobilidade && Array.isArray(certificado.ensaios_mobilidade) && certificado.ensaios_mobilidade.length > 0) {
                    sectionMobilidade.style.display = 'block';
                    containerMobilidade.innerHTML = '';
                    
                    const mobilidade = certificado.ensaios_mobilidade[0]; // Geralmente há apenas um
                    const table = document.createElement('table');
                    table.className = 'table table-sm table-bordered';
                    table.innerHTML = `
                        <thead class="table-light">
                            <tr>
                                <th>Carga</th>
                                <th>Sobrecarga</th>
                                <th>Leitura Antes</th>
                                <th>Leitura Depois</th>
                                <th>Padrão Utilizado</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>${formatarValor(mobilidade.carga)}</td>
                                <td>${formatarValor(mobilidade.sobrecarga)}</td>
                                <td>${formatarValor(mobilidade.leitura_antes)}</td>
                                <td>${formatarValor(mobilidade.leitura_depois)}</td>
                                <td>${formatarValor(mobilidade.padrao_utilizado)}</td>
                            </tr>
                        </tbody>
                    `;
                    containerMobilidade.appendChild(table);
                } else {
                    sectionMobilidade.style.display = 'none';
                    containerMobilidade.innerHTML = '';
                }
            }
        
            // Informações do Sistema
            setElementText('viewId', formatarValor(certificado.id));
            setElementText('viewCreatedAt', formatarData(certificado.created_at));
            setElementText('viewUpdatedAt', formatarData(certificado.updated_at));
            
            // Botão de editar
            const btnEditar = document.getElementById('btnEditarCertificado');
            if (btnEditar) {
                btnEditar.href = `/certificados/editar/${certificado.id}`;
            }
            
            // Reinicializar ícones Feather com verificação robusta e tratamento de erros
            setTimeout(() => {
                try {
                    if (typeof feather !== 'undefined' && feather && typeof feather.replace === 'function') {
                        feather.replace();
                    } else if (window.feather && typeof window.feather.replace === 'function') {
                        window.feather.replace();
                    }
                } catch (error) {
                    // Ignorar erro ao renderizar ícones
                }
            }, 100);
        } catch (error) {
            // Ignorar erro silenciosamente
        }
    }
    
    abrirModalVisualizacao() {
        const modal = document.getElementById('modalVisualizarCertificado');
        if (modal) {
            modal.style.display = 'flex';
            document.body.style.overflow = 'hidden';
        }
    }
    
    async confirmarExclusao() {
        try {
            const response = await fetch(`/api/v1/certificados/${this.certificadoParaExcluir}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${this.getToken()}`
                }
            });
            
            if (response.ok) {
                this.mostrarAlerta('Certificado excluído com sucesso!', 'success');
                
                // Fechar modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('modalConfirmacao'));
                if (modal) {
                    modal.hide();
                }
                
                // Limpar referência
                this.certificadoParaExcluir = null;
                
                this.carregarCertificados();
                this.carregarEstatisticas();
            } else {
                this.logApiCall(`/api/v1/certificados/${this.certificadoParaExcluir}`, response.status);
                this.mostrarAlerta('Erro ao excluir certificado', 'error');
            }
        } catch (error) {
            this.mostrarAlerta('Erro ao excluir certificado', 'error');
        }
    }
    
    getToken() {
        return getToken();
    }
    
    mostrarAlerta(mensagem, tipo) {
        return mostrarAlerta(mensagem, tipo, this.logger);
    }
    
    // ============================================================================
    // FUNÇÕES PARA GERENCIAR PESOS PADRÃO
    // ============================================================================
    
    async carregarPesosPadrao() {
        this.pesosPadrao = await featCarregarPesosPadrao(this.logger, this.getToken.bind(this));
    }
    
    async adicionarPesoPadrao() {
        // Garantir que os pesos padrão estão carregados antes de adicionar
        if (!this.pesosPadrao || this.pesosPadrao.length === 0) {
            await this.carregarPesosPadrao();
        }
        
        const resultado = featAdicionarPesoPadrao(
            this.pesosSelecionados,
            this.proximoIdPeso,
            this.pesosPadrao,
            this.mostrarAlerta.bind(this),
            this.logger
        );
        if (resultado) {
            this.pesosSelecionados = resultado.pesosSelecionados;
            this.proximoIdPeso = resultado.proximoIdPeso;
        }
    }
    
    selecionarPesoPadrao(pesoId) {
        this.pesosSelecionados = featSelecionarPesoPadrao(pesoId, this.pesosPadrao, this.pesosSelecionados);
    }
    
    removerPesoPadrao(pesoId) {
        this.pesosSelecionados = featRemoverPesoPadrao(pesoId, this.pesosSelecionados);
    }
    
    coletarPesosPadrao() {
        return featColetarPesosPadrao(this.pesosSelecionados);
    }
    
    limparPesosPadrao() {
        featLimparPesosPadrao();
        this.pesosSelecionados = [];
        this.proximoIdPeso = 1;
    }
    
    async carregarEstatisticas() {
        const data = await apiCarregarEstatisticas(this.logger);
            this.atualizarEstatisticas(data);
    }
    
    atualizarEstatisticas(data) {
        apiAtualizarEstatisticas(data);
    }
}

// Funções globais para compatibilidade - usar módulo utils/globals.js
// Serão inicializadas após criar instância do CertificadosManager

// ============================================================================
// FUNÇÕES PARA TERMOBAROHIGROMETRO (usando módulo features/termobarohigrometros.js)
// ============================================================================

// Função global para carregar termobarohigrometros (usando módulo)
async function carregarTermobarohigrometros() {
    const logger = window.certificadosManager ? window.certificadosManager.logger : null;
    await featCarregarTermobarohigrometros(logger);
}

// Expor função no window para compatibilidade
window.carregarTermobarohigrometros = carregarTermobarohigrometros;

// Preencher dados do termobarohigrometro selecionado (usando módulo)
window.preencherDadosTermobarohigrometro = featPreencherDadosTermobarohigrometro;

// ============================================================================
// FUNÇÕES PARA ENSAIOS DE EXCENTRICIDADE DINÂMICOS (usando módulo)
// ============================================================================

// Expor funções globais usando módulo
window.adicionarLinhaExcentricidade = function() {
    const mostrarAlertaFn = window.certificadosManager?.mostrarAlerta?.bind(window.certificadosManager);
    featAdicionarLinhaExcentricidade(mostrarAlertaFn);
};

window.removerLinhaExcentricidade = featRemoverLinhaExcentricidade;

// ============================================================================
// FUNÇÕES PARA RESULTADOS DOS ENSAIOS DINÂMICOS (usando módulo)
// ============================================================================

// Expor funções globais usando módulo
window.adicionarLinhaResultado = function() {
    const mostrarAlertaFn = window.certificadosManager?.mostrarAlerta?.bind(window.certificadosManager);
    featAdicionarLinhaResultado(mostrarAlertaFn);
};

window.removerLinhaResultado = featRemoverLinhaResultado;

// ============================================================================
// FUNÇÕES PARA INSPETORES/APROVADORES
// ============================================================================

// Função auxiliar para obter token do cookie - usar getToken do módulo utils/helpers.js
// getTokenFromCookie removido, usar getToken() importado

// Carregar inspetores/aprovadores (usando módulo)
async function carregarInspetores() {
    const logger = window.certificadosManager ? window.certificadosManager.logger : null;
    await featCarregarInspetoresAprovadores(logger);
}

// Expor função com nome alternativo para compatibilidade
window.carregarInspetoresAprovadores = carregarInspetores;

// Preencher dados do inspetor selecionado (usando módulo)
window.preencherDadosInspetor = featPreencherDadosInspetor;

// Fechar modal ao clicar no overlay
document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('modalVisualizarCertificado');
    if (modal) {
        const overlay = modal.querySelector('.modal-visualizar-overlay');
        if (overlay) {
            overlay.addEventListener('click', function(e) {
                if (e.target === overlay) {
                    window.fecharModalVisualizacaoCertificado();
                }
            });
        }
    }
});

// Inicializar quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', function() {
    window.certificadosManager = new CertificadosManager();
    // Configurar funções globais de compatibilidade
    setupGlobalFunctions(window.certificadosManager);
}); 