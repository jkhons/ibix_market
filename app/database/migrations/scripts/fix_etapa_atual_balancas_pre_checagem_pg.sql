-- Ajuste: atualizar etapa_atual em processo_balanca_calibracao quando os dados
-- de ensaio já existem em processo_equipamentos mas a balança ainda está em 'pre_checagem'.
--
-- ========== PostgreSQL (PDV Automscale) ==========
-- Em MySQL usa-se JSON_LENGTH(); em PostgreSQL usa-se jsonb_array_length( col::jsonb ).
-- Execução: psql -h HOST -p 5432 -U USER -d certipeso -f fix_etapa_atual_balancas_pre_checagem_pg.sql

-- Ver quantas linhas serão afetadas (somente leitura)
SELECT
    pbc.id AS balanca_id,
    pbc.processo_id,
    pbc.equipamento_id,
    pbc.etapa_atual AS etapa_atual_antes,
    CASE
        WHEN pe.ensaio_final_medicoes_json IS NOT NULL AND jsonb_array_length(pe.ensaio_final_medicoes_json::jsonb) > 0 THEN 'ensaio_final'
        WHEN pe.medicoes_json IS NOT NULL AND jsonb_array_length(pe.medicoes_json::jsonb) > 0 THEN 'ensaio_inicial'
        ELSE pbc.etapa_atual
    END AS etapa_atual_depois
FROM processo_balanca_calibracao pbc
INNER JOIN processo_equipamentos pe
    ON pe.processo_id = pbc.processo_id AND pe.equipamento_id = pbc.equipamento_id
WHERE pbc.etapa_atual = 'pre_checagem'
  AND (
      (pe.ensaio_final_medicoes_json IS NOT NULL AND jsonb_array_length(pe.ensaio_final_medicoes_json::jsonb) > 0)
      OR (pe.medicoes_json IS NOT NULL AND jsonb_array_length(pe.medicoes_json::jsonb) > 0)
  );

-- Atualização efetiva
UPDATE processo_balanca_calibracao pbc
SET etapa_atual = CASE
    WHEN pe.ensaio_final_medicoes_json IS NOT NULL AND jsonb_array_length(pe.ensaio_final_medicoes_json::jsonb) > 0 THEN 'ensaio_final'
    WHEN pe.medicoes_json IS NOT NULL AND jsonb_array_length(pe.medicoes_json::jsonb) > 0 THEN 'ensaio_inicial'
    ELSE pbc.etapa_atual
END
FROM processo_equipamentos pe
WHERE pe.processo_id = pbc.processo_id AND pe.equipamento_id = pbc.equipamento_id
  AND pbc.etapa_atual = 'pre_checagem'
  AND (
      (pe.ensaio_final_medicoes_json IS NOT NULL AND jsonb_array_length(pe.ensaio_final_medicoes_json::jsonb) > 0)
      OR (pe.medicoes_json IS NOT NULL AND jsonb_array_length(pe.medicoes_json::jsonb) > 0)
  );
