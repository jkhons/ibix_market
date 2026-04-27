"""add certificado_snapshot (XML oficial imutável)

Revision ID: x23yy125l0u7
Revises: w22xx014k9t6
Create Date: 2026-02-08

certificadoxml.md: snapshot oficial do certificado em XML; imutável após emissão.
"""
import sqlalchemy as sa
from alembic import op

revision = "x23yy125l0u7"
down_revision = "w22xx014k9t6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "certificado_snapshot",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("certificado_id", sa.Integer(), nullable=False),
        sa.Column("schema_version", sa.String(20), nullable=False, server_default="1.0.0"),
        sa.Column("template_version_id", sa.Integer(), nullable=True),
        sa.Column("versao", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("xml_content", sa.Text(), nullable=False),
        sa.Column("hash_sha256", sa.String(64), nullable=False),
        sa.Column("emitido_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("emitido_por_usuario_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="ATIVO"),
        sa.Column("substitui_snapshot_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["certificado_id"], ["certificados.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["emitido_por_usuario_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["substitui_snapshot_id"], ["certificado_snapshot.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        comment="Snapshot XML oficial do certificado emitido (imutável)",
    )
    op.create_index("ix_certificado_snapshot_id", "certificado_snapshot", ["id"])
    op.create_index("idx_certificado_snapshot_certificado_id", "certificado_snapshot", ["certificado_id"])
    op.create_index("idx_certificado_snapshot_status", "certificado_snapshot", ["status"])
    op.create_index("idx_certificado_snapshot_hash", "certificado_snapshot", ["hash_sha256"])
    op.create_index("ix_certificado_snapshot_substitui", "certificado_snapshot", ["substitui_snapshot_id"])


def downgrade() -> None:
    op.drop_index("ix_certificado_snapshot_substitui", "certificado_snapshot")
    op.drop_index("idx_certificado_snapshot_hash", "certificado_snapshot")
    op.drop_index("idx_certificado_snapshot_status", "certificado_snapshot")
    op.drop_index("idx_certificado_snapshot_certificado_id", "certificado_snapshot")
    op.drop_index("ix_certificado_snapshot_id", "certificado_snapshot")
    op.drop_table("certificado_snapshot")
