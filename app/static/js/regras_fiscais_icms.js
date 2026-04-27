// PDV Ibix - Regras Fiscais ICMS

const RegrasFiscaisIcmsHelpers = {
    getToken() {
        const m = document.cookie.match(/pdv_solumatica_token=([^;]+)/);
        return m ? m[1].trim() : null;
    },

    mostrarAlerta(msg, tipo = 'info') {
        const container = document.getElementById('alert-container');
        if (!container) return;
        const div = document.createElement('div');
        div.className = `alert alert-${tipo} alert-dismissible fade show`;
        div.setAttribute('role', 'alert');
        div.innerHTML = `${this._escapeHtml(msg)}<button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
        container.innerHTML = '';
        container.appendChild(div);
        setTimeout(() => div.remove(), 5000);
    },

    _escapeHtml(s) {
        const div = document.createElement('div');
        div.textContent = s;
        return div.innerHTML;
    },

    formatCRT(crt) {
        if (crt == null) return '-';
        if (crt === 1 || crt === 2) return 'Simples Nacional';
        if (crt === 3) return 'Regime Normal';
        return String(crt);
    },

    formatTipoOperacao(val) {
        const map = { venda_interna: 'Venda Interna', venda_interestadual: 'Interestadual', qualquer: 'Qualquer' };
        return map[val] || val || '-';
    },

    formatTipoDestinatario(val) {
        const map = { pf: 'PF', pj: 'PJ', qualquer: 'Qualquer' };
        return map[val] || val || '-';
    },

    aplicarVisibilidadeCrt(crt) {
        const campoCst = document.getElementById('campo_cst');
        const campoCsosn = document.getElementById('campo_csosn');
        if (!campoCst || !campoCsosn) return;
        if (crt === '1' || crt === '2') {
            campoCsosn.style.display = '';
            campoCst.style.display = 'none';
        } else if (crt === '3') {
            campoCst.style.display = '';
            campoCsosn.style.display = 'none';
        } else {
            campoCst.style.display = '';
            campoCsosn.style.display = '';
        }
    },

    limparCamposIncompativeisCrt(crt) {
        if (crt === '1' || crt === '2') {
            const el = document.getElementById('cst_icms');
            if (el) el.value = '';
        } else if (crt === '3') {
            const el = document.getElementById('csosn');
            if (el) el.value = '';
        }
    },

    validarFormularioRegra() {
        const erros = [];
        const empresaId = document.getElementById('empresa_id')?.value;
        const cfop = document.getElementById('cfop')?.value?.trim();
        const origem = parseInt(document.getElementById('origem_mercadoria')?.value || '0', 10);
        const crt = document.getElementById('crt')?.value;
        const cst = document.getElementById('cst_icms')?.value?.trim();
        const csosn = document.getElementById('csosn')?.value?.trim();

        if (!empresaId) erros.push('Empresa é obrigatória');
        if (!cfop) erros.push('CFOP é obrigatório');
        if (cfop && cfop.length !== 4) erros.push('CFOP deve ter 4 dígitos');
        if (isNaN(origem) || origem < 0 || origem > 8) erros.push('Origem deve ser entre 0 e 8');
        if (cst && csosn) erros.push('CST e CSOSN não podem estar preenchidos ao mesmo tempo');
        if ((crt === '1' || crt === '2') && cst) erros.push('Simples Nacional deve usar CSOSN, não CST');
        if (crt === '3' && csosn) erros.push('Regime Normal deve usar CST, não CSOSN');

        return { ok: erros.length === 0, erros };
    },

    extrairErroApi(err, response) {
        if (response) {
            try {
                const data = typeof response === 'object' ? response : JSON.parse(response);
                const d = data.detail;
                if (typeof d === 'string') return d;
                if (Array.isArray(d)) return d.map(x => x.msg || JSON.stringify(x)).join('; ');
            } catch (e) {}
        }
        return err?.message || 'Erro desconhecido';
    },

    setLoadingTabela(loading) {
        const tbody = document.getElementById('tabelaRegras');
        if (!tbody) return;
        if (loading) {
            tbody.innerHTML = '<tr><td colspan="10" class="text-center"><div class="spinner-border spinner-border-sm"></div></td></tr>';
        }
    },

    setLoadingBotao(btnId, loading) {
        const btn = document.getElementById(btnId);
        if (!btn) return;
        if (loading) {
            btn.disabled = true;
            btn.textContent = 'Salvando...';
        } else {
            btn.disabled = false;
            btn.textContent = 'Salvar';
        }
    },

    refreshFeatherIcons() {
        setTimeout(() => {
            try {
                if (typeof feather !== 'undefined' && feather?.replace) feather.replace();
            } catch (e) {}
        }, 100);
    }
};

class RegrasFiscaisIcmsManager {
    constructor() {
        this.empresas = [];
        this.regraEmEdicao = null;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupMascaras();
        this.carregarEmpresas();
        this.carregarRegras();
    }

    setupEventListeners() {
        const form = document.getElementById('formRegra');
        if (form) {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                const btn = document.getElementById('btnSalvarRegra');
                if (btn?.disabled) return;
                RegrasFiscaisIcmsHelpers.setLoadingBotao('btnSalvarRegra', true);
                this.salvarRegra().finally(() => RegrasFiscaisIcmsHelpers.setLoadingBotao('btnSalvarRegra', false));
            });
        }

        const crtEl = document.getElementById('crt');
        if (crtEl) {
            crtEl.addEventListener('change', () => {
                RegrasFiscaisIcmsHelpers.limparCamposIncompativeisCrt(crtEl.value);
                RegrasFiscaisIcmsHelpers.aplicarVisibilidadeCrt(crtEl.value);
            });
        }

        document.getElementById('btnConfirmarExclusao')?.addEventListener('click', () => this.confirmarExclusao());

        let timeoutId;
        ['filtroEmpresa', 'filtroAtivo', 'filtroCrt', 'filtroTipoOperacao'].forEach(id => {
            document.getElementById(id)?.addEventListener('change', () => this.aplicarFiltros());
        });
    }

    setupMascaras() {
        ['ncm_prefix', 'ncm_exato', 'cfop', 'cfop_filtro', 'modalidade_bc_icms', 'modalidade_bc_icms_st'].forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.addEventListener('input', (e) => {
                    const max = id.includes('ncm_exato') ? 8 : (id.includes('modalidade') ? 2 : 4);
                    e.target.value = e.target.value.replace(/\D/g, '').slice(0, max);
                });
            }
        });
        const ufEl = document.getElementById('uf_destinatario');
        if (ufEl) {
            ufEl.addEventListener('input', (e) => {
                e.target.value = e.target.value.replace(/[^a-zA-Z]/g, '').toUpperCase().slice(0, 2);
            });
        }
    }

    getToken() {
        return RegrasFiscaisIcmsHelpers.getToken();
    }

    mostrarAlerta(msg, tipo) {
        RegrasFiscaisIcmsHelpers.mostrarAlerta(msg, tipo);
    }

    async carregarEmpresas() {
        try {
            const token = this.getToken();
            const headers = token ? { Authorization: `Bearer ${token}` } : {};
            const r = await fetch('/api/v1/fiscal/empresa', { headers, credentials: 'include' });
            if (!r.ok) throw new Error('Erro ao carregar empresas');
            const data = await r.json();
            this.empresas = Array.isArray(data) ? data : [];

            const sel = document.getElementById('filtroEmpresa');
            const selForm = document.getElementById('empresa_id');
            if (sel) {
                sel.innerHTML = '<option value="">Todas as empresas</option>';
                this.empresas.forEach(emp => {
                    sel.innerHTML += `<option value="${emp.id}">${this._escapeHtml(emp.razao_social || emp.nome_fantasia || `Empresa ${emp.id}`)}</option>`;
                });
            }
            if (selForm) {
                selForm.innerHTML = '<option value="">Selecione a empresa...</option>';
                this.empresas.forEach(emp => {
                    selForm.innerHTML += `<option value="${emp.id}">${this._escapeHtml(emp.razao_social || emp.nome_fantasia || `Empresa ${emp.id}`)}</option>`;
                });
            }
        } catch (e) {
            this.mostrarAlerta('Erro ao carregar empresas', 'danger');
        }
    }

    _escapeHtml(s) {
        if (s == null) return '';
        const div = document.createElement('div');
        div.textContent = String(s);
        return div.innerHTML;
    }

    async carregarRegras() {
        RegrasFiscaisIcmsHelpers.setLoadingTabela(true);
        try {
            const params = new URLSearchParams();
            const empId = document.getElementById('filtroEmpresa')?.value;
            const ativo = document.getElementById('filtroAtivo')?.value;
            const crt = document.getElementById('filtroCrt')?.value;
            const tipoOp = document.getElementById('filtroTipoOperacao')?.value;
            if (empId) params.append('empresa_id', empId);
            if (ativo) params.append('ativo', ativo);
            if (crt) params.append('crt', crt);
            if (tipoOp) params.append('tipo_operacao', tipoOp);

            const token = this.getToken();
            const headers = token ? { Authorization: `Bearer ${token}` } : {};
            const r = await fetch(`/api/v1/fiscal/regras-fiscais-icms?${params}`, { headers, credentials: 'include' });
            if (!r.ok) {
                const err = await r.json().catch(() => ({}));
                throw new Error(err.detail || `Erro ${r.status}`);
            }
            const regras = await r.json();
            this.renderizarTabela(Array.isArray(regras) ? regras : []);
        } catch (e) {
            RegrasFiscaisIcmsHelpers.setLoadingTabela(false);
            this.mostrarAlerta(RegrasFiscaisIcmsHelpers.extrairErroApi(e), 'danger');
            const tbody = document.getElementById('tabelaRegras');
            if (tbody) tbody.innerHTML = '<tr><td colspan="10" class="text-center text-danger">Erro ao carregar. Tente novamente.</td></tr>';
        }
        RegrasFiscaisIcmsHelpers.refreshFeatherIcons();
    }

    renderizarTabela(regras) {
        const tbody = document.getElementById('tabelaRegras');
        if (!tbody) return;
        tbody.innerHTML = '';

        if (!Array.isArray(regras) || regras.length === 0) {
            tbody.innerHTML = '<tr><td colspan="10" class="text-center text-muted">Nenhuma regra encontrada</td></tr>';
            RegrasFiscaisIcmsHelpers.refreshFeatherIcons();
            return;
        }

        regras.forEach(r => {
            const emp = this.empresas.find(e => e.id === r.empresa_id);
            const empNome = emp ? (emp.razao_social || emp.nome_fantasia || `#${r.empresa_id}`) : `#${r.empresa_id}`;
            const cstCsosn = r.cst_icms || r.csosn || '-';
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${r.id}</td>
                <td>${this._escapeHtml(empNome)}</td>
                <td>${r.ordem_prioridade}</td>
                <td>${RegrasFiscaisIcmsHelpers.formatCRT(r.crt)}</td>
                <td>${RegrasFiscaisIcmsHelpers.formatTipoOperacao(r.tipo_operacao)}</td>
                <td>${this._escapeHtml(r.cfop || '-')}</td>
                <td>${this._escapeHtml(cstCsosn)}</td>
                <td>${r.aliquota_icms != null ? Number(r.aliquota_icms) + '%' : '-'}</td>
                <td><span class="badge ${r.ativo ? 'bg-success' : 'bg-secondary'}">${r.ativo ? 'Sim' : 'Não'}</span></td>
                <td>
                    <button type="button" class="btn btn-outline-primary btn-sm" onclick="regrasFiscaisIcmsManager.abrirModalEditar(${r.id})" title="Editar" aria-label="Editar">
                        <i class="align-middle me-1" data-feather="edit-2"></i> Editar
                    </button>
                    <button type="button" class="btn btn-outline-danger btn-sm ms-1" onclick="regrasFiscaisIcmsManager.excluirRegra(${r.id})" title="Excluir" aria-label="Excluir">
                        <i class="align-middle" data-feather="trash-2"></i>
                    </button>
                </td>`;
            tbody.appendChild(row);
        });
        RegrasFiscaisIcmsHelpers.refreshFeatherIcons();
    }

    aplicarFiltros() {
        this.carregarRegras();
    }

    abrirModalNova() {
        this.regraEmEdicao = null;
        document.getElementById('modalRegraTitulo').textContent = 'Nova Regra Fiscal ICMS';
        document.getElementById('modalRegra').style.display = 'block';
        this.limparFormulario();
        RegrasFiscaisIcmsHelpers.aplicarVisibilidadeCrt(document.getElementById('crt')?.value);
        document.getElementById('empresa_id')?.focus();
    }

    async abrirModalEditar(id) {
        try {
            const token = this.getToken();
            const headers = token ? { Authorization: `Bearer ${token}` } : {};
            const r = await fetch(`/api/v1/fiscal/regras-fiscais-icms/${id}`, { headers, credentials: 'include' });
            if (!r.ok) throw new Error('Regra não encontrada');
            const regra = await r.json();
            this.regraEmEdicao = regra;
            document.getElementById('modalRegraTitulo').textContent = 'Editar Regra Fiscal ICMS';
            document.getElementById('modalRegra').style.display = 'block';
            this.preencherFormulario(regra);
            RegrasFiscaisIcmsHelpers.aplicarVisibilidadeCrt(String(regra.crt || ''));
        } catch (e) {
            this.mostrarAlerta(RegrasFiscaisIcmsHelpers.extrairErroApi(e), 'danger');
        }
    }

    preencherFormulario(regra) {
        const set = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.value = val != null ? val : '';
        };
        set('regra_id', regra.id);
        set('empresa_id', regra.empresa_id);
        set('ordem_prioridade', regra.ordem_prioridade);
        set('ativo', regra.ativo ? 'true' : 'false');
        set('crt', regra.crt ?? '');
        set('tipo_operacao', regra.tipo_operacao ?? '');
        set('tipo_destinatario', regra.tipo_destinatario ?? '');
        set('uf_destinatario', regra.uf_destinatario ?? '');
        set('ncm_prefix', regra.ncm_prefix ?? '');
        set('ncm_exato', regra.ncm_exato ?? '');
        set('cest', regra.cest ?? '');
        set('cfop_filtro', regra.cfop_filtro ?? '');
        set('vigencia_inicio', regra.vigencia_inicio ?? '');
        set('vigencia_fim', regra.vigencia_fim ?? '');
        set('cfop', regra.cfop ?? '');
        set('origem_mercadoria', regra.origem_mercadoria ?? 0);
        set('cst_icms', regra.cst_icms ?? '');
        set('csosn', regra.csosn ?? '');
        set('aliquota_icms', regra.aliquota_icms ?? 0);
        set('modalidade_bc_icms', regra.modalidade_bc_icms ?? '');
        set('percentual_reducao_bc', regra.percentual_reducao_bc ?? '');
        set('permite_credito_icms', regra.permite_credito_icms == null ? '' : (regra.permite_credito_icms ? 'true' : 'false'));
        set('gera_icms_st', regra.gera_icms_st ? 'true' : 'false');
        set('aliquota_icms_st', regra.aliquota_icms_st ?? '');
        set('modalidade_bc_icms_st', regra.modalidade_bc_icms_st ?? '');
        set('percentual_mva_st', regra.percentual_mva_st ?? '');
        set('observacao_interna', regra.observacao_interna ?? '');
    }

    limparFormulario() {
        this.preencherFormulario({
            empresa_id: '', ordem_prioridade: 100, ativo: true, crt: '', tipo_operacao: '', tipo_destinatario: '',
            uf_destinatario: '', ncm_prefix: '', ncm_exato: '', cest: '', cfop_filtro: '', vigencia_inicio: '', vigencia_fim: '',
            cfop: '', origem_mercadoria: 0, cst_icms: '', csosn: '', aliquota_icms: 0,
            modalidade_bc_icms: '', percentual_reducao_bc: '', permite_credito_icms: '',
            gera_icms_st: false, aliquota_icms_st: '', modalidade_bc_icms_st: '', percentual_mva_st: '',
            observacao_interna: ''
        });
        document.getElementById('regra_id').value = '';
    }

    coletarPayload(isEdit) {
        const get = (id) => document.getElementById(id)?.value?.trim?.() ?? document.getElementById(id)?.value ?? '';
        const payload = {
            ordem_prioridade: parseInt(get('ordem_prioridade') || '100', 10),
            ativo: get('ativo') === 'true',
            crt: get('crt') ? parseInt(get('crt'), 10) : null,
            tipo_operacao: get('tipo_operacao') || null,
            tipo_destinatario: get('tipo_destinatario') || null,
            uf_destinatario: get('uf_destinatario') || null,
            ncm_prefix: get('ncm_prefix') || null,
            ncm_exato: get('ncm_exato') || null,
            cest: get('cest') || null,
            cfop_filtro: get('cfop_filtro') || null,
            vigencia_inicio: get('vigencia_inicio') || null,
            vigencia_fim: get('vigencia_fim') || null,
            cfop: get('cfop'),
            origem_mercadoria: parseInt(get('origem_mercadoria') || '0', 10),
            cst_icms: get('cst_icms') || null,
            csosn: get('csosn') || null,
            aliquota_icms: parseFloat(get('aliquota_icms') || '0') || 0,
            modalidade_bc_icms: get('modalidade_bc_icms') || null,
            percentual_reducao_bc: get('percentual_reducao_bc') ? parseFloat(get('percentual_reducao_bc')) : null,
            permite_credito_icms: get('permite_credito_icms') === '' ? null : (get('permite_credito_icms') === 'true'),
            gera_icms_st: get('gera_icms_st') === 'true',
            aliquota_icms_st: get('aliquota_icms_st') ? parseFloat(get('aliquota_icms_st')) : null,
            modalidade_bc_icms_st: get('modalidade_bc_icms_st') || null,
            percentual_mva_st: get('percentual_mva_st') ? parseFloat(get('percentual_mva_st')) : null,
            observacao_interna: get('observacao_interna') || null
        };
        if (!isEdit) {
            payload.empresa_id = parseInt(get('empresa_id'), 10);
        }
        return payload;
    }

    async salvarRegra() {
        const val = RegrasFiscaisIcmsHelpers.validarFormularioRegra();
        if (!val.ok) {
            this.mostrarAlerta(val.erros.join('. '), 'warning');
            return;
        }
        const isEdit = !!this.regraEmEdicao?.id;
        const payload = this.coletarPayload(isEdit);
        try {
            const token = this.getToken();
            const headers = { 'Content-Type': 'application/json' };
            if (token) headers.Authorization = `Bearer ${token}`;
            const url = isEdit ? `/api/v1/fiscal/regras-fiscais-icms/${this.regraEmEdicao.id}` : '/api/v1/fiscal/regras-fiscais-icms';
            const method = isEdit ? 'PUT' : 'POST';
            const r = await fetch(url, { method, headers, body: JSON.stringify(payload), credentials: 'include' });
            const data = await r.json().catch(() => ({}));
            if (!r.ok) throw new Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail || data)));
            this.mostrarAlerta(isEdit ? 'Regra atualizada com sucesso.' : 'Regra criada com sucesso.', 'success');
            fecharModalRegra();
            this.carregarRegras();
        } catch (e) {
            this.mostrarAlerta(RegrasFiscaisIcmsHelpers.extrairErroApi(e), 'danger');
        }
    }

    excluirRegra(id) {
        this._regraParaExcluir = id;
        document.getElementById('modalConfirmarExclusao').style.display = 'block';
    }

    async confirmarExclusao() {
        const id = this._regraParaExcluir;
        if (!id) return;
        try {
            const token = this.getToken();
            const headers = {};
            if (token) headers.Authorization = `Bearer ${token}`;
            const r = await fetch(`/api/v1/fiscal/regras-fiscais-icms/${id}`, { method: 'DELETE', headers, credentials: 'include' });
            if (!r.ok) {
                const data = await r.json().catch(() => ({}));
                throw new Error(data.detail || 'Erro ao excluir');
            }
            this.mostrarAlerta('Regra excluída com sucesso.', 'success');
            fecharModalConfirmarExclusao();
            this.carregarRegras();
        } catch (e) {
            this.mostrarAlerta(RegrasFiscaisIcmsHelpers.extrairErroApi(e), 'danger');
        }
        this._regraParaExcluir = null;
    }
}

let regrasFiscaisIcmsManager;
document.addEventListener('DOMContentLoaded', () => {
    regrasFiscaisIcmsManager = new RegrasFiscaisIcmsManager();
    window.regrasFiscaisIcmsManager = regrasFiscaisIcmsManager;
});
