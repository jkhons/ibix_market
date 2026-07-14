# PDV Ibix - Escopo de clientes por role (Saas.md Fase 3)
"""
Retorna lista de cliente_id permitidos para o usuário.
Hierarquia: SA → AD (Administrador, gerencia seus CAs) → CA (Cliente Administrador = tenant, quem paga) → CF (cliente final, compra do CA).
Regra absoluta: quem emite a nota para o CF é o CA, via sua Empresa FISCAL (certificado). Nunca usar Empresa FISCAL de outro CA (isolamento multi-tenant).
"""

from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session


@dataclass
class ClienteScope:
    """Escopo de clientes para filtro em APIs."""
    allowed_ids: List[int]
    is_superadmin: bool
    see_all: bool = False  # True = Técnico (não filtrar por cliente)

    @property
    def has_scope(self) -> bool:
        return self.is_superadmin or self.see_all or len(self.allowed_ids) > 0

    def must_filter_by_cliente(self) -> bool:
        """Se False, a API não deve filtrar por cliente_id."""
        return not (self.is_superadmin or self.see_all)


def get_allowed_cliente_ids(
    db: Session,
    user_id: int,
    role_nome: Optional[str],
    cliente_id_from_token: Optional[int] = None,
) -> List[int]:
    """
    Lista de cliente_id que o usuário pode acessar.
    - Superadministrador: todos (retorno especial: lista vazia = não filtrar).
    - Administrador: IDs da tabela administrador_clientes; sem vínculo = [].
    - Cliente Administrador: IDs da tabela cliente_administrador_clientes.
    - Subcliente (role) ou usuário com AreaCliente: [cliente_id] do token/AreaCliente.
    - Técnico: IDs dos clientes do CA vinculado (cliente_administrador_tecnicos -> cliente_administrador_clientes); sem vínculo = [].
    """
    if not role_nome:
        # Fallback: se tem cliente_id no token (AreaCliente), restringe a um
        if cliente_id_from_token is not None:
            return [cliente_id_from_token]
        return []

    role = (role_nome or "").strip()

    if role == "Superadministrador":
        return []  # convenção: lista vazia + is_superadmin = não filtrar

    if role == "Administrador":
        r = db.execute(
            text("SELECT cliente_id FROM administrador_clientes WHERE usuario_id = :uid"),
            {"uid": user_id},
        )
        return [row[0] for row in r.fetchall()]

    if role == "Cliente Administrador":
        r = db.execute(
            text("SELECT cliente_id FROM cliente_administrador_clientes WHERE usuario_id = :uid"),
            {"uid": user_id},
        )
        ids = [row[0] for row in r.fetchall()]
        # Inclui o cliente "próprio" do CA (empresa fiscal), quando houver vínculo em AreaCliente.
        r_own = db.execute(
            text(
                "SELECT cliente_id FROM areas_cliente "
                "WHERE usuario_id = :uid AND ativo = true AND nome_area = 'administrador' "
                "ORDER BY id DESC LIMIT 1"
            ),
            {"uid": user_id},
        )
        own = r_own.fetchone()
        if own and own[0]:
            ids.append(own[0])
        # Mantém ordem e remove duplicados
        return list(dict.fromkeys(ids))

    if role == "Contador":
        # Contador só vê notas dos clientes do Cliente Administrador ao qual está vinculado
        r_ca = db.execute(
            text("SELECT contador_vinculado_cliente_administrador_id FROM usuarios WHERE id = :uid"),
            {"uid": user_id},
        )
        row_ca = r_ca.fetchone()
        ca_user_id = row_ca[0] if row_ca and row_ca[0] else None
        if not ca_user_id:
            return []  # sem vínculo = não vê nenhum cliente
        r = db.execute(
            text("SELECT cliente_id FROM cliente_administrador_clientes WHERE usuario_id = :uid"),
            {"uid": ca_user_id},
        )
        return [row[0] for row in r.fetchall()]

    if role == "Técnico":
        # Técnico vê apenas os clientes do Cliente Administrador ao qual está vinculado
        r_ca = db.execute(
            text(
                "SELECT usuario_id_cliente_admin FROM cliente_administrador_tecnicos WHERE usuario_id_tecnico = :uid LIMIT 1"
            ),
            {"uid": user_id},
        )
        row_ca = r_ca.fetchone()
        ca_user_id = row_ca[0] if row_ca and row_ca[0] else None
        if not ca_user_id:
            return []  # sem vínculo com CA = não vê nenhum cliente
        r = db.execute(
            text("SELECT cliente_id FROM cliente_administrador_clientes WHERE usuario_id = :uid"),
            {"uid": ca_user_id},
        )
        return [row[0] for row in r.fetchall()]

    if role == "Operador PDV":
        # Operador atua no terminal; escopo por estabelecimento pode ser via vínculo CA ou tabela operador_pdv (futuro)
        return []

    if role == "Subcliente" or cliente_id_from_token is not None:
        if cliente_id_from_token is not None:
            return [cliente_id_from_token]
        # Buscar AreaCliente do usuário
        r = db.execute(
            text(
                "SELECT cliente_id FROM areas_cliente WHERE usuario_id = :uid AND ativo = true LIMIT 1"
            ),
            {"uid": user_id},
        )
        row = r.fetchone()
        return [row[0]] if row else []

    # Visualizador, etc.: sem restrição por cliente (lista vazia)
    return []


