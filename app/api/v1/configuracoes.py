# PDV Ibix - API de Configurações
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.core.email_funcoes import (
    CHAVE_EMAIL_SEPARADO_POR_CLIENTE_ATIVO,
    chave_from,
    chave_from_name,
    get_codigos_funcoes_email,
    get_funcoes_email,
)
from app.core.middleware import (
    forbid_cliente_access,
    require_permission,
    require_superadmin,
    require_superadmin_or_admin,
)
from app.database.connection import get_db
from app.models.configuracao import Configuracao
from app.models.tenant import Tenant
from app.models.usuario import Usuario
from app.schemas.configuracao import (
    ConfiguracaoWhatsAppRequest,
    ConfiguracaoWhatsAppResponse,
    EmailFuncaoItem,
    EmailFuncoesResponse,
    EmailFuncoesUpdate,
)
from app.services.email_service import EmailService
from app.services.integration_webhooks import (
    CHAVE_WEBHOOK_VENDA_FECHADA_ENABLED,
    CHAVE_WEBHOOK_VENDA_FECHADA_TIMEOUT,
    CHAVE_WEBHOOK_VENDA_FECHADA_TOKEN,
    CHAVE_WEBHOOK_VENDA_FECHADA_URL,
    tenant_webhook_key,
)

configuracoes_router = APIRouter(
    prefix="/configuracoes",
    dependencies=[Depends(forbid_cliente_access), Depends(require_superadmin_or_admin())]
)

# Schemas para E-mail
class EmailTestRequest(BaseModel):
    to: EmailStr

def get_configuracao(db: Session, chave: str) -> Configuracao:
    """Buscar configuração por chave"""
    return db.query(Configuracao).filter(Configuracao.chave == chave).first()

def set_configuracao(db: Session, chave: str, valor: str, descricao: str = None) -> Configuracao:
    """Definir configuração"""
    try:
        config = get_configuracao(db, chave)
        if config:
            config.valor = valor
            if descricao:
                config.descricao = descricao
        else:
            config = Configuracao(chave=chave, valor=valor, descricao=descricao)
            db.add(config)
        
        db.commit()
        db.refresh(config)
        return config
    except Exception:
        db.rollback()
        raise

# ===== PROVEDOR FISCAL (único para todo o sistema SaaS; apenas Superadministrador) =====

CHAVE_FISCAL_PROVEDOR = "fiscal.provedor"
CHAVE_FISCAL_PROVEDOR_API_KEY = "fiscal.provedor_api_key"
CHAVE_FISCAL_PROVEDOR_API_SECRET = "fiscal.provedor_api_secret"
CHAVE_FISCAL_SERIE_PADRAO_NFE = "fiscal.serie_padrao_nfe"
CHAVE_FISCAL_SERIE_PADRAO_NFCE = "fiscal.serie_padrao_nfce"


class FiscalProvedorResponse(BaseModel):
    """Resposta da configuração global do provedor fiscal (não expõe API secret)."""
    provedor: Optional[str] = None
    serie_padrao_nfe: Optional[str] = None
    serie_padrao_nfce: Optional[str] = None


class FiscalProvedorUpdate(BaseModel):
    """Body para atualizar provedor fiscal global."""
    provedor: Optional[str] = None
    provedor_api_key: Optional[str] = None
    provedor_api_secret: Optional[str] = None
    serie_padrao_nfe: Optional[str] = None
    serie_padrao_nfce: Optional[str] = None


class IntegracaoWebhookVendaFechadaResponse(BaseModel):
    tenant_id: int
    enabled: bool = False
    webhook_url: Optional[str] = None
    timeout_seconds: Optional[int] = None
    has_token: bool = False


class IntegracaoWebhookVendaFechadaUpdate(BaseModel):
    enabled: Optional[bool] = None
    webhook_url: Optional[str] = None
    token: Optional[str] = None
    timeout_seconds: Optional[int] = None


@configuracoes_router.get("/fiscal-provedor/", response_model=FiscalProvedorResponse)
def obter_fiscal_provedor(
    db: Session = Depends(get_db),
    _=Depends(require_permission("fiscal.empresa.configurar_provedor")),
):
    """Obter configuração global do provedor fiscal. Apenas Superadministrador."""
    c_provedor = get_configuracao(db, CHAVE_FISCAL_PROVEDOR)
    c_nfe = get_configuracao(db, CHAVE_FISCAL_SERIE_PADRAO_NFE)
    c_nfce = get_configuracao(db, CHAVE_FISCAL_SERIE_PADRAO_NFCE)
    return FiscalProvedorResponse(
        provedor=c_provedor.valor if c_provedor else None,
        serie_padrao_nfe=c_nfe.valor if c_nfe else None,
        serie_padrao_nfce=c_nfce.valor if c_nfce else None,
    )


