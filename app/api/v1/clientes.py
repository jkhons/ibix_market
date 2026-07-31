# PDV Ibix - Clientes API
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...core.middleware import (
    forbid_cliente_access,
    get_cliente_scope_dep,
    get_current_user,
    get_user_permissions,
    require_permission,
)
from ...core.pii import apply_cliente_pii_mask
from ...core.pii_access import audit_pii_access, user_can_view_pii
from ...core.scope import ClienteScope, get_current_cliente_admin_id, get_empresa_fiscal_cliente_id
from ...database.connection import get_db
from ...models.area_cliente import AreaCliente
from ...models.cliente import Cliente
from ...models.cliente_administrador_cliente import ClienteAdministradorCliente
from ...models.empresa import Empresa
from ...models.usuario import Usuario
from ...schemas.cliente import ClienteCreate, ClienteListResponse, ClienteResponse, ClienteSearchParams, ClienteUpdate
from ...schemas.cliente_lojista import ClientePerfilLojistaResponse
from ...schemas.usuario import UsuarioClienteCreate
from ...schemas.usuario import UsuarioResponse as UsuarioResponseSchema
from ...services.cliente_categorias_vitrine_service import build_perfil_lojista
from ...services.cliente_service import ClienteService
from ...services.usuario_service import UsuarioService
from .configuracoes import get_configuracao, set_configuracao


def require_admin_or_ca_scope_para_criar_usuario(
    cliente_id: int,
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
) -> Usuario:
    """
    Permite Superadministrador/Administrador ou Cliente Administrador quando o cliente_id
    está no escopo do CA (criar usuário sub cliente / cliente final no modal de clientes).
    """
    if not current_user.role:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")
    if current_user.role.nome in ("Superadministrador", "Administrador"):
        return current_user
    if current_user.role.nome == "Cliente Administrador":
        if scope.is_superadmin or scope.see_all or (scope.allowed_ids and cliente_id in scope.allowed_ids):
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cliente fora do seu escopo",
        )
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")

router = APIRouter(prefix="/clientes", tags=["Clientes"])

_CLIENTE_PII_FIELDS = frozenset({"cpf", "cnpj", "telefone", "email"})


def _cliente_response_dict(cliente: Cliente) -> dict:
    return {
        "id": cliente.id,
        "nome": cliente.nome,
        "cnpj": cliente.cnpj,
        "cpf": cliente.cpf,
        "cep": cliente.cep,
        "endereco": cliente.endereco,
        "cidade": cliente.cidade,
        "uf": cliente.uf,
        "contato": cliente.contato,
        "telefone": cliente.telefone,
        "email": cliente.email,
        "created_at": cliente.created_at.isoformat() if cliente.created_at else None,
        "updated_at": cliente.updated_at.isoformat() if cliente.updated_at else None,
    }


def _cliente_to_response(
    cliente: Cliente,
    db: Session,
    current_user: Usuario,
    *,
    request: Request | None = None,
    audit_access: bool = False,
) -> ClienteResponse:
    reveal = user_can_view_pii(db, current_user)
    payload = apply_cliente_pii_mask(_cliente_response_dict(cliente), reveal=reveal)
    if audit_access and reveal and request is not None:
        from app.core.rate_limiter import get_client_ip

        audit_pii_access(
            db,
            acao="pii_acesso_cliente",
            actor=current_user,
            recurso_tipo="cliente",
            recurso_id=cliente.id,
            ip=get_client_ip(request),
            request_id=getattr(request.state, "request_id", None),
        )
    return ClienteResponse(**payload)


def require_superadministrador(
    current_user: Usuario = Depends(get_current_user),
) -> Usuario:
    if not current_user.role or current_user.role.nome != "Superadministrador":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito ao Superadministrador.",
        )
    return current_user


