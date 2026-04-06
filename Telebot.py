from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
import subprocess
import os

TOKEN = os.getenv("BOT_TOKEN")
ALLOWED_USER = int(os.getenv("USER_ID"))

USER_LINK = {}

async def receive_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER:
        return

    url = update.message.text
    USER_LINK[update.effective_user.id] = url

    keyboard = [
        [
            InlineKeyboardButton("📹 Видео", callback_data="video"),
            InlineKeyboardButton("🎵 MP3", callback_data="mp3"),
        ]
    ]

    await update.message.reply_text(
        "Выбери формат:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if user_id != ALLOWED_USER:
        return

    url = USER_LINK.get(user_id)

    await query.edit_message_text("⬇️ Скачиваю...")

    if query.data == "video":
        subprocess.run(["yt-dlp", url])

    elif query.data == "mp3":
        subprocess.run(["yt-dlp", "-x", "--audio-format", "mp3", url])

    await query.message.reply_text("✅ Готово!")

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_link))
app.add_handler(CallbackQueryHandler(buttons))

app.run_polling()
