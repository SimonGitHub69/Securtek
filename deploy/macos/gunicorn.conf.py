# Configurazione Gunicorn per Securtek (server macOS)
# Uso: gunicorn -c deploy/macos/gunicorn.conf.py config.wsgi:application

import multiprocessing
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

bind = "0.0.0.0:8000"
workers = max(2, min(4, multiprocessing.cpu_count()))
threads = 2
timeout = 360
graceful_timeout = 30
keepalive = 5

accesslog = str(BASE_DIR / "logs" / "gunicorn.access.log")
errorlog = str(BASE_DIR / "logs" / "gunicorn.error.log")
loglevel = "info"

capture_output = True
preload_app = True
