from skills.base import Skill
from skills.registry import all_skills, dispatch, get_skill, toggle_skill
from skills import registry as _registry


def _load_group(mod):
    """Import a skill subpackage, return names it registered."""
    before = {s.name for s in _registry.all_skills()}
    __import__(f"skills.{mod}", fromlist=["x"])
    return [s.name for s in _registry.all_skills()
            if s.name not in before]


GROUPS = {}
for _g in ("core", "web", "productivity", "system"):
    GROUPS[_g] = _load_group(_g)
del _g

from skills import auto_generated  # noqa: F401

__all__ = ["Skill", "all_skills", "dispatch", "get_skill", "toggle_skill",
           "GROUPS"]
