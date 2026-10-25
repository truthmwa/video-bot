import os
import telebot
import fitz  # PyMuPDF
from mutagen.mp3 import MP3
from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip

BOT_TOKEN = "8573139251:AAHoQDqjJvHVbmB_eeUM7QBiwK4lPfHcHnM"
bot = telebot.TeleBot(BOT_TOKEN)

user_data = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "नमस्ते! मुझे अपनी PDF फाइल और Audio (MP3) फाइल भेजिए। दोनों मिलते ही वीडियो बनना शुरू हो जाएगा।")

@bot.message_handler(content_types=['document', 'audio'])
def handle_files(message):
    chat_id = message.chat.id
    os.makedirs(f"temp_{chat_id}", exist_ok=True)
    
    if chat_id not in user_data:
        user_data[chat_id] = {}

    if message.content_type == 'document' and message.document.file_name and message.document.file_name.lower().endswith('.pdf'):
        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        pdf_path = f"temp_{chat_id}/input.pdf"
        with open(pdf_path, 'wb') as f:
            f.write(downloaded)
        user_data[chat_id]['pdf'] = pdf_path
        bot.reply_to(message, "✅ PDF फाइल मिल गई!")

    elif message.content_type in ['audio', 'document']:
        file_id = message.audio.file_id if message.audio else message.document.file_id
        file_info = bot.get_file(file_id)
        downloaded = bot.download_file(file_info.file_path)
        audio_path = f"temp_{chat_id}/audio.mp3"
        with open(audio_path, 'wb') as f:
            f.write(downloaded)
        user_data[chat_id]['audio'] = audio_path
        bot.reply_to(message, "✅ Audio फाइल मिल गई!")

    if 'pdf' in user_data[chat_id] and 'audio' in user_data[chat_id]:
        bot.send_message(chat_id, "⏳ दोनों फाइलें मिल चुकी हैं! वीडियो रेंडर हो रहा है, कृपया 1-2 मिनट इंतज़ार करें...")
        
        try:
            pdf_path = user_data[chat_id]['pdf']
            audio_path = user_data[chat_id]['audio']
            output_video = f"temp_{chat_id}/output.mp4"
            
            doc = fitz.open(pdf_path)
            images = []
            for i, page in enumerate(doc):
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img_path = f"temp_{chat_id}/slide_{i}.png"
                pix.save(img_path)
                images.append(img_path)
            
            audio_info = MP3(audio_path)
            time_per_slide = audio_info.info.length / len(images)
            
            clips = [ImageClip(img).set_duration(time_per_slide) for img in images]
            final_clip = concatenate_videoclips(clips, method="compose")
            final_clip = final_clip.set_audio(AudioFileClip(audio_path))
            final_clip.write_videofile(output_video, fps=24, codec="libx264", audio_codec="aac")
            
            bot.send_message(chat_id, "📤 वीडियो तैयार है! अपलोड की जा रही है...")
            with open(output_video, 'rb') as video_file:
                bot.send_video(chat_id, video_file, caption="आपकी तैयार वीडियो! 🎬")
            
            import shutil
            shutil.rmtree(f"temp_{chat_id}")
            user_data[chat_id] = {}

        except Exception as e:
            bot.send_message(chat_id, f"त्रुटि हुई: {str(e)}")

print("Bot is running...")
bot.infinity_polling()
