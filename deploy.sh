#!/bin/bash
# FindMe - PythonAnywhere Automated Deployment Script
# Idempotent, framework-aware (Flask/Django), with logging and clear error handling.
# Usage (on PythonAnywhere Bash): bash ~/FindMe-lost-and-found-management-system/deploy.sh
# Or via GitHub Actions: curls PythonAnywhere API to execute this script remotely.
# Requirements: git, python3, pip, venv

set -euo pipefail

# --- Logging helpers ---
LOG_FILE="$HOME/deploy.log"
exec > >(tee -a "$LOG_FILE") 2>&1

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
fail() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $*" >&2; exit 1; }
trap 'fail "Deployment failed at line $LINENO (command: $BASH_COMMAND)"' ERR

# --- Detect project location ---
# Default to the directory where this script lives (repo root on PythonAnywhere)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$SCRIPT_DIR}"
VENV_DIR="${VENV_DIR:-$PROJECT_DIR/venv}"
REQUIREMENTS="${REQUIREMENTS:-$PROJECT_DIR/requirements.txt}"
WSGI_FILE="${WSGI_FILE:-$PROJECT_DIR/wsgi.py}"

log "========================================"
log "Starting deployment"
log "Project: $PROJECT_DIR"
log "Venv: $VENV_DIR"
log "========================================"

# --- 1. Detect framework ---
FRAMEWORK="unknown"
if [[ -f "$PROJECT_DIR/manage.py" ]]; then
    FRAMEWORK="django"
    log "Detected framework: Django (manage.py found)"
elif [[ -f "$PROJECT_DIR/app.py" && -f "$PROJECT_DIR/wsgi.py" ]]; then
    FRAMEWORK="flask"
    log "Detected framework: Flask (app.py + wsgi.py found)"
elif [[ -f "$PROJECT_DIR/app.py" ]]; then
    FRAMEWORK="flask"
    log "Detected framework: Flask (app.py found)"
else
    log "WARNING: Could not detect Django or Flask - proceeding with generic Python deployment"
fi

# --- 2. Ensure project directory exists and is a git repo ---
if [[ ! -d "$PROJECT_DIR" ]]; then
    fail "Project directory $PROJECT_DIR does not exist"
fi
cd "$PROJECT_DIR" || fail "Cannot cd to $PROJECT_DIR"

if [[ ! -d ".git" ]]; then
    log "WARNING: No .git directory - initializing from GitHub? Skipping git pull."
else
    log ">>> Pulling latest code from GitHub..."
    # Ensure we are on the correct branch (default to current)
    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "master")
    log "Current branch: $CURRENT_BRANCH"
    git fetch origin || fail "git fetch failed"
    # Try to pull; if branch not tracked, try master/main
    if ! git pull origin "$CURRENT_BRANCH" --ff-only 2>/dev/null; then
        log "Fast-forward failed, trying reset to origin/$CURRENT_BRANCH"
        git reset --hard "origin/$CURRENT_BRANCH" || {
            log "Trying master/main fallback"
            git pull origin master --ff-only || git pull origin main --ff-only || fail "git pull failed for both master and main"
        }
    fi
    log "Git pull complete: $(git rev-parse --short HEAD) - $(git log -1 --pretty=%B | head -n1)"
fi

# --- 3. Activate or create virtual environment ---
log ">>> Setting up virtual environment..."
if [[ ! -d "$VENV_DIR" ]]; then
    log "Creating venv at $VENV_DIR"
    python3 -m venv "$VENV_DIR" || fail "Failed to create venv"
fi
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate" || fail "Failed to activate venv"
log "Venv activated: $(which python) ($(python --version))"

# --- 4. Install/update dependencies ---
log ">>> Installing dependencies from $REQUIREMENTS..."
if [[ ! -f "$REQUIREMENTS" ]]; then
    fail "requirements.txt not found at $REQUIREMENTS"
fi
pip install --upgrade pip || log "WARNING: pip upgrade failed"
pip install -r "$REQUIREMENTS" || fail "pip install failed"
log "Dependencies installed"

# --- 5. Run database migrations (framework-specific) ---
log ">>> Running database migrations (if applicable)..."

if [[ "$FRAMEWORK" == "django" ]]; then
    if [[ -f "$PROJECT_DIR/manage.py" ]]; then
        log "Django: running migrate --no-input"
        python manage.py migrate --no-input || fail "Django migrate failed"
        log "Django migrations complete"
    else
        log "Django detected but manage.py not found - skipping migrate"
    fi
elif [[ "$FRAMEWORK" == "flask" ]]; then
    # Flask: check for Flask-Migrate (flask db) or init_db.py (FindMe)
    if [[ -f "$PROJECT_DIR/migrations" || -d "$PROJECT_DIR/migrations" ]]; then
        if command -v flask >/dev/null 2>&1; then
            log "Flask-Migrate: running flask db upgrade"
            flask db upgrade || log "WARNING: flask db upgrade failed - continuing"
        else
            log "Flask migrations folder found but flask CLI not available - skipping"
        fi
    fi
    # FindMe specific: init_db.py is destructive (DROPs DB), so only run if DB missing or explicitly requested
    if [[ -f "$PROJECT_DIR/init_db.py" ]]; then
        if [[ "${RUN_INIT_DB:-false}" == "true" ]]; then
            log "Flask: RUN_INIT_DB=true, running python init_db.py (DESTRUCTIVE - drops DB)"
            python init_db.py || fail "init_db.py failed"
        else
            log "Flask: Found init_db.py but RUN_INIT_DB not set - verifying DB instead"
            if [[ -f "$PROJECT_DIR/verify_db.py" ]]; then
                python verify_db.py || log "WARNING: verify_db.py failed - DB may need manual init (set RUN_INIT_DB=true for first deploy)"
            else
                log "No verify_db.py - skipping DB check (to init, run: RUN_INIT_DB=true bash deploy.sh)"
            fi
        fi
    else
        log "Flask: no migration system found - skipping migrations"
    fi
