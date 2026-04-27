# PDV Ibix - Notificacoes do modulo Influencer
"""Envio de email e WhatsApp para eventos de influencers."""
from typing import Optional

from sqlalchemy.orm import Session

from ..core.logging import log_error

STATUS_MENSAGENS = {
    "teste": "Parabéns! Seu perfil foi aprovado para a fase de teste. Em breve você receberá sua primeira campanha.",
    "aprovado": "Você foi aprovado como Influencer Ibix! Faça login para ver suas campanhas e cupons.",
    "parceiro": "Você agora é Parceiro Ibix! Seu desempenho garantiu acesso a benefícios exclusivos.",
    "bloqueado": "Seu perfil de influencer foi temporariamente suspenso. Entre em contato para mais informações.",
    "pendente": "Seu perfil foi reativado e está em análise novamente.",
}


def notificar_cadastro_recebido(db: Session, divulgador, usuario_id: int) -> None:
    """Notifica influencer e admin sobre novo cadastro."""
    try:
        _enviar_email_influencer(
            db,
            destinatario_email=divulgador.email,
            assunto="Cadastro recebido — Programa de Influencers Ibix",
            corpo=(
                f"Olá {divulgador.nome},\n\n"
                "Recebemos seu cadastro no Programa de Influencers Ibix!\n\n"
                "Próximos passos:\n"
                "1. Vamos analisar seu perfil (até 48h)\n"
                "2. Você receberá uma notificação com o resultado\n"
                "3. Se aprovado, poderá fazer login e começar\n\n"
                "Obrigado por se interessar em fazer parte do nosso time!\n"
                "— Equipe Ibix"
            ),
        )
        if divulgador.telefone:
            _enviar_whatsapp_influencer(
                db,
                numero=divulgador.telefone,
                texto=(
                    f"Olá {divulgador.nome}! Recebemos seu cadastro no Programa de Influencers Ibix. "
                    "Vamos analisar seu perfil em até 48h. Fique atento ao seu email!"
                ),
                usuario_id=usuario_id,
            )
    except Exception as e:
        log_error(f"Erro ao notificar cadastro influencer: {e}")


def notificar_status_alterado(db: Session, divulgador, novo_status: str, admin_user_id: int) -> None:
    """Notifica influencer sobre mudanca de status."""
    msg = STATUS_MENSAGENS.get(novo_status, f"Seu status foi alterado para: {novo_status}")
    try:
        _enviar_email_influencer(
            db,
            destinatario_email=divulgador.email,
            assunto="Atualização do seu perfil — Influencers Ibix",
            corpo=f"Olá {divulgador.nome},\n\n{msg}\n\nAcesse: /login\n\n— Equipe Ibix",
        )
        if divulgador.telefone:
            _enviar_whatsapp_influencer(
                db, numero=divulgador.telefone,
                texto=f"Olá {divulgador.nome}! {msg}",
                usuario_id=admin_user_id,
            )
    except Exception as e:
        log_error(f"Erro ao notificar status influencer: {e}")


def notificar_nova_campanha(db: Session, divulgador, campanha, admin_user_id: int) -> None:
    """Notifica influencer sobre nova campanha atribuida."""
    tipo_label = {"propaganda": "Propaganda", "cupom": "Cupom de desconto", "live": "Live/Link"}.get(campanha.tipo, campanha.tipo)
    try:
        _enviar_email_influencer(
            db,
            destinatario_email=divulgador.email,
            assunto=f"Nova campanha: {campanha.titulo} — Influencers Ibix",
            corpo=(
                f"Olá {divulgador.nome},\n\n"
                f"Você recebeu uma nova campanha!\n\n"
                f"Título: {campanha.titulo}\n"
                f"Tipo: {tipo_label}\n"
                f"{'Período de teste' if campanha.is_teste else 'Campanha ativa'}\n\n"
                "Faça login para ver os detalhes e seus cupons/links.\n\n"
                "— Equipe Ibix"
            ),
        )
        if divulgador.telefone:
            _enviar_whatsapp_influencer(
                db, numero=divulgador.telefone,
                texto=(
                    f"Olá {divulgador.nome}! Você recebeu uma nova campanha: {campanha.titulo} ({tipo_label}). "
                    "Faça login para ver os detalhes!"
                ),
                usuario_id=admin_user_id,
            )
    except Exception as e:
        log_error(f"Erro ao notificar campanha influencer: {e}")


def _enviar_email_influencer(db: Session, destinatario_email: Optional[str], assunto: str, corpo: str) -> None:
    if not destinatario_email:
        return
    try:
        from .email_service import EmailService
        svc = EmailService(db=db)
        svc.send_email(
            to_email=destinatario_email,
            subject=assunto,
            body=corpo,
        )
    except Exception as e:
        log_error(f"Falha envio email influencer para {destinatario_email}: {e}")


def _enviar_whatsapp_influencer(db: Session, numero: str, texto: str, usuario_id: int) -> None:
    if not numero:
        return
    try:
        from .whatsapp_service import enviar_mensagem_whatsapp
        cleaned = numero.replace("(", "").replace(")", "").replace("-", "").replace(" ", "").replace("+", "")
        if not cleaned.startswith("55"):
            cleaned = "55" + cleaned
        enviar_mensagem_whatsapp(
            db=db,
            numero_destino=cleaned,
            texto=texto,
            usuario_id=usuario_id,
            incluir_prefixo=False,
        )
    except Exception as e:
        log_error(f"Falha envio WhatsApp influencer para {numero}: {e}")
