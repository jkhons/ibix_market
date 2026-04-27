# PDV Ibix - API de Notas de Serviço (NFS-e)
import os
from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from ...core.middleware import (
    forbid_cliente_access,
    forbid_contador_edit,
    get_cliente_scope_dep,
    get_current_user,
    require_permission,
)
from ...core.scope import ClienteScope
from ...database.connection import get_db
from ...models.cliente import Cliente
from ...models.empresa import Empresa
from ...models.fiscal_download_log import ArquivoTipoFiscalEnum as ArquivoTipoLog
from ...models.fiscal_download_log import DocumentoTipoFiscalEnum as DocTipoLog
from ...models.fiscal_download_log import FiscalDownloadLog
from ...models.nota_servico import NotaServico, NotaServicoItem, StatusNotaServicoEnum
from ...models.usuario import Usuario
from ...models.venda import Venda
from ...schemas.nota_servico import NotaServicoCreate, NotaServicoResponse, NotaServicoUpdate
from ...services.fiscal.emissao_service import FiscalEmissaoService, validar_nota_servico

# Sem forbid_cliente_access no router: Subcliente pode GET (lista, detalhe) com escopo por destinatário.
# Rotas de escrita usam Depends(forbid_cliente_access) individualmente.
router = APIRouter(
    prefix="/fiscal/notas-servico",
    tags=["Fiscal - Notas de Serviço"],
)

@router.post("", response_model=NotaServicoResponse, status_code=status.HTTP_201_CREATED)
async def criar_nota_servico(
    nota_data: NotaServicoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
):
    """Cria uma nova nota de serviço (NFS-e)"""
    try:
        # Validar empresa
        empresa = db.query(Empresa).filter(Empresa.id == nota_data.empresa_id).first()
        if not empresa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Empresa não encontrada"
            )
        
        # Validar cliente se fornecido
        if nota_data.cliente_id:
            cliente = db.query(Cliente).filter(Cliente.id == nota_data.cliente_id).first()
            if not cliente:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Cliente não encontrado"
                )
        
        # Validar venda se fornecida
        if nota_data.venda_id:
            venda = db.query(Venda).filter(Venda.id == nota_data.venda_id).first()
            if not venda:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Venda não encontrada"
                )
        
        # Criar nota de serviço
        nota_dict = nota_data.model_dump(exclude={'itens'})
        nota = NotaServico(**nota_dict)
        db.add(nota)
        db.flush()
        
        # Criar itens
        for item_data in nota_data.itens:
            item_dict = item_data.model_dump()
            item = NotaServicoItem(**item_dict, nota_servico_id=nota.id)
            db.add(item)
        
        db.commit()
        db.refresh(nota)
        
        # Carregar itens para resposta
        nota = db.query(NotaServico).options(joinedload(NotaServico.itens)).filter(NotaServico.id == nota.id).first()
        
        return NotaServicoResponse.model_validate(nota)
        
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Erro ao criar nota de serviço. Verifique os dados fornecidos."
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@router.get("", response_model=List[NotaServicoResponse])
async def listar_notas_servico(
    empresa_id: Optional[int] = Query(None, description="Filtrar por empresa"),
    cliente_id: Optional[int] = Query(None, description="Filtrar por cliente"),
    venda_id: Optional[int] = Query(None, description="Filtrar por venda"),
    status: Optional[str] = Query(None, description="Filtrar por status"),
    data_inicio: Optional[date] = Query(None, description="Data inicial de emissão"),
    data_fim: Optional[date] = Query(None, description="Data final de emissão"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Lista notas de serviço com filtros. Subcliente vê por destinatário (NotaServico.cliente_id); demais por emissor (Empresa.cliente_id)."""
    try:
        query = db.query(NotaServico).options(joinedload(NotaServico.itens))
        if scope.must_filter_by_cliente():
            if not scope.allowed_ids:
                return []
            # Subcliente (cliente final): filtrar por destinatário da nota
            if current_user.role and current_user.role.nome == "Subcliente":
                query = query.filter(NotaServico.cliente_id.in_(scope.allowed_ids))
            else:
                query = query.join(Empresa).filter(Empresa.cliente_id.in_(scope.allowed_ids))
        if empresa_id:
            query = query.filter(NotaServico.empresa_id == empresa_id)
        
        if cliente_id:
            query = query.filter(NotaServico.cliente_id == cliente_id)
        
        if venda_id:
            query = query.filter(NotaServico.venda_id == venda_id)
        
        if status:
            query = query.filter(NotaServico.status == status)
        
        if data_inicio:
            query = query.filter(NotaServico.data_emissao >= datetime.combine(data_inicio, datetime.min.time()))
        
        if data_fim:
            query = query.filter(NotaServico.data_emissao <= datetime.combine(data_fim, datetime.max.time()))
        
        notas = query.order_by(NotaServico.data_emissao.desc()).offset(skip).limit(limit).all()
        
        return [NotaServicoResponse.model_validate(nota) for nota in notas]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@router.get("/{nota_id}", response_model=NotaServicoResponse)
async def obter_nota_servico(
    nota_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Obtém uma nota de serviço específica por ID. Subcliente só vê se for destinatário; demais por emissor."""
    try:
        nota = db.query(NotaServico).options(joinedload(NotaServico.itens), joinedload(NotaServico.empresa)).filter(NotaServico.id == nota_id).first()
        if not nota:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nota de serviço não encontrada")
        if scope.must_filter_by_cliente():
            if current_user.role and current_user.role.nome == "Subcliente":
                if nota.cliente_id not in scope.allowed_ids:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nota de serviço não encontrada")
            else:
                cid = getattr(nota.empresa, "cliente_id", None) if nota.empresa else None
                if cid is None or cid not in scope.allowed_ids:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nota de serviço não encontrada")
        return NotaServicoResponse.model_validate(nota)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@router.put("/{nota_id}", response_model=NotaServicoResponse)
async def atualizar_nota_servico(
    nota_id: int,
    nota_data: NotaServicoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    __: None = Depends(forbid_contador_edit),
):
    """Atualiza uma nota de serviço existente. Contador não pode editar."""
    try:
        nota = db.query(NotaServico).filter(NotaServico.id == nota_id).first()
        
        if not nota:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Nota de serviço não encontrada"
            )
        
        if nota.status not in (StatusNotaServicoEnum.RASCUNHO, StatusNotaServicoEnum.PENDENTE):
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
        nota = db.query(NotaServico).options(joinedload(NotaServico.itens)).filter(NotaServico.id == nota.id).first()
        
        return NotaServicoResponse.model_validate(nota)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@router.post("/{nota_id}/validar")
async def validar_nota_servico_endpoint(
    nota_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
):
    """Valida uma nota de serviço antes do envio."""
    nota = db.query(NotaServico).options(joinedload(NotaServico.itens)).filter(NotaServico.id == nota_id).first()
    if not nota:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nota de serviço não encontrada")
    erros = validar_nota_servico(db, nota)
    return {"valido": len(erros) == 0, "erros": erros}


@router.post("/{nota_id}/enviar")
async def enviar_nota_servico(
    nota_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    __: None = Depends(forbid_contador_edit),
):
    """Envia NFS-e ao provedor."""
    nota = db.query(NotaServico).filter(NotaServico.id == nota_id).first()
    if not nota:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nota de serviço não encontrada")
    svc = FiscalEmissaoService(db)
    sucesso, msg_erro, _ = svc.enviar_nfse(nota_id, usuario_id=current_user.id)
    if not sucesso:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg_erro or "Falha no envio")
    db.commit()
    nota = db.query(NotaServico).options(joinedload(NotaServico.itens)).filter(NotaServico.id == nota_id).first()
    return {"sucesso": True, "mensagem": "NFS-e enviada", "nota": NotaServicoResponse.model_validate(nota)}


