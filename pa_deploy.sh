#!/bin/bash
# FindMe - PythonAnywhere one-shot deploy
# Paste this into PythonAnywhere Bash console (after sign-up)
# Repo: https://github.com/walterolum/FindMe-lost-and-found-management-system

set -e
USERNAME=$(whoami)
REPO_URL="https://github.com/walterolum/FindMe-lost-and-found-management-system.git"
PROJECT_DIR="$HOME/FindMe-lost-and-found-management-system"

echo "=== FindMe PythonAnywhere Deploy ==="
echo "User: $USERNAME"

# 1. Clone/update repo
if [ -d "$PROJECT_DIR" ]; then
  echo "Updating existing repo..."
  cd "$PROJECT_DIR" && git pull
else
  echo "Cloning repo..."
  git clone "$REPO_URL" "$PROJECT_DIR"
  cd "$PROJECT_DIR"
fi

# 2. Venv
if [ ! -d "venv" ]; then
  echo "Creating venv..."
  python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 3. Create upload dirs
mkdir -p static/uploads/avatars static/uploads/lost static/uploads/found
touch static/uploads/.gitkeep

# 4. Prompt for DB password if not set (PythonAnywhere MySQL)
echo ""
echo "=== MySQL Setup ==="
echo "Go to Databases tab -> create MySQL DB (note password you set)"
echo "Then run in MySQL console:"
echo "  CREATE DATABASE ${USERNAME}\$findme_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
echo "Then create .env with:"
echo "  SECRET_KEY=$(openssl rand -hex 16)"
echo "  MYSQL_HOST=${USERNAME}.mysql.pythonanywhere-services.com"
echo "  MYSQL_USER=${USERNAME}"
echo "  MYSQL_PASSWORD=your-mysql-password"
echo "  MYSQL_DB=${USERNAME}\$findme_db"
echo ""
read -p "Have you created the DB? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  echo "Creating .env template if missing..."
  if [ ! -f .env ]; then
    SECRET=$(openssl rand -hex 16)
    cat > .env <<EOF
SECRET_KEY=$SECRET
MYSQL_HOST=${USERNAME}.mysql.pythonanywhere-services.com
MYSQL_PORT=3306
MYSQL_USER=${USERNAME}
MYSQL_PASSWORD=your-mysql-password
MYSQL_DB=${USERNAME}\$findme_db
FLASK_ENV=production
EOF
    echo ".env created - EDIT MYSQL_PASSWORD: nano .env"
  fi
  echo "Init DB? Running init_db.py (requires correct .env)..."
  # Uncomment after editing .env:
  # python init_db.py
  echo "If init_db.py fails, edit .env then run: python init_db.py"
fi

echo ""
echo "=== Web App Setup (Manual in Web tab) ==="
echo "1. Web tab -> Add a new web app -> Manual Configuration -> Python 3.11"
echo "2. Set:"
echo "   Source code: $PROJECT_DIR"
echo "   Working directory: $PROJECT_DIR"
echo "   WSGI file: $PROJECT_DIR/wsgi.py"
echo "   Virtualenv: $PROJECT_DIR/venv"
echo "3. Static files:"
echo "   /static/  -> $PROJECT_DIR/static/"
echo "   /media/   -> $PROJECT_DIR/static/uploads/  (or /uploads/)"
echo "4. Reload -> visit https://${USERNAME}.pythonanywhere.com/health (should be {\"status\":\"ok\"})"
echo "5. Login: admin@cavendish.ac.ug / password123"
echo ""
echo "Done! Project at $PROJECT_DIR"
