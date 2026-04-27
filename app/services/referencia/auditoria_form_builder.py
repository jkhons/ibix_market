# -*- coding: utf-8 -*-
"""
REFERÊNCIA DO CERTILOG - Serviço de Auditoria do Form Builder
Este arquivo é uma cópia de referência do sistema Certilog.
Não deve ser usado diretamente no PDV Ibix.
Adaptar conforme necessário para implementação futura.

Serviço de Auditoria do Form Builder
Registra alterações granulares dos dados do formulário para auditoria SIF/QSA/PCM
"""

import logging
from typing import Any, Dict, Optional

from app.models.comum import ComumUsuario
from app.models.manutencao import ManutencaoHistoricoFormulario, ManutencaoOrdemServico
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def registrar_alteracao_campo(
    db: Session,
    os: ManutencaoOrdemServico,
    campo_id: str,
    valor_anterior: Any,
    valor_novo: Any,
    usuario: ComumUsuario,
    perfil_rbac: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    contexto: Optional[Dict[str, Any]] = None
) -> ManutencaoHistoricoFormulario:
    """
    Registra alteração de um campo específico do formulário
    
    Args:
        db: Sessão do banco de dados
        os: Ordem de Serviço
        campo_id: ID do campo alterado
        valor_anterior: Valor anterior do campo
        valor_novo: Novo valor do campo
        usuario: Usuário que alterou
        perfil_rbac: Perfil RBAC no momento da alteração
        ip_address: IP de origem
        user_agent: User-Agent do navegador
        contexto: Dados adicionais do evento
        
    Returns:
        ManutencaoHistoricoFormulario: Registro de histórico criado
    """
    try:
        historico = ManutencaoHistoricoFormulario(
            os_id=os.id,
            campo_id=campo_id,
            valor_anterior=valor_anterior,
            valor_novo=valor_novo,
            usuario_id=usuario.id,
            perfil_rbac=perfil_rbac,
            ip_address=ip_address,
            user_agent=user_agent,
            contexto_json=contexto
        )
        
        db.add(historico)
        db.commit()
        db.refresh(historico)
        
        logger.info(f"Alteração registrada: OS={os.id}, Campo={campo_id}, Usuário={usuario.id}")
        return historico
        
    except Exception as e:
        logger.error(f"Erro ao registrar alteração: {e}", exc_info=True)
        db.rollback()
        raise


def registrar_alteracoes_lote(
    db: Session,
    os: ManutencaoOrdemServico,
    alteracoes: Dict[str, Dict[str, Any]],
    usuario: ComumUsuario,
    perfil_rbac: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> list:
    """
    Registra múltiplas alterações de campos em lote
    
    Args:
        db: Sessão do banco de dados
        os: Ordem de Serviço
        alteracoes: Dict com {campo_id: {valor_anterior: X, valor_novo: Y}}
        usuario: Usuário que alterou
        perfil_rbac: Perfil RBAC no momento da alteração
        ip_address: IP de origem
        user_agent: User-Agent do navegador
        
    Returns:
        List[ManutencaoHistoricoFormulario]: Lista de registros criados
    """
    registros = []
    
    try:
        for campo_id, valores in alteracoes.items():
            historico = ManutencaoHistoricoFormulario(
                os_id=os.id,
                campo_id=campo_id,
                valor_anterior=valores.get("valor_anterior"),
                valor_novo=valores.get("valor_novo"),
                usuario_id=usuario.id,
                perfil_rbac=perfil_rbac,
                ip_address=ip_address,
                user_agent=user_agent,
                contexto_json=valores.get("contexto")
            )
            db.add(historico)
            registros.append(historico)
        
        db.commit()
        for registro in registros:
            db.refresh(registro)
        
        logger.info(f"Alterações em lote registradas: OS={os.id}, {len(registros)} campos, Usuário={usuario.id}")
        return registros
        
    except Exception as e:
        logger.error(f"Erro ao registrar alterações em lote: {e}", exc_info=True)
        db.rollback()
        raise


def obter_historico_campo(
    db: Session,
    os_id: int,
    campo_id: str
) -> list:
    """
    Obtém histórico de alterações de um campo específico
    
    Args:
        db: Sessão do banco de dados
        os_id: ID da OS
        campo_id: ID do campo
        
    Returns:
        List[ManutencaoHistoricoFormulario]: Lista de alterações do campo
    """
    return db.query(ManutencaoHistoricoFormulario).filter(
        ManutencaoHistoricoFormulario.os_id == os_id,
        ManutencaoHistoricoFormulario.campo_id == campo_id
    ).order_by(ManutencaoHistoricoFormulario.data_hora.desc()).all()


def obter_historico_completo(
    db: Session,
    os_id: int
) -> list:
    """
    Obtém histórico completo de alterações do formulário
    
    Args:
        db: Sessão do banco de dados
        os_id: ID da OS
        
    Returns:
        List[ManutencaoHistoricoFormulario]: Lista de todas as alterações
    """
    return db.query(ManutencaoHistoricoFormulario).filter(
        ManutencaoHistoricoFormulario.os_id == os_id
    ).order_by(ManutencaoHistoricoFormulario.data_hora.desc()).all()
