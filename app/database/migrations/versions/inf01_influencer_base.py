"""Modulo Influencers: expandir divulgadores, criar campanhas/links/metricas, seed role + permissoes

Revision ID: inf01_influencer_base
Revises: mv14_marketing_card_anuncio_ids
Create Date: 2026-03-30
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision = "inf01_influencer_base"
down_revision = "mv14_marketing_card_anuncio_ids"
branch_labels = None
depends_on = None

PERMISSOES = [
    ("influencers:listar", "influencers", "listar", "Listar influencers e representantes"),
    ("influencers:gerenciar", "influencers", "gerenciar", "Criar, editar e desativar influencers"),
    ("influencers:aprovar", "influencers", "aprovar", "Aprovar, reprovar e alterar status de influencers"),
    ("influencers:campanhas_listar", "influencers", "visualizar", "Listar campanhas de influencers"),
    ("influencers:campanhas_gerenciar", "influencers", "criar", "Criar e editar campanhas de influencers"),
    ("influencers:metricas", "influencers", "visualizar", "Visualizar metricas de influencers"),
    ("influencers:area", "influencers", "visualizar", "Acesso a area do influencer"),
]

ROLE_PERMISSOES = {
    "Superadministrador": [
        "influencers:listar", "influencers:gerenciar", "influencers:aprovar",
        "influencers:campanhas_listar", "influencers:campanhas_gerenciar", "influencers:metricas",
    ],
    "Administrador": [
        "influencers:listar", "influencers:campanhas_listar", "influencers:metricas",
    ],
    "Cliente Administrador": [
        "influencers:campanhas_listar", "influencers:campanhas_gerenciar", "influencers:metricas",
    ],
    "Influencer": [
        "influencers:campanhas_listar", "influencers:metricas", "influencers:area",
    ],
}


def upgrade() -> None:
    conn = op.get_bind()

    # --- 1. Expandir tabela divulgadores ---
    op.add_column("divulgadores", sa.Column("tipo", sa.String(30), nullable=True, server_default="representante"))
    op.add_column("divulgadores", sa.Column("status", sa.String(30), nullable=True, server_default="aprovado"))
    op.add_column("divulgadores", sa.Column("nicho", sa.String(100), nullable=True))
    op.add_column("divulgadores", sa.Column("cidade", sa.String(150), nullable=True))
    op.add_column("divulgadores", sa.Column("estado", sa.String(2), nullable=True))
    op.add_column("divulgadores", sa.Column("redes_sociais", sa.Text(), nullable=True))
    op.add_column("divulgadores", sa.Column("engajamento", sa.Integer(), nullable=True))
    op.add_column("divulgadores", sa.Column("score_performance", sa.Integer(), nullable=True, server_default=sa.text("0")))
    op.add_column("divulgadores", sa.Column("tipo_atuacao", sa.String(50), nullable=True))
    op.add_column("divulgadores", sa.Column("bio", sa.Text(), nullable=True))
    op.add_column("divulgadores", sa.Column("telefone", sa.String(20), nullable=True))
    op.add_column("divulgadores", sa.Column("foto_url", sa.String(500), nullable=True))

    conn.execute(text("UPDATE divulgadores SET tipo = 'representante' WHERE tipo IS NULL"))
    conn.execute(text("UPDATE divulgadores SET status = 'aprovado' WHERE status IS NULL"))

    op.create_index("ix_divulgadores_tipo", "divulgadores", ["tipo"])
    op.create_index("ix_divulgadores_status", "divulgadores", ["status"])
    op.create_index("ix_divulgadores_nicho", "divulgadores", ["nicho"])
    op.create_index("ix_divulgadores_cidade", "divulgadores", ["cidade"])

    # --- 2. Tabela influencer_campanhas ---
    op.create_table(
        "influencer_campanhas",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("divulgador_id", sa.Integer(), sa.ForeignKey("divulgadores.id", ondelete="CASCADE"), nullable=False),
        sa.Column("loja_id", sa.Integer(), sa.ForeignKey("lojas_marketplace.id", ondelete="SET NULL"), nullable=True),
        sa.Column("titulo", sa.String(255), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("tipo", sa.String(30), nullable=False, comment="propaganda, cupom, live"),
        sa.Column("status", sa.String(30), nullable=False, server_default="rascunho", comment="rascunho, ativa, pausada, finalizada, cancelada"),
        sa.Column("data_inicio", sa.Date(), nullable=True),
        sa.Column("data_fim", sa.Date(), nullable=True),
        sa.Column("valor_fixo", sa.Numeric(10, 2), nullable=True),
        sa.Column("percentual_comissao", sa.Integer(), nullable=True),
        sa.Column("modelo_pagamento", sa.String(30), nullable=True, comment="fixo, comissao, hibrido"),
        sa.Column("codigo_desconto_id", sa.Integer(), sa.ForeignKey("codigos_desconto.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_teste", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        comment="Campanhas de marketing com influencers",
    )
    op.create_index("ix_inf_campanhas_divulgador", "influencer_campanhas", ["divulgador_id"])
    op.create_index("ix_inf_campanhas_loja", "influencer_campanhas", ["loja_id"])
    op.create_index("ix_inf_campanhas_status", "influencer_campanhas", ["status"])
    op.create_index("ix_inf_campanhas_tipo", "influencer_campanhas", ["tipo"])

    # --- 3. Tabela influencer_links ---
    op.create_table(
        "influencer_links",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("campanha_id", sa.Integer(), sa.ForeignKey("influencer_campanhas.id", ondelete="SET NULL"), nullable=True),
        sa.Column("divulgador_id", sa.Integer(), sa.ForeignKey("divulgadores.id", ondelete="CASCADE"), nullable=False),
        sa.Column("url_destino", sa.String(1000), nullable=False),
        sa.Column("codigo_rastreio", sa.String(100), nullable=False, unique=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        comment="Links rastreaveis de influencers",
    )
    op.create_index("ix_inf_links_codigo", "influencer_links", ["codigo_rastreio"], unique=True)
    op.create_index("ix_inf_links_divulgador", "influencer_links", ["divulgador_id"])
    op.create_index("ix_inf_links_campanha", "influencer_links", ["campanha_id"])

    # --- 4. Tabela influencer_metricas ---
    op.create_table(
        "influencer_metricas",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("campanha_id", sa.Integer(), sa.ForeignKey("influencer_campanhas.id", ondelete="SET NULL"), nullable=True),
        sa.Column("divulgador_id", sa.Integer(), sa.ForeignKey("divulgadores.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cliques", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("visualizacoes", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("vendas", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("faturamento", sa.Numeric(12, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("conversoes_cupom", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("periodo_inicio", sa.Date(), nullable=True),
        sa.Column("periodo_fim", sa.Date(), nullable=True),
        comment="Metricas de performance de influencers",
    )
    op.create_index("ix_inf_metricas_divulgador", "influencer_metricas", ["divulgador_id"])
    op.create_index("ix_inf_metricas_campanha", "influencer_metricas", ["campanha_id"])
    op.create_index("ix_inf_metricas_periodo", "influencer_metricas", ["periodo_inicio", "periodo_fim"])

    # --- 5. Seed: Role Influencer ---
    existing = conn.execute(text("SELECT 1 FROM roles WHERE nome = 'Influencer'")).fetchone()
    if not existing:
        conn.execute(text(
            "INSERT INTO roles (nome, descricao, ativo, created_at, updated_at) "
            "VALUES ('Influencer', 'Influenciador digital: acessa painel proprio com campanhas, cupons e metricas.', true, NOW(), NOW())"
        ))

    # --- 6. Seed: Permissoes ---
    for nome, modulo, acao, descricao in PERMISSOES:
        r = conn.execute(text("SELECT 1 FROM permissoes WHERE nome = :n"), {"n": nome}).fetchone()
        if not r:
            conn.execute(text(
                "INSERT INTO permissoes (nome, modulo, acao, descricao, ativo, created_at, updated_at) "
                "VALUES (:nome, :modulo, :acao, :descricao, true, NOW(), NOW())"
            ), {"nome": nome, "modulo": modulo, "acao": acao, "descricao": descricao})

    # --- 7. Vincular permissoes as roles ---
    for role_nome, perms in ROLE_PERMISSOES.items():
        role_row = conn.execute(text("SELECT id FROM roles WHERE nome = :n"), {"n": role_nome}).fetchone()
        if not role_row:
            continue
        role_id = role_row[0]
        for perm_nome in perms:
            perm_row = conn.execute(text("SELECT id FROM permissoes WHERE nome = :n"), {"n": perm_nome}).fetchone()
            if not perm_row:
                continue
            perm_id = perm_row[0]
            exists = conn.execute(text(
                "SELECT 1 FROM role_permissoes WHERE role_id = :r AND permissao_id = :p"
            ), {"r": role_id, "p": perm_id}).fetchone()
            if not exists:
                conn.execute(text(
                    "INSERT INTO role_permissoes (role_id, permissao_id, created_at, updated_at) "
                    "VALUES (:r, :p, NOW(), NOW())"
                ), {"r": role_id, "p": perm_id})


def downgrade() -> None:
    conn = op.get_bind()

    for role_nome, perms in ROLE_PERMISSOES.items():
        role_row = conn.execute(text("SELECT id FROM roles WHERE nome = :n"), {"n": role_nome}).fetchone()
        if not role_row:
            continue
        for perm_nome in perms:
            perm_row = conn.execute(text("SELECT id FROM permissoes WHERE nome = :n"), {"n": perm_nome}).fetchone()
            if perm_row:
                conn.execute(text(
                    "DELETE FROM role_permissoes WHERE role_id = :r AND permissao_id = :p"
                ), {"r": role_row[0], "p": perm_row[0]})

    for nome, _, _, _ in PERMISSOES:
        conn.execute(text("DELETE FROM permissoes WHERE nome = :n"), {"n": nome})

    conn.execute(text("DELETE FROM roles WHERE nome = 'Influencer'"))

    op.drop_table("influencer_metricas")
    op.drop_table("influencer_links")
    op.drop_table("influencer_campanhas")

    op.drop_index("ix_divulgadores_cidade", table_name="divulgadores")
    op.drop_index("ix_divulgadores_nicho", table_name="divulgadores")
    op.drop_index("ix_divulgadores_status", table_name="divulgadores")
    op.drop_index("ix_divulgadores_tipo", table_name="divulgadores")

    for col in ("foto_url", "telefone", "bio", "tipo_atuacao", "score_performance",
                "engajamento", "redes_sociais", "estado", "cidade", "nicho", "status", "tipo"):
        op.drop_column("divulgadores", col)
