/**
 * CertificadosAuxiliaresManager - Gerenciador de Certificados Auxiliares
 * Responsável por gerenciar certificados de TERMOBAROHIGROMETRO e equipamentos auxiliares
 */

class CertificadosAuxiliaresManager {
    constructor() {
        this.certificados = [];
        this.paginaAtual = 1;
        this.itensPorPagina = 10;
        this.totalCertificados = 0;
        this.certificadoEditando = null;
        this.filtros = {
            nome: '',
            fabricante: '',
            status: ''
        };
        
        this.init();
    }
    
    async init() {
        console.log('🔧 Inicializando CertificadosAuxiliaresManager...');
        
        try {
            // Carregar dados iniciais
            await this.carregarCertificados();
            await this.carregarResponsaveis();
            
            // Configurar event listeners
            this.setupEventListeners();
            
            console.log('✅ CertificadosAuxiliaresManager inicializado');
        } catch (error) {
            console.error('❌ Erro na inicialização:', error);
            this.mostrarAlerta(`Erro na inicialização: ${error.message}`, 'error');
        }
    }
    
    setupEventListeners() {
        // Form submission
        const form = document.getElementById('formCertificado');
        if (form) {
            form.addEventListener('submit', (e) => this.salvarCertificado(e));
        }
        
        // Filtros com debounce
        const filtroNome = document.getElementById('filtroNome');
        const filtroFabricante = document.getElementById('filtroFabricante');
        const filtroStatus = document.getElementById('filtroStatus');
        
        if (filtroNome) {
            filtroNome.addEventListener('input', this.debounce(() => this.aplicarFiltros(), 500));
        }
        
        if (filtroFabricante) {
            filtroFabricante.addEventListener('input', this.debounce(() => this.aplicarFiltros(), 500));
        }
        
        if (filtroStatus) {
            filtroStatus.addEventListener('change', () => this.aplicarFiltros());
        }
    }
    
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    async carregarCertificados() {
        try {
            console.log('📋 Carregando certificados auxiliares...');
            
            const token = this.getToken();
            if (!token) {
                console.error('❌ Token não encontrado');
                return;
            }
            
            const response = await fetch('/api/v1/certificados-auxiliares/', {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            this.certificados = data.certificados || [];
            this.totalCertificados = data.total || 0;
            
            console.log(`✅ ${this.certificados.length} certificados carregados`);
            this.renderizarTabela();
            
        } catch (error) {
            console.error('❌ Erro ao carregar certificados:', error);
            this.mostrarAlerta('Erro ao carregar certificados', 'error');
        }
    }
    
    async carregarResponsaveis() {
        try {
            console.log('👥 Carregando responsáveis...');
            
            const token = this.getToken();
            if (!token) {
                console.error('❌ Token não encontrado');
                return;
            }
            
            const response = await fetch('/api/v1/usuarios/', {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            this.preencherSelectResponsaveis(data.usuarios || []);
            
        } catch (error) {
            console.error('❌ Erro ao carregar responsáveis:', error);
        }
    }
    
    preencherSelectResponsaveis(usuarios) {
        const select = document.getElementById('responsavelId');
        if (!select) return;
        
        // Limpar opções existentes (exceto a primeira)
        while (select.children.length > 1) {
            select.removeChild(select.lastChild);
        }
        
        // Adicionar opções
        usuarios.forEach(usuario => {
            const option = document.createElement('option');
            option.value = usuario.id;
            option.textContent = usuario.nome;
            select.appendChild(option);
        });
        
        console.log(`✅ ${usuarios.length} responsáveis carregados`);
    }
    
    renderizarTabela() {
        const tbody = document.getElementById('tabelaCertificados');
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        if (this.certificados.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="text-center text-muted">
                        Nenhum certificado encontrado
                    </td>
                </tr>
            `;
            return;
        }
        
        this.certificados.forEach(certificado => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${certificado.nome}</strong></td>
                <td>${certificado.fabricante || '-'}</td>
                <td>${certificado.modelo || '-'}</td>
                <td>${certificado.numero_serie || '-'}</td>
                <td>${certificado.certificado_numero || '-'}</td>
                <td>${this.formatarData(certificado.data_validade)}</td>
                <td>
                    ${certificado.ativo ? 
                        '<span class="badge bg-success">Ativo</span>' : 
                        '<span class="badge bg-secondary">Inativo</span>'
                    }
                </td>
                <td>
                    <div class="btn-group" role="group">
                        <button type="button" class="btn btn-sm btn-outline-primary" onclick="editarCertificado(${certificado.id})" title="Editar">
                            <i class="align-middle" data-feather="edit-2"></i>
                        </button>
                        <button type="button" class="btn btn-sm btn-outline-danger" onclick="excluirCertificado(${certificado.id})" title="Excluir">
                            <i class="align-middle" data-feather="trash-2"></i>
                        </button>
                    </div>
                </td>
            `;
            tbody.appendChild(tr);
        });
        
        // Atualizar informações da página
        this.atualizarInfoPagina();
        
        // Re-inicializar Feather icons
        if (typeof feather !== 'undefined') {
            feather.replace();
        }
    }
    
    atualizarInfoPagina() {
        const infoPagina = document.getElementById('infoPagina');
        if (infoPagina) {
            const inicio = (this.paginaAtual - 1) * this.itensPorPagina + 1;
            const fim = Math.min(inicio + this.itensPorPagina - 1, this.totalCertificados);
            infoPagina.textContent = `Mostrando ${inicio} a ${fim} de ${this.totalCertificados} certificados`;
        }
    }
    
    formatarData(data) {
        if (!data) return '-';
        if (typeof window.formatarDataApenas === 'function') return window.formatarDataApenas(data);
        const s = String(data).trim();
        const m = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
        if (m) return m[3] + '/' + m[2] + '/' + m[1];
        const d = new Date(data);
        return isNaN(d.getTime()) ? '-' : d.toLocaleDateString('pt-BR');
    }
    
    abrirModalCertificado(certificado = null) {
        console.log('🔧 Abrindo modal de certificado:', certificado);
        this.certificadoEditando = certificado;
        
        const modalElement = document.getElementById('modalCertificado');
        if (!modalElement) {
            console.error('❌ Elemento modal não encontrado');
            this.mostrarAlerta('Erro: Modal não encontrado', 'error');
            return;
        }
        
        const modal = new bootstrap.Modal(modalElement);
        const titulo = document.getElementById('modalCertificadoLabel');
        
        if (certificado) {
            titulo.textContent = 'Editar Certificado TERMOBAROHIGROMETRO';
            this.preencherFormulario(certificado);
        } else {
            titulo.textContent = 'Novo Certificado TERMOBAROHIGROMETRO';
            this.limparFormulario();
        }
        
        modal.show();
        console.log('✅ Modal aberto com sucesso');
    }
    
    preencherFormulario(certificado) {
        document.getElementById('nome').value = certificado.nome || '';
        document.getElementById('tipo').value = certificado.tipo || 'equipamento';
        document.getElementById('fabricante').value = certificado.fabricante || '';
        document.getElementById('modelo').value = certificado.modelo || '';
        document.getElementById('numeroSerie').value = certificado.numero_serie || '';
        document.getElementById('certificadoNumero').value = certificado.certificado_numero || '';
        document.getElementById('responsavelId').value = certificado.responsavel_id || '';
        document.getElementById('dataCalibracao').value = certificado.data_calibracao || '';
        document.getElementById('dataValidade').value = certificado.data_validade || '';
    }
    
    limparFormulario() {
        document.getElementById('formCertificado').reset();
        document.getElementById('tipo').value = 'equipamento';
    }
    
    async salvarCertificado(event) {
        event.preventDefault();
        
        try {
            console.log('💾 Salvando certificado auxiliar...');
            
            const formData = new FormData(event.target);
            const dados = Object.fromEntries(formData.entries());
            
            // Converter responsavel_id para número
            if (dados.responsavel_id) {
                dados.responsavel_id = parseInt(dados.responsavel_id);
            }
            
            console.log('📋 Dados do certificado:', dados);
            
            const token = this.getToken();
            if (!token) {
                throw new Error('Token não encontrado');
            }
            
            const url = this.certificadoEditando 
                ? `/api/v1/certificados-auxiliares/${this.certificadoEditando.id}`
                : '/api/v1/certificados-auxiliares/';
            
            const method = this.certificadoEditando ? 'PUT' : 'POST';
            
            const response = await fetch(url, {
                method: method,
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(dados)
            });
            
            if (!response.ok) {
                const errorText = await response.text();
                let errorData;
                try {
                    errorData = JSON.parse(errorText);
                } catch {
                    errorData = { detail: errorText };
                }
                throw new Error(JSON.stringify(errorData));
            }
            
            const resultado = await response.json();
            
            console.log('✅ Certificado salvo com sucesso:', resultado);
            this.mostrarAlerta('Certificado salvo com sucesso!', 'success');
            
            // Fechar modal e recarregar dados
            const modal = bootstrap.Modal.getInstance(document.getElementById('modalCertificado'));
            modal.hide();
            
            await this.carregarCertificados();
            
        } catch (error) {
            console.error('❌ Erro ao salvar certificado:', error);
            this.mostrarAlerta(`Erro ao salvar certificado: ${error.message}`, 'error');
        }
    }
    
    async excluirCertificado(id) {
        if (!confirm('Tem certeza que deseja excluir este certificado?')) {
            return;
        }
        
        try {
            console.log(`🗑️ Excluindo certificado ${id}...`);
            
            const token = this.getToken();
            if (!token) {
                throw new Error('Token não encontrado');
            }
            
            const response = await fetch(`/api/v1/certificados-auxiliares/${id}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            console.log('✅ Certificado excluído com sucesso');
            this.mostrarAlerta('Certificado excluído com sucesso!', 'success');
            
            await this.carregarCertificados();
            
        } catch (error) {
            console.error('❌ Erro ao excluir certificado:', error);
            this.mostrarAlerta(`Erro ao excluir certificado: ${error.message}`, 'error');
        }
    }
    
    aplicarFiltros() {
        this.filtros.nome = document.getElementById('filtroNome')?.value || '';
        this.filtros.fabricante = document.getElementById('filtroFabricante')?.value || '';
        this.filtros.status = document.getElementById('filtroStatus')?.value || '';
        
        console.log('🔍 Aplicando filtros:', this.filtros);
        
        // Recarregar dados com filtros
        this.carregarCertificados();
    }
    
    limparFiltros() {
        document.getElementById('filtroNome').value = '';
        document.getElementById('filtroFabricante').value = '';
        document.getElementById('filtroStatus').value = '';
        
        this.filtros = {
            nome: '',
            fabricante: '',
            status: ''
        };
        
        console.log('🧹 Filtros limpos');
        this.carregarCertificados();
    }
    
    exportarCertificados() {
        console.log('📤 Exportando certificados...');
        this.mostrarAlerta('Funcionalidade de exportação em desenvolvimento', 'info');
    }
    
    getToken() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'pdv_automscale_token') return value || '';
        }
        return localStorage.getItem('pdv_automscale_token') || sessionStorage.getItem('pdv_automscale_token') || '';
    }
    
    mostrarAlerta(mensagem, tipo = 'info') {
        if (window.alertSystem) {
            window.alertSystem[tipo](mensagem);
        } else {
            alert(mensagem);
        }
    }
}

// Instância global
window.certificadosAuxiliaresManager = new CertificadosAuxiliaresManager();

// Funções globais para compatibilidade
function abrirModalCertificado(certificado = null) {
    window.certificadosAuxiliaresManager.abrirModalCertificado(certificado);
}

function editarCertificado(id) {
    const certificado = window.certificadosAuxiliaresManager.certificados.find(c => c.id === id);
    if (certificado) {
        window.certificadosAuxiliaresManager.abrirModalCertificado(certificado);
    }
}

function excluirCertificado(id) {
    window.certificadosAuxiliaresManager.excluirCertificado(id);
}

function aplicarFiltros() {
    window.certificadosAuxiliaresManager.aplicarFiltros();
}

function limparFiltros() {
    window.certificadosAuxiliaresManager.limparFiltros();
}

function exportarCertificados() {
    window.certificadosAuxiliaresManager.exportarCertificados();
} 