def get_cliente_scope(
    db: Session,
    user_id: int,
    role_nome: Optional[str],
    cliente_id_from_token: Optional[int] = None,
) -> ClienteScope:
    """Retorna ClienteScope para uso nas APIs."""
    role = (role_nome or "").strip()
    allowed = get_allowed_cliente_ids(db, user_id, role_nome, cliente_id_from_token)
    is_superadmin = role == "Superadministrador"
    see_all = False  # Técnico passou a ter escopo por CA vinculado; não há mais role com "ver todos"
    return ClienteScope(allowed_ids=allowed, is_superadmin=is_superadmin, see_all=see_all)


def get_empresa_fiscal_cliente_id(
    db: Session,
    user_id: int,
    role_nome: Optional[str],
    cliente_id_from_token: Optional[int] = None,
) -> Optional[int]:
    """
    Retorna o cliente_id da empresa fiscal do usuário (estabelecimento emissor).
    Para CA: o cliente que tem Empresa vinculada ou o próprio (AreaCliente administrador).
    Para Admin/Super: primeiro do escopo que tenha Empresa; sem nenhum, primeiro do escopo.
    Usado em páginas que exigem contexto único de empresa fiscal (ex.: Entrada de Notas NFe).
    """
    from ..models.area_cliente import AreaCliente
    from ..models.empresa import Empresa

    allowed = get_allowed_cliente_ids(db, user_id, role_nome, cliente_id_from_token)
    role = (role_nome or "").strip()
    if role == "Superadministrador":
        # Super vê todos; retornar primeiro cliente que tenha Empresa (empresa fiscal)
        first_empresa = (
            db.query(Empresa.cliente_id)
            .filter(Empresa.cliente_id.isnot(None))
            .order_by(Empresa.id)
            .first()
        )
        return int(first_empresa[0]) if first_empresa and first_empresa[0] else None
    if not allowed:
        return None
    if role == "Administrador":
        ids_com_empresa = [
            r[0]
            for r in db.query(Empresa.cliente_id)
            .filter(
                Empresa.cliente_id.isnot(None),
                Empresa.cliente_id.in_(allowed),
            )
            .distinct()
            .all()
        ]
        if ids_com_empresa:
            return ids_com_empresa[0]
        return allowed[0]
    if role == "Cliente Administrador":
        # Empresa fiscal do CA = estabelecimento "próprio" (AreaCliente administrador) ou primeiro do escopo com Empresa
        area_own = db.query(AreaCliente.cliente_id).filter(
            AreaCliente.usuario_id == user_id,
            AreaCliente.ativo == True,
            AreaCliente.nome_area == "administrador",
        ).first()
        if area_own and area_own[0] and area_own[0] in allowed:
            return int(area_own[0])
        ids_com_empresa = {
            r[0]
            for r in db.query(Empresa.cliente_id)
            .filter(
                Empresa.cliente_id.isnot(None),
                Empresa.cliente_id.in_(allowed),
            )
            .distinct()
            .all()
        }
        for cid in allowed:
            if cid in ids_com_empresa:
                return cid
        return None
    # Subcliente, token com cliente_id, etc.: único no escopo já é o estabelecimento
    return allowed[0]


