import os
import sqlite3
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 5523761749
WEBHOOK_PATH = "/webhook"
BASE_URL = os.getenv("WEBHOOK_URL")  # https://xxxx.onrender.com

CHANNEL1 = "@ucplanet"
CHANNEL2_ID = -1003934812939
CHANNEL3_ID = -1003999645745

app_flask = Flask(__name__)

# ---------------- DB ----------------
conn = sqlite3.connect("bot.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    firstname TEXT,
    ref_by INTEGER,
    refs INTEGER DEFAULT 0
)
""")
conn.commit()

# ---------------- HELPERS ----------------

def add_user(user, ref_by=None):
    cur.execute("SELECT user_id FROM users WHERE user_id=?", (user.id,))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users (user_id, username, firstname, ref_by, refs) VALUES (?, ?, ?, ?, 0)",
            (user.id, user.username, user.first_name, ref_by)
        )
        conn.commit()
        if ref_by:
            cur.execute("UPDATE users SET refs = refs + 1 WHERE user_id=?", (ref_by,))
            conn.commit()

def get_user(user_id):
    cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    return cur.fetchone()

def is_joined(bot, user_id):
    try:
        m = bot.get_chat_member(CHANNEL1, user_id)
        return m.status in ["member", "administrator", "creator"]
    except:
        return False

def has_requested(bot, user_id, chat_id):
    try:
        m = bot.get_chat_member(chat_id, user_id)
        return m.status == "restricted" or m.status == "left"
    except:
        return False

def build_ref_link(user_id):
    return f"https://t.me/{bot_username}?start={user_id}"

# ---------------- BOT HANDLERS ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args

    ref = int(args[0]) if args else None
    add_user(user, ref)

    keyboard = [
        [InlineKeyboardButton("Channel 1", url=f"https://t.me/{CHANNEL1[1:]}")],
        [InlineKeyboardButton("Channel 2", url="https://t.me/+FZ4aRhgmrvQ1ZmI6")],
        [InlineKeyboardButton("Channel 3", url="https://t.me/+e6xEfcq-pkk0NWVi")],
        [InlineKeyboardButton("Tekshirish", callback_data="check")]
    ]

    await update.message.reply_text(
        "konkursga xush kelibsiz davom etish uchun quyidagi kanallarga a'zo bo'ling!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    user_id = q.from_user.id
    await q.answer()

    bot = context.bot

    c1 = is_joined(bot, user_id)
    c2 = has_requested(bot, user_id, CHANNEL2_ID)
    c3 = has_requested(bot, user_id, CHANNEL3_ID)

    if c1 and c2 and c3:
        ref_link = build_ref_link(user_id)
        await q.edit_message_text(
            "Tabriklaymiz,konkursga qo'shildingiz!\n"
            "Ko'proq do'stlaringizni taklif qiling!\n\n"
            f"Ref link: {ref_link}"
        )
    else:
        await q.edit_message_text("Siz hali barcha shartlarni bajarmagansiz.")

# ---------------- ADMIN COMMANDS ----------------

async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    cur.execute("SELECT COUNT(*) FROM users")
    count = cur.fetchone()[0]
    await update.message.reply_text(f"Users: {count}")

async def topref(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    cur.execute("""
        SELECT username, firstname, refs
        FROM users
        ORDER BY refs DESC
        LIMIT 3
    """)
    rows = cur.fetchall()

    text = "TOP REFERRALS:\n\n"
    for r in rows:
        text += f"{r[1]} (@{r[0]}): {r[2]} refs\n"

    await update.message.reply_text(text)

async def xabar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    msg = " ".join(context.args)
    if not msg:
        return

    cur.execute("SELECT user_id FROM users")
    users_list = cur.fetchall()

    for u in users_list:
        try:
            await context.bot.send_message(u[0], msg)
        except:
            pass

    await update.message.reply_text("Yuborildi.")

# ---------------- JOIN REQUEST HANDLER ----------------

async def join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # We DO NOT approve, only register state implicitly
    pass

# ---------------- FLASK WEBHOOK ----------------

application = Application.builder().token(TOKEN).build()

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("users", users))
application.add_handler(CommandHandler("topref", topref))
application.add_handler(CommandHandler("xabar", xabar))
application.add_handler(CallbackQueryHandler(check, pattern="check"))

application.add_handler(MessageHandler(filters.StatusUpdate.CHAT_JOIN_REQUEST, join_request))

@app_flask.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put_nowait(update)
    return "ok"

# ---------------- START ----------------

def main():
    global bot_username

    import asyncio
    asyncio.run(application.initialize())

    bot_info = asyncio.run(application.bot.get_me())
    bot_username = bot_info.username

    application.bot.set_webhook(url=f"{BASE_URL}{WEBHOOK_PATH}")

    app_flask.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

if __name__ == "__main__":
    main()
