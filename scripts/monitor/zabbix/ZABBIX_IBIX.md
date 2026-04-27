# Zabbix — Monitoramento do Servidor Ibix

Guia completo para instalar o **Zabbix Server** no servidor de monitoramento e o **Zabbix Agent** no servidor ibix.com.br.

---

## 1. Arquitetura

```
┌─────────────────────────────┐         ┌─────────────────────────────────┐
│   SERVIDOR MONITOR (Zabbix) │         │   SERVIDOR IBIX (Monitorado)    │
│                             │         │                                 │
│  Zabbix Server (Docker)     │◄───────►│  Zabbix Agent 2                 │
│  Zabbix Web (porta 8080)    │  10050  │                                 │
│  PostgreSQL (Zabbix DB)     │  10051  │  Nginx (80/443)                 │
│  Grafana (opcional, 3000)   │         │  Gunicorn/FastAPI (127.0.0.1:8000) │
│                             │ HTTPS   │  PostgreSQL (Docker, 127.0.0.1:5432) │
│  Web checks (externo)  ────►├────443──►│  Redis (Docker, 127.0.0.1:6379) │
│                             │         │  Celery Worker                  │
└─────────────────────────────┘         └─────────────────────────────────┘
```

---

## 2. Dados do Servidor Ibix (Monitorado)

| Campo | Valor |
|-------|-------|
| **Hostname** | `solumatica` |
| **IP Público** | `187.77.56.55` |
| **IP Interno** | `187.77.56.55` (mesmo — VPS) |
| **OS** | Ubuntu 25.10 (Questing Quokka) |
| **CPU** | 4 cores |
| **RAM** | 16 GB |
| **Disco** | 193 GB (5% usado) |
| **Domínio** | `www.ibix.com.br` / `ibix.com.br` |
| **SSL** | Let's Encrypt (expira 2026-06-29) |

### Serviços

| Serviço | Processo | Bind | Porta |
|---------|----------|------|-------|
| Nginx | systemd | 0.0.0.0 | 80, 443 |
| Gunicorn (FastAPI) | systemd `pdv_solumatica` | 127.0.0.1 | 8000 |
| Celery Worker | systemd `pdv_solumatica-celery` | — | — |
| PostgreSQL 16 | Docker `pdv_solumatica_db` | 127.0.0.1 | 5432 |
| Redis 7 | Docker `pdv_solumatica_redis` | 127.0.0.1 | 6379 |
| SSH | systemd `sshd` | 0.0.0.0 | 22 |

### Firewall (UFW)

| Porta | Ação |
|-------|------|
| 22/tcp | ALLOW (SSH) |
| 80/tcp | ALLOW (HTTP) |
| 443/tcp | ALLOW (HTTPS) |
| **10050/tcp** | **ADICIONAR** (Zabbix Agent) |
| Demais | DENY |

### Logs

| Log | Caminho |
|-----|---------|
| Nginx access | `/var/log/nginx/access.log` |
| Nginx error | `/var/log/nginx/error.log` |
| App errors | `/central_solumatica/pdv_solumatica/logs/errors.log` |
| App audit | `/central_solumatica/pdv_solumatica/logs/audit.log` |
| Segurança | `/central_solumatica/pdv_solumatica/logs/security.log` |
| Systemd app | `journalctl -u pdv_solumatica` |
| Systemd celery | `journalctl -u pdv_solumatica-celery` |
| Auth Linux | `/var/log/auth.log` |

---

## 3. O que monitorar (Mapa de Itens)

### 3.1 Infraestrutura (Template Linux by Zabbix agent)

| Métrica | Tipo | Trigger |
|---------|------|---------|
| CPU utilization | Agent | > 85% por 5min → WARNING |
| CPU load average | Agent | > 4 (num cores) → WARNING |
| RAM used % | Agent | > 85% → WARNING, > 95% → CRITICAL |
| Disco / used % | Agent | > 80% → WARNING, > 90% → CRITICAL |
| Disco I/O wait | Agent | > 20% → WARNING |
| Swap used | Agent | > 50% → WARNING |
| Network traffic in/out | Agent | Baseline + anomalia |
| Uptime do server | Agent | < 5 min → INFO (reboot detectado) |