def get_empresa_fiscal_empresa(
    db: Session,
    user_id: int,
    role_nome: Optional[str],
    cliente_id_from_token: Optional[int] = None,
):
    """
    Retorna a Empresa FISCAL do CA (tenant) do usuário.
    Hierarquia: CA = Cliente Administrador = tenant (quem paga o sistema); CF = cliente final.
    Quem emite a nota para o CF é o CA, via sua Empresa FISCAL (certificado/CNPJ).
    Para CA: a Empresa cujo cliente_id é o estabelecimento próprio do CA.
    """
    from ..models.empresa import Empresa
    cid = get_empresa_fiscal_cliente_id(db, user_id, role_nome, cliente_id_from_token)
    if not cid:
        return None
    return db.query(Empresa).filter(
        Empresa.cliente_id == cid,
        Empresa.ativo == True,
    ).first()


def get_estabelecimento_cliente_id_da_venda(db: Session, venda_id: int):
    """
    Retorna o cliente_id do estabelecimento da venda.
    Ordem: venda.cliente_id -> empresa do turno de caixa -> primeiro item (produto do estabelecimento).
    Usado para garantir que a nota use a Empresa FISCAL do CA dono da venda.
    """
    from sqlalchemy.orm import joinedload

    from ..models.abertura_caixa import AberturaCaixa
    from ..models.caixa import Caixa
    from ..models.empresa import Empresa
    from ..models.produto_cliente import ProdutoCliente
    from ..models.venda import Venda
    venda = (
        db.query(Venda)
        .options(
            joinedload(Venda.abertura_caixa).joinedload(AberturaCaixa.caixa),
            joinedload(Venda.itens),
        )
        .filter(Venda.id == venda_id)
        .first()
    )
    if not venda:
        return None
    if getattr(venda, "cliente_id", None) is not None:
        return int(venda.cliente_id)
    if getattr(venda, "abertura_caixa_id", None):
        ab = getattr(venda, "abertura_caixa", None) or db.query(AberturaCaixa).filter(AberturaCaixa.id == venda.abertura_caixa_id).first()
        if ab:
            cx = getattr(ab, "caixa", None) or db.query(Caixa).filter(Caixa.id == ab.caixa_id).first()
            if cx:
                emp = db.query(Empresa).filter(Empresa.id == cx.empresa_id).first()
                if emp and getattr(emp, "cliente_id", None) is not None:
                    return int(emp.cliente_id)
    for vi in (getattr(venda, "itens", None) or []):
        if getattr(vi, "produto_cliente_id", None):
            pc = db.query(ProdutoCliente).filter(ProdutoCliente.id == vi.produto_cliente_id).first()
            if pc and getattr(pc, "cliente_id", None) is not None:
                return int(pc.cliente_id)
    return None


def get_empresa_fiscal_para_estabelecimento(
    db: Session,
    estabelecimento_cliente_id: int,
):
    """
    Retorna a Empresa FISCAL do CA (tenant) a que pertence o estabelecimento.

    Regra de negócio: quem emite a nota para o CF (cliente final) é sempre o CA
    (Cliente Administrador = tenant). O vínculo é a Empresa FISCAL (certificado/CNPJ).
    O estabelecimento (cliente_id) pertence a um CA; essa empresa é a do CA para
    aquele estabelecimento. Nunca usar Empresa FISCAL de outro CA (isolamento multi-tenant).
    """
    from ..models.empresa import Empresa
    if not estabelecimento_cliente_id:
        return None
    return db.query(Empresa).filter(
        Empresa.cliente_id == estabelecimento_cliente_id,
        Empresa.ativo == True,
    ).first()


