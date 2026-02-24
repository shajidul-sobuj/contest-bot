# Deployment Guide

This guide covers deploying the Contest Reminder Bot to various platforms.

## Prerequisites

1. **Bot Token**: Get your bot token from [@BotFather](https://t.me/BotFather) on Telegram
   - Send `/newbot` to BotFather
   - Follow the prompts to create your bot
   - Save the token provided

2. **Python 3.9+** (for local/VPS deployment)

## Quick Start (Local)

### Linux/Mac
```bash
chmod +x start.sh
export BOT_TOKEN='your_token_here'
./start.sh
```

### Windows
```cmd
set BOT_TOKEN=your_token_here
start.bat
```

## Deployment Options

### 1. Heroku (Free Tier Available)

**Step-by-step:**

1. Create a Heroku account at [heroku.com](https://heroku.com)

2. Install Heroku CLI:
```bash
# Mac
brew install heroku/brew/heroku

# Ubuntu/Debian
curl https://cli-assets.heroku.com/install.sh | sh

# Windows: Download from heroku.com
```

3. Login and create app:
```bash
heroku login
heroku create your-contest-bot
```

4. Set environment variables:
```bash
heroku config:set BOT_TOKEN='your_token_here'
```

5. Deploy:
```bash
git init
git add .
git commit -m "Initial commit"
git push heroku main
```

6. Scale the worker:
```bash
heroku ps:scale worker=1
```

**Note**: Heroku requires a credit card for verification, even on free tier.

---

### 2. Railway (Easiest, Free)

**Step-by-step:**

1. Go to [railway.app](https://railway.app) and sign up with GitHub

2. Click "New Project" → "Deploy from GitHub repo"

3. Select your repository

4. Add environment variable:
   - Key: `BOT_TOKEN`
   - Value: Your bot token

5. Railway will automatically detect and deploy

**Advantages:**
- No credit card required for free tier
- Automatic deployments from GitHub
- Easy to use dashboard

---

### 3. Render (Free Tier)

**Step-by-step:**

1. Sign up at [render.com](https://render.com)

2. Click "New +" → "Background Worker"

3. Connect your GitHub repository

4. Configure:
   - **Name**: contest-reminder-bot
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python bot.py`

5. Add environment variable:
   - Key: `BOT_TOKEN`
   - Value: Your bot token

6. Click "Create Background Worker"

---

### 4. Docker (Any Platform)

**Using Docker Compose:**

1. Create `.env` file:
```bash
BOT_TOKEN=your_token_here
```

2. Run:
```bash
docker-compose up -d
```

**Manual Docker:**
```bash
# Build
docker build -t contest-bot .

# Run
docker run -d --name contest-bot \
  -e BOT_TOKEN='your_token_here' \
  -v $(pwd)/data:/app \
  --restart unless-stopped \
  contest-bot
```

**Advantages:**
- Works on any platform with Docker
- Easy to update and rollback
- Isolated environment

---

### 5. VPS/Server (Ubuntu/Debian)

**Step-by-step:**

1. SSH into your server:
```bash
ssh user@your-server-ip
```

2. Install Python and dependencies:
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv git -y
```

3. Clone repository:
```bash
git clone <your-repo-url>
cd contest-reminder-bot
```

4. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

5. Set environment variable:
```bash
export BOT_TOKEN='your_token_here'
```

6. **Option A**: Run with screen (simple):
```bash
screen -S contest-bot
python bot.py
# Press Ctrl+A then D to detach
```

7. **Option B**: Run as systemd service (recommended):

Create service file:
```bash
sudo nano /etc/systemd/system/contest-bot.service
```

Paste this (update paths and token):
```ini
[Unit]
Description=Contest Reminder Telegram Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/bot/directory
Environment="BOT_TOKEN=your_bot_token_here"
ExecStart=/path/to/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable contest-bot
sudo systemctl start contest-bot
sudo systemctl status contest-bot
```

**Manage service:**
```bash
# View logs
sudo journalctl -u contest-bot -f

# Restart
sudo systemctl restart contest-bot

# Stop
sudo systemctl stop contest-bot
```

---

### 6. Oracle Cloud (Free Forever)

Oracle Cloud offers free tier with 2 VMs (ARM-based or AMD).

**Step-by-step:**

1. Create account at [oracle.com/cloud/free](https://oracle.com/cloud/free)

2. Create a VM instance (Always Free eligible)

3. SSH into instance and follow VPS instructions above

4. Configure firewall if needed:
```bash
sudo iptables -I INPUT -p tcp --dport 443 -j ACCEPT
sudo iptables -I INPUT -p tcp --dport 80 -j ACCEPT
```

---

### 7. AWS EC2 Free Tier

**Quick setup:**

1. Launch EC2 instance (t2.micro)
2. SSH into instance
3. Follow VPS deployment steps
4. Configure security group to allow outbound HTTPS

---

### 8. PythonAnywhere

**Step-by-step:**

1. Sign up at [pythonanywhere.com](https://pythonanywhere.com)

2. Open a Bash console

3. Clone and setup:
```bash
git clone <your-repo-url>
cd contest-reminder-bot
pip install --user -r requirements.txt
```

4. Create `~/.bashrc` addition:
```bash
export BOT_TOKEN='your_token_here'
```

5. Set as "Always-on task" (requires paid account)

---

## Environment Variables

All deployment methods require setting the `BOT_TOKEN` environment variable:

| Variable | Required | Description |
|----------|----------|-------------|
| `BOT_TOKEN` | Yes | Your Telegram bot token from @BotFather |

## Database

The bot uses SQLite (`database.db`). For persistence:

- **Docker**: Use volume mounting (already configured in docker-compose.yml)
- **VPS**: Stored in working directory
- **Cloud platforms**: Usually persisted automatically

## Monitoring

### Check if bot is running:
```bash
# Heroku
heroku logs --tail

# Railway/Render
Check dashboard logs

# VPS with systemd
sudo journalctl -u contest-bot -f

# Docker
docker logs -f contest-bot
```

### Common issues:

1. **Bot not responding**:
   - Check BOT_TOKEN is set correctly
   - Verify internet connectivity
   - Check logs for errors

2. **Database errors**:
   - Ensure write permissions
   - Check disk space

3. **Memory issues**:
   - Bot uses ~50MB RAM typically
   - Ensure at least 128MB available

## Updating the Bot

### Git-based platforms (Railway, Render, Heroku):
```bash
git pull
git push origin main
# Platform auto-deploys
```

### Docker:
```bash
docker-compose down
git pull
docker-compose up -d --build
```

### VPS:
```bash
cd /path/to/bot
git pull
sudo systemctl restart contest-bot
```

## Security Best Practices

1. **Never commit tokens**: Use environment variables
2. **Keep updated**: Regularly update dependencies
3. **Use HTTPS**: Always (Telegram API requires it)
4. **Backup database**: Regular backups of `database.db`
5. **Monitor logs**: Watch for suspicious activity

## Backup & Restore

### Backup database:
```bash
# Local
cp database.db database.backup.db

# Remote
scp user@server:/path/to/database.db ./backup/
```

### Restore:
```bash
cp database.backup.db database.db
# Restart bot
```

## Support

For issues:
1. Check logs first
2. Verify BOT_TOKEN
3. Open GitHub issue with logs (remove token!)

## Cost Comparison

| Platform | Free Tier | Limits | Best For |
|----------|-----------|--------|----------|
| Railway | Yes | 500 hrs/month | Quick start |
| Render | Yes | Always free | Simple setup |
| Heroku | Yes (with card) | 550 hrs/month | Established platform |
| Oracle Cloud | Yes (forever) | 2 VMs | Long-term |
| VPS (DigitalOcean) | $4/month | No limits | Full control |
| Docker (self-hosted) | Free | Hardware dependent | Maximum control |

## Recommended Setup

**For beginners**: Railway (easiest)  
**For developers**: Docker (flexible)  
**For production**: VPS with systemd (reliable)  
**For free forever**: Oracle Cloud (generous limits)
