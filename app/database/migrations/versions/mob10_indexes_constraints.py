"""Mobile: índices faltantes, constraints, remove índice redundante.

Corrige gaps identificados na auditoria profissional:
- Remove index redundante ix_cupons_marketplace_codigo (UC já cria índice)
- Adiciona índice (consumidor_id, created_at DESC) em notificações para paginação
- Adiciona índice (consumidor_id, ultima_mensagem_em) em conversas
- Adiciona partial unique para uma conversa ativa por (consumidor_id, loja_id)
- Adiciona unique constraint em cupons_consumidor para evitar uso duplo
- Adiciona CHECK constraints para plataforma, tipo_desconto, status
- Adiciona índices em refresh_tokens (expires_at, revoked) para cleanup
- Adiciona índice (ativo, valido_de, valido_ate) em cupons para listagem

Revision ID: mob10_indexes_constraints
Revises: mob09_busca
Create Date: 2026-04-13
"""
import sqlalchemy as sa
from alembic import op

revision = "mob10_indexes_constraints"
down_revision = "mob09_busca"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Remove índice redundante (UniqueConstraint já cria índice no PG)
    op.drop_index("ix_cupons_marketplace_codigo", table_name="cupons_marketplace")

    # 2. Notificações: índice para listagem paginada "mais recentes primeiro"
    op.create_index(
        "ix_notificacoes_consumidor_created",
        "consumidor_notificacoes",
        ["consumidor_id", sa.text("created_at DESC")],
    )

    # 3. Conversas: índice para listagem por última mensagem
    op.create_index(
        "ix_conversas_consumidor_ultima_msg",
        "conversas_marketplace",
        ["consumidor_id", sa.text("ultima_mensagem_em DESC NULLS LAST")],
    )
    op.create_index(
        "ix_conversas_loja_ultima_msg",
        "conversas_marketplace",
        ["loja_id", sa.text("ultima_mensagem_em DESC NULLS LAST")],
    )

    # 4. Partial unique: no máximo uma conversa ativa por (consumidor, loja)
    op.execute(
        "CREATE UNIQUE INDEX uq_conversas_ativa_consumidor_loja "
        "ON conversas_marketplace (consumidor_id, loja_id) "
        "WHERE status = 'ativa'"
    )

    # 5. Cupons consumidor: unique (cupom_id, consumidor_id, pedido_id) evita duplas
    op.create_unique_constraint(
        "uq_cupons_consumidor_uso",
        "cupons_consumidor",
        ["cupom_id", "consumidor_id", "pedido_id"],
    )

    # 6. Cupons marketplace: índice para listagem de disponíveis
    op.create_index(
        "ix_cupons_marketplace_ativo_datas",
        "cupons_marketplace",
        ["ativo", "valido_de", "valido_ate"],
    )

    # 7. Refresh tokens: índices para rotação e cleanup
    op.create_index(
        "ix_refresh_tokens_consumidor_revoked",
        "consumidor_refresh_tokens",
        ["consumidor_id", "revoked"],
    )
    op.create_index(
        "ix_refresh_tokens_expires",
        "consumidor_refresh_tokens",
        ["expires_at"],
        postgresql_where=sa.text("revoked = false"),
    )

    # 8. Push tokens: índice composto para tokens ativos por consumidor
    op.create_index(
        "ix_push_tokens_consumidor_ativo",
        "consumidor_push_tokens",
        ["consumidor_id", "ativo"],
    )

    # 9. CHECK constraints para valores de domínio
    op.execute(
        "ALTER TABLE consumidor_push_tokens "
        "ADD CONSTRAINT ck_push_token_plataforma CHECK (plataforma IN ('ios', 'android'))"
    )
    op.execute(
        "ALTER TABLE app_versao_config "
        "ADD CONSTRAINT ck_app_versao_plataforma CHECK (plataforma IN ('ios', 'android'))"
    )
    op.execute(
        "ALTER TABLE cupons_marketplace "
        "ADD CONSTRAINT ck_cupom_tipo_desconto CHECK (tipo_desconto IN ('percentual', 'fixo'))"
    )
    op.execute(
        "ALTER TABLE cupons_marketplace "
        "ADD CONSTRAINT ck_cupom_valor_positivo CHECK (valor_desconto > 0)"
    )
    op.execute(
        "ALTER TABLE devolucoes_marketplace "
        "ADD CONSTRAINT ck_devolucao_status CHECK (status IN ('aberta', 'em_analise', 'aprovada', 'recusada', 'finalizada'))"
    )
    op.execute(
        "ALTER TABLE devolucoes_marketplace "
        "ADD CONSTRAINT ck_devolucao_tipo CHECK (tipo IN ('devolucao', 'reembolso'))"
    )
    op.execute(
        "ALTER TABLE conversas_marketplace "
        "ADD CONSTRAINT ck_conversa_status CHECK (status IN ('ativa', 'encerrada', 'arquivada'))"
    )
    op.execute(
        "ALTER TABLE mensagens_conversa "
        "ADD CONSTRAINT ck_mensagem_conteudo CHECK (texto IS NOT NULL OR imagem_url IS NOT NULL)"
    )
    op.execute(
        "ALTER TABLE motivos_cancelamento "
        "ADD CONSTRAINT ck_motivo_tipo CHECK (tipo IN ('cancelamento', 'devolucao'))"
    )
    op.execute(
        "ALTER TABLE consumidor_consentimentos "
        "ADD CONSTRAINT ck_consentimento_tipo CHECK (tipo IN ('marketing', 'analytics', 'terceiros'))"
    )

    # 10. Termos buscados: índice funcional para case-insensitive (termo já é lower)
    op.create_index(
        "ix_termos_buscados_termo_lower",
        "termos_buscados",
        [sa.text("lower(termo)")],
    )

    # 11. Devoluções: índice para consulta por pedido + status
    op.create_index(
        "ix_devolucoes_pedido_status",
        "devolucoes_marketplace",
        ["pedido_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_devolucoes_pedido_status", table_name="devolucoes_marketplace")
    op.drop_index("ix_termos_buscados_termo_lower", table_name="termos_buscados")

    op.execute("ALTER TABLE consumidor_consentimentos DROP CONSTRAINT IF EXISTS ck_consentimento_tipo")
    op.execute("ALTER TABLE motivos_cancelamento DROP CONSTRAINT IF EXISTS ck_motivo_tipo")
    op.execute("ALTER TABLE mensagens_conversa DROP CONSTRAINT IF EXISTS ck_mensagem_conteudo")
    op.execute("ALTER TABLE conversas_marketplace DROP CONSTRAINT IF EXISTS ck_conversa_status")
    op.execute("ALTER TABLE devolucoes_marketplace DROP CONSTRAINT IF EXISTS ck_devolucao_tipo")
    op.execute("ALTER TABLE devolucoes_marketplace DROP CONSTRAINT IF EXISTS ck_devolucao_status")
    op.execute("ALTER TABLE cupons_marketplace DROP CONSTRAINT IF EXISTS ck_cupom_valor_positivo")
    op.execute("ALTER TABLE cupons_marketplace DROP CONSTRAINT IF EXISTS ck_cupom_tipo_desconto")
    op.execute("ALTER TABLE app_versao_config DROP CONSTRAINT IF EXISTS ck_app_versao_plataforma")
    op.execute("ALTER TABLE consumidor_push_tokens DROP CONSTRAINT IF EXISTS ck_push_token_plataforma")

    op.drop_index("ix_push_tokens_consumidor_ativo", table_name="consumidor_push_tokens")
    op.drop_index("ix_refresh_tokens_expires", table_name="consumidor_refresh_tokens")
    op.drop_index("ix_refresh_tokens_consumidor_revoked", table_name="consumidor_refresh_tokens")
    op.drop_index("ix_cupons_marketplace_ativo_datas", table_name="cupons_marketplace")
    op.drop_constraint("uq_cupons_consumidor_uso", "cupons_consumidor", type_="unique")
    op.execute("DROP INDEX IF EXISTS uq_conversas_ativa_consumidor_loja")
    op.drop_index("ix_conversas_loja_ultima_msg", table_name="conversas_marketplace")
    op.drop_index("ix_conversas_consumidor_ultima_msg", table_name="conversas_marketplace")
    op.drop_index("ix_notificacoes_consumidor_created", table_name="consumidor_notificacoes")

    op.create_index("ix_cupons_marketplace_codigo", "cupons_marketplace", ["codigo"])
