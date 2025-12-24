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
    raise RuntimeError("BOT_TOKEN or GROQ_API_KEY missing")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")
print("✅ Bot started (FINAL FIXED VERSION)")

# ================= MEMORY =================
sessions = {}
SESSION_TIMEOUT = 300  # 5 minutes

# ================= GROQ AI =================
def ai_extract(text, session):
    today = datetime.date.today().isoformat()

    prompt = f"""
You extract appointment information.

Today: {today}

Known data:
{json.dumps(session)}

User message:
"{text}"

Extract if present:
- name
- date (YYYY-MM-DD)
- time (HH:MM 24h)

Handle: today, tomorrow, next monday, 4pm, 6:30 PM

Return ONLY JSON:
{{
  "name": null,
  "date": null,
  "time": null
}}
"""

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama3-70b-8192",
                "messages": [
                    {"role": "system", "content": "Return only JSON."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0
            },
            timeout=15
        )

        content = response.json()["choices"][0]["message"]["content"]
        start = content.find("{")
        end = content.rfind("}") + 1

        if start == -1 or end == -1:
            return {}

        data = json.loads(content[start:end])
        return {k: v for k, v in data.items() if v}

    except Exception as e:
        print("❌ GROQ ERROR:", e)
        return {}

# ================= START =================
@bot.message_handler(commands=["start"])
def start(message):
    sessions[message.chat.id] = {
        "name": None,
        "date": None,
        "time": None,
        "expecting": "name",
        "last_active": time.time()
    }
    bot.reply_to(message, "👋 Welcome!\n\nWhat is your name?")

# ================= MESSAGE HANDLER =================
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    chat_id = message.chat.id
    text = message.text.strip()
    now = time.time()

    print("📩", chat_id, text)

    # Expire old session
    if chat_id in sessions and now - sessions[chat_id]["last_active"] > SESSION_TIMEOUT:
        sessions.pop(chat_id, None)

    if chat_id not in sessions:
        sessions[chat_id] = {
            "name": None,
            "date": None,
            "time": None,
            "expecting": "name",
            "last_active": now
        }

    session = sessions[chat_id]
    session["last_active"] = now
    bot.send_chat_action(chat_id, "typing")

    # 1️⃣ AI extraction
    extracted = ai_extract(text, session)

    for k in ["name", "date", "time"]:
        if extracted.get(k):
            session[k] = extracted[k]

    # 2️⃣ HARD STATE LOGIC (NO STUCK POSSIBLE)

    # NAME
    if session["expecting"] == "name" and not session["name"]:
        session["name"] = text

    # DATE (🔥 FIX: ALWAYS ACCEPT USER INPUT)
    elif session["expecting"] == "date" and not session["date"]:
        if extracted.get("date"):
            session["date"] = extracted["date"]
        else:
            session["date"] = text  # <- CRITICAL FIX

    # TIME (🔥 FIX: ALWAYS ACCEPT USER INPUT)
    elif session["expecting"] == "time" and not session["time"]:
        if extracted.get("time"):
            session["time"] = extracted["time"]
        else:
            session["time"] = text  # <- CRITICAL FIX

    # 3️⃣ NEXT STEP
    if not session["name"]:
        session["expecting"] = "name"
        reply = "👤 What is your name?"

    elif not session["date"]:
        session["expecting"] = "date"
        reply = f"📅 Hi {session['name']}, which date would you like?"

    elif not session["time"]:
        session["expecting"] = "time"
        reply = f"⏰ What time on {session['date']}?"

    else:
        reply = (
            "✅ *Appointment Confirmed!*\n\n"
            f"👤 Name: {session['name']}\n"
            f"📅 Date: {session['date']}\n"
            f"⏰ Time: {session['time']}"
        )
        sessions.pop(chat_id, None)

    bot.reply_to(message, reply)

# ================= RUN =================
if __name__ == "__main__":
    bot.infinity_polling(
        skip_pending=True,
        timeout=60,
        long_polling_timeout=60
    )
