# PDV Ibix - Cliente SOAP SEFAZ para NF-e 4.0
"""
Resolve endpoint por (UF, modelo, ambiente, serviço). Regra rígida: ambiente vem da Empresa Fiscal.
Em SP: NF-e 55 usa nfe.fazenda.sp.gov.br; NFC-e 65 usa nfce.fazenda.sp.gov.br.
tpAmb 2 = homologação, tpAmb 1 = produção.
"""
import json
import os
import re
import ssl
import tempfile
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

from lxml import etree

from app.core.logging import log_struct

from . import nfe_logging

# tipo_resultado: erro_tecnico, lote_recebido, lote_processado, autorizada, rejeitada, resposta_invalida, resposta_vazia
RAW_RESPONSE_PREVIEW_LEN = 800
TRANSPORT_LOG_BODY_PREVIEW = 1000


def _log_sefaz_transport(
    servico: str,
    uf: str,
    ambiente: str,
    url: str,
    status_http: Optional[int] = None,
    http_content_type: Optional[str] = None,
    content_len: int = 0,
    body_preview: Optional[str] = None,
    url_final: Optional[str] = None,
    exception_type: Optional[str] = None,
    exception_msg: Optional[str] = None,
    **extra: Any,
) -> None:
    """Log estruturado de transporte SEFAZ para diagnóstico (status, headers, body, exceção)."""
    payload = {
        "servico": servico,
        "uf": uf,
        "ambiente": ambiente,
        "url": (url[:100] + "..." if url and len(url) > 100 else url),
        "status_http": status_http,
        "http_content_type": http_content_type or "não informado",
        "content_len": content_len,
        "body_preview_len": len(body_preview or ""),
    }
    if url_final and url_final != url:
        payload["url_final"] = (url_final[:100] + "..." if len(url_final) > 100 else url_final)
    if exception_type:
        payload["exception_type"] = exception_type
    if exception_msg:
        payload["exception_msg"] = (exception_msg[:300] + "..." if len(exception_msg) > 300 else exception_msg)
    payload.update(extra)
    snippet = (body_preview or "")[:500].replace("\n", " ").replace("\r", "")
    if snippet:
        payload["body_preview"] = snippet + ("..." if len(body_preview or "") > 500 else "")
    log_struct("SEFAZ transporte", level="warning" if exception_type or content_len == 0 else "info", **payload)


def _ssl_verify():
    """
    Retorna contexto SSL para a SEFAZ usando o CA correto (ICP-Brasil).
    - SEFAZ_SSL_VERIFY=false (env): desliga verificação (apenas homologação/desenvolvimento).
    - Caso contrário: usa certifi_icpbr (bundle com CAs Mozilla + ICP-Brasil), necessário
      para validar os certificados dos servidores SEFAZ.
    """
    if os.environ.get("SEFAZ_SSL_VERIFY", "").strip().lower() in ("0", "false", "no", "off"):
        return False
    try:
        import certifi_icpbr
        cafile = certifi_icpbr.where()
    except ImportError:
        try:
            import certifi
            cafile = certifi.where()
        except ImportError:
            return True
    ctx = ssl.create_default_context(cafile=cafile)
    return ctx

# URLs de autorização NF-e 4.0 por UF (homologação e produção).
# Fonte: manuais SEFAZ / Ambiente Nacional. Incluir outras UFs conforme necessidade.
_SEFAZ_AUTORIZACAO = {
    "AC": ("https://hnfe.sefaz.ac.gov.br/ws/NFeAutorizacao4", "https://nfe.sefaz.ac.gov.br/ws/NFeAutorizacao4"),
    "AL": ("https://hnfe.sefaz.al.gov.br/ws/NFeAutorizacao4", "https://nfe.sefaz.al.gov.br/ws/NFeAutorizacao4"),
    "AM": ("https://hnfe.sefaz.am.gov.br/ws/NFeAutorizacao4", "https://nfe.sefaz.am.gov.br/ws/NFeAutorizacao4"),
    "BA": ("https://hnfe.sefaz.ba.gov.br/ws/NFeAutorizacao4", "https://nfe.sefaz.ba.gov.br/ws/NFeAutorizacao4"),
    "CE": ("https://hnfe.sefaz.ce.gov.br/ws/NFeAutorizacao4", "https://nfe.sefaz.ce.gov.br/ws/NFeAutorizacao4"),
    "DF": ("https://hnfe.sefaz.df.gov.br/ws/NFeAutorizacao4", "https://nfe.sefaz.df.gov.br/ws/NFeAutorizacao4"),
    "ES": ("https://hnfe.sefaz.es.gov.br/ws/NFeAutorizacao4", "https://nfe.sefaz.es.gov.br/ws/NFeAutorizacao4"),
    "GO": ("https://hnfe.sefaz.go.gov.br/ws/NFeAutorizacao4", "https://nfe.sefaz.go.gov.br/ws/NFeAutorizacao4"),
    "MA": ("https://hnfe.sefaz.ma.gov.br/ws/NFeAutorizacao4", "https://nfe.sefaz.ma.gov.br/ws/NFeAutorizacao4"),
    "MG": ("https://hnfe.fazenda.mg.gov.br/nfe/ws/NFeAutorizacao4", "https://nfe.fazenda.mg.gov.br/nfe/ws/NFeAutorizacao4"),
    "MS": ("https://hom.nfe.sefaz.ms.gov.br/ws/NFeAutorizacao4", "https://nfe.sefaz.ms.gov.br/ws/NFeAutorizacao4"),
    "MT": ("https://hnfe.sefaz.mt.gov.br/ws/NFeAutorizacao4", "https://nfe.sefaz.mt.gov.br/ws/NFeAutorizacao4"),
    "PA": ("https://hnfe.sefaz.pa.gov.br/ws/NFeAutorizacao4", "https://nfe.sefaz.pa.gov.br/ws/NFeAutorizacao4"),
    "PB": ("https://hnfe.sefaz.pb.gov.br/ws/NFeAutorizacao4", "https://nfe.sefaz.pb.gov.br/ws/NFeAutorizacao4"),
    "PE": ("https://nfehomolog.sefaz.pe.gov.br/nfe-web-services/ws/NFeAutorizacao4", "https://nfe.sefaz.pe.gov.br/nfe-web-services/ws/NFeAutorizacao4"),
    "PI": ("https://hnfe.sefaz.pi.gov.br/ws/NFeAutorizacao4", "https://nfe.sefaz.pi.gov.br/ws/NFeAutorizacao4"),
    "PR": ("https://hnfe.sefaz.pr.gov.br/ws/NFeAutorizacao4", "https://nfe.sefaz.pr.gov.br/ws/NFeAutorizacao4"),
    "RJ": ("https://hnfe.fazenda.rj.gov.br/ws/NFeAutorizacao4", "https://nfe.fazenda.rj.gov.br/ws/NFeAutorizacao4"),
    "RN": ("https://hnfe.sefaz.rn.gov.br/ws/NFeAutorizacao4", "https://nfe.sefaz.rn.gov.br/ws/NFeAutorizacao4"),
    "RO": ("https://hnfe.sefaz.ro.gov.br/ws/NFeAutorizacao4", "https://nfe.sefaz.ro.gov.br/ws/NFeAutorizacao4"),
    "RR": ("https://hnfe.sefaz.rr.gov.br/ws/NFeAutorizacao4", "https://nfe.sefaz.rr.gov.br/ws/NFeAutorizacao4"),
    "RS": ("https://nfe-homologacao.sefaz.rs.gov.br/ws/NFeAutorizacao4", "https://nfe.sefaz.rs.gov.br/ws/NFeAutorizacao4"),
    "SC": ("https://hnfe.sefaz.sc.gov.br/ws/NFeAutorizacao4", "https://nfe.sefaz.sc.gov.br/ws/NFeAutorizacao4"),
    "SE": ("https://hnfe.sefaz.se.gov.br/ws/NFeAutorizacao4", "https://nfe.sefaz.se.gov.br/ws/NFeAutorizacao4"),
    "SP": ("https://homologacao.nfe.fazenda.sp.gov.br/ws/nfeautorizacao4.asmx", "https://nfe.fazenda.sp.gov.br/ws/nfeautorizacao4.asmx"),
    "TO": ("https://hnfe.sefaz.to.gov.br/ws/NFeAutorizacao4", "https://nfe.sefaz.to.gov.br/ws/NFeAutorizacao4"),
}

