"""Valida a cascata, margens ponderadas e integracao da DRE no dashboard."""

import unittest
from unittest.mock import patch

import pandas as pd
import test_dashboard as dashboard_helpers

from visualizacao.app import create_app
from visualizacao.config import Settings
from visualizacao.data_loader import prepare_dataframe
from visualizacao.financial import (
    empty_financial_frame, filter_financial_frame, financial_rows,
    financial_summary, prepare_financial_frame,
)
from visualizacao.financial_section import financial_waterfall
from test_dashboard import component_props, sample_dataframe


def sample_financials():
    rows = []
    for month, days, revenue, tax, returns, cpv, net, planned in (
        ("2025-01-01", 31, 1000, 100, 50, 400, 100, 1200),
        ("2025-02-01", 28, 9000, 900, 0, 4500, 2700, 10000),
        ("2025-11-01", 0, 0, 0, 0, 0, 0, 1800),
        ("2026-07-01", 31, 5000, 100, 50, 4000, 500, 6000),
    ):
        rows.append(dict(
            data=month, dias_com_receita=days, receita_bruta=revenue,
            devolucoes=returns, impostos=tax, cpv=cpv,
            lucro_bruto_fonte=revenue - tax - returns - cpv,
            resultado_liquido=net, receita_prevista=planned, receita_plano_real=revenue,
        ))
    return prepare_financial_frame(pd.DataFrame(rows))


class FinancialCalculationTests(unittest.TestCase):
    def test_gross_profit_includes_returns_and_margins_use_period_totals(self):
        frame = filter_financial_frame(sample_financials(), "2025")
        snapshot = frame.copy(deep=True)
        summary = financial_summary(frame)
        self.assertEqual(summary.months, 2)
        self.assertEqual(summary.revenue, 10000)
        self.assertEqual(summary.returns, 50)
        self.assertEqual(summary.taxes, 1000)
        self.assertEqual(summary.cpv, 4900)
        self.assertEqual(summary.gross_profit, 4050)
        self.assertEqual(summary.gross_margin, 0.405)
        self.assertEqual(summary.net_margin, 0.28)
        self.assertEqual(summary.planned_revenue, 11200)
        self.assertNotEqual(summary.gross_margin, (0.45 + 0.4) / 2)
        pd.testing.assert_frame_equal(frame, snapshot)

    def test_filters_use_actual_year_and_include_months_touched_by_partial_dates(self):
        frame = sample_financials()
        july = filter_financial_frame(frame, "2026", "2026-07-12", "2026-07-15")
        self.assertEqual(len(july), 1)
        self.assertEqual(financial_summary(july).revenue, 5000)
        self.assertTrue(filter_financial_frame(frame, "2025", "2026-07-01", "2026-07-31").empty)
        self.assertTrue(filter_financial_frame(frame, "all", "2026-07-20", "2026-07-10").empty)

    def test_zero_formulas_without_observed_revenue_do_not_become_financial_results(self):
        november = filter_financial_frame(sample_financials(), "2025", "2025-11-01", "2025-11-30")
        self.assertTrue(financial_rows(november).empty)
        summary = financial_summary(november)
        self.assertIsNone(summary.revenue)
        self.assertIsNone(summary.gross_profit)
        self.assertIsNone(summary.planned_revenue)
        self.assertTrue(financial_waterfall(november).layout.annotations)

    def test_missing_cost_does_not_silently_reduce_expenses(self):
        frame = filter_financial_frame(sample_financials(), "2025")
        frame.loc[frame["data"].dt.month.eq(2), "cpv"] = float("nan")
        summary = financial_summary(frame)
        self.assertEqual(summary.revenue, 10000)
        self.assertIsNone(summary.cpv)
        self.assertIsNone(summary.gross_profit)
        self.assertIsNone(summary.gross_margin)
        self.assertTrue(financial_waterfall(frame).layout.annotations)

    def test_waterfall_deducts_costs_and_uses_total_measure_for_profit(self):
        frame = sample_financials().iloc[:1]
        trace = financial_waterfall(frame).data[0]
        self.assertEqual(trace.type, "waterfall")
        self.assertEqual(list(trace.measure), ["absolute", "relative", "relative", "relative", "total"])
        self.assertEqual(list(trace.y), [1000, -100, -50, -400, 0])
        self.assertEqual(trace.text[-1], "R$ 450,00")

    def test_genuine_zero_revenue_and_losses_keep_undefined_margins(self):
        frame = sample_financials().iloc[:1].copy()
        frame[["receita_bruta", "impostos", "devolucoes"]] = 0.0
        frame["cpv"] = 100.0
        summary = financial_summary(frame)
        self.assertEqual(summary.gross_profit, -100)
        self.assertIsNone(summary.gross_margin)
        self.assertIsNone(summary.net_margin)
        self.assertEqual(financial_waterfall(frame).data[0].totals.marker.color, "#c43d4a")

    def test_month_keys_coverage_and_nonfinite_amounts_are_validated(self):
        frame = sample_financials()
        for field, value in (("data", "2025-01-02"), ("dias_com_receita", -1),
                             ("dias_com_receita", 32), ("cpv", float("inf"))):
            with self.subTest(field=field, value=value):
                invalid = frame.copy()
                if field == "data":
                    invalid.loc[0, field] = pd.Timestamp(value)
                else:
                    invalid.loc[0, field] = value
                with self.assertRaises(ValueError):
                    prepare_financial_frame(invalid)
        with self.assertRaises(ValueError):
            prepare_financial_frame(pd.concat([frame, frame.iloc[:1]]))
        self.assertIsNone(financial_summary(empty_financial_frame()).gross_profit)


