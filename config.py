import os
from urllib.parse import urlparse

# Load .env if present (local dev)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

def _parse_mysql_url(url):
    """Parse mysql://user:pass@host:port/db into dict, returns None if invalid."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ('mysql', 'mysql+pymysql', 'mariadb'):
            return None
        return {
            'host': parsed.hostname or 'localhost',
            'port': parsed.port or 3306,
            'user': parsed.username or 'root',
            'password': parsed.password or '',
            'db': (parsed.path or '/findme_db').lstrip('/'),
        }
    except Exception:
        return None

# Support DATABASE_URL / MYSQL_URL / JAWSDB_URL / CLEARDB_DATABASE_URL (Render/Railway/Heroku)
_mysql_url = (
    os.environ.get('DATABASE_URL')
    or os.environ.get('MYSQL_URL')
    or os.environ.get('JAWSDB_URL')
    or os.environ.get('CLEARDB_DATABASE_URL')
)
_parsed = _parse_mysql_url(_mysql_url) if _mysql_url else None

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'findme-cavendish-secret-key-change-in-production')
    # If DATABASE_URL provided, use parsed values; else fall back to individual env vars
    MYSQL_HOST = _parsed['host'] if _parsed else os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_PORT = _parsed['port'] if _parsed else int(os.environ.get('MYSQL_PORT', 3306))
    MYSQL_USER = _parsed['user'] if _parsed else os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = _parsed['password'] if _parsed else os.environ.get('MYSQL_PASSWORD', '')
    MYSQL_DB = _parsed['db'] if _parsed else os.environ.get('MYSQL_DB', 'findme_db')
    MYSQL_CHARSET = 'utf8mb4'
    MYSQL_COLLATION = 'utf8mb4_unicode_ci'
    MYSQL_CONNECT_TIMEOUT = 30
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}