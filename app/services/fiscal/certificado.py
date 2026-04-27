# PDV Ibix - Carregador de certificado A1 para assinatura NF-e
"""
Carrega certificado digital A1 (PFX/PKCS12) da empresa para assinatura XML.
Prioridade: certificado_a1_blob; fallback: certificado_a1_path + senha.
Nunca loga certificado, chave privada ou senha.
"""
from datetime import date
from pathlib import Path
from typing import Any, Optional, Tuple

try:
    from app.core.config import FISCAL_UPLOADS_DIR
except Exception:
    FISCAL_UPLOADS_DIR = None

from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat
from cryptography.hazmat.primitives.serialization.pkcs12 import load_key_and_certificates
from cryptography.x509 import Certificate

# Tipo: (chave_privada, certificado) para uso no assinador
CertificadoA1 = Tuple[Any, Certificate]


def _obter_senha(empresa: Any) -> Optional[bytes]:
    """Obtém senha do certificado (descriptografada se estiver em repouso cifrada). Não logar."""
    raw = getattr(empresa, "senha_certificado", None)
    if raw is None:
        return None
    try:
        from app.services.payments.credentials import decrypt_cert_password
        senha = decrypt_cert_password(raw if isinstance(raw, str) else (raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)))
    except Exception:
        senha = raw if isinstance(raw, str) else (raw.decode("utf-8") if isinstance(raw, bytes) else None)
    if not senha or (isinstance(senha, str) and not senha.strip()):
        return None
    return senha.encode("utf-8") if isinstance(senha, str) else (senha if isinstance(senha, bytes) else None)


def validar_validade_certificado(empresa: Any) -> Optional[str]:
    """
    Verifica se o certificado da empresa está dentro da validade.
    Retorna None se OK; mensagem de erro se expirado ou sem data.
    """
    val = getattr(empresa, "certificado_validade", None)
    if val is None:
        return "Certificado sem data de validade cadastrada"
    if isinstance(val, date) and val < date.today():
        return f"Certificado expirado em {val.isoformat()}"
    return None


def _resolver_path_certificado(path_str: str) -> Path:
    """Resolve path do certificado: absoluto usa como está; relativo usa FISCAL_UPLOADS_DIR ou cwd."""
    p = Path(path_str.strip())
    if p.is_absolute():
        return p
    if FISCAL_UPLOADS_DIR is not None and FISCAL_UPLOADS_DIR.is_dir():
        if path_str.startswith("uploads/") or path_str.startswith("uploads\\"):
            return Path(FISCAL_UPLOADS_DIR.parent.parent) / path_str.replace("\\", "/")
        return FISCAL_UPLOADS_DIR / path_str.replace("\\", "/")
    return Path.cwd() / p


def carregar_certificado_a1_sem_validar(empresa: Any, senha_override: Optional[str] = None) -> CertificadoA1:
    """
    Carrega certificado A1 (chave + cert) sem verificar certificado_validade.
    Útil para extrair a data de validade do próprio certificado quando o campo está vazio.
    """
    data: Optional[bytes] = None
    blob = getattr(empresa, "certificado_a1_blob", None)
    if blob:
        data = bytes(blob) if not isinstance(blob, bytes) else blob
    if not data:
        path = getattr(empresa, "certificado_a1_path", None)
        if path and isinstance(path, str) and path.strip():
            p = _resolver_path_certificado(path)
            if not p.exists():
                raise ValueError("Arquivo de certificado não encontrado")
            data = p.read_bytes()
    if not data:
        raise ValueError("Empresa sem certificado A1 configurado (blob ou path)")
    senha = senha_override.encode("utf-8") if senha_override else _obter_senha(empresa)
    if not senha:
        raise ValueError("Senha do certificado não informada")
    try:
        key, cert, _ = load_key_and_certificates(data, senha)
    except Exception as e:
        raise ValueError("Falha ao abrir certificado (senha ou arquivo inválido)") from e
    if key is None or cert is None:
        raise ValueError("Certificado inválido (chave ou certificado ausente)")
    return (key, cert)


def _extrair_data_validade_cert(cert: Certificate) -> Optional[date]:
    """Extrai a data de validade (not_valid_after) do certificado."""
    val = getattr(cert, "not_valid_after_utc", None) or getattr(cert, "not_valid_after", None)
    if val is None:
        return None
    if hasattr(val, "date"):
        return val.date()
    return date(val.year, val.month, val.day)


def carregar_certificado_a1(empresa: Any, senha_override: Optional[str] = None) -> CertificadoA1:
    """
    Carrega certificado A1 (chave + cert) a partir dos dados da empresa.
    Prioridade: certificado_a1_blob; se não houver, certificado_a1_path + senha.
    Retorna (private_key, certificate) para uso na assinatura.
    Levanta ValueError se não houver certificado ou senha inválida.
    """
    err_validade = validar_validade_certificado(empresa)
    if err_validade:
        raise ValueError(err_validade)

    data: Optional[bytes] = None
    senha: Optional[bytes] = None

    blob = getattr(empresa, "certificado_a1_blob", None)
    if blob:
        data = bytes(blob) if not isinstance(blob, bytes) else blob
    if not data:
        path = getattr(empresa, "certificado_a1_path", None)
        if path and isinstance(path, str) and path.strip():
            p = _resolver_path_certificado(path)
            if not p.exists():
                raise ValueError("Arquivo de certificado não encontrado")
            data = p.read_bytes()

    if not data:
        raise ValueError("Empresa sem certificado A1 configurado (blob ou path)")

    senha = senha_override.encode("utf-8") if senha_override else _obter_senha(empresa)
    if not senha:
        raise ValueError("Senha do certificado não informada")

    try:
        key, cert, _ = load_key_and_certificates(data, senha)
    except Exception as e:
        # Não incluir senha/certificado na mensagem
        raise ValueError("Falha ao abrir certificado (senha ou arquivo inválido)") from e

    if key is None or cert is None:
        raise ValueError("Certificado inválido (chave ou certificado ausente)")

    return (key, cert)


def exportar_certificado_pem(cert: Certificate) -> bytes:
    """Exporta o certificado em PEM para inclusão em envelope SOAP (quando necessário)."""
    return cert.public_bytes(Encoding.PEM)


def exportar_chave_pem(key: Any) -> bytes:
    """Exporta a chave privada em PEM (sem criptografia) para uso com signxml/OpenSSL."""
    return key.private_bytes(
        encoding=Encoding.PEM,
        format=PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=NoEncryption(),
    )