class FinancialCallbackTests(unittest.TestCase):
    def setUp(self):
        self.harness = dashboard_helpers.DashboardTests()
        self.finances = sample_financials()
        self.snapshot = self.finances.copy(deep=True)
        server = create_app(Settings(), sample_dataframe(), financial_frame=self.finances)
        self.harness.client = server.test_client()
        self.harness.dashboard = server.extensions["dash_app"]

    def test_last_section_crosses_monthly_dre_and_plan_with_shared_year_filter(self):
        with patch("visualizacao.app.load_financials") as query:
            response = self.harness.post_dashboard("2025", "2025-01-01", "2025-02-28")
            query.assert_not_called()
        self.assertEqual(response.status_code, 200)
        tree = response.get_json()["response"]["page-content"]["children"]
        children = tree["props"]["children"]
        self.assertEqual(children[-2]["props"]["id"], "executiva-financial-section")
        figure = component_props(tree, "executiva-financial-waterfall")["figure"]
        self.assertEqual(figure["data"][0]["text"][-1], "R$ 4.050,00")
        self.assertEqual(component_props(tree, "executiva-financial-planned")["children"], "R$ 11.200,00")
        self.assertFalse(component_props(tree, "executiva-financial-reconciliation")["is_open"])
        self.assertFalse(component_props(tree, "executiva-financial-month-scope")["is_open"])
        self.assertIsNotNone(component_props(tree, "executiva-financial-table"))
        pd.testing.assert_frame_equal(self.finances, self.snapshot)

    def test_partial_day_filter_shows_monthly_scope_and_full_month_amount(self):
        response = self.harness.post_dashboard("2026", "2026-07-12", "2026-07-15")
        self.assertEqual(response.status_code, 200)
        tree = response.get_json()["response"]["page-content"]["children"]
        self.assertTrue(component_props(tree, "executiva-financial-month-scope")["is_open"])
        figure = component_props(tree, "executiva-financial-waterfall")["figure"]
        self.assertEqual(figure["data"][0]["text"][0], "R$ 5.000,00")

    def test_reconciliation_and_incomplete_dre_are_visible(self):
        invalid = sample_financials()
        invalid.loc[0, "receita_plano_real"] = 1234
        invalid.loc[1, "cpv"] = float("nan")
        server = create_app(Settings(), sample_dataframe(), financial_frame=invalid)
        self.harness.client = server.test_client()
        self.harness.dashboard = server.extensions["dash_app"]
        response = self.harness.post_dashboard("2025", "2025-01-01", "2025-02-28")
        self.assertEqual(response.status_code, 200)
        tree = response.get_json()["response"]["page-content"]["children"]
        self.assertTrue(component_props(tree, "executiva-financial-reconciliation")["is_open"])
        self.assertTrue(component_props(tree, "executiva-financial-incomplete")["is_open"])

    def test_production_loads_each_source_once_and_filters_reuse_memory(self):
        with patch("visualizacao.app.load_indicators", return_value=prepare_dataframe(sample_dataframe())) as daily:
            with patch("visualizacao.app.load_financials", return_value=sample_financials()) as financial:
                server = create_app(Settings())
                self.harness.client = server.test_client()
                self.harness.dashboard = server.extensions["dash_app"]
                for start, end in (("2026-07-01", "2026-07-31"), ("2026-01-01", "2026-12-31")):
                    self.assertEqual(self.harness.post_dashboard("2026", start, end).status_code, 200)
                daily.assert_called_once()
                financial.assert_called_once()
                self.assertEqual(self.harness.client.get("/healthz").get_json()["financial_months"], 4)


if __name__ == "__main__":
    unittest.main()
