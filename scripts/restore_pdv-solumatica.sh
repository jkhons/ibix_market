#!/bin/bash
# -*- coding: utf-8 -*-
#
# Script de Restore PDV SOLUMATICA (servidor de destino)
# Restaura backup gerado por backup_pdv-solumatica.sh.
# Alinhado ao DOCUMENTO_MIGRACAO_PDV.md: novo venv, .env a partir de .env.example, etc.
#
# Uso:
#   ./restore_pdv-solumatica.sh DIRETORIO_BACKUP [DESTINO_RESTAURACAO]
# Exemplos:
#   ./restore_pdv-solumatica.sh /caminho/backup_pdv-solumatica_20260226_120000 /opt
#   (restaura em /opt/; raiz da app será /opt/pdv_solumatica/)
#   Executando de dentro do backup: cd /caminho/backup_pdv-solumatica_XXX && ./pdv_solumatica/scripts/restore_pdv-solumatica.sh $(pwd) /opt
#
# Variáveis de ambiente (PostgreSQL do servidor de DESTINO, opcional):
#   DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# -----------------------------------------------------------------------------
# 1) Parâmetros e detecção do backup
# -----------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Diretório do backup (primeiro arg ou diretório onde está o script + backup mais recente)
BACKUP_DIR="${1:-}"
if [ -z "$BACKUP_DIR" ]; then
    BACKUP_BASE="$(cd "$SCRIPT_DIR/../.." && pwd)"
    if [ -d "$BACKUP_BASE/../Backup" ]; then
        LATEST=$(ls -1td "$BACKUP_BASE/../Backup"/backup_pdv-solumatica_* 2>/dev/null | head -n1)
        [ -n "$LATEST" ] && BACKUP_DIR="$LATEST"
    fi
    if [ -z "$BACKUP_DIR" ]; then
        log_error "Uso: $0 DIRETORIO_BACKUP [DESTINO_RESTAURACAO]"
        log_error "Ex.: $0 /caminho/backup_pdv-solumatica_YYYYMMDD_HHMMSS /opt"
        exit 1
    fi
    log_info "Usando backup mais recente: ${BACKUP_DIR}"
fi

if [ ! -d "$BACKUP_DIR" ]; then
    log_error "Diretório de backup não encontrado: ${BACKUP_DIR}"
    exit 1
fi

# Destino da restauração (parent do projeto; exemplo: /opt → app em /opt/pdv_solumatica/)
RESTORE_DEST="${2:-/opt}"
if [ ! -d "$RESTORE_DEST" ]; then
    log_info "Criando diretório de destino: ${RESTORE_DEST}"
    mkdir -p "$RESTORE_DEST"
fi
RESTORE_DEST="$(cd "$RESTORE_DEST" && pwd)"

# Nome do banco (padrão do backup)
DB_NAME="pdv_solumatica"
if [ -f "${BACKUP_DIR}/INFO.txt" ]; then
    _db_line=$(grep -E "^Banco:" "${BACKUP_DIR}/INFO.txt" 2>/dev/null | head -n1)
    [ -n "$_db_line" ] && DB_NAME="${_db_line#Banco: }" && DB_NAME="${DB_NAME// /}"
fi

# -----------------------------------------------------------------------------
# 2) Validar conteúdo do backup (alinhado ao que o backup cria)
# -----------------------------------------------------------------------------
validate_backup() {
    local ok=1
    if [ -f "${BACKUP_DIR}/${DB_NAME}.sql" ] && [ -s "${BACKUP_DIR}/${DB_NAME}.sql" ]; then
        log_info "   ✓ Dump PostgreSQL: ${BACKUP_DIR}/${DB_NAME}.sql"
    else
        log_error "   Dump do banco não encontrado ou vazio: ${BACKUP_DIR}/${DB_NAME}.sql"
        ok=0
    fi
    if [ -d "${BACKUP_DIR}/pdv_solumatica" ]; then
        if [ -f "${BACKUP_DIR}/pdv_solumatica/main.py" ] || [ -f "${BACKUP_DIR}/pdv_solumatica/pdv_solumatica/main.py" ]; then
            log_info "   ✓ Diretório do projeto (rsync): pdv_solumatica/"
        else
            log_error "   Estrutura do diretório do projeto inválida (esperado main.py em pdv_solumatica/ ou pdv_solumatica/pdv_solumatica/)"
            ok=0
        fi
    elif [ -f "${BACKUP_DIR}/pdv_solumatica.tar.gz" ] && [ -s "${BACKUP_DIR}/pdv_solumatica.tar.gz" ]; then
        log_info "   ✓ Arquivo do projeto: pdv_solumatica.tar.gz"
    else
        log_error "   Nem diretório pdv_solumatica/ nem pdv_solumatica.tar.gz encontrados no backup."
        ok=0
    fi
    [ $ok -eq 1 ]
}

