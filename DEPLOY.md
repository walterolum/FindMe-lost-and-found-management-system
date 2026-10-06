# FindMe Deployment Guide (Render + Aiven + Cloudinary)

Free deployment: **Render** (Docker web service) + **Aiven for MySQL** (free, SSL) + **Cloudinary** (images - Render's disk is ephemeral).

For the full beginner-friendly walkthrough see [`README.md`](README.md) → "Deploy to Render + Aiven + Cloudinary".

## Prerequisites
- GitHub account with the FindMe repository
- Aiven account (free tier)
- Cloudinary account (free tier)
- Render account (free tier)

## 1. Create Aiven Free MySQL Service

1. Go to [Aiven](https://console.aiven.io/) and create an account
2. Create a new service → Select MySQL → Choose "Free" tier
3. Select your preferred cloud region
4. Create the service (may take a few minutes)
5. Note the connection details:
   - Host (e.g. `findme-xxxx.aivencloud.com`), Port `3306`, User `avnadmin`, Password, Database `defaultdb`
6. Download the **CA certificate** (Overview page → "Access" section → CA Certificate) and save it in the project root as **`ca.pem`** (see [`ca.pem.README`](ca.pem.README)). The certificate is public - it can be committed to the repo.

## 2. Initialize the Database on Aiven

The Aiven free user **cannot CREATE DATABASE** - use the existing `defaultdb`. `init_db.py` detects a remote host and skips database creation automatically:

```bash
export MYSQL_HOST=your-host.aivencloud.com
export MYSQL_PORT=3306
export MYSQL_USER=avnadmin
export MYSQL_PASSWORD=your-password
export MYSQL_DB=defaultdb
export MYSQL_SSL_CA=ca.pem
python init_db.py
```

This runs `schema.sql` (all tables are `IF NOT EXISTS`) and `seed.sql` (`INSERT IGNORE` - safe to re-run).

**Existing database?** Widen the image columns once:
```bash
mysql -h your-host.aivencloud.com -u avnadmin -p --ssl-ca=ca.pem defaultdb < migration_widen_image_paths.sql
```

**Create a real admin** (never use the demo password in production):
```bash
python create_admin.py
```

## 3. Create Cloudinary Account

1. Go to [Cloudinary](https://cloudinary.com/) and create a free account
2. From your Dashboard get: **Cloud Name**, **API Key**, **API Secret**
3. These become `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`

Images are processed with Pillow (thumbnail 1200px, RGB, quality 85) and uploaded to Cloudinary. The DB keeps the original path style (`lost/<hex>.jpg`); `/uploads/<path>` 302-redirects to the Cloudinary delivery URL.

## 4. Push Code to GitHub

```bash
git add .
git commit -m "Prepare for Render+Aiven+Cloudinary deployment"
git push origin main
```

## 5. Deploy to Render

1. Go to [Render](https://render.com/) → **New** → **Web Service** → connect the GitHub repo
2. Render reads [`render.yaml`](render.yaml) automatically (Docker runtime, free plan, health check `/healthz`)
3. In **Dashboard → Environment** set the `sync: false` variables:

| Variable | Value | Notes |
|---|---|---|
| SECRET_KEY | strong random string | `python -c "import secrets; print(secrets.token_hex(32))"` |
| MYSQL_HOST | your-host.aivencloud.com | From Aiven |
| MYSQL_USER | avnadmin | From Aiven |
| MYSQL_PASSWORD | your-password | From Aiven |
| CLOUDINARY_CLOUD_NAME | your-cloud-name | From Cloudinary |
| CLOUDINARY_API_KEY | your-api-key | From Cloudinary |
| CLOUDINARY_API_SECRET | your-api-secret | From Cloudinary |

Already set by render.yaml (no action needed): `FINDME_ENV=production`, `MYSQL_DB=defaultdb`, `MYSQL_SSL_CA=ca.pem`, `MYSQL_PORT=3306`.

4. Deploy - the app **fails loudly at startup** if required values are missing (check the logs for the exact variable name).
5. Render gives you a public URL (e.g. `https://findme-xxx.onrender.com`).

Start command (in the Dockerfile): `gunicorn wsgi:app --workers 1 --threads 4 --timeout 120 --bind 0.0.0.0:${PORT:-10000}` - one worker on purpose so the AI-matcher background threads share one process.

## 6. Test Checklist

After deployment:
- [ ] `/healthz` returns `ok` (200 OK) and `/health` returns `{"status":"ok","service":"FindMe"}`
- [ ] Register a new account
- [ ] Login successfully
- [ ] Report a lost item with an image (uploaded to Cloudinary)
- [ ] Report a found item with an image
- [ ] AI matching runs after item creation (check admin → AI Match Review)
- [ ] Admin approves/rejects matches
- [ ] Notifications appear correctly
- [ ] Profile image upload works (5 MB limit)
- [ ] All pages load without errors

## 7. Troubleshooting

### Cold Start Delay (Free Tier)
- Render free web services spin down after ~15 min idle. First request after idle may take 30-60 seconds. Normal.

### Database Waking Up (Aiven Free)
- Aiven free MySQL may power off after inactivity. The app retries connections (3 attempts, backoff) and each request opens its own connection (closed in teardown) - correct for the free tier.

### SSL Errors
- `MYSQL_SSL_CA=ca.pem` must point to the real Aiven CA file (downloaded, not invented). Local XAMPP needs no CA - SSL is skipped for localhost.

### Missing Environment Variables
- The app refuses to start without a production `SECRET_KEY` and fails loudly on bad DB/Cloudinary settings. Check Render logs.

### Image Upload Issues
- Verify Cloudinary credentials; check the free-tier quota. Images are resized to 1200x1200 and quality-85 optimized before upload.

### CSRF / Session Errors
- All POST forms carry a `csrf_token` (Flask-WTF). If you see "session expired" flashes, just retry the form. Cookies are HttpOnly + SameSite=Lax + Secure in production.

## Notes

- **Ephemeral disk**: production images live on Cloudinary; `static/uploads` is ignored by git (`.gitkeep` keeps the folders).
- **Exports**: office exports (pptx/docx) stream from memory (BytesIO) - nothing written to disk.
- **ProxyFix**: configured so `request.remote_addr`/scheme are correct behind Render's proxy (activity-log IPs).
- **PyMySQL**: used instead of Flask-MySQLdb (pure Python, no C deps needed on free hosts).
- **Local development is unchanged**: with no new env vars, the app uses XAMPP MySQL on localhost and local-disk uploads exactly as before.
