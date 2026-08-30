import sys
import os

path = os.path.dirname(os.path.abspath(__file__))
if path not in sys.path:
    sys.path.insert(0, path)

# Use PyMySQL as MySQLdb (pure-python, hosting-friendly, no mysqlclient C deps)
try:
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError:
    pass

from app import app as application

# WhiteNoise: serve static files efficiently in production (Render/Railway/Heroku)
try:
    from whitenoise import WhiteNoise
    # Only wrap if not already wrapped
    if not isinstance(application.wsgi_app, WhiteNoise):
        application.wsgi_app = WhiteNoise(application.wsgi_app, root=os.path.join(path, 'static'))
except ImportError:
    pass
