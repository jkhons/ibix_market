# PDV Ibix - API de Notas Fiscais (NF-e / NFC-e)
import asyncio
import os
from datetime import date, datetime
from pathlib import Path as PathLib
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from ...core.config import FISCAL_UPLOADS_DIR, PROJECT_ROOT
from ...core.logging import log_error
from ...core.middleware import (
    forbid_cliente_access,
    forbid_contador_edit,
    get_cliente_scope_dep,
    get_current_user,
    require_permission,
)
from ...core.scope import ClienteScope, get_empresa_fiscal_para_estabelecimento
from ...database.connection import SessionLocal, get_db
from ...models.abertura_caixa import AberturaCaixa
from ...models.caixa import Caixa
from ...models.cliente import Cliente
from ...models.empresa import Empresa
from ...models.fiscal_download_log import ArquivoTipoFiscalEnum as ArquivoTipoLog
from ...models.fiscal_download_log import DocumentoTipoFiscalEnum as DocTipoLog
from ...models.fiscal_download_log import FiscalDownloadLog
from ...models.nota_fiscal import NotaFiscal, NotaFiscalItem, StatusNotaEnum
from ...models.produto_cliente import ProdutoCliente
from ...models.usuario import Usuario
from ...models.venda import Venda
from ...schemas.nota_fiscal import (
    CancelarNotaBody,
    NotaFiscalCreate,
    NotaFiscalResponse,
    NotaFiscalUpdate,
)
from ...services.fiscal.emissao_service import FiscalEmissaoService, preparar_nota_para_validacao, validar_nota_fiscal

router = APIRouter(
    prefix="/fiscal/notas-fiscais",
    tags=["Fiscal - Notas Fiscais"],
    dependencies=[Depends(forbid_cliente_access)]
)

