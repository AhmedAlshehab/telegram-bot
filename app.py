import os
import io
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from flask import Flask
from threading import Thread

# 1. إعداد سيرفر الويب الصغير لـ Render
app_web = Flask('')
@app_web.route('/')
def home():
    return "AI Bot is Live and linked to Hugging Face!"

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app_web.run(host='0.0.0.0', port=port)

Thread(target=run_flask).start()

# 2. إعدادات الربط مع Hugging Face (المصنع)
# تأكد أنك أضفت HF_TOKEN في إعدادات Render
API_URL = "https://api-inference.huggingface.co/models/ZhengPeng7/BiRefNet"
HF_TOKEN = os.getenv("HF_TOKEN")
headers = {"Authorization": f"Bearer {HF_TOKEN}"}

def query_hugging_face(image_bytes):
    response = requests.post(API_URL, headers=headers, data=image_bytes)
    return response.content

async def process_and_remove_bg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("⏳ جاري المعالجة بدقة عالية...")
    try:
        # 1. تحميل الصورة من تليجرام
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        
        # 2. إرسالها لـ Hugging Face
        processed_image_bytes = query_hugging_face(photo_bytes)
        
        # 3. التأكد من سلامة الملف الناتج (إعادة تهيئة البايتات كصورة PNG سليمة)
        image = Image.open(io.BytesIO(processed_image_bytes)).convert("RGBA")
        
        out_io = io.BytesIO()
        # حفظ الصورة بصيغة PNG مع التأكد من حفظ قناة الشفافية (Alpha)
        image.save(out_io, format="PNG", optimize=True)
        out_io.seek(0)
        
        # 4. إرسال الملف مع تحديد الاسم والنوع لضمان عدم حدوث عطل عند الفتح
        await update.message.reply_document(
            document=out_io, 
            filename="transparent_result.png",
            caption="✨ تفضل الصورة شفافة وجاهزة للاستخدام!"
        )
        
    except Exception as e:
        print(f"Error: {e}")
        await update.message.reply_text("❌ حدث خطأ في معالجة الملف، حاول مرة أخرى.")
    finally:
        await status_msg.delete()


if __name__ == '__main__':
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if BOT_TOKEN:
        app = ApplicationBuilder().token(BOT_TOKEN).build()
        app.add_handler(MessageHandler(filters.PHOTO, process_and_remove_bg))
        print("🚀 البوت يعمل الآن بالربط الهجين...")
        app.run_polling()
