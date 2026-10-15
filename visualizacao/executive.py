"""Calculos dos quatro KPIs executivos a partir dos resultados do BigQuery."""

from dataclasses import dataclass

import pandas as pd

from .charts import safe_ratio
from .planning import revenue_target


MARKETING_CHANNELS = (
    ("facebook_ads", "Meta Ads", "#326bba"),
    ("google_ads", "Google Ads", "#17a398"),
    ("outros_investimentos", "Outros", "#8b78b8"),
)


@dataclass(frozen=True)
class ExecutiveSummary:
    revenue: float | None
    target: float | None
    attainment: float | None
    investment: float | None
    roas: float | None
    ticket: float | None
    sales: float | None


def marketing_by_day(frame: pd.DataFrame) -> pd.Series:
    # Soma os canais solicitados, sem duplicar o total registrado na origem.
    # Um dia inteiramente ausente continua ausente, em vez de virar zero.
    return frame[[column for column, _, _ in MARKETING_CHANNELS]].sum(axis=1, min_count=1)


def executive_summary(frame: pd.DataFrame, start_date=None, end_date=None) -> ExecutiveSummary:
    def total(values):
        value = values.sum(min_count=1)
        return None if pd.isna(value) else float(value)

    def boundary(value, fallback):
        if value:
            return pd.Timestamp(value).date()
        return None if frame.empty else fallback().date()

    start = boundary(start_date, frame["data"].min)
    end = boundary(end_date, frame["data"].max)
    revenue = total(frame["faturamento_real"])
    sales = total(frame["vendas"])
    investment = total(marketing_by_day(frame))
    target = revenue_target(start, end)
    return ExecutiveSummary(
        revenue=revenue, target=target,
        attainment=safe_ratio(revenue, target), investment=investment,
        roas=safe_ratio(revenue, investment), ticket=safe_ratio(revenue, sales),
        sales=sales,
    )


def attainment_status(attainment: float | None) -> tuple[str, str, str]:
    """Cor Bootstrap, descricao acessivel e cor Plotly para o atingimento."""
    if attainment is None:
        return "secondary", "Sem comparação", "#64758b"
    if attainment >= 1:
        return "success", "Meta atingida", "#167d57"
    if attainment >= 0.9:
        return "warning", "Próximo da meta", "#a86709"
    return "danger", "Abaixo da meta", "#c43d4a"
