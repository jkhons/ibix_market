# PDV Ibix — validação limpeza permissões Certipeso (rb01)
"""Garante rename de relatórios, remoção de permissões mortas e artefatos órfãos."""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]

NEW_PERM = "negocios.relatorios:visualizar"
OLD_PERM = "certificacao:relatorios:visualizar"

DEAD_PERMS = (
    "auditoria:criar",
    "auditoria:editar",
    "auditoria:excluir",
    "auditoria:exportar",
    "auditoria:visualizar",
    "calibracao",
    "calibracao:criar",
    "calibracao:editar",
    "calibracao:excluir",
    "calibracao:visualizar",
    OLD_PERM,
    "certificados",
    "certificados:assinar",
    "certificados:criar",
    "certificados:editar",
    "certificados:excluir",
    "certificados:visualizar",
    "inspetores",
    "inspetores:criar",
    "inspetores:editar",
    "inspetores:excluir",
    "inspetores:visualizar",
    "peso",
    "peso:criar",
    "peso:editar",
    "peso:excluir",
    "peso:visualizar",
    "termobarohigrometro",
    "termobarohigrometro:criar",
    "termobarohigrometro:editar",
    "termobarohigrometro:excluir",
    "termobarohigrometro:visualizar",
)

ORPHAN_PATHS = (
    "app/static/js/certificados.js",
    "app/static/js/certificados-auxiliares.js",
    "app/static/js/certificados-auxiliares-cadastro.js",
    "app/static/js/certificados-auxiliares-unificado.js",
    "app/static/js/certificados-peso.js",
    "app/static/js/certificados-peso-cadastro.js",
    "app/static/js/inspetores-aprovadores.js",
    "app/static/js/inspetores-aprovadores-cadastro.js",
    "app/static/js/auditorias_internas.js",
    "app/static/js/etapa3_certificado.js",
    "app/static/js/pesos_ensaios_mobile.js",
    "app/static/js/aux-cadastros.js",
    "app/static/sw-calibracao.js",
    "app/static/css/calibracao-mobile.css",
    "app/templates/emails/certificado_pronto.html",
    "app/templates/emails/certificado_renovado.html",
    "app/templates/emails/vencimento_certificado.html",
)

EXPECTED_ROLES = ("Superadministrador", "Administrador", "Cliente Administrador")


def test_migration_file_exists():
    path = ROOT / "app/database/migrations/versions/rb01_cleanup_permissoes_certipeso.py"
    assert path.is_file()
    text_src = path.read_text(encoding="utf-8")
    assert NEW_PERM in text_src
    assert OLD_PERM in text_src
    assert "DEAD_PERMS" in text_src


def test_runtime_uses_new_relatorios_permission():
    relatorios = (ROOT / "app/api/v1/relatorios.py").read_text(encoding="utf-8")
    assert f'require_permission("{NEW_PERM}")' in relatorios
    assert OLD_PERM not in relatorios

    sidebar = (ROOT / "app/templates/components/sidebar.html").read_text(encoding="utf-8")
    assert NEW_PERM in sidebar
    assert OLD_PERM not in sidebar


def test_orphan_certipeso_assets_removed():
    for rel in ORPHAN_PATHS:
        assert not (ROOT / rel).exists(), f"Artefato órfão ainda presente: {rel}"


def test_email_funcoes_sem_certificados():
    from app.core.email_funcoes import get_codigos_funcoes_email

    codigos = get_codigos_funcoes_email()
    assert "certificados" not in codigos
    assert "nota_fiscal" in codigos


def test_send_certificate_ready_email_removido():
    import app.services.email_service as email_service

    assert not hasattr(email_service, "send_certificate_ready_email")


def test_mapa_rbac_documenta_nova_permissao():
    rbac = (ROOT / "MAPA_SISTEMA" / "MAPA_RBAC.md").read_text(encoding="utf-8")
    assert NEW_PERM in rbac
    assert "rb01_cleanup_permissoes_certipeso" in rbac


@pytest.mark.integration
def test_db_new_perm_and_dead_gone():
    from app.database.connection import open_db_session

    db = open_db_session(bypass_rls=True)
    try:
        new_id = db.execute(
            text("SELECT id FROM permissoes WHERE nome = :n"), {"n": NEW_PERM}
        ).scalar()
        assert new_id is not None, f"Permissão {NEW_PERM} deve existir no banco"

        old = db.execute(
            text("SELECT id FROM permissoes WHERE nome = :n"), {"n": OLD_PERM}
        ).scalar()
        assert old is None, f"Permissão legada {OLD_PERM} não deve existir"

        for nome in DEAD_PERMS:
            found = db.execute(
                text("SELECT id FROM permissoes WHERE nome = :n"), {"n": nome}
            ).scalar()
            assert found is None, f"Permissão morta ainda no banco: {nome}"

        roles = [
            row[0]
            for row in db.execute(
                text(
                    """
                    SELECT r.nome
                    FROM roles r
                    JOIN role_permissoes rp ON rp.role_id = r.id
                    JOIN permissoes p ON p.id = rp.permissao_id
                    WHERE p.nome = :n
                    ORDER BY r.nome
                    """
                ),
                {"n": NEW_PERM},
            ).fetchall()
        ]
        for role in EXPECTED_ROLES:
            assert role in roles, f"Role {role} deve ter {NEW_PERM}"

        cfg = db.execute(
            text(
                """
                SELECT COUNT(*) FROM configuracoes
                WHERE chave IN (
                    'certificados.proximo_numero',
                    'iso_17025_certificados_apenas_processo',
                    'notificacoes.certificado_vencendo'
                )
                OR chave LIKE 'email_funcao_certificados_%'
                """
            )
        ).scalar()
        assert cfg == 0, "Chaves órfãs de certificados ainda em configuracoes"
    finally:
        db.close()
