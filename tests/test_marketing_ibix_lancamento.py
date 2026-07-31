"""Testes — Marketing Ibix Lançamento (schemas + serviço + brand gate)."""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.schemas.marketing_ibix_lancamento import MarketingPostPatch
from app.services.marketing_ibix_lancamento_service import (
    _proximo_pendente,
    build_campanha_resumo,
    patch_post,
)


def test_marketing_post_patch_enum_invalido_422():
    with pytest.raises(ValidationError):
        MarketingPostPatch(status_copy="invalido")  # type: ignore[arg-type]


def test_marketing_post_patch_aceita_enums_validos():
    body = MarketingPostPatch(
        status_copy="aprovado",
        status_producao="pronto",
        status_publicacao="ambos",
        telas_ok=True,
    )
    assert body.status_copy == "aprovado"
    assert body.status_publicacao == "ambos"


def test_proximo_pendente_escolhe_menor_data_nao_ambos():
    p1 = MagicMock(data_prevista=date(2026, 7, 27), status_publicacao="ambos", numero=1)
    p2 = MagicMock(data_prevista=date(2026, 7, 29), status_publicacao="pendente", numero=2)
    p3 = MagicMock(data_prevista=date(2026, 7, 31), status_publicacao="ig", numero=3)
    got = _proximo_pendente([p1, p2, p3], date(2026, 7, 28))
    assert got is p2


def test_build_campanha_resumo_404_sem_campanha():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    with pytest.raises(HTTPException) as exc:
        build_campanha_resumo(db)
    assert exc.value.status_code == 404


def test_patch_post_define_publicado_em():
    campanha = MagicMock(id=1, slug="ibix_market_40d")
    post = MagicMock(spec=["campanha_id", "numero", "status_publicacao", "publicado_em", "updated_by_user_id", "updated_at"])
    post.campanha_id = 1
    post.numero = 2
    post.status_publicacao = "pendente"
    post.publicado_em = None
    post.updated_by_user_id = None

    q_camp = MagicMock()
    q_camp.filter.return_value.first.return_value = campanha
    q_post = MagicMock()
    q_post.filter.return_value.first.return_value = post

    def query_side_effect(model):
        name = getattr(model, "__name__", "")
        if name == "MarketingCampanha":
            return q_camp
        return q_post

    db = MagicMock()
    db.query.side_effect = query_side_effect

    body = MarketingPostPatch(status_publicacao="ambos")
    result = patch_post(db, 2, body, user_id=99)

    assert result.status_publicacao == "ambos"
    assert result.publicado_em is not None
    assert result.updated_by_user_id == 99
    db.commit.assert_called_once()
