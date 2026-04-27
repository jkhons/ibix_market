"""Tabela ordem_servico_tipo e migração de ordem_servico.tipo (enum) para tipo_id (FK).

Revision ID: os01_tipo
Revises: nfe05_entrada_aj
Create Date: 2026-03-04

Cria ordem_servico_tipo (por tenant), adiciona ordem_servico.tipo_id, backfill e remove enum.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision = "os01_tipo"
down_revision = "nfe05_entrada_aj"
branch_labels = None
depends_on = None


def _resolve_tenant_id_from_cliente(conn, cliente_id):
    """Retorna tenant_id do CA que possui o cliente, ou None."""
    r = conn.execute(
        text(
            "SELECT u.tenant_id FROM cliente_administrador_clientes cac "
            "INNER JOIN usuarios u ON u.id = cac.usuario_id "
            "WHERE cac.cliente_id = :cid AND u.tenant_id IS NOT NULL LIMIT 1"
        ),
        {"cid": cliente_id},
    )
    row = r.fetchone()
    return row[0] if row and row[0] is not None else None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Criar tabela ordem_servico_tipo
    op.create_table(
        "ordem_servico_tipo",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(100), nullable=False),
        sa.Column("codigo", sa.String(50), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "nome", name="uq_ordem_servico_tipo_tenant_nome"),
        comment="Tipos de ordem de serviço por tenant (CA); nomes únicos por tenant",
    )
    op.create_index("ix_ordem_servico_tipo_tenant_id", "ordem_servico_tipo", ["tenant_id"], unique=False)
    op.create_index("ix_ordem_servico_tipo_tenant_ativo", "ordem_servico_tipo", ["tenant_id", "ativo"], unique=False)

    # 2. Adicionar coluna tipo_id em ordem_servico (nullable inicialmente)
    op.add_column("ordem_servico", sa.Column("tipo_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_ordem_servico_tipo_id",
        "ordem_servico",
        "ordem_servico_tipo",
        ["tipo_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_ordem_servico_tipo_id", "ordem_servico", ["tipo_id"], unique=False)

    # 3. Backfill: para cada ordem_servico, obter tenant_id, criar tipo se não existir, setar tipo_id
    rows = conn.execute(
        text("SELECT id, cliente_id, COALESCE(tipo, 'outro') AS tipo FROM ordem_servico")
    ).fetchall()
    for row in rows:
        os_id, cliente_id, tipo_val = row[0], row[1], row[2]
        tipo_val = tipo_val or "outro"
        tenant_id = _resolve_tenant_id_from_cliente(conn, cliente_id)
        if tenant_id is None:
            continue
        # Inserir tipo se não existir (por tenant_id e nome)
        existing = conn.execute(
            text(
                "SELECT id FROM ordem_servico_tipo WHERE tenant_id = :tid AND nome = :nome LIMIT 1"
            ),
            {"tid": tenant_id, "nome": tipo_val},
        ).fetchone()
        if existing:
            tipo_id = existing[0]
        else:
            conn.execute(
                text(
                    "INSERT INTO ordem_servico_tipo (tenant_id, nome, codigo, ativo, created_at, updated_at) "
                    "VALUES (:tid, :nome, :codigo, true, NOW(), NOW())"
                ),
                {"tid": tenant_id, "nome": tipo_val, "codigo": tipo_val},
            )
            r = conn.execute(text("SELECT LASTVAL()")).fetchone()
            tipo_id = r[0] if r else None
            if tipo_id is None:
                r2 = conn.execute(
                    text("SELECT id FROM ordem_servico_tipo WHERE tenant_id = :tid AND nome = :nome ORDER BY id DESC LIMIT 1"),
                    {"tid": tenant_id, "nome": tipo_val},
                ).fetchone()
                tipo_id = r2[0] if r2 else None
        if tipo_id is not None:
            conn.execute(
                text("UPDATE ordem_servico SET tipo_id = :tid WHERE id = :osid"),
                {"tid": tipo_id, "osid": os_id},
            )

    # Ordens sem tenant (cliente sem CA): criar tipo em um tenant padrão ou pular
    # Se ainda houver ordem_servico com tipo_id NULL, tentar usar primeiro tenant existente para o valor de tipo
    null_os = conn.execute(text("SELECT id, cliente_id, tipo FROM ordem_servico WHERE tipo_id IS NULL AND tipo IS NOT NULL")).fetchall()
    if null_os:
        first_tenant = conn.execute(text("SELECT id FROM tenants ORDER BY id LIMIT 1")).fetchone()
        if first_tenant:
            tenant_id_default = first_tenant[0]
            for row in null_os:
                os_id, _, tipo_val = row[0], row[1], row[2]
                if not tipo_val:
                    continue
                existing = conn.execute(
                    text("SELECT id FROM ordem_servico_tipo WHERE tenant_id = :tid AND nome = :nome LIMIT 1"),
                    {"tid": tenant_id_default, "nome": tipo_val},
                ).fetchone()
                if existing:
                    tipo_id = existing[0]
                else:
                    conn.execute(
                        text(
                            "INSERT INTO ordem_servico_tipo (tenant_id, nome, codigo, ativo, created_at, updated_at) "
                            "VALUES (:tid, :nome, :codigo, true, NOW(), NOW())"
                        ),
                        {"tid": tenant_id_default, "nome": tipo_val, "codigo": tipo_val},
                    )
                    r = conn.execute(
                        text("SELECT id FROM ordem_servico_tipo WHERE tenant_id = :tid AND nome = :nome ORDER BY id DESC LIMIT 1"),
                        {"tid": tenant_id_default, "nome": tipo_val},
                    ).fetchone()
                    tipo_id = r[0] if r else None
                if tipo_id is not None:
                    conn.execute(text("UPDATE ordem_servico SET tipo_id = :tid WHERE id = :osid"), {"tid": tipo_id, "osid": os_id})

    # 4. tipo_id NOT NULL: preencher qualquer NULL restante com primeiro tipo existente
    first_tipo = conn.execute(text("SELECT id FROM ordem_servico_tipo ORDER BY id LIMIT 1")).fetchone()
    if first_tipo:
        conn.execute(
            text("UPDATE ordem_servico SET tipo_id = :tid WHERE tipo_id IS NULL"),
            {"tid": first_tipo[0]},
        )
    null_count = conn.execute(text("SELECT COUNT(*) FROM ordem_servico WHERE tipo_id IS NULL")).scalar()
    if null_count == 0:
        op.alter_column(
            "ordem_servico",
            "tipo_id",
            existing_type=sa.Integer(),
            nullable=False,
        )

    # 5. Remover coluna tipo
    op.drop_column("ordem_servico", "tipo")

    # 6. Se existir tipo enum no PostgreSQL, remover (modelo usava native_enum=False, pode ser varchar)
    # Não é necessário dropar enum se foi criado como VARCHAR.


def downgrade() -> None:
    conn = op.get_bind()

    # Recriar coluna tipo (varchar) e popular a partir de ordem_servico_tipo
    op.add_column("ordem_servico", sa.Column("tipo", sa.String(30), nullable=True))
    conn.execute(
        text(
            "UPDATE ordem_servico os SET tipo = ost.nome FROM ordem_servico_tipo ost WHERE os.tipo_id = ost.id"
        )
    )
    op.alter_column("ordem_servico", "tipo", nullable=False, server_default="outro")

    op.drop_constraint("fk_ordem_servico_tipo_id", "ordem_servico", type_="foreignkey")
    op.drop_index("ix_ordem_servico_tipo_id", table_name="ordem_servico")
    op.drop_column("ordem_servico", "tipo_id")

    op.drop_index("ix_ordem_servico_tipo_tenant_ativo", table_name="ordem_servico_tipo")
    op.drop_index("ix_ordem_servico_tipo_tenant_id", table_name="ordem_servico_tipo")
    op.drop_table("ordem_servico_tipo")