# Matriz SP — modelo 55 (NF-e) e 65 (NFC-e) separados. ambiente: 2=homologação, 1=produção
# Regra: modelo 55 → nfe.fazenda.sp.gov.br | modelo 65 → nfce.fazenda.sp.gov.br
_SP_ENDPOINTS = {
    55: {
        2: {
            "autorizacao": "https://homologacao.nfe.fazenda.sp.gov.br/ws/nfeautorizacao4.asmx",
            "ret_autorizacao": "https://homologacao.nfe.fazenda.sp.gov.br/ws/nferetautorizacao4.asmx",
            "status_servico": "https://homologacao.nfe.fazenda.sp.gov.br/ws/nfestatusservico4.asmx",
            "consulta_protocolo": "https://homologacao.nfe.fazenda.sp.gov.br/ws/nfeconsultaprotocolo4.asmx",
            "recepcao_evento": "https://homologacao.nfe.fazenda.sp.gov.br/ws/nferecepcaoevento4.asmx",
            "inutilizacao": "https://homologacao.nfe.fazenda.sp.gov.br/ws/nfeinutilizacao4.asmx",
            "consulta_cadastro": "https://homologacao.nfe.fazenda.sp.gov.br/ws/cadconsultacadastro4.asmx",
        },
        1: {
            "autorizacao": "https://nfe.fazenda.sp.gov.br/ws/nfeautorizacao4.asmx",
            "ret_autorizacao": "https://nfe.fazenda.sp.gov.br/ws/nferetautorizacao4.asmx",
            "status_servico": "https://nfe.fazenda.sp.gov.br/ws/nfestatusservico4.asmx",
            "consulta_protocolo": "https://nfe.fazenda.sp.gov.br/ws/nfeconsultaprotocolo4.asmx",
            "recepcao_evento": "https://nfe.fazenda.sp.gov.br/ws/nferecepcaoevento4.asmx",
            "inutilizacao": "https://nfe.fazenda.sp.gov.br/ws/nfeinutilizacao4.asmx",
            "consulta_cadastro": "https://nfe.fazenda.sp.gov.br/ws/cadconsultacadastro4.asmx",
        },
    },
    65: {
        2: {
            "autorizacao": "https://homologacao.nfce.fazenda.sp.gov.br/ws/NFeAutorizacao4.asmx",
            "ret_autorizacao": "https://homologacao.nfce.fazenda.sp.gov.br/ws/NFeRetAutorizacao4.asmx",
            "status_servico": "https://homologacao.nfce.fazenda.sp.gov.br/ws/NFeStatusServico4.asmx",
            "consulta_protocolo": "https://homologacao.nfce.fazenda.sp.gov.br/ws/NFeConsultaProtocolo4.asmx",
            "recepcao_evento": "https://homologacao.nfce.fazenda.sp.gov.br/ws/NFeRecepcaoEvento4.asmx",
            "inutilizacao": "https://homologacao.nfce.fazenda.sp.gov.br/ws/NFeInutilizacao4.asmx",
        },
        1: {
            "autorizacao": "https://nfce.fazenda.sp.gov.br/ws/NFeAutorizacao4.asmx",
            "ret_autorizacao": "https://nfce.fazenda.sp.gov.br/ws/NFeRetAutorizacao4.asmx",
            "status_servico": "https://nfce.fazenda.sp.gov.br/ws/NFeStatusServico4.asmx",
            "consulta_protocolo": "https://nfce.fazenda.sp.gov.br/ws/NFeConsultaProtocolo4.asmx",
            "recepcao_evento": "https://nfce.fazenda.sp.gov.br/ws/NFeRecepcaoEvento4.asmx",
            "inutilizacao": "https://nfce.fazenda.sp.gov.br/ws/NFeInutilizacao4.asmx",
        },
    },
}

# RetAutorizacao (consulta recibo) NF-e 4.0 - quando envio retorna 103 + nRec
_SEFAZ_RET_AUTORIZACAO = {
    "AC": ("https://hnfe.sefaz.ac.gov.br/ws/NFeRetAutorizacao4", "https://nfe.sefaz.ac.gov.br/ws/NFeRetAutorizacao4"),
    "AL": ("https://hnfe.sefaz.al.gov.br/ws/NFeRetAutorizacao4", "https://nfe.sefaz.al.gov.br/ws/NFeRetAutorizacao4"),
    "AM": ("https://hnfe.sefaz.am.gov.br/ws/NFeRetAutorizacao4", "https://nfe.sefaz.am.gov.br/ws/NFeRetAutorizacao4"),
    "BA": ("https://hnfe.sefaz.ba.gov.br/ws/NFeRetAutorizacao4", "https://nfe.sefaz.ba.gov.br/ws/NFeRetAutorizacao4"),
    "CE": ("https://hnfe.sefaz.ce.gov.br/ws/NFeRetAutorizacao4", "https://nfe.sefaz.ce.gov.br/ws/NFeRetAutorizacao4"),
    "DF": ("https://hnfe.sefaz.df.gov.br/ws/NFeRetAutorizacao4", "https://nfe.sefaz.df.gov.br/ws/NFeRetAutorizacao4"),
    "ES": ("https://hnfe.sefaz.es.gov.br/ws/NFeRetAutorizacao4", "https://nfe.sefaz.es.gov.br/ws/NFeRetAutorizacao4"),
    "GO": ("https://hnfe.sefaz.go.gov.br/ws/NFeRetAutorizacao4", "https://nfe.sefaz.go.gov.br/ws/NFeRetAutorizacao4"),
    "MA": ("https://hnfe.sefaz.ma.gov.br/ws/NFeRetAutorizacao4", "https://nfe.sefaz.ma.gov.br/ws/NFeRetAutorizacao4"),
    "MG": ("https://nfe.fazenda.mg.gov.br/nfe/ws/NFeRetAutorizacao4", "https://nfe.fazenda.mg.gov.br/nfe/ws/NFeRetAutorizacao4"),
    "MS": ("https://hom.nfe.sefaz.ms.gov.br/ws/NFeRetAutorizacao4", "https://nfe.sefaz.ms.gov.br/ws/NFeRetAutorizacao4"),
    "MT": ("https://hnfe.sefaz.mt.gov.br/ws/NFeRetAutorizacao4", "https://nfe.sefaz.mt.gov.br/ws/NFeRetAutorizacao4"),
    "PA": ("https://hnfe.sefaz.pa.gov.br/ws/NFeRetAutorizacao4", "https://nfe.sefaz.pa.gov.br/ws/NFeRetAutorizacao4"),
    "PB": ("https://hnfe.sefaz.pb.gov.br/ws/NFeRetAutorizacao4", "https://nfe.sefaz.pb.gov.br/ws/NFeRetAutorizacao4"),
    "PE": ("https://nfehomolog.sefaz.pe.gov.br/nfe-web-services/ws/NFeRetAutorizacao4", "https://nfe.sefaz.pe.gov.br/nfe-web-services/ws/NFeRetAutorizacao4"),
    "PI": ("https://hnfe.sefaz.pi.gov.br/ws/NFeRetAutorizacao4", "https://nfe.sefaz.pi.gov.br/ws/NFeRetAutorizacao4"),
    "PR": ("https://hnfe.sefaz.pr.gov.br/ws/NFeRetAutorizacao4", "https://nfe.sefaz.pr.gov.br/ws/NFeRetAutorizacao4"),
    "RJ": ("https://hnfe.fazenda.rj.gov.br/ws/NFeRetAutorizacao4", "https://nfe.fazenda.rj.gov.br/ws/NFeRetAutorizacao4"),
    "RN": ("https://hnfe.sefaz.rn.gov.br/ws/NFeRetAutorizacao4", "https://nfe.sefaz.rn.gov.br/ws/NFeRetAutorizacao4"),
    "RO": ("https://hnfe.sefaz.ro.gov.br/ws/NFeRetAutorizacao4", "https://nfe.sefaz.ro.gov.br/ws/NFeRetAutorizacao4"),
    "RR": ("https://hnfe.sefaz.rr.gov.br/ws/NFeRetAutorizacao4", "https://nfe.sefaz.rr.gov.br/ws/NFeRetAutorizacao4"),
    "RS": ("https://nfe-homologacao.sefaz.rs.gov.br/ws/NFeRetAutorizacao4", "https://nfe.sefaz.rs.gov.br/ws/NFeRetAutorizacao4"),
    "SC": ("https://hnfe.sefaz.sc.gov.br/ws/NFeRetAutorizacao4", "https://nfe.sefaz.sc.gov.br/ws/NFeRetAutorizacao4"),
    "SE": ("https://hnfe.sefaz.se.gov.br/ws/NFeRetAutorizacao4", "https://nfe.sefaz.se.gov.br/ws/NFeRetAutorizacao4"),
    "SP": ("https://homologacao.nfe.fazenda.sp.gov.br/ws/nferetautorizacao4.asmx", "https://nfe.fazenda.sp.gov.br/ws/nferetautorizacao4.asmx"),
    "TO": ("https://hnfe.sefaz.to.gov.br/ws/NFeRetAutorizacao4", "https://nfe.sefaz.to.gov.br/ws/NFeRetAutorizacao4"),
}

