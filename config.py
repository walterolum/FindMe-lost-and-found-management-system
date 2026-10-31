"""FindMe configuration.

Every setting is read from environment variables. Local development keeps
working with zero configuration (XAMPP MySQL on localhost + local disk
uploads); production (Render/Docker + Aiven + Cloudinary) reads real values
from the environment.

Required in production (Render):
    SECRET_KEY, MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB
Optional:
    MYSQL_SSL_CA       path to an Aiven CA certificate (ca.pem in project root)
    CLOUDINARY_*       when set, images go to Cloudinary instead of local disk
    FINDME_ENV=production  (or the Render-provided RENDER env var)
"""
import os
from urllib.parse import urlparse

# Load .env if present (local dev convenience)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
except ImportError:
    pass

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Development-only fallback key - never valid in production (checked below)
DEV_SECRET_KEY = 'findme-cavendish-secret-key-change-in-production'

# Local development defaults (XAMPP MySQL)
DEV_DB_HOST = 'localhost'
DEV_DB_PORT = 3306
DEV_DB_USER = 'root'
DEV_DB_PASSWORD = ''
DEV_DB_NAME = 'findme_db'


def _parse_mysql_url(url):
    """Parse mysql://user:pass@host:port/db into a dict, or None if invalid."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ('mysql', 'mysql+pymysql', 'mariadb'):
            return None
        return {
            'host': parsed.hostname,
            'port': parsed.port or 3306,
            'user': parsed.username,
            'password': parsed.password or '',
            'db': (parsed.path or '').lstrip('/'),
        }
    except Exception:
        return None


def is_production():
    """True on Render (RENDER env var) or when explicitly marked production."""
    return (
        bool(os.environ.get('RENDER'))
        or os.environ.get('FINDME_ENV') == 'production'
        or os.environ.get('FLASK_ENV') == 'production'
    )


# Optional single-URL style credentials (Render/Railway/Heroku convention)
_mysql_url = (
    os.environ.get('DATABASE_URL')
    or os.environ.get('MYSQL_URL')
    or os.environ.get('JAWSDB_URL')
    or os.environ.get('CLEARDB_DATABASE_URL')
)
_parsed = _parse_mysql_url(_mysql_url) if _mysql_url else None


def _env(name, legacy=None, default=None):
    """Read an env var, falling back to the legacy alias then the default."""
    for key in (name, legacy):
        if key:
            value = os.environ.get(key)
            if value is not None and value != '':
                return value
    return default


class Config:
    # ---- Secrets --------------------------------------------------------
    SECRET_KEY = os.environ.get('SECRET_KEY') or DEV_SECRET_KEY
    if is_production() and SECRET_KEY == DEV_SECRET_KEY:
        raise RuntimeError(
            'SECRET_KEY is missing or still the development default while running '
            'in production (RENDER or FINDME_ENV=production). '
            'Set a strong random SECRET_KEY environment variable.'
        )

    # ---- Database (XAMPP-friendly defaults) -----------------------------
    if _parsed:
        MYSQL_HOST = _parsed['host'] or DEV_DB_HOST
        MYSQL_PORT = _parsed['port']
        MYSQL_USER = _parsed['user'] or DEV_DB_USER
        MYSQL_PASSWORD = _parsed['password']
        MYSQL_DB = _parsed['db'] or DEV_DB_NAME
    else:
        MYSQL_HOST = _env('MYSQL_HOST', 'DB_HOST', DEV_DB_HOST)
        MYSQL_PORT = _env('MYSQL_PORT', 'DB_PORT', DEV_DB_PORT)
        MYSQL_USER = _env('MYSQL_USER', 'DB_USER', DEV_DB_USER)
        MYSQL_PASSWORD = _env('MYSQL_PASSWORD', 'DB_PASSWORD', DEV_DB_PASSWORD)
        MYSQL_DB = _env('MYSQL_DB', 'DB_NAME', DEV_DB_NAME)

    # ---- SSL (required by Aiven, never used for local XAMPP) ------------
    MYSQL_SSL_CA = _env('MYSQL_SSL_CA', 'DB_SSL_CA')
    _ssl_ca_path = None
    if MYSQL_SSL_CA:
        _candidate = (
            MYSQL_SSL_CA if os.path.isabs(MYSQL_SSL_CA)
            else os.path.join(BASE_DIR, MYSQL_SSL_CA)
        )
        _ssl_ca_path = os.path.abspath(_candidate)
        if not os.path.isfile(_ssl_ca_path):
            raise RuntimeError(
                f"MYSQL_SSL_CA='{MYSQL_SSL_CA}' was set but the file does not exist "
                f"(looked for {_ssl_ca_path}). Download the Aiven CA certificate and save "
                'it as ca.pem in the project root (see ca.pem.README), or unset '
                'MYSQL_SSL_CA when developing locally.'
            )
    elif (
        MYSQL_HOST not in ('localhost', '127.0.0.1', '::1')
        and os.path.isfile(os.path.join(BASE_DIR, 'ca.pem'))
    ):
        # Remote host + ca.pem in project root -> use it automatically
        _ssl_ca_path = os.path.join(BASE_DIR, 'ca.pem')

    # Omitted entirely (None) so local XAMPP works unchanged
    MYSQL_CUSTOM_OPTIONS = {'ssl': {'ca': _ssl_ca_path}} if _ssl_ca_path else None

    # ---- Cloudinary (optional; local disk is used when unset) -----------
    CLOUDINARY_CLOUD_NAME = _env('CLOUDINARY_CLOUD_NAME')
    CLOUDINARY_API_KEY = _env('CLOUDINARY_API_KEY')
    CLOUDINARY_API_SECRET = _env('CLOUDINARY_API_SECRET')

    # ---- Flask ----------------------------------------------------------
    FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')

    # ---- Session security ------------------------------------------------
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = is_production()

    @classmethod
    def cloudinary_configured(cls):
        """True when all three Cloudinary credentials are available."""
        return bool(
            cls.CLOUDINARY_CLOUD_NAME
            and cls.CLOUDINARY_API_KEY
            and cls.CLOUDINARY_API_SECRET
        )
