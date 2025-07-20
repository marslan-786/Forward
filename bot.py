import os
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Bot is working.")

async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Login command received.")

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("login", login))

    print("Bot is starting...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())