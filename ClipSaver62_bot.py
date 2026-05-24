import telebot
import yt_dlp
import os
import time

# 🔑 توكن البوت
TOKEN = '8825458063:AAFWpeDU0wH8W_brXsEVi7amR4kTA5qr6CQ'

# 📁 إعدادات التحميل
DOWNLOAD_PATH = 'downloads'
if not os.path.exists(DOWNLOAD_PATH):
    os.makedirs(DOWNLOAD_PATH)

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "👋 مرحباً! أرسل رابط فيديو من يوتيوب، انستقرام، تيك توك أو أي موقع آخر وسأقوم بتحميله وإرساله لك، ثم سأحذفه من الخادم فوراً!")

@bot.message_handler(func=lambda message: True)
def download_video(message):
    url = message.text.strip()
    
    if not url.startswith(('http://', 'https://')):
        bot.reply_to(message, "❌ الرجاء إرسال رابط صحيح يبدأ بـ http:// أو https://")
        return

    processing_msg = bot.reply_to(message, "⏳ جاري تحميل الفيديو...")
    
    ydl_opts = {
        'format': 'best[ext=mp4]/best',  # أفضل جودة متاحة
        'outtmpl': f'{DOWNLOAD_PATH}/%(title)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            # ✅ التأكد من وجود الملف
            if not os.path.exists(filename):
                filename = filename.replace('.webm', '.mp4').replace('.mkv', '.mp4')
            
            file_size = os.path.getsize(filename) / (1024 * 1024)
            bot.edit_message_text(f"📤 تم التحميل! جاري الإرسال ({file_size:.1f} MB)...", 
                                  message.chat.id, processing_msg.message_id)
            
            with open(filename, 'rb') as video:
                bot.send_video(message.chat.id, video, caption=f"✅ {info.get('title', 'تم التحميل')[:50]}")
            
            # 🗑️ حذف الملف لتوفير المساحة
            os.remove(filename)
            bot.edit_message_text("✅ تم الإرسال والحذف بنجاح!", message.chat.id, processing_msg.message_id)
    
    except Exception as e:
        error_msg = f"❌ حدث خطأ: {str(e)[:150]}"
        bot.edit_message_text(error_msg, message.chat.id, processing_msg.message_id)

if __name__ == '__main__':
    print("🚀 البوت يعمل...")
    bot.infinity_polling()