# Evento (cancelamento) NF-e 4.0
_SEFAZ_EVENTO = {
    "AC": ("https://hnfe.sefaz.ac.gov.br/ws/NFeRecepcaoEvento4", "https://nfe.sefaz.ac.gov.br/ws/NFeRecepcaoEvento4"),
    "AL": ("https://hnfe.sefaz.al.gov.br/ws/NFeRecepcaoEvento4", "https://nfe.sefaz.al.gov.br/ws/NFeRecepcaoEvento4"),
    "AM": ("https://hnfe.sefaz.am.gov.br/ws/NFeRecepcaoEvento4", "https://nfe.sefaz.am.gov.br/ws/NFeRecepcaoEvento4"),
    "BA": ("https://hnfe.sefaz.ba.gov.br/ws/NFeRecepcaoEvento4", "https://nfe.sefaz.ba.gov.br/ws/NFeRecepcaoEvento4"),
    "CE": ("https://hnfe.sefaz.ce.gov.br/ws/NFeRecepcaoEvento4", "https://nfe.sefaz.ce.gov.br/ws/NFeRecepcaoEvento4"),
    "DF": ("https://hnfe.sefaz.df.gov.br/ws/NFeRecepcaoEvento4", "https://nfe.sefaz.df.gov.br/ws/NFeRecepcaoEvento4"),
    "ES": ("https://hnfe.sefaz.es.gov.br/ws/NFeRecepcaoEvento4", "https://nfe.sefaz.es.gov.br/ws/NFeRecepcaoEvento4"),
    "GO": ("https://hnfe.sefaz.go.gov.br/ws/NFeRecepcaoEvento4", "https://nfe.sefaz.go.gov.br/ws/NFeRecepcaoEvento4"),
    "MA": ("https://hnfe.sefaz.ma.gov.br/ws/NFeRecepcaoEvento4", "https://nfe.sefaz.ma.gov.br/ws/NFeRecepcaoEvento4"),
    "MG": ("https://hnfe.fazenda.mg.gov.br/nfe/ws/NFeRecepcaoEvento4", "https://nfe.fazenda.mg.gov.br/nfe/ws/NFeRecepcaoEvento4"),
    "MS": ("https://hom.nfe.sefaz.ms.gov.br/ws/NFeRecepcaoEvento4", "https://nfe.sefaz.ms.gov.br/ws/NFeRecepcaoEvento4"),
    "MT": ("https://hnfe.sefaz.mt.gov.br/ws/NFeRecepcaoEvento4", "https://nfe.sefaz.mt.gov.br/ws/NFeRecepcaoEvento4"),
    "PA": ("https://hnfe.sefaz.pa.gov.br/ws/NFeRecepcaoEvento4", "https://nfe.sefaz.pa.gov.br/ws/NFeRecepcaoEvento4"),
    "PB": ("https://hnfe.sefaz.pb.gov.br/ws/NFeRecepcaoEvento4", "https://nfe.sefaz.pb.gov.br/ws/NFeRecepcaoEvento4"),
    "PE": ("https://nfehomolog.sefaz.pe.gov.br/nfe-web-services/ws/NFeRecepcaoEvento4", "https://nfe.sefaz.pe.gov.br/nfe-web-services/ws/NFeRecepcaoEvento4"),
    "PI": ("https://hnfe.sefaz.pi.gov.br/ws/NFeRecepcaoEvento4", "https://nfe.sefaz.pi.gov.br/ws/NFeRecepcaoEvento4"),
    "PR": ("https://hnfe.sefaz.pr.gov.br/ws/NFeRecepcaoEvento4", "https://nfe.sefaz.pr.gov.br/ws/NFeRecepcaoEvento4"),
    "RJ": ("https://hnfe.fazenda.rj.gov.br/ws/NFeRecepcaoEvento4", "https://nfe.fazenda.rj.gov.br/ws/NFeRecepcaoEvento4"),
    "RN": ("https://hnfe.sefaz.rn.gov.br/ws/NFeRecepcaoEvento4", "https://nfe.sefaz.rn.gov.br/ws/NFeRecepcaoEvento4"),
    "RO": ("https://hnfe.sefaz.ro.gov.br/ws/NFeRecepcaoEvento4", "https://nfe.sefaz.ro.gov.br/ws/NFeRecepcaoEvento4"),
    "RR": ("https://hnfe.sefaz.rr.gov.br/ws/NFeRecepcaoEvento4", "https://nfe.sefaz.rr.gov.br/ws/NFeRecepcaoEvento4"),
    "RS": ("https://nfe-homologacao.sefaz.rs.gov.br/ws/NFeRecepcaoEvento4", "https://nfe.sefaz.rs.gov.br/ws/NFeRecepcaoEvento4"),
    "SC": ("https://hnfe.sefaz.sc.gov.br/ws/NFeRecepcaoEvento4", "https://nfe.sefaz.sc.gov.br/ws/NFeRecepcaoEvento4"),
    "SE": ("https://hnfe.sefaz.se.gov.br/ws/NFeRecepcaoEvento4", "https://nfe.sefaz.se.gov.br/ws/NFeRecepcaoEvento4"),
    "SP": ("https://homologacao.nfe.fazenda.sp.gov.br/ws/nferecepcaoevento4.asmx", "https://nfe.fazenda.sp.gov.br/ws/nferecepcaoevento4.asmx"),
    "TO": ("https://hnfe.sefaz.to.gov.br/ws/NFeRecepcaoEvento4", "https://nfe.sefaz.to.gov.br/ws/NFeRecepcaoEvento4"),
}

# Namespace e ações SOAP NF-e 4.0
_NS_SOAP = "http://www.w3.org/2003/05/soap-envelope"
_NS_NFE = "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4"
_NS_NFE_RET = "http://www.portalfiscal.inf.br/nfe/wsdl/NFeRetAutorizacao4"
_NS_NFE_ACTION_AUT = "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"
_NS_NFE_ACTION_RET = "http://www.portalfiscal.inf.br/nfe/wsdl/NFeRetAutorizacao4/nfeRetAutorizacaoLote"
_NS_NFE_ACTION_EVT = "http://www.portalfiscal.inf.br/nfe/wsdl/NFeRecepcaoEvento4/nfeRecepcaoEvento"

# Timeout padrão (segundos)
DEFAULT_TIMEOUT = 30


def _normalizar_uf(uf: str) -> str:
    u = (uf or "").strip().upper()
    return u if len(u) == 2 else ""


def _ambiente_para_tp_amb(ambiente: str) -> int:
    """Retorna 2 (homologação) ou 1 (produção). Ambiente obrigatoriamente da Empresa Fiscal."""
    a = (ambiente or "").strip().lower()
    return 2 if a == "homologacao" else 1


