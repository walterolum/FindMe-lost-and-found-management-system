#!/usr/bin/env python3
"""Initialize the FindMe database (schema.sql + seed.sql).

Reads the same MYSQL_* env vars as the application (.env is auto-loaded by config).

- Local XAMPP (MYSQL_HOST=localhost): creates findme_db if it does not exist.
- Remote managed MySQL (e.g. Aiven): uses MYSQL_DB as given - the free service
  user cannot CREATE DATABASE, so the database must already exist.
- SSL is used automatically when MYSQL_SSL_CA / ca.pem applies.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pymysql

from config import Config


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
                f"Create it first (locally: CREATE DATABASE {Config.MYSQL_DB}; "
                'on Aiven pick an existing database such as defaultdb), then re-run.'
            )
        if code == 1045:
            sys.exit(
                f"ERROR: access denied for user '{Config.MYSQL_USER}' at "
                f"{Config.MYSQL_HOST}:{Config.MYSQL_PORT}. Check MYSQL_USER/MYSQL_PASSWORD"
                + (' and MYSQL_SSL_CA (Aiven requires the ca.pem certificate).' if ssl_arg else '.')
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
    """Run a .sql file statement by statement."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    content = '\n'.join(l for l in content.splitlines() if not l.strip().startswith('--'))
    statements = [s.strip() for s in content.split(';') if s.strip()]
    for stmt in statements:
        try:
            cursor.execute(stmt)
        except pymysql.err.MySQLError as e:
            if 'Duplicate key name' in str(e):
                continue
            raise


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ssl_state = 'on' if Config.MYSQL_CUSTOM_OPTIONS else 'off'
    print(
        f"Connecting to MySQL at {Config.MYSQL_HOST}:{Config.MYSQL_PORT} "
        f"as {Config.MYSQL_USER!r} (ssl={ssl_state})..."
    )

    if is_local():
        conn = connect(None)
        cursor = conn.cursor()
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{Config.MYSQL_DB}` "
            'CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci'
        )
        conn.commit()
        conn.select_db(Config.MYSQL_DB)
        print(f'Local database ensured: {Config.MYSQL_DB}')
    else:
        conn = connect(Config.MYSQL_DB)
        cursor = conn.cursor()
        print(f"Using existing remote database: {Config.MYSQL_DB}")

    run_sql_file(cursor, os.path.join(base_dir, 'schema.sql'))
    conn.commit()
    print('Schema applied (schema.sql).')

    run_sql_file(cursor, os.path.join(base_dir, 'seed.sql'))
    conn.commit()
    print('Seed data inserted (seed.sql).')

    cursor.execute('SELECT COUNT(*) FROM users')
    count = cursor.fetchone()[0]
    cursor.close()
    conn.close()

    print(f'Done. {count} user(s) in the database.')
    print('Demo login: admin@cavendish.ac.ug / password123 (demo only -')
    print('run create_admin.py to create a real administrator in production).')


if __name__ == '__main__':
    main()
