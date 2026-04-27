# PDV Ibix - API de MDF-e (Manifesto Eletrônico de Documentos Fiscais)
from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from ...core.middleware import forbid_cliente_access, get_current_user
from ...database.connection import get_db
from ...models.empresa import Empresa
from ...models.mdfe import MDFe, MDFeCondutor, MDFeDocumento, MDFePercurso, MDFeVeiculo
from ...models.usuario import Usuario
from ...schemas.mdfe import MDFeCreate, MDFeResponse, MDFeUpdate

router = APIRouter(
    prefix="/fiscal/mdfe",
    tags=["Fiscal - MDF-e"],
    dependencies=[Depends(forbid_cliente_access)]
)

@router.post("", response_model=MDFeResponse, status_code=status.HTTP_201_CREATED)
async def criar_mdfe(
    mdfe_data: MDFeCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Cria um novo MDF-e"""
    try:
        # Validar empresa
        empresa = db.query(Empresa).filter(Empresa.id == mdfe_data.empresa_id).first()
        if not empresa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Empresa não encontrada"
            )
        
        # Criar MDF-e
        mdfe_dict = mdfe_data.model_dump(exclude={'documentos', 'veiculos', 'condutores', 'percursos'})
        mdfe = MDFe(**mdfe_dict)
        db.add(mdfe)
        db.flush()
        
        # Criar documentos vinculados
        for doc_data in mdfe_data.documentos:
            doc_dict = doc_data.model_dump()
            documento = MDFeDocumento(**doc_dict, mdfe_id=mdfe.id)
            db.add(documento)
        
        # Criar veículos
        for veiculo_data in mdfe_data.veiculos:
            veiculo_dict = veiculo_data.model_dump()
            veiculo = MDFeVeiculo(**veiculo_dict, mdfe_id=mdfe.id)
            db.add(veiculo)
        
        # Criar condutores
        for condutor_data in mdfe_data.condutores:
            condutor_dict = condutor_data.model_dump()
            condutor = MDFeCondutor(**condutor_dict, mdfe_id=mdfe.id)
            db.add(condutor)
        
        # Criar percursos
        for percurso_data in mdfe_data.percursos:
            percurso_dict = percurso_data.model_dump()
            percurso = MDFePercurso(**percurso_dict, mdfe_id=mdfe.id)
            db.add(percurso)
        
        db.commit()
        db.refresh(mdfe)
        
        # Carregar relacionamentos para resposta
        mdfe = db.query(MDFe).options(
            joinedload(MDFe.documentos),
            joinedload(MDFe.veiculos),
            joinedload(MDFe.condutores),
            joinedload(MDFe.percursos)
        ).filter(MDFe.id == mdfe.id).first()
        
        return MDFeResponse.model_validate(mdfe)
        
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Erro ao criar MDF-e. Verifique os dados fornecidos."
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@router.get("", response_model=List[MDFeResponse])
async def listar_mdfes(
    empresa_id: Optional[int] = Query(None, description="Filtrar por empresa"),
    status: Optional[str] = Query(None, description="Filtrar por status"),
    uf_inicio: Optional[str] = Query(None, description="Filtrar por UF de início"),
    uf_fim: Optional[str] = Query(None, description="Filtrar por UF de fim"),
    data_inicio: Optional[date] = Query(None, description="Data inicial de emissão"),
    data_fim: Optional[date] = Query(None, description="Data final de emissão"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Lista MDF-es com filtros"""
    try:
        query = db.query(MDFe).options(
            joinedload(MDFe.documentos),
            joinedload(MDFe.veiculos),
            joinedload(MDFe.condutores),
            joinedload(MDFe.percursos)
        )
        
        if empresa_id:
            query = query.filter(MDFe.empresa_id == empresa_id)
        
        if status:
            query = query.filter(MDFe.status == status)
        
        if uf_inicio:
            query = query.filter(MDFe.uf_inicio == uf_inicio)
        
        if uf_fim:
            query = query.filter(MDFe.uf_fim == uf_fim)
        
        if data_inicio:
            query = query.filter(MDFe.data_emissao >= datetime.combine(data_inicio, datetime.min.time()))
        
        if data_fim:
            query = query.filter(MDFe.data_emissao <= datetime.combine(data_fim, datetime.max.time()))
        
        mdfes = query.order_by(MDFe.data_emissao.desc()).offset(skip).limit(limit).all()
        
        return [MDFeResponse.model_validate(mdfe) for mdfe in mdfes]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@router.get("/{mdfe_id}", response_model=MDFeResponse)
async def obter_mdfe(
    mdfe_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtém um MDF-e específico por ID"""
    try:
        mdfe = db.query(MDFe).options(
            joinedload(MDFe.documentos),
            joinedload(MDFe.veiculos),
            joinedload(MDFe.condutores),
            joinedload(MDFe.percursos)
        ).filter(MDFe.id == mdfe_id).first()
        
        if not mdfe:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="MDF-e não encontrado"
            )
        
        return MDFeResponse.model_validate(mdfe)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@router.put("/{mdfe_id}", response_model=MDFeResponse)
async def atualizar_mdfe(
    mdfe_id: int,
    mdfe_data: MDFeUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Atualiza um MDF-e existente"""
    try:
        mdfe = db.query(MDFe).filter(MDFe.id == mdfe_id).first()
        
        if not mdfe:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="MDF-e não encontrado"
            )
        
        # Verificar se pode ser atualizado
        from ...models.mdfe import StatusMDFeEnum
        if mdfe.status != StatusMDFeEnum.PENDENTE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Apenas MDF-es com status 'pendente' podem ser atualizados"
            )
        
        # Atualizar apenas campos fornecidos
        update_data = mdfe_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(mdfe, field, value)
        
        db.commit()
        db.refresh(mdfe)
        
        # Carregar relacionamentos para resposta
        mdfe = db.query(MDFe).options(
            joinedload(MDFe.documentos),
            joinedload(MDFe.veiculos),
            joinedload(MDFe.condutores),
            joinedload(MDFe.percursos)
        ).filter(MDFe.id == mdfe.id).first()
        
        return MDFeResponse.model_validate(mdfe)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@router.get("/chave/{chave_acesso}", response_model=MDFeResponse)