@router.post("", response_model=NotaFiscalResponse, status_code=status.HTTP_201_CREATED)
async def criar_nota_fiscal(
    nota_data: NotaFiscalCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """
    Cria uma nova nota fiscal (NF-e ou NFC-e).
    Regra: quem emite para o CF é o CA (tenant) via Empresa FISCAL. Se venda_id for informado,
    a empresa da nota é obrigatoriamente a do estabelecimento da venda (nunca de outro CA).
    """
    try:
        empresa_id_uso = nota_data.empresa_id
        if nota_data.venda_id:
            venda = (
                db.query(Venda)
                .options(joinedload(Venda.abertura_caixa).joinedload(AberturaCaixa.caixa), joinedload(Venda.itens))
                .filter(Venda.id == nota_data.venda_id)
                .first()
            )
            if not venda:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venda não encontrada")
            estabelecimento_id = getattr(venda, "cliente_id", None)
            if estabelecimento_id is None and getattr(venda, "abertura_caixa_id", None):
                ab = venda.abertura_caixa if getattr(venda, "abertura_caixa", None) else db.query(AberturaCaixa).filter(AberturaCaixa.id == venda.abertura_caixa_id).first()
                if ab:
                    cx = ab.caixa if getattr(ab, "caixa", None) else db.query(Caixa).filter(Caixa.id == ab.caixa_id).first()
                    if cx:
                        emp_v = db.query(Empresa).filter(Empresa.id == cx.empresa_id).first()
                        if emp_v:
                            estabelecimento_id = getattr(emp_v, "cliente_id", None)
            if estabelecimento_id is None and venda.itens:
                for vi in venda.itens:
                    if getattr(vi, "produto_cliente_id", None):
                        pc = db.query(ProdutoCliente).filter(ProdutoCliente.id == vi.produto_cliente_id).first()
                        if pc:
                            estabelecimento_id = getattr(pc, "cliente_id", None)
                            break
            empresa_venda = get_empresa_fiscal_para_estabelecimento(db, estabelecimento_id) if estabelecimento_id else None
            if empresa_venda:
                empresa_id_uso = empresa_venda.id
        empresa = db.query(Empresa).filter(Empresa.id == empresa_id_uso).first()
        if not empresa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Empresa não encontrada"
            )
        if scope.must_filter_by_cliente():
            cid = getattr(empresa, "cliente_id", None)
            if cid is None or cid not in scope.allowed_ids:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Empresa fora do seu escopo de acesso")
        
        # Validar cliente se fornecido
        if nota_data.cliente_id:
            cliente = db.query(Cliente).filter(Cliente.id == nota_data.cliente_id).first()
            if not cliente:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Cliente não encontrado"
                )
        
        # Criar nota fiscal (empresa_id = Empresa FISCAL do CA dono do contexto; se venda_id, já forçado acima)
        nota_dict = nota_data.model_dump(exclude={'itens'})
        nota_dict["empresa_id"] = empresa_id_uso
        nota = NotaFiscal(**nota_dict)
        db.add(nota)
        db.flush()  # Para obter o ID da nota
        
        # Criar itens
        for item_data in nota_data.itens:
            item_dict = item_data.model_dump()
            item = NotaFiscalItem(**item_dict, nota_id=nota.id)
            db.add(item)
        
        db.commit()
        db.refresh(nota)
        
        # Carregar itens para resposta
        nota = db.query(NotaFiscal).options(joinedload(NotaFiscal.itens)).filter(NotaFiscal.id == nota.id).first()
        
        return NotaFiscalResponse.model_validate(nota)
        
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Erro ao criar nota fiscal. Verifique os dados fornecidos."
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@router.get("", response_model=List[NotaFiscalResponse])
async def listar_notas_fiscais(
    empresa_id: Optional[int] = Query(None, description="Filtrar por empresa"),
    cliente_id: Optional[int] = Query(None, description="Filtrar por cliente"),
    venda_id: Optional[int] = Query(None, description="Filtrar por venda"),
    pedido_id: Optional[int] = Query(None, description="Filtrar por pedido"),
    tipo: Optional[str] = Query(None, description="Filtrar por tipo (NFe ou NFCe)"),
    status_filtro: Optional[str] = Query(None, alias="status", description="Filtrar por status"),
    data_inicio: Optional[date] = Query(None, description="Data inicial de emissão"),
    data_fim: Optional[date] = Query(None, description="Data final de emissão"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Lista notas fiscais com filtros"""
    try:
        query = db.query(NotaFiscal).options(
            joinedload(NotaFiscal.itens),
            joinedload(NotaFiscal.cliente),
            joinedload(NotaFiscal.empresa)
        )
        if scope.must_filter_by_cliente():
            if not scope.allowed_ids:
                return []
            # CA/Admin: apenas notas cuja EMPRESA pertence ao escopo (evita mostrar nota de empresa de outro tenant)
            query = query.join(Empresa, NotaFiscal.empresa_id == Empresa.id).filter(
                Empresa.cliente_id.in_(scope.allowed_ids)
            )
        
        if empresa_id:
            query = query.filter(NotaFiscal.empresa_id == empresa_id)
        
        if cliente_id:
            query = query.filter(NotaFiscal.cliente_id == cliente_id)
        
        if venda_id:
            query = query.filter(NotaFiscal.venda_id == venda_id)
        
        if pedido_id:
            query = query.filter(NotaFiscal.pedido_id == pedido_id)
        
        if tipo:
            query = query.filter(NotaFiscal.tipo == tipo)
        
        if status_filtro:
            query = query.filter(NotaFiscal.status == status_filtro)
        
        if data_inicio:
            query = query.filter(NotaFiscal.data_emissao >= datetime.combine(data_inicio, datetime.min.time()))
        
        if data_fim:
            query = query.filter(NotaFiscal.data_emissao <= datetime.combine(data_fim, datetime.max.time()))
        
        notas = query.order_by(NotaFiscal.data_emissao.desc()).offset(skip).limit(limit).all()
        
        # Converter notas para dict com relacionamentos
        notas_response = []
        for nota in notas:
            nota_dict = NotaFiscalResponse.model_validate(nota).model_dump()
            nota_dict['cliente'] = {
                'id': nota.cliente.id,
                'nome': nota.cliente.nome,
                'razao_social': getattr(nota.cliente, 'razao_social', None) or nota.cliente.nome,
                'cnpj': nota.cliente.cnpj,
                'cpf': getattr(nota.cliente, 'cpf', None)
            } if nota.cliente else None
            nota_dict['empresa'] = {
                'id': nota.empresa.id,
                'razao_social': nota.empresa.razao_social,
                'nome_fantasia': nota.empresa.nome_fantasia,
                'cnpj': nota.empresa.cnpj
            } if nota.empresa else None
            notas_response.append(NotaFiscalResponse(**nota_dict))
        
        return notas_response
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@router.get("/{nota_id}", response_model=NotaFiscalResponse)
async def obter_nota_fiscal(
    nota_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Obtém uma nota fiscal específica por ID"""
    try:
        nota = db.query(NotaFiscal).options(
            joinedload(NotaFiscal.itens),
            joinedload(NotaFiscal.cliente),
            joinedload(NotaFiscal.empresa)
        ).filter(NotaFiscal.id == nota_id).first()
        
        if not nota:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Nota fiscal não encontrada"
            )
        if scope.must_filter_by_cliente():
            cid = getattr(nota.empresa, "cliente_id", None) if nota.empresa else getattr(nota, "cliente_id", None)
            if cid is None or cid not in scope.allowed_ids:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nota fiscal não encontrada")
        
        # Converter nota para dict com relacionamentos
        nota_dict = NotaFiscalResponse.model_validate(nota).model_dump()
        nota_dict['cliente'] = {
            'id': nota.cliente.id,
            'nome': nota.cliente.nome,
            'razao_social': getattr(nota.cliente, 'razao_social', None) or nota.cliente.nome,
            'cnpj': nota.cliente.cnpj,
            'cpf': getattr(nota.cliente, 'cpf', None)
        } if nota.cliente else None
        nota_dict['empresa'] = {
            'id': nota.empresa.id,
            'razao_social': nota.empresa.razao_social,
            'nome_fantasia': nota.empresa.nome_fantasia,
            'cnpj': nota.empresa.cnpj
        } if nota.empresa else None
        
        return NotaFiscalResponse(**nota_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@router.put("/{nota_id}", response_model=NotaFiscalResponse)
async def atualizar_nota_fiscal(
    nota_id: int,
    nota_data: NotaFiscalUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
    _: None = Depends(forbid_contador_edit),
):
    """Atualiza uma nota fiscal existente (apenas rascunho/pendente). Contador não pode editar."""
    try:
        nota = db.query(NotaFiscal).options(joinedload(NotaFiscal.empresa)).filter(NotaFiscal.id == nota_id).first()
        
        if not nota:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Nota fiscal não encontrada"
            )
        if scope.must_filter_by_cliente():
            cid = getattr(nota.empresa, "cliente_id", None) if nota.empresa else getattr(nota, "cliente_id", None)
            if cid is None or cid not in scope.allowed_ids:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nota fiscal não encontrada")
        
        if nota.status not in (StatusNotaEnum.RASCUNHO, StatusNotaEnum.PENDENTE):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Apenas notas em rascunho ou pendente podem ser atualizadas"
            )
        
        # Atualizar apenas campos fornecidos
        update_data = nota_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(nota, field, value)
        
        db.commit()
        db.refresh(nota)
        
        # Carregar itens para resposta
        nota = db.query(NotaFiscal).options(joinedload(NotaFiscal.itens)).filter(NotaFiscal.id == nota.id).first()
        
        return NotaFiscalResponse.model_validate(nota)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@router.get("/chave/{chave_acesso}", response_model=NotaFiscalResponse)
