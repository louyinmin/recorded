"""Life backend bootstrap."""

from .routes import life_bp
from .service import close_life_db, init_life_db


def init_life_module(app, base_dir, db_path):
    app.config['LIFE_BASE_DIR'] = base_dir
    app.config['LIFE_DB_PATH'] = db_path
    app.register_blueprint(life_bp)
    app.teardown_appcontext(close_life_db)
    init_life_db(db_path)

