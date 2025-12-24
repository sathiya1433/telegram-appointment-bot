import os
import json
import datetime
import telebot
import google.generativeai as genai

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not BOT_TOKEN or not GEMINI_API_KEY:
    raise RuntimeError("BOT_TOKEN or GEMINI_API_KEY missing")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")
genai.configure(api_key=GEMINI_API_KEY)

print("✅ Bot started")

# ================= MEMORY =================
# Each user has a session with explicit state
sessions = {}

# ================= AI EXTRACTION =================
def ai_extract(text, session):
    today = datetime.date.today().isoformat()

    prompt = f"""
You are an appointment information extractor.

Today: {today}

Current data:
{json.dumps(session)}

User message:
"{text}"

TASK:
- Extract name, date, time IF PRESENT
- Date format: YYYY-MM-DD
- Time format: HH:MM (24-hour)
- Handle: today, tomorrow, next monday
- If missing, return null
- Return ONLY JSON

JSON:
{{
  "name": null,
  "date": null,
  "time": null
}}
"""

    try:
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(prompt)
        raw = response.text.strip()

        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start == -1 or end == -1:
            return {}

        data = json.loads(raw[start:end])
        return {k: v for k, v in data.items() if v}

    except Exception as e:
        print("AI ERROR:", e)
        return {}

# ================= START =================
@bot.message_handler(commands=["start"])
def start(message):
    sessions[message.chat.id] = {
        "name": None,
        "date": None,
        "time": None,
        "expecting": "name"
    }
    bot.reply_to(
        message,
        "👋 *Welcome!*\n\n"
        "I will help you book an appointment.\n"
        "Let’s start — what is your name?"
    )

# ================= MESSAGE HANDLER =================
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    chat_id = message.chat.id
    text = message.text.strip()

    print("📩", chat_id, text)

    if chat_id not in sessions:
        sessions[chat_id] = {
            "name": None,
            "date": None,
            "time": None,
            "expecting": "name"
        }

    session = sessions[chat_id]
    bot.send_chat_action(chat_id, "typing")

    # 1️⃣ AI extracts meaning
    extracted = ai_extract(text, session)

    # 2️⃣ Update session from AI
    for key in ["name", "date", "time"]:
        if extracted.get(key):
            session[key] = extracted[key]

    # 3️⃣ HARD STATE LOGIC (NO AI CONTROL)
    if session["expecting"] == "name" and not session["name"]:
        session["name"] = text

    elif session["expecting"] == "date" and not session["date"]:
        if extracted.get("date"):
            session["date"] = extracted["date"]
        else:
            bot.reply_to(
                message,
                "📅 Please tell the date clearly.\nExample: `tomorrow` or `2025-01-25`"
            )
            return

    elif session["expecting"] == "time" and not session["time"]:
        if extracted.get("time"):
            session["time"] = extracted["time"]
        else:
            bot.reply_to(
                message,
                "⏰ Please tell the time clearly.\nExample: `4:30 PM` or `16:30`"
            )
            return

    # 4️⃣ Decide next step
    if not session["name"]:
        session["expecting"] = "name"
        reply = "👤 What is your name?"

    elif not session["date"]:
        session["expecting"] = "date"
        reply = f"📅 Hi *{session['name']}*, which date would you like?"

    elif not session["time"]:
        session["expecting"] = "time"
        reply = f"⏰ What time on *{session['date']}*?"

    else:
        reply = (
            "✅ *Appointment Confirmed!*\n\n"
            f"👤 Name: {session['name']}\n"
            f"📅 Date: {session['date']}\n"
            f"⏰ Time: {session['time']}"
        )
        sessions.pop(chat_id, None)  # clear after booking

    bot.reply_to(message, reply)

# ================= RUN =================
if __name__ == "__main__":
    bot.infinity_polling(
        skip_pending=True,
        timeout=90,
        long_polling_timeout=90
    )
