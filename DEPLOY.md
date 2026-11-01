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

This runs `schema.sql` (all tables are `IF NOT EXISTS`) and `seed.sql` (`INSERT IGNORE` - safe to re-run). Campuses/faculties and the lecturer university email use `INSERT ... ON DUPLICATE KEY UPDATE`, so re-running `seed.sql` syncs names and campus assignments on existing databases too.

**Existing database?** Widen the image columns once:
```bash
mysql -h your-host.aivencloud.com -u avnadmin -p --ssl-ca=ca.pem defaultdb < migration_widen_image_paths.sql
```

**Role-aware registration (Student ID vs lecturer University Email) and the 4 Cavendish campuses (Main Campus (Siyani), Acacia, Kingsgate, Mukono):** the missing columns/tables (`users.university_email`, `faculties.campus_id`, `campuses`) are created automatically on the first login/register/settings/admin page - the only manual step is re-running the updated `seed.sql` to load the campus rows:
```bash
mysql -h your-host.aivencloud.com -u avnadmin -p --ssl-ca=ca.pem defaultdb < seed.sql
```
Until the seed runs, the faculty dropdown degrades gracefully (groups faculties under "Other Campuses"). Students register with a Student ID; lecturers/staff register with their university email (required).

**Create a real admin** (never use the demo password in production):
```bash
python create_admin.py
```

## 3. Create Cloudinary Account

1. Go to [Cloudinary](https://cloudinary.com/) and create a free account
2. From your Dashboard get: **Cloud Name**, **API Key**, **API Secret**
3. These become `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`

Images are processed with Pillow (EXIF-safe, thumbnail 1200px, white-flattened RGB, quality 85) and stored in MySQL first (`images` table, `LONGBLOB`) - this is what keeps photos alive across Render redeploys. Cloudinary and local disk are best-effort mirrors for the bytes. `/uploads/<path>` serves from the database, then falls back to Cloudinary (pre-existing uploads), then disk.

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
| SMTP_HOST | smtp.gmail.com | Optional - enables live owner emails (match PDF reports) |
| SMTP_PORT | 587 | 587 STARTTLS or 465 SSL |
| SMTP_USER | you@gmail.com | SMTP login (Gmail: use an App Password) |
| SMTP_PASSWORD | app-password | SMTP password |
| SMTP_FROM | you@gmail.com | The From: address shown to owners |

Already set by render.yaml (no action needed): `FINDME_ENV=production`, `MYSQL_DB=defaultdb`, `MYSQL_SSL_CA=ca.pem`, `MYSQL_PORT=3306`.

**Without SMTP**, owner emails fall back to the server log (console mailbox) and match report PDFs stay downloadable: admins get a one-click **"Email PDF to Owner"** button plus **"Download PDF"** on every match, and owners/finder can download the same PDF from the match detail page.

4. Deploy - the app **fails loudly at startup** if required values are missing (check the logs for the exact variable name).
5. Render gives you a public URL (e.g. `https://findme-xxx.onrender.com`).

Start command (in the Dockerfile): `gunicorn wsgi:app --workers 1 --threads 4 --timeout 120 --bind 0.0.0.0:${PORT:-10000}` - one worker on purpose so the AI-matcher background threads share one process.

## 6. Test Checklist

After deployment:
- [ ] `/healthz` returns `ok` (200 OK) and `/health` returns `{"status":"ok","service":"FindMe"}`
- [ ] Register a new account (student: Student ID field; lecturer: University Email field required)
- [ ] Faculty dropdown shows the 4 campus groups (Main Campus (Siyani), Acacia, Kingsgate, Mukono)
- [ ] Dashboard shows the live clock (time, date, greeting)
- [ ] Report a lost/found item with auto-detected GPS location (address chip fills)
- [ ] Login successfully
- [ ] Report a lost item with an image (stored in the DB `images` table)
- [ ] Report a found item with an image
- [ ] AI matching runs after item creation (check admin → AI Match Review)
- [ ] Approving a match emails the match report PDF to the owner (or logs the console email + offers the one-click "Email PDF to Owner" when SMTP is unset)
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

### GPS Auto-Detect (report pages)
The lost/found report forms detect the user's current location with the browser Geolocation API (HTTPS required - true on Render) and attach the reverse-geocoded address (OpenStreetMap Nominatim) plus lat/lng to the report. Users must grant permission; if they deny it or are offline the manual campus-location dropdown keeps working and nothing breaks. Verified reports show the detected address on the item details page and in the match report PDF.

### Match PDF Reports
Approving a match automatically generates a one-page A4 PDF (compare lost vs found items, locations/dates, contacts, owner instructions) and emails it to the owner and finder (best-effort). Admins can also re-send it with one click from AI Match Review or Match Details. PDFs are generated on the fly with `fpdf2` - nothing is stored on disk.
- The app refuses to start without a production `SECRET_KEY` and fails loudly on bad DB/Cloudinary settings. Check Render logs.

### Image Upload Issues
- Images are resized to 1200x1200 and quality-85 optimized, then stored in the `images` table (`LONGBLOB`). If uploads fail, check the Render logs for `Could not store image bytes in the database` (DB connectivity/quota) - the fallback mirror then goes to Cloudinary/disk.
- Verify Cloudinary credentials so the mirror (and pre-database images) keep working; check the free-tier quota.
- Old deployments missing the `images` table are repaired automatically on the first upload/approval; nothing to run by hand.

### CSRF / Session Errors
- All POST forms carry a `csrf_token` (Flask-WTF). If you see "session expired" flashes, just retry the form. Cookies are HttpOnly + SameSite=Lax + Secure in production.

## Notes

- **Ephemeral disk**: production image bytes live in MySQL (`images` table), so redeploys no longer lose photos. Cloudinary remains a mirror and serves images uploaded before this change.
- **Exports**: office exports (pptx/docx) stream from memory (BytesIO) - nothing written to disk.
- **ProxyFix**: configured so `request.remote_addr`/scheme are correct behind Render's proxy (activity-log IPs).
- **PyMySQL**: used instead of Flask-MySQLdb (pure Python, no C deps needed on free hosts).
- **Local development is unchanged**: with no new env vars, the app uses XAMPP MySQL on localhost, and images are additionally mirrored to local disk exactly as before.
- **AI matcher**: identical serial numbers produce a deterministic 100 % match; conflicting serials are hard-rejected. Fuzzy matches need several independent agreeing signals (name, category, colour, brand/model, description, location, date/time, photo perceptual hash, shape) before they are proposed for review.
