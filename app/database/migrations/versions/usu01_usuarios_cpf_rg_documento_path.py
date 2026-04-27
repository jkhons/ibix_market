"""usuarios: cpf, rg, documento_path

Revision ID: usu01_usr_cpf
Revises: x44yy135p6z2
Create Date: 2026-03-02

Campos opcionais para cadastro de usuário: CPF, RG e caminho do documento/anexo.
"""
import sqlalchemy as sa
from alembic import op

revision = "usu01_usr_cpf"
down_revision = "x44yy135p6z2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "usuarios",
        sa.Column("cpf", sa.String(14), nullable=True, comment="CPF do usuário (opcional)"),
    )
    op.add_column(
        "usuarios",
        sa.Column("rg", sa.String(20), nullable=True, comment="RG do usuário (opcional)"),
    )
    op.add_column(
        "usuarios",
        sa.Column("documento_path", sa.String(500), nullable=True, comment="Caminho do documento/anexo do usuário (opcional)"),
    )
    op.create_index("ix_usuarios_cpf", "usuarios", ["cpf"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_usuarios_cpf", table_name="usuarios")
    op.drop_column("usuarios", "documento_path")
    op.drop_column("usuarios", "rg")
    op.drop_column("usuarios", "cpf")
