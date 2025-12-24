import telebot
import google.generativeai as genai
import os
import json
import datetime
import re # Added for robust text cleaning

# --- CONFIGURATION ---
BOT_TOKEN = os.environ.get('BOT_TOKEN')
GEMINI_KEY = os.environ.get('GEMINI_API_KEY')

bot = telebot.TeleBot(BOT_TOKEN)
genai.configure(api_key=GEMINI_KEY)

# --- MEMORY ---
user_data = {}

print("✅ Bot is starting... (Robust Version)")

# --- AI HELPER (Fixed) ---
def parse_with_ai(text):
    try:
        # 1. Force JSON mode
        model = genai.GenerativeModel('gemini-1.5-flash', 
                                      generation_config={"response_mime_type": "application/json"})
        
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        
        prompt = f"""
        Current Date: {current_date}
        User Input: "{text}"
        
        Extract details. Return ONLY a JSON object.
        fields: name, date (YYYY-MM-DD), time (HH:MM).
        Set missing fields to null.
        """
        
        response = model.generate_content(prompt)
        raw_text = response.text
        
        # 2. Safety Filter (Regex) - Finds the JSON object inside any text
        # This fixes the crash if AI adds "Here is the data..."
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        
        if match:
            clean_json = match.group()
            return json.loads(clean_json)
        else:
            print(f"⚠️ AI returned invalid format: {raw_text}")
            return {}

    except Exception as e:
        # 3. Print the EXACT error to Railway logs so you can see it
        print(f"❌ CRITICAL AI ERROR: {e}")
        return {}

# --- COMMANDS ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_data[message.chat.id] = {} # Reset memory
    bot.reply_to(message, "👋 Hello! I am your AI Appointment Bot.\n\n"
                          "Tell me when you want to book (e.g., 'Book next Friday at 4pm')")

@bot.message_handler(func=lambda m: True)
def handle_message(message):
    chat_id = message.chat.id
    
    # Initialize memory if empty
    if chat_id not in user_data:
        user_data[chat_id] = {}
        
    bot.send_chat_action(chat_id, 'typing')
    
    # Process with AI
    new_info = parse_with_ai(message.text)
    
    # Debugging: Print to Railway logs what the AI found
    print(f"User: {message.text} | AI Found: {new_info}")

    # Update Memory
    if new_info.get('name'): user_data[chat_id]['name'] = new_info['name']
    if new_info.get('date'): user_data[chat_id]['date'] = new_info['date']
    if new_info.get('time'): user_data[chat_id]['time'] = new_info['time']
    
    # Check what is missing
    current = user_data[chat_id]
    
    if not current.get('name'):
        reply = "I need your name to confirm the booking."
    elif not current.get('date'):
        reply = f"Hi {current['name']}, what date would you like?"
    elif not current.get('time'):
        reply = f"Okay {current['name']}, what time on {current['date']}?"
    else:
        reply = (f"✅ **Booking Confirmed!**\n\n"
                 f"👤 Name: {current['name']}\n"
                 f"📅 Date: {current['date']}\n"
                 f"⏰ Time: {current['time']}")
        user_data[chat_id] = {} # Reset after success
    
    bot.reply_to(message, reply, parse_mode='Markdown')

if __name__ == "__main__":
    bot.infinity_polling()
