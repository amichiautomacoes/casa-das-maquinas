"""Ultima secao executiva: cascata da DRE e confronto com o planejamento."""

import dash_bootstrap_components as dbc
from dash import dcc, html
import pandas as pd
import plotly.graph_objects as go

from .charts import format_value
from .components import metric_cards
from .executive import attainment_status
from .financial import empty_financial_frame, financial_rows, financial_summary


def financial_waterfall(frame: pd.DataFrame) -> go.Figure:
    summary = financial_summary(frame)
    figure = go.Figure()
    if summary.gross_profit is not None:
        deductions = [-value if value else 0.0 for value in (summary.taxes, summary.returns, summary.cpv)]
        values = [summary.revenue, *deductions, summary.gross_profit]
        figure.add_trace(go.Waterfall(
            name="DRE", orientation="v",
            x=["Receita<br>bruta", "Impostos<br>sobre vendas", "Devoluções", "CPV", "Lucro<br>bruto"],
            measure=["absolute", "relative", "relative", "relative", "total"],
            y=[*values[:-1], 0],
            text=[format_value(value, "currency") for value in values],
            textposition="outside", textfont={"size": 11}, cliponaxis=False,
            customdata=[format_value(value, "currency") for value in values],
            hovertemplate="%{x}<br>%{customdata}<extra></extra>",
            connector={"line": {"color": "#c4cfdd", "width": 1}},
            increasing={"marker": {"color": "#326bba"}},
            decreasing={"marker": {"color": "#c43d4a"}},
            totals={"marker": {"color": "#167d57" if summary.gross_profit >= 0 else "#c43d4a"}},
        ))
    else:
        figure.add_annotation(
            text="Sem DRE completa para os meses selecionados", x=0.5, y=0.5,
            xref="paper", yref="paper", showarrow=False, font={"color": "#64758b", "size": 13},
        )
    figure.update_layout(
        template="plotly_white", height=420, showlegend=False, separators=",.",
        margin={"l": 60, "r": 30, "t": 50, "b": 65},
        font={"family": "Segoe UI, Arial, sans-serif", "color": "#17324d", "size": 12},
        paper_bgcolor="white", plot_bgcolor="white", waterfallgap=0.35,
    )
    figure.update_xaxes(automargin=True, fixedrange=True)
    figure.update_yaxes(title="R$", tickformat=",.0f", rangemode="tozero", automargin=True, gridcolor="#e9eef5")
    return figure


def _financial_table(frame: pd.DataFrame):
    rows = financial_rows(frame)
    if rows.empty:
        return html.P("Sem valores financeiros nos meses selecionados.", className="empty-message")
    columns = (
        ("receita_bruta", "Receita bruta", "currency"),
        ("receita_prevista", "Receita prevista", "currency"),
        ("impostos", "Impostos", "currency"),
        ("devolucoes", "Devoluções", "currency"),
        ("cpv", "CPV", "currency"),
        ("lucro_bruto_calculado", "Lucro bruto", "currency"),
        ("margem_bruta", "Margem bruta", "percent"),
        ("margem_liquida", "Margem líquida", "percent"),
    )
    head = html.Thead(html.Tr([html.Th("Mês"), *[html.Th(label) for _, label, _ in columns], html.Th("Dias com receita")]))
    body = html.Tbody([
        html.Tr([
            html.Td(row["data"].strftime("%m/%Y")),
            *[html.Td(format_value(row[column], kind)) for column, _, kind in columns],
            html.Td(f"{int(row['dias_com_receita'])}/{row['data'].days_in_month}"),
        ]) for row in rows.to_dict("records")
    ])
    return dbc.Table([head, body], responsive=True, hover=True, class_name="results-table mb-0",
                     id="executiva-financial-table")


