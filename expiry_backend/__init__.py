"""Expiry management module bootstrap."""

from .routes import expiry_bp
from .service import close_expiry_db, init_expiry_db


def init_expiry_module(app, base_dir, db_path):
    """Register the expiry blueprint and ensure schema exists."""
    app.config['EXPIRY_BASE_DIR'] = base_dir
    app.config['EXPIRY_DB_PATH'] = db_path
    app.register_blueprint(expiry_bp)
    app.teardown_appcontext(close_expiry_db)
    init_expiry_db(db_path, base_dir)

