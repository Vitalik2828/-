import os
import logging
import asyncio
import tempfile
import shutil
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import yt_dlp

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN environment variable not set")

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

BASE_TEMP_DIR = Path("/tmp/bot_downloads")
BASE_TEMP_DIR.mkdir(exist_ok=True)

YDL_OPTS_BASE = {
    'quiet': True,
    'no_warnings': True,
    'restrictfilenames': True,
    'socket_timeout': 30,
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 Привет! Я помогу скачать видео или аудио.\n\n"
        "Просто отправь мне ссылку на видео (YouTube, Vimeo и др.), "
        "а затем выбери нужное качество.\n\n"
        "⚠️ Ограничение Telegram: файлы не более 50 MB."
    )

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        await update.message.reply_text("❌ Пожалуйста, отправьте корректную ссылку.")
        return

    context.user_data['url'] = url
    keyboard = [
        [InlineKeyboardButton("🎥 Видео 1080p", callback_data="video_1080")],
        [InlineKeyboardButton("🎥 Видео 720p", callback_data="video_720")],
        [InlineKeyboardButton("🎥 Видео 480p", callback_data="video_480")],
        [InlineKeyboardButton("🎵 Аудио MP3 (192 kbps)", callback_data="audio_mp3")],
        [InlineKeyboardButton("🎵 Аудио M4A (лучшее)", callback_data="audio_m4a")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("⬇️ Выберите качество:", reply_markup=reply_markup)

async def quality_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    choice = query.data
    url = context.user_data.get('url')
    if not url:
        await query.edit_message_text("❌ Ссылка не найдена. Отправьте ссылку заново.")
        return

    if choice.startswith('video_'):
        height = choice.split('_')[1]
        ydl_opts = YDL_OPTS_BASE.copy()
        ydl_opts['format'] = f'bestvideo[height<={height}]+bestaudio/best[height<={height}]'
        ydl_opts['merge_output_format'] = 'mp4'
        media_type = 'video'
        await query.edit_message_text(f"📥 Скачиваю видео {height}p... Подождите.")
    elif choice == 'audio_mp3':
        ydl_opts = YDL_OPTS_BASE.copy()
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
        media_type = 'audio'
        await query.edit_message_text("🎵 Скачиваю и конвертирую в MP3...")
    elif choice == 'audio_m4a':
        ydl_opts = YDL_OPTS_BASE.copy()
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'm4a',
        }]
        media_type = 'audio'
        await query.edit_message_text("🎵 Скачиваю аудио в M4A...")
    else:
        await query.edit_message_text("❌ Неизвестный выбор.")
        return

    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, download_with_ytdlp, url, ydl_opts)

        if result is None:
            await query.edit_message_text("❌ Не удалось скачать файл. Проверьте ссылку.")
            return

        file_path, temp_dir = result
        file_size = os.path.getsize(file_path)

        if file_size > MAX_FILE_SIZE:
            await query.edit_message_text(
                f"⚠️ Файл слишком большой ({file_size / (1024*1024):.1f} MB). "
                f"Telegram允许 до 50 MB. Выберите качество ниже."
            )
            shutil.rmtree(temp_dir, ignore_errors=True)
            return

        with open(file_path, 'rb') as f:
            if media_type == 'video':
                await context.bot.send_video(
                    chat_id=update.effective_chat.id,
                    video=f,
                    caption="✅ Видео готово!",
                    supports_streaming=True
                )
            else:
                title = Path(file_path).stem
                await context.bot.send_audio(
                    chat_id=update.effective_chat.id,
                    audio=f,
                    title=title,
                    caption="✅ Аудио готово!"
                )

        shutil.rmtree(temp_dir, ignore_errors=True)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="🔁 Отправьте новую ссылку, чтобы скачать ещё."
        )

    except Exception as e:
        logger.exception("Ошибка в callback")
        await query.edit_message_text(f"❌ Ошибка: {str(e)}")

def download_with_ytdlp(url, ydl_opts):
    temp_dir = tempfile.mkdtemp(dir=BASE_TEMP_DIR)
    try:
        ydl_opts['outtmpl'] = os.path.join(temp_dir, '%(title)s.%(ext)s')
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)
            files = os.listdir(temp_dir)
            if not files:
                return None
            file_path = os.path.join(temp_dir, files[0])
            return (file_path, temp_dir)
    except Exception as e:
        logger.exception("Ошибка в download_with_ytdlp")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return None

def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    application.add_handler(CallbackQueryHandler(quality_callback))
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
