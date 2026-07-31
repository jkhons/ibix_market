# PDV Ibix

Plataforma SaaS de gestão comercial: PDV, caixa, estoque, fiscal, marketplace e vitrine (`/loja`).

**Stack:** FastAPI, PostgreSQL, SQLAlchemy, Jinja2, Celery + Redis.

## Documentação (fonte de verdade)

Toda implementação e revisão devem seguir os mapas em **[MAPA_SISTEMA/INDICE.md](MAPA_SISTEMA/INDICE.md)** — escolha **um** mapa por tarefa.

| Público | Entrada |
|---------|---------|
| Desenvolvedor | Este README → `MAPA_SISTEMA/INDICE.md` |
| Agente de IA (Cursor) | [AGENTS.md](AGENTS.md) → `MAPA_SISTEMA/INDICE.md` |

**Regras obrigatórias:** [MAPA_SISTEMA/MAPA_DE_REGRAS.md](MAPA_SISTEMA/MAPA_DE_REGRAS.md) (§ 0).

**Planos de execução** (app mobile, features grandes): `.cursor/plans/` — não ficam em `MAPA_SISTEMA/`.

## Ambiente local

| Item | Valor |
|------|--------|
| Porta | 8000 |
| Variáveis | `.env` na raiz (`DB_*`, `SECRET_KEY`, etc.) |
| Venv | `.venv/bin/python` |
| Migrações | `alembic upgrade head` (no venv) |
| Servidor dev | `uvicorn` / script do projeto na porta 8000 |

**Backup:** `scripts/backup_pdv-solumatica.sh` → `/central_solumatica/Backup`

**Deploy produção:** [MAPA_SISTEMA/MAPA_DEPLOY_SERVICOS.md](MAPA_SISTEMA/MAPA_DEPLOY_SERVICOS.md)
