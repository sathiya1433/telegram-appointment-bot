import os
import json
import time
import datetime
import requests
import telebot

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not BOT_TOKEN or not GROQ_API_KEY:
    raise RuntimeError("Missing BOT_TOKEN or GROQ_API_KEY")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")
print("✅ Bot started (STABLE VERSION)")

# ================= SESSION STORE =================
sessions = {}
SESSION_TIMEOUT = 300  # 5 minutes

# ================= AI UNDERSTANDING =================
def ai_extract(text):
    today = datetime.date.today().isoformat()

    prompt = f"""
Extract appointment details from user message.

Today: {today}

Message:
"{text}"

Return ONLY JSON:
{{
  "name": null,
  "date": null,
  "time": null
}}

Rules:
- Date must be YYYY-MM-DD
- Time must be HH:MM (24-hour)
- Understand today, tomorrow, next monday, 4pm, 6:30 PM
"""

    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama3-70b-8192",
                "messages": [
                    {"role": "system", "content": "Return strict JSON only."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0
            },
            timeout=15
        )

        content = r.json()["choices"][0]["message"]["content"]
        start = content.find("{")
        end = content.rfind("}") + 1
        if start == -1:
            return {}

        return json.loads(content[start:end])

    except Exception as e:
        print("AI error:", e)
        return {}

# ================= START =================
@bot.message_handler(commands=["start"])
def start(message):
    sessions[message.chat.id] = {
        "name": None,
        "date": None,
        "time": None,
        "last_active": time.time()
    }
    bot.reply_to(message, "👋 Welcome!\nWhat is your name?")

# ================= MESSAGE HANDLER =================
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    chat_id = message.chat.id
    text = message.text.strip()
    now = time.time()

    print("📩", chat_id, text)

    # Expire old session
    if chat_id in sessions and now - sessions[chat_id]["last_active"] > SESSION_TIMEOUT:
        sessions.pop(chat_id)

    if chat_id not in sessions:
        sessions[chat_id] = {
            "name": None,
            "date": None,
            "time": None,
            "last_active": now
        }

    session = sessions[chat_id]
    session["last_active"] = now
    bot.send_chat_action(chat_id, "typing")

    extracted = ai_extract(text)

    # ---- SAFE UPDATES ----
    if extracted.get("name"):
        session["name"] = extracted["name"]
    elif not session["name"]:
        session["name"] = text  # name fallback

    if extracted.get("date"):
        session["date"] = extracted["date"]
    elif session["name"] and not session["date"] and text.lower() != session["name"].lower():
        session["date"] = text  # date fallback

    if extracted.get("time"):
        session["time"] = extracted["time"]
    elif session["date"] and not session["time"] and text.lower() != session["date"].lower():
        session["time"] = text  # time fallback

    # ---- NEXT STEP ----
    if not session["name"]:
        reply = "👤 What is your name?"
    elif not session["date"]:
        reply = f"📅 Hi {session['name']}, which date would you like?"
    elif not session["time"]:
        reply = f"⏰ What time on {session['date']}?"
    else:
        reply = (
            "✅ *Appointment Confirmed!*\n\n"
            f"👤 {session['name']}\n"
            f"📅 {session['date']}\n"
            f"⏰ {session['time']}"
        )
        sessions.pop(chat_id)

    bot.reply_to(message, reply)

# ================= RUN =================
if __name__ == "__main__":
    bot.infinity_polling(skip_pending=True, timeout=60, long_polling_timeout=60)
