# Runbook DR — PDV Ibix (Fase 9 enterprise)

## Metas (definidas)

| Métrica | Meta | Notas |
|---------|------|-------|
| **RPO** | 24 h | Backup diário (`scripts/backup_pdv-solumatica.sh`) |
| **RTO** | 4 h | Restore + `alembic upgrade head` + restart systemd |

## Pré-requisitos

- Backups em `/central_solumatica/Backup` (retenção 20 diários)
- Opcional: upload cifrado (`BACKUP_ENCRYPT=1`, `BACKUP_UPLOAD_*`)
- PITR PostgreSQL: configurar no servidor se exigir RPO < 24h

## Procedimento de restore (resumo)

1. Parar serviços: `systemctl stop pdv_solumatica pdv_solumatica-celery`
2. Restore DB: `scripts/restore_pdv-solumatica.sh` (ajustar caminho do dump)
3. Migrações: `.venv/bin/alembic upgrade head`
4. Verificar: `.venv/bin/python scripts/verify_rls_policies.py`
5. Subir: `systemctl start pdv_solumatica pdv_solumatica-celery`
6. Smoke: `curl -s http://127.0.0.1:8000/api/health`

## Teste trimestral (obrigatório)

- Restaurar dump em ambiente de homologação
- Documentar data, responsável, RTO real medido
- Registrar em changelog operacional / ticket interno

## Cross-region

- Copiar backups cifrados para storage secundário (S3/outro datacenter)
- Frequência: diária após backup local

## Scripts relacionados

- `scripts/backup_pre_rls.sh` — checklist pré-migração estrutural
- `scripts/verify_enterprise_readiness.sh` — validação Fase 9
- `scripts/rollout_multibrand_fase6.sh` — rollout pós-RLS
