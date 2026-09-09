import os
import json
import shutil
import subprocess
import urllib.request
from flask import Flask, request, jsonify


app = Flask(__name__)


# =========================================================
# ENVIRONMENT
# =========================================================

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

OWNER_ID = 8655472622


# =========================================================
# CODEX CHATGPT AUTH
# =========================================================

CODEX_HOME = "/tmp/codex"

SOURCE_AUTH = "/etc/secrets/auth.json"
TARGET_AUTH = "/tmp/codex/auth.json"

os.makedirs(CODEX_HOME, exist_ok=True)

if os.path.exists(SOURCE_AUTH):
    shutil.copyfile(
        SOURCE_AUTH,
        TARGET_AUTH
    )

# Force ChatGPT authentication.
with open(
    "/tmp/codex/config.toml",
    "w",
    encoding="utf-8"
) as f:
    f.write(
        'cli_auth_credentials_store = "file"\n'
        'forced_login_method = "chatgpt"\n'
    )

os.environ["CODEX_HOME"] = CODEX_HOME

# Never use an API key for /gpt.
os.environ.pop("OPENAI_API_KEY", None)


# =========================================================
# FIND CODEX EXECUTABLE
# =========================================================

def find_codex():

    possible_paths = [
        "/opt/render/project/src/.venv/bin/codex",
        "/app/.venv/bin/codex",
        "/usr/local/bin/codex",
        "/usr/bin/codex",
    ]

    for path in possible_paths:

        if os.path.exists(path):
            return path

    # Search PATH
    path = shutil.which("codex")

    if path:
        return path

    # Search installed Python package
    try:

        import importlib.util

        spec = importlib.util.find_spec(
            "codex_cli_bin"
        )

        if spec and spec.submodule_search_locations:

            package_dir = list(
                spec.submodule_search_locations
            )[0]

            candidate = os.path.join(
                package_dir,
                "bin",
                "codex"
            )

            if os.path.exists(candidate):
                return candidate

    except Exception:
        pass

    raise RuntimeError(
        "Codex executable not found."
    )


# =========================================================
# ORIGINAL CHATGPT VIA CODEX CLI
# =========================================================

def ask_chatgpt(text):

    codex = find_codex()

    command = [
        codex,
        "exec",
        text,
        "--skip-git-repo-check"
    ]

    env = os.environ.copy()

    env["CODEX_HOME"] = CODEX_HOME

    # Explicitly prevent API-key authentication.
    env.pop(
        "OPENAI_API_KEY",
        None
    )

    process = subprocess.run(
        command,
        cwd="/tmp",
        env=env,
        capture_output=True,
        text=True,
        timeout=180
    )

    stdout = process.stdout.strip()
    stderr = process.stderr.strip()

    if process.returncode != 0:

        error_text = (
            stderr[-2000:]
            if stderr
            else stdout[-2000:]
        )

        raise RuntimeError(
            "Codex CLI failed:\n"
            + error_text
        )

    # Codex CLI normally prints the answer
    # after the "codex" marker.
    lines = stdout.splitlines()

    answer_lines = []

    capture = False

    for line in lines:

        stripped = line.strip()

        if stripped == "codex":

            capture = True
            continue

        if capture:

            if stripped.startswith("tokens used"):
                break

            answer_lines.append(line)

    answer = "\n".join(
        answer_lines
    ).strip()

    if not answer:

        # Fallback: remove diagnostic lines.
        answer = stdout

    return answer


# =========================================================
# TELEGRAM
# =========================================================

def telegram_api(method, data):

    url = (
        f"https://api.telegram.org/"
        f"bot{BOT_TOKEN}/{method}"
    )

    body = json.dumps(
        data
    ).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type":
                "application/json"
        },
        method="POST"
    )

    with urllib.request.urlopen(
        req,
        timeout=30
    ) as response:

        return json.loads(
            response.read().decode("utf-8")
        )


def send_message(
    chat_id,
    text
):

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
        "https://generativelanguage.googleapis.com/"
        "v1beta/models/"
        "gemini-3.1-flash-lite:"
        "generateContent?key="
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

    body = json.dumps(
        payload
    ).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type":
                "application/json"
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
        "https://openrouter.ai/api/v1/"
        "chat/completions"
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

    body = json.dumps(
        payload
    ).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type":
                "application/json",
            "Authorization":
                "Bearer "
                + OPENROUTER_API_KEY,
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
# HOME
# =========================================================

@app.route("/")
def home():

    return jsonify({
        "project":
            "Private AI Room",
        "status":
            "online",
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
        "status":
            "healthy"
    })


# =========================================================
# TELEGRAM WEBHOOK
# =========================================================

@app.route(
    "/telegram/webhook",
    methods=["POST"]
)
def telegram_webhook():

    update = (
        request.get_json(
            silent=True
        )
        or {}
    )

    message = update.get(
        "message",
        {}
    )

    chat_id = (
        message
        .get("chat", {})
        .get("id")
    )

    user_id = (
        message
        .get("from", {})
        .get("id")
    )

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

            reply = ask_chatgpt(
                prompt
            )


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

            reply = ask_openrouter(
                prompt
            )


        # -------------------------------------------------
        # GEMINI
        # -------------------------------------------------

        elif text:

            reply = ask_gemini(
                text
            )


        else:

            return jsonify({
                "ok": True
            })


        # -------------------------------------------------
        # SEND RESPONSE
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
            f"{str(e)[:1000]}"
        )


    return jsonify({
        "ok": True
    })


# =========================================================
# WEBHOOK SETUP
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
