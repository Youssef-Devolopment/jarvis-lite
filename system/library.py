"""One-click library: bundled skill packs (Lite).

Everything ships in the repo under ``library/``:

* ``library/catalog.json`` — the catalog (skill packs)
* ``library/skills/*.py``  — pack sources, installed on demand
* ``library/user_catalog.json`` — packs YOU import (gitignored)

Packs go through the SAME validator as community plugins
(``skills.auto_generator._validate``) and hot-load with no restart.

Lite keeps the Library skills-only (no MCP layer here — full JARVIS
owns that surface). v1.8 parity: uninstall, import your own packs as
JSON, installed status.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from logger import get_logger

log = get_logger(__name__)

_ROOT = Path(__file__).resolve().parent.parent
_CATALOG = _ROOT / "library" / "catalog.json"
_PACKS = _ROOT / "library" / "skills"
_USER_CATALOG = _ROOT / "library" / "user_catalog.json"

_ID_RE = re.compile(r"^[a-z][a-z0-9_]{0,29}$")

_PLACEHOLDERS = {
    "{HOME}": str(Path.home()),
    "{DOCUMENTS}": str(Path.home() / "Documents"),
    "{DESKTOP}": str(Path.home() / "Desktop"),
}


def _expand(value):
    """Expand placeholders in a string or list of strings."""
    if isinstance(value, list):
        return [_expand(v) for v in value]
    if isinstance(value, str):
        for key, repl in _PLACEHOLDERS.items():
            value = value.replace(key, repl)
    return value


def _load_user_skills() -> list:
    """Packs the user imported (never raises)."""
    try:
        raw = json.loads(_USER_CATALOG.read_text(encoding="utf-8"))
    except Exception:
        return []
    return [e for e in (raw.get("skills") or [])
            if isinstance(e, dict) and e.get("id") and e.get("code")
            and _ID_RE.match(str(e.get("id", "")))]


def _save_user_skills(entries: list) -> None:
    _USER_CATALOG.parent.mkdir(parents=True, exist_ok=True)
    _USER_CATALOG.write_text(
        json.dumps({"skills": entries}, indent=2), encoding="utf-8")


def load_catalog() -> dict:
    """Read + shape-validate the catalog (shipped + imported). Never raises."""
    try:
        raw = json.loads(_CATALOG.read_text(encoding="utf-8"))
    except Exception as exc:
        log.warning("library catalog unreadable: %s", exc)
        raw = {}
    skills = [e for e in (raw.get("skills") or [])
              if isinstance(e, dict) and e.get("id") and e.get("file")]
    shipped_ids = {e["id"] for e in skills}
    skills += [e for e in _load_user_skills()
               if e["id"] not in shipped_ids]   # shipped wins on clash
    return {"skills": skills}


def _pack_source(entry: dict) -> str:
    """Pack code: inline (imported) or from the bundled file."""
    if entry.get("code"):
        return str(entry["code"])
    return (_PACKS / entry["file"]).read_text(encoding="utf-8")


def _pack_skill_names(entry: dict) -> list:
    """@register names declared inside the pack source."""
    try:
        src = _pack_source(entry)
    except Exception:
        return []
    return re.findall(r'@register\(\s*"([a-z0-9_]+)"', src)


def catalog() -> dict:
    """Catalog with installed flags for the UI."""
    cat = load_catalog()
    try:
        from skills.registry import all_skills
        have_skills = {s.name for s in all_skills()}
    except Exception:
        have_skills = set()
    skills = []
    for e in cat["skills"]:
        names = _pack_skill_names(e)
        skills.append({**e,
                       "code": None,          # never ship code to the UI
                       "skills": names,
                       "installed": bool(names)
                       and all(n in have_skills for n in names)})
    return {"skills": skills}


# ---------- skill packs: install / uninstall / import ---------------------
def install_skill_pack(pid: str) -> dict:
    """One click: pack source -> validated plugin -> hot-load."""
    entry = next((e for e in load_catalog()["skills"]
                  if e["id"] == pid), None)
    if not entry:
        return {"error": f"unknown skill pack: {pid}"}
    try:
        code = _pack_source(entry)
    except Exception as exc:
        return {"error": f"pack file missing: {exc}"}
    from plugins import install_plugin
    res = install_plugin(entry["id"], code)
    if res.get("error"):
        return res
    log.info("library: skill pack %s installed", pid)
    return {"ok": True, "pack": entry["id"],
            "skill": res.get("skill") or entry["id"],
            "name": entry.get("name", entry["id"])}


def uninstall_skill_pack(pid: str) -> dict:
    """Reverse of install: unregister the skills + delete the plugin
    file. Idempotent — removing an absent pack still reports ok."""
    entry = next((e for e in load_catalog()["skills"]
                  if e["id"] == pid), None)
    if not entry:
        return {"error": f"unknown skill pack: {pid}"}
    names = _pack_skill_names(entry)
    unregistered = []
    try:
        from skills import registry
        for n in names:
            if registry.unregister(n):
                unregistered.append(n)
    except Exception as exc:
        log.warning("library: unregister %s failed: %s", pid, exc)
    # Drop the module so a later reinstall re-registers cleanly.
    import sys
    mod = f"plugins.{entry['id']}"
    sys.modules.pop(mod, None)
    try:
        from plugins import _loaded
        if mod in _loaded:
            _loaded.remove(mod)
        if entry["id"] in _loaded:
            _loaded.remove(entry["id"])
    except Exception:
        pass
    deleted = False
    f = _ROOT / "plugins" / f"{entry['id']}.py"
    try:
        if f.is_file() and f.parent == (_ROOT / "plugins"):
            f.unlink()
            deleted = True
    except Exception as exc:
        return {"error": f"could not delete pack file: {exc}"}
    if entry.get("imported"):               # imported packs: drop the record
        kept = [e for e in _load_user_skills() if e["id"] != pid]
        _save_user_skills(kept)
    log.info("library: skill pack %s removed (%d skills, file=%s)",
             pid, len(unregistered), deleted)
    return {"ok": True, "pack": pid, "unregistered": unregistered,
            "file_deleted": deleted}


def import_packs(payload) -> dict:
    """Import user-authored packs (JSON) into the Library.

    Accepts a single pack dict, a list, or {"packs": [...]}. Each pack
    needs an ``id`` (lowercase/underscore) and full ``code``; the code
    must pass the community-plugin validator. Imports are catalogued,
    not auto-installed — hit INSTALL next to them like any other pack.
    """
    from skills.auto_generator import _validate
    if isinstance(payload, list):
        packs = payload
    elif isinstance(payload, dict):
        packs = payload.get("packs") or [payload]
    else:
        return {"error": "expected a pack object or a packs list"}
    existing = _load_user_skills()
    by_id = {e["id"]: e for e in existing}
    shipped = {e["id"] for e in load_catalog()["skills"]}
    results, added = [], 0
    for p in packs:
        if not isinstance(p, dict):
            results.append({"error": "pack must be an object"})
            continue
        pid = str(p.get("id") or "").strip()
        code = str(p.get("code") or "")
        if not _ID_RE.match(pid):
            results.append({"id": pid or "?",
                            "error": "id must be [a-z][a-z0-9_]{0,29}"})
            continue
        if pid in shipped or pid in by_id:
            results.append({"id": pid, "error": "id already in the library"})
            continue
        if not code:
            results.append({"id": pid, "error": "missing 'code'"})
            continue
        try:
            v = _validate(code)
        except ValueError as exc:           # _validate raises on violations
            results.append({"id": pid, "error": f"rejected: {exc}"})
            continue
        if isinstance(v, dict) and v.get("error"):
            results.append({"id": pid,
                            "error": f"rejected: {v['error']}"})
            continue
        by_id[pid] = {"id": pid,
                      "name": str(p.get("name") or pid.replace("_", " ")
                                  ).title()[:40],
                      "description": str(p.get("description")
                                         or v.get("description")
                                         or "Imported pack")[:120],
                      "tags": ["imported"],
                      "imported": True,
                      "code": code}
        added += 1
        results.append({"id": pid, "ok": True,
                        "skill": v.get("name", pid)})
    if added:
        _save_user_skills(list(by_id.values()))
        log.info("library: imported %d pack(s)", added)
    return {"ok": True, "imported": added, "results": results}
