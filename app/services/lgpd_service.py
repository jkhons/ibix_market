# PDV Ibix - Service para conformidade LGPD do consumidor
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.auth import AuthConfig
from app.core.pii import mask_cpf
from app.models.consumidor_consentimento import ConsumidorConsentimento
from app.models.consumidor_favorito import ConsumidorFavorito
from app.models.consumidor_marketplace import ConsumidorMarketplace
from app.models.consumidor_push_token import ConsumidorPushToken
from app.models.consumidor_refresh_token import ConsumidorRefreshToken
from app.models.endereco_consumidor import EnderecoConsumidor
from app.models.tenant import Tenant
from app.services.brand_scope_service import get_ibix_brand_id

TIPOS_CONSENTIMENTO = ["marketing", "analytics", "terceiros"]
LGPD_EXCLUSAO_DIAS = 30


def assert_consumidor_ibix_scope(db: Session, consumidor: ConsumidorMarketplace) -> None:
    """Consumidor marketplace pertence à marca Ibix (tenant.brand_id ou platform-wide)."""
    ibix_brand_id = get_ibix_brand_id(db)
    tenant_id = consumidor.tenant_id
    if tenant_id is None:
        return
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if tenant and tenant.brand_id != ibix_brand_id:
        raise ValueError("CONSUMIDOR_BRAND_SCOPE")


def get_consentimentos(db: Session, consumidor_id: int) -> List[dict]:
    existentes = (
        db.query(ConsumidorConsentimento)
        .filter(ConsumidorConsentimento.consumidor_id == consumidor_id)
        .all()
    )
    mapa = {c.tipo: c.aceito for c in existentes}
    return [{"tipo": t, "aceito": mapa.get(t, False)} for t in TIPOS_CONSENTIMENTO]


def update_consentimentos(
    db: Session,
    consumidor_id: int,
    ip: Optional[str],
    updates: List[dict],
) -> List[dict]:
    invalid_tipos = [item.get("tipo") for item in updates if item.get("tipo") not in TIPOS_CONSENTIMENTO]
    if invalid_tipos:
        raise ValueError(f"Tipos de consentimento inválidos: {', '.join(str(t) for t in invalid_tipos)}")

    for item in updates:
        tipo = item["tipo"]
        existente = (
            db.query(ConsumidorConsentimento)
            .filter(
                ConsumidorConsentimento.consumidor_id == consumidor_id,
                ConsumidorConsentimento.tipo == tipo,
            )
            .first()
        )
        if existente:
            existente.aceito = item["aceito"]
            existente.ip = ip
        else:
            novo = ConsumidorConsentimento(
                consumidor_id=consumidor_id,
                tipo=tipo,
                aceito=item["aceito"],
                ip=ip,
            )
            db.add(novo)
    db.commit()
    return get_consentimentos(db, consumidor_id)


