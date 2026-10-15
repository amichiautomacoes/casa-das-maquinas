"""Visao Geral Executiva: indicadores consolidados e evolucao diaria."""

import dash_bootstrap_components as dbc
from dash import dcc, html
import pandas as pd

from ..charts import metric_figure, revenue_figure
from ..components import chart_panel, executive_kpi_cards, page_header, table_section
from ..executive import marketing_by_day
from ..financial_section import financial_section
from ..insight_sections import clients_section, media_section, sales_section


TITLE = "Visão Geral Executiva"
DESCRIPTION = "Receita, retorno de mídia e valor por venda em uma visão consolidada."


def layout(frame: pd.DataFrame, metric: str = "sessoes", *, start_date=None, end_date=None, financial_frame=None):
    # A pagina inteira usa a mesma definicao de investimento dos cards.
    frame = frame.copy()
    frame["investimento_total"] = marketing_by_day(frame)
    frame["roas_real"] = frame["faturamento_real"] / frame["investimento_total"].where(frame["investimento_total"] > 0)
    return html.Div([
        page_header(TITLE, DESCRIPTION),
        executive_kpi_cards(frame, start_date, end_date),
        html.Section(dbc.Card([
            dbc.CardHeader([
                html.Span("Cruzamento estratégico", className="strategy-eyebrow"),
                html.H3("A Curva de Desacoplamento", id="executiva-strategy-title"),
                html.P("Como o faturamento real e o investimento em mídia evoluem ao longo do tempo."),
            ], class_name="strategy-heading"),
            dbc.CardBody([
                dcc.Loading(dcc.Graph(
                    id="executiva-revenue-chart",
                    figure=revenue_figure(frame, start_date, end_date),
                    config={"displaylogo": False, "responsive": True, "scrollZoom": False,
                            "toImageButtonOptions": {"filename": "curva-de-desacoplamento", "scale": 2}},
                ), type="circle"),
                html.P([
                    html.Strong("Leitura: "),
                    "azul no eixo esquerdo; laranja no direito. Cada eixo tem sua própria escala. ",
                    "No mês, valores diários; em períodos maiores, somas mensais dos dias selecionados. ",
                    "Lacunas indicam ausência de dados.",
                ], className="strategy-note"),
            ], class_name="strategy-body"),
        ], class_name="strategy-card"), id="executiva-strategy-section",
            className="mb-4", **{"aria-labelledby": "executiva-strategy-title"}),
        media_section(frame, start_date, end_date),
        sales_section(frame),
        clients_section(frame),
        dbc.Alert(
            "A coluna de clientes recorrentes precisa de revisão: nas abas de maio a setembro, a origem usa a coluna R como CPA.",
            id="executiva-mapping-warning", color="warning",
            is_open=metric == "clientes_recorrentes" and bool(frame["data"].dt.month.isin([5, 6, 7, 8, 9]).any()),
        ),
        dcc.Loading(html.Div(
            chart_panel(metric_figure(frame, metric), "executiva-metric-chart"), className="mb-4",
        ), type="circle"),
        table_section(frame, "Resultados recentes", (
            "data", "sessoes", "vendas", "faturamento_real", "investimento_total", "roas_real",
        )),
        financial_section(financial_frame, start_date, end_date),
        html.Footer(
            "ROAS global = faturamento real ÷ (Meta Ads + Google Ads + Outros) · TCM = faturamento real ÷ vendas. Valores ausentes: —.",
            className="app-footer",
        ),
    ], id="page-visao-geral-executiva")
