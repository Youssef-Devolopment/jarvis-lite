"""Simple to-do list. Lite: add + read only."""
from __future__ import annotations
import sqlite3, threading
from datetime import datetime
from pathlib import Path
from skills.registry import register
from logger import get_logger

log = get_logger(__name__)

_DB = Path(__file__).resolve().parent.parent.parent / "memory" / "jarvis_memory.db"
_lock = threading.Lock()


def _conn():
    c = sqlite3.connect(str(_DB), check_same_thread=False)
    c.execute("""CREATE TABLE IF NOT EXISTS todos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task TEXT NOT NULL,
        done INTEGER DEFAULT 0,
        created_at TEXT NOT NULL)""")
    c.commit()
    return c


@register("todo_add", [
    r"^add\s+(?:to\s+)?(?:my\s+)?(?:todo|to-?do|task)(?:\s+list)?[:]?\s+(?P<t>.+?)[\?\.\!]?$",
], "Add to-do")
def s_add(text, m):
    task = (m.group("t") or "").strip()
    if not task:
        return None
    with _lock:
        c = _conn()
        c.execute("INSERT INTO todos (task, created_at) VALUES (?,?)",
                  (task, datetime.now().isoformat(timespec="seconds")))
        c.commit(); c.close()
    return f"Added to-do: {task[:80]}"


@register("todo_read", [
    r"^(?:what(?:'s| is)\s+)?(?:on\s+)?(?:my\s+)?(?:todo|to-?do)(?:\s+list)?[\?\.\!]?$",
    r"^read\s+(?:my\s+)?(?:todo|to-?do)[\?\.\!]?$",
], "Read to-dos")
def s_read(text, m):
    with _lock:
        c = _conn()
        rows = c.execute("SELECT id, task, done FROM todos "
                         "WHERE done = 0 ORDER BY id DESC LIMIT 10").fetchall()
        c.close()
    if not rows:
        return "Your to-do list is empty."
    lines = [f"You have {len(rows)} open tasks:"]
    for _id, task, _ in rows:
        lines.append(f"- {task[:80]}")
    return " ".join(lines)
