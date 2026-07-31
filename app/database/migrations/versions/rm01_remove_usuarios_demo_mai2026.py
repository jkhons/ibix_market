"""Remove usuários de demonstração (#16, #18, #19, #21, #22) com validação de e-mail.

Revision ID: rm01_remove_usuarios_demo_mai2026
Revises: pl01_platform_novo_ca_notificacoes
Create Date: 2026-05-13

Exclui apenas se cada id existir e o e-mail (case-insensitive) coincidir com o esperado.
Trata FKs que bloqueiam exclusão: vendas (venda_itens), área do cliente (downloads),
notificações lidas, assinaturas digitais, tokens de reset, contador vinculado,
emitido_por em NFS-e/cupom (reatribui a outro Superadmin/Admin), NF-e com emitido_por nullable.

Downgrade não restaura usuários nem dados apagados.
"""
from __future__ import annotations

from alembic import op
from sqlalchemy import inspect, text

revision = "rm01_remove_usuarios_demo_mai2026"
down_revision = "pl01_platform_novo_ca_notificacoes"
branch_labels = None
depends_on = None

# (id, email esperado após normalização lower + trim)
_USUARIOS_ALVO: tuple[tuple[int, str], ...] = (
    (16, "cf01@cf01.com.br"),
    (18, "ca02@ca02.com.br"),
    (19, "adm_rep01@rep.com"),
    (21, "ca05@ca05.com.br"),
    (22, "ca06@ca06.com.br"),
)

_IDS_SQL = "16, 18, 19, 21, 22"


def _validar_usuarios(conn) -> None:
    esperado = {uid: em for uid, em in _USUARIOS_ALVO}
    rows = conn.execute(
        text(f"SELECT id, lower(trim(email)) AS em FROM usuarios WHERE id IN ({_IDS_SQL})")
    ).fetchall()
    encontrados = {int(r[0]): str(r[1]) for r in rows}
    for uid, em in esperado.items():
        if uid not in encontrados:
            raise RuntimeError(
                f"Migration rm01: usuário id={uid} não encontrado; "
                "nada foi alterado. Ajuste o banco ou remova este revision do chain."
            )
        if encontrados[uid] != em:
            raise RuntimeError(
                f"Migration rm01: id={uid} tem email '{encontrados[uid]}', esperado '{em}'. "
                "Abortado para evitar exclusão indevida."
            )


def _substituto_emitido_por(conn) -> int:
    row = conn.execute(
        text(
            f"""
            SELECT u.id
            FROM usuarios u
            LEFT JOIN roles r ON r.id = u.role_id
            WHERE u.id NOT IN ({_IDS_SQL})
            ORDER BY
                CASE COALESCE(r.nome, '')
                    WHEN 'Superadministrador' THEN 0
                    WHEN 'Administrador' THEN 1
                    ELSE 2
                END,
                u.id
            LIMIT 1
            """
        )
    ).fetchone()
    if not row:
        raise RuntimeError(
            "Migration rm01: não há outro usuário no banco para assumir emitido_por em "
            "NFS-e/cupom fiscal; exclusão abortada."
        )
    return int(row[0])


def upgrade() -> None:
    conn = op.get_bind()
    _validar_usuarios(conn)
    rep_id = _substituto_emitido_por(conn)

    # Self-FK contador → CA
    conn.execute(
        text(
            f"UPDATE usuarios SET contador_vinculado_cliente_administrador_id = NULL "
            f"WHERE contador_vinculado_cliente_administrador_id IN ({_IDS_SQL})"
        )
    )

    conn.execute(
        text(f"UPDATE notas_fiscais SET emitido_por_id = NULL WHERE emitido_por_id IN ({_IDS_SQL})")
    )
    conn.execute(
        text(
            f"UPDATE notas_servico SET emitido_por_id = :rep WHERE emitido_por_id IN ({_IDS_SQL})"
        ),
        {"rep": rep_id},
    )
    conn.execute(
        text(
            f"UPDATE cupons_fiscais SET emitido_por_id = :rep WHERE emitido_por_id IN ({_IDS_SQL})"
        ),
        {"rep": rep_id},
    )

    insp = inspect(conn)
    tables = set(insp.get_table_names())

    if "password_reset_tokens" in tables:
        conn.execute(
            text(
                f"DELETE FROM password_reset_tokens WHERE tipo = 'pdv' "
                f"AND entidade_id IN ({_IDS_SQL})"
            )
        )

    if "downloads_cliente" in tables and "areas_cliente" in tables:
        conn.execute(
            text(
                f"DELETE FROM downloads_cliente WHERE area_cliente_id IN ("
                f"SELECT id FROM areas_cliente WHERE usuario_id IN ({_IDS_SQL}))"
            )
        )

    if "areas_cliente" in tables:
        conn.execute(text(f"DELETE FROM areas_cliente WHERE usuario_id IN ({_IDS_SQL})"))

    if "assinaturas" in tables:
        conn.execute(text(f"DELETE FROM assinaturas WHERE usuario_id IN ({_IDS_SQL})"))

    if "notificacoes_lidas_usuario" in tables:
        conn.execute(
            text(f"DELETE FROM notificacoes_lidas_usuario WHERE usuario_id IN ({_IDS_SQL})")
        )

    if "venda_itens" in tables and "vendas" in tables:
        conn.execute(
            text(
                f"DELETE FROM venda_itens WHERE venda_id IN ("
                f"SELECT id FROM vendas WHERE vendedor_id IN ({_IDS_SQL}))"
            )
        )

    if "vendas" in tables:
        conn.execute(text(f"DELETE FROM vendas WHERE vendedor_id IN ({_IDS_SQL})"))

    conn.execute(text(f"DELETE FROM usuarios WHERE id IN ({_IDS_SQL})"))


def downgrade() -> None:
    pass