def resolver_endpoint(
    uf: str,
    modelo: str,
    ambiente: str,
    servico: str,
    logar: bool = True,
) -> Optional[str]:
    """
    Resolve endpoint SEFAZ por (UF, modelo, ambiente, serviço).
    Ambiente deve vir obrigatoriamente da Empresa Fiscal.
    SP: modelo 55 → nfe; modelo 65 → nfce.
    """
    u = _normalizar_uf(uf)
    if not u:
        return None
    mod = int(re.sub(r"\D", "", str(modelo or "55")) or "55")
    if mod not in (55, 65):
        mod = 55
    tp_amb = _ambiente_para_tp_amb(ambiente)

    if u == "SP":
        if mod not in _SP_ENDPOINTS or tp_amb not in _SP_ENDPOINTS[mod]:
            return None
        svc = _SP_ENDPOINTS[mod][tp_amb].get(servico)
        if not svc:
            return None
        url = svc
    else:
        # Outras UFs: mesmo endpoint para 55 e 65
        if servico == "autorizacao" and u in _SEFAZ_AUTORIZACAO:
            hom, prod = _SEFAZ_AUTORIZACAO[u]
        elif servico == "ret_autorizacao" and u in _SEFAZ_RET_AUTORIZACAO:
            hom, prod = _SEFAZ_RET_AUTORIZACAO[u]
        elif servico == "recepcao_evento" and u in _SEFAZ_EVENTO:
            hom, prod = _SEFAZ_EVENTO[u]
        else:
            return None
        url = hom if tp_amb == 2 else prod

    if logar:
        log_struct(
            "NFE_ENDPOINT_RESOLVIDO",
            level="info",
            uf=u,
            modelo=mod,
            ambiente=tp_amb,
            servico=servico,
            endpoint=(url[:90] + "..." if len(url) > 90 else url),
        )
    return url


def validar_endpoint(modelo: int, endpoint: str) -> Tuple[bool, Optional[str]]:
    """
    Valida consistência: modelo 55 → host nfe; modelo 65 → host nfce; tpAmb → homologacao/producao.
    Retorna (True, None) ou (False, motivo_erro).
    """
    host = (urlparse(endpoint).hostname or "").lower()
    if modelo == 55 and "nfce.fazenda.sp.gov.br" in host and "nfe" not in host:
        return False, "modelo_55_em_endpoint_nfce"
    if modelo == 65 and "nfe.fazenda.sp.gov.br" in host and "nfce" not in host:
        return False, "modelo_65_em_endpoint_nfe"
    return True, None


def get_url_autorizacao(uf: str, ambiente: str, modelo: Optional[str] = None, logar: bool = True) -> Optional[str]:
    """Retorna URL de autorização. Ambiente obrigatoriamente da Empresa Fiscal."""
    return resolver_endpoint(uf, str(modelo or "55"), ambiente, "autorizacao", logar=logar)


def get_url_evento(uf: str, ambiente: str, modelo: Optional[str] = None, logar: bool = True) -> Optional[str]:
    """Retorna URL de recepção de evento. Ambiente obrigatoriamente da Empresa Fiscal."""
    return resolver_endpoint(uf, str(modelo or "55"), ambiente, "recepcao_evento", logar=logar)


def get_url_ret_autorizacao(uf: str, ambiente: str, modelo: Optional[str] = None, logar: bool = True) -> Optional[str]:
    """Retorna URL de retorno/autorização (consulta recibo). Ambiente obrigatoriamente da Empresa Fiscal."""
    return resolver_endpoint(uf, str(modelo or "55"), ambiente, "ret_autorizacao", logar=logar)


# Código IBGE UF para nfeCabecMsg (SEFAZ exige cUF; sem isso retorna 400)
_UF_CODIGO = {"AC": "12", "AL": "27", "AM": "13", "AP": "16", "BA": "29", "CE": "23", "DF": "53",
              "ES": "32", "GO": "52", "MA": "21", "MG": "31", "MS": "50", "MT": "51", "PA": "15",
              "PB": "25", "PE": "26", "PI": "22", "PR": "41", "RJ": "33", "RN": "24", "RO": "11",
              "RR": "14", "RS": "43", "SC": "42", "SE": "28", "SP": "35", "TO": "17"}


def _montar_envelope_autorizacao(xml_nfe: str, uf: str = "") -> str:
    """Monta envelope SOAP 1.2. nfeCabecMsg DEVE ter cUF e versaoDados (SEFAZ retorna 400 se faltar)."""
    cuf = _UF_CODIGO.get((uf or "SP").strip().upper(), "35")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<soap12:Envelope xmlns:soap12="{_NS_SOAP}">'
        "<soap12:Header>"
        f'<nfeCabecMsg xmlns="{_NS_NFE}"><cUF>{cuf}</cUF><versaoDados>4.00</versaoDados></nfeCabecMsg>'
        "</soap12:Header>"
        "<soap12:Body>"
        f'<nfeDadosMsg xmlns="{_NS_NFE}">{xml_nfe}</nfeDadosMsg>'
        "</soap12:Body>"
        "</soap12:Envelope>"
    )


_NS_NFE_EVENTO = "http://www.portalfiscal.inf.br/nfe/wsdl/NFeRecepcaoEvento4"


def _montar_envelope_ret_autorizacao(cons_reci_xml: str) -> str:
    """Monta envelope SOAP 1.2 para nfeRetAutorizacaoLote (consulta recibo)."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<soap12:Envelope xmlns:soap12="{_NS_SOAP}">'
        "<soap12:Header>"
        f'<nfeCabecMsg xmlns="{_NS_NFE_RET}"><versaoDados>4.00</versaoDados></nfeCabecMsg>'
        "</soap12:Header>"
        "<soap12:Body>"
        f'<nfeDadosMsg xmlns="{_NS_NFE_RET}">{cons_reci_xml}</nfeDadosMsg>'
        "</soap12:Body>"
        "</soap12:Envelope>"
    )


def _montar_envelope_evento(xml_evento: str) -> str:
    """Monta envelope SOAP 1.2 para nfeRecepcaoEvento (evento de cancelamento). Inclui nfeCabecMsg/versaoDados."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<soap12:Envelope xmlns:soap12="{_NS_SOAP}">'
        "<soap12:Header>"
        f'<nfeCabecMsg xmlns="{_NS_NFE_EVENTO}"><versaoDados>1.00</versaoDados></nfeCabecMsg>'
        "</soap12:Header>"
        "<soap12:Body>"
        f'<nfeDadosMsg xmlns="{_NS_NFE_EVENTO}">{xml_evento}</nfeDadosMsg>'
        "</soap12:Body>"
        "</soap12:Envelope>"
    )


def _response_text(response: Any) -> str:
    """Extrai texto da resposta; se response.text vazio, tenta decodificar response.content (incl. 4xx)."""
    text = (getattr(response, "text", None) or "").strip()
    if text:
        return text
    content = getattr(response, "content", None)
    if not content:
        return ""
    # Content-Type pode trazer charset (ex.: application/soap+xml; charset=iso-8859-1)
    ct = (getattr(response, "headers", None) or {}).get("content-type", "") if hasattr(response, "headers") else ""
    encodings = ["utf-8", "iso-8859-1", "latin-1", "cp1252"]
    if "charset=" in ct.lower():
        import re as _re
        m = _re.search(r"charset=([^\s;]+)", ct, _re.IGNORECASE)
        if m:
            encodings = [m.group(1).strip().strip('"').lower(), *encodings]
    for enc in encodings:
        try:
            return content.decode(enc, errors="replace").strip()
        except (LookupError, ValueError, UnicodeDecodeError):
            continue
    return content.decode("utf-8", errors="replace").strip()


def _extrair_cstat_xmotivo(resp_text: str) -> Tuple[Optional[str], Optional[str]]:
    """Extrai cStat e xMotivo do XML mesmo com namespace (regex fallback)."""
    if not (resp_text or "").strip():
        return None, None
    cstat_match = re.search(r"<[^>]*cStat[^>]*>([^<]+)</[^>]*cStat[^>]*>", resp_text, re.IGNORECASE)
    xmotivo_match = re.search(r"<[^>]*xMotivo[^>]*>([^<]+)</[^>]*xMotivo[^>]*>", resp_text, re.IGNORECASE)
    cstat = cstat_match.group(1).strip() if cstat_match else None
    xmotivo = xmotivo_match.group(1).strip() if xmotivo_match else None
    return cstat, xmotivo


