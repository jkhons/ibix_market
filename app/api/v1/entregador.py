# PDV Ibix - API Entregador (logística local)
"""Login, cadastro público, painel, entregas e veículos."""
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session, joinedload

from ...core.auth import AuthConfig, create_entregador_token, verify_user_credentials
from ...core.constants.entrega_status import DISPONIVEL
from ...database.connection import get_db
from ...models import Entregador, EntregadorVeiculo, EntregaMarketplace, LojaMarketplace
from ...schemas.entrega_marketplace import EntregaDisponivelOut, EntregaEventoOut, EntregaOut, EntregaStatusUpdateIn
from ...schemas.entregador import (
    CadastroPublicoEntregadorOk,
    EntregadorLoginIn,
    EntregadorLoginResponse,
    EntregadorMeOut,
    EntregadorVeiculoResponse,
    EntregadorVeiculoUpdate,
    PainelCorridaMinhaOut,
    PainelResumoOut,
    EntregadorResponse,
)
from ...services.logistica.entrega_aceite_service import aceitar_entrega
from ...services.logistica.entrega_service import marcar_entregas_expiradas
from ...services.logistica.entrega_status_service import atualizar_status_entrega
from ...services.logistica.entregador_arquivo_service import (
    gravar_em_entregador_dir,
    ler_e_validar_upload,
    normalizar_placa,
    normalizar_tipo_veiculo,
    parse_capacidade_kg,
    validar_assinatura_arquivo,
)
from ...services.logistica import entregador_rules

router = APIRouter(prefix="/entregador", tags=["Entregador (logística)"])

COOKIE_ENTREGADOR = "entregador_token"


def _token_from_request_entregador(request: Request) -> Optional[str]:
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        return auth[7:].strip()
    return request.cookies.get(COOKIE_ENTREGADOR)


def get_entregador_sessao(
    request: Request,
    db: Session = Depends(get_db),
) -> Entregador:
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
    entregador = (
        db.query(Entregador).options(joinedload(Entregador.veiculos)).filter(Entregador.id == eid).first()
    )
    if not entregador or not entregador.ativo or entregador.status == "bloqueado":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Entregador não encontrado ou inativo")
    return entregador


def get_entregador_operacional(entregador: Entregador = Depends(get_entregador_sessao)) -> Entregador:
    if not entregador_rules.entregador_perfil_operacional(entregador):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cadastro em análise ou perfil não aprovado pela plataforma.",
        )
    if not any(v.ativo and v.documento_aprovado for v in entregador.veiculos or []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="É necessário pelo menos um veículo com documento aprovado.",
        )
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


def _iter_entregas_disponiveis_filtradas(db: Session, entregador: Entregador) -> List[EntregaMarketplace]:
    marcar_entregas_expiradas(db)
    agora = datetime.now(timezone.utc)
    q = (
        db.query(EntregaMarketplace)
        .filter(
            EntregaMarketplace.status == DISPONIVEL,
            EntregaMarketplace.entregador_id.is_(None),
        )
        .order_by(EntregaMarketplace.publicada_em.desc())
        .limit(100)
    )
    rows = []
    for e in q.all():
        if e.aceita_ate_em and e.aceita_ate_em < agora:
            continue
        if not entregador_rules.entregador_tem_veiculo_aprovado_para_tipo(entregador, e.tipo_veiculo_aceito):
            continue
        rows.append(e)
    return rows


