FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8505 \
    TRUST_PROXY=true

WORKDIR /app

COPY visualizacao/requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY visualizacao/ ./visualizacao/
RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8505

HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
    CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8505') + '/healthz', timeout=3)"]

CMD ["sh", "-c", "exec gunicorn --bind \"0.0.0.0:${PORT:-8505}\" --workers 2 --threads 4 --timeout 120 visualizacao.wsgi:app"]
