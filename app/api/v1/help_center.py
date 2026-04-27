# PDV Ibix - API Help Center
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from ...core.logging import log_error
from ...database.connection import get_db
from ...services.email_service import EmailService

router = APIRouter(prefix="/api/v1/help-center", tags=["help-center"])

class ContatoRequest(BaseModel):
    """Schema para requisição de contato"""
    nome: str
    email: EmailStr
    telefone: Optional[str] = None
    assunto: str
    mensagem: str

@router.post("/contato")
async def enviar_contato(
    dados: ContatoRequest,
    db: Session = Depends(get_db)
):
    """
    Endpoint para receber formulário de contato e enviar por email
    """
    try:
        # Mapear assunto para texto legível
        assuntos_map = {
            "duvida_tecnica": "Dúvida Técnica",
            "problema_sistema": "Problema no Sistema",
            "solicitacao_suporte": "Solicitação de Suporte",
            "sugestao": "Sugestão de Melhoria",
            "outros": "Outros"
        }
        assunto_texto = assuntos_map.get(dados.assunto, dados.assunto)
        
        # Preparar corpo do email em HTML
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: 'Inter', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: #3b7ddd;
            color: white;
            padding: 20px;
            border-radius: 8px 8px 0 0;
            text-align: center;
        }}
        .content {{
            background: #f8f9fa;
            padding: 30px;
            border-radius: 0 0 8px 8px;
        }}
        .info-row {{
            background: white;
            padding: 15px;
            margin-bottom: 15px;
            border-radius: 6px;
            border-left: 4px solid #3b7ddd;
        }}
        .info-label {{
            font-weight: 600;
            color: #3b7ddd;
            margin-bottom: 5px;
        }}
        .info-value {{
            color: #495057;
        }}
        .message-box {{
            background: white;
            padding: 20px;
            border-radius: 6px;
            margin-top: 20px;
            border: 1px solid #dee2e6;
        }}
        .footer {{
            text-align: center;
            margin-top: 20px;
            color: #6c757d;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h2 style="margin: 0;">📧 Nova Mensagem - Central de Ajuda</h2>
        <p style="margin: 10px 0 0 0; font-size: 0.9em;">PDV Ibix</p>
    </div>
    
    <div class="content">
        <div class="info-row">
            <div class="info-label">👤 Nome:</div>
            <div class="info-value">{dados.nome}</div>
        </div>
        
        <div class="info-row">
            <div class="info-label">📧 Email:</div>
            <div class="info-value">{dados.email}</div>
        </div>
        
        {'<div class="info-row"><div class="info-label">📱 Telefone:</div><div class="info-value">' + dados.telefone + '</div></div>' if dados.telefone else ''}
        
        <div class="info-row">
            <div class="info-label">📋 Assunto:</div>
            <div class="info-value">{assunto_texto}</div>
        </div>
        
        <div class="message-box">
            <div class="info-label" style="margin-bottom: 10px;">💬 Mensagem:</div>
            <div class="info-value">{dados.mensagem.replace(chr(10), '<br>')}</div>
        </div>
        
        <div class="footer">
            <p>Esta mensagem foi enviada através do formulário de contato da Central de Ajuda do PDV Ibix.</p>
            <p style="font-size: 0.85em; color: #adb5bd;">PDV Ibix - Sistema de vendas e gestão</p>
        </div>
    </div>
</body>
</html>
"""
        
        # Preparar corpo do email em texto plano
        text_body = f"""
Nova Mensagem - Central de Ajuda PDV Ibix
==========================================

Nome: {dados.nome}
Email: {dados.email}
{f'Telefone: {dados.telefone}' if dados.telefone else ''}
Assunto: {assunto_texto}

Mensagem:
{dados.mensagem}

---
Esta mensagem foi enviada através do formulário de contato da Central de Ajuda do PDV Ibix.
"""
        
        # Enviar email
        email_service = EmailService(db)
        
        sucesso = email_service.send_email(
            to=["info@certilog.com.br"],
            subject=f"[PDV Ibix Help Center] {assunto_texto} - {dados.nome}",
            body=text_body,
            html=html_body,
            funcao="help_center",
        )
        
        if sucesso:
            return {
                "success": True,
                "message": "Mensagem enviada com sucesso! Entraremos em contato em breve."
            }
        else:
            log_error("❌ Erro ao enviar email de contato")
            raise HTTPException(
                status_code=500,
                detail="Erro ao enviar mensagem. Por favor, tente novamente ou entre em contato diretamente pelo email."
            )
            
    except HTTPException:
        raise
    except Exception as e:
        log_error(f"❌ Erro ao processar formulário de contato: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Erro ao processar sua mensagem. Por favor, tente novamente."
        )

