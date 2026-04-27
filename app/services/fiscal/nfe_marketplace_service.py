# PDV Ibix - Criação de NF-e a partir de pedido marketplace
"""Cria NotaFiscal (rascunho) + itens a partir de PedidoMarketplace para emissão automática ao comprador."""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Tuple

from sqlalchemy.orm import Session, joinedload

from app.models import (
    AnuncioPlataforma,
    Empresa,
    NotaFiscal,
    NotaFiscalItem,
    PedidoItemMarketplace,
    PedidoMarketplace,
    ProdutoCliente,
)
from app.models.nota_fiscal import (
    OrigemDocumentoFiscalEnum,
    StatusNotaEnum,
    TipoNotaEnum,
)


def _proximo_numero_nf(db: Session, empresa_id: int, serie: str = "1") -> str:
    """Próximo número de NF para a empresa/série."""
    rows = db.query(NotaFiscal.numero).filter(
        NotaFiscal.empresa_id == empresa_id,
        NotaFiscal.serie == serie,
    ).all()
    nums = []
    for (n,) in rows:
        try:
            nums.append(int(str(n).strip()))
        except (ValueError, TypeError):
            pass
    return str((max(nums) + 1) if nums else 1)


def criar_nota_fiscal_de_pedido_marketplace(
    db: Session,
    pedido_marketplace_id: int,
    usuario_id_emitente: Optional[int] = None,
) -> Tuple[bool, str, Optional[int]]:
    """
    Cria NotaFiscal (rascunho) + itens a partir do pedido da loja.
    Retorna (True, "", nota_fiscal_id) ou (False, "motivo", None).
    """
    pedido = (
        db.query(PedidoMarketplace)
        .options(
            joinedload(PedidoMarketplace.loja),
            joinedload(PedidoMarketplace.itens).joinedload(PedidoItemMarketplace.anuncio).joinedload(AnuncioPlataforma.produto_cliente),
        )
        .filter(PedidoMarketplace.id == pedido_marketplace_id)
        .first()
    )
    if not pedido:
        return False, "Pedido marketplace não encontrado", None

    loja = pedido.loja
    if not loja:
        return False, "Loja do pedido não encontrada", None

    empresa = db.query(Empresa).filter(Empresa.cliente_id == loja.cliente_id).first()
    if not empresa:
        return False, "Estabelecimento da loja não possui empresa fiscal configurada", None

    # Evitar duplicar NF para o mesmo pedido
    existente = db.query(NotaFiscal).filter(
        NotaFiscal.pedido_marketplace_id == pedido_marketplace_id,
    ).first()
    if existente:
        return False, "Já existe nota fiscal para este pedido", None

    serie = (getattr(empresa, "serie_padrao_nfe", None) or "").strip() or "1"
    numero = _proximo_numero_nf(db, empresa.id, serie)
    now = datetime.now(timezone.utc)

    valor_produtos = sum(
        (item.preco_total or Decimal("0")) for item in pedido.itens
    )

    valor_frete_nf = pedido.taxa_entrega if pedido.taxa_entrega else Decimal("0")

    nf = NotaFiscal(
        numero=numero,
        serie=serie,
        tipo=TipoNotaEnum.NFE,
        modelo="55",
        data_emissao=now,
        empresa_id=empresa.id,
        cliente_id=None,
        pedido_marketplace_id=pedido.id,
        emitido_por_id=usuario_id_emitente,
        origem_documento=OrigemDocumentoFiscalEnum.VENDA_MARKETPLACE,
        valor_total=pedido.total or valor_produtos,
        valor_produtos=valor_produtos,
        valor_frete=valor_frete_nf,
        status=StatusNotaEnum.RASCUNHO,
    )
    db.add(nf)
    db.flush()

    item_num = 1
    for pitem in pedido.itens:
        anuncio = pitem.anuncio
        if not anuncio:
            continue
        prod = getattr(anuncio, "produto_cliente", None) or db.query(ProdutoCliente).filter(
            ProdutoCliente.id == anuncio.produto_ca_id,
        ).first()
        ncm_item = (prod and getattr(prod, "ncm", None)) and (prod.ncm or "").strip() or None
        unidade_item = (prod and getattr(prod, "unidade_medida", None)) and (prod.unidade_medida or "").strip() or "UN"
        cfop_item = (prod and getattr(prod, "cfop_padrao", None)) and (prod.cfop_padrao or "").strip() or None
        cest_item = (prod and getattr(prod, "cest", None)) and (prod.cest or "").strip() or None
        extipi_item = (prod and getattr(prod, "extipi", None)) and (prod.extipi or "").strip() or None
        origem_item = None
        if prod and getattr(prod, "origem_mercadoria", None) is not None:
            try:
                o = int(prod.origem_mercadoria)
                if 0 <= o <= 8:
                    origem_item = o
            except (TypeError, ValueError):
                pass

        descricao = (anuncio.titulo or "").strip() or f"Item {item_num}"
        if len(descricao) > 255:
            descricao = descricao[:252] + "..."

        db.add(
            NotaFiscalItem(
                nota_id=nf.id,
                produto_cliente_id=anuncio.produto_ca_id,
                item_numero=item_num,
                descricao=descricao,
                codigo_produto=(prod.codigo or None) if prod else None,
                unidade=unidade_item[:10] if unidade_item else "UN",
                quantidade=pitem.quantidade,
                valor_unitario=pitem.preco_unitario or Decimal("0"),
                valor_total=pitem.preco_total or Decimal("0"),
                ncm=ncm_item,
                cfop=cfop_item,
                cest=cest_item,
                extipi=extipi_item,
                origem=origem_item,
            )
        )
        item_num += 1

    db.commit()
    db.refresh(nf)
    return True, "", nf.id
