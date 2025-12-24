import telebot
import smtplib
from email.mime.text import MIMEText
import os

# ---------------- ENV VARIABLES ----------------
TOKEN = os.getenv("BOT_TOKEN")
EMAIL = os.getenv("EMAIL")              # Admin Gmail
APP_PASSWORD = os.getenv("APP_PASSWORD")

bot = telebot.TeleBot(TOKEN)
appointments = {}

# ---------------- START ----------------
@bot.message_handler(commands=['start'])
def start(m):
    bot.reply_to(
        m,
        "👋 Welcome!\n\n"
        "📅 /book – Book an appointment\n"
        "❌ /cancel – Cancel booking\n"
        "ℹ️ I will guide you step by step"
    )

# ---------------- BOOK APPOINTMENT ----------------
@bot.message_handler(commands=['book'])
def book(m):
    appointments[m.chat.id] = {}
    bot.reply_to(m, "👤 Please enter your full name:")
    bot.register_next_step_handler(m, get_name)

@bot.message_handler(commands=['cancel'])
def cancel(m):
    if m.chat.id in appointments:
        del appointments[m.chat.id]
        bot.reply_to(m, "❌ Booking cancelled successfully.")
    else:
        bot.reply_to(m, "No active booking found.")

def get_name(m):
    appointments[m.chat.id]['name'] = m.text
    bot.reply_to(m, "📧 Please enter your email address:")
    bot.register_next_step_handler(m, get_email)

def get_email(m):
    appointments[m.chat.id]['user_email'] = m.text
    bot.reply_to(m, "📅 Appointment date (DD-MM-YYYY):")
    bot.register_next_step_handler(m, get_date)

def get_date(m):
    appointments[m.chat.id]['date'] = m.text
    bot.reply_to(m, "⏰ Appointment time (HH:MM):")
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
        "📧 Confirmation email has been sent."
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
If you need to reschedule, contact us.

Best regards,
Appointment Team
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

# ---------------- DEFAULT HANDLER ----------------
@bot.message_handler(func=lambda m: True)
def default_reply(m):
    if m.chat.id in appointments:
        bot.reply_to(
            m,
            "📅 Please complete your booking or type /cancel."
        )
    else:
        bot.reply_to(
            m,
            "👋 Hello!\n\n"
            "📅 Use /book to book an appointment"
        )

# ---------------- RUN ----------------
bot.infinity_polling()
