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

# Получаем ссылку
async def receive_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER:
        return

    USER_LINK[update.effective_user.id] = update.message.text

    keyboard = [
        [
            InlineKeyboardButton("📹 Видео", callback_data="video_menu"),
            InlineKeyboardButton("🎵 Музыка", callback_data="audio_menu"),
        ]
    ]

    await update.message.reply_text(
        "Выбери тип загрузки:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# Обработка кнопок
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if user_id != ALLOWED_USER:
        return

    url = USER_LINK.get(user_id)

    # ===== VIDEO MENU =====
    if query.data == "video_menu":
        keyboard = [
            [
                InlineKeyboardButton("1080p", callback_data="v1080"),
                InlineKeyboardButton("720p", callback_data="v720"),
                InlineKeyboardButton("480p", callback_data="v480"),
            ]
        ]
        await query.edit_message_text(
            "Выбери качество видео:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    # ===== AUDIO MENU =====
    if query.data == "audio_menu":
        keyboard = [
            [
                InlineKeyboardButton("320kbps", callback_data="a320"),
                InlineKeyboardButton("192kbps", callback_data="a192"),
                InlineKeyboardButton("128kbps", callback_data="a128"),
            ]
        ]
        await query.edit_message_text(
            "Выбери качество музыки:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    await query.edit_message_text("⬇️ Скачиваю...")

    # ===== VIDEO DOWNLOAD =====
    if query.data.startswith("v"):
        quality = query.data.replace("v", "")

        subprocess.run([
            "yt-dlp",
            "-f",
            f"bestvideo[height<={quality}]+bestaudio/best",
            "-o",
            "video.%(ext)s",
            url,
        ])

        for file in os.listdir():
            if file.startswith("video"):
                await query.message.reply_video(open(file, "rb"))
                os.remove(file)

    # ===== AUDIO DOWNLOAD =====
    if query.data.startswith("a"):
        bitrate = query.data.replace("a", "")

        subprocess.run([
            "yt-dlp",
            "-x",
            "--audio-format",
            "mp3",
            "--audio-quality",
            bitrate,
            "-o",
            "audio.%(ext)s",
            url,
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
