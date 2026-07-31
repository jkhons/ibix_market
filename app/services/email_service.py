# PDV Ibix - Serviço de E-mail
import os
import smtplib
import ssl
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.email_funcoes import (
    CHAVE_EMAIL_SEPARADO_POR_CLIENTE_ATIVO,
    chave_email_cliente_from,
    chave_email_cliente_from_name,
    chave_from,
    chave_from_name,
    get_codigos_funcoes_email,
)
from app.core.logging import log_error


class EmailService:
    """Serviço para envio de e-mails"""
    
    def __init__(self, db: Session = None):
        """
        Inicializa o serviço de e-mail
        
        Args:
            db: Sessão do banco de dados para buscar configurações
        """
        self.db = db
        self._config = None
    
    def _get_config(self) -> Dict[str, str]:
        """Busca configurações de e-mail do banco de dados"""
        if not self.db:
            raise ValueError("Sessão do banco de dados não fornecida")
        
        if self._config:
            return self._config
        
        from ..models.configuracao import Configuracao
        
        # Buscar configurações do banco
        config_keys = [
            'email_host',
            'email_port',
            'email_username',
            'email_password',
            'email_from',
            'email_from_name',
            'email_use_tls',
            'email_use_ssl'
        ]
        
        configs = self.db.query(Configuracao).filter(
            Configuracao.chave.in_(config_keys)
        ).all()
        
        config_dict = {c.chave: c.valor for c in configs}
        
        # Validar configurações obrigatórias
        required = ['email_host', 'email_port', 'email_username', 'email_password', 'email_from']
        missing = [k for k in required if k not in config_dict]
        
        if missing:
            raise ValueError(f"Configurações de e-mail faltando: {', '.join(missing)}")
        
        self._config = config_dict
        return self._config

    def _get_remetente(
        self,
        funcao: Optional[str] = None,
        cliente_id: Optional[int] = None,
    ) -> Tuple[str, str]:
        """Retorna (email_from, from_name): cliente (se flag ativa) -> função -> global."""
        from ..models.configuracao import Configuracao

        config = self._get_config()
        default_email = config["email_from"]
        default_name = config.get("email_from_name", "PDV Ibix")

        # 1) Se flag ativa e cliente_id informado, tentar remetente do cliente
        if cliente_id is not None:
            cfg_flag = self.db.query(Configuracao).filter(
                Configuracao.chave == CHAVE_EMAIL_SEPARADO_POR_CLIENTE_ATIVO
            ).first()
            if cfg_flag and (cfg_flag.valor or "").strip().lower() == "true":
                cfg_from = self.db.query(Configuracao).filter(
                    Configuracao.chave == chave_email_cliente_from(cliente_id)
                ).first()
                cfg_name = self.db.query(Configuracao).filter(
                    Configuracao.chave == chave_email_cliente_from_name(cliente_id)
                ).first()
                from_val = (cfg_from.valor or "").strip() if cfg_from else ""
                if from_val:
                    return from_val, (cfg_name.valor or "").strip() if cfg_name else ""

        # 2) Remetente por função ou global
        if not funcao or funcao not in get_codigos_funcoes_email():
            return default_email, default_name
        cfg_from = self.db.query(Configuracao).filter(Configuracao.chave == chave_from(funcao)).first()
        cfg_name = self.db.query(Configuracao).filter(Configuracao.chave == chave_from_name(funcao)).first()
        from_val = (cfg_from.valor or "").strip() if cfg_from else ""
        if from_val:
            return from_val, (cfg_name.valor or "").strip() if cfg_name else ""
        return default_email, default_name

    def send_email(
        self,
        to: List[str],
        subject: str,
        body: str,
        html: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[str]] = None,
        funcao: Optional[str] = None,
        cliente_id: Optional[int] = None,
    ) -> bool:
        """
        Envia um e-mail

        Args:
            to: Lista de destinatários
            subject: Assunto do e-mail
            body: Corpo do e-mail em texto plano
            html: Corpo do e-mail em HTML (opcional)
            cc: Lista de destinatários em cópia (opcional)
            bcc: Lista de destinatários em cópia oculta (opcional)
            attachments: Lista de caminhos de arquivos para anexar (opcional)
            funcao: Código da função (certificados, nota_fiscal, etc.) para usar remetente configurado
            cliente_id: ID do cliente para remetente por cliente (quando flag ativa)

        Returns:
            bool: True se enviado com sucesso, False caso contrário
        """
        try:
            config = self._get_config()
            email_from, from_name = self._get_remetente(funcao=funcao, cliente_id=cliente_id)

            # Criar mensagem
            message = MIMEMultipart('alternative')
            message['Subject'] = subject
            message['From'] = f"{from_name} <{email_from}>"
            message['To'] = ', '.join(to)
            
            if cc:
                message['Cc'] = ', '.join(cc)
            
            # Adicionar corpo em texto plano
            part_text = MIMEText(body, 'plain', 'utf-8')
            message.attach(part_text)
            
            # Adicionar corpo em HTML se fornecido
            if html:
                part_html = MIMEText(html, 'html', 'utf-8')
                message.attach(part_html)
            
            # Adicionar anexos se fornecidos
            if attachments:
                for file_path in attachments:
                    if os.path.exists(file_path):
                        with open(file_path, 'rb') as file:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(file.read())
                            encoders.encode_base64(part)
                            part.add_header(
                                'Content-Disposition',
                                f'attachment; filename= {Path(file_path).name}'
                            )
                            message.attach(part)
            
            # Preparar lista completa de destinatários
            all_recipients = to.copy()
            if cc:
                all_recipients.extend(cc)
            if bcc:
                all_recipients.extend(bcc)
            
            # Configurar conexão SMTP
            use_tls = config.get('email_use_tls', 'true').lower() == 'true'
            use_ssl = config.get('email_use_ssl', 'false').lower() == 'true'
            port = int(config['email_port'])
            
            # Enviar e-mail (usar remetente por função no envelope)
            if use_ssl:
                # Conexão SSL
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(config['email_host'], port, context=context) as server:
                    server.login(config['email_username'], config['email_password'])
                    server.sendmail(email_from, all_recipients, message.as_string())
            else:
                # Conexão normal com STARTTLS
                with smtplib.SMTP(config['email_host'], port) as server:
                    if use_tls:
                        context = ssl.create_default_context()
                        server.starttls(context=context)
                    server.login(config['email_username'], config['email_password'])
                    server.sendmail(email_from, all_recipients, message.as_string())
            
            return True

        except Exception as e:
            subj_preview = (subject or "")[:120]
            log_error(
                "EmailService.send_email falhou "
                f"(funcao={funcao!r}, cliente_id={cliente_id}, "
                f"destinatarios={len(to or [])}, assunto={subj_preview!r})",
                exc_info=e,
            )
            return False
    
    def send_template_email(
        self,
        to: List[str],
        template_name: str,
        context: Dict,
        subject: str,
        funcao: Optional[str] = None,
        cliente_id: Optional[int] = None,
        **kwargs
    ) -> bool:
        """
        Envia e-mail usando template HTML

        Args:
            to: Lista de destinatários
            template_name: Nome do template (ex: 'nota_fiscal')
            context: Dicionário com variáveis do template
            subject: Assunto do e-mail
            funcao: Código da função para remetente configurado (ex: certificados)
            cliente_id: ID do cliente para remetente por cliente (quando flag ativa)
            **kwargs: Argumentos adicionais para send_email

        Returns:
            bool: True se enviado com sucesso
        """
        try:
            # Carregar template
            template_path = Path(__file__).parent.parent / 'templates' / 'emails' / f'{template_name}.html'
            
            if not template_path.exists():
                return False
            
            with open(template_path, 'r', encoding='utf-8') as f:
                html_template = f.read()
            
            # Substituir variáveis no template
            for key, value in context.items():
                html_template = html_template.replace(f'{{{{{key}}}}}', str(value))
            
            # Criar versão texto (simples)
            text_body = self._html_to_text(html_template)
            
            # Enviar e-mail
            kwargs.setdefault("funcao", funcao)
            kwargs.setdefault("cliente_id", cliente_id)
            return self.send_email(
                to=to,
                subject=subject,
                body=text_body,
                html=html_template,
                **kwargs
            )

        except Exception as e:
            log_error(
                f"EmailService.send_template_email falhou (template={template_name!r})",
                exc_info=e,
            )
            return False

    def send_template_html_string(
        self,
        to: List[str],
        html_template: str,
        context: Dict,
        subject: str,
        funcao: Optional[str] = None,
        cliente_id: Optional[int] = None,
        **kwargs,
    ) -> bool:
        """
        Igual a send_template_email, mas recebe o HTML já carregado (ex.: override em configuracoes).
        """
        try:
            html_body = html_template
            for key, value in context.items():
                html_body = html_body.replace(f"{{{{{key}}}}}", str(value))
            text_body = self._html_to_text(html_body)
            kwargs.setdefault("funcao", funcao)
            kwargs.setdefault("cliente_id", cliente_id)
            return self.send_email(
                to=to,
                subject=subject,
                body=text_body,
                html=html_body,
                **kwargs,
            )
        except Exception as e:
            log_error(
                "EmailService.send_template_html_string falhou",
                exc_info=e,
            )
            return False

    def _html_to_text(self, html: str) -> str:
        """Converte HTML simples para texto"""
        # Remover tags HTML básicas
        import re
        text = re.sub('<[^<]+?>', '', html)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def test_connection(self) -> tuple[bool, str]:
        """
        Testa a conexão com o servidor SMTP
        
        Returns:
            tuple: (sucesso, mensagem)
        """
        try:
            config = self._get_config()
            
            use_ssl = config.get('email_use_ssl', 'false').lower() == 'true'
            use_tls = config.get('email_use_tls', 'true').lower() == 'true'
            port = int(config['email_port'])
            
            if use_ssl:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(config['email_host'], port, context=context, timeout=10) as server:
                    server.login(config['email_username'], config['email_password'])
                    return True, "Conexão estabelecida com sucesso!"
            else:
                with smtplib.SMTP(config['email_host'], port, timeout=10) as server:
                    if use_tls:
                        context = ssl.create_default_context()
                        server.starttls(context=context)
                    server.login(config['email_username'], config['email_password'])
                    return True, "Conexão estabelecida com sucesso!"
                    
        except smtplib.SMTPAuthenticationError:
            return False, "Erro de autenticação. Verifique usuário e senha."
        except smtplib.SMTPException as e:
            return False, f"Erro SMTP: {str(e)}"
        except Exception as e:
            return False, f"Erro ao conectar: {str(e)}"


# Funções auxiliares para uso fácil
def send_email_quick(
    db: Session,
    to: List[str],
    subject: str,
    body: str,
    html: Optional[str] = None,
    funcao: Optional[str] = None,
    cliente_id: Optional[int] = None,
) -> bool:
    """Função rápida para enviar e-mail. funcao: código da função; cliente_id: remetente por cliente quando flag ativa."""
    service = EmailService(db)
    return service.send_email(to, subject, body, html, funcao=funcao, cliente_id=cliente_id)


