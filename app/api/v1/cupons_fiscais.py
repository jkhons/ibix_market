# PDV Ibix - API de Cupons Fiscais (CF-e - SAT/MFe)
from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from ...core.middleware import forbid_cliente_access, get_current_user
from ...database.connection import get_db
from ...models.cliente import Cliente
from ...models.cupom_fiscal import CupomFiscal, CupomFiscalItem
from ...models.empresa import Empresa
from ...models.usuario import Usuario
from ...models.venda import Venda
from ...schemas.cupom_fiscal import CupomFiscalCreate, CupomFiscalResponse, CupomFiscalUpdate

router = APIRouter(
    prefix="/fiscal/cupons-fiscais",
    tags=["Fiscal - Cupons Fiscais"],
    dependencies=[Depends(forbid_cliente_access)]
)

@router.post("", response_model=CupomFiscalResponse, status_code=status.HTTP_201_CREATED)
async def criar_cupom_fiscal(
    cupom_data: CupomFiscalCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Cria um novo cupom fiscal (CF-e)"""
    try:
        # Validar empresa
        empresa = db.query(Empresa).filter(Empresa.id == cupom_data.empresa_id).first()
        if not empresa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Empresa não encontrada"
            )
        
        # Validar cliente se fornecido
        if cupom_data.cliente_id:
            cliente = db.query(Cliente).filter(Cliente.id == cupom_data.cliente_id).first()
            if not cliente:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Cliente não encontrado"
                )
        
        # Validar venda se fornecida
        if cupom_data.venda_id:
            venda = db.query(Venda).filter(Venda.id == cupom_data.venda_id).first()
            if not venda:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Venda não encontrada"
                )
        
        # Criar cupom fiscal
        cupom_dict = cupom_data.model_dump(exclude={'itens'})
        cupom = CupomFiscal(**cupom_dict)
        db.add(cupom)
        db.flush()
        
        # Criar itens
        for item_data in cupom_data.itens:
            item_dict = item_data.model_dump()
            item = CupomFiscalItem(**item_dict, cupom_fiscal_id=cupom.id)
            db.add(item)
        
        db.commit()
        db.refresh(cupom)
        
        # Carregar itens para resposta
        cupom = db.query(CupomFiscal).options(joinedload(CupomFiscal.itens)).filter(CupomFiscal.id == cupom.id).first()
        
        return CupomFiscalResponse.model_validate(cupom)
        
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Erro ao criar cupom fiscal. Verifique os dados fornecidos."
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@router.get("", response_model=List[CupomFiscalResponse])
async def listar_cupons_fiscais(
    empresa_id: Optional[int] = Query(None, description="Filtrar por empresa"),
    cliente_id: Optional[int] = Query(None, description="Filtrar por cliente"),
    venda_id: Optional[int] = Query(None, description="Filtrar por venda"),
    tipo_equipamento: Optional[str] = Query(None, description="Filtrar por tipo de equipamento (SAT ou MFe)"),
    status: Optional[str] = Query(None, description="Filtrar por status"),
    data_inicio: Optional[date] = Query(None, description="Data inicial de emissão"),
    data_fim: Optional[date] = Query(None, description="Data final de emissão"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Lista cupons fiscais com filtros"""
    try:
        query = db.query(CupomFiscal).options(joinedload(CupomFiscal.itens))
        
        if empresa_id:
            query = query.filter(CupomFiscal.empresa_id == empresa_id)
        
        if cliente_id:
            query = query.filter(CupomFiscal.cliente_id == cliente_id)
        
        if venda_id:
            query = query.filter(CupomFiscal.venda_id == venda_id)
        
        if tipo_equipamento:
            query = query.filter(CupomFiscal.tipo_equipamento == tipo_equipamento)
        
        if status:
            query = query.filter(CupomFiscal.status == status)
        
        if data_inicio:
            query = query.filter(CupomFiscal.data_emissao >= datetime.combine(data_inicio, datetime.min.time()))
        
        if data_fim:
            query = query.filter(CupomFiscal.data_emissao <= datetime.combine(data_fim, datetime.max.time()))
        
        cupons = query.order_by(CupomFiscal.data_emissao.desc()).offset(skip).limit(limit).all()
        
        return [CupomFiscalResponse.model_validate(cupom) for cupom in cupons]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@router.get("/{cupom_id}", response_model=CupomFiscalResponse)
async def obter_cupom_fiscal(
    cupom_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtém um cupom fiscal específico por ID"""
    try:
        cupom = db.query(CupomFiscal).options(joinedload(CupomFiscal.itens)).filter(CupomFiscal.id == cupom_id).first()
        
        if not cupom:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cupom fiscal não encontrado"
            )
        
        return CupomFiscalResponse.model_validate(cupom)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@router.put("/{cupom_id}", response_model=CupomFiscalResponse)
async def atualizar_cupom_fiscal(
    cupom_id: int,
    cupom_data: CupomFiscalUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Atualiza um cupom fiscal existente"""
    try:
        cupom = db.query(CupomFiscal).filter(CupomFiscal.id == cupom_id).first()
        
        if not cupom:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cupom fiscal não encontrado"
            )
        
        # Verificar se pode ser atualizado
        from ...models.cupom_fiscal import StatusCupomEnum
        if cupom.status != StatusCupomEnum.PENDENTE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Apenas cupons fiscais com status 'pendente' podem ser atualizados"
            )
        
        # Atualizar apenas campos fornecidos
        update_data = cupom_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(cupom, field, value)
        
        db.commit()
        db.refresh(cupom)
        
        # Carregar itens para resposta
        cupom = db.query(CupomFiscal).options(joinedload(CupomFiscal.itens)).filter(CupomFiscal.id == cupom.id).first()
        
        return CupomFiscalResponse.model_validate(cupom)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@router.post("/{cupom_id}/cancelar", response_model=CupomFiscalResponse)
async def cancelar_cupom_fiscal(
    cupom_id: int,
    justificativa: str = Query(..., min_length=15, description="Justificativa do cancelamento"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Cancela um cupom fiscal autorizado"""
    try:
        cupom = db.query(CupomFiscal).filter(CupomFiscal.id == cupom_id).first()
        
        if not cupom:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cupom fiscal não encontrado"
            )
        
        from ...models.cupom_fiscal import StatusCupomEnum
        if cupom.status != StatusCupomEnum.AUTORIZADO:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Apenas cupons fiscais autorizados podem ser cancelados"
            )
        
        cupom.status = StatusCupomEnum.CANCELADO
        cupom.mensagem_retorno = f"Cancelado: {justificativa}"
        
        db.commit()
        db.refresh(cupom)
        
        # Carregar itens para resposta
        cupom = db.query(CupomFiscal).options(joinedload(CupomFiscal.itens)).filter(CupomFiscal.id == cupom.id).first()
        
        return CupomFiscalResponse.model_validate(cupom)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