### 3.2 Serviços (systemd)

| Serviço | Item | Trigger |
|---------|------|---------|
| `nginx` | `systemd.unit.is_active[nginx.service]` | != active → CRITICAL |
| `pdv_solumatica` | `systemd.unit.is_active[pdv_solumatica.service]` | != active → CRITICAL |
| `pdv_solumatica-celery` | `systemd.unit.is_active[pdv_solumatica-celery.service]` | != active → CRITICAL |
| `sshd` | `systemd.unit.is_active[ssh.service]` | != active → WARNING |

### 3.3 Docker

| Container | Item | Trigger |
|-----------|------|---------|
| `pdv_solumatica_db` | `docker.container.status[pdv_solumatica_db]` | != running → CRITICAL |
| `pdv_solumatica_redis` | `docker.container.status[pdv_solumatica_redis]` | != running → CRITICAL |

### 3.4 Endpoints Web (Web Scenarios — executados pelo Zabbix Server)

| Endpoint | URL | Expect | Latência alerta |
|----------|-----|--------|-----------------|
| Homepage | `https://www.ibix.com.br/` | 200 | > 3s WARNING, > 8s CRITICAL |
| Login page | `https://www.ibix.com.br/login` | 200 | > 3s |
| Login loja | `https://www.ibix.com.br/loja/login` | 200 | > 3s |
| Carrinho | `https://www.ibix.com.br/loja/carrinho` | 200 | > 3s |
| API categorias | `https://www.ibix.com.br/api/v1/loja/categorias?ativa=true` | 200 | > 2s WARNING |
| API anuncios | `https://www.ibix.com.br/api/v1/loja/anuncios?sort=recent&skip=0&limit=8` | 200 | > 2s WARNING |
| API marketing | `https://www.ibix.com.br/api/v1/marketing-vitrine/vitrine-home` | 200 | > 2s WARNING |
| API social cfg | `https://www.ibix.com.br/api/v1/loja/auth/social/config` | 200 | > 1s |
| security.txt | `https://www.ibix.com.br/.well-known/security.txt` | 200 | > 1s |
| Dashboard redirect | `https://www.ibix.com.br/dashboard` | 302 | > 2s |
| SSL Certificate | `https://www.ibix.com.br:443` | válido | < 14 dias → WARNING |

### 3.5 Segurança

| Check | Tipo | Trigger |
|-------|------|---------|
| SSH brute force | Log `/var/log/auth.log` regex `Failed password` | > 10 em 5min → HIGH |
| Nginx 429 (rate limit) | Log `/var/log/nginx/access.log` regex `" 429 ` | > 50 em 5min → WARNING |
| Nginx 403 (forbidden) | Log `/var/log/nginx/access.log` regex `" 403 ` | > 20 em 5min → WARNING |
| Nginx 5xx | Log `/var/log/nginx/access.log` regex `" 5[0-9]{2} ` | > 5 em 5min → HIGH |
| App errors | Log `/central_solumatica/pdv_solumatica/logs/errors.log` | Novas linhas → WARNING |
| Login failures | UserParameter script | > 20 em 5min → HIGH |
| Port scan detect | Conexões recusadas em portas fechadas | Anomalia → INFO |

### 3.6 Performance (Gargalos)

| Métrica | Tipo | Trigger |
|---------|------|---------|
| Nginx requests/sec | Log parsing | Baseline |
| Nginx active connections | `stub_status` | > 500 → WARNING |
| Gunicorn workers busy | UserParameter | = max workers → WARNING |
| PostgreSQL connections | UserParameter | > 80% max → WARNING |
| Redis memory used | UserParameter | > 80% maxmemory → WARNING |
| Redis connected clients | UserParameter | > 100 → WARNING |
| Celery queue length | UserParameter | > 50 → WARNING |

