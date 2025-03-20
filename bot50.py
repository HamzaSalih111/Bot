import os
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp
import ffmpeg

# إعداد السجل لتتبع الأخطاء
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# **التوكن الخاص بالبوت**
TOKEN = "7980235755:AAGQBHaxdz_5G6cy5qcTsewD-EkNZqoeyW0"

# حد حجم الملف لتيليجرام (50 ميجابايت)
MAX_FILE_SIZE = 50 * 1024 * 1024

# الحد الأقصى لمحاولات ضغط الفيديو
MAX_COMPRESS_ATTEMPTS = 3

# **تحديد الجودة الافتراضية إلى 576p**
DEFAULT_VIDEO_QUALITY = "bestvideo[height<=576]+bestaudio/best"

def download_media(url, quality=DEFAULT_VIDEO_QUALITY, audio_only=False):
    """
    دالة لتحميل الفيديو أو الصوت باستخدام yt-dlp.
    تُعيد مسار الملف المحمل أو ترفع استثناء عند الفشل.
    """
    output_template = 'media.%(ext)s' if not audio_only else 'audio.%(ext)s'
    ydl_opts = {
        'format': quality if not audio_only else 'bestaudio/best',
        'outtmpl': output_template,
        'noplaylist': True,
        'quiet': True,
        'merge_output_format': 'mp4' if not audio_only else None,
        'socket_timeout': 60,  # زيادة مهلة الاتصال إلى 60 ثانية
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}] if audio_only else [],
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return 'audio.mp3' if audio_only else 'media.mp4'
    except Exception as e:
        logger.error(f"Error downloading media: {str(e)}")
        raise Exception(f"❌ فشل التحميل: {str(e)}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    أمر /start لبدء التفاعل مع البوت.
    """
    await update.message.reply_text(
        "مرحبًا! أنا بوت تحميل الفيديوهات والصوتيات.\n"
        "أرسل لي رابط الفيديو وسأقوم بتحميله تلقائيًا بجودة 576p.\n"
        "لتحميل الصوت فقط، استخدم /audio قبل إرسال الرابط."
    )

async def audio_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    أمر /audio لتحميل الصوت فقط.
    """
    await update.message.reply_text("أرسل لي رابط الفيديو وسأحمل الصوت فقط بصيغة MP3.")
    context.user_data["audio_only"] = True

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    معالجة الروابط المرسلة من المستخدم وتحميلها تلقائيًا.
    """
    url = update.message.text.strip()
    chat_id = update.message.chat_id
    audio_only = context.user_data.get("audio_only", False)

    if not url.startswith(('http://', 'https://')):
        await update.message.reply_text("❌ يرجى إرسال رابط صالح!")
        return

    await update.message.reply_text("⏳ جارٍ التحميل، انتظر قليلًا...")

    try:
        # تحميل الفيديو أو الصوت
        media_path = await asyncio.to_thread(download_media, url, DEFAULT_VIDEO_QUALITY, audio_only)

        # إرسال الملف للمستخدم
        with open(media_path, 'rb') as media_file:
            if audio_only:
                await context.bot.send_audio(chat_id=chat_id, audio=media_file)
            else:
                await context.bot.send_video(chat_id=chat_id, video=media_file)

        # حذف الملفات المؤقتة بعد الإرسال
        if os.path.exists(media_path):
            os.remove(media_path)

        await update.message.reply_text("🎉 تم التحميل والإرسال بنجاح بجودة 576p!")
    except Exception as e:
        await update.message.reply_text(f"❌ حدث خطأ: {str(e)}")

    # إعادة تعيين خيار الصوت فقط بعد تنفيذ الطلب
    context.user_data["audio_only"] = False

def main():
    """
    الدالة الرئيسية لتشغيل البوت.
    """
    app = Application.builder().token(TOKEN).build()

    # إضافة المعالجات
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("audio", audio_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # تشغيل البوت
    app.run_polling()

if __name__ == '__main__':
    main()