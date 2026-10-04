"""Tool dispatcher — Lite version (only backends present in Lite)."""

from __future__ import annotations
from logger import get_logger
from memory import context as ctx_tracker

log = get_logger(__name__)


def execute_tool(name: str, args: dict) -> str:
    try:
        _brief = str(args)[:150] if args else ""
        ctx_tracker.log_event("action", f"{name} {_brief}")
    except Exception:
        pass
    try:
        if name == "remember_fact":
            from memory import remember
            fact = (args.get("fact") or "").strip()
            cat = (args.get("category") or "general").strip()
            if not fact: return "Error: empty fact."
            remember(fact, category=cat, source="tool")
            return f"Remembered: {fact}"
        if name == "switch_mood":
            from moods import set_mood
            m = set_mood(args.get("name") or "")
            if m:
                return f"Switched to {m.name} mood."
            return "Unknown mood."
        if name == "open_url":
            from system import launch as _L
            out = _L.open_url(args.get("url", ""))
            return out or "Could not open that."
        return f"Unknown tool: {name}"
    except Exception as exc:
        log.exception("Tool '%s' failed", name)
        return f"Tool error: {exc}"


def mcp_schemas() -> list:
    """No MCP servers in Lite — always empty."""
    return []
