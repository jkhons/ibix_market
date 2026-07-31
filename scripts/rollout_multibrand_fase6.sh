#!/usr/bin/env bash
# Rollout faseado multi-brand Ibix → Solumática (Fase 6)
# Uso: ./scripts/rollout_multibrand_fase6.sh [check|ibix|solumatica|rls-on]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

step="${1:-check}"

run_audit() {
  echo ">> Auditoria multi-brand..."
  ./.venv/bin/python scripts/audit_multibrand_pre_migration.py
}

run_migrate() {
  echo ">> Alembic upgrade head..."
  ./.venv/bin/alembic upgrade head
}

case "${step}" in
  check)
    run_audit
    ./.venv/bin/python scripts/verify_rls_policies.py || echo "(RLS ainda não aplicado — esperado antes de br35)"
    echo "OK: check concluído."
    ;;
  ibix)
    echo ">> Fase Ibix: sem mudança visível; validar health e login www.ibix.com.br"
    curl -sf "http://127.0.0.1:8000/api/health" >/dev/null && echo "Health OK" || echo "Health FAIL"
    ;;
  solumatica)
    echo ">> Fase Solumática: ativar Nginx solumatica-brand.conf + Certbot multibrand"
    echo "   Ver scripts/deploy/nginx/solumatica-brand.conf"
    echo "   CORS_ORIGINS deve incluir domínios Solumática"
    ;;
  rls-on)
    echo ">> Ativar RLS na aplicação"
    if grep -q '^RLS_ENABLED=' .env 2>/dev/null; then
      sed -i 's/^RLS_ENABLED=.*/RLS_ENABLED=true/' .env
    else
      echo 'RLS_ENABLED=true' >> .env
    fi
    echo "RLS_ENABLED=true em .env — reinicie pdv_solumatica e celery."
    run_migrate
    ./.venv/bin/python scripts/verify_rls_policies.py
    ;;
  *)
    echo "Uso: $0 [check|ibix|solumatica|rls-on]" >&2
    exit 1
    ;;
esac
