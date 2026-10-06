"""Per-request MySQL connections (PyMySQL) for FindMe.

One connection per request, stored on flask.g and closed by
teardown_appcontext (free MySQL tiers have a low connection limit).
SSL is used automatically when Config.MYSQL_CUSTOM_OPTIONS is set (Aiven).
A short retry handles free-tier cold starts.
"""
import time

import pymysql
from pymysql.cursors import Cursor  # tuple rows: existing code indexes row[0]
from flask import g, current_app


def _ssl_options():
    """ssl argument for pymysql.connect(), or None (local XAMPP: no SSL)."""
    custom = current_app.config.get('MYSQL_CUSTOM_OPTIONS') or {}
    return custom.get('ssl')


def get_db():
    """Get the database connection for this request (created on first use)."""
    if 'db' not in g:
        ssl_arg = _ssl_options()
        last_error = None
        for attempt in range(3):  # free DB/app may be waking from idle
            try:
                g.db = pymysql.connect(
                    host=current_app.config['MYSQL_HOST'],
                    port=int(current_app.config['MYSQL_PORT']),
                    user=current_app.config['MYSQL_USER'],
                    password=current_app.config['MYSQL_PASSWORD'],
                    database=current_app.config['MYSQL_DB'],
                    charset='utf8mb4',
                    cursorclass=Cursor,
                    connect_timeout=30,
                    ssl=ssl_arg,
                    read_timeout=30,
                    write_timeout=30,
                )
                break
            except Exception as exc:
                last_error = exc
                if attempt < 2:
                    time.sleep(1)  # short backoff
        else:
            raise last_error
    return g.db


def close_db(e=None):
    """Close this request's database connection."""
    db = g.pop('db', None)
    if db is not None:
        db.close()