log_info "Validando backup em: ${BACKUP_DIR}"
if ! validate_backup; then
    log_error "Backup inválido. Abortando."
    exit 1
fi

# -----------------------------------------------------------------------------
# 3) Restaurar arquivos do projeto
# -----------------------------------------------------------------------------
log_info "Restaurando arquivos do projeto em: ${RESTORE_DEST}"
if [ -d "${BACKUP_DIR}/pdv_solumatica" ]; then
    mkdir -p "${RESTORE_DEST}"
    rsync -a "${BACKUP_DIR}/pdv_solumatica/" "${RESTORE_DEST}/"
else
    mkdir -p "${RESTORE_DEST}"
    tar -xzf "${BACKUP_DIR}/pdv_solumatica.tar.gz" -C "${RESTORE_DEST}"
fi
# Estrutura do backup: main.py na raiz de pdv_solumatica/ (ou, em backups antigos, em pdv_solumatica/pdv_solumatica/)
APP_ROOT="${RESTORE_DEST}/pdv_solumatica"
if [ ! -f "${APP_ROOT}/main.py" ]; then
    if [ -f "${RESTORE_DEST}/pdv_solumatica/pdv_solumatica/main.py" ]; then
        APP_ROOT="${RESTORE_DEST}/pdv_solumatica/pdv_solumatica"
    else
        log_error "Raiz da aplicação não encontrada (main.py). Verifique: ${RESTORE_DEST}"
        exit 1
    fi
fi
log_info "Raiz da aplicação: ${APP_ROOT}"

# -----------------------------------------------------------------------------
# 4) PostgreSQL no servidor de DESTINO
# -----------------------------------------------------------------------------
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-postgres}"
DB_PASSWORD="${DB_PASSWORD:-}"

echo ""
log_info "Configuração do PostgreSQL no servidor de DESTINO (onde restaurar o dump)."
if [ -z "$DB_PASSWORD" ]; then
    read -s -p "Senha do usuário PostgreSQL ($DB_USER): " DB_PASSWORD
    echo ""
fi
if [ -z "$DB_PASSWORD" ]; then
    log_warn "Senha não informada. Tentando restaurar sem senha (somente se configurado no servidor)."
fi

export PGPASSWORD="$DB_PASSWORD"
# Criar banco se não existir (conectar em postgres ou template1)
log_info "Criando banco '${DB_NAME}' se não existir..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -v ON_ERROR_STOP=1 -c "SELECT 1 FROM pg_database WHERE datname = '${DB_NAME}'" -t | grep -q 1 || \
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE ${DB_NAME};"
unset PGPASSWORD

log_info "Restaurando dump em ${DB_NAME}..."
export PGPASSWORD="$DB_PASSWORD"
if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 -f "${BACKUP_DIR}/${DB_NAME}.sql"; then
    unset PGPASSWORD
    log_info "Dump restaurado com sucesso."
else
    unset PGPASSWORD
    log_error "Falha ao restaurar dump. Verifique credenciais e se o banco está acessível."
    exit 1
fi

# -----------------------------------------------------------------------------
# 5) Criar .env a partir de .env.example (backup não inclui .env)
# -----------------------------------------------------------------------------
ENV_EXAMPLE="${APP_ROOT}/.env.example"
ENV_FILE="${APP_ROOT}/.env"
if [ -f "$ENV_EXAMPLE" ]; then
    if [ -f "$ENV_FILE" ]; then
        log_warn "Arquivo .env já existe; não sobrescrevendo. Ajuste manualmente DB_*, REDIS_URL, APP_URL, etc."
    else
        cp "$ENV_EXAMPLE" "$ENV_FILE"
        log_info ".env criado a partir de .env.example em ${ENV_FILE}"
        # Ajustar valores padrão para o destino
        sed -i.bak "s|^DB_HOST=.*|DB_HOST=${DB_HOST}|" "$ENV_FILE" 2>/dev/null || true
        sed -i.bak "s|^DB_PORT=.*|DB_PORT=${DB_PORT}|" "$ENV_FILE" 2>/dev/null || true
        sed -i.bak "s|^DB_USER=.*|DB_USER=${DB_USER}|" "$ENV_FILE" 2>/dev/null || true
        sed -i.bak "s|^DB_NAME=.*|DB_NAME=${DB_NAME}|" "$ENV_FILE" 2>/dev/null || true
        [ -n "$DB_PASSWORD" ] && sed -i.bak "s|^DB_PASSWORD=.*|DB_PASSWORD=${DB_PASSWORD}|" "$ENV_FILE" 2>/dev/null || true
        rm -f "${ENV_FILE}.bak"
        log_warn "Revise e edite o .env (SECRET_KEY, APP_URL, REDIS_URL, MP_*, etc.) antes de subir a aplicação."
    fi
