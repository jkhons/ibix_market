"""Seed: tipos de material e categorias de material (varejo/estoque).

Revision ID: mc02_seed
Revises: mc01_tables
Create Date: 2026-03-08

"""
import sqlalchemy as sa
from alembic import op

revision = "mc02_seed"
down_revision = "mc01_tables"
branch_labels = None
depends_on = None


TIPOS_MATERIAL = [
    ("PRODUTO_ACABADO", "Produto Acabado"),
    ("MATERIA_PRIMA", "Matéria-Prima"),
    ("CONSUMIVEL", "Consumível"),
    ("EMBALAGEM", "Embalagem"),
    ("PECA_REPOSICAO", "Peça de Reposição"),
    ("SERVICO", "Serviço"),
    ("LACRE", "Lacre"),
    ("SELO", "Selo"),
    ("PECA", "Peça"),
    ("OUTROS", "Outros"),
]

# codigo: max 20 caracteres (coluna material_categoria.codigo)
CATEGORIAS_MATERIAL = [
    ("PADARIA", "Padaria"),
    ("CARNES_ACOUGUE", "Carnes e Açougue"),
    ("MERCEARIA", "Mercearia"),
    ("CEREAIS_ENLATADOS", "Cereais e Enlatados"),
    ("BEBIDAS", "Bebidas"),
    ("HORTIFRUTI", "Hortifruti"),
    ("HIGIENE_LIMPEZA", "Higiene e Limpeza"),
    ("FRIOS_LATICINIOS", "Frios e Laticínios"),
    ("UTIL_DOMESTICAS", "Utilidades Domésticas"),
    ("PET_SHOP", "Pet Shop"),
    ("CONGELADOS", "Congelados"),
    ("ELETRONICOS", "Eletrônicos"),
    ("VESTUARIO", "Vestuário"),
    ("OUTROS", "Outros"),
]


def upgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name

    for codigo, nome in TIPOS_MATERIAL:
        if dialect == "postgresql":
            op.execute(sa.text(
                "INSERT INTO tipo_material (codigo, nome, ativo) VALUES (:codigo, :nome, true) ON CONFLICT (codigo) DO NOTHING"
            ).bindparams(codigo=codigo, nome=nome))
        else:
            op.execute(sa.text(
                "INSERT OR IGNORE INTO tipo_material (codigo, nome, ativo) VALUES (:codigo, :nome, 1)"
            ).bindparams(codigo=codigo, nome=nome))

    for codigo, nome in CATEGORIAS_MATERIAL:
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
    # Remover seeds por codigo (opcional; em produção pode preferir não remover)
    for codigo, _ in reversed(TIPOS_MATERIAL):
        op.execute(sa.text("DELETE FROM tipo_material WHERE codigo = :c").bindparams(c=codigo))
    for codigo, _ in reversed(CATEGORIAS_MATERIAL):
        op.execute(sa.text("DELETE FROM material_categoria WHERE codigo = :c").bindparams(c=codigo))
