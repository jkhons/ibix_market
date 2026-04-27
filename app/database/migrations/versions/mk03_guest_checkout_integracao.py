"""Guest checkout e integração CRM: tenant_id, tipo_consumidor, numero_pedido, integration_events.

Revision ID: mk03_guest
Revises: pc07_foto_midias
Create Date: 2026-03-09

- consumidores_marketplace: tenant_id, tipo_pessoa, tipo_consumidor, status_cadastro,
  aceite_marketing, aceite_marketing_em, origem_cadastro, canal_origem, utm_*, 
  primeira_compra_em, ultima_compra_em, deleted_at; senha_hash nullable.
  UNIQUE(tenant_id, LOWER(email)) WHERE deleted_at IS NULL.
- enderecos_consumidor: tenant_id, tipo_endereco, referencia, principal.
- pedidos_marketplace: tenant_id, numero_pedido, status_entrega, origem_pedido,
  aceite_marketing_snapshot, canal_origem, utm_*, observacoes_cliente.
- pedido_itens_marketplace: tenant_id, loja_id, produto_id, sku_id, desconto_unitario,
  nome_produto_snapshot, categoria_snapshot, marca_snapshot, sku_snapshot.
- integration_events: nova tabela.
- Backfill: tenant_id em consumidores (de pedidos ou nullable), enderecos (do consumidor),
  pedidos (da loja), numero_pedido (formato tenant_id-id).
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "mk03_guest"
down_revision = "pc07_foto_midias"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- consumidores_marketplace ---
    op.add_column("consumidores_marketplace", sa.Column("tenant_id", sa.Integer(), nullable=True))
    op.add_column("consumidores_marketplace", sa.Column("tipo_pessoa", sa.String(2), nullable=True))
    op.add_column("consumidores_marketplace", sa.Column("tipo_consumidor", sa.String(20), server_default="REGISTERED", nullable=False))
    op.add_column("consumidores_marketplace", sa.Column("status_cadastro", sa.String(20), server_default="COMPLETO", nullable=False))
    op.add_column("consumidores_marketplace", sa.Column("aceite_marketing", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("consumidores_marketplace", sa.Column("aceite_marketing_em", sa.DateTime(timezone=True), nullable=True))
    op.add_column("consumidores_marketplace", sa.Column("origem_cadastro", sa.String(50), nullable=True))
    op.add_column("consumidores_marketplace", sa.Column("canal_origem", sa.String(50), nullable=True))
    op.add_column("consumidores_marketplace", sa.Column("utm_source", sa.String(150), nullable=True))
    op.add_column("consumidores_marketplace", sa.Column("utm_medium", sa.String(150), nullable=True))
    op.add_column("consumidores_marketplace", sa.Column("utm_campaign", sa.String(150), nullable=True))
    op.add_column("consumidores_marketplace", sa.Column("primeira_compra_em", sa.DateTime(timezone=True), nullable=True))
    op.add_column("consumidores_marketplace", sa.Column("ultima_compra_em", sa.DateTime(timezone=True), nullable=True))
    op.add_column("consumidores_marketplace", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.alter_column("consumidores_marketplace", "senha_hash", existing_type=sa.String(255), nullable=True)

    op.create_index("ix_consumidores_marketplace_tenant_id", "consumidores_marketplace", ["tenant_id"])
    op.create_index("ix_consumidores_marketplace_updated_at", "consumidores_marketplace", ["updated_at"])
    op.create_index("ix_consumidores_marketplace_tipo_consumidor", "consumidores_marketplace", ["tipo_consumidor"])
    op.create_index("ix_consumidores_marketplace_status_cadastro", "consumidores_marketplace", ["status_cadastro"])
    op.create_index("ix_consumidores_marketplace_documento", "consumidores_marketplace", ["documento"])

    # Backfill consumidores: tenant_id do primeiro pedido
    op.execute("""
        UPDATE consumidores_marketplace c
        SET tenant_id = (
            SELECT l.cliente_id FROM pedidos_marketplace p
            JOIN lojas_marketplace l ON l.id = p.loja_id
            WHERE p.comprador_id = c.id
            ORDER BY p.created_at ASC LIMIT 1
        )
        WHERE c.tenant_id IS NULL AND EXISTS (
            SELECT 1 FROM pedidos_marketplace p WHERE p.comprador_id = c.id
        )
    """)
    # Órfãos sem pedido: deixar tenant_id NULL (gestão no front)
    # Unique: (tenant_id, LOWER(email)) WHERE deleted_at IS NULL
    op.drop_index("ix_consumidores_marketplace_email", table_name="consumidores_marketplace")
    op.execute("""
        CREATE UNIQUE INDEX uq_consumidores_marketplace_tenant_email_ativo
        ON consumidores_marketplace (tenant_id, LOWER(email))
        WHERE deleted_at IS NULL
    """)
    op.create_index("ix_consumidores_marketplace_email", "consumidores_marketplace", [sa.text("LOWER(email)")])

    # --- enderecos_consumidor ---
    op.add_column("enderecos_consumidor", sa.Column("tenant_id", sa.Integer(), nullable=True))
    op.add_column("enderecos_consumidor", sa.Column("tipo_endereco", sa.String(20), server_default="principal", nullable=False))
    op.add_column("enderecos_consumidor", sa.Column("referencia", sa.String(200), nullable=True))
    op.add_column("enderecos_consumidor", sa.Column("principal", sa.Boolean(), server_default="false", nullable=False))
    op.create_index("ix_enderecos_consumidor_tenant_id", "enderecos_consumidor", ["tenant_id"])
    # Backfill tenant_id dos endereços a partir do consumidor
    op.execute("""
        UPDATE enderecos_consumidor e
        SET tenant_id = c.tenant_id
        FROM consumidores_marketplace c
        WHERE e.consumidor_id = c.id AND e.tenant_id IS NULL
    """)
    # tenant_id permanece nullable para endereços de consumidores órfãos

    # --- pedidos_marketplace ---
    op.add_column("pedidos_marketplace", sa.Column("tenant_id", sa.Integer(), nullable=True))
    op.add_column("pedidos_marketplace", sa.Column("numero_pedido", sa.String(50), nullable=True))
    op.add_column("pedidos_marketplace", sa.Column("status_entrega", sa.String(30), server_default="pendente", nullable=False))
    op.add_column("pedidos_marketplace", sa.Column("origem_pedido", sa.String(30), server_default="checkout_guest", nullable=False))
    op.add_column("pedidos_marketplace", sa.Column("aceite_marketing_snapshot", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("pedidos_marketplace", sa.Column("canal_origem", sa.String(50), nullable=True))
    op.add_column("pedidos_marketplace", sa.Column("utm_source", sa.String(100), nullable=True))
    op.add_column("pedidos_marketplace", sa.Column("utm_medium", sa.String(100), nullable=True))
    op.add_column("pedidos_marketplace", sa.Column("utm_campaign", sa.String(150), nullable=True))
    op.add_column("pedidos_marketplace", sa.Column("observacoes_cliente", sa.Text(), nullable=True))
    op.create_index("ix_pedidos_marketplace_tenant_id", "pedidos_marketplace", ["tenant_id"])
    op.create_index("ix_pedidos_marketplace_numero_pedido", "pedidos_marketplace", ["numero_pedido"])
    op.create_index("ix_pedidos_marketplace_updated_at", "pedidos_marketplace", ["updated_at"])
    # Backfill tenant_id e numero_pedido
    op.execute("""
        UPDATE pedidos_marketplace p
        SET tenant_id = l.cliente_id,
            numero_pedido = l.cliente_id || '-' || p.id
        FROM lojas_marketplace l
        WHERE p.loja_id = l.id AND p.tenant_id IS NULL
    """)
    op.alter_column("pedidos_marketplace", "tenant_id", nullable=False)
    op.alter_column("pedidos_marketplace", "numero_pedido", nullable=False)
    op.create_unique_constraint("uq_pedidos_marketplace_tenant_numero", "pedidos_marketplace", ["tenant_id", "numero_pedido"])

    # --- pedido_itens_marketplace ---
    op.add_column("pedido_itens_marketplace", sa.Column("tenant_id", sa.Integer(), nullable=True))
    op.add_column("pedido_itens_marketplace", sa.Column("loja_id", sa.Integer(), nullable=True))
    op.add_column("pedido_itens_marketplace", sa.Column("produto_id", sa.Integer(), nullable=True))
    op.add_column("pedido_itens_marketplace", sa.Column("sku_id", sa.Integer(), nullable=True))
    op.add_column("pedido_itens_marketplace", sa.Column("desconto_unitario", sa.Numeric(10, 2), server_default="0", nullable=False))
    op.add_column("pedido_itens_marketplace", sa.Column("nome_produto_snapshot", sa.String(255), nullable=True))
    op.add_column("pedido_itens_marketplace", sa.Column("categoria_snapshot", sa.String(120), nullable=True))
    op.add_column("pedido_itens_marketplace", sa.Column("marca_snapshot", sa.String(120), nullable=True))
    op.add_column("pedido_itens_marketplace", sa.Column("sku_snapshot", sa.String(120), nullable=True))
    op.create_index("ix_pedido_itens_marketplace_tenant_id", "pedido_itens_marketplace", ["tenant_id"])
    op.create_index("ix_pedido_itens_marketplace_produto_id", "pedido_itens_marketplace", ["produto_id"])
    # Backfill: tenant_id e loja_id do pedido; nome_produto_snapshot do anúncio
    op.execute("""
        UPDATE pedido_itens_marketplace pi
        SET tenant_id = p.tenant_id,
            loja_id = p.loja_id,
            produto_id = a.produto_ca_id,
            nome_produto_snapshot = COALESCE(a.titulo, '')
        FROM pedidos_marketplace p, anuncios_plataforma a
        WHERE pi.pedido_id = p.id AND pi.anuncio_id = a.id AND pi.tenant_id IS NULL
    """)
    op.alter_column("pedido_itens_marketplace", "tenant_id", nullable=False)
    op.alter_column("pedido_itens_marketplace", "loja_id", nullable=False)
    op.alter_column("pedido_itens_marketplace", "nome_produto_snapshot", nullable=False, server_default="")
    op.alter_column("pedido_itens_marketplace", "nome_produto_snapshot", server_default=None)

    # --- integration_events ---
    op.create_table(
        "integration_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("event_name", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("payload_json", JSONB(), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_integration_events_tenant_id", "integration_events", ["tenant_id"])
    op.create_index("ix_integration_events_event_name", "integration_events", ["event_name"])
    op.create_index("ix_integration_events_entity_type_id", "integration_events", ["entity_type", "entity_id"])
    op.create_index("ix_integration_events_status", "integration_events", ["status"])
    op.create_index("ix_integration_events_created_at", "integration_events", ["created_at"])


def downgrade() -> None:
    op.drop_table("integration_events")

    op.drop_index("ix_pedido_itens_marketplace_produto_id", table_name="pedido_itens_marketplace")
    op.drop_index("ix_pedido_itens_marketplace_tenant_id", table_name="pedido_itens_marketplace")
    op.drop_column("pedido_itens_marketplace", "sku_snapshot")
    op.drop_column("pedido_itens_marketplace", "marca_snapshot")
    op.drop_column("pedido_itens_marketplace", "categoria_snapshot")
    op.drop_column("pedido_itens_marketplace", "nome_produto_snapshot")
    op.drop_column("pedido_itens_marketplace", "desconto_unitario")
    op.drop_column("pedido_itens_marketplace", "sku_id")
    op.drop_column("pedido_itens_marketplace", "produto_id")
    op.drop_column("pedido_itens_marketplace", "loja_id")
    op.drop_column("pedido_itens_marketplace", "tenant_id")

    op.drop_constraint("uq_pedidos_marketplace_tenant_numero", "pedidos_marketplace", type_="unique")
    op.drop_index("ix_pedidos_marketplace_updated_at", table_name="pedidos_marketplace")
    op.drop_index("ix_pedidos_marketplace_numero_pedido", table_name="pedidos_marketplace")
    op.drop_index("ix_pedidos_marketplace_tenant_id", table_name="pedidos_marketplace")
    op.drop_column("pedidos_marketplace", "observacoes_cliente")
    op.drop_column("pedidos_marketplace", "utm_campaign")
    op.drop_column("pedidos_marketplace", "utm_medium")
    op.drop_column("pedidos_marketplace", "utm_source")
    op.drop_column("pedidos_marketplace", "canal_origem")
    op.drop_column("pedidos_marketplace", "aceite_marketing_snapshot")
    op.drop_column("pedidos_marketplace", "origem_pedido")
    op.drop_column("pedidos_marketplace", "status_entrega")
    op.drop_column("pedidos_marketplace", "numero_pedido")
    op.drop_column("pedidos_marketplace", "tenant_id")

    op.drop_index("ix_enderecos_consumidor_tenant_id", table_name="enderecos_consumidor")
    op.drop_column("enderecos_consumidor", "principal")
    op.drop_column("enderecos_consumidor", "referencia")
    op.drop_column("enderecos_consumidor", "tipo_endereco")
    op.drop_column("enderecos_consumidor", "tenant_id")

    op.execute("DROP INDEX IF EXISTS uq_consumidores_marketplace_tenant_email_ativo")
    op.drop_index("ix_consumidores_marketplace_email", table_name="consumidores_marketplace")
    op.create_index("ix_consumidores_marketplace_email", "consumidores_marketplace", ["email"], unique=True)
    op.drop_index("ix_consumidores_marketplace_status_cadastro", table_name="consumidores_marketplace")
    op.drop_index("ix_consumidores_marketplace_tipo_consumidor", table_name="consumidores_marketplace")
    op.drop_index("ix_consumidores_marketplace_updated_at", table_name="consumidores_marketplace")
    op.drop_index("ix_consumidores_marketplace_tenant_id", table_name="consumidores_marketplace")
    op.drop_index("ix_consumidores_marketplace_documento", table_name="consumidores_marketplace")
    op.alter_column("consumidores_marketplace", "senha_hash", existing_type=sa.String(255), nullable=False)
    op.drop_column("consumidores_marketplace", "deleted_at")
    op.drop_column("consumidores_marketplace", "ultima_compra_em")
    op.drop_column("consumidores_marketplace", "primeira_compra_em")
    op.drop_column("consumidores_marketplace", "utm_campaign")
    op.drop_column("consumidores_marketplace", "utm_medium")
    op.drop_column("consumidores_marketplace", "utm_source")
    op.drop_column("consumidores_marketplace", "canal_origem")
    op.drop_column("consumidores_marketplace", "origem_cadastro")
    op.drop_column("consumidores_marketplace", "aceite_marketing_em")
    op.drop_column("consumidores_marketplace", "aceite_marketing")
    op.drop_column("consumidores_marketplace", "status_cadastro")
    op.drop_column("consumidores_marketplace", "tipo_consumidor")
    op.drop_column("consumidores_marketplace", "tipo_pessoa")
    op.drop_column("consumidores_marketplace", "tenant_id")
