"""cliente_administrador_tecnicos (Saas.md Fase 6.2 - Minha equipe)

Revision ID: f55hh357c2i6
Revises: e44gg246b1h5
Create Date: 2026-02-06

"""
import sqlalchemy as sa
from alembic import op

revision = "f55hh357c2i6"
down_revision = "e44gg246b1h5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cliente_administrador_tecnicos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("usuario_id_cliente_admin", sa.Integer(), nullable=False),
        sa.Column("usuario_id_tecnico", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["usuario_id_cliente_admin"], ["usuarios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["usuario_id_tecnico"], ["usuarios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("usuario_id_cliente_admin", "usuario_id_tecnico", name="uq_cliente_admin_tecnico"),
    )
    op.create_index("idx_cliente_admin_tecnicos_admin_id", "cliente_administrador_tecnicos", ["usuario_id_cliente_admin"])
    op.create_index("idx_cliente_admin_tecnicos_tecnico_id", "cliente_administrador_tecnicos", ["usuario_id_tecnico"])


def downgrade() -> None:
    op.drop_table("cliente_administrador_tecnicos")