else
    log_warn ".env.example não encontrado. Crie manualmente o .env em ${APP_ROOT}/.env (ver DOCUMENTO_MIGRACAO_PDV.md)."
fi

# -----------------------------------------------------------------------------
# 6) Novo ambiente virtual (documento de migração: sempre criar novo)
# -----------------------------------------------------------------------------
log_info "Criando novo ambiente virtual em ${APP_ROOT}/.venv (conforme DOCUMENTO_MIGRACAO_PDV.md)..."
if [ -d "${APP_ROOT}/.venv" ]; then
    log_warn "Removendo .venv existente para criar um novo (recomendado no restore)."
    rm -rf "${APP_ROOT}/.venv"
fi
if ! command -v python3 &>/dev/null; then
    log_error "python3 não encontrado. Instale Python 3.10+ e execute novamente."
    exit 1
fi
python3 -m venv "${APP_ROOT}/.venv"
"${APP_ROOT}/.venv/bin/pip" install --upgrade pip -q
log_info "Instalando dependências de requirements.txt..."
if [ ! -f "${APP_ROOT}/requirements.txt" ]; then
    log_error "requirements.txt não encontrado em ${APP_ROOT}"
    exit 1
fi
"${APP_ROOT}/.venv/bin/pip" install -r "${APP_ROOT}/requirements.txt" -q
log_info "Ambiente virtual criado e dependências instaladas."

# -----------------------------------------------------------------------------
# 7) Alembic stamp head (schema já veio no dump)
# -----------------------------------------------------------------------------
log_info "Registrando schema no Alembic (stamp head)..."
(cd "${APP_ROOT}" && "${APP_ROOT}/.venv/bin/alembic" stamp head) || {
    log_warn "alembic stamp head falhou (pode ser normal se migrations divergirem). Verifique com: cd ${APP_ROOT} && .venv/bin/alembic current"
}

# -----------------------------------------------------------------------------
# 8) Atualizar paths nos arquivos systemd (opcional; caminho atual do servidor)
# -----------------------------------------------------------------------------
SYSTEMD_DIR="${APP_ROOT}/scripts/deploy/systemd"
for svc in pdv_solumatica.service pdv_solumatica-celery.service; do
    SVC_FILE="${SYSTEMD_DIR}/${svc}"
    if [ -f "$SVC_FILE" ]; then
        # Substituir path fixo antigo pelo APP_ROOT
        if grep -qE '/central_solumatica/pdv_solumatica' "$SVC_FILE" 2>/dev/null; then
            sed -i.bak "s|/central_solumatica/pdv_solumatica/pdv_solumatica|${APP_ROOT}|g" "$SVC_FILE"
            sed -i.bak "s|/central_solumatica/pdv_solumatica|${APP_ROOT}|g" "$SVC_FILE"
            rm -f "${SVC_FILE}.bak"
            log_info "Paths em ${svc} atualizados para ${APP_ROOT}"
        fi
    fi
done

# -----------------------------------------------------------------------------
# 9) Resumo e próximos passos (alinhado ao documento de migração)
# -----------------------------------------------------------------------------
echo ""
echo "=========================================="
echo "   Restore PDV SOLUMATICA concluído"
echo "=========================================="
echo ""
log_info "Raiz da aplicação: ${APP_ROOT}"
log_info "Banco restaurado: ${DB_NAME} em ${DB_HOST}:${DB_PORT}"
echo ""
log_info "Próximos passos (conforme DOCUMENTO_MIGRACAO_PDV.md):"
echo "  1. Editar .env em ${APP_ROOT}/.env (SECRET_KEY, APP_URL, REDIS_URL, MP_*, etc.)."
echo "  2. Garantir que PostgreSQL e Redis estão rodando no servidor."
echo "  3. Ajustar WorkingDirectory/EnvironmentFile nos .service se necessário:"
echo "     ${APP_ROOT}/scripts/deploy/systemd/"
echo "  4. Instalar serviços systemd: sudo bash ${APP_ROOT}/scripts/criar-units-no-sistema.sh"
echo "  5. Habilitar e iniciar: sudo systemctl enable --now pdv_solumatica pdv_solumatica-celery"
echo "  6. Para job diário de billing (03:00): subir Celery Beat (ver doc, seção 3.5)."
echo "  7. Configurar Nginx/SSL e apontar para a porta 8000."
echo ""
log_info "Teste rápido (com .env configurado e Redis rodando):"
echo "  cd ${APP_ROOT} && .venv/bin/python -c \"from app.database.connection import engine; from sqlalchemy import text; r=engine.connect().execute(text('SELECT 1')); print('DB OK:', r.scalar())\""
echo "  cd ${APP_ROOT} && .venv/bin/gunicorn main:app -w 1 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000"
echo ""