@router.post("/cadastro-publico", response_model=CadastroPublicoEntregadorOk)
async def cadastro_publico_entregador(
    nome: str = Form(..., max_length=150),
    email: str = Form(..., max_length=150),
    senha: str = Form(..., min_length=6, max_length=128),
    telefone: Optional[str] = Form(None, max_length=30),
    cidade: Optional[str] = Form(None, max_length=100),
    veiculos_json: str = Form(..., description="JSON array de veículos"),
    cnh: UploadFile = File(...),
    documentos_veiculos: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """Cadastro público (multipart). Exige CNH e um arquivo por veículo."""
    email_n = (email or "").strip().lower()
    if db.query(Entregador).filter(Entregador.email == email_n).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Não foi possível concluir o cadastro.",
        )
    try:
        raw_veics = json.loads(veiculos_json)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="veiculos_json inválido")
    if not isinstance(raw_veics, list) or len(raw_veics) < 1:
        raise HTTPException(status_code=400, detail="Informe ao menos um veículo")
    if len(documentos_veiculos) != len(raw_veics):
        raise HTTPException(status_code=400, detail="Quantidade de arquivos de veículo deve coincidir com veículos")

    cnh_raw, _ = await ler_e_validar_upload(cnh, "cnh")

    parsed_veics: List[dict] = []
    for i, item in enumerate(raw_veics):
        if not isinstance(item, dict):
            raise HTTPException(status_code=400, detail="Cada veículo deve ser um objeto JSON")
        tv = normalizar_tipo_veiculo(str(item.get("tipo_veiculo") or ""))
        placa = normalizar_placa(item.get("placa"))
        desc = (item.get("descricao") or None)
        if desc is not None:
            desc = str(desc)[:100]
        cap = parse_capacidade_kg(item.get("capacidade_kg"))
        parsed_veics.append({"tipo_veiculo": tv, "placa": placa, "descricao": desc, "capacidade_kg": cap, "idx": i})

    primeiro_tipo = parsed_veics[0]["tipo_veiculo"]
    ent = Entregador(
        nome=nome.strip()[:150],
        email=email_n,
        senha_hash=AuthConfig.get_password_hash(senha),
        telefone=(telefone or "").strip()[:30] or None,
        cidade=(cidade or "").strip()[:100] or None,
        ativo=True,
        status="pendente",
        tipo_veiculo=primeiro_tipo,
    )
    db.add(ent)
    db.flush()

    try:
        ext_cnh, _ = validar_assinatura_arquivo(cnh_raw[: min(len(cnh_raw), 64)], "cnh")
        ent.cnh_arquivo_path = gravar_em_entregador_dir(ent.id, "cnh", ext_cnh, cnh_raw)
        ent.cadastro_enviado_em = datetime.now(timezone.utc)

        for pv in parsed_veics:
            doc_raw, _ = await ler_e_validar_upload(documentos_veiculos[pv["idx"]], "veiculo")
            ext_v, _ = validar_assinatura_arquivo(doc_raw[: min(len(doc_raw), 64)], "veiculo")
            path_v = gravar_em_entregador_dir(ent.id, f"veiculo_{pv['idx']}", ext_v, doc_raw)
            v = EntregadorVeiculo(
                entregador_id=ent.id,
                tipo_veiculo=pv["tipo_veiculo"],
                placa=pv["placa"],
                descricao=pv["descricao"],
                capacidade_kg=pv["capacidade_kg"],
                documento_veiculo_path=path_v,
                documento_aprovado=False,
                ativo=True,
            )
            db.add(v)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail="Falha ao processar cadastro. Verifique os dados e arquivos.")

    return CadastroPublicoEntregadorOk(mensagem="Cadastro recebido. Aguarde a análise da plataforma.")


@router.get("/me", response_model=EntregadorMeOut)
def entregador_me(entregador: Entregador = Depends(get_entregador_sessao)):
    tem_v = any(v.ativo and v.documento_aprovado for v in entregador.veiculos or [])
    pode = entregador_rules.entregador_perfil_operacional(entregador) and tem_v
    return EntregadorMeOut(
        id=entregador.id,
        nome=entregador.nome,
        email=entregador.email,
        status=entregador.status,
        ativo=entregador.ativo,
        tem_veiculo_aprovado=tem_v,
        pode_operar=pode,
    )


