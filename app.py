import os
import json
import urllib.request
from flask import Flask, request, jsonify

app = Flask(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://privateairoom.onrender.com")


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


@app.route("/")
def home():
    return jsonify({
        "project": "Private AI Room",
        "status": "online",
        "telegram": "connected"
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
                "🤖 Welcome to Private AI Room!\n\nHuman + ChatGPT + Gemini\n\nRoom is coming online 🚀"
            )
        elif text:
            send_message(
                chat_id,
                f"📨 Private AI Room received:\n{text}"
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
