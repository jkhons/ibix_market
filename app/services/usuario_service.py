# PDV Ibix - Serviços de Usuário
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..core.auth import AuthConfig
from ..models import AreaCliente, Cliente, Role, Usuario
from ..schemas.usuario import UsuarioClienteCreate


class UsuarioService:
    """Serviços relacionados a usuários"""
    
    @staticmethod
    def criar_usuario_cliente(db: Session, usuario_data: UsuarioClienteCreate) -> Usuario:
        """
        Cria um usuário vinculado a um cliente específico, sempre com role Subcliente.
        Cria o usuário e o registro em AreaCliente (acesso dentro da organização do Cliente Administrador).
        """
        # Verificar se cliente existe
        cliente = db.query(Cliente).filter(Cliente.id == usuario_data.cliente_id).first()
        if not cliente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente não encontrado"
            )
        
        # Verificar se email já está em uso
        usuario_existente = db.query(Usuario).filter(Usuario.email == usuario_data.email).first()
        if usuario_existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email já está em uso"
            )
        
        # Sempre Subcliente (modal de clientes não oferece escolha de função)
        role = db.query(Role).filter(Role.nome == "Subcliente", Role.ativo == True).first()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Função Subcliente não configurada no sistema",
            )
        
        # Criar hash da senha
        senha_hash = AuthConfig.get_password_hash(usuario_data.senha)
        
        # Criar usuário
        db_usuario = Usuario(
            nome=usuario_data.nome,
            email=usuario_data.email,
            senha_hash=senha_hash,
            cargo="Subcliente",
            ativo=usuario_data.ativo if usuario_data.ativo is not None else True,
            role_id=role.id,
        )
        
        db.add(db_usuario)
        db.flush()  # Para obter o ID do usuário criado
        
        # Criar registro em AreaCliente
        area_cliente = AreaCliente(
            cliente_id=usuario_data.cliente_id,
            usuario_id=db_usuario.id,
            nome_area="visualizador",  # Padrão: usuário pode visualizar dados do cliente
            ativo=True
        )
        
        db.add(area_cliente)
        db.commit()
        db.refresh(db_usuario)
        
        return db_usuario

