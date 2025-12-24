import google.generativeai as genai
import os
import json
import datetime

# Configure Gemini
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

def parse_booking_with_ai(user_text):
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # Get current date so AI understands "next Friday"
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    
    prompt = f"""
    Current Date: {current_date}
    User Input: "{user_text}"
    
    Extract the following details from the user input:
    - Name
    - Email (if present)
    - Date (YYYY-MM-DD format)
    - Time (HH:MM format)
    
    Return ONLY a JSON object. If a field is missing, set it to null.
    Example: {{"name": "John", "email": null, "date": "2023-10-25", "time": "14:00"}}
    """
    
    try:
        response = model.generate_content(prompt)
        # Clean up response to ensure it's valid JSON
        json_text = response.text.replace('```json', '').replace('```', '')
        return json.loads(json_text)
    except Exception as e:
        print(f"AI Error: {e}")
        return None
