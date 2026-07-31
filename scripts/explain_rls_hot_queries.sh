#!/usr/bin/env bash
# EXPLAIN (ANALYZE, BUFFERS) de queries quentes pós-RLS — Fase 9 / P1-3
# Uso: ./scripts/explain_rls_hot_queries.sh [tenant_id] [brand_id]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-pdv_solumatica}"
DB_USER="${DB_USER:-pdv_app}"
export PGPASSWORD="${DB_PASSWORD:-}"

TENANT_ID="${1:-1}"
BRAND_ID="${2:-1}"

PSQL=(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1)

echo "=== RLS hot queries EXPLAIN (tenant_id=$TENANT_ID brand_id=$BRAND_ID user=$DB_USER) ==="

run_explain() {
  local title="$1"
  local sql="$2"
  echo ""
  echo "--- $title ---"
  "${PSQL[@]}" -c "BEGIN; SET LOCAL app.tenant_id = '$TENANT_ID'; SET LOCAL app.brand_id = '$BRAND_ID'; EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) $sql; ROLLBACK;"
}

run_explain "vendas por tenant" \
  "SELECT id, total FROM vendas WHERE tenant_id = $TENANT_ID ORDER BY id DESC LIMIT 50"

run_explain "pedidos marketplace por tenant" \
  "SELECT id, status FROM pedidos_marketplace WHERE tenant_id = $TENANT_ID ORDER BY id DESC LIMIT 50"

run_explain "usuarios do tenant" \
  "SELECT id, email FROM usuarios WHERE tenant_id = $TENANT_ID LIMIT 50"

run_explain "tenants por brand (rls_tenants_scope)" \
  "SELECT id, nome FROM tenants WHERE brand_id = $BRAND_ID LIMIT 50"

run_explain "produtos por tenant" \
  "SELECT id, nome FROM produtos WHERE tenant_id = $TENANT_ID LIMIT 50"

echo ""
echo "Concluído. Revise Seq Scan vs Index Scan e custo por nó."
