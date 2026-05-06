#!/usr/bin/env bash
# Sincroniza mobile_marketplace/ com jkhons/IBIX_mobile (fonte canónica no GitHub).
# Pré-requisito: chave SSH desta máquina cadastrada em GitHub (Settings → SSH keys).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CLONE_DIR="${TMPDIR:-/tmp}/IBIX_mobile_sync_$$"
REMOTE_URL="${1:-git@github.com:jkhons/IBIX_mobile.git}"

cleanup() { rm -rf "$CLONE_DIR"; }
trap cleanup EXIT

echo ">> Clone shallow de ${REMOTE_URL}"
git clone --depth 1 --branch main "$REMOTE_URL" "$CLONE_DIR"

echo ">> rsync → ${REPO_ROOT}/mobile_marketplace/"
rsync -av --delete \
  --exclude node_modules \
  --exclude .expo \
  --exclude dist \
  --exclude android/build \
  --exclude ios/build \
  --exclude .git \
  "$CLONE_DIR/" "$REPO_ROOT/mobile_marketplace/"

echo ""
echo ">> Concluído. Revise alterações:"
echo "   cd \"$REPO_ROOT\" && git status"
echo ""
echo ">> Para gravar no Git do monorepo:"
echo "   git add mobile_marketplace && git commit -m \"sync: mobile_marketplace desde IBIX_mobile \$(date -I)\""
