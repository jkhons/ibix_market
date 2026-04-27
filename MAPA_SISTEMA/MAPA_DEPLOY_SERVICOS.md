# MAPA DEPLOY E SERVIÇOS — PDV Ibix

Documentação única de deploy, systemd, Nginx e SSL para **www.ibix.com.br** (vitrine pública).

---

## 1. Serviços systemd (pdv_solumatica)

**Produtos Ibix:** PDV Ibix (este repositório) e Auto Ibix (produto distinto). Units deste repositório: apenas **pdv_solumatica** e **pdv_solumatica-celery** (e opcionalmente pdv_solumatica-beat). Não há mais units pdv-automscale; se Auto Ibix rodar no mesmo servidor, usar outro unit e outra porta (ex.: 8001). Ver `scripts/deploy/systemd/README.md`.

Os units incluem **ExecStartPre** para liberar a porta 8000 antes de iniciar (evita "Address already in use" em restarts) e **TimeoutStopSec=30** para encerramento graceful do Gunicorn.

### Instalar (uma vez no servidor — SOLUMATICA)

**No servidor (root@solumatica), execute:**

```bash
cd /central_solumatica/pdv_solumatica
sudo bash scripts/instalar-units-servidor.sh
```

Esse script cria `/etc/systemd/system/pdv_solumatica.service` e `pdv_solumatica-celery.service` (path fixo `/central_solumatica/pdv_solumatica`), faz `daemon-reload` e `enable --now`.

**Alternativa** (script que detecta o diretório pelo path do script):

```bash
cd /central_solumatica/pdv_solumatica
sudo bash scripts/criar-units-no-sistema.sh
```

### Serviços

| Serviço | Descrição |
|---------|-----------|
| `pdv_solumatica` | Aplicação web (Gunicorn, porta 8000) |
| `pdv_solumatica-celery` | Worker Celery (relatórios, PDFs, tarefas assíncronas) |

### Verificar se todos sobem no boot

```bash
cd /central_solumatica/pdv_solumatica
./scripts/verificar-servicos-boot.sh
```

Verifica: nginx, pdv_solumatica, pdv_solumatica-celery, redis-server, postgresql.

### Comandos do dia a dia

| Ação | Comando |
|------|--------|
| Status | `systemctl status pdv_solumatica pdv_solumatica-celery nginx` |
| Reiniciar app | `systemctl restart pdv_solumatica` ou `sudo service pdv_solumatica restart` |
| Logs da app | `journalctl -u pdv_solumatica -f` |
| Logs Celery | `journalctl -u pdv_solumatica-celery -f` |

Para **verificar erros após reinício**, além de `journalctl -u pdv_solumatica -f`, consultar `logs/errors.log` (o arquivo não é rotacionado automaticamente; entradas antigas permanecem).

### Dependências WeasyPrint (geração de PDF)

A geração de PDF (orçamento, pedido, DANFE de nota fiscal) usa WeasyPrint e exige bibliotecas de sistema (Pango, Cairo, GDK-Pixbuf, fontes, etc.). **Instale uma vez no servidor** conforme a [documentação oficial do WeasyPrint](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation) para a sua distribuição (Debian/Ubuntu: tipicamente pacotes como `python3-cffi`, `libcairo2`, `libpango-1.0-0`, `libpangoft2-1.0-0`, `libgdk-pixbuf2.0-0`, `libffi-dev` e fontes; ajuste versões ao SO). Depois reinicie a app:

```bash
sudo systemctl restart pdv_solumatica
```

Sem essas dependências, o download/visualização de PDF de notas fiscais e a geração de PDF de orçamentos/pedidos falham.

**Notas já autorizadas sem PDF:** O sistema pré-gera o DANFE na autorização quando aplicável. Para notas antigas sem PDF, usar reemissão/baixa pela interface fiscal ou procedimento interno de suporte (não há mais script no repositório).

### Scripts na raiz do projeto

- `scripts/criar-units-no-sistema.sh` — **recomendado**: cria os units em `/etc/systemd/system/` (detecta o diretório do projeto). Rodar: `sudo bash scripts/criar-units-no-sistema.sh`.
- `scripts/install_systemd.sh` — copia units do projeto para `/etc/systemd/system/` com path do diretório atual.
- `scripts/verificar-servicos-boot.sh` — lista enabled/active dos serviços.

### Scripts em /central_solumatica

- `criar-units-no-sistema.sh` — gera os units em `/etc/systemd/system/` (conteúdo embutido; usa `pdv_solumatica`).
- `instalar-servicos-pdv.sh` — detecta projeto, copia units (ou chama `criar-units-no-sistema.sh`), habilita e inicia.

---

## 2. Nginx e SSL — www.ibix.com.br

### Arquivos (em `scripts/deploy/nginx/`)

| Arquivo | Uso |
|---------|-----|
| `solumatica.conf` | HTTPS, upstream pdv_solumatica, redirect HTTP→HTTPS e ibix.com.br→www |
| `solumatica-http-only.conf` | Só HTTP (para Certbot obter certificado) |
| `pdv-solumatica.conf` / `pdv-solumatica-http-only.conf` | Variante produto PDV Ibix (ver README na mesma pasta) |
| `pdv-automscale.conf` / `pdv-automscale-http-only.conf` | Legado / referência |

Os *wrappers* shell de instalação Nginx/Certbot foram removidos do repositório; use cópia manual dos `.conf` e Certbot conforme abaixo.

### Deploy Nginx + SSL (passo a passo)

