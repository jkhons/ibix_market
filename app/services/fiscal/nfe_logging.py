# PDV Ibix - Logging estruturado NF-e para diagnóstico
"""
Pontos de log obrigatórios conforme checklist técnico:
A. Contexto da tentativa
B. Certificado (metadados, nunca chave privada)
C. Payload de envio (dump em arquivo)
D. Chamada HTTP (método, URL, timeout, horários)
E. Resposta bruta (status, headers, size, body prefix, dump)
F. Parse (xml_parse_ok, soap_fault, etc.)
G. Exceção (tipo exato: SSLError, ReadTimeout, etc.)

Diagnóstico fechado (rejeição 290): certificado, assinatura, CNPJ e XML em cada etapa.
"""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.config import PROJECT_ROOT
from app.core.logging import log_struct

NFE_LOGS_DIR = PROJECT_ROOT / "logs" / "nfe"


def _dir_nota(nota_id: int) -> Path:
    """Retorna /logs/nfe/YYYY-MM-DD/nota_{id}/"""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    d = NFE_LOGS_DIR / today / f"nota_{nota_id}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def log_nfe_envio_inicio(
    nota_id: int,
    empresa_id: int,
    operacao: str,
    tp_amb: str,
    uf: str,
    endpoint: str,
    modelo: str = "55",
    serie: str = "1",
    numero: str = "1",
    chave_nfe: Optional[str] = None,
) -> None:
    """A. Log de contexto da tentativa."""
    log_struct(
        "NFE_ENVIO_INICIO",
        level="info",
        nota_id=nota_id,
        empresa_id=empresa_id,
        operacao=operacao,
        tpAmb=tp_amb,
        uf=uf,
        endpoint=(endpoint[:80] + "..." if len(endpoint) > 80 else endpoint),
        modelo=modelo,
        serie=serie,
        numero=numero,
        chave_nfe=chave_nfe,
    )


def log_nfe_cert(
    subject: Optional[str] = None,
    issuer: Optional[str] = None,
    serial: Optional[str] = None,
    not_before: Optional[str] = None,
    not_after: Optional[str] = None,
    cnpj_cert: Optional[str] = None,
    **extra: Any,
) -> None:
    """B. Log do certificado (metadados apenas, nunca chave privada)."""
    log_struct(
        "NFE_CERT",
        level="info",
        subject=(subject[:120] + "..." if subject and len(subject) > 120 else subject),
        issuer=(issuer[:80] + "..." if issuer and len(issuer) > 80 else issuer),
        serial=serial,
        not_before=not_before,
        not_after=not_after,
        cnpj_cert=cnpj_cert,
        **extra,
    )


def log_nfe_xml_envio(
    nota_id: int,
    xml_assinado: str,
) -> Optional[Path]:
    """C. Log do payload + salva request.xml e request_meta.json."""
    try:
        d = _dir_nota(nota_id)
        xml_bytes = len(xml_assinado.encode("utf-8"))
        xml_sha256 = hashlib.sha256(xml_assinado.encode("utf-8")).hexdigest()
        request_path = d / "request.xml"
        request_path.write_text(xml_assinado, encoding="utf-8")
        meta = {"xml_bytes": xml_bytes, "xml_sha256": xml_sha256}
        (d / "request_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        log_struct(
            "NFE_XML_ENVIO",
            level="info",
            nota_id=nota_id,
            xml_bytes=xml_bytes,
            xml_sha256=xml_sha256[:16] + "...",
            xml_dump=str(request_path),
        )
        return request_path
    except Exception:
        return None


def log_nfe_http_request(
    metodo: str,
    url: str,
    content_type: str,
    timeout: int,
    started_at: str,
) -> None:
    """D. Log da chamada HTTP (início)."""
    log_struct(
        "NFE_HTTP_REQUEST",
        level="info",
        method=metodo,
        url=(url[:80] + "..." if len(url) > 80 else url),
        content_type=content_type,
        timeout=timeout,
        started_at=started_at,
    )