@configuracoes_router.put("/fiscal-provedor/", response_model=FiscalProvedorResponse)
def salvar_fiscal_provedor(
    dados: FiscalProvedorUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_permission("fiscal.empresa.configurar_provedor")),
):
    """Salvar configuração global do provedor fiscal. Apenas Superadministrador."""
    if dados.provedor is not None:
        set_configuracao(db, CHAVE_FISCAL_PROVEDOR, dados.provedor or "", "Provedor fiscal (único para o sistema)")
    if dados.provedor_api_key is not None:
        set_configuracao(db, CHAVE_FISCAL_PROVEDOR_API_KEY, dados.provedor_api_key or "", "API key do provedor fiscal")
    if dados.provedor_api_secret is not None:
        set_configuracao(db, CHAVE_FISCAL_PROVEDOR_API_SECRET, dados.provedor_api_secret or "", "API secret do provedor fiscal")
    if dados.serie_padrao_nfe is not None:
        set_configuracao(db, CHAVE_FISCAL_SERIE_PADRAO_NFE, dados.serie_padrao_nfe or "1", "Série padrão NF-e")
    if dados.serie_padrao_nfce is not None:
        set_configuracao(db, CHAVE_FISCAL_SERIE_PADRAO_NFCE, dados.serie_padrao_nfce or "1", "Série padrão NFC-e")
    return obter_fiscal_provedor(db)


@configuracoes_router.get("/integracoes/webhook-venda-fechada/", response_model=IntegracaoWebhookVendaFechadaResponse)
def obter_integracao_webhook_venda_fechada(
    tenant_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
    _=Depends(require_superadmin),
):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")

    enabled_cfg = get_configuracao(db, tenant_webhook_key(CHAVE_WEBHOOK_VENDA_FECHADA_ENABLED, tenant_id))
    url_cfg = get_configuracao(db, tenant_webhook_key(CHAVE_WEBHOOK_VENDA_FECHADA_URL, tenant_id))
    token_cfg = get_configuracao(db, tenant_webhook_key(CHAVE_WEBHOOK_VENDA_FECHADA_TOKEN, tenant_id))
    timeout_cfg = get_configuracao(db, tenant_webhook_key(CHAVE_WEBHOOK_VENDA_FECHADA_TIMEOUT, tenant_id))

    timeout_val = None
    if timeout_cfg and timeout_cfg.valor:
        timeout_val = int(timeout_cfg.valor)
    return IntegracaoWebhookVendaFechadaResponse(
        tenant_id=tenant_id,
        enabled=(enabled_cfg.valor.strip().lower() in {"1", "true", "sim", "yes", "on"}) if enabled_cfg else False,
        webhook_url=url_cfg.valor if url_cfg else None,
        timeout_seconds=timeout_val,
        has_token=bool(token_cfg and token_cfg.valor),
    )


