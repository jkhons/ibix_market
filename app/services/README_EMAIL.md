# 📧 MÓDULO DE E-MAIL - CERTIPESO

Sistema completo de envio de e-mails com SMTP integrado ao PDV Ibix.

---

## 📋 CARACTERÍSTICAS

✅ **Envio de e-mails via SMTP**
✅ **Suporte a TLS/SSL**
✅ **Templates HTML**
✅ **Anexos de arquivos**
✅ **Teste de conexão**
✅ **Interface de configuração**
✅ **Múltiplos destinatários (To, CC, BCC)**

---

## 🚀 CONFIGURAÇÃO

### 1. Acessar Página de Configurações

Acesse `/configuracoes` no sistema e role até a seção **"Configurações de E-mail"**.

### 2. Preencher Dados SMTP

#### Gmail
```
Servidor: smtp.gmail.com
Porta: 587
Usuário: seu-email@gmail.com
Senha: Senha de App (obrigatório)
TLS: ✅ Ativado
SSL: ❌ Desativado
```

**Como gerar senha de app no Gmail:**
1. Acesse https://myaccount.google.com/security
2. Ative a verificação em 2 etapas
3. Vá em "Senhas de app"
4. Gere uma senha para "E-mail"
5. Use essa senha no campo "Senha"

#### Outlook/Office 365
```
Servidor: smtp.office365.com
Porta: 587
Usuário: seu-email@outlook.com
Senha: Sua senha normal
TLS: ✅ Ativado
SSL: ❌ Desativado
```

#### Yahoo
```
Servidor: smtp.mail.yahoo.com
Porta: 587
Usuário: seu-email@yahoo.com
Senha: Senha de App
TLS: ✅ Ativado
SSL: ❌ Desativado
```

### 3. Testar Configuração

Após salvar, clique em:
- **"Testar Conexão"** - Verifica se o servidor está acessível
- **"Enviar E-mail de Teste"** - Envia um e-mail real de teste

---

## 💻 USO NO CÓDIGO

### Importar o Serviço

```python
from app.services.email_service import EmailService
from app.database.connection import get_db
```

### Envio Simples

```python
def minha_funcao(db: Session):
    email_service = EmailService(db)
    
    success = email_service.send_email(
        to=['cliente@email.com'],
        subject='Assunto do E-mail',
        body='Corpo do e-mail em texto',
        html='<h1>Corpo em HTML</h1>'  # Opcional
    )
    
    if success:
        print("E-mail enviado!")
    else:
        print("Erro ao enviar e-mail")
```

### Envio com Múltiplos Destinatários

```python
email_service.send_email(
    to=['cliente1@email.com', 'cliente2@email.com'],
    cc=['gerente@email.com'],
    bcc=['auditoria@email.com'],
    subject='Relatório Mensal',
    body='Segue relatório em anexo'
)
```

### Envio com Anexos

```python
email_service.send_email(
    to=['cliente@email.com'],
    subject='Certificado em Anexo',
    body='Segue certificado solicitado',
    attachments=[
        '/caminho/para/certificado.pdf',
        '/caminho/para/relatorio.xlsx'
    ]
)
```

### Usando Templates HTML

```python
# Template já existe em: app/templates/emails/certificado_pronto.html

success = email_service.send_template_email(
    to=['cliente@email.com'],
    template_name='certificado_pronto',
    context={
        'certificate_number': 'CERT-2025-001',
        'client_name': 'João Silva',
        'download_link': 'https://sistema.com/download/cert-001'
    },
    subject='Certificado CERT-2025-001 Pronto'
)
```

### Função Rápida

```python
from app.services.email_service import send_email_quick

# Envio rápido sem instanciar a classe
send_email_quick(
    db=db,
    to=['cliente@email.com'],
    subject='Notificação',
    body='Sua mensagem aqui'
)
```

### Função para Certificado Pronto

```python
from app.services.email_service import send_certificate_ready_email

# Envia e-mail de certificado pronto usando template
send_certificate_ready_email(
    db=db,
    to='cliente@email.com',
    certificate_number='CERT-2025-001',
    client_name='João Silva',
    download_link='https://sistema.com/download/cert-001'
)
```

---

## 🎨 CRIAR NOVOS TEMPLATES

### 1. Criar arquivo HTML

Criar em: `app/templates/emails/seu_template.html`

```html
<!DOCTYPE html>
<html>
<head>
    <style>
        /* Seus estilos CSS */
    </style>
</head>
<body>
    <h1>Olá, {{nome_cliente}}!</h1>
    <p>Seu pedido {{numero_pedido}} está pronto.</p>
    <a href="{{link}}">Clique aqui</a>
</body>
</html>
```

### 2. Usar no código

```python
email_service.send_template_email(
    to=['cliente@email.com'],
    template_name='seu_template',  # Sem extensão .html
    context={
        'nome_cliente': 'João',
        'numero_pedido': '12345',
        'link': 'https://...'
    },
    subject='Seu Pedido Está Pronto'
)
```

---

## 🔧 API ENDPOINTS

### GET `/api/v1/configuracoes/email/`
Retorna configurações de e-mail atuais

