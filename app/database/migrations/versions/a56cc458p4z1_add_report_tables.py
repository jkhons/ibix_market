"""add report_definitions, report_jobs, report_artifacts (módulo Relatórios)

Revision ID: a56cc458p4z1
Revises: z45aa347n2w9
Create Date: 2026-02-08

E-Relatórios: tabelas para catálogo de relatórios e jobs assíncronos.
Escopo por cliente_id (ClienteScope).
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "a56cc458p4z1"
down_revision = "z45aa347n2w9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Catálogo de relatórios (pré-criados, opcional)
    op.create_table(
        "report_definitions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("report_key", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("output_formats", sa.ARRAY(sa.Text()), nullable=False, server_default=sa.text("ARRAY['pdf']::text[]")),
        sa.Column("required_module", sa.Text(), nullable=True),
        sa.Column("required_perm", sa.Text(), nullable=True),
        sa.Column("param_schema", JSONB, nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("report_key", name="uq_report_definitions_report_key"),
        comment="Catálogo de relatórios disponíveis (registry)",
    )
    op.create_index("ix_report_definitions_report_key", "report_definitions", ["report_key"])

    # Jobs de geração (sob demanda)
    op.create_table(
        "report_jobs",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("cliente_id", sa.Integer(), nullable=True, comment="Escopo ClienteScope; nullable para jobs sem filtro de cliente"),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("report_key", sa.Text(), nullable=False),
        sa.Column("output_format", sa.Text(), nullable=False),
        sa.Column("params_json", JSONB, nullable=False, server_default="{}"),
        sa.Column("status", sa.Text(), nullable=False, server_default="PENDING"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["usuarios.id"], ondelete="CASCADE"),
        comment="Jobs de geração de relatórios (fila assíncrona)",
    )
    op.create_index("ix_report_jobs_cliente_created", "report_jobs", ["cliente_id", "created_at"])
    op.create_index("ix_report_jobs_cliente_status", "report_jobs", ["cliente_id", "status"])
    op.create_index("ix_report_jobs_user_id", "report_jobs", ["user_id"])

    # Artefatos gerados
    op.create_table(
        "report_artifacts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("job_id", UUID(as_uuid=True), nullable=False),
        sa.Column("cliente_id", sa.Integer(), nullable=True),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.Text(), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("checksum_sha256", sa.Text(), nullable=True),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["job_id"], ["report_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"], ondelete="SET NULL"),
        comment="Arquivos gerados por report_jobs",
    )
    op.create_index("ix_report_artifacts_cliente_created", "report_artifacts", ["cliente_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_report_artifacts_cliente_created", table_name="report_artifacts")
    op.drop_table("report_artifacts")
    op.drop_index("ix_report_jobs_user_id", table_name="report_jobs")
    op.drop_index("ix_report_jobs_cliente_status", table_name="report_jobs")
    op.drop_index("ix_report_jobs_cliente_created", table_name="report_jobs")
    op.drop_table("report_jobs")
    op.drop_index("ix_report_definitions_report_key", table_name="report_definitions")
    op.drop_table("report_definitions")
