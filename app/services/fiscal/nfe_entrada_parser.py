# PDV Ibix - Parser XML NF-e (entrada de compras)
"""
Extrai dados do XML de NF-e 4.0 (padrão brasileiro SEFAZ) para popular nfe_documentos e nfe_itens.
Layout: Manual de Orientação do Contribuinte (MOC), NT 2016.002, leiaute NFe 4.0.
Namespace oficial: http://www.portalfiscal.inf.br/nfe
Estrutura: NFe > infNFe (ide, emit, dest, det, total); total contém ICMSTot (vNF, vProd, etc.).
"""
from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

try:
    from lxml import etree
except ImportError:
    etree = None  # type: ignore

NS = "http://www.portalfiscal.inf.br/nfe"
NSMAP = {"nfe": NS}

logger = logging.getLogger(__name__)


def _text(el: Optional[Any], default: str = "") -> str:
    if el is None or not hasattr(el, "text"):
        return default
    return (el.text or "").strip()


def _decimal(el: Optional[Any]) -> Optional[Decimal]:
    if el is None:
        return None
    t = _text(el)
    if not t:
        return None
    try:
        return Decimal(t.replace(",", "."))
    except Exception:
        return None


def _find(node: Any, path: str):
    if etree is None:
        return None
    return node.find(path, namespaces=NSMAP)


def _findall(node: Any, path: str):
    if etree is None:
        return []
    return node.findall(path, namespaces=NSMAP)


def _qty_from_prod(prod: Any, n_item: str) -> Optional[Decimal]:
    """Obtém quantidade do elemento prod: tenta qCom/qTrib com namespace e sem (NFe 4.0 e 3.10)."""
    qcom = _decimal(_find(prod, "nfe:qCom")) or _decimal(_find(prod, "nfe:qTrib"))
    if qcom is not None:
        return qcom
    if etree is not None and hasattr(prod, "find"):
        # Fallback: tag com namespace explícito (lxml)
        for tag in ("qCom", "qTrib"):
            el = prod.find(f"{{{NS}}}{tag}")
            if el is not None:
                q = _decimal(el)
                if q is not None:
                    return q
        # Fallback: tag sem namespace (alguns XMLs)
        for tag in ("qCom", "qTrib"):
            el = prod.find(tag)
            if el is not None:
                q = _decimal(el)
                if q is not None:
                    return q
        # Fallback: descendentes (ex.: prod com estrutura aninhada)
        for tag in ("qCom", "qTrib"):
            el = prod.find(f".//{{{NS}}}{tag}") or prod.find(f".//{tag}")
            if el is not None:
                q = _decimal(el)
                if q is not None:
                    return q
    return None


