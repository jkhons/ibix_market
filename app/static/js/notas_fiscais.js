// PDV Ibix - Notas Fiscais JavaScript
class NotasFiscaisManager {
    constructor() {
        this.notaSelecionada = null;
        this.empresas = [];
        this.clientes = [];
        this._canEditFiscal = true;
        this._userId = null;
        console.log('🔧 NotasFiscaisManager - Inicializando...');
    }

    getUserId() {
        if (this._userId != null) return this._userId;
        const el = document.getElementById('notas-fiscais-page');
        if (el && el.dataset.userId) {
            const n = parseInt(el.dataset.userId, 10);
            this._userId = isNaN(n) ? null : n;
        }
        return this._userId;
    }

    getCanEditFiscal() {
        const el = document.getElementById('notas-fiscais-page');
        if (el && el.dataset.canEditFiscal !== undefined) {
            this._canEditFiscal = el.dataset.canEditFiscal === 'true';
        }
        return this._canEditFiscal;
    }

    getCanBaixarXml() {
        const el = document.getElementById('notas-fiscais-page');
        return el && el.dataset.canBaixarXml === 'true';
    }

    getCanBaixarPdf() {
        const el = document.getElementById('notas-fiscais-page');
        return el && el.dataset.canBaixarPdf === 'true';
    }
    
    init() {
        console.log('🔧 Inicializando NotasFiscaisManager...');
        this.getCanEditFiscal();
        this.getUserId();
        this.setupEventListeners();
        this.carregarEmpresas();
        this.carregarNotasFiscais();
        window.fecharModalDetalhesNota = () => this.fecharModalDetalhesNota();
        window.fecharModalNovaNota = () => this.fecharModalNovaNota();
    }

    fecharModalDetalhesNota() {
        const modal = document.getElementById('modalDetalhesNotaCustom');
        if (modal) {
            modal.style.display = 'none';
            document.body.style.overflow = '';
        }
    }
    
