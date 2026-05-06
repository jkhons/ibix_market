#!/usr/bin/env bash
# Espelhar mobile_marketplace/ → repositório IBIX_mobile (commit + push).
# Pré-requisito: SSH com permissão de escrita em git@github.com:jkhons/IBIX_mobile.git
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MOB="${ROOT}/mobile_marketplace"
REPO_SSH="${IBIX_MOBILE_SSH:-git@github.com:jkhons/IBIX_mobile.git}"
BRANCH="${IBIX_MOBILE_PUSH_BRANCH:-main}"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

git clone "$REPO_SSH" "$TMP/IBIX_mobile"
git -C "$TMP/IBIX_mobile" checkout "$BRANCH"

rsync -a --delete \
  --exclude '.git' \
  --exclude '.env' \
  --exclude 'node_modules' \
  "${MOB}/" "$TMP/IBIX_mobile/"

cd "$TMP/IBIX_mobile"
git add -A
if git diff --cached --quiet; then
  echo "Nada a commitar (IBIX_mobile já igual ao mobile_marketplace/)."
  exit 0
fi

git commit -m "sync: espelha mobile_marketplace do monorepo ($(date -I))"
git push origin "$BRANCH"
echo "Push concluído para IBIX_mobile ($BRANCH)."
