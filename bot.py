import os
import json
import subprocess
import requests
import time
from pathlib import Path

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
URL = f"https://api.telegram.org/bot{TOKEN}/"
DATA = Path("conversation_recovery.json")

if DATA.exists():
    history = json.loads(DATA.read_text())
else:
    history = {}

def save():
    DATA.write_text(json.dumps(history, ensure_ascii=False, indent=2))

def send_message(chat_id, text):
    requests.post(
        URL + "sendMessage",
        json={"chat_id": chat_id, "text": text[:4096]},
        timeout=30
    )

def run_codex(prompt):
    result = subprocess.run(
        ["codex", "exec", prompt, "--skip-git-repo-check"],
        capture_output=True,
        text=True,
        timeout=180
    )
    return (result.stdout or result.stderr).strip()

def recovery(chat_id):
    h = history.get(str(chat_id), [])
    if not h:
        return "📦 Recovery: No saved conversation yet."

    text = "📦 PRIVATE AI ROOM RECOVERY\n\n"
    for item in h:
        text += f"{item['role'].upper()}: {item['text']}\n\n"

    for i in range(0, len(text), 4000):
        send_message(chat_id, text[i:i+4000])

def main():
    print("PRIVATE AI ROOM RECOVERY BOT STARTED")
    offset = None

    while True:
        try:
            r = requests.get(
                URL + "getUpdates",
                params={"timeout": 50, "offset": offset},
                timeout=60
            ).json()

            for update in r.get("result", []):
                offset = update["update_id"] + 1

                message = update.get("message")
                if not message or "text" not in message:
                    continue

                chat_id = message["chat"]["id"]
                text = message["text"]
                key = str(chat_id)

                if text == "/recovery":
                    recovery(chat_id)
                    continue

                if key not in history:
                    history[key] = []

                history[key].append({
                    "role": "user",
                    "text": text
                })
                save()

                send_message(chat_id, "🧠 ChatGPT thinking...")

                conversation = "\n".join(
                    f"{x['role'].upper()}: {x['text']}"
                    for x in history[key]
                )

                prompt = f"""
You are the main ChatGPT inside Private AI Room.

Use the complete conversation history below as context.
Continue the conversation naturally.
Do not claim to be Gemini or OpenRouter.

CONVERSATION HISTORY:
{conversation}

USER'S LATEST MESSAGE:
{text}
"""

                try:
                    reply = run_codex(prompt)
                except Exception as e:
                    reply = f"❌ ChatGPT error: {e}"

                if not reply:
                    reply = "❌ Empty response"

                history[key].append({
                    "role": "assistant",
                    "text": reply
                })
                save()

                send_message(chat_id, reply)

        except Exception as e:
            print("Polling error:", e)
            time.sleep(3)

if __name__ == "__main__":
    main()