def require_clientes_listar_ou_para_venda(
    request: Request,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Usuario:
    """
    Para GET /clientes/: exige clientes:visualizar OU (para_venda=true e módulo negocios ou pdv).
    Assim, CA com permissão negocios/pdv pode listar clientes no modal Nova Venda sem precisar de clientes:visualizar.
    """
    if current_user.role and current_user.role.nome == "Superadministrador":
        return current_user
    perms = get_user_permissions(current_user.id, db)
    if "clientes:visualizar" in perms:
        return current_user
    para_venda = request.query_params.get("para_venda", "").lower() == "true"
    if para_venda and ("negocios" in perms or "pdv" in perms):
        return current_user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Sem permissão para listar clientes. Necessário clientes:visualizar ou acesso ao módulo Negócios/PDV (para busca em Nova Venda).",
    )


def _ids_estabelecimento_para_excluir(
    db: Session, scope: ClienteScope, current_user: Usuario
) -> set[int]:
    """
    Clientes que são estabelecimento/emissor (cadastro do CA) — não devem aparecer como cliente final.
    Usado em venda, orçamento, ordem de serviço e PDV.
    """
    ids_excluir: set[int] = set()
    if not scope.allowed_ids:
        return ids_excluir

    ids_com_empresa = {
        r[0]
        for r in db.query(Empresa.cliente_id)
        .filter(
            Empresa.cliente_id.isnot(None),
            Empresa.cliente_id.in_(scope.allowed_ids),
        )
        .distinct()
        .all()
    }
    ids_excluir.update(ids_com_empresa)

    role = (current_user.role.nome if current_user.role else "") or ""
    ca_user_id = get_current_cliente_admin_id(db, current_user.id, role)
    if ca_user_id:
        area_own = (
            db.query(AreaCliente.cliente_id)
            .filter(
                AreaCliente.usuario_id == ca_user_id,
                AreaCliente.ativo == True,
                AreaCliente.nome_area == "administrador",
            )
            .first()
        )
        if area_own and area_own[0]:
            ids_excluir.add(area_own[0])
        ef_cid = get_empresa_fiscal_cliente_id(db, ca_user_id, "Cliente Administrador", None)
        if ef_cid:
            ids_excluir.add(ef_cid)

    return ids_excluir


def _allowed_cliente_ids_for_list(
    db: Session, scope: ClienteScope, current_user: Usuario
) -> Optional[List[int]]:
    """
    Lista para seleção de cliente final (comprador/destinatário).
    CA, Técnico e Contador: excluem estabelecimento/emissor — apenas subclientes.
    Administrador/Superadministrador: mantém escopo completo (CAs gerenciados).
    """
    if not scope.must_filter_by_cliente():
        return None
    if not scope.allowed_ids:
        return []

    role = (current_user.role.nome if current_user.role else "") or ""
    if role in ("Cliente Administrador", "Técnico", "Contador"):
        ids_excluir = _ids_estabelecimento_para_excluir(db, scope, current_user)
        return [cid for cid in scope.allowed_ids if cid not in ids_excluir]

    return scope.allowed_ids


def _allowed_cliente_ids_para_empresa_fiscal(
    db: Session, scope: ClienteScope, current_user: Usuario
) -> Optional[List[int]]:
    """
    Para Cliente Administrador: retorna os cliente_id que são empresa fiscal do CA
    (emissor de notas), incluindo o "próprio" cliente para criar o primeiro cadastro.
    Usado no dropdown da página Empresa Fiscal. Cada CA vê apenas seus clientes (escopo isolado).
    """
    if not scope.must_filter_by_cliente() or not scope.allowed_ids:
        return None
    if not current_user.role or current_user.role.nome != "Cliente Administrador":
        return scope.allowed_ids
    # CA: ids que são empresa fiscal (já têm Empresa) ou o "próprio" (AreaCliente administrador)
    ids_empresa_fiscal = {
        r[0]
        for r in db.query(Empresa.cliente_id)
        .filter(
            Empresa.cliente_id.isnot(None),
            Empresa.cliente_id.in_(scope.allowed_ids),
        )
        .distinct()
        .all()
    }
    area_own = db.query(AreaCliente.cliente_id).filter(
        AreaCliente.usuario_id == current_user.id,
        AreaCliente.ativo == True,
        AreaCliente.nome_area == "administrador",
    ).first()
    ids_para_empresa_fiscal = set(ids_empresa_fiscal)
    if area_own:
        ids_para_empresa_fiscal.add(area_own[0])
    result = [cid for cid in scope.allowed_ids if cid in ids_para_empresa_fiscal]
    # Fallback: se CA não tem AreaCliente "administrador" (ex.: criado pelo Admin) nem Empresa ainda,
    # retorna todos os clientes do escopo para poder criar o primeiro cadastro no dropdown
    if not result and scope.allowed_ids:
        return list(scope.allowed_ids)
    return result


