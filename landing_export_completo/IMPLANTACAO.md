# Guia de Implantação – Landing Page em Outro Servidor/Produto

Este diretório contém uma **cópia completa** da landing page do Ibix (páginas, CSS, header, footer, formulários) para você implantar em outro servidor ou usar como base para outro produto.

---

## 1. Estrutura do pacote

```
landing_export_completo/
├── IMPLANTACAO.md          ← Este arquivo
├── templates/
│   ├── landing.html        ← Página inicial (hero, oferta, contato, sobre)
│   ├── representantes-revenda.html
│   ├── cadastro.html       ← Página de cadastro público (register_public)
│   ├── politica-privacidade.html
│   ├── termos-de-uso.html
│   └── components/
│       ├── landing_header.html
│       └── landing_header_styles.html
└── static/
    ├── css/landing/
    │   ├── dashboard.css   ← Bootstrap + grid (base)
    │   ├── certipeso.css   ← Cores e componentes (--certipeso-primary, etc.)
    │   └── header.css      ← Navbar e botões
    └── img/
        ├── landing/
        │   └── logoSfundo.png
        └── icons/
            └── icon-48x48.png
```

---

## 2. O que substituir para outro produto/servidor

### 2.1 Variáveis de template (Jinja2)

Se o seu servidor usar **Jinja2** (Flask, FastAPI com Jinja2, etc.), passe no contexto:

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `_base` ou `base_url` | URL base do site (para links e assets) | `https://meusite.com.br` ou `""` |
| `contact_telefone` | Telefone exibido na seção Contato | `(14) 99999-9999` |
| `contact_whatsapp` | Mesmo ou outro número para exibição | `(14) 99999-9999` |
| `contact_whatsapp_link` | Número só dígitos para link WhatsApp | `5514999999999` |
| `show_representante_btn` | Mostrar botão "Representante" no header (apenas em `representantes-revenda.html` use `false`) | `true` / `false` |

Em **landing.html** a linha `{% set _base = (base_url or '') %}` usa `base_url` se existir; caso contrário, use `_base` no contexto.

### 2.2 Substituição em texto (busca e troca)

Para **outro produto**, faça busca e troca nos HTML e, se quiser, nos CSS:

| Buscar | Trocar por |
|--------|------------|
| `Ibix` | Nome do seu produto |
| `PDV Ibix` | Nome do sistema (títulos, meta, rodapé) |
| `Automscale` / `automscale.com.br` | Sua empresa / site |
| `info@certilog.com.br` | E-mail de destino do formulário e termos |
| `R$ 199,00`, `15 dias`, `R$ 70,00` | Seus preços e condições |
| `2022` / `2023` / `2026` | Ano atual no copyright e ofertas |

### 2.3 Imagens

- **Logo:** substitua `static/img/landing/logoSfundo.png` pela logo do seu produto (recomendado: fundo transparente, altura ~64px no header).
- **Favicon:** substitua `static/img/icons/icon-48x48.png` pelo ícone do seu site (48x48 ou múltiplos tamanhos).

### 2.4 Cores (opcional)

No **certipeso.css** as variáveis principais são:

- `--certipeso-primary: #2c3e50`
- `--certipeso-secondary: #34495e`

Altere para a cor da sua marca. O header e botões usam essas variáveis (e `--cp-primary` que referencia `--certipeso-primary`).

---

## 3. Rotas / URLs esperadas

A landing e os links internos assumem estas rotas. Configure no seu servidor:

| Rota | Arquivo / ação |
|------|-----------------|
| `/` ou `/index.html` | `landing.html` |
| `/representantes` | `representantes-revenda.html` |
| `/cadastro` | `cadastro.html` |
| `/login` | Sua página de login |
| `/politica-privacidade` | `politica-privacidade.html` (ou conteúdo equivalente) |
| `/termos-de-uso` | `termos-de-uso.html` (ou conteúdo equivalente) |

**Observação:** `politica-privacidade.html` e `termos-de-uso.html` **estendem** `base.html` (layout com sidebar/navbar do app). No novo servidor você pode:
- usar o mesmo layout (copiando também `base.html` e dependências), ou
- criar uma base mínima só com CSS (dashboard + certipeso + header) e colar o conteúdo do `{% block content %}`, ou
- servir essas páginas com outro sistema (CMS, estático, etc.).

---

## 4. Formulário “Fale conosco”

O formulário na landing envia um **POST** para:

```
POST /api/v1/landing/fale-conosco
Content-Type: application/json
```

**Corpo (JSON):**

- `nome` (string, obrigatório)
- `email` (string, obrigatório)
- `mensagem` (string, obrigatório)
- `whatsapp` (string, opcional)
- `empresa` (string, opcional)
- `area_atuacao` (string, opcional)
- `consentimento_lgpd` (boolean, opcional)
- `consentimento_finalidade` (boolean, opcional)

**Resposta de sucesso (200):**

```json
{ "success": true, "message": "Mensagem enviada com sucesso! Entraremos em contato em breve." }
```

