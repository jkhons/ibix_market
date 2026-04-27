/**
 * CertificadosPesoManager - Gerenciador de Certificados de Peso
 * Responsável por gerenciar certificados de pesos padrão
 */

class CertificadosPesoManager {
    constructor() {
        this.certificados = [];
        this.paginaAtual = 1;
        this.itensPorPagina = 10;
        this.totalCertificados = 0;
        this.certificadoEditando = null;
        this.arquivoParaUpload = null;
        this.filtros = {
            identificacao: '',
            classe: '',
            status: ''
        };
        
        this.init();
    }
    
    async init() {
        // Carregar dados iniciais
        await this.carregarCertificados();
        
        // Configurar event listeners
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        // Form submission
        const form = document.getElementById('formCertificado');
        if (form) {
            form.addEventListener('submit', (e) => this.salvarCertificado(e));
        }
        
        // Filtros com debounce
        const filtroIdentificacao = document.getElementById('filtroIdentificacao');
        const filtroClasse = document.getElementById('filtroClasse');
        const filtroStatus = document.getElementById('filtroStatus');
        
        if (filtroIdentificacao) {
            filtroIdentificacao.addEventListener('input', this.debounce(() => this.aplicarFiltros(), 500));
        }
        
        if (filtroClasse) {
            filtroClasse.addEventListener('input', this.debounce(() => this.aplicarFiltros(), 500));
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
            const token = this.getToken();
            if (!token) {
                return;
            }
            
            const response = await fetch('/api/v1/certificados-auxiliares/peso', {
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
            
            this.renderizarTabela();
            
        } catch (error) {
            this.mostrarAlerta('Erro ao carregar certificados', 'error');
        }
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
                <td><strong>${certificado.identificacao}</strong></td>
                <td>${certificado.valor_nominal} ${certificado.unidade}</td>
                <td>${certificado.classe || '-'}</td>
                <td>${certificado.certificado_numero || '-'}</td>
                <td>${this.formatarData(certificado.data_validade)}</td>
                <td>
                    ${certificado.ativo ? 
                        '<span class="badge bg-success">Ativo</span>' : 
                        '<span class="badge bg-secondary">Inativo</span>'
                    }
                </td>
                <td>
                    ${certificado.arquivo_pdf ? 
                        `<span class="badge bg-info">
                            <i class="align-middle me-1" data-feather="file-text"></i>
                            PDF
                        </span>` : 
                        '<span class="text-muted">-</span>'
                    }
                </td>
                <td>
                    <div class="btn-group" role="group">
                        <button type="button" class="btn btn-sm btn-outline-primary" onclick="editarCertificado(${certificado.id})" title="Editar">
                            <i class="align-middle" data-feather="edit-2"></i>
                        </button>
                        ${certificado.arquivo_pdf ? 
                            `<button type="button" class="btn btn-sm btn-outline-info" onclick="visualizarAnexo('${certificado.arquivo_pdf}')" title="Visualizar Anexo">
                                <i class="align-middle" data-feather="eye"></i>
                            </button>` : 
                            ''
                        }
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
    
    async abrirModalCertificado(certificado = null) {
        this.certificadoEditando = certificado;
        const modal = new bootstrap.Modal(document.getElementById('modalCertificado'));
        const titulo = document.getElementById('modalCertificadoLabel');
        

        
        if (certificado) {
            titulo.textContent = 'Editar Certificado Peso';
            this.preencherFormulario(certificado);
        } else {
            titulo.textContent = 'Novo Certificado Peso';
            this.limparFormulario();
        }
        
        modal.show();
    }
    
    preencherFormulario(certificado) {
        document.getElementById('identificacao').value = certificado.identificacao || '';
        document.getElementById('valor_nominal').value = certificado.valor_nominal || '';
        document.getElementById('unidade').value = certificado.unidade || '';
        document.getElementById('classe').value = certificado.classe || '';
        document.getElementById('certificado_numero').value = certificado.certificado_numero || '';
        document.getElementById('ativo').value = certificado.ativo ? '1' : '0';
        document.getElementById('data_calibracao').value = certificado.data_calibracao || '';
        document.getElementById('data_validade').value = certificado.data_validade || '';
    }
    
    limparFormulario() {
        document.getElementById('formCertificado').reset();
        document.getElementById('unidade').value = '';
        document.getElementById('ativo').value = '1';
        this.arquivoParaUpload = null;
    }
    
    async salvarCertificado(event) {
        event.preventDefault();
        
        try {
            const formData = new FormData(event.target);
            const dados = {};
            
            // Processar campos do formulário
            for (let [key, value] of formData.entries()) {
                // Pular campos vazios
                if (!value || value.toString().trim() === '') {
                    continue;
                }
                
                // Tratar campos específicos
                if (key === 'arquivo_pdf') {
                    if (value instanceof File) {
                        if (value.size === 0) {
                            continue;
                        } else {
                            // Não incluir o arquivo nos dados JSON, será enviado separadamente
                            this.arquivoParaUpload = value;
                        }
                    } else {
                        dados[key] = value;
                    }
                } else if (key === 'ativo') {
                    dados[key] = value === '1';
                } else {
                    dados[key] = value;
                }
            }
            
            const token = this.getToken();
            if (!token) {
                throw new Error('Token não encontrado');
            }
            
            const url = this.certificadoEditando
                ? `/api/v1/certificados-auxiliares/peso/${this.certificadoEditando.id}`
                : '/api/v1/certificados-auxiliares/peso';
            
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
            
            // Upload do arquivo PDF se existir
            if (this.arquivoParaUpload && this.arquivoParaUpload.size > 0) {
                const certificadoId = this.certificadoEditando ? this.certificadoEditando.id : resultado.id;
                await this.uploadArquivoPdf(certificadoId, this.arquivoParaUpload);
                this.arquivoParaUpload = null; // Limpar após upload
            }
            
            this.mostrarAlerta('Certificado salvo com sucesso!', 'success');
            
            // Fechar modal e recarregar dados
            const modal = bootstrap.Modal.getInstance(document.getElementById('modalCertificado'));
            modal.hide();
            
            await this.carregarCertificados();
            
        } catch (error) {
            this.mostrarAlerta(`Erro ao salvar certificado: ${error.message}`, 'error');
        }
    }
    
    async excluirCertificado(id) {
        if (!confirm('Tem certeza que deseja excluir este certificado?')) {
            return;
        }
        
        try {
            const token = this.getToken();
            if (!token) {
                throw new Error('Token não encontrado');
            }
            
            const response = await fetch(`/api/v1/certificados-auxiliares/peso/${id}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            this.mostrarAlerta('Certificado excluído com sucesso!', 'success');
            
            await this.carregarCertificados();
            
        } catch (error) {
            this.mostrarAlerta(`Erro ao excluir certificado: ${error.message}`, 'error');
        }
    }
    
    aplicarFiltros() {
        this.filtros.identificacao = document.getElementById('filtroIdentificacao')?.value || '';
        this.filtros.classe = document.getElementById('filtroClasse')?.value || '';
        this.filtros.status = document.getElementById('filtroStatus')?.value || '';
        
        console.log('🔍 Aplicando filtros:', this.filtros);
        
        // Recarregar dados com filtros
        this.carregarCertificados();
    }
    
    limparFiltros() {
        document.getElementById('filtroIdentificacao').value = '';
        document.getElementById('filtroClasse').value = '';
        document.getElementById('filtroStatus').value = '';
        
        this.filtros = {
            identificacao: '',
            classe: '',
            status: ''
        };
        
        console.log('🧹 Filtros limpos');
        this.carregarCertificados();
    }
    
    exportarCertificados() {
        this.mostrarAlerta('Funcionalidade de exportação em desenvolvimento', 'info');
    }
    
    async uploadArquivoPdf(certificadoId, arquivo) {
        try {
            const formData = new FormData();
            formData.append('file', arquivo);
            
            const response = await fetch(`/api/v1/certificados-auxiliares/peso/${certificadoId}/upload-pdf`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.getToken()}`
                },
                body: formData
            });
            
            if (response.ok) {
                const resultado = await response.json();
                this.mostrarAlerta('Arquivo PDF enviado com sucesso!', 'success');
            } else {
                const error = await response.json();
                this.mostrarAlerta('Erro ao enviar arquivo PDF', 'error');
            }
        } catch (error) {
            this.mostrarAlerta('Erro ao enviar arquivo PDF', 'error');
        }
    }
    
    visualizarAnexo(arquivoPdf) {
        if (!arquivoPdf) {
            this.mostrarAlerta('Nenhum anexo disponível', 'warning');
            return;
        }
        
        // Buscar o certificado para obter o ID
        const certificado = this.certificados.find(c => c.arquivo_pdf === arquivoPdf);
        if (!certificado) {
            this.mostrarAlerta('Certificado não encontrado', 'error');
            return;
        }
        
        // Construir URL da API protegida
        const url = `/api/v1/certificados-auxiliares/peso/${certificado.id}/download-pdf`;
        
        // Abrir em nova aba
        window.open(url, '_blank');
    }
    
    getToken() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'pdv_automscale_token') {
                return value;
            }
        }
        return null;
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
window.certificadosPesoManager = new CertificadosPesoManager();

// Funções globais para compatibilidade
function abrirModalCertificado(certificado = null) {
    window.certificadosPesoManager.abrirModalCertificado(certificado);
}

function editarCertificado(id) {
    const certificado = window.certificadosPesoManager.certificados.find(c => c.id === id);
    if (certificado) {
        window.certificadosPesoManager.abrirModalCertificado(certificado);
    }
}

function excluirCertificado(id) {
    window.certificadosPesoManager.excluirCertificado(id);
}

function aplicarFiltros() {
    window.certificadosPesoManager.aplicarFiltros();
}

function limparFiltros() {
    window.certificadosPesoManager.limparFiltros();
}

function exportarCertificados() {
    window.certificadosPesoManager.exportarCertificados();
}

function visualizarAnexo(arquivoPdf) {
    window.certificadosPesoManager.visualizarAnexo(arquivoPdf);
} 