def _parse_retorno_xml_lxml(resp_text: str) -> Optional[Dict[str, Any]]:
    """
    Parse retorno SEFAZ com lxml (namespace-aware). Prioriza protNFe.infProt sobre retEnviNFe.
    Retorna dict com: cstat_nf, xmotivo_nf, cstat_lote, xmotivo_lote, nrec, protocolo, chave.
    """
    if not (resp_text or "").strip():
        return None
    try:
        root = etree.fromstring(resp_text.encode("utf-8") if isinstance(resp_text, str) else resp_text)
    except Exception:
        return None
    ns = {"nfe": "http://www.portalfiscal.inf.br/nfe"}
    # Namespaces alternativos (SOAP Body pode encapsular)
    def _text(el, tag: str) -> Optional[str]:
        if el is None:
            return None
        # Local name match (ignore namespace)
        for child in el:
            if child.tag.endswith("}" + tag) or child.tag == tag:
                return (child.text or "").strip() or None
        return None

    def _find_all(root_el, path: str):
        try:
            return root_el.findall(path, namespaces=ns)
        except Exception:
            return []
    # Buscar protNFe/infProt (resultado da NF - prioridade)
    cstat_nf, xmotivo_nf, protocolo, chave = None, None, None, None
    for prot in root.iter():
        local = etree.QName(prot).localname if hasattr(prot, "tag") else ""
        if local == "infProt":
            cstat_nf = _text(prot, "cStat") or cstat_nf
            xmotivo_nf = _text(prot, "xMotivo") or xmotivo_nf
            protocolo = _text(prot, "nProt") or protocolo
            chave = _text(prot, "chNFe") or chave
    # Buscar retEnviNFe (lote: cStat, xMotivo, nRec)
    cstat_lote, xmotivo_lote, nrec = None, None, None
    for el in root.iter():
        local = etree.QName(el).localname if hasattr(el, "tag") else ""
        if local == "retEnviNFe":
            cstat_lote = _text(el, "cStat") or cstat_lote
            xmotivo_lote = _text(el, "xMotivo") or xmotivo_lote
            nrec = _text(el, "nRec") or nrec
            break
    for el in root.iter():
        local = etree.QName(el).localname if hasattr(el, "tag") else ""
        if local == "retConsReciNFe":
            cstat_lote = _text(el, "cStat") or cstat_lote
            xmotivo_lote = _text(el, "xMotivo") or xmotivo_lote
            break
    # nRec pode vir em retEnviNFe
    if not nrec:
        nrec_match = re.search(r"<[^>]*nRec[^>]*>([^<]+)</[^>]*nRec[^>]*>", resp_text, re.IGNORECASE)
        nrec = nrec_match.group(1).strip() if nrec_match else None
    if not protocolo:
        prot_match = re.search(r"<[^>]*nProt[^>]*>([^<]+)</[^>]*nProt[^>]*>", resp_text, re.IGNORECASE)
        protocolo = prot_match.group(1).strip() if prot_match else None
    if not chave:
        chave_match = re.search(r"<[^>]*chNFe[^>]*>([^<]+)</[^>]*chNFe[^>]*>", resp_text, re.IGNORECASE)
        chave = chave_match.group(1).strip() if chave_match else None
    return {
        "cstat_nf": cstat_nf,
        "xmotivo_nf": xmotivo_nf,
        "cstat_lote": cstat_lote,
        "xmotivo_lote": xmotivo_lote,
        "nrec": nrec,
        "protocolo": protocolo,
        "chave": chave,
    }


def _parse_retorno_regex_fallback(resp_text: str) -> Dict[str, Any]:
    """Fallback regex quando lxml falha."""
    cstat, xmotivo = _extrair_cstat_xmotivo(resp_text)
    prot_match = re.search(r"<[^>]*nProt[^>]*>([^<]+)</[^>]*nProt[^>]*>", resp_text, re.IGNORECASE)
    chave_match = re.search(r"<[^>]*chNFe[^>]*>([^<]+)</[^>]*chNFe[^>]*>", resp_text, re.IGNORECASE)
    nrec_match = re.search(r"<[^>]*nRec[^>]*>([^<]+)</[^>]*nRec[^>]*>", resp_text, re.IGNORECASE)
    return {
        "cstat_nf": cstat,
        "xmotivo_nf": xmotivo,
        "cstat_lote": cstat,
        "xmotivo_lote": xmotivo,
        "nrec": nrec_match.group(1).strip() if nrec_match else None,
        "protocolo": prot_match.group(1).strip() if prot_match else None,
        "chave": chave_match.group(1).strip() if chave_match else None,
    }


def _classificar_tipo_resultado(parsed: Dict[str, Any], erro_tecnico: Optional[str] = None) -> str:
    if erro_tecnico:
        return "erro_tecnico"
    cstat_nf = parsed.get("cstat_nf")
    cstat_lote = parsed.get("cstat_lote")
    nrec = parsed.get("nrec")
    cstat_efetivo = cstat_nf or cstat_lote
    if cstat_efetivo in ("100", "101", "135"):
        return "autorizada"
    if cstat_nf and cstat_nf not in ("103", "104"):
        return "rejeitada"
    if cstat_lote == "103" and nrec:
        return "lote_recebido"
    if cstat_lote == "104":
        return "lote_processado"
    if cstat_nf or cstat_lote or parsed.get("xmotivo_nf") or parsed.get("xmotivo_lote"):
        return "rejeitada"
    return "resposta_invalida"


def _extrair_retorno_autorizacao_enriquecido(resp_text: str) -> Dict[str, Any]:
    """
    Interpreta resposta SOAP da autorização. Prioriza protNFe.infProt sobre retEnviNFe.
    Retorna dict com: sucesso, protocolo, chave, mensagem, cstat, xmotivo, nrec, tipo_resultado.
    cstat preferido: protNFe.infProt.cStat > retEnviNFe.cStat
    """
    result = {
        "sucesso": False,
        "protocolo": None,
        "chave": None,
        "mensagem": None,
        "cstat": None,
        "xmotivo": None,
        "nrec": None,
        "tipo_resultado": "resposta_invalida",
        "cstat_nf": None,
        "cstat_lote": None,
    }
    if not (resp_text or "").strip():
        result["mensagem"] = "Resposta vazia da SEFAZ"
        result["tipo_resultado"] = "resposta_vazia"
        return result
    parsed = _parse_retorno_xml_lxml(resp_text)
    if not parsed:
        parsed = _parse_retorno_regex_fallback(resp_text)
    cstat_nf = parsed.get("cstat_nf")
    cstat_lote = parsed.get("cstat_lote")
    xmotivo_nf = parsed.get("xmotivo_nf")
    xmotivo_lote = parsed.get("xmotivo_lote")
    result["cstat_nf"] = cstat_nf
    result["cstat_lote"] = cstat_lote
    result["cstat"] = str(cstat_nf) if cstat_nf else (str(cstat_lote) if cstat_lote else None)
    result["xmotivo"] = (xmotivo_nf or xmotivo_lote or "").strip() or None
    result["nrec"] = parsed.get("nrec")
    result["protocolo"] = parsed.get("protocolo")
    result["chave"] = parsed.get("chave")
    result["tipo_resultado"] = _classificar_tipo_resultado(parsed)
    xmotivo_texto = result["xmotivo"] or "Sem mensagem"
    if result["tipo_resultado"] == "autorizada":
        result["sucesso"] = True
        result["mensagem"] = None
        return result
    if result["tipo_resultado"] == "rejeitada":
        result["mensagem"] = f"{result['cstat'] or '?'} - {xmotivo_texto}"
        return result
    if result["tipo_resultado"] == "lote_recebido":
        result["mensagem"] = f"Lote recebido pela SEFAZ. Recibo: {result['nrec']}. Aguardando processamento"
        return result
    if result["tipo_resultado"] == "lote_processado":
        result["mensagem"] = (
            "Lote processado pela SEFAZ, mas sem resultado final identificável no retorno. "
            "Verifique a tentativa de envio."
        )
        return result
    fault_str = re.search(r"<faultstring[^>]*>([^<]+)</faultstring>", resp_text, re.IGNORECASE)
    if fault_str:
        result["tipo_resultado"] = "rejeitada"
        result["mensagem"] = f"SEFAZ (SOAP Fault): {fault_str.group(1).strip()}"
        return result
    fault_reason = re.search(
        r"<fault:Reason[^>]*>.*?<fault:Text>([^<]+)</fault:Text>",
        resp_text,
        re.DOTALL | re.IGNORECASE,
    )
    if fault_reason:
        result["tipo_resultado"] = "rejeitada"
        result["mensagem"] = f"SEFAZ (SOAP Fault): {fault_reason.group(1).strip()}"
        return result
    snippet = (resp_text.strip()[:500]).replace("\n", " ").replace("\r", "")
    if len(resp_text.strip()) > 500:
        snippet += "..."
    result["mensagem"] = (
        "A SEFAZ não autorizou a nota. O motivo detalhado não foi informado. "
        "Verifique a tentativa de envio (resposta_bruta em nfe_tentativa_envio)."
    )
    return result


