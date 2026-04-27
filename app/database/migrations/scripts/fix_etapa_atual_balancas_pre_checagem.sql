-- Ajuste: atualizar etapa_atual em processo_balanca_calibracao quando os dados
-- de ensaio já existem em processo_equipamentos mas a balança ainda está em 'pre_checagem'.
-- Corrige o status exibido no modal "Resumo do Processo" (procedimentos/calibração).
--
-- Execução recomendada:
-- 1. Fazer backup ou rodar em transação (BEGIN; ... COMMIT; ou ROLLBACK; para desfazer)
-- 2. Executar em ambiente de homologação primeiro
--
-- ========== MySQL (projeto PDV Automscale) ==========
-- Banco atual é PostgreSQL; use fix_etapa_atual_balancas_pre_checagem_pg.sql em ambientes PG.

-- Ver quantas linhas serão afetadas (somente leitura)
SELECT
    pbc.id AS balanca_id,
    pbc.processo_id,
    pbc.equipamento_id,
    pbc.etapa_atual AS etapa_atual_antes,
    CASE
        WHEN pe.ensaio_final_medicoes_json IS NOT NULL AND JSON_LENGTH(pe.ensaio_final_medicoes_json) > 0 THEN 'ensaio_final'
        WHEN pe.medicoes_json IS NOT NULL AND JSON_LENGTH(pe.medicoes_json) > 0 THEN 'ensaio_inicial'
        ELSE pbc.etapa_atual
    END AS etapa_atual_depois
FROM processo_balanca_calibracao pbc
INNER JOIN processo_equipamentos pe
    ON pe.processo_id = pbc.processo_id AND pe.equipamento_id = pbc.equipamento_id
WHERE pbc.etapa_atual = 'pre_checagem'
  AND (
      (pe.ensaio_final_medicoes_json IS NOT NULL AND JSON_LENGTH(pe.ensaio_final_medicoes_json) > 0)
      OR (pe.medicoes_json IS NOT NULL AND JSON_LENGTH(pe.medicoes_json) > 0)
  );

-- Atualização efetiva
UPDATE processo_balanca_calibracao pbc
INNER JOIN processo_equipamentos pe
    ON pe.processo_id = pbc.processo_id AND pe.equipamento_id = pbc.equipamento_id
SET pbc.etapa_atual = CASE
    WHEN pe.ensaio_final_medicoes_json IS NOT NULL AND JSON_LENGTH(pe.ensaio_final_medicoes_json) > 0 THEN 'ensaio_final'
    WHEN pe.medicoes_json IS NOT NULL AND JSON_LENGTH(pe.medicoes_json) > 0 THEN 'ensaio_inicial'
    ELSE pbc.etapa_atual
END
WHERE pbc.etapa_atual = 'pre_checagem'
  AND (
      (pe.ensaio_final_medicoes_json IS NOT NULL AND JSON_LENGTH(pe.ensaio_final_medicoes_json) > 0)
      OR (pe.medicoes_json IS NOT NULL AND JSON_LENGTH(pe.medicoes_json) > 0)
  );
