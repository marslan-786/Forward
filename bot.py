import os
import asyncio
import nest_asyncio
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
from telegram import Update, ForceReply
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)

# === nest_asyncio لگائیں تاکہ "event loop already running" کا مسئلہ نہ آئے ===
nest_asyncio.apply()

# === Environment variables سے load کریں ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
CHECKER_BOT = os.getenv("CHECKER_BOT")

# === Telethon Userbot client ===
SESSION_NAME = "userbot_session"
userbot = TelegramClient(SESSION_NAME, API_ID, API_HASH)

# === Bot handlers میں state کے لیے ===
PHONE, OTP, TWOFA = range(3)

logged_in = False
_login_phone = None

# === Telegram Bot setup ===
app = ApplicationBuilder().token(BOT_TOKEN).build()

# === Start command handler ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome! Use /login to start the login process."
    )

# === Login command handler ===
async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Please send your phone number with country code, e.g. +923001234567", reply_markup=ForceReply(selective=True))
    return PHONE

# === Phone number handler ===
async def phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global _login_phone
    phone = update.message.text.strip()
    _login_phone = phone
    try:
        await userbot.connect()
        await userbot.send_code_request(phone)
        await update.message.reply_text(f"Code sent to {phone}. Please send /otp <code>")
        return OTP
    except Exception as e:
        await update.message.reply_text(f"Failed to send code: {e}")
        return ConversationHandler.END

# === OTP handler ===
async def otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global logged_in
    code = update.message.text.strip()
    try:
        await userbot.sign_in(_login_phone, code)
        logged_in = True
        await update.message.reply_text("✅ Logged in successfully!")
        return ConversationHandler.END
    except SessionPasswordNeededError:
        await update.message.reply_text("🔐 Two-step verification enabled. Please send /2fa <password>")
        return TWOFA
    except Exception as e:
        await update.message.reply_text(f"Login failed: {e}")
        return ConversationHandler.END

# === 2FA handler ===
async def twofa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global logged_in
    password = update.message.text.strip()
    try:
        await userbot.sign_in(password=password)
        logged_in = True
        await update.message.reply_text("✅ Logged in successfully with 2FA!")
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text(f"2FA failed: {e}")
        return ConversationHandler.END

# === Check command handler ===
async def chk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global logged_in
    
    if not logged_in:
        await update.message.reply_text("❌ Please login first using /login")
        return
    text = update.message.text
    lines = text.split('\n')
    if len(lines) < 2:
        await update.message.reply_text("Please send /chk followed by CCs in new lines")
        return

    ccs = lines[1:]
    await update.message.reply_text(f"⏳ Checking {len(ccs)} CC(s)...")

    for cc in ccs:
        cc = cc.strip()
        if cc:
            msg = f"/chk {cc}"
            try:
                await userbot.send_message(CHECKER_BOT, msg)
            except Exception as e:
                await update.message.reply_text(f"❌ Failed to send CC: {cc}\n📛 Error: {str(e)}")
            await asyncio.sleep(5)

# === Checker bot replies forward ===
@userbot.on(events.NewMessage(from_users=CHECKER_BOT))
async def checker_reply(event):
    # آپ چاہیں تو OWNER_ID ڈالیں یہاں، یا جو بھی user ID ہو
    # میں نے owner wala حصہ نکال دیا آپ کی درخواست پر
    await userbot.send_message(event.chat_id, f"🔍 {event.text}")

# === Conversation handler setup ===
conv_handler = ConversationHandler(
    entry_points=[CommandHandler('login', login)],
    states={
        PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, phone)],
        OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, otp)],
        TWOFA: [MessageHandler(filters.TEXT & ~filters.COMMAND, twofa)],
    },
    fallbacks=[],
)

app.add_handler(CommandHandler('start', start))
app.add_handler(conv_handler)
app.add_handler(CommandHandler('chk', chk))

# === Main function ===
async def main():
    await userbot.start()
    print("🟢 Userbot connected")
    await app.initialize()
    await app.start()
    print("🤖 Bot starting...")

    # Run both concurrently
    asyncio.create_task(userbot.run_until_disconnected())
    await app.updater.start_polling()
    await app.updater.idle()

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())