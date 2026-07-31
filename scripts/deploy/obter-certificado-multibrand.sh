#!/usr/bin/env bash
# Certbot multi-domínio — Ibix + Solumática (Fase 5 hardening TLS)
# Uso: sudo ./scripts/deploy/obter-certificado-multibrand.sh
set -euo pipefail

WEBROOT="${WEBROOT:-/var/www/letsencrypt}"
EMAIL="${CERTBOT_EMAIL:-}"

DOMAINS=(
  "www.ibix.com.br"
  "ibix.com.br"
  "www.solumatica.com.br"
  "solumatica.com.br"
  "auto.solumatica.com.br"
)

if [[ $EUID -ne 0 ]]; then
  echo "Execute como root (sudo)." >&2
  exit 1
fi

mkdir -p "$WEBROOT"

domain_args=()
for d in "${DOMAINS[@]}"; do
  domain_args+=(-d "$d")
done

if [[ -z "$EMAIL" ]]; then
  echo "Defina CERTBOT_EMAIL=admin@exemplo.com.br" >&2
  exit 1
fi

certbot certonly --webroot -w "$WEBROOT" \
  "${domain_args[@]}" \
  --email "$EMAIL" \
  --agree-tos \
  --non-interactive \
  --expand

echo "Certificados emitidos. Atualize scripts/deploy/nginx/solumatica-brand.conf e recarregue o Nginx."
