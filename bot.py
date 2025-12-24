import telebot
import google.generativeai as genai
import os
import json
import datetime

# --- CONFIGURATION ---
# Get variables from Railway Environment
BOT_TOKEN = os.environ.get('BOT_TOKEN')
GEMINI_KEY = os.environ.get('GEMINI_API_KEY')

# Initialize Bot and AI
bot = telebot.TeleBot(BOT_TOKEN)
genai.configure(api_key=GEMINI_KEY)

print("✅ Bot is starting...")

# --- AI HELPER FUNCTION ---
def parse_with_ai(text):
    """Uses Gemini to extract booking details from natural text"""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        
        prompt = f"""
        Today is: {current_date}
        User said: "{text}"
        
        Extract these details into JSON:
        - name (string or null)
        - date (YYYY-MM-DD or null)
        - time (HH:MM or null)
        
        Return ONLY valid JSON.
        """
        response = model.generate_content(prompt)
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_json)
    except Exception as e:
        print(f"AI Error: {e}")
        return {}

# --- BOT COMMANDS ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "👋 Hello! I am your AI Appointment Bot.\n\n"
                          "Tell me when you want to book (e.g., 'Book John for next Friday at 4pm')")

@bot.message_handler(func=lambda m: True)
def handle_message(message):
    # 1. Send "Typing..." action so user knows bot is thinking
    bot.send_chat_action(message.chat.id, 'typing')
    
    # 2. Process with AI
    data = parse_with_ai(message.text)
    
    # 3. Formulate reply based on what is missing
    if not data.get('name'):
        reply = "I need your name to confirm the booking."
    elif not data.get('date'):
        reply = f"Hi {data['name']}, what date would you like?"
    elif not data.get('time'):
        reply = f"Okay {data['name']}, what time on {data['date']}?"
    else:
        reply = (f"✅ **Booking Confirmed!**\n\n"
                 f"👤 Name: {data['name']}\n"
                 f"📅 Date: {data['date']}\n"
                 f"⏰ Time: {data['time']}")
    
    bot.reply_to(message, reply, parse_mode='Markdown')

# --- RUN BOT ---
# infinity_polling is best for 24/7 uptime on Railway
if __name__ == "__main__":
    bot.infinity_polling()
