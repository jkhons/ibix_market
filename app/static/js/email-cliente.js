// PDV Ibix - E-mail por cliente (Cliente Administrador)

function mostrarAlertaEmailCliente(mensagem, tipo) {
    const container = document.getElementById('alert-email-cliente');
    if (!container) return;
    container.innerHTML = '<div class="alert alert-' + tipo + ' alert-dismissible fade show">' + mensagem + '<button type="button" class="btn-close" data-bs-dismiss="alert"></button></div>';
}

async function carregarEmailCliente() {
    const container = document.getElementById('email-cliente-container');
    const desativado = document.getElementById('email-cliente-desativado');
    const ajuda = document.getElementById('email-cliente-ajuda');
    if (!container) return;

    try {
        const response = await fetch('/api/v1/email-cliente/', { credentials: 'include' });
        if (!response.ok) {
            container.innerHTML = '<div class="alert alert-danger">Erro ao carregar.</div>';
            return;
        }
        const data = await response.json();

        if (!data.ativo) {
            desativado.classList.remove('d-none');
            ajuda.classList.add('d-none');
            container.innerHTML = '';
            return;
        }
        desativado.classList.add('d-none');
        ajuda.classList.remove('d-none');

        const clientes = data.clientes || [];
        if (clientes.length === 0) {
            container.innerHTML = '<p class="text-muted">Nenhum cliente no seu escopo.</p>';
            return;
        }

        let html = '<div class="table-responsive"><table class="table table-sm table-bordered">';
        html += '<thead><tr><th>Cliente</th><th>E-mail remetente</th><th>Nome remetente</th><th></th></tr></thead><tbody>';
        clientes.forEach(function (c) {
            const idFrom = 'emailClienteFrom_' + c.cliente_id;
            const idName = 'emailClienteName_' + c.cliente_id;
            html += '<tr>';
            html += '<td class="align-middle">' + (c.nome || 'Cliente #' + c.cliente_id) + '</td>';
            html += '<td><input type="email" class="form-control form-control-sm" id="' + idFrom + '" data-cliente-id="' + c.cliente_id + '" placeholder="Deixe vazio para usar o geral" value="' + (c.from_email || '').replace(/"/g, '&quot;') + '"></td>';
            html += '<td><input type="text" class="form-control form-control-sm" id="' + idName + '" data-cliente-id="' + c.cliente_id + '" placeholder="Nome" value="' + (c.from_name || '').replace(/"/g, '&quot;') + '"></td>';
            html += '<td class="align-middle"><button type="button" class="btn btn-sm btn-primary btnSalvarEmailCliente" data-cliente-id="' + c.cliente_id + '">Salvar</button></td>';
            html += '</tr>';
        });
        html += '</tbody></table></div>';
        container.innerHTML = html;

        document.querySelectorAll('.btnSalvarEmailCliente').forEach(function (btn) {
            btn.addEventListener('click', function () {
                const clienteId = parseInt(this.getAttribute('data-cliente-id'), 10);
                salvarEmailCliente(clienteId);
            });
        });

        if (typeof feather !== 'undefined') feather.replace();
    } catch (error) {
        console.error('Erro ao carregar e-mail por cliente:', error);
        container.innerHTML = '<div class="alert alert-danger">Erro ao carregar.</div>';
    }
}

async function salvarEmailCliente(clienteId) {
    const fromEl = document.getElementById('emailClienteFrom_' + clienteId);
    const nameEl = document.getElementById('emailClienteName_' + clienteId);
    if (!fromEl || !nameEl) return;

    const payload = {
        from_email: (fromEl.value || '').trim(),
        from_name: (nameEl.value || '').trim()
    };

    mostrarAlertaEmailCliente('Salvando...', 'info');
    try {
        const response = await fetch('/api/v1/email-cliente/' + clienteId, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(payload)
        });
        if (response.ok) {
            mostrarAlertaEmailCliente('Salvo com sucesso.', 'success');
        } else {
            const err = await response.json();
            mostrarAlertaEmailCliente('Erro: ' + (err.detail || response.statusText), 'danger');
        }
    } catch (error) {
        console.error('Erro ao salvar:', error);
        mostrarAlertaEmailCliente('Erro ao salvar: ' + error.message, 'danger');
    }
}

document.addEventListener('DOMContentLoaded', function () {
    carregarEmailCliente();
});
