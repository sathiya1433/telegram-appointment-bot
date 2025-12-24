import telebot
import smtplib
from email.mime.text import MIMEText
import os
import requests

# ---------------- ENV VARIABLES ----------------
TOKEN = os.getenv("BOT_TOKEN")
EMAIL = os.getenv("EMAIL")              # Your admin Gmail
APP_PASSWORD = os.getenv("APP_PASSWORD")
HF_API_KEY = os.getenv("HF_API_KEY")

bot = telebot.TeleBot(TOKEN)
appointments = {}

# ---------------- FREE AI (HUGGING FACE) ----------------
def ai_reply(user_text):
    try:
        headers = {
            "Authorization": f"Bearer {HF_API_KEY}"
        }

        payload = {
            "inputs": f"Reply politely and professionally: {user_text}",
            "parameters": {
                "max_new_tokens": 120,
                "temperature": 0.7
            }
        }

        response = requests.post(
            "https://api-inference.huggingface.co/models/google/flan-t5-base",
            headers=headers,
            json=payload,
            timeout=20
        )

        result = response.json()

        if isinstance(result, list):
            return result[0]["generated_text"]
        else:
            return "🤖 Please rephrase your question."

    except Exception:
        return "⚠️ AI is busy. Please try again shortly."

# ---------------- START ----------------
@bot.message_handler(commands=['start'])
def start(m):
    bot.reply_to(
        m,
        "🤖 Welcome!\n\n"
        "📅 Type /book to book an appointment\n"
        "❌ Type /cancel to cancel booking\n"
        "💬 Or chat with me freely"
    )

# ---------------- BOOKING ----------------
@bot.message_handler(commands=['book'])
def book(m):
    appointments[m.chat.id] = {}
    bot.reply_to(m, "👤 Your full name?")
    bot.register_next_step_handler(m, get_name)

@bot.message_handler(commands=['cancel'])
def cancel(m):
    if m.chat.id in appointments:
        del appointments[m.chat.id]
        bot.reply_to(m, "❌ Booking cancelled. You can chat freely now.")
    else:
        bot.reply_to(m, "No active booking found.")

def get_name(m):
    appointments[m.chat.id]['name'] = m.text
    bot.reply_to(m, "📧 Your email address?")
    bot.register_next_step_handler(m, get_email)

def get_email(m):
    appointments[m.chat.id]['user_email'] = m.text
    bot.reply_to(m, "📅 Appointment date (DD-MM-YYYY)?")
    bot.register_next_step_handler(m, get_date)

def get_date(m):
    appointments[m.chat.id]['date'] = m.text
    bot.reply_to(m, "⏰ Appointment time (HH:MM)?")
    bot.register_next_step_handler(m, get_time)

def get_time(m):
    appointments[m.chat.id]['time'] = m.text
    data = appointments[m.chat.id]

    send_admin_email(data)
    send_user_email(data)

    bot.reply_to(
        m,
        "✅ **Appointment Confirmed!**\n\n"
        f"👤 Name: {data['name']}\n"
        f"📅 Date: {data['date']}\n"
        f"⏰ Time: {data['time']}\n\n"
        "📧 Confirmation email sent to you."
    )

    del appointments[m.chat.id]

# ---------------- EMAIL FUNCTIONS ----------------
def send_admin_email(data):
    body = f"""
New Appointment Booked

Name: {data['name']}
Email: {data['user_email']}
Date: {data['date']}
Time: {data['time']}
"""

    msg = MIMEText(body)
    msg['Subject'] = "📅 New Appointment Booked"
    msg['From'] = EMAIL
    msg['To'] = EMAIL

    send_email(msg)

def send_user_email(data):
    body = f"""
Dear {data['name']},

Your appointment has been successfully booked.

📅 Date: {data['date']}
⏰ Time: {data['time']}

Please be available at the scheduled time.
If you have any questions, feel free to reply to this email.

Thank you for choosing our service.

Best regards,
Appointment Support Team
"""

    msg = MIMEText(body)
    msg['Subject'] = "✅ Appointment Confirmation"
    msg['From'] = EMAIL
    msg['To'] = data['user_email']

    send_email(msg)

def send_email(msg):
    server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
    server.login(EMAIL, APP_PASSWORD)
    server.send_message(msg)
    server.quit()

# ---------------- AI CHAT ----------------
@bot.message_handler(func=lambda m: True)
def chat(m):
    if m.chat.id in appointments:
        bot.reply_to(
            m,
            "📅 Please complete booking first.\n"
            "Or type /cancel to stop booking."
        )
        return

    bot.send_chat_action(m.chat.id, 'typing')
    reply = ai_reply(m.text)
    bot.reply_to(m, reply)

# ---------------- RUN ----------------
bot.infinity_polling()
