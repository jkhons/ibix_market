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
from ...core.scope import ClienteScope, get_current_cliente_admin_id, get_empresa_fiscal_cliente_id
from ...database.connection import get_db
from ...models.area_cliente import AreaCliente
from ...models.cliente import Cliente
from ...models.cliente_administrador_cliente import ClienteAdministradorCliente
from ...models.empresa import Empresa
from ...models.usuario import Usuario
from ...schemas.cliente import ClienteCreate, ClienteListResponse, ClienteResponse, ClienteSearchParams, ClienteUpdate
from ...schemas.usuario import UsuarioClienteCreate
from ...schemas.usuario import UsuarioResponse as UsuarioResponseSchema
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


def _allowed_cliente_ids_for_list(
    db: Session, scope: ClienteScope, current_user: Usuario
) -> Optional[List[int]]:
    """
    Para Cliente Administrador: exclui da listagem os clientes que são empresa fiscal (ou "ele mesmo").
    O Cliente Administrador deve ver apenas sub-clientes (níveis abaixo), não a empresa fiscal.
    - Administrador/Superadministrador: vê clientes (empresas fiscais).
    - Cliente Administrador: vê só sub-clientes (criados no módulo Clientes).
    Minha equipe = técnicos do cliente (outra função, não clientes).
    """
    if not scope.must_filter_by_cliente():
        return None
    if not scope.allowed_ids:
        return []
    if not current_user.role or current_user.role.nome != "Cliente Administrador":
        return scope.allowed_ids
    # Cliente Admin: excluir empresa fiscal e o "próprio" cliente
    ids_excluir = set()
    # 1) Clientes que têm Empresa vinculada (empresa fiscal)
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
    ids_excluir.update(ids_empresa_fiscal)
    # 2) Cliente "próprio" via AreaCliente (nome_area=administrador) - caso ainda não tenha Empresa
    area_own = db.query(AreaCliente.cliente_id).filter(
        AreaCliente.usuario_id == current_user.id,
        AreaCliente.ativo == True,
        AreaCliente.nome_area == "administrador",
        AreaCliente.cliente_id.in_(scope.allowed_ids),
    ).first()
    if area_own:
        ids_excluir.add(area_own[0])
    filtered = [cid for cid in scope.allowed_ids if cid not in ids_excluir]
    return filtered


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
        
        # Converter datetime para string
        return ClienteResponse(
            id=cliente.id,
            nome=cliente.nome,
            cnpj=cliente.cnpj,
            cpf=cliente.cpf,
            cep=cliente.cep,
            endereco=cliente.endereco,
            cidade=cliente.cidade,
            uf=cliente.uf,
            contato=cliente.contato,
            telefone=cliente.telefone,
            email=cliente.email,
            created_at=cliente.created_at.isoformat() if cliente.created_at else None,
            updated_at=cliente.updated_at.isoformat() if cliente.updated_at else None
        )
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
    para_venda: bool = Query(False, description="true=estabelecimentos para usar em Nova Venda (CA: subclientes + própria empresa)"),
    pagina: int = Query(1, ge=1, description="Número da página"),
    por_pagina: int = Query(10, ge=1, le=50000, description="Itens por página"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_clientes_listar_ou_para_venda),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Lista clientes com filtros e paginação (Saas.md Fase 3: escopo por role)."""
    try:
        # IDs permitidos para listagem:
        # - padrão: Cliente Administrador vê subclientes (exclui empresa fiscal/próprio)
        # - empresa_fiscal=true: Cliente Administrador vê clientes emissores (inclui próprio)
        # - para_venda=true: Nova Venda / PDV — CA vê TODOS do escopo (subclientes + próprio, ex. Consumidor Final)
        if para_venda and scope.must_filter_by_cliente() and scope.allowed_ids:
            ids_para_lista = list(scope.allowed_ids)
        elif str(empresa_fiscal).lower() == "true":
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
        
        # Converter clientes para response
        clientes_response = []
        for cliente in resultado["clientes"]:
            clientes_response.append(ClienteResponse(
                id=cliente.id,
                nome=cliente.nome,
                cnpj=cliente.cnpj,
                cpf=cliente.cpf,
                cep=cliente.cep,
                endereco=cliente.endereco,
                cidade=cliente.cidade,
                uf=cliente.uf,
                contato=cliente.contato,
                telefone=cliente.telefone,
                email=cliente.email,
                created_at=cliente.created_at.isoformat() if cliente.created_at else None,
                updated_at=cliente.updated_at.isoformat() if cliente.updated_at else None
            ))
        
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
    """Lista clientes sem paginação (para filtros/selects). Cliente Administrador: apenas sub-clientes (exclui empresa fiscal / próprio)."""
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

        # Converter clientes para response
        clientes_response = []
        for cliente in clientes:
            clientes_response.append(ClienteResponse(
                id=cliente.id,
                nome=cliente.nome,
                cnpj=cliente.cnpj,
                cpf=cliente.cpf,
                cep=cliente.cep,
                endereco=cliente.endereco,
                cidade=cliente.cidade,
                uf=cliente.uf,
                contato=cliente.contato,
                telefone=cliente.telefone,
                email=cliente.email,
                created_at=cliente.created_at.isoformat() if cliente.created_at else None,
                updated_at=cliente.updated_at.isoformat() if cliente.updated_at else None
            ))
        
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


@router.get("/{cliente_id}", response_model=ClienteResponse)
async def obter_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("clientes:visualizar")),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Obtém um cliente específico por ID (respeita escopo por role)."""
    try:
        if scope.must_filter_by_cliente() and (not scope.allowed_ids or cliente_id not in scope.allowed_ids):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")
        cliente = ClienteService.obter_cliente(db, cliente_id)
        
        return ClienteResponse(
            id=cliente.id,
            nome=cliente.nome,
            cnpj=cliente.cnpj,
            cpf=cliente.cpf,
            cep=cliente.cep,
            endereco=cliente.endereco,
            cidade=cliente.cidade,
            uf=cliente.uf,
            contato=cliente.contato,
            telefone=cliente.telefone,
            email=cliente.email,
            created_at=cliente.created_at.isoformat() if cliente.created_at else None,
            updated_at=cliente.updated_at.isoformat() if cliente.updated_at else None
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
    db: Session = Depends(get_db),
    _: None = Depends(forbid_cliente_access),
    current_user: Usuario = Depends(require_permission("clientes:editar")),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Atualiza um cliente existente (respeita escopo por role). CNPJ/CPF duplicado validado só no escopo do CA."""
    try:
        if scope.must_filter_by_cliente() and (not scope.allowed_ids or cliente_id not in scope.allowed_ids):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")
        ids_escopo = None
        if current_user.role and current_user.role.nome == "Cliente Administrador":
            ids_escopo = _ids_subclientes_do_ca(db, current_user.id)
        cliente = ClienteService.atualizar_cliente(db, cliente_id, cliente_data, ids_escopo_subcliente=ids_escopo)
        
        return ClienteResponse(
            id=cliente.id,
            nome=cliente.nome,
            cnpj=cliente.cnpj,
            cpf=cliente.cpf,
            cep=cliente.cep,
            endereco=cliente.endereco,
            cidade=cliente.cidade,
            uf=cliente.uf,
            contato=cliente.contato,
            telefone=cliente.telefone,
            email=cliente.email,
            created_at=cliente.created_at.isoformat() if cliente.created_at else None,
            updated_at=cliente.updated_at.isoformat() if cliente.updated_at else None
        )
        
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
        
        return ClienteResponse(
            id=cliente.id,
            nome=cliente.nome,
            cnpj=cliente.cnpj,
            cpf=cliente.cpf,
            cep=cliente.cep,
            endereco=cliente.endereco,
            cidade=cliente.cidade,
            uf=cliente.uf,
            contato=cliente.contato,
            telefone=cliente.telefone,
            email=cliente.email,
            created_at=cliente.created_at.isoformat() if cliente.created_at else None,
            updated_at=cliente.updated_at.isoformat() if cliente.updated_at else None
        )
        
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