-- Coordenadas das abas DRE e PLANO 2026. Exclui totais e trimestres.
WITH meses AS (
    SELECT 1 mes, 'JANEIRO' aba, 4 dre_col, 3 previsto_col, 4 realizado_col UNION ALL
    SELECT 2, 'FEVEREIRO', 5, 5, 6 UNION ALL
    SELECT 3, 'MARÇO', 6, 7, 8 UNION ALL
    SELECT 4, 'ABRIL', 8, 10, 11 UNION ALL
    SELECT 5, 'MAIO', 9, 12, 13 UNION ALL
    SELECT 6, 'JUNHO', 10, 14, 15 UNION ALL
    SELECT 7, 'JULHO', 12, 17, 18 UNION ALL
    SELECT 8, 'AGOSTO', 13, 19, 20 UNION ALL
    SELECT 9, 'SETEMBRO', 14, 21, 22 UNION ALL
    SELECT 10, 'OUTUBRO', 16, 24, 25 UNION ALL
    SELECT 11, 'NOVEMBRO', 17, 26, 27 UNION ALL
    SELECT 12, 'DEZEMBRO', 18, 28, 29
), celulas AS (
    SELECT TRIM(aba) aba, linha, coluna, SAFE_CAST(valor_data AS DATE) valor_data,
           COALESCE(valor_numero, CAST(valor_inteiro AS FLOAT64)) valor
    FROM `{raw_table_id}`
    WHERE (TRIM(aba) = 'DRE' AND linha IN (4, 6, 7, 9, 10, 24))
       OR (TRIM(aba) = 'PLANO 2026' AND linha = 10)
       OR (TRIM(aba) IN (SELECT aba FROM meses) AND coluna IN (2, 9) AND linha >= 4)
), dias AS (
    SELECT aba, linha,
           MAX(IF(coluna = 2, valor_data, NULL)) data,
           MAX(IF(coluna = 9, valor, NULL)) receita
    FROM celulas
    WHERE aba IN (SELECT aba FROM meses)
    GROUP BY aba, linha
), periodos AS (
    -- O nome PLANO 2026 e o rotulo TOTAL 2025 nao definem o ano dos valores.
    -- Uma aba com mais de um mes/ano e ambigua e nao e associada automaticamente.
    SELECT aba, MIN(EXTRACT(YEAR FROM data)) ano, MIN(EXTRACT(MONTH FROM data)) mes,
           COUNTIF(receita IS NOT NULL) dias_com_receita
    FROM dias
    WHERE data IS NOT NULL
    GROUP BY aba
    HAVING COUNT(DISTINCT DATE_TRUNC(data, MONTH)) = 1
), dre AS (
    SELECT m.mes,
           MAX(IF(c.linha = 4, c.valor, NULL)) receita_bruta,
           MAX(IF(c.linha = 6, c.valor, NULL)) devolucoes,
           MAX(IF(c.linha = 7, c.valor, NULL)) impostos,
           MAX(IF(c.linha = 9, c.valor, NULL)) cpv,
           MAX(IF(c.linha = 10, c.valor, NULL)) lucro_bruto_fonte,
           MAX(IF(c.linha = 24, c.valor, NULL)) resultado_liquido
    FROM meses m
    LEFT JOIN celulas c ON c.aba = 'DRE' AND c.coluna = m.dre_col
    GROUP BY m.mes
), plano AS (
    SELECT m.mes,
           MAX(IF(c.coluna = m.previsto_col, c.valor, NULL)) receita_prevista,
           MAX(IF(c.coluna = m.realizado_col, c.valor, NULL)) receita_plano_real
    FROM meses m
    LEFT JOIN celulas c ON c.aba = 'PLANO 2026' AND c.coluna IN (m.previsto_col, m.realizado_col)
    GROUP BY m.mes
)
SELECT DATE(p.ano, m.mes, 1) data, p.dias_com_receita,
       d.receita_bruta, d.devolucoes, d.impostos, d.cpv,
       d.lucro_bruto_fonte, d.resultado_liquido,
       pl.receita_prevista, pl.receita_plano_real
FROM meses m
JOIN periodos p ON p.aba = m.aba AND p.mes = m.mes
JOIN dre d ON d.mes = m.mes
JOIN plano pl ON pl.mes = m.mes
ORDER BY data
