"""add audit_log (append-only)

Revision ID: v11ww903j8s5
Revises: u00vv802i0r4
Create Date: 2026-02-08

E4.4 confirmação de impl.: audit_log append-only (quem/onde/quando/o quê).
"""
import sqlalchemy as sa
from alembic import op

revision = "v11ww903j8s5"
down_revision = "u00vv802i0r4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("recurso_tipo", sa.String(100), nullable=True),
        sa.Column("recurso_id", sa.Integer(), nullable=True),
        sa.Column("acao", sa.String(100), nullable=False),
        sa.Column("ip", sa.String(45), nullable=True),
        sa.Column("request_id", sa.String(64), nullable=True),
        sa.Column("detalhes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        comment="Audit log append-only (quem/onde/quando/o quê)",
    )
    op.create_index("ix_audit_log_id", "audit_log", ["id"])
    op.create_index("ix_audit_log_user_id", "audit_log", ["user_id"])
    op.create_index("ix_audit_log_recurso_tipo", "audit_log", ["recurso_tipo"])
    op.create_index("ix_audit_log_recurso_id", "audit_log", ["recurso_id"])
    op.create_index("ix_audit_log_acao", "audit_log", ["acao"])
    op.create_index("ix_audit_log_request_id", "audit_log", ["request_id"])
    op.create_index("ix_audit_log_created_at", "audit_log", ["created_at"])
    op.create_index("ix_audit_log_user_created", "audit_log", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_log_user_created", "audit_log")
    op.drop_index("ix_audit_log_created_at", "audit_log")
    op.drop_index("ix_audit_log_request_id", "audit_log")
    op.drop_index("ix_audit_log_acao", "audit_log")
    op.drop_index("ix_audit_log_recurso_id", "audit_log")
    op.drop_index("ix_audit_log_recurso_tipo", "audit_log")
    op.drop_index("ix_audit_log_user_id", "audit_log")
    op.drop_index("ix_audit_log_id", "audit_log")
    op.drop_table("audit_log")
