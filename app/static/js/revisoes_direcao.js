function getToken() {
    var v = ('; ' + document.cookie).split('; pdv_automscale_token=');
    return v.length === 2 ? v.pop().split(';').shift() : null;
}
function fmt(d) { return d ? new Date(d).toLocaleDateString('pt-BR') : '-'; }
function trunc(s, n) { return s ? (s.length > n ? s.substring(0, n) + '...' : s) : '-'; }

async function listar() {
    var tbody = document.getElementById('tabela');
    if (!tbody) return;
    try {
        var r = await fetch('/api/v1/revisoes-direcao', { headers: { 'Authorization': 'Bearer ' + getToken() } });
        var lista = await r.json();
        if (!lista || !lista.length) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">Nenhuma revisao</td></tr>';
            return;
        }
        tbody.innerHTML = lista.map(function(rev) {
            return '<tr><td>' + fmt(rev.data_revisao) + '</td><td>' + trunc(rev.participantes, 40) + '</td><td>' + trunc(rev.itens_analisados, 50) + '</td><td><a href="/qualidade/revisoes-direcao/' + rev.id + '" class="btn btn-sm btn-outline-primary"><i data-feather="eye"></i></a></td></tr>';
        }).join('');
        if (typeof feather !== 'undefined') feather.replace();
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-danger">Erro</td></tr>';
    }
}

function fecharModalRev() {
    var m = document.getElementById('modalRevCustom');
    if (m) { m.style.display = 'none'; document.body.style.overflow = ''; }
}
function abrirModalNovo() {
    document.getElementById('modalRevTitulo').textContent = 'Nova Revisão';
    document.getElementById('formRev').reset();
    document.getElementById('revId').value = '';
    document.getElementById('revData').value = new Date().toISOString().slice(0, 10);
    var m = document.getElementById('modalRevCustom');
    if (m) { m.style.display = 'block'; document.body.style.overflow = 'hidden'; }
}

async function salvar() {
    var id = document.getElementById('revId').value;
    var body = {
        data_revisao: document.getElementById('revData').value,
        participantes: document.getElementById('revParticipantes').value.trim() || null,
        itens_analisados: document.getElementById('revItens').value.trim() || null,
        decisoes: document.getElementById('revDecisoes').value.trim() || null,
        proximas_revisoes: document.getElementById('revProximas').value.trim() || null
    };
    var url = id ? '/api/v1/revisoes-direcao/' + id : '/api/v1/revisoes-direcao';
    var method = id ? 'PUT' : 'POST';
    var r = await fetch(url, { method: method, headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + getToken() }, body: JSON.stringify(body) });
    if (!r.ok) { var err = await r.json(); alert(err.detail || 'Erro'); return; }
    fecharModalRev();
    listar();
}

async function carregarDetalhe(id) {
    try {
        var r = await fetch('/api/v1/revisoes-direcao/' + id, { headers: { 'Authorization': 'Bearer ' + getToken() } });
        if (!r.ok) throw new Error('Nao encontrada');
        var rev = await r.json();
        document.getElementById('loading').classList.add('d-none');
        document.getElementById('conteudo').classList.remove('d-none');
        document.getElementById('bcData').textContent = fmt(rev.data_revisao);
        document.getElementById('tituloRev').textContent = 'Revisao de ' + fmt(rev.data_revisao);
        document.getElementById('data').textContent = fmt(rev.data_revisao);
        document.getElementById('participantes').textContent = rev.participantes || '-';
        document.getElementById('itens').textContent = rev.itens_analisados || '-';
        document.getElementById('decisoes').textContent = rev.decisoes || '-';
        document.getElementById('proximas').textContent = rev.proximas_revisoes || '-';
        document.getElementById('formEditar').dataset.revId = id;
        if (typeof feather !== 'undefined') feather.replace();
    } catch (e) {
        document.getElementById('loading').innerHTML = '<p class="text-danger">Erro</p>';
    }
}

function fecharModalEditarRev() {
    var m = document.getElementById('modalEditarRevCustom');
    if (m) { m.style.display = 'none'; document.body.style.overflow = ''; }
}
function abrirModalEditar() {
    var id = document.getElementById('formEditar')?.dataset?.revId;
    if (!id) return;
    fetch('/api/v1/revisoes-direcao/' + id, { headers: { 'Authorization': 'Bearer ' + getToken() } })
        .then(function(r) { return r.json(); })
        .then(function(rev) {
            document.getElementById('editId').value = rev.id;
            document.getElementById('editData').value = rev.data_revisao ? rev.data_revisao.slice(0, 10) : '';
            document.getElementById('editParticipantes').value = rev.participantes || '';
            document.getElementById('editItens').value = rev.itens_analisados || '';
            document.getElementById('editDecisoes').value = rev.decisoes || '';
            document.getElementById('editProximas').value = rev.proximas_revisoes || '';
            var m = document.getElementById('modalEditarRevCustom');
            if (m) { m.style.display = 'block'; document.body.style.overflow = 'hidden'; }
        });
}

async function salvarEdicao() {
    var id = document.getElementById('editId').value;
    var body = {
        data_revisao: document.getElementById('editData').value,
        participantes: document.getElementById('editParticipantes').value.trim() || null,
        itens_analisados: document.getElementById('editItens').value.trim() || null,
        decisoes: document.getElementById('editDecisoes').value.trim() || null,
        proximas_revisoes: document.getElementById('editProximas').value.trim() || null
    };
    var r = await fetch('/api/v1/revisoes-direcao/' + id, { method: 'PUT', headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + getToken() }, body: JSON.stringify(body) });
    if (!r.ok) { alert('Erro ao salvar'); return; }
    fecharModalEditarRev();
    carregarDetalhe(id);
}