@router.get("/painel-resumo", response_model=PainelResumoOut)
def painel_resumo(
    db: Session = Depends(get_db),
    entregador: Entregador = Depends(get_entregador_operacional),
):
    disponiveis = _iter_entregas_disponiveis_filtradas(db, entregador)
    q_disp = Decimal("0")
    for e in disponiveis:
        q_disp += Decimal(str(e.valor_frete or 0))

    minhas_todas = (
        db.query(EntregaMarketplace)
        .filter(EntregaMarketplace.entregador_id == entregador.id)
        .order_by(EntregaMarketplace.id.desc())
        .limit(300)
        .all()
    )
    andamento_status = ("aceita", "em_retirada", "retirada", "em_rota")
    encerradas_status = ("entregue", "cancelada", "falha_entrega")
    n_and = 0
    n_enc = 0
    soma_repasse = Decimal("0")
    pedidos_sem_custo = 0
    totais_pag: dict = {"pendente": Decimal("0"), "liberado": Decimal("0"), "pago": Decimal("0")}

    for ent in minhas_todas:
        if ent.status in andamento_status:
            n_and += 1
        if ent.status in encerradas_status:
            n_enc += 1
        ped = ent.pedido
        custo = getattr(ped, "custo_frete", None) if ped else None
        if custo is not None:
            soma_repasse += Decimal(str(custo))
        elif ent.status == "entregue":
            pedidos_sem_custo += 1
        stp = ent.status_pagamento_entregador or "pendente"
        if custo is not None and stp in totais_pag:
            totais_pag[stp] += Decimal(str(custo))

    return PainelResumoOut(
        quantidade_disponiveis=len(disponiveis),
        soma_valor_frete_disponiveis=q_disp,
        quantidade_minhas_andamento=n_and,
        quantidade_minhas_encerradas=n_enc,
        soma_repasse_pedidos_com_custo=soma_repasse,
        pedidos_sem_custo_frete=pedidos_sem_custo,
        totais_pagamento={k: float(v) for k, v in totais_pag.items()},
    )


@router.get("/painel-corridas", response_model=dict)
def painel_corridas(
    db: Session = Depends(get_db),
    entregador: Entregador = Depends(get_entregador_operacional),
):
    disponiveis = _iter_entregas_disponiveis_filtradas(db, entregador)
    out_disp = []
    for e in disponiveis:
        loja = None
        if e.pedido:
            loja = db.query(LojaMarketplace).filter(LojaMarketplace.id == e.pedido.loja_id).first()
        loja_nome = loja.nome_loja if loja else None
        out_disp.append(EntregaDisponivelOut(**_entrega_para_disponivel(e, loja_nome)).model_dump())

    minhas = (
        db.query(EntregaMarketplace)
        .filter(EntregaMarketplace.entregador_id == entregador.id)
        .order_by(EntregaMarketplace.aceita_em.desc().nullslast(), EntregaMarketplace.id.desc())
        .limit(150)
        .all()
    )
    out_minhas = []
    for ent in minhas:
        ped = ent.pedido
        custo = getattr(ped, "custo_frete", None) if ped else None
        out_minhas.append(
            PainelCorridaMinhaOut(
                entrega_id=ent.id,
                pedido_id=ent.pedido_id,
                valor_frete=ent.valor_frete,
                valor_repasse_entregador=Decimal(str(custo)) if custo is not None else None,
                status_entrega=ent.status,
                status_pagamento_entregador=ent.status_pagamento_entregador or "pendente",
            ).model_dump(mode="json")
        )
    return {"disponiveis": out_disp, "minhas": out_minhas}


@router.post("/login", response_model=EntregadorLoginResponse)
def entregador_login(body: EntregadorLoginIn, db: Session = Depends(get_db)):
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
    entregador: Entregador = Depends(get_entregador_operacional),
):
    rows = _iter_entregas_disponiveis_filtradas(db, entregador)
    out = []
    for e in rows:
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
    entregador: Entregador = Depends(get_entregador_operacional),
):
    entrega_chk = db.query(EntregaMarketplace).filter(EntregaMarketplace.id == entrega_id).first()
    if not entrega_chk:
        raise HTTPException(status_code=404, detail="Entrega não encontrada")
    if not entregador_rules.entregador_tem_veiculo_aprovado_para_tipo(entregador, entrega_chk.tipo_veiculo_aceito):
        raise HTTPException(status_code=400, detail="Nenhum veículo aprovado compatível com esta corrida")
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
    entregador: Entregador = Depends(get_entregador_operacional),
):
    q = db.query(EntregaMarketplace).filter(EntregaMarketplace.entregador_id == entregador.id)
    if em_andamento is not None:
        if em_andamento:
            q = q.filter(EntregaMarketplace.status.in_(("aceita", "em_retirada", "retirada", "em_rota")))
        else:
            q = q.filter(EntregaMarketplace.status.in_(("entregue", "cancelada", "falha_entrega")))
    rows = q.order_by(EntregaMarketplace.aceita_em.desc().nullslast()).limit(100).all()
    return [
        EntregaOut(**EntregaOut.model_validate(e).model_dump() | {"eventos": [EntregaEventoOut.model_validate(ev) for ev in e.eventos]})
        for e in rows
    ]


