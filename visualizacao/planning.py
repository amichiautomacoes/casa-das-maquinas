"""Metas de faturamento e rateio do planejamento para o periodo selecionado."""

from calendar import isleap, monthrange
from datetime import date
from math import isfinite


# Preencha com o planejamento aprovado. Chaves mensais: "AAAA-MM"; anuais: AAAA.
# Os valores sao em reais. Ausencia de planejamento nao representa meta zero.
MONTHLY_REVENUE_TARGETS: dict[str, float] = {}
ANNUAL_REVENUE_TARGETS: dict[int, float] = {}


def revenue_target(start_date: date | None, end_date: date | None) -> float | None:
    """Soma o planejado dos dias selecionados, priorizando a meta mensal.

    Meses incompletos usam dias selecionados / dias do mes. Quando so existe
    meta anual, o rateio e por dias do ano. Todos os dias precisam de meta.
    """
    if start_date is None or end_date is None or start_date > end_date:
        return None
    total = 0.0
    cursor = start_date
    while cursor <= end_date:
        days_in_month = monthrange(cursor.year, cursor.month)[1]
        last_day = min(end_date, date(cursor.year, cursor.month, days_in_month))
        days = (last_day - cursor).days + 1
        monthly = MONTHLY_REVENUE_TARGETS.get(f"{cursor.year:04d}-{cursor.month:02d}")
        annual = ANNUAL_REVENUE_TARGETS.get(cursor.year)
        target = monthly if monthly is not None else annual
        if target is None or not isfinite(target) or target <= 0:
            return None
        divisor = days_in_month if monthly is not None else (366 if isleap(cursor.year) else 365)
        total += target * days / divisor
        if last_day == end_date:
            break
        cursor = date(cursor.year + (cursor.month == 12), cursor.month % 12 + 1, 1)
    return round(total, 2)
