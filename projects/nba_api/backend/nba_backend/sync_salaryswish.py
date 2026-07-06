"""Command line entry for refreshing SalarySwish salary-cap data."""

import argparse
import json
import os

from .service import connect_db, init_nba_db
from .salaryswish import sync_salaryswish


def default_db_path():
    base_dir = os.environ.get('RECORDED_BASE_DIR') or os.getcwd()
    return os.environ.get('NBA_DB_PATH') or os.path.join(base_dir, 'nba.db')


def parse_args():
    parser = argparse.ArgumentParser(description='Sync SalarySwish NBA salary-cap data into nba.db')
    parser.add_argument('--db', default=default_db_path(), help='SQLite database path. Defaults to NBA_DB_PATH or ./nba.db')
    parser.add_argument('--team', action='append', dest='teams', help='SalarySwish team slug, e.g. lakers. Repeatable.')
    parser.add_argument('--concurrency', type=int, default=4, help='Concurrent team detail fetches. Max is capped in service.')
    return parser.parse_args()


def main():
    args = parse_args()
    init_nba_db(args.db)
    conn = connect_db(args.db)
    try:
        result = sync_salaryswish(conn, team_slugs=args.teams, concurrency=args.concurrency)
    finally:
        conn.close()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == '__main__':
    main()