def get_subcliente_scope_or_404(
    db: Session,
    user_id: int,
    role_nome: Optional[str],
    cliente_id_from_token: Optional[int] = None,
) -> ClienteScope:
    """
    Retorna ClienteScope para rotas do Portal Subcliente.
    Exige role Subcliente; se allowed_ids estiver vazio (sem vínculo), retorna None
    (caller deve retornar 404 ou tela "sem vínculo").
    """
    role = (role_nome or "").strip()
    if role != "Subcliente":
        return None  # caller deve verificar e retornar 403
    scope = get_cliente_scope(db, user_id, role_nome, cliente_id_from_token)
    return scope


def get_current_cliente_admin_id(db: Session, user_id: int, role_nome: Optional[str]) -> Optional[int]:
    """
    Retorna o usuario_id do Cliente Administrador (tenant) ao qual o usuário pertence.
    Usado para isolamento de dados por CA: produto/estoque pertence ao CA, não ao usuário.
    - Cliente Administrador: retorna user_id (ele é o CA).
    - Técnico: retorna usuario_id_cliente_admin do vínculo.
    - Contador: retorna contador_vinculado_cliente_administrador_id.
    - Superadministrador/Administrador/outros: retorna None (sem filtro por CA).
    """
    if not role_nome:
        return None
    role = (role_nome or "").strip()
    if role == "Cliente Administrador":
        return user_id
    if role == "Técnico":
        r = db.execute(
            text(
                "SELECT usuario_id_cliente_admin FROM cliente_administrador_tecnicos WHERE usuario_id_tecnico = :uid LIMIT 1"
            ),
            {"uid": user_id},
        )
        row = r.fetchone()
        return row[0] if row and row[0] else None
    if role == "Contador":
        r = db.execute(
            text("SELECT contador_vinculado_cliente_administrador_id FROM usuarios WHERE id = :uid"),
            {"uid": user_id},
        )
        row = r.fetchone()
        return row[0] if row and row[0] else None
    return None


def resolve_tenant_pagador(db: Session, user_id: int, role_nome: Optional[str]) -> Optional[int]:
    """
    Retorna o tenant_id cuja assinatura é paga pelo usuário (para billing).
    - Cliente Administrador: tenant_id do próprio usuário.
    - Técnico / Contador / Subcliente: tenant_id do CA ao qual estão vinculados.
    - Superadministrador / Administrador: None (não aplica bloqueio por assinatura).
    """
    if not role_nome:
        return None
    role = (role_nome or "").strip()
    if role == "Cliente Administrador":
        r = db.execute(text("SELECT tenant_id FROM usuarios WHERE id = :uid"), {"uid": user_id})
        row = r.fetchone()
        return row[0] if row and row[0] is not None else None
    ca_user_id = get_current_cliente_admin_id(db, user_id, role_nome)
    if not ca_user_id:
        return None
    r = db.execute(text("SELECT tenant_id FROM usuarios WHERE id = :uid"), {"uid": ca_user_id})
    row = r.fetchone()
    return row[0] if row and row[0] is not None else None


def resolve_tenant_id_from_cliente_id(db: Session, cliente_id: int) -> Optional[int]:
    """
    Retorna o tenant_id do CA que possui o cliente (para checagem de limite ao criar PDV).
    Cliente -> cliente_administrador_clientes.usuario_id -> usuarios.tenant_id.
    Retorna None se o cliente não estiver vinculado a nenhum CA com tenant.
    """
    r = db.execute(
        text(
            "SELECT u.tenant_id FROM cliente_administrador_clientes cac "
            "INNER JOIN usuarios u ON u.id = cac.usuario_id "
            "WHERE cac.cliente_id = :cid AND u.tenant_id IS NOT NULL LIMIT 1"
        ),
        {"cid": cliente_id},
    )
    row = r.fetchone()
    return row[0] if row and row[0] is not None else None


