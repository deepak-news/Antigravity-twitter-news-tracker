#!/bin/bash
# ------------------------------------------------------------------
# 1-Click Systemd Service Installer for Always-Free Linux VMs
# (e.g. Oracle Cloud Free Tier / GCP e2-micro / Ubuntu / Debian)
# ------------------------------------------------------------------

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
USER="$(whoami)"
SERVICE_FILE="/etc/systemd/system/twitter-tracker.service"

echo "Configuring Twitter News Tracker systemd service for user $USER in $DIR..."

sudo bash -c "cat << EOF > $SERVICE_FILE
[Unit]
Description=24/7 Twitter News Tracker Daemon (Free Forever)
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$DIR
ExecStart=/usr/bin/python3 $DIR/run_daemon.py
Restart=always
RestartSec=10
EnvironmentFile=$DIR/.env

[Install]
WantedBy=multi-user.target
EOF"

sudo systemctl daemon-reload
sudo systemctl enable twitter-tracker.service
sudo systemctl restart twitter-tracker.service

echo "=========================================================="
echo "✅ Twitter News Tracker is now running 24/7 as a system service!"
echo "Check status: sudo systemctl status twitter-tracker.service"
echo "View live logs: sudo journalctl -u twitter-tracker.service -f"
echo "=========================================================="