def financial_section(frame: pd.DataFrame | None = None, start_date=None, end_date=None):
    frame = empty_financial_frame() if frame is None else frame
    rows = financial_rows(frame)
    summary = financial_summary(frame)
    partial = bool(
        (start_date and not pd.Timestamp(start_date).is_month_start)
        or (end_date and not pd.Timestamp(end_date).is_month_end)
    )
    mismatch = (
        (rows["receita_bruta"] - rows["receita_plano_real"]).abs().gt(0.02)
        | (rows["lucro_bruto_calculado"] - rows["lucro_bruto_fonte"]).abs().gt(0.02)
    )
    missing = not rows.empty and rows[["receita_bruta", "impostos", "devolucoes", "cpv"]].isna().any().any()
    status, _, _ = attainment_status(summary.attainment)
    return html.Section(dbc.Card([
        dbc.CardHeader([
            html.Span("Resultado financeiro", className="strategy-eyebrow"),
            html.H3("Da receita ao lucro", id="executiva-financial-title"),
            html.P(f"DRE × PLANO 2026 · {summary.months} {'mês' if summary.months == 1 else 'meses'} com receitas informadas no período."),
        ], class_name="strategy-heading"),
        dbc.CardBody([
            dbc.Alert(
                "A DRE é mensal: os valores abaixo incluem os meses completos abrangidos pelo filtro de datas. A coluna de cobertura informa os dias com receita registrada em cada mês.",
                id="executiva-financial-month-scope", color="info", is_open=partial and summary.months > 0,
                class_name="mx-3 mt-3",
            ),
            dbc.Alert(
                "Há diferenças entre os valores de origem e os valores cruzados ou recalculados. A cascata usa receita, deduções e CPV da DRE.",
                id="executiva-financial-reconciliation", color="warning", is_open=bool(mismatch.any()),
                class_name="mx-3 mt-3",
            ),
            dbc.Alert(
                "Há meses com custos ou receita ausentes. O resultado acumulado fica indisponível até completar os valores da DRE.",
                id="executiva-financial-incomplete", color="warning", is_open=bool(missing), class_name="mx-3 mt-3",
            ),
            html.Div(metric_cards([
                ("Receita bruta", format_value(summary.revenue, "currency")),
                ("Lucro bruto", format_value(summary.gross_profit, "currency")),
                ("Margem bruta / receita bruta", format_value(summary.gross_margin, "percent")),
                ("Margem líquida / receita bruta", format_value(summary.net_margin, "percent")),
            ]), className="financial-summary"),
            html.Div([
                html.Span("Receita prevista nos meses analisados: "),
                html.Strong(format_value(summary.planned_revenue, "currency"), id="executiva-financial-planned"),
                dbc.Badge(
                    format_value(summary.attainment, "percent") + " do previsto" if summary.attainment is not None else "Sem comparação",
                    id="executiva-financial-attainment", color=status, pill=True,
                ),
            ], className="financial-plan"),
            dcc.Loading(dcc.Graph(
                id="executiva-financial-waterfall", figure=financial_waterfall(frame),
                config={"displaylogo": False, "responsive": True,
                        "toImageButtonOptions": {"filename": "dre-receita-ao-lucro", "scale": 2}},
            ), type="circle"),
            _financial_table(frame),
            html.Div([
                html.P("Lucro bruto = receita bruta − impostos sobre vendas − devoluções − CPV. As devoluções estão na DRE e entram na cascata para reconciliar o resultado."),
                html.P("Margem bruta = lucro bruto ÷ receita bruta. A margem de lucro líquida usa o resultado líquido da DRE, após despesas e provisões. As margens do período são calculadas pelas somas, sem média dos percentuais mensais."),
                html.P("Fonte: DRE cruzada com a receita prevista e realizada de PLANO 2026, por competência. O ano segue as datas das abas mensais de origem. Meses sem receitas informadas ficam fora do acumulado."),
            ], className="strategy-note mt-3"),
        ], class_name="strategy-body"),
    ], class_name="strategy-card"), id="executiva-financial-section", className="mb-4",
        **{"aria-labelledby": "executiva-financial-title"})
