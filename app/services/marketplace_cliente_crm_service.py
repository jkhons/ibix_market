# PDV Ibix — Sincroniza compradores do marketplace com cadastro de clientes (CRM /clientes)
import hashlib
import re
from typing import List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.area_cliente import AreaCliente
from app.models.cliente import Cliente
from app.models.cliente_administrador_cliente import ClienteAdministradorCliente
from app.models.loja_marketplace import LojaMarketplace
from app.schemas.marketplace import PedidoCheckoutCreate
from app.utils.cnpj_validator import CNPJValidator
from app.utils.cpf_validator import CPFValidator


_UFS_VALIDAS = {
    "AC",
    "AL",
    "AP",
    "AM",
    "BA",
    "CE",
    "DF",
    "ES",
    "GO",
    "MA",
    "MT",
    "MS",
    "MG",
    "PA",
    "PB",
    "PR",
    "PE",
    "PI",
    "RJ",
    "RN",
    "RS",
    "RO",
    "RR",
    "SC",
    "SP",
    "SE",
    "TO",
}


def _usuario_ids_ca_estabelecimento(db: Session, establishment_cliente_id: int) -> List[int]:
    """Usuários com área administrador neste cliente (empresa fiscal da loja)."""
    rows = (
        db.query(AreaCliente.usuario_id)
        .filter(
            AreaCliente.cliente_id == establishment_cliente_id,
            AreaCliente.ativo.is_(True),
            AreaCliente.nome_area == "administrador",
        )
        .distinct()
        .all()
    )
    ids: List[int] = [r[0] for r in rows if r[0]]
    # Base legada: CA vinculado a este cliente_id em cliente_administrador_clientes
    extra = (
        db.query(ClienteAdministradorCliente.usuario_id)
        .filter(ClienteAdministradorCliente.cliente_id == establishment_cliente_id)
        .distinct()
        .all()
    )
    for e in extra:
        uid = e[0]
        if uid and uid not in ids:
            ids.append(uid)
    return ids


def _cpf_sintetico_tenant_email(tenant_id: int, email: str) -> str:
    """
    CPF único e matematicamente válido para comprador sem documento,
    derivado de tenant + e-mail (não reutiliza CPF real).
    """
    h = hashlib.sha256(f"mkp_crm:{tenant_id}:{email.lower().strip()}".encode()).digest()
    base = "".join(str(b % 10) for b in h[:9])
    if len(set(base)) == 1:
        base = "123456789"
    d1 = CPFValidator.calcular_digito_verificador(base)
    d2 = CPFValidator.calcular_digito_verificador(base + str(d1))
    limpo = base + str(d1) + str(d2)
    if CPFValidator.validar_sequencia_repetida(limpo):
        base = "987654321"
        d1 = CPFValidator.calcular_digito_verificador(base)
        d2 = CPFValidator.calcular_digito_verificador(base + str(d1))
        limpo = base + str(d1) + str(d2)
    return CPFValidator.formatar_cpf(limpo)


