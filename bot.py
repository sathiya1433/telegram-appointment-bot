import os
import json
import time
import telebot
import requests
import datetime

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not BOT_TOKEN or not GROQ_API_KEY:
    raise RuntimeError("Missing BOT_TOKEN or GROQ_API_KEY")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")
print("✅ Bot started (AI FULL CONTROL MODE)")

# ================= MEMORY =================
sessions = {}
SESSION_TIMEOUT = 300  # 5 minutes

# ================= AI AGENT =================
def ai_agent(user_text, memory):
    today = datetime.date.today().isoformat()

    system_prompt = f"""
You are an AI appointment booking agent.

Today is {today}.

You control the entire booking conversation.

RULES:
- You MUST decide what to ask next
- You MUST NOT repeat questions unnecessarily
- You MUST NOT confirm until name, date, time are known
- Date format: YYYY-MM-DD
- Time format: HH:MM (24-hour)
- Understand: today, tomorrow, next monday, 4pm, 6:30 PM

OUTPUT FORMAT (STRICT JSON ONLY):
{{
  "memory": {{
    "name": string|null,
    "date": string|null,
    "time": string|null
  }},
  "reply": "message to send user",
  "done": true|false
}}

NO extra text.
"""

    payload = {
        "model": "llama3-70b-8192",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "assistant", "content": f"Current memory: {json.dumps(memory)}"},
            {"role": "user", "content": user_text}
        ],
        "temperature": 0
    }

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=20
        )

        content = response.json()["choices"][0]["message"]["content"]
        start = content.find("{")
        end = content.rfind("}") + 1

        if start == -1:
            raise ValueError("No JSON from AI")

        return json.loads(content[start:end])

    except Exception as e:
        print("❌ AI AGENT ERROR:", e)
        return {
            "memory": memory,
            "reply": "Sorry, I didn’t understand that. Could you repeat?",
            "done": False
        }

# ================= START =================
@bot.message_handler(commands=["start"])
def start(message):
    sessions[message.chat.id] = {
        "memory": {"name": None, "date": None, "time": None},
        "last_active": time.time()
    }
    bot.reply_to(message, "👋 Welcome! Let’s book your appointment.\nWhat is your name?")

# ================= MESSAGE HANDLER =================
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    chat_id = message.chat.id
    text = message.text.strip()
    now = time.time()

    print("📩", chat_id, text)

    # Session expiry
    if chat_id in sessions and now - sessions[chat_id]["last_active"] > SESSION_TIMEOUT:
        sessions.pop(chat_id, None)

    if chat_id not in sessions:
        sessions[chat_id] = {
            "memory": {"name": None, "date": None, "time": None},
            "last_active": now
        }

    session = sessions[chat_id]
    session["last_active"] = now
    bot.send_chat_action(chat_id, "typing")

    ai_response = ai_agent(text, session["memory"])

    # Update memory from AI
    session["memory"] = ai_response.get("memory", session["memory"])

    # Send reply
    bot.reply_to(message, ai_response["reply"])

    # Clear session if done
    if ai_response.get("done") is True:
        sessions.pop(chat_id, None)

# ================= RUN =================
if __name__ == "__main__":
    bot.infinity_polling(skip_pending=True, timeout=60, long_polling_timeout=60)
