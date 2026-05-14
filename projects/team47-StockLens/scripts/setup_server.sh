#!/bin/bash
# One-time EC2 setup script.
# Run once on the server: bash scripts/setup_server.sh
set -e

APP_DIR="/home/ubuntu/AI47"
REPO="https://github.com/soma17th-ai47/AI47.git"

echo "=== [1/6] System packages ==="
sudo apt-get update -y
sudo apt-get install -y curl git nginx

echo "=== [2/6] uv (Python package manager) ==="
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

echo "=== [3/6] Clone repo ==="
if [ -d "$APP_DIR" ]; then
  echo "Repo already exists, pulling latest..."
  cd "$APP_DIR" && git pull
else
  git clone "$REPO" "$APP_DIR"
fi

echo "=== [4/6] Python venv + dependencies ==="
cd "$APP_DIR"
uv venv --python 3.11
uv pip install -r requirements.txt --python .venv/bin/python

echo "=== [5/6] systemd service ==="
sudo tee /etc/systemd/system/ai47.service > /dev/null << 'SERVICE'
[Unit]
Description=AI47 FastAPI Server
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/AI47
EnvironmentFile=/home/ubuntu/AI47/.env
ExecStart=/home/ubuntu/AI47/.venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE

sudo systemctl daemon-reload
sudo systemctl enable ai47
sudo systemctl start ai47
echo "Service status:"
sudo systemctl is-active ai47

echo "=== [6/6] Nginx reverse proxy ==="
sudo tee /etc/nginx/sites-available/ai47 > /dev/null << 'NGINX'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_read_timeout 120s;
    }
}
NGINX

sudo ln -sf /etc/nginx/sites-available/ai47 /etc/nginx/sites-enabled/ai47
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

echo ""
echo "=== Setup complete ==="
echo "API is live at: http://3.34.109.154/health"
echo ""
echo "⚠ Don't forget to create /home/ubuntu/AI47/.env with:"
echo "   UPSTAGE_API_KEY=..."
echo "   NEWSAPI_KEY=..."
echo "   DATABASE_URL=..."
