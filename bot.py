import os
import subprocess
import requests
import time
from recovery import add, get

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
URL = f"https://api.telegram.org/bot{TOKEN}/"

def send(chat_id, text):
    requests.post(
        URL + "sendMessage",
        json={"chat_id": chat_id, "text": text[:4096]},
        timeout=30
    )

def chatgpt(prompt):
    r = subprocess.run(
        [os.environ.get("CODEX_BIN", "codex"), "exec",
         prompt, "--skip-git-repo-check"],
        capture_output=True,
        text=True,
        timeout=180
    )
    return (r.stdout or r.stderr).strip()

def main():
    print("PRIVATE AI ROOM FINAL BOT STARTED")
    offset = None

    while True:
        try:
            data = requests.get(
                URL + "getUpdates",
                params={"timeout": 50, "offset": offset},
                timeout=60
            ).json()

            for update in data.get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message")

                if not msg or "text" not in msg:
                    continue

                chat_id = msg["chat"]["id"]
                text = msg["text"]

                if text == "/recovery":
                    history = get(chat_id)

                    if not history:
                        send(chat_id, "📦 No saved conversation yet.")
                    else:
                        out = "📦 PRIVATE AI ROOM RECOVERY\n\n"
                        for item in history:
                            out += f"{item['role'].upper()}: {item['text']}\n\n"

                        for i in range(0, len(out), 4000):
                            send(chat_id, out[i:i+4000])
                    continue

                add(chat_id, "user", text)
                send(chat_id, "🧠 ChatGPT thinking...")

                history = get(chat_id)
                context = "\n".join(
                    f"{x['role'].upper()}: {x['text']}"
                    for x in history
                )

                prompt = f"""You are the main ChatGPT inside Private AI Room.

Use this saved conversation as context:

{context}

Answer the latest user message naturally.
"""

                try:
                    reply = chatgpt(prompt)
                except Exception as e:
                    reply = f"❌ ChatGPT error: {e}"

                if not reply:
                    reply = "❌ Empty response"

                add(chat_id, "assistant", reply)
                send(chat_id, reply)

        except Exception as e:
            print("Polling error:", e)
            time.sleep(3)

if __name__ == "__main__":
    main()
