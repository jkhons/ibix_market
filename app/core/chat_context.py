# PDV Ibix - Contexto de chat/WhatsApp: identificação usuário e empresa
"""Helper para montar identificação de usuário e empresa (cliente) em mensagens."""

from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.models.usuario import Usuario


@dataclass
class ChatContext:
    """Identificação do remetente para mensagens (chat/WhatsApp)."""
    usuario_id: int
    nome_usuario: str
    role_nome: Optional[str]
    cliente_id: Optional[int]
    cliente_nome: Optional[str]

    def empresa_display(self) -> str:
        """Nome da empresa/cliente para exibição; 'Sistema' se sem cliente."""
        return (self.cliente_nome or "Sistema").strip() or "Sistema"

    def prefixo_mensagem(self, formato: str = "curto") -> str:
        """
        Prefixo para anexar ao corpo da mensagem (ex.: WhatsApp).
        formato 'curto': [Nome | Empresa]
        formato 'completo': [PDV Ibix - Usuário: Nome | Empresa: X]
        """
        emp = self.empresa_display()
        if formato == "completo":
            return f"[PDV Ibix - Usuário: {self.nome_usuario} | Empresa: {emp}] "
        return f"[{self.nome_usuario} | {emp}] "


def get_chat_context(
    db: Session,
    usuario_id: int,
    role_nome: Optional[str] = None,
    cliente_id_from_token: Optional[int] = None,
) -> ChatContext:
    """
    Obtém contexto do usuário e empresa (cliente) para identificar mensagens.
    Se não houver cliente_id no token, tenta AreaCliente; se não houver, cliente_nome = None (exibe Sistema).
    """
    user = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    nome_usuario = (user.nome if user else "").strip() or "Sistema"
    role = (role_nome or (user.role.nome if user and user.role else None) or "").strip()

    cliente_id = cliente_id_from_token
    if cliente_id is None and user:
        from app.models.area_cliente import AreaCliente
        area = db.query(AreaCliente).filter(
            AreaCliente.usuario_id == user.id,
            AreaCliente.ativo == True,
        ).first()
        if area:
            cliente_id = area.cliente_id

    cliente_nome = None
    if cliente_id is not None:
        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        if cliente:
            cliente_nome = (cliente.nome or "").strip()

    return ChatContext(
        usuario_id=usuario_id,
        nome_usuario=nome_usuario,
        role_nome=role or None,
        cliente_id=cliente_id,
        cliente_nome=cliente_nome,
    )
