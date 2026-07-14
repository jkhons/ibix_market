# PDV Ibix - Hierarquia completa do sistema (Superadmin)
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session, joinedload

from app.core.middleware import require_superadmin
from app.core.scope import get_cliente_ids_for_brand
from app.database.connection import get_db
from app.models import Tenant, Usuario
from app.models.administrador_cliente import AdministradorCliente
from app.models.administrador_cliente_administrador import AdministradorClienteAdministrador
from app.models.cliente import Cliente
from app.models.cliente_administrador_cliente import ClienteAdministradorCliente
from app.models.cliente_administrador_tecnico import ClienteAdministradorTecnico
from app.models.role import Role
from app.models.subscription_billing import SubscriptionBilling
from app.services.brand_scope_service import brand_scope_meta, resolve_admin_brand_scope

router = APIRouter(prefix="/admin/hierarquia", tags=["Admin - Hierarquia"])


@router.get("", dependencies=[Depends(require_superadmin())])
def hierarquia_completa(request: Request, db: Session = Depends(get_db)):
    """Retorna árvore completa: Tenants → Usuários (por role) → Vínculos."""

    effective_brand = resolve_admin_brand_scope(request, db)

    tenants_q = db.query(Tenant).order_by(Tenant.id)
    if effective_brand is not None:
        tenants_q = tenants_q.filter(Tenant.brand_id == effective_brand)
    tenants = tenants_q.all()
    tenant_ids = {t.id for t in tenants}

    usuarios_q = (
        db.query(Usuario)
        .options(joinedload(Usuario.role))
        .order_by(Usuario.id)
    )
    if effective_brand is not None:
        if not tenant_ids:
            usuarios = []
        else:
            usuarios = usuarios_q.filter(Usuario.tenant_id.in_(tenant_ids)).all()
    else:
        usuarios = usuarios_q.all()

    usuario_ids = {u.id for u in usuarios}

    if effective_brand is not None:
        allowed_cliente_ids = set(get_cliente_ids_for_brand(db, effective_brand))
        clientes = (
            db.query(Cliente)
            .filter(Cliente.id.in_(allowed_cliente_ids))
            .order_by(Cliente.id)
            .all()
            if allowed_cliente_ids
            else []
        )
    else:
        clientes = db.query(Cliente).order_by(Cliente.id).all()

    roles = db.query(Role).filter(Role.ativo == True).order_by(Role.id).all()  # noqa: E712

    if effective_brand is not None:
        subs = (
            db.query(SubscriptionBilling)
            .filter(SubscriptionBilling.tenant_id.in_(tenant_ids))
            .all()
            if tenant_ids
            else []
        )
    else:
        subs = db.query(SubscriptionBilling).all()

    admin_clientes = db.query(AdministradorCliente).all()
    ca_clientes = db.query(ClienteAdministradorCliente).all()
    ca_tecnicos = db.query(ClienteAdministradorTecnico).all()
    admin_cas = db.query(AdministradorClienteAdministrador).all()

    if effective_brand is not None:
        allowed_cliente_ids = {c.id for c in clientes}
        admin_clientes = [ac for ac in admin_clientes if ac.usuario_id in usuario_ids and ac.cliente_id in allowed_cliente_ids]
        ca_clientes = [cc for cc in ca_clientes if cc.usuario_id in usuario_ids and cc.cliente_id in allowed_cliente_ids]
        ca_tecnicos = [
            ct for ct in ca_tecnicos
            if ct.usuario_id_cliente_admin in usuario_ids and ct.usuario_id_tecnico in usuario_ids
        ]
        admin_cas = [
            aca for aca in admin_cas
            if aca.usuario_id_administrador in usuario_ids
            and aca.usuario_id_cliente_administrador in usuario_ids
        ]

    cliente_map = {c.id: {"id": c.id, "nome": c.nome, "cnpj": c.cnpj, "cidade": c.cidade, "uf": c.uf} for c in clientes}
    usuario_map = {u.id: u for u in usuarios}
    sub_map = {s.tenant_id: s for s in subs}

    admin_to_clientes = {}
    for ac in admin_clientes:
        admin_to_clientes.setdefault(ac.usuario_id, []).append(ac.cliente_id)

    admin_to_cas = {}
    for aca in admin_cas:
        admin_to_cas.setdefault(aca.usuario_id_administrador, []).append(aca.usuario_id_cliente_administrador)

    ca_to_clientes = {}
    for cc in ca_clientes:
        ca_to_clientes.setdefault(cc.usuario_id, []).append(cc.cliente_id)

    ca_to_tecnicos = {}
    for ct in ca_tecnicos:
        ca_to_tecnicos.setdefault(ct.usuario_id_cliente_admin, []).append(ct.usuario_id_tecnico)

    def user_brief(u):
        return {
            "id": u.id,
            "nome": u.nome,
            "email": u.email,
            "cargo": u.cargo,
            "ativo": u.ativo,
            "role": u.role.nome if u.role else None,
        }

    tenant_tree = []
    orphan_users = []

    for t in tenants:
        sub = sub_map.get(t.id)
        t_users = [u for u in usuarios if u.tenant_id == t.id]
        roles_agrupados = {}

        for u in t_users:
            role_nome = u.role.nome if u.role else "Sem Role"
            entry = user_brief(u)

            if role_nome == "Administrador":
                entry["clientes_vinculados"] = [
                    cliente_map[cid] for cid in admin_to_clientes.get(u.id, []) if cid in cliente_map
                ]
                ca_ids = admin_to_cas.get(u.id, [])
                entry["cas_vinculados"] = []
                for ca_id in ca_ids:
                    ca_user = usuario_map.get(ca_id)
                    if ca_user:
                        entry["cas_vinculados"].append(user_brief(ca_user))

            elif role_nome == "Cliente Administrador":
                entry["clientes_vinculados"] = [
                    cliente_map[cid] for cid in ca_to_clientes.get(u.id, []) if cid in cliente_map
                ]
                tec_ids = ca_to_tecnicos.get(u.id, [])
                entry["tecnicos_vinculados"] = []
                for tid in tec_ids:
                    tec = usuario_map.get(tid)
                    if tec:
                        entry["tecnicos_vinculados"].append(user_brief(tec))

            elif role_nome == "Contador":
                ca_ref = u.contador_vinculado_cliente_administrador_id
                if ca_ref:
                    ca_user = usuario_map.get(ca_ref)
                    entry["vinculado_a_ca"] = user_brief(ca_user) if ca_user else {"id": ca_ref}

            roles_agrupados.setdefault(role_nome, []).append(entry)

        tenant_tree.append({
            "id": t.id,
            "nome": t.nome,
            "slug": t.slug,
            "ativo": t.ativo,
            "subscription": {
                "status": sub.status if sub else "sem_assinatura",
                "period_end": str(sub.period_end) if sub and sub.period_end else None,
                "qtd_pdvs": sub.qtd_pdvs_contratados if sub else 0,
            } if sub else None,
            "usuarios_por_role": roles_agrupados,
            "total_usuarios": len(t_users),
        })

    if effective_brand is None:
        for u in usuarios:
            if u.tenant_id is None:
                orphan_users.append(user_brief(u))

    role_counts = {}
    for u in usuarios:
        rn = u.role.nome if u.role else "Sem Role"
        role_counts[rn] = role_counts.get(rn, 0) + 1

    return {
        "brand_scope": brand_scope_meta(request, db, effective_brand),
        "tenants": tenant_tree,
        "orphan_users": orphan_users,
        "stats": {
            "total_tenants": len(tenants),
            "total_usuarios": len(usuarios),
            "total_clientes": len(clientes),
            "total_roles": len(roles),
            "usuarios_por_role": role_counts,
        },
        "roles": [{"id": r.id, "nome": r.nome} for r in roles],
    }
