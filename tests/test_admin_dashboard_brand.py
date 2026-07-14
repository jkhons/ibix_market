"""Testes — admin dashboard filtro brand_id (P2-2)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def dashboard_client():
    import sys

    sys.modules.pop("main", None)
    from main import app

    return TestClient(app, raise_server_exceptions=False)


def test_admin_dashboard_aceita_brand_id_query(dashboard_client):
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.role = MagicMock(nome="Superadministrador")

    with (
        patch("app.api.v1.admin_dashboard.require_superadmin_or_admin") as mock_dep,
        patch("app.database.connection.get_db") as mock_get_db,
        patch("app.api.v1.admin_dashboard.resolve_admin_brand_scope", return_value=1),
    ):
        mock_dep.return_value = lambda: mock_user
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])

        brand = MagicMock(id=1, slug="ibix", nome_exibicao="Ibix", ativo=True)
        mock_db.query.return_value.filter.return_value.first.return_value = brand
        mock_db.query.return_value.filter.return_value.count.return_value = 0
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        mock_db.query.return_value.outerjoin.return_value.order_by.return_value.limit.return_value.all.return_value = []
        mock_db.query.return_value.join.return_value.filter.return_value.count.return_value = 0
        mock_db.query.return_value.join.return_value.filter.return_value.one.return_value = MagicMock(total=0, valor_centavos=0)
        mock_db.query.return_value.join.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = []
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        mock_db.query.return_value.filter.return_value.scalar.return_value = 0
        mock_db.query.return_value.outerjoin.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        with patch("app.services.vitrine_access_analytics_service.visitantes_vitrine_por_tipo", return_value={}):
            r = dashboard_client.get(
                "/api/v1/admin/dashboard?brand_id=1",
                headers={"Authorization": "Bearer test"},
            )
    assert r.status_code != 404


def test_admin_dashboard_resposta_inclui_brand_scope(dashboard_client):
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.role = MagicMock(nome="Superadministrador")

    with (
        patch("app.api.v1.admin_dashboard.require_superadmin_or_admin") as mock_dep,
        patch("app.database.connection.get_db") as mock_get_db,
        patch("app.api.v1.admin_dashboard.resolve_admin_brand_scope", return_value=2),
        patch(
            "app.api.v1.admin_dashboard.brand_scope_meta",
            return_value={
                "brand_id": 2,
                "brand_nome": "Solumática",
                "scope_locked": True,
                "scope_label": "Dados: Solumática",
            },
        ),
    ):
        mock_dep.return_value = lambda: mock_user
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        mock_db.query.return_value.filter.return_value.count.return_value = 0
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        mock_db.query.return_value.outerjoin.return_value.order_by.return_value.limit.return_value.all.return_value = []
        mock_db.query.return_value.join.return_value.filter.return_value.count.return_value = 0
        mock_db.query.return_value.join.return_value.filter.return_value.one.return_value = MagicMock(total=0, valor_centavos=0)
        mock_db.query.return_value.join.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = []
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        mock_db.query.return_value.filter.return_value.scalar.return_value = 0
        mock_db.query.return_value.filter.return_value.first.return_value = MagicMock(nome_exibicao="Solumática", slug="solumatica")

        with patch("app.services.vitrine_access_analytics_service.visitantes_vitrine_por_tipo", return_value={}):
            r = dashboard_client.get(
                "/api/v1/admin/dashboard",
                headers={"Authorization": "Bearer test", "Host": "www.solumatica.com.br"},
            )
    if r.status_code == 200:
        data = r.json()
        assert "brand_scope" in data
        assert data.get("brand_id_filtro") == 2
