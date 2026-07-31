# Migração zero-downtime (expand-contract) — Fase 9

Checklist para migrações Alembic estruturais em produção:

1. **Expand** — adicionar coluna/tabela nullable; deploy código compatível com ambos estados
2. **Backfill** — job idempotente (batch + `WHERE col IS NULL LIMIT N`)
3. **Contract** — `NOT NULL`, FK `NOT VALID` + `VALIDATE CONSTRAINT` em janela separada
4. **Índices** — `CREATE INDEX CONCURRENTLY` (migration autocommit ou script SQL manual)
5. **RLS** — política após backfill completo; nunca antes de dados consistentes
6. **Rollback** — manter downgrade testado; backup pré-migração (`scripts/backup_pre_rls.sh`)

Nunca: `DELETE` destrutivo com FK ativa; lock longo em tabela quente sem `CONCURRENTLY`.
