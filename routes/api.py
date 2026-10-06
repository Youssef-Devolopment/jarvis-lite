"""Lite API: info, chat (skills first, AI fallback), voices, HUD, library."""
from __future__ import annotations
import json
import threading
from flask import Blueprint, jsonify, request, Response
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


# ---------- COMMAND (SSE mirror of /chat, for the floating HUD) ----------
_SSE_HEADERS = {
    "Cache-Control": "no-cache", "X-Accel-Buffering": "no",
    "Connection": "keep-alive",
}


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


@bp.post("/command")
def command():
    """Stream a chat as SSE: skill/auto replies leave as one delta,
    AI tokens stream live as they arrive. Body: {text, session}."""
    d = request.get_json(silent=True) or {}
    text = (d.get("text") or "").strip()
    sid = (d.get("session") or d.get("sid") or "web").strip() or "web"
    if not text:
        raise ValidationError("Missing 'text'.")
    if len(text) > 4000:
        raise ValidationError("Command too long.")

    def gen():
        store = get_store()
        hit = dispatch_skill(text)
        if hit:
            store.messages_for(sid, text)
            store.record_reply(sid, hit)
            extract_memory_async(text, hit)
            yield _sse({"delta": hit, "source": "skill"})
            yield "data: [DONE]\n\n"
            return
        try:
            from skills import auto_generator as _ag
            handled = _ag.handle_approval_text(text)
            if handled:
                store.messages_for(sid, text)
                store.record_reply(sid, handled)
                yield _sse({"delta": handled, "source": "auto_skill"})
                yield "data: [DONE]\n\n"
                return
            proposal = _ag.propose_if_enabled(text)
        except Exception:
            proposal = None
        if proposal:
            prompt = _ag.approval_prompt(proposal)
            store.messages_for(sid, text)
            store.record_reply(sid, prompt)
            yield _sse({"delta": prompt, "source": "auto_skill"})
            yield "data: [DONE]\n\n"
            return
        from ai.tools import TOOL_SCHEMAS
        messages = store.messages_for(sid, text)
        working = ([{"role": "system", "content": ""}]
                   + [m for m in messages
                      if m.get("role") in ("user", "assistant")])
        try:
            c = get_client()
        except Exception as exc:
            yield _sse({"error": str(exc)[:200]})
            yield "data: [DONE]\n\n"
            return
        parts = []
        try:
            for kind, payload in c.stream(working, tools=TOOL_SCHEMAS):
                if kind == "content" and payload:
                    parts.append(payload)
                    yield _sse({"delta": payload})
        except Exception as exc:
            # provider outage mid-stream: surface it as a reply error
            # instead of a dead 500 (headers are already sent here).
            yield _sse({"error": str(exc)[:300]})
            yield "data: [DONE]\n\n"
            return
        reply = "".join(parts).strip()
        store.record_reply(sid, reply)
        extract_memory_async(text, reply)
        yield "data: [DONE]\n\n"

    return Response(gen(), mimetype="text/event-stream",
                    headers=_SSE_HEADERS)


# ---------- LISTEN (HUD mic) ----------
@bp.post("/listen")
def listen_route():
    try:
        from voice.input import listen_until_silence
        text = listen_until_silence(verbose=False)
    except Exception as exc:
        log.exception("Listen failed")
        return jsonify({"error": str(exc),
                        "hint": "Check logs and GROQ_API_KEY"}), 500
    if text is None:
        return jsonify({"text": "", "empty": True,
                        "hint": "Set GROQ_API_KEY in .env for dictation"})
    return jsonify({"text": text, "empty": not bool(text)})


# ---------- OVERLAY (floating HUD) ----------
@bp.get("/overlay/state")
def overlay_state():
    from system import overlay
    st = overlay._state
    th = st.get("thread")
    return jsonify({"ready": bool(overlay._ready.is_set()),
                    "visible": bool(st.get("visible")),
                    "thread_alive": bool(th and th.is_alive()),
                    "root": bool(st.get("root"))})


@bp.post("/overlay/toggle")
def overlay_toggle():
    from system import overlay
    threading.Thread(target=overlay.toggle, daemon=True).start()
    return jsonify({"ok": True})


# ---------- LIBRARY (one-click skill packs) ----------
@bp.get("/library")
def library_catalog():
    from system import library
    return jsonify(library.catalog())


@bp.post("/library/skill")
def library_skill_install():
    """One click: install a pack (hot-loads, no restart), or remove
    it with {"remove": true}. Body: {"id": str, "remove": bool}"""
    from system import library
    d = request.get_json(silent=True) or {}
    pid = (d.get("id") or "").strip()
    if not pid:
        raise ValidationError("Missing 'id'.")
    r = (library.uninstall_skill_pack(pid) if d.get("remove")
         else library.install_skill_pack(pid))
    if r.get("error"):
        raise ValidationError(r["error"])
    return jsonify(r)


@bp.post("/library/import")
def library_import():
    """Import user-authored packs (JSON). Body: a pack object, a
    list, or {"packs": [...]} — each needs id + code."""
    from system import library
    d = request.get_json(silent=True) or {}
    r = library.import_packs(d)
    if r.get("error"):
        raise ValidationError(r["error"])
    return jsonify(r)
