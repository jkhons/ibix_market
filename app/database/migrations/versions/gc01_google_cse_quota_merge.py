"""Google Custom Search: cota por tenant, log de uso, merge heads.

Revision ID: gc01_google_cse_quota
Revises: em02_gateway_plataforma, sc01_social_cf
Create Date: 2026-03-25

"""
import sqlalchemy as sa
from alembic import op

revision = "gc01_google_cse_quota"
down_revision = ("em02_gateway_plataforma", "sc01_social_cf")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column(
            "google_cse_limite_diario",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Máximo de buscas Google CSE (imagem) por dia; 0 = bloqueado",
        ),
    )
    op.add_column(
        "tenants",
        sa.Column(
            "google_cse_uso_dia",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Buscas já consumidas no dia de referência",
        ),
    )
    op.add_column(
        "tenants",
        sa.Column(
            "google_cse_uso_data",
            sa.Date(),
            nullable=True,
            comment="Data (servidor) do contador google_cse_uso_dia",
        ),
    )

    op.create_table(
        "google_cse_uso_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.String(32), nullable=False, server_default="search"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_google_cse_uso_log_tenant_id", "google_cse_uso_log", ["tenant_id"])
    op.create_index("ix_google_cse_uso_log_created_at", "google_cse_uso_log", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_google_cse_uso_log_created_at", table_name="google_cse_uso_log")
    op.drop_index("ix_google_cse_uso_log_tenant_id", table_name="google_cse_uso_log")
    op.drop_table("google_cse_uso_log")
    op.drop_column("tenants", "google_cse_uso_data")
    op.drop_column("tenants", "google_cse_uso_dia")
    op.drop_column("tenants", "google_cse_limite_diario")
