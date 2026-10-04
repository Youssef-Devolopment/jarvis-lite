from __future__ import annotations
from flask import Flask
from config import get_settings, ensure_flask_secret
from errors import register_error_handlers
from logger import get_logger, setup_logging
from routes import api_bp, views_bp

log = get_logger(__name__)


def create_app() -> Flask:
    s = get_settings()
    setup_logging(s.log_level)
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config["SECRET_KEY"] = ensure_flask_secret()
    if s.host not in ("127.0.0.1", "localhost", "::1"):
        log.warning("Listening on %s — the API has no auth. "
                    "Prefer 127.0.0.1 unless you know what you are doing.",
                    s.host)
    register_error_handlers(app)
    app.register_blueprint(views_bp)
    app.register_blueprint(api_bp)
    log.info("App created.")
    return app


app = create_app()
