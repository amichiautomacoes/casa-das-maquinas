"""Application factory Flask com Dash integrado e rotas de infraestrutura."""

import dash_bootstrap_components as dbc
from dash import Dash
from flask import Flask, jsonify, redirect
import pandas as pd
from werkzeug.middleware.proxy_fix import ProxyFix

from .callbacks import register_callbacks
from .config import PACKAGE_ROOT, Settings
from .data_loader import load_financials, load_indicators, prepare_dataframe
from .financial import empty_financial_frame, prepare_financial_frame
from .layout import create_layout
from .pages import PAGES


def create_app(settings: Settings | None = None, dataframe: pd.DataFrame | None = None,
               financial_frame: pd.DataFrame | None = None) -> Flask:
    settings = Settings.from_environment() if settings is None else settings
    frame = load_indicators(settings) if dataframe is None else prepare_dataframe(dataframe)
    if financial_frame is not None:
        finances = prepare_financial_frame(financial_frame)
    else:
        # A injecao de dados para testes continua totalmente independente do GCP.
        finances = load_financials(settings) if dataframe is None else empty_financial_frame()
    server = Flask(__name__)
    if settings.trust_proxy:
        server.wsgi_app = ProxyFix(server.wsgi_app, x_for=1, x_proto=1, x_host=1)

    @server.get("/")
    def index():
        return redirect(settings.dash_path)

    @server.get("/healthz")
    def health():
        return jsonify(status="ok", application="casa-das-maquinas", rows=len(frame), financial_months=len(finances))

    dashboard = Dash(
        __name__, server=server, url_base_pathname=settings.dash_path,
        external_stylesheets=[dbc.themes.BOOTSTRAP],
        assets_folder=str(PACKAGE_ROOT / "assets"),
        title="Casa das Máquinas | Indicadores", update_title="Atualizando…",
    )
    dashboard.layout = create_layout(frame, pages=PAGES, financial_frame=finances)
    register_callbacks(dashboard, frame, pages=PAGES, financial_frame=finances)
    server.extensions["dash_app"] = dashboard
    return server
