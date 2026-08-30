# FindMe - Cavendish University Uganda AI-Powered Lost & Found Management System

## Project Overview

FindMe is a centralized digital Lost and Found management platform for Cavendish University Uganda. It uses an AI-assisted matching engine to automatically identify potential matches between lost and found item reports, enabling students, lecturers, and staff to efficiently report, search, and recover lost property.

## Problem Statement

Cavendish University Ugandan students, lecturers, and staff lose personal items around campus. Without a centralized system, reporting and recovering lost property is difficult. FindMe solves this by providing:

- A digital platform for reporting lost and found items
- AI-powered automatic matching of potential lost/found pairs
- Administrator review and approval workflow
- Privacy protection for sensitive information
- A complete recovery tracking system

## System Architecture

### Tech Stack

- **Backend**: Python 3.x with Flask framework
- **Database**: MySQL (findme_db)
- **Frontend**: HTML5, CSS3, JavaScript (vanilla)
- **AI Engine**: Custom text similarity matching engine (Python)
- **Authentication**: bcrypt password hashing, session-based auth
- **Image Processing**: Pillow (PIL) for image optimization

### Folder Structure

```
findme/
├── app.py                  # Main Flask application (all routes)
├── config.py               # Application configuration
├── schema.sql              # Database schema
├── seed.sql                # Seed data for demo
├── init_db.py              # Database initialization script
├── requirements.txt         # Python dependencies
├── run.bat                  # Quick start script
├── ai/
│   ├── __init__.py          # AI package initialization
│   └── matcher.py           # AI matching engine
├── static/
│   ├── css/
│   │   └── style.css        # Main stylesheet
│   ├── js/
│   │   └── main.js          # Client-side JavaScript
│   └── uploads/             # Uploaded item images
└── templates/
    ├── base.html            # Base template with nav
    ├── index.html           # Landing page
    ├── login.html           # Login page
    ├── register.html        # Registration page
    ├── forgot_password.html # Forgot password page
    ├── change_password.html # Password change page
    ├── dashboard.html       # User dashboard
    ├── report_lost.html     # Report lost item form
    ├── report_found.html    # Report found item form
    ├── my_reports.html      # User's reports
    ├── search.html          # Search page
    ├── item_detail.html     # Item detail view
    ├── matches.html         # User's matches list
    ├── match_detail.html    # Match detail view
    ├── notifications.html   # Notification center
    ├── profile.html         # User profile
    ├── about.html           # About page
    └── admin/               # Admin templates
        ├── dashboard.html
        ├── users.html
        ├── faculties.html
        ├── courses.html
        ├── categories.html
        ├── locations.html
        ├── lost_items.html
        ├── found_items.html
        ├── ai_matches.html
        ├── verifications.html
        ├── recoveries.html
        ├── reports.html
        ├── activity_logs.html
        └── settings.html
```

## Deploy to Hosting (One-Click)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/walterolum/FindMe-lost-and-found-management-system)
[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/github/walterolum/FindMe-lost-and-found-management-system)

**Compatible hosts (Flask + MySQL):** PythonAnywhere (free, built-in MySQL - *recommended*), Render, Railway, Fly.io, DigitalOcean App Platform, Heroku. See [`DEPLOY.md`](DEPLOY.md) and [`deploy.txt`](deploy.txt) for full guide. This repo includes `Procfile`, `render.yaml`, `railway.json`, `Dockerfile`, `docker-compose.yml`, `wsgi.py` (with `pymysql` + `whitenoise`), and `/health` for hosting checks. Quick Docker: `docker-compose up --build` -> http://localhost:5000.

## Automated PythonAnywhere Deployment (GitHub Actions)

Fully automated: **push to `master`/`main` -> GitHub Actions pulls code on PythonAnywhere, updates deps, runs migrations, collects static (if Django), and reloads the webapp**. No manual SSH needed. Uses `deploy.sh` (idempotent, Flask/Django-aware) + PythonAnywhere API.

### How It Works
1. `deploy.sh` (in repo root) detects framework: `manage.py` -> Django, `app.py`+`wsgi.py` -> Flask (this project), otherwise generic Python.
2. On PythonAnywhere it: `git pull`, creates/activates `venv`, `pip install -r requirements.txt`, runs `migrate`/`collectstatic` for Django or `init_db.py` check for Flask, ensures `static/uploads`, then reloads via API or `touch` WSGI.
3. `.github/workflows/pythonanywhere.yml` triggers on push to `master`/`main` (or manual dispatch), creates an API console on PythonAnywhere, runs `bash deploy.sh`, and `POST /api/v0/user/{username}/webapps/{domain}/reload/`.

