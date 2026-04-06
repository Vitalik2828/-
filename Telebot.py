import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from yt_dlp import YoutubeDL

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

bot = Bot(token=TOKEN)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)

DOWNLOAD_PATH = "downloads"
if not os.path.exists(DOWNLOAD_PATH):
    os.makedirs(DOWNLOAD_PATH)

@dp.message(lambda message: message.from_user.id != ADMIN_ID)
async def access_denied(message: types.Message):
    return

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("🤖 Доступ разрешен. Пришли ссылку.")

@dp.message(F.text.contains("http"))
async def handle_link(message: types.Message):
    url = message.text
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="🎬 720p", callback_data=f"v_720|{url}"),
        types.InlineKeyboardButton(text="🎬 Best", callback_data=f"v_best|{url}"),
        types.InlineKeyboardButton(text="🎵 MP3", callback_data=f"audio|{url}")
    )
    await message.answer("Качество:", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("v_") | F.data.startswith("audio"))
async def process_download(callback: types.CallbackQuery):
    action, url = callback.data.split("|")
    await callback.message.edit_text("⏳ Загрузка...")

    ydl_opts = {
        'outtmpl': f'{DOWNLOAD_PATH}/%(id)s.%(ext)s',
        'noplaylist': True,
    }

    if action == "audio":
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
        })
    else:
        res = "720" if "720" in action else "1080"
        ydl_opts.update({
            'format': f'bestvideo[height<={res}]+bestaudio/best/best[height<={res}]',
            'merge_output_format': 'mp4',
        })

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            path = ydl.prepare_filename(info)
            if action == "audio":
                path = os.path.splitext(path)[0] + ".mp3"

        file_to_send = types.FSInputFile(path)
        
        if action == "audio":
            await callback.message.answer_audio(file_to_send)
        else:
            await callback.message.answer_video(file_to_send)
            
        os.remove(path)
        await callback.message.delete()

    except Exception as e:
        logging.error(e)
        await callback.message.answer("❌ Ошибка")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
