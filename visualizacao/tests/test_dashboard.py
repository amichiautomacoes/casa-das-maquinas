from datetime import date
from math import isnan
import unittest
from unittest.mock import patch

import pandas as pd

from visualizacao.app import create_app
from visualizacao.auth import load_credentials
from visualizacao.charts import filter_frame, revenue_figure
from visualizacao.config import METRICS, Settings
from visualizacao.data_loader import load_indicators, prepare_dataframe


def component_props(tree, component_id):
    if isinstance(tree, dict):
        props = tree.get("props", {})
        if props.get("id") == component_id:
            return props
        for value in tree.values():
            found = component_props(value, component_id)
            if found is not None:
                return found
    elif isinstance(tree, list):
        for item in tree:
            found = component_props(item, component_id)
            if found is not None:
                return found
    return None


def sample_dataframe():
    rows = []
    for day, sessions, sales, revenue, investment in (
        ("2025-01-01", 50, 1, 100, 20),
        ("2026-07-01", 100, 10, 1000, 100),
        ("2026-07-03", 900, 45, 500, 400),
    ):
        row = {column: None for column in METRICS}
        row.update(
            data=day, sessoes=sessions, vendas=sales,
            faturamento_real=revenue, faturamento_analytics=revenue,
            investimento_total=investment, roas_real=revenue / investment,
            taxa_de_conversao=sales / sessions,
            clientes_recorrentes=2 if day == "2025-01-01" else 999,
        )
        rows.append(row)
    return pd.DataFrame(rows)


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.original = sample_dataframe()
        self.snapshot = self.original.copy(deep=True)
        self.server = create_app(settings=Settings(), dataframe=self.original)
        self.server.testing = True
        self.client = self.server.test_client()
        self.dashboard = self.server.extensions["dash_app"]

    def post_dashboard(self, year, start, end, metric="sessoes"):
        key = next(key for key in self.dashboard.callback_map if "period-label" in key)
        spec = self.dashboard.callback_map[key]
        return self.client.post("/dashboard/_dash-update-component", json={
            "output": key,
            "outputs": [{"id": item.component_id, "property": item.component_property} for item in spec["output"]],
            "inputs": [
                {"id": "year-filter", "property": "value", "value": year},
                {"id": "date-filter", "property": "start_date", "value": start},
                {"id": "date-filter", "property": "end_date", "value": end},
                {"id": "metric-filter", "property": "value", "value": metric},
            ],
            "state": [], "changedPropIds": ["year-filter.value"],
        })

    def test_flask_routes_and_dash_assets(self):
        self.assertEqual(self.client.get("/").location, "/dashboard/")
        self.assertEqual(self.client.get("/healthz").get_json()["rows"], 3)
        for url in ("/dashboard/", "/dashboard/_dash-layout", "/dashboard/_dash-dependencies", "/dashboard/assets/dashboard.css"):
            with self.client.get(url) as response:
                self.assertEqual(response.status_code, 200, url)
        layout = self.client.get("/dashboard/_dash-layout").get_json()
        self.assertIsNone(component_props(layout, "main-tabs"))
        self.assertIsNotNone(component_props(layout, "page-visao-geral-executiva"))
        self.assertIsNotNone(component_props(layout, "metric-filter"))
        dependencies = self.client.get("/dashboard/_dash-dependencies").get_json()
        self.assertFalse(any(
            item["id"] == "main-tabs"
            for callback in dependencies for item in callback["inputs"]
        ))

    def test_year_and_date_filters_through_real_callback_endpoint(self):
        response = self.post_dashboard("2026", "2026-07-01", "2026-07-03")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["response"]["period-label"]["children"], "2 dias com registro no período selecionado")
        response = self.post_dashboard("2025", "2025-01-01", "2025-01-01", "vendas")
        self.assertEqual(response.get_json()["response"]["period-label"]["children"], "1 dia com registro no período selecionado")
        pd.testing.assert_frame_equal(self.original, self.snapshot)

    def test_executive_page_handles_empty_period_for_different_metrics(self):
        for metric in ("sessoes", "faturamento_real", "clientes_recorrentes"):
            with self.subTest(metric=metric):
                response = self.post_dashboard("2026", "2026-01-01", "2026-01-31", metric)
                self.assertEqual(response.status_code, 200)
                payload = response.get_json()["response"]
                self.assertEqual(payload["period-label"]["children"], "0 dias com registro no período selecionado")
                graph = component_props(payload["page-content"]["children"], "executiva-metric-chart")
                self.assertTrue(graph["figure"]["layout"]["annotations"])

    def test_filters_and_metric_selector_reuse_data_without_querying_bigquery(self):
        with patch("visualizacao.app.load_indicators") as query:
            for metric in ("sessoes", "vendas", "faturamento_real"):
                with self.subTest(metric=metric):
                    response = self.post_dashboard("2026", "2026-07-03", "2026-07-03", metric)
                    self.assertEqual(response.status_code, 200)
                    payload = response.get_json()["response"]
                    content = payload["page-content"]["children"]
                    self.assertIsNotNone(component_props(content, "page-visao-geral-executiva"))
                    self.assertEqual(payload["period-label"]["children"], "1 dia com registro no período selecionado")
                    figure = component_props(content, "executiva-metric-chart")["figure"]
                    self.assertEqual(figure["data"][0]["name"], METRICS[metric][0])
            query.assert_not_called()
        pd.testing.assert_frame_equal(self.original, self.snapshot)

    def test_recurring_metric_warning_follows_selected_metric_and_period(self):
        for year, metric, expected in (
            ("2026", "clientes_recorrentes", True),
            ("2026", "sessoes", False),
            ("2025", "clientes_recorrentes", False),
        ):
            with self.subTest(year=year, metric=metric):
                response = self.post_dashboard(year, None, None, metric).get_json()["response"]
                content = response["page-content"]["children"]
                self.assertEqual(component_props(content, "executiva-mapping-warning")["is_open"], expected)

    def test_missing_days_stay_missing_in_revenue_chart(self):
        selected = filter_frame(prepare_dataframe(self.original), "2026", None, None)
        figure = revenue_figure(selected)
        self.assertEqual(len(figure.data[0].x), 3)
        self.assertTrue(isnan(figure.data[0].y[1]))

    def test_invalid_sql_date_range_fails_before_authentication(self):
        with patch("visualizacao.data_loader.load_credentials") as auth:
            with self.assertRaises(ValueError):
                load_indicators(Settings(), date(2026, 7, 2), date(2026, 7, 1))
            auth.assert_not_called()

    def test_container_pem_credentials_do_not_require_local_json(self):
        pem = "-----BEGIN PRIVATE KEY-----\\nCHAVE-DE-TESTE\\n-----END PRIVATE KEY-----"
        env = {
            "GOOGLE_APPLICATION_CREDENTIALS": pem,
            "GCP_SERVICE_ACCOUNT_EMAIL": "teste@example.iam.gserviceaccount.com",
            "GCP_PROJECT_ID": "example-project",
        }
        with patch("visualizacao.auth._read_json", side_effect=AssertionError("Nao pode ler JSON local")):
            with patch("visualizacao.auth.service_account.Credentials.from_service_account_info") as constructor:
                load_credentials(env)
                info = constructor.call_args.args[0]
                self.assertEqual(info["client_email"], env["GCP_SERVICE_ACCOUNT_EMAIL"])
                self.assertIn("\nCHAVE-DE-TESTE\n", info["private_key"])
                self.assertEqual(info["token_uri"], "https://oauth2.googleapis.com/token")


if __name__ == "__main__":
    unittest.main()
