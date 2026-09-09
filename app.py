import os
import json
import urllib.request
from flask import Flask, request, jsonify

app = Flask(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
OWNER_ID = 5931266589


def telegram_api(method, data):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    body = json.dumps(data).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def send_message(chat_id, text):
    telegram_api("sendMessage", {
        "chat_id": chat_id,
        "text": text
    })


def ask_gemini(text):
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-3.1-flash-lite:generateContent?key="
        + GEMINI_API_KEY
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": text
                    }
                ]
            }
        ]
    }

    body = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=60) as response:
        result = json.loads(response.read().decode("utf-8"))

    return result["candidates"][0]["content"]["parts"][0]["text"]


@app.route("/")
def home():
    return jsonify({
        "project": "Private AI Room",
        "status": "online"
    })


@app.route("/health")
def health():
    return jsonify({"status": "healthy"})


@app.route("/telegram/webhook", methods=["POST"])
def telegram_webhook():
    update = request.get_json(silent=True) or {}

    message = update.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")

    if not chat_id:
        return jsonify({"ok": True})

    # Private owner-only access
    if chat_id != OWNER_ID:
        send_message(chat_id, "🔒 Private AI Room is private.")
        return jsonify({"ok": True})

    if text:
        try:
            reply = ask_gemini(text)
            send_message(chat_id, reply)

        except Exception as e:
            send_message(
                chat_id,
                f"⚠️ Gemini error:\n{type(e).__name__}: {str(e)[:500]}"
            )

    return jsonify({"ok": True})


def setup_telegram():
    if not BOT_TOKEN:
        return

    url = (
        "https://api.telegram.org/bot"
        + BOT_TOKEN
        + "/setWebhook"
    )

    data = json.dumps({
        "url": "https://privateairoom.onrender.com/telegram/webhook"
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        urllib.request.urlopen(req, timeout=20)
    except Exception:
        pass


setup_telegram()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
