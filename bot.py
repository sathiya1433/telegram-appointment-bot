import os
import json
import datetime
import telebot
from google import genai

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not BOT_TOKEN or not GEMINI_API_KEY:
    raise Exception("❌ BOT_TOKEN or GEMINI_API_KEY missing")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")
client = genai.Client(api_key=GEMINI_API_KEY)

print("✅ Bot started")

# ================= MEMORY =================
user_sessions = {}

# ================= AI FUNCTION =================
def ai_extract(user_text, memory):
    today = datetime.date.today().isoformat()

    prompt = f"""
You are an AI appointment booking assistant.

Today date: {today}

Current data:
{json.dumps(memory)}

User message:
"{user_text}"

TASK:
- Extract name, date, time if present
- Convert date to YYYY-MM-DD
- Convert time to HH:MM (24-hour)
- Handle words like today, tomorrow, next monday
- If info is missing, do not invent
- Return ONLY valid JSON
- No explanations

JSON format:
{{
  "name": "",
  "date": "",
  "time": ""
}}
"""

    try:
        response = client.models.generate_content(
            model="gemini-1.5-pro",
            contents=prompt
        )
        text = response.text.strip()

        start = text.find("{")
        end = text.rfind("}") + 1
        if start == -1 or end == -1:
            return {}

        data = json.loads(text[start:end])

        # Remove empty values
        return {k: v for k, v in data.items() if v}

    except Exception as e:
        print("❌ AI ERROR:", e)
        return {}

# ================= START =================
@bot.message_handler(commands=["start"])
def start(message):
    user_sessions[message.chat.id] = {}
    bot.reply_to(
        message,
        "👋 *Welcome!*\n\n"
        "Just tell me your appointment details.\n"
        "_Example: Book tomorrow at 5 PM_"
    )

# ================= MESSAGE HANDLER =================
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    chat_id = message.chat.id
    text = message.text.strip()

    print("📩 RECEIVED:", text)

    if chat_id not in user_sessions:
        user_sessions[chat_id] = {}

    session = user_sessions[chat_id]

    bot.send_chat_action(chat_id, "typing")

    extracted = ai_extract(text, session)

    # Update session from AI
    session.update(extracted)

    # Decide next question
    if "name" not in session:
        reply = "👤 What is your name?"
    elif "date" not in session:
        reply = f"📅 Hi {session['name']}, which date would you like?"
    elif "time" not in session:
        reply = f"⏰ What time on {session['date']}?"
    else:
        reply = (
            "✅ *Appointment Confirmed!*\n\n"
            f"👤 Name: {session['name']}\n"
            f"📅 Date: {session['date']}\n"
            f"⏰ Time: {session['time']}"
        )
        user_sessions[chat_id] = {}  # reset after booking

    bot.reply_to(message, reply)

# ================= RUN =================
if __name__ == "__main__":
    bot.infinity_polling(
        skip_pending=True,
        timeout=60,
        long_polling_timeout=60
    )
