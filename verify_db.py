import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import Config
import pymysql

conn = pymysql.connect(host=Config.MYSQL_HOST, port=Config.MYSQL_PORT, user=Config.MYSQL_USER, password=Config.MYSQL_PASSWORD, database='findme_db', charset='utf8mb4')
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
print('Database verified successfully!')