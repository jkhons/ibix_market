#!/usr/bin/env bash
# Trazer conteúdo de IBIX_mobile (GitHub) para mobile_marketplace/ no monorepo.
# Pré-requisito: SSH para git@github.com:jkhons/IBIX_mobile.git (deploy key ou ssh-agent).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MOB="${ROOT}/mobile_marketplace"
REPO_SSH="${IBIX_MOBILE_SSH:-git@github.com:jkhons/IBIX_mobile.git}"
BRANCH="${IBIX_MOBILE_BRANCH:-main}"

ENV_BKP="$(mktemp)"
cleanup() { rm -f "$ENV_BKP"; }
trap cleanup EXIT

if [[ -f "${MOB}/.env" ]]; then
  cp -a "${MOB}/.env" "$ENV_BKP"
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

git clone --depth 1 -b "$BRANCH" "$REPO_SSH" "$TMP/IBIX_mobile"
HASH="$(git -C "$TMP/IBIX_mobile" rev-parse HEAD)"

rsync -a --delete --exclude '.env' "$TMP/IBIX_mobile/" "$MOB/"
if [[ -s "$ENV_BKP" ]]; then
  cp -a "$ENV_BKP" "${MOB}/.env"
fi

echo "Sincronizado com IBIX_mobile @ ${HASH}"
(cd "$MOB" && npm ci && npm run typecheck)
echo "OK — revise git diff em mobile_marketplace/ e faça commit no monorepo."
