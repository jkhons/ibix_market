# PDV Ibix - API Entregador (logística local)
"""Login, entregas disponíveis, aceitar, minhas entregas, atualizar status."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ...core.auth import AuthConfig, create_entregador_token, verify_user_credentials
from ...core.constants.entrega_status import DISPONIVEL
from ...database.connection import get_db
from ...models import Entregador, EntregadorVeiculo, EntregaMarketplace, LojaMarketplace
from ...schemas.entrega_marketplace import EntregaDisponivelOut, EntregaEventoOut, EntregaOut, EntregaStatusUpdateIn
from ...schemas.entregador import (
    EntregadorLoginIn,
    EntregadorLoginResponse,
    EntregadorResponse,
    EntregadorVeiculoCreate,
    EntregadorVeiculoResponse,
    EntregadorVeiculoUpdate,
)
from ...services.logistica.entrega_aceite_service import aceitar_entrega
from ...services.logistica.entrega_service import marcar_entregas_expiradas
from ...services.logistica.entrega_status_service import atualizar_status_entrega

router = APIRouter(prefix="/entregador", tags=["Entregador (logística)"])

COOKIE_ENTREGADOR = "entregador_token"


def _token_from_request_entregador(request: Request) -> Optional[str]:
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        return auth[7:].strip()
    return request.cookies.get(COOKIE_ENTREGADOR)


async def get_current_entregador(
    request: Request,
    db: Session = Depends(get_db),
) -> Entregador:
    """Dependency: retorna Entregador a partir do cookie entregador_token ou Bearer."""
    token = _token_from_request_entregador(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não autenticado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = AuthConfig.verify_token(token)
    except HTTPException:
        raise
    if payload.get("tipo") != "entregador":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido para entregador")
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    try:
        eid = int(sub)
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    entregador = db.query(Entregador).filter(Entregador.id == eid).first()
    if not entregador or not entregador.ativo or entregador.status == "bloqueado":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Entregador não encontrado ou inativo")
    return entregador


def _entrega_para_disponivel(e: EntregaMarketplace, loja_nome: Optional[str]) -> dict:
    bairro_retirada = None
    bairro_entrega = None
    if e.endereco_retirada_json and isinstance(e.endereco_retirada_json, dict):
        bairro_retirada = e.endereco_retirada_json.get("bairro") or e.endereco_retirada_json.get("cidade")
    if e.endereco_entrega_json and isinstance(e.endereco_entrega_json, dict):
        bairro_entrega = e.endereco_entrega_json.get("bairro") or e.endereco_entrega_json.get("cidade")
    return {
        "id": e.id,
        "pedido_id": e.pedido_id,
        "loja_nome": loja_nome,
        "bairro_retirada": bairro_retirada,
        "bairro_entrega": bairro_entrega,
        "valor_frete": e.valor_frete,
        "tipo_veiculo_aceito": e.tipo_veiculo_aceito,
        "observacoes": e.observacoes,
    }


@router.post("/login", response_model=EntregadorLoginResponse)
def entregador_login(body: EntregadorLoginIn, db: Session = Depends(get_db)):
    """Login do entregador. Retorna token e dados do entregador."""
    entregador = db.query(Entregador).filter(Entregador.email == body.email).first()
    if not entregador or not entregador.senha_hash:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email ou senha inválidos")
    if not entregador.ativo or entregador.status == "bloqueado":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Entregador inativo ou bloqueado")
    if not verify_user_credentials(body.email, body.senha, entregador.senha_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email ou senha inválidos")
    token = create_entregador_token(entregador.id, email=entregador.email)
    return EntregadorLoginResponse(
        access_token=token,
        token_type="bearer",
        entregador=EntregadorResponse(
            id=entregador.id,
            nome=entregador.nome,
            email=entregador.email,
            tipo_veiculo=entregador.tipo_veiculo,
        ),
    )


@router.get("/entregas-disponiveis", response_model=List[EntregaDisponivelOut])
def listar_entregas_disponiveis(
    db: Session = Depends(get_db),
    entregador: Entregador = Depends(get_current_entregador),
):
    """Lista entregas com status disponivel (para aceitar). Marca como expiradas as que passaram de aceita_ate_em."""
    marcar_entregas_expiradas(db)
    from datetime import datetime, timezone
    agora = datetime.now(timezone.utc)
    q = (
        db.query(EntregaMarketplace)
        .filter(
            EntregaMarketplace.status == DISPONIVEL,
            EntregaMarketplace.entregador_id.is_(None),
        )
    )
    if entregador.cidade:
        # Filtro opcional por cidade (endereco retirada/entrega)
        pass
    rows = q.order_by(EntregaMarketplace.publicada_em.desc()).limit(100).all()
    out = []
    for e in rows:
        if e.aceita_ate_em and e.aceita_ate_em < agora:
            continue
        loja = None
        if e.pedido:
            loja = db.query(LojaMarketplace).filter(LojaMarketplace.id == e.pedido.loja_id).first()
        loja_nome = loja.nome_loja if loja else None
        out.append(EntregaDisponivelOut(**_entrega_para_disponivel(e, loja_nome)))
    return out


@router.post("/entregas/{entrega_id}/aceitar", response_model=EntregaOut)
def aceitar_entrega_endpoint(
    entrega_id: int,
    db: Session = Depends(get_db),
    entregador: Entregador = Depends(get_current_entregador),
):
    """Aceita uma entrega (lock transacional). 409 se já aceita."""
    try:
        entrega = aceitar_entrega(db, entrega_id, entregador.id)
    except ValueError as e:
        if "já foi aceita" in str(e).lower() or "já aceita" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    eventos = [EntregaEventoOut.model_validate(ev) for ev in entrega.eventos]
    data = EntregaOut.model_validate(entrega).model_dump()
    data["eventos"] = eventos
    return EntregaOut(**data)


@router.get("/minhas-entregas", response_model=List[EntregaOut])
def minhas_entregas(
    em_andamento: Optional[bool] = None,
    db: Session = Depends(get_db),
    entregador: Entregador = Depends(get_current_entregador),
):
    """Lista entregas do entregador logado. em_andamento=True: aceita, em_retirada, retirada, em_rota; False: entregue, cancelada, falha."""
    q = db.query(EntregaMarketplace).filter(EntregaMarketplace.entregador_id == entregador.id)
    if em_andamento is not None:
        if em_andamento:
            q = q.filter(EntregaMarketplace.status.in_(("aceita", "em_retirada", "retirada", "em_rota")))
        else:
            q = q.filter(EntregaMarketplace.status.in_(("entregue", "cancelada", "falha_entrega")))
    rows = q.order_by(EntregaMarketplace.aceita_em.desc()).limit(100).all()
    return [
        EntregaOut(**EntregaOut.model_validate(e).model_dump() | {"eventos": [EntregaEventoOut.model_validate(ev) for ev in e.eventos]})
        for e in rows
    ]


@router.get("/entregas/{entrega_id}", response_model=EntregaOut)
def detalhe_entrega(
  entrega_id: int,
  db: Session = Depends(get_db),
  entregador: Entregador = Depends(get_current_entregador),
):
    """Detalhe de uma entrega (só se for do entregador)."""
    entrega = db.query(EntregaMarketplace).filter(
        EntregaMarketplace.id == entrega_id,
        EntregaMarketplace.entregador_id == entregador.id,
    ).first()
    if not entrega:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entrega não encontrada")
    data = EntregaOut.model_validate(entrega).model_dump()
    data["eventos"] = [EntregaEventoOut.model_validate(ev) for ev in entrega.eventos]
    return EntregaOut(**data)


@router.post("/entregas/{entrega_id}/status", response_model=EntregaOut)
def atualizar_status(
  entrega_id: int,
  body: EntregaStatusUpdateIn,
  db: Session = Depends(get_db),
  entregador: Entregador = Depends(get_current_entregador),
):
    """Atualiza status da entrega (máquina de estados)."""
    try:
        entrega = atualizar_status_entrega(db, entrega_id, entregador.id, body.novo_status)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    data = EntregaOut.model_validate(entrega).model_dump()
    data["eventos"] = [EntregaEventoOut.model_validate(ev) for ev in entrega.eventos]
    return EntregaOut(**data)


# --- CRUD Veículos do Entregador ---
@router.get("/veiculos", response_model=List[EntregadorVeiculoResponse])
def listar_veiculos(
    db: Session = Depends(get_db),
    entregador: Entregador = Depends(get_current_entregador),
):
    """Lista veículos do entregador logado."""
    return (
        db.query(EntregadorVeiculo)
        .filter(EntregadorVeiculo.entregador_id == entregador.id)
        .order_by(EntregadorVeiculo.id)
        .all()
    )


@router.post("/veiculos", response_model=EntregadorVeiculoResponse, status_code=status.HTTP_201_CREATED)
def criar_veiculo(
    body: EntregadorVeiculoCreate,
    db: Session = Depends(get_db),
    entregador: Entregador = Depends(get_current_entregador),
):
    """Cadastra novo veículo para o entregador logado."""
    veiculo = EntregadorVeiculo(
        entregador_id=entregador.id,
        tipo_veiculo=body.tipo_veiculo,
        capacidade_kg=body.capacidade_kg,
        descricao=body.descricao,
        placa=body.placa,
    )
    db.add(veiculo)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail="Placa já cadastrada para este entregador")
    db.refresh(veiculo)
    return veiculo


@router.patch("/veiculos/{veiculo_id}", response_model=EntregadorVeiculoResponse)
def atualizar_veiculo(
    veiculo_id: int,
    body: EntregadorVeiculoUpdate,
    db: Session = Depends(get_db),
    entregador: Entregador = Depends(get_current_entregador),
):
    """Atualiza veículo do entregador logado."""
    veiculo = db.query(EntregadorVeiculo).filter(
        EntregadorVeiculo.id == veiculo_id,
        EntregadorVeiculo.entregador_id == entregador.id,
    ).first()
    if not veiculo:
        raise HTTPException(status_code=404, detail="Veículo não encontrado")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(veiculo, k, v)
    db.commit()
    db.refresh(veiculo)
    return veiculo


@router.delete("/veiculos/{veiculo_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_veiculo(
    veiculo_id: int,
    db: Session = Depends(get_db),
    entregador: Entregador = Depends(get_current_entregador),
):
    """Remove veículo do entregador logado."""
    veiculo = db.query(EntregadorVeiculo).filter(
        EntregadorVeiculo.id == veiculo_id,
        EntregadorVeiculo.entregador_id == entregador.id,
    ).first()
    if not veiculo:
        raise HTTPException(status_code=404, detail="Veículo não encontrado")
    db.delete(veiculo)
    db.commit()
