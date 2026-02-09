import os
import io
import requests
from PIL import Image  # الحل لمشكلة 'Image' is not defined
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from flask import Flask
from threading import Thread

# 1. إعداد سيرفر Flask لإرضاء Render ومنع الـ Port Timeout
app_web = Flask(__name__)

@app_web.route('/')
def home():
    return "Bot is alive!"

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app_web.run(host='0.0.0.0', port=port)

# تشغيل Flask في الخلفية فوراً
Thread(target=run_flask, daemon=True).start()

# 2. إعدادات Hugging Face (تأكد من وضع التوكن في Render Environment)
API_URL = "https://api-inference.huggingface.co/models/ZhengPeng7/BiRefNet"
headers = {"Authorization": f"Bearer {os.getenv('HF_TOKEN')}"}

def query_hugging_face(image_bytes):
    response = requests.post(API_URL, headers=headers, data=image_bytes, timeout=30)
    if response.status_code != 200:
        raise Exception(f"HF Error: {response.status_code}")
    return response.content

# 3. دالة معالجة الصور وإصلاح "العطل" البصري
async def process_and_remove_bg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("⏳ جاري تنظيف الصورة بدقة...")
    try:
        # تحميل الصورة
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        
        # إرسالها للذكاء الاصطناعي
        processed_bytes = query_hugging_face(photo_bytes)
        
        # استخدام مكتبة PIL لإصلاح هيكلة الـ PNG (هنا الحل النهائي للعطل)
        image = Image.open(io.BytesIO(processed_bytes)).convert("RGBA")
        out_io = io.BytesIO()
        image.save(out_io, format="PNG", optimize=True)
        out_io.seek(0)
        
        # إرسال كملف لضمان الشفافية بنسبة 100%
        await update.message.reply_document(
            document=out_io, 
            filename="transparent_result.png",
            caption="✨ تمت المعالجة! الملف سليم وشفاف 100%."
        )
    except Exception as e:
        print(f"Error logic: {e}")
        await update.message.reply_text(f"❌ خطأ تقني: {str(e)}")
    finally:
        await status_msg.delete()

# 4. تشغيل البوت مع زيادة مهلة الانتظار (لحل NetworkError)
if __name__ == '__main__':
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if BOT_TOKEN:
        # رفعنا الـ timeouts لـ 60 ثانية لضمان عدم انقطاع الاتصال
        app = ApplicationBuilder().token(BOT_TOKEN).read_timeout(60).connect_timeout(60).build()
        app.add_handler(MessageHandler(filters.PHOTO, process_and_remove_bg))
        print("🚀 البوت انطلق بنجاح...")
        app.run_polling(drop_pending_updates=True) # لتجنب التضارب (Conflict)
