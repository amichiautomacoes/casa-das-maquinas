"""Calcula indicadores e constroi as figuras Plotly a partir do DataFrame."""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .config import METRICS


def format_value(value, kind: str = "number") -> str:
    if value is None or pd.isna(value):
        return "—"
    numeric = float(value) * (100 if kind == "percent" else 1)
    decimals = 0 if kind == "integer" else 2
    text = f"{numeric:,.{decimals}f}".replace(",", "_").replace(".", ",").replace("_", ".")
    if kind == "currency":
        return "R$ " + text
    if kind == "percent":
        return text + "%"
    if kind == "ratio":
        return text + "x"
    return text


def filter_frame(frame: pd.DataFrame, year, start_date, end_date) -> pd.DataFrame:
    mask = pd.Series(True, index=frame.index)
    if year not in (None, "all"):
        mask &= frame["data"].dt.year == int(year)
    if start_date:
        mask &= frame["data"] >= pd.Timestamp(start_date)
    if end_date:
        mask &= frame["data"] <= pd.Timestamp(end_date)
    return frame.loc[mask].copy()


def safe_ratio(numerator, denominator):
    if pd.isna(numerator) or pd.isna(denominator) or denominator <= 0:
        return None
    return numerator / denominator


def attainment_figure(attainment, color: str) -> go.Figure:
    """Bullet chart compacto com o marco de 100% e faixas de atingimento."""
    figure = go.Figure()
    if attainment is not None:
        value = max(0, attainment * 100)
        ceiling = max(120, value * 1.08)
        figure.add_trace(go.Indicator(
            mode="gauge", value=value,
            gauge={
                "shape": "bullet", "axis": {"range": [0, ceiling], "visible": False},
                "bar": {"color": color, "thickness": 0.4},
                "bgcolor": "rgba(0,0,0,0)", "borderwidth": 0,
                "steps": [
                    {"range": [0, 90], "color": "#fbe9ec"},
                    {"range": [90, 100], "color": "#fff2d8"},
                    {"range": [100, ceiling], "color": "#e2f3eb"},
                ],
                "threshold": {"value": 100, "line": {"color": "#17324d", "width": 2}, "thickness": 0.85},
            },
            domain={"x": [0, 1], "y": [0.2, 0.9]},
        ))
    figure.update_layout(
        template="plotly_white", height=58,
        margin={"l": 2, "r": 2, "t": 4, "b": 4},
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    return figure


def kpi_sparkline(frame: pd.DataFrame, values: pd.Series, color: str, kind: str) -> go.Figure:
    """Evolucao diaria contextual; o numero principal usa os totais do periodo."""
    series = pd.DataFrame({"data": frame["data"], "value": values})
    series = _daily_grid(series)
    figure = go.Figure(go.Scatter(
        x=series["data"], y=series["value"], mode="lines",
        line={"color": color, "width": 2}, connectgaps=False,
        hovertemplate="%{x|%d/%m/%Y}<br>" + (
            "R$ %{y:,.2f}" if kind == "currency" else "%{y:,.2f}x"
        ) + "<extra></extra>",
    ))
    figure.update_layout(
        template="plotly_white", height=58,
        margin={"l": 2, "r": 2, "t": 6, "b": 4}, showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Segoe UI, Arial, sans-serif"}, separators=",.",
        xaxis={"visible": False, "fixedrange": True},
        yaxis={"visible": False, "fixedrange": True, "rangemode": "tozero"},
    )
    return figure


def _figure(title: str) -> go.Figure:
    figure = go.Figure()
    figure.update_layout(
        title={"text": title, "font": {"size": 17}},
        template="plotly_white", height=350,
        margin={"l": 45, "r": 24, "t": 65, "b": 45},
        font={"family": "Arial, sans-serif", "color": "#17324d"},
        hovermode="x unified", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        legend={"orientation": "h", "y": 1.12, "x": 0},
    )
    figure.update_xaxes(title=None, tickformat="%d/%m/%Y")
    return figure


def _daily_grid(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    # Datas sem registro viram lacunas, evitando linhas que ligam meses ausentes.
    days = pd.date_range(frame["data"].min(), frame["data"].max(), freq="D", name="data")
    return frame.set_index("data").reindex(days).reset_index()


def period_totals(frame: pd.DataFrame, columns, start_date=None, end_date=None):
    """Alinha medidas pelo calendario e agrega meses sem converter ausencias em zero."""
    values = frame.set_index("data")[list(columns)].sort_index()
    start = pd.Timestamp(start_date) if start_date else values.index.min()
    end = pd.Timestamp(end_date) if end_date else values.index.max()
    monthly = not (pd.isna(start) or pd.isna(end)) and start.to_period("M") != end.to_period("M")
    if pd.isna(start) or pd.isna(end) or start > end:
        return values.iloc[:0], monthly

    values = values.loc[start:end]
    if monthly:
        # min_count=1 impede que um mes sem valores seja exibido como zero.
        values = values.resample("MS").sum(min_count=1)
        calendar = pd.date_range(start.to_period("M").start_time, end.to_period("M").start_time, freq="MS")
    else:
        calendar = pd.date_range(start, end, freq="D")
    return values.reindex(calendar), monthly


def revenue_figure(frame: pd.DataFrame, start_date=None, end_date=None) -> go.Figure:
    """Curva de Desacoplamento: receita e midia em dois eixos Y independentes."""
    values, monthly = period_totals(frame, ("faturamento_real", "investimento_total"), start_date, end_date)
    figure = make_subplots(specs=[[{"secondary_y": True}]])
    months = ("Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez")
    labels = [f"{months[day.month - 1]}/{day.year}" if monthly else day.strftime("%d/%m/%Y") for day in values.index]
    for column, name, color, secondary, dash, symbol in (
        ("faturamento_real", "Faturamento Real", "#326bba", False, "solid", "circle"),
        ("investimento_total", "Investimento em Mídia", "#d97706", True, "dash", "diamond"),
    ):
        figure.add_trace(go.Scatter(
            x=values.index.to_pydatetime().tolist(), y=values[column].tolist(),
            name=name, mode="lines+markers", connectgaps=False,
            line={"color": color, "width": 3, "dash": dash},
            marker={"size": 6 if monthly else 4, "symbol": symbol},
            customdata=[
                [label, format_value(value, "currency")]
                for label, value in zip(labels, values[column])
            ],
            hovertemplate="%{customdata[0]}<br>" + name + ": <b>%{customdata[1]}</b><extra></extra>",
        ), secondary_y=secondary)
        figure.update_yaxes(
            title={"text": "Investimento (R$)" if secondary else "Faturamento (R$)",
                   "font": {"color": color, "size": 12}, "standoff": 12},
            tickfont={"color": color, "size": 11}, tickformat=",.0f",
            rangemode="tozero", separatethousands=True, automargin=True,
            showgrid=not secondary, gridcolor="rgba(23,50,77,0.12)", zeroline=False,
            secondary_y=secondary,
        )
    stride = max(1, (len(values) + 11) // 12)
    figure.update_layout(
        template="plotly_white", height=430,
        margin={"l": 64, "r": 64, "t": 16, "b": 80},
        font={"family": "Segoe UI, Arial, sans-serif", "color": "#17324d", "size": 12},
        hovermode="x unified", separators=",.",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        legend={"orientation": "h", "y": -0.23, "x": 0, "font": {"size": 11}},
        meta={"aggregation": "monthly" if monthly else "daily"},
    )
    figure.update_xaxes(
        title={"text": "Meses do ano" if monthly else "Dias do mês", "standoff": 12},
        type="date", tickmode="array", tickvals=values.index[::stride].to_pydatetime().tolist(),
        ticktext=labels[::stride] if monthly else [day.strftime("%d") for day in values.index[::stride]],
        hoverformat="%m/%Y" if monthly else "%d/%m/%Y",
        showgrid=False, zeroline=False, automargin=True,
    )
    if len(values):
        # Mantem visiveis os limites do filtro mesmo sem valores nas pontas.
        padding = pd.Timedelta(days=10 if monthly else 0.5)
        figure.update_xaxes(range=[values.index[0] - padding, values.index[-1] + padding])
    if not values.notna().any().any():
        figure.add_annotation(
            text="Sem dados no período selecionado", x=0.5, y=0.5,
            xref="paper", yref="paper", showarrow=False,
            font={"color": "#52657a", "size": 14},
        )
    return figure


def metric_figure(frame: pd.DataFrame, metric: str) -> go.Figure:
    metric = metric if metric in METRICS else "sessoes"
    name, kind = METRICS[metric]
    figure = _figure(name + " por dia")
    values = _daily_grid(frame)
    figure.add_trace(go.Scatter(
        x=values["data"], y=values[metric], name=name, mode="lines+markers",
        line={"color": "#326bba", "width": 2}, marker={"size": 4}, connectgaps=False,
    ))
    if kind == "percent":
        figure.update_yaxes(tickformat=".1%")
    elif kind == "currency":
        figure.update_yaxes(title="R$", separatethousands=True)
    elif kind == "ratio":
        figure.update_yaxes(ticksuffix="x")
    if frame.empty:
        figure.add_annotation(text="Sem dados no período selecionado", x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)
    return figure
