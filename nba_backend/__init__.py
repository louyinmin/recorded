"""Compatibility entry for the NBA mini-program backend package."""

import os
from pathlib import Path

_MODULE_DIR = Path(__file__).resolve().parents[1] / "projects" / "nba_api" / "backend" / "nba_backend"
__path__ = [str(_MODULE_DIR)]

from .routes import nba_bp
from .service import close_nba_db, init_nba_db


def init_nba_module(app, base_dir, db_path):
    app.config["NBA_BASE_DIR"] = base_dir
    app.config["NBA_DB_PATH"] = db_path
    app.config["NBA_IMAGE_DIR"] = os.environ.get(
        "NBA_IMAGE_DIR",
        os.path.join(base_dir, "nba_images"),
    )
    app.config["NBA_AVATAR_DIR"] = os.environ.get(
        "NBA_AVATAR_DIR",
        os.path.join(base_dir, "nba_avatar"),
    )
    app.config["NBA_TEAM_IMAGE_DIR"] = os.environ.get(
        "NBA_TEAM_IMAGE_DIR",
        os.path.join(base_dir, "nba_team_images"),
    )
    app.register_blueprint(nba_bp)
    app.teardown_appcontext(close_nba_db)
    init_nba_db(db_path)
