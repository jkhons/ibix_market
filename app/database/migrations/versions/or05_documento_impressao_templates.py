"""Templates configuráveis de impressão (Orçamento · OS) por tenant.

Revision ID: or05_documento_impressao_templates
Revises: or04_venda_origens_rastreio
Create Date: 2026-06-18
"""
import sqlalchemy as sa
from alembic import op

from app.core.rls import RLS_TENANT_POLICY

revision = "or05_documento_impressao_templates"
down_revision = "or04_venda_origens_rastreio"
branch_labels = None
depends_on = None

TEMPLATE_ORC = """<div style="font-family:sans-serif;padding:20px;">
{% if brand_logo_url %}<img src="{{ brand_logo_url }}" alt="" style="max-height:48px;margin-bottom:12px;">{% endif %}
<h1>Orçamento {{ numero_orcamento }}</h1>
<p>Validade: {{ data_validade }} | Status: {{ status }}</p>
<p>Unidade: {{ cliente_nome }}</p>
<p>Consumidor: {{ destinatario_nome or '-' }}</p>
<p>Vendedor: {{ vendedor_nome or '-' }}</p>
<table style="width:100%;border-collapse:collapse;margin-top:16px;">
<thead><tr style="background:#eee;">
<th style="border:1px solid #999;padding:6px;">Código</th>
<th style="border:1px solid #999;padding:6px;">Descrição</th>
<th style="border:1px solid #999;padding:6px;">Qtd</th>
<th style="border:1px solid #999;padding:6px;">Unit.</th>
<th style="border:1px solid #999;padding:6px;">Total</th>
</tr></thead>
<tbody>
{% for i in itens %}
<tr>
<td style="border:1px solid #ccc;padding:4px;">{{ i.codigo_produto or '' }}</td>
<td style="border:1px solid #ccc;padding:4px;">{{ i.descricao_produto or '' }}</td>
<td style="border:1px solid #ccc;padding:4px;">{{ i.quantidade }}</td>
<td style="border:1px solid #ccc;padding:4px;">R$ {{ i.preco_unitario }}</td>
<td style="border:1px solid #ccc;padding:4px;">R$ {{ i.total_item }}</td>
</tr>
{% endfor %}
</tbody></table>
<p style="margin-top:16px;">Subtotal: R$ {{ subtotal }} | Desconto: R$ {{ desconto }} | Total: R$ {{ total }}</p>
<p>{{ observacoes }}</p>
<p>{{ condicoes_pagamento }}</p>
</div>"""

TEMPLATE_OS = """<div style="font-family:sans-serif;padding:20px;">
{% if brand_logo_url %}<img src="{{ brand_logo_url }}" alt="" style="max-height:48px;margin-bottom:12px;">{% endif %}
<h1>Ordem de Serviço {{ codigo }}</h1>
<p>Status: {{ status }} | Tipo: {{ tipo_nome or '-' }} | Abertura: {{ data_abertura }}</p>
<p>Cliente: {{ cliente_nome or '-' }}</p>
<table style="width:100%;border-collapse:collapse;margin-top:16px;">
<thead><tr style="background:#eee;">
<th style="border:1px solid #999;padding:6px;">Descrição</th>
<th style="border:1px solid #999;padding:6px;">Qtd</th>
<th style="border:1px solid #999;padding:6px;">Unit.</th>
<th style="border:1px solid #999;padding:6px;">Total</th>
</tr></thead>
<tbody>
{% for i in itens %}
<tr>
<td style="border:1px solid #ccc;padding:4px;">{{ i.descricao }}</td>
<td style="border:1px solid #ccc;padding:4px;">{{ i.quantidade }}</td>
<td style="border:1px solid #ccc;padding:4px;">R$ {{ i.valor_unitario }}</td>
<td style="border:1px solid #ccc;padding:4px;">R$ {{ i.valor_total }}</td>
</tr>
{% endfor %}
</tbody></table>
<p style="margin-top:16px;">Subtotal: R$ {{ subtotal }} | Desconto: R$ {{ desconto }} | Total: R$ {{ total }}</p>
<p>{{ observacoes }}</p>
</div>"""


def upgrade() -> None:
    op.create_table(
        "documento_impressao_templates",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tipo_documento", sa.String(30), nullable=False),
        sa.Column("nome", sa.String(120), nullable=False),
        sa.Column("conteudo_html", sa.Text(), nullable=False),
        sa.Column("css_extra", sa.Text(), nullable=True),
        sa.Column("is_padrao", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id", "tipo_documento", "nome", name="uq_doc_imp_tenant_tipo_nome"),
    )
    op.create_index(
        "ix_doc_imp_tenant_tipo_padrao",
        "documento_impressao_templates",
        ["tenant_id", "tipo_documento", "is_padrao"],
    )

    conn = op.get_bind()
    conn.execute(sa.text("ALTER TABLE documento_impressao_templates ENABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("ALTER TABLE documento_impressao_templates FORCE ROW LEVEL SECURITY"))
    conn.execute(sa.text(RLS_TENANT_POLICY.format(table="documento_impressao_templates")))

    conn.execute(
        sa.text(
            """
            INSERT INTO documento_impressao_templates
                (tenant_id, tipo_documento, nome, conteudo_html, is_padrao, ativo)
            SELECT t.id, 'orcamento', 'Padrão A4', :html, true, true
            FROM tenants t
            WHERE NOT EXISTS (
                SELECT 1 FROM documento_impressao_templates d
                WHERE d.tenant_id = t.id AND d.tipo_documento = 'orcamento' AND d.is_padrao = true
            )
            """
        ),
        {"html": TEMPLATE_ORC},
    )
    conn.execute(
        sa.text(
            """
            INSERT INTO documento_impressao_templates
                (tenant_id, tipo_documento, nome, conteudo_html, is_padrao, ativo)
            SELECT t.id, 'ordem_servico', 'Padrão A4', :html, true, true
            FROM tenants t
            WHERE NOT EXISTS (
                SELECT 1 FROM documento_impressao_templates d
                WHERE d.tenant_id = t.id AND d.tipo_documento = 'ordem_servico' AND d.is_padrao = true
            )
            """
        ),
        {"html": TEMPLATE_OS},
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DROP POLICY IF EXISTS rls_documento_impressao_templates_tenant ON documento_impressao_templates"))
    op.drop_index("ix_doc_imp_tenant_tipo_padrao", table_name="documento_impressao_templates")
    op.drop_table("documento_impressao_templates")
