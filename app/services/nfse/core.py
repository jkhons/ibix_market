# Core NFS-e: validações, cálculo ISS, reserva RPS, criação de invoice (subscription / OS)
from datetime import date
from decimal import Decimal
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Cliente, Empresa
from app.models.nfse import NfseInvoice, NfseRps
from app.services.nfse.errors import NfseErrorCode
from app.services.nfse.provider_router import get_provider_for_municipio

MSG_BLOQUEIO = (
    "Configure empresa emissora padrão e cliente CA, e preencha o código IBGE do município do emissor e do tomador."
)


def validar_pre_requisitos_emissao(
    db: Session,
    tenant_id: int,
    empresa_id: int,
    cliente_id: Optional[int],
    municipio_prestacao_ibge: int,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Valida pré-requisitos antes de criar/enfileirar invoice.
    Retorna (ok, last_error_code, last_error_msg).
    """
    empresa = db.get(Empresa, empresa_id)
    if not empresa:
        return False, NfseErrorCode.SCHEMA_INVALID.value, "Empresa não encontrada."
    if not empresa.im or (empresa.im and str(empresa.im).strip() == ""):
        return False, NfseErrorCode.SCHEMA_INVALID.value, "Empresa sem Inscrição Municipal (IM)."
    if empresa.municipio_ibge is None:
        return False, NfseErrorCode.MUN_IBGE_MISSING.value, "Empresa sem código IBGE do município."
    if cliente_id:
        cliente = db.get(Cliente, cliente_id)
        if not cliente:
            return False, NfseErrorCode.SCHEMA_INVALID.value, "Cliente não encontrado."
        if cliente.municipio_ibge is None:
            return False, NfseErrorCode.MUN_IBGE_MISSING.value, "Cliente (tomador) sem código IBGE do município."
    return True, None, None


def reservar_rps(
    db: Session,
    tenant_id: int,
    empresa_id: int,
    serie: str = "1",
) -> Optional[NfseRps]:
    """
    Reserva o próximo número de RPS para o emissor (transacional).
    Obtém MAX(numero)+1 e insere com status RESERVED. Retorna o registro ou None em falha.
    """
    try:
        r = db.execute(
            select(NfseRps.numero).where(
                NfseRps.tenant_id == tenant_id,
                NfseRps.empresa_id == empresa_id,
                NfseRps.serie == serie,
            ).order_by(NfseRps.numero.desc()).limit(1)
        )
        row = r.scalar_one_or_none()
        proximo = (row or 0) + 1
        rps = NfseRps(
            tenant_id=tenant_id,
            empresa_id=empresa_id,
            serie=serie,
            numero=proximo,
            tipo=1,
            status="RESERVED",
        )
        db.add(rps)
        db.flush()
        return rps
    except Exception:
        return None


def _calcular_iss(valor_servicos: Decimal, valor_deducoes: Decimal, aliquota_iss: float, iss_retido: bool) -> Tuple[Decimal, Decimal]:
    base = Decimal(str(valor_servicos)) - Decimal(str(valor_deducoes))
    valor_iss = (base * Decimal(str(aliquota_iss)) / 100).quantize(Decimal("0.01"))
    valor_iss_retido = valor_iss if iss_retido else Decimal("0")
    return base, valor_iss, valor_iss_retido


def criar_invoice_from_subscription(
    db: Session,
    subscription_id: int,
    tenant_id: int,
    empresa_id: int,
    cliente_id: int,
    data_competencia: date,
    descricao_servico: str,
    valor_servicos: float,
    aliquota_iss: float,
    item_lista_servico: Optional[str] = None,
    cnae: Optional[str] = None,
    iss_retido: bool = False,
) -> Optional[NfseInvoice]:
    """
    Cria NfseInvoice a partir de subscription (idempotente: UNIQUE tenant_id, origin_type, origin_id).
    Retorna o invoice existente ou o novo; None se validação falhar.
    """
    empresa = db.get(Empresa, empresa_id)
    if not empresa:
        return None
    municipio_ibge = empresa.municipio_ibge
    if municipio_ibge is None:
        return None
    ok, code, msg = validar_pre_requisitos_emissao(db, tenant_id, empresa_id, cliente_id, municipio_ibge)
    if not ok:
        return None

    existente = db.execute(
        select(NfseInvoice).where(
            NfseInvoice.tenant_id == tenant_id,
            NfseInvoice.origin_type == "SUBSCRIPTION",
            NfseInvoice.origin_id == subscription_id,
        )
    ).scalar_one_or_none()
    if existente:
        return existente

    base, valor_iss, valor_iss_retido = _calcular_iss(
        Decimal(str(valor_servicos)), Decimal("0"), aliquota_iss, iss_retido
    )
    provider = get_provider_for_municipio(empresa_id, municipio_ibge, db) or "NACIONAL"

    inv = NfseInvoice(
        tenant_id=tenant_id,
        empresa_id=empresa_id,
        cliente_id=cliente_id,
        origin_type="SUBSCRIPTION",
        origin_id=subscription_id,
        municipio_prestacao_ibge=municipio_ibge,
        data_competencia=data_competencia,
        descricao_servico=descricao_servico,
        item_lista_servico=item_lista_servico,
        cnae=cnae,
        valor_servicos=Decimal(str(valor_servicos)),
        valor_deducoes=Decimal("0"),
        base_iss=base,
        aliquota_iss=Decimal(str(aliquota_iss)),
        valor_iss=valor_iss,
        iss_retido=iss_retido,
        valor_iss_retido=valor_iss_retido,
        status="QUEUED",
        provider=provider,
    )
    db.add(inv)
    db.flush()
    return inv


def criar_invoice_from_os(
    db: Session,
    ordem_servico_id: int,
    tenant_id: int,
    empresa_id: int,
    cliente_id: int,
    data_competencia: date,
    descricao_servico: str,
    valor_servicos: float,
    aliquota_iss: float,
    municipio_prestacao_ibge: int,
    item_lista_servico: Optional[str] = None,
    cnae: Optional[str] = None,
    iss_retido: bool = False,
) -> Optional[NfseInvoice]:
    """
    Cria NfseInvoice a partir de ordem de serviço (idempotente por origin_id).
    """
    ok, code, msg = validar_pre_requisitos_emissao(db, tenant_id, empresa_id, cliente_id, municipio_prestacao_ibge)
    if not ok:
        return None

    existente = db.execute(
        select(NfseInvoice).where(
            NfseInvoice.tenant_id == tenant_id,
            NfseInvoice.origin_type == "OS",
            NfseInvoice.origin_id == ordem_servico_id,
        )
    ).scalar_one_or_none()
    if existente:
        return existente

    base, valor_iss, valor_iss_retido = _calcular_iss(
        Decimal(str(valor_servicos)), Decimal("0"), aliquota_iss, iss_retido
    )
    provider = get_provider_for_municipio(empresa_id, municipio_prestacao_ibge, db) or "NACIONAL"

    inv = NfseInvoice(
        tenant_id=tenant_id,
        empresa_id=empresa_id,
        cliente_id=cliente_id,
        origin_type="OS",
        origin_id=ordem_servico_id,
        municipio_prestacao_ibge=municipio_prestacao_ibge,
        data_competencia=data_competencia,
        descricao_servico=descricao_servico,
        item_lista_servico=item_lista_servico,
        cnae=cnae,
        valor_servicos=Decimal(str(valor_servicos)),
        valor_deducoes=Decimal("0"),
        base_iss=base,
        aliquota_iss=Decimal(str(aliquota_iss)),
        valor_iss=valor_iss,
        iss_retido=iss_retido,
        valor_iss_retido=valor_iss_retido,
        status="QUEUED",
        provider=provider,
    )
    db.add(inv)
    db.flush()
    return inv
