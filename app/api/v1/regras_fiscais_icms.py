# PDV Ibix - API de Regras Fiscais ICMS
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from ...core.middleware import forbid_cliente_access, get_cliente_scope_dep, get_current_user
from ...core.redis_cache import invalidate_regras_fiscais_empresa
from ...core.scope import ClienteScope
from ...database.connection import get_db
from ...models.empresa import Empresa
from ...models.regra_fiscal_icms import (
    RegraFiscalIcms,
    TipoDestinatarioFiscalEnum,
    TipoOperacaoFiscalEnum,
)
from ...models.usuario import Usuario
from ...schemas.regra_fiscal_icms import (
    RegraFiscalIcmsCreate,
    RegraFiscalIcmsResponse,
    RegraFiscalIcmsUpdate,
)

router = APIRouter(
    prefix="/fiscal/regras-fiscais-icms",
    tags=["Fiscal - Regras Fiscais ICMS"],
    dependencies=[Depends(forbid_cliente_access)],
)

LISTA_LIMITE_MAX = 500


def _scope_allows_empresa(scope: ClienteScope, empresa: Empresa) -> bool:
    """Verifica se o escopo do usuário permite acessar a empresa."""
    if scope.is_superadmin or scope.see_all:
        return True
    if empresa.cliente_id is None:
        return True
    return empresa.cliente_id in scope.allowed_ids


def _converter_regra_para_response(regra: RegraFiscalIcms) -> dict:
    """Converte RegraFiscalIcms para dict compatível com RegraFiscalIcmsResponse."""
    return {
        "id": regra.id,
        "empresa_id": regra.empresa_id,
        "ativo": regra.ativo,
        "ordem_prioridade": regra.ordem_prioridade,
        "crt": regra.crt,
        "tipo_operacao": regra.tipo_operacao.value if regra.tipo_operacao else None,
        "tipo_destinatario": regra.tipo_destinatario.value if regra.tipo_destinatario else None,
        "uf_destinatario": regra.uf_destinatario,
        "ncm_prefix": regra.ncm_prefix,
        "ncm_exato": regra.ncm_exato,
        "cest": regra.cest,
        "cfop_filtro": regra.cfop_filtro,
        "finalidade_emissao": regra.finalidade_emissao,
        "consumidor_final": regra.consumidor_final,
        "contribuinte_icms": regra.contribuinte_icms,
        "vigencia_inicio": regra.vigencia_inicio,
        "vigencia_fim": regra.vigencia_fim,
        "observacao_interna": regra.observacao_interna,
        "cfop": regra.cfop,
        "origem_mercadoria": regra.origem_mercadoria,
        "cst_icms": regra.cst_icms,
        "csosn": regra.csosn,
        "aliquota_icms": regra.aliquota_icms,
        "modalidade_bc_icms": regra.modalidade_bc_icms,
        "percentual_reducao_bc": regra.percentual_reducao_bc,
        "gera_icms_st": regra.gera_icms_st,
        "aliquota_icms_st": regra.aliquota_icms_st,
        "modalidade_bc_icms_st": regra.modalidade_bc_icms_st,
        "percentual_mva_st": regra.percentual_mva_st,
        "permite_credito_icms": regra.permite_credito_icms,
        "created_at": regra.created_at,
        "updated_at": regra.updated_at,
    }