def get_cliente_ids_for_tenant(db: Session, tenant_id: int) -> List[int]:
    """
    Lista de cliente_id que pertencem ao tenant (todos os clientes dos CAs desse tenant).
    Alinhado à lógica de get_allowed_cliente_ids para Cliente Administrador, para que
    a contagem de PDVs (meus-limites e checagem ao criar PDV) seja idêntica.
    Inclui: cliente_administrador_clientes + areas_cliente (nome_area=administrador) dos usuários do tenant.
    """
    # Clientes via cliente_administrador_clientes (CAs do tenant)
    r = db.execute(
        text(
            "SELECT DISTINCT cac.cliente_id FROM cliente_administrador_clientes cac "
            "INNER JOIN usuarios u ON u.id = cac.usuario_id WHERE u.tenant_id = :tid"
        ),
        {"tid": tenant_id},
    )
    ids = [row[0] for row in r.fetchall()]
    # Cliente "próprio" do CA (areas_cliente administrador) para usuários do tenant
    r_own = db.execute(
        text(
            "SELECT ac.cliente_id FROM areas_cliente ac "
            "INNER JOIN usuarios u ON u.id = ac.usuario_id "
            "WHERE u.tenant_id = :tid AND ac.ativo = true AND ac.nome_area = 'administrador' "
            "ORDER BY ac.id DESC"
        ),
        {"tid": tenant_id},
    )
    for row in r_own.fetchall():
        if row[0]:
            ids.append(row[0])
    return list(dict.fromkeys(ids))


def get_cliente_ids_for_brand(db: Session, brand_id: int) -> List[int]:
    """Cliente IDs de todos os tenants da marca (relatórios/exportações multi-brand)."""
    from app.models.tenant import Tenant

    tenant_ids = [
        row[0]
        for row in db.query(Tenant.id).filter(Tenant.brand_id == brand_id).all()
    ]
    out: List[int] = []
    for tid in tenant_ids:
        out.extend(get_cliente_ids_for_tenant(db, tid))
    return list(dict.fromkeys(out))


def get_ca_ids_for_cliente_ids(db: Session, cliente_ids: List[int]) -> List[int]:
    """
    Retorna os usuario_id (CA) que possuem pelo menos um dos cliente_id em cliente_administrador_clientes.
    Usado para escopo por estabelecimento quando o usuário é Administrador (allowed_ids = clientes do admin).
    """
    if not cliente_ids:
        return []
    stmt = text(
        "SELECT DISTINCT usuario_id FROM cliente_administrador_clientes WHERE cliente_id IN :ids"
    ).bindparams(bindparam("ids", expanding=True))
    r = db.execute(stmt, {"ids": cliente_ids})
    return [row[0] for row in r.fetchall()]


def get_cliente_ids_escopo_caixa(
    db: Session,
    user_id: int,
    role_nome: Optional[str],
    scope: ClienteScope,
) -> Optional[List[int]]:
    """
    Cliente IDs cujos caixas (via empresa fiscal) o usuário pode acessar.
    None = sem filtro automático por cliente (Superadministrador; rota deve exigir empresa_id).
    Lista vazia = usuário sem escopo de caixa.
    """
    if not scope.must_filter_by_cliente():
        return None
    tenant_id = resolve_tenant_pagador(db, user_id, role_nome)
    if tenant_id is not None:
        ids = get_cliente_ids_for_tenant(db, tenant_id)
        if ids:
            return ids
    return list(scope.allowed_ids or [])


def caixa_ids_para_clientes(db: Session, cliente_ids: List[int]) -> List[int]:
    """IDs de caixas cujo emissor (empresa.cliente_id) está no escopo."""
    if not cliente_ids:
        return []
    from ..models.caixa import Caixa
    from ..models.empresa import Empresa

    rows = (
        db.query(Caixa.id)
        .join(Empresa, Caixa.empresa_id == Empresa.id)
        .filter(Empresa.cliente_id.in_(cliente_ids))
        .all()
    )
    return [r[0] for r in rows]