@configuracoes_router.put("/integracoes/webhook-venda-fechada/", response_model=IntegracaoWebhookVendaFechadaResponse)
def salvar_integracao_webhook_venda_fechada(
    dados: IntegracaoWebhookVendaFechadaUpdate,
    tenant_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
    _=Depends(require_superadmin),
):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")

    cfg_enabled = tenant_webhook_key(CHAVE_WEBHOOK_VENDA_FECHADA_ENABLED, tenant_id)
    cfg_url = tenant_webhook_key(CHAVE_WEBHOOK_VENDA_FECHADA_URL, tenant_id)
    cfg_token = tenant_webhook_key(CHAVE_WEBHOOK_VENDA_FECHADA_TOKEN, tenant_id)
    cfg_timeout = tenant_webhook_key(CHAVE_WEBHOOK_VENDA_FECHADA_TIMEOUT, tenant_id)

    existing_enabled = get_configuracao(db, cfg_enabled)
    existing_url = get_configuracao(db, cfg_url)
    final_enabled = dados.enabled if dados.enabled is not None else (
        existing_enabled.valor.strip().lower() in {"1", "true", "sim", "yes", "on"} if existing_enabled else False
    )
    final_url = dados.webhook_url.strip() if dados.webhook_url is not None else (existing_url.valor if existing_url else None)

    if final_enabled and not final_url:
        raise HTTPException(status_code=400, detail="Para habilitar a integração, informe webhook_url")

    if dados.enabled is not None:
        set_configuracao(
            db,
            cfg_enabled,
            "true" if dados.enabled else "false",
            f"Habilita integração webhook para evento venda.fechada (tenant {tenant_id})",
        )
    if dados.webhook_url is not None:
        set_configuracao(
            db,
            cfg_url,
            dados.webhook_url.strip(),
            f"URL do webhook externo para evento venda.fechada (tenant {tenant_id})",
        )
    if dados.token is not None:
        set_configuracao(
            db,
            cfg_token,
            dados.token.strip(),
            f"Token Bearer para webhook externo de venda.fechada (tenant {tenant_id})",
        )
    if dados.timeout_seconds is not None:
        if dados.timeout_seconds <= 0:
            raise HTTPException(status_code=400, detail="timeout_seconds deve ser maior que zero")
        set_configuracao(
            db,
            cfg_timeout,
            str(dados.timeout_seconds),
            f"Timeout em segundos para envio de webhook venda.fechada (tenant {tenant_id})",
        )
    return obter_integracao_webhook_venda_fechada(tenant_id=tenant_id, db=db)


# ===== POLÍTICAS DE QUALIDADE (ISO 17025 Fase 3.1 - 4.1, 4.2) =====

CHAVE_POLITICA_IMPARCIALIDADE = "politica.imparcialidade"
CHAVE_POLITICA_CONFIDENCIALIDADE = "politica.confidencialidade"


class PoliticasQualidadeResponse(BaseModel):
    """Resposta com textos das políticas de qualidade"""
    imparcialidade: str = ""
    confidencialidade: str = ""


class PoliticasQualidadeUpdate(BaseModel):
    """Body para atualizar políticas de qualidade"""
    imparcialidade: Optional[str] = None
    confidencialidade: Optional[str] = None


@configuracoes_router.get("/politicas-qualidade/", response_model=PoliticasQualidadeResponse)
def obter_politicas_qualidade(db: Session = Depends(get_db)):
    """Obter textos das políticas de imparcialidade e confidencialidade (ISO 17025 4.1, 4.2)."""
    c_imp = get_configuracao(db, CHAVE_POLITICA_IMPARCIALIDADE)
    c_conf = get_configuracao(db, CHAVE_POLITICA_CONFIDENCIALIDADE)
    return PoliticasQualidadeResponse(
        imparcialidade=c_imp.valor if c_imp else "",
        confidencialidade=c_conf.valor if c_conf else "",
    )


@configuracoes_router.put("/politicas-qualidade/", response_model=PoliticasQualidadeResponse)
def salvar_politicas_qualidade(
    dados: PoliticasQualidadeUpdate,
    db: Session = Depends(get_db),
):
    """Salvar textos das políticas de imparcialidade e confidencialidade."""
    if dados.imparcialidade is not None:
        set_configuracao(db, CHAVE_POLITICA_IMPARCIALIDADE, dados.imparcialidade, "Política de imparcialidade (ISO 17025 4.1)")
    if dados.confidencialidade is not None:
        set_configuracao(db, CHAVE_POLITICA_CONFIDENCIALIDADE, dados.confidencialidade, "Política de confidencialidade (ISO 17025 4.2)")
    return obter_politicas_qualidade(db)


# ===== ENDPOINTS DE E-MAIL =====

@configuracoes_router.get("/email/")
def obter_configuracoes_email(db: Session = Depends(get_db)):
    """Obter configurações de e-mail"""
    try:
        chaves = [
            'email_host',
            'email_port',
            'email_username',
            'email_password',
            'email_from',
            'email_from_name',
            'email_use_tls',
            'email_use_ssl'
        ]
        
        configs = {}
        for chave in chaves:
            config = get_configuracao(db, chave)
            configs[chave] = config.valor if config else ''
        
        return configs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter configurações de e-mail: {str(e)}")


