/**
 * Reclamações (ISO 17025 5.8)
 */
function getToken() {
    const v = (`; ${document.cookie}`).split('; pdv_automscale_token=');
    return v.length === 2 ? v.pop().split(';').shift() : null;
}

function apiFetch(url, options) {
    const opts = options || {};
    opts.headers = opts.headers || {};
    opts.headers['Authorization'] = `Bearer ${getToken()}`;
    if (opts.body && typeof opts.body === 'object' && !(opts.body instanceof FormData)) {
        opts.headers['Content-Type'] = 'application/json';
        opts.body = JSON.stringify(opts.body);
    }
    return fetch(url, opts);
}

function statusBadge(s) {
    const map = { aberta: 'warning', em_analise: 'info', concluida: 'success' };
    return `<span class="badge bg-${map[s] || 'secondary'}">${s || '-'}</span>`;
}

function formatDate(d) {
    if (!d) return '-';
    return new Date(d).toLocaleDateString('pt-BR');
}

function truncar(str, n) {
    if (!str) return '-';
    return str.length > n ? str.substring(0, n) + '...' : str;
}

async function carregarClientesSelect(selectId) {
    const sel = document.getElementById(selectId);
    if (!sel) return;
    const isFiltro = selectId.indexOf('filtro') >= 0;
    try {
        const r = await apiFetch('/api/v1/clientes/todos');
        const lista = await r.json();
        const items = Array.isArray(lista) ? lista : (lista.items || lista.data || []);
        sel.innerHTML = isFiltro ? '<option value="">Todos</option>' : '<option value="">Selecione...</option>';
        items.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c.id;
            opt.textContent = c.nome || c.razao_social || 'Cliente #' + c.id;
            sel.appendChild(opt);
        });
    } catch (e) {
        console.warn('Erro ao carregar clientes', e);
    }
}

async function listarReclamacoes() {
    const tbody = document.getElementById('tabelaReclamacoes');
    if (!tbody) return;
    const status = document.getElementById('filtroStatus')?.value || '';
    const clienteId = document.getElementById('filtroCliente')?.value || '';
    const params = new URLSearchParams();
    if (status) params.set('status', status);
    if (clienteId) params.set('cliente_id', clienteId);
    const url = '/api/v1/reclamacoes' + (params.toString() ? '?' + params : '');
    try {
        const r = await apiFetch(url);
        const lista = await r.json();
        if (!lista || !lista.length) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">Nenhuma reclamação</td></tr>';
            return;
        }
        tbody.innerHTML = lista.map(rec => `
            <tr>
                <td><a href="/reclamacoes/${rec.id}">${rec.numero || '-'}</a></td>
                <td>${formatDate(rec.data_abertura)}</td>
                <td>${rec.cliente_nome || '-'}</td>
                <td>${truncar(rec.descricao, 50)}</td>
                <td>${statusBadge(rec.status)}</td>
                <td>
                    <a href="/reclamacoes/${rec.id}" class="btn btn-sm btn-outline-primary"><i data-feather="eye"></i></a>
                </td>
            </tr>
        `).join('');
        if (typeof feather !== 'undefined') feather.replace();
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-danger">Erro ao carregar</td></tr>';
    }
}

function aplicarFiltros() {
    listarReclamacoes();
}

async function salvarNovaReclamacao() {
    const dataAbertura = document.getElementById('novaDataAbertura').value;
    const descricao = document.getElementById('novaDescricao').value.trim();
    if (!descricao) {
        alert('Informe a descrição');
        return;
    }
    const clienteId = document.getElementById('novaCliente')?.value || null;
    const body = {
        data_abertura: dataAbertura,
        descricao: descricao,
        status: 'aberta',
        cliente_id: clienteId ? parseInt(clienteId, 10) : null
    };
    try {
        const r = await apiFetch('/api/v1/reclamacoes', { method: 'POST', body });
        if (!r.ok) {
            const err = await r.json();
            alert(err.detail || 'Erro ao salvar');
            return;
        }
        const rec = await r.json();
        bootstrap.Modal.getInstance(document.getElementById('modalNovaReclamacao')).hide();
        window.location.href = '/reclamacoes/' + rec.id;
    } catch (e) {
        alert('Erro ao salvar');
    }
}

