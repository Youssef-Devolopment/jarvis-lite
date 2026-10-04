"""System control skills (Lite): exact volume/brightness, lock, screenshot."""
from __future__ import annotations
import platform
import time
from pathlib import Path
from skills.registry import register
from logger import get_logger

log = get_logger(__name__)
IS_WIN = platform.system() == "Windows"

_SHOT_DIR = Path(__file__).resolve().parent.parent.parent / "logs" / "screenshots"
_SHOT_DIR.mkdir(parents=True, exist_ok=True)


def _lock():
    if not IS_WIN:
        return "Lock only on Windows."
    try:
        import ctypes
        ctypes.windll.user32.LockWorkStation()
        return "Locking the screen."
    except Exception as exc:
        return f"Lock failed: {exc}"


def _screenshot():
    try:
        import pyautogui
        ts = time.strftime("%Y%m%d_%H%M%S")
        path = _SHOT_DIR / f"screen_{ts}.png"
        pyautogui.screenshot(str(path))
        return f"Screenshot saved as {path.name}."
    except Exception as exc:
        return f"Screenshot failed: {str(exc)[:60]}"


@register("volume_set", [
    r"\b(?:set\s+)?volume\s+(?:to\s+)?(?P<level>\d{1,3})\b",
], "Set volume to a specific level (0-100)")
def s_volume_set(text, m):
    level = max(0, min(100, int(m.group("level"))))
    # pyautogui stepping is unreliable, so use pycaw if available.
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        vol = cast(interface, POINTER(IAudioEndpointVolume))
        vol.SetMasterVolumeLevelScalar(level / 100.0, None)
        return f"Volume set to {level}%."
    except Exception:
        return f"Cannot set exact volume. Try 'volume up' or 'volume down'."


@register("brightness_set", [
    r"\b(?:set\s+)?brightness\s+(?:to\s+)?(?P<level>\d{1,3})\b",
], "Set brightness to a specific level (0-100)")
def s_brightness_set(text, m):
    level = max(0, min(100, int(m.group("level"))))
    try:
        import subprocess
        ps = ('powershell -NoProfile -Command "'
              f'(Get-WmiObject -Namespace root/WMI '
              f'-Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,{level})"')
        subprocess.run(ps, capture_output=True, timeout=5)
        return f"Brightness set to {level}%."
    except Exception as exc:
        return f"Brightness set failed: {str(exc)[:60]}"


@register("lock_pc", [
    r"\b(?:lock|secure)\s+(?:the\s+)?(?:screen|pc|computer|windows)\b",
    r"^(?:lock\s+it|lock\s+screen)[\?\.\!]?$",
], "Lock screen")
def s_lock(text, m): return _lock()


@register("screenshot", [
    r"^(?:take\s+)?(?:a\s+)?screenshot(?:\s+of\s+(?:the\s+)?screen)?[\?\.\!]?$",
    r"^capture\s+(?:the\s+)?screen[\?\.\!]?$",
], "Take screenshot")
def s_screenshot(text, m): return _screenshot()
