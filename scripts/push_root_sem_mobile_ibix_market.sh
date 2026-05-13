#!/usr/bin/env bash
# Espelha a raiz do PDV (tudo exceto mobile_marketplace/) → repositório ibix_market (commit + push).
# A VPS é tratada como fonte de conteúdo; o clone em /tmp recebe cópia filtrada.
#
# Não envia: mobile_marketplace/, .git, venvs, .env, uploads pesados, caches — alinhado ao .gitignore.
#
# Uso (na VPS):
#   cd /central_solumatica/pdv_solumatica
#   ./scripts/push_root_sem_mobile_ibix_market.sh
#
# Variáveis opcionais: IBIX_MARKET_SSH (default git@github.com:jkhons/ibix_market.git), IBIX_MARKET_PUSH_BRANCH (default main)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO_SSH="${IBIX_MARKET_SSH:-git@github.com:jkhons/ibix_market.git}"
BRANCH="${IBIX_MARKET_PUSH_BRANCH:-main}"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

git clone "$REPO_SSH" "$TMP/ibix_market"
git -C "$TMP/ibix_market" checkout "$BRANCH"

rsync -a --delete \
  --exclude '.git/' \
  --exclude 'mobile_marketplace/' \
  --exclude '.venv/' \
  --exclude 'venv/' \
  --exclude 'env/' \
  --exclude 'ENV/' \
  --exclude 'node_modules/' \
  --exclude '.env' \
  --exclude '.env.*' \
  --exclude '__pycache__/' \
  --exclude '.pytest_cache/' \
  --exclude 'htmlcov/' \
  --exclude '.cache/' \
  --exclude 'app/static/uploads/' \
  --exclude 'app/static/pdfs/' \
  --exclude 'app/static/certificados/' \
  --exclude 'uploads/' \
  --exclude 'certificados/' \
  --exclude 'comprovantes/' \
  --exclude 'relatorios/' \
  --exclude 'celerybeat-schedule' \
  --exclude 'celerybeat-schedule-shm' \
  --exclude 'celerybeat-schedule-wal' \
  --exclude 'celerybeat.pid' \
  --exclude 'client_secret*.json' \
  --exclude '.cursor/' \
  --exclude 'dist/' \
  --exclude '_builder/' \
  --exclude '*.log' \
  --exclude 'logs/' \
  --exclude '.DS_Store' \
  --exclude 'Thumbs.db' \
  "${ROOT}/" "$TMP/ibix_market/"

# Garantir que o repositório de destino não mantenha mobile/ antigo (rsync --exclude não remove sozinho).
rm -rf "$TMP/ibix_market/mobile_marketplace"

cd "$TMP/ibix_market"
git add -A
if git diff --cached --quiet; then
  echo "Nada a commitar (ibix_market já espelha a raiz sem mobile_marketplace/)."
  exit 0
fi

git commit -m "sync: raiz PDV sem mobile_marketplace ($(date -I))"
git push origin "$BRANCH"
echo "Push concluído para ibix_market ($BRANCH) — conteúdo sem pasta mobile_marketplace/."
