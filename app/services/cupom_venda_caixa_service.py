"""Monta cupom não fiscal de venda (caixa / PDV)."""
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.core.scope import ClienteScope, get_empresa_fiscal_empresa
from app.models.abertura_caixa import AberturaCaixa
from app.models.caixa import Caixa
from app.models.cliente import Cliente
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.venda import Venda, VendaItem
from app.models.venda_pagamento import VendaPagamento
from app.schemas.cupom import CupomConteudoResponse
from app.services.cupom_receipt import gerar_cupom_resumo_venda_caixa


def _estabelecimento_cliente_id_da_venda(db: Session, venda: Venda) -> Optional[int]:
    if getattr(venda, "cliente_id", None) is not None:
        return int(venda.cliente_id)
    ab_id = getattr(venda, "abertura_caixa_id", None)
    if ab_id:
        ab = db.query(AberturaCaixa).filter(AberturaCaixa.id == ab_id).first()
        if ab:
            cx = db.query(Caixa).filter(Caixa.id == ab.caixa_id).first()
            if cx:
                emp = db.query(Empresa).filter(Empresa.id == cx.empresa_id).first()
                if emp and getattr(emp, "cliente_id", None) is not None:
                    return int(emp.cliente_id)
    for vi in venda.itens or []:
        if getattr(vi, "produto_cliente_id", None) and getattr(vi, "produto_cliente", None):
            pc = vi.produto_cliente
            if pc and getattr(pc, "cliente_id", None) is not None:
                return int(pc.cliente_id)
    return None


def _empresa_fiscal_dict(empresa) -> dict:
    partes_end = []
    if getattr(empresa, "endereco", None):
        linha = str(empresa.endereco).strip()
        if getattr(empresa, "numero", None):
            linha += f", {str(empresa.numero).strip()}"
        partes_end.append(linha)
    if getattr(empresa, "bairro", None):
        partes_end.append(str(empresa.bairro).strip())
    cidade_uf = []
    if getattr(empresa, "cidade", None):
        cidade_uf.append(str(empresa.cidade).strip())
    if getattr(empresa, "uf", None):
        cidade_uf.append(str(empresa.uf).strip())
    if cidade_uf:
        partes_end.append(" - ".join(cidade_uf))
    if getattr(empresa, "cep", None):
        partes_end.append(f"CEP {str(empresa.cep).strip()}")
    return {
        "razao_social": (getattr(empresa, "razao_social", None) or "").strip(),
        "nome_fantasia": (getattr(empresa, "nome_fantasia", None) or "").strip(),
        "cnpj": (getattr(empresa, "cnpj", None) or "").strip(),
        "ie": (getattr(empresa, "ie", None) or "").strip(),
        "telefone": (getattr(empresa, "telefone", None) or "").strip(),
        "endereco_linhas": [p for p in partes_end if p],
    }


def _nome_estabelecimento(venda: Venda, empresa_dict: Optional[dict]) -> str:
    if empresa_dict:
        return (
            empresa_dict.get("nome_fantasia")
            or empresa_dict.get("razao_social")
            or "Estabelecimento"
        )
    if venda.cliente and (venda.cliente.nome or "").strip():
        return venda.cliente.nome.strip()
    return "Estabelecimento"


def montar_cupom_venda_caixa(
    db: Session,
    venda_id: int,
    current_user: Usuario,
    scope: ClienteScope,
) -> CupomConteudoResponse:
    venda = (
        db.query(Venda)
        .options(
            joinedload(Venda.itens).joinedload(VendaItem.produto_cliente),
            joinedload(Venda.cliente),
            joinedload(Venda.vendedor),
            joinedload(Venda.abertura_caixa).joinedload(AberturaCaixa.caixa),
        )
        .filter(Venda.id == venda_id)
        .first()
    )
    if not venda:
        raise HTTPException(status_code=404, detail="Venda não encontrada")
    if scope.must_filter_by_cliente():
        cid = venda.cliente_id
        if cid is None:
            estab_id = _estabelecimento_cliente_id_da_venda(db, venda)
            if estab_id is None or estab_id not in scope.allowed_ids:
                raise HTTPException(status_code=404, detail="Venda não encontrada")
        elif cid not in scope.allowed_ids:
            raise HTTPException(status_code=404, detail="Venda não encontrada")

    empresa_fiscal = get_empresa_fiscal_empresa(
        db, current_user.id, current_user.role.nome if current_user.role else None
    )
    empresa_dict = _empresa_fiscal_dict(empresa_fiscal) if empresa_fiscal else None
    estabelecimento_nome = _nome_estabelecimento(venda, empresa_dict)

    itens_data: List[dict] = []
    for item in venda.itens or []:
        nome = "Item"
        codigo = ""
        if getattr(item, "produto_cliente", None):
            if item.produto_cliente.nome:
                nome = item.produto_cliente.nome.strip()
            if getattr(item.produto_cliente, "codigo", None):
                codigo = str(item.produto_cliente.codigo).strip()
        elif (item.observacoes or "").strip():
            nome = (item.observacoes or "").split("\n")[0].strip() or nome
        itens_data.append(
            {
                "codigo": codigo,
                "nome": nome,
                "quantidade": float(item.quantidade),
                "valor_unitario": float(item.valor_unitario),
                "valor_total": float(item.valor_total),
            }
        )

    pagamentos = [
        {"forma": p.forma, "valor": float(p.valor or 0)}
        for p in (
            db.query(VendaPagamento)
            .filter(VendaPagamento.venda_id == venda.id)
            .order_by(VendaPagamento.id.asc())
            .all()
        )
        if float(p.valor or 0) > 0
    ]

    linhas, html = gerar_cupom_resumo_venda_caixa(
        estabelecimento_nome=estabelecimento_nome,
        numero_venda=venda.numero_venda,
        data_referencia=venda.data_venda,
        subtotal=venda.subtotal,
        desconto=venda.desconto,
        acrescimo=venda.acrescimo,
        total=venda.total,
        tipo_pagamento=venda.tipo_pagamento,
        valor_pago=venda.valor_pago,
        troco=venda.troco,
        itens=itens_data,
        observacoes=venda.observacoes,
        cliente_nome=(venda.cliente.nome if venda.cliente else None),
        vendedor_nome=(venda.vendedor.nome if getattr(venda, "vendedor", None) else None),
        pagamentos=pagamentos or None,
        empresa_fiscal=empresa_dict,
        largura=48,
        largura_mm=80,
    )
    return CupomConteudoResponse(tipo="nao_fiscal", linhas=linhas, html=html, largura_mm=80)
