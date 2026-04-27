# PDV Ibix - API Landing (formulário Fale conosco)
"""Endpoint público para envio do formulário da landing page. Envia e-mail para o destino configurado (help_center)."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from ...core.logging import log_error, logger
from ...database.connection import get_db
from ...services.email_service import EmailService

router = APIRouter(prefix="/landing", tags=["Landing"])


class FaleConoscoRequest(BaseModel):
    """Schema para o formulário Fale conosco da landing."""
    nome: str
    email: EmailStr
    mensagem: str
    whatsapp: Optional[str] = None
    empresa: Optional[str] = None
    area_atuacao: Optional[str] = None
    consentimento_lgpd: Optional[bool] = None
    consentimento_finalidade: Optional[bool] = None


@router.post("/fale-conosco")
async def fale_conosco(
    dados: FaleConoscoRequest,
    db: Session = Depends(get_db),
):
    """
    Recebe nome, e-mail e mensagem da landing e envia por e-mail.
    Destino: mesmo do help_center (info@certilog.com.br). Público, sem autenticação.
    """
    try:
        logger.info("Fale conosco: handler iniciado")
        html_extra = ""
        if dados.whatsapp and dados.whatsapp.strip():
            html_extra += f"""
        <div class="info-row">
            <div class="info-label">WhatsApp</div>
            <div class="info-value">{dados.whatsapp.strip()}</div>
        </div>"""
        if dados.empresa and dados.empresa.strip():
            html_extra += f"""
        <div class="info-row">
            <div class="info-label">Empresa</div>
            <div class="info-value">{dados.empresa.strip()}</div>
        </div>"""
        if dados.area_atuacao and dados.area_atuacao.strip():
            html_extra += f"""
        <div class="info-row">
            <div class="info-label">Área de atuação</div>
            <div class="info-value">{dados.area_atuacao.strip()}</div>
        </div>"""
        if dados.consentimento_lgpd:
            html_extra += """
        <div class="info-row">
            <div class="info-label">Aceito Política de Privacidade</div>
            <div class="info-value">Sim</div>
        </div>"""
        if dados.consentimento_finalidade:
            html_extra += """
        <div class="info-row">
            <div class="info-label">Autoriza contato comercial</div>
            <div class="info-value">Sim</div>
        </div>"""

        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: 'Inter', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 8px 8px 0 0; text-align: center; }}
        .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 8px 8px; }}
        .info-row {{ background: white; padding: 15px; margin-bottom: 15px; border-radius: 6px; border-left: 4px solid #2c3e50; }}
        .info-label {{ font-weight: 600; color: #2c3e50; margin-bottom: 5px; }}
        .info-value {{ color: #495057; }}
        .message-box {{ background: white; padding: 20px; border-radius: 6px; margin-top: 20px; border: 1px solid #dee2e6; }}
        .footer {{ text-align: center; margin-top: 20px; color: #6c757d; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="header">
        <h2 style="margin: 0;">Landing - Fale conosco</h2>
        <p style="margin: 10px 0 0 0; font-size: 0.9em;">PDV Ibix</p>
    </div>
    <div class="content">
        <div class="info-row">
            <div class="info-label">Nome</div>
            <div class="info-value">{dados.nome}</div>
        </div>
        <div class="info-row">
            <div class="info-label">E-mail</div>
            <div class="info-value">{dados.email}</div>
        </div>
{html_extra}
        <div class="message-box">
            <div class="info-label" style="margin-bottom: 10px;">Mensagem</div>
            <div class="info-value">{dados.mensagem.replace(chr(10), '<br>')}</div>
        </div>
        <div class="footer">
            <p>Enviado pelo formulário da landing page do PDV Ibix.</p>
        </div>
    </div>
</body>
</html>
"""
        text_extra = ""
        if dados.whatsapp and dados.whatsapp.strip():
            text_extra += f"WhatsApp: {dados.whatsapp.strip()}\n"
        if dados.empresa and dados.empresa.strip():
            text_extra += f"Empresa: {dados.empresa.strip()}\n"
        if dados.area_atuacao and dados.area_atuacao.strip():
            text_extra += f"Área de atuação: {dados.area_atuacao.strip()}\n"
        if dados.consentimento_lgpd:
            text_extra += "Aceito Política de Privacidade: Sim\n"
        if dados.consentimento_finalidade:
            text_extra += "Autoriza contato comercial: Sim\n"
        if text_extra:
            text_extra = text_extra + "\n"

        text_body = f"""
Landing - Fale conosco - PDV Ibix
=======================================

Nome: {dados.nome}
E-mail: {dados.email}
{text_extra}Mensagem:
{dados.mensagem}

---
Enviado pelo formulário da landing page do PDV Ibix.
"""
        email_service = EmailService(db)
        sucesso = email_service.send_email(
            to=["info@certilog.com.br"],
            subject=f"[PDV Ibix Landing] Fale conosco - {dados.nome}",
            body=text_body,
            html=html_body,
            funcao="help_center",
        )
        if not sucesso:
            log_error("Erro ao enviar email do formulário landing")
            raise HTTPException(
                status_code=500,
                detail="Erro ao enviar mensagem. Por favor, tente novamente ou entre em contato diretamente pelo e-mail.",
            )

        return {
            "success": True,
            "message": "Mensagem enviada com sucesso! Entraremos em contato em breve.",
        }
    except HTTPException:
        raise
    except Exception as e:
        log_error(f"Erro ao processar formulário landing: {e}")
        raise HTTPException(
            status_code=500,
            detail="Erro ao processar sua mensagem. Por favor, tente novamente.",
        )
