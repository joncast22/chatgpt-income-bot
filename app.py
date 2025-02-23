import openai
import os
import stripe
from flask import Flask, request, jsonify, url_for
from dotenv import load_dotenv
from twilio.rest import Client

# Load environment variables
load_dotenv()

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
stripe.api_key = STRIPE_SECRET_KEY

app = Flask(__name__)

# Home route to check if bot is running
@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Chatbot is running! Visit /subscribe to sign up."})

# Stripe Subscription Route
@app.route("/subscribe", methods=["GET"])
def subscribe():
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price": "price_xxx12345",  # Replace with your Stripe Price ID
                    "quantity": 1,
                }
            ],
            mode="subscription",
            success_url=url_for("subscription_success", _external=True) + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=url_for("home", _external=True),
        )
        return jsonify({"checkout_url": session.url})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Payment Success Route
@app.route("/subscription_success", methods=["GET"])
def subscription_success():
    session_id = request.args.get("session_id")
    return jsonify({"message": "Subscription successful!", "session_id": session_id})

# Chatbot API (Only for Paid Users)
@app.route("/chat", methods=["GET", "POST"])
def chat():
    if request.method == "GET":
        return jsonify({"message": "Use POST to chat!"})

    session_id = request.args.get("session_id")
    if not session_id:
        return jsonify({"error": "Subscription required. Visit /subscribe to sign up."}), 402

    try:
        session = stripe.checkout.Session.retrieve(session_id)
        subscription = stripe.Subscription.retrieve(session.subscription)
        if subscription.status != "active":
            return jsonify({"error": "Subscription not active. Please renew."}), 402
    except stripe.error.StripeError:
        return jsonify({"error": "Invalid subscription."}), 402

    # Process Chat Message
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

# WhatsApp Chatbot API
@app.route("/whatsapp", methods=["GET", "POST"])
def whatsapp():
    if request.method == "GET":
        return jsonify({"message": "Use POST to send WhatsApp messages!"})

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

    # Send WhatsApp message
    twilio_client.messages.create(
        from_=f"whatsapp:{TWILIO_WHATSAPP_NUMBER}",
        body=response['choices'][0]['message']['content'],
        to="whatsapp:+1234567890"  # Replace with the recipient's WhatsApp number
    )

    return jsonify({"response": "Message sent!"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
