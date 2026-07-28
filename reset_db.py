import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pymysql
from config import Config

def reset_database():
    conn = pymysql.connect(
        host=Config.MYSQL_HOST,
        port=Config.MYSQL_PORT,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        charset='utf8mb4',
        autocommit=True
    )
    cursor = conn.cursor()

    cursor.execute('DROP DATABASE IF EXISTS findme_db')
    cursor.execute('CREATE DATABASE findme_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci')
    cursor.execute('USE findme_db')

    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schema.sql'), 'r') as f:
        sql = f.read()

    sql = sql.replace('USE findme_db;', '')

    cursor.execute('SET FOREIGN_KEY_CHECKS = 0')

    count = 0
    for stmt in sql.split(';'):
        stmt = stmt.strip()
        if stmt and not stmt.startswith('--') and not stmt.startswith('/*'):
            try:
                cursor.execute(stmt)
                count += 1
            except Exception as e:
                print(f'Schema error ({count}): {e}')

    cursor.execute('SET FOREIGN_KEY_CHECKS = 1')
    conn.commit()
    print(f'Schema: {count} statements executed')

    seed_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'seed.sql')
    if os.path.exists(seed_path):
        cursor.execute('USE findme_db')
        cursor.execute('SET FOREIGN_KEY_CHECKS = 0')

        with open(seed_path, 'r') as f:
            seed = f.read()

        seed = seed.replace('USE findme_db;', '')

        s_count = 0
        for stmt in seed.split(';'):
            stmt = stmt.strip()
            if stmt and not stmt.startswith('--') and not stmt.startswith('/*'):
                try:
                    cursor.execute(stmt)
                    s_count += 1
                except Exception as e:
                    print(f'Seed error: {e}')

        cursor.execute('SET FOREIGN_KEY_CHECKS = 1')
        conn.commit()
        print(f'Seed: {s_count} statements executed')

    cursor.close()
    conn.close()
    print('Database reset complete!')

if __name__ == '__main__':
    reset_database()