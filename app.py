import os
import subprocess
from flask import Flask, request, jsonify

app = Flask(__name__)

def ask_chatgpt(message):
    result = subprocess.run(
        ["codex", "exec", message, "--skip-git-repo-check"],
        capture_output=True,
        text=True,
        timeout=180
    )
    if result.returncode != 0:
        raise Exception(result.stderr[-3000:])
    return result.stdout.strip()

@app.get("/")
def home():
    return "Private AI Room: ONLINE"

@app.get("/chat")
def chat_get():
    message = request.args.get("message", "").strip()
    if not message:
        return jsonify({"error": "message required"}), 400
    try:
        return jsonify({"reply": ask_chatgpt(message)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.post("/chat")
def chat_post():
    data = request.get_json(silent=True) or {}
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"error": "message required"}), 400
    try:
        return jsonify({"reply": ask_chatgpt(message)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