async def buscar_mdfe_por_chave_acesso(
    chave_acesso: str,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Busca MDF-e por chave de acesso"""
    try:
        mdfe = db.query(MDFe).options(
            joinedload(MDFe.documentos),
            joinedload(MDFe.veiculos),
            joinedload(MDFe.condutores),
            joinedload(MDFe.percursos)
        ).filter(MDFe.chave_acesso == chave_acesso).first()
        
        if not mdfe:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="MDF-e não encontrado"
            )
        
        return MDFeResponse.model_validate(mdfe)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@router.post("/{mdfe_id}/cancelar", response_model=MDFeResponse)
async def cancelar_mdfe(
    mdfe_id: int,
    justificativa: str = Query(..., min_length=15, description="Justificativa do cancelamento"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Cancela um MDF-e autorizado"""
    try:
        mdfe = db.query(MDFe).filter(MDFe.id == mdfe_id).first()
        
        if not mdfe:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="MDF-e não encontrado"
            )
        
        from ...models.mdfe import StatusMDFeEnum
        if mdfe.status != StatusMDFeEnum.AUTORIZADO:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Apenas MDF-es autorizados podem ser cancelados"
            )
        
        mdfe.status = StatusMDFeEnum.CANCELADO
        mdfe.mensagem_retorno = f"Cancelado: {justificativa}"
        
        db.commit()
        db.refresh(mdfe)
        
        # Carregar relacionamentos para resposta
        mdfe = db.query(MDFe).options(
            joinedload(MDFe.documentos),
            joinedload(MDFe.veiculos),
            joinedload(MDFe.condutores),
            joinedload(MDFe.percursos)
        ).filter(MDFe.id == mdfe.id).first()
        
        return MDFeResponse.model_validate(mdfe)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@router.post("/{mdfe_id}/encerrar", response_model=MDFeResponse)
async def encerrar_mdfe(
    mdfe_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Encerra um MDF-e autorizado"""
    try:
        mdfe = db.query(MDFe).filter(MDFe.id == mdfe_id).first()
        
        if not mdfe:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="MDF-e não encontrado"
            )
        
        from ...models.mdfe import StatusMDFeEnum
        if mdfe.status != StatusMDFeEnum.AUTORIZADO:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Apenas MDF-es autorizados podem ser encerrados"
            )
        
        mdfe.status = StatusMDFeEnum.ENCERRADO
        
        db.commit()
        db.refresh(mdfe)
        
        # Carregar relacionamentos para resposta
        mdfe = db.query(MDFe).options(
            joinedload(MDFe.documentos),
            joinedload(MDFe.veiculos),
            joinedload(MDFe.condutores),
            joinedload(MDFe.percursos)
        ).filter(MDFe.id == mdfe.id).first()
        
        return MDFeResponse.model_validate(mdfe)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

