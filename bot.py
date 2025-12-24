import telebot
import smtplib
from email.mime.text import MIMEText
import os
import requests

TOKEN = os.getenv("BOT_TOKEN")
EMAIL = os.getenv("EMAIL")
APP_PASSWORD = os.getenv("APP_PASSWORD")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

bot = telebot.TeleBot(TOKEN)
appointments = {}

def ai_reply(user_text):
    try:
        headers = {
            "Authorization": f"Bearer {OPENAI_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are a helpful, concise assistant."},
                {"role": "user", "content": user_text}
            ],
            "max_tokens": 150
        }

        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=15   # ✅ prevents bot from getting stuck
        )

        return r.json()["choices"][0]["message"]["content"]

    except Exception:
        return "⏳ I'm thinking… please try again."

@bot.message_handler(commands=['start'])
def start(m):
    bot.reply_to(m, "🤖 Hi! I’m your AI assistant.\nType /book to book appointment or ask me anything.")

@bot.message_handler(commands=['book'])
def book(m):
    appointments[m.chat.id] = {}
    bot.reply_to(m, "👤 Your name?")
    bot.register_next_step_handler(m, get_name)

def get_name(m):
    appointments[m.chat.id]['name'] = m.text
    bot.reply_to(m, "📅 Date (DD-MM-YYYY)?")
    bot.register_next_step_handler(m, get_date)

def get_date(m):
    appointments[m.chat.id]['date'] = m.text
    bot.reply_to(m, "⏰ Time (HH:MM)?")
    bot.register_next_step_handler(m, get_time)

def get_time(m):
    appointments[m.chat.id]['time'] = m.text
    data = appointments[m.chat.id]
    send_email(data)
    bot.reply_to(m, "✅ Appointment booked. I’ve notified you by email.")
    del appointments[m.chat.id]
@bot.message_handler(func=lambda m: True)
def chat(m):
    # If user is in booking process, don't use AI
    if m.chat.id in appointments:
        bot.reply_to(
            m,
            "📅 Please finish booking first.\n"
            "Or type /cancel to stop booking."
        )
        return

    # Normal AI chat
    bot.send_chat_action(m.chat.id, 'typing')
    reply = ai_reply(m.text)
    bot.reply_to(m, reply)
def send_email(data):
    body = f"""
New Appointment

Name: {data['name']}
Date: {data['date']}
Time: {data['time']}
"""
    msg = MIMEText(body)
    msg['Subject'] = "New Appointment"
    msg['From'] = EMAIL
    msg['To'] = EMAIL

    server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
    server.login(EMAIL, APP_PASSWORD)
    server.send_message(msg)
    server.quit()

bot.infinity_polling()
