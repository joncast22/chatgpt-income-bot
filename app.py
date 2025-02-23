import openai
import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

# Home route to check if bot is running
@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Chatbot is running!"})

# Add GET support for testing
@app.route("/chat", methods=["GET", "POST"])
def chat():
    if request.method == "GET":
        return jsonify({"message": "Use POST to chat!"})

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
