import openai
import os
import stripe
import secrets
import sqlite3
from flask import Flask, request, jsonify, url_for
from dotenv import load_dotenv
from twilio.rest import Client
import smtplib
from email.mime.text import MIMEText

# Load environment variables
load_dotenv()

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = os.getenv("EMAIL_PORT")
EMAIL_USERNAME = os.getenv("EMAIL_USERNAME")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
stripe.api_key = STRIPE_SECRET_KEY

app = Flask(__name__)

# Database setup
conn = sqlite3.connect("api_keys.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS api_keys (
    email TEXT PRIMARY KEY,
    api_key TEXT
)
""")
conn.commit()

def generate_api_key():
    return secrets.token_hex(16)

def store_api_key(email, api_key):
    cursor.execute("REPLACE INTO api_keys (email, api_key) VALUES (?, ?)", (email, api_key))
    conn.commit()

def get_api_key(email):
    cursor.execute("SELECT api_key FROM api_keys WHERE email = ?", (email,))
    result = cursor.fetchone()
    return result[0] if result else None

def send_api_key_email(email, api_key):
    subject = "Your API Key Access"
    body = f"Thank you for subscribing! Your API key is: {api_key}\n\nKeep it safe and use it to access our AI chatbot API."
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_USERNAME
    msg["To"] = email
    
    try:
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
        server.sendmail(EMAIL_USERNAME, email, msg.as_string())
        server.quit()
    except Exception as e:
        print(f"Failed to send email: {e}")

@app.route("/subscription_success", methods=["GET"])
def subscription_success():
    session_id = request.args.get("session_id")
    session = stripe.checkout.Session.retrieve(session_id)
    customer_email = session.customer_email
    
    if not customer_email:
        return jsonify({"error": "Could not retrieve customer email."}), 400
    
    api_key = generate_api_key()
    store_api_key(customer_email, api_key)
    send_api_key_email(customer_email, api_key)
    
    return jsonify({"message": "Subscription successful! API key sent via email.", "api_key": api_key})

@app.route("/api/chat", methods=["POST"])
def api_chat():
    api_key = request.headers.get("X-API-KEY")
    
    cursor.execute("SELECT email FROM api_keys WHERE api_key = ?", (api_key,))
    result = cursor.fetchone()
    if not result:
        return jsonify({"error": "Unauthorized. Get an API key at yoursite.com"}), 401
    
    data = request.json
    user_message = data.get("message", "")
    
    if not user_message:
        return jsonify({"error": "Message is required"}), 400
    
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "system", "content": "You are a helpful AI assistant."},
                  {"role": "user", "content": user_message}],
        temperature=0.7
    )
    
    return jsonify({"response": response['choices'][0]['message']['content']})

@app.route("/api/validate_key", methods=["GET"])
def validate_api_key():
    api_key = request.headers.get("X-API-KEY")
    cursor.execute("SELECT email FROM api_keys WHERE api_key = ?", (api_key,))
    result = cursor.fetchone()
    
    if result:
        return jsonify({"message": "API Key is valid.", "email": result[0]}), 200
    else:
        return jsonify({"error": "Invalid API Key."}), 401

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