@router.get("", response_model=List[RegraFiscalIcmsResponse])
async def listar_regras_fiscais_icms(
    empresa_id: Optional[int] = Query(None, description="Filtrar por empresa"),
    ativo: Optional[bool] = Query(None, description="Filtrar por ativo"),
    crt: Optional[int] = Query(None, ge=1, le=3, description="Filtrar por CRT"),
    tipo_operacao: Optional[str] = Query(None, description="Filtrar por tipo de operação"),
    limit: int = Query(LISTA_LIMITE_MAX, ge=1, le=500, description="Limite de registros"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Lista regras fiscais ICMS. Filtro por escopo (empresas acessíveis)."""
    query = (
        db.query(RegraFiscalIcms)
        .options(joinedload(RegraFiscalIcms.empresa))
        .join(Empresa, RegraFiscalIcms.empresa_id == Empresa.id)
    )

    if scope.must_filter_by_cliente() and scope.allowed_ids:
        query = query.filter(Empresa.cliente_id.in_(scope.allowed_ids))
    elif scope.must_filter_by_cliente() and not scope.allowed_ids:
        query = query.filter(RegraFiscalIcms.id == -1)

    if empresa_id is not None:
        query = query.filter(RegraFiscalIcms.empresa_id == empresa_id)
    if ativo is not None:
        query = query.filter(RegraFiscalIcms.ativo == ativo)
    if crt is not None:
        query = query.filter(RegraFiscalIcms.crt == crt)
    if tipo_operacao:
        try:
            tipo_enum = TipoOperacaoFiscalEnum(tipo_operacao.strip().lower())
            query = query.filter(RegraFiscalIcms.tipo_operacao == tipo_enum)
        except ValueError:
            pass

    regras = query.order_by(RegraFiscalIcms.empresa_id, RegraFiscalIcms.ordem_prioridade).limit(limit).all()

    return [RegraFiscalIcmsResponse(**_converter_regra_para_response(r)) for r in regras]


@router.get("/{regra_id}", response_model=RegraFiscalIcmsResponse)
async def obter_regra_fiscal_icms(
    regra_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Obtém regra fiscal por ID (respeitando escopo)."""
    regra = (
        db.query(RegraFiscalIcms)
        .options(joinedload(RegraFiscalIcms.empresa))
        .filter(RegraFiscalIcms.id == regra_id)
        .first()
    )
    if not regra:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Regra não encontrada")
    if not _scope_allows_empresa(scope, regra.empresa):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Regra não encontrada")
    return RegraFiscalIcmsResponse(**_converter_regra_para_response(regra))


def _dict_para_modelo(data: dict) -> dict:
    """Converte enums do Pydantic para valores do modelo SQLAlchemy."""
    out = dict(data)
    if "tipo_operacao" in out and out["tipo_operacao"] is not None:
        if hasattr(out["tipo_operacao"], "value"):
            out["tipo_operacao"] = TipoOperacaoFiscalEnum(out["tipo_operacao"].value)
        else:
            try:
                out["tipo_operacao"] = TipoOperacaoFiscalEnum(str(out["tipo_operacao"]))
            except ValueError:
                out["tipo_operacao"] = None
    if "tipo_destinatario" in out and out["tipo_destinatario"] is not None:
        if hasattr(out["tipo_destinatario"], "value"):
            out["tipo_destinatario"] = TipoDestinatarioFiscalEnum(out["tipo_destinatario"].value)
        else:
            try:
                out["tipo_destinatario"] = TipoDestinatarioFiscalEnum(str(out["tipo_destinatario"]))
            except ValueError:
                out["tipo_destinatario"] = None
    return out


@router.post("", response_model=RegraFiscalIcmsResponse, status_code=status.HTTP_201_CREATED)
async def criar_regra_fiscal_icms(
    regra_data: RegraFiscalIcmsCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Cria nova regra fiscal ICMS."""
    empresa = db.query(Empresa).filter(Empresa.id == regra_data.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada")
    if not _scope_allows_empresa(scope, empresa):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Empresa fora do seu escopo")

    try:
        d = regra_data.model_dump()
        d = _dict_para_modelo(d)
        regra = RegraFiscalIcms(**d)
        db.add(regra)
        db.commit()
        db.refresh(regra)
        db.refresh(regra, ["empresa"])
        invalidate_regras_fiscais_empresa(regra.empresa_id)
        return RegraFiscalIcmsResponse(**_converter_regra_para_response(regra))
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Erro ao criar regra. Verifique os dados.")


@router.put("/{regra_id}", response_model=RegraFiscalIcmsResponse)
async def atualizar_regra_fiscal_icms(
    regra_id: int,
    regra_data: RegraFiscalIcmsUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Atualiza regra fiscal ICMS."""
    regra = (
        db.query(RegraFiscalIcms)
        .options(joinedload(RegraFiscalIcms.empresa))
        .filter(RegraFiscalIcms.id == regra_id)
        .first()
    )
    if not regra:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Regra não encontrada")
    if not _scope_allows_empresa(scope, regra.empresa):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Regra não encontrada")

    try:
        d = regra_data.model_dump(exclude_unset=True)
        d = _dict_para_modelo(d)
        for k, v in d.items():
            setattr(regra, k, v)
        db.commit()
        db.refresh(regra)
        invalidate_regras_fiscais_empresa(regra.empresa_id)
        return RegraFiscalIcmsResponse(**_converter_regra_para_response(regra))
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Erro ao atualizar regra.")


@router.delete("/{regra_id}", status_code=status.HTTP_204_NO_CONTENT)
async def excluir_regra_fiscal_icms(
    regra_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Exclui regra fiscal ICMS."""
    regra = (
        db.query(RegraFiscalIcms)
        .options(joinedload(RegraFiscalIcms.empresa))
        .filter(RegraFiscalIcms.id == regra_id)
        .first()
    )
    if not regra:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Regra não encontrada")
    if not _scope_allows_empresa(scope, regra.empresa):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Regra não encontrada")
    empresa_id = regra.empresa_id
    db.delete(regra)
    db.commit()
    invalidate_regras_fiscais_empresa(empresa_id)