async def buscar_nota_por_chave_acesso(
    chave_acesso: str,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Busca nota fiscal por chave de acesso"""
    try:
        nota = db.query(NotaFiscal).options(
            joinedload(NotaFiscal.itens),
            joinedload(NotaFiscal.empresa),
        ).filter(NotaFiscal.chave_acesso == chave_acesso).first()
        
        if not nota:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Nota fiscal não encontrada"
            )
        if scope.must_filter_by_cliente():
            cid = getattr(nota.empresa, "cliente_id", None) if nota.empresa else getattr(nota, "cliente_id", None)
            if cid is None or cid not in scope.allowed_ids:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nota fiscal não encontrada")
        
        return NotaFiscalResponse.model_validate(nota)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@router.post("/{nota_id}/validar")
async def validar_nota_fiscal_endpoint(
    nota_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Valida uma nota fiscal antes do envio. Pré-processa número/série e motor tributário (CFOP, CSOSN) antes de validar. Retorna lista de erros (vazia se OK)."""
    nota = db.query(NotaFiscal).options(
        joinedload(NotaFiscal.itens),
        joinedload(NotaFiscal.empresa),
        joinedload(NotaFiscal.cliente),
    ).filter(NotaFiscal.id == nota_id).first()
    if not nota:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nota fiscal não encontrada")
    if scope.must_filter_by_cliente():
        cid = getattr(nota.empresa, "cliente_id", None) if nota.empresa else None
        if cid is None or cid not in scope.allowed_ids:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nota fiscal não encontrada")
    err_prep = preparar_nota_para_validacao(db, nota)
    if err_prep:
        db.rollback()
        return {"valido": False, "erros": [err_prep]}
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    erros = validar_nota_fiscal(db, nota)
    return {"valido": len(erros) == 0, "erros": erros}


def _run_enviar_nfe_sync(nota_id: int, usuario_id: int):
    """Executa envio à SEFAZ em thread com sessão dedicada. Evita bloquear o event loop e reduz 'Client closed request'."""
    session = SessionLocal()
    try:
        svc = FiscalEmissaoService(session)
        ok, err, _ = svc.enviar_nfe(nota_id, usuario_id=usuario_id)
        if not ok:
            return (False, err, None)
        session.commit()
        nota = session.query(NotaFiscal).options(
            joinedload(NotaFiscal.itens),
            joinedload(NotaFiscal.empresa),
            joinedload(NotaFiscal.cliente),
        ).filter(NotaFiscal.id == nota_id).first()
        nota_dict = NotaFiscalResponse.model_validate(nota).model_dump() if nota else None
        return (True, None, nota_dict)
    finally:
        session.close()


@router.post("/{nota_id}/enviar")
async def enviar_nota_fiscal(
    nota_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
    _: None = Depends(forbid_contador_edit),
):
    """Envia nota fiscal ao provedor (NF-e ou NFC-e conforme tipo). Operação em thread para evitar timeout (Client closed request)."""
    nota = db.query(NotaFiscal).options(joinedload(NotaFiscal.empresa)).filter(NotaFiscal.id == nota_id).first()
    if not nota:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nota fiscal não encontrada")
    if scope.must_filter_by_cliente():
        cid = getattr(nota.empresa, "cliente_id", None) if nota.empresa else None
        if cid is None or cid not in scope.allowed_ids:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nota fiscal não encontrada")
    try:
        sucesso, msg_erro, nota_dict = await asyncio.to_thread(
            _run_enviar_nfe_sync, nota_id, current_user.id
        )
    except Exception as e:
        log_error(f"Erro ao enviar NF-e (nota_id={nota_id}): {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao emitir nota fiscal: {str(e)}",
        )
    if not sucesso:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg_erro or "Falha no envio")
    return {"sucesso": True, "mensagem": "Nota enviada", "nota": nota_dict}


