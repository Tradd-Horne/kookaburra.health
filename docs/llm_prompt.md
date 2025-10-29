# LLM Build Prompt — Django Template

This file contains the **exact prompt** to give an advanced Large Language Model (LLM) such as Claude, ChatGPT, or similar in order to **generate and maintain this Django project template**.

The prompt describes:
- ✅ Required stack and dependencies (Django, Python, PostgreSQL, Docker, Nginx, HTTPS)
- ✅ Settings structure (`base.py`, `dev.py`, `prod.py`)
- ✅ User authentication (custom `AbstractUser` model)
- ✅ Django REST Framework configuration
- ✅ Static/media handling
- ✅ Deployment setup for DigitalOcean with HTTPS (Let’s Encrypt)
- ✅ Logging, backups, and security baseline
- ✅ Developer workflow expectations

---

## Prompt

You are an elite full-stack developer with deep expertise in **Django, Python, Docker, PostgreSQL, Nginx, and DigitalOcean**.

Your task is to **generate a reusable Django project template** named **`django-template`** that is production-ready, secure, and fast to deploy.

### Requirements
- **Python & Django:** Latest stable LTS.
- **Databases:** Separate **PostgreSQL** instances for **development** and **production** (dev must use persistent Docker volumes).
- **Environment management:** `.env.dev`, `.env.prod`, and `.env.example`.
- **Settings split:** `config/settings/{base.py, dev.py, prod.py}`.
- **Users app:** Custom user model extending `AbstractUser` (minimal: `username`, `email`, `password`, `first_name`, `last_name`, `is_staff`, `is_superuser`, timestamps, groups/permissions). Provide ready-to-use signup/login/password-reset views & templates.
- **Django REST Framework:** Installed & preconfigured (JSON renderer, pagination, Spectacular schema, Swagger UI at `/api/docs/`). Include a minimal `GET /api/health/ -> {"status":"ok"}` endpoint.
- **Static & media:** Whitenoise in dev; Nginx serves `/static/` and `/media/` in prod. Ensure `collectstatic` is wired into prod startup.
- **Deployment:** Manual first (no CI/CD). Dockerized with `Dockerfile`, `docker-compose.dev.yml`, `docker-compose.prod.yml`.
- **Production stack:** `gunicorn + nginx + certbot` for HTTPS on domain **`flowtels.com`**.
- **Security:** HSTS, `SECURE_SSL_REDIRECT`, secure cookies, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`.
- **HTTPS:** Let’s Encrypt via Certbot (Docker) with webroot, auto-renew + Nginx reload.
- **Logging:** Docker-friendly stdout logs (Django & Gunicorn), sensible prod logging config.
- **Backups:** `scripts/backup_db.sh` and `scripts/restore_db.sh` using `pg_dump`/`psql`.
- **Developer workflow:** Pushing code requires only:
git add .
git commit -m "message"
git push origin main

- **Docs:** `README.md` covering quick start (dev/prod), env vars, auth URLs, API docs, backup/restore, common issues.

### Tech Details
- **Domain:** `flowtels.com`
- **Postgres:** `15`
- **Dev DB:** persistent Docker volume
- **WSGI:** Gunicorn in prod
- **Assets size:** static/media < 0.5 GB
- **Deployment target:** DigitalOcean droplet (manual)

### Deliverables (must be complete and copy-paste ready)
1. **Directory tree** of the final template.
2. **All key files in full**: 
 - `Dockerfile`, `docker-compose.dev.yml`, `docker-compose.prod.yml`
 - Nginx config (`compose/prod/nginx/nginx.conf`) and Certbot wiring
 - `config/settings/{base.py, dev.py, prod.py}`, `config/urls.py`, `config/wsgi.py`
 - `apps/users/` (models, admin, urls, views, forms), `templates/registration/` (auth screens)
 - `api/` (`urls.py`, `health.py`)
 - `scripts/` (`wait-for-db.sh`, `entrypoint.sh` if used, backup/restore scripts)
 - `requirements/{base.txt, dev.txt, prod.txt}`
 - `.env.example`, `.gitignore`, `README.md`, `LICENSE`, optional `Makefile`
3. **Deployment steps** for DigitalOcean:
 - Create droplet, SSH hardening, install Docker & compose plugin, clone repo, create `.env.prod`, run `docker compose -f docker-compose.prod.yml up -d --build`.
 - First-time cert obtain & renewals instructions.
4. **Dev quick start** with `docker compose -f docker-compose.dev.yml up` and initial migrations/superuser.
5. **Security checklist** (HSTS, cookies, `ALLOWED_HOSTS`, secrets not committed).

### Build Steps (execute in this exact order)
1. Initialize repo & meta (`.gitignore`, `README`, `LICENSE`, optional `Makefile`).
2. Create `requirements/`:
 - `base.txt`: django, psycopg2-binary, gunicorn, whitenoise, python-dotenv, django-environ, djangorestframework, drf-spectacular
 - `dev.txt`: django-debug-toolbar, pytest, pytest-django, factory-boy
 - `prod.txt`: sentry-sdk (optional), whitenoise
3. Scaffold project:
django-template/
│─ compose/
│ ├─ dev/
│ └─ prod/
│ ├─ nginx/nginx.conf
│ └─ certbot/
│─ config/settings/{base.py,dev.py,prod.py}
│─ config/{urls.py,wsgi.py}
│─ apps/users/{models.py,admin.py,urls.py,views.py,forms.py}
│─ api/{urls.py,health.py}
│─ templates/registration/ (login, signup, password reset)
│─ static/
│─ media/
│─ scripts/{wait-for-db.sh,backup_db.sh,restore_db.sh}
│─ Dockerfile
│─ docker-compose.dev.yml
│─ docker-compose.prod.yml
│─ manage.py
│─ .env.example

4. Env config: fill `.env.example` with all required keys; document `.env.dev` and `.env.prod` creation.
5. Settings split: `base` (apps/middleware/db/auth/static/DRF/Spectacular), `dev` (DEBUG, toolbar, console email), `prod` (security, hosts, logging, SSL redirects).
6. Users app: `AbstractUser`, admin registration, auth URLs, templates for login/logout/signup/password reset.
7. DRF: install, defaults, schema at `/api/schema/`, Swagger at `/api/docs/`, `GET /api/health/`.
8. Static/media: Whitenoise (dev), Nginx (prod), ensure `collectstatic` runs in prod build/startup.
9. Docker:
- `Dockerfile` (multi-stage, non-root user)
- `docker-compose.dev.yml` (web + postgres with **persistent volume**)
- `docker-compose.prod.yml` (web + postgres + nginx + certbot; volumes for static/media/nginx/letsencrypt/pgdata)
10. Nginx (prod): `server_name flowtels.com www.flowtels.com;` HTTP→HTTPS redirect; HTTPS with cert paths; routes for `/static/`, `/media/`, and proxy to Gunicorn.
11. HTTPS: Certbot webroot, first-issue command, auto-renew with reload hook.
12. DB: separate env vars & volumes for dev/prod; add backup/restore scripts.
13. Security: HSTS, cookie security, `ALLOWED_HOSTS`, CSRF trusted origins, strong `SECRET_KEY`.
14. Logging: Django & Gunicorn to stdout.
15. Migrations/superuser instructions; optional `entrypoint.sh` to run migrate & collectstatic on start.
16. Tests: minimal pytest config + sample tests (health endpoint, user model).
17. README: dev/prod quick starts, env vars, auth URLs, API docs, backup/restore, common issues.

### Constraints (important)
- Do **not** include secrets. Use env vars everywhere.
- Prefer **explicit versions** in `requirements` where reasonable.
- Output **complete file contents** (no “…” omissions).
- Use **POSIX-compatible** shell scripts.
- Avoid distro-specific instructions beyond Ubuntu LTS for the droplet.
- If something is ambiguous, choose the **safest, most common** default.

### Validation
- After generation, the project should:
1) `docker compose -f docker-compose.dev.yml up` → site runs at `http://localhost:8000`.
2) `python manage.py migrate` and `createsuperuser` succeed.
3) `GET /api/health/` returns `{"status":"ok"}`.
4) Production compose builds and serves app behind Nginx; HTTPS issues successfully for `flowtels.com`.