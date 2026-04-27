"""add tenant_id to audit_log (Fase 1 - Blindagem SaaS)

Revision ID: mm22oo358u8
Revises: ll11nn247c7
Create Date: 2026-02-20

Plano consultoria PDV Etapa 1.2: coluna tenant_id (nullable para ações SA) e índice.
"""
import sqlalchemy as sa
from alembic import op

revision = "mm22oo358u8"
down_revision = "ll11nn247c7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "audit_log",
        sa.Column("tenant_id", sa.Integer(), nullable=True, comment="Tenant SaaS (nullable para SuperAdmin)"),
    )
    op.create_index("ix_audit_log_tenant_id", "audit_log", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_log_tenant_id", "audit_log")
    op.drop_column("audit_log", "tenant_id")
