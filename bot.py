import os
import logging
import requests
import sqlite3
import datetime
import asyncio
from zoneinfo import ZoneInfo
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

# Get token from environment variable (required for production)
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set! Get your token from @BotFather")

BD_TZ = ZoneInfo("Asia/Dhaka")

# Configure logging with more detail for production
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ================= DATABASE =================
conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS chats (
    chat_id INTEGER PRIMARY KEY
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS contests (
    id TEXT PRIMARY KEY,
    name TEXT,
    start_time INTEGER,
    platform TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS reminders (
    contest_id TEXT,
    reminder_seconds INTEGER,
    chat_id INTEGER,
    PRIMARY KEY (contest_id, reminder_seconds, chat_id)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS chat_settings (
    chat_id INTEGER PRIMARY KEY,
    platforms TEXT,
    reminder_times TEXT
)
""")

# Migrate reminders table if it was created without chat_id.
cursor.execute("PRAGMA table_info(reminders)")
reminder_columns = [row[1] for row in cursor.fetchall()]
if "chat_id" not in reminder_columns:
    cursor.execute("DROP TABLE IF EXISTS reminders")
    cursor.execute("""
    CREATE TABLE reminders (
        contest_id TEXT,
        reminder_seconds INTEGER,
        chat_id INTEGER,
        PRIMARY KEY (contest_id, reminder_seconds, chat_id)
    )
    """)
conn.commit()

# ================= FETCHERS =================

def fetch_codeforces():
    url = "https://codeforces.com/api/contest.list"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        logger.warning("Codeforces fetch failed: %s", exc)
        return []

    contests = []
    for c in data.get("result", []):
        if c.get("phase") == "BEFORE":
            contests.append({
                "id": f"cf_{c['id']}",
                "name": c.get("name", "Codeforces Contest"),
                "start": c.get("startTimeSeconds"),
                "platform": "Codeforces",
                "url": f"https://codeforces.com/contest/{c['id']}"
            })
    return [c for c in contests if c.get("start")]

def fetch_leetcode():
    url = "https://leetcode.com/graphql"
    query = {
        "query": """
        {
          allContests {
            title
            startTime
            titleSlug
          }
        }
        """
    }
    try:
        response = requests.post(url, json=query, timeout=15)
        response.raise_for_status()
        res = response.json()
    except Exception as exc:
        logger.warning("LeetCode fetch failed: %s", exc)
        return []

    contests = []
    now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    for c in res.get("data", {}).get("allContests", []):
        start_time = c.get("startTime")
        if start_time and start_time > now:
            slug = c.get("titleSlug", str(start_time))
            contests.append({
                "id": f"lc_{slug}",
                "name": c.get("title", "LeetCode Contest"),
                "start": start_time,
                "platform": "LeetCode",
                "url": f"https://leetcode.com/contest/{slug}/"
            })
    return contests

def fetch_atcoder():
    url = "https://kenkoooo.com/atcoder/resources/contests.json"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        logger.warning("AtCoder fetch failed: %s", exc)
        return []

    contests = []
    now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    for c in data:
        start_time = c.get("start_epoch_second")
        if start_time and start_time > now:
            contest_id = c.get("id", "")
            contests.append({
                "id": f"ac_{contest_id}",
                "name": c.get("title", "AtCoder Contest"),
                "start": start_time,
                "platform": "AtCoder",
                "url": f"https://atcoder.jp/contests/{contest_id}"
            })
    return contests

def fetch_codechef():
    url = "https://www.codechef.com/api/list/contests/all"
    try:
        response = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        logger.warning("CodeChef fetch failed: %s", exc)
        return []

    contests = []
    now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    future_contests = data.get("future_contests", [])
    for c in future_contests:
        start_time_str = c.get("contest_start_date")
        if start_time_str:
            try:
                # CodeChef returns timestamps in milliseconds-like format or ISO
                start_time = int(c.get("contest_start_date_iso", 0))
                if start_time == 0:
                    continue
                if start_time > now:
                    contest_code = c.get("contest_code", "")
                    contests.append({
                        "id": f"cc_{contest_code}",
                        "name": c.get("contest_name", "CodeChef Contest"),
                        "start": start_time,
                        "platform": "CodeChef",
                        "url": f"https://www.codechef.com/{contest_code}"
                    })
            except (ValueError, TypeError):
                continue
    return contests

# ================= BOT COMMANDS =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    cursor.execute("INSERT OR IGNORE INTO chats VALUES (?)", (chat_id,))
    cursor.execute(
        "INSERT OR IGNORE INTO chat_settings VALUES (?, ?, ?)",
        (chat_id, "Codeforces,LeetCode,AtCoder,CodeChef", ",".join(str(x) for x in DEFAULT_REMINDER_TIMES)),
    )
    conn.commit()
    await update.message.reply_text("✅ Subscribed to Contest Reminders!")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    cursor.execute("DELETE FROM chats WHERE chat_id=?", (chat_id,))
    cursor.execute("DELETE FROM chat_settings WHERE chat_id=?", (chat_id,))
    conn.commit()
    await update.message.reply_text("❌ Unsubscribed!")

async def upcoming(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    settings = load_chat_settings(chat_id)
    limit = 5
    if context.args and context.args[0].isdigit():
        limit = max(1, min(10, int(context.args[0])))

    codeforces_task = asyncio.to_thread(fetch_codeforces)
    leetcode_task = asyncio.to_thread(fetch_leetcode)
    atcoder_task = asyncio.to_thread(fetch_atcoder)
    codechef_task = asyncio.to_thread(fetch_codechef)
    codeforces, leetcode, atcoder, codechef = await asyncio.gather(
        codeforces_task, leetcode_task, atcoder_task, codechef_task
    )
    all_contests = [
        c for c in (codeforces + leetcode + atcoder + codechef)
        if c["platform"] in settings["platforms"]
    ]
    all_contests.sort(key=lambda c: c["start"])
    upcoming_contests = all_contests[:limit]

    if not upcoming_contests:
        await update.message.reply_text("No upcoming contests found for your filters.")
        return

    lines = []
    for contest in upcoming_contests:
        start_time = datetime.datetime.fromtimestamp(
            contest["start"], tz=BD_TZ
        ).strftime("%Y-%m-%d %H:%M %Z")
        lines.append(
            f"{contest['name']}\n"
            f"Platform: {contest['platform']}\n"
            f"Start: {start_time}\n"
            f"{contest['url']}"
        )

    await update.message.reply_text("\n\n".join(lines))

async def platform(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args:
        settings = load_chat_settings(chat_id)
        await update.message.reply_text(
            "Platforms enabled: " + ", ".join(settings["platforms"]) + "\n"
            "Usage: /platform all | /platform cf lc ac cc"
        )
        return

    if context.args[0].lower() == "all":
        platforms = ["Codeforces", "LeetCode", "AtCoder", "CodeChef"]
    else:
        platforms = []
        for token in context.args:
            key = token.lower()
            if key in PLATFORM_MAP:
                value = PLATFORM_MAP[key]
                if value not in platforms:
                    platforms.append(value)
        if not platforms:
            await update.message.reply_text(
                "Invalid platforms. Use: /platform all | /platform cf lc ac cc"
            )
            return

    settings = load_chat_settings(chat_id)
    save_chat_settings(chat_id, platforms, settings["reminders"])
    await update.message.reply_text("Platforms updated: " + ", ".join(platforms))

async def reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args:
        settings = load_chat_settings(chat_id)
        await update.message.reply_text(
            "Reminder times: " + format_reminder_list(settings["reminders"]) + "\n"
            "Usage: /reminders 1d 2h 1h 30m 10m 5m"
        )
        return

    reminder_list = parse_reminder_tokens(" ".join(context.args))
    if not reminder_list:
        await update.message.reply_text(
            "Invalid reminder list. Example: /reminders 1d 2h 1h 30m 10m 5m"
        )
        return

    settings = load_chat_settings(chat_id)
    save_chat_settings(chat_id, settings["platforms"], reminder_list)
    await update.message.reply_text(
        "Reminder times updated: " + format_reminder_list(reminder_list)
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Commands:\n"
        "/start - Subscribe to contest reminders\n"
        "/stop - Unsubscribe\n"
        "/upcoming [n] - Show next contests (1-10)\n"
        "/next - Show the next contest\n"
        "/recent [n] - Show latest contests by start time\n"
        "/platform all | /platform cf lc ac cc - Set platform filters\n"
        "/reminders 1d 2h 1h 30m 10m 5m - Set reminder times\n\n"
        "Platforms: Codeforces (cf), LeetCode (lc), AtCoder (ac), CodeChef (cc)"
    )

async def next_contest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    settings = load_chat_settings(chat_id)

    codeforces_task = asyncio.to_thread(fetch_codeforces)
    leetcode_task = asyncio.to_thread(fetch_leetcode)
    atcoder_task = asyncio.to_thread(fetch_atcoder)
    codechef_task = asyncio.to_thread(fetch_codechef)
    codeforces, leetcode, atcoder, codechef = await asyncio.gather(
        codeforces_task, leetcode_task, atcoder_task, codechef_task
    )
    all_contests = [
        c for c in (codeforces + leetcode + atcoder + codechef)
        if c["platform"] in settings["platforms"]
    ]
    if not all_contests:
        await update.message.reply_text("No upcoming contests found for your filters.")
        return

    contest = min(all_contests, key=lambda c: c["start"])
    start_time = datetime.datetime.fromtimestamp(
        contest["start"], tz=BD_TZ
    ).strftime("%Y-%m-%d %H:%M %Z")
    await update.message.reply_text(
        f"{contest['name']}\n"
        f"Platform: {contest['platform']}\n"
        f"Start: {start_time}\n"
        f"{contest['url']}"
    )

async def recent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    settings = load_chat_settings(chat_id)
    limit = 5
    if context.args and context.args[0].isdigit():
        limit = max(1, min(10, int(context.args[0])))

    codeforces_task = asyncio.to_thread(fetch_codeforces)
    leetcode_task = asyncio.to_thread(fetch_leetcode)
    atcoder_task = asyncio.to_thread(fetch_atcoder)
    codechef_task = asyncio.to_thread(fetch_codechef)
    codeforces, leetcode, atcoder, codechef = await asyncio.gather(
        codeforces_task, leetcode_task, atcoder_task, codechef_task
    )
    all_contests = [
        c for c in (codeforces + leetcode + atcoder + codechef)
        if c["platform"] in settings["platforms"]
    ]
    if not all_contests:
        await update.message.reply_text("No contests found for your filters.")
        return

    all_contests.sort(key=lambda c: c["start"], reverse=True)
    recent_contests = all_contests[:limit]

    lines = []
    for contest in recent_contests:
        start_time = datetime.datetime.fromtimestamp(
            contest["start"], tz=BD_TZ
        ).strftime("%Y-%m-%d %H:%M %Z")
        lines.append(
            f"{contest['name']}\n"
            f"Platform: {contest['platform']}\n"
            f"Start: {start_time}\n"
            f"{contest['url']}"
        )

    await update.message.reply_text("\n\n".join(lines))

async def auto_subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or not update.message:
        return
    chat_id = update.effective_chat.id
    cursor.execute("INSERT OR IGNORE INTO chats VALUES (?)", (chat_id,))
    cursor.execute(
        "INSERT OR IGNORE INTO chat_settings VALUES (?, ?, ?)",
        (chat_id, "Codeforces,LeetCode,AtCoder,CodeChef", ",".join(str(x) for x in DEFAULT_REMINDER_TIMES)),
    )
    conn.commit()

# ================= REMINDER SYSTEM =================

DEFAULT_REMINDER_TIMES = [
    86400,  # 1 day
    7200,   # 2 hours
    3600,   # 1 hour
    1800,   # 30 min
    600,    # 10 min
    300     # 5 min
]

PLATFORM_MAP = {
    "cf": "Codeforces",
    "codeforces": "Codeforces",
    "lc": "LeetCode",
    "leetcode": "LeetCode",
    "ac": "AtCoder",
    "atcoder": "AtCoder",
    "cc": "CodeChef",
    "codechef": "CodeChef",
}

def format_reminder_list(reminders):
    return ", ".join(str(datetime.timedelta(seconds=seconds)) for seconds in reminders)

def parse_reminder_tokens(text):
    if not text:
        return []
    raw_tokens = []
    for chunk in text.replace(",", " ").split():
        if chunk.strip():
            raw_tokens.append(chunk.strip().lower())
    reminders = []
    for token in raw_tokens:
        if token.endswith("d") and token[:-1].isdigit():
            reminders.append(int(token[:-1]) * 86400)
        elif token.endswith("h") and token[:-1].isdigit():
            reminders.append(int(token[:-1]) * 3600)
        elif token.endswith("m") and token[:-1].isdigit():
            reminders.append(int(token[:-1]) * 60)
        elif token.isdigit():
            reminders.append(int(token))
        else:
            return []
    reminders = sorted(set(reminders), reverse=True)
    return [r for r in reminders if r > 0]

def load_chat_settings(chat_id):
    cursor.execute(
        "SELECT platforms, reminder_times FROM chat_settings WHERE chat_id=?",
        (chat_id,),
    )
    row = cursor.fetchone()
    if not row:
        return {
            "platforms": ["Codeforces", "LeetCode", "AtCoder", "CodeChef"],
            "reminders": DEFAULT_REMINDER_TIMES,
        }
    platforms = [p for p in (row[0] or "").split(",") if p]
    reminders = [int(x) for x in (row[1] or "").split(",") if x.isdigit()]
    if not platforms:
        platforms = ["Codeforces", "LeetCode", "AtCoder", "CodeChef"]
    if not reminders:
        reminders = DEFAULT_REMINDER_TIMES
    return {"platforms": platforms, "reminders": reminders}

def save_chat_settings(chat_id, platforms, reminders):
    platforms_value = ",".join(platforms)
    reminders_value = ",".join(str(x) for x in reminders)
    cursor.execute(
        "INSERT OR REPLACE INTO chat_settings VALUES (?, ?, ?)",
        (chat_id, platforms_value, reminders_value),
    )
    conn.commit()

async def check_contests(context: ContextTypes.DEFAULT_TYPE):
    app = context.application
    codeforces_task = asyncio.to_thread(fetch_codeforces)
    leetcode_task = asyncio.to_thread(fetch_leetcode)
    atcoder_task = asyncio.to_thread(fetch_atcoder)
    codechef_task = asyncio.to_thread(fetch_codechef)
    codeforces, leetcode, atcoder, codechef = await asyncio.gather(
        codeforces_task, leetcode_task, atcoder_task, codechef_task
    )
    all_contests = codeforces + leetcode + atcoder + codechef
    now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())

    cursor.execute("SELECT chat_id FROM chats")
    chat_rows = cursor.fetchall()
    chat_settings = {}
    for row in chat_rows:
        chat_id = row[0]
        chat_settings[chat_id] = load_chat_settings(chat_id)

    for contest in all_contests:
        cursor.execute("SELECT id FROM contests WHERE id=?", (contest["id"],))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO contests VALUES (?, ?, ?, ?)",
                           (contest["id"], contest["name"], contest["start"], contest["platform"]))
            conn.commit()
            for chat_id, settings in chat_settings.items():
                if contest["platform"] in settings["platforms"]:
                    try:
                        await app.bot.send_message(
                            chat_id=chat_id,
                            text=(
                                "🆕 New Contest Published!\n\n"
                                f"{contest['name']}\n"
                                f"Platform: {contest['platform']}\n"
                                f"{contest['url']}"
                            ),
                        )
                    except Exception as exc:
                        logger.warning("Failed to send message to %s: %s", chat_id, exc)

        remaining = contest["start"] - now
        if remaining <= 0:
            continue
        for chat_id, settings in chat_settings.items():
            if contest["platform"] not in settings["platforms"]:
                continue
            for r in settings["reminders"]:
                if r - 60 <= remaining <= r + 60:
                    cursor.execute(
                        "SELECT 1 FROM reminders WHERE contest_id=? AND reminder_seconds=? AND chat_id=?",
                        (contest["id"], r, chat_id),
                    )
                    if cursor.fetchone():
                        continue
                    cursor.execute(
                        "INSERT INTO reminders VALUES (?, ?, ?)",
                        (contest["id"], r, chat_id),
                    )
                    conn.commit()
                    time_str = str(datetime.timedelta(seconds=r))
                    try:
                        await app.bot.send_message(
                            chat_id=chat_id,
                            text=(
                                f"⏰ Reminder ({time_str} left)\n\n"
                                f"{contest['name']}\n"
                                f"Platform: {contest['platform']}\n"
                                f"{contest['url']}"
                            ),
                        )
                    except Exception as exc:
                        logger.warning("Failed to send message to %s: %s", chat_id, exc)

async def broadcast(app, message):
    cursor.execute("SELECT chat_id FROM chats")
    chats = cursor.fetchall()
    for chat in chats:
        try:
            await app.bot.send_message(chat_id=chat[0], text=message)
        except Exception as exc:
            logger.warning("Failed to send message to %s: %s", chat[0], exc)

# ================= MAIN =================

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors caused by updates."""
    logger.error("Exception while handling an update:", exc_info=context.error)

def main():
    logger.info("Starting Contest Reminder Bot...")
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Add error handler
    app.add_error_handler(error_handler)
    
    # Add command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("upcoming", upcoming))
    app.add_handler(CommandHandler("next", next_contest))
    app.add_handler(CommandHandler("recent", recent))
    app.add_handler(CommandHandler("platform", platform))
    app.add_handler(CommandHandler("reminders", reminders))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auto_subscribe))

    app.job_queue.run_repeating(check_contests, interval=300, first=5)

    logger.info("Bot started successfully!")
    try:
        app.run_polling(allowed_updates=Update.ALL_TYPES)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed with error: {e}")
        raise
    finally:
        conn.close()
        logger.info("Database connection closed")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"Failed to start bot: {e}")
        exit(1)