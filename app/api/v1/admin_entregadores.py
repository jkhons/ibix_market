# PDV Ibix — Admin: gestão de entregadores (Superadmin)
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from ...core.constants.entregador_logistica import STATUS_PAGAMENTO_ENTREGADOR_VALUES
from ...core.middleware import require_superadmin
from ...database.connection import get_db
from ...models import EntregaEvento, EntregaMarketplace, Entregador, EntregadorVeiculo, PedidoMarketplace, Usuario

router = APIRouter(prefix="/admin/entregadores", tags=["Admin entregadores"])


class EntregadorPagamentoPatch(BaseModel):
    status_pagamento_entregador: str = Field(..., description="pendente | liberado | pago")
    observacao: Optional[str] = None


class EntregadorVeiculoAdminOut(BaseModel):
    id: int
    tipo_veiculo: Optional[str] = None
    placa: Optional[str] = None
    documento_aprovado: bool
    documento_veiculo_path: Optional[str] = None

    model_config = {"from_attributes": True}


class EntregadorListOut(BaseModel):
    id: int
    nome: str
    email: str
    status: str
    ativo: bool
    cidade: Optional[str] = None
    cadastro_enviado_em: Optional[datetime] = None

    model_config = {"from_attributes": True}


@router.get("/", response_model=List[EntregadorListOut])
def listar_entregadores(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status_filtro: Optional[str] = Query(None, alias="status"),
    cidade: Optional[str] = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_superadmin()),
):
    q = db.query(Entregador).order_by(Entregador.id.desc())
    if status_filtro:
        q = q.filter(Entregador.status == status_filtro)
    if cidade:
        q = q.filter(Entregador.cidade.ilike(f"%{cidade.strip()}%"))
    rows = q.offset(skip).limit(limit).all()
    return rows


@router.get("/{entregador_id:int}", response_model=dict)
def detalhe_entregador(
    entregador_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_superadmin()),
):
    e = (
        db.query(Entregador)
        .options(joinedload(Entregador.veiculos))
        .filter(Entregador.id == entregador_id)
        .first()
    )
    if not e:
        raise HTTPException(status_code=404, detail="Entregador não encontrado")
    veics = [EntregadorVeiculoAdminOut.model_validate(v).model_dump() for v in sorted(e.veiculos, key=lambda x: x.id)]
    entregas = (
        db.query(EntregaMarketplace)
        .filter(EntregaMarketplace.entregador_id == entregador_id)
        .order_by(EntregaMarketplace.id.desc())
        .limit(80)
        .all()
    )
    ent_out = []
    for ent in entregas:
        ped = ent.pedido
        custo = getattr(ped, "custo_frete", None) if ped else None
        ent_out.append(
            {
                "id": ent.id,
                "pedido_id": ent.pedido_id,
                "status": ent.status,
                "valor_frete": float(ent.valor_frete or 0),
                "status_pagamento_entregador": ent.status_pagamento_entregador,
                "custo_frete_pedido": float(custo) if custo is not None else None,
            }
        )
    return {
        "id": e.id,
        "nome": e.nome,
        "email": e.email,
        "telefone": e.telefone,
        "cpf": e.cpf,
        "cidade": e.cidade,
        "status": e.status,
        "ativo": e.ativo,
        "cnh_arquivo_path": e.cnh_arquivo_path,
        "cadastro_enviado_em": e.cadastro_enviado_em.isoformat() if e.cadastro_enviado_em else None,
        "veiculos": veics,
        "entregas": ent_out,
    }


