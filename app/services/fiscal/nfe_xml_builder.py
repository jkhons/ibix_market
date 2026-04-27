# PDV Ibix - Gerador de XML NF-e 4.0
"""
Monta o XML da NF-e no layout 4.0 (infNFe: ide, emit, dest, det, total)
a partir do payload produzido por _payload_nota_fiscal e dados da empresa/destinatário.
Namespace: http://www.portalfiscal.inf.br/nfe
"""
import base64
import hashlib
import random
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

_NS_NFE = "http://www.portalfiscal.inf.br/nfe"

# URL base NFC-e (qrCode + urlChave). Schema: urlChave maxLength=85.
_NFCE_URL_CONSULTA = {
    "SP": {
        2: "https://www.homologacao.nfce.fazenda.sp.gov.br/qrcode",
        1: "https://www.nfce.fazenda.sp.gov.br/NFCeConsultaPublica/Paginas/ConsultaQRCode.aspx",
    },
}

_NFCE_URL_CHAVE = _NFCE_URL_CONSULTA  # mesmo base

# Código IBGE da UF (2 dígitos) para cUF no XML
_UF_PARA_CODIGO = {
    "AC": "12", "AL": "27", "AM": "13", "AP": "16", "BA": "29", "CE": "23", "DF": "53",
    "ES": "32", "GO": "52", "MA": "21", "MG": "31", "MS": "50", "MT": "51", "PA": "15",
    "PB": "25", "PE": "26", "PI": "22", "PR": "41", "RJ": "33", "RN": "24", "RO": "11",
    "RR": "14", "RS": "43", "SC": "42", "SE": "28", "SP": "35", "TO": "17",
}


def _digito_verificador_chave(chave_43: str) -> str:
    """Calcula o dígito verificador (módulo 11) da chave NF-e (43 dígitos).
    Pesos 2-9 aplicados da direita para a esquerda conforme spec NF-e."""
    pesos = [2, 3, 4, 5, 6, 7, 8, 9]
    soma = sum(int(c) * pesos[i % 8] for i, c in enumerate(reversed(chave_43)))
    resto = soma % 11
    if resto in (0, 1):
        return "0"
    return str(11 - resto)


def _apenas_digitos(val: Any, tamanho: int, default: str) -> str:
    """Extrai só dígitos do valor e preenche até o tamanho (evita int('R') quando serie/número têm letras)."""
    if val is None or val == "":
        s = default
    else:
        s = re.sub(r"\D", "", str(val))
    return (s or default).zfill(tamanho)[:tamanho]


def _gerar_chave_nfe(
    cuf: str,
    aamm: str,
    cnpj: str,
    modelo: str,
    serie: str,
    nnf: str,
    tp_emis: str,
    cnf: Optional[str] = None,
) -> str:
    """
    Gera chave NF-e 44 dígitos: cUF(2) + AAMM(4) + CNPJ(14) + mod(2) + serie(3) + nNF(9) + tpEmis(1) + cNF(8) + cDV(1).
    Campos numéricos são sanitizados (apenas dígitos) para evitar int('R') quando série/número contêm letras.
    """
    cnpj_num = _apenas_digitos(cnpj, 14, "0")
    serie_num = _apenas_digitos(serie, 3, "1")
    nnf_num = _apenas_digitos(nnf, 9, "1")
    cnf_num = _apenas_digitos(cnf, 8, str(random.randint(1, 99999999)))
    cuf_num = _UF_PARA_CODIGO.get((cuf or "SP").strip().upper(), "35")
    aamm_num = _apenas_digitos(aamm, 4, "0000")
    mod_num = _apenas_digitos(modelo, 2, "55")
    tp_emis_num = _apenas_digitos(tp_emis, 1, "1")
    chave_43 = f"{cuf_num}{aamm_num}{cnpj_num}{mod_num}{serie_num}{nnf_num}{tp_emis_num}{cnf_num}"
    return chave_43 + _digito_verificador_chave(chave_43)


def _escape_xml(text: Optional[str]) -> str:
    if text is None:
        return ""
    s = str(text)
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&apos;")


def _decimal_xml(val: Any) -> str:
    if val is None or val == "":
        return "0.00"
    try:
        return f"{float(val):.2f}"
    except (TypeError, ValueError):
        return "0.00"


_TZ_SP = timezone(timedelta(hours=-3))


