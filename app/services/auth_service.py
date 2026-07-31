# PDV Ibix - Serviços de Autenticação
import re
from datetime import date, timedelta
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from ..core.audit import audit_action
from ..core.auth import AuthConfig, create_user_token, verify_user_credentials
from ..core.billing_config import get_valor_mensal_centavos
from ..core.logging import log_error, log_security
from ..models import AreaCliente, Cliente, ClienteAdministradorCliente, Empresa, Role, Usuario
from ..models.administrador_cliente_administrador import AdministradorClienteAdministrador
from ..models.divulgador import Divulgador
from ..models.empresa import AmbienteEnum
from ..models.subscription_billing import SubscriptionBilling
from ..models.tenant import Tenant
from ..schemas.auth import (
    RegisterInfluencerRequest,
    RegisterPublicRequest,
    RegisterRepresentanteRequest,
    Token,
    UserLogin,
    UserRegister,
)
from ..services.codigo_desconto_lookup import buscar_codigo_desconto_ativo_por_entrada
from ..utils.cnpj_validator import CNPJValidator


class AuthService:
    """Serviços de autenticação"""
    
    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> Optional[Usuario]:
        """Autentica usuário com email e senha"""
        if not email or not password:
            return None
        email = email.strip().lower()
        # Buscar usuário por email
        user = db.query(Usuario).filter(Usuario.email == email).first()
        
        if not user:
            return None
        
        # Verificar senha
        if not verify_user_credentials(email, password, user.senha_hash):
            return None
        
        # Verificar se usuário está ativo
        if not user.ativo:
            return None
        
        return user
    
    @staticmethod
    def create_user(db: Session, user_data: UserRegister) -> Usuario:
        """Cria novo usuário"""
        # Verificar se email já existe
        existing_user = db.query(Usuario).filter(Usuario.email == user_data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email já cadastrado"
            )
        
        # Verificar se role existe (se fornecida)
        if user_data.role_id:
            role = db.query(Role).filter(Role.id == user_data.role_id).first()
            if not role:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Role não encontrada"
                )
        
        # Criar hash da senha
        hashed_password = AuthConfig.get_password_hash(user_data.password)
        
        # Criar usuário
        db_user = Usuario(
            nome=user_data.nome,
            email=user_data.email,
            senha_hash=hashed_password,
            cargo=user_data.cargo,
            role_id=user_data.role_id,
            ativo=True
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        return db_user
    
    @staticmethod
    def login_user(
        db: Session,
        login_data: UserLogin,
        ip: Optional[str] = None,
        request=None,
    ) -> Token:
        """Realiza login do usuário. ip opcional para log de segurança."""
        # Autenticar usuário
        user = AuthService.authenticate_user(db, login_data.email, login_data.password)
        
        if not user:
            log_security("login_falha", ip=ip or "", user=login_data.email or "unknown", details="credencial_invalida")
            try:
                audit_action(db, "login_falha", recurso_tipo="usuario", detalhes="credencial_invalida")
            except Exception:
                pass
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou senha incorretos",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if request is not None:
            from app.services.brand_scope_service import assert_user_tenant_matches_request_brand

            assert_user_tenant_matches_request_brand(db, user, request)
        
        audit_action(
            db,
            "login_sucesso",
            user_id=user.id,
            tenant_id=getattr(user, "tenant_id", None),
            recurso_tipo="usuario",
            recurso_id=user.id,
        )
        log_security("login_sucesso", ip=ip or "", user=str(user.id), details="")
        # Obter nome da role
        role_name = user.role.nome if user.role else None
        
        # Consultar AreaCliente para obter cliente_id vinculado ao usuário
        area_cliente = db.query(AreaCliente).filter(
            AreaCliente.usuario_id == user.id,
            AreaCliente.ativo == True
        ).first()
        
        cliente_id = area_cliente.cliente_id if area_cliente else None
        
        # Criar token com cliente_id se disponível
        access_token = create_user_token(user.id, user.email, role_name or "", cliente_id=cliente_id)
        
        # Criar resposta do token
        token_response = Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=30,  # minutos
            user_id=user.id,
            email=user.email,
            role=role_name
        )
        
        return token_response

    @staticmethod
    def register_public(db: Session, data: RegisterPublicRequest, brand_id: int) -> Usuario:
        """Cadastro público: cria Cliente (empresa) + Usuario com role Cliente Administrador + vínculo (Saas.md Fase 6).
        Se codigo_promocional informado: valida código, cria Tenant + Subscription (valor com desconto) e vínculo AdministradorClienteAdministrador."""
        if not brand_id:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Marca não resolvida para cadastro.",
            )
        codigo_obj = None
        divulgador = None
        codigo_promocional = (data.codigo_promocional or "").strip() if getattr(data, "codigo_promocional", None) else None
        if codigo_promocional:
            codigo_obj = buscar_codigo_desconto_ativo_por_entrada(db, codigo_promocional)
            if not codigo_obj:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Código promocional inválido ou expirado.",
                )
            divulgador = codigo_obj.divulgador if codigo_obj.divulgador_id else None
            if not divulgador or not divulgador.usuario_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Código promocional não vinculado a um administrador.",
                )
            admin_user = db.query(Usuario).options(joinedload(Usuario.role)).filter(Usuario.id == divulgador.usuario_id).first()
            role_nome = (admin_user.role.nome or "").strip() if (admin_user and admin_user.role) else ""
            if not admin_user or not admin_user.role or role_nome.upper() != "ADMINISTRADOR":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Código promocional inválido ou não vinculado a um administrador.",
                )

        existing = db.query(Usuario).filter(Usuario.email == data.email).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email já cadastrado")
        cnpj_ok, cnpj_fmt, cnpj_erro = CNPJValidator.validar_e_formatar(data.cnpj)
        if not cnpj_ok:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=cnpj_erro if cnpj_erro else "CNPJ inválido",
            )
        if db.query(Cliente).filter(Cliente.cnpj == cnpj_fmt).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CNPJ já cadastrado")
        # Dados bancários + PIX são obrigatórios no cadastro do CA (empresa pagadora)
        banco_nome = (getattr(data, "banco_nome", "") or "").strip()
        agencia = (getattr(data, "agencia", "") or "").strip()
        conta = (getattr(data, "conta", "") or "").strip()
        tipo_conta = (getattr(data, "tipo_conta", "") or "").strip()
        pix_chave = (getattr(data, "pix_chave", "") or "").strip()
        banco_codigo = (getattr(data, "banco_codigo", None) or "").strip() or None
        if not banco_nome:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Banco (nome) é obrigatório.")
        if not agencia:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Agência é obrigatória.")
        if not conta:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Conta é obrigatória.")
        if not tipo_conta:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tipo de conta é obrigatório.")
        if not pix_chave:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chave PIX é obrigatória.")

        role = db.query(Role).filter(func.lower(Role.nome) == "cliente administrador").first()
        if not role:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Role Cliente Administrador não configurada")
        cep_raw = (data.cep or "").strip()
        digits_only = re.sub(r"\D", "", cep_raw)
        if len(digits_only) == 8:
            cep_val = f"{digits_only[:5]}-{digits_only[5:]}"  # 00000-000
        else:
            cep_val = cep_raw[:20] if cep_raw else ""
        cliente = Cliente(
            nome=data.nome_empresa,
            cnpj=cnpj_fmt,
            cep=cep_val or "",
            endereco=data.endereco,
            cidade=data.cidade,
            uf=data.uf.upper(),
            contato=data.contato,
            telefone=data.telefone,
            email=data.email,
            banco_nome=banco_nome[:100],
            banco_codigo=banco_codigo[:10] if banco_codigo else None,
            agencia=agencia[:20],
            conta=conta[:30],
            tipo_conta=tipo_conta[:20],
            pix_chave=pix_chave[:120],
        )
        db.add(cliente)
        db.flush()
        from app.services.cliente_categorias_vitrine_service import salvar_categorias_cliente

        salvar_categorias_cliente(db, cliente.id, data.categorias_vitrine_ids)
        hashed = AuthConfig.get_password_hash(data.password)
        user = Usuario(
            nome=data.nome,
            email=data.email,
            senha_hash=hashed,
            cargo="Cliente Administrador",
            role_id=role.id,
            ativo=True,
        )
        db.add(user)
        db.flush()
        db.add(ClienteAdministradorCliente(usuario_id=user.id, cliente_id=cliente.id))
        db.add(AreaCliente(usuario_id=user.id, cliente_id=cliente.id, nome_area="administrador", ativo=True))
        # Criar Empresa Fiscal (dados fiscais do emissor) com os mesmos dados do cliente
        cep_empresa = (cep_val or "").strip() or None
        empresa_fiscal = Empresa(
            cliente_id=cliente.id,
            razao_social=data.nome_empresa,
            nome_fantasia=data.nome_empresa,
            cnpj=cnpj_fmt,
            cep=cep_empresa or None,
            endereco=data.endereco,
            cidade=data.cidade,
            uf=data.uf.upper(),
            telefone=data.telefone,
            email=data.email,
            ativo=True,
            ambiente=AmbienteEnum.HOMOLOGACAO,
            uf_emissao=data.uf.upper(),
        )
        db.add(empresa_fiscal)

        # Sempre criar Tenant e Subscription (código promocional opcional: com código = desconto + vínculo admin)
        from app.services.billing_service import DEFAULT_GRACE_DAYS, TRIAL_DAYS
        from app.services.brand_scope_service import generate_unique_tenant_slug

        slug_base = f"ca-{user.id}"
        slug = generate_unique_tenant_slug(db, slug_base, brand_id)
        tenant = Tenant(
            nome=data.nome_empresa or data.nome or "Assinante",
            slug=slug,
            brand_id=brand_id,
            ativo=True,
        )
        db.add(tenant)
        db.flush()
        user.tenant_id = tenant.id
        base_centavos = get_valor_mensal_centavos(db)
        if codigo_obj and divulgador:
            pct = codigo_obj.desconto_mensalidade_percent or 0
            if codigo_obj.tipo_promocao == "desconto_primeira_parcela":
                pct = codigo_obj.desconto_primeira_parcela_percent or 0
            elif codigo_obj.desconto_mensalidade_percent is not None:
                pct = codigo_obj.desconto_mensalidade_percent
            valor_centavos = 0 if pct >= 100 else max(1, int(round(base_centavos * (1 - pct / 100.0))))
        else:
            valor_centavos = base_centavos
        today = date.today()
        period_end = today + timedelta(days=TRIAL_DAYS)
        sub = SubscriptionBilling(
            tenant_id=tenant.id,
            plano_codigo="pdv_solumatica_490",
            valor_mensal_centavos=valor_centavos,
            qtd_pdvs_contratados=1,
            status="trial",
            grace_days=DEFAULT_GRACE_DAYS,
            period_start=today,
            period_end=period_end,
            next_charge_at=period_end,
            codigo_desconto_id=codigo_obj.id if (codigo_obj and divulgador) else None,
        )
        db.add(sub)
        if codigo_obj and divulgador:
            db.add(AdministradorClienteAdministrador(
                usuario_id_administrador=divulgador.usuario_id,
                usuario_id_cliente_administrador=user.id,
            ))

        db.commit()
        db.refresh(user)
        try:
            from app.services.platform_novo_ca_notify_service import after_register_public_success

            after_register_public_success(
                db,
                ca_user_id=user.id,
                tenant_id=tenant.id,
                nome_empresa=(data.nome_empresa or data.nome or "").strip(),
                cnpj=cnpj_fmt,
                email_responsavel=(user.email or data.email or "").strip(),
            )
        except Exception as e:
            log_error("after_register_public_success (notificação plataforma)", exc_info=e)
        audit_action(
            db,
            "cadastro_publico",
            user_id=user.id,
            tenant_id=getattr(user, "tenant_id", None),
            recurso_tipo="usuario",
            recurso_id=user.id,
            detalhes=f"email={user.email}",
        )
        return user

    @staticmethod
    def register_representante(db: Session, data: RegisterRepresentanteRequest) -> Usuario:
        """Cadastro público do Representante (Administrador): cria apenas Usuario com role Administrador.
        Sem Cliente, Tenant ou Empresa."""
        existing = db.query(Usuario).filter(Usuario.email == data.email.strip().lower()).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="E-mail já cadastrado.")
        role = db.query(Role).filter(func.lower(Role.nome) == "administrador").first()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Role Administrador não configurada.",
            )
        hashed = AuthConfig.get_password_hash(data.password)
        user = Usuario(
            nome=data.nome.strip(),
            email=data.email.strip().lower(),
            senha_hash=hashed,
            cargo="Representante",
            role_id=role.id,
            ativo=True,
        )
        db.add(user)
        db.flush()
        db.commit()
        db.refresh(user)
        audit_action(
            db,
            "cadastro_representante",
            user_id=user.id,
            tenant_id=None,
            recurso_tipo="usuario",
            recurso_id=user.id,
            detalhes=f"email={user.email}",
        )
        return user

    @staticmethod
    def register_influencer(db: Session, data: RegisterInfluencerRequest) -> Usuario:
        """Cadastro publico do Influencer: cria Usuario com role Influencer + Divulgador vinculado."""
        existing = db.query(Usuario).filter(Usuario.email == data.email.strip().lower()).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="E-mail já cadastrado.")
        role = db.query(Role).filter(func.lower(Role.nome) == "influencer").first()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Role Influencer não configurada. Execute a migração inf01_influencer_base.",
            )
        hashed = AuthConfig.get_password_hash(data.password)
        user = Usuario(
            nome=data.nome.strip(),
            email=data.email.strip().lower(),
            senha_hash=hashed,
            cargo="Influencer",
            role_id=role.id,
            ativo=True,
        )
        db.add(user)
        db.flush()

        from ..models.divulgador import Divulgador
        div = Divulgador(
            nome=data.nome.strip(),
            email=data.email.strip().lower(),
            telefone=data.telefone,
            usuario_id=user.id,
            ativo=True,
            tipo="influencer",
            status="pendente",
            cidade=data.cidade,
            estado=data.estado,
            nicho=data.nicho,
            redes_sociais=data.redes_sociais,
            tipo_atuacao=data.tipo_atuacao,
            bio=data.bio,
        )
        db.add(div)
        db.commit()
        db.refresh(user)
        audit_action(
            db,
            "cadastro_influencer",
            user_id=user.id,
            tenant_id=None,
            recurso_tipo="usuario",
            recurso_id=user.id,
            detalhes=f"email={user.email}",
        )
        try:
            from .influencer_notification_service import notificar_cadastro_recebido
            notificar_cadastro_recebido(db, div, user.id)
        except Exception:
            pass
        return user

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[Usuario]:
        """Obtém usuário por ID"""
        return db.query(Usuario).filter(Usuario.id == user_id).first()
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[Usuario]:
        """Obtém usuário por email"""
        return db.query(Usuario).filter(Usuario.email == email).first()
    
    @staticmethod
    def update_user(db: Session, user_id: int, user_data: dict) -> Optional[Usuario]:
        """Atualiza dados do usuário"""
        user = db.query(Usuario).filter(Usuario.id == user_id).first()
        if not user:
            return None
        
        # Atualizar campos fornecidos
        for field, value in user_data.items():
            if value is not None and hasattr(user, field):
                setattr(user, field, value)
        
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def change_password(db: Session, user_id: int, current_password: str, new_password: str) -> bool:
        """Altera senha do usuário"""
        user = db.query(Usuario).filter(Usuario.id == user_id).first()
        if not user:
            return False
        
        # Verificar senha atual
        if not verify_user_credentials(user.email, current_password, user.senha_hash):
            return False
        
        # Gerar novo hash
        new_hash = AuthConfig.get_password_hash(new_password)
        user.senha_hash = new_hash
        
        db.commit()
        return True
    
    @staticmethod
    def deactivate_user(db: Session, user_id: int) -> bool:
        """Desativa usuário"""
        user = db.query(Usuario).filter(Usuario.id == user_id).first()
        if not user:
            return False
        
        user.ativo = False
        db.commit()
        return True
    
    @staticmethod
    def activate_user(db: Session, user_id: int) -> bool:
        """Ativa usuário"""
        user = db.query(Usuario).filter(Usuario.id == user_id).first()
        if not user:
            return False
        
        user.ativo = True
        db.commit()
        return True 