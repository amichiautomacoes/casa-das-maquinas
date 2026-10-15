"""Configuracao de ambiente compartilhada por Windows e Docker/Linux."""

from dataclasses import dataclass
from pathlib import Path
import os
import re

from dotenv import dotenv_values


PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent


def read_environment() -> dict[str, str]:
    # O ambiente do processo (EasyPanel/Docker) tem prioridade sobre o .env local.
    local = dotenv_values(PROJECT_ROOT / ".env", interpolate=False)
    return {**{key: value for key, value in local.items() if value is not None}, **os.environ}


@dataclass(frozen=True)
class Settings:
    project_id: str = "casa-das-maquinas"
    dataset_id: str = "casa_maquinas"
    table_id: str = "tb_indicadores_diarios"
    location: str = "southamerica-east1"
    dash_path: str = "/dashboard/"
    host: str = "127.0.0.1"
    port: int = 8505
    maximum_bytes_billed: int = 100 * 1024 * 1024
    query_timeout: int = 120
    trust_proxy: bool = False
    raw_table_id: str = "casa_maquina_bruto"

    @classmethod
    def from_environment(cls, environment: dict[str, str] | None = None) -> "Settings":
        env = read_environment() if environment is None else environment
        settings = cls(
            project_id=env.get("GCP_PROJECT_ID", "casa-das-maquinas"),
            dataset_id=env.get("BIGQUERY_DATASET_ID", "casa_maquinas"),
            table_id=env.get("BIGQUERY_TABLE_ID", "tb_indicadores_diarios"),
            location=env.get("BIGQUERY_LOCATION", "southamerica-east1"),
            dash_path=env.get("DASH_URL_BASE_PATHNAME", "/dashboard/"),
            host=env.get("HOST", "127.0.0.1"),
            port=int(env.get("PORT", "8505")),
            maximum_bytes_billed=int(env.get("BIGQUERY_MAXIMUM_BYTES_BILLED", str(100 * 1024 * 1024))),
            query_timeout=int(env.get("BIGQUERY_QUERY_TIMEOUT", "120")),
            trust_proxy=env.get("TRUST_PROXY", "false").lower() in ("1", "true", "yes"),
            raw_table_id=env.get("BIGQUERY_RAW_TABLE_ID", "casa_maquina_bruto"),
        )
        if not re.fullmatch(r"[A-Za-z0-9_.:-]+", settings.project_id):
            raise ValueError("GCP_PROJECT_ID invalido.")
        for name in (settings.dataset_id, settings.table_id, settings.raw_table_id):
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,1023}", name):
                raise ValueError("Dataset e tabela precisam ser identificadores validos.")
        if not settings.dash_path.startswith("/") or not settings.dash_path.endswith("/") or settings.dash_path == "/":
            raise ValueError("DASH_URL_BASE_PATHNAME deve ser um caminho como /dashboard/.")
        if not 1 <= settings.port <= 65535 or settings.maximum_bytes_billed <= 0 or settings.query_timeout <= 0:
            raise ValueError("Porta, limite de bytes e timeout precisam ser positivos e validos.")
        return settings

    @property
    def qualified_table(self) -> str:
        return f"{self.project_id}.{self.dataset_id}.{self.table_id}"

    @property
    def qualified_raw_table(self) -> str:
        return f"{self.project_id}.{self.dataset_id}.{self.raw_table_id}"


METRICS = {
    "sessoes": ("Sessões", "integer"),
    "vendas": ("Vendas", "integer"),
    "taxa_de_conversao": ("Taxa de conversão", "percent"),
    "cps_custo_por_sessao": ("Custo por sessão", "currency"),
    "ticket_medio": ("Ticket médio", "currency"),
    "faturamento_analytics": ("Faturamento Analytics", "currency"),
    "faturamento_real": ("Faturamento real", "currency"),
    "facebook_ads": ("Facebook Ads", "currency"),
    "google_ads": ("Google Ads", "currency"),
    "meta_api": ("Meta API — valor bruto", "number"),
    "investimento_real": ("Investimento real", "currency"),
    "outros_investimentos": ("Outros investimentos", "currency"),
    "investimento_total": ("Investimento total", "currency"),
    "roas_analytics": ("ROAS Analytics", "ratio"),
    "roas_real": ("ROAS real", "ratio"),
    "clientes_recorrentes": ("Clientes recorrentes — revisar origem", "number"),
    "novos_clientes": ("Novos clientes", "integer"),
    "total_clientes": ("Total de clientes", "integer"),
}
