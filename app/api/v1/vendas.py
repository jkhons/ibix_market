# PDV Ibix - API de Vendas
#
# Fluxo nova venda (resumo): Abrir modal → Cliente (opcional) → Buscar produto → Adicionar itens
# → Resumo (subtotal/desconto/acréscimo/total) → Finalizar Venda → Popup (pagamentos, PDV, obs.)
# → Confirmar Venda (POST /vendas, POST /venda-pagamentos) → Conclusão. Ver docs/fluxo_nova_venda_resumo.md.
#
import asyncio
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import ValidationError
from sqlalchemy import and_, case, exists, func, or_, text
from sqlalchemy.orm import Session, joinedload

from app.services.conversao_venda_service import registrar_origem_manual
from app.core.audit import audit_action
from app.core.logging import log_error
from app.core.middleware import forbid_cliente_access, get_cliente_scope_dep, get_current_user
from app.core.scope import ClienteScope, get_empresa_fiscal_empresa
from app.database.connection import SessionLocal, get_db
from app.models.abertura_caixa import AberturaCaixa, StatusAberturaCaixa
from app.models.caixa import Caixa
from app.models.cliente import Cliente
from app.models.empresa import Empresa
from app.models.movimentacao_estoque import MovimentacaoEstoque
from app.models.nota_fiscal import NotaFiscal, NotaFiscalItem, OrigemDocumentoFiscalEnum, StatusNotaEnum, TipoNotaEnum
from app.models.produto_cliente import ProdutoCliente
from app.models.tenant import Tenant
from app.models.usuario import Usuario
from app.models.venda import StatusVenda, TipoPagamento, Venda, VendaItem
from app.models.venda_origem import VendaOrigem
from app.models.orcamento import Orcamento
from app.models.ordem_servico import OrdemServico
from app.models.venda_pagamento import VendaPagamento
from app.schemas.cupom import CupomConteudoResponse
from app.schemas.venda import (
    VendaCancelarRequest,
    VendaCreate,
    VendaEstornoRequest,
    VendaFinalizarRequest,
    VendaItemResponse,
    VendaPedidoPendenteCreate,
    VendaResponse,
)
from app.services.cupom_venda_caixa_service import montar_cupom_venda_caixa
from app.services.fiscal.emissao_service import FiscalEmissaoService
from app.services.integration_webhooks import queue_venda_fechada_webhook

# Sem forbid_cliente_access no router: Subcliente pode acessar GET (lista, detalhe, estatísticas).
# Rotas de escrita (POST, PUT, DELETE, estornar) usam Depends(forbid_cliente_access) individualmente.
router = APIRouter(prefix="/vendas", tags=["Vendas"])


def _estabelecimento_cliente_id_da_venda(db: Session, venda: Venda) -> Optional[int]:
    """
    Retorna o cliente_id do estabelecimento da venda.
    Ordem: venda.cliente_id -> empresa do turno de caixa -> primeiro item (produto do estabelecimento).
    """
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
    for vi in (venda.itens or []):
        if getattr(vi, "produto_cliente_id", None):
            pc = db.query(ProdutoCliente).filter(ProdutoCliente.id == vi.produto_cliente_id).first()
            if pc and getattr(pc, "cliente_id", None) is not None:
                return int(pc.cliente_id)
    return None


def _venda_scope_sql_condition(scope: ClienteScope) -> tuple[str, dict]:
    """
    Condição SQL para vendas visíveis no escopo do tenant.
    Inclui vendas pendentes sem caixa/cliente, identificadas pelos produtos do estabelecimento.
    """
    if not scope.must_filter_by_cliente() or not scope.allowed_ids:
        return "", {}
    condition = (
        "((v.cliente_id IS NOT NULL AND v.cliente_id = ANY(:cliente_ids)) OR "
        "(e_caixa.cliente_id IS NOT NULL AND e_caixa.cliente_id = ANY(:cliente_ids)) OR "
        "EXISTS ("
        "SELECT 1 FROM venda_itens vi_scope "
        "INNER JOIN produtos_cliente pc_scope ON pc_scope.id = vi_scope.produto_cliente_id "
        "WHERE vi_scope.venda_id = v.id AND pc_scope.cliente_id = ANY(:cliente_ids)"
        "))"
    )
    return condition, {"cliente_ids": scope.allowed_ids}


def _venda_scope_orm_filter(scope: ClienteScope):
    """Filtro ORM equivalente a _venda_scope_sql_condition."""
    if not scope.must_filter_by_cliente() or not scope.allowed_ids:
        return None
    ids = scope.allowed_ids
    produto_scope = exists().where(
        and_(
            VendaItem.venda_id == Venda.id,
            ProdutoCliente.id == VendaItem.produto_cliente_id,
            ProdutoCliente.cliente_id.in_(ids),
        )
    )
    caixa_scope = exists().where(
        and_(
            Venda.abertura_caixa_id == AberturaCaixa.id,
            AberturaCaixa.caixa_id == Caixa.id,
            Caixa.empresa_id == Empresa.id,
            Empresa.cliente_id.in_(ids),
        )
    )
    return or_(
        Venda.cliente_id.in_(ids),
        caixa_scope,
        produto_scope,
    )


def _venda_visivel_no_escopo(db: Session, venda: Venda, scope: ClienteScope) -> bool:
    """Verifica se a venda pertence ao escopo (mesma regra da listagem)."""
    if not scope.must_filter_by_cliente():
        return True
    if not scope.allowed_ids:
        return False
    ids = set(scope.allowed_ids)
    if venda.cliente_id is not None and venda.cliente_id in ids:
        return True
    ab_id = getattr(venda, "abertura_caixa_id", None)
    if ab_id:
        ab = getattr(venda, "abertura_caixa", None) or db.query(AberturaCaixa).filter(AberturaCaixa.id == ab_id).first()
        if ab:
            cx = getattr(ab, "caixa", None) or db.query(Caixa).filter(Caixa.id == ab.caixa_id).first()
            if cx:
                emp = db.query(Empresa).filter(Empresa.id == cx.empresa_id).first()
                if emp and getattr(emp, "cliente_id", None) in ids:
                    return True
    for vi in (venda.itens or []):
        pc = getattr(vi, "produto_cliente", None)
        if pc is None and getattr(vi, "produto_cliente_id", None):
            pc = db.query(ProdutoCliente).filter(ProdutoCliente.id == vi.produto_cliente_id).first()
        if pc and getattr(pc, "cliente_id", None) in ids:
            return True
    return False


def _criar_rascunho_nfe_ao_finalizar_venda(
    db: Session,
    venda: Venda,
    usuario_id: int,
    empresa_fiscal_usuario: Optional[Empresa] = None,
) -> None:
    """Cria rascunho de NF-e. Usa a Empresa FISCAL do CA dono da venda (nunca de outro CA/tenant)."""
    if not empresa_fiscal_usuario:
        return
    empresa = empresa_fiscal_usuario
    from datetime import datetime as dt
    from decimal import Decimal
    serie = getattr(empresa, "serie_padrao_nfce", None) or getattr(empresa, "serie_padrao_nfe", None) or "1"
    modelo = "65"
    tipo = TipoNotaEnum.NFCE
    numero_rascunho = f"RASCUNHO-VENDA-{venda.id}"
    nota = NotaFiscal(
        numero=numero_rascunho,
        serie=serie,
        tipo=tipo,
        modelo=modelo,
        data_emissao=dt.utcnow(),
        cliente_id=venda.cliente_id,
        empresa_id=empresa.id,
        venda_id=venda.id,
        emitido_por_id=usuario_id,
        valor_total=venda.total or Decimal("0"),
        valor_produtos=venda.subtotal or Decimal("0"),
        status=StatusNotaEnum.RASCUNHO,
        origem_documento=OrigemDocumentoFiscalEnum.VENDA_BALCAO,
    )
    db.add(nota)
    db.flush()
    for idx, vi in enumerate(venda.itens or [], start=1):
        descricao = None
        ncm = None
        cfop = None
        unidade = "UN"
        cest = None
        origem = None
        if getattr(vi, "produto_cliente_id", None):
            produto_pc = db.query(ProdutoCliente).filter(ProdutoCliente.id == vi.produto_cliente_id).first()
            if produto_pc:
                descricao = produto_pc.nome
                ncm = getattr(produto_pc, "ncm", None) and str(produto_pc.ncm).strip() or None
                cfop = getattr(produto_pc, "cfop_padrao", None) and str(produto_pc.cfop_padrao).strip() or None
                unidade = (getattr(produto_pc, "unidade_medida", None) and str(produto_pc.unidade_medida).strip()) or "UN"
                cest = getattr(produto_pc, "cest", None) and str(produto_pc.cest).strip() or None
                if getattr(produto_pc, "origem_mercadoria", None) is not None:
                    origem = int(produto_pc.origem_mercadoria)
        descricao = descricao or getattr(vi, "observacoes", None) or f"Item {idx}"
        item = NotaFiscalItem(
            nota_id=nota.id,
            item_numero=idx,
            produto_cliente_id=getattr(vi, "produto_cliente_id", None),
            descricao=descricao[:255] if descricao else f"Item {idx}",
            unidade=unidade[:10] if unidade else "UN",
            quantidade=getattr(vi, "quantidade", None) or Decimal("1"),
            valor_unitario=getattr(vi, "valor_unitario", None) or Decimal("0"),
            valor_total=getattr(vi, "valor_total", None) or Decimal("0"),
            ncm=ncm,
            cfop=cfop,
            cest=cest,
            origem=origem,
        )
        db.add(item)
    venda.nota_fiscal_id = nota.id


