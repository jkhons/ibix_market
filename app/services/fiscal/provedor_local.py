# PDV Ibix - Provedor fiscal local (NF-e 4.0: XML, assinatura, SEFAZ)
"""
Implementa IProvedorFiscal com geração de XML NF-e 4.0, assinatura A1 e envio ao webservice SEFAZ.
Usa apenas empresa_id e dados da empresa; isolamento por tenant garantido na API.
Em rejeição SEFAZ: extrai e retorna a chave real do XML (44 dígitos) para persistir na nota.
"""
import hashlib
import re
import time
from pathlib import Path
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.core.logging import log_struct
from app.models.empresa import Empresa
from app.models.nota_fiscal import NotaFiscal

from .certificado import (
    _extrair_data_validade_cert,
    carregar_certificado_a1,
    carregar_certificado_a1_sem_validar,
    validar_validade_certificado,
)
from .nfe_assinador import assinar_nfe
from .nfe_logging import (
    gravar_diagnostico_nfe,
    log_nfe_cert,
    log_nfe_envio_inicio,
    log_nfe_xml_envio,
)
from .nfe_xml_builder import montar_nfe
from .provedor_base import IProvedorFiscal, ResultadoCancelamentoFiscal, ResultadoEnvioFiscal
from .sefaz_client import (
    enviar_evento_cancelamento,
    enviar_nfe_autorizacao,
    get_url_autorizacao,
)


# Diretório base para gravar XML (opcional); por tenant: uploads/fiscal/cliente_{id}/
def _dir_xml_empresa(base_dir: Optional[str], empresa_id: int) -> Path:
    if base_dir:
        d = Path(base_dir) / "fiscal" / f"empresa_{empresa_id}"
    else:
        d = Path("uploads/fiscal") / f"empresa_{empresa_id}"
    d.mkdir(parents=True, exist_ok=True)
    return d