@router.patch("/{entregador_id:int}/aprovar")
def aprovar_perfil(
    entregador_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_superadmin()),
):
    e = db.query(Entregador).filter(Entregador.id == entregador_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Entregador não encontrado")
    e.status = "ativo"
    e.ativo = True
    db.commit()
    return {"ok": True, "status": e.status}


@router.patch("/{entregador_id:int}/bloquear")
def bloquear_perfil(
    entregador_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_superadmin()),
):
    e = db.query(Entregador).filter(Entregador.id == entregador_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Entregador não encontrado")
    e.status = "bloqueado"
    e.ativo = False
    db.commit()
    return {"ok": True}


@router.patch("/{entregador_id:int}/veiculos/{veiculo_id:int}/aprovar-documento")
def aprovar_documento_veiculo(
    entregador_id: int,
    veiculo_id: int,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_superadmin()),
):
    v = (
        db.query(EntregadorVeiculo)
        .filter(
            EntregadorVeiculo.id == veiculo_id,
            EntregadorVeiculo.entregador_id == entregador_id,
        )
        .first()
    )
    if not v:
        raise HTTPException(status_code=404, detail="Veículo não encontrado")
    agora = datetime.now(timezone.utc)
    v.documento_aprovado = True
    v.documento_aprovado_em = agora
    v.documento_aprovado_por_usuario_id = user.id
    db.commit()
    db.refresh(v)
    return EntregadorVeiculoAdminOut.model_validate(v)


@router.patch("/entregas/{entrega_id:int}/pagamento-entregador")
def atualizar_pagamento_entregador(
    entrega_id: int,
    body: EntregadorPagamentoPatch,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_superadmin()),
):
    st = (body.status_pagamento_entregador or "").strip()
    if st not in STATUS_PAGAMENTO_ENTREGADOR_VALUES:
        raise HTTPException(status_code=400, detail="status_pagamento_entregador inválido")
    ent = db.query(EntregaMarketplace).filter(EntregaMarketplace.id == entrega_id).first()
    if not ent:
        raise HTTPException(status_code=404, detail="Entrega não encontrada")
    if not ent.entregador_id:
        raise HTTPException(status_code=400, detail="Entrega sem entregador vinculado")
    anterior = ent.status_pagamento_entregador
    if anterior == st:
        return {"ok": True, "status_pagamento_entregador": st}
    ent.status_pagamento_entregador = st
    ent.pagamento_entregador_obs = body.observacao
    ent.pagamento_entregador_atualizado_em = datetime.now(timezone.utc)
    ent.pagamento_entregador_atualizado_por_usuario_id = user.id
    ev = EntregaEvento(
        entrega_id=ent.id,
        tipo_evento="pagamento_entregador_atualizado",
        actor_type="tenant_usuario",
        actor_id=user.id,
        payload_json={
            "status_anterior": anterior,
            "status_novo": st,
            "observacao": body.observacao,
        },
    )
    db.add(ev)
    db.commit()
    return {"ok": True, "status_pagamento_entregador": st}


@router.get("/{entregador_id:int}/arquivos/cnh")
def download_cnh(
    entregador_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_superadmin()),
):
    from ...services.logistica.entregador_arquivo_service import caminho_absoluto_seguro

    e = db.query(Entregador).filter(Entregador.id == entregador_id).first()
    if not e or not e.cnh_arquivo_path:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    abs_path = caminho_absoluto_seguro(e.cnh_arquivo_path)
    if not abs_path:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    return FileResponse(abs_path, filename="cnh", media_type="application/octet-stream")


@router.get("/{entregador_id:int}/veiculos/{veiculo_id:int}/arquivo-documento")
def download_documento_veiculo(
    entregador_id: int,
    veiculo_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_superadmin()),
):
    from ...services.logistica.entregador_arquivo_service import caminho_absoluto_seguro

    v = (
        db.query(EntregadorVeiculo)
        .filter(
            EntregadorVeiculo.id == veiculo_id,
            EntregadorVeiculo.entregador_id == entregador_id,
        )
        .first()
    )
    if not v or not v.documento_veiculo_path:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    abs_path = caminho_absoluto_seguro(v.documento_veiculo_path)
    if not abs_path:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    return FileResponse(abs_path, filename="documento_veiculo", media_type="application/octet-stream")
