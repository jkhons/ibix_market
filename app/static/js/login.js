// PDV - Script de Login
window.addEventListener('load', function() {
    const loginForm = document.getElementById('login-form');
    const alertArea = document.getElementById('alert-area');
    const loginBtn = document.getElementById('login-btn');
    if (!loginForm || !alertArea || !loginBtn) return;

    function showError(message) {
        var msg = (message && String(message).trim()) ? message : 'Ocorreu um erro. Tente novamente.';
        alertArea.innerHTML = '<div class="alert alert-danger alert-dismissible fade show d-flex align-items-center" role="alert">' +
            '<span class="me-2" aria-hidden="true">&#9888;</span>' +
            '<span class="flex-grow-1">' + msg + '</span>' +
            '<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Fechar"></button></div>';
        alertArea.style.display = '';
        alertArea.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    function clearAlert() {
        alertArea.innerHTML = '';
    }

    function setLoading(loading) {
        const btnText = loginBtn.querySelector('.btn-text');
        const btnLoading = loginBtn.querySelector('.btn-loading');
        if (btnText && btnLoading) {
            loginBtn.disabled = loading;
            btnText.classList.toggle('d-none', loading);
            btnLoading.classList.toggle('d-none', !loading);
        }
    }

    function getErrorMessage(response, data) {
        if (data && data.message) return data.message;
        const detail = data && data.detail;
        if (typeof detail === 'string') return detail;
        if (Array.isArray(detail) && detail.length > 0) return typeof detail[0] === 'string' ? detail[0] : String(detail[0]);
        if (detail && detail.msg) return detail.msg;
        if (detail && detail.message) return detail.message;
        if (detail && detail.error) return detail.error;
        if (response && response.status === 401) return 'E-mail ou senha incorretos. Verifique e tente novamente.';
        if (response && response.status === 429) return 'Muitas tentativas. Aguarde alguns instantes e tente novamente.';
        if (response && response.status >= 500) return 'Erro temporário no servidor. Tente novamente em instantes.';
        return 'Não foi possível entrar. Tente novamente.';
    }

    loginForm.addEventListener('submit', function(e) {
        e.preventDefault();
        clearAlert();
        setLoading(true);

        const email = document.getElementById('email').value.trim();
        const password = document.getElementById('password').value;

        fetch('/api/v1/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ email: email, password: password })
        })
        .then(function(response) {
            return response.json().then(function(data) {
                return { response: response, data: data };
            }).catch(function() {
                return { response: response, data: {} };
            });
        })
        .then(function(result) {
            var response = result.response;
            var data = result.data;

            if (response.ok && data.success && data.token && data.token.access_token) {
                const tok = data.token.access_token;
                try { sessionStorage.setItem('pdv_automscale_token', tok); } catch (_) {}
                document.cookie = 'pdv_automscale_token=' + tok + '; path=/; max-age=28800; SameSite=Lax' + (location.protocol === 'https:' ? '; Secure' : '');
                window.location.href = '/dashboard';
                return;
            }

            var msg = getErrorMessage(response, data);
            showError(msg);
        })
        .catch(function(error) {
            var msg = (error && error.message) ? error.message : 'Erro de conexão. Verifique sua internet e tente novamente.';
            showError(msg);
        })
        .finally(function() {
            setLoading(false);
        });
    });
}); 