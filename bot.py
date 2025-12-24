import os
import time
import telebot
import smtplib
from email.message import EmailMessage

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
OWNER_EMAIL = os.getenv("OWNER_EMAIL")

if not all([BOT_TOKEN, EMAIL_ADDRESS, EMAIL_PASSWORD, OWNER_EMAIL]):
    raise RuntimeError("Missing environment variables")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")
print("✅ Appointment Bot Started (STABLE VERSION)")

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
        "I’ll help you book an appointment.\n"
        "What is your *full name*?"
    )

# ================= MESSAGE HANDLER =================
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    chat_id = message.chat.id
    text = message.text.strip()
    now = time.time()

    # Clear expired session
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

    # ---------------- FLOW (NO AI, NO STUCK) ----------------

    if not session["name"]:
        session["name"] = text
        reply = f"Nice to meet you *{session['name']}* 😊\n\n📧 Please share your *email address*."

    elif not session["email"]:
        if "@" not in text:
            reply = "❌ Please enter a valid email address."
        else:
            session["email"] = text
            reply = "📅 What *date* would you like to book? (Example: 28/12 or Tomorrow)"

    elif not session["date"]:
        session["date"] = text
        reply = f"⏰ What *time* on *{session['date']}* works for you?"

    elif not session["time"]:
        session["time"] = text

        # ---------- SEND EMAILS ----------
        send_email(
            session["email"],
            "Appointment Confirmed",
            f"""Hello {session['name']},

Your appointment is confirmed.

📅 Date: {session['date']}
⏰ Time: {session['time']}

Thank you!
"""
        )

        send_email(
            OWNER_EMAIL,
            "New Appointment Booked",
            f"""New appointment booked:

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
            "📧 Confirmation email sent."
        )

        sessions.pop(chat_id)

    bot.reply_to(message, reply)

# ================= RUN =================
if __name__ == "__main__":
    bot.infinity_polling(skip_pending=True)