def _formatar_mensagem_cliente_enriquecida(parsed: Dict[str, Any], erro_tecnico: Optional[str] = None) -> str:
    """Formata mensagem final para o cliente conforme tipo_resultado."""
    if erro_tecnico:
        return f"Falha técnica na comunicação com a SEFAZ: {erro_tecnico}"
    tipo = parsed.get("tipo_resultado", "resposta_invalida")
    msg = parsed.get("mensagem")
    if tipo == "autorizada":
        return ""
    if tipo == "rejeitada" and msg:
        cstat = parsed.get("cstat")
        xmotivo = parsed.get("xmotivo") or "Rejeição pela SEFAZ"
        return f"Rejeição {cstat or '?'}: {xmotivo}"
    if tipo in ("lote_recebido", "lote_processado"):
        return msg or ""
    return msg or (
        "A SEFAZ não autorizou a nota. O motivo detalhado não foi informado. "
        "Verifique a tentativa de envio (resposta_bruta em nfe_tentativa_envio)."
    )


def _mensagem_rejeicao_para_cliente(
    msg_tecnica: Optional[str],
    status_http: Optional[int],
    resp_text: str,
) -> str:
    """
    Retorna mensagem para o CLIENTE (não técnica). Nunca exibir HTTP 400 ou jargão.
    Usado como fallback legado; preferir _formatar_mensagem_cliente_enriquecida.
    """
    cstat, xmotivo = _extrair_cstat_xmotivo(resp_text or "")
    if cstat or xmotivo:
        motivo = (xmotivo or "").strip() or "Rejeição pela SEFAZ"
        return f"Rejeição {cstat or '?'}: {motivo}"
    if msg_tecnica and ("faultstring" in (msg_tecnica or "").lower() or "SOAP Fault" in (msg_tecnica or "")):
        return msg_tecnica
    return (
        "A SEFAZ não autorizou a nota. O motivo detalhado não foi informado. "
        "Verifique a tentativa de envio (resposta_bruta em nfe_tentativa_envio)."
    )


def _extrair_retorno_autorizacao(resp_text: str) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
    """
    Interpreta resposta SOAP da autorização. Retorna (sucesso, protocolo, chave, mensagem_erro).
    Usa _extrair_retorno_autorizacao_enriquecido internamente (compatibilidade).
    """
    p = _extrair_retorno_autorizacao_enriquecido(resp_text)
    return p["sucesso"], p["protocolo"], p["chave"], p["mensagem"]


def _extrair_retorno_evento(resp_text: str) -> Tuple[bool, Optional[str]]:
    """Interpreta resposta SOAP do evento (cancelamento). Retorna (sucesso, mensagem_erro)."""
    if not resp_text:
        return False, "Resposta vazia da SEFAZ"
    cstat_match = re.search(r"<cStat>([^<]+)</cStat>", resp_text)
    xmotivo_match = re.search(r"<xMotivo>([^<]+)</xMotivo>", resp_text)
    cstat = cstat_match.group(1).strip() if cstat_match else ""
    xmotivo = xmotivo_match.group(1).strip() if xmotivo_match else "Sem mensagem"
    sucesso = cstat in ("135", "101", "573")  # evento registrado / cancelamento
    return sucesso, None if sucesso else f"{cstat} - {xmotivo}"