else
    log "Unknown framework - skipping migrations"
fi

# --- 6. Collect static files (Django only) ---
log ">>> Collecting static files (if Django)..."
if [[ "$FRAMEWORK" == "django" ]]; then
    if [[ -f "$PROJECT_DIR/manage.py" ]]; then
        log "Django: running collectstatic --no-input"
        python manage.py collectstatic --no-input || fail "collectstatic failed"
        log "collectstatic complete"
    fi
else
    # Flask: ensure upload dirs exist (idempotent)
    log "Flask: ensuring upload directories exist"
    mkdir -p "$PROJECT_DIR/static/uploads/avatars" "$PROJECT_DIR/static/uploads/lost" "$PROJECT_DIR/static/uploads/found" || fail "Failed to create upload dirs"
    touch "$PROJECT_DIR/static/uploads/.gitkeep" || true
    log "Upload dirs ready"
fi

# --- 7. Reload PythonAnywhere web app ---
log ">>> Reloading PythonAnywhere web application..."

# Method 1: PythonAnywhere API (if token available)
if [[ -n "${PA_API_TOKEN:-}" && -n "${PA_USERNAME:-}" ]]; then
    PA_DOMAIN="${PA_DOMAIN:-${PA_USERNAME}.pythonanywhere.com}"
    log "Reloading via PythonAnywhere API: https://www.pythonanywhere.com/api/v0/user/$PA_USERNAME/webapps/$PA_DOMAIN/reload/"
    HTTP_CODE=$(curl -s -o /tmp/pa_reload.out -w "%{http_code}" -X POST "https://www.pythonanywhere.com/api/v0/user/$PA_USERNAME/webapps/$PA_DOMAIN/reload/" \
        -H "Authorization: Token $PA_API_TOKEN" || echo "000")
    cat /tmp/pa_reload.out || true
    if [[ "$HTTP_CODE" == "200" ]]; then
        log "API reload successful (HTTP 200)"
    else
        log "WARNING: API reload returned HTTP $HTTP_CODE - trying WSGI touch fallback"
        # Fallback to touch
        if [[ -n "${PA_USERNAME:-}" ]]; then
            WSGI_PA="/var/www/${PA_USERNAME}_pythonanywhere_com_wsgi.py"
            if [[ -f "$WSGI_PA" ]]; then
                touch "$WSGI_PA" && log "Touched $WSGI_PA"
            else
                log "WARNING: WSGI file $WSGI_PA not found - ensure Web app is created in PythonAnywhere Web tab"
            fi
        fi
        # Also touch local wsgi.py
        touch "$WSGI_FILE" && log "Touched $WSGI_FILE"
    fi
else
    # Method 2: Touch WSGI file (works when script runs on PythonAnywhere directly)
    log "PA_API_TOKEN not set - using WSGI touch reload"
    if [[ -n "${PA_USERNAME:-}" ]]; then
        WSGI_PA="/var/www/${PA_USERNAME}_pythonanywhere_com_wsgi.py"
        if [[ -f "$WSGI_PA" ]]; then
            touch "$WSGI_PA" && log "Touched $WSGI_PA - PythonAnywhere will reload"
        else
            log "WARNING: $WSGI_PA not found - touching local wsgi.py"
            touch "$WSGI_FILE" && log "Touched $WSGI_FILE"
        fi
    else
        # Try common locations
        if [[ -f "/var/www/$(whoami)_pythonanywhere_com_wsgi.py" ]]; then
            touch "/var/www/$(whoami)_pythonanywhere_com_wsgi.py" && log "Touched PythonAnywhere WSGI file"
        else
            touch "$WSGI_FILE" && log "Touched $WSGI_FILE"
        fi
    fi
fi

# --- 8. Verify deployment ---
log ">>> Verifying deployment..."
sleep 2
if command -v curl >/dev/null 2>&1; then
    # Try health endpoint if PA_DOMAIN known
    VERIFY_DOMAIN="${PA_DOMAIN:-${PA_USERNAME:-}.pythonanywhere.com}"
    # Remove trailing dot if PA_USERNAME empty
    if [[ "$VERIFY_DOMAIN" == ".pythonanywhere.com" ]]; then
        log "Skipping HTTP verify - PA_USERNAME not set"
    else
        HEALTH_URL="https://$VERIFY_DOMAIN/health"
        log "Checking $HEALTH_URL"
        if curl -fsS --max-time 10 "$HEALTH_URL" | grep -q "ok"; then
            log "Health check passed: $HEALTH_URL is live"
        else
            log "WARNING: Health check failed or returned non-ok (may need a few seconds to reload)"
        fi
    fi
fi

log "========================================"
log "Deployment completed successfully"
log "Project: $PROJECT_DIR @ $(git rev-parse --short HEAD 2>/dev/null || echo 'no-git')"
log "Framework: $FRAMEWORK"
log "Log file: $LOG_FILE"
log "========================================"

deactivate || true
