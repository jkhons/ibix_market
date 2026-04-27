# PDV Ibix - Assinador XML NF-e (padrão SEFAZ)
"""
Assina o XML da NF-e com o certificado A1 (RSA + SHA-1, C14N inclusive).
Assinatura manual (sem signxml): garante XMLDSig sem prefixo ds: e X509Certificate
em base64 contínuo — requisitos práticos da SEFAZ/SP que causam rejeição 290.

Fluxo:
1. C14N inclusivo do infNFe (cópia standalone) → SHA-1 digest
2. Monta SignedInfo XML (sem prefixo, namespace default xmldsig)
3. C14N inclusivo do SignedInfo → RSA-SHA1 sign
4. Monta Signature completa (sem prefixo ds:, X509Certificate em linha única)
5. Injeta Signature antes de </NFe> no XML serializado
"""
import base64
import hashlib
from copy import deepcopy
from typing import Any

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import Encoding

NS_DS = "http://www.w3.org/2000/09/xmldsig#"
NS_NFE = "http://www.portalfiscal.inf.br/nfe"


def _validar_xml_assinado(xml_assinado: str, id_infnfe_esperado: str) -> None:
    """
    Valida estrutura mínima do XML assinado. Levanta ValueError se inválido.
    """
    from lxml import etree

    root = etree.fromstring(xml_assinado.encode("utf-8"))
    inf_nfe = root.find(f".//{{{NS_NFE}}}infNFe")
    if inf_nfe is None:
        raise ValueError("Assinatura inválida: infNFe não encontrado no XML final.")

    sig = root.find(f".//{{{NS_DS}}}Signature")
    if sig is None:
        raise ValueError("Assinatura inválida: elemento Signature não encontrado.")

    def _text(el):
        if el is None:
            return ""
        return ("".join(el.itertext()) or (el.text or "")).strip()

    digest = sig.find(f".//{{{NS_DS}}}DigestValue")
    if digest is None or not _text(digest):
        raise ValueError("Assinatura inválida: DigestValue não encontrado ou vazio.")

    sig_value = sig.find(f".//{{{NS_DS}}}SignatureValue")
    if sig_value is None or not _text(sig_value):
        raise ValueError("Assinatura inválida: SignatureValue não encontrado ou vazio.")

    uri_esperado = "#" + (id_infnfe_esperado or "NFe")
    refs = list(sig.iter(f"{{{NS_DS}}}Reference"))
    if not any(r.get("URI") == uri_esperado for r in refs):
        first_uri = refs[0].get("URI") if refs else None
        raise ValueError(
            f"Assinatura inválida: Reference URI deve ser {uri_esperado!r}. Encontrado: {first_uri!r}."
        )

    x509 = sig.find(f".//{{{NS_DS}}}X509Certificate")
    if x509 is None or not _text(x509):
        raise ValueError("Assinatura inválida: X509Certificate não encontrado ou vazio.")


def assinar_nfe(xml_nfe: str, chave_privada: Any, certificado: Any) -> str:
    """
    Assina o documento NFe (string XML). Retorna XML com Signature (sem prefixo ds:).
    chave_privada e certificado: retornos de carregar_certificado_a1 (cryptography).
    """
    from lxml import etree

    root = etree.fromstring(xml_nfe.encode("utf-8"))
    ns = {"nfe": NS_NFE}
    inf_nfe = root.find(".//nfe:infNFe", namespaces=ns)
    if inf_nfe is None:
        raise ValueError("Elemento infNFe não encontrado no XML")
    id_infnfe = inf_nfe.get("Id")
    if not id_infnfe or not id_infnfe.startswith("NFe"):
        raise ValueError(f"infNFe Id inválido: {id_infnfe}")

    # 1. C14N inclusivo do infNFe (cópia standalone para isolar do contexto do pai)
    inf_copy = deepcopy(inf_nfe)
    c14n_inf = etree.tostring(inf_copy, method="c14n", exclusive=False)

    # 2. SHA-1 digest
    digest_b64 = base64.b64encode(hashlib.sha1(c14n_inf).digest()).decode()

    # 3. SignedInfo XML (namespace default xmldsig, SEM prefixo ds:)
    signed_info_xml = (
        '<SignedInfo xmlns="http://www.w3.org/2000/09/xmldsig#">'
        '<CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>'
        '<SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1"/>'
        f'<Reference URI="#{id_infnfe}">'
        '<Transforms>'
        '<Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>'
        '<Transform Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>'
        '</Transforms>'
        '<DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"/>'
        f'<DigestValue>{digest_b64}</DigestValue>'
        '</Reference>'
        '</SignedInfo>'
    )

    # 4. C14N inclusivo do SignedInfo → bytes para assinar
    si_el = etree.fromstring(signed_info_xml.encode("utf-8"))
    c14n_si = etree.tostring(si_el, method="c14n", exclusive=False)

    # 5. RSA-SHA1 (PKCS#1 v1.5)
    sig_bytes = chave_privada.sign(c14n_si, padding.PKCS1v15(), hashes.SHA1())
    sig_b64 = base64.b64encode(sig_bytes).decode()

    # 6. X509Certificate: DER em base64 contínuo (sem newlines)
    cert_b64 = base64.b64encode(certificado.public_bytes(Encoding.DER)).decode()

    # 7. Signature completa (SignedInfo SEM xmlns — herda do Signature pai)
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

    # 8. Serializar XML sem Signature, depois injetar antes de </NFe>
    resultado_bytes = etree.tostring(root, encoding="utf-8", xml_declaration=True, method="xml")
    resultado = resultado_bytes.decode("utf-8")
    for a, b in [("version='1.0'", 'version="1.0"'), ("encoding='utf-8'", 'encoding="utf-8"')]:
        resultado = resultado.replace(a, b)

    # Injetar Signature antes do fechamento </NFe>
    ns_nfe_tag = f"{{{NS_NFE}}}"
    close_tag = "</NFe>" if "</NFe>" in resultado else f"</{ns_nfe_tag}NFe>"
    if close_tag not in resultado:
        raise ValueError("Tag </NFe> não encontrada no XML serializado")
    resultado = resultado.replace(close_tag, signature_str + "</NFe>", 1)

    _validar_xml_assinado(resultado, id_infnfe)
    return resultado
