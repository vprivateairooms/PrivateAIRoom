import sqlite3
from pathlib import Path

DB = Path("/workspaces/PrivateAIRoom/recovery.db")

def db():
    c = sqlite3.connect(DB)
    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT NOT NULL,
            role TEXT NOT NULL,
            text TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.commit()
    return c

def add(chat_id, role, text):
    c = db()
    c.execute(
        "INSERT INTO messages(chat_id,role,text) VALUES(?,?,?)",
        (str(chat_id), role, text)
    )
    c.commit()
    c.close()

def get(chat_id):
    c = db()
    rows = c.execute(
        "SELECT role,text FROM messages WHERE chat_id=? ORDER BY id",
        (str(chat_id),)
    ).fetchall()
    c.close()
    return [{"role": r, "text": t} for r, t in rows]
