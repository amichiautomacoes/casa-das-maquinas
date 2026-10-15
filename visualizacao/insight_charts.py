"""Figuras Plotly para os cruzamentos de midia, vendas e clientes."""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .charts import format_value, period_totals
from .executive import marketing_by_day
from .insights import client_cost_reference, client_mix, sales_by_daily_ticket, ticket_distribution


BLUE = "#326bba"
TEAL = "#167d57"
ORANGE = "#d97706"
TICKET_COLORS = ("#a6bddb", "#6493c7", "#326bba", "#8b78b8", "#d97706")


def _style(figure: go.Figure, height: int = 380) -> go.Figure:
    figure.update_layout(
        template="plotly_white", height=height,
        margin={"l": 55, "r": 25, "t": 20, "b": 60},
        font={"family": "Segoe UI, Arial, sans-serif", "color": "#17324d", "size": 12},
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", separators=",.",
        legend={"orientation": "h", "y": -0.2, "x": 0, "font": {"size": 11}},
    )
    figure.update_xaxes(automargin=True, showgrid=False)
    figure.update_yaxes(automargin=True, gridcolor="rgba(23,50,77,0.12)", zeroline=False, rangemode="tozero")
    return figure


def _empty(figure: go.Figure, message: str):
    figure.add_annotation(text=message, x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False,
                          font={"size": 13, "color": "#52657a"})
    return figure