async function carregarDetalheReclamacao(id) {
    const loading = document.getElementById('loadingDetalhe');
    const erro = document.getElementById('erroDetalhe');
    const conteudo = document.getElementById('conteudoDetalhe');
    try {
        const r = await apiFetch(`/api/v1/reclamacoes/${id}`);
        if (!r.ok) {
            erro.textContent = r.status === 404 ? 'Reclamação não encontrada' : 'Erro ao carregar';
            erro.classList.remove('d-none');
            loading.classList.add('d-none');
            return;
        }
        const rec = await r.json();
        loading.classList.add('d-none');
        conteudo.classList.remove('d-none');

        document.getElementById('breadcrumbNumero').textContent = rec.numero;
        document.getElementById('tituloReclamacao').textContent = 'Reclamação ' + rec.numero;
        document.getElementById('numeroReclamacao').textContent = rec.numero;
        document.getElementById('badgeStatus').className = 'badge bg-' + (rec.status === 'concluida' ? 'success' : rec.status === 'em_analise' ? 'info' : 'warning');
        document.getElementById('badgeStatus').textContent = rec.status;
        document.getElementById('dataAbertura').textContent = formatDate(rec.data_abertura);
        document.getElementById('clienteNome').textContent = rec.cliente_nome || '-';
        document.getElementById('responsavelNome').textContent = rec.responsavel_nome || '-';
        document.getElementById('dataConclusao').textContent = formatDate(rec.data_conclusao) || '-';
        document.getElementById('certificadoRef').textContent = rec.certificado_id ? '#' + rec.certificado_id : '-';
        document.getElementById('processoRef').textContent = rec.processo_id ? '#' + rec.processo_id : '-';
        document.getElementById('descricao').textContent = rec.descricao || '-';
        document.getElementById('analise').textContent = rec.analise || '-';
        document.getElementById('acaoTomada').textContent = rec.acao_tomada || '-';

        if (typeof feather !== 'undefined') feather.replace();
    } catch (e) {
        loading.classList.add('d-none');
        erro.textContent = 'Erro ao carregar';
        erro.classList.remove('d-none');
    }
}

function abrirModalAtualizar() {
    const form = document.getElementById('formAtualizar');
    const id = form ? parseInt(form.dataset.recId || '0', 10) : 0;
    if (!id) return;
    apiFetch(`/api/v1/reclamacoes/${id}`)
        .then(r => r.json())
        .then(rec => {
            document.getElementById('editStatus').value = rec.status || 'aberta';
            document.getElementById('editAnalise').value = rec.analise || '';
            document.getElementById('editAcaoTomada').value = rec.acao_tomada || '';
            document.getElementById('editDataConclusao').value = rec.data_conclusao ? rec.data_conclusao.slice(0, 10) : '';
            form.dataset.recId = rec.id;
            new bootstrap.Modal(document.getElementById('modalAtualizar')).show();
        })
        .catch(() => alert('Erro ao carregar'));
}

async function salvarAtualizacao() {
    const form = document.getElementById('formAtualizar');
    const id = form.dataset.recId;
    if (!id) return;
    const body = {
        status: document.getElementById('editStatus').value,
        analise: document.getElementById('editAnalise').value || null,
        acao_tomada: document.getElementById('editAcaoTomada').value || null,
        data_conclusao: document.getElementById('editDataConclusao').value || null
    };
    try {
        const r = await apiFetch(`/api/v1/reclamacoes/${id}`, { method: 'PUT', body });
        if (!r.ok) {
            const err = await r.json();
            alert(err.detail || 'Erro ao salvar');
            return;
        }
        bootstrap.Modal.getInstance(document.getElementById('modalAtualizar')).hide();
        carregarDetalheReclamacao(id);
        if (typeof feather !== 'undefined') feather.replace();
    } catch (e) {
        alert('Erro ao salvar');
    }
}
