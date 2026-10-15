"""Componentes de apresentacao compartilhados pelas paginas do dashboard."""

import dash_bootstrap_components as dbc
from dash import dcc, html
import pandas as pd

from .charts import attainment_figure, format_value, kpi_sparkline
from .config import METRICS
from .executive import MARKETING_CHANNELS, attainment_status, executive_summary, marketing_by_day


def page_header(title: str, description: str):
    return html.Div([
        html.Div([html.H2(title), html.P(description)]),
        html.Span("Resultados de e-commerce", className="section-tag"),
    ], className="section-heading")


def metric_cards(items: list[tuple[str, str]]):
    width = 12 // min(len(items), 6) if items else 12
    return dbc.Row([
        dbc.Col(html.Div([
            html.Div(label, className="kpi-label"),
            html.Div(value, className="kpi-value"),
        ], className="kpi-card"), xs=12, sm=6, lg=4, xl=width)
        for label, value in items
    ], class_name="g-3 mb-4")


def executive_kpi_cards(frame: pd.DataFrame, start_date=None, end_date=None):
    summary = executive_summary(frame, start_date, end_date)
    status, status_label, color = attainment_status(summary.attainment)
    investment = marketing_by_day(frame)
    roas = frame["faturamento_real"] / investment.where(investment > 0)
    ticket = frame["faturamento_real"] / frame["vendas"].where(frame["vendas"] > 0)

    def graph(figure, graph_id, label):
        return html.Div(dcc.Graph(
            id=graph_id, figure=figure,
            config={"displayModeBar": False, "responsive": True},
            className="executive-kpi-chart",
        ), role="img", **{"aria-label": label})

    def card(slug, label, value, kind, badge, detail, visual, footer, accent):
        return dbc.Col(dbc.Card(dbc.CardBody([
            html.Div([
                html.H3(label, className="executive-kpi-label"), badge,
            ], className="executive-kpi-heading"),
            html.Div(format_value(value, kind), id=f"executiva-{slug}-value",
                     className="executive-kpi-value"),
            html.Div(detail, className="executive-kpi-detail"),
            html.Div(visual, className="executive-kpi-visual"),
            html.Div(footer, className="executive-kpi-footer"),
        ]), id=f"executiva-{slug}-card", class_name=f"executive-kpi-card executive-kpi-{accent}"),
            xs=12, md=6, xl=3)

    if summary.target is None:
        target_detail = "Meta não cadastrada"
        revenue_visual = html.Div("Atingimento disponível após definir a meta.", className="executive-kpi-placeholder")
    else:
        target_detail = "Meta do período: " + format_value(summary.target, "currency")
        revenue_visual = graph(
            attainment_figure(summary.attainment, color), "executiva-attainment-chart",
            "Atingimento da meta: " + format_value(summary.attainment, "percent"),
        ) if summary.attainment is not None else html.Div("Sem faturamento no período.", className="executive-kpi-placeholder")
    revenue_badge = dbc.Badge(
        format_value(summary.attainment, "percent") + " atingido" if summary.attainment is not None else "Sem meta" if summary.target is None else "Sem dados",
        id="executiva-attainment-badge", color=status, pill=True,
        class_name="executive-kpi-badge", title=status_label,
    )
    channel_totals = [
        html.Span([
            html.Span(className="channel-dot", style={"backgroundColor": channel_color}),
            f"{label}: {format_value(frame[column].sum(min_count=1), 'currency')}",
        ]) for column, label, channel_color in MARKETING_CHANNELS
    ]
    missing_channels = [
        label for column, label, _ in MARKETING_CHANNELS if frame[column].isna().any()
    ]
    channel_note = (
        "Há valores não informados em " + ", ".join(missing_channels) + ". Total dos valores registrados."
        if missing_channels else "Soma dos três canais no período selecionado."
    )
    return html.Section([
        dbc.Row([
            card("revenue", "Faturamento Real vs. Meta", summary.revenue, "currency", revenue_badge,
                 target_detail, revenue_visual,
                 html.Span(status_label + " · Meta proporcional ao período" if summary.target is not None else "Defina o planejamento para comparar os resultados."),
                 status),
            card("roas", "ROAS Real Global", summary.roas, "ratio",
                 dbc.Badge("Retorno", color="light", text_color="dark", pill=True, class_name="executive-kpi-badge"),
                 "Faturamento real ÷ investimento em marketing",
                 graph(kpi_sparkline(frame, roas, "#326bba", "ratio"), "executiva-roas-sparkline", "Evolução diária do ROAS"),
                 "Retorno acumulado · Linha: ROAS por dia", "blue"),
            card("investment", "Investimento Total em Marketing", summary.investment, "currency",
                 dbc.Badge("Mídia", color="light", text_color="dark", pill=True, class_name="executive-kpi-badge"),
                 "Meta Ads + Google Ads + Outros",
                 graph(kpi_sparkline(frame, investment, "#17a398", "currency"), "executiva-investment-sparkline", "Evolução diária do investimento em marketing"),
                 html.Div(channel_totals, className="executive-channel-totals", title=channel_note), "teal"),
            card("ticket", "Ticket Médio Geral (TCM)", summary.ticket, "currency",
                 dbc.Badge("Por venda", color="light", text_color="dark", pill=True, class_name="executive-kpi-badge"),
                 "Faturamento real ÷ vendas do período",
                 graph(kpi_sparkline(frame, ticket, "#8b78b8", "currency"), "executiva-ticket-sparkline", "Evolução diária do ticket médio"),
                 format_value(summary.sales, "integer") + " vendas · Linha: ticket por dia", "violet"),
        ], class_name="g-3"),
    ], id="executiva-kpis", className="executive-kpis mb-4", **{"aria-label": "Resumo dos quatro indicadores principais"})


def chart_panel(figure, graph_id: str):
    return html.Div(dcc.Graph(
        id=graph_id, figure=figure, config={"displaylogo": False},
    ), className="chart-panel")


def recent_table(frame: pd.DataFrame, columns: tuple[str, ...]):
    if frame.empty:
        return html.P("Nenhum resultado para este período.", className="empty-message")
    header = html.Thead(html.Tr([
        html.Th("Data" if name == "data" else METRICS[name][0]) for name in columns
    ]))
    rows = []
    for row in frame.sort_values("data", ascending=False).head(12).to_dict("records"):
        rows.append(html.Tr([
            html.Td(row[name].strftime("%d/%m/%Y") if name == "data"
                    else format_value(row[name], METRICS[name][1]))
            for name in columns
        ]))
    return dbc.Table([header, html.Tbody(rows)], responsive=True, hover=True,
                     class_name="results-table mb-0")


def table_section(frame: pd.DataFrame, title: str, columns: tuple[str, ...]):
    return html.Div([
        html.Div([html.H3(title), html.Span("Últimos 12 dias com registro")],
                 className="table-heading"),
        recent_table(frame, columns),
    ], className="table-panel")


def pending_section(title: str, explanation: str):
    return html.Section([
        html.H3(title), html.P(explanation),
    ], className="information-panel")
