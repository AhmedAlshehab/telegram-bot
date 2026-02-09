import os
import io
import threading
import logging
from flask import Flask
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler
from PIL import Image
import requests

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN')
HF_TOKEN = os.getenv('HF_TOKEN')
HF_API_URL = "https://api-inference.huggingface.co/models/levihsu/BiRefNet"

# Flask app for keeping the server alive (for Render deployment)
app = Flask(__name__)

@app.route('/')
def home():
    return "Telegram Bot is running!", 200

def run_flask():
    """Run Flask server on port 10000"""
    app.run(host='0.0.0.0', port=10000, debug=False, use_reloader=False)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when the command /start is issued."""
    welcome_text = (
        "👋 Welcome to Background Remover Bot!\n\n"
        "I can remove backgrounds from your images using AI.\n\n"
        "Just send me any image (as photo or document) and I'll remove the background for you!\n\n"
        "I'll send back a PNG image with perfect transparency."
    )
    await update.message.reply_text(welcome_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a help message when the command /help is issued."""
    help_text = (
        "📖 How to use:\n"
        "1. Send me any image (as a photo or document)\n"
        "2. I'll process it and remove the background\n"
        "3. I'll send back a transparent PNG\n\n"
        "💡 Tips:\n"
        "- For best results, use clear images with distinct subjects\n"
        "- Large images may take longer to process\n"
        "- The result will be sent as a document to preserve quality"
    )
    await update.message.reply_text(help_text)

async def remove_background_hf(image_bytes):
    """Remove background using Hugging Face API"""
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    
    try:
        response = requests.post(
            HF_API_URL, 
            headers=headers, 
            data=image_bytes,
            timeout=60
        )
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        logger.error(f"Hugging Face API error: {e}")
        raise

async def process_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process incoming images"""
    user = update.effective_user
    
    # Send processing message
    processing_msg = await update.message.reply_text(
        "🔄 Processing your image... Please wait."
    )
    
    try:
        # Get the photo or document
        if update.message.photo:
            # Get the highest quality photo
            photo_file = await update.message.photo[-1].get_file()
            image_bytes = await photo_file.download_as_bytearray()
        elif update.message.document and update.message.document.mime_type.startswith('image/'):
            # Get the document
            doc_file = await update.message.document.get_file()
            image_bytes = await doc_file.download_as_bytearray()
        else:
            await update.message.reply_text(
                "⚠️ Please send an image (as a photo or image document)."
            )
            return
        
        # Process the image
        await processing_msg.edit_text("🎨 Removing background...")
        
        # Call Hugging Face API
        result_bytes = await remove_background_hf(bytes(image_bytes))
        
        if not result_bytes:
            await processing_msg.edit_text("❌ Failed to process image. Please try again.")
            return
        
        # Process with PIL
        await processing_msg.edit_text("📝 Finalizing image...")
        
        # Open the result image
        result_image = Image.open(io.BytesIO(result_bytes))
        
        # Ensure RGBA mode for transparency
        if result_image.mode != 'RGBA':
            result_image = result_image.convert('RGBA')
        
        # Save to bytes as high-quality PNG
        output_buffer = io.BytesIO()
        result_image.save(output_buffer, format='PNG', optimize=True, quality=100)
        output_buffer.seek(0)
        
        # Delete processing message
        await processing_msg.delete()
        
        # Send the result as document (to avoid compression)
        await update.message.reply_document(
            document=output_buffer,
            filename=f"no_bg_{user.id}.png",
            caption="✅ Background removed successfully!",
            read_timeout=60,
            write_timeout=60,
            connect_timeout=60
        )
        
        logger.info(f"Successfully processed image for user {user.id}")
        
    except Exception as e:
        logger.error(f"Error processing image for user {user.id}: {str(e)}", exc_info=True)
        
        # Update or delete processing message
        try:
            await processing_msg.edit_text(
                "❌ An error occurred while processing your image. "
                "Please try again with a different image."
            )
        except:
            await update.message.reply_text(
                "❌ An error occurred while processing your image. "
                "Please try again with a different image."
            )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors and handle them gracefully"""
    logger.error(f"Update {update} caused error {context.error}", exc_info=True)
    
    # Try to send error message to user
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ An unexpected error occurred. Please try again later."
            )
        except:
            pass

def main():
    """Start the bot."""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN environment variable is not set!")
        return
    if not HF_TOKEN:
        logger.error("HF_TOKEN environment variable is not set!")
        return
    
    # Start Flask server in a separate thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("Flask server started on port 10000")
    
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(
        filters.PHOTO | filters.Document.IMAGE, 
        process_image
    ))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    # Start the Bot with polling
    logger.info("Bot is starting...")
    
    # Configure polling with timeouts and drop pending updates
        # الكود الصحيح والمختصر
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )

if __name__ == '__main__':
    main()