def log_nfe_http_response(
    status_code: Optional[int] = None,
    reason: Optional[str] = None,
    content_type: Optional[str] = None,
    response_bytes: int = 0,
    body_prefix: Optional[str] = None,
    response_dump: Optional[str] = None,
) -> None:
    """E. Log da resposta bruta (antes do parse)."""
    log_struct(
        "NFE_HTTP_RESPONSE",
        level="warning" if response_bytes == 0 else "info",
        status_code=status_code,
        reason=reason or "N/A",
        content_type=content_type or "não informado",
        response_bytes=response_bytes,
        body_prefix=(body_prefix[:500] if body_prefix else ""),
        response_dump=response_dump,
    )


def log_nfe_parse(
    xml_parse_ok: bool,
    soap_envelope: bool = False,
    soap_fault: bool = False,
    ret_autorizacao_node: bool = False,
    error: Optional[str] = None,
) -> None:
    """F. Log de parse (XML/SOAP)."""
    payload = {
        "xml_parse_ok": xml_parse_ok,
        "soap_envelope": soap_envelope,
        "soap_fault": soap_fault,
        "ret_autorizacao_node": ret_autorizacao_node,
    }
    if error:
        payload["error"] = (error[:200] + "..." if len(error) > 200 else error)
    log_struct("NFE_PARSE", level="info" if xml_parse_ok else "warning", **payload)


def log_nfe_exception(
    exc_type: str,
    exc_message: str,
    endpoint: Optional[str] = None,
    elapsed_ms: Optional[int] = None,
) -> None:
    """G. Log de exceção (tipo exato: ReadTimeout, SSLError, etc.). Nunca reduzir a 'resposta vazia'."""
    log_struct(
        "NFE_EXCEPTION",
        level="warning",
        type=exc_type,
        exception_msg=(exc_message[:300] + "..." if len(exc_message) > 300 else exc_message),
        endpoint=(endpoint[:80] + "..." if endpoint and len(endpoint) > 80 else endpoint),
        elapsed_ms=elapsed_ms,
    )


def _extrair_cnpj_14(val: Any) -> Optional[str]:
    """Extrai CNPJ de 14 dígitos (apenas números)."""
    if val is None or val == "":
        return None
    s = re.sub(r"\D", "", str(val))
    if len(s) < 14:
        return None
    return s[:14]


def _extrair_assinatura_diag(xml_assinado: str) -> Dict[str, Any]:
    """Extrai estrutura da assinatura XML para diagnóstico (rejeição 290)."""
    out: Dict[str, Any] = {
        "id_infnfe": None,
        "reference_uri": None,
        "signature_method_algorithm": None,
        "digest_method_algorithm": None,
        "canonicalization_method_algorithm": None,
        "signedinfo_excerpt": None,
        "x509_certificate_presente": False,
        "x509_certificate_len": 0,
        "qtd_signatures": 0,
    }
    try:
        # Id infNFe
        m_id = re.search(r'Id="(NFe\d{44})"', xml_assinado)
        if m_id:
            out["id_infnfe"] = m_id.group(1)

        # Quantidade de assinaturas (apenas tags de abertura, não fechamento)
        out["qtd_signatures"] = len(re.findall(r"<(?!/)\w*:?Signature[\s>]", xml_assinado))

        # Reference URI
        m_uri = re.search(r'URI="(#NFe\d{44})"', xml_assinado)
        if m_uri:
            out["reference_uri"] = m_uri.group(1)
        if not out["reference_uri"]:
            m_uri2 = re.search(r'URI="([^"]+)"', xml_assinado)
            if m_uri2:
                out["reference_uri"] = m_uri2.group(1)

        # SignatureMethod
        m_sig = re.search(r"<[^:]*:?SignatureMethod[^>]*Algorithm=\"([^\"]+)\"", xml_assinado)
        if m_sig:
            out["signature_method_algorithm"] = m_sig.group(1)

        # DigestMethod
        m_dig = re.search(r"<[^:]*:?DigestMethod[^>]*Algorithm=\"([^\"]+)\"", xml_assinado)
        if m_dig:
            out["digest_method_algorithm"] = m_dig.group(1)

        # CanonicalizationMethod
        m_c14n = re.search(r"<[^:]*:?CanonicalizationMethod[^>]*Algorithm=\"([^\"]+)\"", xml_assinado)
        if m_c14n:
            out["canonicalization_method_algorithm"] = m_c14n.group(1)

        # SignedInfo (trecho entre tags)
        m_si = re.search(r"<[^:]*:?SignedInfo[^>]*>(.*?)</[^:]*:?SignedInfo>", xml_assinado, re.DOTALL)
        if m_si:
            si_inner = m_si.group(1).strip()[:800]
            out["signedinfo_excerpt"] = si_inner + ("..." if len(m_si.group(1)) > 800 else "")

        # X509Certificate
        m_x509 = re.search(r"<[^:]*:?X509Certificate[^>]*>([^<]+)</[^:]*:?X509Certificate>", xml_assinado)
        if m_x509:
            out["x509_certificate_presente"] = True
            out["x509_certificate_len"] = len(m_x509.group(1).strip())
    except Exception:
        pass
    return out


