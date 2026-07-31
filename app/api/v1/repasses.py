# PDV Ibix - API Repasses Financeiros (SuperAdmin only)
"""CRUD de repasses, resumo por CA, extrato e marcação de repasse efetuado."""
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from ...core.middleware import get_current_user, require_superadmin
from ...database.connection import get_db
from ...models.cliente import Cliente
from ...models.empresa import Empresa
from ...models.entrega_marketplace import EntregaMarketplace
from ...models.entregador import Entregador
from ...models.loja_marketplace import LojaMarketplace
from ...models.payment_transaction import PaymentTransaction
from ...models.pedido_marketplace import PedidoMarketplace
from ...models.repasse import Repasse
from ...models.repasse_status import RepasseStatus
from ...models.usuario import Usuario
from ...models.venda import Venda
from ...services.payments.marketplace_unified_payment_scope import (
    amount_payment_transaction_para_estabelecimento,
    filter_transactions_query_for_estabelecimento,
    listagem_sessao_valores_para_tenant,
)

router = APIRouter(
    prefix="/negocio/financeiro/repasses",
    tags=["Financeiro - Repasses"],
    dependencies=[Depends(require_superadmin())],
)


class ResumoCA(BaseModel):
    cliente_id: int
    cliente_nome: Optional[str] = None
    total_vendas_bruto: Decimal = Decimal("0")
    total_taxa: Decimal = Decimal("0")
    total_repassado: Decimal = Decimal("0")
    saldo_pendente: Decimal = Decimal("0")
    modo_recebimento: Optional[str] = None
    taxa_plataforma_percentual: Optional[Decimal] = None
    taxa_plataforma_valor_fixo: Optional[Decimal] = None
    qtd_transacoes: int = 0


class RepasseCreate(BaseModel):
    cliente_id: int = Field(..., description="CA que receberá o repasse")
    valor_bruto: Decimal = Field(..., gt=0)
    valor_taxa: Decimal = Field(default=Decimal("0"), ge=0)
    valor_liquido: Decimal = Field(..., gt=0)
    periodo_inicio: date
    periodo_fim: date
    comprovante: Optional[str] = None
    observacao: Optional[str] = None


class RepasseUpdate(BaseModel):
    status: Optional[str] = Field(None, description="pendente, repassado, cancelado")
    comprovante: Optional[str] = None
    observacao: Optional[str] = None


class RepasseResponse(BaseModel):
    id: int
    cliente_id: int
    cliente_nome: Optional[str] = None
    valor_bruto: Decimal
    valor_taxa: Decimal
    valor_liquido: Decimal
    periodo_inicio: date
    periodo_fim: date
    status: str
    data_repasse: Optional[datetime] = None
    comprovante: Optional[str] = None
    observacao: Optional[str] = None
    usuario_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TaxaCA(BaseModel):
    empresa_id: int
    razao_social: Optional[str] = None
    taxa_plataforma_percentual: Optional[Decimal] = None
    taxa_plataforma_valor_fixo: Optional[Decimal] = None


class TransacaoRepasseResponse(BaseModel):
    """Transação (venda) que compõe o saldo pendente de repasse."""
    id: int
    uuid: Optional[str] = None
    cliente_id: int
    cliente_nome: Optional[str] = None
    amount: Decimal
    status: str
    payment_method: Optional[str] = None
    created_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    pedido_id: Optional[int] = None
    numero_pedido: Optional[str] = None
    venda_id: Optional[int] = None
    numero_venda: Optional[str] = None
    modo_recebimento: Optional[str] = None
    taxa_plataforma_percentual: Optional[Decimal] = None
    taxa_plataforma_valor_fixo: Optional[Decimal] = None
    valor_taxa: Decimal = Decimal("0")
    valor_liquido: Decimal = Decimal("0")
    status_repasse_id: Optional[int] = None
    status_repasse_nome: Optional[str] = None
    status_repasse_sigla: Optional[str] = None


class StatusRepasseItem(BaseModel):
    """Item da lista de status de repasse para dropdown."""
    id: int
    nome: str
    sigla: str


class TransacaoStatusUpdate(BaseModel):
    """Body para alterar status de repasse da transação."""
    repasse_status_id: int = Field(..., description="ID do status_repasse")


