"""Lite API: info, chat (skills first, AI fallback), voices."""
from __future__ import annotations
from flask import Blueprint, jsonify, request
from ai import get_client, get_store, extract_memory_async
from errors import ValidationError
from logger import get_logger
from skills import dispatch as dispatch_skill, all_skills
from skills import GROUPS as SKILL_GROUPS
from voice import current_voice, all_voices, set_voice as set_voice_impl
import moods

log = get_logger(__name__)
bp = Blueprint("api", __name__, url_prefix="/api")


@bp.get("/info")
def info():
    from config import get_settings
    s = get_settings()
    return jsonify({
        "app": "jarvis-lite",
        "model": s.model,
        "voice": current_voice(),
        "mood": moods.current_name(),
        "moods": moods.all_moods(),
        "skills": sorted(sk.name for sk in all_skills()),
        "skill_groups": {g: sorted(names)
                         for g, names in SKILL_GROUPS.items()},
    })


@bp.post("/chat")
def chat():
    d = request.get_json(silent=True) or {}
    text = (d.get("text") or "").strip()
    sid = (d.get("sid") or "web").strip() or "web"
    if not text:
        raise ValidationError("Missing 'text'.")
    store = get_store()
    hit = dispatch_skill(text)
    if hit:
        store.messages_for(sid, text)
        store.record_reply(sid, hit)
        extract_memory_async(text, hit)
        return jsonify({"reply": hit, "source": "skill"})
    # Auto-generate hook: approve/reject commands first, then draft on miss.
    try:
        from skills import auto_generator as _ag
        _handled = _ag.handle_approval_text(text)
        if _handled:
            store.messages_for(sid, text)
            store.record_reply(sid, _handled)
            return jsonify({"reply": _handled, "source": "auto_skill"})
        _proposal = _ag.propose_if_enabled(text)
    except Exception:
        _proposal = None
    if _proposal:
        _prompt = _ag.approval_prompt(_proposal)
        store.messages_for(sid, text)
        store.record_reply(sid, _prompt)
        return jsonify({"reply": _prompt, "source": "auto_skill",
                        "proposal": {"name": _proposal["name"],
                                     "test_ok": _proposal["test_ok"]}})
    from ai.tools import TOOL_SCHEMAS
    messages = store.messages_for(sid, text)
    # stream() installs the full system prompt itself; seed an empty one.
    working = ([{"role": "system", "content": ""}]
               + [m for m in messages if m.get("role") in ("user", "assistant")])
    c = get_client()
    parts = []
    for kind, payload in c.stream(working, tools=TOOL_SCHEMAS):
        if kind == "content":
            parts.append(payload)
    reply = "".join(parts).strip()
    store.record_reply(sid, reply)
    extract_memory_async(text, reply)
    return jsonify({"reply": reply, "source": "ai"})


@bp.get("/voices")
def voices_list():
    return jsonify({"voices": all_voices(), "active": current_voice()["key"]})


@bp.post("/voice")
def voice_set():
    from voice import speak_async
    d = request.get_json(silent=True) or {}
    key = (d.get("key") or "").strip()
    if not key:
        raise ValidationError("Missing 'key'.")
    v = set_voice_impl(key)
    if not v:
        raise ValidationError(f"Unknown voice: {key}")
    speak_async(f"Hello, I am {v['label']}. This is my voice.")
    return jsonify({"ok": True, "voice": current_voice()})


@bp.get("/auto_skills/pending")
def auto_skills_pending():
    from skills import auto_generator as _ag
    return jsonify({"pending": _ag.list_pending(),
                    "enabled": _ag.auto_gen_enabled()})


@bp.post("/auto_skills/approve")
def auto_skills_approve():
    from skills import auto_generator as _ag
    d = request.get_json(silent=True) or {}
    name = (d.get("name") or "").strip()
    if not name:
        raise ValidationError("Missing 'name'.")
    r = _ag.approve_skill(name)
    if not r.get("ok"):
        raise ValidationError(r.get("error") or "Approve failed.")
    return jsonify({"ok": True, "name": r["name"]})


@bp.post("/auto_skills/reject")
def auto_skills_reject():
    from skills import auto_generator as _ag
    d = request.get_json(silent=True) or {}
    name = (d.get("name") or "").strip()
    if not name:
        raise ValidationError("Missing 'name'.")
    r = _ag.reject_skill(name)
    if not r.get("ok"):
        raise ValidationError(r.get("error") or "Reject failed.")
    return jsonify({"ok": True, "name": r["name"]})


@bp.post("/auto_skills/enabled")
def auto_skills_enabled():
    from skills import auto_generator as _ag
    d = request.get_json(silent=True) or {}
    ok = _ag.set_auto_gen_enabled(bool(d.get("enabled", True)))
    if not ok:
        raise ValidationError("Could not save preference.")
    return jsonify({"ok": True, "enabled": _ag.auto_gen_enabled()})
