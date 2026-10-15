"""Performance de Midia: investimento nos canais registrados na base diaria."""

import dash_bootstrap_components as dbc
from dash import dcc, html
import pandas as pd

from ..charts import format_value, metric_figure, series_figure
from ..components import chart_panel, metric_cards, page_header, pending_section, table_section


TITLE = "Performance de Mídia"
DESCRIPTION = "Acompanhe os investimentos registrados em cada canal de mídia."


def layout(frame: pd.DataFrame, metric: str = "sessoes", *, start_date=None, end_date=None, financial_frame=None):
    totals = [
        (label, format_value(frame[column].sum(min_count=1), "currency"))
        for column, label in (
            ("facebook_ads", "Facebook Ads"), ("google_ads", "Google Ads"),
            ("outros_investimentos", "Outros investimentos"),
            ("investimento_total", "Investimento total"),
        )
    ]
    return html.Div([
        page_header(TITLE, DESCRIPTION),
        metric_cards(totals),
        dcc.Loading(dbc.Row([
            dbc.Col(chart_panel(series_figure(frame, "Investimento registrado por canal", (
                ("facebook_ads", "Facebook Ads", "#326bba"),
                ("google_ads", "Google Ads", "#167d57"),
                ("outros_investimentos", "Outros investimentos", "#e29435"),
            ), kind="currency"), "midia-channel-chart"), xs=12, lg=7),
            dbc.Col(chart_panel(metric_figure(frame, "investimento_total"), "midia-total-chart"), xs=12, lg=5),
        ], class_name="g-3 mb-4"), type="circle"),
        table_section(frame, "Investimentos recentes", (
            "data", "facebook_ads", "google_ads", "outros_investimentos", "investimento_total",
        )),
        pending_section("Resultados atribuídos à mídia",
            "ROAS, conversão e custo de aquisição por canal precisam de vendas e receita atribuídas a cada mídia. O campo Meta API permanece como valor bruto até que seu significado seja confirmado."),
    ], id="page-performance-midia")
