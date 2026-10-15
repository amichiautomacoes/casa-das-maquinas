"""Prepara a DRE mensal, cruza o plano e calcula o resultado do periodo."""

from dataclasses import dataclass

import pandas as pd

from .charts import safe_ratio


FINANCIAL_COLUMNS = (
    "dias_com_receita", "receita_bruta", "devolucoes", "impostos", "cpv",
    "lucro_bruto_fonte", "resultado_liquido", "receita_prevista", "receita_plano_real",
)


def empty_financial_frame() -> pd.DataFrame:
    return pd.DataFrame({"data": pd.Series(dtype="datetime64[ns]"),
                         **{column: pd.Series(dtype="float64") for column in FINANCIAL_COLUMNS}})


def prepare_financial_frame(dataframe: pd.DataFrame) -> pd.DataFrame:
    missing = {"data", *FINANCIAL_COLUMNS} - set(dataframe.columns)
    if missing:
        raise ValueError("Colunas ausentes no financeiro: " + ", ".join(sorted(missing)))
    frame = dataframe[["data", *FINANCIAL_COLUMNS]].copy()
    frame["data"] = pd.to_datetime(frame["data"], errors="raise")
    if frame["data"].isna().any() or frame["data"].duplicated().any() or not frame["data"].dt.is_month_start.all():
        raise ValueError("A DRE precisa de um primeiro dia de mes unico e valido por linha.")
    for column in FINANCIAL_COLUMNS:
        frame[column] = pd.to_numeric(frame[column], errors="raise").astype("float64")
        if frame[column].isin([float("inf"), -float("inf")]).any():
            raise ValueError("A DRE nao aceita valores infinitos.")
    coverage = frame["dias_com_receita"]
    if (coverage.isna() | coverage.lt(0) | coverage.mod(1).ne(0) | coverage.gt(frame["data"].dt.days_in_month)).any():
        raise ValueError("Cobertura de dias com receita invalida na DRE.")
    return frame.sort_values("data").reset_index(drop=True)


def filter_financial_frame(frame: pd.DataFrame, year=None, start_date=None, end_date=None) -> pd.DataFrame:
    mask = pd.Series(True, index=frame.index)
    if year not in (None, "all"):
        mask &= frame["data"].dt.year.eq(int(year))
    if start_date:
        mask &= frame["data"] >= pd.Timestamp(start_date).to_period("M").start_time
    if end_date:
        mask &= frame["data"] <= pd.Timestamp(end_date).to_period("M").start_time
    if start_date and end_date and pd.Timestamp(start_date) > pd.Timestamp(end_date):
        mask &= False
    return frame.loc[mask].copy()


@dataclass(frozen=True)
class FinancialSummary:
    revenue: float | None
    returns: float | None
    taxes: float | None
    cpv: float | None
    gross_profit: float | None
    gross_margin: float | None
    net_profit: float | None
    net_margin: float | None
    planned_revenue: float | None
    attainment: float | None
    months: int


def financial_rows(frame: pd.DataFrame) -> pd.DataFrame:
    # Uma formula SUM sem entradas gera zero na planilha. Sem dias com receita,
    # esse zero nao e tratado como um fechamento financeiro observado.
    values = frame.loc[frame["dias_com_receita"] > 0].copy()
    values["lucro_bruto_calculado"] = values["receita_bruta"] - values["devolucoes"] - values["impostos"] - values["cpv"]
    values["margem_bruta"] = values["lucro_bruto_calculado"] / values["receita_bruta"].where(values["receita_bruta"] > 0)
    values["margem_liquida"] = values["resultado_liquido"] / values["receita_bruta"].where(values["receita_bruta"] > 0)
    return values


def financial_summary(frame: pd.DataFrame) -> FinancialSummary:
    rows = financial_rows(frame)

    def total(column):
        value = rows[column].sum(min_count=max(1, len(rows)))
        return None if pd.isna(value) else float(value)

    revenue, returns, taxes, cpv = (total(column) for column in ("receita_bruta", "devolucoes", "impostos", "cpv"))
    profit = None if any(value is None for value in (revenue, returns, taxes, cpv)) else revenue - returns - taxes - cpv
    net, planned = total("resultado_liquido"), total("receita_prevista")
    return FinancialSummary(revenue, returns, taxes, cpv, profit, safe_ratio(profit, revenue),
                            net, safe_ratio(net, revenue), planned, safe_ratio(revenue, planned), len(rows))
