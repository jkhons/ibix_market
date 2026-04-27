-- Preencher data_conclusao em processo_balanca_calibracao para balanças já
-- em etapa concluído/reprovado que ainda não têm data_conclusao (permite emissão de certificado).
--
-- Execução recomendada:
-- 1. Fazer backup ou rodar em transação (BEGIN; ... COMMIT; ou ROLLBACK; para desfazer)
-- 2. Executar em ambiente de homologação primeiro
--
-- ========== MySQL (projeto PDV Automscale) ==========
-- Banco atual é PostgreSQL; use fix_data_conclusao_balancas_concluidas_pg.sql em ambientes PG.

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
SET pbc.data_conclusao = NOW()
WHERE pbc.etapa_atual IN ('concluido', 'reprovado')
  AND pbc.data_conclusao IS NULL;
