from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.audit import audit_action
from app.core.middleware import AuthMiddleware, forbid_cliente_access, get_cliente_scope_dep
from app.core.scope import ClienteScope, resolve_tenant_id_from_cliente_id
from app.database.connection import get_db
from app.models import (
    Empresa,
    NotaServico,
    NotaServicoItem,
    OrdemServico,
    OrdemServicoTipo,
    Permissao,
    RolePermissao,
    Usuario,
)
from app.models.nota_servico import OrigemDocumentoFiscalEnum, StatusNotaServicoEnum
from app.schemas.ordem_servico import (
    OrdemServicoCreate,
    OrdemServicoItemResponse,
    OrdemServicoResponse,
    OrdemServicoResumoResponse,
    OrdemServicoStatusEnum,
    OrdemServicoTipoCreate,
    OrdemServicoTipoResponse,
    OrdemServicoTipoUpdate,
    OrdemServicoUpdate,
)
from app.schemas.venda import VendaResponse
from app.services.ordem_servico_service import OrdemServicoService
from app.services.ordem_servico_venda_service import criar_venda_a_partir_da_os

# Sem forbid_cliente_access no router: Subcliente pode GET (lista, detalhe) com escopo.
# Rotas de escrita usam Depends(forbid_cliente_access) individualmente.
router = APIRouter(
    prefix="/ordens-servico",
    tags=["Ordens de Serviço"],
)

PERMISSAO_GERENCIAR_TIPOS = "negocios.ordem-servico-tipos:gerenciar"


def _tenant_efetivo_para_tipos(db: Session, current_user: Usuario, scope: ClienteScope) -> Optional[int]:
    """Retorna tenant_id para listar/criar tipos: current_user.tenant_id ou do primeiro cliente do escopo."""
    tid = getattr(current_user, "tenant_id", None)
    if tid is not None:
        return tid
    if scope.allowed_ids:
        return resolve_tenant_id_from_cliente_id(db, scope.allowed_ids[0])
    return None


def _pode_gerenciar_tipos(db: Session, current_user: Usuario) -> bool:
    """Apenas Superadministrador e Administrador com permissão negocios.ordem-servico-tipos:gerenciar."""
    if not current_user.role:
        return False
    if current_user.role.nome in ("Superadministrador", "Administrador"):
        if current_user.role.nome == "Superadministrador":
            return True
        r = db.query(Permissao).join(RolePermissao, RolePermissao.permissao_id == Permissao.id).filter(
            RolePermissao.role_id == current_user.role_id,
            Permissao.nome == PERMISSAO_GERENCIAR_TIPOS,
            Permissao.ativo == True,
        ).first()
        return r is not None
    return False


def _mapear_itens(ordem: OrdemServico) -> List[OrdemServicoItemResponse]:
    respostas: List[OrdemServicoItemResponse] = []
    for item in ordem.itens:
        respostas.append(
            OrdemServicoItemResponse(
                id=item.id,
                ordem_servico_id=item.ordem_servico_id,
                produto_cliente_id=getattr(item, "produto_cliente_id", None),
                codigo=item.codigo,
                nome=item.nome,
                unidade=item.unidade,
                quantidade=item.quantidade,
                valor_unitario=item.valor_unitario,
                desconto=item.desconto,
                valor_total=item.valor_total,
                observacao=item.observacao,
                lacre_lote_id=getattr(item, 'lacre_lote_id', None),
                lacre_serial=getattr(item, 'lacre_serial', None),
                historico_selo_id=getattr(item, 'historico_selo_id', None),
            )
        )
    return respostas


def _venda_vinculada(ordem: OrdemServico):
    """Retorna a primeira venda vinculada à OS (no máximo uma por constraint 1:1) ou None."""
    vendas = getattr(ordem, "vendas", None) or []
    return vendas[0] if vendas else None


def _mapear_ordem(ordem: OrdemServico) -> OrdemServicoResponse:
    venda = _venda_vinculada(ordem)
    tipo_rel = getattr(ordem, "tipo_rel", None)
    return OrdemServicoResponse(
        id=ordem.id,
        codigo=ordem.codigo,
        cliente_id=ordem.cliente_id,
        cliente_nome=ordem.cliente.nome if ordem.cliente else None,
        status=OrdemServicoStatusEnum(ordem.status),
        tipo_id=ordem.tipo_id,
        tipo_nome=tipo_rel.nome if tipo_rel else None,
        prioridade=ordem.prioridade,
        data_abertura=ordem.data_abertura,
        data_prevista=ordem.data_prevista,
        data_conclusao=ordem.data_conclusao,
        responsavel_id=ordem.responsavel_id,
        responsavel_nome=ordem.responsavel.nome if ordem.responsavel else None,
        lacre_utilizado_id=getattr(ordem, "lacre_utilizado_id", None),
        observacoes=ordem.observacoes,
        itens=_mapear_itens(ordem),
        venda_id=venda.id if venda else None,
        venda_numero=venda.numero_venda if venda else None,
    )


