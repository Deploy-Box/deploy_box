#!/bin/bash

# Update package manager
sudo dnf update -y

# Install Docker/Moby
sudo dnf install -y moby-engine moby-cli
sudo systemctl start docker
sudo systemctl enable docker

# Create application directory
sudo mkdir -p /opt/app

sudo curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Download application files
curl -L -o /opt/app/main.zip https://github.com/Deploy-Box/Redis/archive/refs/heads/main.zip

# Unzip application files
sudo dnf install -y unzip
sudo unzip /opt/app/main.zip -d /opt/app

# Create systemd service file for docker-compose
cat <<'SERVICE' | sudo tee /etc/systemd/system/docker-compose.service
[Unit]
Description=Docker Compose Application Service
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/app/Redis-main

# Pull images and start the stack
ExecStart=/usr/local/bin/docker-compose up -d

# Stop the stack
ExecStop=/usr/local/bin/docker-compose down

# Restart containers if they exit
ExecReload=/usr/local/bin/docker-compose restart

TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
SERVICE

# Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable docker-compose.service
sudo systemctl start docker-compose.service