def gravar_diagnostico_nfe(
    nota_id: int,
    cert: Any,
    xml_antes_assinatura: str,
    xml_apos_assinatura: str,
    xml_enviado: str,
    cnpj_emitente: Optional[str] = None,
) -> Optional[Path]:
    """
    Grava diagnóstico fechado para rejeição 290 em logs/nfe/YYYY-MM-DD/nota_{id}/:
    - cert_diag.json: subject, serial, notBefore, notAfter, CNPJ, fingerprint
    - assinatura_diag.json: SignedInfo, Reference URI, Id, SignatureMethod, DigestMethod, CanonicalizationMethod
    - cnpj_comparacao: CNPJ cert vs emitente (match ou mismatch)
    - xml_antes_assinatura.xml
    - xml_apos_assinatura.xml (redundante com request.xml; referência explícita)
    - enviNFe_enviado.xml (payload exato enviado à SEFAZ)
    """
    try:
        d = _dir_nota(nota_id)
    except Exception:
        return None

    try:
        # Certificado
        cert_subject = None
        cert_serial = None
        cert_not_before = None
        cert_not_after = None
        cnpj_cert = None
        fingerprint_sha256 = None
        cert_version_val = None
        key_usage_val = None
        basic_constraint_ca_val = None
        if cert is not None:
            try:
                cert_subject = (
                    cert.subject.rfc4514_string()
                    if hasattr(cert, "subject") and cert.subject
                    else str(getattr(cert, "subject", ""))[:255]
                )
            except Exception:
                cert_subject = str(getattr(cert, "subject", ""))[:255] if getattr(cert, "subject", None) else None
            cert_serial = str(cert.serial_number) if getattr(cert, "serial_number", None) is not None else None
            try:
                nb = getattr(cert, "not_valid_before_utc", None) or getattr(cert, "not_valid_before", None)
                na = getattr(cert, "not_valid_after_utc", None) or getattr(cert, "not_valid_after", None)
                cert_not_before = nb.isoformat() if nb and hasattr(nb, "isoformat") else str(nb) if nb else None
                cert_not_after = na.isoformat() if na and hasattr(na, "isoformat") else str(na) if na else None
            except Exception:
                pass
            if cert_subject:
                m = re.search(r"\d{14}", cert_subject)
                if m:
                    cnpj_cert = m.group(0)
            try:
                from cryptography.hazmat.primitives import hashes
                fp = cert.fingerprint(hashes.SHA256())
                fingerprint_sha256 = fp.hex() if fp else None
            except Exception:
                pass
            # NT 2011.003 E01: versão 3, Basic Constraint (não CA), KeyUsage (digitalSignature, nonRepudiation)
            cert_version_val = None
            key_usage_val = None
            basic_constraint_ca_val = None
            try:
                v = getattr(cert, "version", None)
                cert_version_val = "3" if (v and "3" in str(v)) else (str(v) if v else None)
                for ext in getattr(cert, "extensions", []) or []:
                    oid_name = getattr(ext.oid, "_name", "") or str(ext.oid)
                    if "key_usage" in oid_name.lower() or "2.5.29.15" in str(ext.oid):
                        ku = ext.value
                        flags = []
                        if getattr(ku, "digital_signature", False):
                            flags.append("digitalSignature")
                        if getattr(ku, "content_commitment", False) or getattr(ku, "non_repudiation", False):
                            flags.append("nonRepudiation")
                        if getattr(ku, "key_encipherment", False):
                            flags.append("keyEncipherment")
                        key_usage_val = flags or str(ku)[:200]
                    elif "basic_constraints" in oid_name.lower() or "2.5.29.19" in str(ext.oid):
                        basic_constraint_ca_val = getattr(ext.value, "ca", None)
            except Exception:
                pass

        # CNPJ comparação
        cnpj_emit = _extrair_cnpj_14(cnpj_emitente) if cnpj_emitente else None
        if not cnpj_emit and xml_antes_assinatura:
            m_emit = re.search(r"<CNPJ>(\d{14})</CNPJ>", xml_antes_assinatura)
            if m_emit:
                cnpj_emit = m_emit.group(1)
        cnpj_match = cnpj_cert == cnpj_emit if (cnpj_cert and cnpj_emit) else None

        cert_diag = {
            "subject": cert_subject,
            "serial": cert_serial,
            "notBefore": cert_not_before,
            "notAfter": cert_not_after,
            "cnpj_cert": cnpj_cert,
            "fingerprint_sha256": fingerprint_sha256,
            "cnpj_emitente": cnpj_emit,
            "cnpj_match": cnpj_match,
            "cnpj_match_ok": cnpj_match is True,
            "nt_e01": {
                "version": cert_version_val,
                "version_ok": cert_version_val == "3",
                "key_usage": key_usage_val,
                "key_usage_ok": (
                    isinstance(key_usage_val, list)
                    and "digitalSignature" in key_usage_val
                    and ("nonRepudiation" in key_usage_val or "contentCommitment" in str(key_usage_val))
                ),
                "basic_constraint_ca": basic_constraint_ca_val,
                "basic_constraint_ok": basic_constraint_ca_val is False,
            },
        }
        (d / "cert_diag.json").write_text(json.dumps(cert_diag, indent=2, ensure_ascii=False), encoding="utf-8")

        # Assinatura
        assinatura_diag = _extrair_assinatura_diag(xml_apos_assinatura)
        (d / "assinatura_diag.json").write_text(
            json.dumps(assinatura_diag, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # XMLs
        (d / "xml_antes_assinatura.xml").write_text(xml_antes_assinatura, encoding="utf-8")
        (d / "xml_apos_assinatura.xml").write_text(xml_apos_assinatura, encoding="utf-8")
        (d / "enviNFe_enviado.xml").write_text(xml_enviado, encoding="utf-8")

        # Hash dos XMLs para verificar alteração pós-assinatura
        hash_apos = hashlib.sha256(xml_apos_assinatura.encode("utf-8")).hexdigest()
        nfe_sem_decl = re.sub(r"<\?xml[^>]*\?>", "", xml_apos_assinatura, count=1, flags=re.IGNORECASE).strip()
        hash_nfe_no_envi = hashlib.sha256(nfe_sem_decl.encode("utf-8")).hexdigest()
        meta_diag = {
            "xml_apos_sha256": hash_apos,
            "nfe_no_envi_sha256": hash_nfe_no_envi,
            "encoding": "utf-8",
            "id_infnfe": assinatura_diag.get("id_infnfe"),
            "reference_uri": assinatura_diag.get("reference_uri"),
        }
        (d / "diag_meta.json").write_text(json.dumps(meta_diag, indent=2), encoding="utf-8")

        log_struct(
            "NFE_DIAG_GRAVADO",
            level="info",
            nota_id=nota_id,
            dir_dump=str(d),
            cnpj_match=cnpj_match,
            id_infnfe=assinatura_diag.get("id_infnfe"),
            reference_uri=assinatura_diag.get("reference_uri"),
        )
        return d
    except Exception as e:
        log_struct("NFE_DIAG_ERRO", level="warning", nota_id=nota_id, error=str(e)[:200])
        return None
