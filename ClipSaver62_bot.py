import os
import telebot
from flask import Flask, request

TOKEN = '8825458063:AAFWpeDU0wH8W_brXsEVi7amR4kTA5qr6CQ'
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# الرابط العام اللي راح يعطيك إياه Render (مثلاً: https://my-bot.onrender.com)
WEBHOOK_URL = 'http://t.me/ClipSaver62_bot'

# معالج أوامر البوت
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "أهلاً وسهلاً! البوت يعمل بنجاح.")

# نقطة النهاية اللي راح يرسل ليها تلجرام التحديثات
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK', 200
    else:
        return 'Unsupported Media Type', 415

# رابط تجربة عشان تتأكد إن السيرفر شغال
@app.route('/')
def hello():
    return "Hello! The bot is running."

if __name__ == "__main__":
    # نتأكد إن مافي ويب هوك قديم مربوط قبل ما نضيف الجديد
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 8080)))
