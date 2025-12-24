import os
import json
import time
import datetime
import requests
import telebot
import smtplib
from email.message import EmailMessage

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
OWNER_EMAIL = os.getenv("OWNER_EMAIL")

if not all([BOT_TOKEN, GROQ_API_KEY, EMAIL_ADDRESS, EMAIL_PASSWORD, OWNER_EMAIL]):
    raise RuntimeError("Missing environment variables")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")
print("✅ Appointment Bot Started (FINAL FIX)")

# ================= MEMORY =================
sessions = {}
SESSION_TIMEOUT = 300  # 5 minutes

# ================= EMAIL =================
def send_email(to_email, subject, body):
    msg = EmailMessage()
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)

# ================= AI EXTRACTION =================
def ai_extract(text):
    today = datetime.date.today().isoformat()

    prompt = f"""
Extract appointment details.

Today: {today}

Message:
"{text}"

Return ONLY JSON:
{{
  "name": null,
  "email": null,
  "date": null,
  "time": null
}}

Rules:
- Date → YYYY-MM-DD
- Time → HH:MM (24-hour)
- Understand: today, tomorrow, next monday, 4pm
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
        print("AI ERROR:", e)
        return {}

# ================= START =================
@bot.message_handler(commands=["start"])
def start(message):
    sessions[message.chat.id] = {
        "name": None,
        "email": None,
        "date": None,
        "time": None,
        "last_active": time.time()
    }

    bot.reply_to(
        message,
        "👋 *Welcome!*\n\n"
        "I will help you book an appointment.\n"
        "Please tell me your *full name*."
    )

# ================= MESSAGE HANDLER =================
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    chat_id = message.chat.id
    text = message.text.strip()
    now = time.time()

    # Expire old session
    if chat_id in sessions and now - sessions[chat_id]["last_active"] > SESSION_TIMEOUT:
        sessions.pop(chat_id)

    if chat_id not in sessions:
        sessions[chat_id] = {
            "name": None,
            "email": None,
            "date": None,
            "time": None,
            "last_active": now
        }

    session = sessions[chat_id]
    session["last_active"] = now
    bot.send_chat_action(chat_id, "typing")

    extracted = ai_extract(text)

    # -------- SAFE FIELD UPDATES (FINAL FIX) --------

    # NAME (critical fix)
    if not session["name"] and "@" not in text:
        session["name"] = extracted.get("name") or text

    # EMAIL
    if extracted.get("email") and not session["email"]:
        session["email"] = extracted["email"]
    elif "@" in text and not session["email"]:
        session["email"] = text

    # DATE
    if extracted.get("date") and not session["date"]:
        session["date"] = extracted["date"]

    # TIME
    if extracted.get("time") and not session["time"]:
        session["time"] = extracted["time"]

    # -------- FLOW CONTROL --------
    if not session["name"]:
        reply = "👤 Please tell me your full name."

    elif not session["email"]:
        reply = "📧 Please provide your email address."

    elif not session["date"]:
        reply = f"📅 Thank you {session['name']}, which *date* would you like?"

    elif not session["time"]:
        reply = f"⏰ What *time* on {session['date']} works for you?"

    else:
        # Send confirmation emails
        send_email(
            session["email"],
            "Appointment Confirmation",
            f"""Hello {session['name']},

Your appointment is confirmed.

📅 Date: {session['date']}
⏰ Time: {session['time']}

Thank you.
"""
        )

        send_email(
            OWNER_EMAIL,
            "New Appointment Booked",
            f"""New appointment booked.

Name: {session['name']}
Email: {session['email']}
Date: {session['date']}
Time: {session['time']}
"""
        )

        reply = (
            "✅ *Appointment Confirmed!*\n\n"
            f"👤 {session['name']}\n"
            f"📅 {session['date']}\n"
            f"⏰ {session['time']}\n\n"
            "📧 Confirmation email sent to you and the owner."
        )

        sessions.pop(chat_id)

    bot.reply_to(message, reply)

# ================= RUN =================
if __name__ == "__main__":
    bot.infinity_polling(skip_pending=True, timeout=60, long_polling_timeout=60)
