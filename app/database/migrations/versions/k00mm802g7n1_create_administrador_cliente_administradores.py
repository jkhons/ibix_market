"""administrador_cliente_administradores - Cliente Administrador vinculado a um Administrador (RBAC)

Revision ID: k00mm802g7n1
Revises: j99ll791f6m0
Create Date: 2026-02-06

"""
import sqlalchemy as sa
from alembic import op

revision = "k00mm802g7n1"
down_revision = "j99ll791f6m0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "administrador_cliente_administradores",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("usuario_id_administrador", sa.Integer(), nullable=False),
        sa.Column("usuario_id_cliente_administrador", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["usuario_id_administrador"], ["usuarios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["usuario_id_cliente_administrador"], ["usuarios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("usuario_id_cliente_administrador", name="uq_administrador_cliente_administradores_cliente_admin"),
    )
    op.create_index("idx_admin_cliente_admin_administrador", "administrador_cliente_administradores", ["usuario_id_administrador"])
    op.create_index("idx_admin_cliente_admin_cliente_admin", "administrador_cliente_administradores", ["usuario_id_cliente_administrador"])


def downgrade() -> None:
    op.drop_table("administrador_cliente_administradores")
