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
ADMIN_ID = int(os.getenv("ADMIN_ID"))

USER_LINK = {}


# ===== Получаем ссылку =====
async def receive_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    USER_LINK[update.effective_user.id] = update.message.text

    keyboard = [
        [
            InlineKeyboardButton("📹 Видео", callback_data="video"),
            InlineKeyboardButton("🎵 Музыка", callback_data="audio"),
        ]
    ]

    await update.message.reply_text(
        "Что скачать?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ===== Кнопки =====
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return

    url = USER_LINK.get(query.from_user.id)

    await query.edit_message_text("⬇️ Скачиваю...")

    # ===== VIDEO =====
    if query.data == "video":
        subprocess.run([
            "yt-dlp",
            "--merge-output-format",
            "mp4",
            "-o",
            "video.%(ext)s",
            url
        ])

        for file in os.listdir():
            if file.startswith("video"):
                await query.message.reply_video(open(file, "rb"))
                os.remove(file)

    # ===== AUDIO =====
    if query.data == "audio":
        subprocess.run([
            "yt-dlp",
            "-x",
            "--audio-format",
            "mp3",
            "-o",
            "audio.%(ext)s",
            url
        ])

        for file in os.listdir():
            if file.startswith("audio"):
                await query.message.reply_audio(open(file, "rb"))
                os.remove(file)

    await query.message.reply_text("✅ Готово!")


app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_link))
app.add_handler(CallbackQueryHandler(buttons))

app.run_polling()
