#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDV Ibix - Sistema de Logging e Monitoramento
Configuração centralizada de logs para o sistema
"""

import logging
import logging.handlers
import os
import re
from pathlib import Path
from typing import Any, List, Optional

# Redação de tokens em logs (evita expor JWT em access log e syslog)
_TOKEN_REDACT_PATTERN = re.compile(
    r"token=eyJ[^&\s\"]+",
    re.IGNORECASE
)


class RedactTokenFilter(logging.Filter):
    """Filtro que redige parâmetro token (JWT) em mensagens de log."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
            if "token=" in msg:
                record.msg = _TOKEN_REDACT_PATTERN.sub("token=***", msg)
                record.args = ()
        except Exception:
            pass
        return True


class SkipNotificacoesAccessFilter(logging.Filter):
    """Suprime linhas de access log para /api/v1/notificacoes (polling frequente, evita ruído)."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
            if "/api/v1/notificacoes" in msg:
                return False
        except Exception:
            pass
        return True


def install_redact_token_filter() -> None:
    """Instala filtros nos loggers de access (uvicorn/gunicorn): redação de JWT e supressão de /api/v1/notificacoes."""
    for logger_name in ("uvicorn.access", "gunicorn.access"):
        access_logger = logging.getLogger(logger_name)
        for h in access_logger.handlers:
            if not any(isinstance(f, RedactTokenFilter) for f in h.filters):
                h.addFilter(RedactTokenFilter())
            if not any(isinstance(f, SkipNotificacoesAccessFilter) for f in h.filters):
                h.addFilter(SkipNotificacoesAccessFilter())
        if not any(isinstance(f, RedactTokenFilter) for f in access_logger.filters):
            access_logger.addFilter(RedactTokenFilter())
        if not any(isinstance(f, SkipNotificacoesAccessFilter) for f in access_logger.filters):
            access_logger.addFilter(SkipNotificacoesAccessFilter())

# Formato estruturado para correlação (request_id, tenant_id, user_id) — confirmação de impl.
def _structured_prefix(request_id: Optional[str] = None, tenant_id: Optional[str] = None, user_id: Optional[str] = None, **extra: Any) -> str:
    """Monta prefixo key=value para logs estruturados (Loki/ELK-friendly)."""
    parts: List[str] = []
    if request_id:
        parts.append(f"request_id={request_id}")
    if tenant_id:
        parts.append(f"tenant_id={tenant_id}")
    if user_id:
        parts.append(f"user_id={user_id}")
    for k, v in extra.items():
        if v is not None:
            parts.append(f"{k}={v}")
    return " ".join(parts) + " " if parts else ""


class PdvIbixLogger:
    """Sistema de logging centralizado para o PDV Ibix"""

    def __init__(self, name: str = "pdv_solumatica"):
        self.name = name
        self.logger = None
        self.setup_logging()
    
    def _get_log_dir(self) -> Optional[Path]:
        """Retorna diretório de logs (LOG_DIR ou projeto/logs). None se não for possível criar."""
        log_dir = os.getenv("LOG_DIR", "").strip()
        if log_dir:
            log_dir = Path(log_dir)
        else:
            log_dir = Path(__file__).resolve().parent.parent.parent / "logs"
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            return log_dir
        except OSError:
            return None

    def setup_logging(self):
        """Configura o sistema de logging"""
        # Obter nível de log do ambiente
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        debug_mode = os.getenv('DEBUG', 'False').lower() == 'true'
        
        # Definir nível baseado em ambiente
        if debug_mode:
            pass
        else:
            getattr(logging, log_level, logging.INFO)
        
        log_dir = self._get_log_dir()
        self._log_dir = log_dir  # para setup_database_logging()
        if log_dir is None:
            import sys
            h = logging.StreamHandler(sys.stderr)
            h.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            self.logger = logging.getLogger(self.name)
            self.logger.handlers.clear()
            self.logger.addHandler(h)
            self.logger.setLevel(logging.DEBUG)
            self.logger.warning("Diretório de logs não pôde ser criado; usando apenas console.")
            self._security_logger = None
            return
        
        # Configurar logger principal
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(logging.DEBUG)  # Sempre DEBUG no logger para filtrar nos handlers
        
        # Limpar handlers existentes
        self.logger.handlers.clear()
        
        # Handler para console (INFO+ para aparecer em journalctl/terminal)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # Handler para arquivo de logs gerais (delay=False para flush imediato em diagnóstico)
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / "pdv_solumatica.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8',
            delay=False
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        
        # Handler para erros
        error_handler = logging.handlers.RotatingFileHandler(
            log_dir / "errors.log",
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s\n'
            'Exception: %(exc_info)s\n',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        error_handler.setFormatter(error_formatter)
        self.logger.addHandler(error_handler)
        
        # Handler para auditoria
        audit_handler = logging.handlers.RotatingFileHandler(
            log_dir / "audit.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=10,
            encoding='utf-8'
        )
        audit_handler.setLevel(logging.INFO)
        audit_formatter = logging.Formatter(
            '%(asctime)s - AUDIT - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        audit_handler.setFormatter(audit_formatter)
        self.logger.addHandler(audit_handler)
        
        # Logger e handler dedicados para security.log (apenas eventos de segurança)
        self._security_logger = logging.getLogger("pdv_solumatica.security")
        self._security_logger.setLevel(logging.INFO)
        self._security_logger.handlers.clear()
        self._security_logger.propagate = False
        security_handler = logging.handlers.RotatingFileHandler(
            log_dir / "security.log",
            maxBytes=5*1024*1024,
            backupCount=5,
            encoding='utf-8'
        )
        security_handler.setLevel(logging.INFO)
        security_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        self._security_logger.addHandler(security_handler)
    
    def info(self, message: str, **kwargs):
        """Log de informação"""
        self.logger.info(message, **kwargs)
    
    def error(self, message: str, exc_info: Optional[Exception] = None, **kwargs):
        """Log de erro"""
        self.logger.error(message, exc_info=exc_info, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log de aviso"""
        self.logger.warning(message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log de debug"""
        self.logger.debug(message, **kwargs)
    
    def audit(self, action: str, user: str = "system", details: str = ""):
        """Log de auditoria"""
        audit_message = f"USER:{user} - ACTION:{action} - {details}"
        self.logger.info(audit_message)
    
    def security(self, event: str, ip: str = "", user: str = "unknown", details: str = ""):
        """Log de segurança (arquivo security.log e logger principal)."""
        security_message = f"SECURITY - IP:{ip} - USER:{user} - EVENT:{event} - {details}"
        if getattr(self, "_security_logger", None):
            self._security_logger.warning(security_message)
        self.logger.warning(security_message)

    def struct(
        self,
        message: str,
        level: str = "info",
        request_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        **extra: Any,
    ) -> None:
        """Log estruturado com correlação (request_id, tenant_id, user_id) para observabilidade."""
        prefix = _structured_prefix(request_id=request_id, tenant_id=tenant_id, user_id=user_id, **extra)
        msg = f"{prefix}{message}"
        getattr(self.logger, level, self.logger.info)(msg)

# Instância global do logger
logger = PdvIbixLogger()


def setup_database_logging() -> None:
    """Configura log de banco (sqlalchemy.engine) em logs/database.log. Chamar no startup da app."""
    log_dir = getattr(logger, "_log_dir", None)
    if log_dir is None:
        log_dir = os.getenv("LOG_DIR", "").strip()
        log_dir = Path(log_dir) if log_dir else Path(__file__).resolve().parent.parent.parent / "logs"
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            return
    db_logger = logging.getLogger("sqlalchemy.engine")
    db_logger.handlers.clear()
    level = logging.INFO if os.getenv("DEBUG", "").lower() == "true" or os.getenv("LOG_LEVEL", "").upper() == "DEBUG" else logging.WARNING
    db_logger.setLevel(level)
    handler = logging.handlers.RotatingFileHandler(
        log_dir / "database.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    db_logger.addHandler(handler)

# Funções de conveniência
def log_info(message: str, **kwargs):
    """Log de informação"""
    logger.info(message, **kwargs)

def log_error(
    message: str,
    exc_info: Optional[Exception] = None,
    request_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    user_id: Optional[str] = None,
    **kwargs: Any,
) -> None:
    """Log de erro com correlação opcional (request_id, tenant_id, user_id)."""
    if request_id is not None or tenant_id is not None or user_id is not None:
        prefix = _structured_prefix(request_id=request_id, tenant_id=tenant_id, user_id=user_id)
        message = f"{prefix}{message}"
    logger.error(message, exc_info=exc_info, **kwargs)

def log_warning(message: str, **kwargs):
    """Log de aviso"""
    logger.warning(message, **kwargs)

def log_debug(message: str, **kwargs):
    """Log de debug"""
    logger.debug(message, **kwargs)

def log_audit(action: str, user: str = "system", details: str = ""):
    """Log de auditoria"""
    logger.audit(action, user, details)

def log_security(event: str, ip: str = "", user: str = "unknown", details: str = ""):
    """Log de segurança"""
    logger.security(event, ip, user, details)


def log_struct(
    message: str,
    level: str = "info",
    request_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    user_id: Optional[str] = None,
    **extra: Any,
) -> None:
    """Log estruturado com correlação (request_id, tenant_id, user_id). Uso: log_struct('msg', request_id=rid, user_id=uid)."""
    logger.struct(message, level=level, request_id=request_id, tenant_id=tenant_id, user_id=user_id, **extra) 