def _parse_documento(documento: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """Retorna (cnpj_formatado, cpf_formatado) com no máximo um preenchido."""
    digits = re.sub(r"[^0-9]", "", documento or "")
    if len(digits) == 14:
        ok, fmt, _ = CNPJValidator.validar_e_formatar(documento or "")
        return (fmt if ok else None), None
    if len(digits) == 11:
        ok, fmt, _ = CPFValidator.validar_e_formatar(documento or "")
        return None, (fmt if ok else None)
    return None, None


def _format_telefone_obrigatorio(telefone: Optional[str]) -> str:
    dig = re.sub(r"[^0-9]", "", telefone or "")
    if len(dig) < 10:
        dig = "11000000000"
    if len(dig) > 11:
        dig = dig[:11]
    if len(dig) == 11:
        return f"({dig[:2]}) {dig[2:7]}-{dig[7:]}"
    return f"({dig[:2]}) {dig[2:6]}-{dig[6:]}"


def _cep_formatado(cep: Optional[str]) -> Optional[str]:
    if not cep:
        return None
    d = re.sub(r"[^0-9]", "", cep)
    if len(d) != 8:
        return None
    return f"{d[:5]}-{d[5:]}"


def _endereco_e_local_do_body(body: PedidoCheckoutCreate) -> Tuple[str, str, str, Optional[str]]:
    log = (getattr(body, "endereco_logradouro", None) or "").strip()
    num = (getattr(body, "endereco_numero", None) or "").strip()
    comp = (getattr(body, "endereco_complemento", None) or "").strip()
    bairro = (getattr(body, "endereco_bairro", None) or "").strip()
    cidade = (getattr(body, "endereco_cidade", None) or "").strip()
    uf_raw = (getattr(body, "endereco_uf", None) or "").strip().upper()[:2]
    uf = uf_raw if uf_raw in _UFS_VALIDAS else "SP"
    cep_fmt = _cep_formatado(getattr(body, "endereco_cep", None))

    partes_linha = []
    if log:
        linha = log
        if num:
            linha += f", {num}"
        partes_linha.append(linha)
    if comp:
        partes_linha.append(comp)
    if bairro:
        partes_linha.append(bairro)
    endereco = ", ".join(partes_linha) if partes_linha else "Cliente originado em pedido marketplace — endereço não informado"
    if not cidade:
        cidade = "Não informado"
    return endereco, cidade, uf, cep_fmt


def _vinculos_ca_para_cliente(
    db: Session,
    ca_usuario_ids: List[int],
    cliente_id: int,
) -> None:
    for uid in ca_usuario_ids:
        existe = (
            db.query(ClienteAdministradorCliente.id)
            .filter(
                ClienteAdministradorCliente.usuario_id == uid,
                ClienteAdministradorCliente.cliente_id == cliente_id,
            )
            .first()
        )
        if not existe:
            db.add(ClienteAdministradorCliente(usuario_id=uid, cliente_id=cliente_id))


def sync_cliente_crm_from_pedido_marketplace(
    db: Session,
    loja: LojaMarketplace,
    body: PedidoCheckoutCreate,
    comprador_nome: str,
    comprador_email: str,
    comprador_telefone: Optional[str],
    comprador_documento: Optional[str],
    tenant_id: int,
) -> None:
    """
    Garante um registro em `clientes` visível para o lojista (escopo CA) e atualiza dados básicos.
    Não faz commit (transação do checkout).
    """
    email_norm = (comprador_email or "").strip().lower()[:100]
    nome = (comprador_nome or "").strip()[:255]
    if not email_norm or not nome:
        return

    ca_ids = _usuario_ids_ca_estabelecimento(db, loja.cliente_id)
    if not ca_ids:
        return

    cnpj_doc, cpf_doc = _parse_documento(comprador_documento)

    existente = (
        db.query(Cliente)
        .join(
            ClienteAdministradorCliente,
            ClienteAdministradorCliente.cliente_id == Cliente.id,
        )
        .filter(
            ClienteAdministradorCliente.usuario_id.in_(ca_ids),
            func.lower(func.trim(Cliente.email)) == email_norm,
        )
        .first()
    )
    if not existente and (cpf_doc or cnpj_doc):
        q = (
            db.query(Cliente)
            .join(
                ClienteAdministradorCliente,
                ClienteAdministradorCliente.cliente_id == Cliente.id,
            )
            .filter(ClienteAdministradorCliente.usuario_id.in_(ca_ids))
        )
        if cpf_doc:
            existente = q.filter(Cliente.cpf == cpf_doc).first()
        if not existente and cnpj_doc:
            existente = q.filter(Cliente.cnpj == cnpj_doc).first()

    endereco, cidade, uf, cep_fmt = _endereco_e_local_do_body(body)
    telefone_fmt = _format_telefone_obrigatorio(comprador_telefone)
    contato = nome[:100]

    if existente:
        existente.nome = nome
        existente.contato = contato
        existente.telefone = telefone_fmt
        existente.email = email_norm
        if cep_fmt:
            existente.cep = cep_fmt
        if endereco:
            existente.endereco = endereco[:500]
        existente.cidade = cidade[:100]
        existente.uf = uf
        if cnpj_doc and not existente.cnpj:
            existente.cnpj = cnpj_doc
            existente.cpf = None
        elif cpf_doc and not existente.cpf and not existente.cnpj:
            existente.cpf = cpf_doc
        _vinculos_ca_para_cliente(db, ca_ids, existente.id)
        return

    if cnpj_doc:
        cpf_val = None
        cnpj_val = cnpj_doc
    elif cpf_doc:
        cpf_val = cpf_doc
        cnpj_val = None
    else:
        cpf_val = _cpf_sintetico_tenant_email(tenant_id, email_norm)
        cnpj_val = None

    novo = Cliente(
        nome=nome,
        cnpj=cnpj_val,
        cpf=cpf_val,
        cep=cep_fmt,
        endereco=endereco[:500],
        cidade=cidade[:100],
        uf=uf,
        contato=contato,
        telefone=telefone_fmt,
        email=email_norm,
    )
    db.add(novo)
    db.flush()
    _vinculos_ca_para_cliente(db, ca_ids, novo.id)