### Required GitHub Secrets
Add in GitHub repo: **Settings -> Secrets and variables -> Actions -> New repository secret** (never hardcode):

| Secret | Required | Value | Where to find |
|--------|----------|-------|---------------|
| `PA_API_TOKEN` | Yes | PythonAnywhere API token | https://www.pythonanywhere.com/user/YOURNAME/account/#api_token -> **Create new API token** |
| `PA_USERNAME` | Yes | Your PythonAnywhere username | Your username on PythonAnywhere (e.g., `walterolum`) |
| `PA_DOMAIN` | No | Webapp domain | Defaults to `YOURNAME.pythonanywhere.com`; set only if you use a custom domain |

Optional for first deploy only: set `RUN_INIT_DB=true` as a secret or in `deploy.sh` call to run `python init_db.py` (destructive - drops DB). Normally migrations are non-destructive.

### PythonAnywhere Setup (One-Time)
1. Sign up at https://www.pythonanywhere.com
2. **Bash** console:
   ```bash
   git clone https://github.com/walterolum/FindMe-lost-and-found-management-system.git
   cd FindMe-lost-and-found-management-system
   # deploy.sh will handle venv, but you can also run manually once:
   bash deploy.sh
   ```
3. **Databases** tab -> create MySQL DB `YOURNAME$findme_db` (host `YOURNAME.mysql.pythonanywhere-services.com`) -> in MySQL console:
   ```sql
   CREATE DATABASE YOURNAME$findme_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```
   Then set `.env` (or Secrets) for DB: `MYSQL_HOST`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DB`, `SECRET_KEY`.
4. **Web** tab -> **Add new web app** -> **Manual Configuration** -> Python 3.11 -> set:
   - Source code: `/home/YOURNAME/FindMe-lost-and-found-management-system`
   - Working directory: same
   - WSGI file: `/var/www/YOURNAME_pythonanywhere_com_wsgi.py` (edit to `from wsgi import application` or point to `/home/YOURNAME/.../wsgi.py`)
   - Virtualenv: `/home/YOURNAME/FindMe-lost-and-found-management-system/venv`
   - Static: `/static/` -> `/home/YOURNAME/.../static/`
5. Add secrets in GitHub as above, then **push to master** -> Actions runs -> site live at `https://YOURNAME.pythonanywhere.com/health`.

### Idempotency & Logging
- `deploy.sh` is idempotent: `mkdir -p`, `git pull --ff-only` with fallback, `pip install` upgrades, `migrate` is safe to re-run, `touch` reload is safe. Logs to `~/deploy.log` with timestamps and `set -euo pipefail` + `trap` for clear errors.
- Workflow uses pinned `actions/checkout@v4`, minimal `permissions: contents: read`, `concurrency: pythonanywhere-deploy`, and masks secrets.

### Verify
- Actions tab -> **Deploy to PythonAnywhere** -> green check -> visit `https://YOURNAME.pythonanywhere.com/health` -> `{"status":"ok"}` -> login `admin@cavendish.ac.ug` / `password123`.

## Installation Instructions

### Prerequisites

1. **Python 3.8+** installed
2. **MySQL 8.0+** installed and running
3. **XAMPP** (optional, includes MySQL)

### Setup Steps

#### 1. Start MySQL

If using XAMPP:
```
Start XAMPP Control Panel
Start MySQL service
```

Or start MySQL manually:
```
net start MySQL
```

#### 2. Install Python Dependencies

```bash
pip install Flask flask-mysqldb bcrypt Pillow PyMySQL
```

#### 3. Configure Database Connection

Edit `config.py` if needed:
```python
MYSQL_HOST = 'localhost'
MYSQL_PORT = 3306
MYSQL_USER = 'root'
MYSQL_PASSWORD = ''  # Your MySQL root password
MYSQL_DB = 'findme_db'
```

#### 4. Initialize the Database

```bash
python init_db.py
```

This creates the `findme_db` database and all tables, then seeds with demo data.

#### 5. Run the Application

```bash
python app.py
```

The application runs on `http://localhost:5000`

## Default Demo Accounts

| Email | Password | Role |
|-------|----------|------|
| admin@cavendish.ac.ug | password123 | Administrator |
| john.musinguzi@cavendish.ac.ug | password123 | Student |
| sarah.nakamya@cavendish.ac.ug | password123 | Student |
| peter.okello@cavendish.ac.ug | password123 | Lecturer |
| grace.tumusiime@cavendish.ac.ug | password123 | Student |

## User Roles

