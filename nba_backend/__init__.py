"""NBA player data backend bootstrap."""

from .routes import nba_bp
from .service import close_nba_db, init_nba_db


def init_nba_module(app, base_dir, db_path):
    app.config['NBA_BASE_DIR'] = base_dir
    app.config['NBA_DB_PATH'] = db_path
    app.config['NBA_IMAGE_DIR'] = __import__('os').environ.get(
        'NBA_IMAGE_DIR',
        __import__('os').path.join(base_dir, 'nba_images'),
    )
    app.config['NBA_AVATAR_DIR'] = __import__('os').environ.get(
        'NBA_AVATAR_DIR',
        __import__('os').path.join(base_dir, 'nba_avatar'),
    )
    app.register_blueprint(nba_bp)
    app.teardown_appcontext(close_nba_db)
    init_nba_db(db_path)
