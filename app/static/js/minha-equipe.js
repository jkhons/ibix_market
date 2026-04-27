(function() {
    function getToken() {
        var v = document.cookie.match(/(?:^|;\s*)pdv_automscale_token=([^;]*)/);
        return v ? v[1] : null;
    }
    function authHeaders() {
        var t = getToken();
        return { "Content-Type": "application/json", "Authorization": "Bearer " + (t || "") };
    }
    function alertMsg(containerId, type, msg) {
        var c = document.getElementById(containerId);
        if (!c) return;
        c.innerHTML = '<div class="alert alert-' + type + ' alert-dismissible fade show">' + msg + '<button type="button" class="btn-close" data-bs-dismiss="alert"></button></div>';
    }
    function clearAlert(containerId) {
        var c = document.getElementById(containerId);
        if (c) c.innerHTML = "";
    }

    function loadTecnicos() {
        var el = document.getElementById("lista-tecnicos");
        if (!el) return;
        el.innerHTML = '<p class="text-muted">Carregando...</p>';
        fetch("/api/v1/minha-equipe/tecnicos", { headers: authHeaders() })
            .then(function(r) {
                if (!r.ok) throw new Error("Erro ao carregar técnicos");
                return r.json();
            })
            .then(function(tecnicos) {
                if (tecnicos.length === 0) {
                    el.innerHTML = '<p class="text-muted">Nenhum técnico vinculado. Clique em "Vincular técnico" e informe o email.</p>';
                    return;
                }
                var html = '<div class="table-responsive"><table class="table table-sm"><thead><tr><th>Nome</th><th>Email</th><th></th></tr></thead><tbody>';
                tecnicos.forEach(function(t) {
                    html += '<tr><td>' + (t.nome || '') + '</td><td>' + (t.email || '') + '</td><td><button type="button" class="btn btn-sm btn-outline-danger btn-desvincular" data-id="' + t.id + '">Desvincular</button></td></tr>';
                });
                html += '</tbody></table></div>';
                el.innerHTML = html;
                document.querySelectorAll(".btn-desvincular").forEach(function(btn) {
                    btn.addEventListener("click", function() {
                        var id = parseInt(this.getAttribute("data-id"), 10);
                        if (!confirm("Desvincular este técnico da sua equipe?")) return;
                        fetch("/api/v1/minha-equipe/tecnicos/" + id, { method: "DELETE", headers: authHeaders() })
                            .then(function(r) {
                                if (r.ok) loadTecnicos();
                                else r.json().then(function(d) { alertMsg("alert-minha-equipe", "danger", d.detail || "Erro"); });
                            });
                    });
                });
            })
            .catch(function(e) {
                el.innerHTML = '<p class="text-danger">' + (e.message || "Erro ao carregar.") + '</p>';
            });
    }

    document.addEventListener("DOMContentLoaded", function() {
        loadTecnicos();

        document.getElementById("btnVincularTecnico").addEventListener("click", function() {
            document.getElementById("inputTecnicoNome").value = "";
            document.getElementById("inputTecnicoEmail").value = "";
            document.getElementById("inputTecnicoSenha").value = "";
            var m = document.getElementById("modalVincularTecnicoCustom");
            if (m) { m.style.display = "block"; document.body.style.overflow = "hidden"; }
        });

        document.getElementById("btnConfirmarVincularTecnico").addEventListener("click", function() {
            var nome = document.getElementById("inputTecnicoNome").value.trim();
            var email = document.getElementById("inputTecnicoEmail").value.trim();
            var senha = document.getElementById("inputTecnicoSenha").value;
            if (!email) {
                alertMsg("alert-minha-equipe", "warning", "Informe o email do técnico.");
                return;
            }
            var body = { email: email };
            if (nome) body.nome = nome;
            if (senha) body.senha = senha;
            fetch("/api/v1/minha-equipe/tecnicos", {
                method: "POST",
                headers: authHeaders(),
                body: JSON.stringify(body)
            })
                .then(function(r) {
                    if (r.ok) {
                        fecharModalVincularTecnico();
                        loadTecnicos();
                        clearAlert("alert-minha-equipe");
                    } else {
                        return r.json().then(function(d) {
                            alertMsg("alert-minha-equipe", "danger", (d.detail && (d.detail.message || d.detail)) || "Erro");
                        });
                    }
                })
                .catch(function(e) {
                    alertMsg("alert-minha-equipe", "danger", e.message || "Erro.");
                });
        });
    });

    function fecharModalVincularTecnico() {
        var m = document.getElementById("modalVincularTecnicoCustom");
        if (m) { m.style.display = "none"; document.body.style.overflow = ""; }
    }
    window.fecharModalVincularTecnico = fecharModalVincularTecnico;
})();
