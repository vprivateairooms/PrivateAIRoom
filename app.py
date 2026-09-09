import os
import json
import urllib.request
from flask import Flask, request, jsonify
from openai import OpenAI

app = Flask(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
RENDER_URL = os.environ.get(
    "RENDER_EXTERNAL_URL",
    "https://privateairoom.onrender.com"
)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def telegram_api(method, data):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    body = json.dumps(data).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def send_message(chat_id, text):
    return telegram_api(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text
        }
    )


def ask_chatgpt(text):
    response = client.responses.create(
        model="gpt-5",
        input=text
    )
    return response.output_text


@app.route("/")
def home():
    return jsonify({
        "project": "Private AI Room",
        "status": "online",
        "telegram": "connected",
        "chatgpt": "connected"
    })


@app.route("/health")
def health():
    return jsonify({
        "status": "healthy"
    })


@app.route("/telegram/webhook", methods=["POST"])
def telegram_webhook():
    update = request.get_json(silent=True) or {}

    message = update.get("message", {})
    chat = message.get("chat", {})
    text = message.get("text", "")

    chat_id = chat.get("id")

    if chat_id:
        if text == "/start":
            send_message(
                chat_id,
                "🤖 Welcome to Private AI Room!\n\n"
                "Human + ChatGPT + Gemini\n\n"
                "ChatGPT is coming online 🚀"
            )
        elif text:
            try:
                reply = ask_chatgpt(text)
                send_message(chat_id, reply)
            except Exception:
                send_message(
                    chat_id,
                    "⚠️ ChatGPT connection error."
                )

    return jsonify({"ok": True})


def setup_telegram():
    if not BOT_TOKEN:
        return

    webhook_url = f"{RENDER_URL}/telegram/webhook"

    try:
        telegram_api(
            "setWebhook",
            {
                "url": webhook_url
            }
        )
    except Exception:
        pass


setup_telegram()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
