"""Regra de comprador no checkout: sessão (JWT) alinhada ao e-mail e tenant (ou legado tenant NULL)."""
from unittest.mock import MagicMock, patch

from app.schemas.marketplace import CheckoutItem, PedidoCheckoutCreate
from app.services.marketplace_checkout_pedido_service import resolve_comprador_para_loja


def _body() -> PedidoCheckoutCreate:
    return PedidoCheckoutCreate(
        loja_id=1,
        itens=[CheckoutItem(anuncio_id=1, quantidade=1)],
        comprador_nome="Nome",
        comprador_email="comprador@exemplo.com",
        aceite_politica_privacidade=True,
    )


def _loja(cliente_id: int = 42) -> MagicMock:
    loja = MagicMock()
    loja.cliente_id = cliente_id
    return loja


@patch("app.services.marketplace_guest_service.get_or_create_consumidor")
def test_reusa_sessao_tenant_igual_loja_mesmo_email(mock_goc):
    loja = _loja(42)
    body = _body()
    consumidor = MagicMock()
    consumidor.tenant_id = 42
    consumidor.email = "comprador@exemplo.com"
    c, created = resolve_comprador_para_loja(MagicMock(), loja, body, consumidor)
    assert c is consumidor
    assert created is False
    mock_goc.assert_not_called()


@patch("app.services.marketplace_guest_service.get_or_create_consumidor")
def test_reusa_sessao_tenant_nulo_legado_mesmo_email(mock_goc):
    loja = _loja(42)
    body = _body()
    consumidor = MagicMock()
    consumidor.tenant_id = None
    consumidor.email = "comprador@exemplo.com"
    c, created = resolve_comprador_para_loja(MagicMock(), loja, body, consumidor)
    assert c is consumidor
    assert created is False
    mock_goc.assert_not_called()


@patch("app.services.marketplace_guest_service.get_or_create_consumidor")
def test_tenant_diferente_nao_reusa_mesmo_email(mock_goc):
    loja = _loja(99)
    body = _body()
    guest = MagicMock()
    mock_goc.return_value = (guest, True)
    consumidor = MagicMock()
    consumidor.tenant_id = 10
    consumidor.email = "comprador@exemplo.com"
    c, created = resolve_comprador_para_loja(MagicMock(), loja, body, consumidor)
    assert c is guest
    assert created is True
    mock_goc.assert_called_once()


@patch("app.services.marketplace_guest_service.get_or_create_consumidor")
def test_mesmo_tenant_email_formulario_diferente_vai_guest(mock_goc):
    loja = _loja(42)
    body = _body()
    body = body.model_copy(update={"comprador_email": "outro@exemplo.com"})
    guest = MagicMock()
    mock_goc.return_value = (guest, True)
    consumidor = MagicMock()
    consumidor.tenant_id = 42
    consumidor.email = "comprador@exemplo.com"
    c, created = resolve_comprador_para_loja(MagicMock(), loja, body, consumidor)
    assert c is guest
    assert created is True
    mock_goc.assert_called_once()
    call_kw = mock_goc.call_args[1]
    assert call_kw["email"] == "outro@exemplo.com"
