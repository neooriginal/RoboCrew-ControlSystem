import sqlite3
import os
from pathlib import Path

DB_PATH = os.path.join(os.getcwd(), 'robocrew_memory.db')

def _get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = _get_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def add_memory(text: str):
    conn = _get_connection()
    c = conn.cursor()
    c.execute('INSERT INTO memories (text) VALUES (?)', (text,))
    conn.commit()
    conn.close()

def get_recent_memories(limit: int = 50):
    conn = _get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT id, text, timestamp FROM memories ORDER BY timestamp DESC LIMIT ?', (limit,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]
