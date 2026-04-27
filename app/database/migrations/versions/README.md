# Migrações Alembic (PostgreSQL)

O schema do banco é criado por `scripts/create_all_pg.py` (SQLAlchemy `Base.metadata.create_all()`).

Para **novas alterações de schema** (colunas, índices, tabelas), use:

```bash
# Gerar nova migração
alembic revision -m "descricao_da_alteracao"

# Editar o arquivo gerado e executar
alembic upgrade head
```