class ProvedorFiscalLocal(IProvedorFiscal):
    """Provedor que gera XML NF-e 4.0, assina com certificado A1 da empresa e envia à SEFAZ."""

    def __init__(self, db: Session, base_storage_path: Optional[str] = None):
        self.db = db
        self.base_storage_path = base_storage_path

    def enviar_nfe(
        self, empresa_id: int, nota_fiscal_id: int, payload: Dict[str, Any]
    ) -> ResultadoEnvioFiscal:
        empresa = self.db.query(Empresa).filter(Empresa.id == empresa_id).first()
        if not empresa:
            return ResultadoEnvioFiscal(
                sucesso=False,
                status="erro",
                mensagem="Empresa não encontrada",
            )
        # Se validade não está cadastrada mas o certificado existe, extrair do .pfx e salvar
        if getattr(empresa, "certificado_validade", None) is None and (
            getattr(empresa, "certificado_a1_blob", None) or getattr(empresa, "certificado_a1_path", None)
        ):
            try:
                _, cert = carregar_certificado_a1_sem_validar(empresa)
                data_val = _extrair_data_validade_cert(cert)
                if data_val:
                    empresa.certificado_validade = data_val
                    self.db.commit()
                    self.db.refresh(empresa)
            except Exception:
                pass  # Segue e retorna mensagem orientando preenchimento manual
        err = validar_validade_certificado(empresa)
        if err:
            if "sem data de validade" in (err or "").lower():
                err = (
                    "Certificado sem data de validade. Acesse Fiscal > Empresa, edite a empresa, "
                    "preencha o campo 'Validade do certificado' com a data de vencimento do certificado e salve."
                )
            return ResultadoEnvioFiscal(sucesso=False, status="erro", mensagem=err)
        try:
            key, cert = carregar_certificado_a1(empresa)
        except ValueError as e:
            return ResultadoEnvioFiscal(sucesso=False, status="erro", mensagem=str(e))
        # Regra: ambiente da empresa fiscal é a fonte primária (Fiscal > Empresa); nota segue a empresa
        _amb = getattr(empresa, "ambiente", None) or payload.get("ambiente")
        ambiente = str(getattr(_amb, "value", _amb) or "homologacao").strip().lower()
        payload["ambiente"] = ambiente  # XML (tpAmb) e URL SEFAZ usam o ambiente da empresa
        emp_dict = payload.get("empresa") or {}
        dest_dict = payload.get("destinatario")
        xml_nfe = montar_nfe(payload, emp_dict, dest_dict)
        try:
            xml_assinado = assinar_nfe(xml_nfe, key, cert)
        except Exception as e:
            return ResultadoEnvioFiscal(
                sucesso=False,
                status="erro",
                mensagem=f"Falha ao assinar XML: {e}",
                payload_retorno={"tipo_erro": "assinatura", "mensagem": str(e), "servico": "autorizacao"},
            )
        uf = (emp_dict.get("uf") or getattr(empresa, "uf_emissao", None) or "SP").strip().upper()[:2]
        tp_amb = "2" if ambiente == "homologacao" else "1"
        modelo = str(payload.get("modelo") or "55").zfill(2)[:2]
        url_endpoint = get_url_autorizacao(uf, ambiente, modelo) or ""
        serie = str(payload.get("serie") or "1").zfill(3)[:3]
        numero = str(payload.get("numero") or "1").zfill(9)[:9]
        chave_xml_pre = None
        m_pre = re.search(r'Id="NFe(\d{44})"', xml_assinado)
        if m_pre:
            chave_xml_pre = m_pre.group(1)
        cert_serial = str(cert.serial_number) if getattr(cert, "serial_number", None) is not None else None
        try:
            cert_subject = (cert.subject.rfc4514_string() if hasattr(cert, "subject") and cert.subject else None) or str(getattr(cert, "subject", ""))[:255]
        except Exception:
            cert_subject = None
        # A. Log de contexto da tentativa
        log_nfe_envio_inicio(
            nota_id=nota_fiscal_id,
            empresa_id=empresa_id,
            operacao="autorizacao",
            tp_amb=tp_amb,
            uf=uf,
            endpoint=url_endpoint,
            modelo=modelo,
            serie=serie,
            numero=numero,
            chave_nfe=chave_xml_pre,
        )
        # B. Log do certificado (metadados apenas)
        try:
            cert_issuer = (cert.issuer.rfc4514_string() if hasattr(cert, "issuer") and cert.issuer else None) or ""
            cert_not_before = cert.not_valid_before_utc.isoformat() if getattr(cert, "not_valid_before_utc", None) else None
            cert_not_after = cert.not_valid_after_utc.isoformat() if getattr(cert, "not_valid_after_utc", None) else None
            if cert_not_before is None and getattr(cert, "not_valid_before", None):
                cert_not_before = str(cert.not_valid_before)
            if cert_not_after is None and getattr(cert, "not_valid_after", None):
                cert_not_after = str(cert.not_valid_after)
            cnpj_cert = None
            if cert_subject:
                cnpj_match = re.search(r"\d{14}", cert_subject)
                if cnpj_match:
                    cnpj_cert = cnpj_match.group(0)
            log_nfe_cert(
                subject=cert_subject,
                issuer=cert_issuer[:120] if cert_issuer else None,
                serial=cert_serial,
                not_before=cert_not_before,
                not_after=cert_not_after,
                cnpj_cert=cnpj_cert,
            )
        except Exception:
            pass
        # C. Log do payload + dump request.xml
        log_nfe_xml_envio(nota_id=nota_fiscal_id, xml_assinado=xml_assinado)
        xml_hash_sha256 = hashlib.sha256(xml_assinado.encode("utf-8")).hexdigest()
        # Envelope enviNFe (lote com uma NFe) conforme schema 4.00. Remover <?xml ...?> do NFe embutido (causa 400).
        # Obrigatório: versao="4.00", idLote, indSinc (1=síncrono). Sem indSinc ou versao errada → cStat 225.
        nfe_sem_decl = re.sub(r"<\?xml[^>]*\?>", "", xml_assinado, count=1, flags=re.IGNORECASE).strip()
        ns = "http://www.portalfiscal.inf.br/nfe"
        envi_nfe = f'<enviNFe xmlns="{ns}" versao="4.00"><idLote>1</idLote><indSinc>1</indSinc>{nfe_sem_decl}</enviNFe>'
        # Diagnóstico fechado rejeição 290: certificado, assinatura, CNPJ, XML em cada etapa
        cnpj_emit = emp_dict.get("cnpj") or getattr(empresa, "cnpj", None)
        gravar_diagnostico_nfe(
            nota_id=nota_fiscal_id,
            cert=cert,
            xml_antes_assinatura=xml_nfe,
            xml_apos_assinatura=xml_assinado,
            xml_enviado=envi_nfe,
            cnpj_emitente=cnpj_emit,
        )
        # SEFAZ exige mTLS (certificado A1); sem envio do cert retorna 403 Forbidden
        from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat
        cert_pem = cert.public_bytes(Encoding.PEM)
        key_pem = key.private_bytes(
            encoding=Encoding.PEM,
            format=PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=NoEncryption(),
        )
        t0 = time.perf_counter()
        ret = enviar_nfe_autorizacao(uf, ambiente, envi_nfe, cert_pem=cert_pem, key_pem=key_pem, nota_id=nota_fiscal_id, modelo=modelo)
        duracao_ms = int((time.perf_counter() - t0) * 1000)
        ret["cert_serial"] = cert_serial
        ret["cert_subject"] = (cert_subject[:255] if cert_subject else None)
        ret["xml_hash_sha256"] = xml_hash_sha256
        ret["duracao_ms"] = duracao_ms
        ret["ambiente_sefaz"] = ambiente
        # Chave real do XML (44 dígitos) para persistir mesmo em rejeição SEFAZ
        chave_xml = None
        m = re.search(r'Id="NFe(\d{44})"', xml_assinado)
        if m:
            chave_xml = m.group(1)
            ret["chave_xml"] = chave_xml
        log_struct(
            "NFe envio SEFAZ (provedor_local)",
            level="info",
            servico="nfe_autorizacao",
            uf=uf,
            ambiente=ambiente,
            status_http=ret.get("status_http"),
            http_content_type=ret.get("http_content_type"),
            duracao_ms=duracao_ms,
            cert_serial=cert_serial,
            cert_subject=(cert_subject[:100] + "..." if cert_subject and len(cert_subject) > 100 else cert_subject),
            sucesso=ret.get("sucesso"),
        )
        xml_path = None
        xml_retorno_path = None
        raw_ret = ret.get("raw_response") or ""
        try:
            dir_xml = _dir_xml_empresa(self.base_storage_path, empresa_id)
            xml_path = str(dir_xml / f"nota_{nota_fiscal_id}.xml")
            Path(xml_path).write_text(xml_assinado, encoding="utf-8")
            if raw_ret and (raw_ret.strip().startswith("<?") or raw_ret.strip().startswith("<")):
                xml_retorno_path = str(dir_xml / f"retorno_{nota_fiscal_id}.xml")
                Path(xml_retorno_path).write_text(raw_ret, encoding="utf-8")
        except Exception:
            pass
        if not ret.get("sucesso"):
            return ResultadoEnvioFiscal(
                sucesso=False,
                status="rejeitado",
                mensagem=ret.get("mensagem") or "Rejeição SEFAZ",
                chave=ret.get("chave") or ret.get("chave_xml"),
                payload_retorno=ret,
                xml_retorno=raw_ret or None,
                xml_path=xml_path,
                xml_retorno_path=xml_retorno_path,
            )
        return ResultadoEnvioFiscal(
            sucesso=True,
            status="autorizado",
            protocolo=ret.get("protocolo"),
            chave=ret.get("chave"),
            mensagem=ret.get("mensagem"),
            payload_retorno=ret,
            xml_retorno=raw_ret or None,
            xml_path=xml_path,
            xml_retorno_path=xml_retorno_path,
        )

    def cancelar_nfe(
        self, empresa_id: int, nota_fiscal_id: int, motivo: str
    ) -> ResultadoCancelamentoFiscal:
        # Evento de cancelamento: montar XML do evento 110111, assinar e enviar
        nota = self.db.query(NotaFiscal).filter(NotaFiscal.id == nota_fiscal_id).first()
        if not nota or not getattr(nota, "chave_acesso", None):
            return ResultadoCancelamentoFiscal(
                sucesso=False,
                mensagem="Nota não encontrada ou sem chave de acesso",
            )
        empresa = self.db.query(Empresa).filter(Empresa.id == empresa_id).first()
        if not empresa:
            return ResultadoCancelamentoFiscal(sucesso=False, mensagem="Empresa não encontrada")
        if getattr(empresa, "certificado_validade", None) is None and (
            getattr(empresa, "certificado_a1_blob", None) or getattr(empresa, "certificado_a1_path", None)
        ):
            try:
                _, cert = carregar_certificado_a1_sem_validar(empresa)
                data_val = _extrair_data_validade_cert(cert)
                if data_val:
                    empresa.certificado_validade = data_val
                    self.db.commit()
                    self.db.refresh(empresa)
            except Exception:
                pass
        err = validar_validade_certificado(empresa)
        if err:
            if "sem data de validade" in (err or "").lower():
                err = (
                    "Certificado sem data de validade. Acesse Fiscal > Empresa, edite a empresa, "
                    "preencha o campo 'Validade do certificado' com a data de vencimento do certificado e salve."
                )
            return ResultadoCancelamentoFiscal(sucesso=False, mensagem=err)
        try:
            key, cert = carregar_certificado_a1(empresa)
        except ValueError as e:
            return ResultadoCancelamentoFiscal(sucesso=False, mensagem=str(e))
        from datetime import datetime, timedelta, timezone
        _TZ_SP = timezone(timedelta(hours=-3))
        chave = nota.chave_acesso
        cnpj_emit = re.sub(r"\D", "", str(empresa.cnpj or ""))[:14].zfill(14)
        dt_sp = datetime.now(timezone.utc).astimezone(_TZ_SP)
        dt_evento = dt_sp.strftime("%Y-%m-%dT%H:%M:%S-03:00")
        ns = "http://www.portalfiscal.inf.br/nfe"
        _amb_evt = getattr(empresa, "ambiente", None)
        amb_evt = str(getattr(_amb_evt, "value", _amb_evt) or "homologacao").strip().lower()
        tp_amb_evt = "2" if amb_evt == "homologacao" else "1"
        n_seq = "1"
        id_evento = f"ID110111{chave}{n_seq.zfill(2)}"
        protocolo = getattr(nota, "protocolo", None) or getattr(nota, "protocolo_autorizacao", None) or ""
        evento = (
            f'<evento xmlns="{ns}" versao="1.00">'
            f'<infEvento Id="{id_evento}">'
            f'<cOrgao>{chave[:2]}</cOrgao>'
            f'<tpAmb>{tp_amb_evt}</tpAmb>'
            f'<CNPJ>{cnpj_emit}</CNPJ>'
            f'<chNFe>{chave}</chNFe>'
            f'<dhEvento>{dt_evento}</dhEvento>'
            '<tpEvento>110111</tpEvento>'
            f'<nSeqEvento>{n_seq}</nSeqEvento>'
            '<verEvento>1.00</verEvento>'
            f'<detEvento versao="1.00"><descEvento>Cancelamento</descEvento>'
            f'<nProt>{protocolo}</nProt>'
            f'<xJust>{motivo[:255]}</xJust>'
            '</detEvento>'
            "</infEvento></evento>"
        )
        try:
            import base64
            import hashlib as _hashlib
            from copy import deepcopy

            from cryptography.hazmat.primitives import hashes as _hashes
            from cryptography.hazmat.primitives.asymmetric import padding as _padding
            from cryptography.hazmat.primitives.serialization import Encoding
            from lxml import etree

            root = etree.fromstring(evento.encode("utf-8"))
            inf_evt = root.find(f".//{{{ns}}}infEvento")
            if inf_evt is None:
                inf_evt = root.find(".//infEvento")
            if inf_evt is not None:
                id_inf = inf_evt.get("Id")
                inf_copy = deepcopy(inf_evt)
                c14n_inf = etree.tostring(inf_copy, method="c14n", exclusive=False)
                digest_b64 = base64.b64encode(_hashlib.sha1(c14n_inf).digest()).decode()
                signed_info_xml = (
                    '<SignedInfo xmlns="http://www.w3.org/2000/09/xmldsig#">'
                    '<CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>'
                    '<SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1"/>'
                    f'<Reference URI="#{id_inf}">'
                    '<Transforms>'
                    '<Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>'
                    '<Transform Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>'
                    '</Transforms>'
                    '<DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"/>'
                    f'<DigestValue>{digest_b64}</DigestValue>'
                    '</Reference></SignedInfo>'
                )
                si_el = etree.fromstring(signed_info_xml.encode("utf-8"))
                c14n_si = etree.tostring(si_el, method="c14n", exclusive=False)
                sig_bytes = key.sign(c14n_si, _padding.PKCS1v15(), _hashes.SHA1())
                sig_b64 = base64.b64encode(sig_bytes).decode()
                cert_b64 = base64.b64encode(cert.public_bytes(Encoding.DER)).decode()
                si_inner = signed_info_xml.replace(' xmlns="http://www.w3.org/2000/09/xmldsig#"', "")
                signature_str = (
                    '<Signature xmlns="http://www.w3.org/2000/09/xmldsig#">'
                    f"{si_inner}"
                    f"<SignatureValue>{sig_b64}</SignatureValue>"
                    "<KeyInfo><X509Data>"
                    f"<X509Certificate>{cert_b64}</X509Certificate>"
                    "</X509Data></KeyInfo>"
                    "</Signature>"
                )
                resultado_bytes = etree.tostring(root, encoding="utf-8", xml_declaration=False, method="xml")
                evento = resultado_bytes.decode("utf-8")
                close_tag = "</evento>"
                evento = evento.replace(close_tag, signature_str + close_tag, 1)
        except Exception:
            pass
        env_evt = re.sub(r"<\?xml[^>]*\?>", "", evento, count=1).strip()
        env = f'<envEvento xmlns="{ns}" versao="1.00"><idLote>1</idLote>{env_evt}</envEvento>'
        uf = (getattr(empresa, "uf_emissao", None) or "SP").strip().upper()[:2]
        ambiente = amb_evt
        modelo = str(getattr(nota, "modelo", None) or "55").strip()
        from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat
        cert_pem = cert.public_bytes(Encoding.PEM)
        key_pem = key.private_bytes(encoding=Encoding.PEM, format=PrivateFormat.TraditionalOpenSSL, encryption_algorithm=NoEncryption())
        ret = enviar_evento_cancelamento(uf, ambiente, env, cert_pem=cert_pem, key_pem=key_pem, modelo=modelo)
        return ResultadoCancelamentoFiscal(
            sucesso=ret.get("sucesso", False),
            mensagem=ret.get("mensagem"),
            payload_retorno=ret,
        )

    def enviar_nfse(
        self, empresa_id: int, nota_servico_id: int, payload: Dict[str, Any]
    ) -> ResultadoEnvioFiscal:
        return ResultadoEnvioFiscal(sucesso=False, status="nao_implementado", mensagem="NFS-e local não implementado")

    def enviar_nfce(
        self, empresa_id: int, nota_fiscal_id: int, payload: Dict[str, Any]
    ) -> ResultadoEnvioFiscal:
        return ResultadoEnvioFiscal(sucesso=False, status="nao_implementado", mensagem="NFC-e local não implementado")

    def cancelar_nfse(self, empresa_id: int, nota_servico_id: int, motivo: str) -> ResultadoCancelamentoFiscal:
        return ResultadoCancelamentoFiscal(sucesso=False, mensagem="NFS-e local não implementado")

    def cancelar_nfce(self, empresa_id: int, nota_fiscal_id: int, motivo: str) -> ResultadoCancelamentoFiscal:
        return ResultadoCancelamentoFiscal(sucesso=False, mensagem="NFC-e local não implementado")
