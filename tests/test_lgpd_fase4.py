"""Testes — LGPD Fase 4 multi-brand."""
from unittest.mock import MagicMock, patch

from app.core.billing_secrets import BILLING_SECRET_KEYS, decrypt_stored_secret, encrypt_stored_secret
from app.core.pii import apply_usuario_pii_mask, mask_cpf
from app.core.pii_access import PERMISSAO_PII
from app.services import lgpd_service as lgs


def test_mask_cpf():
    assert mask_cpf("123.456.789-09") == "***.***.***-09"
    assert mask_cpf(None) is None


def test_apply_usuario_pii_mask_oculta_sem_permissao():
    payload = {"cpf": "123.456.789-09", "rg": "1234567", "documento_path": "/static/x.pdf"}
    masked = apply_usuario_pii_mask(payload, reveal=False)
    assert masked["cpf"].startswith("***")
    assert masked["documento_path"] == "[documento restrito]"


def test_apply_cliente_pii_mask_oculta_sem_permissao():
    from app.core.pii import apply_cliente_pii_mask

    payload = {
        "cpf": "123.456.789-09",
        "cnpj": "12.345.678/0001-99",
        "telefone": "11999998888",
        "email": "loja@exemplo.com",
    }
    masked = apply_cliente_pii_mask(payload, reveal=False)
    assert masked["cpf"].startswith("***")
    assert masked["cnpj"].startswith("**")
    assert masked["telefone"].startswith("****")
    assert "@" in masked["email"] and "***" in masked["email"]


def test_user_can_view_pii_cliente_administrador():
    from app.core.pii_access import user_can_view_pii

    user = MagicMock()
    user.id = 1
    user.role = MagicMock(nome="Cliente Administrador")
    with patch("app.core.pii_access.get_user_permissions", return_value=[]):
        assert user_can_view_pii(MagicMock(), user) is True


def test_billing_secret_roundtrip():
    with patch.dict("os.environ", {"PAYMENT_CREDENTIALS_PASSWORD": "test-secret-key-phase4"}):
        enc = encrypt_stored_secret("APP_USR-token-12345")
        assert enc.startswith("enc:v1:")
        assert decrypt_stored_secret(enc) == "APP_USR-token-12345"
        assert decrypt_stored_secret("plaintext-legacy") == "plaintext-legacy"


def test_billing_secret_keys_include_mp_token():
    assert "billing_mp_access_token" in BILLING_SECRET_KEYS


def test_exportar_dados_brand_scope_rejeita_outra_marca():
    db = MagicMock()
    consumidor = MagicMock()
    consumidor.id = 1
    consumidor.tenant_id = 10
    tenant_outro = MagicMock()
    tenant_outro.brand_id = 99

    def query_side(model):
        q = MagicMock()
        if getattr(model, "__name__", "") == "ConsumidorMarketplace":
            q.filter.return_value.first.return_value = consumidor
        elif getattr(model, "__name__", "") == "Tenant":
            q.filter.return_value.first.return_value = tenant_outro
        else:
            q.filter.return_value.all.return_value = []
            q.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        return q

    db.query.side_effect = query_side
    with patch.object(lgs, "get_ibix_brand_id", return_value=1):
        with patch.object(lgs, "assert_consumidor_ibix_scope"):
            try:
                lgs.exportar_dados(db, 1, brand_id=1)
            except ValueError as e:
                assert str(e) == "CONSUMIDOR_BRAND_SCOPE"
            else:
                raise AssertionError("expected CONSUMIDOR_BRAND_SCOPE")


def test_permissao_pii_slug():
    assert PERMISSAO_PII == "pii:visualizar"