def parse_nfe_xml(xml_content: str | bytes) -> Dict[str, Any]:
    """
    Parseia XML de NF-e 4.0 e retorna estrutura para nfe_documentos + nfe_itens.
    Levanta ValueError se o XML for inválido ou não for NF-e.
    """
    if etree is None:
        raise RuntimeError("lxml é necessário para importar NF-e. pip install lxml")

    if isinstance(xml_content, str):
        xml_content = xml_content.encode("utf-8")

    try:
        root = etree.fromstring(xml_content)
    except etree.XMLSyntaxError as e:
        raise ValueError(f"XML inválido ou corrompido: {e}") from e

    root_local = etree.QName(root).localname
    if root_local in (
        "procEventoNFe",
        "retEventoNFe",
        "procEventoCTe",
        "retEventoCTe",
        "envEvento",
        "retEnvEvento",
        "evento",
    ):
        raise ValueError(
            "Este arquivo é de evento fiscal (cancelamento, carta de correção etc.), não o XML da NF-e. "
            "Importe o XML da nota autorizada (NFe ou nfeProc com infNFe)."
        )

    inf = _find(root, ".//nfe:infNFe")
    if inf is None:
        inf = root.find(f".//{{{NS}}}infNFe")
    if inf is None:
        raise ValueError(
            "Elemento infNFe não encontrado. O arquivo precisa ser o XML da NF-e (modelo 55/65), "
            "não DANFE/PDF, resumo de compra nem XML de evento."
        )

    # Chave 44: do Id do infNFe (ex: NFe431...)
    id_attr = (inf.get("Id") or "").strip()
    if id_attr.upper().startswith("NFE"):
        chave_acesso_44 = id_attr[3:47] if len(id_attr) >= 47 else id_attr[3:]
    else:
        chave_acesso_44 = id_attr[:44] if len(id_attr) >= 44 else ""

    if len(chave_acesso_44) != 44:
        # Fallback: montar chave a partir de ide+emit (padrão NFe 4.0: cUF(2)+AAMM(4)+CNPJ(14)+mod(2)+serie(3)+nNF(9)+tpEmis(1)+cNF(8)+cDV(1))
        ide_fb = _find(inf, "nfe:ide")
        if ide_fb is None:
            ide_fb = inf.find(f"{{{NS}}}ide")
        if ide_fb is not None:
            c_uf = _text(_find(ide_fb, "nfe:cUF")).zfill(2)[:2]
            dh_emi = _text(_find(ide_fb, "nfe:dhEmi"))
            aamm = ""
            if dh_emi:
                # dhEmi formato ISO: YYYY-MM-DDThh:mm:ss; AAMM = YYMM (4 dígitos)
                aamm_raw = dh_emi[:7].replace("-", "")  # YYYYMM
                aamm = (aamm_raw[2:6] if len(aamm_raw) >= 6 else aamm_raw)
            emit_fb = _find(inf, "nfe:emit")
            if emit_fb is None:
                emit_fb = inf.find(f"{{{NS}}}emit")
            cnpj_raw = _text(_find(emit_fb, "nfe:CNPJ")) if emit_fb is not None else ""
            cnpj = "".join(c for c in cnpj_raw if c.isdigit())[:14].zfill(14)
            mod = _text(_find(ide_fb, "nfe:mod")).zfill(2)[:2]
            serie = _text(_find(ide_fb, "nfe:serie")).zfill(3)[:3]
            nnf = _text(_find(ide_fb, "nfe:nNF")).zfill(9)[:9]
            if c_uf and aamm and len(cnpj) == 14 and mod and nnf:
                chave_acesso_44 = f"{c_uf}{aamm}{cnpj}{mod}{serie}{nnf}1000000000"[:44]

    if len(chave_acesso_44) != 44:
        raise ValueError("Não foi possível obter chave de acesso de 44 dígitos")

    ide = _find(inf, "nfe:ide")
    if ide is None:
        ide = inf.find(f"{{{NS}}}ide")
    emit = _find(inf, "nfe:emit")
    if emit is None:
        emit = inf.find(f"{{{NS}}}emit")
    dest = _find(inf, "nfe:dest")
    if dest is None:
        dest = inf.find(f"{{{NS}}}dest")
    total_el = _find(inf, "nfe:total")
    if total_el is None:
        total_el = inf.find(f"{{{NS}}}total")

    # ide
    modelo = _text(_find(ide, "nfe:mod")) if ide is not None else ""
    serie = _text(_find(ide, "nfe:serie")) if ide is not None else ""
    numero = _text(_find(ide, "nfe:nNF")) if ide is not None else ""
    dh_emi = _text(_find(ide, "nfe:dhEmi")) if ide is not None else ""
    tp_nf = _text(_find(ide, "nfe:tpNF")) or "0"  # 0=entrada, 1=saída; ausente/VAZIO trata como entrada
    tp_amb = _text(_find(ide, "nfe:tpAmb"))  # 1=produção, 2=homologação

    emissao_em: Optional[datetime] = None
    if dh_emi:
        try:
            from dateutil import parser as date_parser
            emissao_em = date_parser.parse(dh_emi)
        except Exception:
            try:
                emissao_em = datetime.fromisoformat(dh_emi.replace("Z", "+00:00"))
            except Exception:
                pass

    entrada_saida = "ENTRADA" if tp_nf == "0" else "SAIDA"
    ambiente = "HOMOLOGACAO" if tp_amb == "2" else "PRODUCAO"

    # emit (CNPJ, razão; telefone opcional em enderEmit/fone — MOC NFe 4.0)
    emitente_cnpj = ""
    emitente_razao = ""
    emitente_fone = ""
    if emit is not None:
        emitente_cnpj = _text(_find(emit, "nfe:CNPJ")) or _text(_find(emit, "nfe:CPF")) or ""
        emitente_razao = _text(_find(emit, "nfe:xNome")) or _text(_find(emit, "nfe:xFant")) or ""
        ender_emit = _find(emit, "nfe:enderEmit")
        if ender_emit is None:
            ender_emit = emit.find(f"{{{NS}}}enderEmit")
        if ender_emit is not None:
            emitente_fone = _text(_find(ender_emit, "nfe:fone"))
            if not emitente_fone and etree is not None:
                el_f = ender_emit.find(f"{{{NS}}}fone")
                if el_f is not None:
                    emitente_fone = _text(el_f)
                if not emitente_fone:
                    el_f2 = ender_emit.find("fone")
                    if el_f2 is not None:
                        emitente_fone = _text(el_f2)

    # total (padrão NFe 4.0: total > ICMSTot > vProd, vNF, etc.)
    icms_tot = None
    if total_el is not None:
        icms_tot = _find(total_el, "nfe:ICMSTot")
        if icms_tot is None:
            icms_tot = total_el.find(f"{{{NS}}}ICMSTot")
    total_produtos = _decimal(_find(icms_tot, "nfe:vProd")) if icms_tot is not None else None
    total_nota = _decimal(_find(icms_tot, "nfe:vNF")) if icms_tot is not None else None

    doc = {
        "chave_acesso_44": chave_acesso_44,
        "modelo": modelo or "55",
        "serie": serie,
        "numero": numero,
        "emissao_em": emissao_em,
        "entrada_saida": entrada_saida,
        "ambiente": ambiente,
        "emitente_cnpj": emitente_cnpj,
        "emitente_razao": emitente_razao,
        "emitente_fone": (emitente_fone or "").strip() or None,
        "total_produtos": total_produtos,
        "total_nota": total_nota,
    }

    # det/itens
    itens: List[Dict[str, Any]] = []
    dets = _findall(inf, "nfe:det")
    if not dets:
        dets = inf.findall(f"{{{NS}}}det")
    for det in dets:
        # Atributo do det: nItem (padrão NFe 4.0 - número do item)
        n_item = (det.get("nItem") or det.get("nitem") or "").strip() or str(len(itens) + 1)
        prod = _find(det, "nfe:prod")
        if prod is None:
            prod = det.find(f"{{{NS}}}prod")
        if prod is None:
            continue

        cprod = _text(_find(prod, "nfe:cProd"))
        xprod = _text(_find(prod, "nfe:xProd"))
        ean = _text(_find(prod, "nfe:cEAN")) or _text(_find(prod, "nfe:cEANTrib"))
        if ean == "0000000000000" or ean == "SEM GTIN":
            ean = None
        ncm = _text(_find(prod, "nfe:NCM"))
        cfop = _text(_find(prod, "nfe:CFOP"))
        # Layout NFe 4.0 (MOC SEFAZ): det/prod — uCom, uTrib, qCom, qTrib
        ucom = _text(_find(prod, "nfe:uCom")) or _text(_find(prod, "nfe:uTrib"))
        qcom = _qty_from_prod(prod, n_item)
        if qcom is None:
            logger.debug(
                "NFe item nItem=%s: quantidade (qCom/qTrib) não encontrada no XML; cProd=%s",
                n_item,
                cprod,
            )
        vuncom = _decimal(_find(prod, "nfe:vUnCom")) or _decimal(_find(prod, "nfe:vUnTrib"))
        vprod = _decimal(_find(prod, "nfe:vProd"))
        vdesc = _decimal(_find(prod, "nfe:vDesc"))
        vfrete = _decimal(_find(prod, "nfe:vFrete"))
        vseg = _decimal(_find(prod, "nfe:vSeg"))
        voutro = _decimal(_find(prod, "nfe:vOutro"))
        cest = _text(_find(prod, "nfe:CEST")) or None
        extipi = _text(_find(prod, "nfe:EXTIPI")) or None
        infadprod = _text(_find(det, "nfe:infAdProd")) or None
        if infadprod:
            infadprod = infadprod[:500] if len(infadprod) > 500 else infadprod  # limite 500 chars

        # Impostos (por item)
        vipi = None
        vicmsst = None
        orig_xml = None
        imp = _find(det, "nfe:imposto")
        if imp is None:
            imp = det.find(f"{{{NS}}}imposto")
        if imp is not None:
            ipi = _find(imp, "nfe:IPI")
            if ipi is None:
                ipi = imp.find(f"{{{NS}}}IPI")
            if ipi is not None:
                ipi_trib = _find(ipi, "nfe:IPITrib")
                if ipi_trib is None:
                    ipi_trib = ipi.find(f"{{{NS}}}IPITrib")
                if ipi_trib is not None:
                    vipi = _decimal(_find(ipi_trib, "nfe:vIPI"))
            icms = _find(imp, "nfe:ICMS")
            if icms is None:
                icms = imp.find(f"{{{NS}}}ICMS")
            if icms is not None:
                for tag in ("ICMS00", "ICMS10", "ICMS20", "ICMS30", "ICMS40", "ICMS51", "ICMS60", "ICMS70", "ICMS90", "ICMSPart", "ICMSST"):
                    st_el = _find(icms, f"nfe:{tag}")
                    if st_el is None:
                        st_el = icms.find(f"{{{NS}}}{tag}")
                    if st_el is not None:
                        if orig_xml is None:
                            orig_str = _text(_find(st_el, "nfe:orig"))
                            if orig_str and orig_str.isdigit():
                                o = int(orig_str)
                                orig_xml = o if 0 <= o <= 8 else None
                        if vicmsst is None:
                            vicmsst = _decimal(_find(st_el, "nfe:vBCST")) or _decimal(_find(st_el, "nfe:vICMSST"))

        itens.append({
            "numero_item": int(n_item) if n_item.isdigit() else len(itens) + 1,
            "cprod_xml": cprod or None,
            "xprod_xml": xprod or None,
            "ean_xml": ean,
            "ncm_xml": ncm or None,
            "cfop_xml": cfop or None,
            "ucom_xml": ucom or None,
            "qcom_xml": qcom,
            "vuncom_xml": vuncom,
            "vprod_xml": vprod,
            "vdesc_xml": vdesc,
            "vfrete_xml": vfrete,
            "vseg_xml": vseg,
            "voutro_xml": voutro,
            "vipi_xml": vipi,
            "vicmsst_xml": vicmsst,
            "cest_xml": (cest[:10] if cest else None) or None,
            "extipi_xml": (extipi[:5] if extipi else None) or None,
            "infadprod_xml": infadprod or None,
            "orig_xml": orig_xml,
        })

    doc["itens"] = itens
    return doc
