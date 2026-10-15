"""Callbacks Dash filtram o DataFrame em memoria, sem repetir a consulta SQL."""

from dash import Input, Output, ctx
import pandas as pd

from .charts import filter_frame
from .financial import empty_financial_frame, filter_financial_frame
from .layout import current_period, date_bounds, period_label
from .pages.visao_geral_executiva import layout as executive_layout


def register_callbacks(app, dataframe: pd.DataFrame, *, financial_frame=None) -> None:
    finances = empty_financial_frame() if financial_frame is None else financial_frame
    available_dates = pd.concat([dataframe[["data"]], finances[["data"]]], ignore_index=True)
    @app.callback(
        Output("date-filter", "min_date_allowed"),
        Output("date-filter", "max_date_allowed"),
        Output("date-filter", "start_date"),
        Output("date-filter", "end_date"),
        Output("year-filter", "value"),
        Input("year-filter", "value"),
        Input("current-month", "n_clicks"),
        Input("current-year", "n_clicks"),
        prevent_initial_call=True,
    )
    def update_date_range(year, month_clicks, year_clicks):
        if ctx.triggered_id in ("current-month", "current-year"):
            year, start, end = current_period("year" if ctx.triggered_id == "current-year" else "month")
            minimum, maximum = date_bounds(available_dates, year)
            return minimum, maximum, start, end, year
        start, end = date_bounds(available_dates, year)
        return start, end, start, end, year

    @app.callback(
        Output("page-content", "children"),
        Output("period-label", "children"),
        Input("year-filter", "value"),
        Input("date-filter", "start_date"),
        Input("date-filter", "end_date"),
        Input("metric-filter", "value"),
    )
    def update_dashboard(year, start_date, end_date, metric):
        selected = filter_frame(dataframe, year, start_date, end_date)
        selected_finances = filter_financial_frame(finances, year, start_date, end_date)
        return (
            executive_layout(selected, metric, start_date=start_date, end_date=end_date,
                             financial_frame=selected_finances), period_label(selected),
        )
