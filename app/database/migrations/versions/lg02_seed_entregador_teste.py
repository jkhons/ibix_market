"""Seed: entregador de teste para logística local (módulo frete).

Insere um entregador apenas se ainda não existir nenhum.
Login: carlos.moto@teste.com / Senha: 123456

Revision ID: lg02_seed_entregador
Revises: merge_lg01_mc03
Create Date: 2026-03-10

"""
import sqlalchemy as sa
from alembic import op

revision = "lg02_seed_entregador"
down_revision = "merge_lg01_mc03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    # Só insere se a tabela estiver vazia
    r = conn.execute(sa.text("SELECT 1 FROM entregadores LIMIT 1"))
    if r.fetchone() is not None:
        return
    try:
        import bcrypt
        senha_hash = bcrypt.hashpw(b"123456", bcrypt.gensalt()).decode("utf-8")
    except ImportError:
        # Sem bcrypt: pule o seed; adicione o entregador manualmente ou instale bcrypt
        return

    conn.execute(
        sa.text("""
            INSERT INTO entregadores (
                nome, email, senha_hash, telefone, tipo_veiculo, ativo, status, cidade,
                created_at, updated_at
            ) VALUES (
                :nome, :email, :senha_hash, :telefone, :tipo_veiculo, true, 'ativo', :cidade,
                NOW(), NOW()
            )
        """),
        {
            "nome": "Carlos Moto",
            "email": "carlos.moto@teste.com",
            "senha_hash": senha_hash,
            "telefone": "14999999999",
            "tipo_veiculo": "moto",
            "cidade": "Barra Bonita",
        },
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM entregadores WHERE email = 'carlos.moto@teste.com'"))
