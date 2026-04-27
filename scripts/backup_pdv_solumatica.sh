#!/bin/bash
# -*- coding: utf-8 -*-
#
# Script de Backup PDV Solumatica
# Sistema PDV (Ponto de Venda) Solumatica
#
# Este script realiza backup do diretório /central_solumatica/pdv_solumatica
# e do banco de dados (PostgreSQL)
#
# Mantém apenas os 20 backups mais recentes

set -e  # Sair em caso de erro

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configurações
SOURCE_DIR="/central_solumatica/pdv_solumatica"
BACKUP_BASE_DIR="/central_solumatica/backup"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="${BACKUP_BASE_DIR}/backup_pdv_solumatica_${TIMESTAMP}"

# Número de backups a manter
MAX_BACKUPS=20

# Função para imprimir mensagens
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configurações do Banco de Dados
# Tenta ler do arquivo .env primeiro, depois usa valores padrão
ENV_FILE="${SOURCE_DIR}/.env"

# Função para carregar variáveis de ambiente do .env
load_env_file() {
    if [ -f "${ENV_FILE}" ]; then
        log_info "Carregando configurações do arquivo .env..."
        # Processar linha por linha para ter melhor controle
        while IFS= read -r line || [ -n "$line" ]; do
            # Ignorar comentários e linhas vazias
            [[ "$line" =~ ^[[:space:]]*# ]] && continue
            [[ -z "${line// }" ]] && continue

            # Processar apenas linhas que contêm =
            if [[ "$line" =~ ^[[:space:]]*([^=]+)=(.*)$ ]]; then
                local key="${BASH_REMATCH[1]}"
                local value="${BASH_REMATCH[2]}"

                # Remover espaços em branco do início e fim da chave
                key="${key#"${key%%[![:space:]]*}"}"
                key="${key%"${key##*[![:space:]]}"}"

                # Processar o valor (pode ter aspas ou não)
                # Remover espaços no início
                value="${value#"${value%%[![:space:]]*}"}"
                # Remover aspas se presentes
                if [[ "$value" =~ ^\".*\"$ ]] || [[ "$value" =~ ^\'.*\'$ ]]; then
                    value="${value:1:-1}"
                fi
                # Remover espaços no final
                value="${value%"${value##*[![:space:]]}"}"

                # Exportar variável de forma segura
                # Usar printf %q para escapar caracteres especiais corretamente
                local escaped_value=$(printf '%q' "$value")
                eval "export ${key}=${escaped_value}"
            fi
        done < "${ENV_FILE}"
    else
        log_warn "Arquivo .env não encontrado em: ${ENV_FILE}"
    fi
}

# Carregar .env se existir (deve ser chamado antes de definir as variáveis)
load_env_file

# Configurações do Banco de Dados (PostgreSQL)
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-postgres}"
DB_PASSWORD="${DB_PASSWORD:-}"
DB_NAME="${DB_NAME:-pdv_solumatica}"

# Debug: mostrar se as variáveis foram carregadas (sem mostrar a senha)
if [ -f "${ENV_FILE}" ]; then
    log_info "Variáveis carregadas do .env:"
    log_info "   DB_HOST=${DB_HOST}"
    log_info "   DB_PORT=${DB_PORT}"
    log_info "   DB_USER=${DB_USER}"
    log_info "   DB_NAME=${DB_NAME}"
    log_info "   DB_PASSWORD=$([ -n "${DB_PASSWORD}" ] && echo "[definida - ${#DB_PASSWORD} caracteres]" || echo "[não definida]")"
fi

# Verificar se a senha foi fornecida
if [ -z "$DB_PASSWORD" ]; then
    echo ""
    log_warn "Senha do banco de dados não encontrada nas variáveis de ambiente."
    log_warn "Por favor, forneça a senha do PostgreSQL:"
    read -s -p "Senha PostgreSQL: " DB_PASSWORD
    echo ""
    if [ -z "$DB_PASSWORD" ]; then
        log_error "Senha do banco de dados é obrigatória."
        exit 1
    fi
fi

# Função para mostrar resumo das configurações
show_config_summary() {
    log_info "Configurações do backup:"
    log_info "   Banco: PostgreSQL"
    log_info "   Diretório fonte: ${SOURCE_DIR}"
    log_info "   Diretório de backup: ${BACKUP_DIR}"
    log_info "   Banco de dados: ${DB_NAME}"
    log_info "   Host: ${DB_HOST}"
    log_info "   Porta: ${DB_PORT}"
    log_info "   Usuário: ${DB_USER}"
    log_info "   Senha: [${#DB_PASSWORD} caracteres]"
    echo ""
}

# Função para verificar dependências
check_dependencies() {
    local missing_deps=()
    if ! command -v pg_dump &> /dev/null; then
        missing_deps+=("pg_dump")
    fi
    if [ ${#missing_deps[@]} -ne 0 ]; then
        log_error "Dependências faltando: ${missing_deps[*]}"
        log_error "No Ubuntu/Debian: sudo apt-get install postgresql-client"
        exit 1
    fi
    if ! command -v tar &> /dev/null && ! command -v rsync &> /dev/null; then
        missing_deps+=("tar ou rsync")
    fi
    if [ ${#missing_deps[@]} -ne 0 ]; then
        log_error "Dependências faltando: ${missing_deps[*]}"
        exit 1
    fi
}

# Função para perguntar motivo do backup
ask_backup_reason() {
    echo ""
    log_info "Por favor, informe o motivo/descrição deste backup:"
    read -p "Descrição: " BACKUP_REASON

    if [ -z "$BACKUP_REASON" ]; then
        log_warn "Nenhuma descrição informada. Usando 'Backup manual' como padrão."
        BACKUP_REASON="Backup manual"
    fi
}

# Função para criar diretório de backup
create_backup_directory() {
    log_info "Criando diretório de backup: ${BACKUP_DIR}"
    mkdir -p "${BACKUP_DIR}"

    if [ ! -d "${BACKUP_DIR}" ]; then
        log_error "Falha ao criar diretório de backup: ${BACKUP_DIR}"
        exit 1
    fi
}

# Função para fazer backup do diretório
backup_directory() {
    log_info "Iniciando backup do diretório: ${SOURCE_DIR}"

    if [ ! -d "${SOURCE_DIR}" ]; then
        log_error "Diretório fonte não encontrado: ${SOURCE_DIR}"
        exit 1
    fi

    # Usar rsync se disponível (mais eficiente), caso contrário usar tar
    if command -v rsync &> /dev/null; then
        log_info "Usando rsync para backup do diretório..."
        rsync -av --progress \
            --exclude='.venv/' \
            --exclude='venv/' \
            --exclude='venv.bak/' \
            --exclude='env/' \
            --exclude='env.bak/' \
            --exclude='ENV/' \
            --exclude='__pycache__/' \
            --exclude='*.pyc' \
            --exclude='.git/' \
            --exclude='.cursor/' \
            --exclude='*.log' \
            --exclude='*.sqlite' \
            --exclude='.env' \
            --exclude='node_modules/' \
            --exclude='.pytest_cache/' \
            --exclude='htmlcov/' \
            --exclude='.coverage' \
            "${SOURCE_DIR}/" "${BACKUP_DIR}/pdv_solumatica/"
    else
        log_info "Usando tar para backup do diretório..."
        cd "$(dirname "${SOURCE_DIR}")"
        tar -czf "${BACKUP_DIR}/pdv_solumatica.tar.gz" \
            --exclude='.venv' \
            --exclude='venv' \
            --exclude='venv.bak' \
            --exclude='env' \
            --exclude='env.bak' \
            --exclude='ENV' \
            --exclude='__pycache__' \
            --exclude='*.pyc' \
            --exclude='.git' \
            --exclude='.cursor' \
            --exclude='*.log' \
            --exclude='*.sqlite' \
            --exclude='.env' \
            --exclude='node_modules' \
            --exclude='.pytest_cache' \
            --exclude='htmlcov' \
            --exclude='.coverage' \
            "$(basename "${SOURCE_DIR}")"
    fi

    log_info "Backup do diretório concluído."
}

# Função para testar conexão com o banco de dados
test_database_connection() {
    log_info "Testando conexão com o banco de dados (PostgreSQL)..."
    if [ -z "${DB_PASSWORD}" ]; then
        log_error "Senha do banco de dados não está definida."
        return 1
    fi
    export PGPASSWORD="${DB_PASSWORD}"
    local error_output=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -c "SELECT 1;" 2>&1)
    local exit_code=$?
    unset PGPASSWORD
    if [ $exit_code -ne 0 ]; then
        log_error "Falha ao conectar ao PostgreSQL."
        echo "$error_output" | while IFS= read -r line; do [ -n "$line" ] && log_error "   $line"; done
        log_error "Configurações: Host=${DB_HOST} Porta=${DB_PORT} User=${DB_USER} DB=${DB_NAME}"
        log_error "Dica: psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME}"
        return 1
    fi
    log_info "Conexão com o banco de dados estabelecida com sucesso."
    return 0
}

# Função para fazer backup do banco de dados
backup_database() {
    log_info "Iniciando backup do banco de dados (PostgreSQL): ${DB_NAME}"
    if ! test_database_connection; then
        log_error "Não foi possível conectar ao banco de dados. Abortando backup."
        rm -rf "${BACKUP_DIR}"
        exit 1
    fi
    local db_backup_file="${BACKUP_DIR}/${DB_NAME}.sql"
    local error_log="${BACKUP_DIR}/db_error.log"
    export PGPASSWORD="${DB_PASSWORD}"
    if pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
        --no-owner --no-acl -f "${db_backup_file}" 2>"${error_log}"; then
        unset PGPASSWORD
        rm -f "${error_log}"
        if [ ! -s "${db_backup_file}" ]; then
            log_error "Arquivo de backup do banco está vazio."
            rm -rf "${BACKUP_DIR}"
            exit 1
        fi
        log_info "Backup do banco de dados concluído: ${db_backup_file}"
    else
        unset PGPASSWORD
        log_error "Falha ao fazer backup do PostgreSQL."
        [ -s "${error_log}" ] && cat "${error_log}" | while IFS= read -r line; do log_error "   $line"; done
        log_error "Verifique: credenciais, banco ${DB_NAME}, PostgreSQL em ${DB_HOST}:${DB_PORT}"
        rm -f "${error_log}"
        rm -rf "${BACKUP_DIR}"
        exit 1
    fi
}

# Função para criar arquivo INFO.txt
create_info_file() {
    log_info "Criando arquivo de informações do backup..."

    local info_file="${BACKUP_DIR}/INFO.txt"
    local backup_size=$(du -sh "${BACKUP_DIR}" | cut -f1)
    local date_time=$(date +"%Y-%m-%d %H:%M:%S")

    # Detectar formato do backup
    local backup_format="rsync"
    if [ -f "${BACKUP_DIR}/pdv_solumatica.tar.gz" ]; then
        backup_format="tar"
    fi

    # Verificar se diretório foi copiado
    local dir_ok="OK"
    if [ "$backup_format" = "rsync" ] && [ ! -d "${BACKUP_DIR}/pdv_solumatica" ]; then
        dir_ok="FALHA"
    elif [ "$backup_format" = "tar" ] && [ ! -f "${BACKUP_DIR}/pdv_solumatica.tar.gz" ]; then
        dir_ok="FALHA"
    fi

    # Verificar se banco foi copiado
    local db_ok="OK"
    if [ ! -f "${BACKUP_DIR}/${DB_NAME}.sql" ] || [ ! -s "${BACKUP_DIR}/${DB_NAME}.sql" ]; then
        db_ok="FALHA"
    fi

    cat > "${info_file}" << EOF
Backup PDV Solumatica
=====================
Data/Hora: ${date_time}
Descrição: ${BACKUP_REASON}
Tamanho: ${backup_size}
Diretório: ${SOURCE_DIR}
Banco: ${DB_NAME}
Host: ${DB_HOST}
Porta: ${DB_PORT}
Timestamp: ${TIMESTAMP}
Formato: ${backup_format}
Status Diretório: ${dir_ok}
Status Banco: ${db_ok}
EOF

    log_info "Arquivo de informações criado: ${info_file}"
}

# Função para validar integridade do backup
validate_backup() {
    log_info "Validando integridade do backup..."

    local validation_errors=()

    # Verificar se diretório foi copiado
    if [ -d "${BACKUP_DIR}/pdv_solumatica" ]; then
        local file_count=$(find "${BACKUP_DIR}/pdv_solumatica" -type f | wc -l)
        if [ "$file_count" -eq 0 ]; then
            validation_errors+=("Diretório restaurado está vazio")
        else
            log_info "   ✓ Diretório: OK ($file_count arquivos)"
        fi
    elif [ -f "${BACKUP_DIR}/pdv_solumatica.tar.gz" ]; then
        if [ ! -s "${BACKUP_DIR}/pdv_solumatica.tar.gz" ]; then
            validation_errors+=("Arquivo tar.gz está vazio")
        else
            log_info "   ✓ Arquivo tar.gz: OK"
        fi
    else
        validation_errors+=("Backup do diretório não encontrado")
    fi

    # Verificar se banco foi copiado
    if [ ! -f "${BACKUP_DIR}/${DB_NAME}.sql" ]; then
        validation_errors+=("Backup do banco de dados não encontrado")
    elif [ ! -s "${BACKUP_DIR}/${DB_NAME}.sql" ]; then
        validation_errors+=("Backup do banco de dados está vazio")
    else
        log_info "   ✓ Banco de dados: OK"
    fi

    # Verificar se INFO.txt existe
    if [ ! -f "${BACKUP_DIR}/INFO.txt" ]; then
        validation_errors+=("Arquivo INFO.txt não encontrado")
    else
        log_info "   ✓ INFO.txt: OK"
    fi

    if [ ${#validation_errors[@]} -ne 0 ]; then
        log_error "Falhas na validação do backup:"
        for error in "${validation_errors[@]}"; do
            log_error "   - $error"
        done
        return 1
    fi

    log_info "Validação do backup concluída com sucesso."
    return 0
}

# Função para limpar backups antigos (manter apenas os 20 mais recentes)
cleanup_old_backups() {
    log_info "Verificando backups antigos..."

    if [ ! -d "${BACKUP_BASE_DIR}" ]; then
        return
    fi

    # Listar todos os diretórios de backup, ordenar por data (mais recente primeiro)
    # e pegar apenas os que excedem MAX_BACKUPS
    local old_backups=$(ls -1td "${BACKUP_BASE_DIR}"/backup_pdv_solumatica_* 2>/dev/null | tail -n +$((MAX_BACKUPS + 1)))

    if [ -z "$old_backups" ]; then
        log_info "Nenhum backup antigo para remover."
        return
    fi

    log_info "Removendo backups antigos (mantendo apenas os ${MAX_BACKUPS} mais recentes)..."

    while IFS= read -r old_backup; do
        if [ -d "$old_backup" ]; then
            log_info "Removendo backup antigo: $(basename "$old_backup")"
            rm -rf "$old_backup"
        fi
    done <<< "$old_backups"

    log_info "Limpeza de backups antigos concluída."
}

# Função principal
main() {
    echo ""
    echo "=========================================="
    echo "   Script de Backup PDV Solumatica"
    echo "=========================================="
    echo ""

    # Verificar dependências
    check_dependencies

    # Mostrar resumo das configurações
    show_config_summary

    # Perguntar motivo do backup
    ask_backup_reason

    # Criar diretório de backup
    create_backup_directory

    # Fazer backup do diretório
    backup_directory

    # Fazer backup do banco de dados
    backup_database

    # Criar arquivo de informações
    create_info_file

    # Validar integridade do backup
    if ! validate_backup; then
        log_error "Backup concluído mas com falhas na validação."
        log_error "Verifique os erros acima antes de confiar neste backup."
        exit 1
    fi

    # Limpar backups antigos
    cleanup_old_backups

    echo ""
    log_info "Backup concluído com sucesso!"
    log_info "Localização: ${BACKUP_DIR}"
    echo ""

    # Listar backups disponíveis
    log_info "Backups disponíveis (últimos ${MAX_BACKUPS}):"
    ls -1td "${BACKUP_BASE_DIR}"/backup_pdv_solumatica_* 2>/dev/null | head -n ${MAX_BACKUPS} | while read backup; do
        if [ -d "$backup" ]; then
            local size=$(du -sh "$backup" 2>/dev/null | cut -f1)
            echo "  - $(basename "$backup") (${size})"
        fi
    done
    echo ""
}

# Executar função principal
main