@router.get("/entregas/{entrega_id}", response_model=EntregaOut)
def detalhe_entrega(
    entrega_id: int,
    db: Session = Depends(get_db),
    entregador: Entregador = Depends(get_entregador_operacional),
):
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
    entregador: Entregador = Depends(get_entregador_operacional),
):
    try:
        entrega = atualizar_status_entrega(db, entrega_id, entregador.id, body.novo_status)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    data = EntregaOut.model_validate(entrega).model_dump()
    data["eventos"] = [EntregaEventoOut.model_validate(ev) for ev in entrega.eventos]
    return EntregaOut(**data)


@router.get("/veiculos", response_model=List[EntregadorVeiculoResponse])
def listar_veiculos(
    db: Session = Depends(get_db),
    entregador: Entregador = Depends(get_entregador_sessao),
):
    return (
        db.query(EntregadorVeiculo)
        .filter(EntregadorVeiculo.entregador_id == entregador.id)
        .order_by(EntregadorVeiculo.id)
        .all()
    )


@router.post("/veiculos", status_code=status.HTTP_400_BAD_REQUEST)
def criar_veiculo_json_descontinuado(
    db: Session = Depends(get_db),
    entregador: Entregador = Depends(get_entregador_operacional),
):
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Use POST /api/v1/entregador/veiculos/com-documento com arquivo do veículo.",
    )


@router.post("/veiculos/com-documento", response_model=EntregadorVeiculoResponse, status_code=status.HTTP_201_CREATED)
async def criar_veiculo_com_documento(
    tipo_veiculo: str = Form(...),
    placa: Optional[str] = Form(None),
    descricao: Optional[str] = Form(None),
    capacidade_kg: Optional[str] = Form(None),
    documento: UploadFile = File(...),
    db: Session = Depends(get_db),
    entregador: Entregador = Depends(get_entregador_operacional),
):
    tv = normalizar_tipo_veiculo(tipo_veiculo)
    doc_raw, _ = await ler_e_validar_upload(documento, "veiculo")
    ext_v, _ = validar_assinatura_arquivo(doc_raw[: min(len(doc_raw), 64)], "veiculo")
    path_v = gravar_em_entregador_dir(entregador.id, "veiculo_novo", ext_v, doc_raw)
    veiculo = EntregadorVeiculo(
        entregador_id=entregador.id,
        tipo_veiculo=tv,
        placa=normalizar_placa(placa),
        descricao=(descricao or "").strip()[:100] or None,
        capacidade_kg=parse_capacidade_kg(capacidade_kg),
        documento_veiculo_path=path_v,
        documento_aprovado=False,
        ativo=True,
    )
    db.add(veiculo)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail="Não foi possível cadastrar veículo (placa duplicada?)")
    db.refresh(veiculo)
    db.refresh(entregador, ["veiculos"])
    return veiculo


@router.patch("/veiculos/{veiculo_id}", response_model=EntregadorVeiculoResponse)
def atualizar_veiculo(
    veiculo_id: int,
    body: EntregadorVeiculoUpdate,
    db: Session = Depends(get_db),
    entregador: Entregador = Depends(get_entregador_operacional),
):
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
    entregador: Entregador = Depends(get_entregador_operacional),
):
    veiculo = db.query(EntregadorVeiculo).filter(
        EntregadorVeiculo.id == veiculo_id,
        EntregadorVeiculo.entregador_id == entregador.id,
    ).first()
    if not veiculo:
        raise HTTPException(status_code=404, detail="Veículo não encontrado")
    db.delete(veiculo)
    db.commit()
