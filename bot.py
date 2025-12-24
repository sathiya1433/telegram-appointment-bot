import telebot
import smtplib
from email.mime.text import MIMEText
import os

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
EMAIL = os.getenv("EMAIL")              # Admin Gmail
APP_PASSWORD = os.getenv("APP_PASSWORD")

bot = telebot.TeleBot(BOT_TOKEN)
appointments = {}

# ================= START =================
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(
        message,
        "👋 Welcome!\n\n"
        "📅 /book - Book an appointment\n"
        "❌ /cancel - Cancel booking"
    )

# ================= BOOK =================
@bot.message_handler(commands=['book'])
def book(message):
    appointments[message.chat.id] = {}
    bot.reply_to(message, "👤 Enter your full name:")
    bot.register_next_step_handler(message, get_name)

@bot.message_handler(commands=['cancel'])
def cancel(message):
    if message.chat.id in appointments:
        del appointments[message.chat.id]
        bot.reply_to(message, "❌ Booking cancelled.")
    else:
        bot.reply_to(message, "No active booking.")

def get_name(message):
    appointments[message.chat.id]["name"] = message.text
    bot.reply_to(message, "📧 Enter your email address:")
    bot.register_next_step_handler(message, get_email)

def get_email(message):
    appointments[message.chat.id]["user_email"] = message.text
    bot.reply_to(message, "📅 Appointment date (DD-MM-YYYY):")
    bot.register_next_step_handler(message, get_date)

def get_date(message):
    appointments[message.chat.id]["date"] = message.text
    bot.reply_to(message, "⏰ Appointment time (HH:MM):")
    bot.register_next_step_handler(message, get_time)

def get_time(message):
    appointments[message.chat.id]["time"] = message.text
    data = appointments[message.chat.id]

    send_admin_email(data)
    send_user_email(data)

    bot.reply_to(
        message,
        "✅ Appointment Confirmed!\n\n"
        f"👤 Name: {data['name']}\n"
        f"📅 Date: {data['date']}\n"
        f"⏰ Time: {data['time']}\n\n"
        "📧 Confirmation email sent."
    )

    del appointments[message.chat.id]

# ================= EMAIL =================
def send_admin_email(data):
    body = (
        "New Appointment Booked\n\n"
        f"Name: {data['name']}\n"
        f"Email: {data['user_email']}\n"
        f"Date: {data['date']}\n"
        f"Time: {data['time']}\n"
    )

    msg = MIMEText(body)
    msg["Subject"] = "📅 New Appointment"
    msg["From"] = EMAIL
    msg["To"] = EMAIL

    send_email(msg)

def send_user_email(data):
    body = (
        f"Dear {data['name']},\n\n"
        "Your appointment has been successfully booked.\n\n"
        f"📅 Date: {data['date']}\n"
        f"⏰ Time: {data['time']}\n\n"
        "Please be available at the scheduled time.\n\n"
        "Best regards,\n"
        "Appointment Team"
    )

    msg = MIMEText(body)
    msg["Subject"] = "✅ Appointment Confirmation"
    msg["From"] = EMAIL
    msg["To"] = data["user_email"]

    send_email(msg)

def send_email(msg):
    server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
    server.login(EMAIL, APP_PASSWORD)
    server.send_message(msg)
    server.quit()

# ================= DEFAULT =================
@bot.message_handler(func=lambda m: True)
def default_reply(message):
    if message.chat.id in appointments:
        bot.reply_to(message, "📅 Please complete booking or /cancel.")
    else:
        bot.reply_to(
            message,
            "👋 Hi!\n\n"
            "📅 Use /book to book an appointment"
        )

# ================= RUN =================
bot.infinity_polling()
