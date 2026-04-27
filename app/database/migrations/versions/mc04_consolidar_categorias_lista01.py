"""Consolidar categorias de material conforme Lista 01 (Comprar por categoria).

Para cada item da Lista 01, mantém uma única categoria principal e remove as demais
que são cobertas por ela. Produtos vinculados às categorias removidas são migrados
para a principal antes da exclusão.

Revision ID: mc04_lista01
Revises: mc03_marketplace
Create Date: 2026-03-23

"""
from typing import Optional

import sqlalchemy as sa
from alembic import op

revision = "mc04_lista01"
down_revision = "mc03_marketplace"
branch_labels = None
depends_on = None


# Mapeamento: (codigo_principal, nome_principal, codigos_a_remover)
# Produtos em codigos_a_remover serão migrados para codigo_principal, depois removidos.
# Se codigo_principal não existir, será criado.
CONSOLIDACAO = [
    # Alimentos e Bebidas: uma única categoria
    (
        "ALIMENTOS_BEBIDAS",
        "Alimentos e Bebidas",
        ["BEBIDAS", "MERCEARIA", "CEREAIS_ENLATADOS", "HORTIFRUTI", "PADARIA", "CARNES_ACOUGUE", "CONGELADOS", "FRIOS_LATICINIOS"],
    ),
    # Automotivo
    ("AUTOMOTIVO", "Automotivo", ["AUTOMOVEIS_PECAS"]),
    # Beleza e Cuidados Pessoais
    ("BELEZA_CUIDADOS", "Beleza e Cuidados Pessoais", ["MODA_BELEZA"]),
    # Brinquedos e Jogos
    ("BRINQUEDOS_JOGOS", "Brinquedos e Jogos", ["BRINQUEDOS_GAMES"]),
    # Casa, Jardim e Limpeza
    (
        "CASA_JARDIM_LIMPEZA",
        "Casa, Jardim e Limpeza",
        ["CASA_DECORACAO", "HIGIENE_LIMPEZA", "JARDIM_PISCINA", "UTIL_DOMESTICAS"],
    ),
    # Eletrônicos, TV e Áudio (ELETRONICOS vem do mc02)
    ("ELETRONICOS", "Eletrônicos, TV e Áudio", ["ELE", "ELETRODOMESTICOS"]),
    # Ferramentas e Construção
    ("FERRAMENTAS", "Ferramentas e Construção", ["FER"]),
    # Roupas, Calçados e Acessórios
    ("ROUPAS_CALCADOS", "Roupas, Calçados e Acessórios", ["VESTUARIO"]),
    # Outros: categorias de uso interno/sistema
    (
        "OUTROS",
        "Outros",
        [
            "CER", "CON", "ETI", "LAC", "MEC", "PEC", "QUI", "SEL",
            "INDUSTRIA_COMERCIO", "SAUDE_MEDICAMENTOS",
        ],
    ),
]

# Categorias a atualizar apenas o nome (já são principais)
ATUALIZAR_NOME = [
    ("BEBES", "Bebês"),
    ("COZINHA", "Cozinha"),
    ("ELETRONICOS", "Eletrônicos, TV e Áudio"),
    ("ESPORTES_FITNESS", "Esportes, Aventura e Lazer"),
    ("GAMES_CONSOLES", "Games e Consoles"),
    ("LIVROS_PAPELARIA", "Livros e Papelaria"),
    ("PET_SHOP", "Pet Shop"),
    ("INFORMATICA", "Computadores e Informática"),
]


def _get_id_by_codigo(conn, codigo: str) -> Optional[int]:
    r = conn.execute(sa.text("SELECT id FROM material_categoria WHERE codigo = :c"), {"c": codigo})
    row = r.fetchone()
    return row[0] if row else None


def _get_ids_by_codigos(conn, codigos: list[str]) -> list[int]:
    ids = []
    for c in codigos:
        r = conn.execute(sa.text("SELECT id FROM material_categoria WHERE codigo = :c"), {"c": c})
        row = r.fetchone()
        if row:
            ids.append(row[0])
    return ids


def upgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name

    for principal_codigo, principal_nome, remover_codigos in CONSOLIDACAO:
        principal_id = _get_id_by_codigo(conn, principal_codigo)
        remover_ids = _get_ids_by_codigos(conn, remover_codigos)

        if not remover_ids:
            continue

        # Criar principal se não existir
        if principal_id is None:
            if dialect == "postgresql":
                conn.execute(sa.text("""
                    INSERT INTO material_categoria (nome, codigo, ativo, controla_estoque, permite_negativo,
                        tem_validade, dias_alerta_vencimento, requer_aprovacao, incluir_relatorios, cor_relatorio)
                    VALUES (:nome, :codigo, true, true, false, false, 30, false, true, '#007bff')
                """), {"nome": principal_nome, "codigo": principal_codigo})
            else:
                conn.execute(sa.text("""
                    INSERT INTO material_categoria (nome, codigo, ativo, controla_estoque, permite_negativo,
                        tem_validade, dias_alerta_vencimento, requer_aprovacao, incluir_relatorios, cor_relatorio)
                    VALUES (:nome, :codigo, 1, 1, 0, 0, 30, 0, 1, '#007bff')
                """), {"nome": principal_nome, "codigo": principal_codigo})
            principal_id = _get_id_by_codigo(conn, principal_codigo)
            if principal_id is None:
                continue

        # Migrar produtos_cliente para a principal
        for rid in remover_ids:
            conn.execute(
                sa.text("UPDATE produtos_cliente SET categoria_id = :pid WHERE categoria_id = :rid"),
                {"pid": principal_id, "rid": rid},
            )

        # Remover categorias antigas
        for c in remover_codigos:
            conn.execute(sa.text("DELETE FROM material_categoria WHERE codigo = :c"), {"c": c})

    # Atualizar nomes das categorias principais
    for codigo, novo_nome in ATUALIZAR_NOME:
        conn.execute(
            sa.text("UPDATE material_categoria SET nome = :nome WHERE codigo = :codigo"),
            {"nome": novo_nome, "codigo": codigo},
        )


def downgrade() -> None:
    # Não é possível reverter a consolidação sem perda de informação
    # (produtos já foram migrados e categorias removidas)
    pass
