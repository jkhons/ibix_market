"""Limpeza permissões legadas Certipeso + rename relatórios.

Revision ID: rb01_cleanup_permissoes_certipeso
Revises: or05_documento_impressao_templates
Create Date: 2026-07-16

1) Cria negocios.relatorios:visualizar e copia role_permissoes de
   certificacao:relatorios:visualizar.
2) Remove permissões mortas do Certipeso/ISO 17025 (lista explícita de nome).
3) Remove chaves órfãs em configuracoes ligadas a certificados de calibração.
"""
from alembic import op
from sqlalchemy import text

revision = "rb01_cleanup_permissoes_certipeso"
down_revision = "or05_documento_impressao_templates"
branch_labels = None
depends_on = None

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

CONFIG_KEYS = (
    "certificados.proximo_numero",
    "iso_17025_certificados_apenas_processo",
    "notificacoes.certificado_vencendo",
)


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Nova permissão
    exists = conn.execute(
        text("SELECT id FROM permissoes WHERE nome = :n"), {"n": NEW_PERM}
    ).fetchone()
    if not exists:
        conn.execute(
            text(
                """
                INSERT INTO permissoes (nome, descricao, modulo, acao, ativo, created_at, updated_at)
                VALUES (
                    :nome,
                    'Visualizar e gerar relatórios do PDV (E-Relatórios)',
                    'negocios',
                    'visualizar',
                    true,
                    NOW(),
                    NOW()
                )
                """
            ),
            {"nome": NEW_PERM},
        )

    new_row = conn.execute(
        text("SELECT id FROM permissoes WHERE nome = :n"), {"n": NEW_PERM}
    ).fetchone()
    if not new_row:
        raise RuntimeError(f"Falha ao criar permissão {NEW_PERM}")
    new_id = new_row[0]

    # 2. Copiar vínculos da permissão antiga (e garantir Superadmin/Admin/CA)
    old_row = conn.execute(
        text("SELECT id FROM permissoes WHERE nome = :n"), {"n": OLD_PERM}
    ).fetchone()
    if old_row:
        conn.execute(
            text(
                """
                INSERT INTO role_permissoes (role_id, permissao_id, created_at, updated_at)
                SELECT rp.role_id, :new_id, NOW(), NOW()
                FROM role_permissoes rp
                WHERE rp.permissao_id = :old_id
                  AND NOT EXISTS (
                      SELECT 1 FROM role_permissoes x
                      WHERE x.role_id = rp.role_id AND x.permissao_id = :new_id
                  )
                """
            ),
            {"new_id": new_id, "old_id": old_row[0]},
        )

    for role_nome in ("Superadministrador", "Administrador", "Cliente Administrador"):
        role_row = conn.execute(
            text("SELECT id FROM roles WHERE nome = :n"), {"n": role_nome}
        ).fetchone()
        if not role_row:
            continue
        already = conn.execute(
            text(
                "SELECT 1 FROM role_permissoes WHERE role_id = :rid AND permissao_id = :pid"
            ),
            {"rid": role_row[0], "pid": new_id},
        ).fetchone()
        if not already:
            conn.execute(
                text(
                    """
                    INSERT INTO role_permissoes (role_id, permissao_id, created_at, updated_at)
                    VALUES (:role_id, :permissao_id, NOW(), NOW())
                    """
                ),
                {"role_id": role_row[0], "permissao_id": new_id},
            )

    # 3. Remover permissões mortas (lista explícita de nome)
    for nome in DEAD_PERMS:
        perm = conn.execute(
            text("SELECT id FROM permissoes WHERE nome = :n"), {"n": nome}
        ).fetchone()
        if not perm:
            continue
        conn.execute(
            text("DELETE FROM role_permissoes WHERE permissao_id = :pid"),
            {"pid": perm[0]},
        )
        conn.execute(text("DELETE FROM permissoes WHERE id = :pid"), {"pid": perm[0]})

    # 4. Chaves órfãs de configuração + e-mail função certificados
    for chave in CONFIG_KEYS:
        conn.execute(text("DELETE FROM configuracoes WHERE chave = :c"), {"c": chave})
    conn.execute(
        text("DELETE FROM configuracoes WHERE chave LIKE 'email_funcao_certificados_%'")
    )


def downgrade() -> None:
    """Best-effort: recria a permissão antiga de relatórios e remove a nova."""
    conn = op.get_bind()

    new_row = conn.execute(
        text("SELECT id FROM permissoes WHERE nome = :n"), {"n": NEW_PERM}
    ).fetchone()
    if not new_row:
        return

    exists_old = conn.execute(
        text("SELECT id FROM permissoes WHERE nome = :n"), {"n": OLD_PERM}
    ).fetchone()
    if not exists_old:
        conn.execute(
            text(
                """
                INSERT INTO permissoes (nome, descricao, modulo, acao, ativo, created_at, updated_at)
                VALUES (
                    :nome,
                    'Visualizar e gerar relatórios de certificação',
                    'certificacao',
                    'relatorios:visualizar',
                    true,
                    NOW(),
                    NOW()
                )
                """
            ),
            {"nome": OLD_PERM},
        )
    old_row = conn.execute(
        text("SELECT id FROM permissoes WHERE nome = :n"), {"n": OLD_PERM}
    ).fetchone()
    if old_row:
        conn.execute(
            text(
                """
                INSERT INTO role_permissoes (role_id, permissao_id, created_at, updated_at)
                SELECT rp.role_id, :old_id, NOW(), NOW()
                FROM role_permissoes rp
                WHERE rp.permissao_id = :new_id
                  AND NOT EXISTS (
                      SELECT 1 FROM role_permissoes x
                      WHERE x.role_id = rp.role_id AND x.permissao_id = :old_id
                  )
                """
            ),
            {"old_id": old_row[0], "new_id": new_row[0]},
        )

    conn.execute(
        text("DELETE FROM role_permissoes WHERE permissao_id = :pid"),
        {"pid": new_row[0]},
    )
    conn.execute(text("DELETE FROM permissoes WHERE id = :pid"), {"pid": new_row[0]})
