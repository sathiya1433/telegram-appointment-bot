import os
import json
import time
import datetime
import threading
import requests
import telebot
import smtplib
from email.message import EmailMessage

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")      # your gmail
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")    # gmail app password
OWNER_EMAIL = os.getenv("OWNER_EMAIL")          # owner/admin email

if not all([BOT_TOKEN, GROQ_API_KEY, EMAIL_ADDRESS, EMAIL_PASSWORD, OWNER_EMAIL]):
    raise RuntimeError("Missing environment variables")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")
print("✅ Professional Appointment Bot Started")

# ================= MEMORY =================
sessions = {}
appointments = []  # stored in-memory (use DB later)

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

# ================= AI UNDERSTANDING =================
def ai_extract(text):
    today = datetime.date.today().isoformat()

    prompt = f"""
Extract appointment details from the message.

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
- Time → HH:MM (24h)
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
        start, end = content.find("{"), content.rfind("}") + 1
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
        "I’ll help you schedule your appointment.\n"
        "May I know your *full name*?"
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

    # Update safely
    # -------- SAFE FIELD UPDATES --------

# Name
if extracted.get("name") and not session["name"]:
    session["name"] = extracted["name"]

# Email
if extracted.get("email") and not session["email"]:
    session["email"] = extracted["email"]
elif "@" in text and not session["email"]:
    session["email"] = text

# Date
if extracted.get("date") and not session["date"]:
    session["date"] = extracted["date"]

# Time
if extracted.get("time") and not session["time"]:
    session["time"] = extracted["time"]

    # Flow
    if not session["name"]:
        reply = "👤 Please tell me your full name."
    elif not session["email"] or "@" not in session["email"]:
        reply = "📧 Please provide your email address."
    elif not session["date"]:
        reply = f"📅 Thank you {session['name']}. Which *date* would you prefer?"
    elif not session["time"]:
        reply = f"⏰ What *time* on {session['date']} works for you?"
    else:
        # Save appointment
        appointment = {
            "name": session["name"],
            "email": session["email"],
            "date": session["date"],
            "time": session["time"]
        }
        appointments.append(appointment)

        # Confirmation emails
        send_email(
            session["email"],
            "Appointment Confirmation",
            f"""Hello {session['name']},

Your appointment is confirmed.

📅 Date: {session['date']}
⏰ Time: {session['time']}

Thank you for choosing us.
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
            "📧 Confirmation email sent.\n"
            "⏰ You will receive a reminder before the appointment."
        )

        sessions.pop(chat_id)

    bot.reply_to(message, reply)

# ================= REMINDER SYSTEM =================
def reminder_worker():
    while True:
        now = datetime.datetime.now()
        for appt in appointments:
            appt_time = datetime.datetime.strptime(
                f"{appt['date']} {appt['time']}", "%Y-%m-%d %H:%M"
            )

            # 1-hour reminder
            if 0 < (appt_time - now).total_seconds() < 3600:
                send_email(
                    appt["email"],
                    "Appointment Reminder",
                    f"""Hello {appt['name']},

This is a reminder for your appointment today.

⏰ Time: {appt['time']}
"""
                )
                send_email(
                    OWNER_EMAIL,
                    "Upcoming Appointment Reminder",
                    f"Reminder: {appt['name']} at {appt['time']}"
                )
                appointments.remove(appt)
        time.sleep(300)

threading.Thread(target=reminder_worker, daemon=True).start()

# ================= RUN =================
if __name__ == "__main__":
    bot.infinity_polling(skip_pending=True, timeout=60, long_polling_timeout=60)