def normalizar_status_venda(status: Optional[StatusVenda | str]) -> str:
    """Garantir status em minúsculo e tratar valores legados."""
    if status is None:
        return ""

    if isinstance(status, StatusVenda):
        valor = status.value
    else:
        valor = str(status)

    if valor == StatusVenda.FINALIZADA_LEGADO.value:
        return StatusVenda.FINALIZADA.value.lower()

    return valor.lower()


def _gerar_numero_venda(db: Session) -> str:
    """Delega para o serviço compartilhado (único gerador para Nova Venda e Enviar para vendas)."""
    from app.services.venda_numero import gerar_numero_venda
    return gerar_numero_venda(db)


# Rotas com path literal primeiro (evitar que /estatisticas e /produtos sejam capturados por /{venda_id})
@router.get("/estatisticas", response_model=dict)
async def obter_estatisticas_vendas(
    db: Session = Depends(get_db),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Obter estatísticas das vendas (respeitando escopo do usuário)."""
    try:
        query = db.query(
            func.count(Venda.id).label("total_vendas"),
            func.coalesce(func.sum(Venda.total), 0).label("valor_total_vendas"),
            func.coalesce(
                func.sum(
                    case(
                        (Venda.status == StatusVenda.PENDENTE.value, 1),
                        else_=0
                    )
                ),
                0
            ).label("vendas_pendentes")
        )

        if scope.must_filter_by_cliente():
            if not scope.allowed_ids:
                return {"total_vendas": 0, "valor_total_vendas": 0.0, "vendas_pendentes": 0, "valor_medio_venda": 0.0}
            scope_filter = _venda_scope_orm_filter(scope)
            if scope_filter is not None:
                query = query.filter(scope_filter)

        resultado = query.one()
        total_vendas = int(resultado.total_vendas or 0)
        valor_total = float(resultado.valor_total_vendas or 0)
        vendas_pendentes = int(resultado.vendas_pendentes or 0)
        ticket_medio = (valor_total / total_vendas) if total_vendas else 0.0

        return {
            "total_vendas": total_vendas,
            "valor_total_vendas": valor_total,
            "vendas_pendentes": vendas_pendentes,
            "valor_medio_venda": ticket_medio
        }
    except Exception as e:
        log_error(f"❌ Erro ao obter estatísticas de vendas: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {str(e)}")


@router.get("/produtos", response_model=List[dict])
async def listar_produtos(
    busca: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Listar produtos disponíveis para venda (catálogo do estabelecimento). Filtro por escopo; estoque validado ao finalizar."""
    try:
        query = db.query(ProdutoCliente).options(joinedload(ProdutoCliente.categoria_rel)).filter(ProdutoCliente.ativo == True)
        if scope.must_filter_by_cliente() and scope.allowed_ids:
            query = query.filter(ProdutoCliente.cliente_id.in_(scope.allowed_ids))
        if busca:
            query = query.filter(
                or_(
                    ProdutoCliente.codigo.ilike(f"%{busca}%"),
                    ProdutoCliente.nome.ilike(f"%{busca}%"),
                    func.coalesce(ProdutoCliente.descricao, "").ilike(f"%{busca}%"),
                )
            )
        produtos = query.order_by(ProdutoCliente.nome).all()
        produtos_dict = []
        for produto in produtos:
            produtos_dict.append({
                "id": produto.id,
                "cliente_id": produto.cliente_id,
                "codigo": produto.codigo,
                "nome": produto.nome,
                "descricao": produto.descricao,
                "categoria": (produto.categoria_rel.nome if produto.categoria_rel else None) or getattr(produto, "categoria", None),
                "quantidade_atual": float(produto.quantidade_atual),
                "unidade_medida": produto.unidade_medida,
                "valor_venda": float(produto.valor_venda) if produto.valor_venda else 0,
                "foto_peca": getattr(produto, "foto_peca", None),
            })
        return produtos_dict
    except Exception as e:
        log_error(f"❌ Erro ao listar produtos: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {str(e)}")


@router.post("/", response_model=VendaResponse, status_code=status.HTTP_201_CREATED)
async def criar_venda(
    venda_data: VendaCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
    _: None = Depends(forbid_cliente_access),
):
    """Criar nova venda. Subcliente não pode criar (forbid_cliente_access)."""
    try:
        if scope.must_filter_by_cliente() and venda_data.cliente_id is not None and venda_data.cliente_id not in scope.allowed_ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cliente fora do seu escopo de acesso")
        
        # Verificar se cliente existe (se fornecido)
        if venda_data.cliente_id:
            cliente = db.query(Cliente).filter(Cliente.id == venda_data.cliente_id).first()
            if not cliente:
                raise HTTPException(status_code=404, detail="Cliente não encontrado")
        
        # Verificar se produtos existem e têm estoque suficiente (apenas produto_cliente_id)
        for i, item in enumerate(venda_data.itens):
            try:
                if item.produto_cliente_id is None:
                    raise HTTPException(status_code=400, detail=f"Item {i+1}: produto_cliente_id é obrigatório")
                produto_pc = db.query(ProdutoCliente).filter(ProdutoCliente.id == item.produto_cliente_id).first()
                if not produto_pc:
                    raise HTTPException(status_code=404, detail=f"Produto estabelecimento ID {item.produto_cliente_id} não encontrado")
                if not produto_pc.ativo:
                    raise HTTPException(status_code=400, detail=f"Produto {produto_pc.nome} está inativo")
                if float(produto_pc.quantidade_atual) < item.quantidade:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Estoque insuficiente para {produto_pc.nome}. Disponível: {produto_pc.quantidade_atual}, Solicitado: {item.quantidade}",
                    )
            except HTTPException:
                raise
            except Exception as e:
                log_error(f"❌ Erro ao verificar item {i+1}: {e}")
                raise

        # Turno de caixa (obrigatório) — mesma empresa fiscal do usuário
        ab = (
            db.query(AberturaCaixa)
            .options(joinedload(AberturaCaixa.caixa))
            .filter(AberturaCaixa.id == venda_data.abertura_caixa_id)
            .first()
        )
        if not ab:
            raise HTTPException(status_code=404, detail="Turno de caixa (abertura) não encontrado")
        if str(ab.status).lower() != StatusAberturaCaixa.ABERTA.value:
            raise HTTPException(
                status_code=400,
                detail="Turno de caixa não está aberto. Abra o caixa em Negócios > Caixa.",
            )
        empresa_fiscal_venda = get_empresa_fiscal_empresa(
            db, current_user.id, current_user.role.nome if current_user.role else None
        )
        if not empresa_fiscal_venda:
            raise HTTPException(
                status_code=400,
                detail="Empresa fiscal obrigatória para registrar venda. Configure em /fiscal/empresa",
            )
        cx_turno = ab.caixa if getattr(ab, "caixa", None) else db.query(Caixa).filter(Caixa.id == ab.caixa_id).first()
        if not cx_turno or cx_turno.empresa_id != empresa_fiscal_venda.id:
            raise HTTPException(
                status_code=403,
                detail="Turno de caixa não pertence à sua empresa fiscal.",
            )

        from datetime import datetime
        data_atual = datetime.now()
        numero_venda = _gerar_numero_venda(db)
        
        # Criar venda
        try:
            tipo_pagamento_enum = TipoPagamento(venda_data.tipo_pagamento) if venda_data.tipo_pagamento else None
        except Exception as e:
            log_error(f"❌ Erro ao converter tipo de pagamento: {e}")
            raise HTTPException(status_code=400, detail=f"Tipo de pagamento inválido: {venda_data.tipo_pagamento}")
        try:
            # O banco de dados usa valores em minúsculo no ENUM
            # Precisamos usar FINALIZADA_LEGADO que tem o valor "finalizada" correspondente ao banco
            # Mas vamos criar o objeto com String diretamente para evitar validação do enum
            nova_venda = Venda(
                numero_venda=numero_venda,
                data_venda=data_atual,
                status=StatusVenda.FINALIZADA_LEGADO.value,  # Usar .value para obter a string "finalizada"
                cliente_id=venda_data.cliente_id,
                abertura_caixa_id=venda_data.abertura_caixa_id,
                vendedor_id=current_user.id,
                subtotal=venda_data.subtotal,
                desconto=venda_data.desconto,
                acrescimo=venda_data.acrescimo,
                total=venda_data.total,
                tipo_pagamento=tipo_pagamento_enum.value if tipo_pagamento_enum else None,  # Usar .value para string
                valor_pago=venda_data.valor_pago,
                troco=venda_data.troco,
                observacoes=venda_data.observacoes
            )
        except Exception as e:
            log_error(f"❌ Erro ao criar objeto Venda: {e}")
            log_error(f"❌ Tipo do erro: {type(e).__name__}")
            raise
        
        db.add(nova_venda)
        db.flush()  # Para obter o ID da venda
        
        # Criar itens da venda e atualizar estoque (ProdutoCliente)
        from decimal import Decimal
        itens_criados = []
        for i, item_data in enumerate(venda_data.itens):
            try:
                item_venda = VendaItem(
                    venda_id=nova_venda.id,
                    produto_cliente_id=item_data.produto_cliente_id,
                    quantidade=item_data.quantidade,
                    valor_unitario=item_data.valor_unitario,
                    valor_total=item_data.valor_total,
                    desconto_item=item_data.desconto_item,
                    observacoes=item_data.observacoes,
                )
                db.add(item_venda)
                itens_criados.append(item_venda)
            except Exception as e:
                log_error(f"❌ Erro ao criar VendaItem {i+1}: {e}")
                raise

            quantidade_subtrair = Decimal(str(item_data.quantidade))
            produto_pc = db.query(ProdutoCliente).filter(ProdutoCliente.id == item_data.produto_cliente_id).first()
            if produto_pc:
                produto_pc.quantidade_atual -= quantidade_subtrair
                mov = MovimentacaoEstoque(
                    produto_cliente_id=produto_pc.id,
                    tipo="saida",
                    quantidade=quantidade_subtrair,
                    valor_unitario=Decimal(str(item_data.valor_unitario)),
                    documento_ref=f"Venda {nova_venda.numero_venda}",
                    usuario_id=current_user.id,
                )
                db.add(mov)
        
        db.commit()
        db.refresh(nova_venda)
        registrar_origem_manual(db, nova_venda, current_user.id)
        db.commit()
        audit_action(
            db,
            "venda_criada",
            user_id=current_user.id,
            tenant_id=getattr(current_user, "tenant_id", None),
            recurso_tipo="venda",
            recurso_id=nova_venda.id,
            detalhes=f"numero={nova_venda.numero_venda} total={nova_venda.total}",
        )
        venda_completa = db.query(Venda).options(
            joinedload(Venda.itens),
            joinedload(Venda.abertura_caixa).joinedload(AberturaCaixa.caixa),
        ).filter(Venda.id == nova_venda.id).first()
        if venda_completa and venda_completa.status in (StatusVenda.FINALIZADA.value, StatusVenda.FINALIZADA_LEGADO.value, "finalizada", "FINALIZADA"):
            try:
                # Uma Empresa FISCAL por CA; usamos a do CA para a nota
                empresa_do_ca = get_empresa_fiscal_empresa(db, current_user.id, current_user.role.nome if current_user.role else None)
                _criar_rascunho_nfe_ao_finalizar_venda(db, venda_completa, current_user.id, empresa_fiscal_usuario=empresa_do_ca)
                db.commit()
            except Exception as e:
                log_error(f"Erro ao criar rascunho NF-e para venda {venda_completa.id}: {e}")
                try:
                    db.rollback()
                except Exception:
                    pass
            try:
                queue_venda_fechada_webhook(
                    db=db,
                    venda_id=venda_completa.id,
                    numero_venda=venda_completa.numero_venda,
                    cliente_id=venda_completa.cliente_id,
                    total=venda_completa.total,
                    vendedor_id=current_user.id,
                    tenant_id=getattr(current_user, "tenant_id", None),
                )
            except Exception as e:
                log_error(f"Erro ao preparar webhook venda.fechada para venda {venda_completa.id}: {e}")
        
        if not venda_completa:
            log_error(f"❌ Venda {nova_venda.id} não encontrada após commit")
            raise HTTPException(status_code=500, detail="Erro ao carregar venda criada")
        
        # Converter itens para dict
        itens_dict = []
        for item in venda_completa.itens:
            itens_dict.append({
                "id": item.id,
                "venda_id": item.venda_id,
                "produto_cliente_id": getattr(item, "produto_cliente_id", None),
                "quantidade": float(item.quantidade),
                "valor_unitario": float(item.valor_unitario),
                "valor_total": float(item.valor_total),
                "desconto_item": float(item.desconto_item),
                "observacoes": item.observacoes,
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "updated_at": item.updated_at.isoformat() if item.updated_at else None,
            })
        
        try:
            _ab = venda_completa.abertura_caixa
            _cx = _ab.caixa if _ab and getattr(_ab, "caixa", None) else None
            resposta = VendaResponse(
                id=venda_completa.id,
                numero_venda=venda_completa.numero_venda,
                data_venda=venda_completa.data_venda,
                status=normalizar_status_venda(venda_completa.status),
                cliente_id=venda_completa.cliente_id,
                abertura_caixa_id=getattr(venda_completa, "abertura_caixa_id", None),
                caixa_id=_cx.id if _cx else None,
                caixa_identificador=_cx.identificador if _cx else None,
                vendedor_id=venda_completa.vendedor_id,
                subtotal=float(venda_completa.subtotal),
                desconto=float(venda_completa.desconto),
                acrescimo=float(venda_completa.acrescimo),
                total=float(venda_completa.total),
                tipo_pagamento=venda_completa.tipo_pagamento,
                valor_pago=float(venda_completa.valor_pago),
                troco=float(venda_completa.troco),
                observacoes=venda_completa.observacoes,
                itens=itens_dict,
                nota_fiscal_id=getattr(venda_completa, "nota_fiscal_id", None),
                created_at=venda_completa.created_at,
                updated_at=venda_completa.updated_at
            )
            return resposta
        except Exception as e:
            log_error(f"❌ Erro ao criar resposta: {e}")
            raise
        
    except HTTPException:
        raise
    except ValidationError as e:
        log_error(f"❌ Erro de validação: {e}")
        log_error(f"❌ Detalhes: {e.errors()}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Erro de validação: {e}"
        )
    except Exception as e:
        log_error(f"❌ Erro ao criar venda: {e}")
        log_error(f"❌ Tipo do erro: {type(e).__name__}")
        log_error(f"❌ Detalhes do erro: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )


def _venda_badge_status_pendente(status_bruto) -> bool:
    return normalizar_status_venda(status_bruto) == "pendente"


def _validar_itens_pedido_pendente(db: Session, itens) -> None:
    """Valida produtos dos itens de pedido pendente (criação ou edição)."""
    for i, item in enumerate(itens):
        if item.produto_cliente_id is None:
            raise HTTPException(status_code=400, detail=f"Item {i+1}: produto_cliente_id é obrigatório")
        produto_pc = db.query(ProdutoCliente).filter(ProdutoCliente.id == item.produto_cliente_id).first()
        if not produto_pc:
            raise HTTPException(
                status_code=404,
                detail=f"Produto estabelecimento ID {item.produto_cliente_id} não encontrado",
            )
        if not produto_pc.ativo:
            raise HTTPException(status_code=400, detail=f"Produto {produto_pc.nome} está inativo")


def _validar_turno_caixa_venda(
    db: Session, abertura_caixa_id: int, current_user: Usuario
) -> AberturaCaixa:
    """Reutiliza a mesma regra de POST /vendas (empresa fiscal + turno aberto)."""
    ab = (
        db.query(AberturaCaixa)
        .options(joinedload(AberturaCaixa.caixa))
        .filter(AberturaCaixa.id == abertura_caixa_id)
        .first()
    )
    if not ab:
        raise HTTPException(status_code=404, detail="Turno de caixa (abertura) não encontrado")
    if str(ab.status).lower() != StatusAberturaCaixa.ABERTA.value:
        raise HTTPException(
            status_code=400,
            detail="Turno de caixa não está aberto. Abra o caixa em Negócios > Caixa.",
        )
    empresa_fiscal_venda = get_empresa_fiscal_empresa(
        db, current_user.id, current_user.role.nome if current_user.role else None
    )
    if not empresa_fiscal_venda:
        raise HTTPException(
            status_code=400,
            detail="Empresa fiscal obrigatória para registrar venda. Configure em /fiscal/empresa",
        )
    cx_turno = ab.caixa if getattr(ab, "caixa", None) else db.query(Caixa).filter(Caixa.id == ab.caixa_id).first()
    if not cx_turno or cx_turno.empresa_id != empresa_fiscal_venda.id:
        raise HTTPException(status_code=403, detail="Turno de caixa não pertence à sua empresa fiscal.")
    return ab


def _origem_cadeia_venda(db: Session, venda_id: int, venda_row: dict) -> list:
    """Monta breadcrumb ordenado (raiz → imediata → venda) com timestamps de conversão."""
    from app.services.conversao_venda_service import montar_origem_cadeia_resposta

    rows = (
        db.query(VendaOrigem)
        .filter(VendaOrigem.venda_id == venda_id)
        .order_by(VendaOrigem.papel.asc(), VendaOrigem.created_at.asc())
        .all()
    )
    return montar_origem_cadeia_resposta(venda_id, venda_row, rows)


def _campos_origem_venda(db: Session, venda: Venda) -> dict:
    """Enriquece resposta ORM com rastreio comercial (FKs + venda_origens)."""
    numero_orcamento = None
    ordem_servico_codigo = None
    if venda.orcamento_id:
        orc = db.query(Orcamento).filter(Orcamento.id == venda.orcamento_id).first()
        numero_orcamento = orc.numero_orcamento if orc else None
    if venda.ordem_servico_id:
        os_row = db.query(OrdemServico).filter(OrdemServico.id == venda.ordem_servico_id).first()
        ordem_servico_codigo = os_row.codigo if os_row else None

    origem_imediata_tipo = origem_imediata_ref = origem_raiz_tipo = origem_raiz_ref = None
    for vo in db.query(VendaOrigem).filter(VendaOrigem.venda_id == venda.id).all():
        if vo.papel == "imediata":
            origem_imediata_tipo = vo.tipo_origem
            origem_imediata_ref = vo.documento_ref
        elif vo.papel == "raiz":
            origem_raiz_tipo = vo.tipo_origem
            origem_raiz_ref = vo.documento_ref

    return {
        "orcamento_id": getattr(venda, "orcamento_id", None),
        "numero_orcamento": numero_orcamento,
        "ordem_servico_id": getattr(venda, "ordem_servico_id", None),
        "ordem_servico_codigo": ordem_servico_codigo,
        "origem_imediata_tipo": origem_imediata_tipo,
        "origem_imediata_ref": origem_imediata_ref,
        "origem_raiz_tipo": origem_raiz_tipo,
        "origem_raiz_ref": origem_raiz_ref,
    }


def _venda_response_orm(db: Session, venda_id: int) -> VendaResponse:
    venda_completa = (
        db.query(Venda)
        .options(
            joinedload(Venda.itens),
            joinedload(Venda.abertura_caixa).joinedload(AberturaCaixa.caixa),
        )
        .filter(Venda.id == venda_id)
        .first()
    )
    if not venda_completa:
        raise HTTPException(status_code=404, detail="Venda não encontrada")
    itens_resp: List[VendaItemResponse] = []
    for item in venda_completa.itens or []:
        itens_resp.append(VendaItemResponse.model_validate(item, from_attributes=True))
    _ab = venda_completa.abertura_caixa
    _cx = _ab.caixa if _ab and getattr(_ab, "caixa", None) else None
    origem = _campos_origem_venda(db, venda_completa)
    origem["origem_cadeia"] = _origem_cadeia_venda(
        db,
        venda_completa.id,
        {
            **origem,
            "numero_venda": venda_completa.numero_venda,
            "created_at": venda_completa.created_at,
        },
    )
    return VendaResponse(
        id=venda_completa.id,
        numero_venda=venda_completa.numero_venda,
        data_venda=venda_completa.data_venda,
        status=normalizar_status_venda(venda_completa.status),
        cliente_id=venda_completa.cliente_id,
        abertura_caixa_id=getattr(venda_completa, "abertura_caixa_id", None),
        caixa_id=_cx.id if _cx else None,
        caixa_identificador=_cx.identificador if _cx else None,
        vendedor_id=venda_completa.vendedor_id,
        subtotal=float(venda_completa.subtotal),
        desconto=float(venda_completa.desconto),
        acrescimo=float(venda_completa.acrescimo),
        total=float(venda_completa.total),
        tipo_pagamento=venda_completa.tipo_pagamento,
        valor_pago=float(venda_completa.valor_pago),
        troco=float(venda_completa.troco),
        observacoes=venda_completa.observacoes,
        itens=itens_resp,
        nota_fiscal_id=getattr(venda_completa, "nota_fiscal_id", None),
        **origem,
        created_at=venda_completa.created_at,
        updated_at=venda_completa.updated_at,
    )


@router.post("/pedido-pendente", response_model=VendaResponse, status_code=status.HTTP_201_CREATED)
async def criar_pedido_venda_pendente(
    body: VendaPedidoPendenteCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
    _: None = Depends(forbid_cliente_access),
):
    """
    Cria venda com status PENDENTE (sem pagamento, sem baixa de estoque).
    Finalize depois com POST /vendas/{id}/finalizar.
    """
    if scope.must_filter_by_cliente() and body.cliente_id is not None and body.cliente_id not in scope.allowed_ids:
        raise HTTPException(status_code=403, detail="Cliente fora do seu escopo de acesso")
    if body.cliente_id:
        cliente = db.query(Cliente).filter(Cliente.id == body.cliente_id).first()
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente não encontrado")

    _validar_itens_pedido_pendente(db, body.itens)

    data_atual = datetime.now()
    numero_venda = _gerar_numero_venda(db)

    nova_venda = Venda(
        numero_venda=numero_venda,
        data_venda=data_atual,
        status=StatusVenda.PENDENTE.value,
        cliente_id=body.cliente_id,
        vendedor_id=current_user.id,
        subtotal=body.subtotal,
        desconto=body.desconto,
        acrescimo=body.acrescimo,
        total=body.total,
        tipo_pagamento=None,
        valor_pago=Decimal("0"),
        troco=Decimal("0"),
        observacoes=body.observacoes,
        abertura_caixa_id=None,
    )
    db.add(nova_venda)
    db.flush()

    for item_data in body.itens:
        db.add(
            VendaItem(
                venda_id=nova_venda.id,
                produto_cliente_id=item_data.produto_cliente_id,
                quantidade=item_data.quantidade,
                valor_unitario=item_data.valor_unitario,
                valor_total=item_data.valor_total,
                desconto_item=item_data.desconto_item,
                observacoes=item_data.observacoes,
            )
        )

    db.commit()
    db.refresh(nova_venda)
    registrar_origem_manual(db, nova_venda, current_user.id)
    db.commit()
    audit_action(
        db,
        "venda_pendente_criada",
        user_id=current_user.id,
        tenant_id=getattr(current_user, "tenant_id", None),
        recurso_tipo="venda",
        recurso_id=nova_venda.id,
        detalhes=f"numero={nova_venda.numero_venda} pendente=True",
    )
    return _venda_response_orm(db, nova_venda.id)


@router.put("/{venda_id}/pedido-pendente", response_model=VendaResponse)
async def atualizar_pedido_venda_pendente(
    venda_id: int,
    body: VendaPedidoPendenteCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
    _: None = Depends(forbid_cliente_access),
):
    """
    Atualiza venda PENDENTE: cliente, totais e itens (substituição completa).
    Não altera estoque nem pagamentos — somente pedidos ainda não finalizados.
    """
    venda = (
        db.query(Venda)
        .options(joinedload(Venda.itens))
        .filter(Venda.id == venda_id)
        .first()
    )
    if not venda:
        raise HTTPException(status_code=404, detail="Venda não encontrada")
    if scope.must_filter_by_cliente() and not _venda_visivel_no_escopo(db, venda, scope):
        raise HTTPException(status_code=404, detail="Venda não encontrada")

    if not _venda_badge_status_pendente(venda.status):
        raise HTTPException(
            status_code=400,
            detail="Somente vendas com status pendente podem ser editadas por esta rota.",
        )

    if scope.must_filter_by_cliente() and body.cliente_id is not None and body.cliente_id not in scope.allowed_ids:
        raise HTTPException(status_code=403, detail="Cliente fora do seu escopo de acesso")
    if body.cliente_id:
        cliente = db.query(Cliente).filter(Cliente.id == body.cliente_id).first()
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente não encontrado")

    _validar_itens_pedido_pendente(db, body.itens)

    for item_antigo in list(venda.itens or []):
        db.delete(item_antigo)
    db.flush()

    venda.cliente_id = body.cliente_id
    venda.subtotal = body.subtotal
    venda.desconto = body.desconto
    venda.acrescimo = body.acrescimo
    venda.total = body.total
    if body.observacoes is not None:
        venda.observacoes = body.observacoes

    for item_data in body.itens:
        db.add(
            VendaItem(
                venda_id=venda.id,
                produto_cliente_id=item_data.produto_cliente_id,
                quantidade=item_data.quantidade,
                valor_unitario=item_data.valor_unitario,
                valor_total=item_data.valor_total,
                desconto_item=item_data.desconto_item,
                observacoes=item_data.observacoes,
            )
        )

    db.commit()
    db.refresh(venda)
    audit_action(
        db,
        "venda_pendente_atualizada",
        user_id=current_user.id,
        tenant_id=getattr(current_user, "tenant_id", None),
        recurso_tipo="venda",
        recurso_id=venda.id,
        detalhes=f"numero={venda.numero_venda} itens={len(body.itens)}",
    )
    return _venda_response_orm(db, venda.id)


@router.post("/{venda_id}/finalizar", response_model=VendaResponse)
async def finalizar_venda_pendente(
    venda_id: int,
    body: VendaFinalizarRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
    _: None = Depends(forbid_cliente_access),
):
    """Conclui venda PENDENTE: pagamentos, baixa de estoque nos itens com produto, status finalizada."""
    venda = (
        db.query(Venda)
        .options(joinedload(Venda.itens))
        .filter(Venda.id == venda_id)
        .first()
    )
    if not venda:
        raise HTTPException(status_code=404, detail="Venda não encontrada")
    if scope.must_filter_by_cliente() and not _venda_visivel_no_escopo(db, venda, scope):
        raise HTTPException(status_code=404, detail="Venda não encontrada")

    if not _venda_badge_status_pendente(venda.status):
        raise HTTPException(
            status_code=400,
            detail="Somente vendas com status pendente podem ser finalizadas por esta rota.",
        )

    subtotal_dec = Decimal(str(venda.subtotal or 0))
    desconto_dec = Decimal(str(body.desconto if body.desconto is not None else (venda.desconto or 0)))
    acrescimo_dec = Decimal(str(body.acrescimo if body.acrescimo is not None else (venda.acrescimo or 0)))
    total_dec = subtotal_dec - desconto_dec + acrescimo_dec
    if total_dec < Decimal("0"):
        raise HTTPException(status_code=400, detail="Total da venda não pode ser negativo.")
    venda.desconto = desconto_dec
    venda.acrescimo = acrescimo_dec
    venda.total = total_dec

    valor_pago_dec = Decimal(str(body.valor_pago))
    troco_dec = Decimal(str(body.troco))
    if valor_pago_dec + Decimal("0.001") < total_dec:
        raise HTTPException(
            status_code=400,
            detail=f"Valor pago ({valor_pago_dec}) não pode ser menor que o total ({total_dec}).",
        )
    esperado_troco = valor_pago_dec - total_dec if valor_pago_dec > total_dec else Decimal("0")
    if abs(float(esperado_troco - troco_dec)) > 0.02:
        raise HTTPException(
            status_code=400,
            detail=f"Troco inconsistente. Esperado {esperado_troco:.2f}, informado {troco_dec:.2f}.",
        )

    _validar_turno_caixa_venda(db, body.abertura_caixa_id, current_user)

    linhas_pg = body.pagamentos if body.pagamentos and len(body.pagamentos) > 0 else None
    if linhas_pg:
        soma_pg = sum(Decimal(str(p.valor)) for p in linhas_pg)
        if abs(float(soma_pg - valor_pago_dec)) > 0.02:
            raise HTTPException(
                status_code=400,
                detail="A soma dos pagamentos fracionados deve coincidir com valor_pago.",
            )

    try:
        tipo_pg_enum = TipoPagamento(body.tipo_pagamento)
    except Exception:
        raise HTTPException(status_code=400, detail="Tipo de pagamento inválido")

    for vi in venda.itens or []:
        if not getattr(vi, "produto_cliente_id", None):
            continue
        produto_pc = db.query(ProdutoCliente).filter(ProdutoCliente.id == vi.produto_cliente_id).first()
        if not produto_pc:
            raise HTTPException(status_code=404, detail=f"Produto item id {vi.produto_cliente_id} não encontrado")
        qtd = Decimal(str(vi.quantidade or 0))
        if float(produto_pc.quantidade_atual) < float(qtd):
            raise HTTPException(
                status_code=400,
                detail=f"Estoque insuficiente para {produto_pc.nome}. Disponível: {produto_pc.quantidade_atual}, necessário: {qtd}",
            )

    for vi in venda.itens or []:
        if not getattr(vi, "produto_cliente_id", None):
            continue
        produto_pc = db.query(ProdutoCliente).filter(ProdutoCliente.id == vi.produto_cliente_id).first()
        if not produto_pc:
            continue
        qtd = Decimal(str(vi.quantidade or 0))
        produto_pc.quantidade_atual -= qtd
        db.add(
            MovimentacaoEstoque(
                produto_cliente_id=produto_pc.id,
                tipo="saida",
                quantidade=qtd,
                valor_unitario=Decimal(str(vi.valor_unitario or 0)),
                documento_ref=f"Venda {venda.numero_venda}",
                usuario_id=current_user.id,
            )
        )

    venda.abertura_caixa_id = body.abertura_caixa_id
    venda.tipo_pagamento = tipo_pg_enum.value
    venda.valor_pago = valor_pago_dec
    venda.troco = troco_dec
    venda.status = StatusVenda.FINALIZADA_LEGADO.value
    if body.observacoes and body.observacoes.strip():
        prefix = (venda.observacoes or "").strip()
        venda.observacoes = (
            prefix + ("\n\n" if prefix else "") + "[Pagamento] " + body.observacoes.strip()
        )

    db.flush()

    if linhas_pg:
        for pg in linhas_pg:
            db.add(
                VendaPagamento(
                    venda_id=venda.id,
                    forma=pg.forma,
                    valor=Decimal(str(pg.valor)),
                    status="confirmado",
                )
            )
    else:
        db.add(
            VendaPagamento(
                venda_id=venda.id,
                forma=tipo_pg_enum.value,
                valor=valor_pago_dec,
                status="confirmado",
            )
        )

    db.commit()
    db.refresh(venda)

    venda_completa = (
        db.query(Venda)
        .options(
            joinedload(Venda.itens),
            joinedload(Venda.abertura_caixa).joinedload(AberturaCaixa.caixa),
        )
        .filter(Venda.id == venda_id)
        .first()
    )
    if venda_completa and normalizar_status_venda(venda_completa.status) == "finalizada":
        try:
            empresa_do_ca = get_empresa_fiscal_empresa(
                db, current_user.id, current_user.role.nome if current_user.role else None
            )
            _criar_rascunho_nfe_ao_finalizar_venda(db, venda_completa, current_user.id, empresa_fiscal_usuario=empresa_do_ca)
            db.commit()
        except Exception as e:
            log_error(f"Erro ao criar rascunho NF-e para venda {venda_completa.id}: {e}")
            try:
                db.rollback()
            except Exception:
                pass
        try:
            queue_venda_fechada_webhook(
                db=db,
                venda_id=venda_completa.id,
                numero_venda=venda_completa.numero_venda,
                cliente_id=venda_completa.cliente_id,
                total=venda_completa.total,
                vendedor_id=current_user.id,
                tenant_id=getattr(current_user, "tenant_id", None),
            )
        except Exception as e:
            log_error(f"Erro webhook venda.fechada {venda_completa.id}: {e}")

    audit_action(
        db,
        "venda_finalizada",
        user_id=current_user.id,
        tenant_id=getattr(current_user, "tenant_id", None),
        recurso_tipo="venda",
        recurso_id=venda_id,
        detalhes=f"finalizada_de_pendente numero={venda.numero_venda}",
    )
    return _venda_response_orm(db, venda_id)


@router.post("/{venda_id}/cancelar", response_model=VendaResponse)
async def cancelar_venda_pendente(
    venda_id: int,
    body: VendaCancelarRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
    _: None = Depends(forbid_cliente_access),
):
    """Cancela venda PENDENTE (pedido não concluído)."""
    venda = (
        db.query(Venda)
        .options(joinedload(Venda.itens).joinedload(VendaItem.produto_cliente))
        .filter(Venda.id == venda_id)
        .first()
    )
    if not venda:
        raise HTTPException(status_code=404, detail="Venda não encontrada")
    if scope.must_filter_by_cliente() and not _venda_visivel_no_escopo(db, venda, scope):
        raise HTTPException(status_code=404, detail="Venda não encontrada")

    if not _venda_badge_status_pendente(venda.status):
        raise HTTPException(status_code=400, detail="Somente vendas pendentes podem ser canceladas por esta rota.")

    obs_extra = (body.motivo or "").strip()
    if obs_extra:
        prefix = (venda.observacoes or "").strip()
        venda.observacoes = prefix + ("\n\n" if prefix else "") + "[Cancelado] " + obs_extra
    venda.status = StatusVenda.CANCELADA.value
    db.commit()
    audit_action(
        db,
        "venda_cancelada",
        user_id=current_user.id,
        tenant_id=getattr(current_user, "tenant_id", None),
        recurso_tipo="venda",
        recurso_id=venda_id,
        detalhes=f"pedido_pendente_cancelado numero={venda.numero_venda}",
    )
    return _venda_response_orm(db, venda_id)


@router.get("", response_model=dict)
async def listar_vendas(
    skip: int = Query(0, ge=0, description="Offset para paginação"),
    limit: int = Query(100, ge=1, le=1000, description="Máximo de registros"),
    data_inicio: Optional[str] = Query(None, description="Data início (YYYY-MM-DD)"),
    data_fim: Optional[str] = Query(None, description="Data fim (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Listar vendas com paginação. Retorna {vendas, total, skip, limit}."""
    try:
        base_sql = """
            SELECT
                v.id, v.numero_venda, v.data_venda, v.status,
                v.cliente_id, v.vendedor_id, v.subtotal, v.desconto,
                v.acrescimo, v.total, v.tipo_pagamento, v.valor_pago,
                v.troco, v.observacoes, v.created_at, v.updated_at,
                v.ordem_servico_id, v.orcamento_id, v.nota_fiscal_id,
                v.abertura_caixa_id,
                cx.id AS caixa_id,
                cx.identificador AS caixa_identificador,
                os.codigo AS ordem_servico_codigo,
                orc.numero_orcamento AS numero_orcamento,
                c.nome AS cliente_nome,
                u.nome AS vendedor_nome,
                (SELECT COUNT(*) FROM venda_itens vi WHERE vi.venda_id = v.id) AS total_itens,
                (SELECT vo.tipo_origem FROM venda_origens vo WHERE vo.venda_id = v.id AND vo.papel = 'imediata' LIMIT 1) AS origem_imediata_tipo,
                (SELECT vo.documento_ref FROM venda_origens vo WHERE vo.venda_id = v.id AND vo.papel = 'imediata' LIMIT 1) AS origem_imediata_ref,
                (SELECT vo.tipo_origem FROM venda_origens vo WHERE vo.venda_id = v.id AND vo.papel = 'raiz' LIMIT 1) AS origem_raiz_tipo,
                (SELECT vo.documento_ref FROM venda_origens vo WHERE vo.venda_id = v.id AND vo.papel = 'raiz' LIMIT 1) AS origem_raiz_ref
            FROM vendas v
            LEFT JOIN clientes c ON c.id = v.cliente_id
            LEFT JOIN usuarios u ON u.id = v.vendedor_id
            LEFT JOIN ordem_servico os ON os.id = v.ordem_servico_id
            LEFT JOIN orcamentos orc ON orc.id = v.orcamento_id
            LEFT JOIN aberturas_caixa ab ON ab.id = v.abertura_caixa_id
            LEFT JOIN caixas cx ON cx.id = ab.caixa_id
            LEFT JOIN empresa e_caixa ON e_caixa.id = cx.empresa_id
        """
        count_sql = """
            SELECT COUNT(*) FROM vendas v
            LEFT JOIN aberturas_caixa ab ON ab.id = v.abertura_caixa_id
            LEFT JOIN caixas cx ON cx.id = ab.caixa_id
            LEFT JOIN empresa e_caixa ON e_caixa.id = cx.empresa_id
        """
        where_parts = []
        params: dict = {}

        if scope.must_filter_by_cliente():
            if not scope.allowed_ids:
                return {"vendas": [], "total": 0, "skip": skip, "limit": limit}
            scope_sql, scope_params = _venda_scope_sql_condition(scope)
            if scope_sql:
                where_parts.append(scope_sql)
                params.update(scope_params)

        if data_inicio:
            where_parts.append("v.data_venda >= :data_inicio")
            params["data_inicio"] = data_inicio
        if data_fim:
            where_parts.append("v.data_venda <= :data_fim")
            params["data_fim"] = data_fim

        where_clause = (" WHERE " + " AND ".join(where_parts)) if where_parts else ""
        total = db.execute(text(count_sql + where_clause), params).scalar() or 0

        full_sql = base_sql + where_clause + " ORDER BY v.data_venda DESC, v.id DESC LIMIT :lim OFFSET :off"
        params["lim"] = limit
        params["off"] = skip
        resultados = db.execute(text(full_sql), params).mappings().all()

        vendas_dict = []
        for row in resultados:
            vendas_dict.append({
                "id": row["id"],
                "numero_venda": row["numero_venda"],
                "data_venda": row["data_venda"].isoformat() if row["data_venda"] else None,
                "status": normalizar_status_venda(row["status"]),
                "cliente_id": row["cliente_id"],
                "vendedor_id": row["vendedor_id"],
                "subtotal": float(row["subtotal"]) if row["subtotal"] is not None else 0.0,
                "desconto": float(row["desconto"]) if row["desconto"] is not None else 0.0,
                "acrescimo": float(row["acrescimo"]) if row["acrescimo"] is not None else 0.0,
                "total": float(row["total"]) if row["total"] is not None else 0.0,
                "tipo_pagamento": row["tipo_pagamento"],
                "valor_pago": float(row["valor_pago"]) if row["valor_pago"] is not None else 0.0,
                "troco": float(row["troco"]) if row["troco"] is not None else 0.0,
                "observacoes": row["observacoes"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
                "total_itens": int(row["total_itens"]) if row["total_itens"] is not None else 0,
                "ordem_servico_id": row.get("ordem_servico_id"),
                "ordem_servico_codigo": row.get("ordem_servico_codigo"),
                "orcamento_id": row.get("orcamento_id"),
                "numero_orcamento": row.get("numero_orcamento"),
                "origem_imediata_tipo": row.get("origem_imediata_tipo"),
                "origem_imediata_ref": row.get("origem_imediata_ref"),
                "origem_raiz_tipo": row.get("origem_raiz_tipo"),
                "origem_raiz_ref": row.get("origem_raiz_ref"),
                "nota_fiscal_id": row.get("nota_fiscal_id"),
                "abertura_caixa_id": row.get("abertura_caixa_id"),
                "caixa_id": row.get("caixa_id"),
                "caixa_identificador": row.get("caixa_identificador"),
                "cliente": {
                    "id": row["cliente_id"],
                    "nome": row["cliente_nome"] or "Cliente não informado"
                } if row["cliente_id"] else {"id": None, "nome": "Cliente não informado"},
                "vendedor": {
                    "id": row["vendedor_id"],
                    "nome": row["vendedor_nome"] or "Vendedor não informado"
                } if row["vendedor_id"] else {"id": None, "nome": "Vendedor não informado"},
            })

        return {"vendas": vendas_dict, "total": total, "skip": skip, "limit": limit}

    except Exception as e:
        log_error(f"❌ Erro ao listar vendas: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro interno do servidor.")

@router.get("/{venda_id}", response_model=dict)
async def obter_venda(
    venda_id: int,
    db: Session = Depends(get_db),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Obter detalhes de uma venda específica"""
    try:
        stmt_venda = text("""
            SELECT
                v.id,
                v.numero_venda,
                v.data_venda,
                v.status,
                v.cliente_id,
                v.vendedor_id,
                v.subtotal,
                v.desconto,
                v.acrescimo,
                v.total,
                v.tipo_pagamento,
                v.valor_pago,
                v.troco,
                v.observacoes,
                v.created_at,
                v.updated_at,
                v.ordem_servico_id,
                v.orcamento_id,
                v.abertura_caixa_id,
                cx.id AS caixa_id,
                cx.identificador AS caixa_identificador,
                os.codigo AS ordem_servico_codigo,
                orc.numero_orcamento AS numero_orcamento,
                c.nome AS cliente_nome,
                u.nome AS vendedor_nome,
                e_caixa.cliente_id AS empresa_cliente_id,
                (SELECT vo.tipo_origem FROM venda_origens vo WHERE vo.venda_id = v.id AND vo.papel = 'imediata' LIMIT 1) AS origem_imediata_tipo,
                (SELECT vo.documento_ref FROM venda_origens vo WHERE vo.venda_id = v.id AND vo.papel = 'imediata' LIMIT 1) AS origem_imediata_ref,
                (SELECT vo.tipo_origem FROM venda_origens vo WHERE vo.venda_id = v.id AND vo.papel = 'raiz' LIMIT 1) AS origem_raiz_tipo,
                (SELECT vo.documento_ref FROM venda_origens vo WHERE vo.venda_id = v.id AND vo.papel = 'raiz' LIMIT 1) AS origem_raiz_ref
            FROM vendas v
            LEFT JOIN clientes c ON c.id = v.cliente_id
            LEFT JOIN usuarios u ON u.id = v.vendedor_id
            LEFT JOIN ordem_servico os ON os.id = v.ordem_servico_id
            LEFT JOIN orcamentos orc ON orc.id = v.orcamento_id
            LEFT JOIN aberturas_caixa ab ON ab.id = v.abertura_caixa_id
            LEFT JOIN caixas cx ON cx.id = ab.caixa_id
            LEFT JOIN empresa e_caixa ON e_caixa.id = cx.empresa_id
            WHERE v.id = :venda_id
        """)

        venda_row = db.execute(stmt_venda, {"venda_id": venda_id}).mappings().first()

        if not venda_row:
            raise HTTPException(status_code=404, detail="Venda não encontrada")
        if scope.must_filter_by_cliente():
            venda_escopo = (
                db.query(Venda)
                .options(joinedload(Venda.itens).joinedload(VendaItem.produto_cliente))
                .filter(Venda.id == venda_id)
                .first()
            )
            if not venda_escopo or not _venda_visivel_no_escopo(db, venda_escopo, scope):
                raise HTTPException(status_code=404, detail="Venda não encontrada")

        stmt_itens = text("""
            SELECT
                vi.id,
                vi.venda_id,
                vi.produto_cliente_id,
                vi.quantidade,
                vi.valor_unitario,
                vi.valor_total,
                vi.desconto_item,
                vi.observacoes,
                vi.created_at,
                vi.updated_at,
                pc.codigo AS produto_cliente_codigo,
                pc.nome AS produto_cliente_nome
            FROM venda_itens vi
            LEFT JOIN produtos_cliente pc ON pc.id = vi.produto_cliente_id
            WHERE vi.venda_id = :venda_id
            ORDER BY vi.id ASC
        """)

        itens_rows = db.execute(stmt_itens, {"venda_id": venda_id}).mappings().all()

        itens_dict = []
        for item in itens_rows:
            pc_id = item.get("produto_cliente_id")
            obs = (item.get("observacoes") or "").strip()
            if pc_id:
                codigo = item.get("produto_cliente_codigo") or (f"ID {pc_id}")
                nome = item.get("produto_cliente_nome") or "Produto não encontrado"
            else:
                primeira_linha = obs.split("\n")[0].strip() if obs else ""
                nome = primeira_linha or "Peça/serviço (OS)"
                codigo = "—"
            itens_dict.append({
                "id": item["id"],
                "produto_cliente_id": item.get("produto_cliente_id"),
                "quantidade": float(item["quantidade"]) if item["quantidade"] is not None else 0.0,
                "valor_unitario": float(item["valor_unitario"]) if item["valor_unitario"] is not None else 0.0,
                "valor_total": float(item["valor_total"]) if item["valor_total"] is not None else 0.0,
                "desconto_item": float(item["desconto_item"]) if item["desconto_item"] is not None else 0.0,
                "observacoes": item["observacoes"],
                "produto_codigo": codigo,
                "produto_nome": nome,
                "created_at": item["created_at"].isoformat() if item["created_at"] else None,
                "updated_at": item["updated_at"].isoformat() if item["updated_at"] else None,
            })

        return {
            "id": venda_row["id"],
            "numero_venda": venda_row["numero_venda"],
            "data_venda": venda_row["data_venda"].isoformat() if venda_row["data_venda"] else None,
            "status": normalizar_status_venda(venda_row["status"]),
            "ordem_servico_id": venda_row.get("ordem_servico_id"),
            "ordem_servico_codigo": venda_row.get("ordem_servico_codigo"),
            "orcamento_id": venda_row.get("orcamento_id"),
            "numero_orcamento": venda_row.get("numero_orcamento"),
            "origem_imediata_tipo": venda_row.get("origem_imediata_tipo"),
            "origem_imediata_ref": venda_row.get("origem_imediata_ref"),
            "origem_raiz_tipo": venda_row.get("origem_raiz_tipo"),
            "origem_raiz_ref": venda_row.get("origem_raiz_ref"),
            "origem_cadeia": _origem_cadeia_venda(db, venda_id, dict(venda_row)),
            "abertura_caixa_id": venda_row.get("abertura_caixa_id"),
            "caixa_id": venda_row.get("caixa_id"),
            "caixa_identificador": venda_row.get("caixa_identificador"),
            "cliente": {
                "id": venda_row["cliente_id"],
                "nome": venda_row["cliente_nome"] or "Cliente não informado"
            },
            "vendedor": {
                "id": venda_row["vendedor_id"],
                "nome": venda_row["vendedor_nome"] or "Vendedor não informado"
            },
            "subtotal": float(venda_row["subtotal"]) if venda_row["subtotal"] is not None else 0.0,
            "desconto": float(venda_row["desconto"]) if venda_row["desconto"] is not None else 0.0,
            "acrescimo": float(venda_row["acrescimo"]) if venda_row["acrescimo"] is not None else 0.0,
            "total": float(venda_row["total"]) if venda_row["total"] is not None else 0.0,
            "tipo_pagamento": venda_row["tipo_pagamento"],
            "valor_pago": float(venda_row["valor_pago"]) if venda_row["valor_pago"] is not None else 0.0,
            "troco": float(venda_row["troco"]) if venda_row["troco"] is not None else 0.0,
            "observacoes": venda_row["observacoes"],
            "itens": itens_dict,
            "total_itens": len(itens_dict),
            "created_at": venda_row["created_at"].isoformat() if venda_row["created_at"] else None,
            "updated_at": venda_row["updated_at"].isoformat() if venda_row["updated_at"] else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log_error(f"❌ Erro ao obter venda {venda_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {str(e)}")


@router.get("/{venda_id}/cupom", response_model=CupomConteudoResponse)
async def obter_cupom_venda(
    venda_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Cupom não fiscal do caixa (PDV). Padrão visual alinhado ao cupom de pedidos."""
    return montar_cupom_venda_caixa(db, venda_id, current_user, scope)


@router.post("/{venda_id}/emitir-nota", response_model=dict, status_code=status.HTTP_200_OK)
async def emitir_nota_fiscal_venda(
    venda_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
    _: None = Depends(forbid_cliente_access),
):
    """
    Obtém ou cria a nota fiscal da venda (rascunho) e envia à SEFAZ. Apenas vendas finalizadas.
    Regra absoluta: SA → AD → CA (tenant, quem paga) → CF (cliente final, quem compra do CA).
    Quem emite a nota para o CF é o CA, via sua Empresa FISCAL (certificado). Nunca usar
    Empresa FISCAL de outro CA (isolamento multi-tenant). Subcliente não pode (forbid_cliente_access).
    """
    venda = db.query(Venda).options(
        joinedload(Venda.itens),
        joinedload(Venda.abertura_caixa).joinedload(AberturaCaixa.caixa),
    ).filter(Venda.id == venda_id).first()
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
    empresa_para_nota = get_empresa_fiscal_empresa(db, current_user.id, current_user.role.nome if current_user.role else None)
    if not empresa_para_nota:
        raise HTTPException(
            status_code=400,
            detail="Empresa fiscal não configurada. O cadastro do Cliente Administrador exige Empresa FISCAL (CNPJ). Acesse Fiscal > Empresa e cadastre.",
        )
    if venda.status not in (StatusVenda.FINALIZADA.value, StatusVenda.FINALIZADA_LEGADO.value, "finalizada", "FINALIZADA"):
        raise HTTPException(status_code=400, detail="Somente vendas finalizadas podem emitir nota fiscal")
    nota_id = getattr(venda, "nota_fiscal_id", None)
    if not nota_id:
        nota = db.query(NotaFiscal).filter(NotaFiscal.venda_id == venda_id).first()
        if nota:
            nota_id = nota.id
            venda.nota_fiscal_id = nota_id
            db.commit()
        else:
            try:
                _criar_rascunho_nfe_ao_finalizar_venda(db, venda, current_user.id, empresa_fiscal_usuario=empresa_para_nota)
                db.commit()
                db.refresh(venda)
                nota_id = getattr(venda, "nota_fiscal_id", None)
            except Exception as e:
                log_error(f"Erro ao criar rascunho NF-e para venda {venda_id}: {e}")
                db.rollback()
                raise HTTPException(status_code=500, detail=f"Erro ao criar nota fiscal: {e}")
    if not nota_id:
        raise HTTPException(status_code=500, detail="Nota fiscal não foi criada para esta venda")
    # Garantir que a nota usa a Empresa FISCAL do CA dono da venda (nunca de outro CA/tenant)
    nota = db.query(NotaFiscal).options(joinedload(NotaFiscal.empresa)).filter(NotaFiscal.id == nota_id).first()
    if nota and empresa_para_nota and nota.empresa_id != empresa_para_nota.id:
        nota.empresa_id = empresa_para_nota.id
        db.commit()
        db.refresh(nota)

    def _run_emissao_nfe_sync(nid: int, uid: int):
        """Executa envio à SEFAZ em thread própria com sessão dedicada."""
        session = SessionLocal()
        try:
            svc = FiscalEmissaoService(session)
            ok, err, res = svc.enviar_nfe(nid, usuario_id=uid)
            if ok:
                session.commit()
                n = session.query(NotaFiscal).filter(NotaFiscal.id == nid).first()
                st = getattr(n, "status", None)
                status_val = (st.value if hasattr(st, "value") else str(st)) if st else None
            else:
                status_val = None
            return (ok, err, res, status_val)
        finally:
            session.close()

    try:
        sucesso, msg_erro, resultado, status_nota = await asyncio.to_thread(
            _run_emissao_nfe_sync, nota_id, current_user.id
        )
    except Exception as e:
        log_error(f"Erro ao emitir NF-e (venda {venda_id}): {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao emitir nota fiscal: {str(e)}",
        )
    if not sucesso:
        raise HTTPException(status_code=400, detail=msg_erro or "Falha no envio à SEFAZ")
    msg_provedor = getattr(resultado, "mensagem", None) if resultado else None
    mensagem = (msg_provedor and str(msg_provedor).strip()) or "Nota fiscal emitida com sucesso"
    return {
        "sucesso": True,
        "mensagem": mensagem,
        "nota_id": nota_id,
        "status": status_nota,
    }


@router.post("/{venda_id}/estornar", response_model=dict, status_code=status.HTTP_200_OK)
async def estornar_venda(
    venda_id: int,
    motivo_data: VendaEstornoRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
    _: None = Depends(forbid_cliente_access),
):
    """Estornar uma venda finalizada. Subcliente não pode estornar (forbid_cliente_access)."""
    try:
        
        # Buscar venda
        venda = db.query(Venda).filter(Venda.id == venda_id).first()
        if not venda:
            raise HTTPException(status_code=404, detail="Venda não encontrada")
        if scope.must_filter_by_cliente() and (venda.cliente_id is None or venda.cliente_id not in scope.allowed_ids):
            raise HTTPException(status_code=404, detail="Venda não encontrada")
        
        # Verificar se venda está finalizada (pode ser FINALIZADA ou FINALIZADA_LEGADO dependendo do banco)
        status_finalizado = venda.status in [StatusVenda.FINALIZADA, StatusVenda.FINALIZADA_LEGADO]
        if not status_finalizado:
            raise HTTPException(
                status_code=400, 
                detail=f"Somente vendas finalizadas podem ser estornadas. Status atual: {venda.status.value}"
            )
        
        # Obter motivo do estorno
        motivo = motivo_data.motivo
        
        # Buscar itens da venda
        itens_venda = db.query(VendaItem).filter(VendaItem.venda_id == venda_id).all()
        
        if not itens_venda:
            log_error(f"❌ Nenhum item encontrado na venda {venda_id}")
            raise HTTPException(status_code=400, detail="Venda não possui itens para estornar")
        
        # Reverter itens ao estoque (ProdutoCliente)
        from decimal import Decimal
        for item in itens_venda:
            quantidade_adicionar = Decimal(str(item.quantidade))
            if getattr(item, "produto_cliente_id", None) is None:
                raise HTTPException(status_code=400, detail="Item da venda sem produto_cliente_id; não é possível estornar")
            produto_pc = db.query(ProdutoCliente).filter(ProdutoCliente.id == item.produto_cliente_id).first()
            if produto_pc:
                produto_pc.quantidade_atual += quantidade_adicionar
            else:
                raise HTTPException(status_code=404, detail=f"Produto estabelecimento ID {item.produto_cliente_id} não encontrado")
        
        # Atualizar status da venda para CANCELADA
        venda.status = StatusVenda.CANCELADA
        
        # Adicionar motivo do estorno nas observações
        observacoes_estorno = f"\n\n--- ESTORNO ---\nData: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\nUsuário: {current_user.nome}\nMotivo: {motivo}\n"
        
        if venda.observacoes:
            venda.observacoes += observacoes_estorno
        else:
            venda.observacoes = observacoes_estorno
        
        # Salvar alterações
        db.commit()
        db.refresh(venda)
        audit_action(
            db,
            "venda_cancelada",
            user_id=current_user.id,
            tenant_id=getattr(current_user, "tenant_id", None),
            recurso_tipo="venda",
            recurso_id=venda_id,
            detalhes=f"motivo={motivo}",
        )
        return {
            "mensagem": "Venda estornada com sucesso",
            "venda_id": venda.id,
            "numero_venda": venda.numero_venda,
            "status": normalizar_status_venda(venda.status),
            "itens_revertidos": len(itens_venda)
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        log_error(f"❌ Erro ao estornar venda {venda_id}: {e}")
        log_error(f"❌ Tipo do erro: {type(e).__name__}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )
