"""Compatibility entry for the Court Deck mini-game backend package."""

from pathlib import Path

_MODULE_DIR = Path(__file__).resolve().parents[1] / 'projects' / 'nbagame_api' / 'backend' / 'nbagame_backend'
__path__ = [str(_MODULE_DIR)]

from .routes import nbagame_bp
from .service import close_nbagame_db, init_nbagame_db, publish_local_assets


def init_nbagame_module(app, app_dir, db_path):
    """Register the isolated Court Deck API and its immutable local assets."""
    import os

    app.config['NBAGAME_DB_PATH'] = db_path
    app.config['NBAGAME_APP_ID'] = os.environ.get('NBAGAME_APP_ID', 'court-deck-prod')
    app.config['NBAGAME_APP_STATUS'] = os.environ.get('NBAGAME_APP_STATUS', 'active')
    app.config['NBAGAME_WECHAT_APPID'] = os.environ.get('NBAGAME_WECHAT_APPID', '')
    app.config['NBAGAME_WECHAT_SECRET'] = os.environ.get('NBAGAME_WECHAT_SECRET', '')
    app.config['NBAGAME_TOKEN_SECRET'] = os.environ.get('NBAGAME_TOKEN_SECRET', '')
    app.config['NBAGAME_PUBLIC_BASE_URL'] = os.environ.get('NBAGAME_PUBLIC_BASE_URL', '').rstrip('/')
    app.config['NBAGAME_MAX_REQUEST_BYTES'] = max(1, int(
        os.environ.get('NBAGAME_MAX_REQUEST_BYTES', str(2 * 1024 * 1024))
    ))
    app.config['NBAGAME_LOGIN_RATE_LIMIT'] = max(1, int(
        os.environ.get('NBAGAME_LOGIN_RATE_LIMIT', '20')
    ))
    app.config['NBAGAME_LOGIN_RATE_WINDOW_SECONDS'] = max(1, int(
        os.environ.get('NBAGAME_LOGIN_RATE_WINDOW_SECONDS', '60')
    ))
    app.config['NBAGAME_ASSET_MANIFEST_VERSION'] = os.environ.get(
        'NBAGAME_ASSET_MANIFEST_VERSION', '20260722.1'
    )
    app.config['NBAGAME_ASSETS_DIR'] = os.environ.get(
        'NBAGAME_ASSETS_DIR', os.path.join(app_dir, 'nbagame')
    )
    app.config['NBAGAME_PUBLISHED_ASSETS_DIR'] = os.environ.get(
        'NBAGAME_PUBLISHED_ASSETS_DIR',
        os.path.join(app_dir, 'nbagame_published_assets'),
    )
    app.register_blueprint(nbagame_bp)
    app.teardown_appcontext(close_nbagame_db)
    init_nbagame_db(db_path)
    publish_local_assets(app)