def media_performance_figure(frame: pd.DataFrame, start_date=None, end_date=None) -> go.Figure:
    data = frame.copy()
    data["marketing_total"] = marketing_by_day(frame)
    values, monthly = period_totals(
        data, ("facebook_ads", "google_ads", "faturamento_real", "marketing_total"), start_date, end_date,
    )
    values["roas_global"] = values["faturamento_real"] / values["marketing_total"].where(values["marketing_total"] > 0)
    figure = _style(make_subplots(specs=[[{"secondary_y": True}]]), height=420)
    months = ("Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez")
    labels = [f"{months[day.month - 1]}/{day.year}" if monthly else day.strftime("%d/%m/%Y") for day in values.index]
    for column, label, color, secondary, dash in (
        ("facebook_ads", "Investimento Meta", BLUE, False, "solid"),
        ("google_ads", "Investimento Google", TEAL, False, "solid"),
        ("roas_global", "ROAS global", ORANGE, True, "dash"),
    ):
        figure.add_trace(go.Scatter(
            x=values.index.to_pydatetime().tolist(), y=values[column].tolist(), name=label,
            mode="lines+markers", connectgaps=False, line={"color": color, "width": 2.5, "dash": dash},
            marker={"size": 5, "symbol": "diamond" if secondary else "circle"},
            customdata=[[date_label, format_value(value, "ratio" if secondary else "currency")]
                        for date_label, value in zip(labels, values[column])],
            hovertemplate="%{customdata[0]}<br>" + label + ": <b>%{customdata[1]}</b><extra></extra>",
        ), secondary_y=secondary)
    stride = max(1, (len(values) + 11) // 12)
    figure.update_layout(hovermode="x unified", margin={"r": 60, "b": 85},
                         meta={"aggregation": "monthly" if monthly else "daily"})
    figure.update_xaxes(
        title="Meses do ano" if monthly else "Dias do mês", type="date", tickmode="array",
        tickvals=values.index[::stride].to_pydatetime().tolist(),
        ticktext=labels[::stride] if monthly else [day.strftime("%d") for day in values.index[::stride]],
    )
    if len(values):
        padding = pd.Timedelta(days=10 if monthly else 0.5)
        figure.update_xaxes(range=[values.index[0] - padding, values.index[-1] + padding])
    figure.update_yaxes(title="Investimento (R$)", tickformat=",.0f", secondary_y=False)
    figure.update_yaxes(title={"text": "ROAS global", "font": {"color": ORANGE}}, ticksuffix="x",
                        tickformat=".1f", tickfont={"color": ORANGE}, showgrid=False, secondary_y=True)
    if not values[["facebook_ads", "google_ads", "roas_global"]].notna().any().any():
        _empty(figure, "Sem dados no período selecionado")
    return figure


def ticket_distribution_figure(frame: pd.DataFrame) -> go.Figure:
    values = ticket_distribution(frame)
    figure = _style(go.Figure())
    if not values["dias"].sum():
        return _empty(figure, "Sem vendas com faturamento informado no período")
    figure.add_trace(go.Bar(
        x=values["vendas"].tolist(), y=values["faixa_ticket"].astype(str).tolist(), orientation="h",
        marker_color=TICKET_COLORS, text=[format_value(value, "integer") for value in values["vendas"]],
        textposition="auto", cliponaxis=False,
        customdata=[[int(row.dias), format_value(row.faturamento, "currency"), format_value(row.participacao, "percent")]
                    for row in values.itertuples()],
        hovertemplate="%{y}<br>Vendas dos dias desta faixa: %{x:,.0f}<br>Dias: %{customdata[0]}<br>Receita: %{customdata[1]}<br>Participação: %{customdata[2]}<extra></extra>",
    ))
    figure.update_layout(showlegend=False)
    figure.update_xaxes(title="Vendas agrupadas pelo ticket médio do dia", tickformat=",.0f")
    figure.update_yaxes(autorange="reversed", showgrid=False)
    return figure


def ticket_peaks_figure(frame: pd.DataFrame) -> go.Figure:
    values = sales_by_daily_ticket(frame)
    figure = _style(go.Figure())
    if values.empty:
        return _empty(figure, "Sem vendas com faturamento informado no período")
    figure.add_trace(go.Scatter(
        x=values["data"].tolist(), y=values["ticket_calculado"].tolist(),
        mode="markers", name="Ticket médio diário",
        marker={"size": values["vendas"].tolist(), "sizemode": "area",
                "sizeref": 2 * values["vendas"].max() / 32 ** 2, "sizemin": 4,
                "color": values["ticket_calculado"].tolist(),
                "colorscale": [[0, BLUE], [1, ORANGE]], "showscale": False, "opacity": 0.8},
        customdata=[[format_value(row.ticket_calculado, "currency"), format_value(row.vendas, "integer"),
                     format_value(row.faturamento_real, "currency")]
                    for row in values.itertuples()],
        hovertemplate="%{x|%d/%m/%Y}<br>Ticket médio: %{customdata[0]}<br>Vendas: %{customdata[1]}<br>Receita: %{customdata[2]}<extra></extra>",
    ))
    figure.update_layout(showlegend=False)
    figure.update_xaxes(title="Data · tamanho da bolha = vendas", tickformat="%d/%m/%Y")
    figure.update_yaxes(title="Ticket médio do dia (R$)", tickformat=",.0f")
    return figure


def client_mix_figure(frame: pd.DataFrame) -> go.Figure:
    counts, days = client_mix(frame)
    figure = _style(go.Figure())
    figure.update_xaxes(visible=False)
    figure.update_yaxes(visible=False)
    if not days:
        return _empty(figure, "Sem dias válidos com os dois tipos de cliente")
    if counts.sum(min_count=1) <= 0:
        return _empty(figure, "Nenhum cliente registrado nos dias comparáveis")
    figure.add_trace(go.Pie(
        labels=["Novos clientes", "Clientes recorrentes"], values=counts.tolist(), hole=0.68,
        marker={"colors": [BLUE, ORANGE], "line": {"color": "white", "width": 3}},
        sort=False, textinfo="percent", textposition="inside",
        customdata=[format_value(count, "integer") for count in counts],
        hovertemplate="%{label}<br>%{customdata} registros<br>%{percent}<extra></extra>",
    ))
    figure.add_annotation(text=f"<b>{days}</b><br>dias comparáveis", x=0.5, y=0.5,
                          xref="paper", yref="paper", showarrow=False,
                          font={"color": "#17324d", "size": 15})
    return figure


def client_cost_figure(frame: pd.DataFrame) -> go.Figure:
    values = client_cost_reference(frame)
    figure = _style(go.Figure())
    valid = values["custo_por_registro"].notna()
    if not valid.any():
        return _empty(figure, "Sem investimento e registros válidos para calcular")
    figure.add_trace(go.Bar(
        x=values["tipo"].tolist(), y=values["custo_por_registro"].tolist(),
        marker_color=[BLUE, ORANGE],
        text=[format_value(value, "currency") for value in values["custo_por_registro"]], textposition="auto",
        customdata=[[int(row.dias), format_value(row.investimento, "currency"), format_value(row.registros, "integer")]
                    for row in values.itertuples()],
        hovertemplate="%{x}<br>Investimento por registro: R$ %{y:,.2f}<br>Dias com cobertura: %{customdata[0]}<br>Investimento total nesses dias: %{customdata[1]}<br>Registros do tipo: %{customdata[2]}<extra></extra>",
    ))
    for row in values.loc[~valid].itertuples():
        figure.add_annotation(x=row.tipo, y=0, text="Sem dados", showarrow=False, yshift=15)
    figure.update_layout(showlegend=False)
    figure.update_yaxes(title="Investimento por registro (R$)", tickformat=",.0f")
    return figure
