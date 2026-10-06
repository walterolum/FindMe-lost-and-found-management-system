# FindMe - Cavendish University Uganda AI-Powered Lost & Found Management System

## Project Overview

FindMe is a centralized digital Lost and Found management platform for Cavendish University Uganda. An AI-assisted matching engine automatically compares lost and found item reports, so students, lecturers, and staff can report, search, and recover lost property quickly.

**Problem:** without a centralized system, reporting and recovering lost property on campus is slow and unreliable. FindMe solves this with:

- A digital platform for reporting lost and found items
- AI-powered automatic matching of potential lost/found pairs
- Administrator review and approval workflow
- Privacy protection for sensitive information
- A complete recovery tracking system

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+ with Flask (gunicorn in production) |
| Database | MySQL (XAMPP locally, Aiven for MySQL in production, PyMySQL driver) |
| Frontend | HTML5, CSS3, JavaScript (vanilla) |
| AI Engine | Custom text-similarity matcher (`ai/matcher.py`), 12 weighted factors |
| Images | Cloudinary (production) / local disk `static/uploads` (development) |
| Security | bcrypt password hashing, Flask-WTF CSRF protection, Flask-Limiter rate limiting, secure session cookies |

## User Roles

| Role | Capabilities |
|---|---|
| Student | Report lost/found items, search, claim matches, manage profile |
| Lecturer/Staff | Same as student (role 2) |
| Administrator | Review/approve matches, verify ownership, manage users, faculties, courses, categories, locations, activity logs, system settings |

Demo accounts after seeding: `admin@cavendish.ac.ug` / `password123` (demo only - see below), plus demo students/lecturers.

## Local Setup (XAMPP)

Local development needs **no new configuration** - with no environment variables set, the app uses XAMPP MySQL on `localhost` and saves images to `static/uploads`.

1. **Install XAMPP** and start **MySQL** from the XAMPP control panel.
2. **Clone the repository**
   ```bash
   git clone https://github.com/walterolum/FindMe-lost-and-found-management-system.git
   cd FindMe-lost-and-found-management-system
   ```
3. **Create a virtual environment and install dependencies**
   ```bash
   python -m venv venv
   venv\Scripts\activate        # Windows
   # source venv/bin/activate   # macOS/Linux
   pip install -r requirements.txt
   ```
