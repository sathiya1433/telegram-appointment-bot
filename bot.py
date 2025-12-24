import telebot
import google.generativeai as genai
import os
import json
import datetime

# --- CONFIGURATION ---
BOT_TOKEN = os.environ.get('BOT_TOKEN')
GEMINI_KEY = os.environ.get('GEMINI_API_KEY')

bot = telebot.TeleBot(BOT_TOKEN)
genai.configure(api_key=GEMINI_KEY)

# --- MEMORY (The Fix) ---
# This dictionary will store data: {chat_id: {'name': 'John', 'date': '...', 'time': '...'}}
user_data = {}

print("✅ Bot is starting...")

# --- AI HELPER ---
def parse_with_ai(text):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # Improved prompt to handle single words like "Sathiya"
        prompt = f"""
        Current Date: {current_date}
        User Input: "{text}"
        
        You are a booking assistant. Extract any of these details if present:
        - name (Look for proper nouns or "I am X")
        - date (YYYY-MM-DD)
        - time (HH:MM)
        
        Return JSON with null for missing fields. 
        Example: {{"name": "Sathiya", "date": null, "time": null}}
        """
        response = model.generate_content(prompt)
        clean_text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_text)
    except Exception as e:
        print(f"AI Error: {e}")
        return {}

# --- COMMANDS ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    # Clear memory on start
    user_data[message.chat.id] = {}
    bot.reply_to(message, "👋 Hello! I am your AI Appointment Bot.\n\n"
                          "Tell me when you want to book (e.g., 'Book next Friday at 4pm')")

@bot.message_handler(func=lambda m: True)
def handle_message(message):
    chat_id = message.chat.id
    
    # 1. Initialize memory if new user
    if chat_id not in user_data:
        user_data[chat_id] = {}
        
    bot.send_chat_action(chat_id, 'typing')
    
    # 2. Get new info from AI
    new_info = parse_with_ai(message.text)
    
    # 3. UPDATE MEMORY (Merge new info with old info)
    # Only overwrite if the AI found something new (not null)
    if new_info.get('name'): 
        user_data[chat_id]['name'] = new_info['name']
    if new_info.get('date'): 
        user_data[chat_id]['date'] = new_info['date']
    if new_info.get('time'): 
        user_data[chat_id]['time'] = new_info['time']
    
    # 4. Check what is STILL missing from memory
    current_data = user_data[chat_id]
    
    if not current_data.get('name'):
        reply = "I need your name to confirm the booking."
    elif not current_data.get('date'):
        reply = f"Hi {current_data['name']}, what date would you like?"
    elif not current_data.get('time'):
        reply = f"Okay {current_data['name']}, what time on {current_data['date']}?"
    else:
        # Success!
        reply = (f"✅ **Booking Confirmed!**\n\n"
                 f"👤 Name: {current_data['name']}\n"
                 f"📅 Date: {current_data['date']}\n"
                 f"⏰ Time: {current_data['time']}")
        # Clear memory after success so they can book again
        user_data[chat_id] = {}
    
    bot.reply_to(message, reply, parse_mode='Markdown')

if __name__ == "__main__":
    bot.infinity_polling()
