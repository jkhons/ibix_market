#!/usr/bin/env bash
# Instala units systemd do PDV (app, Celery, dependências Docker db/redis).
# Uso: sudo ./scripts/install_systemd.sh
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNIT_DIR="$ROOT_DIR/scripts/deploy/systemd"

for u in pdv_solumatica-docker-deps.service pdv_solumatica.service pdv_solumatica-celery.service; do
  install -m 0644 "$UNIT_DIR/$u" "/etc/systemd/system/$u"
done

systemctl daemon-reload
systemctl enable pdv_solumatica-docker-deps.service
systemctl enable pdv_solumatica.service
systemctl enable pdv_solumatica-celery.service

echo "Units instalados. Subir dependências e serviços:"
echo "  sudo systemctl start pdv_solumatica-docker-deps.service"
echo "  sudo systemctl restart pdv_solumatica.service pdv_solumatica-celery.service"
