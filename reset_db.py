#!/usr/bin/env python3
"""Reset the FindMe database and reload schema + seed.

- Local XAMPP (MYSQL_HOST=localhost): drops and recreates findme_db.
- Remote managed MySQL (e.g. Aiven): cannot drop databases, so all rows are
  deleted (foreign keys disabled) and the schema/seed are re-applied.
- SSL is used automatically when MYSQL_SSL_CA / ca.pem applies.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pymysql

from config import Config

# Order matters: children before parents
CLEAR_ORDER = [
    'activity_logs', 'notifications', 'recoveries', 'verification_requests',
    'matches', 'item_images', 'found_items', 'lost_items',
    'users', 'courses', 'faculties', 'roles', 'categories', 'locations',
]


def is_local():
    return Config.MYSQL_HOST in ('localhost', '127.0.0.1', '::1')


def connect(database=None):
    ssl_arg = (Config.MYSQL_CUSTOM_OPTIONS or {}).get('ssl') if Config.MYSQL_CUSTOM_OPTIONS else None
    try:
        return pymysql.connect(
            host=Config.MYSQL_HOST,
            port=int(Config.MYSQL_PORT),
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=database,
            charset='utf8mb4',
            connect_timeout=30,
            ssl=ssl_arg,
        )
    except pymysql.err.OperationalError as e:
        code = e.args[0] if e.args else None
        if code == 1049:
            sys.exit(
                f"ERROR: database '{database}' does not exist on {Config.MYSQL_HOST}. "
                'Run init_db.py first.'
            )
        if code == 1045:
            sys.exit(
                f"ERROR: access denied for user '{Config.MYSQL_USER}' at "
                f"{Config.MYSQL_HOST}:{Config.MYSQL_PORT}. Check MYSQL_USER/MYSQL_PASSWORD."
            )
        if code == 2003:
            sys.exit(
                f"ERROR: cannot reach MySQL at {Config.MYSQL_HOST}:{Config.MYSQL_PORT}. "
                'Check MYSQL_HOST/MYSQL_PORT (and that MySQL is running locally).'
            )
        sys.exit(f'ERROR: MySQL connection failed: {e}. Check the MYSQL_* env vars (see .env.example).')
    except Exception as e:
        sys.exit(f'ERROR: MySQL connection failed: {e}. Check the MYSQL_* env vars (see .env.example).')


def run_sql_file(cursor, file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    statements = [s.strip() for s in content.split(';') if s.strip() and not s.strip().startswith('--')]
    for stmt in statements:
        try:
            cursor.execute(stmt)
        except pymysql.err.MySQLError as e:
            if 'Duplicate key name' in str(e):  # CREATE INDEX on re-run
                continue
            raise


def reset_database():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ssl_state = 'on' if Config.MYSQL_CUSTOM_OPTIONS else 'off'
    print(
        f"Connecting to MySQL at {Config.MYSQL_HOST}:{Config.MYSQL_PORT} "
        f"as {Config.MYSQL_USER!r} (ssl={ssl_state})..."
    )

    if is_local():
        conn = connect(None)
        cursor = conn.cursor()
        cursor.execute(f"DROP DATABASE IF EXISTS `{Config.MYSQL_DB}`")
        cursor.execute(
            f"CREATE DATABASE `{Config.MYSQL_DB}` "
            'CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci'
        )
        conn.commit()
        conn.select_db(Config.MYSQL_DB)
        print(f'Local database dropped and recreated: {Config.MYSQL_DB}')
    else:
        conn = connect(Config.MYSQL_DB)
        cursor = conn.cursor()
        print(
            f"Remote host detected - clearing all rows in '{Config.MYSQL_DB}' "
            '(managed MySQL does not allow dropping databases)'
        )
        cursor.execute('SET FOREIGN_KEY_CHECKS=0')
        for table in CLEAR_ORDER:
            try:
                cursor.execute(f'DELETE FROM `{table}`')
                print(f'    cleared {table}')
            except pymysql.err.MySQLError as e:
                if "doesn't exist" not in str(e):
                    raise
        cursor.execute('SET FOREIGN_KEY_CHECKS=1')
        conn.commit()

    run_sql_file(cursor, os.path.join(base_dir, 'schema.sql'))
    conn.commit()
    print('Schema applied (schema.sql).')

    run_sql_file(cursor, os.path.join(base_dir, 'seed.sql'))
    conn.commit()
    print('Seed data inserted (seed.sql).')

    cursor.close()
    conn.close()
    print('Reset complete.')


if __name__ == '__main__':
    reset_database()
