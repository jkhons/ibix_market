"""Entregador: CNH, documento veículo + aprovação; pagamento ao entregador por corrida; permissões platform.

Merge heads ca01bb01d0p1 + nt01_notifications (nt01 inclui a linha mt01_marketplace_taxa_regras).

Revision ID: en01_entregador_docs_pagamento_merge
Revises: ca01bb01d0p1, nt01_notifications
Create Date: 2026-04-30

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision = "en01_entregador_docs_pagamento_merge"
down_revision = ("ca01bb01d0p1", "nt01_notifications")
branch_labels = None
depends_on = None

PERMISSOES = [
    ("platform.entregadores:listar", "platform_entregadores", "listar", "Listar entregadores (Superadmin)"),
    ("platform.entregadores:gerenciar", "platform_entregadores", "gerenciar", "Aprovar/bloquear perfil entregador"),
    ("platform.entregadores:documentos", "platform_entregadores", "documentos", "Aprovar documentos CNH/veículo"),
    ("platform.entregadores:pagamentos", "platform_entregadores", "pagamentos", "Alterar status pagamento corrida"),
]


def upgrade() -> None:
    conn = op.get_bind()

    op.add_column("entregadores", sa.Column("cnh_arquivo_path", sa.String(500), nullable=True))
    op.add_column(
        "entregadores",
        sa.Column("cadastro_enviado_em", sa.DateTime(timezone=True), nullable=True),
    )

    op.add_column("entregador_veiculos", sa.Column("documento_veiculo_path", sa.String(500), nullable=True))
    op.add_column(
        "entregador_veiculos",
        sa.Column("documento_aprovado", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "entregador_veiculos",
        sa.Column("documento_aprovado_em", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "entregador_veiculos",
        sa.Column("documento_aprovado_por_usuario_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_ev_documento_aprovado_por_usuario",
        "entregador_veiculos",
        "usuarios",
        ["documento_aprovado_por_usuario_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Veículos já cadastrados: considerar documento aprovado para não bloquear operação legada
    conn.execute(text("UPDATE entregador_veiculos SET documento_aprovado = true"))

    op.add_column(
        "entregas_marketplace",
        sa.Column(
            "status_pagamento_entregador",
            sa.String(30),
            nullable=False,
            server_default="pendente",
        ),
    )
    op.add_column("entregas_marketplace", sa.Column("pagamento_entregador_obs", sa.Text(), nullable=True))
    op.add_column(
        "entregas_marketplace",
        sa.Column("pagamento_entregador_atualizado_em", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "entregas_marketplace",
        sa.Column("pagamento_entregador_atualizado_por_usuario_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_entrega_pagamento_atualizado_por",
        "entregas_marketplace",
        "usuarios",
        ["pagamento_entregador_atualizado_por_usuario_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        "ck_entregas_status_pagamento_entregador",
        "entregas_marketplace",
        "status_pagamento_entregador IN ('pendente', 'liberado', 'pago')",
    )

    # Seed de teste sem veículos: um veículo legado aprovado
    conn.execute(
        text(
            """
            INSERT INTO entregador_veiculos (
                entregador_id, tipo_veiculo, placa, ativo, documento_aprovado,
                created_at, updated_at
            )
            SELECT e.id, 'moto', 'LEGADO01', true, true, NOW(), NOW()
            FROM entregadores e
            WHERE e.email = 'carlos.moto@teste.com'
              AND NOT EXISTS (SELECT 1 FROM entregador_veiculos v WHERE v.entregador_id = e.id)
            """
        )
    )

    for nome, modulo, acao, descricao in PERMISSOES:
        r = conn.execute(text("SELECT 1 FROM permissoes WHERE nome = :n"), {"n": nome}).fetchone()
        if not r:
            conn.execute(
                text(
                    "INSERT INTO permissoes (nome, modulo, acao, descricao, ativo, created_at, updated_at) "
                    "VALUES (:nome, :modulo, :acao, :descricao, true, NOW(), NOW())"
                ),
                {"nome": nome, "modulo": modulo, "acao": acao, "descricao": descricao},
            )

    role_row = conn.execute(text("SELECT id FROM roles WHERE nome = 'Superadministrador'")).fetchone()
    if role_row:
        role_id = role_row[0]
        for nome, _, _, _ in PERMISSOES:
            perm_row = conn.execute(text("SELECT id FROM permissoes WHERE nome = :n"), {"n": nome}).fetchone()
            if not perm_row:
                continue
            pid = perm_row[0]
            ex = conn.execute(
                text("SELECT 1 FROM role_permissoes WHERE role_id = :r AND permissao_id = :p"),
                {"r": role_id, "p": pid},
            ).fetchone()
            if not ex:
                conn.execute(
                    text(
                        "INSERT INTO role_permissoes (role_id, permissao_id, created_at, updated_at) "
                        "VALUES (:r, :p, NOW(), NOW())"
                    ),
                    {"r": role_id, "p": pid},
                )


def downgrade() -> None:
    conn = op.get_bind()

    role_row = conn.execute(text("SELECT id FROM roles WHERE nome = 'Superadministrador'")).fetchone()
    if role_row:
        for nome, _, _, _ in PERMISSOES:
            perm_row = conn.execute(text("SELECT id FROM permissoes WHERE nome = :n"), {"n": nome}).fetchone()
            if perm_row:
                conn.execute(
                    text("DELETE FROM role_permissoes WHERE role_id = :r AND permissao_id = :p"),
                    {"r": role_row[0], "p": perm_row[0]},
                )

    for nome, _, _, _ in PERMISSOES:
        conn.execute(text("DELETE FROM permissoes WHERE nome = :n"), {"n": nome})

    op.drop_constraint("ck_entregas_status_pagamento_entregador", "entregas_marketplace", type_="check")
    op.drop_constraint("fk_entrega_pagamento_atualizado_por", "entregas_marketplace", type_="foreignkey")
    op.drop_column("entregas_marketplace", "pagamento_entregador_atualizado_por_usuario_id")
    op.drop_column("entregas_marketplace", "pagamento_entregador_atualizado_em")
    op.drop_column("entregas_marketplace", "pagamento_entregador_obs")
    op.drop_column("entregas_marketplace", "status_pagamento_entregador")

    op.drop_constraint("fk_ev_documento_aprovado_por_usuario", "entregador_veiculos", type_="foreignkey")
    op.drop_column("entregador_veiculos", "documento_aprovado_por_usuario_id")
    op.drop_column("entregador_veiculos", "documento_aprovado_em")
    op.drop_column("entregador_veiculos", "documento_aprovado")
    op.drop_column("entregador_veiculos", "documento_veiculo_path")

    op.drop_column("entregadores", "cadastro_enviado_em")
    op.drop_column("entregadores", "cnh_arquivo_path")
