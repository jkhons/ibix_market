#!/usr/bin/env bash
# Backup obrigatório antes de aplicar br35 (RLS) — Fase 6
# Uso: ./scripts/backup_pre_rls.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date +%Y%m%d_%H%M%S)"
DEST="${BACKUP_DEST:-/central_solumatica/backup/pre_rls_${STAMP}}"

echo "=== Backup pré-RLS (Fase 6) ==="
echo "Destino: ${DEST}"
mkdir -p "${DEST}"

if [[ -x "${ROOT}/scripts/backup_pdv_solumatica.sh" ]]; then
  BACKUP_BASE_DIR="${DEST}" MAX_BACKUPS=999 SOURCE_DIR="${ROOT}" \
    bash -c 'echo "pre-RLS br35" | '"${ROOT}/scripts/backup_pdv_solumatica.sh" || true
fi

# Dump dedicado com formato custom (restauração rápida)
ENV_FILE="${ROOT}/.env"
if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source <(grep -E '^[A-Z_]+=' "${ENV_FILE}" | sed 's/\r$//')
  set +a
fi

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-postgres}"
DB_NAME="${DB_NAME:-pdv_solumatica}"

if command -v pg_dump >/dev/null 2>&1 && [[ -n "${DB_PASSWORD:-}" ]]; then
  export PGPASSWORD="${DB_PASSWORD}"
  pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
    -Fc -f "${DEST}/${DB_NAME}_pre_rls.dump"
  pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
    --schema-only -f "${DEST}/${DB_NAME}_schema_pre_rls.sql"
  unset PGPASSWORD
  echo "Dump custom: ${DEST}/${DB_NAME}_pre_rls.dump"
fi

cat > "${DEST}/CHECKLIST_PRE_RLS.txt" <<'EOF'
Checklist pré-RLS (Fase 6)
==========================
[ ] Backup completo verificado (pg_restore --list ou psql -f schema)
[ ] WAL archiving / PITR configurado no PostgreSQL (se produção)
[ ] scripts/audit_multibrand_pre_migration.py sem ERRO
[ ] Alembic: alembic upgrade br35_rls_policies
[ ] .env: RLS_ENABLED=true
[ ] Reiniciar pdv_solumatica + celery
[ ] Smoke: login CA Ibix + Solumática; Superadmin dashboard
[ ] scripts/verify_rls_policies.py
EOF

echo "Checklist: ${DEST}/CHECKLIST_PRE_RLS.txt"
echo "Concluído."
