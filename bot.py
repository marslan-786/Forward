import os
import asyncio
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
from telegram import Update, ForceReply
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
CHECKER_BOT = os.getenv("CHECKER_BOT")  # @CheckerBotUsername

# Telethon userbot
SESSION_NAME = "userbot_session"
userbot = TelegramClient(SESSION_NAME, API_ID, API_HASH)

# States for ConversationHandler
PHONE, OTP, TWOFA = range(3)

logged_in = False
_login_phone = None

# Telegram bot setup
app = ApplicationBuilder().token(BOT_TOKEN).build()

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome! Use /login to start the login process.")

# Login command
async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Please send your phone number with country code, e.g. +923001234567", reply_markup=ForceReply(selective=True))
    return PHONE

# Phone number handler
async def phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global _login_phone
    _login_phone = update.message.text.strip()
    try:
        await userbot.connect()
        await userbot.send_code_request(_login_phone)
        await update.message.reply_text(f"Code sent to {_login_phone}. Please send /otp <code>")
        return OTP
    except Exception as e:
        await update.message.reply_text(f"Failed to send code: {e}")
        return ConversationHandler.END

# OTP handler
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

# 2FA handler
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

# /chk command handler
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

# Forward replies from checker bot to whoever sent the command (removed owner restriction)
@userbot.on(events.NewMessage(from_users=CHECKER_BOT))
async def checker_reply(event):
    # Simply forward reply to whoever sent the last /chk? 
    # But we don't keep track, so let's just send to the chat where event originated.
    # Since telethon event has no update chat context, safest is to print or do nothing.
    # Alternative: You can forward to a public chat or log channel if you want.

    # For now, just print to console:
    print(f"CheckerBot reply: {event.text}")

# Conversation handler setup
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

async def main():
    await userbot.connect()
    if not await userbot.is_user_authorized():
        print("❌ Userbot not logged in. Please login using /login command in bot.")
    else:
        print("✅ Userbot logged in.")

    userbot_task = asyncio.create_task(userbot.run_until_disconnected())
    await app.run_polling()
    await userbot_task

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())