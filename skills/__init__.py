from skills.base import Skill
from skills.registry import all_skills, dispatch, get_skill, toggle_skill
from skills import registry as _registry


def _load_group(mod):
    """Import a skill subpackage, return names it registered.
    One broken file never kills the boot — logged and skipped."""
    from logger import get_logger as _get_logger
    _log = _get_logger(__name__)
    before = {s.name for s in _registry.all_skills()}
    try:
        __import__(f"skills.{mod}", fromlist=["x"])
    except Exception as exc:
        _log.warning("skill group '%s' failed to load: %s", mod, exc)
        return []
    return [s.name for s in _registry.all_skills()
            if s.name not in before]


GROUPS = {}
# NOTE: system loads before web on purpose — "open X" must reach the
# app launcher before web_open claims it as a site search.
for _g in ("core", "system", "web", "productivity"):
    GROUPS[_g] = _load_group(_g)
del _g

from skills import auto_generated  # noqa: F401
from plugins import load_plugins as _load_community_plugins  # noqa: F401

# Skills registered after grouping (auto-generated) get their own group
# so the UI chip list always covers every loaded skill.
_grouped = set()
for _names in GROUPS.values():
    _grouped.update(_names)
GROUPS["other"] = sorted(
    s.name for s in _registry.all_skills() if s.name not in _grouped)
del _grouped

__all__ = ["Skill", "all_skills", "dispatch", "get_skill", "toggle_skill",
           "GROUPS"]
