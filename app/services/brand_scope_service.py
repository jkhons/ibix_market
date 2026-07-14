# PDV Ibix — Escopo de marca para tenants e marketplace (Fase 3.1)
from __future__ import annotations

from typing import Any, Optional

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.logging import log_security
from app.models.brand import Brand
from app.models.tenant import Tenant
from app.services.brand_service import brand_context_from_request, get_origin_brand, normalize_host, resolve_brand_by_host


def get_ibix_brand(db: Session) -> Brand:
    return get_origin_brand(db)


def get_ibix_brand_id(db: Session) -> int:
    return get_ibix_brand(db).id


def brand_id_from_request(request: Request, db: Session) -> int:
    brand = brand_context_from_request(request)
    if brand:
        return brand.id
    return get_ibix_brand_id(db)


def tenant_slug_exists(db: Session, slug: str, brand_id: int, *, exclude_tenant_id: Optional[int] = None) -> bool:
    if not slug:
        return False
    q = db.query(Tenant.id).filter(Tenant.slug == slug, Tenant.brand_id == brand_id)
    if exclude_tenant_id is not None:
        q = q.filter(Tenant.id != exclude_tenant_id)
    return q.first() is not None


def generate_unique_tenant_slug(
    db: Session,
    base_slug: str,
    brand_id: int,
    *,
    exclude_tenant_id: Optional[int] = None,
    max_len: int = 100,
) -> str:
    slug = (base_slug or "").strip()[:max_len]
    if not tenant_slug_exists(db, slug, brand_id, exclude_tenant_id=exclude_tenant_id):
        return slug
    suffix = 2
    while suffix < 10_000:
        candidate = f"{slug[: max_len - 4]}-{suffix}"[:max_len]
        if not tenant_slug_exists(db, candidate, brand_id, exclude_tenant_id=exclude_tenant_id):
            return candidate
        suffix += 1
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Não foi possível gerar slug único para o tenant nesta marca.",
    )


def assert_tenant_belongs_to_request_brand(db: Session, tenant: Tenant, request: Request) -> None:
    """403 se o tenant pertence a outra marca que a do Host atual."""
    expected_brand_id = brand_id_from_request(request, db)
    if tenant.brand_id != expected_brand_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant não pertence à marca deste domínio.",
        )


def assert_marketplace_ibix_brand(request: Request) -> None:
    """Marketplace/consumidor só na marca origem (Ibix). Defesa além do gating de módulo."""
    brand = brand_context_from_request(request)
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Marca não resolvida.",
        )
    if not brand.is_origem:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Marketplace disponível apenas na marca Ibix.",
        )


def assert_user_tenant_matches_request_brand(db: Session, user, request: Request) -> None:
    """Login PDV: usuário com tenant só acessa o domínio da sua marca."""
    tenant_id = getattr(user, "tenant_id", None)
    if not tenant_id:
        return
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant do usuário não encontrado.",
        )
    assert_tenant_belongs_to_request_brand(db, tenant, request)


def _brand_from_request_resolved(request: Request, db: Session):
    """Marca do request.state ou resolução direta pelo Host (defesa se middleware falhar)."""
    brand = brand_context_from_request(request)
    if brand:
        return brand
    host = normalize_host(request.headers.get("host"))
    if not host:
        return None
    try:
        return resolve_brand_by_host(db, host)
    except Exception:
        return None


def resolve_admin_brand_scope(
    request: Request,
    db: Session,
    brand_id: Optional[int] = None,
) -> Optional[int]:
    """
    Escopo de marca para APIs admin (Superadmin).
    Marca derivada (Solumática): sempre brand.id do Host; query cross-brand → 403.
    Marca origem (Ibix): brand_id na query ou None (visão global).
    """
    brand = _brand_from_request_resolved(request, db)
    if brand and not brand.is_origem:
        if brand_id is not None and brand_id != brand.id:
            log_security(
                "admin_brand_scope_denied",
                ip=request.client.host if request.client else "",
                details=f"host_brand={brand.id} requested_brand={brand_id}",
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Consulta cross-brand não permitida neste domínio.",
            )
        return brand.id
    if brand_id is not None:
        brand_row = db.query(Brand).filter(Brand.id == brand_id, Brand.ativo.is_(True)).first()
        if not brand_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Marca não encontrada ou inativa.",
            )
        return brand_id
    return None


