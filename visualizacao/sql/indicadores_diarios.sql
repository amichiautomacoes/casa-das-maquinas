SELECT
    data,
    sessoes,
    vendas,
    taxa_de_conversao,
    cps_custo_por_sessao,
    ticket_medio,
    faturamento_analytics,
    faturamento_real,
    facebook_ads,
    google_ads,
    meta_api,
    investimento_real,
    outros_investimentos,
    investimento_total,
    roas_analytics,
    roas_real,
    clientes_recorrentes,
    novos_clientes,
    total_clientes
FROM `{table_id}`
WHERE data IS NOT NULL
  AND (@start_date IS NULL OR data >= @start_date)
  AND (@end_date IS NULL OR data <= @end_date)
ORDER BY data
