"""Calculos de midia, faixas de ticket e registros de clientes."""

import numpy as np
import pandas as pd

from .charts import format_value, safe_ratio
from .executive import marketing_by_day


# Faixas de analise do ticket medio DIARIO, em reais; nao sao categorias de produto.
TICKET_BAND_EDGES = (0, 100, 150, 300, 1000, float("inf"))
CPA_SOURCE_MONTHS = (5, 6, 7, 8, 9)


def ticket_band_labels() -> list[str]:
    def money(value):
        return format_value(value, "currency").removesuffix(",00")

    edges = TICKET_BAND_EDGES
    return [
        f"Abaixo de {money(edges[1])}",
        *[f"{money(lower)} a < {money(upper)}" for lower, upper in zip(edges[1:-2], edges[2:-1])],
        f"{money(edges[-2])} ou mais",
    ]


def sales_by_daily_ticket(frame: pd.DataFrame) -> pd.DataFrame:
    """Classifica os dias e pesa a distribuicao pelo numero de vendas do dia."""
    values = frame[["data", "vendas", "faturamento_real"]].copy()
    values["ticket_calculado"] = values["faturamento_real"] / values["vendas"].where(values["vendas"] > 0)
    valid = np.isfinite(values["ticket_calculado"]) & values["ticket_calculado"].ge(0)
    values = values.loc[valid].copy()
    values["faixa_ticket"] = pd.cut(
        values["ticket_calculado"], bins=TICKET_BAND_EDGES,
        labels=ticket_band_labels(), right=False, include_lowest=True,
    )
    return values.sort_values("data")


def ticket_distribution(frame: pd.DataFrame) -> pd.DataFrame:
    values = sales_by_daily_ticket(frame)
    result = values.groupby("faixa_ticket", observed=False).agg(
        vendas=("vendas", "sum"), faturamento=("faturamento_real", "sum"), dias=("data", "size"),
    ).reset_index()
    total = result["vendas"].sum()
    result["participacao"] = result["vendas"] / total if total > 0 else float("nan")
    return result


def validated_client_counts(frame: pd.DataFrame) -> pd.DataFrame:
    values = frame[["data", "novos_clientes", "clientes_recorrentes"]].copy()
    for column in ("novos_clientes", "clientes_recorrentes"):
        count = values[column]
        values[column] = count.where(np.isfinite(count) & count.ge(0) & count.mod(1).eq(0))
    values.loc[values["data"].dt.month.isin(CPA_SOURCE_MONTHS), "clientes_recorrentes"] = float("nan")
    return values


def client_mix(frame: pd.DataFrame) -> tuple[pd.Series, int]:
    # A proporcao so compara dias que informam OS DOIS tipos de cliente.
    counts = validated_client_counts(frame).dropna(subset=["novos_clientes", "clientes_recorrentes"])
    return counts[["novos_clientes", "clientes_recorrentes"]].sum(min_count=1), len(counts)


def client_cost_reference(frame: pd.DataFrame) -> pd.DataFrame:
    """Investimento total / registros do tipo nos mesmos dias; sem atribuicao."""
    counts = validated_client_counts(frame)
    investment = marketing_by_day(frame)
    rows = []
    for column, label in (("novos_clientes", "Novos clientes"), ("clientes_recorrentes", "Clientes recorrentes")):
        valid = counts[column].notna() & investment.notna() & investment.ge(0)
        spend = investment.loc[valid].sum(min_count=1)
        records = counts.loc[valid, column].sum(min_count=1)
        rows.append({
            "tipo": label, "investimento": spend, "registros": records,
            "dias": int(valid.sum()), "custo_por_registro": safe_ratio(spend, records),
        })
    return pd.DataFrame(rows)
