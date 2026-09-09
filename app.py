import os
import json
import urllib.request
from flask import Flask, request, jsonify
from openai import OpenAI

app = Flask(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)


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
    telegram_api("sendMessage", {
        "chat_id": chat_id,
        "text": text
    })


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

    if chat_id and text:
        try:
            reply = ask_chatgpt(text)
            send_message(chat_id, reply)
        except Exception as e:
            send_message(
                chat_id,
                f"⚠️ ChatGPT error:\n{type(e).__name__}: {str(e)[:500]}"
            )

    return jsonify({"ok": True})


def setup_telegram():
    if not BOT_TOKEN:
        return

    url = "https://api.telegram.org/bot" + BOT_TOKEN + "/setWebhook"
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
