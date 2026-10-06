#!/usr/bin/env python3
"""Quick health check: connect using the same env vars as the app and list users."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pymysql

from config import Config

ssl_arg = (Config.MYSQL_CUSTOM_OPTIONS or {}).get('ssl') if Config.MYSQL_CUSTOM_OPTIONS else None

try:
    conn = pymysql.connect(
        host=Config.MYSQL_HOST,
        port=int(Config.MYSQL_PORT),
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DB,
        charset='utf8mb4',
        connect_timeout=30,
        ssl=ssl_arg,
    )
except pymysql.err.OperationalError as e:
    code = e.args[0] if e.args else None
    if code == 1049:
        sys.exit(
            f"ERROR: database '{Config.MYSQL_DB}' does not exist on {Config.MYSQL_HOST}. "
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

cursor = conn.cursor()

cursor.execute('DESCRIBE users')
cols = cursor.fetchall()
print('Users table columns:')
for c in cols:
    print(f'  {c[0]} ({c[1]})')

cursor.execute('SELECT COUNT(*) FROM users')
count = cursor.fetchone()[0]
print(f'Total users: {count}')

cursor.execute('SELECT id, full_name, email, role_id FROM users')
for u in cursor.fetchall():
    print(f'  id={u[0]}: {u[1]}, {u[2]}, role_id={u[3]}')

cursor.close()
conn.close()
