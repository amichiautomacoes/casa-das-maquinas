"""Executa o servidor Flask local: python -m visualizacao.run."""

import logging
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from visualizacao.app import create_app
from visualizacao.config import Settings


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s", stream=sys.stdout)
    try:
        settings = Settings.from_environment()
        app = create_app(settings)
    except (ValueError, OSError, RuntimeError) as error:
        logging.error("Falha ao iniciar o dashboard: %s", error)
        return 1
    logging.info("Dashboard local: http://%s:%s%s", settings.host, settings.port, settings.dash_path)
    app.run(host=settings.host, port=settings.port, debug=False, use_reloader=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
