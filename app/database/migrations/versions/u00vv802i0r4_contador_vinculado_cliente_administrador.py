"""contador_vinculado_cliente_administrador_id em usuarios

Revision ID: u00vv802i0r4
Revises: t99uu791h9q3
Create Date: 2026-02-08

Contador só vê notas dos clientes do Cliente Administrador ao qual está vinculado.
"""
import sqlalchemy as sa
from alembic import op

revision = "u00vv802i0r4"
down_revision = "t99uu791h9q3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "usuarios",
        sa.Column(
            "contador_vinculado_cliente_administrador_id",
            sa.Integer(),
            nullable=True,
            comment="Se role=Contador: usuario_id do Cliente Administrador cujos clientes este contador pode ver",
        ),
    )
    op.create_foreign_key(
        "fk_usuarios_contador_vinculado_ca",
        "usuarios",
        "usuarios",
        ["contador_vinculado_cliente_administrador_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "idx_usuarios_contador_vinculado_ca",
        "usuarios",
        ["contador_vinculado_cliente_administrador_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_usuarios_contador_vinculado_ca", table_name="usuarios")
    op.drop_constraint("fk_usuarios_contador_vinculado_ca", "usuarios", type_="foreignkey")
    op.drop_column("usuarios", "contador_vinculado_cliente_administrador_id")
