#!/usr/bin/env bash
# ==============================================================================
# Mobile World Sales & Service — Linux VPS Production Deployment Script
# Compatible with Ubuntu 22.04 / 24.04 LTS & Debian 12
# ==============================================================================

set -euo pipefail

APP_DIR="/var/www/mobileworld"
REPO_URL="https://github.com/aayash317-svg/mobile-world.git"
SERVICE_NAME="mobileworld"
USER_NAME="www-data"

echo "============================================================"
echo "🚀 Deploying Mobile World Sales & Service to Linux VPS..."
echo "============================================================"

# 1. Update OS Packages & Install Prerequisites
echo "📦 [1/6] Installing OS dependencies (Python, Nginx, Git)..."
sudo apt-get update -y
sudo apt-get install -y python3 python3-pip python3-venv git nginx certbot python3-certbot-nginx curl ufw

# 2. Setup Application Directory
echo "📂 [2/6] Setting up project directory at ${APP_DIR}..."
sudo mkdir -p ${APP_DIR}
sudo chown -R $USER:${USER} ${APP_DIR}

if [ ! -d "${APP_DIR}/.git" ]; then
    echo "Cloning repository from GitHub..."
    git clone ${REPO_URL} ${APP_DIR}
else
    echo "Updating existing repository..."
    cd ${APP_DIR}
    git pull origin main
fi

cd ${APP_DIR}

# 3. Setup Python Virtual Environment
echo "🐍 [3/6] Configuring Python virtual environment & dependencies..."
if [ ! -d "${APP_DIR}/.venv" ]; then
    python3 -m venv ${APP_DIR}/.venv
fi

${APP_DIR}/.venv/bin/pip install --upgrade pip
${APP_DIR}/.venv/bin/pip install -r requirements.txt

# 4. Configure Production Environment Variables (.env)
if [ ! -f "${APP_DIR}/.env" ]; then
    echo "📝 [4/6] Initializing default production .env..."
    SECRET_KEY_GEN=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    cat <<EOF > "${APP_DIR}/.env"
# Application Settings
SECRET_KEY=${SECRET_KEY_GEN}
ADMIN_USERNAME=admin
ADMIN_PASSWORD=MobileWorld@2026
FLAT_DELIVERY_FEE=50.00
PORT=5000
DEBUG=False

# Database Configuration (Defaults to SQLite for instant plug-and-play; set to mysql if using local MySQL)
DB_TYPE=sqlite
EOF
    echo "Created ${APP_DIR}/.env (you can update DB_TYPE and credentials anytime)"
fi

# 5. Create Systemd Service for Gunicorn
echo "⚙️ [5/6] Creating Systemd Service (/etc/systemd/system/${SERVICE_NAME}.service)..."
sudo bash -c "cat <<EOF > /etc/systemd/system/${SERVICE_NAME}.service
[Unit]
Description=Mobile World Sales & Service Flask/Gunicorn Application
After=network.target

[Service]
User=root
WorkingDirectory=${APP_DIR}
Environment=\"PATH=${APP_DIR}/.venv/bin\"
ExecStart=${APP_DIR}/.venv/bin/gunicorn --workers 3 --threads 2 --bind 127.0.0.1:5000 --timeout 120 --access-logfile - --error-logfile - \"app:app\"
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF"

sudo systemctl daemon-reload
sudo systemctl enable ${SERVICE_NAME}
sudo systemctl restart ${SERVICE_NAME}

# 6. Configure Nginx Reverse Proxy
echo "🌐 [6/6] Configuring Nginx reverse proxy..."
sudo bash -c "cat <<EOF > /etc/nginx/sites-available/${SERVICE_NAME}
server {
    listen 80;
    server_name _;

    client_max_body_size 32M;

    location /static/ {
        alias ${APP_DIR}/static/;
        expires 30d;
        add_header Cache-Control \"public, no-transform\";
    }

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \\\$host;
        proxy_set_header X-Real-IP \\\$remote_addr;
        proxy_set_header X-Forwarded-For \\\$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \\\$scheme;
        proxy_read_timeout 120s;
    }
}
EOF"

sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf /etc/nginx/sites-available/${SERVICE_NAME} /etc/nginx/sites-enabled/${SERVICE_NAME}
sudo nginx -t
sudo systemctl restart nginx

# Configure Firewall
if sudo ufw status | grep -q "Status: active"; then
    sudo ufw allow 'Nginx Full'
    sudo ufw allow OpenSSH
fi

SERVER_IP=\$(curl -s https://ifconfig.me || hostname -I | awk '{print \$1}')

echo ""
echo "============================================================"
echo "🎉 DEPLOYMENT COMPLETE!"
echo "============================================================"
echo "Public Storefront: http://${SERVER_IP}/"
echo "Admin Portal:      http://${SERVER_IP}/admin/login"
echo ""
echo "🔑 Owner Credentials:"
echo "   Username: admin"
echo "   Password: MobileWorld@2026"
echo "   Demo 2FA: 0000"
echo ""
echo "🔒 To attach a custom domain & Free SSL certificate:"
echo "   1. Point your domain DNS (A Record) to ${SERVER_IP}"
echo "   2. Run: sudo certbot --nginx -d yourdomain.com"
echo "============================================================"
