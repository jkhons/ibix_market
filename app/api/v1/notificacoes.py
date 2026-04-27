# PDV Ibix - API de Notificações
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.core.logging import log_error
from app.core.middleware import get_current_user
from app.database.connection import get_db
from app.models.notificacao_lida import NotificacaoLida
from app.models.usuario import Usuario

router = APIRouter(
    prefix="/api/v1/notificacoes",
    tags=["Notificações"],
)

@router.get("")
async def listar_notificacoes(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """
    Lista notificações do usuário.
    Módulo de agendamentos removido - mantido para compatibilidade.
    """
    try:
        return {
            "notificacoes": [],
            "total": 0,
            "nao_lidas": 0
        }
    except Exception as e:
        log_error(f"Erro ao listar notificações: {e}")
        return {
            "notificacoes": [],
            "total": 0,
            "nao_lidas": 0
        }

@router.post("/{notificacao_id}/marcar-lido")
async def marcar_notificacao_lida(
    notificacao_id: str,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Marca uma notificação como lida no banco de dados"""
    try:
        user_id = current_user.id
        
        # Verificar se já existe
        existe = db.query(NotificacaoLida).filter(
            and_(
                NotificacaoLida.usuario_id == user_id,
                NotificacaoLida.notificacao_id == notificacao_id
            )
        ).first()
        
        if not existe:
            # Extrair tipo da notificação do ID
            partes = notificacao_id.split('_')
            tipo = f"{partes[0]}_{partes[1]}" if len(partes) >= 2 else 'outro'
            if tipo not in ['certificado_vencendo', 'contrato_vencendo']:
                tipo = 'outro'
            
            nova_lida = NotificacaoLida(
                usuario_id=user_id,
                notificacao_id=notificacao_id,
                tipo_notificacao=tipo,
                data_leitura=datetime.now()
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
    current_user: Usuario = Depends(get_current_user)
):
    """Remove uma notificação (marca como lida permanentemente)"""
    try:
        user_id = current_user.id
        
        # Marcar como lida (mesmo comportamento)
        existe = db.query(NotificacaoLida).filter(
            and_(
                NotificacaoLida.usuario_id == user_id,
                NotificacaoLida.notificacao_id == notificacao_id
            )
        ).first()
        
        if not existe:
            partes = notificacao_id.split('_')
            tipo = f"{partes[0]}_{partes[1]}" if len(partes) >= 2 else 'outro'
            if tipo not in ['certificado_vencendo', 'contrato_vencendo']:
                tipo = 'outro'
                
            nova_lida = NotificacaoLida(
                usuario_id=user_id,
                notificacao_id=notificacao_id,
                tipo_notificacao=tipo,
                data_leitura=datetime.now()
            )
            db.add(nova_lida)
            db.commit()
        
        return {"success": True, "mensagem": "Notificação removida"}
        
    except Exception as e:
        db.rollback()
        log_error(f"Erro ao remover notificação: {e}")
        return {"success": False, "mensagem": str(e)}

