# Contest Reminder Bot

A Telegram bot that sends automated reminders for programming contests from Codeforces, LeetCode, AtCoder, and CodeChef.

## Features

- 🔔 Automated contest reminders (1 day, 2 hours, 1 hour, 30 min, 10 min, 5 min before start)
- 🌐 Multi-platform support: Codeforces, LeetCode, AtCoder, CodeChef
- ⚙️ Per-chat customizable settings
- 🕐 Bangladesh Time (BST) display
- 🔗 Direct contest links

## Commands

- `/start` - Subscribe to contest reminders
- `/stop` - Unsubscribe from reminders
- `/help` - Show all commands
- `/upcoming [n]` - Show next N contests (1-10)
- `/next` - Show the next contest
- `/recent [n]` - Show latest contests
- `/platform all | cf lc ac cc` - Set platform filters
- `/reminders 1d 2h 1h 30m 10m 5m` - Customize reminder times

## Platform Shortcuts

- `cf` = Codeforces
- `lc` = LeetCode
- `ac` = AtCoder
- `cc` = CodeChef

## Setup

### Requirements

- Python 3.9+
- pip

### Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd contest-reminder-bot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env and add your BOT_TOKEN from @BotFather
```

4. Run the bot:
```bash
python bot.py
```

## Deployment

### Heroku

1. Create a new Heroku app
2. Set the BOT_TOKEN config var:
```bash
heroku config:set BOT_TOKEN=your_token_here
```
3. Deploy:
```bash
git push heroku main
```

### Railway

1. Create a new project on Railway
2. Add BOT_TOKEN environment variable
3. Connect your repository and deploy

### VPS/Server

1. Install Python 3.9+
2. Clone and install dependencies
3. Set BOT_TOKEN environment variable
4. Run with a process manager like systemd or PM2:
```bash
# Using screen
screen -S contest-bot
python bot.py

# Or using systemd (create /etc/systemd/system/contest-bot.service)
```

### Docker (Optional)

Create a `Dockerfile`:
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "bot.py"]
```

Build and run:
```bash
docker build -t contest-bot .
docker run -e BOT_TOKEN=your_token contest-bot
```

## Configuration

### Environment Variables

- `BOT_TOKEN` - Your Telegram bot token (required)

### Database

The bot uses SQLite (`database.db`) to store:
- Subscribed chats
- Contest information
- Reminder tracking
- Per-chat settings

## How It Works

1. Bot checks for new contests every 5 minutes
2. Sends notifications for newly published contests
3. Sends reminders at configured intervals before contest starts
4. Each chat can customize platform filters and reminder times

## Support

For issues or feature requests, please open an issue on GitHub.

## License

MIT License - feel free to use and modify!
