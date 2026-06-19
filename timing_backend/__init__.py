"""Timing Mini Program plan config backend bootstrap."""

from .routes import timing_bp


def init_timing_module(app, base_dir):
    app.config['TIMING_BASE_DIR'] = base_dir
    app.register_blueprint(timing_bp)
