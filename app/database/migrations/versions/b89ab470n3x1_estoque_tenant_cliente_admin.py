"""Estoque: produto pertence ao CA (tenant). usuario_id_cliente_admin + UNIQUE(ca, codigo).

Revision ID: b89ab470n3x1
Revises: e99hh279s8q6
Create Date: 2026-02-09

- Adiciona usuario_id_cliente_admin (tenant).
- Backfill: preenche a partir de cliente_administrador_clientes onde estoque.cliente_id existe.
- Remove unicidade global de codigo; cria UNIQUE(usuario_id_cliente_admin, codigo).
- cliente_id permanece opcional (associação/uso preferencial, não dono).
"""
import sqlalchemy as sa
from alembic import op

revision = "b89ab470n3x1"
down_revision = "e99hh279s8q6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) Adicionar coluna tenant (nullable para backfill)
    op.add_column(
        "estoque",
        sa.Column(
            "usuario_id_cliente_admin",
            sa.Integer(),
            nullable=True,
            comment="Usuario_id do Cliente Administrador (tenant). NOT NULL após backfill.",
        ),
    )
    op.create_foreign_key(
        "fk_estoque_usuario_id_cliente_admin",
        "estoque",
        "usuarios",
        ["usuario_id_cliente_admin"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_estoque_usuario_id_cliente_admin",
        "estoque",
        ["usuario_id_cliente_admin"],
    )

    # 2) Backfill: onde estoque.cliente_id existe, definir CA dono desse cliente
    conn = op.get_bind()
    conn.execute(
        sa.text("""
            UPDATE estoque e
            SET usuario_id_cliente_admin = (
                SELECT cac.usuario_id
                FROM cliente_administrador_clientes cac
                WHERE cac.cliente_id = e.cliente_id
                LIMIT 1
            )
            WHERE e.cliente_id IS NOT NULL
              AND e.usuario_id_cliente_admin IS NULL
        """)
    )
    # Logar registros sem CA (cliente_id NULL ou sem vínculo em cliente_administrador_clientes)
    result = conn.execute(sa.text("SELECT id, codigo, cliente_id FROM estoque WHERE usuario_id_cliente_admin IS NULL"))
    rows = result.fetchall()
    if rows:
        import logging
        log = logging.getLogger("alembic.runtime.migration")
        log.warning(
            "Estoque: %d registro(s) sem usuario_id_cliente_admin (revisão manual). ids=%s",
            len(rows),
            [r[0] for r in rows],
        )

    # 3) Remover unicidade global de codigo
    insp = sa.inspect(op.get_bind())
    for uc in insp.get_unique_constraints("estoque"):
        if "codigo" in uc["column_names"] and len(uc["column_names"]) == 1:
            op.drop_constraint(uc["name"], "estoque", type_="unique")
            break

    # 4) Unicidade por CA: UNIQUE(usuario_id_cliente_admin, codigo)
    op.create_unique_constraint(
        "uq_estoque_cliente_admin_codigo",
        "estoque",
        ["usuario_id_cliente_admin", "codigo"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_estoque_cliente_admin_codigo", "estoque", type_="unique")
    op.create_unique_constraint("estoque_codigo_key", "estoque", ["codigo"])
    op.drop_index("ix_estoque_usuario_id_cliente_admin", table_name="estoque")
    op.drop_constraint("fk_estoque_usuario_id_cliente_admin", "estoque", type_="foreignkey")
    op.drop_column("estoque", "usuario_id_cliente_admin")
