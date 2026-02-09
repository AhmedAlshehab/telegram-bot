import os
import io
import requests
from PIL import Image
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from flask import Flask
from threading import Thread

# 1. إعداد Flask (يجب أن يعمل أولاً لإرضاء Render)
app_web = Flask(__name__)

@app_web.route('/')
def home():
    return "Bot is running perfectly!"

def run_flask():
    # Render يرسل المنفذ عبر متغير بيئة اسمه PORT
    port = int(os.environ.get('PORT', 10000))
    app_web.run(host='0.0.0.0', port=port)

# تشغيل Flask في الخلفية
Thread(target=run_flask).start()

# 2. إعدادات Hugging Face
API_URL = "https://api-inference.huggingface.co/models/ZhengPeng7/BiRefNet"
HF_TOKEN = os.getenv("HF_TOKEN")
headers = {"Authorization": f"Bearer {HF_TOKEN}"}

def query_hugging_face(image_bytes):
    response = requests.post(API_URL, headers=headers, data=image_bytes)
    return response.content

# 3. دالة معالجة الصور (بإصلاح PIL للشفافية)
async def process_and_remove_bg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("⏳ جاري المعالجة...")
    try:
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        
        # طلب المعالجة من هجين
        processed_bytes = query_hugging_face(photo_bytes)
        
        # إصلاح "عطل" الصورة باستخدام PIL
        image = Image.open(io.BytesIO(processed_bytes)).convert("RGBA")
        out_io = io.BytesIO()
        image.save(out_io, format="PNG")
        out_io.seek(0)
        
        await update.message.reply_document(
            document=out_io, 
            filename="no_bg.png", 
            caption="✨ جاهزة وشفافة!"
        )
    except Exception as e:
        print(f"Error: {e}")
        await update.message.reply_text("❌ حدث خطأ، جرب مرة أخرى.")
    finally:
        await status_msg.delete()

# 4. تشغيل البوت مع إعدادات الـ Timeout
if __name__ == '__main__':
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if BOT_TOKEN:
        app = ApplicationBuilder().token(BOT_TOKEN).read_timeout(60).build()
        app.add_handler(MessageHandler(filters.PHOTO, process_and_remove_bg))
        print("🚀 البوت انطلق...")
        app.run_polling()
