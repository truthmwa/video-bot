import os
import shutil
import telebot
import fitz  # PyMuPDF
from mutagen.mp3 import MP3
from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip

BOT_TOKEN = "8573139251:AAHoQDqjJvHVbmB_eeUM7QBiwK4lPfHcHnM"
bot = telebot.TeleBot(BOT_TOKEN, threaded=True)

user_data = {}

@bot.message_handler(commands=['start', 'reset'])
def send_welcome(message):
    chat_id = message.chat.id
    user_data[chat_id] = {}
    bot.reply_to(message, "नमस्ते! मुझे अपनी PDF और MP3 Audio फाइल भेजिए। दोनों आते ही वीडियो प्रोसेसिंग शुरू हो जाएगी।")

@bot.message_handler(content_types=['document', 'audio', 'voice'])
def handle_files(message):
    chat_id = message.chat.id
    temp_dir = f"temp_{chat_id}"
    os.makedirs(temp_dir, exist_ok=True)
    
    if chat_id not in user_data:
        user_data[chat_id] = {}

    try:
        # 1. PDF Handling
        if message.content_type == 'document' and message.document.file_name and message.document.file_name.lower().endswith('.pdf'):
            bot.reply_to(message, "⏳ PDF डाउनलोड हो रही है...")
            file_info = bot.get_file(message.document.file_id)
            downloaded = bot.download_file(file_info.file_path)
            pdf_path = os.path.join(temp_dir, "input.pdf")
            with open(pdf_path, 'wb') as f:
                f.write(downloaded)
            user_data[chat_id]['pdf'] = pdf_path
            bot.reply_to(message, "✅ PDF सुरक्षित सेव हो गई!")

        # 2. Audio Handling
        elif message.content_type in ['audio', 'voice'] or (message.content_type == 'document' and message.document.mime_type and 'audio' in message.document.mime_type):
            bot.reply_to(message, "⏳ ऑडियो डाउनलोड हो रही है, कृपया 10-20 सेकंड प्रतीक्षा करें...")
            file_id = message.audio.file_id if message.audio else (message.voice.file_id if message.voice else message.document.file_id)
            file_info = bot.get_file(file_id)
            downloaded = bot.download_file(file_info.file_path)
            audio_path = os.path.join(temp_dir, "audio.mp3")
            with open(audio_path, 'wb') as f:
                f.write(downloaded)
            user_data[chat_id]['audio'] = audio_path
            bot.reply_to(message, "✅ ऑडियो फाइल सुरक्षित सेव हो गई!")

        # 3. Processing Start
        if 'pdf' in user_data[chat_id] and 'audio' in user_data[chat_id]:
            bot.send_message(chat_id, "🎬 दोनों फाइलें मिल चुकी हैं! वीडियो रेंडरिंग शुरू हो रही है...\n(30+ मिनट के वीडियो में रेंडरिंग में 3-5 मिनट लग सकते हैं, कृपया इंतज़ार करें)")
            
            pdf_path = user_data[chat_id]['pdf']
            audio_path = user_data[chat_id]['audio']
            output_video = os.path.join(temp_dir, "output.mp4")

            # Extract Slides
            doc = fitz.open(pdf_path)
            images = []
            for i, page in enumerate(doc):
                pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
                img_path = os.path.join(temp_dir, f"slide_{i}.png")
                pix.save(img_path)
                images.append(img_path)

            # Audio Duration & Clips
            audio_info = MP3(audio_path)
            time_per_slide = audio_info.info.length / len(images)

            clips = [ImageClip(img).set_duration(time_per_slide) for img in images]
            final_clip = concatenate_videoclips(clips, method="compose")
            final_clip = final_clip.set_audio(AudioFileClip(audio_path))

            # Fast Render Settings
            final_clip.write_videofile(
                output_video,
                fps=15,
                codec="libx264",
                preset="ultrafast",
                audio_codec="aac"
            )

            bot.send_message(chat_id, "📤 वीडियो रेंडर हो गई है! अब टेलीग्राम पर भेजी जा रही है...")
            with open(output_video, 'rb') as vf:
                bot.send_video(chat_id, vf, caption="लीजिए, आपकी फ़ाइनल वीडियो तैयार है! 🎉", timeout=300)

            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)
            user_data[chat_id] = {}

    except Exception as e:
        bot.send_message(chat_id, f"⚠️ एरर आया: {str(e)}\nकृप्या /reset दबाकर दोबारा भेजें।")

print("Bot is up and polling...")
bot.infinity_polling(timeout=60, long_polling_timeout=60)
