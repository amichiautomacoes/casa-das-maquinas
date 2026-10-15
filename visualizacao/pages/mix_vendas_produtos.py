"""Mix de Vendas & Produtos: vendas diarias e secao para futura base de itens."""

import dash_bootstrap_components as dbc
from dash import dcc, html
import pandas as pd

from ..charts import format_value, metric_figure, safe_ratio
from ..components import chart_panel, metric_cards, page_header, pending_section, table_section


TITLE = "Mix de Vendas & Produtos"
DESCRIPTION = "Acompanhe vendas e receita; o detalhamento de produtos será integrado nesta página."


def layout(frame: pd.DataFrame, metric: str = "sessoes", *, start_date=None, end_date=None, financial_frame=None):
    sales = frame["vendas"].sum(min_count=1)
    revenue = frame["faturamento_real"].sum(min_count=1)
    sessions = frame["sessoes"].sum(min_count=1)
    return html.Div([
        page_header(TITLE, DESCRIPTION),
        metric_cards([
            ("Vendas", format_value(sales, "integer")),
            ("Faturamento real", format_value(revenue, "currency")),
            ("Faturamento real por venda", format_value(safe_ratio(revenue, sales), "currency")),
            ("Conversão do período", format_value(safe_ratio(sales, sessions), "percent")),
        ]),
        dcc.Loading(dbc.Row([
            dbc.Col(chart_panel(metric_figure(frame, "vendas"), "vendas-volume-chart"), xs=12, lg=6),
            dbc.Col(chart_panel(metric_figure(frame, "ticket_medio"), "vendas-ticket-chart"), xs=12, lg=6),
        ], class_name="g-3 mb-4"), type="circle"),
        table_section(frame, "Vendas recentes", (
            "data", "vendas", "ticket_medio", "faturamento_real", "taxa_de_conversao",
        )),
        pending_section("Mix de produtos",
            "A base atual contém indicadores diários. Para analisar produtos, categorias e participação nas vendas, esta seção precisa de SKU, nome do produto, categoria, quantidade vendida e receita por item."),
    ], id="page-mix-vendas-produtos")