@router.get("/{nota_id}/download/xml")
async def download_xml_nota_fiscal(
    nota_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
    _: Usuario = Depends(require_permission("fiscal:baixar_xml")),
):
    """Baixa XML da nota fiscal. Exige permissão fiscal:baixar_xml. Registra em fiscal_download_log.
    Se o arquivo não existir (ex.: nota emitida em stub), gera o XML sob demanda a partir dos dados da nota."""
    nota = (
        db.query(NotaFiscal)
        .options(
            joinedload(NotaFiscal.empresa),
            joinedload(NotaFiscal.cliente),
            joinedload(NotaFiscal.itens),
            joinedload(NotaFiscal.venda),
        )
        .filter(NotaFiscal.id == nota_id)
        .first()
    )
    if not nota:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nota fiscal não encontrada")
    if scope.must_filter_by_cliente():
        if not scope.allowed_ids:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nota fiscal não encontrada")
        cid = getattr(nota.empresa, "cliente_id", None) if nota.empresa else None
        if cid is None or cid not in scope.allowed_ids:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nota fiscal não encontrada")
    path = nota.xml_path or nota.xml_retorno_path
    if path and os.path.exists(path):
        log = FiscalDownloadLog(usuario_id=current_user.id, documento_tipo=DocTipoLog.NFE if getattr(nota, "tipo", None) and str(getattr(nota.tipo, "value", "")).upper() == "NFE" else DocTipoLog.NFCE, documento_id=nota.id, arquivo_tipo=ArquivoTipoLog.XML)
        db.add(log)
        db.commit()
        return FileResponse(path, media_type="application/xml", filename=f"nota-{nota_id}.xml")
    # Nota autorizada sem arquivo (ex.: emitida em stub): gerar XML sob demanda
    if getattr(nota, "status", None) != StatusNotaEnum.AUTORIZADO and not getattr(nota, "chave_acesso", None):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo XML não disponível")
    if not nota.empresa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo XML não disponível")
    from ...services.fiscal.emissao_service import (
        _cliente_destinatario_para_payload,
        _empresa_para_payload,
        _payload_nota_fiscal,
    )
    from ...services.fiscal.nfe_xml_builder import montar_nfe

    payload = _payload_nota_fiscal(nota)
    payload["empresa"] = _empresa_para_payload(nota.empresa)
    payload["destinatario"] = _cliente_destinatario_para_payload(nota.cliente) if nota.cliente else None
    chave_override = (nota.chave_acesso or "").strip() if getattr(nota, "chave_acesso", None) else None
    xml_str = montar_nfe(payload, payload["empresa"], payload["destinatario"], chave_override=chave_override)
    log = FiscalDownloadLog(usuario_id=current_user.id, documento_tipo=DocTipoLog.NFE if getattr(nota, "tipo", None) and str(getattr(nota.tipo, "value", "")).upper() == "NFE" else DocTipoLog.NFCE, documento_id=nota.id, arquivo_tipo=ArquivoTipoLog.XML)
    db.add(log)
    db.commit()
    return Response(
        content=xml_str.encode("utf-8"),
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="nota-{nota_id}.xml"'},
    )


