#!/bin/bash
# ==============================================================================
# Mail_pot 1-Click AWS EC2 Setup Script
# ==============================================================================
# Run this script on your new Ubuntu EC2 server to automatically deploy Mail_pot.
# Usage: 
#   chmod +x aws_setup.sh
#   sudo ./aws_setup.sh
# ==============================================================================

set -e

echo "🚀 Starting Mail_pot AWS Setup..."

# 1. Update and install dependencies
echo "📦 Installing system dependencies..."
apt update && apt upgrade -y
apt install -y python3-venv python3-pip nginx git curl

# 2. Setup Python Virtual Environment
echo "🐍 Setting up Python environment..."
cd /home/ubuntu/Mail_pot || cd /root/Mail_pot || { echo "❌ Could not find Mail_pot directory. Please run this script from inside the Mail_pot folder."; exit 1; }

# Create venv if it doesn't exist
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Install python requirements
echo "📚 Installing Python packages..."
source venv/bin/activate
pip install -r requirements.txt
deactivate

# 3. Setup Systemd Service
echo "⚙️ Configuring Systemd for Mail_pot..."
cat > /etc/systemd/system/mailpot.service << 'EOF'
[Unit]
Description=Mail_pot FastAPI Backend
After=network.target

[Service]
User=root
WorkingDirectory=/home/ubuntu/Mail_pot
Environment="PATH=/home/ubuntu/Mail_pot/venv/bin"
ExecStart=/home/ubuntu/Mail_pot/venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Note: Adjust the User and WorkingDirectory if you cloned to /root instead of /home/ubuntu
if [ "$PWD" == "/root/Mail_pot" ]; then
    sed -i 's/\/home\/ubuntu/\/root/g' /etc/systemd/system/mailpot.service
fi

systemctl daemon-reload
systemctl enable mailpot
systemctl restart mailpot

# 4. Setup Nginx
echo "🌐 Configuring Nginx Web Server..."
cat > /etc/nginx/sites-available/mailpot << 'EOF'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# Enable site and remove default
ln -sf /etc/nginx/sites-available/mailpot /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

systemctl restart nginx

echo "✅ ================================================================="
echo "✅ Mail_pot setup complete!"
echo "✅ The application should now be accessible via your EC2 Public IP."
echo "✅ Don't forget to create your .env file in $PWD before testing!"
echo "✅ You can use: nano .env"
echo "✅ ================================================================="