**Resposta:**
```json
{
    "email_host": "smtp.gmail.com",
    "email_port": "587",
    "email_username": "sistema@gmail.com",
    "email_from": "noreply@certipeso.com",
    "email_from_name": "PDV Ibix",
    "email_use_tls": "true",
    "email_use_ssl": "false"
}
```

### POST `/api/v1/configuracoes/email/`
Salva configurações de e-mail

**Body:**
```json
{
    "email_host": "smtp.gmail.com",
    "email_port": "587",
    "email_username": "sistema@gmail.com",
    "email_password": "senha-de-app",
    "email_from": "noreply@certipeso.com",
    "email_from_name": "PDV Ibix",
    "email_use_tls": "true",
    "email_use_ssl": "false"
}
```

### POST `/api/v1/configuracoes/email/test-connection/`
Testa conexão com servidor SMTP

**Resposta:**
```json
{
    "success": true,
    "message": "Conexão estabelecida com sucesso!"
}
```

### POST `/api/v1/configuracoes/email/send-test/`
Envia e-mail de teste

**Body:**
```json
{
    "to": "destino@email.com"
}
```

**Resposta:**
```json
{
    "success": true,
    "message": "E-mail de teste enviado com sucesso"
}
```

---

## 🛠️ TROUBLESHOOTING

### Erro: "Configurações de e-mail faltando"
**Solução:** Configure todas as informações obrigatórias na página de configurações.

### Erro: "Erro de autenticação"
**Solução:** 
- Gmail: Use senha de app, não a senha normal
- Verifique se o usuário e senha estão corretos
- Verifique se autenticação de 2 fatores está ativa (Gmail)

### Erro: "Timeout" ou "Conexão recusada"
**Solução:**
- Verifique o servidor SMTP e porta
- Verifique firewall/antivírus
- Tente portas alternativas: 587 (TLS), 465 (SSL), 25 (não criptografado)

### E-mails não estão sendo recebidos
**Solução:**
- Verifique caixa de spam
- Verifique se o e-mail "De" está correto
- Teste com diferentes provedores de e-mail
- Verifique logs do servidor

### Gmail bloqueando acesso
**Solução:**
1. Ative verificação em 2 etapas
2. Gere uma senha de app
3. Use a senha de app no lugar da senha normal
4. Link: https://myaccount.google.com/apppasswords

---

## 📊 BOAS PRÁTICAS

### ✅ Faça
- Use sempre senhas de app (Gmail)
- Configure TLS para segurança
- Teste antes de usar em produção
- Use templates HTML para e-mails profissionais
- Valide e-mails antes de enviar
- Trate erros adequadamente

### ❌ Não Faça
- Não use senhas normais no Gmail
- Não envie spam
- Não exponha senhas em logs
- Não envie e-mails sem teste
- Não ignore erros de envio

---

## 📝 EXEMPLOS PRÁTICOS

### Notificar Cliente sobre Certificado

```python
from app.services.email_service import EmailService

def notificar_cliente_certificado(db, certificado):
    email_service = EmailService(db)
    
    html = f"""
    <h2>Certificado {certificado.numero} Pronto!</h2>
    <p>Olá {certificado.cliente.nome},</p>
    <p>Seu certificado está disponível para download.</p>
    <a href="https://sistema.com/download/{certificado.id}">Baixar Agora</a>
    """
    
    email_service.send_email(
        to=[certificado.cliente.email],
        subject=f'Certificado {certificado.numero} Pronto',
        body='Seu certificado está pronto',
        html=html
    )
```

### Enviar Relatório Mensal

```python
def enviar_relatorio_mensal(db, mes, ano):
    email_service = EmailService(db)
    
    # Gerar PDF do relatório
    pdf_path = gerar_relatorio_pdf(mes, ano)
    
    email_service.send_email(
        to=['gerente@empresa.com'],
        cc=['diretor@empresa.com'],
        subject=f'Relatório Mensal - {mes}/{ano}',
        body='Segue relatório em anexo',
        attachments=[pdf_path]
    )
```

### Alerta de Sistema

```python
def enviar_alerta_sistema(db, mensagem):
    from app.services.email_service import send_email_quick
    
    send_email_quick(
        db=db,
        to=['admin@certipeso.com'],
        subject='⚠️ Alerta de Sistema',
        body=f'Alerta: {mensagem}',
        html=f'<h3 style="color: red;">⚠️ ALERTA</h3><p>{mensagem}</p>'
    )
```

---

## 🔐 SEGURANÇA

- ✅ Senhas são armazenadas no banco de dados
- ✅ Use HTTPS em produção
- ✅ Não exponha senhas em logs
- ✅ Use senhas de app quando possível
- ✅ Valide destinatários antes de enviar

---

## 📞 SUPORTE

**Dúvidas:** Consulte a documentação do seu provedor de e-mail
**Problemas:** Verifique logs do sistema em `/logs`

---

**Desenvolvido para o PDV Ibix (desenvolvedor: Automscale)**  
**Versão:** 1.0  
**Data:** 10 de outubro de 2025