    setupEventListeners() {
        console.log('🔧 Configurando event listeners...');
        
        // Filtros com debounce
        let timeoutId;
        ['filtroEmpresa', 'filtroTipo', 'filtroStatus', 'filtroDataInicio', 'filtroDataFim', 'filtroPedidoId'].forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.addEventListener('change', () => {
                    clearTimeout(timeoutId);
                    timeoutId = setTimeout(() => this.aplicarFiltros(), 500);
                });
            }
        });
        const modalDetalhes = document.getElementById('modalDetalhesNotaCustom');
        if (modalDetalhes) {
            modalDetalhes.addEventListener('click', (e) => {
                if (e.target === modalDetalhes) this.fecharModalDetalhesNota();
            });
        }
        const modalNovaNota = document.getElementById('modalNovaNotaFiscalCustom');
        if (modalNovaNota) {
            modalNovaNota.addEventListener('click', (e) => {
                if (e.target === modalNovaNota) this.fecharModalNovaNota();
            });
        }
        const selectEmpresaNovaNota = document.getElementById('novaNotaEmpresaId');
        if (selectEmpresaNovaNota) {
            selectEmpresaNovaNota.addEventListener('change', () => this.atualizarHintCstCsosn());
        }
    }

    atualizarHintCstCsosn() {
        const el = document.getElementById('novaNotaHintCstCsosn');
        if (!el) return;
        const empresaIdVal = document.getElementById('novaNotaEmpresaId')?.value;
        if (!empresaIdVal) {
            el.textContent = '';
            return;
        }
        const empresaId = parseInt(empresaIdVal, 10);
        const empresa = this.empresas.find(e => e.id === empresaId);
        const crt = empresa && (empresa.crt !== undefined && empresa.crt !== null) ? parseInt(empresa.crt, 10) : null;
        if (crt === 1 || crt === 2) {
            el.textContent = 'Empresa no Simples Nacional: preencha CSOSN nos itens (ex: 102, 202, 900).';
        } else if (crt === 3) {
            el.textContent = 'Empresa em Regime Normal: preencha CST ICMS nos itens (ex: 00).';
        } else {
            el.textContent = 'Conforme regime da empresa: CST ICMS (Regime Normal) ou CSOSN (Simples Nacional).';
        }
    }
    
    /**
     * Token legível no JS (sessionStorage pós-login). Cookies PDV são HttpOnly —
     * não aparecem em document.cookie; a sessão vale via credentials: 'include'.
     */
    getToken() {
        if (typeof window.getAuthToken === 'function') {
            return window.getAuthToken();
        }
        try {
            return sessionStorage.getItem('pdv_solumatica_token')
                || sessionStorage.getItem('pdv_automscale_token')
                || null;
        } catch (_) {
            return null;
        }
    }

    /** Fetch autenticado: cookie HttpOnly + Bearer opcional (sessionStorage). */
    apiFetch(url, options = {}) {
        if (typeof window.authenticatedFetch === 'function') {
            return window.authenticatedFetch(url, options);
        }
        const token = this.getToken();
        const headers = { ...(options.headers || {}) };
        if (token) headers['Authorization'] = `Bearer ${token}`;
        return fetch(url, {
            credentials: 'include',
            ...options,
            headers,
        });
    }
    
    async carregarEmpresas() {
        try {
            const response = await this.apiFetch('/api/v1/fiscal/empresa');
            
            if (!response.ok) {
                if (response.status === 401) {
                    throw new Error('Sessão expirada. Faça login novamente.');
                }
                throw new Error(`Erro ao carregar empresas (${response.status})`);
            }
            
            const empresas = await response.json();
            this.empresas = Array.isArray(empresas) ? empresas : [];
            
            // Preencher select de empresas
            const selectEmpresa = document.getElementById('filtroEmpresa');
            if (selectEmpresa) {
                selectEmpresa.innerHTML = '<option value="">Todas as empresas</option>';
                this.empresas.forEach(empresa => {
                    const option = document.createElement('option');
                    option.value = empresa.id;
                    option.textContent = empresa.razao_social || empresa.nome_fantasia || `Empresa ${empresa.id}`;
                    selectEmpresa.appendChild(option);
                });
            }
        } catch (error) {
            console.error('❌ Erro ao carregar empresas:', error);
        }
    }
    
    async carregarNotasFiscais() {
        console.log('📥 Carregando notas fiscais...');
        try {
            const params = new URLSearchParams();
            
            const empresaId = document.getElementById('filtroEmpresa')?.value;
            const tipo = document.getElementById('filtroTipo')?.value;
            const status = document.getElementById('filtroStatus')?.value;
            const dataInicio = document.getElementById('filtroDataInicio')?.value;
            const dataFim = document.getElementById('filtroDataFim')?.value;
            const pedidoId = document.getElementById('filtroPedidoId')?.value;
            
            if (empresaId) params.append('empresa_id', empresaId);
            if (tipo) params.append('tipo', tipo);
            if (status) params.append('status', status);
            if (dataInicio) params.append('data_inicio', dataInicio);
            if (dataFim) params.append('data_fim', dataFim);
            if (pedidoId) params.append('pedido_id', pedidoId);
            
            const url = `/api/v1/fiscal/notas-fiscais${params.toString() ? '?' + params.toString() : ''}`;
            
            const response = await this.apiFetch(url);
            
            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                const detail = typeof error.detail === 'string' ? error.detail : (Array.isArray(error.detail) ? error.detail.join(' ') : error.detail?.msg || null);
                const msg = detail || (response.status === 401 ? 'Sessão expirada. Faça login novamente.' : response.status === 403 ? 'Sem permissão para acessar notas fiscais.' : `Erro ao carregar notas fiscais (${response.status}).`);
                throw new Error(msg);
            }
            
            const notas = await response.json();
            console.log('📊 Notas fiscais recebidas:', notas);
            
            // Garantir que notas é um array
            const notasArray = Array.isArray(notas) ? notas : [];
            this.renderizarTabela(notasArray);
            
        } catch (error) {
            console.error('❌ Erro ao carregar notas fiscais:', error);
            this.mostrarAlerta(error.message || 'Erro ao carregar notas fiscais. Tente novamente.', 'danger');
            
            // Mostrar mensagem na tabela em caso de erro
            const tbody = document.getElementById('tabelaNotasFiscais');
            if (tbody) {
                tbody.innerHTML = `
                <tr>
                    <td colspan="10" class="text-center text-danger">
                            ${(error.message || 'Erro ao carregar notas fiscais. Tente novamente.').replace(/</g, '&lt;')}
                        </td>
                    </tr>
                `;
            }
        }
    }
    
    aplicarFiltros() {
        this.carregarNotasFiscais();
    }
    
    renderizarTabela(notas) {
        const tbody = document.getElementById('tabelaNotasFiscais');
        if (!tbody) return;
        
        if (!notas || notas.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="10" class="text-center text-muted">
                        Nenhuma nota fiscal encontrada.
                    </td>
                </tr>
            `;
            return;
        }
        
        const canEdit = this.getCanEditFiscal();
        tbody.innerHTML = notas.map(nota => {
            const dataEmissao = nota.data_emissao ? (typeof formatarDataApenas === 'function' ? formatarDataApenas(nota.data_emissao) : nota.data_emissao) : '-';
            const valorTotal = nota.valor_total ? parseFloat(nota.valor_total).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }) : 'R$ 0,00';
            const statusBadge = this.getStatusBadge(nota.status);
            const tipoBadge = this.getTipoBadge(nota.tipo);
            const chaveAcesso = nota.chave_acesso || '-';
            const clienteNome = nota.cliente ? (nota.cliente.nome || nota.cliente.razao_social || 'Cliente') : 'Consumidor Final';
            const origemTexto = nota.origem_documento ? (nota.origem_documento === 'orcamento' ? 'Orçamento' : nota.origem_documento === 'venda_balcao' ? 'Venda' : nota.origem_documento === 'ordem_servico' ? 'OS' : nota.origem_documento === 'venda_marketplace' ? 'Marketplace' : nota.origem_documento) : '-';
            const origemCel = nota.pedido_id
                ? `<a href="/negocio/pedidos/${nota.pedido_id}" target="_blank" title="Ver pedido">Pedido #${nota.pedido_id}</a>`
                : (origemTexto !== '-' ? origemTexto : '-');
            const podeValidarEnviar = (nota.status === 'rascunho' || nota.status === 'pendente') && canEdit;
            const podeReenviar = (nota.status === 'rejeitado') && canEdit;
            const podeCancelar = nota.status === 'autorizado' && canEdit;
            const podeDownload = nota.status === 'autorizado' || nota.chave_acesso;
            const canPdf = this.getCanBaixarPdf();
            const numeroExibicao = this.formatarNumeroExibicao(nota.numero);
            const isRv = /^RASCUNHO-VENDA-\d+$/i.test(nota.numero || '');
            const badgeClasse = isRv ? 'bg-secondary' : 'bg-primary';
            const numeroLink = `<a href="#" class="badge badge-numero ${badgeClasse} text-decoration-none" onclick="notasFiscaisManager.visualizarNota(${nota.id}); return false;" title="Visualizar">${numeroExibicao}</a>`;
            return `
                <tr>
                    <td>${numeroLink}</td>
                    <td>${nota.serie || '1'}</td>
                    <td>${tipoBadge}</td>
                    <td>${dataEmissao}</td>
                    <td>${clienteNome}</td>
                    <td>${valorTotal}</td>
                    <td>${statusBadge}</td>
                    <td>${origemCel}</td>
                    <td><small>${chaveAcesso}</small></td>
                    <td>
                        ${podeDownload ? `
                            <button class="btn btn-sm btn-outline-info" onclick="notasFiscaisManager.visualizarPdfPorId(${nota.id})" title="Ver nota renderizada (abre em nova aba)">
                                <i class="align-middle" data-feather="file-text"></i>
                            </button>
                        ` : ''}
                        ${podeValidarEnviar ? `
                            <button class="btn btn-sm btn-outline-warning" onclick="notasFiscaisManager.validarNotaPorId(${nota.id})" title="Validar">
                                <i class="align-middle" data-feather="check-circle"></i>
                            </button>
                            <button class="btn btn-sm btn-outline-success" onclick="notasFiscaisManager.enviarNotaPorId(${nota.id})" title="Enviar">
                                <i class="align-middle" data-feather="send"></i>
                            </button>
                        ` : ''}
                        ${podeReenviar ? `
                            <button class="btn btn-sm btn-outline-success" onclick="notasFiscaisManager.enviarNotaPorId(${nota.id})" title="Reenviar nota rejeitada à SEFAZ">
                                <i class="align-middle" data-feather="send"></i>
                            </button>
                        ` : ''}
                        ${podeDownload ? `
                            <div class="dropdown d-inline">
                                <button class="btn btn-sm btn-outline-secondary dropdown-toggle" type="button" data-bs-toggle="dropdown" title="Baixar">
                                    <i class="align-middle" data-feather="download"></i>
                                </button>
                                <ul class="dropdown-menu dropdown-menu-end">
                                    <li><a class="dropdown-item" href="#" onclick="notasFiscaisManager.downloadXmlPorId(${nota.id}); return false;">XML</a></li>
                                    <li><a class="dropdown-item" href="#" onclick="notasFiscaisManager.downloadPdfPorId(${nota.id}); return false;">PDF</a></li>
                                </ul>
                            </div>
                        ` : ''}
                        ${podeCancelar ? `
                            <button class="btn btn-sm btn-danger" onclick="notasFiscaisManager.confirmarCancelamento(${nota.id})" title="Cancelar">
                                <i class="align-middle" data-feather="x-circle"></i>
                            </button>
                        ` : ''}
                    </td>
                </tr>
            `;
        }).join('');
        
        // Renderizar Feather Icons na tabela (ícones nos botões de ação)
        setTimeout(() => {
            const container = document.getElementById('tabelaNotasFiscais');
            if (container && typeof feather !== 'undefined' && feather && typeof feather.replace === 'function') {
                try {
                    feather.replace();
                } catch (e) {
                    console.warn('Erro ao renderizar Feather Icons:', e);
                }
            }
        }, 200);
    }
    
    getStatusBadge(status) {
        const badges = {
            'rascunho': '<span class="badge bg-secondary">Rascunho</span>',
            'pendente': '<span class="badge bg-warning">Pendente</span>',
            'autorizado': '<span class="badge bg-success">Autorizado</span>',
            'cancelado': '<span class="badge bg-danger">Cancelado</span>',
            'rejeitado': '<span class="badge bg-danger">Rejeitado</span>',
            'denegado': '<span class="badge bg-secondary">Denegado</span>'
        };
        return badges[status] || `<span class="badge bg-secondary">${status || '-'}</span>`;
    }
    
    /** Formata número de rascunho para exibição: RASCUNHO-VENDA-123 → RV-123 */
    formatarNumeroExibicao(numero) {
        if (!numero || typeof numero !== 'string') return numero || '-';
        const m = numero.match(/^RASCUNHO-VENDA-(\d+)$/i);
        return m ? `RV-${m[1]}` : numero;
    }

    getTipoBadge(tipo) {
        const badges = {
            'NFe': '<span class="badge bg-primary">NF-e</span>',
            'NFCe': '<span class="badge bg-info">NFC-e</span>'
        };
        return badges[tipo] || `<span class="badge bg-secondary">${tipo || '-'}</span>`;
    }
    
    async visualizarNota(notaId) {
        try {
            const response = await this.apiFetch(`/api/v1/fiscal/notas-fiscais/${notaId}`);
            
            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                const detail = typeof error.detail === 'string' ? error.detail : null;
                throw new Error(detail || (response.status === 401 ? 'Sessão expirada. Faça login novamente.' : `Erro ao carregar nota fiscal (${response.status})`));
            }
            
            const nota = await response.json();
            this.notaSelecionada = nota;
            
            this.exibirDetalhesNota(nota);
            
        } catch (error) {
            console.error('❌ Erro ao visualizar nota:', error);
            this.mostrarAlerta(error.message || 'Erro ao carregar detalhes da nota fiscal', 'danger');
        }
    }
    
    exibirDetalhesNota(nota) {
        const modalEl = document.getElementById('modalDetalhesNotaCustom');
        const conteudo = document.getElementById('conteudoDetalhesNota');
        const btnValidar = document.getElementById('btnValidarNota');
        const btnEnviar = document.getElementById('btnEnviarNota');
        const btnVerNotaRenderizada = document.getElementById('btnVerNotaRenderizada');
        const btnDownloadXml = document.getElementById('btnDownloadXmlNota');
        const btnDownloadPdf = document.getElementById('btnDownloadPdfNota');
        const btnCancelar = document.getElementById('btnCancelarNota');
        const canEdit = this.getCanEditFiscal();
        const podeValidarEnviar = (nota.status === 'rascunho' || nota.status === 'pendente');
        const podeReenviar = (nota.status === 'rejeitado');
        const podeEnviarOuReenviar = (podeValidarEnviar || podeReenviar) && canEdit;
        const podeDownload = nota.status === 'autorizado' || nota.chave_acesso;
        const canPdf = this.getCanBaixarPdf();
        if (btnValidar) btnValidar.style.display = podeValidarEnviar && canEdit ? 'inline-block' : 'none';
        if (btnEnviar) {
            btnEnviar.style.display = podeEnviarOuReenviar ? 'inline-block' : 'none';
            const spanEnviar = btnEnviar.querySelector('.ms-1');
            if (spanEnviar) spanEnviar.textContent = podeReenviar ? 'Reenviar' : 'Enviar';
        }
        if (btnVerNotaRenderizada) btnVerNotaRenderizada.style.display = podeDownload && canPdf ? 'inline-block' : 'none';
        if (btnDownloadXml) btnDownloadXml.style.display = podeDownload ? 'inline-block' : 'none';
        if (btnDownloadPdf) btnDownloadPdf.style.display = podeDownload && canPdf ? 'inline-block' : 'none';
        if (btnCancelar) btnCancelar.style.display = (nota.status === 'autorizado' && canEdit) ? 'inline-block' : 'none';
        
        if (!conteudo) return;
        
        const dataEmissao = nota.data_emissao ? (typeof formatarDataApenas === 'function' ? formatarDataApenas(nota.data_emissao) : nota.data_emissao) : '-';
        const dataSaida = nota.data_saida ? (typeof formatarDataApenas === 'function' ? formatarDataApenas(nota.data_saida) : nota.data_saida) : '-';
        const dataAutorizacao = nota.data_autorizacao ? (typeof formatarDataApenas === 'function' ? formatarDataApenas(nota.data_autorizacao) : nota.data_autorizacao) : '-';
        
        const valorTotal = nota.valor_total ? parseFloat(nota.valor_total).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }) : 'R$ 0,00';
        const valorProdutos = nota.valor_produtos ? parseFloat(nota.valor_produtos).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }) : 'R$ 0,00';
        const valorDesconto = nota.valor_desconto ? parseFloat(nota.valor_desconto).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }) : 'R$ 0,00';
        const valorICMS = nota.valor_icms ? parseFloat(nota.valor_icms).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }) : 'R$ 0,00';
        
        const clienteNome = nota.cliente ? (nota.cliente.nome || nota.cliente.razao_social || 'Cliente') : 'Consumidor Final';
        const empresaNome = nota.empresa ? (nota.empresa.razao_social || nota.empresa.nome_fantasia || 'Empresa') : '-';
        const ambienteTexto = nota.ambiente === 'homologacao' ? 'Homologação' : 'Produção';
        
        conteudo.innerHTML = `
            <h6 class="mb-2">Dados da nota</h6>
            <table class="table table-sm table-bordered mb-3">
                <tbody>
                    <tr><th style="width:28%;">Número / Série</th><td>${this.formatarNumeroExibicao(nota.numero)} / ${nota.serie || '1'}</td><th>Tipo / Modelo</th><td>${this.getTipoBadge(nota.tipo)} ${nota.modelo ? '· ' + nota.modelo : ''}</td></tr>
                    <tr><th>Status</th><td>${this.getStatusBadge(nota.status)}</td><th>Ambiente</th><td>${ambienteTexto}</td></tr>
                    <tr><th>Data emissão</th><td>${dataEmissao}</td><th>Data saída</th><td>${dataSaida || '-'}</td></tr>
                    <tr><th>Empresa (emissor)</th><td colspan="3">${empresaNome}</td></tr>
                    <tr><th>Cliente (destinatário)</th><td colspan="3">${clienteNome}</td></tr>
                    <tr><th>Chave de acesso</th><td colspan="3"><small class="chave-acesso-truncada" title="${(nota.chave_acesso || '-').replace(/"/g, '&quot;')}">${nota.chave_acesso || '-'}</small></td></tr>
                    <tr><th>Protocolo</th><td>${nota.protocolo_autorizacao || '-'}</td><th>Data autorização</th><td>${dataAutorizacao || '-'}</td></tr>
                    ${nota.mensagem_retorno ? `<tr><th>Retorno SEFAZ</th><td colspan="3"><span class="text-danger small">${(nota.mensagem_retorno || '').replace(/</g, '&lt;')}</span></td></tr>` : ''}
                    <tr><th>Valor produtos</th><td>${valorProdutos}</td><th>Desconto</th><td>${valorDesconto}</td></tr>
                    <tr><th>ICMS</th><td>${valorICMS}</td><th><strong>Total</strong></th><td><strong>${valorTotal}</strong></td></tr>
                </tbody>
            </table>
            
            ${nota.itens && nota.itens.length > 0 ? `
                <div class="row mt-3">
                    <div class="col-12">
                        <h6>Itens da Nota</h6>
                        <div class="table-responsive">
                            <table class="table table-sm table-striped">
                                <thead>
                                    <tr>
                                        <th>Item</th>
                                        <th>Descrição</th>
                                        <th>NCM</th>
                                        <th>CFOP</th>
                                        <th>Origem</th>
                                        <th>CST/CSOSN</th>
                                        <th>Qtd</th>
                                        <th>Valor Unit.</th>
                                        <th>Valor Total</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${nota.itens.map(item => `
                                        <tr>
                                            <td>${item.item_numero || '-'}</td>
                                            <td>${item.descricao || '-'}</td>
                                            <td>${item.ncm || '-'}</td>
                                            <td>${item.cfop || '-'}</td>
                                            <td>${item.origem != null && item.origem !== '' ? item.origem : '-'}</td>
                                            <td>${item.csosn || item.cst_icms || '-'}</td>
                                            <td>${item.quantidade ? parseFloat(item.quantidade).toLocaleString('pt-BR') : '-'}</td>
                                            <td>${item.valor_unitario ? parseFloat(item.valor_unitario).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }) : '-'}</td>
                                            <td>${item.valor_total ? parseFloat(item.valor_total).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }) : '-'}</td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            ` : ''}
            
            ${nota.observacoes ? `
                <div class="mt-3">
                    <h6>Observações</h6>
                    <p class="mb-0">${(nota.observacoes || '').replace(/</g, '&lt;').replace(/>/g, '&gt;')}</p>
                </div>
            ` : ''}
        `;
        
        if (modalEl) {
            modalEl.style.display = 'block';
            document.body.style.overflow = 'hidden';
        }
    }

    fecharModalNovaNota() {
        const modal = document.getElementById('modalNovaNotaFiscalCustom');
        if (modal) {
            modal.style.display = 'none';
            document.body.style.overflow = '';
        }
    }

    confirmarCancelamento(notaId) {
        if (confirm('Tem certeza que deseja cancelar esta nota fiscal?')) {
            this.cancelarNota(notaId);
        }
    }
    
    async cancelarNota(notaId) {
        const id = notaId != null ? notaId : (this.notaSelecionada && this.notaSelecionada.id);
        if (!id) {
            this.mostrarAlerta('Nenhuma nota selecionada', 'warning');
            return;
        }
        if (!confirm('Tem certeza que deseja cancelar esta nota fiscal?')) return;
        try {
            const response = await this.apiFetch(`/api/v1/fiscal/notas-fiscais/${id}/cancelar`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ justificativa: 'Cancelamento solicitado pelo usuário' })
            });
            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                const detail = typeof error.detail === 'string' ? error.detail : null;
                throw new Error(detail || (response.status === 401 ? 'Sessão expirada. Faça login novamente.' : `Erro ao cancelar nota fiscal (${response.status})`));
            }
            this.mostrarAlerta('Nota fiscal cancelada com sucesso', 'success');
            this.carregarNotasFiscais();
            if (window.fecharModalDetalhesNota) window.fecharModalDetalhesNota();
        } catch (error) {
            console.error('❌ Erro ao cancelar nota:', error);
            this.mostrarAlerta(error.message || 'Erro ao cancelar nota fiscal', 'danger');
        }
    }

    validarNota() { if (this.notaSelecionada && this.notaSelecionada.id) this.validarNotaPorId(this.notaSelecionada.id); }
    enviarNota() { if (this.notaSelecionada && this.notaSelecionada.id) this.enviarNotaPorId(this.notaSelecionada.id); }
    downloadXmlNota() { if (this.notaSelecionada && this.notaSelecionada.id) this.downloadXmlPorId(this.notaSelecionada.id); }
    downloadPdfNota() { if (this.notaSelecionada && this.notaSelecionada.id) this.downloadPdfPorId(this.notaSelecionada.id); }
    visualizarPdfNota() { if (this.notaSelecionada && this.notaSelecionada.id) this.visualizarPdfPorId(this.notaSelecionada.id); }

    async validarNotaPorId(notaId) {
        try {
            const response = await this.apiFetch(`/api/v1/fiscal/notas-fiscais/${notaId}/validar`, {
                method: 'POST'
            });
            if (response.status === 401) {
                throw new Error('Sessão expirada. Faça login novamente.');
            }
            const data = await response.json().catch(() => ({}));
            if (data.valido) {
                this.mostrarAlerta('Nota válida para envio.', 'success');
            } else {
                const erros = (data.erros || []).join('; ') || (data.detail || 'Erros de validação');
                this.mostrarAlerta('Erros: ' + erros, 'warning');
            }
        } catch (error) {
            console.error('❌ Erro ao validar nota:', error);
            this.mostrarAlerta(error.message || 'Erro ao validar nota', 'danger');
        }
    }

    async enviarNotaPorId(notaId) {
        try {
            const timeoutMs = 180000; // 3 min (alinhado ao Nginx para emissão SEFAZ)
            const ctrl = new AbortController();
            const timeoutId = setTimeout(() => ctrl.abort(), timeoutMs);
            const response = await this.apiFetch(`/api/v1/fiscal/notas-fiscais/${notaId}/enviar`, {
                method: 'POST',
                signal: ctrl.signal
            }).finally(() => clearTimeout(timeoutId));
            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                const msg = typeof error.detail === 'string' ? error.detail
                    : (Array.isArray(error.detail) ? error.detail.map(d => d.msg || d).join('; ') : error.detail?.msg)
                    || (response.status === 401 ? 'Sessão expirada. Faça login novamente.' : `Erro no envio (${response.status})`);
                throw new Error(msg);
            }
            this.mostrarAlerta('Nota enviada com sucesso.', 'success');
            this.carregarNotasFiscais();
            if (window.fecharModalDetalhesNota) window.fecharModalDetalhesNota();
        } catch (error) {
            console.error('❌ Erro ao enviar nota:', error);
            const msg = error.name === 'AbortError'
                ? 'A emissão demorou (timeout). Verifique na listagem se a nota foi autorizada.'
                : (error.message || 'Erro ao enviar nota');
            this.mostrarAlerta(msg, 'danger');
        }
    }

    async downloadXmlPorId(notaId) {
        try {
            const response = await this.apiFetch(`/api/v1/fiscal/notas-fiscais/${notaId}/download/xml`);
            if (!response.ok) {
                const err = await response.json().catch(() => ({}));
                const msg = typeof err.detail === 'string' ? err.detail : (Array.isArray(err.detail) ? err.detail.map(d => d.msg || d).join(' ') : null);
                throw new Error(msg || (response.status === 401 ? 'Sessão expirada. Faça login novamente.' : (response.status === 404 ? 'Arquivo XML não disponível para esta nota.' : 'Download indisponível.')));
            }
            const blob = await response.blob();
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = `nota-${notaId}.xml`;
            a.click();
            URL.revokeObjectURL(a.href);
        } catch (error) {
            console.error('❌ Erro ao baixar XML:', error);
            this.mostrarAlerta(error.message || 'Erro ao baixar XML', 'danger');
        }
    }

    downloadPdfPorId(notaId) {
        // Link direto com cookie (mesma origem). Evita fetch longo que causa "Client closed request".
        const url = `${window.location.origin}/api/v1/fiscal/notas-fiscais/${notaId}/download/pdf`;
        const a = document.createElement('a');
        a.href = url;
        a.download = `nota-${notaId}.pdf`;
        a.rel = 'noopener';
        a.click();
    }

    visualizarPdfPorId(notaId) {
        // Abre o PDF em nova aba para visualizar (inline=1 faz o servidor enviar Content-Disposition: inline = exibe, não baixa).
        const url = `${window.location.origin}/api/v1/fiscal/notas-fiscais/${notaId}/download/pdf?inline=1`;
        const w = window.open(url, '_blank', 'noopener');
        if (!w) {
            this.mostrarAlerta('Permita pop-ups para abrir a nota em nova aba.', 'warning');
        }
    }

    async abrirModalNovaNota() {
        const modalEl = document.getElementById('modalNovaNotaFiscalCustom');
        if (!modalEl) return;
        const selectEmpresa = document.getElementById('novaNotaEmpresaId');
        if (selectEmpresa) {
            selectEmpresa.innerHTML = '<option value="">Selecione a empresa</option>';
            this.empresas.forEach(emp => {
                const opt = document.createElement('option');
                opt.value = emp.id;
                opt.textContent = emp.razao_social || emp.nome_fantasia || `Empresa ${emp.id}`;
                selectEmpresa.appendChild(opt);
            });
        }
        await this.carregarClientesParaNovaNota();
        const selectCliente = document.getElementById('novaNotaClienteId');
        if (selectCliente) {
            selectCliente.innerHTML = '<option value="">Consumidor final</option>';
            (this.clientes || []).forEach(c => {
                const opt = document.createElement('option');
                opt.value = c.id;
                opt.textContent = c.nome || c.razao_social || `Cliente ${c.id}`;
                selectCliente.appendChild(opt);
            });
        }
        document.getElementById('novaNotaNumero').value = '1';
        const serieEl = document.getElementById('novaNotaSerie');
        if (serieEl) serieEl.value = '1';
        const ambEl = document.getElementById('novaNotaAmbiente');
        if (ambEl) ambEl.value = 'homologacao';
        const now = new Date();
        const pad = n => String(n).padStart(2, '0');
        document.getElementById('novaNotaDataEmissao').value = `${now.getFullYear()}-${pad(now.getMonth()+1)}-${pad(now.getDate())}T${pad(now.getHours())}:${pad(now.getMinutes())}`;
        const tbody = document.getElementById('corpoItensNovaNota');
        if (tbody) tbody.innerHTML = '';
        this.adicionarItemNovaNota();
        this.atualizarTotalNovaNota();
        const hintEl = document.getElementById('novaNotaHintCstCsosn');
        if (hintEl) hintEl.textContent = '';
        modalEl.style.display = 'block';
        document.body.style.overflow = 'hidden';
        setTimeout(() => { if (typeof feather !== 'undefined' && feather.replace) feather.replace(); }, 100);
    }

    async carregarClientesParaNovaNota() {
        try {
            const response = await this.apiFetch('/api/v1/clientes/todos');
            if (response.ok) {
                const list = await response.json();
                this.clientes = Array.isArray(list) ? list : [];
            } else {
                this.clientes = [];
            }
        } catch (e) {
            this.clientes = [];
        }
    }

    adicionarItemNovaNota() {
        const tbody = document.getElementById('corpoItensNovaNota');
        if (!tbody) return;
        const n = tbody.querySelectorAll('tr').length + 1;
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${n}</td>
            <td><input type="text" class="form-control form-control-sm item-descricao" placeholder="Descrição" required></td>
            <td><input type="text" class="form-control form-control-sm item-ncm" placeholder="NCM" maxlength="10" title="Nomenclatura Comum do Mercosul"></td>
            <td><input type="text" class="form-control form-control-sm item-cfop" placeholder="CFOP" maxlength="10"></td>
            <td><input type="number" class="form-control form-control-sm item-origem" min="0" max="8" value="0" placeholder="0-8" title="Origem da mercadoria"></td>
            <td><input type="text" class="form-control form-control-sm item-cst" placeholder="CST/CSOSN" maxlength="5"></td>
            <td><input type="text" class="form-control form-control-sm item-unidade" value="UN" placeholder="UN"></td>
            <td><input type="number" class="form-control form-control-sm item-qtd" min="0.001" step="0.001" value="1" placeholder="Qtd"></td>
            <td><input type="number" class="form-control form-control-sm item-vunit" min="0" step="0.01" value="0" placeholder="Valor unit."></td>
            <td><span class="item-total">R$ 0,00</span></td>
            <td><button type="button" class="btn btn-sm btn-outline-danger" onclick="notasFiscaisManager.removerItemNovaNota(this)"><i class="align-middle" data-feather="trash-2"></i></button></td>
        `;
        tbody.appendChild(tr);
        tr.querySelectorAll('.item-qtd, .item-vunit').forEach(input => {
            input.addEventListener('input', () => this.atualizarTotalNovaNota());
        });
        this.atualizarTotalNovaNota();
        if (typeof feather !== 'undefined' && feather.replace) feather.replace();
    }

    removerItemNovaNota(btn) {
        const tr = btn.closest('tr');
        if (tr && document.getElementById('corpoItensNovaNota').querySelectorAll('tr').length > 1) {
            tr.remove();
            document.getElementById('corpoItensNovaNota').querySelectorAll('tr').forEach((row, i) => {
                row.querySelector('td:first-child').textContent = i + 1;
            });
            this.atualizarTotalNovaNota();
        }
    }

    atualizarTotalNovaNota() {
        const tbody = document.getElementById('corpoItensNovaNota');
        if (!tbody) return;
        let totalGeral = 0;
        tbody.querySelectorAll('tr').forEach((row, idx) => {
            const qtd = parseFloat(row.querySelector('.item-qtd')?.value || 0) || 0;
            const vunit = parseFloat(row.querySelector('.item-vunit')?.value || 0) || 0;
            const vtotal = qtd * vunit;
            totalGeral += vtotal;
            const totalEl = row.querySelector('.item-total');
            if (totalEl) totalEl.textContent = vtotal.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
        });
        const el = document.getElementById('novaNotaValorTotal');
        if (el) el.value = totalGeral.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    }

    async salvarNovaNota() {
        const empresaId = parseInt(document.getElementById('novaNotaEmpresaId')?.value, 10);
        const tipo = document.getElementById('novaNotaTipo')?.value || 'NFe';
        const numero = (document.getElementById('novaNotaNumero')?.value || '1').trim() || '1';
        const serie = (document.getElementById('novaNotaSerie')?.value || '1').trim() || '1';
        const dataEmissaoStr = document.getElementById('novaNotaDataEmissao')?.value;
        const dataSaidaStr = document.getElementById('novaNotaDataSaida')?.value;
        const naturezaOperacao = (document.getElementById('novaNotaNaturezaOperacao')?.value || '').trim() || null;
        const ambiente = (document.getElementById('novaNotaAmbiente')?.value || 'homologacao').trim() || 'homologacao';
        const clienteIdVal = document.getElementById('novaNotaClienteId')?.value;
        const userId = this.getUserId();
        if (!empresaId || !dataEmissaoStr) {
            this.mostrarAlerta('Preencha Empresa e Data de emissão.', 'warning');
            return;
        }
        if (!userId) {
            this.mostrarAlerta('Usuário não identificado. Faça login novamente.', 'danger');
            return;
        }
        const tbody = document.getElementById('corpoItensNovaNota');
        const rows = tbody ? tbody.querySelectorAll('tr') : [];
        const itens = [];
        let valorProdutos = 0;
        rows.forEach((row, i) => {
            const descricao = row.querySelector('.item-descricao')?.value?.trim();
            const unidade = (row.querySelector('.item-unidade')?.value?.trim() || 'UN').substring(0, 10);
            const qtd = parseFloat(row.querySelector('.item-qtd')?.value || 0) || 0;
            const vunit = parseFloat(row.querySelector('.item-vunit')?.value || 0) || 0;
            const ncm = (row.querySelector('.item-ncm')?.value || '').trim() || null;
            const cfop = (row.querySelector('.item-cfop')?.value || '').trim() || null;
            const origemVal = row.querySelector('.item-origem')?.value;
            const origem = origemVal !== '' && origemVal !== undefined ? parseInt(origemVal, 10) : null;
            const cstVal = (row.querySelector('.item-cst')?.value || '').trim() || null;
            if (!descricao || qtd <= 0) return;
            const vtotal = Math.round(qtd * vunit * 100) / 100;
            valorProdutos += vtotal;
            itens.push({
                item_numero: i + 1,
                descricao: descricao.substring(0, 255),
                unidade: unidade || 'UN',
                quantidade: qtd,
                valor_unitario: vunit,
                valor_total: vtotal,
                valor_desconto: 0,
                ncm: ncm || undefined,
                cfop: cfop || undefined,
                origem: (origem !== null && origem >= 0 && origem <= 8) ? origem : undefined,
                cst_icms: cstVal || undefined,
                csosn: cstVal || undefined,
                valor_icms: 0,
                valor_base_icms: 0,
                valor_icms_st: 0,
                valor_ipi: 0,
                pis_valor: 0,
                pis_base_calculo: 0,
                cofins_valor: 0,
                cofins_base_calculo: 0
            });
        });
        if (itens.length === 0) {
            this.mostrarAlerta('Adicione pelo menos um item com descrição e quantidade.', 'warning');
            return;
        }
        const valorTotal = Math.round(valorProdutos * 100) / 100;
        const dataEmissao = new Date(dataEmissaoStr).toISOString();
        const dataSaida = dataSaidaStr ? new Date(dataSaidaStr).toISOString() : null;
        const modelo = tipo === 'NFCe' ? '65' : '55';
        const payload = {
            numero,
            serie,
            tipo,
            modelo,
            data_emissao: dataEmissao,
            data_saida: dataSaida,
            natureza_operacao: naturezaOperacao,
            empresa_id: empresaId,
            emitido_por_id: userId,
            cliente_id: clienteIdVal ? parseInt(clienteIdVal, 10) : null,
            status: 'rascunho',
            valor_total: valorTotal,
            valor_produtos: valorProdutos,
            valor_frete: 0,
            valor_seguro: 0,
            valor_desconto: 0,
            valor_outros: 0,
            valor_icms: 0,
            valor_icms_desonerado: 0,
            valor_icms_st: 0,
            valor_ipi: 0,
            valor_pis: 0,
            valor_cofins: 0,
            ambiente,
            itens
        };
        try {
            const response = await this.apiFetch('/api/v1/fiscal/notas-fiscais', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            if (!response.ok) {
                const err = await response.json().catch(() => ({}));
                const detail = typeof err.detail === 'string' ? err.detail : null;
                throw new Error(detail || (response.status === 401 ? 'Sessão expirada. Faça login novamente.' : `Erro ao criar nota (${response.status})`));
            }
            this.mostrarAlerta('Nota criada com sucesso. Você pode validar e enviar na listagem.', 'success');
            this.fecharModalNovaNota();
            this.carregarNotasFiscais();
        } catch (error) {
            console.error('❌ Erro ao salvar nota:', error);
            this.mostrarAlerta(error.message || 'Erro ao criar nota fiscal', 'danger');
        }
    }
    
    mostrarAlerta(mensagem, tipo = 'info') {
        const alertContainer = document.getElementById('alert-container');
        if (!alertContainer) {
            // Fallback para alert do navegador
            if (window.alertSystem && typeof window.alertSystem.show === 'function') {
                window.alertSystem.show(mensagem, tipo);
            } else {
                alert(mensagem);
            }
            return;
        }
        
        const alertId = 'alert-' + Date.now();
        const alertHTML = `
            <div id="${alertId}" class="alert alert-${tipo} alert-dismissible fade show" role="alert">
                ${mensagem}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
        
        alertContainer.insertAdjacentHTML('beforeend', alertHTML);
        
        // Auto-remover após 5 segundos
        setTimeout(() => {
            const alertElement = document.getElementById(alertId);
            if (alertElement) {
                alertElement.remove();
            }
        }, 5000);
    }
}

// Inicializar manager quando o script for carregado
const notasFiscaisManager = new NotasFiscaisManager();