def consultar_recibo_nfe(
    uf: str,
    ambiente: str,
    nrec: str,
    timeout: int = DEFAULT_TIMEOUT,
    cert_pem: Optional[bytes] = None,
    key_pem: Optional[bytes] = None,
    modelo: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Consulta resultado do recibo (quando envio retornou 103 + nRec).
    Em SP, modelo 65 (NFC-e) usa webservice nfce.fazenda.sp.gov.br.
    Retorna mesmo formato de enviar_nfe_autorizacao.
    """
    url = get_url_ret_autorizacao(uf, ambiente, modelo)
    if not url:
        return {"sucesso": False, "mensagem": f"UF {uf!r} ou ambiente não suportado para consulta recibo"}
    tp_amb = "2" if (ambiente or "").strip().lower() == "homologacao" else "1"
    ns = "http://www.portalfiscal.inf.br/nfe"
    cons_reci = f'<consReciNFe xmlns="{ns}" versao="4.00"><tpAmb>{tp_amb}</tpAmb><nRec>{nrec}</nRec></consReciNFe>'
    envelope = _montar_envelope_ret_autorizacao(cons_reci)
    try:
        import httpx
        headers = {"Content-Type": "application/soap+xml; charset=utf-8", "SOAPAction": _NS_NFE_ACTION_RET}
        verify_ctx = _ssl_verify()
        if cert_pem and key_pem:
            cert_f = tempfile.NamedTemporaryFile(mode="wb", suffix=".pem", delete=False)
            key_f = tempfile.NamedTemporaryFile(mode="wb", suffix=".pem", delete=False)
            try:
                cert_f.write(cert_pem if isinstance(cert_pem, bytes) else cert_pem.encode("utf-8"))
                key_f.write(key_pem if isinstance(key_pem, bytes) else key_pem.encode("utf-8"))
                cert_f.close()
                key_f.close()
                with httpx.Client(timeout=timeout, verify=verify_ctx, cert=(cert_f.name, key_f.name)) as client:
                    response = client.post(url, content=envelope.encode("utf-8"), headers=headers)
            finally:
                try:
                    os.unlink(cert_f.name)
                    os.unlink(key_f.name)
                except OSError:
                    pass
        else:
            with httpx.Client(timeout=timeout, verify=verify_ctx) as client:
                response = client.post(url, content=envelope.encode("utf-8"), headers=headers)
        resp_text = _response_text(response)
        status_code = getattr(response, "status_code", None)
        content_type = (response.headers.get("content-type") or "").strip().split(";")[0].strip() if hasattr(response, "headers") else None
        parsed = _extrair_retorno_autorizacao_enriquecido(resp_text)
        msg_cli = _formatar_mensagem_cliente_enriquecida(parsed) if not parsed["sucesso"] else None
        return {
            "sucesso": parsed["sucesso"],
            "protocolo": parsed["protocolo"],
            "chave": parsed["chave"],
            "mensagem": msg_cli,
            "raw_response": resp_text,
            "status_http": status_code,
            "http_content_type": content_type,
            "cstat": parsed.get("cstat"),
            "xmotivo": parsed.get("xmotivo"),
            "nrec": nrec,
            "tipo_resultado": parsed.get("tipo_resultado"),
            "erro_tecnico": None,
            "url": url,
            "ambiente_sefaz": ambiente,
        }
    except Exception as e:
        err_str = str(e)[:500]
        log_struct("SEFAZ consulta recibo falhou", level="warning", servico="nfe_consulta_recibo", uf=uf, ambiente=ambiente, erro=err_str)
        return {
            "sucesso": False,
            "mensagem": f"Falha técnica na comunicação com a SEFAZ: {err_str}",
            "raw_response": None,
            "status_http": None,
            "http_content_type": None,
            "cstat": None,
            "xmotivo": None,
            "nrec": nrec,
            "tipo_resultado": "erro_tecnico",
            "erro_tecnico": err_str,
            "url": url,
            "ambiente_sefaz": ambiente,
        }


def enviar_nfe_autorizacao(
    uf: str,
    ambiente: str,
    xml_assinado: str,
    timeout: int = DEFAULT_TIMEOUT,
    cert_pem: Optional[bytes] = None,
    key_pem: Optional[bytes] = None,
    nota_id: Optional[int] = None,
    modelo: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Envia NF-e/NFC-e (XML já assinado) para autorização na SEFAZ.
    uf: sigla 2 letras; ambiente: 'homologacao' ou 'producao'; modelo: 55 (NF-e) ou 65 (NFC-e).
    Em SP, modelo 65 usa webservice nfce.fazenda.sp.gov.br.
    Retorna dict com: sucesso, protocolo, chave, mensagem, raw_response (opcional).
    """
    url = get_url_autorizacao(uf, ambiente, modelo)
    if not url:
        return {"sucesso": False, "mensagem": f"UF {uf!r} ou ambiente não suportado"}
    mod_int = int(re.sub(r"\D", "", str(modelo or "55")) or "55")
    if mod_int not in (55, 65):
        mod_int = 55
    ok_val, motivo = validar_endpoint(mod_int, url)
    host = (urlparse(url).hostname or "").lower()
    log_struct(
            "NFE_ENDPOINT_VALIDACAO",
            level="warning" if not ok_val else "info",
            modelo=mod_int,
            host=host,
            status="erro" if not ok_val else "ok",
            motivo=motivo if not ok_val else None,
        )
    if not ok_val:
        return {"sucesso": False, "mensagem": f"Inconsistência de endpoint: {motivo}. Modelo {mod_int} não pode usar esse webservice."}
    envelope = _montar_envelope_autorizacao(xml_assinado, uf)
    if nota_id and nfe_logging.NFE_LOGS_DIR:
        try:
            d = nfe_logging._dir_nota(nota_id)
            (d / "envelope_request.xml").write_text(envelope, encoding="utf-8")
        except Exception:
            pass
    status_code = None
    t0 = time.perf_counter()
    started_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:23] + "Z"
    nfe_logging.log_nfe_http_request(
            metodo="POST",
            url=url,
            content_type="application/soap+xml; charset=utf-8",
            timeout=timeout,
            started_at=started_at,
        )
    try:
        import httpx
        headers = {
            "Content-Type": "application/soap+xml; charset=utf-8",
            "SOAPAction": _NS_NFE_ACTION_AUT,
        }
        # Confirmação pré-envio (endpoint nfce para modelo 65, Content-Type, nfeCabecMsg)
        host = (urlparse(url).hostname or "").lower()
        log_struct(
            "SEFAZ_REQUEST_CONFIRM",
            level="info",
            url=url,
            host=host,
            modelo=mod_int,
            endpoint_nfce_ok=("nfce" in host or mod_int != 65),
            content_type=headers["Content-Type"],
            nfeCabecMsg_tem_cUF=True,
            nfeCabecMsg_tem_versaoDados=True,
        )
        verify_ctx = _ssl_verify()
        # SEFAZ exige mTLS (certificado A1): sem client cert retorna 403 Forbidden
        if cert_pem and key_pem:
            cert_f = tempfile.NamedTemporaryFile(mode="wb", suffix=".pem", delete=False)
            key_f = tempfile.NamedTemporaryFile(mode="wb", suffix=".pem", delete=False)
            try:
                cert_f.write(cert_pem if isinstance(cert_pem, bytes) else cert_pem.encode("utf-8"))
                key_f.write(key_pem if isinstance(key_pem, bytes) else key_pem.encode("utf-8"))
                cert_f.close()
                key_f.close()
                with httpx.Client(
                    timeout=timeout,
                    verify=verify_ctx,
                    cert=(cert_f.name, key_f.name),
                ) as client:
                    response = client.post(url, content=envelope.encode("utf-8"), headers=headers)
            finally:
                try:
                    os.unlink(cert_f.name)
                    os.unlink(key_f.name)
                except OSError:
                    pass
        else:
            with httpx.Client(timeout=timeout, verify=verify_ctx) as client:
                response = client.post(url, content=envelope.encode("utf-8"), headers=headers)
        status_code = getattr(response, "status_code", None)
        resp_headers = getattr(response, "headers", None) or {}
        raw_bytes = getattr(response, "content", None) or b""
        resp_text = _response_text(response)
        # PASSO 2: Log retorno bruto ANTES de qualquer parse (body pode ser HTML, SOAP Fault, texto)
        log_struct(
            "SEFAZ_RESPONSE_BRUTO",
            level="info",
            status_code=status_code,
            headers=dict(resp_headers),
            body_len=len(raw_bytes),
            body_preview=(resp_text[:2000] if resp_text else "(vazio)"),
            url=url,
        )
        content_type = (resp_headers.get("content-type") or "").strip().split(";")[0].strip()
        reason = getattr(response, "reason_phrase", None) or (getattr(response, "http_version", None) and "OK") or "N/A"
        duracao_ms = int((time.perf_counter() - t0) * 1000)
        url_final = str(getattr(response, "url", url) or url)
        resp_preview = resp_text[:TRANSPORT_LOG_BODY_PREVIEW] if resp_text else None
        response_dump_path = None
        if nota_id and nfe_logging.NFE_LOGS_DIR:
            try:
                d = nfe_logging._dir_nota(nota_id)
                (d / "response.raw").write_bytes(raw_bytes)
                try:
                    headers_dict = dict(resp_headers) if resp_headers else {}
                except Exception:
                    headers_dict = {}
                (d / "response_headers.json").write_text(
                    json.dumps(headers_dict, ensure_ascii=False),
                    encoding="utf-8",
                )
                response_dump_path = str(d / "response.raw")
            except Exception:
                pass
        nfe_logging.log_nfe_http_response(
            status_code=status_code,
            reason=reason,
            content_type=content_type or "não informado",
            response_bytes=len(raw_bytes),
            body_prefix=resp_preview[:1000] if resp_preview else None,
            response_dump=response_dump_path,
        )
        _log_sefaz_transport(
            servico="nfe_autorizacao",
            uf=uf,
            ambiente=ambiente,
            url=url,
            status_http=status_code,
            http_content_type=content_type,
            content_len=len(raw_bytes),
            body_preview=resp_preview,
            url_final=url_final if url_final != url else None,
            duracao_ms=duracao_ms,
        )
        # Em 4xx com corpo vazio, forçar leitura direta de content
        if (not resp_text or not resp_text.strip()) and raw_bytes:
            for enc in ("utf-8", "iso-8859-1", "latin-1", "cp1252"):
                try:
                    resp_text = raw_bytes.decode(enc, errors="replace").strip()
                    if resp_text:
                        break
                except Exception:
                    pass
    except Exception as e:
        duracao_ms = int((time.perf_counter() - t0) * 1000)
        err_str = str(e)[:500]
        exc_type = type(e).__name__
        nfe_logging.log_nfe_exception(
            exc_type=exc_type,
            exc_message=err_str,
            endpoint=url,
            elapsed_ms=duracao_ms,
        )
        if nota_id and nfe_logging.NFE_LOGS_DIR:
            try:
                d = nfe_logging._dir_nota(nota_id)
                (d / "exception.txt").write_text(f"{exc_type}: {err_str}", encoding="utf-8")
            except Exception:
                pass
        _log_sefaz_transport(
            servico="nfe_autorizacao",
            uf=uf,
            ambiente=ambiente,
            url=url,
            status_http=None,
            http_content_type=None,
            content_len=0,
            body_preview=None,
            url_final=None,
            exception_type=exc_type,
            exception_msg=err_str,
            tipo_resultado="erro_tecnico",
            duracao_ms=duracao_ms,
        )
        log_struct(
            "SEFAZ envio NFe autorização falhou (conexão)",
            level="warning",
            servico="nfe_autorizacao",
            uf=uf,
            ambiente=ambiente,
            erro=err_str,
            exception_type=exc_type,
            tipo_resultado="erro_tecnico",
        )
        msg_cli = _formatar_mensagem_cliente_enriquecida({}, erro_tecnico=err_str)
        return {
            "sucesso": False,
            "mensagem": msg_cli,
            "status_http": None,
            "http_content_type": None,
            "raw_response": None,
            "raw_response_preview": None,
            "cstat": None,
            "xmotivo": None,
            "nrec": None,
            "protocolo": None,
            "chave": None,
            "tipo_resultado": "erro_tecnico",
            "erro_tecnico": err_str,
            "url": url,
            "ambiente_sefaz": ambiente,
        }
    parsed = _extrair_retorno_autorizacao_enriquecido(resp_text)
    # F. Log de parse (xml_parse_ok, soap_envelope, soap_fault, ret_autorizacao_node)
    has_cstat = bool(parsed.get("cstat_nf") or parsed.get("cstat_lote"))
    soap_env = bool(resp_text and ("envelope" in resp_text.lower() or "soap" in resp_text.lower()))
    soap_fault = "SOAP Fault" in (parsed.get("mensagem") or "")
    parse_ok = has_cstat or bool(parsed.get("protocolo") or parsed.get("chave"))
    nfe_logging.log_nfe_parse(
        xml_parse_ok=parse_ok,
        soap_envelope=soap_env,
        soap_fault=soap_fault,
        ret_autorizacao_node=has_cstat,
    )
    if nota_id and nfe_logging.NFE_LOGS_DIR:
        try:
            d = nfe_logging._dir_nota(nota_id)
            pr_safe = {k: str(v)[:200] if v is not None else None for k, v in parsed.items()}
            (d / "parse_result.json").write_text(json.dumps(pr_safe, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
    # Resposta vazia (resposta_vazia) ou corpo vazio: enriquecer mensagem com diagnóstico
    if parsed.get("tipo_resultado") == "resposta_vazia":
        parts = [
            f"Resposta vazia da SEFAZ (HTTP {status_code or '?'}",
            f"Content-Type: {content_type or 'não informado'})",
        ]
        if status_code == 401:
            parts.append("Certificado pode estar inválido ou rejeitado.")
        elif status_code == 403:
            parts.append("Acesso negado (certificado ou ambiente incorreto).")
        elif status_code in (502, 503, 504):
            parts.append("SEFAZ indisponível ou timeout no intermediário.")
        elif status_code == 200:
            parts.append("Corpo vazio com 200 OK pode indicar proxy/firewall ou erro de rede.")
        parts.append("Verifique nfe_tentativa_envio para detalhes.")
        parsed["mensagem"] = " ".join(parts)
    if (
        parsed.get("tipo_resultado") == "lote_recebido"
        and parsed.get("nrec")
        and cert_pem
        and key_pem
    ):
        time.sleep(2)
        ret_cons = consultar_recibo_nfe(uf, ambiente, parsed["nrec"], timeout=timeout, cert_pem=cert_pem, key_pem=key_pem, modelo=modelo)
        if ret_cons.get("tipo_resultado") in ("autorizada", "rejeitada"):
            parsed = {
                "sucesso": ret_cons.get("sucesso", False),
                "protocolo": ret_cons.get("protocolo"),
                "chave": ret_cons.get("chave"),
                "mensagem": ret_cons.get("mensagem"),
                "cstat": ret_cons.get("cstat"),
                "xmotivo": ret_cons.get("xmotivo"),
                "nrec": parsed.get("nrec"),
                "tipo_resultado": ret_cons.get("tipo_resultado"),
            }
            resp_text = ret_cons.get("raw_response") or resp_text
            status_code = ret_cons.get("status_http") or status_code
            content_type = ret_cons.get("http_content_type") or content_type
    msg_cli = _formatar_mensagem_cliente_enriquecida(parsed) if not parsed.get("sucesso") else None
    raw_preview = (resp_text[:RAW_RESPONSE_PREVIEW_LEN] + ("..." if len(resp_text) > RAW_RESPONSE_PREVIEW_LEN else "")) if resp_text else None
    log_struct(
        "SEFAZ resultado NFe autorização",
        level="info",
        servico="nfe_autorizacao",
        uf=uf,
        ambiente=ambiente,
        url=(url[:80] + "..." if url and len(url) > 80 else url),
        status_http=status_code,
        http_content_type=content_type,
        sucesso=parsed.get("sucesso", False),
        mensagem_trecho=(msg_cli[:120] if msg_cli else None),
        cstat=parsed.get("cstat"),
        xmotivo_trecho=(parsed.get("xmotivo") or "")[:80],
        nrec=parsed.get("nrec"),
        tipo_resultado=parsed.get("tipo_resultado"),
        raw_response_preview_len=len(raw_preview or ""),
    )
    return {
        "sucesso": parsed["sucesso"],
        "protocolo": parsed["protocolo"],
        "chave": parsed["chave"],
        "mensagem": msg_cli if not parsed["sucesso"] else None,
        "raw_response": resp_text,
        "raw_response_preview": raw_preview,
        "status_http": status_code,
        "http_content_type": content_type,
        "cstat": parsed.get("cstat"),
        "xmotivo": parsed.get("xmotivo"),
        "nrec": parsed.get("nrec"),
        "tipo_resultado": parsed.get("tipo_resultado"),
        "erro_tecnico": None,
        "url": url,
        "ambiente_sefaz": ambiente,
    }


def enviar_evento_cancelamento(
    uf: str,
    ambiente: str,
    xml_evento_assinado: str,
    timeout: int = DEFAULT_TIMEOUT,
    cert_pem: Optional[bytes] = None,
    key_pem: Optional[bytes] = None,
    modelo: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Envia evento de cancelamento (XML do evento já assinado).
    Em SP, modelo 65 (NFC-e) usa webservice nfce.fazenda.sp.gov.br.
    Retorna dict com: sucesso, mensagem.
    """
    url = get_url_evento(uf, ambiente, modelo)
    if not url:
        return {"sucesso": False, "mensagem": f"UF {uf!r} ou ambiente não suportado para evento"}
    envelope = _montar_envelope_evento(xml_evento_assinado)
    try:
        import httpx
        headers = {
            "Content-Type": "application/soap+xml; charset=utf-8",
            "SOAPAction": _NS_NFE_ACTION_EVT,
        }
        verify_ctx = _ssl_verify()
        if cert_pem and key_pem:
            cert_f = tempfile.NamedTemporaryFile(mode="wb", suffix=".pem", delete=False)
            key_f = tempfile.NamedTemporaryFile(mode="wb", suffix=".pem", delete=False)
            try:
                cert_f.write(cert_pem if isinstance(cert_pem, bytes) else cert_pem.encode("utf-8"))
                key_f.write(key_pem if isinstance(key_pem, bytes) else key_pem.encode("utf-8"))
                cert_f.close()
                key_f.close()
                with httpx.Client(timeout=timeout, verify=verify_ctx, cert=(cert_f.name, key_f.name)) as client:
                    response = client.post(url, content=envelope.encode("utf-8"), headers=headers)
            finally:
                try:
                    os.unlink(cert_f.name)
                    os.unlink(key_f.name)
                except OSError:
                    pass
        else:
            with httpx.Client(timeout=timeout, verify=verify_ctx) as client:
                response = client.post(url, content=envelope.encode("utf-8"), headers=headers)
        resp_text = _response_text(response)
        status_code = getattr(response, "status_code", None)
        content_type = (response.headers.get("content-type") or "").strip().split(";")[0].strip() if hasattr(response, "headers") else None
    except Exception as e:
        log_struct("SEFAZ envio evento cancelamento falhou (conexão)", level="warning", servico="nfe_evento", uf=uf, ambiente=ambiente, erro=str(e)[:200])
        return {"sucesso": False, "mensagem": f"Erro de conexão: {e}", "status_http": None, "http_content_type": None}
    ok, msg = _extrair_retorno_evento(resp_text)
    log_struct("SEFAZ resultado evento cancelamento", level="info", servico="nfe_evento", uf=uf, ambiente=ambiente, status_http=status_code, http_content_type=content_type, sucesso=ok)
    return {"sucesso": ok, "mensagem": msg, "status_http": status_code, "http_content_type": content_type, "raw_response": resp_text}
