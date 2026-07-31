#!/usr/bin/env bash
# Smoke de prontidão DR (Fase 9) — não restaura, apenas valida artefatos.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-/central_solumatica/Backup}"
OK=0

echo "== DR readiness =="

if [[ -f "$ROOT/scripts/backup_pdv-solumatica.sh" || -f "$ROOT/scripts/backup_pdv_solumatica.sh" ]]; then
  echo "OK: script de backup encontrado"
else
  echo "WARN: script backup não encontrado"
  OK=1
fi

if [[ -d "$BACKUP_DIR" ]]; then
  recent=$(find "$BACKUP_DIR" -maxdepth 2 -type f \( -name '*.sql' -o -name '*.dump' -o -name '*.gz' \) -mtime -2 2>/dev/null | head -1)
  if [[ -n "$recent" ]]; then
    echo "OK: backup recente (<48h): $recent"
  else
    echo "WARN: nenhum backup recente em $BACKUP_DIR"
    OK=1
  fi
else
  echo "WARN: diretório backup ausente: $BACKUP_DIR"
  OK=1
fi

if [[ -f "$ROOT/scripts/dr/runbook_dr.md" ]]; then
  echo "OK: runbook DR presente"
else
  echo "WARN: runbook ausente"
  OK=1
fi

exit $OK
