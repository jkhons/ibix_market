function getToken() {
    const v = (`; ${document.cookie}`).split('; pdv_automscale_token=');
    return v.length === 2 ? v.pop().split(';').shift() : null;
}
function fmt(d) { return d ? new Date(d).toLocaleDateString('pt-BR') : '-'; }
function badge(r) { return r ? '<span class="badge bg-' + (r === 'conforme' ? 'success' : 'danger') + '">' + r + '</span>' : '-'; }

async function listar() {
    const tbody = document.getElementById('tabela');
    if (!tbody) return;
    const ano = document.getElementById('filtroAno')?.value || '';
    const resultado = document.getElementById('filtroResultado')?.value || '';
    let url = '/api/v1/auditorias-internas?';
    if (ano) url += 'ano=' + ano + '&';
    if (resultado) url += 'resultado=' + resultado + '&';
    try {
        const r = await fetch(url, { headers: { 'Authorization': 'Bearer ' + getToken() } });
        const lista = await r.json();
        if (!lista || !lista.length) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">Nenhuma auditoria</td></tr>';
            return;
        }
        tbody.innerHTML = lista.map(a => `
            <tr>
                <td><a href="/qualidade/auditorias-internas/${a.id}">${a.numero || '-'}</a></td>
                <td>${fmt(a.data_planejada)}</td>
                <td>${(a.escopo || '').substring(0, 50)}${(a.escopo||'').length > 50 ? '...' : ''}</td>
                <td>${badge(a.resultado)}</td>
                <td>
                    <a href="/qualidade/auditorias-internas/${a.id}" class="btn btn-sm btn-outline-primary"><i data-feather="eye"></i></a>
                    <button class="btn btn-sm btn-outline-primary" onclick="editar(${a.id})"><i data-feather="edit-2"></i></button>
                </td>
            </tr>
        `).join('');
        if (typeof feather !== 'undefined') feather.replace();
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-danger">Erro</td></tr>';
    }
}

function fecharModalAud() {
    const m = document.getElementById('modalAudCustom');
    if (m) { m.style.display = 'none'; document.body.style.overflow = ''; }
}
function abrirModalNovo() {
    document.getElementById('modalAudTitulo').textContent = 'Nova Auditoria';
    document.getElementById('formAud').reset();
    document.getElementById('audId').value = '';
    document.getElementById('audDataPlanejada').value = new Date().toISOString().slice(0, 10);
    const m = document.getElementById('modalAudCustom');
    if (m) { m.style.display = 'block'; document.body.style.overflow = 'hidden'; }
}

async function editar(id) {
    const r = await fetch('/api/v1/auditorias-internas/' + id, { headers: { 'Authorization': 'Bearer ' + getToken() } });
    const a = await r.json();
    document.getElementById('modalAudTitulo').textContent = 'Editar Auditoria';
    document.getElementById('audId').value = a.id;
    document.getElementById('audEscopo').value = a.escopo || '';
    document.getElementById('audDataPlanejada').value = a.data_planejada ? a.data_planejada.slice(0, 10) : '';
    document.getElementById('audDataRealizada').value = a.data_realizada ? a.data_realizada.slice(0, 10) : '';
    document.getElementById('audAuditores').value = a.auditores || '';
    document.getElementById('audResultado').value = a.resultado || '';
    document.getElementById('audNC').value = a.nao_conformidades || '';
    document.getElementById('audPlano').value = a.plano_acao || '';
    const m = document.getElementById('modalAudCustom');
    if (m) { m.style.display = 'block'; document.body.style.overflow = 'hidden'; }
}

