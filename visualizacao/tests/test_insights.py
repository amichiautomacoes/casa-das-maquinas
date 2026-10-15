"""Verifica os cruzamentos complementares sem consultar o GCP."""

import unittest
from unittest.mock import patch

import pandas as pd
import test_dashboard as dashboard_helpers

from visualizacao.app import create_app
from visualizacao.config import METRICS, Settings
from visualizacao.data_loader import prepare_dataframe
from visualizacao.insights import (
    client_cost_reference, client_mix, sales_by_daily_ticket,
    ticket_distribution, validated_client_counts,
)
from visualizacao.insight_charts import (
    client_cost_figure, client_mix_figure, media_performance_figure,
    ticket_distribution_figure, ticket_peaks_figure,
)
from test_dashboard import component_props


def insight_dataframe():
    rows = []
    for day, revenue, sales, meta, google, new, recurring in (
        ("2025-01-01", 1000, 10, 80, 20, 8, 2),
        ("2025-01-03", 200, 2, 300, 100, 2, 2),
        ("2025-02-01", 900, 3, 200, 100, None, 6),
        ("2025-07-01", 1000, 10, 80, 20, 10, 999),
    ):
        row = {column: None for column in METRICS}
        row.update(data=day, faturamento_real=revenue, vendas=sales,
                   facebook_ads=meta, google_ads=google, outros_investimentos=0,
                   novos_clientes=new, clientes_recorrentes=recurring,
                   ticket_medio=99999, investimento_total=99999, roas_real=99999)
        rows.append(row)
    return prepare_dataframe(pd.DataFrame(rows))


class MediaAnalysisTests(unittest.TestCase):
    def test_monthly_roas_is_ratio_of_totals_and_spend_uses_same_definition_as_kpis(self):
        frame = insight_dataframe()
        snapshot = frame.copy(deep=True)
        figure = media_performance_figure(frame, "2025-01-01", "2025-07-31")
        meta, google, roas = figure.data
        self.assertEqual(meta.y[0], 380)
        self.assertEqual(google.y[0], 120)
        self.assertEqual(roas.y[0], 2.4)
        self.assertEqual(roas.y[1], 3)
        self.assertTrue(pd.isna(roas.y[2]))
        self.assertEqual(roas.yaxis, "y2")
        self.assertEqual(meta.yaxis, "y")
        pd.testing.assert_frame_equal(frame, snapshot)

    def test_daily_gaps_and_zero_denominator_leave_roas_missing(self):
        frame = insight_dataframe().iloc[:2].copy()
        frame.loc[0, ["facebook_ads", "google_ads", "outros_investimentos"]] = 0.0
        figure = media_performance_figure(frame, "2025-01-01", "2025-01-03")
        self.assertEqual(len(figure.data[0].x), 3)
        self.assertTrue(pd.isna(figure.data[2].y[0]))
        self.assertTrue(pd.isna(figure.data[0].y[1]))
        self.assertEqual(figure.data[2].y[2], 0.5)
        self.assertFalse(figure.data[2].connectgaps)


class TicketAnalysisTests(unittest.TestCase):
    def test_distribution_weights_sales_instead_of_counting_days_or_source_ticket(self):
        frame = insight_dataframe()
        snapshot = frame.copy(deep=True)
        result = ticket_distribution(frame)
        self.assertEqual(result["vendas"].tolist(), [0, 22, 0, 3, 0])
        self.assertEqual(result["dias"].sum(), 4)
        self.assertEqual(result["vendas"].sum(), frame["vendas"].sum())
        self.assertEqual(result["faturamento"].sum(), frame["faturamento_real"].sum())
        self.assertAlmostEqual(result["participacao"].sum(), 1)
        self.assertEqual(sales_by_daily_ticket(frame)["ticket_calculado"].tolist(), [100, 100, 300, 100])
        pd.testing.assert_frame_equal(frame, snapshot)

    def test_band_edges_do_not_duplicate_or_drop_sales(self):
        tickets = [0, 99.99, 100, 149.99, 150, 299.99, 300, 999.99, 1000]
        frame = pd.DataFrame({"data": pd.date_range("2025-01-01", periods=len(tickets)),
                              "vendas": 1, "faturamento_real": tickets})
        result = ticket_distribution(frame)
        self.assertEqual(result["vendas"].tolist(), [2, 2, 2, 2, 1])

    def test_zero_sales_missing_revenue_and_negative_ticket_are_excluded(self):
        frame = insight_dataframe()
        frame["vendas"] = [0, -1, 3, 10]
        frame["faturamento_real"] = [1000, 200, float("nan"), -10]
        self.assertTrue(sales_by_daily_ticket(frame).empty)
        self.assertTrue(ticket_distribution_figure(frame).layout.annotations)
        self.assertTrue(ticket_peaks_figure(frame).layout.annotations)


