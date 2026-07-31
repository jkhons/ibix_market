# PDV Ibix — Rastreio de origem comercial da venda (Orçamento · OS · manual)
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Orcamento, OrdemServico, Usuario, Venda
from app.models.venda_origem import VendaOrigem


@dataclass
class OrigemDocumento:
    tipo: str
    documento_id: Optional[int]
    documento_ref: Optional[str]


def tenant_id_do_vendedor(db: Session, vendedor_id: int) -> Optional[int]:
    u = db.query(Usuario).filter(Usuario.id == vendedor_id).first()
    return getattr(u, "tenant_id", None) if u else None


def registrar_origem_venda(
    db: Session,
    *,
    venda: Venda,
    usuario_id: int,
    imediata: OrigemDocumento,
    raiz: Optional[OrigemDocumento] = None,
) -> None:
    """Grava linhas em venda_origens (imediata + raiz opcional)."""
    tenant_id = tenant_id_do_vendedor(db, venda.vendedor_id or usuario_id)
    if tenant_id is None:
        return

    raiz_efetiva = raiz or imediata
    pares = [(imediata, "imediata")]
    if (
        raiz_efetiva.tipo != imediata.tipo
        or raiz_efetiva.documento_id != imediata.documento_id
    ):
        pares.append((raiz_efetiva, "raiz"))
    elif raiz is None and imediata.tipo != "manual":
        pares.append((imediata, "raiz"))

    for origem, papel in pares:
        exists = (
            db.query(VendaOrigem)
            .filter(
                VendaOrigem.venda_id == venda.id,
                VendaOrigem.papel == papel,
                VendaOrigem.tipo_origem == origem.tipo,
                VendaOrigem.documento_id == origem.documento_id,
            )
            .first()
        )
        if exists:
            continue
        db.add(
            VendaOrigem(
                tenant_id=tenant_id,
                venda_id=venda.id,
                tipo_origem=origem.tipo,
                documento_id=origem.documento_id,
                documento_ref=origem.documento_ref,
                papel=papel,
                usuario_id=usuario_id,
            )
        )


def registrar_origem_manual(db: Session, venda: Venda, usuario_id: int) -> None:
    registrar_origem_venda(
        db,
        venda=venda,
        usuario_id=usuario_id,
        imediata=OrigemDocumento(tipo="manual", documento_id=None, documento_ref=None),
    )


def registrar_origem_orcamento(
    db: Session,
    venda: Venda,
    orcamento: Orcamento,
    usuario_id: int,
) -> None:
    ref = orcamento.numero_orcamento
    origem = OrigemDocumento(tipo="orcamento", documento_id=orcamento.id, documento_ref=ref)
    registrar_origem_venda(db, venda=venda, usuario_id=usuario_id, imediata=origem, raiz=origem)


def registrar_origem_ordem_servico(
    db: Session,
    venda: Venda,
    ordem: OrdemServico,
    usuario_id: int,
    orcamento_raiz: Optional[Orcamento] = None,
) -> None:
    imediata = OrigemDocumento(
        tipo="ordem_servico",
        documento_id=ordem.id,
        documento_ref=ordem.codigo,
    )
    raiz = None
    if orcamento_raiz:
        raiz = OrigemDocumento(
            tipo="orcamento",
            documento_id=orcamento_raiz.id,
            documento_ref=orcamento_raiz.numero_orcamento,
        )
    registrar_origem_venda(db, venda=venda, usuario_id=usuario_id, imediata=imediata, raiz=raiz)


def orcamento_raiz_da_os(db: Session, ordem: OrdemServico) -> Optional[Orcamento]:
    oid = getattr(ordem, "orcamento_origem_id", None)
    if not oid:
        return None
    return db.query(Orcamento).filter(Orcamento.id == oid).first()


def montar_origem_cadeia_resposta(
    venda_id: int,
    venda_row: dict,
    origem_rows: list,
) -> list:
    """Monta breadcrumb ordenado (raiz → imediata → venda) com timestamps de conversão."""
    cadeia: list = []
    for vo in origem_rows:
        created = getattr(vo, "created_at", None)
        cadeia.append(
            {
                "tipo": vo.tipo_origem,
                "ref": vo.documento_ref,
                "documento_id": vo.documento_id,
                "papel": vo.papel,
                "convertido_em": created.isoformat() if created else None,
            }
        )
    if not cadeia:
        if venda_row.get("numero_orcamento") or venda_row.get("orcamento_id"):
            cadeia.append(
                {
                    "tipo": "orcamento",
                    "ref": venda_row.get("numero_orcamento"),
                    "documento_id": venda_row.get("orcamento_id"),
                    "papel": "imediata",
                    "convertido_em": None,
                }
            )
        if venda_row.get("ordem_servico_codigo") or venda_row.get("ordem_servico_id"):
            cadeia.append(
                {
                    "tipo": "ordem_servico",
                    "ref": venda_row.get("ordem_servico_codigo"),
                    "documento_id": venda_row.get("ordem_servico_id"),
                    "papel": "imediata",
                    "convertido_em": None,
                }
            )
    created_v = venda_row.get("created_at")
    cadeia.append(
        {
            "tipo": "venda",
            "ref": venda_row.get("numero_venda"),
            "documento_id": venda_id,
            "papel": "destino",
            "convertido_em": created_v.isoformat()
            if created_v and hasattr(created_v, "isoformat")
            else None,
        }
    )
    return cadeia