def exportar_dados(db: Session, consumidor_id: int, *, brand_id: Optional[int] = None) -> dict:
    consumidor = db.query(ConsumidorMarketplace).filter(ConsumidorMarketplace.id == consumidor_id).first()
    if not consumidor:
        raise ValueError("CONSUMIDOR_NOT_FOUND")
    assert_consumidor_ibix_scope(db, consumidor)
    if brand_id is not None and consumidor.tenant_id:
        tenant = db.query(Tenant).filter(Tenant.id == consumidor.tenant_id).first()
        if not tenant or tenant.brand_id != brand_id:
            raise ValueError("CONSUMIDOR_BRAND_SCOPE")

    enderecos = db.query(EnderecoConsumidor).filter(EnderecoConsumidor.consumidor_id == consumidor_id).all()
    favoritos = db.query(ConsumidorFavorito).filter(ConsumidorFavorito.consumidor_id == consumidor_id).all()
    consentimentos = db.query(ConsumidorConsentimento).filter(ConsumidorConsentimento.consumidor_id == consumidor_id).all()

    from app.models.pedido_marketplace import PedidoMarketplace
    pedidos = db.query(PedidoMarketplace).filter(PedidoMarketplace.comprador_id == consumidor_id).all()

    from app.models.conversa_marketplace import ConversaMarketplace
    from app.models.mensagem_conversa import MensagemConversa
    conversas = db.query(ConversaMarketplace).filter(ConversaMarketplace.consumidor_id == consumidor_id).all()

    from app.models.consumidor_notificacao import ConsumidorNotificacao
    notificacoes = (
        db.query(ConsumidorNotificacao)
        .filter(ConsumidorNotificacao.consumidor_id == consumidor_id)
        .order_by(ConsumidorNotificacao.created_at.desc())
        .limit(500)
        .all()
    )

    return {
        "brand_scope": "ibix",
        "tenant_id": consumidor.tenant_id,
        "consumidor": {
            "id": consumidor.id,
            "nome": consumidor.nome,
            "email": consumidor.email,
            "telefone": consumidor.telefone,
            "documento": consumidor.documento,
            "tipo_pessoa": consumidor.tipo_pessoa,
            "created_at": consumidor.created_at.isoformat() if consumidor.created_at else None,
        },
        "enderecos": [
            {
                "apelido": e.apelido,
                "cep": e.cep,
                "logradouro": e.logradouro,
                "numero": e.numero,
                "complemento": e.complemento,
                "bairro": e.bairro,
                "cidade": e.cidade,
                "uf": e.uf,
            }
            for e in enderecos
        ],
        "pedidos": [
            {
                "id": p.id,
                "status": p.status_pedido,
                "valor_total": float(p.valor_total) if p.valor_total else None,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in pedidos
        ],
        "favoritos": [
            {"anuncio_id": f.anuncio_id, "created_at": f.created_at.isoformat() if f.created_at else None}
            for f in favoritos
        ],
        "conversas": [
            {
                "id": c.id,
                "loja_id": c.loja_id,
                "mensagens_count": db.query(MensagemConversa).filter(MensagemConversa.conversa_id == c.id).count(),
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in conversas
        ],
        "notificacoes_count": len(notificacoes),
        "consentimentos": [
            {"tipo": c.tipo, "aceito": c.aceito, "updated_at": c.updated_at.isoformat() if c.updated_at else None}
            for c in consentimentos
        ],
    }


def solicitar_exclusao(
    db: Session,
    consumidor_id: int,
    senha: str,
) -> None:
    consumidor = db.query(ConsumidorMarketplace).filter(ConsumidorMarketplace.id == consumidor_id).first()
    if not consumidor:
        raise ValueError("CONSUMIDOR_NOT_FOUND")
    if consumidor.senha_hash and not AuthConfig.verify_password(senha, consumidor.senha_hash):
        raise PermissionError("WRONG_PASSWORD")

    assert_consumidor_ibix_scope(db, consumidor)

    consumidor.deleted_at = datetime.now(timezone.utc) + timedelta(days=LGPD_EXCLUSAO_DIAS)
    consumidor.ativo = False

    db.query(ConsumidorPushToken).filter(ConsumidorPushToken.consumidor_id == consumidor_id).update(
        {"ativo": False}, synchronize_session=False
    )
    db.query(ConsumidorRefreshToken).filter(
        ConsumidorRefreshToken.consumidor_id == consumidor_id,
        ConsumidorRefreshToken.revoked.is_(False),
    ).update({"revoked": True}, synchronize_session=False)

    db.commit()


def purge_consumidores_exclusao_vencida(db: Session) -> int:
    """Anonimiza consumidores com deleted_at <= now (direito ao esquecimento). Retorna quantidade."""
    now = datetime.now(timezone.utc)
    rows = (
        db.query(ConsumidorMarketplace)
        .filter(
            ConsumidorMarketplace.deleted_at.isnot(None),
            ConsumidorMarketplace.deleted_at <= now,
        )
        .all()
    )
    count = 0
    for c in rows:
        cid = c.id
        c.nome = "Consumidor excluído"
        c.email = f"excluido_{cid}@anonymized.local"
        c.telefone = None
        c.documento = None
        c.senha_hash = None
        c.avatar_url = None
        c.ativo = False
        db.query(EnderecoConsumidor).filter(EnderecoConsumidor.consumidor_id == cid).delete(
            synchronize_session=False
        )
        db.query(ConsumidorFavorito).filter(ConsumidorFavorito.consumidor_id == cid).delete(
            synchronize_session=False
        )
        db.query(ConsumidorPushToken).filter(ConsumidorPushToken.consumidor_id == cid).delete(
            synchronize_session=False
        )
        db.query(ConsumidorRefreshToken).filter(ConsumidorRefreshToken.consumidor_id == cid).delete(
            synchronize_session=False
        )
        count += 1
    if count:
        db.commit()
    return count


def exportar_tenant_dados(db: Session, tenant_id: int, *, brand_id: Optional[int] = None) -> dict:
    """Exportação LGPD de tenant (Superadmin) — escopada por brand_id."""
    from app.models.usuario import Usuario

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise ValueError("TENANT_NOT_FOUND")
    if brand_id is not None and tenant.brand_id != brand_id:
        raise ValueError("TENANT_BRAND_SCOPE")

    usuarios = db.query(Usuario).filter(Usuario.tenant_id == tenant_id).all()
    return {
        "tenant": {
            "id": tenant.id,
            "nome": tenant.nome,
            "slug": tenant.slug,
            "brand_id": tenant.brand_id,
            "ativo": tenant.ativo,
        },
        "usuarios": [
            {
                "id": u.id,
                "nome": u.nome,
                "email": u.email,
                "cpf": mask_cpf(getattr(u, "cpf", None)),
                "ativo": u.ativo,
            }
            for u in usuarios
        ],
        "usuarios_total": len(usuarios),
    }


def solicitar_offboarding_tenant(db: Session, tenant_id: int, *, brand_id: Optional[int] = None) -> dict:
    """Desativa tenant para offboarding LGPD (não apaga dados fiscais/vendas)."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise ValueError("TENANT_NOT_FOUND")
    if brand_id is not None and tenant.brand_id != brand_id:
        raise ValueError("TENANT_BRAND_SCOPE")
    tenant.ativo = False
    db.commit()
    return {"tenant_id": tenant_id, "ativo": False, "mensagem": "Tenant desativado para offboarding LGPD."}
