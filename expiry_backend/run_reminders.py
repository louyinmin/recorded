"""CLI entrypoint for expiry reminder scanning."""

import os

from .reminder import run_daily_scan


def main():
    base_dir = os.environ.get('RECORDED_BASE_DIR', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    db_path = os.environ.get('RECORDED_DB_PATH', os.path.join(base_dir, 'data.db'))
    summary = run_daily_scan(db_path, base_dir)
    print('site_created={site_created} email_sent={email_sent} email_failed={email_failed} advanced_resources={advanced_resources}'.format(**summary))


if __name__ == '__main__':
    main()
