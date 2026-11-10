"""
SOS Guardian — Production WSGI Entry Point
============================================================
This entrypoint exposes the WSGI callable `app` (and alias `application`)
for production deployment on:
  - Render / Linux VPS (Gunicorn): gunicorn wsgi:app --workers 2 --bind 0.0.0.0:$PORT
  - Windows / Local Production (Waitress): python wsgi.py
  - Docker / Containerized Workloads
"""

import os
import sys

# Ensure project root and backend are on sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, os.getenv("ENV_FILE", ".env")))

from backend.app import app
from backend.database import initialize_database

# Idempotently verify database schema readiness
initialize_database()

# WSGI standard alias
application = app

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 5000))
    is_prod = os.getenv("FLASK_ENV") == "production"

    print("=" * 60)
    print("🛡️  SOS GUARDIAN — PRODUCTION WSGI RUNNER")
    print(f"🌐 Host: {host}:{port}")
    print(f"⚙️  Environment: {'production' if is_prod else 'development'}")
    print("=" * 60)

    try:
        from waitress import serve
        print(f"🚀 Serving with Waitress WSGI on http://{host}:{port}")
        serve(app, host=host, port=port, threads=int(os.getenv("WAITRESS_THREADS", "4")))
    except ImportError:
        print("⚠️ Waitress not available, running Flask fallback server.")
        app.run(host=host, port=port, debug=not is_prod)
