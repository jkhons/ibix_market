# Ibix External Monitor

Monitoramento externo do servidor **ibix.com.br**, executado a partir de um segundo servidor Linux.

---

## O que monitora

| # | Categoria | Checks |
|---|-----------|--------|
| 1 | **Disponibilidade** | Site online/offline, DNS resolve |
| 2 | **Latência de endpoints** | Tempo de resposta de cada página e API |
| 3 | **Gargalos** | Endpoints lentos (>3s warning, >8s critical), P95, média |
| 4 | **Headers de segurança** | HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy, X-Permitted-Cross-Domain-Policies |
| 5 | **Certificado SSL** | Validade, dias restantes, issuer, protocolo TLS |
| 6 | **Rate limiting** | Proteção brute-force ativa (429 no login) |
| 7 | **CORS** | Rejeita origens maliciosas, não usa wildcard |
| 8 | **Endpoints internos** | /metrics, /docs, /redoc, /openapi.json bloqueados |
| 9 | **Vetores de invasão** | Path traversal, SQL injection, XSS, probes (wp-admin, .env, .git) |
| 10 | **Endpoints de usuário** | Auth sem token retorna 401, login não vaza existência de conta, social config sem secrets |
| 11 | **Portas expostas** | Verifica 8000, 5432, 6379, 3306, 27017, 9090 |
| 12 | **Erros HTTP** | Status codes inesperados em qualquer endpoint |

---

## Estrutura de arquivos

```
scripts/monitor/
├── ibix_monitor.py        # Script principal
├── monitor_config.yaml    # Configuração (copiar para o servidor monitor)
├── install_monitor.sh     # Instalador (roda no servidor monitor)
└── README_MONITOR.md      # Este arquivo
```

---

## Instalação no servidor monitor

### Pré-requisitos

- Linux (Ubuntu/Debian recomendado)
- Python 3.8+
- Acesso à internet (para alcançar ibix.com.br)

### Passo a passo

```bash
# 1. Copie os arquivos para o servidor monitor
scp -r scripts/monitor/ usuario@servidor-monitor:/tmp/ibix-monitor/

# 2. No servidor monitor, execute o instalador
ssh usuario@servidor-monitor
sudo bash /tmp/ibix-monitor/install_monitor.sh
```

Isso instala:
- Script em `/opt/ibix-monitor/ibix_monitor.py`
- Config em `/etc/ibix-monitor/monitor_config.yaml`
- Logs em `/var/log/ibix-monitor/`
- Systemd timer (executa a cada 5 minutos)

### 3. Configure alertas

```bash
sudo nano /etc/ibix-monitor/monitor_config.yaml
```

Edite a seção `alerts:` com webhook e/ou email SMTP.

---

## Uso manual

```bash
# Execução completa
python3 /opt/ibix-monitor/ibix_monitor.py

# Check específico
python3 /opt/ibix-monitor/ibix_monitor.py --check ssl
python3 /opt/ibix-monitor/ibix_monitor.py --check endpoints
python3 /opt/ibix-monitor/ibix_monitor.py --check security
python3 /opt/ibix-monitor/ibix_monitor.py --check ratelimit
python3 /opt/ibix-monitor/ibix_monitor.py --check ports
python3 /opt/ibix-monitor/ibix_monitor.py --check intrusion

# Saída JSON pura (para integração com outros sistemas)
python3 /opt/ibix-monitor/ibix_monitor.py --json

# Sem enviar alertas
python3 /opt/ibix-monitor/ibix_monitor.py --no-alerts
```

---

## Saída

### Terminal

```
============================================================
  IBIX MONITOR — https://www.ibix.com.br
  Status: OK
  Timestamp: 2026-04-13T21:30:00+00:00
  Duração: 12.3s
------------------------------------------------------------
  Total checks: 24
  OK:       22
  Warnings: 2
  Errors:   0
  Critical: 0
------------------------------------------------------------
  Latência média:  245.3ms
  Latência P95:    890.1ms
  Mais lento:      API anuncios (890.1ms)
  SSL expira em:   67 dias
  Rate limiting:   ATIVO
============================================================
```

### Relatório JSON

Salvo em `/var/log/ibix-monitor/report_YYYYMMDD_HHMMSS.json` e `/var/log/ibix-monitor/latest.json`.

Estrutura:
```json
{
  "timestamp": "2026-04-13T21:30:00+00:00",
  "target": "https://www.ibix.com.br",
  "overall_status": "OK",
  "site_online": true,
  "results": {
    "dns": { ... },
    "availability": { ... },
    "endpoints": [ ... ],
    "bottleneck_analysis": { ... },
    "security_headers": { ... },
    "ssl_certificate": { ... },
    "rate_limiting": { ... },
    "cors": { ... },
    "protected_endpoints": { ... },
    "intrusion_vectors": { ... },
    "user_endpoints": { ... },
    "exposed_ports": { ... }
  },
  "summary": {
    "total_checks": 24,
    "ok": 22,
    "warnings": 2,
    "errors": 0,
    "critical": 0
  }
}
```

---

## Alertas

### Webhook (Slack/Discord/Teams/Custom)

Na config, defina:
```yaml
alerts:
  webhook_url: "https://hooks.slack.com/services/xxx/yyy/zzz"
```

Payload enviado:
```json
{
  "text": "**[CRITICAL] Site fora do ar**\n...",
  "severity": "CRITICAL",
  "subject": "Site fora do ar",
  "timestamp": "2026-04-13T21:30:00+00:00"
}
```

### Email (SMTP)

```yaml
alerts:
  email_to: "admin@ibix.com.br"
  email_from: "monitor@ibix.com.br"
  smtp_host: "smtp.gmail.com"
  smtp_port: 587
  smtp_user: "monitor@ibix.com.br"
  smtp_pass: "app-password-aqui"
```

---

## Severidades

| Severidade | Quando | Ação |
|------------|--------|------|
| **OK** | Tudo normal | Nenhuma |
| **WARNING** | Lento, SSL expirando, rate limit fraco | Investigar |
| **ERROR** | Status HTTP errado, headers faltando | Corrigir em breve |
| **CRITICAL** | Site off, SSL expirado, portas expostas, invasão | Ação imediata |

---

## Systemd

```bash
# Status do timer
systemctl status ibix-monitor.timer

# Logs da última execução
journalctl -u ibix-monitor.service --no-pager -n 50

# Executar agora (fora do timer)
systemctl start ibix-monitor.service

# Desabilitar
systemctl stop ibix-monitor.timer
systemctl disable ibix-monitor.timer
```

---

## Retenção de dados

Relatórios JSON são mantidos por 30 dias (configurável em `output.retention_days`). Relatórios mais antigos são removidos automaticamente.
