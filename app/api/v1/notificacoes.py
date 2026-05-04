# PDV Ibix - API de Notificações (sino do CA + compatibilidade NotificacaoLida)
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.core.logging import log_error
from app.core.middleware import get_current_user
from app.database.connection import get_db
from app.models.notificacao_lida import NotificacaoLida
from app.models.usuario import Usuario
from app.models.usuario_notificacao import UsuarioNotificacao

router = APIRouter(
    prefix="/api/v1/notificacoes",
    tags=["Notificações"],
)


def _serializar_ucca(row: UsuarioNotificacao) -> dict:
    return {
        "id": str(row.id),
        "titulo": row.titulo,
        "mensagem": row.mensagem,
        "link": row.link or "#",
        "lido": bool(row.lida),
        "icone": row.icone or "bell",
        "cor": row.cor or "info",
    }


@router.get("")
async def listar_notificacoes(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """
    Lista notificações do usuário logado (painel CA): inbox persistente + legado vazio.
    """
    try:
        rows = (
            db.query(UsuarioNotificacao)
            .filter(UsuarioNotificacao.usuario_id == current_user.id)
            .order_by(UsuarioNotificacao.created_at.desc())
            .limit(80)
            .all()
        )
        notificacoes = [_serializar_ucca(r) for r in rows]
        nao_lidas = sum(1 for r in rows if not r.lida)
        return {
            "notificacoes": notificacoes,
            "total": len(notificacoes),
            "nao_lidas": nao_lidas,
        }
    except Exception as e:
        log_error(f"Erro ao listar notificações: {e}")
        return {"notificacoes": [], "total": 0, "nao_lidas": 0}


@router.post("/{notificacao_id}/marcar-lido")
async def marcar_notificacao_lida(
    notificacao_id: str,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Marca uma notificação como lida (inbox CA ou legado NotificacaoLida)."""
    try:
        user_id = current_user.id

        if notificacao_id.isdigit():
            row = (
                db.query(UsuarioNotificacao)
                .filter(
                    UsuarioNotificacao.id == int(notificacao_id),
                    UsuarioNotificacao.usuario_id == user_id,
                )
                .first()
            )
            if row:
                row.lida = True
                row.lida_em = datetime.now(timezone.utc)
                db.commit()
                return {"success": True, "mensagem": "Notificação marcada como lida"}

        existe = (
            db.query(NotificacaoLida)
            .filter(
                and_(
                    NotificacaoLida.usuario_id == user_id,
                    NotificacaoLida.notificacao_id == notificacao_id,
                )
            )
            .first()
        )

        if not existe:
            partes = notificacao_id.split("_")
            tipo = f"{partes[0]}_{partes[1]}" if len(partes) >= 2 else "outro"
            if tipo not in ["certificado_vencendo", "contrato_vencendo"]:
                tipo = "outro"

            nova_lida = NotificacaoLida(
                usuario_id=user_id,
                notificacao_id=notificacao_id,
                tipo_notificacao=tipo,
                data_leitura=datetime.now(),
            )
            db.add(nova_lida)
            db.commit()

        return {"success": True, "mensagem": "Notificação marcada como lida"}

    except Exception as e:
        db.rollback()
        log_error(f"Erro ao marcar notificação como lida: {e}")
        return {"success": False, "mensagem": str(e)}


@router.delete("/{notificacao_id}")
async def remover_notificacao(
    notificacao_id: str,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Remove / dispensa notificação do inbox CA ou marca legado como lido."""
    try:
        user_id = current_user.id

        if notificacao_id.isdigit():
            row = (
                db.query(UsuarioNotificacao)
                .filter(
                    UsuarioNotificacao.id == int(notificacao_id),
                    UsuarioNotificacao.usuario_id == user_id,
                )
                .first()
            )
            if row:
                db.delete(row)
                db.commit()
                return {"success": True, "mensagem": "Notificação removida"}

        existe = (
            db.query(NotificacaoLida)
            .filter(
                and_(
                    NotificacaoLida.usuario_id == user_id,
                    NotificacaoLida.notificacao_id == notificacao_id,
                )
            )
            .first()
        )

        if not existe:
            partes = notificacao_id.split("_")
            tipo = f"{partes[0]}_{partes[1]}" if len(partes) >= 2 else "outro"
            if tipo not in ["certificado_vencendo", "contrato_vencendo"]:
                tipo = "outro"

            nova_lida = NotificacaoLida(
                usuario_id=user_id,
                notificacao_id=notificacao_id,
                tipo_notificacao=tipo,
                data_leitura=datetime.now(),
            )
            db.add(nova_lida)
            db.commit()

        return {"success": True, "mensagem": "Notificação removida"}

    except Exception as e:
        db.rollback()
        log_error(f"Erro ao remover notificação: {e}")
        return {"success": False, "mensagem": str(e)}
