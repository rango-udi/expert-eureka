"""Serve one Wowy process inside the application container."""

from pathlib import Path
import sys
import os

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.configuration import load


def main():
    """Load private settings and bind the container port with a single default worker thread."""
    if os.environ.get("CMDC_CONTAINER") != "1":
        raise ValueError("Start Wowy through cmdc with Docker.")
    values = load()
    from waitress import serve
    from storefront.wsgi import application

    if not (ROOT / ".runtime/data/db.sqlite3").exists():
        raise ValueError("Database missing. Run cmdc setup before starting Wowy.")
    serve(application, host="0.0.0.0", port=8000,
          threads=int(values["WEB_THREADS"]), connection_limit=16, channel_timeout=30)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback

        diagnostic = ROOT / ".runtime/server-errors.log"
        try:
            diagnostic.parent.mkdir(parents=True, exist_ok=True)
            with diagnostic.open("a", encoding="utf-8") as stream:
                traceback.print_exc(file=stream)
            detail = "Technical details: .runtime/server-errors.log."
        except OSError:
            detail = "Check write permissions for the project folder."
        print("ERROR: Wowy could not start. Run cmdc setup to initialize the database, "
              "check .env and container memory limits, then retry. " + detail,
              file=sys.stderr)
        raise SystemExit(2)
