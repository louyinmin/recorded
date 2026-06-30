"""Compatibility entry for the timing mini-program backend package."""

from pathlib import Path

_MODULE_DIR = Path(__file__).resolve().parents[1] / "projects" / "timing_api" / "backend" / "timing_backend"
__path__ = [str(_MODULE_DIR)]

from .routes import timing_bp


def init_timing_module(app, base_dir):
    app.config["TIMING_BASE_DIR"] = base_dir
    app.register_blueprint(timing_bp)
