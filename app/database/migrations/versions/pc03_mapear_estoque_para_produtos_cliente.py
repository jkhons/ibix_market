"""Mapear Estoque -> ProdutoCliente: tabela de mapeamento e script de dados.

Para cada linha em estoque: determina cliente_id (estoque.cliente_id ou empresa fiscal do CA),
insere em produtos_cliente (evitando duplicata por cliente_id+codigo) e guarda mapa estoque_id -> produto_cliente_id.

Revision ID: pc03_mapear
Revises: pc02_estender
Create Date: 2026-03-03

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision = "pc03_mapear"
down_revision = "pc02_estender"
branch_labels = None
depends_on = None


def _resolve_cliente_id(conn, cliente_id_val, usuario_id_cliente_admin):
    """Retorna cliente_id: estoque.cliente_id ou empresa fiscal do CA (areas_cliente)."""
    if cliente_id_val is not None:
        return cliente_id_val
    if usuario_id_cliente_admin is None:
        return None
    r = conn.execute(
        text(
            "SELECT cliente_id FROM areas_cliente "
            "WHERE usuario_id = :uid AND nome_area = 'administrador' AND ativo = true "
            "ORDER BY id DESC LIMIT 1"
        ),
        {"uid": usuario_id_cliente_admin},
    )
    row = r.fetchone()
    return row[0] if row else None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Criar tabela de mapeamento estoque_id -> produto_cliente_id
    op.create_table(
        "migracao_estoque_produto_cliente_map",
        sa.Column("estoque_id", sa.Integer(), primary_key=True),
        sa.Column("produto_cliente_id", sa.Integer(), sa.ForeignKey("produtos_cliente.id", ondelete="CASCADE"), nullable=False),
    )

    # 2. Buscar todos os estoques
    result = conn.execute(text("SELECT id, usuario_id_cliente_admin, cliente_id, codigo, nome, descricao, ncm, cfop_padrao, "
                               "unidade_medida, valor_custo, valor_venda, quantidade_atual, quantidade_minima, quantidade_maxima, "
                               "ativo, categoria, tipo_material, categoria_id, fabricante, fornecedor, data_validade, data_fabricacao, controla_estoque "
                               "FROM estoque"))
    rows = result.fetchall()

    for r in rows:
        estoque_id = r[0]
        cliente_id = _resolve_cliente_id(conn, r[2], r[1])  # r[2]=cliente_id, r[1]=usuario_id_cliente_admin
        if cliente_id is None:
            continue
        codigo = r[3] or ""
        nome = r[4] or ""
        descricao = r[5]
        ncm = r[6]
        cfop_padrao = r[7]
        unidade_medida = r[8] or "UN"
        valor_custo = r[9]
        valor_venda = r[10]
        quantidade_atual = r[11] or 0
        quantidade_minima = r[12]
        quantidade_maxima = r[13]
        ativo = r[14] if r[14] is not None else True
        categoria = r[15]
        tipo_material = r[16]
        if tipo_material is not None and hasattr(tipo_material, "value"):
            tipo_material = tipo_material.value
        categoria_id = r[17]
        fabricante = r[18]
        fornecedor = r[19]
        data_validade = r[20]
        data_fabricacao = r[21]
        controla_estoque = r[22] if r[22] is not None else True

        # Verificar se já existe produto_cliente com (cliente_id, codigo)
        sel = conn.execute(
            text("SELECT id FROM produtos_cliente WHERE cliente_id = :cid AND codigo = :cod"),
            {"cid": cliente_id, "cod": codigo},
        )
        existing = sel.fetchone()
        if existing:
            produto_cliente_id = existing[0]
        else:
            conn.execute(
                text(
                    "INSERT INTO produtos_cliente (cliente_id, codigo, nome, descricao, ncm, cfop_padrao, unidade_medida, "
                    "valor_custo, valor_venda, quantidade_atual, quantidade_minima, quantidade_maxima, ativo, "
                    "categoria, tipo_material, categoria_id, fabricante, fornecedor, data_validade, data_fabricacao, controla_estoque) "
                    "VALUES (:cid, :cod, :nome, :desc, :ncm, :cfop, :um, :vc, :vv, :qa, :qm, :qmax, :ativo, "
                    ":cat, :tm, :catid, :fab, :forn, :dv, :df, :ce)"
                ),
                {
                    "cid": cliente_id, "cod": codigo, "nome": nome, "desc": descricao, "ncm": ncm, "cfop": cfop_padrao,
                    "um": unidade_medida, "vc": valor_custo, "vv": valor_venda, "qa": quantidade_atual, "qm": quantidade_minima,
                    "qmax": quantidade_maxima, "ativo": ativo, "cat": categoria, "tm": tipo_material, "catid": categoria_id,
                    "fab": fabricante, "forn": fornecedor, "dv": data_validade, "df": data_fabricacao, "ce": controla_estoque,
                },
            )
            sel2 = conn.execute(text("SELECT id FROM produtos_cliente WHERE cliente_id = :cid AND codigo = :cod"), {"cid": cliente_id, "cod": codigo})
            produto_cliente_id = sel2.fetchone()[0]

        conn.execute(
            text("INSERT INTO migracao_estoque_produto_cliente_map (estoque_id, produto_cliente_id) VALUES (:eid, :pcid)"),
            {"eid": estoque_id, "pcid": produto_cliente_id},
        )


def downgrade() -> None:
    op.drop_table("migracao_estoque_produto_cliente_map")