@router.get("/transacoes", response_model=List[TransacaoRepasseResponse])
async def listar_transacoes_repasse(
    cliente_id: Optional[int] = Query(None, description="Filtrar por CA (cliente_id)"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Lista transações (vendas) que compõem o saldo pendente de repasse (modo=plataforma, paid/authorized)."""
    q = (
        db.query(PaymentTransaction)
        .filter(
            PaymentTransaction.modo_recebimento == "plataforma",
            PaymentTransaction.status.in_(["paid", "authorized"]),
        )
    )
    if cliente_id:
        q = filter_transactions_query_for_estabelecimento(q, cliente_id)
    rows = q.order_by(PaymentTransaction.id.desc()).limit(limit).all()
    result = []
    for tx in rows:
        display_cliente_id = cliente_id if cliente_id is not None else tx.cliente_id
        cli = db.query(Cliente).filter(Cliente.id == display_cliente_id).first()
        numero_pedido = None
        numero_venda = None
        if cliente_id is not None and tx.checkout_session_id:
            _, numeros_concat, primeiro_pid = listagem_sessao_valores_para_tenant(
                db,
                checkout_session_id=tx.checkout_session_id,
                viewer_tenant_id=cliente_id,
            )
            numero_pedido = numeros_concat
            ped_ref_id = primeiro_pid
        elif tx.pedido_id:
            ped = db.query(PedidoMarketplace).filter(PedidoMarketplace.id == tx.pedido_id).first()
            numero_pedido = ped.numero_pedido if ped else None
            ped_ref_id = tx.pedido_id
        else:
            ped_ref_id = tx.pedido_id
        if tx.venda_id:
            venda = db.query(Venda).filter(Venda.id == tx.venda_id).first()
            numero_venda = venda.numero_venda if venda else None

        emp = (
            db.query(Empresa)
            .filter(
                Empresa.cliente_id == display_cliente_id,
                Empresa.modo_recebimento == "plataforma",
                Empresa.ativo.is_(True),
            )
            .first()
        )
        pct = (emp.taxa_plataforma_percentual or Decimal("0")) if emp else Decimal("0")
        fixo = (emp.taxa_plataforma_valor_fixo or Decimal("0")) if emp else Decimal("0")
        if cliente_id is not None:
            amount = amount_payment_transaction_para_estabelecimento(db, tx, cliente_id)
        else:
            amount = tx.amount or Decimal("0")
        valor_taxa = (amount * pct / Decimal("100")) + fixo
        valor_liquido = amount - valor_taxa

        rs = tx.repasse_status
        result.append(TransacaoRepasseResponse(
            id=tx.id,
            uuid=tx.uuid,
            cliente_id=display_cliente_id,
            cliente_nome=cli.nome if cli else None,
            amount=amount,
            status=tx.status or "",
            payment_method=tx.payment_method,
            created_at=tx.created_at,
            paid_at=tx.paid_at,
            pedido_id=ped_ref_id,
            numero_pedido=numero_pedido,
            venda_id=tx.venda_id,
            numero_venda=numero_venda,
            modo_recebimento=tx.modo_recebimento,
            taxa_plataforma_percentual=pct if pct else None,
            taxa_plataforma_valor_fixo=fixo if fixo else None,
            valor_taxa=valor_taxa,
            valor_liquido=max(valor_liquido, Decimal("0")),
            status_repasse_id=tx.repasse_status_id,
            status_repasse_nome=rs.nome if rs else None,
            status_repasse_sigla=rs.sigla if rs else None,
        ))
    return result


@router.get("/status-repasse", response_model=List[StatusRepasseItem])
async def listar_status_repasse(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Lista status de repasse para dropdown (Aguardando, Feito, Cancelado, etc.)."""
    rows = db.query(RepasseStatus).filter(RepasseStatus.ativo.is_(True)).order_by(RepasseStatus.ordem).all()
    return [StatusRepasseItem(id=r.id, nome=r.nome, sigla=r.sigla) for r in rows]


@router.put("/transacoes/{tx_id}/status")
async def atualizar_status_transacao(
    tx_id: int,
    data: TransacaoStatusUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Altera o status de repasse de uma transação (modo plataforma)."""
    tx = db.query(PaymentTransaction).filter(
        PaymentTransaction.id == tx_id,
        PaymentTransaction.modo_recebimento == "plataforma",
        PaymentTransaction.status.in_(["paid", "authorized"]),
    ).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transação não encontrada ou não elegível.")
    st = db.query(RepasseStatus).filter(RepasseStatus.id == data.repasse_status_id, RepasseStatus.ativo.is_(True)).first()
    if not st:
        raise HTTPException(status_code=400, detail="Status inválido.")
    tx.repasse_status_id = data.repasse_status_id
    db.commit()
    return {"ok": True, "repasse_status_id": data.repasse_status_id, "status_repasse_sigla": st.sigla}


class SugestaoRepasseResponse(BaseModel):
    """Sugestão de valores para novo repasse com base nas transações do período."""
    valor_bruto: Decimal
    valor_taxa: Decimal
    valor_liquido: Decimal
    taxa_plataforma_percentual: Optional[Decimal] = None
    taxa_plataforma_valor_fixo: Optional[Decimal] = None
    qtd_transacoes: int = 0


@router.get("/sugestao", response_model=SugestaoRepasseResponse)
async def sugestao_repasse(
    cliente_id: int = Query(..., description="CA (cliente_id)"),
    periodo_inicio: date = Query(..., description="Início do período"),
    periodo_fim: date = Query(..., description="Fim do período"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Calcula sugestão de bruto, taxa e líquido para repasse com base nas transações do período."""
    emp = (
        db.query(Empresa)
        .filter(
            Empresa.cliente_id == cliente_id,
            Empresa.modo_recebimento == "plataforma",
            Empresa.ativo.is_(True),
        )
        .first()
    )
    if not emp:
        return SugestaoRepasseResponse(
            valor_bruto=Decimal("0"),
            valor_taxa=Decimal("0"),
            valor_liquido=Decimal("0"),
            qtd_transacoes=0,
        )
    pct = emp.taxa_plataforma_percentual or Decimal("0")
    fixo = emp.taxa_plataforma_valor_fixo or Decimal("0")

    dt_inicio = datetime.combine(periodo_inicio, datetime.min.time())
    dt_fim = datetime.combine(periodo_fim + timedelta(days=1), datetime.min.time())

    q = db.query(PaymentTransaction).filter(
        PaymentTransaction.modo_recebimento == "plataforma",
        PaymentTransaction.status.in_(["paid", "authorized"]),
        or_(
            and_(
                PaymentTransaction.paid_at.isnot(None),
                PaymentTransaction.paid_at >= dt_inicio,
                PaymentTransaction.paid_at < dt_fim,
            ),
            and_(
                PaymentTransaction.paid_at.is_(None),
                PaymentTransaction.created_at >= dt_inicio,
                PaymentTransaction.created_at < dt_fim,
            ),
        ),
    )
    q = filter_transactions_query_for_estabelecimento(q, cliente_id)
    rows = q.all()
    vendas_bruto = sum(amount_payment_transaction_para_estabelecimento(db, tx, cliente_id) for tx in rows)
    tx_count = len(rows)
    valor_taxa = (vendas_bruto * pct / Decimal("100")) + (fixo * tx_count)
    valor_liquido = vendas_bruto - valor_taxa

    return SugestaoRepasseResponse(
        valor_bruto=vendas_bruto,
        valor_taxa=valor_taxa,
        valor_liquido=max(valor_liquido, Decimal("0")),
        taxa_plataforma_percentual=pct if pct else None,
        taxa_plataforma_valor_fixo=fixo if fixo else None,
        qtd_transacoes=tx_count,
    )


@router.get("/resumo", response_model=List[ResumoCA])
async def resumo_por_ca(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Saldos pendentes de repasse agrupados por CA (modo=plataforma)."""
    empresas = (
        db.query(Empresa)
        .filter(Empresa.modo_recebimento == "plataforma", Empresa.ativo.is_(True))
        .all()
    )
    result = []
    for emp in empresas:
        cid = emp.cliente_id
        if cid is None:
            continue
        cli = db.query(Cliente).filter(Cliente.id == cid).first()

        total_repassado = (
            db.query(func.coalesce(func.sum(Repasse.valor_liquido), 0))
            .filter(Repasse.cliente_id == cid, Repasse.status == "repassado")
            .scalar()
        ) or Decimal("0")

        pct = emp.taxa_plataforma_percentual or Decimal("0")
        fixo = emp.taxa_plataforma_valor_fixo or Decimal("0")

        q_tx = (
            db.query(PaymentTransaction)
            .filter(
                PaymentTransaction.modo_recebimento == "plataforma",
                PaymentTransaction.status.in_(["paid", "authorized"]),
            )
        )
        q_tx = filter_transactions_query_for_estabelecimento(q_tx, cid)
        rows_tx = q_tx.all()
        vendas_bruto = sum(amount_payment_transaction_para_estabelecimento(db, tx, cid) for tx in rows_tx)
        tx_count = len(rows_tx)
        total_taxa = (vendas_bruto * pct / Decimal("100")) + (fixo * tx_count)

        saldo = vendas_bruto - total_taxa - total_repassado
        result.append(ResumoCA(
            cliente_id=cid,
            cliente_nome=cli.nome if cli else None,
            total_vendas_bruto=vendas_bruto,
            total_taxa=total_taxa,
            total_repassado=total_repassado,
            saldo_pendente=max(saldo, Decimal("0")),
            modo_recebimento=emp.modo_recebimento,
            taxa_plataforma_percentual=pct if pct else None,
            taxa_plataforma_valor_fixo=fixo if fixo else None,
            qtd_transacoes=tx_count,
        ))
    return result


@router.get("/extrato", response_model=List[RepasseResponse])
async def extrato_repasses(
    cliente_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Extrato de repasses (filtro por CA e status)."""
    q = db.query(Repasse)
    if cliente_id:
        q = q.filter(Repasse.cliente_id == cliente_id)
    if status_filter:
        q = q.filter(Repasse.status == status_filter)
    q.count()
    rows = q.order_by(Repasse.id.desc()).offset((page - 1) * per_page).limit(per_page).all()
    result = []
    for r in rows:
        cli = db.query(Cliente).filter(Cliente.id == r.cliente_id).first()
        resp = RepasseResponse.model_validate(r)
        resp.cliente_nome = cli.nome if cli else None
        result.append(resp)
    return result


@router.post("/", response_model=RepasseResponse, status_code=status.HTTP_201_CREATED)
async def criar_repasse(
    data: RepasseCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Cria registro de repasse (manual)."""
    cli = db.query(Cliente).filter(Cliente.id == data.cliente_id).first()
    if not cli:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")
    repasse = Repasse(
        cliente_id=data.cliente_id,
        valor_bruto=data.valor_bruto,
        valor_taxa=data.valor_taxa,
        valor_liquido=data.valor_liquido,
        periodo_inicio=data.periodo_inicio,
        periodo_fim=data.periodo_fim,
        status="pendente",
        comprovante=data.comprovante,
        observacao=data.observacao,
        usuario_id=current_user.id,
    )
    db.add(repasse)
    db.commit()
    db.refresh(repasse)
    resp = RepasseResponse.model_validate(repasse)
    resp.cliente_nome = cli.nome
    return resp


@router.put("/{repasse_id}", response_model=RepasseResponse)
async def atualizar_repasse(
    repasse_id: int,
    data: RepasseUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Atualiza status, comprovante ou observação de um repasse."""
    repasse = db.query(Repasse).filter(Repasse.id == repasse_id).first()
    if not repasse:
        raise HTTPException(status_code=404, detail="Repasse não encontrado.")
    update_data = data.model_dump(exclude_unset=True)
    if "status" in update_data:
        valid = {"pendente", "repassado", "cancelado"}
        if update_data["status"] not in valid:
            raise HTTPException(status_code=400, detail=f"Status deve ser: {', '.join(valid)}")
        if update_data["status"] == "repassado" and repasse.status != "repassado":
            repasse.data_repasse = datetime.utcnow()
    for k, v in update_data.items():
        setattr(repasse, k, v)
    db.commit()
    db.refresh(repasse)
    cli = db.query(Cliente).filter(Cliente.id == repasse.cliente_id).first()
    resp = RepasseResponse.model_validate(repasse)
    resp.cliente_nome = cli.nome if cli else None
    return resp


@router.get("/taxas", response_model=List[TaxaCA])
async def listar_taxas(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Lista taxas configuradas por empresa fiscal (modo=plataforma)."""
    empresas = (
        db.query(Empresa)
        .filter(Empresa.modo_recebimento == "plataforma", Empresa.ativo.is_(True))
        .all()
    )
    return [
        TaxaCA(
            empresa_id=e.id,
            razao_social=e.razao_social,
            taxa_plataforma_percentual=e.taxa_plataforma_percentual,
            taxa_plataforma_valor_fixo=e.taxa_plataforma_valor_fixo,
        )
        for e in empresas
    ]


# --- Relatório de Transportes (SuperAdmin) ---
class TransporteResumoResponse(BaseModel):
    entrega_id: int
    pedido_id: int
    pedido_numero: Optional[str] = None
    tenant_id: int
    tenant_nome: Optional[str] = None
    comprador_nome: Optional[str] = None
    comprador_documento: Optional[str] = None
    entregador_nome: Optional[str] = None
    entregador_tipo_veiculo: Optional[str] = None
    formato_frete: Optional[str] = None
    valor_frete_cliente: Optional[Decimal] = None
    custo_frete_entregador: Optional[Decimal] = None
    lucro_frete_plataforma: Optional[Decimal] = None
    status_entrega: Optional[str] = None
    entregue_em: Optional[datetime] = None


@router.get("/transportes", response_model=dict)
async def relatorio_transportes(
    tenant_id: Optional[int] = Query(None),
    status_entrega: Optional[str] = Query(None),
    entregador_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Relatório completo de transportes para o SuperAdmin com rastreabilidade total."""
    q = (
        db.query(
            EntregaMarketplace,
            PedidoMarketplace,
            Entregador,
            LojaMarketplace,
        )
        .join(PedidoMarketplace, EntregaMarketplace.pedido_id == PedidoMarketplace.id)
        .outerjoin(Entregador, EntregaMarketplace.entregador_id == Entregador.id)
        .outerjoin(LojaMarketplace, PedidoMarketplace.loja_id == LojaMarketplace.id)
    )
    if tenant_id:
        q = q.filter(EntregaMarketplace.tenant_id == tenant_id)
    if status_entrega:
        q = q.filter(EntregaMarketplace.status == status_entrega)
    if entregador_id:
        q = q.filter(EntregaMarketplace.entregador_id == entregador_id)

    total_count = q.count()
    rows = q.order_by(EntregaMarketplace.id.desc()).offset(skip).limit(limit).all()

    totais_q = (
        db.query(
            func.sum(PedidoMarketplace.taxa_entrega).label("total_frete_cobrado"),
            func.sum(PedidoMarketplace.custo_frete).label("total_custo_entregadores"),
            func.sum(PedidoMarketplace.lucro_frete).label("total_lucro_plataforma"),
        )
        .join(EntregaMarketplace, EntregaMarketplace.pedido_id == PedidoMarketplace.id)
        .filter(PedidoMarketplace.formato_frete_snapshot.in_(["taxa_fixa", "plataforma"]))
    )
    if tenant_id:
        totais_q = totais_q.filter(EntregaMarketplace.tenant_id == tenant_id)
    totais = totais_q.first()

    items = []
    for entrega, pedido, entregador, loja in rows:
        items.append(TransporteResumoResponse(
            entrega_id=entrega.id,
            pedido_id=pedido.id,
            pedido_numero=pedido.numero_pedido,
            tenant_id=entrega.tenant_id,
            tenant_nome=loja.nome_loja if loja else None,
            comprador_nome=pedido.comprador_nome,
            comprador_documento=pedido.comprador_documento,
            entregador_nome=entregador.nome if entregador else None,
            entregador_tipo_veiculo=entregador.tipo_veiculo if entregador else None,
            formato_frete=pedido.formato_frete_snapshot,
            valor_frete_cliente=pedido.taxa_entrega,
            custo_frete_entregador=pedido.custo_frete,
            lucro_frete_plataforma=pedido.lucro_frete,
            status_entrega=entrega.status,
            entregue_em=entrega.entregue_em,
        ))

    return {
        "items": [i.model_dump() for i in items],
        "total": total_count,
        "skip": skip,
        "limit": limit,
        "totais": {
            "total_frete_cobrado": float(totais.total_frete_cobrado or 0),
            "total_custo_entregadores": float(totais.total_custo_entregadores or 0),
            "total_lucro_plataforma": float(totais.total_lucro_plataforma or 0),
        },
    }
