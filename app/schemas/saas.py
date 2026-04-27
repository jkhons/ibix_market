# PDV Ibix - Schemas SaaS (Plan, Module, Tenant, Entitlement)
from datetime import date
from decimal import Decimal
from typing import Any, List, Optional

from pydantic import BaseModel, field_validator


def _decimal_to_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (int, float)):
        return float(v)
    return v


class PlanResponse(BaseModel):
    id: int
    nome: str
    slug: str
    descricao: Optional[str] = None
    preco: Optional[float] = None
    ativo: bool

    class Config:
        from_attributes = True

    @field_validator("preco", mode="before")
    @classmethod
    def preco_to_float(cls, v: Any) -> Optional[float]:
        return _decimal_to_float(v)


class ModuleResponse(BaseModel):
    id: int
    nome: str
    slug: str
    descricao: Optional[str] = None
    ativo: bool

    class Config:
        from_attributes = True


class TenantEntitlementResponse(BaseModel):
    module_id: int
    module_slug: str
    module_nome: str
    status: str
    limits: Optional[str] = None
    vigencia_inicio: Optional[date] = None
    vigencia_fim: Optional[date] = None

    class Config:
        from_attributes = True


class EntitlementsListResponse(BaseModel):
    tenant_id: Optional[int] = None
    entitlements: List[TenantEntitlementResponse]