def _formatar_data_iso(dt: Any) -> str:
    """Formato ISO 8601 para SEFAZ: AAAA-MM-DDThh:mm:ss-03:00 (sem fração de segundos).
    Converte UTC → SP (-03:00) automaticamente para datetimes naive (assume UTC) ou aware."""
    if dt is None:
        return ""
    if hasattr(dt, "strftime"):
        if hasattr(dt, "tzinfo") and dt.tzinfo is not None:
            dt_sp = dt.astimezone(_TZ_SP)
        else:
            dt_sp = dt.replace(tzinfo=timezone.utc).astimezone(_TZ_SP)
        return dt_sp.strftime("%Y-%m-%dT%H:%M:%S-03:00")
    s = str(dt).strip()
    if "T" in s:
        data_part = s.split("T")[0]
        hora_part = s.split("T")[1].split(".")[0].split("+")[0].split("Z")[0]
        if "-" not in hora_part[-6:] and "+" not in hora_part:
            return f"{data_part}T{hora_part}-03:00"[:25]
    return s[:25]


def _cnpj_cpf_num(doc: Optional[str]) -> str:
    if not doc:
        return ""
    return re.sub(r"\D", "", doc)


def _codigo_ibge_7(val: Any) -> str:
    """Retorna código IBGE do município com 7 dígitos (ou 0000000 se inválido)."""
    if val is None or val == "":
        return "0000000"
    s = str(val).strip().replace(".", "").replace("-", "")
    s = re.sub(r"\D", "", s)
    if not s:
        return "0000000"
    return s.zfill(7)[:7]


def _digest_value_infnfe(inf_nfe_xml: str) -> str:
    """Calcula DigestValue do infNFe (C14N, SHA256, base64) para cHashQRCode NFC-e."""
    try:
        from lxml import etree
        root = etree.fromstring(inf_nfe_xml.encode("utf-8"))
        inf = root if "infNFe" in (root.tag or "").split("}")[-1] else root.find(".//{http://www.portalfiscal.inf.br/nfe}infNFe")
        if inf is None:
            for el in root.iter():
                if el.tag and "infNFe" in (el.tag.split("}")[-1] if "}" in str(el.tag) else el.tag):
                    inf = el
                    break
        if inf is None:
            return ""
        c14n = etree.tostring(
            inf,
            method="c14n",
            exclusive=True,
            with_comments=False,
            inclusive_ns_prefixes=[],
        )
        digest = hashlib.sha256(c14n).digest()
        return base64.b64encode(digest).decode("ascii")
    except Exception:
        return ""


def _chash_qrcode_nfce(
    chave: str,
    tp_amb: str,
    csc_id: str,
    csc_token: str,
) -> str:
    """
    Calcula cHashQRCode para NFC-e ONLINE (v2, tpEmis=1).
    SHA-1 puro de: chNFe|2|tpAmb|cIdCSC + CSC (token concatenado sem separador).
    Resultado: hex uppercase 40 caracteres.
    Ref: Manual DANFE NFC-e QR Code v5.0, p.21.
    """
    csc_id_trim = str(csc_id or "1").lstrip("0") or "1"
    param_str = f"{chave}|2|{tp_amb}|{csc_id_trim}"
    hash_input = param_str + (csc_token or "")
    return hashlib.sha1(hash_input.encode("utf-8")).hexdigest().upper()


def _build_infnfesupl_nfce(
    chave: str,
    tp_amb: str,
    csc_id: str,
    csc_token: str,
    uf: str,
) -> str:
    """Monta infNFeSupl (qrCode + urlChave) para NFC-e modelo 65, QR Code v2 online."""
    tp_amb_int = "1" if str(tp_amb).strip() == "1" else "2"
    csc_id_trim = str(csc_id or "1").lstrip("0") or "1"
    c_hash = _chash_qrcode_nfce(chave, tp_amb_int, csc_id, csc_token)
    params = f"{chave}|2|{tp_amb_int}|{csc_id_trim}|{c_hash}"
    urls = _NFCE_URL_CONSULTA.get((uf or "SP").strip().upper(), _NFCE_URL_CONSULTA.get("SP", {}))
    url_base = urls.get(1 if tp_amb_int == "1" else 2) if isinstance(urls, dict) else ""
    if not url_base:
        url_base = "https://www.nfce.fazenda.sp.gov.br/NFCeConsultaPublica/Paginas/ConsultaQRCode.aspx"
    url_chave = _NFCE_URL_CHAVE.get((uf or "SP").strip().upper(), {}).get(1 if tp_amb_int == "1" else 2) or url_base
    url_qr = f"{url_base}?p={params}"
    return f"<infNFeSupl><qrCode>{_escape_xml(url_qr)}</qrCode><urlChave>{_escape_xml(url_chave)}</urlChave></infNFeSupl>"


