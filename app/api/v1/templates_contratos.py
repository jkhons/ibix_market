import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.middleware import get_current_user
from app.database.connection import get_db
from app.models.template_contrato import TemplateContrato, TipoContratoEnum
from app.models.usuario import Usuario
from app.schemas.template_contrato import (
    TemplateContratoCreate,
    TemplateContratoList,
    TemplateContratoResponse,
    TemplateContratoUpdate,
)

router = APIRouter()


@router.get("/", response_model=TemplateContratoList)
def listar_templates(
    skip: int = Query(0, ge=0, description="Número de registros a pular"),
    limit: int = Query(50, ge=1, le=10000, description="Limite de registros por página"),
    tipo: Optional[str] = Query(None, description="Filtrar por tipo de contrato"),
    ativo: Optional[bool] = Query(None, description="Filtrar por templates ativos/inativos"),
    busca: Optional[str] = Query(None, description="Buscar por nome ou descrição"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Lista todos os templates de contratos com filtros e paginação
    """
    query = db.query(TemplateContrato)
    
    # Aplicar filtros
    if tipo:
        try:
            tipo_enum = TipoContratoEnum(tipo)
            query = query.filter(TemplateContrato.tipo_contrato == tipo_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Tipo inválido: {tipo}")
    
    if ativo is not None:
        query = query.filter(TemplateContrato.ativo == ativo)
    
    if busca:
        busca_pattern = f"%{busca}%"
        query = query.filter(
            (TemplateContrato.nome.like(busca_pattern)) |
            (TemplateContrato.descricao.like(busca_pattern))
        )
    
    # Total de registros
    total = query.count()
    
    # Paginação
    templates = query.order_by(TemplateContrato.created_at.desc()) \
                    .offset(skip) \
                    .limit(limit) \
                    .all()
    
    total_paginas = math.ceil(total / limit) if total > 0 else 0
    pagina_atual = (skip // limit) + 1 if limit > 0 else 1
    
    return {
        "templates": templates,
        "total": total,
        "pagina": pagina_atual,
        "por_pagina": limit,
        "total_paginas": total_paginas
    }


@router.get("/{template_id}", response_model=TemplateContratoResponse)
def obter_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtém um template específico por ID
    """
    template = db.query(TemplateContrato).filter(TemplateContrato.id == template_id).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template não encontrado")
    
    return template


@router.post("/", response_model=TemplateContratoResponse, status_code=201)
def criar_template(
    template_data: TemplateContratoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Cria um novo template de contrato
    """
    # Verificar se já existe template com o mesmo nome
    template_existente = db.query(TemplateContrato).filter(
        TemplateContrato.nome == template_data.nome
    ).first()
    
    if template_existente:
        raise HTTPException(
            status_code=400, 
            detail="Já existe um template com este nome"
        )
    
    # Criar novo template
    novo_template = TemplateContrato(
        **template_data.model_dump(),
        created_by=current_user.id
    )
    
    db.add(novo_template)
    db.commit()
    db.refresh(novo_template)
    
    return novo_template


@router.patch("/{template_id}", response_model=TemplateContratoResponse)
def atualizar_template(
    template_id: int,
    template_data: TemplateContratoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Atualiza um template existente
    """
    template = db.query(TemplateContrato).filter(TemplateContrato.id == template_id).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template não encontrado")
    
    # Atualizar apenas campos fornecidos
    update_data = template_data.model_dump(exclude_unset=True)
    
    # Verificar nome duplicado se estiver sendo alterado
    if "nome" in update_data and update_data["nome"] != template.nome:
        template_existente = db.query(TemplateContrato).filter(
            TemplateContrato.nome == update_data["nome"],
            TemplateContrato.id != template_id
        ).first()
        
        if template_existente:
            raise HTTPException(
                status_code=400,
                detail="Já existe outro template com este nome"
            )
    
    # Aplicar atualizações
    for campo, valor in update_data.items():
        setattr(template, campo, valor)
    
    template.updated_by = current_user.id
    
    db.commit()
    db.refresh(template)
    
    return template


@router.delete("/{template_id}")
def excluir_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Exclui um template
    """
    template = db.query(TemplateContrato).filter(TemplateContrato.id == template_id).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template não encontrado")
    
    db.delete(template)
    db.commit()
    
    return {"message": "Template excluído com sucesso"}


@router.post("/{template_id}/duplicar", response_model=TemplateContratoResponse)
def duplicar_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Duplica um template existente
    """
    template_original = db.query(TemplateContrato).filter(
        TemplateContrato.id == template_id
    ).first()
    
    if not template_original:
        raise HTTPException(status_code=404, detail="Template não encontrado")
    
    # Criar novo template como cópia
    novo_nome = f"{template_original.nome} (Cópia)"
    
    # Verificar se o nome já existe e adicionar número
    contador = 1
    nome_final = novo_nome
    while db.query(TemplateContrato).filter(TemplateContrato.nome == nome_final).first():
        contador += 1
        nome_final = f"{novo_nome} {contador}"
    
    template_duplicado = TemplateContrato(
        nome=nome_final,
        descricao=template_original.descricao,
        conteudo=template_original.conteudo,
        tipo_contrato=template_original.tipo_contrato,
        ativo=True,
        created_by=current_user.id
    )
    
    db.add(template_duplicado)
    db.commit()
    db.refresh(template_duplicado)
    
    return template_duplicado

