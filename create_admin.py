#!/usr/bin/env python3
"""Create (or update) an Administrator account interactively.

Production deployments should never rely on the demo password - run this
script once (locally or on the host) to create a real admin with role_id 3.

Reads the same MYSQL_* env vars as the application. Safe to re-run: if the
email already exists, the account is updated to Administrator with the new
password.
"""
import getpass
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bcrypt
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
            sys.exit(f"ERROR: database '{database}' does not exist. Run init_db.py first.")
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


def main():
    print('=== Create / update a FindMe Administrator ===')
    print(f"(database: {Config.MYSQL_DB} @ {Config.MYSQL_HOST})\n")

    email = input('Admin email: ').strip().lower()
    full_name = input('Full name: ').strip()
    password = getpass.getpass('Password: ')
    confirm = getpass.getpass('Confirm password: ')

    if not email or '@' not in email:
        sys.exit('ERROR: please enter a valid email address.')
    if not full_name:
        sys.exit('ERROR: please enter a full name.')
    if len(password) < 8:
        sys.exit('ERROR: password must be at least 8 characters.')
    if password != confirm:
        sys.exit('ERROR: passwords do not match.')

    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    conn = connect(Config.MYSQL_DB)
    cursor = conn.cursor()

    # Ensure the Administrator role exists (id 3 is required by the app)
    cursor.execute(
        "INSERT IGNORE INTO roles (id, name, description) VALUES "
        "(3, 'Administrator', 'System administrator')"
    )
    conn.commit()

    cursor.execute('SELECT id FROM users WHERE email = %s', (email,))
    existing = cursor.fetchone()

    if existing:
        cursor.execute(
            'UPDATE users SET full_name = %s, password_hash = %s, role_id = 3, '
            'is_active = TRUE, email_verified = TRUE WHERE email = %s',
            (full_name, password_hash, email),
        )
        action = 'updated'
    else:
        cursor.execute(
            'INSERT INTO users (full_name, email, password_hash, role_id, is_active, email_verified) '
            'VALUES (%s, %s, %s, 3, TRUE, TRUE)',
            (full_name, email, password_hash),
        )
        action = 'created'

    conn.commit()
    cursor.close()
    conn.close()

    print(f"\nSuccess: administrator {action} ({email}).")
    print('You can now log in on the deployed site with this email and password.')


if __name__ == '__main__':
    main()