@router.get("/tipos", response_model=List[OrdemServicoTipoResponse])
def listar_tipos_ordem_servico(
    tenant_id: Optional[int] = Query(None, description="Filtrar por tenant (Admin/Super Admin); se omitido, usa tenant efetivo"),
    ativo: Optional[bool] = Query(True, description="Apenas tipos ativos (True); use incluir_inativos=True para listar todos"),
    incluir_inativos: bool = Query(False, description="Se True, retorna todos os tipos (ativos e inativos) para gestão"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(AuthMiddleware.get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
) -> List[OrdemServicoTipoResponse]:
    """Lista tipos de ordem de serviço do tenant. Qualquer usuário com acesso à OS pode listar (para dropdown)."""
    tid = tenant_id if tenant_id is not None else _tenant_efetivo_para_tipos(db, current_user, scope)
    if tid is None:
        return []
    OrdemServicoService.garantir_tipo_servico_do_catalogo_estoque(db, tid)
    q = db.query(OrdemServicoTipo).filter(OrdemServicoTipo.tenant_id == tid)
    if not incluir_inativos and ativo is not None:
        q = q.filter(OrdemServicoTipo.ativo == ativo)
    tipos = q.order_by(OrdemServicoTipo.nome).all()
    return [OrdemServicoTipoResponse.model_validate(t) for t in tipos]


@router.post("/tipos", response_model=OrdemServicoTipoResponse, status_code=status.HTTP_201_CREATED)
def criar_tipo_ordem_servico(
    body: OrdemServicoTipoCreate,
    tenant_id: Optional[int] = Query(None, description="Tenant (CA) para o tipo; obrigatório para Admin ao gerenciar outro CA"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(AuthMiddleware.get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
) -> OrdemServicoTipoResponse:
    """Cria tipo de ordem de serviço. Exige permissão negocios.ordem-servico-tipos:gerenciar (Super Admin / Admin)."""
    if not _pode_gerenciar_tipos(db, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para gerenciar tipos de ordem de serviço")
    tid = tenant_id if tenant_id is not None else _tenant_efetivo_para_tipos(db, current_user, scope)
    if tid is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Não foi possível definir o tenant para o tipo")
    existente = db.query(OrdemServicoTipo).filter(
        OrdemServicoTipo.tenant_id == tid,
        OrdemServicoTipo.nome == body.nome.strip(),
    ).first()
    if existente:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Já existe um tipo com este nome para este tenant")
    tipo = OrdemServicoTipo(
        tenant_id=tid,
        nome=body.nome.strip(),
        codigo=body.codigo.strip() if body.codigo else None,
        ativo=body.ativo,
    )
    db.add(tipo)
    db.commit()
    db.refresh(tipo)
    return OrdemServicoTipoResponse.model_validate(tipo)


@router.patch("/tipos/{tipo_id}", response_model=OrdemServicoTipoResponse)
def atualizar_tipo_ordem_servico(
    tipo_id: int,
    body: OrdemServicoTipoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(AuthMiddleware.get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
) -> OrdemServicoTipoResponse:
    """Atualiza tipo de ordem de serviço. Exige permissão negocios.ordem-servico-tipos:gerenciar."""
    if not _pode_gerenciar_tipos(db, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para gerenciar tipos de ordem de serviço")
    tipo = db.query(OrdemServicoTipo).filter(OrdemServicoTipo.id == tipo_id).first()
    if not tipo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo não encontrado")
    payload = body.dict(exclude_unset=True)
    if "nome" in payload and payload["nome"] is not None:
        payload["nome"] = payload["nome"].strip()
        outro = db.query(OrdemServicoTipo).filter(
            OrdemServicoTipo.tenant_id == tipo.tenant_id,
            OrdemServicoTipo.nome == payload["nome"],
            OrdemServicoTipo.id != tipo_id,
        ).first()
        if outro:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Já existe um tipo com este nome para este tenant")
    for k, v in payload.items():
        setattr(tipo, k, v)
    db.commit()
    db.refresh(tipo)
    return OrdemServicoTipoResponse.model_validate(tipo)


@router.get("", response_model=dict)
def listar_ordens_servico(
    busca: Optional[str] = Query(None, description="Filtro por código ou observação"),
    cliente_id: Optional[int] = Query(None, description="Filtrar por cliente"),
    status: Optional[OrdemServicoStatusEnum] = Query(None, description="Filtrar por status"),
    responsavel_id: Optional[int] = Query(None, description="Filtrar por responsável"),
    tipo_id: Optional[int] = Query(None, description="Filtrar por tipo de ordem"),
    prioridade: Optional[str] = Query(None, description="Filtrar por prioridade"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    cliente_ids_arg = None
    cliente_id_arg = cliente_id
    if scope.must_filter_by_cliente():
        if not scope.allowed_ids:
            return {"ordens": [], "total": 0, "skip": skip, "limit": limit}
        if cliente_id is not None and cliente_id not in scope.allowed_ids:
            return {"ordens": [], "total": 0, "skip": skip, "limit": limit}
        cliente_ids_arg = [cliente_id] if (cliente_id is not None and cliente_id in scope.allowed_ids) else scope.allowed_ids
        cliente_id_arg = None
    ordens, total = OrdemServicoService.listar_ordens_paginado(
        db=db,
        busca=busca,
        cliente_id=cliente_id_arg,
        cliente_ids=cliente_ids_arg,
        status=status,
        responsavel_id=responsavel_id,
        tipo_id=tipo_id,
        prioridade=prioridade,
        skip=skip,
        limit=limit,
    )

    resumo = []
    for os_obj in ordens:
        venda = _venda_vinculada(os_obj)
        tipo_rel = getattr(os_obj, "tipo_rel", None)
        resumo.append(
            OrdemServicoResumoResponse(
                id=os_obj.id,
                codigo=os_obj.codigo,
                cliente_id=os_obj.cliente_id,
                cliente_nome=os_obj.cliente.nome if os_obj.cliente else None,
                status=OrdemServicoStatusEnum(os_obj.status),
                tipo_id=os_obj.tipo_id,
                tipo_nome=tipo_rel.nome if tipo_rel else None,
                prioridade=os_obj.prioridade,
                data_abertura=os_obj.data_abertura,
                data_prevista=os_obj.data_prevista,
                data_conclusao=os_obj.data_conclusao,
                venda_id=venda.id if venda else None,
                venda_numero=venda.numero_venda if venda else None,
            )
        )
    return {"ordens": resumo, "total": total, "skip": skip, "limit": limit}


@router.get("/{ordem_id}", response_model=OrdemServicoResponse)
def obter_ordem_servico(
    ordem_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(AuthMiddleware.get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
) -> OrdemServicoResponse:
    ordem = OrdemServicoService.obter_ordem(db, ordem_id)
    if scope.must_filter_by_cliente() and ordem.cliente_id not in scope.allowed_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ordem de serviço não encontrada")
    return _mapear_ordem(ordem)


@router.post("", response_model=OrdemServicoResponse, status_code=status.HTTP_201_CREATED)
def criar_ordem_servico(
    ordem_data: OrdemServicoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(AuthMiddleware.get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
    _: None = Depends(forbid_cliente_access),
) -> OrdemServicoResponse:
    if scope.must_filter_by_cliente() and ordem_data.cliente_id not in scope.allowed_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cliente fora do seu escopo de acesso")
    aplicado_por = current_user.email if current_user.email else f"usuario_{current_user.id}"
    ordem = OrdemServicoService.criar_ordem(db, ordem_data, current_user.id, aplicado_por=aplicado_por)
    return _mapear_ordem(ordem)


@router.patch("/{ordem_id}", response_model=OrdemServicoResponse)
def atualizar_ordem_servico(
    ordem_id: int,
    ordem_data: OrdemServicoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(AuthMiddleware.get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
    _: None = Depends(forbid_cliente_access),
) -> OrdemServicoResponse:
    ordem = OrdemServicoService.obter_ordem(db, ordem_id)
    if scope.must_filter_by_cliente() and ordem.cliente_id not in scope.allowed_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ordem de serviço não encontrada")
    ordem = OrdemServicoService.atualizar_ordem(db, ordem_id, ordem_data)
    return _mapear_ordem(ordem)


def _criar_rascunho_nfse_ao_concluir_os(db: Session, ordem: OrdemServico, usuario_id: int) -> None:
    """Cria rascunho de NFS-e vinculado à OS ao concluir. Ignora se não houver empresa fiscal para o cliente."""
    empresa = db.query(Empresa).filter(Empresa.cliente_id == ordem.cliente_id, Empresa.ativo == True).first()
    if not empresa:
        return
    from datetime import datetime as dt
    from decimal import Decimal
    valor_total = sum(
        (getattr(i, "valor_total") or Decimal("0")) for i in (ordem.itens or [])
    )
    discriminacao = ordem.observacoes or ""
    if ordem.itens:
        discriminacao += (" - " if discriminacao else "") + "; ".join(getattr(i, "nome", "") or "" for i in ordem.itens)
    if not discriminacao.strip():
        discriminacao = f"Serviço conforme OS {ordem.codigo}"
    numero_rascunho = f"RASCUNHO-OS-{ordem.id}"
    nota = NotaServico(
        numero=numero_rascunho,
        data_emissao=dt.utcnow(),
        cliente_id=ordem.cliente_id,
        empresa_id=empresa.id,
        ordem_servico_id=ordem.id,
        emitido_por_id=usuario_id,
        valor_total=valor_total,
        valor_servicos=valor_total,
        discriminacao_servicos=discriminacao[:5000],
        status=StatusNotaServicoEnum.RASCUNHO,
        origem_documento=OrigemDocumentoFiscalEnum.ORDEM_SERVICO,
    )
    db.add(nota)
    db.flush()
    item = NotaServicoItem(
        nota_servico_id=nota.id,
        item_numero=1,
        discriminacao=discriminacao[:5000],
        valor_total=valor_total,
        quantidade=Decimal("1"),
    )
    db.add(item)


@router.patch("/{ordem_id}/status", response_model=OrdemServicoResponse)
def atualizar_status_ordem_servico(
    ordem_id: int,
    status_novo: OrdemServicoStatusEnum,
    observacoes: Optional[str] = None,
    data_conclusao: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(AuthMiddleware.get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
    _: None = Depends(forbid_cliente_access),
) -> OrdemServicoResponse:
    ordem = OrdemServicoService.obter_ordem(db, ordem_id)
    if scope.must_filter_by_cliente() and ordem.cliente_id not in scope.allowed_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ordem de serviço não encontrada")
    ordem = OrdemServicoService.atualizar_status(db, ordem_id, status_novo, observacoes, data_conclusao)
    if status_novo == OrdemServicoStatusEnum.concluida:
        ordem_refresh = db.query(OrdemServico).filter(OrdemServico.id == ordem_id).first()
        if ordem_refresh and ordem_refresh.itens is not None:
            _criar_rascunho_nfse_ao_concluir_os(db, ordem_refresh, current_user.id)
        else:
            from sqlalchemy.orm import selectinload
            ordem_com_itens = db.query(OrdemServico).options(selectinload(OrdemServico.itens)).filter(OrdemServico.id == ordem_id).first()
            if ordem_com_itens:
                _criar_rascunho_nfse_ao_concluir_os(db, ordem_com_itens, current_user.id)
        db.commit()
    return _mapear_ordem(ordem)


@router.post(
    "/{ordem_id}/enviar-para-vendas",
    response_model=VendaResponse,
    status_code=status.HTTP_201_CREATED,
)
def enviar_ordem_para_vendas(
    ordem_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(AuthMiddleware.get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
    _: None = Depends(forbid_cliente_access),
) -> VendaResponse:
    """Cria uma Venda a partir da OS concluída (Finalizar venda / Enviar para vendas). Exige OS concluída e com itens."""
    ordem = OrdemServicoService.obter_ordem(db, ordem_id)
    if scope.must_filter_by_cliente() and ordem.cliente_id not in scope.allowed_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ordem de serviço não encontrada")
    venda = criar_venda_a_partir_da_os(db, ordem_id=ordem_id, usuario_id=current_user.id)
    audit_action(
        db,
        "venda_criada",
        user_id=current_user.id,
        tenant_id=getattr(current_user, "tenant_id", None),
        recurso_tipo="venda",
        recurso_id=venda.id,
        detalhes=f"numero={venda.numero_venda} ordem_servico_id={ordem_id}",
    )
    # garante que defaults do banco (timestamps) e relacionamentos estejam carregados
    db.refresh(venda)
    for it in (venda.itens or []):
        db.refresh(it)

    return VendaResponse.model_validate(venda, from_attributes=True)


@router.delete("/{ordem_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_ordem_servico(
    ordem_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(AuthMiddleware.get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
    _: None = Depends(forbid_cliente_access),
) -> None:
    ordem = OrdemServicoService.obter_ordem(db, ordem_id)
    if scope.must_filter_by_cliente() and ordem.cliente_id not in scope.allowed_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ordem de serviço não encontrada")
    OrdemServicoService.remover_ordem(db, ordem_id)
    return None

