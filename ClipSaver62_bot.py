import telebot
import yt_dlp
import os
import time
from flask import Flask
from threading import Thread

# ------------------------------
# 🔑 توكن البوت (استبدله بتوكنك الحقيقي)
TOKEN = '8825458063:AAFWpeDU0wH8W_brXsEVi7amR4kTA5qr6CQ'
# ------------------------------

# إعداد مسار التحميل
DOWNLOAD_PATH = 'downloads'
if not os.path.exists(DOWNLOAD_PATH):
    os.makedirs(DOWNLOAD_PATH)

bot = telebot.TeleBot(TOKEN)

# ------------------------------
# جزء Flask لإبقاء السيرفر مستيقظاً (ضروري لـ Render)
app = Flask('')

@app.route('/')
def home():
    return "✅ البوت يعمل!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# تشغيل Flask في خيط منفصل
Thread(target=run_flask).start()
# ------------------------------

# أمر /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "👋 مرحباً! أرسل رابط فيديو من يوتيوب، انستقرام، تيك توك أو أي موقع آخر وسأقوم بتحميله وإرساله لك، ثم سأحذفه من الخادم فوراً!")

# معالجة أي رسالة نصية (الروابط)
@bot.message_handler(func=lambda message: True)
def download_video(message):
    url = message.text.strip()
    
    if not url.startswith(('http://', 'https://')):
        bot.reply_to(message, "❌ الرجاء إرسال رابط صحيح يبدأ بـ http:// أو https://")
        return

    processing_msg = bot.reply_to(message, "⏳ جاري تحميل الفيديو...")
    
    ydl_opts = {
        'format': 'best[ext=mp4]/best',  # أفضل جودة بصيغة mp4
        'outtmpl': f'{DOWNLOAD_PATH}/%(title)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            # إذا كان الملف بصيغة أخرى غير mp4 (مثل webm) نحاول تعديل الامتداد
            if not os.path.exists(filename):
                for ext in ['.mp4', '.mkv', '.webm']:
                    test_name = filename.rsplit('.', 1)[0] + ext
                    if os.path.exists(test_name):
                        filename = test_name
                        break
            
            file_size = os.path.getsize(filename) / (1024 * 1024)
            bot.edit_message_text(f"📤 تم التحميل! جاري الإرسال ({file_size:.1f} MB)...", 
                                  message.chat.id, processing_msg.message_id)
            
            # إرسال الفيديو
            with open(filename, 'rb') as video:
                bot.send_video(message.chat.id, video, caption=f"✅ {info.get('title', 'تم التحميل')[:50]}")
            
            # حذف الملف لتوفير المساحة
            os.remove(filename)
            bot.edit_message_text("✅ تم الإرسال والحذف بنجاح!", message.chat.id, processing_msg.message_id)
    
    except Exception as e:
        error_msg = f"❌ حدث خطأ: {str(e)[:200]}"
        bot.edit_message_text(error_msg, message.chat.id, processing_msg.message_id)

# تشغيل البوت
if __name__ == '__main__':
    print("🚀 البوت يعمل مع Flask...")
    bot.infinity_polling()