No servidor, com DNS apontando para o servidor:

1. **Pré-requisitos:** DNS `ibix.com.br` e `www.ibix.com.br`; `sudo apt install nginx certbot python3-certbot-nginx` (ou equivalente).
2. **Copiar configs:** a partir de `scripts/deploy/nginx/`, copiar `solumatica-http-only.conf` (ou o ficheiro adequado) para `/etc/nginx/sites-available/` e criar symlink em `sites-enabled/`; `sudo nginx -t && sudo systemctl reload nginx`.
3. **Certificado:** `sudo certbot certonly --webroot -w /var/www/html -d ibix.com.br -d www.ibix.com.br` (ajustar webroot/domínios ao ambiente) ou `certbot --nginx` conforme política do servidor.
4. **Ativar HTTPS:** substituir pelo `.conf` completo com TLS (ex.: `solumatica.conf`), `nginx -t`, `reload`.
5. **Renovação:** `sudo certbot renew --dry-run`.

### Domínio e redirects

- **Canônico:** `https://www.ibix.com.br`
- **Redirects:** `http://...` → `https://www.ibix.com.br`; `https://ibix.com.br` → `https://www.ibix.com.br`
- **Upstream:** `pdv_solumatica` → `127.0.0.1:8000`
- **Static:** `alias /central_solumatica/pdv_solumatica/app/static/` (ou valor de `APP_ROOT`)

---

## 3. Estrutura em /central_solumatica

- `pdv_solumatica/` — aplicação.
- `criar-units-no-sistema.sh` — script que cria units no systemd (recomendado para instalação).
- `instalar-servicos-pdv.sh` — script que detecta projeto e instala/habilita/inicia serviços.

Toda a documentação de deploy e serviços está consolidada neste mapa (**MAPA_DEPLOY_SERVICOS.md**).

---

## 4. Proteção do servidor (internet)

Para expor apenas o estritamente necessário e manter o serviço acessível somente via Nginx:

- **Firewall (UFW):** Apenas portas **22** (SSH), **80** (HTTP) e **443** (HTTPS). Demais portas (8000, 5432, 6379) não devem ser abertas. Regras: `ufw default deny incoming`, `ufw allow 22/tcp`, `ufw allow 80/tcp`, `ufw allow 443/tcp`, `ufw enable` (conferir que 22 está allow antes de enable).
- **Aplicação:** Em produção atrás de Nginx, o Gunicorn escuta em **127.0.0.1:8000** (ou 0.0.0.0:8000 conforme o unit no servidor). Units em `scripts/deploy/systemd/`: `pdv_solumatica.service`, `pdv_solumatica-celery.service`; opcional `pdv_solumatica-beat.service`. Nginx deve repassar `Host` e `X-Forwarded-Proto`/`X-Forwarded-Host` para que a landing use o domínio correto (www vs auto.ibix).
- **PostgreSQL e Redis:** Só localhost ou rede interna. No `docker-compose.yml` use `ports: 127.0.0.1:5432:5432` e `127.0.0.1:6379:6379` para não expor à internet.
- **Nginx:** Configs em `scripts/deploy/nginx/` incluem `server_tokens off;` para não divulgar versão.
- **Script de finalização:** [scripts/finalizar-acesso-internet.sh](scripts/finalizar-acesso-internet.sh) — orienta UFW (22, 80, 443), instala serviços systemd, e documenta os passos de proteção (app em 127.0.0.1, DB/Redis só localhost).

### 4.1 Headers de segurança (OWASP)

Aplicados em **duas camadas** (Nginx + middleware FastAPI):

| Header | Valor | Camada |
|--------|-------|--------|
| `Strict-Transport-Security` | `max-age=63072000; includeSubDomains; preload` | Nginx + FastAPI (quando `HTTPS=true`) |
| `X-Content-Type-Options` | `nosniff` | Nginx + FastAPI |
| `X-Frame-Options` | `DENY` | Nginx + FastAPI |
| `Content-Security-Policy` | whitelist explícita (CDNs, MP SDK, Google, fonts) | FastAPI |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Nginx + FastAPI |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=(self), payment=(self), usb=()` | Nginx + FastAPI |
| `X-Permitted-Cross-Domain-Policies` | `none` | FastAPI |

Para CSP customizado, defina `CSP_EXTRA_SOURCES` no `.env` (concatenado ao final da policy).

### 4.2 CORS

- **Produção (`ENV=production`):** aceita apenas `https://www.ibix.com.br` e `https://ibix.com.br` (ou valor de `CORS_ORIGINS`). Wildcard `*` nunca é usado em produção.
- **Desenvolvimento:** wildcard `*` (quando `CORS_ORIGINS` não definido e `ENV != production`).
- `allow_methods` e `allow_headers` são explícitos (não wildcard).

### 4.3 Endpoints internos

- **`/metrics` (Prometheus):** Nginx restringe acesso a `127.0.0.1` / `::1` (deny all). Não acessível externamente.
- **`/docs`, `/redoc`, `/openapi.json`:** Desabilitados (`docs_url=None`, `redoc_url=None`, `openapi_url=None` em `FastAPI()`).
- **`X-Process-Time`:** Header de debug removido em produção (`ENV=production`).

### 4.4 SSL/TLS hardening (Nginx)

- Protocolos: TLS 1.2 + 1.3 apenas.
- Ciphers: suíte Mozilla Intermediate (ECDHE + CHACHA20/AES-GCM).
- `ssl_session_cache`, `ssl_session_tickets off`, `ssl_stapling on`.