@router.get("/{nota_id}/download/pdf")
async def download_pdf_nota_fiscal(
    nota_id: int,
    inline: bool = Query(False, description="Se true, exibe o PDF no navegador (Content-Disposition: inline); se false, força download."),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
    _: Usuario = Depends(require_permission("fiscal:baixar_pdf")),
):
    """Baixa ou exibe PDF/DANFE da nota fiscal. inline=true para visualizar na aba; inline=false para download."""
    nota = (
        db.query(NotaFiscal)
        .options(
            joinedload(NotaFiscal.empresa),
            joinedload(NotaFiscal.cliente),
            joinedload(NotaFiscal.itens),
        )
        .filter(NotaFiscal.id == nota_id)
        .first()
    )
    if not nota:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nota fiscal não encontrada")
    if scope.must_filter_by_cliente():
        cid = getattr(nota.empresa, "cliente_id", None) if nota.empresa else None
        if cid is None or cid not in scope.allowed_ids:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nota fiscal não encontrada")
    path = getattr(nota, "danfe_path", None)
    if path and not os.path.isabs(path):
        path = str(PROJECT_ROOT / path)
    if not path or not os.path.exists(path):
        # Nota emitida (autorizada) deve ter PDF: gerar DANFE sob demanda se o provedor não salvou
        if getattr(nota, "status", None) != StatusNotaEnum.AUTORIZADO:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo PDF não disponível")
        from ...services.pdf_orcamento_pedido import gerar_pdf_danfe

        empresa_nome = (nota.empresa.razao_social or nota.empresa.nome_fantasia or "-") if nota.empresa else "-"
        cliente_nome = (nota.cliente.nome or getattr(nota.cliente, "razao_social", None) or "Consumidor final") if nota.cliente else "Consumidor final"
        itens = [
            {
                "item_numero": getattr(i, "item_numero", idx + 1),
                "descricao": getattr(i, "descricao", ""),
                "quantidade": getattr(i, "quantidade", 0),
                "valor_unitario": getattr(i, "valor_unitario", 0),
                "valor_total": getattr(i, "valor_total", 0),
            }
            for idx, i in enumerate(nota.itens or [])
        ]
        dados = {
            "numero": nota.numero,
            "serie": getattr(nota, "serie", None) or "1",
            "data_emissao": nota.data_emissao,
            "chave_acesso": getattr(nota, "chave_acesso", None),
            "empresa_nome": empresa_nome,
            "cliente_nome": cliente_nome,
            "valor_total": nota.valor_total,
            "itens": itens,
        }
        # Geração em thread para não bloquear o event loop e evitar timeout/Client closed request
        pdf_bytes = await asyncio.to_thread(gerar_pdf_danfe, dados)
        dir_pdf = FISCAL_UPLOADS_DIR / f"empresa_{nota.empresa_id}"
        dir_pdf.mkdir(parents=True, exist_ok=True)
        path = str(dir_pdf / f"danfe_{nota_id}.pdf")
        PathLib(path).write_bytes(pdf_bytes)
        nota.danfe_path = path
        db.commit()
    log = FiscalDownloadLog(usuario_id=current_user.id, documento_tipo=DocTipoLog.NFE if getattr(nota, "tipo", None) and str(getattr(nota.tipo, "value", "")).upper() == "NFE" else DocTipoLog.NFCE, documento_id=nota.id, arquivo_tipo=ArquivoTipoLog.PDF)
    db.add(log)
    db.commit()
    path_abs = str(PathLib(path).resolve())
    if inline:
        # Visualizar na aba: Content-Disposition inline para o navegador exibir o PDF em vez de baixar
        pdf_bytes = PathLib(path_abs).read_bytes()
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="danfe-{nota_id}.pdf"'},
        )
    return FileResponse(path_abs, media_type="application/pdf", filename=f"danfe-{nota_id}.pdf")


