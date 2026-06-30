"""Compatibility entry for the life atlas backend package."""

from pathlib import Path

_MODULE_DIR = Path(__file__).resolve().parents[1] / "projects" / "life_atlas" / "backend" / "life_backend"
__path__ = [str(_MODULE_DIR)]

from .routes import life_bp
from .service import close_life_db, init_life_db


def init_life_module(app, base_dir, db_path):
    app.config["LIFE_BASE_DIR"] = base_dir
    app.config["LIFE_DB_PATH"] = db_path
    app.register_blueprint(life_bp)
    app.teardown_appcontext(close_life_db)
    init_life_db(db_path)
