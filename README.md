# Django Template - Currently set up as: Flowtels.com

To get started:
  1. Copy .env.example to .env.dev
  2. Run make dev or docker compose -f docker-compose.dev.yml up --build
  3. Run migrations: make migrate
  4. Create a superuser: make superuser
  5. Access the site at http://localhost:8000

A production-ready Django project template with Docker, PostgreSQL, Nginx, and HTTPS support.

## Features

- 🐍 Django 5.0+ with custom user model
- 🐳 Fully Dockerized development and production environments
- 🗄️ PostgreSQL with persistent volumes
- 🔐 HTTPS with Let's Encrypt (production)
- 🚀 Nginx + Gunicorn for production
- 📦 Django REST Framework with API documentation
- 🎨 Static files handling with WhiteNoise
- 🔑 Environment-based configuration
- 📝 User authentication (signup, login, password reset)
- 🧪 Testing with pytest
- 💾 Database backup/restore scripts

## Quick Start - Development

1. Clone the repository:
```bash
git clone <repository-url>
cd flowtels.com
```

2. Create development environment file:
```bash
cp .env.example .env.dev
# Edit .env.dev with your settings
```

3. Start the development environment:
```bash
make dev
# or
docker compose -f docker-compose.dev.yml up --build
```

4. Run migrations and create superuser:
```bash
make migrate
make superuser
```

5. Access the application:
- Application: http://localhost:8000
- Admin: http://localhost:8000/admin/
- API Documentation: http://localhost:8000/api/docs/

## Quick Start - Production

1. Set up your DigitalOcean droplet:
```bash
# SSH into your droplet
ssh root@your-droplet-ip

# Update system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
apt install docker-compose-plugin

# Create non-root user (recommended)
adduser deploy
usermod -aG docker deploy
su - deploy
```

2. Clone and configure:
```bash
git clone <repository-url>
cd flowtels.com

# Create production environment file
cp .env.example .env.prod
# Edit .env.prod with production values
```

3. Deploy:
```bash
make prod
# or
docker compose -f docker-compose.prod.yml up -d --build
```

4. Obtain SSL certificate (first time):
```bash
# Create certificate
docker compose -f docker-compose.prod.yml exec certbot certbot certonly \
  --webroot --webroot-path=/var/www/certbot \
  -d flowtels.com -d www.flowtels.com \
  --email your-email@example.com \
  --agree-tos --no-eff-email

# Restart nginx to load certificate
docker compose -f docker-compose.prod.yml restart nginx
```

5. Set up auto-renewal:
```bash
# Add to crontab
crontab -e
# Add this line:
0 12 * * * cd /path/to/flowtels.com && docker compose -f docker-compose.prod.yml exec certbot certbot renew --quiet && docker compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

## Environment Variables

Copy `.env.example` to `.env.dev` or `.env.prod` and configure:

```env
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True  # False for production
ALLOWED_HOSTS=localhost,127.0.0.1  # flowtels.com,www.flowtels.com for production

# Database
POSTGRES_DB=flowtels_db
POSTGRES_USER=flowtels_user
POSTGRES_PASSWORD=secure-password
DATABASE_URL=postgresql://flowtels_user:secure-password@db:5432/flowtels_db

# Email (optional)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Domain (production)
DOMAIN_NAME=flowtels.com
```

## Authentication URLs

- Login: `/accounts/login/`
- Logout: `/accounts/logout/`
- Signup: `/accounts/signup/`
- Password Reset: `/accounts/password/reset/`
- Password Change: `/accounts/password/change/`

## API Endpoints

- Health Check: `GET /api/health/`
- API Documentation: `/api/docs/`
- API Schema: `/api/schema/`

## Database Backup & Restore

### Backup
```bash
make backup
# or
./scripts/backup_db.sh
```

Backups are stored in `backups/` directory.

### Restore
```bash
make restore BACKUP_FILE=backups/backup_20240115_120000.sql
# or
./scripts/restore_db.sh backups/backup_20240115_120000.sql
```

## Development Commands

```bash
# Start development server
make dev

# Run migrations
make migrate

# Create migrations
make makemigrations

# Create superuser
make superuser

# Run tests
make test

# Open Django shell
make shell

# View logs
make logs

# Stop containers
make dev-down
```

## Production Commands

```bash
# Deploy
make prod

# Run migrations
make migrate-prod

# Create superuser
make superuser-prod

# View logs
make logs-prod

# Stop containers
make prod-down
```

## Common Issues

### Permission denied errors
- Ensure Docker daemon is running
- Add user to docker group: `sudo usermod -aG docker $USER`
- Logout and login again

### Database connection errors
- Check DATABASE_URL in environment file
- Ensure database container is running: `docker compose ps`
- Wait for database to be ready (handled automatically by wait-for-db.sh)

### Static files not loading in production
- Run collectstatic: `make collectstatic-prod`
- Check Nginx configuration
- Verify static files volume mapping

### HTTPS issues
- Ensure domain DNS points to server
- Check Certbot logs: `docker compose -f docker-compose.prod.yml logs certbot`
- Verify Nginx SSL configuration

## Security Checklist

- [ ] Change SECRET_KEY in production
- [ ] Set DEBUG=False in production
- [ ] Configure ALLOWED_HOSTS with your domain
- [ ] Use strong database passwords
- [ ] Enable HTTPS in production
- [ ] Set secure cookie settings
- [ ] Configure CSRF_TRUSTED_ORIGINS
- [ ] Regular security updates

## Project Structure

```
flowtels.com/
├── compose/
│   ├── dev/
│   └── prod/
│       ├── nginx/
│       └── certbot/
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── prod.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   └── users/
├── api/
├── templates/
├── static/
├── media/
├── scripts/
├── requirements/
├── docker-compose.dev.yml
├── docker-compose.prod.yml
├── Dockerfile
├── manage.py
└── README.md
```

## License

MIT License - see LICENSE file for details.


## Development 
 # In your terminal, press Ctrl+C to stop the current server
  # Then run again:
  docker compose -f docker-compose.dev.yml up

  Or just access the site at: http://localhost:8000

  Then you can access:
  - Home page: http://localhost:8000
  - Admin panel: http://localhost:8000/admin/
  - API docs: http://localhost:8000/api/docs/