-- Preencher data_conclusao em processo_balanca_calibracao para balanças já
-- em etapa concluído/reprovado que ainda não têm data_conclusao (permite emissão de certificado).
--
-- ========== PostgreSQL (PDV Automscale) ==========
-- Execução: psql -h HOST -p 5432 -U USER -d certipeso -f fix_data_conclusao_balancas_concluidas_pg.sql
-- Ou em transação: BEGIN; \i fix_data_conclusao_balancas_concluidas_pg.sql COMMIT;

-- Ver quantas linhas serão afetadas (somente leitura)
SELECT
    pbc.id AS balanca_id,
    pbc.processo_id,
    pbc.equipamento_id,
    pbc.etapa_atual,
    pbc.data_conclusao AS data_conclusao_antes
FROM processo_balanca_calibracao pbc
WHERE pbc.etapa_atual IN ('concluido', 'reprovado')
  AND pbc.data_conclusao IS NULL;

-- Atualização: definir data_conclusao = NOW() onde está nula e etapa já é concluído/reprovado
UPDATE processo_balanca_calibracao pbc
SET data_conclusao = NOW()
WHERE pbc.etapa_atual IN ('concluido', 'reprovado')
  AND pbc.data_conclusao IS NULL;
