"""Seed: categorias e tipos mais usados em marketplaces (Brasil).

Fontes: Mercado Livre, Amazon BR, E-Commerce Brasil (2024):
- Categorias líderes: Casa e Decoração, Moda e Beleza, Eletrônicos, Supermercado,
  Educação/Livros/Papelaria, Esportes e Fitness, Eletrodomésticos, Informática, etc.
- Tipos: adiciona Digital/Assinatura e Kit/Combo (comuns em e-commerce).

Revision ID: mc03_marketplace
Revises: mc02_seed
Create Date: 2026-03-08

"""
import sqlalchemy as sa
from alembic import op

revision = "mc03_marketplace"
down_revision = "mc02_seed"
branch_labels = None
depends_on = None


# Tipos de material adicionais (marketplace/e-commerce) – codigo max 20
TIPOS_MATERIAL_MARKETPLACE = [
    ("DIGITAL", "Digital / Assinatura"),
    ("KIT", "Kit / Combo"),
]

# Categorias mais usadas em marketplaces Brasil – codigo max 20 caracteres
CATEGORIAS_MARKETPLACE = [
    ("CASA_DECORACAO", "Casa e Decoração"),
    ("MODA_BELEZA", "Moda e Beleza"),
    ("LIVROS_PAPELARIA", "Livros e Papelaria"),
    ("ESPORTES_FITNESS", "Esportes e Fitness"),
    ("ELETRODOMESTICOS", "Eletrodomésticos"),
    ("INFORMATICA", "Informática"),
    ("FERRAMENTAS", "Ferramentas e Construção"),
    ("BRINQUEDOS_GAMES", "Brinquedos e Games"),
    ("SAUDE_MEDICAMENTOS", "Saúde e Medicamentos"),
    ("AUTOMOVEIS_PECAS", "Automóveis e Peças"),
    ("GAMES_CONSOLES", "Games e Consoles"),
    ("COZINHA", "Cozinha"),
    ("JARDIM_PISCINA", "Jardim e Piscina"),
    ("BEBES", "Bebês"),
    ("INDUSTRIA_COMERCIO", "Indústria e Comércio"),
]


def upgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name

    for codigo, nome in TIPOS_MATERIAL_MARKETPLACE:
        if dialect == "postgresql":
            op.execute(sa.text(
                "INSERT INTO tipo_material (codigo, nome, ativo) VALUES (:codigo, :nome, true) ON CONFLICT (codigo) DO NOTHING"
            ).bindparams(codigo=codigo, nome=nome))
        else:
            op.execute(sa.text(
                "INSERT OR IGNORE INTO tipo_material (codigo, nome, ativo) VALUES (:codigo, :nome, 1)"
            ).bindparams(codigo=codigo, nome=nome))

    for codigo, nome in CATEGORIAS_MARKETPLACE:
        if dialect == "postgresql":
            op.execute(sa.text("""
                INSERT INTO material_categoria (nome, codigo, ativo, controla_estoque, permite_negativo, tem_validade, dias_alerta_vencimento, requer_aprovacao, incluir_relatorios, cor_relatorio)
                SELECT :nome, :codigo, true, true, false, false, 30, false, true, '#007bff'
                WHERE NOT EXISTS (SELECT 1 FROM material_categoria WHERE codigo = :codigo OR nome = :nome)
            """).bindparams(nome=nome, codigo=codigo))
        else:
            op.execute(sa.text("""
                INSERT OR IGNORE INTO material_categoria (nome, codigo, ativo, controla_estoque, permite_negativo, tem_validade, dias_alerta_vencimento, requer_aprovacao, incluir_relatorios, cor_relatorio)
                VALUES (:nome, :codigo, 1, 1, 0, 0, 30, 0, 1, '#007bff')
            """).bindparams(nome=nome, codigo=codigo))


def downgrade() -> None:
    for codigo, _ in reversed(TIPOS_MATERIAL_MARKETPLACE):
        op.execute(sa.text("DELETE FROM tipo_material WHERE codigo = :c").bindparams(c=codigo))
    for codigo, _ in reversed(CATEGORIAS_MARKETPLACE):
        op.execute(sa.text("DELETE FROM material_categoria WHERE codigo = :c").bindparams(c=codigo))