### Student / Lecturer (Regular Users)
- Report lost items
- Report found items
- Search items
- View their own reports
- View AI-generated matches
- Receive notifications
- Manage profile
- Change password

### Administrator
- All user features
- Manage users (activate/deactivate)
- Manage faculties, courses, categories, locations
- Review and approve/reject AI matches
- Handle verification requests
- Manage recoveries
- View reports and analytics
- View activity logs
- System settings

## AI Matching System

### How It Works

When a user submits a lost or found item report, the AI matching engine automatically compares the new report against all existing compatible reports (lost vs found).

The engine analyzes multiple factors:

| Factor | Weight | Description |
|--------|--------|-------------|
| Item Name | 25% | Text similarity of item names |
| Category | 15% | Same item category match |
| Color | 10% | Color match or similar color group |
| Brand | 10% | Brand name similarity |
| Model | 8% | Model similarity |
| Description | 12% | NLP-based description comparison |
| Location | 10% | Location proximity |
| Date | 5% | Date proximity |
| Time | 3% | Time proximity |
| Image | 2% | Image similarity (simulated) |

### Confidence Score Levels

| Score | Level | Meaning |
|-------|-------|---------|
| 90-100% | Very High | Strong match |
| 75-89% | High | Likely match |
| 50-74% | Possible | Potential match |
| Below 50% | Low | Weak match |

### AI Governance

A key design principle: **AI assists, it does not decide**. The AI generates potential matches, but an administrator must review and approve each match before sensitive information is revealed to users. This ensures:

- No false ownership claims
- Privacy protection
- Human oversight

### Extensibility

The AI module (`ai/matcher.py`) is designed to be upgradeable. The `compute_match_score()` function can be replaced with more advanced ML models without changing the rest of the application. External AI APIs can be integrated by modifying this module in isolation.

## Security Features

- **Password Hashing**: bcrypt with salt
- **SQL Injection Protection**: Parameterized queries (Flask-MySQLdb)
- **Session Management**: Flask sessions with secret key
- **Role-Based Access Control**: Separate routes for admin vs user
- **File Upload Validation**: File type, extension whitelist
- **CSRF Protection**: Form-based actions with confirmation
- **Sensitive Data Protection**: Images and details hidden until admin approval
- **Input Validation**: Server-side validation on all forms

## Database Design

### Key Tables

| Table | Purpose |
|-------|---------|
| users | User accounts with roles |
| roles | User type definitions |
| faculties | University faculties |
| courses | Academic programs |
| categories | Item categories |
| locations | Loss/found locations |
| lost_items | Lost item reports |
| found_items | Found item reports |
| matches | AI-generated matches |
| notifications | User notifications |
| verification_requests | Ownership verification |
| recoveries | Recovery tracking |
| activity_logs | Audit trail |

## Workflow

The FindMe workflow follows these steps:

1. **Report**: User submits a lost or found item report
2. **Match**: AI engine automatically compares against existing reports
3. **Review**: Administrator reviews AI-generated potential matches
4. **Approve/Reject**: Admin approves legitimate matches, rejects false ones
5. **Verify**: User may provide ownership verification if needed
6. **Notify**: Users receive notifications about match status
7. **Recover**: Owner collects the item with recovery instructions
8. **Close**: Item marked as recovered and case archived

## Demo Workflow for Presentation

1. Login as student (john.musinguzi / password123)
2. Report a lost item (e.g., "Black Samsung Phone lost near Library")
3. Login as another user (sarah.nakamya / password123)
4. Report a found item (e.g., "Black Samsung Phone found near Library")
5. AI automatically generates a potential match with confidence score
6. Both users receive notifications about the potential match
7. Login as admin (admin@cavendish.ac.ug / password123)
8. Go to AI Match Review to see pending matches
9. Compare the two reports and their images
10. Approve the match
11. Both users get notified of the approved match
12. The owner can see recovery information
13. Mark the item as recovered

## Known Limitations

- Image comparison is simulated (no real ML model for visual similarity)
- Email notifications are not implemented (in-app only)
- Password reset sends a message but does not actually email
- Demo accounts share the same password
- No rate limiting on login attempts
- No pagination on very large result sets (basic implementation)

## Future Improvements

- Real image similarity model (CNN-based)
- Email notification integration
- Pagination for large datasets
- Advanced search with filters
- Mobile app version
- Real-time chat between finder and owner
- QR code-based item verification
- Map-based location visualization
- Advanced analytics dashboard with charts
- REST API for mobile integration
- Elasticsearch for advanced text search

## License

This project was developed as an academic project for Cavendish University Uganda. All rights reserved.