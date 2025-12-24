import telebot
import smtplib
from email.mime.text import MIMEText
import os

TOKEN = os.getenv("BOT_TOKEN")
EMAIL = os.getenv("EMAIL")
APP_PASSWORD = os.getenv("APP_PASSWORD")

bot = telebot.TeleBot(TOKEN)
appointments = {}

@bot.message_handler(commands=['start'])
def start(m):
    bot.reply_to(m, "📅 Welcome!\nType /book to book an appointment")

@bot.message_handler(commands=['book'])
def book(m):
    appointments[m.chat.id] = {}
    bot.reply_to(m, "Your name?")
    bot.register_next_step_handler(m, get_name)

def get_name(m):
    appointments[m.chat.id]['name'] = m.text
    bot.reply_to(m, "Date (DD-MM-YYYY)?")
    bot.register_next_step_handler(m, get_date)

def get_date(m):
    appointments[m.chat.id]['date'] = m.text
    bot.reply_to(m, "Time (HH:MM)?")
    bot.register_next_step_handler(m, get_time)

def get_time(m):
    appointments[m.chat.id]['time'] = m.text
    data = appointments[m.chat.id]
    send_email(data)
    bot.reply_to(m, "✅ Appointment booked. Email sent.")

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