@configuracoes_router.post("/email/")
def salvar_configuracoes_email(
    configs: Dict[str, str],
    db: Session = Depends(get_db)
):
    """Salvar configurações de e-mail"""
    try:
        # Validar configurações obrigatórias
        required = ['email_host', 'email_port', 'email_username', 'email_password', 'email_from']
        missing = [k for k in required if k not in configs or not configs[k]]
        
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Configurações obrigatórias faltando: {', '.join(missing)}"
            )
        
        # Salvar cada configuração
        descricoes = {
            'email_host': 'Servidor SMTP',
            'email_port': 'Porta do servidor SMTP',
            'email_username': 'Usuário/E-mail para autenticação',
            'email_password': 'Senha para autenticação',
            'email_from': 'E-mail remetente',
            'email_from_name': 'Nome do remetente',
            'email_use_tls': 'Usar TLS',
            'email_use_ssl': 'Usar SSL'
        }
        
        for chave, valor in configs.items():
            set_configuracao(db, chave, valor, descricoes.get(chave, ''))
        
        return {"success": True, "message": "Configurações de e-mail salvas com sucesso"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar configurações: {str(e)}")


@configuracoes_router.post("/email/test-connection/")
def testar_conexao_email(db: Session = Depends(get_db)):
    """Testar conexão com servidor SMTP"""
    try:
        email_service = EmailService(db)
        success, message = email_service.test_connection()
        
        return {"success": success, "message": message}
    except ValueError as e:
        return {"success": False, "message": str(e)}
    except Exception as e:
        return {"success": False, "message": f"Erro ao testar conexão: {str(e)}"}


@configuracoes_router.post("/email/send-test/")
def enviar_email_teste(
    request: EmailTestRequest,
    db: Session = Depends(get_db)
):
    """Enviar e-mail de teste"""
    try:
        email_service = EmailService(db)
        
        subject = "Teste de Envio - PDV Ibix"
        body = """
        Este é um e-mail de teste do sistema PDV Ibix.
        
        Se você recebeu esta mensagem, significa que as configurações de e-mail estão funcionando corretamente.
        
        Atenciosamente,
        Sistema PDV Ibix
        """
        
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background-color: #0d6efd; color: white; padding: 20px; text-align: center; }
                .content { background-color: #f8f9fa; padding: 20px; margin-top: 20px; }
                .footer { text-align: center; margin-top: 20px; color: #666; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>✅ Teste de E-mail</h1>
                </div>
                <div class="content">
                    <p>Olá!</p>
                    <p>Este é um <strong>e-mail de teste</strong> do sistema <strong>PDV Ibix</strong>.</p>
                    <p>Se você recebeu esta mensagem, significa que as configurações de e-mail estão funcionando corretamente! 🎉</p>
                    <p>Você pode agora utilizar o sistema de e-mail para:</p>
                    <ul>
                        <li>Notificar clientes sobre certificados prontos</li>
                        <li>Enviar relatórios automáticos</li>
                        <li>Alertas de sistema</li>
                    </ul>
                </div>
                <div class="footer">
                    <p>Sistema PDV Ibix - Gestão de Vendas PDV</p>
                    <p>Este é um e-mail automático, não responda.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        success = email_service.send_email(
            to=[request.to],
            subject=subject,
            body=body,
            html=html,
            funcao="sistema",
        )
        
        if success:
            return {"success": True, "message": f"E-mail de teste enviado com sucesso para {request.to}"}
        else:
            return {"success": False, "message": "Falha ao enviar e-mail. Verifique as configurações."}
            
    except ValueError as e:
        return {"success": False, "message": str(e)}
    except Exception as e:
        return {"success": False, "message": f"Erro ao enviar e-mail: {str(e)}"}


# ===== FLAG E-MAIL SEPARADO POR CLIENTE (Super Admin) =====

class EmailSeparadoPorClienteResponse(BaseModel):
    ativo: bool


class EmailSeparadoPorClienteUpdate(BaseModel):
    ativo: bool


@configuracoes_router.get("/email/separado-por-cliente/", response_model=EmailSeparadoPorClienteResponse)
def obter_email_separado_por_cliente(db: Session = Depends(get_db)):
    """Retorna se as configurações de e-mail separado por cliente estão ativas (para Cliente Administrador)."""
    cfg = get_configuracao(db, CHAVE_EMAIL_SEPARADO_POR_CLIENTE_ATIVO)
    ativo = bool(cfg and (cfg.valor or "").strip().lower() == "true")
    return EmailSeparadoPorClienteResponse(ativo=ativo)


@configuracoes_router.put("/email/separado-por-cliente/", response_model=EmailSeparadoPorClienteResponse)
def salvar_email_separado_por_cliente(
    payload: EmailSeparadoPorClienteUpdate,
    db: Session = Depends(get_db),
    _superadmin: None = Depends(require_superadmin()),
):
    """Ativa ou desativa configurações de e-mail separado por cliente. Apenas Superadministrador."""
    set_configuracao(
        db,
        CHAVE_EMAIL_SEPARADO_POR_CLIENTE_ATIVO,
        "true" if payload.ativo else "false",
        "Ativar e-mail separado por cliente para Cliente Administrador",
    )
    return EmailSeparadoPorClienteResponse(ativo=payload.ativo)


# ===== ENDPOINTS DE E-MAIL POR FUNÇÃO =====

@configuracoes_router.get("/email/funcoes/", response_model=EmailFuncoesResponse)
def obter_configuracoes_email_funcoes(db: Session = Depends(get_db)):
    """Obter configurações de e-mail por função (remetente por função)."""
    try:
        funcoes = []
        for codigo, label, descricao in get_funcoes_email():
            cfg_from = get_configuracao(db, chave_from(codigo))
            cfg_name = get_configuracao(db, chave_from_name(codigo))
            funcoes.append(EmailFuncaoItem(
                codigo=codigo,
                label=label,
                descricao=descricao,
                from_email=cfg_from.valor if cfg_from else "",
                from_name=cfg_name.valor if cfg_name else "",
            ))
        return EmailFuncoesResponse(funcoes=funcoes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter configurações de e-mail por função: {str(e)}")


@configuracoes_router.post("/email/funcoes/", response_model=EmailFuncoesResponse)
def salvar_configuracoes_email_funcoes(
    payload: EmailFuncoesUpdate,
    db: Session = Depends(get_db),
):
    """Salvar configurações de e-mail por função (remetente por função)."""
    try:
        codigos_validos = set(get_codigos_funcoes_email())
        for item in payload.funcoes:
            if item.codigo not in codigos_validos:
                continue
            if item.from_email is not None:
                set_configuracao(
                    db,
                    chave_from(item.codigo),
                    item.from_email.strip(),
                    f"E-mail remetente para função: {item.codigo}",
                )
            if item.from_name is not None:
                set_configuracao(
                    db,
                    chave_from_name(item.codigo),
                    item.from_name.strip(),
                    f"Nome do remetente para função: {item.codigo}",
                )
        return obter_configuracoes_email_funcoes(db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar configurações de e-mail por função: {str(e)}")


# ===== ENDPOINTS DE ALERTAS E NOTIFICAÇÕES =====

class ConfiguracoesAlertasRequest(BaseModel):
    prazo_cert_alerta: int
    prazo_cert_critico: int
    prazo_contrato_alerta: int
    prazo_contrato_critico: int
    janela_novos_agendamentos: int
    intervalo_atualizacao: int
    notif_agendamento_hoje: bool
    notif_novo_agendamento: bool
    notif_certificado_vencendo: bool
    notif_contrato_vencendo: bool


@configuracoes_router.get("/alertas/")
def obter_configuracoes_alertas(db: Session = Depends(get_db)):
    """Obter configurações de alertas e notificações"""
    try:
        # Buscar todas as configurações de alertas
        configs = {
            'prazo_cert_alerta': int(get_configuracao(db, 'alertas.prazo_cert_alerta').valor) if get_configuracao(db, 'alertas.prazo_cert_alerta') else 15,
            'prazo_cert_critico': int(get_configuracao(db, 'alertas.prazo_cert_critico').valor) if get_configuracao(db, 'alertas.prazo_cert_critico') else 7,
            'prazo_contrato_alerta': int(get_configuracao(db, 'alertas.prazo_contrato_alerta').valor) if get_configuracao(db, 'alertas.prazo_contrato_alerta') else 15,
            'prazo_contrato_critico': int(get_configuracao(db, 'alertas.prazo_contrato_critico').valor) if get_configuracao(db, 'alertas.prazo_contrato_critico') else 7,
            'janela_novos_agendamentos': int(get_configuracao(db, 'alertas.janela_novos_agendamentos').valor) if get_configuracao(db, 'alertas.janela_novos_agendamentos') else 24,
            'intervalo_atualizacao': int(get_configuracao(db, 'alertas.intervalo_atualizacao').valor) if get_configuracao(db, 'alertas.intervalo_atualizacao') else 30,
            'notif_agendamento_hoje': get_configuracao(db, 'notificacoes.agendamento_hoje').valor == 'true' if get_configuracao(db, 'notificacoes.agendamento_hoje') else True,
            'notif_novo_agendamento': get_configuracao(db, 'notificacoes.novo_agendamento').valor == 'true' if get_configuracao(db, 'notificacoes.novo_agendamento') else True,
            'notif_certificado_vencendo': get_configuracao(db, 'notificacoes.certificado_vencendo').valor == 'true' if get_configuracao(db, 'notificacoes.certificado_vencendo') else True,
            'notif_contrato_vencendo': get_configuracao(db, 'notificacoes.contrato_vencendo').valor == 'true' if get_configuracao(db, 'notificacoes.contrato_vencendo') else True
        }
        
        return configs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter configurações de alertas: {str(e)}")


@configuracoes_router.post("/alertas/")
def salvar_configuracoes_alertas(
    configs: ConfiguracoesAlertasRequest,
    db: Session = Depends(get_db)
):
    """Salvar configurações de alertas e notificações"""
    try:
        # Salvar prazos de certificados
        set_configuracao(db, 'alertas.prazo_cert_alerta', str(configs.prazo_cert_alerta), 'Dias de antecedência para alerta de vencimento de certificados')
        set_configuracao(db, 'alertas.prazo_cert_critico', str(configs.prazo_cert_critico), 'Dias para prioridade ALTA em certificados')
        
        # Salvar prazos de contratos
        set_configuracao(db, 'alertas.prazo_contrato_alerta', str(configs.prazo_contrato_alerta), 'Dias de antecedência para alerta de vencimento de contratos')
        set_configuracao(db, 'alertas.prazo_contrato_critico', str(configs.prazo_contrato_critico), 'Dias para prioridade ALTA em contratos')
        
        # Salvar janelas temporais
        set_configuracao(db, 'alertas.janela_novos_agendamentos', str(configs.janela_novos_agendamentos), 'Horas para considerar um agendamento como novo')
        set_configuracao(db, 'alertas.intervalo_atualizacao', str(configs.intervalo_atualizacao), 'Segundos para atualizar notificações automaticamente')
        
        # Salvar tipos de notificações
        set_configuracao(db, 'notificacoes.agendamento_hoje', 'true' if configs.notif_agendamento_hoje else 'false', 'Ativar notificações de agendamentos do dia')
        set_configuracao(db, 'notificacoes.novo_agendamento', 'true' if configs.notif_novo_agendamento else 'false', 'Ativar notificações de novos agendamentos')
        set_configuracao(db, 'notificacoes.certificado_vencendo', 'true' if configs.notif_certificado_vencendo else 'false', 'Ativar notificações de certificados vencendo')
        set_configuracao(db, 'notificacoes.contrato_vencendo', 'true' if configs.notif_contrato_vencendo else 'false', 'Ativar notificações de contratos vencendo')
        
        return {"success": True, "message": "Configurações de alertas salvas com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar configurações: {str(e)}")


# ===== ENDPOINTS DE TEMPLATES =====

class TemplateEmailRequest(BaseModel):
    nome: str
    assunto: Optional[str] = None
    variaveis: Optional[str] = None
    html: str


@configuracoes_router.get("/email/templates/")
def listar_templates(db: Session = Depends(get_db)):
    """Listar templates de e-mail disponíveis"""
    try:
        from pathlib import Path
        
        templates_dir = Path(__file__).parent.parent.parent / 'templates' / 'emails'
        templates_dir.mkdir(parents=True, exist_ok=True)
        
        templates = []
        
        for template_file in templates_dir.glob('*.html'):
            nome = template_file.stem
            
            # Buscar metadados do banco
            assunto_config = get_configuracao(db, f"template_{nome}_assunto")
            variaveis_config = get_configuracao(db, f"template_{nome}_variaveis")
            
            templates.append({
                'nome': nome,
                'assunto': assunto_config.valor if assunto_config else None,
                'variaveis': variaveis_config.valor if variaveis_config else None
            })
        
        return templates
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao listar templates: {str(e)}")


@configuracoes_router.get("/email/templates/{nome}")
def obter_template(nome: str, db: Session = Depends(get_db)):
    """Obter template específico"""
    try:
        from pathlib import Path
        
        template_path = Path(__file__).parent.parent.parent / 'templates' / 'emails' / f'{nome}.html'
        
        if not template_path.exists():
            raise HTTPException(status_code=404, detail="Template não encontrado")
        
        with open(template_path, 'r', encoding='utf-8') as f:
            html = f.read()
        
        # Buscar metadados
        assunto_config = get_configuracao(db, f"template_{nome}_assunto")
        variaveis_config = get_configuracao(db, f"template_{nome}_variaveis")
        
        return {
            'nome': nome,
            'assunto': assunto_config.valor if assunto_config else '',
            'variaveis': variaveis_config.valor if variaveis_config else '',
            'html': html
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter template: {str(e)}")


@configuracoes_router.post("/email/templates/")
def criar_template(
    template: TemplateEmailRequest,
    db: Session = Depends(get_db)
):
    """Criar novo template de e-mail"""
    try:
        import re
        from pathlib import Path
        
        # Validar nome do template
        if not re.match(r'^[a-z0-9_]+$', template.nome):
            raise HTTPException(
                status_code=400,
                detail="Nome inválido. Use apenas letras minúsculas, números e underscore"
            )
        
        templates_dir = Path(__file__).parent.parent.parent / 'templates' / 'emails'
        templates_dir.mkdir(parents=True, exist_ok=True)
        
        template_path = templates_dir / f'{template.nome}.html'
        
        if template_path.exists():
            raise HTTPException(status_code=400, detail="Template já existe")
        
        # Salvar arquivo HTML
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(template.html)
        
        # Salvar metadados no banco
        if template.assunto:
            set_configuracao(db, f"template_{template.nome}_assunto", template.assunto, "Assunto padrão do template")
        
        if template.variaveis:
            set_configuracao(db, f"template_{template.nome}_variaveis", template.variaveis, "Variáveis do template")
        
        return {"success": True, "message": "Template criado com sucesso"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao criar template: {str(e)}")


@configuracoes_router.put("/email/templates/{nome}")
def atualizar_template(
    nome: str,
    template: TemplateEmailRequest,
    db: Session = Depends(get_db)
):
    """Atualizar template de e-mail"""
    try:
        from pathlib import Path
        
        template_path = Path(__file__).parent.parent.parent / 'templates' / 'emails' / f'{nome}.html'
        
        if not template_path.exists():
            raise HTTPException(status_code=404, detail="Template não encontrado")
        
        # Atualizar arquivo HTML
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(template.html)
        
        # Atualizar metadados
        if template.assunto:
            set_configuracao(db, f"template_{nome}_assunto", template.assunto, "Assunto padrão do template")
        
        if template.variaveis:
            set_configuracao(db, f"template_{nome}_variaveis", template.variaveis, "Variáveis do template")
        
        return {"success": True, "message": "Template atualizado com sucesso"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar template: {str(e)}")


@configuracoes_router.delete("/email/templates/{nome}")
def excluir_template(nome: str, db: Session = Depends(get_db)):
    """Excluir template de e-mail"""
    try:
        from pathlib import Path
        
        template_path = Path(__file__).parent.parent.parent / 'templates' / 'emails' / f'{nome}.html'
        
        if not template_path.exists():
            raise HTTPException(status_code=404, detail="Template não encontrado")
        
        # Excluir arquivo
        template_path.unlink()
        
        # Excluir metadados do banco
        assunto_config = get_configuracao(db, f"template_{nome}_assunto")
        if assunto_config:
            db.delete(assunto_config)
        
        variaveis_config = get_configuracao(db, f"template_{nome}_variaveis")
        if variaveis_config:
            db.delete(variaveis_config)
        
        db.commit()
        
        return {"success": True, "message": "Template excluído com sucesso"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao excluir template: {str(e)}")


# --- Configurações SEO / NAP Marketplace (apenas Superadministrador) ---

CHAVES_MARKETPLACE_NAP = {
    "marketplace_nome": "Nome do marketplace (NAP para SEO local)",
    "marketplace_endereco": "Endereço completo (NAP para SEO local)",
    "marketplace_cidade": "Cidade (NAP para SEO local)",
    "marketplace_uf": "UF / Estado (NAP para SEO local)",
    "marketplace_cep": "CEP (NAP para SEO local)",
    "marketplace_telefone": "Telefone (NAP para SEO local)",
}


class MarketplaceNapResponse(BaseModel):
    marketplace_nome: str = ""
    marketplace_endereco: str = ""
    marketplace_cidade: str = ""
    marketplace_uf: str = ""
    marketplace_cep: str = ""
    marketplace_telefone: str = ""


class MarketplaceNapUpdate(BaseModel):
    marketplace_nome: Optional[str] = None
    marketplace_endereco: Optional[str] = None
    marketplace_cidade: Optional[str] = None
    marketplace_uf: Optional[str] = None
    marketplace_cep: Optional[str] = None
    marketplace_telefone: Optional[str] = None


@configuracoes_router.get("/marketplace-nap/", response_model=MarketplaceNapResponse)
def obter_marketplace_nap(
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_superadmin()),
):
    """Obter dados NAP (Nome, Endereço, Telefone) do marketplace para SEO local. Apenas Superadministrador."""
    result = {}
    for chave in CHAVES_MARKETPLACE_NAP:
        c = get_configuracao(db, chave)
        result[chave] = (c.valor or "").strip() if c else ""
    return MarketplaceNapResponse(**result)


@configuracoes_router.put("/marketplace-nap/", response_model=MarketplaceNapResponse)
def salvar_marketplace_nap(
    dados: MarketplaceNapUpdate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_superadmin()),
):
    """Salvar dados NAP do marketplace para SEO local. Apenas Superadministrador."""
    for campo, descricao in CHAVES_MARKETPLACE_NAP.items():
        valor = getattr(dados, campo, None)
        if valor is not None:
            set_configuracao(db, campo, valor.strip(), descricao)
    return obter_marketplace_nap(db=db)


# --- Configurações WhatsApp (apenas Superadministrador) ---
CHAVES_WHATSAPP = ("whatsapp.ativo", "whatsapp.phone_number_id", "whatsapp.token", "whatsapp.verify_token", "whatsapp.business_account_id", "whatsapp.app_secret")


@configuracoes_router.get("/whatsapp/", response_model=ConfiguracaoWhatsAppResponse)
def obter_configuracoes_whatsapp(
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_superadmin()),
):
    """Obter configurações da integração WhatsApp. Apenas Superadministrador."""
    ativo = False
    phone_number_id = None
    verify_token = None
    business_account_id = None
    token_preenchido = False
    for chave in CHAVES_WHATSAPP:
        c = get_configuracao(db, chave)
        if not c:
            continue
        if chave == "whatsapp.ativo":
            ativo = (c.valor or "").strip().lower() in ("1", "true", "sim", "yes")
        elif chave == "whatsapp.phone_number_id":
            phone_number_id = (c.valor or "").strip() or None
        elif chave == "whatsapp.verify_token":
            verify_token = "••••••••" if (c.valor or "").strip() else None
        elif chave == "whatsapp.business_account_id":
            business_account_id = (c.valor or "").strip() or None
        elif chave == "whatsapp.token":
            token_preenchido = bool((c.valor or "").strip())
    c_app = get_configuracao(db, "whatsapp.app_secret")
    app_secret_preenchido = bool(c_app and (c_app.valor or "").strip())
    return ConfiguracaoWhatsAppResponse(
        ativo=ativo,
        phone_number_id=phone_number_id,
        verify_token=verify_token,
        business_account_id=business_account_id,
        token_preenchido=token_preenchido,
        app_secret_preenchido=app_secret_preenchido,
    )


@configuracoes_router.post("/whatsapp/", response_model=ConfiguracaoWhatsAppResponse)
def salvar_configuracoes_whatsapp(
    body: ConfiguracaoWhatsAppRequest,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_superadmin()),
):
    """Salvar configurações da integração WhatsApp. Apenas Superadministrador."""
    set_configuracao(db, "whatsapp.ativo", "1" if body.ativo else "0", "Integração WhatsApp ativa")
    if body.phone_number_id is not None:
        set_configuracao(db, "whatsapp.phone_number_id", (body.phone_number_id or "").strip(), "Phone Number ID (Meta)")
    if body.verify_token is not None:
        set_configuracao(db, "whatsapp.verify_token", (body.verify_token or "").strip(), "Verify token do webhook")
    if body.business_account_id is not None:
        set_configuracao(db, "whatsapp.business_account_id", (body.business_account_id or "").strip(), "WhatsApp Business Account ID")
    if body.token is not None:
        set_configuracao(db, "whatsapp.token", (body.token or "").strip(), "Token de acesso Meta (não logar)")
    if body.app_secret is not None:
        set_configuracao(db, "whatsapp.app_secret", (body.app_secret or "").strip(), "App Secret Meta (validação X-Hub-Signature-256)")
    return obter_configuracoes_whatsapp(db=db)
