# Scripts SQL de manutenção (migrations/scripts)

Scripts de correção de dados executados manualmente quando necessário.

| Script | Descrição |
|--------|-----------|
| `fix_data_conclusao_balancas_concluidas_pg.sql` | Preenche `data_conclusao` em balanças já concluídas/reprovadas |
| `fix_etapa_atual_balancas_pre_checagem_pg.sql` | Ajusta `etapa_atual` quando ensaios já existem |

**Uso:** `psql -h HOST -p 5432 -U USER -d certipeso -f script_pg.sql`
