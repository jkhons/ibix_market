# -*- coding: utf-8 -*-
"""
PDV Ibix - API Principal de Form Builder
Endpoint único centralizado para gerenciamento de templates de formulários
Adaptado para o contexto do PDV Ibix (processos, aferições, certificados)
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.logging import log_error
from app.core.middleware import get_current_user
from app.database.connection import get_db
from app.models.usuario import Usuario

# Importar renderizador centralizado
from app.services.form_builder_renderer import render_form, validate_form

router = APIRouter(
    prefix="/form-builder",
    tags=["Form Builder"]
)


# ============================================================================
# SCHEMAS
# ============================================================================

class TemplateSchema(BaseModel):
    """Schema de template de formulário"""
    id: Optional[int] = None
    nome: str = Field(..., description="Nome do template")
    descricao: Optional[str] = None
    tipo: str = Field(..., description="Tipo: processo, afericao, certificado")
    form_schema: Dict[str, Any] = Field(..., alias="schema_json", description="Schema JSON do template")
    ativo: bool = True
    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None


class TemplateCreate(BaseModel):
    """Schema para criação de template"""
    nome: str
    descricao: Optional[str] = None
    tipo: str
    form_schema: Dict[str, Any] = Field(..., alias="schema_json")


class TemplateUpdate(BaseModel):
    """Schema para atualização de template"""
    nome: Optional[str] = None
    descricao: Optional[str] = None
    tipo: Optional[str] = None
    form_schema: Optional[Dict[str, Any]] = Field(None, alias="schema_json")
    ativo: Optional[bool] = None


class TemplateResponse(BaseModel):
    """Schema de resposta de template"""
    id: int
    nome: str
    descricao: Optional[str]
    tipo: str
    form_schema: Dict[str, Any] = Field(..., alias="schema_json")
    ativo: bool
    criado_em: datetime
    atualizado_em: Optional[datetime]

    class Config:
        from_attributes = True
        populate_by_name = True


class RenderRequest(BaseModel):
    """Schema para requisição de renderização"""
    template_id: Optional[int] = None
    template_schema: Optional[Dict[str, Any]] = None
    dados: Optional[Dict[str, Any]] = None
    contexto: Optional[Dict[str, Any]] = None
    modo: str = Field(default="edicao", description="Modo: criacao, edicao, visualizacao")


class RenderResponse(BaseModel):
    """Schema de resposta de renderização"""
    html: str
    campos: List[Dict[str, Any]]
    validacoes: Dict[str, Any]


class ValidateRequest(BaseModel):
    """Schema para requisição de validação"""
    template_schema: Dict[str, Any]
    dados: Dict[str, Any]
    contexto: Optional[Dict[str, Any]] = None


class ValidateResponse(BaseModel):
    """Schema de resposta de validação"""
    valido: bool
    erros: List[Dict[str, Any]]


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/render", response_model=RenderResponse, status_code=status.HTTP_200_OK)
async def renderizar_formulario(
    request: RenderRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Renderiza formulário a partir de template
    
    - **template_id**: ID do template (opcional se template_schema fornecido)
    - **template_schema**: Schema JSON do template (opcional se template_id fornecido)
    - **dados**: Dados preenchidos do formulário
    - **contexto**: Contexto adicional (processo, aferição, etc.)
    - **modo**: Modo de renderização (criacao, edicao, visualizacao)
    """
    try:
        # Obter schema do template
        schema = None
        if request.template_id:
            # TODO: Buscar template do banco quando implementar persistência
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Busca por template_id ainda não implementada"
            )
        elif request.template_schema:
            schema = request.template_schema
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="template_id ou template_schema deve ser fornecido"
            )
        
        # Preparar contexto
        contexto = request.contexto or {}
        contexto["usuario"] = {
            "id": current_user.id,
            "email": current_user.email,
            "role": current_user.role.nome if current_user.role else None
        }
        
        # Renderizar formulário
        resultado = render_form(
            template_schema=schema,
            dados=request.dados or {},
            contexto=contexto,
            modo=request.modo
        )
        
        return RenderResponse(
            html=resultado.get("html", ""),
            campos=resultado.get("campos", []),
            validacoes=resultado.get("validacoes", {})
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log_error(f"Erro ao renderizar formulário: {e}", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao renderizar formulário: {str(e)}"
        )


@router.get("/templates", response_model=List[TemplateResponse], status_code=status.HTTP_200_OK)
async def listar_templates(
    tipo: Optional[str] = Query(None, description="Filtrar por tipo"),
    ativo: Optional[bool] = Query(None, description="Filtrar por status ativo"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Lista templates disponíveis
    
    - **tipo**: Filtrar por tipo (processo, afericao, certificado)
    - **ativo**: Filtrar por status ativo
    - **skip**: Número de registros para pular (paginação)
    - **limit**: Número máximo de registros a retornar
    """
    try:
        # TODO: Implementar busca no banco quando implementar persistência
        # Por enquanto, retornar lista vazia
        return []
        
    except Exception as e:
        log_error(f"Erro ao listar templates: {e}", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar templates: {str(e)}"
        )


@router.get("/templates/{template_id}", response_model=TemplateResponse, status_code=status.HTTP_200_OK)
async def obter_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtém template específico por ID
    """
    try:
        # TODO: Implementar busca no banco quando implementar persistência
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template {template_id} não encontrado"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log_error(f"Erro ao obter template: {e}", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter template: {str(e)}"
        )


@router.post("/templates", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def criar_template(
    template: TemplateCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Cria novo template
    """
    try:
        # TODO: Implementar criação no banco quando implementar persistência
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Criação de templates ainda não implementada"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log_error(f"Erro ao criar template: {e}", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar template: {str(e)}"
        )


@router.put("/templates/{template_id}", response_model=TemplateResponse, status_code=status.HTTP_200_OK)
async def atualizar_template(
    template_id: int,
    template: TemplateUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Atualiza template existente
    """
    try:
        # TODO: Implementar atualização no banco quando implementar persistência
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Atualização de templates ainda não implementada"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log_error(f"Erro ao atualizar template: {e}", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar template: {str(e)}"
        )


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Deleta template
    """
    try:
        # TODO: Implementar deleção no banco quando implementar persistência
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Deleção de templates ainda não implementada"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log_error(f"Erro ao deletar template: {e}", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao deletar template: {str(e)}"
        )


@router.post("/validate", response_model=ValidateResponse, status_code=status.HTTP_200_OK)
async def validar_formulario(
    request: ValidateRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Valida dados de formulário
    
    - **template_schema**: Schema JSON do template
    - **dados**: Dados a validar
    - **contexto**: Contexto adicional (opcional)
    """
    try:
        # Preparar contexto
        contexto = request.contexto or {}
        contexto["usuario"] = {
            "id": current_user.id,
            "email": current_user.email,
            "role": current_user.role.nome if current_user.role else None
        }
        
        # Validar formulário
        resultado = validate_form(
            template_schema=request.template_schema,
            dados=request.dados,
            contexto=contexto
        )
        
        return ValidateResponse(
            valido=resultado.get("valido", False),
            erros=resultado.get("erros", [])
        )
        
    except Exception as e:
        log_error(f"Erro ao validar formulário: {e}", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao validar formulário: {str(e)}"
        )
