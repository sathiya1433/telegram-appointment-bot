import telebot
import google.generativeai as genai
import os
import json
import datetime
import re

# ================== CONFIG ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not BOT_TOKEN or not GEMINI_API_KEY:
    raise Exception("BOT_TOKEN or GEMINI_API_KEY missing")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")
genai.configure(api_key=GEMINI_API_KEY)

print("✅ Bot started")

# ================== MEMORY ==================
user_data = {}

# ================== AI PARSER ==================
def parse_with_ai(user_text, memory):
    try:
        model = genai.GenerativeModel("gemini-pro")
        today = datetime.date.today().isoformat()

        prompt = f"""
You are an AI appointment booking assistant.

Today date: {today}

Current booking data:
{json.dumps(memory)}

User message:
"{user_text}"

TASK:
Extract booking info.

RULES:
- Extract name if present
- Extract date and convert to YYYY-MM-DD
  (today, tomorrow, next friday, etc.)
- Extract time and convert to HH:MM 24-hour format
- Return ONLY JSON
- If nothing found, return {{}}

JSON FORMAT:
{{
  "name": "",
  "date": "",
  "time": ""
}}
"""

        response = model.generate_content(prompt)
        text = response.text.strip()

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return {}

        return json.loads(match.group())

    except Exception as e:
        print("AI ERROR:", e)
        return {}

# ================== START COMMAND ==================
@bot.message_handler(commands=["start"])
def start(message):
    user_data[message.chat.id] = {}
    bot.reply_to(
        message,
        "👋 *Welcome!*\n\n"
        "You can say:\n"
        "`Book tomorrow at 6 PM`\n"
        "or just send details one by one 😊"
    )

# ================== MESSAGE HANDLER ==================
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    chat_id = message.chat.id
    text = message.text.strip()

    if chat_id not in user_data:
        user_data[chat_id] = {}

    memory = user_data[chat_id]
    bot.send_chat_action(chat_id, "typing")

    extracted = parse_with_ai(text, memory)

    # Update memory ONLY from AI
    for key in ["name", "date", "time"]:
        if extracted.get(key):
            memory[key] = extracted[key]

    # Conversation flow
    if "name" not in memory:
        reply = "👤 What is your name?"
    elif "date" not in memory:
        reply = "📅 Which date would you like?"
    elif "time" not in memory:
        reply = f"⏰ What time on {memory['date']}?"
    else:
        reply = (
            "✅ *Appointment Confirmed!*\n\n"
            f"👤 Name: {memory['name']}\n"
            f"📅 Date: {memory['date']}\n"
            f"⏰ Time: {memory['time']}"
        )
        user_data[chat_id] = {}

    bot.reply_to(message, reply)

# ================== RUN ==================
if __name__ == "__main__":
    bot.infinity_polling(
        skip_pending=True,
        timeout=30,
        long_polling_timeout=30
    )
