# Deploy Workflow Configuration

This document describes how to configure the GitHub Actions deploy workflow for your Oracle Ampere server.

## Prerequisites

1. **Oracle Ampere server** (ARM64, free tier) with Docker and Docker Compose installed
2. **GitHub repository** with GitHub Container Registry enabled (free for public repos, or with free minutes for private)

## Required GitHub Secrets

Go to your GitHub repository → Settings → Secrets and add the following:

### Server Connection
| Secret Name | Description | Example |
|-------------|-------------|---------|
| `SERVER_HOST` | Your server IP or hostname | `123.45.67.890` or `svaes.example.com` |
| `SERVER_USER` | SSH username | `ubuntu` |
| `SERVER_SSH_KEY` | Private SSH key (paste entire key including `-----BEGIN OPENSSH PRIVATE KEY-----`) | See below |

### To generate SSH key:
```bash
ssh-keygen -t ed25519 -C "github-deploy"
# Save to ~/.ssh/github_deploy
# Add the PUBLIC key to ~/.ssh/authorized_keys on your server
```

### Database & Redis
| Secret Name | Description |
|-------------|-------------|
| `POSTGRES_USER` | PostgreSQL username (default: svaes) |
| `POSTGRES_PASSWORD` | PostgreSQL password |
| `REDIS_PASSWORD` | Redis password |

### Security Keys
| Secret Name | Description | How to generate |
|-------------|-------------|-----------------|
| `JWT_SECRET_KEY` | Key for signing JWT tokens | `openssl rand -hex 32` |
| `ENCRYPTION_KEY` | Key for encrypting connector credentials | `openssl rand -hex 32` |
| `ENGINE_API_KEY` | API key for engine communication | `openssl rand -hex 32` |

### Application
| Secret Name | Description | Example |
|-------------|-------------|---------|
| `ALLOWED_ORIGINS` | CORS allowed origins (comma-separated) | `https://svaes.example.com` |
| `APP_BASE_URL` | Base URL of the application | `https://svaes.example.com` |

### SMTP (Email)
| Secret Name | Description |
|-------------|-------------|
| `SMTP_HOST` | SMTP server hostname |
| `SMTP_PORT` | SMTP port (587 for TLS) |
| `SMTP_USER` | SMTP username |
| `SMTP_PASSWORD` | SMTP password |
| `SMTP_FROM` | From email address |

### Admin
| Secret Name | Description | Example |
|-------------|-------------|---------|
| `ADMIN_EMAIL` | Initial admin email | `admin@svaes.example.com` |
| `ADMIN_PASSWORD` | Initial admin password | `SecurePassword123!` |

## Server Setup

### 1. Install Docker on Oracle Ampere
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y docker.io docker-compose
sudo usermod -aG docker $USER
```

### 2. Create SSL certificates (for HTTPS)
```bash
sudo mkdir -p ~/svaes/certs
# Option A: Let's Encrypt (recommended)
sudo apt install -y certbot
sudo certbot certonly --standalone -d svaes.example.com

# Option B: Self-signed (for testing)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ~/svaes/certs/privkey.pem \
  -out ~/svaes/certs/fullchain.pem
```

### 3. Add SSH public key to server
```bash
cat ~/.ssh/github_deploy.pub >> ~/.ssh/authorized_keys
```

### 4. Open firewall ports
```bash
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS
sudo ufw enable
```

## Running the Deployment

1. Go to your GitHub repository
2. Click on **Actions** tab
3. Select **Deploy to Server** workflow
4. Click **Run workflow**
5. Choose:
   - **Environment**: `production` (or `staging`)
   - **Force rebuild**: `false` (set to `true` if you need to force rebuild images)
   - **Skip migration**: `false` (set to `true` if you don't want to run DB migrations)

## Monitoring

After deployment, check services on your server:
```bash
ssh ubuntu@your-server
cd ~/svaes/production
docker compose ps
docker compose logs -f api
docker compose logs -f web
```

## Troubleshooting

### Images fail to pull on server
Make sure you've logged into ghcr.io on the server:
```bash
ssh ubuntu@your-server
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
```

### Database migration fails
Run manually:
```bash
cd ~/svaes/production
docker compose run --rm api python -m alembic upgrade head
```

### SSL Certificate issues
Check that certificates exist and are valid:
```bash
ls -la ~/svaes/production/certs/
openssl x509 -in ~/svaes/production/certs/fullchain.pem -text -noout | grep Subject
```