async function salvar() {
    const id = document.getElementById('audId').value;
    const body = {
        escopo: document.getElementById('audEscopo').value.trim(),
        data_planejada: document.getElementById('audDataPlanejada').value,
        data_realizada: document.getElementById('audDataRealizada').value || null,
        auditores: document.getElementById('audAuditores').value.trim() || null,
        resultado: document.getElementById('audResultado').value || null,
        nao_conformidades: document.getElementById('audNC').value.trim() || null,
        plano_acao: document.getElementById('audPlano').value.trim() || null
    };
    const url = id ? '/api/v1/auditorias-internas/' + id : '/api/v1/auditorias-internas';
    const method = id ? 'PUT' : 'POST';
    const r = await fetch(url, { method, headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + getToken() }, body: JSON.stringify(body) });
    if (!r.ok) { const err = await r.json(); alert(err.detail || 'Erro'); return; }
    fecharModalAud();
    listar();
}

async function carregarDetalhe(id) {
    try {
        const r = await fetch('/api/v1/auditorias-internas/' + id, { headers: { 'Authorization': 'Bearer ' + getToken() } });
        if (!r.ok) throw new Error('Não encontrada');
        const a = await r.json();
        document.getElementById('loading').classList.add('d-none');
        document.getElementById('conteudo').classList.remove('d-none');
        document.getElementById('bcNumero').textContent = a.numero;
        document.getElementById('tituloAud').textContent = 'Auditoria ' + a.numero;
        document.getElementById('numero').textContent = a.numero || '-';
        document.getElementById('dataPlanejada').textContent = fmt(a.data_planejada);
        document.getElementById('dataRealizada').textContent = fmt(a.data_realizada);
        document.getElementById('auditores').textContent = a.auditores || '-';
        document.getElementById('resultado').innerHTML = badge(a.resultado);
        document.getElementById('escopo').textContent = a.escopo || '-';
        document.getElementById('naoConformidades').textContent = a.nao_conformidades || '-';
        document.getElementById('planoAcao').textContent = a.plano_acao || '-';
        document.getElementById('formEditar').dataset.audId = id;
        if (typeof feather !== 'undefined') feather.replace();
    } catch (e) {
        document.getElementById('loading').innerHTML = '<p class="text-danger">Erro ao carregar</p>';
    }
}

function fecharModalEditarAud() {
    const m = document.getElementById('modalEditarAudCustom');
    if (m) { m.style.display = 'none'; document.body.style.overflow = ''; }
}
function abrirModalEditar() {
    const id = document.getElementById('formEditar')?.dataset?.audId;
    if (!id) return;
    fetch('/api/v1/auditorias-internas/' + id, { headers: { 'Authorization': 'Bearer ' + getToken() } })
        .then(r => r.json())
        .then(a => {
            document.getElementById('editId').value = a.id;
            document.getElementById('editEscopo').value = a.escopo || '';
            document.getElementById('editDataPlanejada').value = a.data_planejada ? a.data_planejada.slice(0, 10) : '';
            document.getElementById('editDataRealizada').value = a.data_realizada ? a.data_realizada.slice(0, 10) : '';
            document.getElementById('editAuditores').value = a.auditores || '';
            document.getElementById('editResultado').value = a.resultado || '';
            document.getElementById('editNC').value = a.nao_conformidades || '';
            document.getElementById('editPlano').value = a.plano_acao || '';
            const m = document.getElementById('modalEditarAudCustom');
            if (m) { m.style.display = 'block'; document.body.style.overflow = 'hidden'; }
        });
}

async function salvarEdicao() {
    const id = document.getElementById('editId').value;
    const body = {
        escopo: document.getElementById('editEscopo').value.trim(),
        data_planejada: document.getElementById('editDataPlanejada').value,
        data_realizada: document.getElementById('editDataRealizada').value || null,
        auditores: document.getElementById('editAuditores').value.trim() || null,
        resultado: document.getElementById('editResultado').value || null,
        nao_conformidades: document.getElementById('editNC').value.trim() || null,
        plano_acao: document.getElementById('editPlano').value.trim() || null
    };
    const r = await fetch('/api/v1/auditorias-internas/' + id, { method: 'PUT', headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + getToken() }, body: JSON.stringify(body) });
    if (!r.ok) { alert('Erro ao salvar'); return; }
    fecharModalEditarAud();
    carregarDetalhe(id);
}
