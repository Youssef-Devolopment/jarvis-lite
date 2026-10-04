"""Tool schemas exposed to the LLM (Lite: only backends present in Lite)."""

TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "remember_fact",
        "description": "Store a durable fact about the user for future sessions.",
        "parameters": {"type": "object",
                       "properties": {"fact": {"type": "string"},
                                      "category": {"type": "string"}},
                       "required": ["fact"]}}},
    {"type": "function", "function": {
        "name": "switch_mood",
        "description": "Switch JARVIS mood: instant, thinking, deep, coding, creative, tutor, fast.",
        "parameters": {"type": "object",
                       "properties": {"name": {"type": "string"}},
                       "required": ["name"]}}},
    {"type": "function", "function": {
        "name": "open_url",
        "description": "Open ANY url as a real tab in the user's browser (shortcuts, domains, or full links).",
        "parameters": {"type": "object",
                       "properties": {"url": {"type": "string"}},
                       "required": ["url"]}}},
]
