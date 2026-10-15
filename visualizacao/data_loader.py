"""Executa SQL no BigQuery e entrega um Pandas DataFrame ao dashboard."""

from datetime import date
import logging

import pandas as pd
from google.cloud import bigquery

from .auth import load_credentials
from .config import METRICS, PACKAGE_ROOT, Settings
from .financial import prepare_financial_frame


LOGGER = logging.getLogger(__name__)


def prepare_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    missing = {"data", *METRICS} - set(dataframe.columns)
    if missing:
        raise ValueError("Colunas ausentes no DataFrame: " + ", ".join(sorted(missing)))
    frame = dataframe.loc[:, ["data", *METRICS]].copy()
    frame["data"] = pd.to_datetime(frame["data"], errors="raise")
    if frame["data"].isna().any() or frame["data"].duplicated().any():
        raise ValueError("Os indicadores precisam ter uma data valida e unica por linha.")
    for column in METRICS:
        frame[column] = pd.to_numeric(frame[column], errors="raise").astype("float64")
    return frame.sort_values("data").reset_index(drop=True)


def load_indicators(
    settings: Settings,
    start_date: date | None = None,
    end_date: date | None = None,
) -> pd.DataFrame:
    if start_date is not None and end_date is not None and start_date > end_date:
        raise ValueError("A data inicial precisa ser anterior ou igual a data final.")
    credentials = load_credentials()
    sql = (PACKAGE_ROOT / "sql" / "indicadores_diarios.sql").read_text(encoding="utf-8")
    sql = sql.format(table_id=settings.qualified_table)
    config = bigquery.QueryJobConfig(
        use_legacy_sql=False,
        maximum_bytes_billed=settings.maximum_bytes_billed,
        query_parameters=[
            bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
            bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
        ],
    )
    LOGGER.info("Consultando BigQuery: %s", settings.qualified_table)
    try:
        with bigquery.Client(project=settings.project_id, credentials=credentials) as client:
            job = client.query(sql, job_config=config, location=settings.location, timeout=30)
            rows = job.result(timeout=settings.query_timeout)
            # REST e suficiente para este conjunto pequeno e dispensa outra API.
            dataframe = rows.to_dataframe(create_bqstorage_client=False)
    except Exception:
        # A excecao da API nao e renderizada no navegador nem inclui credenciais no log.
        LOGGER.error("Falha ao consultar o BigQuery. Verifique a configuracao e as permissoes da conta.")
        raise RuntimeError("Nao foi possivel carregar os indicadores do BigQuery.") from None
    result = prepare_dataframe(dataframe)
    LOGGER.info("BigQuery -> Pandas: %s linhas e %s colunas.", len(result), len(result.columns))
    return result


def load_financials(settings: Settings) -> pd.DataFrame:
    """Consulta a tabela bruta uma vez por processo, sem depender de Raw local."""
    sql = (PACKAGE_ROOT / "sql" / "financeiro_mensal.sql").read_text(encoding="utf-8")
    sql = sql.format(raw_table_id=settings.qualified_raw_table)
    config = bigquery.QueryJobConfig(use_legacy_sql=False, maximum_bytes_billed=settings.maximum_bytes_billed)
    LOGGER.info("Consultando DRE e PLANO 2026 no BigQuery: %s", settings.qualified_raw_table)
    try:
        with bigquery.Client(project=settings.project_id, credentials=load_credentials()) as client:
            job = client.query(sql, job_config=config, location=settings.location, timeout=30)
            frame = job.result(timeout=settings.query_timeout).to_dataframe(create_bqstorage_client=False)
    except Exception:
        LOGGER.error("Falha ao consultar DRE e PLANO 2026 no BigQuery.")
        raise RuntimeError("Nao foi possivel carregar o financeiro do BigQuery.") from None
    result = prepare_financial_frame(frame)
    LOGGER.info("BigQuery -> DRE mensal: %s meses.", len(result))
    return result
