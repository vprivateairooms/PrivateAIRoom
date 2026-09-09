import os
import json
import shutil
import urllib.request
from pathlib import Path

from flask import Flask, request, jsonify


# =========================================================
# CODEX AUTH SETUP — MUST HAPPEN BEFORE IMPORTING CODEX
# =========================================================

CODEX_HOME = "/tmp/codex"
SOURCE_AUTH = "/etc/secrets/auth.json"
TARGET_AUTH = "/tmp/codex/auth.json"
CONFIG_FILE = "/tmp/codex/config.toml"

os.makedirs(CODEX_HOME, exist_ok=True)

if os.path.exists(SOURCE_AUTH):
    shutil.copyfile(SOURCE_AUTH, TARGET_AUTH)

# Force Codex to use ChatGPT authentication
# and file-based credentials.
with open(CONFIG_FILE, "w", encoding="utf-8") as f:
    f.write(
        'cli_auth_credentials_store = "file"\n'
        'forced_login_method = "chatgpt"\n'
    )

os.environ["CODEX_HOME"] = CODEX_HOME

# Do NOT let an API key accidentally override ChatGPT auth.
os.environ.pop("OPENAI_API_KEY", None)


# Import only AFTER CODEX_HOME is configured.
from openai_codex import Codex


# =========================================================
# FLASK
# =========================================================

app = Flask(__name__)


# =========================================================
# ENVIRONMENT
# =========================================================

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

OWNER_ID = 8655472622


# =========================================================
# TELEGRAM API
# =========================================================

def telegram_api(method, data):

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"

    body = json.dumps(data).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json"
        },
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(
            response.read().decode("utf-8")
        )


def send_message(chat_id, text):

    telegram_api(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text
        }
    )


# =========================================================
# GEMINI
# =========================================================

def ask_gemini(text):

    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY is missing."
        )

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
        headers={
            "Content-Type": "application/json"
        },
        method="POST"
    )

    with urllib.request.urlopen(
        req,
        timeout=60
    ) as response:

        result = json.loads(
            response.read().decode("utf-8")
        )

    return (
        result["candidates"][0]
        ["content"]["parts"][0]["text"]
    )


# =========================================================
# OPENROUTER FREE
# =========================================================

def ask_openrouter(text):

    if not OPENROUTER_API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY is missing."
        )

    url = (
        "https://openrouter.ai/api/v1/chat/completions"
    )

    payload = {
        "model": "openrouter/free",
        "messages": [
            {
                "role": "user",
                "content": text
            }
        ]
    }

    body = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization":
                "Bearer " + OPENROUTER_API_KEY,
            "HTTP-Referer":
                "https://privateairoom.onrender.com",
            "X-Title":
                "Private AI Room"
        },
        method="POST"
    )

    with urllib.request.urlopen(
        req,
        timeout=60
    ) as response:

        result = json.loads(
            response.read().decode("utf-8")
        )

    return (
        result["choices"][0]
        ["message"]["content"]
    )


# =========================================================
# ORIGINAL OPENAI / CHATGPT
# =========================================================

def ask_chatgpt(text):

    with Codex() as codex:

        thread = codex.thread_start(
            cwd="/tmp",
            ephemeral=True
        )

        result = thread.run(text)

        return result.final_response


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return jsonify({
        "project": "Private AI Room",
        "status": "online",
        "ai": [
            "Human",
            "Original ChatGPT",
            "Gemini",
            "OpenRouter"
        ]
    })


# =========================================================
# HEALTH
# =========================================================

@app.route("/health")
def health():

    return jsonify({
        "status": "healthy"
    })


# =========================================================
# TELEGRAM WEBHOOK
# =========================================================

@app.route(
    "/telegram/webhook",
    methods=["POST"]
)
def telegram_webhook():

    update = request.get_json(
        silent=True
    ) or {}

    message = update.get(
        "message",
        {}
    )

    chat_id = message.get(
        "chat",
        {}
    ).get("id")

    user_id = message.get(
        "from",
        {}
    ).get("id")

    text = message.get(
        "text",
        ""
    )

    if not chat_id:
        return jsonify({
            "ok": True
        })


    # =====================================================
    # OWNER LOCK
    # =====================================================

    if user_id != OWNER_ID:

        send_message(
            chat_id,
            "🔒 Private AI Room is private."
        )

        return jsonify({
            "ok": True
        })


    try:

        # -------------------------------------------------
        # START
        # -------------------------------------------------

        if text == "/start":

            send_message(
                chat_id,
                "🤖 Welcome to Private AI Room!\n\n"
                "👤 Human\n"
                "🧠 Original ChatGPT\n"
                "💜 Gemini\n"
                "🌐 OpenRouter\n\n"
                "🔐 Private access confirmed.\n\n"
                "Normal message → Gemini\n"
                "/gpt message → Original ChatGPT\n"
                "/free message → OpenRouter"
            )

            return jsonify({
                "ok": True
            })


        # -------------------------------------------------
        # MY ID
        # -------------------------------------------------

        if text == "/myid":

            send_message(
                chat_id,
                f"Your Telegram ID is: {user_id}"
            )

            return jsonify({
                "ok": True
            })


        # -------------------------------------------------
        # ORIGINAL CHATGPT
        # -------------------------------------------------

        if text.startswith("/gpt "):

            prompt = text[5:].strip()

            if not prompt:

                send_message(
                    chat_id,
                    "Use:\n/gpt your message"
                )

                return jsonify({
                    "ok": True
                })

            reply = ask_chatgpt(prompt)


        # -------------------------------------------------
        # OPENROUTER
        # -------------------------------------------------

        elif text.startswith("/free "):

            prompt = text[6:].strip()

            if not prompt:

                send_message(
                    chat_id,
                    "Use:\n/free your message"
                )

                return jsonify({
                    "ok": True
                })

            reply = ask_openrouter(prompt)


        # -------------------------------------------------
        # GEMINI
        # -------------------------------------------------

        elif text:

            reply = ask_gemini(text)


        else:

            return jsonify({
                "ok": True
            })


        # -------------------------------------------------
        # SEND
        # -------------------------------------------------

        send_message(
            chat_id,
            reply
        )


    except Exception as e:

        send_message(
            chat_id,
            "⚠️ AI error:\n"
            f"{type(e).__name__}: "
            f"{str(e)[:700]}"
        )


    return jsonify({
        "ok": True
    })


# =========================================================
# TELEGRAM WEBHOOK SETUP
# =========================================================

def setup_telegram():

    if not BOT_TOKEN:
        return

    url = (
        "https://api.telegram.org/bot"
        + BOT_TOKEN
        + "/setWebhook"
    )

    data = json.dumps({
        "url":
            "https://privateairoom.onrender.com/"
            "telegram/webhook"
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type":
                "application/json"
        },
        method="POST"
    )

    try:

        urllib.request.urlopen(
            req,
            timeout=20
        )

    except Exception:
        pass


# =========================================================
# START
# =========================================================

setup_telegram()


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            10000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
