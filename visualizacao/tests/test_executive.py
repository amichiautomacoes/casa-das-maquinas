"""Verifica as regras de negocio dos KPIs e o planejamento do periodo."""

from datetime import date
import unittest
from unittest.mock import patch

import pandas as pd
import test_dashboard as dashboard_helpers

from visualizacao.app import create_app
from visualizacao.charts import filter_frame, kpi_sparkline
from visualizacao.config import Settings
from visualizacao.data_loader import prepare_dataframe
from visualizacao.executive import attainment_status, executive_summary, marketing_by_day
from visualizacao.layout import current_period
from visualizacao.planning import revenue_target
from test_dashboard import component_props, sample_dataframe


def executive_dataframe():
    frame = sample_dataframe()
    # O total da origem e a Meta API nao entram na soma dos tres canais pedidos.
    frame["investimento_total"] = 99999
    frame["investimento_real"] = 555
    frame["facebook_ads"] = [10, 50, 250]
    frame["google_ads"] = [10, 40, 100]
    frame["outros_investimentos"] = [0, 10, 50]
    frame["ticket_medio"] = 99999
    frame["roas_real"] = 99999
    return prepare_dataframe(frame)


class ExecutiveCalculationTests(unittest.TestCase):
    def setUp(self):
        self.frame = filter_frame(executive_dataframe(), "2026", None, None)

    def test_totals_compute_global_roas_and_weighted_ticket(self):
        snapshot = self.frame.copy(deep=True)
        summary = executive_summary(self.frame)
        self.assertEqual(summary.revenue, 1500)
        self.assertEqual(summary.investment, 500)
        self.assertEqual(summary.roas, 3)
        self.assertAlmostEqual(summary.ticket, 1500 / 55)
        self.assertNotAlmostEqual(summary.ticket, (1000 / 10 + 500 / 45) / 2)
        self.assertEqual(marketing_by_day(self.frame).tolist(), [100, 400])
        pd.testing.assert_frame_equal(self.frame, snapshot)

    def test_zero_denominators_and_missing_data_are_not_fabricated(self):
        for column in ("facebook_ads", "google_ads", "outros_investimentos", "vendas"):
            self.frame[column] = 0.0
        summary = executive_summary(self.frame)
        self.assertEqual(summary.investment, 0)
        self.assertIsNone(summary.roas)
        self.assertIsNone(summary.ticket)
        self.frame.loc[:, ["facebook_ads", "google_ads", "outros_investimentos"]] = float("nan")
        self.assertIsNone(executive_summary(self.frame).investment)
        empty = executive_summary(self.frame.iloc[:0])
        self.assertIsNone(empty.revenue)
        self.assertIsNone(empty.investment)
        self.assertIsNone(empty.ticket)

    def test_exact_color_thresholds_and_overachievement(self):
        for ratio, color in ((None, "secondary"), (0, "danger"), (0.8999, "danger"),
                             (0.9, "warning"), (0.9999, "warning"), (1, "success"), (1.25, "success")):
            with self.subTest(ratio=ratio):
                self.assertEqual(attainment_status(ratio)[0], color)

    def test_sparkline_keeps_missing_dates_as_gaps(self):
        figure = kpi_sparkline(self.frame, marketing_by_day(self.frame), "#326bba", "currency")
        self.assertEqual(len(figure.data[0].x), 3)
        self.assertTrue(pd.isna(figure.data[0].y[1]))
        self.assertFalse(figure.data[0].connectgaps)

    def test_current_periods_use_calendar_dates_even_without_current_data(self):
        today = date(2026, 10, 14)
        self.assertEqual(current_period("month", today), ("2026", "2026-10-01", "2026-10-14"))
        self.assertEqual(current_period("year", today), ("2026", "2026-01-01", "2026-10-14"))


class PlanningTests(unittest.TestCase):
    def test_monthly_target_is_prorated_by_calendar_days_and_not_rows(self):
        with patch.dict("visualizacao.planning.MONTHLY_REVENUE_TARGETS", {"2026-07": 31000}, clear=True):
            self.assertEqual(revenue_target(date(2026, 7, 1), date(2026, 7, 31)), 31000)
            summary = executive_summary(filter_frame(executive_dataframe(), "2026", None, None), "2026-07-01", "2026-07-15")
            self.assertEqual(summary.target, 15000)
            self.assertEqual(summary.attainment, 0.1)

    def test_leap_year_and_monthly_override(self):
        with patch.dict("visualizacao.planning.ANNUAL_REVENUE_TARGETS", {2024: 36600}, clear=True):
            with patch.dict("visualizacao.planning.MONTHLY_REVENUE_TARGETS", {}, clear=True):
                self.assertEqual(revenue_target(date(2024, 2, 1), date(2024, 2, 29)), 2900)
                self.assertEqual(revenue_target(date(2024, 1, 1), date(2024, 12, 31)), 36600)
            with patch.dict("visualizacao.planning.MONTHLY_REVENUE_TARGETS", {"2024-02": 5800}, clear=True):
                self.assertEqual(revenue_target(date(2024, 1, 1), date(2024, 2, 29)), 8900)

    def test_missing_partial_zero_and_invalid_plans_do_not_become_targets(self):
        with patch.dict("visualizacao.planning.ANNUAL_REVENUE_TARGETS", {}, clear=True):
            for amount in (None, 0, -1, float("nan"), float("inf")):
                with patch.dict("visualizacao.planning.MONTHLY_REVENUE_TARGETS", {"2026-07": amount}, clear=True):
                    self.assertIsNone(revenue_target(date(2026, 7, 1), date(2026, 7, 31)))
            with patch.dict("visualizacao.planning.MONTHLY_REVENUE_TARGETS", {"2026-07": 31000}, clear=True):
                self.assertIsNone(revenue_target(date(2026, 7, 1), date(2026, 8, 31)))
                self.assertIsNone(revenue_target(date(2026, 8, 1), date(2026, 7, 31)))