def brand_scope_meta(
    request: Request,
    db: Session,
    effective_brand_id: Optional[int],
) -> dict[str, Any]:
    """Metadados de escopo para respostas JSON e templates."""
    brand = brand_context_from_request(request)
    if effective_brand_id is not None:
        if brand and brand.id == effective_brand_id:
            nome = brand.nome_exibicao or brand.nome_curto or brand.slug
        else:
            row = db.query(Brand).filter(Brand.id == effective_brand_id).first()
            nome = (row.nome_exibicao or row.slug) if row else str(effective_brand_id)
        scope_locked = brand is not None and not brand.is_origem
        return {
            "brand_id": effective_brand_id,
            "brand_nome": nome,
            "scope_locked": scope_locked,
            "scope_label": f"Dados: {nome}",
        }
    origin_nome = brand.nome_exibicao if brand else "Ibix"
    return {
        "brand_id": None,
        "brand_nome": None,
        "scope_locked": False,
        "scope_label": f"Visão global ({origin_nome})",
    }


def assert_usuario_in_admin_brand_scope(
    db: Session,
    usuario,
    request: Request,
) -> None:
    """403 se usuário não pertence a tenant da marca do escopo admin atual."""
    effective = resolve_admin_brand_scope(request, db)
    if effective is None:
        return
    tenant_id = getattr(usuario, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário fora do escopo desta marca.",
        )
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant or tenant.brand_id != effective:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário fora do escopo desta marca.",
        )


def assert_tenant_in_admin_brand_scope(
    db: Session,
    tenant: Tenant,
    request: Request,
    brand_id_query: Optional[int] = None,
) -> None:
    """403 se tenant não pertence ao escopo admin resolvido."""
    effective = resolve_admin_brand_scope(request, db, brand_id_query)
    if effective is None:
        return
    if tenant.brand_id != effective:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant fora do escopo desta marca.",
        )


def tenant_ids_for_admin_brand(db: Session, effective_brand_id: int) -> list[int]:
    """IDs de tenants da marca (escopo admin)."""
    return [
        row[0]
        for row in db.query(Tenant.id).filter(Tenant.brand_id == effective_brand_id).all()
    ]


def filter_usuario_query_by_admin_brand(query, effective_brand_id: Optional[int], db: Session):
    """
    Restringe query de Usuario à marca (marca derivada).
    Usa tenant_id IN — sem JOIN extra. Retorna (query, force_empty).
    """
    from app.models.usuario import Usuario

    if effective_brand_id is None:
        return query, False
    tenant_ids = tenant_ids_for_admin_brand(db, effective_brand_id)
    if not tenant_ids:
        return query, True
    return query.filter(Usuario.tenant_id.in_(tenant_ids)), False


def filter_user_ids_by_admin_brand(db: Session, user_ids: list[int], brand_id: int) -> list[int]:
    """Interseção de user_ids com usuários cujo tenant pertence à marca."""
    if not user_ids:
        return []
    from app.models.usuario import Usuario

    rows = (
        db.query(Usuario.id)
        .join(Tenant, Usuario.tenant_id == Tenant.id)
        .filter(Usuario.id.in_(user_ids), Tenant.brand_id == brand_id)
        .all()
    )
    return [row[0] for row in rows]


def apply_host_brand_cliente_scope(request: Request, db: Session, scope) -> "ClienteScope":
    """
    Restringe ClienteScope à marca do Host (marca derivada).
    Superadmin: só clientes dos tenants da marca. Demais roles: interseção com escopo existente.
    """
    from app.core.scope import ClienteScope, get_cliente_ids_for_brand

    effective = resolve_admin_brand_scope(request, db)
    if effective is None:
        return scope
    brand_client_ids = get_cliente_ids_for_brand(db, effective)
    if scope.is_superadmin or scope.see_all:
        return ClienteScope(allowed_ids=brand_client_ids, is_superadmin=False, see_all=False)
    if not scope.allowed_ids:
        return ClienteScope(allowed_ids=[], is_superadmin=False, see_all=False)
    brand_set = set(brand_client_ids)
    intersect = [cid for cid in scope.allowed_ids if cid in brand_set]
    return ClienteScope(allowed_ids=intersect, is_superadmin=False, see_all=False)
