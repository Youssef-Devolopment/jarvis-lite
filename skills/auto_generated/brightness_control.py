from skills.registry import register

@register("brightness_control", [
    r"brightness\s*(?:set\s*)?(?:to\s*)?(?P<level>\d{1,3})\s*%?",
    r"(?:set|change|adjust)\s+(?:the\s+)?brightness\s+to\s+(?P<level>\d{1,3})\s*%?",
    r"(?P<direction>increase|decrease|raise|lower|dim|brighten)\s+(?:the\s+)?brightness(?:\s+by\s+(?P<step>\d{1,3})\s*%?)?",
], "Sets or adjusts the screen brightness")
def brightness_control(text, match):
    groups = match.groupdict()
    level = groups.get("level")
    if level:
        value = max(0, min(100, int(level)))
        return "Brightness set to {} percent.".format(value)

    direction = (groups.get("direction") or "").lower()
    if not direction:
        return None

    try:
        step = int(groups.get("step") or 10)
    except ValueError:
        step = 10
    step = max(1, min(100, step))

    if direction in ("increase", "raise", "brighten"):
        return "Increasing brightness by {} percent.".format(step)
    if direction in ("decrease", "lower", "dim"):
        return "Decreasing brightness by {} percent.".format(step)
    return None