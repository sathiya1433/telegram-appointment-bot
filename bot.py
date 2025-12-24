import telebot
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ===================== CONFIG =====================
BOT_TOKEN = "PASTE_YOUR_BOT_TOKEN_HERE"

SMTP_EMAIL = "yourgmail@gmail.com"
SMTP_PASSWORD = "YOUR_GMAIL_APP_PASSWORD"
# =================================================

bot = telebot.TeleBot(BOT_TOKEN)

user_state = {}
user_data = {}

# ---------------- START ----------------
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    user_state[user_id] = "NAME"
    user_data[user_id] = {}
    bot.send_message(user_id, "👤 Enter your full name:")

# ---------------- CANCEL ----------------
@bot.message_handler(commands=['cancel'])
def cancel(message):
    user_id = message.chat.id
    user_state.pop(user_id, None)
    user_data.pop(user_id, None)
    bot.send_message(user_id, "❌ Booking cancelled.")

# ---------------- MAIN HANDLER ----------------
@bot.message_handler(func=lambda message: True)
def handle(message):
    user_id = message.chat.id
    text = message.text.strip()

    if user_id not in user_state:
        bot.send_message(user_id, "Type /start to book appointment")
        return

    # ---- NAME ----
    if user_state[user_id] == "NAME":
        user_data[user_id]['name'] = text
        user_state[user_id] = "EMAIL"
        bot.send_message(user_id, "📧 Enter your email address:")

    # ---- EMAIL ----
    elif user_state[user_id] == "EMAIL":
        user_data[user_id]['email'] = text
        user_state[user_id] = "DATE"
        bot.send_message(user_id, "📅 Appointment date (DD-MM-YYYY):")

    # ---- DATE ----
    elif user_state[user_id] == "DATE":
        user_data[user_id]['date'] = text
        user_state[user_id] = "TIME"
        bot.send_message(user_id, "⏰ Appointment time (HH:MM):")

    # ---- TIME ----
    elif user_state[user_id] == "TIME":
        user_data[user_id]['time'] = text
        user_state[user_id] = "CONFIRM"

        bot.send_message(
            user_id,
            f"📋 Please confirm booking\n\n"
            f"👤 Name: {user_data[user_id]['name']}\n"
            f"📧 Email: {user_data[user_id]['email']}\n"
            f"📅 Date: {user_data[user_id]['date']}\n"
            f"⏰ Time: {user_data[user_id]['time']}\n\n"
            f"Type *Booking* to confirm or /cancel",
            parse_mode="Markdown"
        )

    # ---- CONFIRM ----
    elif user_state[user_id] == "CONFIRM":

        if text.lower() == "booking":
            send_email(user_data[user_id])

            bot.send_message(
                user_id,
                "✅ *Appointment Confirmed!*\n\n"
                "📧 Confirmation email sent.",
                parse_mode="Markdown"
            )

            user_state.pop(user_id)
            user_data.pop(user_id)

        else:
            bot.send_message(user_id, "❌ Type *Booking* or /cancel", parse_mode="Markdown")


# ---------------- EMAIL FUNCTION ----------------
def send_email(data):
    msg = MIMEMultipart()
    msg['From'] = SMTP_EMAIL
    msg['To'] = data['email']
    msg['Subject'] = "Appointment Confirmation"

    body = f"""
Hello {data['name']},

Your appointment has been confirmed.

Date : {data['date']}
Time : {data['time']}

Thank you.
"""
    msg.attach(MIMEText(body, 'plain'))

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(SMTP_EMAIL, SMTP_PASSWORD)
    server.send_message(msg)
    server.quit()

# ---------------- RUN ----------------
print("🤖 Bot is running...")
bot.infinity_polling()