class ExecutiveCallbackTests(unittest.TestCase):
    def setUp(self):
        # Reutiliza apenas os auxiliares HTTP, sem repetir os testes da suite base.
        self.harness = dashboard_helpers.DashboardTests()
        self.harness.original = executive_dataframe()
        self.harness.server = create_app(Settings(), self.harness.original)
        self.harness.client = self.harness.server.test_client()
        self.harness.dashboard = self.harness.server.extensions["dash_app"]

    def test_four_cards_follow_dates_and_render_attainment_above_one_hundred(self):
        with patch.dict("visualizacao.planning.MONTHLY_REVENUE_TARGETS", {"2026-07": 1000}, clear=True):
            response = self.harness.post_dashboard("2026", "2026-07-01", "2026-07-31")
        self.assertEqual(response.status_code, 200)
        tree = response.get_json()["response"]["page-content"]["children"]
        self.assertEqual(len(component_props(tree, "executiva-kpis")["children"][0]["props"]["children"]), 4)
        self.assertEqual(component_props(tree, "executiva-revenue-value")["children"], "R$ 1.500,00")
        self.assertEqual(component_props(tree, "executiva-roas-value")["children"], "3,00x")
        self.assertEqual(component_props(tree, "executiva-investment-value")["children"], "R$ 500,00")
        self.assertEqual(component_props(tree, "executiva-ticket-value")["children"], "R$ 27,27")
        badge = component_props(tree, "executiva-attainment-badge")
        self.assertEqual(badge["color"], "success")
        self.assertEqual(badge["children"], "150,00% atingido")
        gauge = component_props(tree, "executiva-attainment-chart")["figure"]["data"][0]
        self.assertEqual(gauge["value"], 150)
        self.assertGreater(gauge["gauge"]["axis"]["range"][1], 150)

    def test_empty_current_month_does_not_display_zero_revenue_or_zero_attainment(self):
        with patch.dict("visualizacao.planning.MONTHLY_REVENUE_TARGETS", {"2026-10": 31000}, clear=True):
            response = self.harness.post_dashboard("2026", "2026-10-01", "2026-10-14")
        self.assertEqual(response.status_code, 200)
        tree = response.get_json()["response"]["page-content"]["children"]
        for slug in ("revenue", "roas", "investment", "ticket"):
            self.assertEqual(component_props(tree, f"executiva-{slug}-value")["children"], "—")
        self.assertEqual(component_props(tree, "executiva-attainment-badge")["children"], "Sem dados")

    def test_decoupling_chart_respects_filters_and_matches_kpi_investment(self):
        for start, end, aggregation, index in (
            ("2026-07-03", "2026-07-03", "daily", 0),
            ("2026-01-01", "2026-12-31", "monthly", 6),
        ):
            with self.subTest(aggregation=aggregation):
                with patch("visualizacao.app.load_indicators") as query:
                    response = self.harness.post_dashboard("2026", start, end)
                    query.assert_not_called()
                self.assertEqual(response.status_code, 200)
                tree = response.get_json()["response"]["page-content"]["children"]
                self.assertIsNotNone(component_props(tree, "executiva-strategy-section"))
                figure = component_props(tree, "executiva-revenue-chart")["figure"]
                self.assertEqual(figure["layout"]["meta"]["aggregation"], aggregation)
                self.assertEqual(len(figure["data"]), 2)
                self.assertEqual(figure["data"][1]["yaxis"], "y2")
                expected = 400 if aggregation == "daily" else 500
                self.assertEqual(figure["data"][1]["y"][index], expected)
                self.assertEqual(component_props(tree, "executiva-investment-value")["children"], f"R$ {expected},00")

    def test_shortcuts_update_year_and_dates_through_http(self):
        dashboard = self.harness.dashboard
        key = next(key for key in dashboard.callback_map if "min_date_allowed" in key)
        spec = dashboard.callback_map[key]
        for trigger, expected_start in (("current-month", "2026-10-01"), ("current-year", "2026-01-01")):
            with self.subTest(trigger=trigger), patch("visualizacao.callbacks.current_period", side_effect=lambda mode: current_period(mode, date(2026, 10, 14))):
                response = self.harness.client.post("/dashboard/_dash-update-component", json={
                    "output": key,
                    "outputs": [{"id": item.component_id, "property": item.component_property} for item in spec["output"]],
                    "inputs": [
                        {"id": "year-filter", "property": "value", "value": "2025"},
                        {"id": "current-month", "property": "n_clicks", "value": 1},
                        {"id": "current-year", "property": "n_clicks", "value": 1},
                    ], "state": [], "changedPropIds": [trigger + ".n_clicks"],
                })
                self.assertEqual(response.status_code, 200)
                result = response.get_json()["response"]
                self.assertEqual(result["year-filter"]["value"], "2026")
                self.assertEqual(result["date-filter"]["start_date"], expected_start)
                self.assertEqual(result["date-filter"]["end_date"], "2026-10-14")


if __name__ == "__main__":
    unittest.main()