class ClientAnalysisTests(unittest.TestCase):
    def test_mix_uses_only_paired_days_and_excludes_cpa(self):
        frame = insight_dataframe()
        snapshot = frame.copy(deep=True)
        counts, days = client_mix(frame)
        self.assertEqual(days, 2)
        self.assertEqual(counts.tolist(), [10, 4])
        self.assertTrue(pd.isna(validated_client_counts(frame).iloc[3]["clientes_recorrentes"]))
        figure = client_mix_figure(frame)
        self.assertEqual(list(figure.data[0].values), [10, 4])
        pd.testing.assert_frame_equal(frame, snapshot)

    def test_cost_reference_aligns_spend_and_counts_for_each_type(self):
        values = client_cost_reference(insight_dataframe())
        self.assertEqual(values["dias"].tolist(), [3, 3])
        self.assertEqual(values["investimento"].tolist(), [600, 800])
        self.assertEqual(values["registros"].tolist(), [20, 10])
        self.assertEqual(values["custo_por_registro"].tolist(), [30, 80])

    def test_invalid_counts_are_not_treated_as_people(self):
        frame = insight_dataframe().iloc[:3].copy()
        frame["novos_clientes"] = [-1, 2.5, float("nan")]
        counts = validated_client_counts(frame)
        self.assertTrue(counts["novos_clientes"].isna().all())
        self.assertEqual(client_mix(frame)[1], 0)
        costs = client_cost_reference(frame)
        self.assertTrue(pd.isna(costs.iloc[0]["custo_por_registro"]))
        self.assertEqual(costs.iloc[1]["dias"], 3)

    def test_zero_records_and_missing_investment_do_not_produce_infinite_cost(self):
        frame = insight_dataframe().iloc[:2].copy()
        frame["novos_clientes"] = 0.0
        frame["clientes_recorrentes"] = 0.0
        self.assertTrue(client_cost_reference(frame)["custo_por_registro"].isna().all())
        self.assertTrue(client_cost_figure(frame).layout.annotations)
        self.assertTrue(client_mix_figure(frame).layout.annotations)
        frame[["facebook_ads", "google_ads", "outros_investimentos"]] = float("nan")
        self.assertEqual(client_cost_reference(frame)["dias"].tolist(), [0, 0])


class InsightCallbackTests(unittest.TestCase):
    def setUp(self):
        self.harness = dashboard_helpers.DashboardTests()
        self.frame = insight_dataframe()
        server = create_app(Settings(), self.frame)
        self.harness.client = server.test_client()
        self.harness.dashboard = server.extensions["dash_app"]

    def test_three_sections_are_on_first_page_and_share_filters_without_bigquery_query(self):
        with patch("visualizacao.app.load_indicators") as query:
            response = self.harness.post_dashboard("2025", "2025-01-01", "2025-01-31")
            query.assert_not_called()
        self.assertEqual(response.status_code, 200)
        tree = response.get_json()["response"]["page-content"]["children"]
        for slug in ("midia", "mix", "clientes"):
            self.assertIsNotNone(component_props(tree, f"executiva-{slug}-section"))
        pie = component_props(tree, "executiva-client-mix-chart")["figure"]
        self.assertEqual(pie["data"][0]["values"], [10, 4])
        media = component_props(tree, "executiva-midia-performance-chart")["figure"]
        self.assertEqual(media["layout"]["meta"]["aggregation"], "daily")
        costs = component_props(tree, "executiva-client-cost-chart")["figure"]
        self.assertEqual(costs["data"][0]["y"], [50, 125])

    def test_cpa_month_only_suppresses_unreliable_recurring_data(self):
        response = self.harness.post_dashboard("2025", "2025-07-01", "2025-07-31")
        self.assertEqual(response.status_code, 200)
        tree = response.get_json()["response"]["page-content"]["children"]
        self.assertTrue(component_props(tree, "executiva-clientes-source-warning")["is_open"])
        pie = component_props(tree, "executiva-client-mix-chart")["figure"]
        self.assertTrue(pie["layout"]["annotations"])
        self.assertFalse(pie["data"])
        costs = component_props(tree, "executiva-client-cost-chart")["figure"]
        self.assertEqual(costs["data"][0]["y"], [10, None])

    def test_empty_period_is_safe_in_every_new_graph(self):
        response = self.harness.post_dashboard("2025", "2025-11-01", "2025-11-30")
        self.assertEqual(response.status_code, 200)
        tree = response.get_json()["response"]["page-content"]["children"]
        for slug in ("midia-performance", "ticket-distribution", "ticket-peaks", "client-mix", "client-cost"):
            with self.subTest(graph=slug):
                figure = component_props(tree, f"executiva-{slug}-chart")["figure"]
                self.assertTrue(figure["layout"]["annotations"])


if __name__ == "__main__":
    unittest.main()
