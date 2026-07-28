import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pymysql
from config import Config

def init_database():
    conn = pymysql.connect(
        host=Config.MYSQL_HOST,
        port=Config.MYSQL_PORT,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        charset='utf8mb4'
    )
    cursor = conn.cursor()

    cursor.execute('DROP DATABASE IF EXISTS findme_db')
    cursor.execute('CREATE DATABASE findme_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci')
    cursor.execute('USE findme_db')
    conn.commit()

    schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schema.sql')
    with open(schema_path, 'r') as f:
        schema = f.read()

    schema = schema.replace('USE findme_db;', '')
    for statement in schema.split(';'):
        statement = statement.strip()
        if statement and not statement.startswith('--'):
            try:
                cursor.execute(statement)
            except Exception as e:
                print(f"Schema error: {e}")

    conn.commit()

    seed_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'seed.sql')
    if os.path.exists(seed_path):
        with open(seed_path, 'r') as f:
            seed = f.read()
        seed_cursor = conn.cursor()
        seed = seed.replace('USE findme_db;', '')
        for statement in seed.split(';'):
            statement = statement.strip()
            if statement and not statement.startswith('--'):
                try:
                    seed_cursor.execute(statement)
                except Exception as e:
                    print(f"Seed error: {e}")
        conn.commit()
        seed_cursor.close()

    cursor.close()
    conn.close()
    print("Database initialized successfully!")

if __name__ == '__main__':
    init_database()