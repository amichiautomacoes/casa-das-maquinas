"""Estrutura principal: navegacao, filtros compartilhados e pagina ativa."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

import dash_bootstrap_components as dbc
from dash import dcc, html
import pandas as pd

from .charts import filter_frame
from .config import METRICS
from .financial import empty_financial_frame, filter_financial_frame
from .pages import PAGES, Page


def current_period(mode: str = "month", today: date | None = None):
    today = today or datetime.now(ZoneInfo("America/Sao_Paulo")).date()
    start = date(today.year, 1 if mode == "year" else today.month, 1)
    return str(today.year), start.isoformat(), today.isoformat()


def date_bounds(frame: pd.DataFrame, year):
    if year not in (None, "all"):
        return f"{int(year):04d}-01-01", f"{int(year):04d}-12-31"
    current_year = int(current_period()[0])
    first = min(current_year, int(frame["data"].dt.year.min())) if not frame.empty else current_year
    last = max(current_year, int(frame["data"].dt.year.max())) if not frame.empty else current_year
    return f"{first:04d}-01-01", f"{last:04d}-12-31"


def period_label(frame: pd.DataFrame) -> str:
    days = len(frame)
    unit = "dia" if days == 1 else "dias"
    return f"{days} {unit} com registro no período selecionado"


def create_layout(frame: pd.DataFrame, pages: tuple[Page, ...] = PAGES, *, financial_frame=None):
    initial_page = pages[0]
    finances = empty_financial_frame() if financial_frame is None else financial_frame
    available_dates = pd.concat([frame[["data"]], finances[["data"]]], ignore_index=True)
    year, start, end = current_period()
    years = sorted(set(available_dates["data"].dt.year.unique().tolist()) | {int(year)})
    minimum, maximum = date_bounds(available_dates, year)
    selected = filter_frame(frame, year, start, end)
    selected_finances = filter_financial_frame(finances, year, start, end)
    available_until = frame["data"].max().strftime("%d/%m/%Y") if not frame.empty else "sem registros"
    return html.Div([
        html.Header(dbc.Container([
            html.Div([
                html.Div("CM", className="brand-mark"),
                html.Div([html.H1("Casa das Máquinas"), html.P("Indicadores de desempenho")]),
            ], className="brand"),
            html.Div([html.Span("Dados disponíveis até", className="header-caption"), html.Strong(available_until)], className="data-status"),
        ], fluid=True, class_name="header-inner"), className="app-header"),
        dbc.Container([
            dbc.Tabs([
                dbc.Tab(label=page.title, tab_id=page.slug) for page in pages
            ], id="main-tabs", active_tab=initial_page.slug, class_name="page-tabs"),
            html.Div([
                html.Div([
                    html.Span("Acumulado", className="period-shortcuts-label"),
                    dbc.ButtonGroup([
                        dbc.Button("Mês atual", id="current-month", n_clicks=0, color="primary", outline=True, size="sm"),
                        dbc.Button("Ano atual", id="current-year", n_clicks=0, color="primary", outline=True, size="sm"),
                    ], size="sm"),
                    html.Span("Até hoje · ou selecione um período abaixo", className="period-shortcuts-hint"),
                ], className="period-shortcuts"),
                html.Div([
                    html.Div([html.Label("Ano", htmlFor="year-filter"), dcc.Dropdown(
                        id="year-filter", options=[{"label": "Todos", "value": "all"}] + [{"label": str(value), "value": str(value)} for value in years],
                        value=year, clearable=False,
                    )], className="year-control"),
                    html.Div([html.Label("Período"), dcc.DatePickerRange(
                        id="date-filter", start_date=start, end_date=end,
                        min_date_allowed=minimum, max_date_allowed=maximum,
                        display_format="DD/MM/YYYY", first_day_of_week=1,
                        start_date_placeholder_text="Data inicial", end_date_placeholder_text="Data final",
                    )], className="date-control"),
                    html.Div([html.Label("Indicador do gráfico", htmlFor="metric-filter"), dcc.Dropdown(
                        id="metric-filter", options=[{"label": label, "value": name} for name, (label, _) in METRICS.items()],
                        value="sessoes", clearable=False,
                    )], id="metric-control", className="metric-control",
                        style={} if initial_page.has_metric_selector else {"display": "none"}),
                ], className="filters-grid"),
            ], className="filters-panel"),
            html.Div(period_label(selected), id="period-label", className="period-label"),
            dcc.Loading(html.Main(initial_page.layout(selected, "sessoes", start_date=start, end_date=end,
                                                     financial_frame=selected_finances), id="page-content"), type="circle"),
        ], fluid=True, class_name="main-container"),
    ])
