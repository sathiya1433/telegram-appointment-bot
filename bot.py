import telebot
import google.generativeai as genai
import os
import json
import datetime
import re

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

if not BOT_TOKEN or not GEMINI_KEY:
    raise Exception("❌ BOT_TOKEN or GEMINI_API_KEY not set")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")
genai.configure(api_key=GEMINI_KEY)

print("✅ Bot started successfully")

# ================= MEMORY =================
user_data = {}

# ================= AI PARSER =================
def parse_with_ai(user_text, memory):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        today = datetime.date.today().isoformat()

        prompt = f"""
Today date: {today}

Current booking data:
{json.dumps(memory)}

User message:
"{user_text}"

Extract ONLY these fields if present:
- name
- date (YYYY-MM-DD)
- time (HH:MM 24h)

Return STRICT JSON only.
If nothing found, return empty JSON {{}}.
"""

        response = model.generate_content(prompt)
        text = response.text.strip()

        # Extract JSON safely
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return {}

        return json.loads(match.group())

    except Exception as e:
        print("AI error:", e)
        return {}

# ================= COMMANDS =================
@bot.message_handler(commands=["start"])
def start(message):
    user_data[message.chat.id] = {}
    bot.reply_to(
        message,
        "👋 *Welcome!*\n\n"
        "You can say something like:\n"
        "`Book an appointment next Friday at 4 PM`\n\n"
        "Let’s start 😊"
    )

# ================= MESSAGE HANDLER =================
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    chat_id = message.chat.id
    text = message.text.strip()

    if chat_id not in user_data:
        user_data[chat_id] = {}

    bot.send_chat_action(chat_id, "typing")

    memory = user_data[chat_id]

    # ---- AI Extraction ----
    extracted = parse_with_ai(text, memory)

    # ---- Update Memory ----
    for key in ["name", "date", "time"]:
        if extracted.get(key):
            memory[key] = extracted[key]

    # ---- Manual fallback for NAME ----
    if "name" not in memory and len(text.split()) <= 3:
        memory["name"] = text

    # ---- Conversation Flow ----
    if "name" not in memory:
        reply = "👤 What is your name?"
    elif "date" not in memory:
        reply = f"📅 Hi *{memory['name']}*, which date do you want?"
    elif "time" not in memory:
        reply = f"⏰ What time on *{memory['date']}*?"
    else:
        reply = (
            "✅ *Booking Confirmed!*\n\n"
            f"👤 Name: {memory['name']}\n"
            f"📅 Date: {memory['date']}\n"
            f"⏰ Time: {memory['time']}"
        )
        user_data[chat_id] = {}  # Reset after booking

    bot.reply_to(message, reply)

# ================= RUN =================
if __name__ == "__main__":
    bot.infinity_polling(skip_pending=True)
