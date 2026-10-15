"""Entrypoint de producao para Gunicorn no Docker/Linux."""

import logging
import sys

from .app import create_app

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s", stream=sys.stdout)
app = create_app()
