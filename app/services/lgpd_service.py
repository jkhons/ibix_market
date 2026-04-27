# PDV Ibix - Service para conformidade LGPD do consumidor
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.auth import AuthConfig
from app.models.consumidor_consentimento import ConsumidorConsentimento
from app.models.consumidor_favorito import ConsumidorFavorito
from app.models.consumidor_marketplace import ConsumidorMarketplace
from app.models.consumidor_push_token import ConsumidorPushToken
from app.models.consumidor_refresh_token import ConsumidorRefreshToken
from app.models.endereco_consumidor import EnderecoConsumidor

TIPOS_CONSENTIMENTO = ["marketing", "analytics", "terceiros"]


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


def exportar_dados(db: Session, consumidor_id: int) -> dict:
    consumidor = db.query(ConsumidorMarketplace).filter(ConsumidorMarketplace.id == consumidor_id).first()
    if not consumidor:
        raise ValueError("CONSUMIDOR_NOT_FOUND")

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

    consumidor.deleted_at = datetime.now(timezone.utc) + timedelta(days=30)
    consumidor.ativo = False

    db.query(ConsumidorPushToken).filter(ConsumidorPushToken.consumidor_id == consumidor_id).update(
        {"ativo": False}, synchronize_session=False
    )
    db.query(ConsumidorRefreshToken).filter(
        ConsumidorRefreshToken.consumidor_id == consumidor_id,
        ConsumidorRefreshToken.revoked.is_(False),
    ).update({"revoked": True}, synchronize_session=False)

    db.commit()
