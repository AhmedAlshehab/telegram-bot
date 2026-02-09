import os
import io
import torch
import nest_asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from transformers import AutoModelForImageSegmentation
from torchvision import transforms
from PIL import Image
# --- إضافة هذه المكتبات الجديدة للحل ---
from threading import Thread
from flask import Flask

# 1. تشغيل سيرفر ويب صغير جداً في الخلفية لإرضاء Render
web_app = Flask('')
@web_app.route('/')
def home():
    return "Bot is Running Live!"

def run_web_server():
    port = int(os.environ.get('PORT', 10000))
    web_app.run(host='0.0.0.0', port=port)

# بدء تشغيل السيرفر في "خيط" منفصل (Thread)
Thread(target=run_web_server).start()

# --- بقية كودك الأصلي كما هو ---
nest_asyncio.apply()

print("⏳ Loading AI Model (BiRefNet)...")
device = "cuda" if torch.cuda.is_available() else "cpu"
model = AutoModelForImageSegmentation.from_pretrained("ZhengPeng7/BiRefNet", trust_remote_code=True)
model.to(device)
model.eval()

transform_image = transforms.Compose([
    transforms.Resize((1024, 1024)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

async def process_and_remove_bg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("⏳ جاري تنقية الصورة... يرجى الانتظار")
    try:
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        input_image = Image.open(io.BytesIO(photo_bytes)).convert("RGB")
        original_size = input_image.size

        input_tensor = transform_image(input_image).unsqueeze(0).to(device)
        if device == "cuda":
            input_tensor = input_tensor.to(model.dtype)

        with torch.no_grad():
            preds = model(input_tensor)[-1].sigmoid().cpu()
        
        mask = transforms.ToPILImage()(preds[0].float().squeeze())
        mask = mask.resize(original_size)
        input_image.putalpha(mask)
        
        out_io = io.BytesIO()
        input_image.save(out_io, 'PNG')
        out_io.seek(0)
        await update.message.reply_document(document=out_io, filename="no_bg.png", caption="✨ تم التخلص من الخلفية بنجاح!")
    except Exception as e:
        await update.message.reply_text(f"❌ حدث خطأ أثناء المعالجة: {str(e)}")
    finally:
        await status_msg.delete()

if __name__ == '__main__':
    # تأكد من إضافة BOT_TOKEN في إعدادات Render (Environment Variables)
    TOKEN = os.getenv("BOT_TOKEN") 
    if not TOKEN:
        print("❌ Error: BOT_TOKEN not found!")
    else:
        app = ApplicationBuilder().token(TOKEN).build()
        app.add_handler(MessageHandler(filters.PHOTO, process_and_remove_bg))
        print("🚀 البوت يعمل الآن...")
        app.run_polling(close_loop=False)
        input_image = Image.open(io.BytesIO(photo_bytes)).convert("RGB")
        original_size = input_image.size

        # المعالجة بالذكاء الاصطناعي
        input_tensor = transform_image(input_image).unsqueeze(0).to(device)
        if device == "cuda":
            input_tensor = input_tensor.to(model.dtype)

        with torch.no_grad():
            preds = model(input_tensor)[-1].sigmoid().cpu()
        
        mask = transforms.ToPILImage()(preds[0].float().squeeze())
        mask = mask.resize(original_size)
        
        # تطبيق الشفافية
        input_image.putalpha(mask)
        
        # تحويل النتيجة لملف لإرساله
        out_io = io.BytesIO()
        input_image.save(out_io, 'PNG')
        out_io.seek(0)

        await update.message.reply_document(document=out_io, filename="no_bg.png", caption="✨ تم التخلص من الخلفية بنجاح!")
    except Exception as e:
        await update.message.reply_text(f"❌ حدث خطأ أثناء المعالجة: {str(e)}")
    finally:
        await status_msg.delete()

# 3. تشغيل البوت
if __name__ == '__main__':
    TOKEN = os.getenv("BOT_TOKEN") # سيتم جلبه من إعدادات Render
    if not TOKEN:
        print("❌ Error: BOT_TOKEN not found in environment variables!")
    else:
        app = ApplicationBuilder().token(TOKEN).build()
        app.add_handler(MessageHandler(filters.PHOTO, process_and_remove_bg))
        print("🚀 البوت يعمل الآن...")
        app.run_polling(close_loop=False)