def _ids_subclientes_do_ca(db: Session, usuario_id: int) -> Optional[List[int]]:
    """Retorna os cliente_id dos subclientes deste CA (ClienteAdministradorCliente). None se não for CA."""
    rows = (
        db.query(ClienteAdministradorCliente.cliente_id)
        .filter(ClienteAdministradorCliente.usuario_id == usuario_id)
        .all()
    )
    return [r[0] for r in rows] if rows else []


@router.post("/", response_model=ClienteResponse, status_code=status.HTTP_201_CREATED)
async def criar_cliente(
    cliente_data: ClienteCreate,
    db: Session = Depends(get_db),
    _: None = Depends(forbid_cliente_access),
    current_user: Usuario = Depends(require_permission("clientes:criar"))
):
    """Cria um novo cliente. Cliente Administrador: vincula o novo cliente ao seu escopo (sub-cliente). CNPJ/CPF duplicado validado só no escopo do CA."""
    try:
        ids_escopo = None
        if current_user.role and current_user.role.nome == "Cliente Administrador":
            ids_escopo = _ids_subclientes_do_ca(db, current_user.id)
        cliente = ClienteService.criar_cliente(db, cliente_data, ids_escopo_subcliente=ids_escopo)
        # Cliente Administrador: vincular novo cliente como sub-cliente (nível abaixo)
        if current_user.role and current_user.role.nome == "Cliente Administrador":
            db.add(ClienteAdministradorCliente(usuario_id=current_user.id, cliente_id=cliente.id))
            db.commit()
            db.refresh(cliente)
        
        return _cliente_to_response(cliente, db, current_user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@router.get("/", response_model=ClienteListResponse)
async def listar_clientes(
    nome: Optional[str] = Query(None, description="Filtrar por nome"),
    cnpj: Optional[str] = Query(None, description="Filtrar por CNPJ"),
    cpf: Optional[str] = Query(None, description="Filtrar por CPF"),
    cidade: Optional[str] = Query(None, description="Filtrar por cidade"),
    uf: Optional[str] = Query(None, description="Filtrar por UF"),
    empresa_fiscal: Optional[str] = Query(None, description="true=apenas Empresas Fiscais, false=apenas Subclientes (Admin/SuperAdmin)"),
    para_venda: bool = Query(False, description="true=clientes finais para venda/orçamento/OS/PDV (exclui cadastro do CA/emissor)"),
    pagina: int = Query(1, ge=1, description="Número da página"),
    por_pagina: int = Query(10, ge=1, le=50000, description="Itens por página"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_clientes_listar_ou_para_venda),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Lista clientes com filtros e paginação (Saas.md Fase 3: escopo por role)."""
    try:
        # IDs permitidos para listagem:
        # - padrão e para_venda: subclientes (cliente final); exclui estabelecimento do CA
        # - empresa_fiscal=true: clientes emissores (inclui cadastro do CA)
        if str(empresa_fiscal).lower() == "true":
            ids_para_lista = _allowed_cliente_ids_para_empresa_fiscal(db, scope, current_user)
        else:
            ids_para_lista = _allowed_cliente_ids_for_list(db, scope, current_user)
        if scope.must_filter_by_cliente() and ids_para_lista is not None and not ids_para_lista:
            return ClienteListResponse(
                clientes=[],
                total=0,
                pagina=1,
                por_pagina=por_pagina,
                total_paginas=0,
            )
        params = ClienteSearchParams(
            nome=nome,
            cnpj=cnpj,
            cpf=cpf,
            cidade=cidade,
            uf=uf,
            empresa_fiscal=empresa_fiscal,
            pagina=pagina,
            por_pagina=por_pagina,
            cliente_ids=ids_para_lista if scope.must_filter_by_cliente() else None,
        )
        
        resultado = ClienteService.listar_clientes(db, params)
        
        clientes_response = [
            _cliente_to_response(cliente, db, current_user)
            for cliente in resultado["clientes"]
        ]
        
        return ClienteListResponse(
            clientes=clientes_response,
            total=resultado["total"],
            pagina=resultado["pagina"],
            por_pagina=resultado["por_pagina"],
            total_paginas=resultado["total_paginas"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@router.get("/todos", response_model=List[ClienteResponse])
async def listar_todos_clientes(
    para_empresa_fiscal: bool = Query(False, description="Quando true, retorna lista para módulos fiscais/pagamentos (inclui cliente emissor do CA)."),
    db: Session = Depends(get_db),
    _: None = Depends(forbid_cliente_access),
    current_user: Usuario = Depends(require_permission("clientes:visualizar")),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Lista clientes sem paginação (para filtros/selects). Exclui estabelecimento do CA — apenas clientes finais."""
    try:
        if para_empresa_fiscal:
            ids_para_lista = _allowed_cliente_ids_para_empresa_fiscal(db, scope, current_user)
        else:
            ids_para_lista = _allowed_cliente_ids_for_list(db, scope, current_user)
        q = db.query(Cliente).order_by(Cliente.nome)
        if scope.must_filter_by_cliente():
            if ids_para_lista is None or not ids_para_lista:
                return []
            q = q.filter(Cliente.id.in_(ids_para_lista))
        clientes = q.all()

        clientes_response = [
            _cliente_to_response(cliente, db, current_user) for cliente in clientes
        ]
        
        return clientes_response
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )


CHAVE_PDV_CLIENTE_PADRAO_CA = "pdv_cliente_padrao:ca:"
CHAVE_PDV_CLIENTE_PADRAO_USER = "pdv_cliente_padrao:user:"


def _get_pdv_cliente_padrao_valor(db: Session, chave: str) -> Optional[int]:
    config = get_configuracao(db, chave)
    if not config or not (config.valor or "").strip():
        return None
    try:
        return int(config.valor.strip())
    except ValueError:
        return None


class EstabelecimentoFiscalResponse(BaseModel):
    """Estabelecimento (empresa fiscal) do usuário — loja onde estão o estoque e os produtos."""
    cliente_id: Optional[int] = None


class PdvClientePadraoResponse(BaseModel):
    """Cliente padrão do PDV (escopo por CA ou por usuário)."""
    cliente_id: Optional[int] = None


class PdvClientePadraoUpdate(BaseModel):
    """Body para definir cliente padrão do PDV."""
    cliente_id: Optional[int] = None


@router.get("/estabelecimento-fiscal/", response_model=EstabelecimentoFiscalResponse)
async def get_estabelecimento_fiscal(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """
    Retorna o cliente_id do estabelecimento (empresa fiscal) do usuário.
    CA = sua loja; Admin/Super = primeiro do escopo com Empresa.
    Usado em Nova Venda para listar produtos do ESTOQUE (nunca do cliente comprador).
    """
    cid = get_empresa_fiscal_cliente_id(db, current_user.id, current_user.role.nome if current_user.role else None, None)
    return EstabelecimentoFiscalResponse(cliente_id=cid)


@router.get("/pdv-cliente-padrao/", response_model=PdvClientePadraoResponse)
async def get_pdv_cliente_padrao(
    db: Session = Depends(get_db),
    _: None = Depends(forbid_cliente_access),
    current_user: Usuario = Depends(require_permission("clientes:visualizar")),
):
    """
    Retorna o cliente definido como padrão no PDV.
    CA (e usuários sob CA): valor do contexto do CA. Admin/Superadmin: valor por usuário.
    """
    ca_user_id = get_current_cliente_admin_id(db, current_user.id, current_user.role.nome if current_user.role else None)
    if ca_user_id:
        cid = _get_pdv_cliente_padrao_valor(db, f"{CHAVE_PDV_CLIENTE_PADRAO_CA}{ca_user_id}")
        if cid is not None:
            return PdvClientePadraoResponse(cliente_id=cid)
    cid = _get_pdv_cliente_padrao_valor(db, f"{CHAVE_PDV_CLIENTE_PADRAO_USER}{current_user.id}")
    return PdvClientePadraoResponse(cliente_id=cid)


@router.put("/pdv-cliente-padrao/", response_model=PdvClientePadraoResponse)
async def set_pdv_cliente_padrao(
    body: PdvClientePadraoUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(forbid_cliente_access),
    current_user: Usuario = Depends(require_permission("clientes:editar")),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """
    Define o cliente padrão do PDV. CA: escopo do CA; Admin/Superadmin: por usuário (cliente no escopo).
    """
    ca_user_id = get_current_cliente_admin_id(db, current_user.id, current_user.role.nome if current_user.role else None)
    ids_para_lista = _allowed_cliente_ids_for_list(db, scope, current_user)

    if body.cliente_id is not None:
        if scope.must_filter_by_cliente():
            if not ids_para_lista:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Nenhum cliente no escopo.")
            if body.cliente_id not in ids_para_lista:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado ou fora do seu escopo.")
        else:
            cliente_existe = db.query(Cliente).filter(Cliente.id == body.cliente_id).first()
            if not cliente_existe:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado.")

    if ca_user_id:
        chave = f"{CHAVE_PDV_CLIENTE_PADRAO_CA}{ca_user_id}"
        desc = "Cliente padrão exibido no PDV (escopo CA)"
    else:
        chave = f"{CHAVE_PDV_CLIENTE_PADRAO_USER}{current_user.id}"
        desc = "Cliente padrão exibido no PDV (por usuário)"

    valor = str(body.cliente_id) if body.cliente_id is not None else ""
    set_configuracao(db, chave, valor, desc)
    return PdvClientePadraoResponse(cliente_id=body.cliente_id)


@router.get("/{cliente_id}/perfil-lojista", response_model=ClientePerfilLojistaResponse)
async def obter_perfil_lojista(
    cliente_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_superadministrador),
):
    """
    Perfil completo do lojista (CA): empresa, responsável, bancário, categorias da vitrine, tenant e loja.
    Apenas Superadministrador; somente clientes com empresa fiscal (cadastro público).
    """
    data = build_perfil_lojista(db, cliente_id)
    return ClientePerfilLojistaResponse.model_validate(data)


@router.get("/{cliente_id}", response_model=ClienteResponse)
async def obter_cliente(
    cliente_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("clientes:visualizar")),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Obtém um cliente específico por ID (respeita escopo por role)."""
    try:
        if scope.must_filter_by_cliente() and (not scope.allowed_ids or cliente_id not in scope.allowed_ids):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")
        cliente = ClienteService.obter_cliente(db, cliente_id)
        
        return _cliente_to_response(
            cliente, db, current_user, request=request, audit_access=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@router.put("/{cliente_id}", response_model=ClienteResponse)
async def atualizar_cliente(
    cliente_id: int,
    cliente_data: ClienteUpdate,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(forbid_cliente_access),
    current_user: Usuario = Depends(require_permission("clientes:editar")),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Atualiza um cliente existente (respeita escopo por role). CNPJ/CPF duplicado validado só no escopo do CA."""
    try:
        if scope.must_filter_by_cliente() and (not scope.allowed_ids or cliente_id not in scope.allowed_ids):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")
        dump = cliente_data.model_dump(exclude_unset=True)
        pii_touched = _CLIENTE_PII_FIELDS.intersection(dump.keys())
        if pii_touched and not user_can_view_pii(db, current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissão necessária para alterar dados pessoais (PII): pii:visualizar",
            )
        ids_escopo = None
        if current_user.role and current_user.role.nome == "Cliente Administrador":
            ids_escopo = _ids_subclientes_do_ca(db, current_user.id)
        cliente = ClienteService.atualizar_cliente(db, cliente_id, cliente_data, ids_escopo_subcliente=ids_escopo)
        if pii_touched:
            from app.core.rate_limiter import get_client_ip

            audit_pii_access(
                db,
                acao="pii_alteracao_cliente",
                actor=current_user,
                recurso_tipo="cliente",
                recurso_id=cliente_id,
                ip=get_client_ip(request),
                request_id=getattr(request.state, "request_id", None),
                detalhes=f"campos={','.join(sorted(pii_touched))}",
            )
        
        return _cliente_to_response(cliente, db, current_user)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@router.delete("/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(forbid_cliente_access),
    current_user: Usuario = Depends(require_permission("clientes:excluir")),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Deleta um cliente (respeita escopo por role)."""
    try:
        if scope.must_filter_by_cliente() and (not scope.allowed_ids or cliente_id not in scope.allowed_ids):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")
        ClienteService.deletar_cliente(db, cliente_id)
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@router.get("/buscar/cnpj/{cnpj}", response_model=ClienteResponse)
async def buscar_cliente_por_cnpj(
    cnpj: str,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("clientes:visualizar")),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Busca cliente por CNPJ (respeita escopo por role)."""
    try:
        cliente = ClienteService.buscar_por_cnpj(db, cnpj)
        if not cliente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente não encontrado"
            )
        if scope.must_filter_by_cliente() and (not scope.allowed_ids or cliente.id not in scope.allowed_ids):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")
        
        return _cliente_to_response(cliente, db, current_user)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@router.get("/estatisticas/dashboard")
async def obter_estatisticas_clientes(
    db: Session = Depends(get_db),
    _: None = Depends(forbid_cliente_access),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtém estatísticas dos clientes para o dashboard"""
    try:
        return ClienteService.obter_estatisticas(db)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )


@router.post("/{cliente_id}/usuarios", response_model=UsuarioResponseSchema, status_code=status.HTTP_201_CREATED)
async def criar_usuario_cliente(
    cliente_id: int,
    usuario_data: UsuarioClienteCreate,
    db: Session = Depends(get_db),
    _: None = Depends(forbid_cliente_access),
    current_user: Usuario = Depends(require_admin_or_ca_scope_para_criar_usuario),
):
    """
    Cria usuário com role Subcliente vinculado ao cliente (AreaCliente).
    Usado pelo modal "Criar usuário" na tela de Clientes. Lugar e função distintos de /minha-equipe/tecnicos
    (que cria/vincula Técnico via ClienteAdministradorTecnico).
    """
    try:
        # Validar se cliente_id na URL corresponde ao do body
        if usuario_data.cliente_id != cliente_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="cliente_id na URL deve corresponder ao cliente_id no body"
            )
        
        # Verificar se cliente existe
        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        if not cliente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente não encontrado"
            )
        
        # Criar usuário vinculado ao cliente
        usuario = UsuarioService.criar_usuario_cliente(db, usuario_data)
        
        return UsuarioResponseSchema(
            id=usuario.id,
            nome=usuario.nome,
            email=usuario.email,
            cargo=usuario.cargo,
            ativo=usuario.ativo,
            role_id=usuario.role_id,
            created_at=usuario.created_at,
            updated_at=usuario.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        ) 