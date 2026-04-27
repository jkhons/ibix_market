/**
 * CertificadosAuxiliaresUnificadoManager - Gerenciador Unificado de Certificados Auxiliares
 * Gerencia todas as categorias: TERMOBAROHIGROMETRO, PESO, INSPETOR_APROVADOR
 * Usa a API unificada /api/v1/aux-cadastros
 */

class CertificadosAuxiliaresUnificadoManager {
    constructor() {
        this.cadastros = [];
        this.paginaAtual = 1;
        this.itensPorPagina = 50;
        this.totalCadastros = 0;
        this.cadastroEditando = null;
        this.filtros = {
            categoria_codigo: null,
            identificador: null,
            nome_titulo: null,
            ativo: null
        };
        
        // Mapeamento de categorias
        this.categorias = {
            'TERMOBAROHIGROMETRO': { nome: 'Termobarohigrômetro', icon: 'thermometer' },
            'PESO': { nome: 'Peso Padrão', icon: 'package' },
            'INSPETOR_APROVADOR': { nome: 'Inspetor/Aprovador', icon: 'user-check' }
        };
    }
    
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    getToken() {
        return getCookie('pdv_automscale_token');
    }
    
    async listarCadastros(filtros = {}) {
        try {
            const token = this.getToken();
            if (!token) {
                this.mostrarAlerta('Token não encontrado. Faça login novamente.', 'error');
                return;
            }
            
            // Salvar filtros para uso posterior
            this.filtros = { ...this.filtros, ...filtros };
            
            // Construir query string
            const params = new URLSearchParams();
            params.append('skip', ((this.paginaAtual - 1) * this.itensPorPagina).toString());
            params.append('limit', this.itensPorPagina.toString());
            
            if (filtros.categoria_codigo) {
                params.append('categoria_codigo', filtros.categoria_codigo);
            }
            if (filtros.identificador) {
                params.append('identificador', filtros.identificador);
            }
            if (filtros.nome_titulo) {
                params.append('nome_titulo', filtros.nome_titulo);
            }
            if (filtros.ativo !== undefined) {
                params.append('ativo', filtros.ativo.toString());
            }
            
            const response = await fetch(`/api/v1/aux-cadastros?${params.toString()}`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: response.statusText }));
                throw new Error(errorData.detail || `HTTP ${response.status}`);
            }
            
            const data = await response.json();
            this.cadastros = data.cadastros || [];
            this.totalCadastros = data.total || 0;
            
            this.renderizarTabela();
            this.atualizarPaginacao();
            this.atualizarInfoPagina();
            
        } catch (error) {
            console.error('❌ Erro ao listar cadastros:', error);
            this.mostrarAlerta(`Erro ao carregar certificados: ${error.message}`, 'error');
            this.renderizarTabelaVazia();
        }
    }
    
    async obterCadastro(id) {
        try {
            const token = this.getToken();
            if (!token) {
                throw new Error('Token não encontrado');
            }
            
            const response = await fetch(`/api/v1/aux-cadastros/${id}`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: response.statusText }));
                throw new Error(errorData.detail || `HTTP ${response.status}`);
            }
            
            return await response.json();
            
        } catch (error) {
            console.error('❌ Erro ao obter cadastro:', error);
            throw error;
        }
    }
    
    async criarCadastro(dados) {
        try {
            const token = this.getToken();
            if (!token) {
                throw new Error('Token não encontrado');
            }
            
            const response = await fetch('/api/v1/aux-cadastros', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(dados)
            });
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: response.statusText }));
                const errorMessage = errorData.detail || `HTTP ${response.status}`;
                
                // Melhorar mensagens de erro de unicidade
                if (response.status === 409 || errorMessage.includes('já existe') || errorMessage.includes('Conflict')) {
                    throw new Error(errorMessage);
                }
                
                throw new Error(errorMessage);
            }
            
            return await response.json();
            
        } catch (error) {
            console.error('❌ Erro ao criar cadastro:', error);
            throw error;
        }
    }
    
    async atualizarCadastro(id, dados) {
        try {
            const token = this.getToken();
            if (!token) {
                throw new Error('Token não encontrado');
            }
            
            const response = await fetch(`/api/v1/aux-cadastros/${id}`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(dados)
            });
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: response.statusText }));
                const errorMessage = errorData.detail || `HTTP ${response.status}`;
                
                // Melhorar mensagens de erro de unicidade
                if (response.status === 409 || errorMessage.includes('já existe') || errorMessage.includes('Conflict')) {
                    throw new Error(errorMessage);
                }
                
                throw new Error(errorMessage);
            }
            
            return await response.json();
            
        } catch (error) {
            console.error('❌ Erro ao atualizar cadastro:', error);
            throw error;
        }
    }
    
    async excluirCadastro(id) {
        try {
            const token = this.getToken();
            if (!token) {
                throw new Error('Token não encontrado');
            }
            
            const response = await fetch(`/api/v1/aux-cadastros/${id}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: response.statusText }));
                throw new Error(errorData.detail || `HTTP ${response.status}`);
            }
            
            return true;
            
        } catch (error) {
            console.error('❌ Erro ao excluir cadastro:', error);
            throw error;
        }
    }
    
    renderizarTabela() {
        const tbody = document.getElementById('tabelaCertificados');
        if (!tbody) return;
        
        // Determinar categoria atual para colunas dinâmicas
        const categoriaAtual = this.filtros.categoria_codigo || null;
        this.configurarColunasDinamicas(categoriaAtual);
        
        // Verificar quais colunas dinâmicas estão visíveis
        const col1 = document.getElementById('colunaDinamica1');
        const col2 = document.getElementById('colunaDinamica2');
        const col1Visivel = col1 && col1.style.display !== 'none';
        const col2Visivel = col2 && col2.style.display !== 'none';
        
        // Calcular colspan: 7 colunas fixas + colunas dinâmicas visíveis
        const colspan = 7 + (col1Visivel ? 1 : 0) + (col2Visivel ? 1 : 0);
        
        if (this.cadastros.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="${colspan}" class="text-center text-muted">
                        Nenhum certificado auxiliar encontrado
                    </td>
                </tr>
            `;
            return;
        }
        
        let html = '';
        this.cadastros.forEach(cadastro => {
            const categoria = this.categorias[cadastro.categoria?.codigo] || { nome: cadastro.categoria?.codigo || 'N/A', icon: 'file' };
            const atributos = cadastro.atributos_json || {};
            
            // Colunas dinâmicas baseadas na categoria - só inserir se estiverem visíveis
            let colunaDinamica1 = '';
            let colunaDinamica2 = '';
            
            if (col1Visivel) {
                if (cadastro.categoria?.codigo === 'PESO') {
                    const valorNominal = this.escapeHtml(atributos.valor_nominal || '');
                    const unidade = this.escapeHtml(atributos.unidade || '');
                    colunaDinamica1 = `<td class="campo-dinamico">${valorNominal}${unidade ? ' ' + unidade : ''}</td>`;
                } else if (cadastro.categoria?.codigo === 'INSPETOR_APROVADOR') {
                    colunaDinamica1 = `<td class="campo-dinamico">${this.escapeHtml(atributos.cpf || '-')}</td>`;
                } else {
                    colunaDinamica1 = '<td class="campo-dinamico">-</td>';
                }
            }
            
            if (col2Visivel) {
                if (cadastro.categoria?.codigo === 'PESO') {
                    colunaDinamica2 = `<td class="campo-dinamico">${this.escapeHtml(atributos.classe || '-')}</td>`;
                } else if (cadastro.categoria?.codigo === 'INSPETOR_APROVADOR') {
                    colunaDinamica2 = `<td class="campo-dinamico">${this.escapeHtml(atributos.email || '-')}</td>`;
                } else {
                    colunaDinamica2 = '<td class="campo-dinamico">-</td>';
                }
            }
            
            let dataValidade = '-';
            if (cadastro.data_validade) {
                if (typeof window.formatarDataApenas === 'function') {
                    dataValidade = window.formatarDataApenas(cadastro.data_validade);
                } else {
                    try {
                        const s = String(cadastro.data_validade).trim();
                        const m = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
                        if (m) dataValidade = m[3] + '/' + m[2] + '/' + m[1];
                        else {
                            const data = new Date(cadastro.data_validade);
                            if (!isNaN(data.getTime())) dataValidade = data.toLocaleDateString('pt-BR');
                        }
                    } catch (e) {
                        dataValidade = '-';
                    }
                }
            }
            let validadeBadge = '';
            if (cadastro.alerta_validade && cadastro.data_validade) {
                const hoje = new Date();
                hoje.setHours(0, 0, 0, 0);
                const validade = new Date(cadastro.data_validade);
                validade.setHours(0, 0, 0, 0);
                const dias = Math.ceil((validade - hoje) / (1000 * 60 * 60 * 24));
                validadeBadge = dias < 0
                    ? ' <span class="badge bg-danger">Vencido</span>'
                    : ' <span class="badge bg-warning text-dark">Vence em ' + dias + ' dias</span>';
            }
            const statusEquip = cadastro.status_equipamento
                ? '<span class="badge bg-info me-1">' + (cadastro.status_equipamento === 'ok' ? 'OK' : cadastro.status_equipamento === 'em_calibracao' ? 'Em calibração' : 'Fora de uso') + '</span>'
                : '';
            const statusBadge = cadastro.ativo 
                ? '<span class="badge bg-success">Ativo</span>' 
                : '<span class="badge bg-secondary">Inativo</span>';
            
            // Escapar valores para evitar problemas com caracteres especiais
            const identificadorEscapado = this.escapeHtml(cadastro.identificador || '-');
            const nomeTituloEscapado = this.escapeHtml(cadastro.nome_titulo || '-');
            const certificadoNumeroEscapado = this.escapeHtml(cadastro.certificado_numero || '-');
            const nomeTituloParaOnclick = this.escapeHtml(cadastro.nome_titulo || cadastro.identificador || '').replace(/'/g, "\\'");
            
            html += `
                <tr>
                    <td>
                        <span class="badge categoria-badge bg-primary">${this.escapeHtml(categoria.nome)}</span>
                    </td>
                    <td>${identificadorEscapado}</td>
                    <td>${nomeTituloEscapado}</td>
                    ${colunaDinamica1}
                    ${colunaDinamica2}
                    <td>${certificadoNumeroEscapado}</td>
                    <td>${dataValidade}${validadeBadge} ${statusEquip}</td>
                    <td>${statusBadge}</td>
                    <td>
                        <a href="/certificados-auxiliares/editar/${cadastro.id}" class="btn btn-sm btn-outline-primary" title="Editar">
                            <i class="align-middle" data-feather="edit-2"></i>
                        </a>
                        <button type="button" class="btn btn-sm btn-outline-danger" onclick="manager.confirmarExclusao(${cadastro.id}, '${nomeTituloParaOnclick}')" title="Excluir">
                            <i class="align-middle" data-feather="trash-2"></i>
                        </button>
                    </td>
                </tr>
            `;
        });
        
        tbody.innerHTML = html;
        
        // Reinicializar feather icons
        if (typeof feather !== 'undefined') {
            feather.replace();
        }
    }
    
    configurarColunasDinamicas(categoriaCodigo) {
        const col1 = document.getElementById('colunaDinamica1');
        const col2 = document.getElementById('colunaDinamica2');
        
        if (!col1 || !col2) return;
        
        if (categoriaCodigo === 'PESO') {
            col1.textContent = 'Valor Nominal';
            col2.textContent = 'Classe';
            col1.style.display = '';
            col2.style.display = '';
        } else if (categoriaCodigo === 'INSPETOR_APROVADOR') {
            col1.textContent = 'CPF';
            col2.textContent = 'Email';
            col1.style.display = '';
            col2.style.display = '';
        } else if (categoriaCodigo === 'TERMOBAROHIGROMETRO') {
            // TERMOBAROHIGROMETRO não tem campos específicos
            col1.style.display = 'none';
            col2.style.display = 'none';
        } else if (!categoriaCodigo) {
            // Sem filtro: mostrar colunas apenas se houver itens de categorias que as usam
            const temPeso = this.cadastros.some(c => c.categoria?.codigo === 'PESO');
            const temInspetor = this.cadastros.some(c => c.categoria?.codigo === 'INSPETOR_APROVADOR');
            
            if (temPeso || temInspetor) {
                col1.textContent = 'Detalhes';
                col2.textContent = 'Detalhes 2';
                col1.style.display = '';
                col2.style.display = '';
            } else {
                col1.style.display = 'none';
                col2.style.display = 'none';
            }
        } else {
            col1.style.display = 'none';
            col2.style.display = 'none';
        }
    }
    
    renderizarTabelaVazia() {
        const tbody = document.getElementById('tabelaCertificados');
        if (tbody) {
            // Verificar quais colunas dinâmicas estão visíveis
            const col1 = document.getElementById('colunaDinamica1');
            const col2 = document.getElementById('colunaDinamica2');
            const col1Visivel = col1 && col1.style.display !== 'none';
            const col2Visivel = col2 && col2.style.display !== 'none';
            
            // Calcular colspan: 7 colunas fixas + colunas dinâmicas visíveis
            const colspan = 7 + (col1Visivel ? 1 : 0) + (col2Visivel ? 1 : 0);
            
            tbody.innerHTML = `
                <tr>
                    <td colspan="${colspan}" class="text-center text-danger">
                        Erro ao carregar certificados. Tente novamente.
                    </td>
                </tr>
            `;
        }
    }
    
    atualizarPaginacao() {
        const paginacao = document.getElementById('paginacao');
        if (!paginacao) return;
        
        const totalPaginas = Math.ceil(this.totalCadastros / this.itensPorPagina);
        
        if (totalPaginas <= 1) {
            paginacao.innerHTML = '';
            return;
        }
        
        let html = '';
        
        // Botão anterior
        html += `
            <li class="page-item ${this.paginaAtual === 1 ? 'disabled' : ''}">
                <a class="page-link" href="#" onclick="manager.irParaPagina(${this.paginaAtual - 1}); return false;">Anterior</a>
            </li>
        `;
        
        // Números de página
        for (let i = 1; i <= totalPaginas; i++) {
            if (i === 1 || i === totalPaginas || (i >= this.paginaAtual - 2 && i <= this.paginaAtual + 2)) {
                html += `
                    <li class="page-item ${i === this.paginaAtual ? 'active' : ''}">
                        <a class="page-link" href="#" onclick="manager.irParaPagina(${i}); return false;">${i}</a>
                    </li>
                `;
            } else if (i === this.paginaAtual - 3 || i === this.paginaAtual + 3) {
                html += '<li class="page-item disabled"><span class="page-link">...</span></li>';
            }
        }
        
        // Botão próximo
        html += `
            <li class="page-item ${this.paginaAtual === totalPaginas ? 'disabled' : ''}">
                <a class="page-link" href="#" onclick="manager.irParaPagina(${this.paginaAtual + 1}); return false;">Próximo</a>
            </li>
        `;
        
        paginacao.innerHTML = html;
    }
    
    irParaPagina(pagina) {
        if (pagina < 1 || pagina > Math.ceil(this.totalCadastros / this.itensPorPagina)) {
            return;
        }
        this.paginaAtual = pagina;
        this.listarCadastros(this.filtros);
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
    
    atualizarInfoPagina() {
        const info = document.getElementById('infoPagina');
        if (!info) return;
        
        const inicio = (this.paginaAtual - 1) * this.itensPorPagina + 1;
        const fim = Math.min(this.paginaAtual * this.itensPorPagina, this.totalCadastros);
        
        info.textContent = `Mostrando ${inicio} a ${fim} de ${this.totalCadastros} certificados`;
    }
    
    confirmarExclusao(id, nome) {
        const modal = new bootstrap.Modal(document.getElementById('modalExcluir'));
        const detalhes = document.getElementById('modalExcluirDetalhes');
        const btnConfirmar = document.getElementById('btnConfirmarExcluir');
        
        if (detalhes) {
            detalhes.textContent = `Certificado: ${nome}`;
        }
        
        if (btnConfirmar) {
            btnConfirmar.onclick = async () => {
                try {
                    await this.excluirCadastro(id);
                    modal.hide();
                    this.mostrarAlerta('Certificado excluído com sucesso!', 'success');
                    this.listarCadastros(this.filtros);
                } catch (error) {
                    this.mostrarAlerta(`Erro ao excluir: ${error.message}`, 'error');
                }
            };
        }
        
        modal.show();
    }
    
    mostrarAlerta(mensagem, tipo = 'info') {
        // Usar alert simples por enquanto (pode ser melhorado com toast)
        if (tipo === 'error') {
            alert('❌ ' + mensagem);
        } else if (tipo === 'success') {
            alert('✅ ' + mensagem);
        } else {
            alert('ℹ️ ' + mensagem);
        }
    }
}

// Exportar para uso global
window.CertificadosAuxiliaresUnificadoManager = CertificadosAuxiliaresUnificadoManager;
