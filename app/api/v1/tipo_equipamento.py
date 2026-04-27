# PDV Ibix - API de TipoEquipamento
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.tipo_equipamento import TipoEquipamento
from app.schemas.tipo_equipamento import TipoEquipamentoCreate, TipoEquipamentoResponse, TipoEquipamentoUpdate

router = APIRouter(prefix="/tipo_equipamento", tags=["TipoEquipamento"])

@router.post("/", response_model=TipoEquipamentoResponse, status_code=status.HTTP_201_CREATED)
def criar_tipo_equipamento(
    tipo_equipamento: TipoEquipamentoCreate,
    db: Session = Depends(get_db)
):
    """Criar novo tipo de equipamento"""
    try:
        db_tipo_equipamento = TipoEquipamento(**tipo_equipamento.dict())
        db.add(db_tipo_equipamento)
        db.commit()
        db.refresh(db_tipo_equipamento)
        return db_tipo_equipamento
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar tipo de equipamento: {str(e)}"
        )

@router.get("/", response_model=List[TipoEquipamentoResponse])
def listar_tipos_equipamento(db: Session = Depends(get_db)):
    """Listar todos os tipos de equipamento"""
    try:
        tipos = db.query(TipoEquipamento).order_by(TipoEquipamento.tipo_equipamento).all()
        return tipos
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar tipos de equipamento: {str(e)}"
        )

@router.get("/{tipo_id}", response_model=TipoEquipamentoResponse)
def obter_tipo_equipamento(tipo_id: int, db: Session = Depends(get_db)):
    """Obter tipo de equipamento por ID"""
    tipo_equipamento = db.query(TipoEquipamento).filter(TipoEquipamento.id == tipo_id).first()
    
    if not tipo_equipamento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tipo de equipamento não encontrado"
        )
    
    return tipo_equipamento

@router.put("/{tipo_id}", response_model=TipoEquipamentoResponse)
def atualizar_tipo_equipamento(
    tipo_id: int,
    tipo_update: TipoEquipamentoUpdate,
    db: Session = Depends(get_db)
):
    """Atualizar tipo de equipamento"""
    try:
        db_tipo = db.query(TipoEquipamento).filter(TipoEquipamento.id == tipo_id).first()
        
        if not db_tipo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tipo de equipamento não encontrado"
            )
        
        update_data = tipo_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_tipo, field, value)
        
        db.commit()
        db.refresh(db_tipo)
        return db_tipo
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar tipo de equipamento: {str(e)}"
        )

@router.delete("/{tipo_id}", status_code=status.HTTP_200_OK)
def excluir_tipo_equipamento(tipo_id: int, db: Session = Depends(get_db)):
    """Excluir tipo de equipamento"""
    try:
        db_tipo = db.query(TipoEquipamento).filter(TipoEquipamento.id == tipo_id).first()
        
        if not db_tipo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tipo de equipamento não encontrado"
            )
        
        db.delete(db_tipo)
        db.commit()
        return {"message": "Tipo de equipamento excluído com sucesso"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao excluir tipo de equipamento: {str(e)}"
        )

