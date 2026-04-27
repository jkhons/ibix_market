# PDV Ibix — política de quem pode alterar gateways em Recebíveis (por estabelecimento)
"""Chave em configuracoes: payment_lojas_gateway_self_service (true/false).
Vale para todos os gateways de Recebíveis: Mercado Pago, PagBank e Pagar.me (criar, editar, OAuth PagBank).
Quando false: apenas Superadministrador altera. Quando true: Cliente Administrador e Administrador como hoje."""
from sqlalchemy.orm import Session

from app.models import Configuracao, Usuario

CHAVE_PAYMENT_LOJAS_GATEWAY_SELF_SERVICE = "payment_lojas_gateway_self_service"

# Mensagem única para APIs (POST/PATCH configs, OAuth PagBank start, etc.)
HTTP_DETAIL_GATEWAY_SELF_SERVICE_DENIED = (
    "Integrações de gateway em Recebíveis (Mercado Pago, PagBank e Pagar.me) estão restritas ao "
    "Super Administrador. Em Admin → Billing → Config, marque «Liberado para lojas» para permitir "
    "que Cliente Administrador e Administrador criem ou editem configurações."
)


def payment_lojas_gateway_self_service_enabled(db: Session) -> bool:
    """
    Se a chave não existir ou estiver vazia → True (compatível com instalações antigas: lojas podem configurar).
    """
    row = db.query(Configuracao).filter(Configuracao.chave == CHAVE_PAYMENT_LOJAS_GATEWAY_SELF_SERVICE).first()
    if row is None or row.valor is None or not str(row.valor).strip():
        return True
    return str(row.valor).strip().lower() in ("true", "1", "yes", "sim", "on")


def user_may_mutate_establishment_gateway(db: Session, user: Usuario) -> bool:
    role = (user.role.nome if user.role else "") or ""
    if role == "Superadministrador":
        return True
    return payment_lojas_gateway_self_service_enabled(db)
