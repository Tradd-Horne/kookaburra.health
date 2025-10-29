# Rebrand Guide: Django Template Setup

This guide shows you how to clone this Django template and rebrand it for your own project.

## Prerequisites

- Docker installed
- Git installed
- GitHub account
- `git-filter-repo` installed: `brew install git-filter-repo`

## Step-by-Step Instructions

### 1. Clone the Template

```bash
git clone https://github.com/Tradd-Horne/kookaburra.health.git
cd kookaburra.health
```

### 2. Remove Git History & Start Fresh

```bash
# Remove the existing git repository
rm -rf .git

# Initialize a new git repository
git init
git add .
git commit -m "Initial commit from template"
```

### 3. Configure Environment

```bash
# Copy environment template
cp .env.example .env.dev

# The default settings should work for local development
# Database defaults:
# - POSTGRES_DB=kookaburra_db
# - POSTGRES_USER=kookaburra_user
# - POSTGRES_PASSWORD=devpassword
```

### 4. Rebrand the Application

Update these files with your brand name (replace "Your Brand" with your project name):

**Django Settings** - `config/settings/base.py`:
```python
# Line 154-156: Update API documentation
SPECTACULAR_SETTINGS = {
    'TITLE': 'Your Brand API',
    'DESCRIPTION': 'API documentation for Your Brand',
    ...
}

# Line 181: Update default email
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@yourbrand.com')
```

**Environment Files** - `.env.example` and `.env.dev`:
```env
# Update database names
POSTGRES_DB=yourbrand_db
POSTGRES_USER=yourbrand_user
POSTGRES_PASSWORD=devpassword
DATABASE_URL=postgresql://yourbrand_user:devpassword@db:5432/yourbrand_db

# Update domain
DOMAIN_NAME=yourbrand.com

# Update email
DEFAULT_FROM_EMAIL=noreply@yourbrand.com
CSRF_TRUSTED_ORIGINS=https://yourbrand.com,https://www.yourbrand.com
```

**Docker Compose** - `docker-compose.dev.yml`:
```yaml
# Lines 7-13: Update database defaults
environment:
  - POSTGRES_DB=${POSTGRES_DB:-yourbrand_db}
  - POSTGRES_USER=${POSTGRES_USER:-yourbrand_user}
  - POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-devpassword}

healthcheck:
  test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-yourbrand_user} -d ${POSTGRES_DB:-yourbrand_db}"]
```

**Templates** - `templates/base.html`:
```html
<!-- Line 7: Update page title -->
<title>{% block title %}Your Brand{% endblock %}</title>

<!-- Line 151: Update header -->
<h1>Your Brand</h1>

<!-- Line 185: Update footer -->
<p>&copy; {% now "Y" %} Your Brand. All rights reserved.</p>
```

**Landing Page** - `templates/index.html`:
```html
{% block title %}Home - Your Brand{% endblock %}

<!-- Update hero section with your content -->
<div class="hero">
    <h1>Welcome to Your Brand</h1>
    <p>Your tagline here</p>
    ...
</div>

<!-- Update feature cards with your features -->
```

**README.md**:
- Update project name and description
- Update all references to match your brand
- Update domain names in examples

### 5. Test Locally

```bash
# Start Docker containers
docker compose -f docker-compose.dev.yml up --build

# Visit http://localhost:8000 to verify
```

### 6. Remove Any Credentials from Git History

**IMPORTANT**: Before pushing to GitHub, ensure no credential files are tracked:

```bash
# Add credentials to .gitignore (if not already there)
echo "credentials.json" >> .gitignore
echo "service-account.json" >> .gitignore
echo "token.json" >> .gitignore
echo ".env" >> .gitignore
echo ".env.dev" >> .gitignore
echo ".env.prod" >> .gitignore

# Commit the .gitignore changes
git add .gitignore
git commit -m "Update gitignore for credentials"
```

If credentials were accidentally committed:
```bash
# Remove them from history
git filter-repo --path credentials.json --invert-paths --force
git filter-repo --path service-account.json --invert-paths --force
git filter-repo --path token.json --invert-paths --force
```

### 7. Create New GitHub Repository

1. Go to https://github.com/new
2. Name your repository (e.g., `yourbrand-backend`)
3. **Do NOT** initialize with README (you already have one)
4. Click "Create repository"

### 8. Push to GitHub

```bash
# Add your new repository as remote
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git

# Push to GitHub
git push -u origin master
```

### 9. Set Up Production (Optional)

When ready to deploy:

1. Copy `.env.example` to `.env.prod`
2. Update production values (strong passwords, real domain, etc.)
3. Follow production deployment steps in main README

## Common Customizations

### Change Color Scheme

Edit `templates/index.html` - update the gradient colors:
```css
background: linear-gradient(135deg, #YOUR_COLOR1 0%, #YOUR_COLOR2 100%);
```

### Add More Pages

1. Create new template in `templates/`
2. Add view in appropriate app (e.g., `apps/core/views.py`)
3. Add URL route in `config/urls.py`

### Modify Database Schema

1. Edit models in `apps/*/models.py`
2. Create migrations: `docker compose -f docker-compose.dev.yml exec web python manage.py makemigrations`
3. Apply migrations: `docker compose -f docker-compose.dev.yml exec web python manage.py migrate`

## Project Structure Preserved

This template maintains:
- ✅ User authentication system (signup, login, password reset)
- ✅ Custom user model
- ✅ Django REST Framework with API docs
- ✅ PostgreSQL database with Docker
- ✅ Production-ready configuration
- ✅ Nginx + Gunicorn setup for production

## Need Help?

- Check the main [README.md](README.md) for detailed setup instructions
- Review Django settings in `config/settings/`
- Inspect docker-compose files for configuration

## Security Checklist

Before going live:
- [ ] Change `SECRET_KEY` in production
- [ ] Set `DEBUG=False` in production
- [ ] Use strong database passwords
- [ ] Configure `ALLOWED_HOSTS` properly
- [ ] Set up HTTPS/SSL certificates
- [ ] Never commit credential files
- [ ] Review `CSRF_TRUSTED_ORIGINS`
- [ ] Regenerate any exposed API keys

---

**That's it!** You now have a fully rebranded Django application ready to customize further.
