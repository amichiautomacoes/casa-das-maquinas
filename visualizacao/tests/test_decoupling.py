"""Regras de agregacao e alinhamento temporal da Curva de Desacoplamento."""

import unittest

import pandas as pd

from visualizacao.charts import filter_frame, revenue_figure
from visualizacao.executive import marketing_by_day
from test_executive import executive_dataframe


class DecouplingTests(unittest.TestCase):
    def setUp(self):
        self.frame = filter_frame(executive_dataframe(), "2026", None, None)
        self.frame["investimento_total"] = marketing_by_day(self.frame)

    def test_daily_series_use_matching_dates_and_independent_y_axes(self):
        snapshot = self.frame.copy(deep=True)
        figure = revenue_figure(self.frame, "2026-07-01", "2026-07-31")
        revenue, investment = figure.data
        self.assertEqual(revenue.yaxis, "y")
        self.assertEqual(investment.yaxis, "y2")
        self.assertEqual(figure.layout.yaxis2.overlaying, "y")
        self.assertEqual(figure.layout.yaxis2.side, "right")
        self.assertEqual(revenue.line.color, "#326bba")
        self.assertEqual(investment.line.color, "#d97706")
        self.assertEqual(list(revenue.x), list(investment.x))
        self.assertEqual(len(revenue.x), 31)
        self.assertEqual(revenue.y[0], 1000)
        self.assertEqual(investment.y[0], 100)
        self.assertTrue(pd.isna(revenue.y[1]))
        self.assertTrue(pd.isna(investment.y[1]))
        self.assertEqual(revenue.y[2], 500)
        self.assertEqual(investment.y[2], 400)
        self.assertFalse(revenue.connectgaps)
        self.assertFalse(investment.connectgaps)
        self.assertEqual(figure.layout.meta["aggregation"], "daily")
        self.assertEqual(revenue.customdata[0][1], "R$ 1.000,00")
        self.assertEqual(revenue.customdata[1][1], "—")
        pd.testing.assert_frame_equal(self.frame, snapshot)

    def test_year_view_sums_each_measure_and_preserves_empty_calendar_months(self):
        figure = revenue_figure(self.frame, "2026-01-01", "2026-12-31")
        revenue, investment = figure.data
        self.assertEqual(len(revenue.x), 12)
        self.assertEqual(figure.layout.meta["aggregation"], "monthly")
        self.assertEqual(revenue.y[6], 1500)
        self.assertEqual(investment.y[6], 500)
        self.assertTrue(all(pd.isna(revenue.y[i]) for i in range(12) if i != 6))
        self.assertTrue(all(pd.isna(investment.y[i]) for i in range(12) if i != 6))
        self.assertIn("Jul/2026", figure.layout.xaxis.ticktext)
        self.assertEqual(figure.layout.xaxis.title.text, "Meses do ano")

    def test_partial_months_only_sum_days_inside_requested_dates(self):
        frame = pd.DataFrame({
            "data": pd.to_datetime(["2026-06-01", "2026-06-30", "2026-07-01", "2026-07-31", "2026-08-01", "2026-08-02"]),
            "faturamento_real": [9999, 50, 100, 200, 400, 9999],
            "investimento_total": [9999, 5, 10, 20, 40, 9999],
        })
        figure = revenue_figure(frame, "2026-06-30", "2026-08-01")
        self.assertEqual(list(figure.data[0].y), [50, 300, 400])
        self.assertEqual(list(figure.data[1].y), [5, 30, 40])

    def test_same_month_in_different_years_is_not_merged(self):
        frame = pd.DataFrame({
            "data": pd.to_datetime(["2025-07-01", "2026-07-01"]),
            "faturamento_real": [100, 900], "investimento_total": [10, 90],
        })
        figure = revenue_figure(frame)
        self.assertEqual(len(figure.data[0].x), 13)
        self.assertEqual(figure.data[0].y[0], 100)
        self.assertEqual(figure.data[0].y[-1], 900)
        self.assertTrue(pd.isna(figure.data[0].y[1]))

    def test_missing_measure_and_genuine_zero_remain_distinct(self):
        frame = pd.DataFrame({
            "data": pd.to_datetime(["2026-01-01", "2026-02-01", "2026-03-01"]),
            "faturamento_real": [0, float("nan"), 100],
            "investimento_total": [float("nan"), 0, 20],
        })
        figure = revenue_figure(frame)
        self.assertEqual(figure.data[0].y[0], 0)
        self.assertTrue(pd.isna(figure.data[1].y[0]))
        self.assertTrue(pd.isna(figure.data[0].y[1]))
        self.assertEqual(figure.data[1].y[1], 0)

    def test_empty_periods_and_null_measures_display_no_data_message(self):
        for start, end, points in (("2026-10-01", "2026-10-15", 15), ("2027-01-01", "2027-12-31", 12), (None, None, 0)):
            with self.subTest(start=start):
                figure = revenue_figure(self.frame.iloc[:0], start, end)
                self.assertEqual(len(figure.data[0].x), points)
                self.assertEqual(figure.layout.annotations[0].text, "Sem dados no período selecionado")
        self.frame[["faturamento_real", "investimento_total"]] = float("nan")
        self.assertTrue(revenue_figure(self.frame).layout.annotations)

    def test_single_day_and_leap_day_are_visible(self):
        frame = pd.DataFrame({
            "data": pd.to_datetime(["2024-02-29"]),
            "faturamento_real": [100], "investimento_total": [20],
        })
        figure = revenue_figure(frame, "2024-02-01", "2024-02-29")
        self.assertEqual(len(figure.data[0].x), 29)
        self.assertEqual(figure.data[0].y[-1], 100)
        figure = revenue_figure(frame)
        self.assertEqual(len(figure.data[0].x), 1)
        self.assertIn("markers", figure.data[0].mode)
        self.assertLess(pd.Timestamp(figure.layout.xaxis.range[0]), frame["data"].iloc[0])
        self.assertGreater(pd.Timestamp(figure.layout.xaxis.range[1]), frame["data"].iloc[0])


if __name__ == "__main__":
    unittest.main()
