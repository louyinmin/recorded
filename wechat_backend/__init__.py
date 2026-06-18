"""WeChat Mini Program session backend bootstrap."""

import os

from .routes import wechat_bp
from .service import close_wechat_db, init_wechat_db


def init_wechat_module(app, base_dir, db_path):
    app.config['WECHAT_DB_PATH'] = db_path
    app.config['WECHAT_MINIPROGRAM_APPID'] = os.environ.get(
        'WECHAT_MINIPROGRAM_APPID',
        'wxb329162424904f03',
    )
    app.config['WECHAT_MINIPROGRAM_SECRET'] = os.environ.get('WECHAT_MINIPROGRAM_SECRET', '')
    app.register_blueprint(wechat_bp)
    app.teardown_appcontext(close_wechat_db)
    init_wechat_db(db_path)
