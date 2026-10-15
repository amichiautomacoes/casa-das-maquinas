"""Secoes Bootstrap com os cruzamentos de midia, vendas e clientes."""

import dash_bootstrap_components as dbc
from dash import dcc, html
import pandas as pd

from .insight_charts import (
    client_cost_figure, client_mix_figure, media_performance_figure,
    ticket_distribution_figure, ticket_peaks_figure,
)
from .insights import CPA_SOURCE_MONTHS, client_mix, sales_by_daily_ticket


def _graph(figure, graph_id):
    return dcc.Graph(id=graph_id, figure=figure,
                     config={"displaylogo": False, "responsive": True, "scrollZoom": False})


def _panel(slug, title, subtitle, body, note, prefix):
    title_id = f"{prefix}-{slug}-title"
    return html.Section(dbc.Card([
        dbc.CardHeader([html.H3(title, id=title_id), html.P(subtitle)], class_name="strategy-heading"),
        dbc.CardBody([
            dcc.Loading(body, type="circle"),
            html.Div(note, className="strategy-note"),
        ], class_name="strategy-body"),
    ], class_name="strategy-card"), id=f"{prefix}-{slug}-section", className="mb-4",
        **{"aria-labelledby": title_id})


def media_section(frame: pd.DataFrame, start_date=None, end_date=None, *, prefix="executiva"):
    return _panel(
        "midia", "Performance de Mídia", "Investimento Meta e Google em reais, com o ROAS global no eixo direito.",
        _graph(media_performance_figure(frame, start_date, end_date), f"{prefix}-midia-performance-chart"),
        "O ROAS é faturamento real ÷ (Meta Ads + Google Ads + Outros). Em períodos maiores, ele é recalculado pelas somas mensais. "
        "As linhas mostram como gasto e retorno evoluem juntos; cada eixo tem sua escala. ROAS por canal exige receita atribuída a cada mídia.",
        prefix,
    )


def sales_section(frame: pd.DataFrame, *, prefix="executiva"):
    days = len(sales_by_daily_ticket(frame))
    return _panel(
        "mix", "Mix de Vendas & Produtos",
        f"Vendas agrupadas pelo ticket médio diário · {days} de {len(frame)} dias com vendas e receita válidas.",
        dbc.Row([
            dbc.Col([
                html.H4("Vendas por faixa de ticket", className="insight-plot-title"),
                _graph(ticket_distribution_figure(frame), f"{prefix}-ticket-distribution-chart"),
            ], xs=12, lg=7),
            dbc.Col([
                html.H4("Picos de ticket no tempo", className="insight-plot-title"),
                _graph(ticket_peaks_figure(frame), f"{prefix}-ticket-peaks-chart"),
            ], xs=12, lg=5),
        ], class_name="g-3"),
        "Ticket do dia = faturamento real ÷ vendas. Cada barra soma as vendas dos dias daquela faixa; as bolhas destacam dias com ticket elevado, "
        "com tamanho proporcional às vendas. A distribuição por pedido e a separação entre máquinas e peças dependem de SKU/categoria nos itens vendidos.",
        prefix,
    )


def clients_section(frame: pd.DataFrame, *, prefix="executiva"):
    _, comparable_days = client_mix(frame)
    needs_review = bool(frame["data"].dt.month.isin(CPA_SOURCE_MONTHS).any())
    return _panel(
        "clientes", "Saúde de Clientes & Retenção",
        f"Novos e recorrentes nos mesmos dias · {comparable_days} de {len(frame)} dias comparáveis.",
        html.Div([
            dbc.Alert([
                html.Strong("Revisar origem: "),
                "de maio a setembro, a coluna de recorrentes contém CPA. Esses valores foram excluídos das proporções e dos custos por registro.",
            ], id=f"{prefix}-clientes-source-warning", color="warning", is_open=needs_review, class_name="mx-3 mt-3"),
            dbc.Row([
                dbc.Col([
                    html.H4("Proporção dos registros", className="insight-plot-title"),
                    _graph(client_mix_figure(frame), f"{prefix}-client-mix-chart"),
                ], xs=12, lg=6),
                dbc.Col([
                    html.H4("Investimento por registro · referência", className="insight-plot-title"),
                    _graph(client_cost_figure(frame), f"{prefix}-client-cost-chart"),
                ], xs=12, lg=6),
            ], class_name="g-3"),
        ]),
        [
            html.P("A proporção usa somente os dias com os dois tipos informados. Os números são somas diárias de registros; a contagem de pessoas únicas e a retenção dependem de identificadores de clientes."),
            html.P("Custo de referência = investimento total nos dias com cobertura ÷ registros do tipo nesses dias. Cada tipo usa o investimento total, sem rateio entre novos e recorrentes. O CAC atribuído por tipo exige essa separação de custos."),
        ], prefix,
    )
