import telebot
from telebot import types
import smtplib
from email.message import EmailMessage
import os

# 1. Load Environment Variables
API_TOKEN = os.environ.get('BOT_TOKEN')
SMTP_EMAIL = os.environ.get('SMTP_EMAIL')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')
ADMIN_ID = os.environ.get('ADMIN_ID')  # Optional: For Admin Notifications

bot = telebot.TeleBot(API_TOKEN)

# Dictionary to store user data temporarily
# Structure: {user_id: {'name': '...', 'email': '...', 'date': '...', 'time': '...'}}
user_data = {}

# --- Step 1: Start ---
@bot.message_handler(commands=['start', 'book'])
def send_welcome(message):
    msg = bot.reply_to(message, "👋 Welcome to the Appointment Bot.\n\nWhat is your full name?")
    bot.register_next_step_handler(msg, process_name_step)

# --- Step 2: Name -> Email ---
def process_name_step(message):
    try:
        chat_id = message.chat.id
        name = message.text
        user_data[chat_id] = {'name': name}
        msg = bot.reply_to(message, f"Nice to meet you, {name}. \n\nPlease enter your email address:")
        bot.register_next_step_handler(msg, process_email_step)
    except Exception as e:
        bot.reply_to(message, "⚠️ An error occurred. Please type /start to try again.")

# --- Step 3: Email -> Date ---
def process_email_step(message):
    try:
        chat_id = message.chat.id
        email = message.text
        # Simple validation could go here
        user_data[chat_id]['email'] = email
        msg = bot.reply_to(message, "Got it. What date would you like to book? (e.g., 2023-10-25)")
        bot.register_next_step_handler(msg, process_date_step)
    except Exception as e:
        bot.reply_to(message, "⚠️ Error. Type /start.")

# --- Step 4: Date -> Time ---
def process_date_step(message):
    try:
        chat_id = message.chat.id
        date = message.text
        user_data[chat_id]['date'] = date
        msg = bot.reply_to(message, "Almost done. What time? (e.g., 14:00)")
        bot.register_next_step_handler(msg, process_time_step)
    except Exception as e:
        bot.reply_to(message, "⚠️ Error. Type /start.")

# --- Step 5: Time -> Confirmation (Inline Buttons) ---
def process_time_step(message):
    try:
        chat_id = message.chat.id
        time = message.text
        user_data[chat_id]['time'] = time
        
        # Retrieve all data
        booking = user_data[chat_id]
        
        # Create Inline Keyboard
        markup = types.InlineKeyboardMarkup()
        btn_confirm = types.InlineKeyboardButton("✅ Confirm Booking", callback_data="confirm")
        btn_cancel = types.InlineKeyboardButton("❌ Cancel", callback_data="cancel")
        markup.add(btn_confirm, btn_cancel)
        
        summary = (
            f"Please verify your details:\n\n"
            f"👤 Name: {booking['name']}\n"
            f"📧 Email: {booking['email']}\n"
            f"📅 Date: {booking['date']}\n"
            f"⏰ Time: {booking['time']}"
        )
        
        bot.send_message(chat_id, summary, reply_markup=markup)
        
    except Exception as e:
        bot.reply_to(message, "⚠️ Error. Type /start.")

# --- Step 6: Handle Button Clicks ---
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = call.message.chat.id
    
    if call.data == "confirm":
        # Check if user data exists
        if chat_id in user_data:
            bot.answer_callback_query(call.id, "Processing...")
            bot.edit_message_text("⏳ Sending confirmation email...", chat_id, call.message.message_id)
            
            # Send Emails
            send_confirmation_emails(user_data[chat_id])
            
            bot.edit_message_text("✅ **Booking Confirmed!** check your email.", chat_id, call.message.message_id, parse_mode='Markdown')
            # Clear data
            del user_data[chat_id]
        else:
            bot.send_message(chat_id, "Session expired. Please /start again.")
            
    elif call.data == "cancel":
        bot.answer_callback_query(call.id, "Booking Cancelled")
        bot.edit_message_text("❌ Booking request cancelled. Type /start to begin again.", chat_id, call.message.message_id)
        if chat_id in user_data:
            del user_data[chat_id]

# --- Email Logic (User + Admin) ---
def send_confirmation_emails(data):
    # 1. Email to User
    msg = EmailMessage()
    msg.set_content(f"Hello {data['name']},\n\nYour appointment is confirmed for {data['date']} at {data['time']}.\n\nThank you!")
    msg['Subject'] = 'Appointment Confirmation'
    msg['From'] = SMTP_EMAIL
    msg['To'] = data['email']

    # 2. Email to Admin (Optional)
    admin_msg = EmailMessage()
    admin_msg.set_content(f"New Booking!\nName: {data['name']}\nEmail: {data['email']}\nDate: {data['date']} @ {data['time']}")
    admin_msg['Subject'] = 'New Booking Alert'
    admin_msg['From'] = SMTP_EMAIL
    admin_msg['To'] = SMTP_EMAIL  # Send to yourself or a specific admin email

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)
            server.send_message(admin_msg) # Send admin alert
            print("Emails sent successfully.")
            
            # Optional: Telegram Notification to Admin
            if ADMIN_ID:
                bot.send_message(ADMIN_ID, f"🔔 **New Booking:**\n{data['name']} booked for {data['date']}", parse_mode='Markdown')
                
    except Exception as e:
        print(f"Failed to send email: {e}")

# --- Run Bot ---
print("Bot is polling...")
bot.infinity_polling()