No novo servidor você pode:

1. **Implementar o mesmo endpoint** (ex.: FastAPI/Flask) e enviar o e-mail para o seu endereço (trocar `info@certilog.com.br` pelo seu).
2. **Apontar o `fetch()` no JavaScript** para outra URL (ex.: `/api/contato` ou um serviço externo). No `landing.html`, localize:
   `fetch("{{ _base }}/api/v1/landing/fale-conosco", ...)`  
   e altere para a URL do seu backend.

---

## 5. Página de cadastro (`cadastro.html`)

A página de cadastro envia **POST** para:

```
POST /api/v1/auth/register/public
Content-Type: application/json
```

Com campos: `nome`, `email`, `password`, `confirm_password`, `nome_empresa`, `cnpj`, `cep`, `endereco`, `cidade`, `uf`, `contato`, `telefone`, `codigo_promocional` (opcional).

No novo servidor:

- Implemente esse endpoint no seu backend (criação de empresa + usuário administrador), ou
- Altere o `action`/`fetch` para a sua API de cadastro e ajuste os campos conforme necessário.

Há também validação de **código promocional** via `GET /api/v1/codigos-desconto/validar/{codigo}`; você pode remover ou apontar para o seu sistema.

---

## 6. Include do header

Nos templates, o header é incluído com:

```jinja2
{% include 'components/landing_header.html' %}
```

A pasta de templates do seu projeto deve ter:

- `landing.html` (e demais páginas) na raiz do diretório de templates.
- `components/landing_header.html` dentro do mesmo diretório de templates.

Se a sua engine usar outro diretório base, ajuste o caminho do `include` (ex.: `components/landing_header.html` ou `templates/components/landing_header.html`, conforme a configuração).

---

## 7. Ordem de carregamento do CSS

No `<head>` das páginas, carregue na ordem:

1. `static/css/landing/dashboard.css` (base Bootstrap/grid)
2. `static/css/landing/certipeso.css` (variáveis e componentes)
3. `static/css/landing/header.css` (navbar e botões)

As fontes usam **Inter** do Google Fonts (já referenciadas nos HTML).

---

## 8. Uso sem motor de templates (HTML estático)

Se você **não** usar Jinja2:

1. Substitua em todos os arquivos:
   - `{{ _base }}` → sua URL base (ex: `https://meusite.com.br`) ou string vazia ``
   - `{% set _base = (base_url or '') %}` → apague a linha
   - `{% include 'components/landing_header.html' %}` → cole o conteúdo do arquivo `components/landing_header.html` (e faça a troca de `{{ _base }}` nesse conteúdo também)
   - `{% if ... %}` / `{% endif %}` (blocos de contato e representante) → deixe só o HTML que deseja exibir ou apague o bloco condicional
2. No JavaScript do formulário “Fale conosco”, troque a URL do `fetch` para o endpoint real do seu backend.
3. Faça as trocas de texto (nome do produto, empresa, e-mail, etc.) conforme a seção 2.2.

---

## 9. Checklist rápido

- [ ] Copiar `static/` para a pasta de arquivos estáticos do seu servidor.
- [ ] Copiar `templates/` para a pasta de templates (e ajustar include/base se necessário).
- [ ] Definir `_base` / `base_url` e variáveis de contato no contexto.
- [ ] Substituir nome do produto, empresa, e-mails e telefones.
- [ ] Trocar logo e favicon.
- [ ] Implementar ou redirecionar `POST /api/v1/landing/fale-conosco` (e, se usar, o cadastro e códigos promocionais).
- [ ] Ajustar política de privacidade e termos de uso (conteúdo e layout).
- [ ] Testar links (/, /cadastro, /login, /representantes, /politica-privacidade, /termos-de-uso) e formulário de contato.

Com isso, você terá a mesma landing em outro servidor ou adaptada para outro produto.

---

## 10. Exemplo de endpoint “Fale conosco” (FastAPI)

Se você usar FastAPI no novo servidor, pode criar algo assim para o formulário:

```python
from fastapi import APIRouter
from pydantic import BaseModel, EmailStr
from typing import Optional

router = APIRouter(prefix="/api/v1/landing", tags=["Landing"])

class FaleConoscoRequest(BaseModel):
    nome: str
    email: EmailStr
    mensagem: str
    whatsapp: Optional[str] = None
    empresa: Optional[str] = None
    area_atuacao: Optional[str] = None
    consentimento_lgpd: Optional[bool] = None
    consentimento_finalidade: Optional[bool] = None

@router.post("/fale-conosco")
async def fale_conosco(dados: FaleConoscoRequest):
    # Aqui: enviar e-mail (SMTP, SendGrid, etc.) para seu destino
    # to = ["seu-email@dominio.com"]
    return {"success": True, "message": "Mensagem enviada com sucesso! Entraremos em contato em breve."}
```

Registre o router no app e sirva os arquivos estáticos da pasta `static/` e as rotas que renderizam os templates.
