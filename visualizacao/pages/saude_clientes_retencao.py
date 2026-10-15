"""Saude de Clientes & Retencao: totais diarios e limites da fonte atual."""

import dash_bootstrap_components as dbc
from dash import html
import pandas as pd

from ..charts import format_value, series_figure
from ..components import chart_panel, metric_cards, page_header, pending_section, table_section


TITLE = "Saúde de Clientes & Retenção"
DESCRIPTION = "Acompanhe os registros diários de clientes e a preparação das análises de retenção."


def layout(frame: pd.DataFrame, metric: str = "sessoes", *, start_date=None, end_date=None, financial_frame=None):
    needs_review = bool(frame["data"].dt.month.isin([5, 6, 7, 8, 9]).any())
    recurring = ("Revisar origem" if needs_review else
                 format_value(frame["clientes_recorrentes"].sum(min_count=1), "integer"))
    columns = [("novos_clientes", "Novos clientes", "#326bba"),
               ("total_clientes", "Total de clientes", "#167d57")]
    table_columns = ("data", "novos_clientes", "total_clientes")
    if not needs_review:
        columns.append(("clientes_recorrentes", "Clientes recorrentes", "#e29435"))
        table_columns += ("clientes_recorrentes",)
    return html.Div([
        page_header(TITLE, DESCRIPTION),
        metric_cards([
            ("Novos clientes (soma diária)", format_value(frame["novos_clientes"].sum(min_count=1), "integer")),
            ("Total de clientes (soma diária)", format_value(frame["total_clientes"].sum(min_count=1), "integer")),
            ("Clientes recorrentes (soma diária)", recurring),
        ]),
        dbc.Alert(
            "Nas abas de maio a setembro, a coluna R representa CPA. Os valores de clientes recorrentes desse período precisam de revisão antes de entrar nesta análise.",
            id="clientes-mapping-warning", color="warning", is_open=needs_review,
        ),
        html.P("As somas diárias podem contar a mesma pessoa em dias diferentes. A contagem de clientes únicos depende de um identificador de cliente.",
               className="page-note"),
        html.Div(chart_panel(series_figure(frame, "Registros de clientes por dia", tuple(columns)),
                             "clientes-daily-chart"), className="mb-4"),
        table_section(frame, "Registros recentes de clientes", table_columns),
        pending_section("Retenção e recompra",
            "Para calcular retenção, recompra e coortes, esta seção precisa do identificador do cliente e do histórico de pedidos com suas datas. Os totais diários atuais não fornecem esse histórico."),
    ], id="page-saude-clientes-retencao")