@router.post("/{nota_id}/cancelar", response_model=NotaFiscalResponse)
async def cancelar_nota_fiscal(
    nota_id: int,
    body: CancelarNotaBody = Body(..., description="Justificativa do cancelamento (mínimo 15 caracteres)"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
    _: None = Depends(forbid_contador_edit),
):
    """Cancela uma nota fiscal autorizada no provedor. Justificativa no body (mín. 15 caracteres). Contador não pode cancelar."""
    try:
        nota = db.query(NotaFiscal).options(joinedload(NotaFiscal.empresa)).filter(NotaFiscal.id == nota_id).first()
        if not nota:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nota fiscal não encontrada")
        if scope.must_filter_by_cliente():
            cid = getattr(nota.empresa, "cliente_id", None) if nota.empresa else getattr(nota, "cliente_id", None)
            if cid is None or cid not in scope.allowed_ids:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nota fiscal não encontrada")
        if nota.status != StatusNotaEnum.AUTORIZADO:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Apenas notas fiscais autorizadas podem ser canceladas")
        svc = FiscalEmissaoService(db)
        sucesso, msg_erro = svc.cancelar_nfe(nota_id, motivo=body.justificativa, usuario_id=current_user.id)
        if not sucesso:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg_erro or "Falha no cancelamento")
        db.commit()
        db.refresh(nota)
        nota = db.query(NotaFiscal).options(joinedload(NotaFiscal.itens)).filter(NotaFiscal.id == nota.id).first()
        return NotaFiscalResponse.model_validate(nota)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

