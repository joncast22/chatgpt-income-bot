import openai
import os
import stripe
from flask import Flask, request, jsonify, redirect, url_for
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")

app = Flask(__name__)

stripe.api_key = STRIPE_SECRET_KEY

# Home route to check if bot is running
@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Chatbot is running! Visit /checkout to pay."})

# Stripe Checkout Route (Fixed)
@app.route("/checkout", methods=["GET"])
def checkout():
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": "AI Chatbot Access"},
                        "unit_amount": 500,  # $5.00 per use
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            success_url=url_for("success", _external=True) + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=url_for("home", _external=True),
        )
        return jsonify({"checkout_url": session.url})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Payment Success Route
@app.route("/success", methods=["GET"])
def success():
    session_id = request.args.get("session_id")
    return jsonify({"message": "Payment successful!", "session_id": session_id})

# Chatbot API (Only for Paid Users)
@app.route("/chat", methods=["POST"])
def chat():
    session_id = request.args.get("session_id")

    # Validate Stripe Payment
    if not session_id:
        return jsonify({"error": "Payment required. Visit /checkout to purchase access."}), 402

    try:
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status != "paid":
            return jsonify({"error": "Payment not verified."}), 402
    except stripe.error.StripeError:
        return jsonify({"error": "Invalid session ID."}), 402

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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
