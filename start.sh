#!/bin/bash

# Contest Reminder Bot - Quick Start Script

echo "==================================="
echo "Contest Reminder Bot - Quick Start"
echo "==================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.9 or higher."
    exit 1
fi

echo "✅ Python found: $(python3 --version)"
echo ""

# Check if BOT_TOKEN is set
if [ -z "$BOT_TOKEN" ]; then
    echo "⚠️  BOT_TOKEN environment variable is not set!"
    echo ""
    echo "Please get your bot token from @BotFather on Telegram and set it:"
    echo "  export BOT_TOKEN='your_token_here'"
    echo ""
    echo "Or create a .env file with:"
    echo "  BOT_TOKEN=your_token_here"
    echo ""
    exit 1
fi

echo "✅ BOT_TOKEN is set"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt --quiet

echo ""
echo "✅ Setup complete!"
echo ""
echo "🚀 Starting bot..."
echo ""

# Run the bot
python bot.py
