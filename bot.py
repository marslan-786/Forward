import os
import asyncio
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
from telegram import Update, ForceReply
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)

# === Load Environment Variables ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
CHECKER_BOT = os.getenv("CHECKER_BOT")

# === Global state ===
SESSION_NAME = "userbot_session"
userbot = TelegramClient(SESSION_NAME, API_ID, API_HASH)

PHONE, OTP, TWOFA = range(3)
logged_in = False
_login_phone = None

# === Telegram Bot ===
app = ApplicationBuilder().token(BOT_TOKEN).build()

# === /start command ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome! Use /login to start the login process.")

# === /login command ===
async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📱 Send your phone number (with +92...)", reply_markup=ForceReply(selective=True))
    return PHONE

# === Phone input ===
async def phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global _login_phone
    _login_phone = update.message.text.strip()
    try:
        await userbot.connect()
        await userbot.send_code_request(_login_phone)
        await update.message.reply_text("✅ Code sent! Now send /otp <code>")
        return OTP
    except Exception as e:
        await update.message.reply_text(f"❌ Error sending code: {e}")
        return ConversationHandler.END

# === OTP input ===
async def otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global logged_in
    code = update.message.text.strip()
    try:
        await userbot.sign_in(_login_phone, code)
        logged_in = True
        await update.message.reply_text("✅ Logged in successfully!")
        return ConversationHandler.END
    except SessionPasswordNeededError:
        await update.message.reply_text("🔒 2FA enabled. Please send /2fa <password>")
        return TWOFA
    except Exception as e:
        await update.message.reply_text(f"❌ Login failed: {e}")
        return ConversationHandler.END

# === 2FA input ===
async def twofa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global logged_in
    password = update.message.text.strip()
    try:
        await userbot.sign_in(password=password)
        logged_in = True
        await update.message.reply_text("✅ Logged in with 2FA!")
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text(f"❌ 2FA failed: {e}")
        return ConversationHandler.END

# === /chk command ===
async def chk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global logged_in
    if not logged_in:
        await update.message.reply_text("❌ Login first with /login")
        return

    lines = update.message.text.split("\n")[1:]  # Skip first line (/chk)
    if not lines:
        await update.message.reply_text("❗ Send /chk followed by CCs in new lines.")
        return

    await update.message.reply_text(f"🔍 Checking {len(lines)} CC(s)...")

    for cc in lines:
        cc = cc.strip()
        if cc:
            try:
                await userbot.send_message(CHECKER_BOT, f"/chk {cc}")
            except Exception as e:
                await update.message.reply_text(f"❌ Error with CC: {cc}\nError: {e}")
            await asyncio.sleep(5)

# === Forward replies from checker bot ===
@userbot.on(events.NewMessage(from_users=CHECKER_BOT))
async def handle_checker_reply(event):
    try:
        await userbot.send_message("me", f"💳 {event.text}")
    except Exception as e:
        print(f"❌ Failed to forward checker reply: {e}")

# === Conversation handler ===
conv_handler = ConversationHandler(
    entry_points=[CommandHandler("login", login)],
    states={
        PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, phone)],
        OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, otp)],
        TWOFA: [MessageHandler(filters.TEXT & ~filters.COMMAND, twofa)],
    },
    fallbacks=[]
)

# === Add handlers ===
app.add_handler(CommandHandler("start", start))
app.add_handler(conv_handler)
app.add_handler(CommandHandler("chk", chk))

# === MAIN ===
async def main():
    await userbot.connect()
    print("🟢 Userbot connected")

    # Start userbot in background
    asyncio.create_task(userbot.run_until_disconnected())

    # Start telegram bot
    print("🤖 Bot starting...")
    await app.run_polling()

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())