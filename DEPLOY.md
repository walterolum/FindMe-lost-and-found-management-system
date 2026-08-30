# FindMe - Hosting Guide (Compatible Hosting Websites)

FindMe is a **Flask + MySQL** app (with `pymysql` pure-python fallback, `gunicorn` + `whitenoise` for production). Any host that supports **Python 3.11 + MySQL** works. Below are **1-click / free-tier** options tested.

## Quick Compatibility Matrix

| Host | Free Tier | MySQL Support | Deploy Method | Recommended For |
|------|-----------|---------------|---------------|-----------------|
| **PythonAnywhere** | Yes (1 web app) | Built-in MySQL (free) | Manual + WSGI | Easiest for this stack, no Docker needed |
| **Render** | Yes (750h) | External MySQL (PlanetScale/Aiven/Railway) | `render.yaml` + `Procfile` | Free HTTPS, auto deploys from GitHub |
| **Railway** | $5 free credit | Native MySQL plugin | `railway.json` + `Procfile`/`Dockerfile` | Fastest container deploy, 1-click MySQL |
| **Fly.io** | Free allowance | External MySQL | `Dockerfile` | Global edge |
| **DigitalOcean App Platform** | $5 | Managed MySQL | `Dockerfile`/`Procfile` | Production |
| **Heroku** | Paid | ClearDB/JawsDB | `Procfile` | Legacy |
| **Vercel/Netlify** | — | Not compatible | — | Static only, not for Flask+MySQL |

> **Repo now includes:** `Procfile`, `runtime.txt`, `render.yaml`, `railway.json`, `nixpacks.toml`, `Dockerfile`, `docker-compose.yml`, `.env.example`, `wsgi.py` (with `pymysql.install_as_MySQLdb()` + WhiteNoise), `config.py` (handles `DATABASE_URL`/`MYSQL_URL`), `/health` endpoint.

---

## 1) PythonAnywhere (Recommended - 100% Compatible)

This repo's `deploy.txt` covers it. Free MySQL included.

1. Sign up at https://www.pythonanywhere.com
2. Bash console:
   ```bash
   git clone https://github.com/walterolum/FindMe-lost-and-found-management-system.git
   cd FindMe-lost-and-found-management-system
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   mkdir -p static/uploads/{avatars,lost,found}
   ```
3. **Databases** tab -> Create MySQL DB `yourusername$findme_db` (note host `yourusername.mysql.pythonanywhere-services.com`)
   ```sql
   CREATE DATABASE yourusername$findme_db;
   USE yourusername$findme_db;
   SOURCE /home/yourusername/FindMe-lost-and-found-management-system/schema.sql;
   SOURCE /home/yourusername/FindMe-lost-and-found-management-system/seed.sql;
   ```
   Or `python init_db.py` after setting env.
4. Set env vars in `.env` or **Web** tab -> **WSGI file** edit (or via `config.py` env):
   ```bash
   SECRET_KEY=random-32-char
   MYSQL_HOST=yourusername.mysql.pythonanywhere-services.com
   MYSQL_USER=yourusername
   MYSQL_PASSWORD=your-mysql-pass
   MYSQL_DB=yourusername$findme_db
   ```
5. **Web** tab -> Add web app -> **Manual** -> Python 3.11 -> set:
   - Source: `/home/yourusername/FindMe-lost-and-found-management-system`
   - Working dir: same
   - WSGI: `/home/yourusername/FindMe-lost-and-found-management-system/wsgi.py`
   - Virtualenv: `/home/yourusername/FindMe-lost-and-found-management-system/venv`
   - Static: `/static/` -> `/home/.../static/` and `/uploads/` -> `/home/.../static/uploads/`
6. **Reload** -> live at `https://yourusername.pythonanywhere.com` -> check `/health` returns `{"status":"ok"}`.

Admin login: `admin@cavendish.ac.ug` / `password123`

---

## 2) Render (Free via render.yaml)

Render auto-reads `render.yaml`. Needs external MySQL (free options: PlanetScale, Aiven, TiDB Cloud, Railway MySQL).

1. Create MySQL on **PlanetScale** (or Aiven free) -> copy connection string `mysql://user:pass@host:3306/db`
2. In **Render** dashboard: **New +** -> **Blueprint** -> connect `walterolum/FindMe-lost-and-found-management-system` -> it detects `render.yaml`
3. Add env var **DATABASE_URL** (or `MYSQL_HOST`/`USER`/`PASSWORD`/`DB`) in Render Environment
4. After first deploy, load schema:
   ```bash
   mysql -h $MYSQL_HOST -u $MYSQL_USER -p$MYSQL_PASSWORD $MYSQL_DB < schema.sql
   mysql -h $MYSQL_HOST -u $MYSQL_USER -p$MYSQL_PASSWORD $MYSQL_DB < seed.sql
   ```
   Or use Render Shell: `python init_db.py`
5. Deploy -> live at `https://findme.onrender.com` -> `/health` check.

**One-click button** (add to README):
```md
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/walterolum/FindMe-lost-and-found-management-system)
```

---

## 3) Railway (MySQL Plugin + Fastest)

1. At https://railway.app -> **New Project** -> **Deploy from GitHub** -> `FindMe-lost-and-found-management-system`
2. **Add MySQL** plugin -> Railway injects `DATABASE_URL` (we auto-parse) or `MYSQL_*` vars
3. In service **Variables**, ensure:
   ```
   SECRET_KEY=generate-random
   MYSQL_DB=findme_db  # or rely on DATABASE_URL
   FLASK_ENV=production
   ```
4. Railway uses `railway.json` + `nixpacks.toml` -> `gunicorn wsgi:application` auto
5. After deploy, run in Railway console:
   ```bash
   python init_db.py
   ```
   Or `mysql < schema.sql` via `railway run mysql ...`
6. **Deploy** -> public URL generated -> `/health` verify.

**CLI alternative:**
```bash
npm i -g @railway/cli
railway login
railway init
railway add --database mysql
railway up
```

---

## 4) Docker (Any host: Fly.io, DigitalOcean, AWS, Azure, local)

```bash
docker-compose up --build
# loads schema/seed automatically via volumes
# app at http://localhost:5000, db at localhost:3306
```

**Fly.io:**
```bash
fly launch --dockerfile Dockerfile
fly secrets set SECRET_KEY=... MYSQL_HOST=... MYSQL_USER=... MYSQL_PASSWORD=... MYSQL_DB=findme_db
fly deploy
```

**DigitalOcean App Platform:** Connect GitHub repo -> autodetects `Dockerfile` -> add MySQL managed DB -> set env vars.

---

## 5) Heroku (Procfile)

```bash
heroku create findme-cu
heroku addons:create jawsdb:kitefin  # or cleardb:ignite
heroku config:set SECRET_KEY=$(openssl rand -hex 16)
git push heroku master
heroku run python init_db.py
heroku open
```

---

## Environment Variables

See `.env.example`. Priority:
1. `DATABASE_URL` / `MYSQL_URL` / `JAWSDB_URL` (full URL, auto-parsed)
2. `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DB`

`SECRET_KEY` **must** be set in production.

---

## Verification

After any deploy, test:
```bash
curl https://your-app/health        # -> {"status":"ok"}
curl https://your-app/              # -> landing page
# Login admin@cavendish.ac.ug / password123 -> /admin/dashboard
```

Repo: https://github.com/walterolum/FindMe-lost-and-found-management-system