4. **Create and seed the database** (XAMPP's default root user has no password):
   ```bash
   python init_db.py
   ```
   This creates `findme_db`, applies `schema.sql` (all tables `IF NOT EXISTS`), and inserts `seed.sql` (`INSERT IGNORE` - safe to re-run).
5. **Run the app**
   ```bash
   python app.py
   ```
   Open http://localhost:5000 and log in with `admin@cavendish.ac.ug` / `password123`.

Optional helper scripts (all read the same env vars, see `.env.example`):

| Script | Purpose |
|---|---|
| `python init_db.py` | Create schema + seed (creates `findme_db` locally if missing) |
| `python reset_db.py` | Drop/recreate locally (or clear rows remotely) + reseed |
| `python verify_db.py` | Connect and list users |
| `python create_admin.py` | Interactive prompt to create/update a real Administrator |

To use a non-default MySQL user/password, copy `.env.example` to `.env` and fill in `MYSQL_USER` / `MYSQL_PASSWORD` (`.env` is gitignored and auto-loaded).

## Deploy to Render + Aiven + Cloudinary (Free)

Full walkthrough: [`DEPLOY.md`](DEPLOY.md). Short version:

### 1. Aiven for MySQL (free)

1. Create an account at [console.aiven.io](https://console.aiven.io/) → create a **MySQL** service on the **free** tier.
2. Note **Host**, **Port** (3306), **User** (`avnadmin`), **Password**, **Database** (`defaultdb`).
3. Download the **CA certificate** and save it in the project root as **`ca.pem`** (see [`ca.pem.README`](ca.pem.README)). The free user cannot create databases - use `defaultdb` as-is.

### 2. Initialize the database

```bash
export MYSQL_HOST=your-host.aivencloud.com
export MYSQL_PORT=3306
export MYSQL_USER=avnadmin
export MYSQL_PASSWORD=your-password
export MYSQL_DB=defaultdb
export MYSQL_SSL_CA=ca.pem
python init_db.py
python create_admin.py      # real admin - never rely on the demo password
```

### 3. Cloudinary (free)

Create an account at [cloudinary.com](https://cloudinary.com/) and copy your **Cloud Name**, **API Key**, and **API Secret** from the dashboard. Images are Pillow-processed (thumbnail 1200px, RGB, quality 85) and uploaded to Cloudinary; the database keeps the original `folder/<hex>.jpg` path style and `/uploads/<path>` redirects to the Cloudinary delivery URL.

### 4. Render (free web service)

1. Push this repository to GitHub.
2. On [render.com](https://render.com/) → **New** → **Web Service** → connect the repo. Render reads [`render.yaml`](render.yaml) (Docker runtime, free plan, health check `/healthz`).
3. Set these environment variables in **Dashboard → Environment** (declared `sync: false` in render.yaml):

| Variable | Required | Value |
|---|---|---|
| `SECRET_KEY` | Yes | Strong random string (`python -c "import secrets; print(secrets.token_hex(32))"`) |
| `MYSQL_HOST` | Yes | Your Aiven host (`....aivencloud.com`) |
| `MYSQL_USER` | Yes | `avnadmin` |
| `MYSQL_PASSWORD` | Yes | Aiven service password |
| `CLOUDINARY_CLOUD_NAME` | Yes | From Cloudinary dashboard |
| `CLOUDINARY_API_KEY` | Yes | From Cloudinary dashboard |
| `CLOUDINARY_API_SECRET` | Yes | From Cloudinary dashboard |
| `MYSQL_DB` | No | `defaultdb` (preset in render.yaml) |
| `MYSQL_SSL_CA` | No | `ca.pem` (preset in render.yaml - commit the downloaded file) |
| `MYSQL_PORT` | No | `3306` (preset in render.yaml) |
| `FINDME_ENV` | No | `production` (preset in render.yaml) |

4. Deploy. The app **fails loudly at startup** if required variables are missing. Verify `/healthz` returns `ok`.

Other supported env vars: `DATABASE_URL=mysql://user:pass@host:3306/db` (parsed automatically), and legacy aliases `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_SSL_CA`. Local development with XAMPP needs none of them.

## AI Matching System

### How It Works

When a user submits a lost or found item report, the engine compares it against all existing compatible reports (lost vs found). Matches scoring ≥30% are stored as **pending** for administrator approval. Background threads run the matcher after each report (with a synchronous fallback), and admins can regenerate everything from **Admin → AI Match Review → Re-run AI Matching**.

### Factor Weights (12 factors, sum = 1.00)

| Factor | Weight | Description |
|---|---|---|
| Item name | 0.20 (20%) | Text similarity of item names |
| Category | 0.10 (10%) | Same item category |
| Color | 0.08 (8%) | Color match or similar color group |
| Brand | 0.08 (8%) | Brand name similarity |
| Model | 0.06 (6%) | Model similarity |
| Description | 0.10 (10%) | NLP-style description comparison |
| Location | 0.10 (10%) | Location proximity |
| Date | 0.04 (4%) | Date proximity |
| Time | 0.02 (2%) | Time proximity |
| Appearance (image) | 0.08 (8%) | Appearance/image similarity (simulated) |
| Shape | 0.04 (4%) | Shape match |
| Identical features | 0.10 (10%) | Serial number, unique marks, approximate value |
| **Total** | **1.00 (100%)** | Enforced by an assert in `ai/matcher.py` |

### Confidence Score Levels

| Score | Level | Meaning |
|---|---|---|
| 90-100% | Very High | Strong match |
| 75-89% | High | Likely match |
| 50-74% | Possible | Potential match |
| Below 50% | Low | Weak match (below 30% is not stored) |

## Security

- Passwords hashed with **bcrypt**
- **CSRF protection** (Flask-WTF) on every POST form, with a friendly error handler
- **Rate limiting** (Flask-Limiter, in-memory): 10/min on login POST, 5/min on register and forgot-password POST
- Session cookies: **HttpOnly**, **SameSite=Lax**, **Secure** in production
- Parameterized SQL everywhere
- Role-based access control + activity logging (client IP via `X-Forwarded-For` behind Render's proxy, ProxyFix configured)
- Debug mode OFF in production; logs to stdout

## Project Structure

```
findme/
├── app.py                  # Flask application (routes, auth, reports, admin)
├── config.py               # All settings from env vars (XAMPP defaults, fails loudly in production)
├── db.py                   # Per-request PyMySQL connections (SSL, retry, teardown)
├── storage.py              # Cloudinary upload helper (local-disk fallback in save_image)
├── wsgi.py                 # gunicorn entry point (PyMySQL + WhiteNoise)
├── ai/matcher.py           # 12-factor AI matching engine
├── schema.sql              # Database schema (IF NOT EXISTS, imports into selected DB)
├── seed.sql                # Demo data (INSERT IGNORE, safe to re-run)
├── init_db.py              # Create schema + seed (local DB creation when on localhost)
├── reset_db.py             # Reset database (drop locally / clear rows remotely)
├── verify_db.py            # Connection + user listing check
├── create_admin.py         # Interactive real-admin creation (role_id 3)
├── Dockerfile              # python:3.11-slim, gunicorn 1 worker + 4 threads
├── render.yaml             # Render blueprint (Docker, free plan, /healthz)
├── Procfile / runtime.txt  # Heroku-style hosts
├── requirements.txt        # Pinned dependencies
├── .env.example            # Every env var, documented
├── ca.pem.README           # How to obtain the Aiven CA certificate
├── DEPLOY.md / deploy.txt  # Deployment guides
├── templates/              # Jinja2 templates
├── static/                 # CSS/JS/images (uploads are runtime data, gitignored)
└── generate_findme_pdf.py  # PDF documentation generator (utility)
```

## Documentation

- [`DEPLOY.md`](DEPLOY.md) - full Render + Aiven + Cloudinary guide with troubleshooting
- [`deploy.txt`](deploy.txt) - quick reference (PythonAnywhere alternative included)
- [`ca.pem.README`](ca.pem.README) - obtaining the Aiven CA certificate
- [`.env.example`](.env.example) - every supported environment variable
