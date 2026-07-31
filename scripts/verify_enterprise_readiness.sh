#!/usr/bin/env bash
# Verifica prontidão enterprise (Fase 9): RLS, role DB, backup, pytest isolamento.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PY="${ROOT}/.venv/bin/python3"
FAIL=0

echo "== Enterprise readiness (Fase 9) =="

if [[ -x "$PY" ]]; then
  "$PY" scripts/verify_enterprise_readiness.py || FAIL=1
  "$PY" -m pytest tests/test_tenant_isolation.py tests/test_fase9_enterprise.py tests/test_fase78_governance.py -q --tb=line || FAIL=1
else
  echo "WARN: .venv não encontrado — pulando pytest"
fi

if [[ -x scripts/verify_rls_policies.py ]]; then
  "$PY" scripts/verify_rls_policies.py || FAIL=1
fi

if [[ -f scripts/backup_pdv_solumatica.sh ]]; then
  echo "OK: script backup presente (scripts/backup_pdv-solumatica.sh)"
else
  echo "WARN: script backup ausente"
fi

if [[ $FAIL -eq 0 ]]; then
  echo "== [OK] Prontidão enterprise verificada =="
else
  echo "== [FALHA] Corrija itens acima antes de ENTERPRISE_STRICT_STARTUP=true =="
  exit 1
fi