def _simples_nacional(crt: Any) -> bool:
    """CRT 1 ou 2 = Simples Nacional; 3 = Regime Normal."""
    if crt is None:
        return False
    try:
        c = int(crt)
        return c in (1, 2)
    except (TypeError, ValueError):
        return False


def montar_nfe(
    payload: Dict[str, Any],
    empresa: Dict[str, Any],
    destinatario: Optional[Dict[str, Any]],
    chave_override: Optional[str] = None,
) -> str:
    """
    Monta o XML do documento NF-e (raiz NFe, infNFe com ide, emit, dest, det, total).
    Retorna string XML sem assinatura (a assinatura será inserida pelo assinador).
    O payload é o retorno de _payload_nota_fiscal; empresa e destinatario são dicts do payload.
    chave_override: se informada (44 dígitos), usa esta chave no XML (ex.: nota já autorizada).
    """
    itens = payload.get("itens") or []

    cuf = str(empresa.get("uf") or "SP").strip().upper()[:2]
    cnpj_emit = _cnpj_cpf_num(empresa.get("cnpj") or "")
    if len(cnpj_emit) != 14:
        cnpj_emit = cnpj_emit.zfill(14)[:14]
    data_emissao = payload.get("data_emissao") or ""
    if hasattr(data_emissao, "isoformat"):
        data_emissao = data_emissao.isoformat()
    if data_emissao and len(data_emissao) >= 7:
        yyyymm = data_emissao[:7].replace("-", "")
        aamm = yyyymm[2:6] if len(yyyymm) >= 6 else datetime.utcnow().strftime("%y%m")
    else:
        aamm = datetime.utcnow().strftime("%y%m")
    modelo = str(payload.get("modelo") or "55").zfill(2)[:2]
    serie_raw = str(re.sub(r"\D", "", str(payload.get("serie") or "1")) or "1")
    serie = serie_raw.lstrip("0") or "1"
    nnf_raw = str(re.sub(r"\D", "", str(payload.get("numero") or "1")) or "1")
    nnf = nnf_raw.lstrip("0") or "1"
    chave_limpa = re.sub(r"\D", "", (chave_override or "").strip())
    chave = (chave_limpa[:44].zfill(44)) if len(chave_limpa) >= 44 else _gerar_chave_nfe(cuf, aamm, cnpj_emit, modelo, serie, nnf, "1")

    # ide
    nat_op = _escape_xml(payload.get("natureza_operacao") or "Venda")
    dh_emi = _formatar_data_iso(payload.get("data_emissao"))
    dh_sai = _formatar_data_iso(payload.get("data_saida")) or dh_emi
    tp_amb = "2" if (str(payload.get("ambiente") or "").lower() == "homologacao") else "1"
    ver_proc = "PDV_SOLUMATICA_1.0"

    cuf_codigo = _UF_PARA_CODIGO.get(cuf, "35")
    sb_ide = [
        f'<cUF>{cuf_codigo}</cUF>',
        f'<cNF>{chave[-9:-1]}</cNF>',
        f'<natOp>{nat_op}</natOp>',
        f'<mod>{modelo}</mod>',
        f'<serie>{serie}</serie>',
        f'<nNF>{nnf}</nNF>',
        f'<dhEmi>{dh_emi}</dhEmi>',
        *([] if modelo == "65" else [f'<dhSaiEnt>{dh_sai}</dhSaiEnt>']),
        '<tpNF>1</tpNF>',  # 1=saída
        '<idDest>1</idDest>',
        f"<cMunFG>{_codigo_ibge_7(empresa.get('municipio_ibge'))}</cMunFG>",
        f'<tpImp>{"4" if modelo == "65" else "1"}</tpImp>',  # 4=NFC-e; 1=NF-e DANFe Retrato
        '<tpEmis>1</tpEmis>',
        f'<cDV>{chave[-1]}</cDV>',
        f'<tpAmb>{tp_amb}</tpAmb>',
        '<finNFe>1</finNFe>',
        '<indFinal>1</indFinal>',
        '<indPres>1</indPres>',
        '<procEmi>0</procEmi>',
        f'<verProc>{_escape_xml(ver_proc)}</verProc>',
    ]
    xml_ide = "<ide>" + "".join(sb_ide) + "</ide>"

    # emit
    x_nome = _escape_xml(empresa.get("razao_social") or empresa.get("nome_fantasia") or "")
    x_fant = _escape_xml(empresa.get("nome_fantasia") or "")
    end = empresa.get("endereco") or ""
    nro = empresa.get("numero") or "S/N"
    x_bairro = (empresa.get("bairro") or "").strip() or "S/N"
    c_mun = _codigo_ibge_7(empresa.get("municipio_ibge"))
    x_mun = _escape_xml(empresa.get("cidade") or "")
    uf_emit = (empresa.get("uf") or cuf).strip().upper()[:2]
    cep = _cnpj_cpf_num(empresa.get("cep")) or "00000000"
    cep = cep.zfill(8)[:8]
    sb_ender = [
        f'<xLgr>{_escape_xml(end)}</xLgr>',
        f'<nro>{_escape_xml(str(nro))}</nro>',
        f'<xBairro>{_escape_xml(x_bairro)}</xBairro>',
        f'<cMun>{c_mun}</cMun>',
        f'<xMun>{x_mun}</xMun>',
        f'<UF>{uf_emit}</UF>',
        f'<CEP>{cep}</CEP>',
        '<cPais>1058</cPais>',
        '<xPais>Brasil</xPais>',
        f'<fone>{_escape_xml(empresa.get("telefone") or "")}</fone>',
    ]
    xml_ender_emit = "<enderEmit>" + "".join(sb_ender) + "</enderEmit>"
    ie_emit_raw = re.sub(r"\D", "", str(empresa.get("ie") or ""))[:14]
    ie_emit = ie_emit_raw or "ISENTO"
    # CRT: 1=Simples, 2=Simples excedente, 3=Regime Normal; só dígitos 1-3 (evita "R" ou texto)
    _crt_raw = empresa.get("crt")
    try:
        _c = int(_crt_raw) if _crt_raw is not None else 1
        crt = str(max(1, min(3, _c)))
    except (TypeError, ValueError):
        crt = "1"
    xml_emit = (
        "<emit>"
        f'<CNPJ>{cnpj_emit}</CNPJ>'
        f'<xNome>{x_nome}</xNome>'
        f'<xFant>{x_fant}</xFant>'
        f"{xml_ender_emit}"
        f'<IE>{ie_emit}</IE>'
        f'<CRT>{crt}</CRT>'
        "</emit>"
    )

    # dest
    if destinatario:
        cpf_dest = _cnpj_cpf_num(destinatario.get("cpf"))
        cnpj_dest = _cnpj_cpf_num(destinatario.get("cnpj"))
        if len(cnpj_dest) == 14:
            tag_doc = f'<CNPJ>{cnpj_dest}</CNPJ>'
        elif len(cpf_dest) == 11:
            tag_doc = f'<CPF>{cpf_dest}</CPF>'
        else:
            tag_doc = '<CPF>00000000000</CPF>'
        # Homologação: xNome deve ser literal exata (rej. 598)
        x_nome_dest = (
            "NF-E EMITIDA EM AMBIENTE DE HOMOLOGACAO - SEM VALOR FISCAL"
            if tp_amb == "2"
            else _escape_xml(destinatario.get("nome") or destinatario.get("razao_social") or "CONSUMIDOR FINAL")
        )
        end_dest = _escape_xml(destinatario.get("endereco") or "")
        cep_dest = _cnpj_cpf_num(destinatario.get("cep")) or "00000000"
        cep_dest = cep_dest.zfill(8)[:8]
        uf_dest = (destinatario.get("uf") or "SP").strip().upper()[:2]
        nro_dest = str(destinatario.get("numero") or "0").strip() or "S/N"
        x_bairro_dest = _escape_xml((destinatario.get("bairro") or "").strip() or "S/N")
        c_mun_dest = _codigo_ibge_7(destinatario.get("municipio_ibge"))
        x_mun_dest = _escape_xml(destinatario.get("cidade") or "")
        if c_mun_dest == "0000000":
            c_mun_dest = _codigo_ibge_7(empresa.get("municipio_ibge"))
            x_mun_dest = x_mun_dest or _escape_xml(empresa.get("cidade") or "")
            if c_mun_dest == "0000000":
                c_mun_dest, x_mun_dest = "3550308", "Sao Paulo"  # Fallback SP
        ie_dest = (destinatario.get("ie") or "").strip()
        ind_ie_dest = "1" if ie_dest else "9"
        ie_tag = f'<IE>{_escape_xml(ie_dest)}</IE>' if ind_ie_dest == "1" else ""
        xml_dest = (
            "<dest>"
            f"{tag_doc}"
            f'<xNome>{x_nome_dest}</xNome>'
            "<enderDest>"
            f'<xLgr>{end_dest}</xLgr>'
            f"<nro>{_escape_xml(nro_dest)}</nro>"
            f"<xBairro>{x_bairro_dest}</xBairro>"
            f"<cMun>{c_mun_dest}</cMun>"
            f"<xMun>{x_mun_dest}</xMun>"
            f'<UF>{uf_dest}</UF>'
            f'<CEP>{cep_dest}</CEP>'
            "<cPais>1058</cPais>"
            "<xPais>Brasil</xPais>"
            "</enderDest>"
            f"<indIEDest>{ind_ie_dest}</indIEDest>"
            f"{ie_tag}"
            "</dest>"
        )
    else:
        if modelo == "65":
            xml_dest = ""
        else:
            c_mun_cf = _codigo_ibge_7(empresa.get("municipio_ibge"))
            x_mun_cf = _escape_xml(empresa.get("cidade") or "")
            uf_cf = (empresa.get("uf") or cuf or "SP").strip().upper()[:2]
            if c_mun_cf == "0000000":
                c_mun_cf = "3550308"
                x_mun_cf = x_mun_cf or "Sao Paulo"
            x_nome_cf = "NF-E EMITIDA EM AMBIENTE DE HOMOLOGACAO - SEM VALOR FISCAL" if tp_amb == "2" else "CONSUMIDOR FINAL"
            xml_dest = (
                "<dest>"
                "<CPF>00000000000</CPF>"
                f"<xNome>{x_nome_cf}</xNome>"
                "<enderDest>"
                f"<xLgr>Consumidor</xLgr><nro>0</nro><xBairro>N/A</xBairro>"
                f"<cMun>{c_mun_cf}</cMun><xMun>{x_mun_cf}</xMun><UF>{uf_cf}</UF><CEP>00000000</CEP>"
                "<cPais>1058</cPais><xPais>Brasil</xPais>"
                "</enderDest>"
                "<indIEDest>9</indIEDest>"
                "</dest>"
            )

    # det
    crt_emit = empresa.get("crt")
    usar_simples = _simples_nacional(crt_emit)
    sb_det = []
    for idx, item in enumerate(itens, 1):
        n_item = str(idx)
        # Homologação: 1º item xProd deve ser literal exata (rej. 373)
        desc = (
            "NOTA FISCAL EMITIDA EM AMBIENTE DE HOMOLOGACAO - SEM VALOR FISCAL"
            if tp_amb == "2" and idx == 1
            else _escape_xml(item.get("descricao") or "")
        )
        ncm = (item.get("ncm") or "00000000").replace(".", "").zfill(8)[:8]
        cfop = (item.get("cfop") or "5102").replace(".", "").zfill(4)[:4]
        u_com = (item.get("unidade") or "UN").strip()[:6]
        q_com = _decimal_xml(item.get("quantidade"))
        v_un_com = _decimal_xml(item.get("valor_unitario"))
        v_prod = _decimal_xml(item.get("valor_total"))
        c_prod = _escape_xml(item.get("codigo_produto") or str(idx))
        c_ean_raw = (item.get("ean") or item.get("cEAN") or "").strip().replace(" ", "")
        # cEAN válido: "0" (sem GTIN) ou 8, 12, 13 ou 14 dígitos. Rejeição 611: evitar "SEM GTIN" e "0000000000000" em algumas SEFAZ.
        if c_ean_raw.isdigit() and len(c_ean_raw) in (8, 12, 13, 14):
            c_ean = c_ean_raw
        else:
            c_ean = "0"
        cest = (item.get("cest") or "").strip()[:7] if item.get("cest") else None
        origem = str(item.get("origem") if item.get("origem") is not None else "0")
        cst = (item.get("cst_icms") or "00").strip()[:3]
        csosn = (item.get("csosn") or "102").strip()[:3]
        v_icms = _decimal_xml(item.get("valor_icms"))
        v_bc = _decimal_xml(item.get("valor_base_icms"))
        p_icms = _decimal_xml(item.get("aliquota_icms"))
        pis_cst = (item.get("pis_cst") or "01").strip()[:2]
        cofins_cst = (item.get("cofins_cst") or "01").strip()[:2]
        v_pis = _decimal_xml(item.get("pis_valor"))
        v_cofins = _decimal_xml(item.get("cofins_valor"))
        prod_cest = f'<CEST>{cest}</CEST>' if cest else ""
        if usar_simples:
            tag_csosn = f"ICMSSN{csosn}" if csosn in ("102", "202", "500", "900") else "ICMSSN102"
            if csosn == "900":
                xml_icms = (
                    f"<ICMS><{tag_csosn}>"
                    f'<orig>{origem}</orig>'
                    f'<CSOSN>{csosn}</CSOSN>'
                    f'<vBC>{v_bc}</vBC>'
                    f'<pICMS>{p_icms}</pICMS>'
                    f'<vICMS>{v_icms}</vICMS>'
                    f"</{tag_csosn}></ICMS>"
                )
            else:
                xml_icms = (
                    f"<ICMS><{tag_csosn}>"
                    f'<orig>{origem}</orig>'
                    f'<CSOSN>{csosn}</CSOSN>'
                    f"</{tag_csosn}></ICMS>"
                )
        else:
            xml_icms = (
                "<ICMS><ICMS00>"
                f'<orig>{origem}</orig>'
                f'<CST>{cst}</CST>'
                f'<vBC>{v_bc}</vBC>'
                f'<pICMS>{p_icms}</pICMS>'
                f'<vICMS>{v_icms}</vICMS>'
                "</ICMS00></ICMS>"
            )
        sb_det.append(
            f"<det nItem=\"{n_item}\">"
            "<prod>"
            f'<cProd>{c_prod}</cProd>'
            f'<cEAN>{c_ean}</cEAN>'
            f'<xProd>{desc}</xProd>'
            f'<NCM>{ncm}</NCM>'
            f'{prod_cest}'
            f'<CFOP>{cfop}</CFOP>'
            f'<uCom>{u_com}</uCom>'
            f'<qCom>{q_com}</qCom>'
            f'<vUnCom>{v_un_com}</vUnCom>'
            f'<vProd>{v_prod}</vProd>'
            f'<cEANTrib>{c_ean}</cEANTrib>'
            f'<uTrib>{u_com}</uTrib>'
            f'<qTrib>{q_com}</qTrib>'
            f'<vUnTrib>{v_un_com}</vUnTrib>'
            f'<indTot>1</indTot>'
            "</prod>"
            "<imposto>"
            f"{xml_icms}"
            "<PIS><PISAliq>"
            f'<CST>{pis_cst}</CST>'
            f'<vBC>0.00</vBC>'
            f'<pPIS>0.00</pPIS>'
            f'<vPIS>{v_pis}</vPIS>'
            "</PISAliq></PIS>"
            "<COFINS><COFINSAliq>"
            f'<CST>{cofins_cst}</CST>'
            f'<vBC>0.00</vBC>'
            f'<pCOFINS>0.00</pCOFINS>'
            f'<vCOFINS>{v_cofins}</vCOFINS>'
            "</COFINSAliq></COFINS>"
            "</imposto>"
            "</det>"
        )
    xml_det = "".join(sb_det)

    # total: vBC = soma das bases de ICMS dos itens (não valor de ICMS); vFrete/vSeg/vOutro da capa
    v_prod_t = _decimal_xml(payload.get("valor_produtos"))
    v_nf = _decimal_xml(payload.get("valor_total"))
    v_desc = _decimal_xml(payload.get("valor_desconto"))
    v_icms_t = _decimal_xml(payload.get("valor_icms"))
    v_pis_t = _decimal_xml(payload.get("valor_pis"))
    v_cofins_t = _decimal_xml(payload.get("valor_cofins"))
    v_bc_t = "0.00"
    if itens:
        try:
            v_bc_t = _decimal_xml(sum(float(item.get("valor_base_icms") or 0) for item in itens))
        except (TypeError, ValueError):
            pass
    v_frete_t = _decimal_xml(payload.get("valor_frete"))
    v_seg_t = _decimal_xml(payload.get("valor_seguro"))
    v_outro_t = _decimal_xml(payload.get("valor_outros"))
    xml_total = (
        "<total>"
        "<ICMSTot>"
        f'<vBC>{v_bc_t}</vBC>'
        f'<vICMS>{v_icms_t}</vICMS>'
        "<vICMSDeson>0.00</vICMSDeson>"
        "<vFCP>0.00</vFCP>"
        "<vBCST>0.00</vBCST>"
        "<vST>0.00</vST>"
        "<vFCPST>0.00</vFCPST>"
        "<vFCPSTRet>0.00</vFCPSTRet>"
        f'<vProd>{v_prod_t}</vProd>'
        f'<vFrete>{v_frete_t}</vFrete>'
        f'<vSeg>{v_seg_t}</vSeg>'
        f'<vDesc>{v_desc}</vDesc>'
        "<vII>0.00</vII>"
        "<vIPI>0.00</vIPI>"
        "<vIPIDevol>0.00</vIPIDevol>"
        f'<vPIS>{v_pis_t}</vPIS>'
        f'<vCOFINS>{v_cofins_t}</vCOFINS>'
        f'<vOutro>{v_outro_t}</vOutro>'
        f'<vNF>{v_nf}</vNF>'
        "</ICMSTot>"
        "</total>"
    )

    mod_frete = str(payload.get("mod_frete") or payload.get("modalidade_frete") or "9").strip()[:1]
    if mod_frete not in ("0", "1", "2", "9"):
        mod_frete = "9"
    xml_transp = f"<transp><modFrete>{mod_frete}</modFrete></transp>"
    # cobr: NF-e 55 exige fat (rej. 905 se ausente); dup só para a prazo (rej. 853 se à vista); NFC-e: omitir
    if modelo == "65":
        xml_cobr = ""
    else:
        n_fat = nnf.zfill(9)
        xml_cobr = (
            "<cobr><fat>"
            f"<nFat>{n_fat}</nFat>"
            f"<vOrig>{v_nf}</vOrig>"
            f"<vDesc>{v_desc}</vDesc>"
            f"<vLiq>{v_nf}</vLiq>"
            "</fat></cobr>"
        )
    # pag: tPag 99 exige xPag (rej. 441). vPag obrigatório. indPag removido NT 2016.002 (causa 225 se presente).
    t_pag = str(payload.get("forma_pagamento") or payload.get("t_pag") or "99").strip()[:2].zfill(2)
    if t_pag not in ("01", "02", "03", "04", "05", "10", "11", "12", "13", "15", "90", "99"):
        t_pag = "99"
    v_pag = v_nf
    x_pag = _escape_xml(payload.get("descricao_pagamento") or ("Outros" if t_pag == "99" else ""))
    x_pag_tag = f"<xPag>{x_pag}</xPag>" if x_pag else ""
    xml_pag = f"<pag><detPag><tPag>{t_pag}</tPag>{x_pag_tag}<vPag>{v_pag}</vPag></detPag></pag>"
    inf_nfe = (
        f'<infNFe Id="NFe{chave}" versao="4.00" xmlns="{_NS_NFE}">'
        f"{xml_ide}{xml_emit}{xml_dest}{xml_det}{xml_total}"
        f"{xml_transp}"
        f"{xml_cobr}"
        f"{xml_pag}"
        "</infNFe>"
    )
    xml_supl = ""
    if modelo == "65":
        csc_id = (empresa.get("nfce_csc_id") or "").strip()
        csc_token = (empresa.get("nfce_csc_token") or "").strip()
        if csc_id and csc_token:
            xml_supl = _build_infnfesupl_nfce(
                chave=chave,
                tp_amb=tp_amb,
                csc_id=csc_id,
                csc_token=csc_token,
                uf=cuf,
            )
    return f'<NFe xmlns="{_NS_NFE}">{inf_nfe}{xml_supl}</NFe>'