---

## 4. Instalação

### 4.1 No Servidor MONITOR — Zabbix Server (Docker)

Veja arquivo: `server/docker-compose.yml`

```bash
cd /opt/zabbix
docker compose up -d
```

Acesso web: `http://IP-SERVIDOR-MONITOR:8080`
- Login padrão: `Admin` / `zabbix`

### 4.2 No Servidor IBIX — Zabbix Agent 2

Veja arquivo: `agent/install_agent_ibix.sh`

```bash
# No servidor ibix (187.77.56.55)
sudo bash install_agent_ibix.sh
```

### 4.3 Configurar Host no Zabbix

1. Acesse Zabbix Web → **Data collection** → **Hosts** → **Create host**
2. Preencha:
   - **Host name:** `ibix-server`
   - **Visible name:** `Servidor Ibix (www.ibix.com.br)`
   - **Host groups:** `Linux servers`, `Web servers`
   - **Interfaces:** Agent → IP: `187.77.56.55`, Port: `10050`
3. **Templates** (vincular):
   - `Linux by Zabbix agent` (built-in)
   - `Nginx by Zabbix agent` (built-in)
   - `Template Ibix Custom` (importar de `templates/`)
4. **Macros** (definir no host):
   - `{$IBIX.URL}` = `https://www.ibix.com.br`
   - `{$IBIX.API.URL}` = `https://www.ibix.com.br/api/v1`
   - `{$IBIX.SLOW.WARN}` = `3`
   - `{$IBIX.SLOW.CRIT}` = `8`
   - `{$IBIX.SSL.WARN.DAYS}` = `14`

---

## 5. Rede e Firewall

### No servidor IBIX (187.77.56.55)

Liberar porta **10050** (Zabbix Agent) **apenas** para o IP do servidor monitor:

```bash
# Substituir IP_MONITOR pelo IP real do servidor Zabbix
sudo ufw allow from IP_MONITOR to any port 10050 proto tcp comment "Zabbix Agent"
sudo ufw reload
```

### No servidor MONITOR

Liberar (se tiver firewall):

```bash
sudo ufw allow 8080/tcp comment "Zabbix Web"
sudo ufw allow 10051/tcp comment "Zabbix Server (trapper)"
```

---

## 6. Alertas (Media Types)

Configurar no Zabbix Web → **Alerts** → **Media types**:

| Canal | Tipo | Config |
|-------|------|--------|
| **Telegram** | Webhook (built-in) | Bot token + Chat ID |
| **Email** | SMTP | Servidor SMTP + credenciais |
| **Slack** | Webhook (built-in) | Webhook URL |
| **Discord** | Webhook customizado | Webhook URL |

### Severidades para notificação

| Severidade Zabbix | Quando | Ação |
|-------------------|--------|------|
| Not classified | Info geral | Log apenas |
| Information | Reboot, deploy | Log |
| Warning | Lento, SSL <14d, RAM >85% | Notificar |
| Average | Endpoint fora, erros 5xx | Notificar |
| High | Brute force, muitos erros | Notificar urgente |
| Disaster | Site off, DB off, disco cheio | Notificar + ligar |

---

## 7. Estrutura dos arquivos

```
scripts/monitor/zabbix/
├── ZABBIX_IBIX.md                    # Este documento
├── server/
│   └── docker-compose.yml            # Zabbix Server (rodar no servidor monitor)
├── agent/
│   ├── install_agent_ibix.sh         # Instalar agent no servidor ibix
│   └── zabbix_agent2.conf            # Config do agent
├── templates/
│   └── template_ibix_custom.yaml     # Template customizado (importar no Zabbix)
└── scripts/
    ├── ibix_check_endpoints.sh       # UserParameter: latência de endpoints
    ├── ibix_check_security.sh        # UserParameter: erros de segurança
    ├── ibix_check_services.sh        # UserParameter: status de serviços
    └── ibix_check_performance.sh     # UserParameter: métricas de performance
```