@router.get("/{nota_id}/download/xml")
async def download_xml_nota_servico(
    nota_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: Usuario = Depends(require_permission("fiscal:baixar_xml")),
):
    """Baixa XML da NFS-e. Registra em fiscal_download_log."""
    nota = db.query(NotaServico).filter(NotaServico.id == nota_id).first()
    if not nota:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nota de serviço não encontrada")
    path = nota.xml_path
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo XML não disponível")
    log = FiscalDownloadLog(usuario_id=current_user.id, documento_tipo=DocTipoLog.NFSE, documento_id=nota.id, arquivo_tipo=ArquivoTipoLog.XML)
    db.add(log)
    db.commit()
    return FileResponse(path, media_type="application/xml", filename=f"nfse-{nota_id}.xml")


@router.get("/{nota_id}/download/pdf")
async def download_pdf_nota_servico(
    nota_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: Usuario = Depends(require_permission("fiscal:baixar_pdf")),
):
    """Baixa PDF da NFS-e. Registra em fiscal_download_log."""
    nota = db.query(NotaServico).filter(NotaServico.id == nota_id).first()
    if not nota:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nota de serviço não encontrada")
    path = getattr(nota, "pdf_path", None)
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo PDF não disponível")
    log = FiscalDownloadLog(usuario_id=current_user.id, documento_tipo=DocTipoLog.NFSE, documento_id=nota.id, arquivo_tipo=ArquivoTipoLog.PDF)
    db.add(log)
    db.commit()
    return FileResponse(path, media_type="application/pdf", filename=f"nfse-{nota_id}.pdf")


@router.post("/{nota_id}/cancelar", response_model=NotaServicoResponse)
async def cancelar_nota_servico(
    nota_id: int,
    justificativa: str = Query(..., min_length=15, description="Justificativa do cancelamento"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    __: None = Depends(forbid_contador_edit),
):
    """Cancela uma nota de serviço autorizada no provedor. Contador não pode cancelar."""
    try:
        nota = db.query(NotaServico).filter(NotaServico.id == nota_id).first()
        if not nota:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nota de serviço não encontrada")
        if nota.status != StatusNotaServicoEnum.AUTORIZADO:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Apenas notas de serviço autorizadas podem ser canceladas")
        svc = FiscalEmissaoService(db)
        sucesso, msg_erro = svc.cancelar_nfse(nota_id, motivo=justificativa, usuario_id=current_user.id)
        if not sucesso:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg_erro or "Falha no cancelamento")
        db.commit()
        db.refresh(nota)
        nota = db.query(NotaServico).options(joinedload(NotaServico.itens)).filter(NotaServico.id == nota.id).first()
        return NotaServicoResponse.model_validate(nota)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

